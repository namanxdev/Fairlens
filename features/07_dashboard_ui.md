# Feature 07: Dashboard UI — Heatmap, Charts & Metric Cards

## Overview

The main audit dashboard displays bias analysis results through interactive visualizations: a bias heatmap, group distribution bar charts, metric cards with severity indicators, and a schema preview panel. This is the primary view users interact with after an audit completes.

---

## Page Structure

### Route: `/dashboard?audit_id={id}`

**File:** `frontend/app/dashboard/page.tsx`

The dashboard is a single-page layout with the following sections (top to bottom):

### 1. Dashboard Header
- Dataset name, audit date, row/column count
- Overall risk badge (CRITICAL=red, HIGH=orange, MEDIUM=yellow, LOW=green)
- Audit status indicator (with polling while pipeline is running)
- Navigation: back to upload, view report, audit history

### 2. Schema Preview Panel (from Feature 04)
- Color-coded column classification chips
- Expandable proxy warning alerts

### 3. Bias Heatmap (Primary View)
- Matrix: rows = protected attributes, columns = fairness metrics
- Cells color-coded: Green (pass) / Yellow (warning) / Red (fail)
- Clicking a cell drills down to the detailed breakdown

### 4. Group Distribution Charts
- Side-by-side bar charts: outcome rates per group for each protected attribute
- E.g., "% Hired" for Male vs Female, White vs Black vs Asian

### 5. Metric Cards
- One card per protected attribute showing key metric values
- Severity badge, sparkline trend (if audit history exists)

---

## Component Specifications

### BiasHeatmap Component

**File:** `frontend/components/BiasHeatmap.tsx`

**Data shape:**
```typescript
interface HeatmapCell {
  attribute: string;       // "gender", "race"
  metric: string;          // "DPD", "DIR", "EOD", "PPD"
  value: number;
  threshold: number;
  status: 'pass' | 'warning' | 'fail';
}
```

**Behavior:**
- Render as a grid/table with colored cells
- Color scale: `#22c55e` (green/pass) → `#eab308` (yellow/warning) → `#ef4444` (red/fail)
- On cell click: expand to show the detailed breakdown below the row
- Hover tooltip: shows exact value, threshold, and delta

**Implementation:** Use a custom CSS grid or HTML table with conditional background colors. Do NOT use Recharts for the heatmap — build it with styled divs for maximum control.

### DistributionChart Component

**File:** `frontend/components/DistributionChart.tsx`

**Uses:** `recharts` — `BarChart`, `Bar`, `XAxis`, `YAxis`, `Tooltip`, `Legend`

**Data shape:**
```typescript
interface GroupRate {
  group: string;     // "Male", "Female"
  rate: number;      // 0.312 (31.2%)
  count: number;     // 21790
}
```

**Behavior:**
- Side-by-side grouped bar chart
- Each bar labeled with the percentage
- Color per group (use a consistent palette)
- Tooltip shows: group name, positive rate %, sample size

### MetricCard Component

**File:** `frontend/components/MetricCard.tsx`

**Displays:**
- Protected attribute name (e.g., "Gender")
- Flag level badge with color
- Key metric: Disparate Impact Ratio (large number)
- Sub-metrics: DPD, EOD, PPD as smaller values
- p-value indicator
- Sample sizes per group

**Style:** Dark glassmorphic card with subtle gradient border matching severity color.

---

## Data Fetching

### Dashboard Data Hook

**File:** `frontend/lib/hooks/useAuditData.ts`

```typescript
import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export function useAuditData(auditId: string) {
  const [status, setStatus] = useState<string>('pending');
  const [results, setResults] = useState(null);
  const [schema, setSchema] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const pollStatus = async () => {
      const res = await api.get(`/audit/${auditId}/status`);
      setStatus(res.data.status);
      setSchema(res.data.schema);

      if (res.data.status === 'completed') {
        const resultsRes = await api.get(`/audit/${auditId}/results`);
        setResults(resultsRes.data);
        setLoading(false);
        return true; // stop polling
      }
      return false;
    };

    const interval = setInterval(async () => {
      const done = await pollStatus();
      if (done) clearInterval(interval);
    }, 2000);

    pollStatus(); // initial call
    return () => clearInterval(interval);
  }, [auditId]);

  return { status, results, schema, loading };
}
```

---

## Loading State

While the pipeline is running, show:
1. A progress stepper: `Profiling → Analyzing → Generating Report → Complete`
2. Current step highlighted with a pulse animation
3. Estimated time remaining (rough: ~5-15 seconds per node)

---

## Design Requirements

- **Dark theme** — Deep navy/charcoal background (`#0a0a1a` base)
- **Glassmorphic cards** — `backdrop-filter: blur(12px)`, semi-transparent backgrounds
- **Color palette:** Coral red for CRITICAL, amber for HIGH, yellow for MEDIUM, emerald for LOW
- **Typography:** Inter or similar modern sans-serif from Google Fonts
- **Responsive:** Works on desktop (1920px) down to tablet (768px)
- **Animations:** Fade-in on data load, smooth color transitions on heatmap hover

---

## Verification

1. Dashboard loads and polls for status while pipeline runs
2. Heatmap renders correctly with color-coded cells
3. Clicking a heatmap cell shows detailed breakdown
4. Bar charts accurately show group distribution rates
5. Metric cards display correct values with severity badges
6. Loading stepper animates through pipeline stages
7. Responsive layout works on tablet and desktop
