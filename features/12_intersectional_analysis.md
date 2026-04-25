# Feature 12: Intersectional Analysis

## Overview

Single-attribute bias analysis can miss hidden disparities at the intersection of multiple protected attributes. For example, overall gender and race metrics might look acceptable, but Black women specifically may face severe bias. This feature computes metrics at all pairwise intersections and visualizes them in a matrix/bubble chart.

---

## What is Intersectional Analysis?

**Problem:** Analyzing gender and race separately may show:
- Gender DIR = 0.78 (borderline, but passes 0.8 rule? close)
- Race DIR = 0.82 (passes)

But at intersections:
- White Male: 35% positive rate
- White Female: 28% positive rate
- Black Male: 20% positive rate
- **Black Female: 8% positive rate** ← CRITICAL (DIR = 0.23)

The combined effect is far worse than either dimension alone.

---

## Backend Implementation

### `backend/metrics/intersectional.py`

```python
import pandas as pd
import numpy as np
from itertools import combinations
from metrics.fairness import compute_disparate_impact, compute_demographic_parity

def compute_intersectional_metrics(
    df: pd.DataFrame,
    protected_attrs: list[str],
    target_col: str
) -> list[dict]:
    """Compute fairness metrics at all pairwise intersections of protected attributes."""
    results = []

    for attr1, attr2 in combinations(protected_attrs, 2):
        # Create intersection column
        df['_intersection'] = df[attr1].astype(str) + ' × ' + df[attr2].astype(str)

        # Compute positive rate per intersection group
        group_rates = df.groupby('_intersection')[target_col].mean().to_dict()
        group_sizes = df.groupby('_intersection')[target_col].count().to_dict()

        # Compute DIR across intersection groups
        rates = list(group_rates.values())
        dir_value = min(rates) / max(rates) if max(rates) > 0 else 0

        # Find the most/least advantaged intersection groups
        best_group = max(group_rates, key=group_rates.get)
        worst_group = min(group_rates, key=group_rates.get)

        results.append({
            "attributes": [attr1, attr2],
            "groups": group_rates,
            "sample_sizes": group_sizes,
            "disparate_impact_ratio": round(dir_value, 4),
            "best_group": {"name": best_group, "rate": round(group_rates[best_group], 4)},
            "worst_group": {"name": worst_group, "rate": round(group_rates[worst_group], 4)},
            "flag_level": classify_intersectional_flag(dir_value),
        })

        df.drop('_intersection', axis=1, inplace=True)

    return results
```

### Integration with Bias Detector (Node 2)

Add intersectional analysis as an additional step after single-attribute analysis in `pipeline/bias_detector.py`. Store results in a new JSONB field on the `audits` table or as additional `audit_results` rows.

---

## API Endpoint

### `GET /api/audit/{audit_id}/intersectional`

**File:** `backend/routes/audit.py`

```json
{
  "intersections": [
    {
      "attributes": ["sex", "race"],
      "groups": {
        "Male × White": 0.332,
        "Male × Black": 0.198,
        "Female × White": 0.128,
        "Female × Black": 0.051
      },
      "disparate_impact_ratio": 0.154,
      "best_group": {"name": "Male × White", "rate": 0.332},
      "worst_group": {"name": "Female × Black", "rate": 0.051},
      "flag_level": "CRITICAL"
    }
  ]
}
```

---

## Frontend: Intersectional Heatmap

### `frontend/components/IntersectionalMatrix.tsx`

**Visualization:** A heatmap or bubble chart where:
- **Rows:** Values of attribute 1 (e.g., Male, Female)
- **Columns:** Values of attribute 2 (e.g., White, Black, Asian)
- **Cell color/size:** Positive outcome rate (darker/larger = higher rate)

**Alternative: Bubble Chart**
- Each intersection group as a bubble
- X-axis: attribute 1 groups
- Y-axis: positive rate
- Bubble size: sample size
- Bubble color: severity (green→red)

**Behavior:**
- Dropdown selectors for which two attributes to cross
- Hover shows exact rate, sample size, and DIR relative to best group
- Worst intersection groups highlighted with a warning border

---

## Design

- Use diverging color scale: deep red (low rate) → white (median) → deep green (high rate)
- Annotate cells with percentage values
- Add a legend explaining the color scale and the 80% rule threshold
- Responsive grid layout

---

## Verification

1. For Adult Income: `Female × Black` intersection shows worst outcome rate
2. Intersectional DIR is lower than any single-attribute DIR
3. Heatmap renders with correct color coding
4. Attribute selector dropdowns work
5. Hover tooltips show correct values
6. API returns all pairwise intersections
