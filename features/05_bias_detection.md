# Feature 05: Statistical Bias Detection (LangGraph Node 2)

## Overview

The Bias Detector is the core computation engine. It takes the profiled schema and raw data from Node 1, computes industry-standard fairness metrics for every protected attribute against the target variable, runs statistical significance tests, and classifies severity.

---

## Fairness Metrics Computed

### 1. Demographic Parity Difference (DPD)
- **Formula:** `P(Ŷ=1 | group=A) - P(Ŷ=1 | group=B)`
- **Meaning:** Do all groups receive positive outcomes at equal rates?
- **Threshold:** Flag if `|DPD| > 0.1`

### 2. Disparate Impact Ratio (DIR) — The 80% Rule
- **Formula:** `min(P(Ŷ=1|group)) / max(P(Ŷ=1|group))`
- **Meaning:** Is the lowest group's rate at least 80% of the highest?
- **Threshold:** Flag if `DIR < 0.8` (EEOC legal standard)

### 3. Equalized Odds Difference (EOD)
- **Formula:** Max difference in TPR and FPR across groups
- **Meaning:** Does the model make errors at equal rates across groups?
- **Threshold:** Flag if `|EOD| > 0.1`

### 4. Predictive Parity Difference (PPD)
- **Formula:** Max difference in positive predictive value across groups
- **Meaning:** When the model says "yes," does it mean the same thing for all groups?
- **Threshold:** Flag if `|PPD| > 0.1`

### 5. Theil Index (Generalized Entropy)
- Information-theoretic measure of inequality
- Captures between-group and within-group unfairness
- Useful for intersectional analysis

### 6. Statistical Significance
- **Chi-squared test** for categorical outcomes
- **Mann-Whitney U** for continuous outcomes
- Only flag if `p < 0.05`

---

## Implementation

### `backend/metrics/fairness.py`

Core metric computation functions using pandas, numpy, scipy. Each function takes a DataFrame, the protected attribute column name, and the target column name.

**Key functions:**
```python
def compute_positive_rates(df, protected_col, target_col) -> dict[str, float]
def compute_demographic_parity(df, protected_col, target_col) -> float
def compute_disparate_impact(df, protected_col, target_col) -> float
def compute_equalized_odds(df, protected_col, target_col, pred_col=None) -> float
def compute_predictive_parity(df, protected_col, target_col, pred_col=None) -> float
def compute_theil_index(df, protected_col, target_col) -> float
```

### `backend/metrics/statistical.py`

Statistical significance testing:
```python
def chi_squared_test(df, protected_col, target_col) -> float  # returns p-value
def mann_whitney_test(df, protected_col, target_col) -> float  # returns p-value
```

### `backend/pipeline/bias_detector.py`

The LangGraph node function:
1. Loads the dataset from `state["file_path"]`
2. For each protected attribute in `state["protected_attributes"]`:
   - Computes all 6 metrics against `state["target"]`
   - Computes group-level positive rates and sample sizes
   - Runs significance test
   - Assigns flag level based on thresholds
3. Determines `overall_risk` (worst flag across all attributes)
4. Saves results to `audit_results` table (one row per attribute-group pair)
5. Updates audit status to "analyzing"

**Flag Level Logic:**
```python
def classify_flag(dir_value, dpd_value, p_value):
    if dir_value < 0.6 and p_value < 0.01:
        return "CRITICAL"
    elif dir_value < 0.8 and p_value < 0.05:
        return "HIGH"
    elif dir_value < 0.9:
        return "MEDIUM"
    else:
        return "LOW"
```

---

## API Endpoint

### `GET /api/audit/{audit_id}/results`

**File:** `backend/routes/audit.py`

Returns all computed metrics for an audit:
```json
{
  "audit_id": "...",
  "overall_risk": "CRITICAL",
  "metrics": [
    {
      "protected_attr": "gender",
      "groups": {"Male": 0.312, "Female": 0.109},
      "demographic_parity_diff": -0.203,
      "disparate_impact_ratio": 0.349,
      "equalized_odds_diff": null,
      "predictive_parity_diff": null,
      "theil_index": 0.087,
      "p_value": 0.00001,
      "sample_sizes": {"Male": 21790, "Female": 10771},
      "flag_level": "CRITICAL"
    }
  ]
}
```

---

## Database Storage

Each metric result creates rows in `audit_results`:
- One row per (protected_attribute, group_name) pair
- `positive_rate` stores the group's outcome rate
- All metric values stored in their respective columns
- `flag_level` stores the severity classification

---

## Target Binarization

If the target column is not already binary (0/1), apply binarization:
- **Numeric continuous** (e.g., income): use median split → above median = 1, below = 0
- **Categorical with 2 values** (e.g., "Yes"/"No"): map to 1/0
- **Categorical with >2 values**: use the most common positive-sounding value as 1, rest as 0
- Use LLM to determine which value represents the "positive" outcome if ambiguous

---

## Verification

1. For Adult Income dataset: gender DIR ≈ 0.35 (CRITICAL), race DIR ≈ 0.42 (HIGH)
2. All metrics computed and stored in database
3. Statistical significance tests produce valid p-values
4. Flag levels correctly assigned based on thresholds
5. `overall_risk` reflects the worst flag across all attributes
6. API endpoint returns structured metric JSON
