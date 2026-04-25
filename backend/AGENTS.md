# Backend Agent Guide

## Scope

These instructions apply to `backend/`. Follow the feature specs in `../features/`, but verify contracts against real code before editing because the specs are ahead of the implementation.

## Architecture Rules

- Use FastAPI with async route handlers.
- Keep route handlers thin: validate input, call service/pipeline code, return typed schemas.
- Place API routers in `routes/` and register them from `main.py`.
- Keep database access in `db/` or narrowly scoped repository/service helpers, not inside metric functions.
- Use Pydantic v2 models in `schemas/` for request and response contracts.
- Use SQLAlchemy 2 async sessions from a single `db/connection.py`.
- Use Alembic migrations for schema changes; do not rely on `create_all` except throwaway local prototypes.

## API Conventions

- Prefix application endpoints with `/api`.
- Return JSON objects with stable keys; avoid changing frontend-facing response shapes without updating `frontend/lib/api.ts`.
- Raise `HTTPException` only at API boundaries. Internal code should raise typed domain errors or return explicit result objects.
- Do not expose local file paths, secrets, raw stack traces, or provider errors to users.
- For paginated endpoints, use `page`, `per_page`, `total`, and an array key named after the resource.

## Upload And Data Safety

- Validate extension, MIME/type intent, size, parseability, row count, and column count before creating audit records.
- Generate server-side filenames with UUIDs; never trust uploaded filenames for storage paths.
- Store uploads in a gitignored directory.
- Avoid loading very large files twice in memory. Prefer streaming write, then bounded parsing/profiling.
- Delete uploaded files if validation or audit creation fails.

## Pipeline Rules

- The LangGraph state must remain serializable and small. Store file paths and IDs, not whole DataFrames.
- Keep fairness metric functions pure where possible: inputs in, values out, no database writes.
- Pipeline nodes may update audit status, but the status transitions must be consistent: `pending`, `profiling`, `analyzing`, `explaining`, `remediating`, `completed`, `failed`.
- LLM output must be parsed defensively. Validate JSON from model calls before saving it.
- Regulatory/RAG content is guidance, not legal advice. Keep report wording factual and avoid definitive legal conclusions.

## Quality Bar

- Add tests for every metric function and API route that changes behavior.
- Use representative small fixtures for CSV upload, binary target mapping, missing values, and small group sizes.
- Keep statistical thresholds centralized so dashboard, reports, and backend classification stay aligned.
- Prefer deterministic code for metric computation; isolate non-deterministic LLM calls behind interfaces that can be mocked.

## Commands

```bash
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
uv run pytest
uv run ruff check .
uv run mypy .
```

Run only commands that exist in the project configuration. If a tool is not configured yet, either add the config intentionally or state that verification is not available.
