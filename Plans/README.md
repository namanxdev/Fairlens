# FairLens — AI Bias Detection & Remediation Platform

**Ensuring Fairness and Detecting Bias in Automated Decisions**

FairLens is an end-to-end bias auditing platform that lets organizations upload datasets or connect ML models, automatically detect hidden discrimination across protected attributes, and receive actionable remediation — all powered by an agentic LangGraph pipeline with LLM-generated plain-English explanations.

---

## The Problem

Automated decision-making systems (hiring algorithms, loan approvers, healthcare triaging) increasingly determine life-changing outcomes. When these systems learn from historically biased data, they don't just repeat discrimination — they scale and amplify it. Most organizations lack the technical expertise to audit their own systems, and existing tools produce raw statistical outputs that non-technical stakeholders can't act on.

FairLens bridges that gap: technical rigor meets human-readable insight.

---

## What FairLens Does

FairLens operates as a three-stage pipeline: **Ingest → Analyze → Report**.

**1. Ingest** — Users upload a CSV dataset (e.g., hiring records, loan applications, patient data) through the web dashboard. FairLens auto-detects column types, identifies protected attributes (gender, race, age, disability status), distinguishes features from the target/outcome variable, and builds a structured schema.

**2. Analyze** — A multi-node LangGraph agentic pipeline runs statistical fairness tests, computes industry-standard bias metrics, optionally audits a connected ML model's predictions, and flags violations against legal thresholds (the 80% rule, EU AI Act Article 10, EEOC guidelines).

**3. Report** — An LLM synthesizes all findings into a plain-English audit report: what bias was found, how severe it is, which groups are affected, relevant legal/regulatory context (pulled via RAG from a fairness knowledge base), and specific step-by-step remediation recommendations. Users can auto-apply debiasing techniques and compare before/after metrics.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   NEXT.JS FRONTEND                  │
│  Upload Panel │ Bias Heatmap │ Charts │ Report View  │
└────────────────────────┬────────────────────────────┘
                         │ REST API
┌────────────────────────▼────────────────────────────┐
│                  FASTAPI BACKEND                    │
│         File Handling · Auth · Orchestration         │
└────────────────────────┬────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              LANGGRAPH AUDIT PIPELINE               │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐    │
│  │  Data     │──▶│ Bias     │──▶│ Model Audit  │    │
│  │ Profiler  │   │ Detector │   │ (Optional)   │    │
│  └──────────┘   └──────────┘   └──────┬───────┘    │
│                                        │            │
│  ┌──────────────┐   ┌────────────────┐ │            │
│  │ Remediation  │◀──│ LLM Explainer  │◀┘            │
│  │ Engine       │   │ + RAG Context  │              │
│  └──────────────┘   └────────────────┘              │
└─────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────┐
│              POSTGRESQL + PGVECTOR                  │
│     Audit History · User Accounts · RAG Embeddings   │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js, TypeScript, Tailwind CSS, Recharts | Dashboard, visualizations, report viewer |
| Backend | FastAPI, Python 3.11+ | API, file handling, pipeline orchestration |
| AI Pipeline | LangGraph, LangChain | Multi-node agentic audit workflow |
| Bias Computation | Fairlearn, AIF360, pandas, NumPy, SciPy | Statistical fairness metrics |
| LLM Layer | Claude API / OpenAI (BYOK) | Plain-English explanations, report generation |
| RAG | LangChain + pgvector | Regulatory context retrieval (EU AI Act, EEOC, ECOA) |
| Database | PostgreSQL + pgvector | Audit storage, embeddings, user auth |
| Deployment | Docker, Docker Compose | Containerized services |

---

## LangGraph Pipeline — Node-by-Node Breakdown

The audit pipeline is a directed acyclic graph with 5 nodes. Each node receives structured state, performs its task, and passes enriched state to the next node.

### Node 1: Data Profiler

**Input:** Raw CSV file upload.

