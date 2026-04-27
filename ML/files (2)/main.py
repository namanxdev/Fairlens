"""
main.py — generic FastAPI app
Works for jobs, banking, healthcare, education — any CSV.
User only needs to tell us: target_col + sensitive_col.
"""

import io
import json
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from pipeline import (
    train_pipeline, get_audit, get_schema,
    predict_applicant, compute_group_stats,
    get_debiased_predictions, _state
)
from database import (
    DatabaseOperationError,
    create_audit,
    delete_audit,
    list_audits,
    load_audit,
    load_models_into_state,
    save_audit_results,
    save_models,
    set_audit_status,
)
from llm_context import build_audit_context, build_compare_prompt
from schemas import CompareRequest, DashboardStatsRequest

app = FastAPI(
    title="AI Fairness Auditor — Universal",
    description="""
Upload ANY dataset (jobs, loans, healthcare, education).
Just tell us which column is the target and which is the sensitive attribute.
We handle everything else automatically.
    """,
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Remediation-Summary", "Content-Disposition"],
)

UPLOAD_DIR = Path(__file__).with_name("uploaded_datasets")
UPLOAD_DIR.mkdir(exist_ok=True)


def _uploaded_dataset_path(audit_id: str) -> Path:
    return UPLOAD_DIR / f"{audit_id}.csv"


def _user_id_from_headers(
    authorization: str | None = None,
    x_user_id: str | None = None,
) -> str:
    if x_user_id:
        return x_user_id.strip() or "anonymous"
    if authorization:
        token = authorization.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        return token or "anonymous"
    return "anonymous"


def _db_http_error(exc: DatabaseOperationError) -> HTTPException:
    message = str(exc)
    status_code = 404 if "not found" in message.lower() else 500
    return HTTPException(status_code=status_code, detail=message)


def _load_owned_audit(audit_id: str, user_id: str) -> dict:
    try:
        audit_data = load_audit(audit_id)
    except DatabaseOperationError as exc:
        raise _db_http_error(exc)

    if audit_data.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Audit not found for this user.")
    return audit_data


def _current_audit_result() -> dict:
    if _state.get("audit_result"):
        return _state["audit_result"]
    return get_audit()


def _current_dashboard_stats() -> dict:
    stats = _state.get("dashboard_stats")
    if stats:
        return stats
    if _state.get("raw_df") is None:
        return {}
    sensitive_cols = _state.get("dashboard_sensitive_cols") or [_state.get("sensitive_col")]
    sensitive_cols = [col for col in sensitive_cols if col]
    if not sensitive_cols:
        return {}
    return compute_group_stats(_state["raw_df"], _state["target_col"], sensitive_cols)


def _recommendations(audit_result: dict, dashboard_stats: dict) -> list[str]:
    recommendations = []
    for result in audit_result.get("results", []):
        if not result.get("legal_pass"):
            recommendations.append(
                f"Review {result.get('model')} because its DI ratio is "
                f"{result.get('disparate_impact_ratio')}."
            )
    for attribute, flag in (dashboard_stats.get("legal_flags") or {}).items():
        if flag == "FAIL":
            recommendations.append(
                f"Investigate {attribute} because it fails the 80% rule in dashboard stats."
            )
    if not recommendations:
        recommendations.append("No immediate 80% rule failure was detected in the saved metrics.")
    return recommendations


def _candidate_features_and_sensitive(candidate: dict) -> tuple[dict, str]:
    candidate_copy = dict(candidate)
    sensitive_value = candidate_copy.pop("sensitive_value", None)
    sensitive_col = _state.get("sensitive_col")
    if sensitive_value is None and sensitive_col in candidate_copy:
        sensitive_value = candidate_copy.pop(sensitive_col)
    if sensitive_value is None:
        raise HTTPException(
            status_code=400,
            detail=f"Missing 'sensitive_value' or '{sensitive_col}' in candidate payload.",
        )
    return candidate_copy, str(sensitive_value)


# ── Health check ─────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status":  "running",
        "trained": _state["trained"],
        "domain":  _state.get("domain"),
        "message": "POST /upload with target_col + sensitive_col to begin"
    }


