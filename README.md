# FairLens

FairLens is an AI bias detection and remediation platform for auditing tabular datasets and model decisions. Users upload a CSV or Excel dataset, FairLens profiles the data, computes fairness metrics across protected attributes, generates a plain-English audit report, and can compare remediation strategies.

## Repository Status

This repository is currently in scaffold/specification state.

- `features/` contains detailed feature specifications.
- `backend/` has a minimal Python project with FastAPI dependencies but the API is not implemented yet.
- `frontend/` is a freshly scaffolded Next.js app and still shows the starter page.
- `Plans/README.md` contains a broader product plan, but it has encoding artifacts and should be treated as draft material.

## Planned Stack

- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS v4
- UI libraries: shadcn/ui, Aceternity UI, HeroUI, Magic UI
- Charts: Recharts plus custom heatmaps where needed
- Backend: FastAPI, Pydantic v2, SQLAlchemy async, Alembic
- Data and metrics: pandas, NumPy, SciPy, Fairlearn/AIF360
- Pipeline: LangGraph and LangChain
- Database: PostgreSQL with pgvector
- LLM/RAG: Claude-first report generation with OpenAI-compatible fallback

## Target Workflow

1. Upload a CSV or Excel dataset.
2. Validate the file and create an audit record.
3. Profile columns and identify protected attributes, features, target, identifiers, and proxy warnings.
4. Compute fairness metrics such as demographic parity difference, disparate impact ratio, equalized odds, predictive parity, Theil index, and statistical significance.
5. Generate an LLM-backed audit report with regulatory context.
6. Display results in a dashboard with heatmaps, charts, metric cards, and audit history.
7. Apply remediation strategies and compare before/after metrics.

## Project Layout

```text
FairLens/
  backend/      FastAPI backend package
  frontend/     Next.js frontend application
  features/     Feature-by-feature implementation specs
  Plans/        Product plan draft
```

## Local Development

Backend:

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Expected local URLs once Feature 01 is implemented:

- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`

## Implementation Notes

- Build Feature 01 before implementing later specs; most later features assume routes, config, database connection, and shared directories already exist.
- Keep API contracts centralized and update frontend clients whenever backend response shapes change.
- Do not treat LLM output as trusted data. Validate generated JSON and keep metric computation deterministic.
- Use real migrations for database schema changes.
- Add tests for metric computation, upload validation, API contracts, and pipeline status transitions.

## Key Risks To Fix Before Real Implementation

- Backend and frontend are not yet aligned with the feature specs.
- Required dependencies from the specs are not installed.
- The component libraries mentioned for the frontend are not installed yet.
- Some existing planning/spec markdown contains encoding corruption.
- Long-running audit work needs a production queue eventually; FastAPI background tasks are only acceptable for a prototype.
