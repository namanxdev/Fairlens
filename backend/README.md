# FairLens Backend

FastAPI backend for FairLens, an AI bias detection and remediation platform. The backend is intended to own dataset ingestion, audit orchestration, fairness metric computation, regulatory-context retrieval, LLM report generation, and remediation workflows.

## Current Status

This package is still scaffold-level. `features/` at the repository root contains the implementation specs, but most backend modules described there are not present yet.

Implemented:

- Python project metadata in `pyproject.toml`
- Basic `main.py` placeholder
- FastAPI and Uvicorn dependencies

Not implemented yet:

- FastAPI `app` instance and `/api/health`
- Upload, audit, report, remediation, and sample dataset routes
- SQLAlchemy async models, database connection, and Alembic migrations
- LangGraph audit pipeline
- Fairness metrics, RAG, and LLM explainer modules
- Tests and Docker files

## Target Architecture

```text
backend/
  main.py
  config.py
  routes/
  db/
  schemas/
  pipeline/
  metrics/
  rag/
  scripts/
  tests/
```

Core runtime stack:

- Python 3.12+
- FastAPI with async endpoints
- Pydantic v2 and `pydantic-settings`
- SQLAlchemy 2 async with PostgreSQL and pgvector
- Alembic migrations
- pandas, NumPy, SciPy, Fairlearn/AIF360 for metrics
- LangGraph/LangChain for pipeline orchestration and report generation

## Development

Install dependencies:

```bash
uv sync
```

Run the backend:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected API once Feature 01 is implemented:

```text
GET /api/health
POST /api/upload
POST /api/audit/{audit_id}/run
GET /api/audit/{audit_id}/status
GET /api/audit/{audit_id}/results
GET /api/audit/{audit_id}/report
POST /api/audit/{audit_id}/remediate
GET /api/audits
```

## Implementation Notes

- Treat `features/*.md` as product specs, not verified implementation.
- Keep uploaded files out of Git and validate file type, size, parseability, row count, and column count before creating an audit.
- Do not run long audit/LLM work directly inside request handlers; use FastAPI background tasks only for the prototype and move to a real queue before production.
- Use Alembic migrations instead of relying on `Base.metadata.create_all` outside local prototypes.
- Return stable response schemas from `schemas/` and keep API contracts aligned with the frontend client.
