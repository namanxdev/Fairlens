# Feature 11: Sample Datasets & One-Click Demo

## Overview

Bundle well-known bias-relevant datasets from Kaggle/UCI so users can immediately try FairLens without uploading their own data. Provide a "Try Demo" experience with one-click dataset loading.

---

## Bundled Datasets

### 1. UCI Adult Income Dataset
- **Source:** [UCI ML Repository](https://archive.ics.uci.edu/dataset/2/adult) / [Kaggle](https://www.kaggle.com/datasets/uciml/adult-census-income)
- **File:** `sample_data/adult_income.csv`
- **Rows:** 32,561
- **Target:** `income` (>50K / <=50K)
- **Protected Attributes:** `sex`, `race`, `age`
- **Known Bias:** Severe gender bias (DIR ≈ 0.35), racial bias (DIR ≈ 0.42)
- **Use Case:** Hiring / income prediction

### 2. German Credit Dataset
- **Source:** [UCI ML Repository](https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data) / [Kaggle](https://www.kaggle.com/datasets/uciml/german-credit)
- **File:** `sample_data/german_credit.csv`
- **Rows:** 1,000
- **Target:** `credit_risk` (good / bad)
- **Protected Attributes:** `age`, `sex`, `foreign_worker`
- **Known Bias:** Age-based disparities in credit approval
- **Use Case:** Lending / credit scoring

### 3. COMPAS Recidivism Dataset
- **Source:** [ProPublica](https://github.com/propublica/compas-analysis) / [Kaggle](https://www.kaggle.com/datasets/danofer/compass)
- **File:** `sample_data/compas_recidivism.csv`
- **Rows:** 7,214
- **Target:** `two_year_recid` (recidivism within 2 years)
- **Protected Attributes:** `race`, `sex`, `age`
- **Known Bias:** Severe racial bias — Black defendants flagged as high-risk at much higher rates
- **Use Case:** Criminal justice risk assessment

### 4. Bank Marketing Dataset
- **Source:** [UCI ML Repository](https://archive.ics.uci.edu/dataset/222/bank+marketing) / [Kaggle](https://www.kaggle.com/datasets/henriqueyamahata/bank-marketing)
- **File:** `sample_data/bank_marketing.csv`
- **Rows:** 45,211
- **Target:** `y` (subscribed to term deposit: yes/no)
- **Protected Attributes:** `age`, `marital`, `education`
- **Known Bias:** Age-based targeting disparities
- **Use Case:** Marketing / customer targeting

---

## How to Obtain the Data

**Option A: Download from Kaggle (Recommended)**
1. Download CSVs from the Kaggle links above
2. Place in `sample_data/` directory
3. Rename to match the filenames above

**Option B: Use Kaggle API**
```bash
pip install kaggle
kaggle datasets download uciml/adult-census-income -p sample_data/ --unzip
kaggle datasets download uciml/german-credit -p sample_data/ --unzip
```

**Option C: Use UCI ML Repository directly**
Download from UCI URLs and convert to CSV with pandas.

### Data Preprocessing Script

Create `backend/scripts/prepare_sample_data.py`:
```python
"""Download and preprocess sample datasets for FairLens demo."""
import pandas as pd
import os

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'sample_data')

def prepare_adult_income():
    """Prepare UCI Adult Income dataset with clean column names."""
    url = "https://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data"
    columns = ['age', 'workclass', 'fnlwgt', 'education', 'education_num',
               'marital_status', 'occupation', 'relationship', 'race', 'sex',
               'capital_gain', 'capital_loss', 'hours_per_week', 'native_country', 'income']
    df = pd.read_csv(url, names=columns, skipinitialspace=True)
    df['income'] = df['income'].map({'>50K': 1, '<=50K': 0, '>50K.': 1, '<=50K.': 0})
    df.to_csv(os.path.join(SAMPLE_DIR, 'adult_income.csv'), index=False)
    print(f"Adult Income: {len(df)} rows saved")

# Similar functions for other datasets...
```

---

## Backend Implementation

### API Endpoint: `GET /api/sample-datasets`

**File:** `backend/routes/upload.py`

```json
{
  "datasets": [
    {
      "id": "adult_income",
      "name": "Adult Income (UCI)",
      "description": "Predict whether income exceeds $50K. Known gender and racial bias.",
      "rows": 32561,
      "columns": 15,
      "known_bias": ["Gender (CRITICAL)", "Race (HIGH)"],
      "use_case": "Hiring / Income Prediction",
      "file": "adult_income.csv"
    }
  ]
}
```

### API Endpoint: `POST /api/sample-datasets/{dataset_id}/load`

Copies the sample dataset to the uploads directory and creates an audit record, just like a manual upload would. Returns the same response as `POST /api/upload`.

---

## Frontend: Demo Section

### On the Landing Page (`frontend/app/page.tsx`)

Below the upload zone, add a "Try with Demo Data" section:

1. **Section title:** "Try with Demo Data" or "Quick Start"
2. **Dataset cards** — One card per sample dataset showing:
   - Dataset name and icon
   - Row count and description
   - Known bias indicators (badges)
   - Use case tag
   - "Load & Audit" button
3. Clicking "Load & Audit" → calls `POST /api/sample-datasets/{id}/load` → navigates to dashboard

### Card Design

- Dark glassmorphic cards in a 2×2 grid
- Hover effect: subtle lift + glow
- Known bias badges use severity colors
- Each card has a unique accent color

---

## Verification

1. Sample datasets exist in `sample_data/` directory
2. `GET /api/sample-datasets` returns list of available demos
3. Clicking "Load & Audit" creates an audit and starts the pipeline
4. Adult Income dataset produces CRITICAL gender bias results
5. COMPAS dataset produces CRITICAL racial bias results
6. Demo cards render correctly on the landing page
