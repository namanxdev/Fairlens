"""
schemas.py — request models for new dashboard, LLM, and compare routes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FairnessConfigRequest(BaseModel):
    fairness_criterion: str = Field(
        "equal_opportunity",
        description="Fairness constraint: equal_opportunity or demographic_parity.",
    )
    difference_bound: float = Field(0.05, ge=0, le=1)
    positive_label: str | None = Field(
        None,
        description="Required when the positive target label cannot be inferred safely.",
    )


class RemediationConfigRequest(BaseModel):
    remediation_method: str = Field(
        "reweighing",
        description="Data-level remediation method: reweighing or disparate_impact_remover.",
    )
    repair_level: float = Field(1.0, ge=0, le=1)
    max_attempts: int = Field(3, ge=1, le=5)


class DashboardStatsRequest(BaseModel):
    sensitive_cols: list[str] = Field(
        ...,
        examples=[["gender", "age", "ethnicity"]],
        description="Sensitive attributes to break down independently.",
    )
    use_debiased: bool = Field(False)


class CompareRequest(BaseModel):
    candidate_a: dict[str, Any] = Field(
        ...,
        examples=[{"years_experience": 5, "gpa": 3.7, "sensitive_value": "Female"}],
    )
    candidate_b: dict[str, Any] = Field(
        ...,
        examples=[{"years_experience": 4, "gpa": 3.8, "sensitive_value": "Male"}],
    )
