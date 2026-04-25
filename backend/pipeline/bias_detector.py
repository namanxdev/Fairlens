import os
import uuid
import pandas as pd
from pipeline.state import PipelineState
from db.connection import async_session
from db.models import Audit, AuditResult
from metrics.fairness import (
    compute_positive_rates,
    compute_demographic_parity,
    compute_disparate_impact,
    compute_equalized_odds,
    compute_predictive_parity,
    compute_theil_index,
    classify_flag,
)
from metrics.statistical import chi_squared_test


def _binarize_target(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    df = df.copy()
    if pd.api.types.is_numeric_dtype(df[target_col]):
        median = df[target_col].median()
        df[target_col] = (df[target_col] > median).astype(int)
    else:
        unique_vals = df[target_col].dropna().unique()
        if len(unique_vals) == 2:
            pos = unique_vals[0]
            df[target_col] = (df[target_col] == pos).astype(int)
        else:
            mode_val = df[target_col].mode()[0]
            df[target_col] = (df[target_col] == mode_val).astype(int)
    return df


async def detect_bias(state: PipelineState) -> PipelineState:
    file_path = state["file_path"]
    protected_attrs = state.get("protected_attributes") or []
    target = state.get("target")

    if not protected_attrs or not target:
        state["error"] = "Missing protected attributes or target column"
        return state

    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        state["error"] = f"Failed to load dataset: {str(e)}"
        return state

    df = _binarize_target(df, target)
    bias_metrics = []
    overall_risk = "NONE"

    for attr in protected_attrs:
        if attr not in df.columns:
            continue
        df_clean = df[[attr, target]].dropna()
        if len(df_clean) < 10:
            continue

        rates = compute_positive_rates(df_clean, attr, target)
        dpd = compute_demographic_parity(df_clean, attr, target)
        dir_val = compute_disparate_impact(df_clean, attr, target)
        eod = compute_equalized_odds(df_clean, attr, target)
        ppd = compute_predictive_parity(df_clean, attr, target)
        theil = compute_theil_index(df_clean, attr, target)
        p_val = chi_squared_test(df_clean, attr, target)

        flag = classify_flag(dir_val, dpd, p_val)

        metric = {
            "protected_attr": attr,
            "groups": rates,
            "demographic_parity_diff": dpd,
            "disparate_impact_ratio": dir_val,
            "equalized_odds_diff": eod,
            "predictive_parity_diff": ppd,
            "theil_index": theil,
            "p_value": p_val,
            "sample_sizes": {str(g): int(df_clean[df_clean[attr] == g].shape[0]) for g in df_clean[attr].unique()},
            "flag_level": flag,
        }
        bias_metrics.append(metric)

        risk_priority = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0}
        if risk_priority.get(flag, 0) > risk_priority.get(overall_risk, 0):
            overall_risk = flag

    audit_uuid = uuid.UUID(state["audit_id"])
    async with async_session() as db:
        audit = await db.get(Audit, audit_uuid)
        if audit:
            audit.status = "analyzing"
            audit.overall_risk = overall_risk
            await db.commit()

        for metric in bias_metrics:
            for group_name, pos_rate in metric["groups"].items():
                result = AuditResult(
                    audit_id=audit_uuid,
                    protected_attr=metric["protected_attr"],
                    group_name=str(group_name),
                    positive_rate=pos_rate,
                    demographic_parity_diff=metric["demographic_parity_diff"],
                    disparate_impact_ratio=metric["disparate_impact_ratio"],
                    equalized_odds_diff=metric["equalized_odds_diff"],
                    predictive_parity_diff=metric["predictive_parity_diff"],
                    theil_index=metric["theil_index"],
                    p_value=metric["p_value"],
                    sample_size=metric["sample_sizes"].get(group_name),
                    flag_level=metric["flag_level"],
                )
                db.add(result)
            await db.commit()

    return {
        **state,
        "bias_metrics": bias_metrics,
        "overall_risk": overall_risk,
        "status": "analyzing",
    }
