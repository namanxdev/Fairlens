import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, ForeignKey,
    DateTime, JSON, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from db.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    org_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    audits = relationship("Audit", back_populates="user")


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (
        Index("idx_audits_user_id", "user_id"),
        Index("idx_audits_status", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    dataset_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    status = Column(String(50), default="pending")
    overall_risk = Column(String(20), nullable=True)
    schema_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="audits")
    results = relationship("AuditResult", back_populates="audit", cascade="all, delete-orphan")
    remediations = relationship("RemediationLog", back_populates="audit", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="audit", uselist=False, cascade="all, delete-orphan")


class AuditResult(Base):
    __tablename__ = "audit_results"
    __table_args__ = (
        Index("idx_audit_results_audit_id", "audit_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    protected_attr = Column(String(100), nullable=False)
    group_name = Column(String(100), nullable=False)
    positive_rate = Column(Float, nullable=True)
    demographic_parity_diff = Column(Float, nullable=True)
    disparate_impact_ratio = Column(Float, nullable=True)
    equalized_odds_diff = Column(Float, nullable=True)
    predictive_parity_diff = Column(Float, nullable=True)
    theil_index = Column(Float, nullable=True)
    p_value = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=True)
    flag_level = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    audit = relationship("Audit", back_populates="results")


class RemediationLog(Base):
    __tablename__ = "remediation_logs"
    __table_args__ = (
        Index("idx_remediation_logs_audit_id", "audit_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    strategy = Column(String(100), nullable=False)
    metric_before = Column(JSONB, nullable=False)
    metric_after = Column(JSONB, nullable=False)
    accuracy_before = Column(Float, nullable=True)
    accuracy_after = Column(Float, nullable=True)
    applied_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    audit = relationship("Audit", back_populates="remediations")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    content_md = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    audit = relationship("Audit", back_populates="report")
