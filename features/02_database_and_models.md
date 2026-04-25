# Feature 02: Database Schema & ORM Models

## Overview

Define the PostgreSQL database schema and SQLAlchemy async ORM models that store users, audits, audit results, remediation logs, and LLM-generated reports. This feature also sets up Alembic for migrations.

---

## Database Schema (SQL)

```sql
-- Enable pgvector extension (for RAG embeddings in Feature 06)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    org_name      VARCHAR(255),
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE audits (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES users(id) ON DELETE SET NULL,
    dataset_name  VARCHAR(255) NOT NULL,
    file_path     VARCHAR(500) NOT NULL,
    row_count     INTEGER,
    column_count  INTEGER,
    status        VARCHAR(50) DEFAULT 'pending',
    -- status values: pending, profiling, analyzing, explaining, remediating, completed, failed
    overall_risk  VARCHAR(20),
    -- risk values: CRITICAL, HIGH, MEDIUM, LOW, NONE
    schema_json   JSONB,        -- Output of Data Profiler (Node 1)
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at  TIMESTAMP WITH TIME ZONE
);

CREATE TABLE audit_results (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id                 UUID REFERENCES audits(id) ON DELETE CASCADE,
    protected_attr           VARCHAR(100) NOT NULL,
    group_name               VARCHAR(100) NOT NULL,
    positive_rate            FLOAT,
    demographic_parity_diff  FLOAT,
    disparate_impact_ratio   FLOAT,
    equalized_odds_diff      FLOAT,
    predictive_parity_diff   FLOAT,
    theil_index              FLOAT,
    p_value                  FLOAT,
    sample_size              INTEGER,
    flag_level               VARCHAR(20),
    -- flag values: CRITICAL, HIGH, MEDIUM, LOW
    created_at               TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE remediation_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id        UUID REFERENCES audits(id) ON DELETE CASCADE,
    strategy        VARCHAR(100) NOT NULL,
    metric_before   JSONB NOT NULL,
    metric_after    JSONB NOT NULL,
    accuracy_before FLOAT,
    accuracy_after  FLOAT,
    applied_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE reports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id    UUID REFERENCES audits(id) ON DELETE CASCADE,
    content_md  TEXT NOT NULL,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast audit lookups
CREATE INDEX idx_audits_user_id ON audits(user_id);
CREATE INDEX idx_audits_status ON audits(status);
CREATE INDEX idx_audit_results_audit_id ON audit_results(audit_id);
CREATE INDEX idx_remediation_logs_audit_id ON remediation_logs(audit_id);
```

---

## SQLAlchemy ORM Models

### `backend/db/models.py`

```python
import uuid
from datetime import datetime
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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    audits = relationship("Audit", back_populates="user")


class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    dataset_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    status = Column(String(50), default="pending")
    overall_risk = Column(String(20), nullable=True)
    schema_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="audits")
    results = relationship("AuditResult", back_populates="audit", cascade="all, delete-orphan")
    remediations = relationship("RemediationLog", back_populates="audit", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="audit", uselist=False, cascade="all, delete-orphan")


class AuditResult(Base):
    __tablename__ = "audit_results"

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
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    audit = relationship("Audit", back_populates="results")


class RemediationLog(Base):
    __tablename__ = "remediation_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    strategy = Column(String(100), nullable=False)
    metric_before = Column(JSONB, nullable=False)
    metric_after = Column(JSONB, nullable=False)
    accuracy_before = Column(Float, nullable=True)
    accuracy_after = Column(Float, nullable=True)
    applied_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    audit = relationship("Audit", back_populates="remediations")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id", ondelete="CASCADE"), nullable=False)
    content_md = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    audit = relationship("Audit", back_populates="report")
```

---

## Pydantic Schemas

### `backend/schemas/audit.py`

```python
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
    strategy: str  # "reweighting", "resampling", "threshold_adjustment"


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
```

---

## Alembic Setup

```bash
cd backend
alembic init alembic
```

Configure `alembic/env.py` to use the async engine from `db/connection.py` and auto-detect model changes from `db/models.py`.

---

## Verification

1. Running `alembic upgrade head` creates all tables in PostgreSQL
2. Tables `users`, `audits`, `audit_results`, `remediation_logs`, `reports` exist with correct columns
3. Foreign key constraints and cascade deletes work correctly
4. pgvector extension is enabled (verify with `SELECT * FROM pg_extension WHERE extname = 'vector';`)
