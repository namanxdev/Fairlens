"""
main.py — FastAPI app
Run with: uvicorn main:app --reload
Docs at:  http://localhost:8000/docs
"""

import io
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pipeline import train_pipeline, get_audit, get_summary, predict_applicant, _state
from schemas import ApplicantRequest, AuditResponse, PredictResponse

# ── App setup ────────────────────────────────────────────────────────────
app = FastAPI(
    title="AI Fairness Auditor",
    description="Upload a hiring/loan dataset → get bias metrics → compare debiased models",
    version="1.0.0",
)

# Allow frontend (Next.js on :3000) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health check ─────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status": "running",
        "trained": _state["trained"],
        "message": "POST /upload a CSV to begin audit"
    }


# ── POST /upload ──────────────────────────────────────────────────────────
# This replaces your colab's hardcoded read_csv("/content/...")
# Frontend sends the CSV file → pipeline trains all 3 models → returns summary
@app.post("/upload", response_model=AuditResponse)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a CSV file (like job_applications_biased.csv).
    Trains baseline, reweighted, and threshold models.
    Returns audit metrics immediately after training.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files accepted.")

    contents = await file.read()
    try:
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {e}")

    required_cols = ["hired", "gender", "years_experience", "gpa",
                     "technical_score", "interview_score"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {missing}"
        )

    try:
        summary = train_pipeline(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Training failed: {e}")

    return summary


# ── GET /audit ────────────────────────────────────────────────────────────
# Returns metrics for all 3 models — your colab's print_metrics() as JSON
@app.get("/audit", response_model=AuditResponse)
def audit():
    """
    Get fairness metrics for all 3 models on the held-out test set.
    Each result includes accuracy, approval rates, DI ratio, 80% rule pass/fail.
    """
    if not _state["trained"]:
        raise HTTPException(
            status_code=400,
            detail="No dataset loaded. POST /upload first."
        )
    return get_audit()


# ── GET /summary ──────────────────────────────────────────────────────────
# Same as audit — for your dashboard's summary table
@app.get("/summary")
def summary():
    """Summary table — same as /audit, formatted for dashboard consumption."""
    if not _state["trained"]:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")
    return get_summary()


# ── POST /predict ─────────────────────────────────────────────────────────
# New endpoint — not in your colab
# Send one applicant → get decision from all 3 models → see if bias changed the outcome
@app.post("/predict", response_model=PredictResponse)
def predict(applicant: ApplicantRequest):
    """
    Submit a single applicant's details.
    Returns hiring decision from all 3 models so you can compare:
      - baseline (biased)
      - reweighted (Stage 1 fixed)
      - threshold calibrated (Stage 3 fixed)

    If decisions differ, bias_detected=True — the baseline was treating this person unfairly.
    """
    if not _state["trained"]:
        raise HTTPException(status_code=400, detail="No dataset loaded. POST /upload first.")

    applicant_dict = applicant.model_dump()
    gender = applicant_dict.pop("gender")

    try:
        result = predict_applicant(applicant_dict, gender)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


# ── GET /status ───────────────────────────────────────────────────────────
@app.get("/status")
def status():
    """Check if models are trained and ready."""
    return {
        "trained": _state["trained"],
        "feature_cols": _state["feature_cols"],
    }
