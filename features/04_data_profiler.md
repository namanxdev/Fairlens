# Feature 04: Data Profiler (LangGraph Node 1)

## Overview

First node in the LangGraph pipeline. Takes a raw uploaded dataset, profiles it, and uses an LLM call to classify every column as **protected_attribute**, **feature**, **target**, or **identifier**. Detects proxy variables via correlation analysis.

---

## LangGraph Pipeline State

### `backend/pipeline/state.py`

```python
from typing import TypedDict, Optional, Any

class PipelineState(TypedDict):
    audit_id: str
    file_path: str
    dataset_name: str
    total_rows: Optional[int]
    total_columns: Optional[int]
    protected_attributes: Optional[list[str]]
    features: Optional[list[str]]
    target: Optional[str]
    excluded: Optional[list[str]]
    null_summary: Optional[dict[str, float]]
    proxy_warnings: Optional[list[str]]
    column_details: Optional[list[dict]]
    schema_json: Optional[dict]
    bias_metrics: Optional[list[dict]]
    overall_risk: Optional[str]
    report_markdown: Optional[str]
    remediation_results: Optional[dict]
    status: Optional[str]
    error: Optional[str]
```

---

## LangGraph Graph Definition

### `backend/pipeline/graph.py`

```python
from langgraph.graph import StateGraph, END
from pipeline.state import PipelineState
from pipeline.profiler import profile_data
from pipeline.bias_detector import detect_bias
from pipeline.explainer import explain_findings

def build_audit_pipeline():
    graph = StateGraph(PipelineState)
    graph.add_node("profiler", profile_data)
    graph.add_node("bias_detector", detect_bias)
    graph.add_node("explainer", explain_findings)
    graph.add_edge("profiler", "bias_detector")
    graph.add_edge("bias_detector", "explainer")
    graph.add_edge("explainer", END)
    graph.set_entry_point("profiler")
    return graph.compile()

audit_pipeline = build_audit_pipeline()
```

---

## Node 1 Implementation

### `backend/pipeline/profiler.py`

**What it does:**
1. Loads the CSV/Excel file with pandas
2. Computes per-column stats: dtype, null%, unique count, sample values, mean/std for numerics
3. Runs correlation analysis to find pairs with |r| > 0.5 (proxy detection)
4. Sends column summary to the LLM with a system prompt asking it to classify each column
5. Parses the JSON response and organizes into `protected_attributes`, `features`, `target`, `excluded`
6. Saves the schema JSON to the `audits.schema_json` database column
7. Updates audit status to "profiling" while running

**LLM System Prompt:**
- Classify each column as: `protected_attribute`, `feature`, `target`, or `identifier`
- Protected attributes include: gender/sex, race/ethnicity, age, disability, religion, national origin, marital status
- Target is the outcome column (hired, approved, income, default, etc.) — exactly ONE
- Identifiers are names, IDs, emails — excluded from analysis
- Also flag proxy variables: features highly correlated with protected attributes

**LLM Response format (JSON):**
```json
{
  "columns": [
    {"name": "col_name", "category": "protected_attribute", "reason": "..."}
  ],
  "proxy_warnings": ["zip_code correlates with race (r=0.73)"]
}
```

---

## API: Trigger Audit Pipeline

### `POST /api/audit/{audit_id}/run`

**File:** `backend/routes/audit.py`

- Validates audit exists and is in `pending` or `failed` status
- Constructs initial `PipelineState` from the audit record
- Runs the pipeline as a FastAPI `BackgroundTask`
- Returns immediately with `{"message": "Audit pipeline started"}`

### `GET /api/audit/{audit_id}/status`

Returns current status, risk level, schema JSON, row/column count.

---

## Frontend: Schema Preview Panel

After profiling, the dashboard shows:
1. **Color-coded column chips** — Red=protected, Green=feature, Blue=target, Gray=excluded
2. **Null summary bar chart** — horizontal bars per column
3. **Proxy warning alerts** — yellow banners
4. **Stats overview** — row count, column count, number of protected attributes

---

## Expected Output (Adult Income Dataset)

```json
{
  "total_rows": 32561,
  "total_columns": 15,
  "protected_attributes": ["sex", "race", "age"],
  "features": ["education", "occupation", "workclass", "hours_per_week", "capital_gain", "capital_loss"],
  "target": "income",
  "excluded": ["fnlwgt"],
  "null_summary": {"workclass": 0.0566, "occupation": 0.0566},
  "proxy_warnings": ["relationship correlates with sex (r=0.65)"]
}
```

---

## Verification

1. Upload `adult_income.csv` → profiler detects `sex`, `race`, `age` as protected
2. `income` identified as target
3. Proxy warnings generated for correlated columns
4. Schema JSON stored in database
5. Audit status updates correctly through pipeline
