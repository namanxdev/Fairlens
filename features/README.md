# FairLens — Feature Specifications

This directory contains end-to-end feature specifications for the FairLens AI Bias Detection & Remediation Platform. Each `.md` file describes a single feature from frontend to backend, including data models, API contracts, UI behavior, and implementation details.

## Feature Index

| # | Feature File | Description | Dependencies |
|---|-------------|-------------|--------------|
| 1 | [01_project_setup.md](./01_project_setup.md) | Monorepo scaffolding, dependencies, env config, Docker | None |
| 2 | [02_database_and_models.md](./02_database_and_models.md) | PostgreSQL schema, SQLAlchemy models, migrations | Feature 1 |
| 3 | [03_dataset_upload.md](./03_dataset_upload.md) | CSV/Excel upload, validation, storage, upload UI | Feature 1, 2 |
| 4 | [04_data_profiler.md](./04_data_profiler.md) | LangGraph Node 1 — auto-detect columns, schema generation | Feature 3 |
| 5 | [05_bias_detection.md](./05_bias_detection.md) | LangGraph Node 2 — statistical fairness metrics engine | Feature 4 |
| 6 | [06_llm_explainer.md](./06_llm_explainer.md) | LangGraph Node 4 — LLM report generation with RAG | Feature 5 |
| 7 | [07_dashboard_ui.md](./07_dashboard_ui.md) | Bias heatmap, distribution charts, metric cards | Feature 5 |
| 8 | [08_remediation_engine.md](./08_remediation_engine.md) | LangGraph Node 5 — debiasing strategies, before/after | Feature 5, 6 |
| 9 | [09_audit_report.md](./09_audit_report.md) | Report viewer, PDF export, download | Feature 6 |
| 10 | [10_audit_history.md](./10_audit_history.md) | Timeline view, past audits, trend tracking | Feature 2, 7 |
| 11 | [11_sample_datasets.md](./11_sample_datasets.md) | Bundled demo datasets from Kaggle/UCI, one-click load | Feature 3 |
| 12 | [12_intersectional_analysis.md](./12_intersectional_analysis.md) | Cross-attribute bias analysis, bubble charts | Feature 5 |

## Build Order

```
Feature 1  →  Feature 2  →  Feature 3  →  Feature 4  →  Feature 5
                                                           ↓
Feature 11 ─────────────────────────────────────→  Feature 7
                                                           ↓
                                          Feature 6  →  Feature 9
                                                           ↓
                                          Feature 8  →  Feature 10
                                                           ↓
                                                    Feature 12
```

## Conventions

- **Backend**: FastAPI (Python 3.12+), async endpoints, Pydantic v2 schemas
- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS v4, Recharts
- **AI Pipeline**: LangGraph for orchestration, LangChain for LLM/RAG
- **Database**: PostgreSQL with pgvector (via SQLAlchemy async)
- **Data Source**: CSV and Excel files (uploaded or bundled from Kaggle/UCI)
- **LLM**: Claude API (primary), OpenAI-compatible fallback via BYOK
