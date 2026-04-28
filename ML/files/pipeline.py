"""
pipeline.py - fully generic fairness pipeline.

The API still accepts any CSV with target_col + sensitive_col, but the
preprocessing and remediation paths now preserve the original labels. A
"debiased CSV" is a data-level remediation artifact, not model predictions
written over ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd
from fairlearn.metrics import (
    MetricFrame,
    demographic_parity_difference,
    demographic_parity_ratio,
    equalized_odds_difference,
)
from fairlearn.postprocessing import ThresholdOptimizer
from fairlearn.reductions import DemographicParity, ExponentiatedGradient, TruePositiveRateParity
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


FairnessCriterion = Literal["equal_opportunity", "demographic_parity"]
RemediationMethod = Literal["reweighing", "disparate_impact_remover"]


_state = {
    "baseline": None,
    "reweighted_model": None,
    "threshold_model": None,
    "X_test": None,
    "y_test": None,
    "A_test": None,
    "A_test_raw": None,
    "feature_cols": None,
    "target_col": None,
    "sensitive_col": None,
    "sensitive_groups": None,
    "sensitive_encoder": None,
    "sensitive_info": None,
    "preprocessor": None,
    "target_info": None,
    "positive_label": None,
    "scaler": None,
    "label_encoders": {},
    "trained": False,
    "domain": None,
    "raw_df": None,
    "dashboard_stats": None,
    "dashboard_sensitive_cols": None,
    "audit_id": None,
    "audit_result": None,
    "dataset_name": None,
    "user_id": None,
    "fairness_criterion": "equal_opportunity",
    "difference_bound": 0.05,
}


@dataclass(frozen=True)
class RemediationResult:
    dataframe: pd.DataFrame
    method: str
    repair_level: float
    weight_power: float
    original_di_ratio: float
    verified_di_ratio_after_retraining: float
    verified_metrics: dict
    attempts: int


def detect_columns(df: pd.DataFrame, target_col: str, sensitive_col: str) -> list[str]:
    """Return usable feature columns, excluding target, sensitive, IDs, and sparse columns."""
    exclude = {target_col, sensitive_col}
    feature_cols = []
    for col in df.columns:
        if col in exclude:
            continue
        id_hints = ["id", "name", "ref", "code", "num", "index", "uuid", "key"]
        if any(h in col.lower() for h in id_hints) and df[col].nunique() > 0.9 * len(df):
            continue
        if df[col].isnull().mean() > 0.5:
            continue
        if df[col].dtype == object and df[col].nunique() == len(df):
            continue
        feature_cols.append(col)
    return feature_cols


def _is_categorical(series: pd.Series) -> bool:
    return (
        series.dtype == object
        or series.dtype.name in ("category", "string")
        or pd.api.types.is_string_dtype(series)
        or pd.api.types.is_bool_dtype(series)
    )


def _make_preprocessor(df: pd.DataFrame, feature_cols: list[str]) -> ColumnTransformer:
    categorical_cols = [col for col in feature_cols if _is_categorical(df[col])]
    numeric_cols = [col for col in feature_cols if col not in categorical_cols]

    numeric_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipe = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipe, numeric_cols),
            ("categorical", categorical_pipe, categorical_cols),
        ],
        remainder="drop",
    )


def _normalize_label(value) -> str:
    return str(value).strip().lower()


def encode_target(series: pd.Series, positive_label: str | None = None) -> tuple[np.ndarray, dict]:
    """
    Encode target to 0/1. Ambiguous string targets must provide positive_label.
    """
    valid = series.dropna()
    if valid.empty:
        raise ValueError("Target column has no non-null values.")

    if pd.api.types.is_bool_dtype(valid):
        return series.astype(bool).astype(int).to_numpy(), {
            "kind": "bool",
            "positive_label": "True",
        }

    if pd.api.types.is_numeric_dtype(valid):
        numeric = pd.to_numeric(series, errors="coerce")
        unique = sorted(v for v in numeric.dropna().unique())
        if len(unique) != 2:
            raise ValueError("Target column must be binary. Numeric target has more than two values.")
        pos = float(positive_label) if positive_label is not None else max(unique)
        if pos not in unique:
            raise ValueError(f"positive_label '{positive_label}' is not present in target_col.")
        return (numeric == pos).astype(int).to_numpy(), {
            "kind": "numeric",
            "positive_label": pos,
            "negative_label": min(v for v in unique if v != pos),
        }

    text = series.astype(str).str.strip()
    normalized = text.str.lower()
    unique = [v for v in normalized.dropna().unique() if v and v != "nan"]
    if len(unique) != 2:
        raise ValueError("Target column must be binary. Provide a binary target column.")

    if positive_label is not None:
        pos_norm = _normalize_label(positive_label)
        if pos_norm not in unique:
            raise ValueError(f"positive_label '{positive_label}' is not present in target_col.")
    else:
        pos_keywords = [
            "yes", "true", "1", "approved", "approve", "hired", "hire",
            "accept", "accepted", "positive", "readmit", "pass", "selected",
        ]
        matches = [v for v in unique if any(k in v for k in pos_keywords)]
        if len(matches) != 1:
            raise ValueError(
                "Could not infer the positive label for target_col. "
                "Pass positive_label explicitly."
            )
        pos_norm = matches[0]

    original_pos = next(str(v).strip() for v in text.dropna().unique() if _normalize_label(v) == pos_norm)
    return (normalized == pos_norm).astype(int).to_numpy(), {
        "kind": "categorical",
        "positive_label": original_pos,
        "positive_label_normalized": pos_norm,
        "classes": sorted(unique),
    }


def transform_target(series: pd.Series, target_info: dict | None = None) -> np.ndarray:
    if target_info is None:
        return encode_target(series)[0]
    kind = target_info.get("kind")
    if kind == "bool":
        return series.astype(bool).astype(int).to_numpy()
    if kind == "numeric":
        numeric = pd.to_numeric(series, errors="coerce")
        return (numeric == target_info["positive_label"]).astype(int).to_numpy()
    normalized = series.astype(str).str.strip().str.lower()
    return (normalized == target_info["positive_label_normalized"]).astype(int).to_numpy()


def _fit_sensitive(series: pd.Series) -> tuple[np.ndarray, np.ndarray, list[str], dict]:
    clean = series.copy()
    if _is_categorical(clean):
        raw = clean.astype(str).str.strip().replace("", "Unknown").fillna("Unknown")
        groups = sorted(raw.unique().tolist())
        mapping = {group: idx for idx, group in enumerate(groups)}
        encoded = raw.map(mapping).astype(int).to_numpy()
        return encoded, raw.to_numpy(), groups, {"kind": "categorical", "mapping": mapping, "groups": groups}

    numeric = pd.to_numeric(clean, errors="coerce")
    if numeric.notna().sum() < 2:
        raw = numeric.astype("string").fillna("Unknown")
        groups = sorted(raw.unique().tolist())
        mapping = {group: idx for idx, group in enumerate(groups)}
        return raw.map(mapping).astype(int).to_numpy(), raw.to_numpy(), groups, {
            "kind": "categorical",
            "mapping": mapping,
            "groups": groups,
        }

    labels = ["Group_Q1", "Group_Q2", "Group_Q3", "Group_Q4"]
    binned, bins = pd.qcut(numeric, q=4, labels=labels, duplicates="drop", retbins=True)
    used_labels = [str(label) for label in binned.dropna().astype(str).unique()]
    groups = sorted(used_labels)
    mapping = {group: idx for idx, group in enumerate(groups)}
    raw = binned.astype("string").fillna("Unknown")
    if "Unknown" in raw.unique() and "Unknown" not in mapping:
        mapping["Unknown"] = len(mapping)
        groups.append("Unknown")
    encoded = raw.map(mapping).fillna(mapping.get("Unknown", 0)).astype(int).to_numpy()
    return encoded, raw.to_numpy(), groups, {
        "kind": "numeric_quantile",
        "bins": bins.tolist(),
        "labels": labels[: max(len(bins) - 1, 0)],
        "mapping": mapping,
        "groups": groups,
    }


def transform_sensitive(series: pd.Series, info: dict | None = None) -> tuple[np.ndarray, np.ndarray]:
    if info is None:
        encoded, raw, _, _ = _fit_sensitive(series)
        return encoded, raw

    if info.get("kind") == "numeric_quantile":
        numeric = pd.to_numeric(series, errors="coerce")
        bins = np.array(info["bins"], dtype=float)
        if len(bins) > 0:
            bins[0] = -np.inf
            bins[-1] = np.inf
        raw = pd.cut(numeric, bins=bins, labels=info["labels"], include_lowest=True)
        raw = raw.astype("string").fillna("Unknown")
    else:
        raw = series.astype(str).str.strip().replace("", "Unknown").fillna("Unknown")

    mapping = info.get("mapping") or {}
    unknown = mapping.get("Unknown", 0)
    encoded = raw.map(mapping).fillna(unknown).astype(int).to_numpy()
    return encoded, raw.to_numpy()


def encode_sensitive(series: pd.Series):
    """Backward-compatible wrapper used by dashboard and older imports."""
    encoded, raw, groups, info = _fit_sensitive(series)
    return encoded, info, groups, raw


def _fairness_constraint(fairness_criterion: str, difference_bound: float):
    if fairness_criterion == "demographic_parity":
        return DemographicParity(difference_bound=difference_bound)
    if fairness_criterion in ("equal_opportunity", "true_positive_rate_parity"):
        return TruePositiveRateParity(difference_bound=difference_bound)
    raise ValueError(f"Unsupported fairness_criterion '{fairness_criterion}'.")


def _threshold_constraint(fairness_criterion: str) -> str:
    if fairness_criterion == "demographic_parity":
        return "demographic_parity"
    if fairness_criterion in ("equal_opportunity", "true_positive_rate_parity"):
        return "true_positive_rate_parity"
    raise ValueError(f"Unsupported fairness_criterion '{fairness_criterion}'.")


def _joint_stratify(y: np.ndarray, A: np.ndarray):
    joint = pd.Series(y).astype(str) + "|" + pd.Series(A).astype(str)
    if joint.value_counts().min() >= 2:
        return joint
    if pd.Series(y).value_counts().min() >= 2:
        return y
    return None


def load_and_preprocess(
    df: pd.DataFrame,
    target_col: str,
    sensitive_col: str,
    feature_cols: list[str],
    positive_label: str | None = None,
):
    """
    Keep only rows with target/sensitive present, encode y/A, and build a raw X frame.
    Feature missingness is handled later inside the train-only ColumnTransformer.
    """
    work = df.dropna(subset=[target_col, sensitive_col]).copy()
    if work.empty:
        raise ValueError("No rows remain after dropping missing target/sensitive values.")

    y, target_info = encode_target(work[target_col], positive_label=positive_label)
    A, A_raw, groups, sensitive_info = _fit_sensitive(work[sensitive_col])
    X = work[feature_cols].copy()
    return X, y, A, A_raw, work.index, target_info, sensitive_info, groups


def train_pipeline(
    df: pd.DataFrame,
    target_col: str,
    sensitive_col: str,
    domain: str = "custom",
    positive_label: str | None = None,
    fairness_criterion: FairnessCriterion = "equal_opportunity",
    difference_bound: float = 0.05,
) -> dict:
    """Train baseline, in-processing fairness model, and threshold optimizer."""
    np.random.seed(42)

    # Extract instance_weight BEFORE feature detection so it is never used as a
    # predictor. When a debiased CSV is re-uploaded, instance_weight is a direct
    # proxy for the sensitive attribute (Reweighing assigns higher weights to
    # under-represented groups), so including it as a feature would make the
    # model MORE discriminatory, not less.
    sample_weights_series: pd.Series | None = None
    if "instance_weight" in df.columns:
        sample_weights_series = df["instance_weight"].copy()
        df = df.drop(columns=["instance_weight"])

    feature_cols = detect_columns(df, target_col, sensitive_col)
    if not feature_cols:
        raise ValueError("No usable feature columns detected in this CSV.")

    X, y, A, A_raw, kept_index, target_info, sensitive_info, groups = load_and_preprocess(
        df, target_col, sensitive_col, feature_cols, positive_label=positive_label
    )

    # Align sample weights to the rows that survived dropna in load_and_preprocess.
    sw: np.ndarray | None = None
    if sample_weights_series is not None:
        sw = sample_weights_series.reindex(kept_index).fillna(1.0).to_numpy()

    stratify = _joint_stratify(y, A)
    if sw is not None:
        X_train, X_test, y_train, y_test, A_train, A_test, Araw_train, Araw_test, sw_train, sw_test = train_test_split(
            X, y, A, A_raw, sw, test_size=0.3, random_state=42, stratify=stratify
        )
    else:
        X_train, X_test, y_train, y_test, A_train, A_test, Araw_train, Araw_test = train_test_split(
            X, y, A, A_raw, test_size=0.3, random_state=42, stratify=stratify
        )
        sw_train = sw_test = None

    baseline = Pipeline(
        steps=[
            ("preprocessor", _make_preprocessor(X_train, feature_cols)),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )
    if sw_train is not None:
        baseline.fit(X_train, y_train, classifier__sample_weight=sw_train)
    else:
        baseline.fit(X_train, y_train)

    # Pre-transform using the already-fitted baseline preprocessor so EG receives
    # a plain numpy array. This avoids the sklearn Pipeline + ExponentiatedGradient
    # sample_weight routing issue (broken in sklearn >=1.5, unreliable in 1.4).
    fitted_preprocessor = baseline.named_steps["preprocessor"]
    X_train_t = fitted_preprocessor.transform(X_train)

    base_estimator = LogisticRegression(max_iter=1000, solver="liblinear", random_state=42)
    reweighted_model = ExponentiatedGradient(
        estimator=base_estimator,
        constraints=_fairness_constraint(fairness_criterion, difference_bound),
        eps=0.05,
    )
    # EG constraints (TruePositiveRateParity, DemographicParity) do not all
    # accept sample_weight — EG handles fairness via its own constraint solver,
    # so we rely on the baseline having already been fit on the weighted data.
    reweighted_model.fit(X_train_t, y_train, sensitive_features=A_train)

    threshold_model = ThresholdOptimizer(
        estimator=baseline,
        constraints=_threshold_constraint(fairness_criterion),
        objective="balanced_accuracy_score",
        predict_method="predict_proba",
        prefit=True,
    )
    to_fit_kwargs: dict = {"sensitive_features": A_train}
    if sw_train is not None:
        to_fit_kwargs["sample_weight"] = sw_train
    threshold_model.fit(X_train, y_train, **to_fit_kwargs)

    _state.update({
        "baseline": baseline,
        "reweighted_model": reweighted_model,
        "threshold_model": threshold_model,
        "X_test": X_test,
        "y_test": y_test,
        "A_test": A_test,
        "A_test_raw": Araw_test,
        "feature_cols": feature_cols,
        "target_col": target_col,
        "sensitive_col": sensitive_col,
        "sensitive_groups": groups,
        "sensitive_encoder": sensitive_info,
        "sensitive_info": sensitive_info,
        "preprocessor": baseline.named_steps["preprocessor"],
        "target_info": target_info,
        "positive_label": target_info.get("positive_label"),
        "scaler": None,
        "label_encoders": {},
        "trained": True,
        "domain": domain,
        "raw_df": df.copy(),
        "kept_index": kept_index,
        "dashboard_stats": None,
        "dashboard_sensitive_cols": None,
        "fairness_criterion": fairness_criterion,
        "difference_bound": difference_bound,
    })

    audit = get_audit()
    _state["audit_result"] = audit
    return audit


def _compute_metrics(label: str, y_true, y_pred, A, A_raw, groups) -> dict:
    acc = float(accuracy_score(y_true, y_pred))
    dpd = float(demographic_parity_difference(y_true, y_pred, sensitive_features=A))
    dpr = float(demographic_parity_ratio(y_true, y_pred, sensitive_features=A))
    eod = float(equalized_odds_difference(y_true, y_pred, sensitive_features=A))

    mf = MetricFrame(
        metrics={"approval_rate": lambda yt, yp: float(np.mean(yp)) if len(yp) else 0.0},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=A_raw,
    )
    group_rates = {
        str(grp): round(float(rate), 3)
        for grp, rate in mf.by_group["approval_rate"].items()
    }

    return {
        "model": label,
        "accuracy": round(acc, 3),
        "group_approval_rates": group_rates,
        "disparate_impact_ratio": round(dpr, 3),
        "demographic_parity_difference": round(dpd, 3),
        "equalized_odds_difference": round(eod, 3),
        "legal_pass": bool(dpr >= 0.8),
        "legal_threshold": "EEOC 80% rule: DI ratio >= 0.80",
    }


def get_audit() -> dict:
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet. Call POST /upload first.")

    if _state.get("X_test") is None:
        cached_audit = _state.get("audit_result")
        if cached_audit:
            return cached_audit
        raise RuntimeError("Audit metrics are not available for the loaded model state.")

    X_test = _state["X_test"]
    y_test = _state["y_test"]
    A_test = _state["A_test"]
    A_raw = _state["A_test_raw"]
    groups = _state["sensitive_groups"]

    preprocessor = _state.get("preprocessor")
    X_test_t = preprocessor.transform(X_test) if preprocessor is not None else X_test

    y_pred_baseline = _state["baseline"].predict(X_test)
    y_pred_reweighted = _state["reweighted_model"].predict(X_test_t)
    y_pred_threshold = _state["threshold_model"].predict(X_test, sensitive_features=A_test)

    return {
        "domain": _state["domain"],
        "target_col": _state["target_col"],
        "sensitive_col": _state["sensitive_col"],
        "groups_found": groups,
        "feature_cols": _state["feature_cols"],
        "fairness_criterion": _state.get("fairness_criterion", "equal_opportunity"),
        "difference_bound": _state.get("difference_bound", 0.05),
        "positive_label": _state.get("positive_label"),
        "results": [
            _compute_metrics("Baseline (biased)", y_test, y_pred_baseline, A_test, A_raw, groups),
            _compute_metrics("Fair in-processing (Stage 1)", y_test, y_pred_reweighted, A_test, A_raw, groups),
            _compute_metrics("Threshold optimizer (Stage 3)", y_test, y_pred_threshold, A_test, A_raw, groups),
        ],
    }


def predict_applicant(features: dict, sensitive_value: str) -> dict:
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet.")

    feature_cols = _state["feature_cols"]
    missing = [col for col in feature_cols if col not in features]
    if missing:
        raise ValueError(f"Missing feature(s): {missing}")

    x_frame = pd.DataFrame([{col: features.get(col) for col in feature_cols}])
    A_arr, _ = transform_sensitive(pd.Series([sensitive_value]), _state.get("sensitive_info"))

    preprocessor = _state.get("preprocessor")
    x_frame_t = preprocessor.transform(x_frame) if preprocessor is not None else x_frame

    baseline_pred = int(_state["baseline"].predict(x_frame)[0])
    baseline_prob = round(float(_state["baseline"].predict_proba(x_frame)[0][1]), 3)
    reweighted_pred = int(_state["reweighted_model"].predict(x_frame_t)[0])
    threshold_pred = int(_state["threshold_model"].predict(x_frame, sensitive_features=A_arr)[0])

    target = _state["target_col"]
    pos_label = str(_state.get("positive_label") or "POSITIVE").upper()
    neg_label = "NEGATIVE"

    return {
        "sensitive_col": _state["sensitive_col"],
        "sensitive_value": sensitive_value,
        "target_col": target,
        "baseline": {
            "decision": baseline_pred,
            "probability": baseline_prob,
            "label": pos_label if baseline_pred else neg_label,
        },
        "reweighted": {
            "decision": reweighted_pred,
            "label": pos_label if reweighted_pred else neg_label,
        },
        "threshold_calibrated": {
            "decision": threshold_pred,
            "label": pos_label if threshold_pred else neg_label,
        },
        "bias_detected": baseline_pred != reweighted_pred or baseline_pred != threshold_pred,
        "note": "bias_detected=True means the fair model changed the baseline decision.",
    }


def get_schema() -> dict:
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet.")
    return {
        "feature_cols": _state["feature_cols"],
        "target_col": _state["target_col"],
        "sensitive_col": _state["sensitive_col"],
        "sensitive_groups": _state["sensitive_groups"],
        "domain": _state["domain"],
        "fairness_criterion": _state.get("fairness_criterion"),
        "positive_label": _state.get("positive_label"),
    }


def _coerce_target_to_binary(series: pd.Series) -> pd.Series:
    target_info = _state.get("target_info")
    if target_info is not None:
        return pd.Series(transform_target(series, target_info), index=series.index, dtype=float)
    return pd.Series(encode_target(series)[0], index=series.index, dtype=float)


def _attribute_labels(df: pd.DataFrame, sensitive_col: str) -> pd.Series:
    series = df[sensitive_col]
    if "age" in sensitive_col.lower() and pd.api.types.is_numeric_dtype(series):
        ages = pd.to_numeric(series, errors="coerce")
        return pd.cut(
            ages,
            bins=[-np.inf, 30, 40, 50, np.inf],
            labels=["22-30", "31-40", "41-50", "51+"],
        ).astype("string")
    return series.astype("string").str.strip()


def _round_or_none(value, digits: int = 3):
    if pd.isna(value):
        return None
    return round(float(value), digits)


def compute_group_stats(
    df: pd.DataFrame,
    target_col: str,
    sensitive_cols: list[str],
    use_debiased: bool = False,
) -> dict:
    if target_col not in df.columns:
        raise ValueError(f"target_col '{target_col}' not found in dataset.")
    if not sensitive_cols:
        raise ValueError("At least one sensitive column is required.")

    missing = [col for col in sensitive_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Sensitive column(s) not found: {missing}")

    work = df.copy()
    target_binary = None
    if _state.get("trained") and _state.get("baseline") is not None:
        try:
            feature_cols = _state["feature_cols"]
            model_input = work[feature_cols].copy()
            if use_debiased and _state.get("reweighted_model") is not None and _state.get("preprocessor") is not None:
                # Use EG (Fair in-processing) for the debiased view — it improves
                # demographic parity DI. ThresholdOptimizer optimises TPR parity which
                # can worsen demographic parity on some datasets.
                X_t = _state["preprocessor"].transform(model_input)
                target_binary = pd.Series(
                    _state["reweighted_model"].predict(X_t).astype(float),
                    index=work.index,
                )
            else:
                target_binary = pd.Series(
                    _state["baseline"].predict(model_input).astype(float),
                    index=work.index,
                )
        except Exception:
            target_binary = None

    if target_binary is None:
        target_binary = _coerce_target_to_binary(work[target_col])
    work["_target_binary"] = target_binary
    valid_sensitive_cols = [col for col in sensitive_cols if col in work.columns]

    numeric_feature_cols = [
        col
        for col in work.select_dtypes(include=[np.number]).columns
        if col not in set(valid_sensitive_cols + [target_col]) and not col.startswith("_")
    ]

    by_attribute = {}
    di_ratios = {}
    legal_flags = {}
    label_cache = {}

    for sensitive_col in valid_sensitive_cols:
        labels = _attribute_labels(work, sensitive_col)
        label_cache[sensitive_col] = labels
        attr_frame = pd.DataFrame({"label": labels, "target": work["_target_binary"]}).dropna(
            subset=["label", "target"]
        )

        group_rows = {}
        group_rates = []
        for label, subset in attr_frame.groupby("label", dropna=True):
            mask = (labels == label).fillna(False)
            source_subset = work.loc[mask]
            numeric_averages = {
                col: _round_or_none(source_subset[col].mean()) for col in numeric_feature_cols
            }
            approval_rate = _round_or_none(subset["target"].mean())
            if approval_rate is not None:
                group_rates.append(approval_rate)

            avg_score = None
            if numeric_feature_cols:
                avg_score = _round_or_none(source_subset[numeric_feature_cols].mean(axis=1).mean())

            group_rows[str(label)] = {
                "count": int(len(subset)),
                "approval_rate": approval_rate,
                "avg_score": avg_score,
                "numeric_averages": numeric_averages,
            }

        by_attribute[sensitive_col] = group_rows
        if group_rates and max(group_rates) > 0:
            ratio = round(float(min(group_rates) / max(group_rates)), 3)
            di_ratios[sensitive_col] = ratio
            legal_flags[sensitive_col] = "PASS" if ratio >= 0.8 else "FAIL"
        else:
            di_ratios[sensitive_col] = None
            legal_flags[sensitive_col] = "UNKNOWN"

    intersectional = {}
    if len(valid_sensitive_cols) >= 2:
        first, second = valid_sensitive_cols[:2]
        pair_frame = pd.DataFrame({
            "first": label_cache[first],
            "second": label_cache[second],
            "target": work["_target_binary"],
        }).dropna(subset=["first", "second", "target"])

        for (first_label, second_label), subset in pair_frame.groupby(["first", "second"]):
            if len(subset) < 5:
                continue
            key = f"{first_label} x {second_label}"
            intersectional[key] = {
                "count": int(len(subset)),
                "approval_rate": _round_or_none(subset["target"].mean()),
            }

    result = {
        "by_attribute": by_attribute,
        "intersectional": intersectional,
        "di_ratios": di_ratios,
        "legal_flags": legal_flags,
    }
    _state["dashboard_stats"] = result
    _state["dashboard_sensitive_cols"] = valid_sensitive_cols
    return result


def _selection_di(y: np.ndarray, A: np.ndarray) -> float:
    return float(demographic_parity_ratio(y, y, sensitive_features=A))


def _compute_reweighing_weights(y: np.ndarray, A: np.ndarray, power: float = 1.0) -> np.ndarray:
    y_series = pd.Series(y)
    a_series = pd.Series(A)
    n = len(y_series)
    weights = np.ones(n, dtype=float)
    for a in a_series.unique():
        for label in y_series.unique():
            mask = (a_series == a) & (y_series == label)
            joint = mask.mean()
            if joint == 0:
                continue
            expected = (a_series == a).mean() * (y_series == label).mean()
            weights[mask.to_numpy()] = (expected / joint) ** power
    return weights


def _apply_disparate_impact_remover(df: pd.DataFrame, repair_level: float) -> pd.DataFrame:
    try:
        from aif360.algorithms.preprocessing import DisparateImpactRemover
        from aif360.datasets import BinaryLabelDataset
    except Exception as exc:
        raise RuntimeError(
            "DisparateImpactRemover requires aif360. Install requirements or use remediation_method='reweighing'."
        ) from exc

    feature_cols = _state["feature_cols"]
    target_col = _state["target_col"]
    sensitive_col = _state["sensitive_col"]
    target_info = _state.get("target_info")

    work = df.dropna(subset=[target_col, sensitive_col]).copy()
    encoded = work[feature_cols + [sensitive_col]].copy()
    category_maps = {}
    for col in encoded.columns:
        if _is_categorical(encoded[col]):
            codes, uniques = pd.factorize(encoded[col].astype(str), sort=True)
            encoded[col] = codes.astype(float)
            category_maps[col] = list(uniques)
        else:
            encoded[col] = pd.to_numeric(encoded[col], errors="coerce")
    encoded = encoded.fillna(encoded.median(numeric_only=True))
    encoded[target_col] = transform_target(work[target_col], target_info)

    dataset = BinaryLabelDataset(
        favorable_label=1,
        unfavorable_label=0,
        df=encoded[feature_cols + [sensitive_col, target_col]],
        label_names=[target_col],
        protected_attribute_names=[sensitive_col],
    )
    repaired = DisparateImpactRemover(repair_level=repair_level).fit_transform(dataset)
    repaired_df, _ = repaired.convert_to_dataframe()

    export_df = work.copy()
    for col in feature_cols:
        export_df[col] = repaired_df[col].to_numpy()
    return export_df


def build_remediated_dataset(
    df: pd.DataFrame | None = None,
    remediation_method: RemediationMethod = "reweighing",
    repair_level: float = 1.0,
    weight_power: float = 1.0,
) -> pd.DataFrame:
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet.")

    raw_df = df.copy() if df is not None else _state.get("raw_df")
    if raw_df is None:
        raise RuntimeError("Raw uploaded data is not available in memory for CSV export.")
    raw_df = raw_df.copy()

    target_col = _state["target_col"]
    sensitive_col = _state["sensitive_col"]
    required = [target_col, sensitive_col] + list(_state["feature_cols"] or [])
    missing = [col for col in required if col not in raw_df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns for remediation: {missing}")

    valid_df = raw_df.dropna(subset=[target_col, sensitive_col]).copy()
    if valid_df.empty:
        raise RuntimeError("No rows with target and sensitive values are available for CSV export.")

    y = transform_target(valid_df[target_col], _state.get("target_info"))
    A, _ = transform_sensitive(valid_df[sensitive_col], _state.get("sensitive_info"))

    if remediation_method == "disparate_impact_remover":
        export_df = _apply_disparate_impact_remover(valid_df, repair_level=repair_level)
    elif remediation_method == "reweighing":
        export_df = valid_df.copy()
        export_df["instance_weight"] = _compute_reweighing_weights(y, A, power=weight_power)
    else:
        raise ValueError(f"Unsupported remediation_method '{remediation_method}'.")

    export_df.attrs["original_di_ratio"] = _selection_di(y, A)
    return export_df


def verify_remediated_dataset(df: pd.DataFrame) -> dict:
    feature_cols = [col for col in (_state["feature_cols"] or []) if col in df.columns]
    target_col = _state["target_col"]
    sensitive_col = _state["sensitive_col"]
    if not feature_cols:
        raise ValueError("No feature columns remain for verification.")

    work = df.dropna(subset=[target_col, sensitive_col]).copy()
    y = transform_target(work[target_col], _state.get("target_info"))
    A, A_raw = transform_sensitive(work[sensitive_col], _state.get("sensitive_info"))
    X = work[feature_cols].copy()
    sample_weight = None
    if "instance_weight" in work.columns:
        sample_weight = pd.to_numeric(work["instance_weight"], errors="coerce").fillna(1.0).to_numpy()

    stratify = _joint_stratify(y, A)
    split = train_test_split(
        X,
        y,
        A,
        A_raw,
        sample_weight if sample_weight is not None else np.ones(len(y)),
        test_size=0.3,
        random_state=42,
        stratify=stratify,
    )
    X_train, X_test, y_train, y_test, A_train, A_test, Araw_train, Araw_test, w_train, w_test = split

    verifier = Pipeline(
        steps=[
            ("preprocessor", _make_preprocessor(X_train, feature_cols)),
            ("classifier", LogisticRegression(max_iter=1000, random_state=42)),
        ]
    )
    fit_kwargs = {}
    if sample_weight is not None:
        fit_kwargs["classifier__sample_weight"] = w_train
    verifier.fit(X_train, y_train, **fit_kwargs)
    y_pred = verifier.predict(X_test)
    metrics = _compute_metrics("Verified retrain", y_test, y_pred, A_test, Araw_test, _state["sensitive_groups"])
    return {
        "metrics": metrics,
        "verified_di_ratio_after_retraining": metrics["disparate_impact_ratio"],
    }


def remediate_with_reaudit(
    df: pd.DataFrame | None = None,
    remediation_method: RemediationMethod = "reweighing",
    repair_level: float = 1.0,
    max_attempts: int = 3,
) -> RemediationResult:
    best_df = None
    best_verified = -1.0
    best_metrics = None
    best_power = 1.0
    attempts = 0

    for attempt in range(1, max_attempts + 1):
        attempts = attempt
        if remediation_method == "reweighing":
            weight_power = float(attempt)
            current_repair_level = repair_level
        else:
            weight_power = 1.0
            current_repair_level = min(1.0, repair_level + 0.25 * (attempt - 1))

        candidate = build_remediated_dataset(
            df,
            remediation_method=remediation_method,
            repair_level=current_repair_level,
            weight_power=weight_power,
        )
        verification = verify_remediated_dataset(candidate)
        verified_di = float(verification["verified_di_ratio_after_retraining"])
        if verified_di > best_verified:
            best_df = candidate
            best_verified = verified_di
            best_metrics = verification["metrics"]
            best_power = weight_power
            repair_level = current_repair_level
        if verified_di >= 0.8:
            break

    if best_df is None or best_metrics is None:
        raise RuntimeError("Could not produce a remediated dataset.")

    return RemediationResult(
        dataframe=best_df,
        method=remediation_method,
        repair_level=repair_level,
        weight_power=best_power,
        original_di_ratio=float(best_df.attrs.get("original_di_ratio", np.nan)),
        verified_di_ratio_after_retraining=best_verified,
        verified_metrics=best_metrics,
        attempts=attempts,
    )


def get_debiased_predictions() -> pd.DataFrame:
    """Backward-compatible export helper. Returns remediated data, not relabeled targets."""
    return build_remediated_dataset(remediation_method="reweighing")
