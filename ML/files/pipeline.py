"""
pipeline.py — your colab logic, refactored into functions
No hardcoded paths. No print(). Returns dicts everywhere.
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

# ── module-level state (lives in memory while server runs) ──────────────
# These get populated once when /upload is called
_state = {
    "baseline":          None,
    "reweighted_model":  None,
    "threshold_model":   None,
    "X_test":            None,
    "y_test":            None,
    "A_test":            None,
    "feature_cols":      None,
    "scaler":            None,
    "label_encoders":    {},
    "trained":           False,
}

FEATURE_COLS = [
    "years_experience", "gpa", "technical_score", "interview_score",
    "online_assessment", "communication", "num_prev_jobs",
    "has_certification", "referral", "cover_letter_len",
]

# ── 1. LOAD + PREPROCESS ────────────────────────────────────────────────

def load_and_preprocess(df: pd.DataFrame):
    """
    Accepts a DataFrame (from uploaded CSV).
    Returns X, y, sensitive arrays + fitted encoders.
    Exactly your colab Step 2 — but returns objects instead of setting globals.
    """
    df = df.copy()

    # Drop rows with nulls in key columns
    df.dropna(subset=FEATURE_COLS + ["hired", "gender"], inplace=True)

    # Encode any remaining object columns (education_level, ethnicity etc.)
    label_encoders = {}
    cat_cols = df.select_dtypes("object").columns.tolist()
    for col in ["applicant_id", "gender", "hired"]:
        if col in cat_cols:
            cat_cols.remove(col)

    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col].astype(str))
        label_encoders[col] = le

    # Binary sensitive attribute: 1=Male, 0=Female/Non-binary/other
    df["gender_binary"] = (df["gender"].str.strip() == "Male").astype(int)

    X = df[FEATURE_COLS].values.astype(float)
    y = df["hired"].values.astype(int)
    sensitive = df["gender_binary"].values

    # Scale features (needed for KNN and improves LR too)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    return X_scaled, y, sensitive, scaler, label_encoders


# ── 2. TRAIN ALL THREE MODELS ───────────────────────────────────────────

def train_pipeline(df: pd.DataFrame):
    """
    Your colab Steps 3–5 wrapped in one function.
    Trains baseline, reweighted, threshold models.
    Stores everything in _state so routes can use them.
    Returns a summary dict immediately.
    """
    X, y, sensitive, scaler, label_encoders = load_and_preprocess(df)

    X_train, X_test, y_train, y_test, A_train, A_test = train_test_split(
        X, y, sensitive, test_size=0.3, random_state=42, stratify=y
    )

    # ── Baseline (your Step 3) ──────────────────────────────────────────
    baseline = LogisticRegression(max_iter=1000, random_state=42)
    baseline.fit(X_train, y_train)

    # ── Reweighting via ExponentiatedGradient (your Step 4) ────────────
    base_estimator = LogisticRegression(max_iter=1000, solver="liblinear", random_state=42)
    reweighted_model = ExponentiatedGradient(
        estimator=base_estimator,
        constraints=DemographicParity(difference_bound=0.05),
        eps=0.05,
    )
    reweighted_model.fit(X_train, y_train, sensitive_features=A_train)

    # ── ThresholdOptimizer (your Step 5) ───────────────────────────────
    threshold_model = ThresholdOptimizer(
        estimator=baseline,
        constraints="demographic_parity",
        objective="balanced_accuracy_score",
        predict_method="predict_proba",
    )
    threshold_model.fit(X_train, y_train, sensitive_features=A_train)

    # Store in module state
    _state.update({
        "baseline":         baseline,
        "reweighted_model": reweighted_model,
        "threshold_model":  threshold_model,
        "X_test":           X_test,
        "y_test":           y_test,
        "A_test":           A_test,
        "feature_cols":     FEATURE_COLS,
        "scaler":           scaler,
        "label_encoders":   label_encoders,
        "trained":          True,
    })

    return get_summary()  # immediately return metrics after training


# ── 3. METRICS HELPER ───────────────────────────────────────────────────

def _compute_metrics(label: str, y_true, y_pred, A) -> dict:
    """
    Your colab print_metrics() — but returns a dict instead of printing.
    This dict goes straight into the JSON response.
    """
    acc = accuracy_score(y_true, y_pred)
    dpd = demographic_parity_difference(y_true, y_pred, sensitive_features=A)
    dpr = demographic_parity_ratio(y_true, y_pred, sensitive_features=A)
    eod = equalized_odds_difference(y_true, y_pred, sensitive_features=A)

    mf = MetricFrame(
        metrics={"approval_rate": lambda yt, yp: yp.mean()},
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=A,
    )
    female_rate = float(mf.by_group["approval_rate"].iloc[0])
    male_rate   = float(mf.by_group["approval_rate"].iloc[1])

    return {
        "model":                label,
        "accuracy":             round(float(acc), 3),
        "female_approval_rate": round(female_rate, 3),
        "male_approval_rate":   round(male_rate, 3),
        "disparate_impact_ratio": round(float(dpr), 3),
        "demographic_parity_difference": round(float(dpd), 3),
        "equalized_odds_difference": round(float(eod), 3),
        "legal_pass":           bool(dpr >= 0.8),   # EEOC 80% rule
    }


# ── 4. GET AUDIT REPORT ─────────────────────────────────────────────────

def get_audit() -> dict:
    """Called by GET /audit. Returns metrics for all 3 models."""
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet. Call POST /upload first.")

    X_test = _state["X_test"]
    y_test = _state["y_test"]
    A_test = _state["A_test"]

    y_pred_baseline   = _state["baseline"].predict(X_test)
    y_pred_reweighted = _state["reweighted_model"].predict(X_test)
    y_pred_threshold  = _state["threshold_model"].predict(
        X_test, sensitive_features=A_test
    )

    return {
        "results": [
            _compute_metrics("Baseline (biased)",        y_test, y_pred_baseline,   A_test),
            _compute_metrics("Reweighting (Stage 1)",    y_test, y_pred_reweighted,  A_test),
            _compute_metrics("Threshold cal. (Stage 3)", y_test, y_pred_threshold,   A_test),
        ]
    }


# ── 5. SUMMARY TABLE ────────────────────────────────────────────────────

def get_summary() -> dict:
    """Your colab Step 6 summary table — as JSON."""
    return get_audit()   # same data, summary is just the audit results


# ── 6. SINGLE APPLICANT PREDICTION ──────────────────────────────────────

def predict_applicant(applicant: dict, gender: str) -> dict:
    """
    New — not in your colab.
    Takes one applicant's features + gender, runs all 3 models,
    returns all 3 decisions so you can show the difference.

    applicant: dict with keys matching FEATURE_COLS
    gender:    "Male" | "Female" | "Non-binary"
    """
    if not _state["trained"]:
        raise RuntimeError("No dataset uploaded yet. Call POST /upload first.")

    scaler = _state["scaler"]
    x_raw  = np.array([[applicant[col] for col in FEATURE_COLS]], dtype=float)
    x_scaled = scaler.transform(x_raw)

    sensitive_val = np.array([1 if gender == "Male" else 0])

    baseline_pred   = int(_state["baseline"].predict(x_scaled)[0])
    baseline_prob   = round(float(_state["baseline"].predict_proba(x_scaled)[0][1]), 3)

    reweighted_pred = int(_state["reweighted_model"].predict(x_scaled)[0])

    threshold_pred  = int(_state["threshold_model"].predict(
        x_scaled, sensitive_features=sensitive_val
    )[0])

    return {
        "applicant":        applicant,
        "gender":           gender,
        "baseline":         {"decision": baseline_pred, "probability": baseline_prob,
                             "label": "HIRED" if baseline_pred else "REJECTED"},
        "reweighted":       {"decision": reweighted_pred,
                             "label": "HIRED" if reweighted_pred else "REJECTED"},
        "threshold_calibrated": {"decision": threshold_pred,
                                  "label": "HIRED" if threshold_pred else "REJECTED"},
        "bias_detected":    baseline_pred != reweighted_pred or baseline_pred != threshold_pred,
        "note": "If decisions differ across models, the baseline was likely biased for this applicant."
    }
