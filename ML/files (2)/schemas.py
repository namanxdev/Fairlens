"""
schemas.py — request models for new dashboard, LLM, and compare routes.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DashboardStatsRequest(BaseModel):
    sensitive_cols: list[str] = Field(
        ...,
        examples=[["gender", "age", "ethnicity"]],
        description="Sensitive attributes to break down independently.",
    )


class CompareRequest(BaseModel):
    candidate_a: dict[str, Any] = Field(
        ...,
        examples=[{"years_experience": 5, "gpa": 3.7, "sensitive_value": "Female"}],
    )
    candidate_b: dict[str, Any] = Field(
        ...,
        examples=[{"years_experience": 4, "gpa": 3.8, "sensitive_value": "Male"}],
    )
