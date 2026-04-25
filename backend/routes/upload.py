from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.connection import get_db
from db.models import Audit
from config import settings
import pandas as pd
import uuid
import os
import aiofiles

router = APIRouter(prefix="/api", tags=["upload"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


@router.post("/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(400, f"File too large: {size_mb:.1f}MB (max {settings.MAX_FILE_SIZE_MB}MB)")

    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        row_count = len(df)
        col_count = len(df.columns)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(400, f"Failed to parse file: {str(e)}")

    if row_count < 10:
        os.remove(file_path)
        raise HTTPException(400, "Dataset must have at least 10 rows for meaningful analysis")
    if col_count < 2:
        os.remove(file_path)
        raise HTTPException(400, "Dataset must have at least 2 columns")

    audit = Audit(
        dataset_name=file.filename,
        file_path=file_path,
        row_count=row_count,
        column_count=col_count,
        status="pending",
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    return {
        "audit_id": str(audit.id),
        "dataset_name": file.filename,
        "row_count": row_count,
        "column_count": col_count,
        "status": "pending",
        "message": f"Dataset uploaded successfully. {row_count} rows × {col_count} columns."
    }
