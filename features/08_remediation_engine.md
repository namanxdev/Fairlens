# Feature 08: Remediation Engine (LangGraph Node 5)

## Overview

The Remediation Engine offers debiasing strategies that users can apply to their dataset. After applying a strategy, it re-runs all bias metrics and produces a before/after comparison showing the improvement (or tradeoff).

---

## Debiasing Strategies

### 1. Reweighting (Pre-processing)
- Assign instance weights inversely proportional to group frequency × outcome frequency
- Uses `fairlearn` utilities
- **Best for:** Addressing imbalanced group representation in training data
- **Tradeoff:** Minimal accuracy loss (typically 1-3%)

### 2. Resampling (Pre-processing)
- Oversample underrepresented groups or undersample overrepresented ones
- Uses SMOTE for synthetic oversampling
- **Best for:** Small datasets with severe group imbalance
- **Tradeoff:** Can introduce synthetic artifacts; moderate accuracy impact

### 3. Threshold Adjustment (Post-processing)
- Set group-specific decision thresholds to equalize outcome rates
- Uses `fairlearn.postprocessing.ThresholdOptimizer`
- **Best for:** Quick fix when you can't retrain the model
- **Tradeoff:** May reduce overall accuracy; different groups get different thresholds

---

## Backend Implementation

### `backend/pipeline/remediator.py`

```python
async def apply_remediation(state, strategy: str) -> dict:
    """Apply a debiasing strategy and compute before/after metrics."""
    # 1. Load original dataset
    # 2. Apply selected strategy
    # 3. Re-compute all fairness metrics on remediated data
    # 4. Calculate accuracy tradeoff (if applicable)
    # 5. Return before/after comparison
```

**Key functions in `backend/metrics/remediation.py`:**
```python
def reweight_dataset(df, protected_col, target_col) -> tuple[pd.DataFrame, np.ndarray]
def resample_dataset(df, protected_col, target_col) -> pd.DataFrame
def adjust_thresholds(df, protected_col, target_col, predictions) -> pd.DataFrame
```

### API Endpoint: `POST /api/audit/{audit_id}/remediate`

**File:** `backend/routes/remediate.py`

**Request:**
```json
{
  "strategy": "reweighting"
}
```

**Response:**
```json
{
  "strategy": "reweighting",
  "before": {
    "gender_disparate_impact": 0.349,
    "gender_dpd": -0.203,
    "race_disparate_impact": 0.424,
    "race_dpd": -0.163
  },
  "after": {
    "gender_disparate_impact": 0.812,
    "gender_dpd": -0.042,
    "race_disparate_impact": 0.791,
    "race_dpd": -0.051
  },
  "accuracy_tradeoff": {
    "before": 0.847,
    "after": 0.831
  },
  "recommendation": "Reweighting brought gender DIR above the 0.8 legal threshold with 1.6% accuracy loss."
}
```

### API Endpoint: `GET /api/audit/{audit_id}/compare`

Returns the before/after comparison for display in charts.

---

## Frontend: Before/After Comparison

### `frontend/components/BeforeAfter.tsx`

**Displays:**
1. **Strategy selector** — Dropdown or card selection for reweighting / resampling / threshold adjustment
2. **Dual bar chart** — Side-by-side bars showing metric values before (red) and after (green) remediation
3. **Accuracy tradeoff indicator** — Shows accuracy loss as a percentage with a gauge
4. **Recommendation text** — LLM-generated plain-English summary of the result
5. **"Apply & Download" button** — Downloads the remediated dataset as CSV

**Uses:** `recharts` — `BarChart` with two `Bar` elements (before/after), different colors.

---

## Database Storage

Each remediation attempt creates a row in `remediation_logs`:
- `strategy` — which method was applied
- `metric_before` — JSONB of all metrics before
- `metric_after` — JSONB of all metrics after
- `accuracy_before` / `accuracy_after` — accuracy values

---

## Verification

1. Select "reweighting" → metrics improve, DIR crosses 0.8 threshold
2. Before/after chart renders correctly with dual bars
3. Accuracy tradeoff is displayed and reasonable (< 5% loss)
4. Remediation log saved to database
5. Remediated dataset downloadable as CSV
6. Multiple strategies can be tried sequentially
