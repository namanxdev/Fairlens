from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.connection import get_db
from db.models import Report
from schemas.audit import ReportResponse
import uuid

router = APIRouter(prefix="/api", tags=["report"])


@router.get("/audit/{audit_id}/report")
async def get_report(
    audit_id: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        audit_uuid = uuid.UUID(audit_id)
    except ValueError:
        raise HTTPException(400, "Invalid audit_id format")

    result = await db.execute(select(Report).where(Report.audit_id == audit_uuid))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(404, "Report not found")

    return ReportResponse(
        id=report.id,
        audit_id=report.audit_id,
        content_md=report.content_md,
        created_at=report.created_at,
    )