**What it does:**
- Parses the CSV with pandas and runs basic profiling (row/column count, dtypes, null percentages, unique value counts).
- Uses an LLM call to intelligently classify each column into one of four categories: `protected_attribute` (gender, race, age, disability, etc.), `feature` (education, experience, credit_score), `target` (hired, approved, diagnosed), or `identifier` (name, ID — excluded from analysis).
- Detects edge cases: proxy variables (zip code as a proxy for race), highly correlated columns, low-variance features.
- Outputs a structured schema JSON.

**Output:**
```json
{
  "total_rows": 32561,
  "total_columns": 15,
  "protected_attributes": ["gender", "race", "age_group"],
  "features": ["education", "occupation", "hours_per_week", "capital_gain"],
  "target": "income_above_50k",
  "excluded": ["id", "full_name"],
  "null_summary": {"age_group": 0.02, "occupation": 0.06},
  "proxy_warnings": ["zip_code is highly correlated with race (r=0.73)"]
}
```

### Node 2: Statistical Bias Detector

**Input:** Profiled schema + raw data.

**What it does:**
Computes the following fairness metrics for every protected attribute against the target variable:

**Demographic Parity Difference (DPD)**
Measures whether the positive outcome rate is equal across groups. Formula: `P(Ŷ=1 | group=A) - P(Ŷ=1 | group=B)`. A value of 0 means perfect parity. Threshold: flag if |DPD| > 0.1.

**Disparate Impact Ratio (DIR)**
The ratio of the lowest group's positive outcome rate to the highest group's rate. This is the legal "80% rule" — if the ratio falls below 0.8, it constitutes prima facie evidence of discrimination under US employment law (EEOC Uniform Guidelines). Formula: `min(P(Ŷ=1|group)) / max(P(Ŷ=1|group))`. Threshold: flag if DIR < 0.8.

**Equalized Odds Difference (EOD)**
Measures whether the model's true positive rate and false positive rate are equal across groups. A model can have equal approval rates (demographic parity) but still discriminate if it's more accurate for one group than another. Threshold: flag if |EOD| > 0.1.

**Predictive Parity Difference (PPD)**
Measures whether the precision (positive predictive value) is equal across groups. A flagged loan system might approve the same percentage of men and women, but the women it approves might default at a higher rate — indicating the model uses a lower bar for one group. Threshold: flag if |PPD| > 0.1.

**Theil Index / Generalized Entropy Index**
An information-theoretic measure of inequality in the benefit distribution. Captures both between-group and within-group unfairness. Useful for intersectional analysis (e.g., Black women vs. White men, not just race or gender alone).

**Statistical Significance Tests**
Chi-squared test for categorical outcomes, Mann-Whitney U for continuous outcomes. Ensures flagged disparities aren't just noise from small sample sizes. Only flags with p < 0.05 are reported as significant.

**Output:**
```json
{
  "metrics": [
    {
      "attribute": "gender",
      "groups": {"Male": 0.312, "Female": 0.109},
      "demographic_parity_diff": -0.203,
      "disparate_impact_ratio": 0.349,
      "flag_level": "CRITICAL",
      "chi_squared_p_value": 0.00001,
      "sample_sizes": {"Male": 21790, "Female": 10771}
    },
    {
      "attribute": "race",
      "groups": {"White": 0.264, "Black": 0.120, "Asian": 0.283},
      "demographic_parity_diff": -0.163,
      "disparate_impact_ratio": 0.424,
      "flag_level": "HIGH",
      "chi_squared_p_value": 0.0003
    }
  ]
}
```

### Node 3: Model Audit (Optional)

**Input:** A trained model file (pickle, ONNX, joblib) or a prediction API endpoint + the dataset.

**What it does:**
- Runs the dataset through the model to generate predictions.
- Computes all the same fairness metrics from Node 2, but on model *outputs* instead of raw data.
- Compares data-level bias vs. model-level bias — answers the critical question: "Does the model amplify existing bias, reduce it, or introduce new bias?"
- Runs feature importance analysis (SHAP values) to identify if protected attributes or their proxies are driving predictions.

