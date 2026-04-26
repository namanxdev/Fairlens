"""
llm_context.py — turns audit metrics into LLM-ready context strings.
"""

from __future__ import annotations

import json
from typing import Any


def _title(value: str | None) -> str:
    return str(value or "custom").replace("_", " ").title()


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "unknown"


def _ratio(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "unknown"


def _best_and_worst(group_rows: dict) -> tuple[tuple[str, dict] | None, tuple[str, dict] | None]:
    usable = [
        (name, row)
        for name, row in (group_rows or {}).items()
        if row.get("approval_rate") is not None
    ]
    if not usable:
        return None, None
    worst = min(usable, key=lambda item: item[1]["approval_rate"])
    best = max(usable, key=lambda item: item[1]["approval_rate"])
    return worst, best


def build_audit_context(audit_result: dict, dashboard_stats: dict) -> str:
    """
    Takes get_audit() + compute_group_stats() output and returns plain-English
    context to prepend to every LLM system prompt.
    """
    domain = _title(audit_result.get("domain"))
    target_col = audit_result.get("target_col", "target")
    audit_sensitive = audit_result.get("sensitive_col")
    by_attribute = (dashboard_stats or {}).get("by_attribute") or {}
    sensitive_cols = list(by_attribute.keys())
    if audit_sensitive and audit_sensitive not in sensitive_cols:
        sensitive_cols.insert(0, audit_sensitive)

    lines = [
        f"FAIRNESS AUDIT CONTEXT - {domain} Dataset",
        f"Target: {target_col} | Sensitive: {', '.join(sensitive_cols) or audit_sensitive or 'unknown'}",
        "",
        "BIAS FINDINGS:",
    ]

    if by_attribute:
        di_ratios = (dashboard_stats or {}).get("di_ratios") or {}
        legal_flags = (dashboard_stats or {}).get("legal_flags") or {}
        for attribute, group_rows in by_attribute.items():
            worst, best = _best_and_worst(group_rows)
            if not worst or not best:
                continue
            worst_name, worst_row = worst
            best_name, best_row = best
            status = legal_flags.get(attribute, "UNKNOWN")
            verb = "FAILS" if status == "FAIL" else "PASSES" if status == "PASS" else "UNKNOWN"
            lines.append(
                "- "
                f"{_title(attribute)}: {worst_name} approval rate {_pct(worst_row.get('approval_rate'))} "
                f"vs {best_name} {_pct(best_row.get('approval_rate'))} "
                f"(DI ratio: {_ratio(di_ratios.get(attribute))}) - {verb} 80% rule"
            )
    else:
        lines.append("- No multi-attribute dashboard stats are available yet.")

    lines.extend(["", "MODEL COMPARISON:"])
    for result in audit_result.get("results", []):
        pass_fail = "PASSES" if result.get("legal_pass") else "FAILS"
        lines.append(
            "- "
            f"{result.get('model', 'Unknown model')}: accuracy {_ratio(result.get('accuracy'))}, "
            f"DI ratio {_ratio(result.get('disparate_impact_ratio'))} - {pass_fail} 80% rule"
        )

    feature_cols = audit_result.get("feature_cols") or []
    lines.extend([
        "",
        "CANDIDATE COMPARISON INSTRUCTIONS:",
        "When comparing candidates, base your analysis on merit features only:",
        f"{feature_cols}",
        f"Never use {', '.join(sensitive_cols) or 'protected attributes'} as deciding factors.",
        "Prefer the threshold-calibrated model when explaining the fairer decision.",
        "If the baseline and debiased decisions differ, explain that the baseline may have reflected historical bias.",
    ])
    return "\n".join(lines)


def build_compare_prompt(
    audit_context: str,
    candidate_a: dict,
    candidate_b: dict,
    candidate_a_scores: dict,
    candidate_b_scores: dict,
    fairer_decision: dict,
    bias_impact: dict,
) -> str:
    """
    Build a complete ready-to-send prompt for the frontend's LLM endpoint.
    """
    payload = {
        "candidate_a_features": candidate_a,
        "candidate_b_features": candidate_b,
        "candidate_a_model_scores": candidate_a_scores,
        "candidate_b_model_scores": candidate_b_scores,
        "fairer_decision": fairer_decision,
        "bias_impact": bias_impact,
    }
    return (
        f"{audit_context}\n\n"
        "USER TASK:\n"
        "Compare Candidate A and Candidate B for this audit. "
        "Use the debiased model results as the primary recommendation, "
        "explain whether the baseline model appears biased, and state which "
        "candidate is stronger based on merit features only.\n\n"
        "STRUCTURED COMPARISON DATA:\n"
        f"{json.dumps(payload, indent=2, default=str)}"
    )
