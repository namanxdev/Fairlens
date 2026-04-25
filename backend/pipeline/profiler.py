import json
import os
import uuid
import pandas as pd
from pipeline.state import PipelineState
from db.connection import async_session
from db.models import Audit
from config import settings


async def profile_data(state: PipelineState) -> PipelineState:
    file_path = state["file_path"]
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        state["error"] = f"Failed to load dataset: {str(e)}"
        return state

    total_rows = len(df)
    total_columns = len(df.columns)
    null_summary = {col: round(df[col].isna().mean(), 4) for col in df.columns}
    
    column_details = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        unique_count = df[col].nunique(dropna=False)
        sample_values = df[col].dropna().head(5).tolist()
        detail = {
            "name": col,
            "dtype": dtype,
            "null_pct": round(null_summary[col], 4),
            "unique_count": int(unique_count),
            "sample_values": [str(v) for v in sample_values],
        }
        if pd.api.types.is_numeric_dtype(df[col]):
            detail["mean"] = float(df[col].mean()) if not df[col].isna().all() else None
            detail["std"] = float(df[col].std()) if not df[col].isna().all() else None
        column_details.append(detail)

    # Correlation analysis for numeric columns
    proxy_warnings = []
    numeric_df = df.select_dtypes(include=["number"])
    if len(numeric_df.columns) > 1:
        corr = numeric_df.corr()
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                col_i = corr.columns[i]
                col_j = corr.columns[j]
                r = corr.iloc[i, j]
                if abs(r) > 0.7:
                    proxy_warnings.append(f"{col_i} is highly correlated with {col_j} (r={r:.2f})")

    # Heuristic classification without LLM for now
    protected_keywords = ["sex", "gender", "race", "ethnicity", "age", "disability", "religion", "marital", "national"]
    target_keywords = ["income", "hired", "approved", "default", "target", "outcome", "label", "class", "result", "flag"]
    id_keywords = ["id", "name", "email", "phone", "ssn", "uuid"]

    protected_attributes = []
    features = []
    target = None
    excluded = []

    for col in df.columns:
        col_lower = col.lower().replace(" ", "_")
        if any(kw in col_lower for kw in id_keywords):
            excluded.append(col)
        elif any(kw in col_lower for kw in protected_keywords):
            protected_attributes.append(col)
        elif any(kw in col_lower for kw in target_keywords):
            if target is None:
                target = col
            else:
                features.append(col)
        else:
            features.append(col)

    if target is None:
        # fallback: use last column as target
        target = df.columns[-1]
        if target in features:
            features.remove(target)
        if target in excluded:
            excluded.remove(target)

    schema_json = {
        "total_rows": total_rows,
        "total_columns": total_columns,
        "protected_attributes": protected_attributes,
        "features": features,
        "target": target,
        "excluded": excluded,
        "null_summary": null_summary,
        "proxy_warnings": proxy_warnings,
        "column_details": column_details,
    }

    # Update DB
    async with async_session() as db:
        audit = await db.get(Audit, uuid.UUID(state["audit_id"]))
        if audit:
            audit.status = "profiling"
            audit.schema_json = schema_json
            audit.row_count = total_rows
            audit.column_count = total_columns
            await db.commit()

    return {
        **state,
        "total_rows": total_rows,
        "total_columns": total_columns,
        "protected_attributes": protected_attributes,
        "features": features,
        "target": target,
        "excluded": excluded,
        "null_summary": null_summary,
        "proxy_warnings": proxy_warnings,
        "column_details": column_details,
        "schema_json": schema_json,
        "status": "profiling",
    }