**Output:** Same metric structure as Node 2, plus a `bias_amplification_score` comparing data vs. model bias, and a SHAP-based feature contribution breakdown.

### Node 4: LLM Explainer + RAG Context

**Input:** All metrics from Nodes 2 and 3 + regulatory knowledge base.

**What it does:**
- Retrieves relevant regulatory context via RAG from an embedded knowledge base containing: EU AI Act (Articles 9, 10, 13-15 on high-risk AI systems), EEOC Uniform Guidelines on Employee Selection Procedures, Equal Credit Opportunity Act (ECOA) and Fair Lending regulations, NIST AI Risk Management Framework (AI RMF 1.0), and ISO/IEC TR 24027:2021 (Bias in AI systems).
- Feeds the metrics JSON + retrieved regulatory context into an LLM prompt.
- Generates a structured, plain-English audit report covering: executive summary (2-3 sentences for C-suite), detailed findings per protected attribute, legal risk assessment with specific regulation citations, severity classification (CRITICAL / HIGH / MEDIUM / LOW), and prioritized remediation recommendations.

**Output:** A structured markdown report (see Expected Outputs section below).

### Node 5: Remediation Engine

**Input:** Original dataset + bias metrics + remediation strategy selection.

**What it does:**
Offers and optionally auto-applies three debiasing strategies:

