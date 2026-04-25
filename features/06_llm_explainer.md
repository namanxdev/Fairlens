# Feature 06: LLM Explainer + RAG Context (LangGraph Node 4)

## Overview

The LLM Explainer takes all computed bias metrics from Node 2 and generates a plain-English audit report. It uses RAG (Retrieval-Augmented Generation) to pull relevant regulatory context from an embedded knowledge base of fairness laws and standards.

---

## RAG Knowledge Base

### Source Documents

Create `backend/rag/knowledge_base/` directory with markdown files containing key regulatory text:

| File | Content | Key Sections |
|------|---------|--------------|
| `eu_ai_act.md` | EU AI Act (2024) | Articles 9-15 on high-risk AI systems |
| `eeoc_guidelines.md` | EEOC Uniform Guidelines | 80% / four-fifths rule for adverse impact |
| `ecoa_fair_lending.md` | Equal Credit Opportunity Act | Prohibitions on credit discrimination |
| `nist_ai_rmf.md` | NIST AI RMF 1.0 | MAP/MEASURE/MANAGE/GOVERN functions |
| `iso_24027_bias.md` | ISO/IEC TR 24027:2021 | Bias in AI systems standard |

These are plain-text summaries of the key provisions relevant to bias detection. They do NOT need to be the full legal text — just the actionable sections an AI auditor would cite.

### Embedding & Storage

**File:** `backend/rag/ingest.py`

1. Load each markdown file from `knowledge_base/`
2. Split into chunks (~500 tokens each) using `RecursiveCharacterTextSplitter`
3. Embed using the configured LLM provider's embedding model
4. Store in PostgreSQL using pgvector

**File:** `backend/rag/retriever.py`

1. Given a query (e.g., "disparate impact gender hiring EEOC"), perform similarity search
2. Return top-k (k=5) relevant chunks with source attribution
3. Use `langchain_community.vectorstores.PGVector`

---

## Node 4 Implementation

### `backend/pipeline/explainer.py`

**What it does:**
1. Receives all bias metrics from `state["bias_metrics"]`
2. Constructs a query from the most critical findings (e.g., "gender disparate impact ratio 0.35 hiring")
3. Retrieves relevant regulatory context via RAG
4. Builds a structured prompt with metrics + regulatory context
5. Calls the LLM to generate a markdown audit report
6. Saves the report to the `reports` table
7. Updates audit status to "completed"

**LLM Prompt Structure:**
```
You are FairLens, an AI bias auditor. Generate a structured audit report.

METRICS DATA:
{json.dumps(bias_metrics)}

REGULATORY CONTEXT:
{retrieved_rag_chunks}

Generate a report with these sections:
1. EXECUTIVE SUMMARY (2-3 sentences for C-suite)
2. FINDINGS (one per protected attribute, with severity, stats, and legal context)
3. LEGAL RISK ASSESSMENT (which regulations are violated)
4. REMEDIATION RECOMMENDATIONS (prioritized, actionable steps)

Use markdown formatting. Cite specific regulations and thresholds.
```

---

## Report Structure

The generated markdown report follows this template:

```markdown
# FAIRLENS AUDIT REPORT

**Dataset:** {dataset_name}
**Date:** {date}
**Overall Risk Level:** {CRITICAL|HIGH|MEDIUM|LOW}

---

## Executive Summary

{2-3 sentence summary for non-technical stakeholders}

---

## Finding 1: {Attribute} Bias — {SEVERITY}

- **Attribute:** {protected_attr}
- **Groups:** {group breakdown with positive rates}
- **Disparate Impact Ratio:** {value} (threshold: 0.80)
- **Statistical Significance:** p < {value}
- **Sample Size:** {breakdown}

**Legal Context:** {RAG-retrieved regulatory citations}

**Remediation Priority:** {IMMEDIATE|HIGH|MEDIUM|MONITOR}

---

## Remediation Recommendations

1. {Specific actionable step}
2. {Specific actionable step}
...
```

---

## API Endpoint

### `GET /api/audit/{audit_id}/report`

**File:** `backend/routes/report.py`

Returns the generated report:
```json
{
  "audit_id": "...",
  "report": "# FAIRLENS AUDIT REPORT\n\n...",
  "created_at": "2026-04-25T12:00:00Z"
}
```

---

## Verification

1. After bias detection completes, the explainer generates a coherent markdown report
2. Report includes executive summary, findings per attribute, and remediation steps
3. Report cites specific regulatory standards (EEOC 80% rule, EU AI Act articles)
4. Report is saved to `reports` table
5. RAG retrieval returns relevant regulatory chunks
6. API endpoint returns the full report markdown
