"""
database.py — persistent audit sessions for the fairness API.

PostgreSQL only. Connection string is read from the DATABASE_URL env var (or
FAIRNESS_DATABASE_URL as fallback). Load a .env file by setting one up at
<repo-root>/backend/.env with DATABASE_URL=postgresql+psycopg2://...
"""

from __future__ import annotations

import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

# Load .env from <repo-root>/backend/.env — works regardless of cwd
_env_file = Path(__file__).resolve().parent.parent.parent / "backend" / ".env"
load_dotenv(dotenv_path=_env_file, override=False)

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    LargeBinary,
    String,
    create_engine,
    delete,
    select,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


_raw_url = (
    os.getenv("DATABASE_URL")
    or os.getenv("FAIRNESS_DATABASE_URL")
    or "postgresql+psycopg2://postgres:postgres@localhost:5432/fairlens"
)
# asyncpg is async-only; swap it for psycopg2 which works with sync SQLAlchemy.
DATABASE_URL = _raw_url.replace("+asyncpg", "+psycopg2")

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()
_INIT_ERROR: str | None = None


def _uuid() -> str:
    return str(uuid4())


class DatabaseOperationError(RuntimeError):
    """Raised when a database operation fails in a controlled way."""


class Audit(Base):
    __tablename__ = "audits"

    id = Column(PGUUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(String, nullable=False, index=True, default="anonymous")
    domain = Column(String, nullable=False, default="custom")
    dataset_name = Column(String, nullable=False)
    target_col = Column(String, nullable=False)
    sensitive_col = Column(String, nullable=False)
    fairness_config = Column(JSON, nullable=False, default=dict)
    verified_di_ratio_after_retraining = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String, nullable=False, default="processing")

    results = relationship(
        "AuditResult",
        back_populates="audit",
        cascade="all, delete-orphan",
    )
    saved_model = relationship(
        "SavedModel",
        back_populates="audit",
        cascade="all, delete-orphan",
        uselist=False,
    )


class AuditResult(Base):
    __tablename__ = "audit_results"

    id = Column(PGUUID(as_uuid=False), primary_key=True, default=_uuid)
    audit_id = Column(PGUUID(as_uuid=False), ForeignKey("audits.id"), nullable=False, index=True)
    model_name = Column(String, nullable=False)
    group_rates = Column(JSON, nullable=False, default=dict)
    di_ratio = Column(Float, nullable=True)
    dp_diff = Column(Float, nullable=True)
    eq_odds_diff = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    legal_pass = Column(Boolean, nullable=False, default=False)

    audit = relationship("Audit", back_populates="results")


class SavedModel(Base):
    __tablename__ = "saved_models"

    id = Column(PGUUID(as_uuid=False), primary_key=True, default=_uuid)
    audit_id = Column(PGUUID(as_uuid=False), ForeignKey("audits.id"), nullable=False, index=True)
    model_blob = Column(LargeBinary, nullable=False)
    feature_cols = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    audit = relationship("Audit", back_populates="saved_model")


def _init_db() -> None:
    global _INIT_ERROR
    try:
        Base.metadata.create_all(bind=engine)
        _INIT_ERROR = None
    except SQLAlchemyError as exc:
        _INIT_ERROR = f"Could not initialize database: {exc}"


def _ensure_ready() -> None:
    if _INIT_ERROR:
        raise DatabaseOperationError(_INIT_ERROR)


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _result_to_dict(row: AuditResult) -> dict:
    return {
        "model": row.model_name,
        "accuracy": row.accuracy,
        "group_approval_rates": row.group_rates or {},
        "disparate_impact_ratio": row.di_ratio,
        "demographic_parity_difference": row.dp_diff,
        "equalized_odds_difference": row.eq_odds_diff,
        "legal_pass": bool(row.legal_pass),
        "legal_threshold": "EEOC 80% rule: DI ratio >= 0.80",
    }


def create_audit(
    user_id,
    domain,
    dataset_name,
    target_col,
    sensitive_col,
    fairness_config: dict | None = None,
) -> str:
    """Insert an audit row and return its UUID string."""
    _ensure_ready()
    audit_id = _uuid()
    try:
        with SessionLocal() as session:
            audit = Audit(
                id=audit_id,
                user_id=user_id or "anonymous",
                domain=domain or "custom",
                dataset_name=dataset_name,
                target_col=target_col,
                sensitive_col=sensitive_col,
                fairness_config=fairness_config or {},
                status="processing",
            )
            session.add(audit)
            session.commit()
        return audit_id
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database create_audit failed: {exc}") from exc