# ── POST /upload ──────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_dataset(
    file:          UploadFile = File(...),
    target_col:    str        = Form(...),   # e.g. "hired", "loan_approved", "readmitted"
    sensitive_col: str        = Form(...),   # e.g. "gender", "age", "ethnicity"
    domain:        str        = Form("custom"),  # just a label: "jobs"/"banking"/"healthcare"
    authorization: str | None = Header(None),
    x_user_id:     str | None = Header(None, alias="X-User-Id"),
):
    """
    Upload any CSV file.

    Required form fields:
    - **file**: the CSV
    - **target_col**: column name of what you're predicting (must be 0/1 or Yes/No)
    - **sensitive_col**: protected attribute column (gender, age, ethnicity, race, etc.)
    - **domain**: optional label — jobs / banking / healthcare / education / custom

    Returns full fairness audit immediately after training.
    """
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted.")

    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    # Validate columns exist
    if target_col not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"target_col '{target_col}' not found. Available: {list(df.columns)}"
        )
    if sensitive_col not in df.columns:
        raise HTTPException(
            status_code=400,
            detail=f"sensitive_col '{sensitive_col}' not found. Available: {list(df.columns)}"
        )
    if len(df) < 50:
        raise HTTPException(status_code=400, detail="Dataset too small (need at least 50 rows).")

    user_id = _user_id_from_headers(authorization, x_user_id)
    try:
        audit_id = create_audit(user_id, domain, file.filename, target_col, sensitive_col)
    except DatabaseOperationError as e:
        raise _db_http_error(e)

    try:
        _uploaded_dataset_path(audit_id).write_bytes(contents)
    except OSError:
        pass

    try:
        result = train_pipeline(df, target_col, sensitive_col, domain)
    except Exception as e:
        try:
            set_audit_status(audit_id, "failed")
        except DatabaseOperationError:
            pass
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

    result = {
        **result,
        "audit_id": audit_id,
        "dataset_name": file.filename,
        "status": "complete",
    }
    _state.update({
        "audit_id": audit_id,
        "dataset_name": file.filename,
        "user_id": user_id,
        "audit_result": result,
    })

    # Auto-compute dashboard stats for likely protected attributes on upload.
    try:
        sensitive_cols_to_use = [sensitive_col]
        for extra in ["age", "ethnicity", "religion", "race", "caste"]:
            if extra in df.columns and extra != sensitive_col:
                sensitive_cols_to_use.append(extra)
        compute_group_stats(_state["raw_df"], target_col, sensitive_cols_to_use)
    except Exception:
        pass

    try:
        save_audit_results(audit_id, result["results"])
        save_models(audit_id, _state)
        set_audit_status(audit_id, "complete")
    except DatabaseOperationError as e:
        try:
            set_audit_status(audit_id, "failed")
        except DatabaseOperationError:
            pass
        raise _db_http_error(e)

    return result


# ── GET /audit ────────────────────────────────────────────────────────────
@app.get("/audit")
def audit():
    """
    Fairness metrics for all 3 models on the test set.
    Returns per-group approval rates for however many groups exist in your sensitive col.
    """
    if not _state["trained"]:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")
    return get_audit()


# ── GET /schema ───────────────────────────────────────────────────────────
@app.get("/schema")
def schema():
    """
    Returns the auto-detected column structure of the uploaded dataset.
    Frontend uses this to dynamically build the prediction form — no hardcoding needed.

    Example response:
    {
      "feature_cols": ["cibil_score", "income", "employment_years", ...],
      "target_col": "loan_approved",
      "sensitive_col": "gender",
      "sensitive_groups": ["Female", "Male"],
      "domain": "banking"
    }
    """
    if not _state["trained"]:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")
    return get_schema()


# ── POST /predict ─────────────────────────────────────────────────────────
@app.post("/predict")
def predict(body: dict):
    """
    Predict for a single applicant using all 3 models.

    Send a JSON body with:
    - All feature columns (get the list from GET /schema)
    - The sensitive column value (e.g. "Female", "Asian", "Group_Q2")

    Example for banking dataset:
    {
      "cibil_score": 720,
      "monthly_income": 62000,
      "loan_amount": 400000,
      "employment_years": 5,
      "existing_loans": 1,
      "has_property": 1,
      "age": 34,
      "sensitive_value": "Female"
    }

    Returns decision from all 3 models + whether bias was detected.
    """
    if not _state["trained"]:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")

    sensitive_value = body.pop("sensitive_value", None)
    if sensitive_value is None:
        raise HTTPException(
            status_code=400,
            detail="Missing 'sensitive_value' field. "
                   f"Should be one of: {_state['sensitive_groups']}"
        )

    try:
        result = predict_applicant(body, str(sensitive_value))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


