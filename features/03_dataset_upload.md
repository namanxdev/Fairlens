# Feature 03: Dataset Upload & Validation

## Overview

Allow users to upload CSV or Excel files through the web dashboard. The backend validates the file, stores it on disk, creates an `audit` record in the database, and returns an `audit_id` for subsequent pipeline operations.

---

## Data Sources

FairLens accepts two types of data input:

1. **User-uploaded files** — CSV (`.csv`) and Excel (`.xlsx`, `.xls`) files uploaded via the web UI
2. **Bundled sample datasets** — Pre-loaded demo datasets (see Feature 11) that users can select with one click

### Supported File Formats

| Format | Extension | Parser | Max Size |
|--------|-----------|--------|----------|
| CSV | `.csv` | `pandas.read_csv()` | 100 MB |
| Excel | `.xlsx`, `.xls` | `pandas.read_excel()` (openpyxl) | 100 MB |

---

## Backend Implementation

### API Endpoint: `POST /api/upload`

**File:** `backend/routes/upload.py`

```python
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
    # 1. Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}. Allowed: {ALLOWED_EXTENSIONS}")

    # 2. Validate file size
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(400, f"File too large: {size_mb:.1f}MB (max {settings.MAX_FILE_SIZE_MB}MB)")

    # 3. Save file to disk
    file_id = str(uuid.uuid4())
    filename = f"{file_id}{ext}"
    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    async with aiofiles.open(file_path, "wb") as f:
        await f.write(contents)

    # 4. Quick-parse to get row/column counts
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

    # 5. Validate minimum data requirements
    if row_count < 10:
        os.remove(file_path)
        raise HTTPException(400, "Dataset must have at least 10 rows for meaningful analysis")
    if col_count < 2:
        os.remove(file_path)
        raise HTTPException(400, "Dataset must have at least 2 columns")

    # 6. Create audit record
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
```

### Register Route in `main.py`

```python
from routes.upload import router as upload_router
app.include_router(upload_router)
```

---

## Frontend Implementation

### Upload Page UI (`frontend/app/page.tsx`)

The landing page should serve as the primary upload interface with:

1. **Hero Section** — App title "FairLens", tagline "Detect and Fix Bias in Your Data", and a brief description
2. **Upload Zone** — A drag-and-drop area (using `react-dropzone`) with:
   - Dashed border that highlights on drag-over
   - File type indicators (CSV, XLSX icons)
   - "or click to browse" text
   - Maximum file size display (100 MB)
3. **Upload Progress** — Progress bar during upload with percentage
4. **Post-Upload** — After successful upload, show:
   - Dataset name, row count, column count
   - "Start Audit" button that navigates to `/dashboard?audit_id=<id>`
5. **Quick-Start Section** — Cards for sample datasets (Feature 11) with "Try with demo data" button

### UI Component: `FileUpload.tsx`

**File:** `frontend/components/FileUpload.tsx`

```typescript
'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadFile } from '@/lib/api';
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle } from 'lucide-react';

interface UploadResult {
  audit_id: string;
  dataset_name: string;
  row_count: number;
  column_count: number;
}

interface FileUploadProps {
  onUploadComplete: (result: UploadResult) => void;
}

export default function FileUpload({ onUploadComplete }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      const response = await uploadFile(file, setProgress);
      onUploadComplete(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  }, [onUploadComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/vnd.ms-excel': ['.xls'],
    },
    maxFiles: 1,
    maxSize: 100 * 1024 * 1024, // 100 MB
  });

  return (
    <div
      {...getRootProps()}
      className={`upload-zone ${isDragActive ? 'drag-active' : ''} ${uploading ? 'uploading' : ''}`}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <div className="upload-progress">
          <div className="progress-bar" style={{ width: `${progress}%` }} />
          <span>{progress}% uploaded</span>
        </div>
      ) : (
        <>
          <Upload size={48} />
          <h3>Drop your dataset here</h3>
          <p>CSV or Excel files up to 100 MB</p>
          <span className="upload-browse">or click to browse</span>
        </>
      )}
      {error && (
        <div className="upload-error">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
```

### Upload Zone Styling

The upload zone should have:
- Dark glassmorphic card with subtle border
- Dashed border (2px) that changes color on hover/drag
- Smooth pulse animation when dragging files over
- Progress bar with gradient fill
- Error state with red accent

---

## Validation Rules

| Check | Condition | Error Message |
|-------|-----------|---------------|
| File extension | Not in `.csv`, `.xlsx`, `.xls` | "Unsupported file type" |
| File size | > 100 MB | "File too large" |
| Parse success | pandas fails to read | "Failed to parse file" |
| Minimum rows | < 10 rows | "Dataset must have at least 10 rows" |
| Minimum columns | < 2 columns | "Dataset must have at least 2 columns" |

---

## API Response Schema

### Success (200)

```json
{
  "audit_id": "550e8400-e29b-41d4-a716-446655440000",
  "dataset_name": "hiring_data_2024.csv",
  "row_count": 32561,
  "column_count": 15,
  "status": "pending",
  "message": "Dataset uploaded successfully. 32561 rows × 15 columns."
}
```

### Error (400)

```json
{
  "detail": "Unsupported file type: .pdf. Allowed: {'.csv', '.xlsx', '.xls'}"
}
```

---

## Verification

1. Upload a valid CSV file → returns `audit_id`, correct row/column count
2. Upload an Excel file → same success behavior
3. Upload a PDF → 400 error with correct message
4. Upload a file > 100 MB → 400 error
5. Upload a CSV with 5 rows → 400 error (minimum 10 rows)
6. Drag-and-drop works in the frontend
7. Progress bar updates during upload
8. After upload, audit record exists in database with status "pending"
