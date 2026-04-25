import pandas as pd
from scipy.stats import chi2_contingency, mannwhitneyu


def chi_squared_test(df: pd.DataFrame, protected_col: str, target_col: str) -> float:
    try:
        contingency = pd.crosstab(df[protected_col], df[target_col])
        if contingency.shape[0] < 2 or contingency.shape[1] < 2:
            return 1.0
        _, p, _, _ = chi2_contingency(contingency)
        return float(p)
    except Exception:
        return 1.0


def mann_whitney_test(df: pd.DataFrame, protected_col: str, target_col: str) -> float:
    try:
        groups = df[protected_col].dropna().unique()
        if len(groups) != 2:
            return 1.0
        g1 = df[df[protected_col] == groups[0]][target_col].dropna()
        g2 = df[df[protected_col] == groups[1]][target_col].dropna()
        if len(g1) == 0 or len(g2) == 0:
            return 1.0
        _, p = mannwhitneyu(g1, g2, alternative="two-sided")
        return float(p)
    except Exception:
        return 1.0