# ── GET /status ───────────────────────────────────────────────────────────
@app.get("/status")
def status():
    return {
        "trained":       _state["trained"],
        "domain":        _state.get("domain"),
        "target_col":    _state.get("target_col"),
        "sensitive_col": _state.get("sensitive_col"),
        "groups":        _state.get("sensitive_groups"),
        "n_features":    len(_state["feature_cols"]) if _state["feature_cols"] else 0,
        "audit_id":      _state.get("audit_id"),
    }


# ── POST /dashboard-stats ────────────────────────────────────────────────
@app.post("/dashboard-stats")
def dashboard_stats(body: DashboardStatsRequest):
    """
    Compute dashboard-ready breakdowns across multiple sensitive attributes.

    Example input:
    {"sensitive_cols": ["gender", "age", "ethnicity"]}

    Example output:
    {"by_attribute": {"gender": {"Female": {"count": 12, "approval_rate": 0.25}}},
     "intersectional": {}, "di_ratios": {"gender": 0.5}, "legal_flags": {"gender": "FAIL"}}
    """
    if not _state["trained"] or _state.get("raw_df") is None:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")

    try:
        return compute_group_stats(_state["raw_df"], _state["target_col"], body.sensitive_cols)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── GET /llm-context ─────────────────────────────────────────────────────