def set_audit_status(audit_id: str, status: str) -> None:
    """Update audit status without exposing SQLAlchemy exceptions to routes."""
    _ensure_ready()
    try:
        with SessionLocal() as session:
            audit = session.get(Audit, audit_id)
            if audit:
                audit.status = status
                session.commit()
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database set_audit_status failed: {exc}") from exc


def save_remediation_summary(audit_id: str, verified_di_ratio_after_retraining: float | None) -> None:
    """Persist the round-trip verification score for the remediated dataset."""
    _ensure_ready()
    try:
        with SessionLocal() as session:
            audit = session.get(Audit, audit_id)
            if audit:
                audit.verified_di_ratio_after_retraining = _as_float(
                    verified_di_ratio_after_retraining
                )
                session.commit()
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database save_remediation_summary failed: {exc}") from exc


def save_audit_results(audit_id, results_list):
    """Persist one audit_results row for each model result."""
    _ensure_ready()
    try:
        with SessionLocal() as session:
            audit = session.get(Audit, audit_id)
            if not audit:
                raise DatabaseOperationError(f"Audit '{audit_id}' not found.")

            session.execute(delete(AuditResult).where(AuditResult.audit_id == audit_id))
            for result in results_list:
                session.add(
                    AuditResult(
                        id=_uuid(),
                        audit_id=audit_id,
                        model_name=result.get("model") or result.get("model_name") or "Unknown",
                        group_rates=result.get("group_approval_rates") or {},
                        di_ratio=_as_float(result.get("disparate_impact_ratio")),
                        dp_diff=_as_float(result.get("demographic_parity_difference")),
                        eq_odds_diff=_as_float(result.get("equalized_odds_difference")),
                        accuracy=_as_float(result.get("accuracy")),
                        legal_pass=bool(result.get("legal_pass")),
                    )
                )
            session.commit()
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database save_audit_results failed: {exc}") from exc


def save_models(audit_id, state_dict):
    """
    Pickle only model/scaler/encoder objects and metadata needed for prediction.
    Raw uploaded DataFrames and held-out arrays are intentionally excluded.
    """
    _ensure_ready()
    model_state = {
        "baseline": state_dict.get("baseline"),
        "reweighted_model": state_dict.get("reweighted_model"),
        "threshold_model": state_dict.get("threshold_model"),
        "preprocessor": state_dict.get("preprocessor"),
        "feature_cols": state_dict.get("feature_cols"),
        "target_col": state_dict.get("target_col"),
        "sensitive_col": state_dict.get("sensitive_col"),
        "sensitive_groups": state_dict.get("sensitive_groups"),
        "sensitive_encoder": state_dict.get("sensitive_encoder"),
        "sensitive_info": state_dict.get("sensitive_info"),
        "target_info": state_dict.get("target_info"),
        "positive_label": state_dict.get("positive_label"),
        "scaler": state_dict.get("scaler"),
        "label_encoders": state_dict.get("label_encoders") or {},
        "domain": state_dict.get("domain"),
        "fairness_criterion": state_dict.get("fairness_criterion"),
        "difference_bound": state_dict.get("difference_bound"),
    }
    try:
        blob = pickle.dumps(model_state)
        with SessionLocal() as session:
            audit = session.get(Audit, audit_id)
            if not audit:
                raise DatabaseOperationError(f"Audit '{audit_id}' not found.")

            session.execute(delete(SavedModel).where(SavedModel.audit_id == audit_id))
            session.add(
                SavedModel(
                    id=_uuid(),
                    audit_id=audit_id,
                    model_blob=blob,
                    feature_cols=state_dict.get("feature_cols") or [],
                )
            )
            session.commit()
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database save_models failed: {exc}") from exc
    except (pickle.PickleError, AttributeError, TypeError) as exc:
        raise DatabaseOperationError(f"Could not pickle saved models: {exc}") from exc


