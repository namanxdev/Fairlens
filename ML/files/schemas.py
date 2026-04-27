"""
schemas.py — Pydantic models for request/response validation
FastAPI uses these to auto-generate docs at /docs
"""

from pydantic import BaseModel, Field
from typing import Optional

# ── Request: single applicant prediction ────────────────────────────────
class ApplicantRequest(BaseModel):
    years_experience:  float = Field(..., example=4.5,   description="Years of work experience")
    gpa:               float = Field(..., example=3.6,   description="GPA out of 4.0")
    technical_score:   float = Field(..., example=72.0,  description="Technical test score 0-100")
    interview_score:   float = Field(..., example=65.0,  description="Interview score 0-100")
    online_assessment: float = Field(..., example=74.0,  description="Online test score 0-100")
    communication:     int   = Field(..., example=7,     description="Communication rating 1-10")
    num_prev_jobs:     int   = Field(..., example=2,     description="Number of previous jobs")
    has_certification: int   = Field(..., example=1,     description="Has certification? 0 or 1")
    referral:          int   = Field(..., example=0,     description="Was referred? 0 or 1")
    cover_letter_len:  int   = Field(..., example=350,   description="Cover letter word count")
    gender:            str   = Field(..., example="Female", description="Male | Female | Non-binary")

# ── Response: single metric row ─────────────────────────────────────────
class MetricRow(BaseModel):
    model:                          str
    accuracy:                       float
    female_approval_rate:           float
    male_approval_rate:             float
    disparate_impact_ratio:         float
    demographic_parity_difference:  float
    equalized_odds_difference:      float
    legal_pass:                     bool

# ── Response: audit / summary ───────────────────────────────────────────
class AuditResponse(BaseModel):
    results: list[MetricRow]

# ── Response: single prediction ─────────────────────────────────────────
class ModelDecision(BaseModel):
    decision:    int
    label:       str
    probability: Optional[float] = None

class PredictResponse(BaseModel):
    applicant:            dict
    gender:               str
    baseline:             ModelDecision
    reweighted:           ModelDecision
    threshold_calibrated: ModelDecision
    bias_detected:        bool
    note:                 str
