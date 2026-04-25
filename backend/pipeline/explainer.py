import uuid
from datetime import datetime, timezone
from pipeline.state import PipelineState
from db.connection import async_session
from db.models import Audit, Report
from rag.retriever import retrieve_regulatory_context
from config import settings


async def explain_findings(state: PipelineState) -> PipelineState:
    audit_uuid = uuid.UUID(state["audit_id"])
    bias_metrics = state.get("bias_metrics") or []
    dataset_name = state.get("dataset_name", "Unknown dataset")
    overall_risk = state.get("overall_risk", "NONE")

    async with async_session() as db:
        audit = await db.get(Audit, audit_uuid)
        if audit:
            audit.status = "explaining"
            await db.commit()

    query_parts = []
    for m in bias_metrics:
        if m.get("flag_level") in ("CRITICAL", "HIGH"):
            query_parts.append(f"{m['protected_attr']} disparate impact {m['disparate_impact_ratio']}")
    query = " ".join(query_parts) if query_parts else "fairness bias detection"

    rag_chunks = retrieve_regulatory_context(query, k=3)

    report_md = f"""# FAIRLENS AUDIT REPORT

**Dataset:** {dataset_name}
**Date:** {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
**Overall Risk Level:** {overall_risk}

---

## Executive Summary

"""
    if bias_metrics:
        critical_attrs = [m["protected_attr"] for m in bias_metrics if m["flag_level"] == "CRITICAL"]
        high_attrs = [m["protected_attr"] for m in bias_metrics if m["flag_level"] == "HIGH"]
        summary_parts = []
        if critical_attrs:
            summary_parts.append(f"This dataset exhibits critical bias in {', '.join(critical_attrs)}.")
        if high_attrs:
            summary_parts.append(f"High bias detected in {', '.join(high_attrs)}.")
        if not summary_parts:
            summary_parts.append("Bias levels are within acceptable thresholds.")
        report_md += " ".join(summary_parts) + "\n"
    else:
        report_md += "No protected attributes were identified for bias analysis.\n"

    report_md += "\n---\n\n## Findings\n\n"

    for i, metric in enumerate(bias_metrics, 1):
        attr = metric["protected_attr"]
        flag = metric["flag_level"]
        groups_str = ", ".join([f"{k} ({v:.1%})" for k, v in metric["groups"].items()])
        report_md += f"""### Finding {i}: {attr.title()} Bias — {flag}

- **Attribute:** {attr}
- **Groups:** {groups_str}
- **Disparate Impact Ratio:** {metric['disparate_impact_ratio']} (threshold: 0.80)
- **Demographic Parity Difference:** {metric['demographic_parity_diff']}
- **Statistical Significance:** p = {metric['p_value']:.5f}

**Remediation Priority:** {"IMMEDIATE" if flag == "CRITICAL" else flag}

---

"""

    report_md += "## Regulatory Context\n\n"
    for chunk in rag_chunks:
        report_md += f"> {chunk}\n\n"

    report_md += """## Remediation Recommendations

1. Review the flagged protected attributes for data collection and representation issues.
2. Consider pre-processing techniques such as reweighting or resampling to balance group representation.
3. Investigate proxy variables that may be highly correlated with protected attributes.
4. Apply post-processing threshold adjustments to equalize outcome rates across groups.
5. Re-audit after remediation to verify metrics improve above legal thresholds.
"""

    async with async_session() as db:
        audit = await db.get(Audit, audit_uuid)
        if audit:
            audit.status = "completed"
            audit.completed_at = datetime.now(timezone.utc)
            await db.commit()

        report = Report(
            audit_id=audit_uuid,
            content_md=report_md,
        )
        db.add(report)
        await db.commit()

    return {
        **state,
        "report_markdown": report_md,
        "status": "completed",
    }