**Pre-processing (data-level fixes):**
- Resampling — oversample underrepresented groups or undersample overrepresented ones.
- Reweighting — assign instance weights inversely proportional to group frequency × outcome frequency (using Fairlearn's `ExponentiatedGradient`).
- Synthetic data generation — use SMOTE variants to generate synthetic minority samples.

**In-processing (model-level fixes):**
- Constrained optimization — retrain with fairness constraints (e.g., demographic parity constraint via Fairlearn's `ThresholdOptimizer`).
- Adversarial debiasing — add an adversary network that tries to predict the protected attribute from model embeddings; penalize the main model for leaking group information.

**Post-processing (output-level fixes):**
- Threshold adjustment — set group-specific decision thresholds to equalize outcome rates.
- Reject option classification — defer borderline decisions for human review.

After applying remediation, re-runs all Node 2 metrics and produces a before/after comparison.

**Output:**
```json
{
  "strategy_applied": "reweighting",
  "before": {"gender_disparate_impact": 0.349, "gender_dpd": -0.203},
  "after": {"gender_disparate_impact": 0.812, "gender_dpd": -0.042},
  "accuracy_tradeoff": {"before": 0.847, "after": 0.831},
  "recommendation": "Reweighting brought DIR above the 0.8 legal threshold with only 1.6% accuracy loss."
}
```

---

## Expected Outputs & Visualizations

### 1. Bias Heatmap (Primary Dashboard View)

A matrix where rows are protected attributes (gender, race, age_group) and columns are fairness metrics (DPD, DIR, EOD, PPD). Each cell is color-coded:
- **Green** — metric within acceptable range, no action needed.
- **Yellow** — metric approaching threshold, warrants monitoring.
- **Red** — metric violates threshold, requires immediate remediation.

Clicking any red cell drills down into the detailed breakdown for that attribute-metric pair.

### 2. Group Distribution Bar Charts

Side-by-side bar charts showing outcome rates (e.g., "% Hired") broken down by each protected attribute group. These instantly visualize disparities — if the "Female" bar is a third of the "Male" bar's height, the problem is obvious even to non-technical stakeholders.

### 3. Intersectional Analysis Matrix

A heatmap or bubble chart showing outcome rates at the intersection of two protected attributes (e.g., Race × Gender). This catches hidden bias — overall gender parity might mask severe disparities for Black women specifically.

### 4. Before/After Remediation Comparison

Dual bar charts or a toggle-able overlay showing metric values before and after debiasing. Includes an accuracy tradeoff indicator (small accuracy loss is expected and acceptable; large loss suggests the original model was relying heavily on discriminatory features).

### 5. Feature Importance Waterfall (SHAP)

A waterfall or beeswarm plot showing which features most influence the model's decisions. Protected attributes or their proxies appearing near the top is a red flag — the model is directly or indirectly using group membership to make decisions.

### 6. Plain-English Audit Report

A downloadable PDF/markdown report structured as follows:

```
FAIRLENS AUDIT REPORT
Dataset: hiring_data_2024.csv
Date: 2026-04-20
Overall Risk Level: CRITICAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

EXECUTIVE SUMMARY
This dataset exhibits severe gender-based bias in hiring outcomes.
Female applicants are approved at 10.9% compared to 31.2% for male
applicants — a disparate impact ratio of 0.35, well below the 0.8
legal threshold established by EEOC Uniform Guidelines.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINDING 1: Gender Bias — CRITICAL
Attribute: gender
Groups: Male (31.2% positive), Female (10.9% positive)
Disparate Impact Ratio: 0.349 (threshold: 0.80)
Statistical Significance: p < 0.00001 (Chi-squared)
Sample Size: Male=21,790 | Female=10,771

Legal Context: Under EEOC Uniform Guidelines Section 4D, a
selection rate for any group below 80% of the highest group
constitutes adverse impact. This dataset's 34.9% ratio represents
a severe violation. Under EU AI Act Article 10(2), training data
for high-risk AI systems must be "relevant, sufficiently
representative, and to the best extent possible, free of errors
and complete."

Remediation Priority: IMMEDIATE
Recommended Actions:
  1. Apply reweighting to equalize effective group representation.
  2. Audit feature "hours_per_week" — it correlates with gender
     at r=0.34 and may act as a proxy variable.
  3. Consider removing or decorrelating "marital_status" as it
     shows 0.41 correlation with gender.
  4. After remediation, re-audit to confirm DIR > 0.8.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINDING 2: Racial Bias — HIGH
[...similar structure...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

REMEDIATION RESULTS (if applied)
Strategy: Reweighting (Fairlearn ExponentiatedGradient)
Gender DIR: 0.349 → 0.812 ✓ (now above 0.8 threshold)
Accuracy tradeoff: 84.7% → 83.1% (-1.6%)
Verdict: Acceptable tradeoff. Bias mitigated with minimal
performance loss.
```

### 7. Audit History Timeline

A timeline view showing all past audits for an organization, with trend lines for key metrics. Tracks whether bias is improving or degrading over successive data refreshes or model retrains.

---

## How Fairness Checking Works — The Math

For anyone evaluating this system, here's how each core metric is computed and why it matters:

**Demographic Parity** asks: "Do all groups receive positive outcomes at equal rates?" If 30% of men get hired but only 10% of women get hired, that's a 20-percentage-point gap. This is the simplest and most intuitive metric, but it has a limitation — it doesn't account for legitimate differences in qualifications. Use case: initial screening, regulatory compliance checks.

**Disparate Impact (80% Rule)** asks: "Is the lowest group's rate at least 80% of the highest group's rate?" This is a legal standard, not just a statistical one. A ratio of 0.35 (as in the gender example above) means women are hired at only 35% the rate of men — far below the 80% legal threshold. Use case: legal risk assessment, EEOC compliance.

**Equalized Odds** asks: "Does the model make errors at equal rates across groups?" Even if approval rates are equal, a model might achieve that by being more accurate for one group (correctly identifying qualified men) while being less accurate for another (randomly approving/rejecting women). Use case: model-level fairness, ensuring equal error distribution.

**Calibration / Predictive Parity** asks: "When the model says 'yes,' does that mean the same thing for all groups?" If 90% of approved men succeed but only 60% of approved women succeed, the model is applying different standards. Use case: outcome-level fairness, ensuring predictions carry equal meaning across groups.

**Intersectional Analysis** asks: "Are there hidden disparities at group intersections?" Overall gender and race metrics might look acceptable, but Black women or elderly Asian applicants might face severe bias that single-attribute analysis misses. FairLens computes metrics at all pairwise intersections of protected attributes.

---

## Project Structure

```
fairlens/
├── frontend/                    # Next.js dashboard
│   ├── app/
│   │   ├── page.tsx             # Landing / upload page
│   │   ├── dashboard/
│   │   │   ├── page.tsx         # Main audit dashboard
│   │   │   ├── heatmap.tsx      # Bias heatmap component
│   │   │   ├── charts.tsx       # Distribution bar charts
│   │   │   └── report.tsx       # LLM report viewer
│   │   └── history/
│   │       └── page.tsx         # Past audits timeline
│   ├── components/
│   │   ├── FileUpload.tsx
│   │   ├── MetricCard.tsx
│   │   ├── BeforeAfter.tsx
│   │   └── SHAPWaterfall.tsx
│   └── lib/
│       └── api.ts               # FastAPI client
│
├── backend/                     # FastAPI server
│   ├── main.py                  # App entry, CORS, routes
│   ├── routes/
│   │   ├── upload.py            # File upload endpoint
│   │   ├── audit.py             # Trigger audit pipeline
│   │   ├── report.py            # Fetch/download reports
│   │   └── remediate.py         # Apply debiasing
│   ├── pipeline/                # LangGraph nodes
│   │   ├── graph.py             # Pipeline DAG definition
│   │   ├── profiler.py          # Node 1: Data profiler
│   │   ├── bias_detector.py     # Node 2: Statistical tests
│   │   ├── model_auditor.py     # Node 3: Model audit
│   │   ├── explainer.py         # Node 4: LLM + RAG
│   │   └── remediator.py        # Node 5: Debiasing
│   ├── metrics/
│   │   ├── fairness.py          # Fairlearn/AIF360 wrappers
│   │   ├── statistical.py       # Chi-squared, Mann-Whitney
│   │   └── intersectional.py    # Cross-attribute analysis
│   ├── rag/
│   │   ├── ingest.py            # Embed regulatory docs
│   │   └── retriever.py         # pgvector retrieval
│   └── db/
│       ├── models.py            # SQLAlchemy models
│       └── connection.py        # PostgreSQL connection
│
├── knowledge_base/              # RAG source documents
│   ├── eu_ai_act.md
│   ├── eeoc_guidelines.md
│   ├── ecoa_fair_lending.md
│   ├── nist_ai_rmf.md
│   └── iso_24027_bias.md
│
├── sample_data/                 # Demo datasets
│   ├── adult_income.csv         # UCI Adult dataset
│   ├── german_credit.csv        # UCI German Credit
│   └── compas_recidivism.csv    # ProPublica COMPAS
│
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── requirements.txt
└── README.md
```

---

## Database Schema

```sql
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    org_name      VARCHAR(255),
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE audits (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID REFERENCES users(id),
    dataset_name  VARCHAR(255) NOT NULL,
    row_count     INTEGER,
    column_count  INTEGER,
    status        VARCHAR(50) DEFAULT 'pending',
    overall_risk  VARCHAR(20),
    created_at    TIMESTAMP DEFAULT NOW(),
    completed_at  TIMESTAMP
);

CREATE TABLE audit_results (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id          UUID REFERENCES audits(id),
    protected_attr    VARCHAR(100) NOT NULL,
    group_name        VARCHAR(100) NOT NULL,
    positive_rate     FLOAT,
    demographic_parity_diff  FLOAT,
    disparate_impact_ratio   FLOAT,
    equalized_odds_diff      FLOAT,
    predictive_parity_diff   FLOAT,
    theil_index              FLOAT,
    p_value                  FLOAT,
    sample_size              INTEGER,
    flag_level               VARCHAR(20),
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE TABLE remediation_logs (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id       UUID REFERENCES audits(id),
    strategy       VARCHAR(100) NOT NULL,
    metric_before  JSONB,
    metric_after   JSONB,
    accuracy_before FLOAT,
    accuracy_after  FLOAT,
    created_at     TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reports (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id    UUID REFERENCES audits(id),
    content_md  TEXT NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload CSV dataset, returns `audit_id` |
| POST | `/api/audit/{audit_id}/run` | Trigger the LangGraph pipeline |
| GET | `/api/audit/{audit_id}/status` | Poll pipeline progress (node-by-node) |
| GET | `/api/audit/{audit_id}/results` | Fetch computed metrics |
| GET | `/api/audit/{audit_id}/report` | Fetch LLM-generated report |
| POST | `/api/audit/{audit_id}/remediate` | Apply debiasing strategy |
| GET | `/api/audit/{audit_id}/compare` | Before/after metrics comparison |
| GET | `/api/audits` | List all audits for authenticated user |
| POST | `/api/upload-model` | Upload model file for model audit |

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/namanxdev/fairlens.git
cd fairlens

# Set environment variables
cp .env.example .env
# Add your LLM API key (Claude/OpenAI), PostgreSQL credentials

# Start with Docker
docker-compose up --build

# Frontend runs on http://localhost:3000
# Backend runs on http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## Demo Walkthrough

1. Open `http://localhost:3000` and upload `sample_data/adult_income.csv` (UCI Adult Income dataset — 32K rows, predicts whether income exceeds $50K).
2. FairLens auto-profiles the dataset: detects `sex` and `race` as protected attributes, `income` as the target variable.
3. The pipeline runs in ~15 seconds. The bias heatmap lights up: `sex` shows a CRITICAL flag (DIR = 0.35), `race` shows HIGH (DIR = 0.42).
4. Click the `sex` row to see the distribution chart — male positive rate is 3x the female rate.
5. Read the LLM-generated report: it explains the disparity in plain English, cites the EEOC 80% rule, and recommends reweighting + proxy variable investigation.
6. Click "Auto-Remediate" → select "Reweighting" → the system re-runs metrics. Gender DIR jumps from 0.35 to 0.81 (above the 0.8 legal threshold) with only 1.6% accuracy loss.
7. Download the full audit report as PDF.

---

## Sample Datasets for Testing

| Dataset | Source | Rows | Known Bias | Use Case |
|---------|--------|------|-----------|----------|
| Adult Income | UCI ML Repository | 32,561 | Gender, Race | Income prediction / hiring |
| German Credit | UCI ML Repository | 1,000 | Age, Gender | Credit scoring / lending |
| COMPAS Recidivism | ProPublica | 7,214 | Race | Criminal justice risk scoring |
| Bank Marketing | UCI ML Repository | 45,211 | Age, Marital Status | Marketing / customer targeting |

---

## Regulatory Framework Coverage

FairLens maps its findings against these regulatory standards (stored in the RAG knowledge base and cited in reports):

- **EU AI Act (2024)** — Articles 9-15 on high-risk AI system requirements, data governance, transparency.
- **EEOC Uniform Guidelines (US)** — The 80% / four-fifths rule for adverse impact in employment.
- **Equal Credit Opportunity Act (US)** — Prohibits discrimination in credit decisions based on race, color, religion, national origin, sex, marital status, age.
- **NIST AI RMF 1.0** — Risk management framework for AI systems, MAP/MEASURE/MANAGE/GOVERN functions.
- **ISO/IEC TR 24027:2021** — International standard on bias in AI systems and AI-aided decision making.

---

## Roadmap

- [ ] Core pipeline (Nodes 1-2-4): data profiling, bias detection, LLM reports
- [ ] Frontend dashboard with heatmap and distribution charts
- [ ] Node 5: Remediation engine with before/after comparison
- [ ] Node 3: Model audit with SHAP integration
- [ ] RAG knowledge base with regulatory documents
- [ ] Intersectional analysis module
- [ ] PDF report export
- [ ] Auth + multi-tenant audit history
- [ ] CI/CD pipeline with automated fairness regression tests
- [ ] API mode for integration into MLOps pipelines (pre-deployment gate)

---

## License

MIT

---

*Built for hackathon — designed for production.*
