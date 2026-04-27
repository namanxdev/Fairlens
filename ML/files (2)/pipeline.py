"""
pipeline.py — fully generic fairness pipeline
Works for any CSV with any column names.
User only needs to specify: target_col + sensitive_col.
Everything else is auto-detected.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score
from fairlearn.reductions import ExponentiatedGradient, DemographicParity
from fairlearn.postprocessing import ThresholdOptimizer
from fairlearn.metrics import (
    MetricFrame,
    demographic_parity_difference,
    demographic_parity_ratio,
    equalized_odds_difference,
)

# ── module-level state ───────────────────────────────────────────────────
_state = {
    "baseline":          None,
    "reweighted_model":  None,
    "threshold_model":   None,
    "X_test":            None,
    "y_test":            None,
    "A_test":            None,
    "A_test_raw":        None,   # original string labels (e.g. "Female", "Male")
    "feature_cols":      None,
    "target_col":        None,
    "sensitive_col":     None,
    "sensitive_groups":  None,   # unique values in sensitive col
    "sensitive_encoder": None,   # LabelEncoder for sensitive col
    "scaler":            None,
    "label_encoders":    {},
    "trained":           False,
    "domain":            None,   # "jobs" / "banking" / "custom" — just a label
    "raw_df":            None,   # in-memory only; never persisted with models
    "dashboard_stats":   None,
    "dashboard_sensitive_cols": None,
    "audit_id":          None,
    "audit_result":      None,
    "dataset_name":      None,
    "user_id":           None,
}


# ── STEP 1: AUTO-DETECT COLUMNS ─────────────────────────────────────────

def detect_columns(df: pd.DataFrame, target_col: str, sensitive_col: str) -> list:
    """
    Given a DataFrame and the two special columns (target + sensitive),
    returns everything else as feature columns — automatically.

    Skips:
      - target_col (what we're predicting)
      - sensitive_col (protected attribute — never a model feature)
      - id-like columns (all unique strings, or column name contains "id")
      - columns with >50% nulls
    """
    exclude = {target_col, sensitive_col}

    feature_cols = []
    for col in df.columns:
        if col in exclude:
            continue
        # Skip obvious ID columns
        id_hints = ["id", "name", "ref", "code", "num", "index", "uuid", "key"]
        if any(h in col.lower() for h in id_hints) and df[col].nunique() > 0.9 * len(df):
            continue
        # Skip columns with >50% missing
        if df[col].isnull().mean() > 0.5:
            continue
        # Skip columns that are all unique (likely free-text / IDs)
        if df[col].dtype == object and df[col].nunique() == len(df):
            continue
        feature_cols.append(col)

    return feature_cols


# ── STEP 2: ENCODE SENSITIVE COLUMN (any type) ───────────────────────────

def encode_sensitive(series: pd.Series):
    """
    Handles any sensitive column type:
      - String/categorical (gender, ethnicity) → LabelEncoder → integers
      - Numeric continuous (age) → binned into groups (e.g. 22-35, 36-50, 51+)
    
    Returns:
      encoded  : numpy int array
      encoder  : the LabelEncoder (or None if binned)
      groups   : list of unique group labels (strings, for reporting)
      raw      : original string labels per row
    """
    if series.dtype == object or series.dtype.name in ("category", "string") or pd.api.types.is_string_dtype(series):
        # Categorical: just label-encode
        le = LabelEncoder()
        encoded = le.fit_transform(series.astype(str).str.strip())
        groups  = list(le.classes_)
        raw     = series.astype(str).str.strip().values
        return encoded, le, groups, raw

    else:
        # Numeric (e.g. age): bin into meaningful groups
        # Use quartiles so it works for any numeric range
        labels = ["Group_Q1", "Group_Q2", "Group_Q3", "Group_Q4"]
        binned = pd.qcut(series, q=4, labels=labels, duplicates="drop")
        le = LabelEncoder()
        encoded = le.fit_transform(binned.astype(str))
        groups  = list(le.classes_)
        raw     = binned.astype(str).values
        return encoded, le, groups, raw


# ── STEP 3: PREPROCESS (generic) ────────────────────────────────────────

def load_and_preprocess(df: pd.DataFrame, target_col: str,
                        sensitive_col: str, feature_cols: list):
    """
    Generic preprocessing — works for any dataset.
    Encodes categoricals, scales features, encodes sensitive col.
    """
    df = df.copy()
    df.dropna(subset=[target_col, sensitive_col] + feature_cols, inplace=True)

    # Encode non-numeric feature columns
    label_encoders = {}
    for col in feature_cols:
        if df[col].dtype == object or pd.api.types.is_string_dtype(df[col]):
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            label_encoders[col] = le

    # Encode target (must be 0/1)
    if df[target_col].dtype == object:
        # Try to detect positive label (yes/true/1/approved/hired etc.)
        pos_keywords = ["yes", "true", "1", "approved", "hired",
                        "accept", "positive", "readmit"]
        unique_vals = df[target_col].str.lower().str.strip().unique()
        pos_label = next(
            (v for v in unique_vals if any(k in v for k in pos_keywords)),
            unique_vals[0]   # fallback: first value = positive
        )
        df[target_col] = (df[target_col].str.lower().str.strip() == pos_label).astype(int)

    # Encode sensitive column
    sensitive_encoded, sensitive_encoder, groups, raw = encode_sensitive(df[sensitive_col])

    X = df[feature_cols].values.astype(float)
    y = df[target_col].values.astype(int)

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, sensitive_encoded, raw, scaler, label_encoders, sensitive_encoder, groups


# ── STEP 4: TRAIN ALL THREE MODELS ──────────────────────────────────────

def train_pipeline(df: pd.DataFrame, target_col: str,
                   sensitive_col: str, domain: str = "custom") -> dict:
    """
    Main entry point called by POST /upload.
    Accepts any CSV + column names → trains 3 models → returns audit.
    """
    # Auto-detect features
    feature_cols = detect_columns(df, target_col, sensitive_col)
    if len(feature_cols) == 0:
        raise ValueError("No usable feature columns detected in this CSV.")

    (X, y, A, A_raw,
     scaler, label_encoders,
     sensitive_encoder, groups) = load_and_preprocess(df, target_col, sensitive_col, feature_cols)

    X_train, X_test, y_train, y_test, A_train, A_test, Araw_train, Araw_test = train_test_split(
        X, y, A, A_raw, test_size=0.3, random_state=42, stratify=y
    )

    # Baseline
    baseline = LogisticRegression(max_iter=1000, random_state=42)
    baseline.fit(X_train, y_train)

    # Reweighting — ExponentiatedGradient
    base_estimator = LogisticRegression(max_iter=1000, solver="liblinear", random_state=42)
    reweighted_model = ExponentiatedGradient(
        estimator=base_estimator,
        constraints=DemographicParity(difference_bound=0.05),
        eps=0.05,
    )
    reweighted_model.fit(X_train, y_train, sensitive_features=A_train)

    # Threshold calibration — ThresholdOptimizer
    threshold_model = ThresholdOptimizer(
        estimator=baseline,
        constraints="demographic_parity",
        objective="balanced_accuracy_score",
        predict_method="predict_proba",
    )
    threshold_model.fit(X_train, y_train, sensitive_features=A_train)

    # Save state
    _state.update({
        "baseline":          baseline,
        "reweighted_model":  reweighted_model,
        "threshold_model":   threshold_model,
        "X_test":            X_test,
        "y_test":            y_test,
        "A_test":            A_test,
        "A_test_raw":        Araw_test,
        "feature_cols":      feature_cols,
        "target_col":        target_col,
        "sensitive_col":     sensitive_col,
        "sensitive_groups":  groups,
        "sensitive_encoder": sensitive_encoder,
        "scaler":            scaler,
        "label_encoders":    label_encoders,
        "trained":           True,
        "domain":            domain,
        "raw_df":            df.copy(),
        "dashboard_stats":   None,
        "dashboard_sensitive_cols": None,
    })

    audit = get_audit()
    _state["audit_result"] = audit
    return audit


# ── METRICS ─────────────────────────────────────────────────────────────

def _compute_metrics(label: str, y_true, y_pred, A, A_raw, groups) -> dict:
    """
    Returns per-group approval rates + fairness metrics as a dict.
    Works for any number of groups (not just Male/Female).
    """
    acc = float(accuracy_score(y_true, y_pred))
    dpd = float(demographic_parity_difference(y_true, y_pred, sensitive_features=A))
    dpr = float(demographic_parity_ratio(y_true, y_pred, sensitive_features=A))
    eod = float(equalized_odds_difference(y_true, y_pred, sensitive_features=A))

    # Per-group approval rates — works for any number of groups
    mf = MetricFrame(
        metrics={"approval_rate": lambda yt, yp: float(yp.mean())},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=A_raw,   # use raw labels for readable group names
    )
    group_rates = {
        str(grp): round(float(rate), 3)
        for grp, rate in mf.by_group["approval_rate"].items()
    }

    return {
        "model":                         label,
        "accuracy":                      round(acc, 3),
        "group_approval_rates":          group_rates,   # e.g. {"Female": 0.17, "Male": 0.53}
        "disparate_impact_ratio":        round(dpr, 3),
        "demographic_parity_difference": round(dpd, 3),
        "equalized_odds_difference":     round(eod, 3),
        "legal_pass":                    bool(dpr >= 0.8),
        "legal_threshold":               "EEOC 80% rule: DI ratio >= 0.80",
    }


# ── AUDIT ────────────────────────────────────────────────────────────────

def get_audit() -> dict:
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet. Call POST /upload first.")

    if _state.get("X_test") is None:
        cached_audit = _state.get("audit_result")
        if cached_audit:
            return cached_audit
        raise RuntimeError("Audit metrics are not available for the loaded model state.")

    X_test  = _state["X_test"]
    y_test  = _state["y_test"]
    A_test  = _state["A_test"]
    A_raw   = _state["A_test_raw"]
    groups  = _state["sensitive_groups"]

    y_pred_baseline   = _state["baseline"].predict(X_test)
    y_pred_reweighted = _state["reweighted_model"].predict(X_test)
    y_pred_threshold  = _state["threshold_model"].predict(X_test, sensitive_features=A_test)

    return {
        "domain":        _state["domain"],
        "target_col":    _state["target_col"],
        "sensitive_col": _state["sensitive_col"],
        "groups_found":  groups,
        "feature_cols":  _state["feature_cols"],
        "results": [
            _compute_metrics("Baseline (biased)",        y_test, y_pred_baseline,   A_test, A_raw, groups),
            _compute_metrics("Reweighting (Stage 1)",    y_test, y_pred_reweighted,  A_test, A_raw, groups),
            _compute_metrics("Threshold cal. (Stage 3)", y_test, y_pred_threshold,   A_test, A_raw, groups),
        ]
    }


# ── SINGLE PREDICTION ────────────────────────────────────────────────────

def predict_applicant(features: dict, sensitive_value: str) -> dict:
    """
    features       : dict of {col_name: value} — any domain's feature set
    sensitive_value: raw string value of sensitive col (e.g. "Female", "Asian", "Group_Q2")
    """
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet.")

    feature_cols = _state["feature_cols"]
    scaler       = _state["scaler"]
    le_map       = _state["label_encoders"]
    sens_enc     = _state["sensitive_encoder"]

    # Build feature vector in correct column order
    x_raw = []
    for col in feature_cols:
        val = features.get(col)
        if val is None:
            raise ValueError(f"Missing feature: '{col}'")
        # Encode string features
        if col in le_map:
            val = int(le_map[col].transform([str(val)])[0])
        x_raw.append(float(val))

    x_scaled = scaler.transform([x_raw])

    # Encode sensitive value
    try:
        A_val = int(sens_enc.transform([sensitive_value])[0])
    except Exception:
        A_val = 0   # fallback if unseen group

    A_arr = np.array([A_val])

    baseline_pred   = int(_state["baseline"].predict(x_scaled)[0])
    baseline_prob   = round(float(_state["baseline"].predict_proba(x_scaled)[0][1]), 3)
    reweighted_pred = int(_state["reweighted_model"].predict(x_scaled)[0])
    threshold_pred  = int(_state["threshold_model"].predict(x_scaled, sensitive_features=A_arr)[0])

    target = _state["target_col"]
    pos_label = "APPROVED" if any(k in target.lower() for k in
                                  ["loan","approv","hire","hired","admit","scholar"]) else "POSITIVE"
    neg_label = "REJECTED" if pos_label == "APPROVED" else ("NOT HIRED" if "hire" in target.lower() else "NEGATIVE")

    return {
        "sensitive_col":   _state["sensitive_col"],
        "sensitive_value": sensitive_value,
        "target_col":      target,
        "baseline":             {"decision": baseline_pred, "probability": baseline_prob,
                                 "label": pos_label if baseline_pred else neg_label},
        "reweighted":           {"decision": reweighted_pred,
                                 "label": pos_label if reweighted_pred else neg_label},
        "threshold_calibrated": {"decision": threshold_pred,
                                 "label": pos_label if threshold_pred else neg_label},
        "bias_detected": baseline_pred != reweighted_pred or baseline_pred != threshold_pred,
        "note": "bias_detected=True means the baseline treated this person differently due to bias."
    }


# ── SCHEMA (for dynamic frontend forms) ─────────────────────────────────

def get_schema() -> dict:
    """
    Returns detected column info so the frontend can build its form dynamically.
    No hardcoding needed on the frontend side.
    """
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet.")
    return {
        "feature_cols":   _state["feature_cols"],
        "target_col":     _state["target_col"],
        "sensitive_col":  _state["sensitive_col"],
        "sensitive_groups": _state["sensitive_groups"],
        "domain":         _state["domain"],
    }


# ── DASHBOARD STATS ─────────────────────────────────────────────────────

def _coerce_target_to_binary(series: pd.Series) -> pd.Series:
    """Convert common target encodings to numeric 0/1 values."""
    if pd.api.types.is_bool_dtype(series):
        return series.astype(int)

    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce")
        unique = sorted(v for v in numeric.dropna().unique())
        if len(unique) <= 2:
            return numeric.astype(float)
        return (numeric > 0).astype(float)

    text = series.astype(str).str.lower().str.strip()
    pos_keywords = [
        "yes", "true", "1", "approved", "approve", "hired",
        "hire", "accept", "accepted", "positive", "readmit",
        "pass", "selected",
    ]
    unique_vals = [v for v in text.dropna().unique() if v and v != "nan"]
    pos_label = next(
        (v for v in unique_vals if any(k in v for k in pos_keywords)),
        unique_vals[0] if unique_vals else "1",
    )
    return (text == pos_label).astype(float)


def _attribute_labels(df: pd.DataFrame, sensitive_col: str) -> pd.Series:
    """Return dashboard-friendly labels, including fixed bins for age columns."""
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


def compute_group_stats(df: pd.DataFrame, target_col: str,
                        sensitive_cols: list, use_debiased: bool = False) -> dict:
    """
    Computes per-attribute and intersectional dashboard stats.

    Returns:
    {
      "by_attribute": {"gender": {"Female": {"count": 10, "approval_rate": 0.2}}},
      "intersectional": {"Female × 22-30": {"count": 8, "approval_rate": 0.125}},
      "di_ratios": {"gender": 0.5},
      "legal_flags": {"gender": "FAIL"}
    }
    """
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
            scaler = _state["scaler"]
            le_map = _state["label_encoders"] or {}

            model_input = work[feature_cols].copy()
            valid_mask = model_input.notna().all(axis=1)
            for col, enc in le_map.items():
                if col in model_input.columns:
                    valid_mask &= model_input[col].astype(str).isin(enc.classes_)

            if valid_mask.any():
                encoded_input = model_input.loc[valid_mask].copy()
                for col, enc in le_map.items():
                    if col in encoded_input.columns:
                        encoded_input[col] = enc.transform(encoded_input[col].astype(str))

                X_all = scaler.transform(encoded_input.values.astype(float))
                target_binary = pd.Series(np.nan, index=work.index, dtype=float)
                
                if use_debiased and _state.get("threshold_model") is not None:
                    # Need sensitive features for threshold_model
                    sensitive_col = _state["sensitive_col"]
                    A_all, _, _, _ = encode_sensitive(work.loc[valid_mask, sensitive_col])
                    target_binary.loc[valid_mask] = _state["threshold_model"].predict(X_all, sensitive_features=A_all).astype(float)
                else:
                    target_binary.loc[valid_mask] = _state["baseline"].predict(X_all).astype(float)
        except Exception:
            target_binary = None

    if target_binary is None:
        target_binary = _coerce_target_to_binary(work[target_col])
    work["_target_binary"] = target_binary
    valid_sensitive_cols = [col for col in sensitive_cols if col in work.columns]

    numeric_feature_cols = [
        col for col in work.select_dtypes(include=[np.number]).columns
        if col not in set(valid_sensitive_cols + [target_col])
        and not col.startswith("_")
    ]

    by_attribute = {}
    di_ratios = {}
    legal_flags = {}
    label_cache = {}

    for sensitive_col in valid_sensitive_cols:
        labels = _attribute_labels(work, sensitive_col)
        label_cache[sensitive_col] = labels
        attr_frame = pd.DataFrame({
            "label": labels,
            "target": work["_target_binary"],
        })
        attr_frame = attr_frame.dropna(subset=["label", "target"])

        group_rows = {}
        group_rates = []
        for label, subset in attr_frame.groupby("label", dropna=True):
            mask = (labels == label).fillna(False)
            source_subset = work.loc[mask]
            numeric_averages = {
                col: _round_or_none(source_subset[col].mean())
                for col in numeric_feature_cols
            }
            approval_rate = _round_or_none(subset["target"].mean())
            if approval_rate is not None:
                group_rates.append(approval_rate)

            avg_score = None
            if numeric_feature_cols:
                avg_score = _round_or_none(
                    source_subset[numeric_feature_cols].mean(axis=1).mean()
                )

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
            key = f"{first_label} × {second_label}"
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


def get_debiased_predictions() -> pd.DataFrame:
    """
    Build an exportable DataFrame with baseline and threshold-calibrated decisions.
    Raw rows stay in memory only and are not saved to the audit database.
    """
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet.")
    if _state.get("raw_df") is None:
        raise RuntimeError("Raw uploaded data is not available in memory for CSV export.")

    feature_cols = _state["feature_cols"]
    sensitive_col = _state["sensitive_col"]
    target_col = _state["target_col"]
    raw_df = _state["raw_df"].copy()
    required_cols = feature_cols + [sensitive_col]
    if target_col in raw_df.columns:
        required_cols.append(target_col)
    valid_df = raw_df.dropna(subset=required_cols).copy()
    if valid_df.empty:
        raise RuntimeError("No complete rows are available for CSV export.")

    model_input = valid_df[feature_cols].copy()
    for col, encoder in _state["label_encoders"].items():
        if col in model_input.columns:
            model_input[col] = encoder.transform(model_input[col].astype(str))

    X = model_input.values.astype(float)
    X_scaled = _state["scaler"].transform(X)
    A, _, _, _ = encode_sensitive(valid_df[sensitive_col])

    baseline_pred = _state["baseline"].predict(X_scaled).astype(int)
    debiased_pred = _state["threshold_model"].predict(
        X_scaled,
        sensitive_features=A,
    ).astype(int)

    export_df = valid_df[feature_cols].copy()
    export_df["baseline_decision"] = baseline_pred
    export_df["debiased_decision"] = debiased_pred
    export_df["bias_detected"] = baseline_pred != debiased_pred
    return export_df
