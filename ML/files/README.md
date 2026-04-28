# AI Fairness Auditor - Universal ML API

Run from this directory:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Routes

| Method | Route | What it does |
|--------|-------|--------------|
| GET | / | Health check |
| POST | /upload | Upload CSV, train models, save audit session |
| GET | /audit | Current audit metrics |
| GET | /schema | Current feature/target/sensitive schema |
| POST | /predict | Single applicant prediction from all 3 models |
| GET | /status | Current in-memory model status |
| POST | /dashboard-stats | Multi-attribute dashboard breakdowns |
| GET | /llm-context | LLM-ready audit context string |
| POST | /compare | Compare two candidates and return an LLM-ready prompt |
| GET | /audits | List saved audits for the current user |
| GET | /audits/{audit_id} | Load saved audit metrics only |
| POST | /audits/{audit_id}/load | Restore saved models into memory |
| DELETE | /audits/{audit_id} | Delete a saved audit |
| GET | /export/report/{audit_id} | Download full audit report JSON |
| GET | /export/csv/{audit_id} | Download debiased prediction CSV for current in-memory audit |

## Upload

Send `multipart/form-data`:

- `file`: CSV file
- `target_col`: outcome column, such as `hired` or `loan_approved`
- `sensitive_col`: protected attribute, such as `gender`, `age`, or `ethnicity`
- `domain`: optional label, such as `jobs`, `banking`, `healthcare`, or `custom`

Optional headers:

- `Authorization: Bearer <user_id>`
- `X-User-Id: <user_id>`

If neither header is provided, audits are stored under `anonymous`.

## Dashboard Stats

```json
{
  "sensitive_cols": ["gender", "age", "ethnicity"]
}
```

Returns per-attribute approval rates, intersectional stats for the first two
attributes, DI ratios, and 80% rule pass/fail flags.

## Compare

Each candidate must include all feature columns from `/schema` plus
`sensitive_value` or the current sensitive column name.

```json
{
  "candidate_a": {
    "years_experience": 5,
    "gpa": 3.7,
    "sensitive_value": "Female"
  },
  "candidate_b": {
    "years_experience": 4,
    "gpa": 3.8,
    "sensitive_value": "Male"
  }
}
```

The response includes model scores, the threshold-calibrated recommendation,
bias impact checks, and `llm_prompt`, which is ready to send to the frontend LLM endpoint.

## Persistence Notes

SQLite is used by default at `fairness_audits.db` in this directory. To use
PostgreSQL later, set `FAIRNESS_DATABASE_URL`.

Only model objects, scaler/encoders, feature names, and audit metrics are saved.
Uploaded raw rows stay in memory only and are not pickled into the database.