@app.get("/llm-context")
def llm_context():
    """
    Return a plain-English audit context string for the frontend LLM layer.

    Example output:
    {"audit_id": "uuid", "context": "FAIRNESS AUDIT CONTEXT - Jobs Dataset..."}
    """
    if not _state["trained"]:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")

    try:
        audit_result = _current_audit_result()
        stats = _current_dashboard_stats()
        return {
            "audit_id": _state.get("audit_id"),
            "context": build_audit_context(audit_result, stats),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── POST /compare ────────────────────────────────────────────────────────
@app.post("/compare")
def compare(body: CompareRequest):
    """
    Compare two candidates using all models and return an LLM-ready prompt.

    Example input:
    {"candidate_a": {"gpa": 3.7, "sensitive_value": "Female"},
     "candidate_b": {"gpa": 3.8, "sensitive_value": "Male"}}

    Example output:
    {"candidate_a_scores": {"baseline": {...}}, "fairer_decision": {...},
     "bias_impact": {...}, "llm_prompt": "ready-to-send prompt"}
    """
    if not _state["trained"]:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")

    candidate_a_features, candidate_a_sensitive = _candidate_features_and_sensitive(body.candidate_a)
    candidate_b_features, candidate_b_sensitive = _candidate_features_and_sensitive(body.candidate_b)

    try:
        candidate_a_scores = predict_applicant(candidate_a_features, candidate_a_sensitive)
        candidate_b_scores = predict_applicant(candidate_b_features, candidate_b_sensitive)
        candidate_a_swapped = predict_applicant(candidate_a_features, candidate_b_sensitive)
        candidate_b_swapped = predict_applicant(candidate_b_features, candidate_a_sensitive)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    a_threshold = candidate_a_scores["threshold_calibrated"]["decision"]
    b_threshold = candidate_b_scores["threshold_calibrated"]["decision"]
    if a_threshold > b_threshold:
        recommended = "candidate_a"
    elif b_threshold > a_threshold:
        recommended = "candidate_b"
    else:
        recommended = "tie_or_needs_human_review"

    fairer_decision = {
        "model": "threshold_calibrated",
        "recommended_candidate": recommended,
        "candidate_a_decision": candidate_a_scores["threshold_calibrated"],
        "candidate_b_decision": candidate_b_scores["threshold_calibrated"],
    }
    bias_impact = {
        "candidate_a_baseline_changed_after_debiasing": (
            candidate_a_scores["baseline"]["decision"] != a_threshold
        ),
        "candidate_b_baseline_changed_after_debiasing": (
            candidate_b_scores["baseline"]["decision"] != b_threshold
        ),
        "candidate_a_threshold_changes_if_sensitive_value_swapped": (
            candidate_a_swapped["threshold_calibrated"]["decision"] != a_threshold
        ),
        "candidate_b_threshold_changes_if_sensitive_value_swapped": (
            candidate_b_swapped["threshold_calibrated"]["decision"] != b_threshold
        ),
    }

    audit_context = build_audit_context(_current_audit_result(), _current_dashboard_stats())
    llm_prompt = build_compare_prompt(
        audit_context,
        body.candidate_a,
        body.candidate_b,
        candidate_a_scores,
        candidate_b_scores,
        fairer_decision,
        bias_impact,
    )
    return {
        "candidate_a_scores": candidate_a_scores,
        "candidate_b_scores": candidate_b_scores,
        "fairer_decision": fairer_decision,
        "bias_impact": bias_impact,
        "llm_prompt": llm_prompt,
    }


# ── AUDIT HISTORY ROUTES ────────────────────────────────────────────────
@app.get("/audits")
def audits(
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    List persisted audits for the current user.

    Example output:
    [{"audit_id": "uuid", "dataset_name": "jobs.csv", "status": "complete"}]
    """
    user_id = _user_id_from_headers(authorization, x_user_id)
    try:
        return list_audits(user_id)
    except DatabaseOperationError as e:
        raise _db_http_error(e)


@app.get("/audits/{audit_id}")
def get_saved_audit(
    audit_id: str,
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Load metrics for a specific persisted audit without restoring models.

    Example output:
    {"audit_id": "uuid", "results": [{"model": "Baseline (biased)", "accuracy": 0.81}]}
    """
    user_id = _user_id_from_headers(authorization, x_user_id)
    return _load_owned_audit(audit_id, user_id)


@app.post("/audits/{audit_id}/load")
def load_saved_audit_models(
    audit_id: str,
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Restore saved models for a historical audit into memory so /predict works.

    Example output:
    {"status": "loaded", "audit_id": "uuid", "schema": {"feature_cols": ["income"]}}
    """
    user_id = _user_id_from_headers(authorization, x_user_id)
    _load_owned_audit(audit_id, user_id)
    try:
        audit_result = load_models_into_state(audit_id)
        return {
            "status": "loaded",
            "audit_id": audit_id,
            "audit": audit_result,
            "schema": get_schema(),
        }
    except DatabaseOperationError as e:
        raise _db_http_error(e)


@app.delete("/audits/{audit_id}")
def remove_saved_audit(
    audit_id: str,
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Delete one persisted audit, including saved metrics and model bundle.

    Example output:
    {"deleted": true, "audit_id": "uuid"}
    """
    user_id = _user_id_from_headers(authorization, x_user_id)
    try:
        deleted = delete_audit(audit_id, user_id)
    except DatabaseOperationError as e:
        raise _db_http_error(e)
    if not deleted:
        raise HTTPException(status_code=404, detail="Audit not found for this user.")
    return {"deleted": True, "audit_id": audit_id}


# ── EXPORT ROUTES ───────────────────────────────────────────────────────
@app.get("/export/report/{audit_id}")
def export_report(
    audit_id: str,
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Download the full audit report as JSON.

    Example output:
    Content-Type: application/json with {"audit": {...}, "dashboard_stats": {...}}
    """
    user_id = _user_id_from_headers(authorization, x_user_id)
    audit_data = _load_owned_audit(audit_id, user_id)
    dashboard_data = {}
    if _state.get("audit_id") == audit_id:
        dashboard_data = _state.get("dashboard_stats") or {}

    payload = {
        "audit": audit_data,
        "dashboard_stats": dashboard_data,
        "recommendations": _recommendations(audit_data, dashboard_data),
    }
    return Response(
        content=json.dumps(payload, indent=2, default=str),
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="audit_{audit_id}.json"'
        },
    )


@app.get("/export/csv/{audit_id}")
def export_csv(
    audit_id: str,
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Download debiased predictions for the in-memory uploaded dataset as CSV.

    Example output columns:
    all feature columns, baseline_decision, debiased_decision, bias_detected
    """
    user_id = _user_id_from_headers(authorization, x_user_id)
    _load_owned_audit(audit_id, user_id)
    if _state.get("audit_id") != audit_id:
        raise HTTPException(
            status_code=400,
            detail="Load this audit or re-upload its dataset before CSV export.",
        )

    try:
        export_df = get_debiased_predictions()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(
        content=export_df.to_csv(index=False),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="audit_{audit_id}_predictions.csv"'
        },
    )

@app.post("/remediate/{audit_id}")
async def remediate(
    audit_id: str,
    file: UploadFile | None = File(None),
    authorization: str | None = Header(None),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
):
    """
    Generate a debiased dataset for an audit.
    Uses the uploaded CSV when provided, otherwise falls back to the
    in-memory raw dataframe or the server-side saved dataset copy.
    """
    user_id = _user_id_from_headers(authorization, x_user_id)

    # If this audit's models aren't in memory, load them from DB
    if _state.get("audit_id") != audit_id or not _state.get("trained"):
        try:
            load_models_into_state(audit_id)
        except DatabaseOperationError as e:
            raise _db_http_error(e)

    # Verify ownership
    _load_owned_audit(audit_id, user_id)

    df: pd.DataFrame | None = None
    if file is not None:
        contents = await file.read()
        try:
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
        except Exception as e:
            raise HTTPException(400, detail=f"Could not parse CSV: {e}")
        try:
            _uploaded_dataset_path(audit_id).write_bytes(contents)
        except OSError:
            pass
    elif _state.get("audit_id") == audit_id and _state.get("raw_df") is not None:
        df = _state["raw_df"].copy()
    else:
        saved_dataset_path = _uploaded_dataset_path(audit_id)
        if saved_dataset_path.exists():
            try:
                df = pd.read_csv(saved_dataset_path)
            except Exception as e:
                raise HTTPException(400, detail=f"Could not parse saved CSV: {e}")
        else:
            raise HTTPException(
                status_code=400,
                detail="Original dataset not available for this audit. Re-upload the CSV once, then retry.",
            )

    required_cols = list(_state.get("feature_cols") or []) + [_state["sensitive_col"]]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise HTTPException(
            status_code=400,
            detail=f"CSV is missing required columns for remediation: {missing_cols}",
        )

    # Store raw_df in state so get_debiased_predictions() works
    _state["raw_df"] = df.copy()

    # Run debiased predictions
    try:
        export_df = get_debiased_predictions()
    except Exception as e:
        raise HTTPException(400, detail=str(e))

    # Add sensitive col back
    sensitive_col = _state["sensitive_col"]
    target_col    = _state["target_col"]
    aligned_df    = df.iloc[:len(export_df)]
    export_df[sensitive_col] = aligned_df[sensitive_col].values

    # Rename debiased_decision → target_col so it re-uploads cleanly
    original_decisions = export_df["baseline_decision"].values
    debiased_decisions = export_df["debiased_decision"].values
    export_df[target_col] = debiased_decisions

    # Compute summary stats
    rows_changed   = int((original_decisions != debiased_decisions).sum())
    pct_changed    = round(rows_changed / len(export_df) * 100, 1)

    from fairlearn.metrics import demographic_parity_ratio
    from pipeline import encode_sensitive
    A, _, _, _ = encode_sensitive(export_df[sensitive_col])
    original_di = float(demographic_parity_ratio(
        export_df[target_col].values, original_decisions, sensitive_features=A
    ))
    debiased_di = float(demographic_parity_ratio(
        export_df[target_col].values, debiased_decisions, sensitive_features=A
    ))

    # Drop helper columns
    export_df.drop(
        columns=["baseline_decision", "debiased_decision", "bias_detected"],
        errors="ignore", inplace=True
    )

    summary = {
        "rows_changed":       rows_changed,
        "pct_changed":        pct_changed,
        "original_di_ratio":  round(original_di, 3),
        "debiased_di_ratio":  round(debiased_di, 3),
    }

    dataset_name = _state.get("dataset_name") or "dataset.csv"
    out_filename = f"debiased_{dataset_name}"

    return Response(
        content=export_df.to_csv(index=False),
        media_type="text/csv",
        headers={
            "Content-Disposition":    f'attachment; filename="{out_filename}"',
            "X-Remediation-Summary":  json.dumps(summary),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Remediation-Summary",
        },
    )
