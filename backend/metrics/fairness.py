import numpy as np
import pandas as pd
from scipy import stats


def compute_positive_rates(df: pd.DataFrame, protected_col: str, target_col: str) -> dict:
    rates = {}
    for group in df[protected_col].dropna().unique():
        subset = df[df[protected_col] == group]
        pos = subset[target_col].sum()
        total = len(subset)
        rates[str(group)] = round(pos / total, 4) if total > 0 else 0.0
    return rates


def compute_demographic_parity(df: pd.DataFrame, protected_col: str, target_col: str) -> float:
    rates = compute_positive_rates(df, protected_col, target_col)
    if not rates:
        return 0.0
    values = list(rates.values())
    return round(max(values) - min(values), 4)


def compute_disparate_impact(df: pd.DataFrame, protected_col: str, target_col: str) -> float:
    rates = compute_positive_rates(df, protected_col, target_col)
    if not rates:
        return 1.0
    values = list(rates.values())
    max_rate = max(values)
    min_rate = min(values)
    if max_rate == 0:
        return 1.0
    return round(min_rate / max_rate, 4)


def compute_equalized_odds(df: pd.DataFrame, protected_col: str, target_col: str) -> float:
    groups = df[protected_col].dropna().unique()
    tprs = []
    for g in groups:
        subset = df[df[protected_col] == g]
        positives = subset[target_col].sum()
        total = len(subset)
        tpr = positives / total if total > 0 else 0.0
        tprs.append(tpr)
    if not tprs:
        return 0.0
    return round(max(tprs) - min(tprs), 4)


def compute_predictive_parity(df: pd.DataFrame, protected_col: str, target_col: str) -> float:
    groups = df[protected_col].dropna().unique()
    ppvs = []
    for g in groups:
        subset = df[df[protected_col] == g]
        positives = subset[target_col].sum()
        total = len(subset)
        ppv = positives / total if total > 0 else 0.0
        ppvs.append(ppv)
    if not ppvs:
        return 0.0
    return round(max(ppvs) - min(ppvs), 4)


def compute_theil_index(df: pd.DataFrame, protected_col: str, target_col: str) -> float:
    y = df[target_col].astype(float).values
    y = y[~np.isnan(y)]
    if len(y) == 0 or y.mean() == 0:
        return 0.0
    yi_y = y / y.mean()
    valid = yi_y > 0
    if not valid.any():
        return 0.0
    ti = np.mean((yi_y[valid]) * np.log(yi_y[valid]))
    return round(float(ti), 4)


def classify_flag(dir_value: float, dpd_value: float, p_value: float) -> str:
    if dir_value < 0.6 and p_value < 0.01:
        return "CRITICAL"
    elif dir_value < 0.8 and p_value < 0.05:
        return "HIGH"
    elif dir_value < 0.9:
        return "MEDIUM"
    else:
        return "LOW"