def load_audit(audit_id) -> dict:
    """Load audit metadata and saved result rows in the get_audit-compatible shape."""
    _ensure_ready()
    try:
        with SessionLocal() as session:
            audit = session.get(Audit, audit_id)
            if not audit:
                raise DatabaseOperationError(f"Audit '{audit_id}' not found.")

            results = [_result_to_dict(row) for row in audit.results]
            feature_cols = []
            if audit.saved_model:
                feature_cols = audit.saved_model.feature_cols or []
            groups_found = sorted({
                str(group)
                for result in results
                for group in (result.get("group_approval_rates") or {}).keys()
            })
            return {
                "audit_id": audit.id,
                "user_id": audit.user_id,
                "domain": audit.domain,
                "dataset_name": audit.dataset_name,
                "target_col": audit.target_col,
                "sensitive_col": audit.sensitive_col,
                "created_at": audit.created_at.isoformat(),
                "status": audit.status,
                "fairness_config": audit.fairness_config or {},
                "verified_di_ratio_after_retraining": audit.verified_di_ratio_after_retraining,
                "groups_found": groups_found,
                "feature_cols": feature_cols,
                "results": results,
            }
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database load_audit failed: {exc}") from exc


def load_models_into_state(audit_id):
    """Unpickle saved models into pipeline._state so /predict works again."""
    _ensure_ready()
    try:
        with SessionLocal() as session:
            audit = session.get(Audit, audit_id)
            if not audit or not audit.saved_model:
                raise DatabaseOperationError(f"Saved models for audit '{audit_id}' not found.")
            model_state = pickle.loads(audit.saved_model.model_blob)

        audit_result = load_audit(audit_id)
        from pipeline import _state

        _state.update({
            "baseline": model_state.get("baseline"),
            "reweighted_model": model_state.get("reweighted_model"),
            "threshold_model": model_state.get("threshold_model"),
            "preprocessor": model_state.get("preprocessor"),
            "X_test": None,
            "y_test": None,
            "A_test": None,
            "A_test_raw": None,
            "feature_cols": model_state.get("feature_cols"),
            "target_col": model_state.get("target_col"),
            "sensitive_col": model_state.get("sensitive_col"),
            "sensitive_groups": model_state.get("sensitive_groups"),
            "sensitive_encoder": model_state.get("sensitive_encoder"),
            "sensitive_info": model_state.get("sensitive_info") or model_state.get("sensitive_encoder"),
            "target_info": model_state.get("target_info"),
            "positive_label": model_state.get("positive_label"),
            "scaler": model_state.get("scaler"),
            "label_encoders": model_state.get("label_encoders") or {},
            "trained": True,
            "domain": model_state.get("domain"),
            "raw_df": None,
            "dashboard_stats": None,
            "dashboard_sensitive_cols": None,
            "audit_id": audit_id,
            "audit_result": audit_result,
            "dataset_name": audit_result.get("dataset_name"),
            "user_id": audit_result.get("user_id"),
            "fairness_criterion": model_state.get("fairness_criterion", "equal_opportunity"),
            "difference_bound": model_state.get("difference_bound", 0.05),
        })
        return audit_result
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database load_models_into_state failed: {exc}") from exc
    except (
        pickle.PickleError,
        EOFError,
        AttributeError,
        TypeError,
        ImportError,
        ModuleNotFoundError,
    ) as exc:
        raise DatabaseOperationError(f"Could not unpickle saved models: {exc}") from exc


def list_audits(user_id) -> list:
    """Return audit summaries for the audit history page."""
    _ensure_ready()
    try:
        with SessionLocal() as session:
            audits = session.execute(
                select(Audit)
                .where(Audit.user_id == (user_id or "anonymous"))
                .order_by(Audit.created_at.desc())
            ).scalars().all()
            return [
                {
                    "audit_id": audit.id,
                    "domain": audit.domain,
                    "dataset_name": audit.dataset_name,
                    "target_col": audit.target_col,
                    "sensitive_col": audit.sensitive_col,
                    "created_at": audit.created_at.isoformat(),
                    "status": audit.status,
                    "fairness_config": audit.fairness_config or {},
                    "verified_di_ratio_after_retraining": audit.verified_di_ratio_after_retraining,
                    "models_saved": bool(audit.saved_model),
                    "results_count": len(audit.results),
                }
                for audit in audits
            ]
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database list_audits failed: {exc}") from exc


def delete_audit(audit_id, user_id):
    """Delete an audit and its result/model rows for the requesting user."""
    _ensure_ready()
    try:
        with SessionLocal() as session:
            audit = session.get(Audit, audit_id)
            if not audit or audit.user_id != (user_id or "anonymous"):
                return False
            session.delete(audit)
            session.commit()
            return True
    except SQLAlchemyError as exc:
        raise DatabaseOperationError(f"Database delete_audit failed: {exc}") from exc


_init_db()
