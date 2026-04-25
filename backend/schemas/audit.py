from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class AuditCreate(BaseModel):
    dataset_name: str
    file_path: str


class AuditStatusResponse(BaseModel):
    id: UUID
    dataset_name: str
    status: str
    overall_risk: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AuditResultResponse(BaseModel):
    id: UUID
    protected_attr: str
    group_name: str
    positive_rate: Optional[float] = None
    demographic_parity_diff: Optional[float] = None
    disparate_impact_ratio: Optional[float] = None
    equalized_odds_diff: Optional[float] = None
    predictive_parity_diff: Optional[float] = None
    theil_index: Optional[float] = None
    p_value: Optional[float] = None
    sample_size: Optional[int] = None
    flag_level: Optional[str] = None

    class Config:
        from_attributes = True


class RemediationRequest(BaseModel):
    strategy: str


class RemediationResponse(BaseModel):
    strategy: str
    metric_before: dict
    metric_after: dict
    accuracy_before: Optional[float] = None
    accuracy_after: Optional[float] = None

    class Config:
        from_attributes = True


class ReportResponse(BaseModel):
    id: UUID
    audit_id: UUID
    content_md: str
    created_at: datetime

    class Config:
        from_attributes = True
