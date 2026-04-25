from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.connection import get_db, async_session
from db.models import Audit, AuditResult
from schemas.audit import AuditStatusResponse, AuditResultResponse
from pipeline.graph import audit_pipeline
from pipeline.state import PipelineState
import uuid

router = APIRouter(prefix="/api", tags=["audit"])


async def run_pipeline(audit_id: str, file_path: str, dataset_name: str):
    initial_state: PipelineState = {
        "audit_id": audit_id,
        "file_path": file_path,
        "dataset_name": dataset_name,
        "total_rows": None,
        "total_columns": None,
        "protected_attributes": None,
        "features": None,
        "target": None,
        "excluded": None,
        "null_summary": None,
        "proxy_warnings": None,
        "column_details": None,
        "schema_json": None,
        "bias_metrics": None,
        "overall_risk": None,
        "report_markdown": None,
        "remediation_results": None,
        "status": "pending",
        "error": None,
    }
    try:
        await audit_pipeline.ainvoke(initial_state)
    except Exception as e:
        async with async_session() as db:
            audit = await db.get(Audit, audit_id)
            if audit:
                audit.status = "failed"
                await db.commit()
        raise e


@router.post("/audit/{audit_id}/run")
async def trigger_audit(
    audit_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(400, "Invalid audit_id format")

    audit = await db.get(Audit, audit_uuid)
    if not audit:
        raise HTTPException(404, "Audit not found")
    if audit.status not in ("pending", "failed"):
        raise HTTPException(400, f"Audit already in progress or completed (status: {audit.status})")

    audit.status = "profiling"
    await db.commit()

    background_tasks.add_task(run_pipeline, audit_id, audit.file_path, audit.dataset_name)
    return {"message": "Audit pipeline started"}


@router.get("/audit/{audit_id}/status", response_model=AuditStatusResponse)
async def get_audit_status(
    audit_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(400, "Invalid audit_id format")

    audit = await db.get(Audit, audit_uuid)
    if not audit:
        raise HTTPException(404, "Audit not found")

    return AuditStatusResponse(
        id=audit.id,
        dataset_name=audit.dataset_name,
        status=audit.status,
        overall_risk=audit.overall_risk,
        row_count=audit.row_count,
        column_count=audit.column_count,
        created_at=audit.created_at,
        completed_at=audit.completed_at,
    )


@router.get("/audit/{audit_id}/results")
async def get_audit_results(
    audit_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(400, "Invalid audit_id format")

    audit = await db.get(Audit, audit_uuid)
    if not audit:
        raise HTTPException(404, "Audit not found")

    results = await db.execute(select(AuditResult).where(AuditResult.audit_id == audit_uuid))
    result_rows = results.scalars().all()

    metrics_map = {}
    for r in result_rows:
        if r.protected_attr not in metrics_map:
            metrics_map[r.protected_attr] = {
                "protected_attr": r.protected_attr,
                "groups": {},
                "demographic_parity_diff": r.demographic_parity_diff,
                "disparate_impact_ratio": r.disparate_impact_ratio,
                "equalized_odds_diff": r.equalized_odds_diff,
                "predictive_parity_diff": r.predictive_parity_diff,
                "theil_index": r.theil_index,
                "p_value": r.p_value,
                "sample_sizes": {},
                "flag_level": r.flag_level,
            }
        metrics_map[r.protected_attr]["groups"][r.group_name] = r.positive_rate
        metrics_map[r.protected_attr]["sample_sizes"][r.group_name] = r.sample_size

    return {
        "audit_id": audit_id,
        "overall_risk": audit.overall_risk,
        "metrics": list(metrics_map.values()),
    }
