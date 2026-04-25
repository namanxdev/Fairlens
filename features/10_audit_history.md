# Feature 10: Audit History & Timeline

## Overview

A timeline view showing all past audits for the user/organization. Displays audit history with trend lines for key metrics, tracking whether bias is improving or degrading over successive audits.

---

## Backend

### API Endpoint: `GET /api/audits`

**File:** `backend/routes/audit.py`

Returns a paginated list of all audits, ordered by creation date (newest first):

```json
{
  "audits": [
    {
      "id": "...",
      "dataset_name": "hiring_data_2024.csv",
      "status": "completed",
      "overall_risk": "CRITICAL",
      "row_count": 32561,
      "column_count": 15,
      "created_at": "2026-04-25T12:00:00Z",
      "completed_at": "2026-04-25T12:00:15Z"
    }
  ],
  "total": 12,
  "page": 1,
  "per_page": 10
}
```

**Query params:** `?page=1&per_page=10&status=completed`

---

## Frontend Page

### Route: `/history`

**File:** `frontend/app/history/page.tsx`

### Layout

1. **Page Header** — "Audit History" title, filter controls
2. **Timeline View** — Vertical timeline with audit cards
3. **Summary Stats** — Total audits, average risk level, most common issues

### Timeline Component

**File:** `frontend/components/AuditTimeline.tsx`

Each audit displayed as a card on a vertical timeline:
- **Left:** Date/time indicator on the timeline line
- **Right:** Card with:
  - Dataset name
  - Risk level badge (colored dot + text)
  - Row/column count
  - Key metric summary (worst DIR value)
  - Status indicator
  - "View Dashboard" and "View Report" action links

### Design

- Vertical timeline with a thin line connecting audit events
- Cards alternate left/right on desktop, stack on mobile
- Risk-level colored dots on the timeline
- Hover to preview key metrics, click to navigate to full dashboard
- Empty state: illustration + "Run your first audit" CTA

---

## Trend Tracking (Bonus)

If the same dataset name has been audited multiple times, show trend lines:
- Sparkline chart showing DIR values across audits
- ↑ or ↓ indicator showing improvement or degradation
- "Improving" / "Degrading" / "Stable" label

---

## Verification

1. History page lists all past audits
2. Audits sorted newest-first
3. Risk level badges display correctly
4. Clicking "View Dashboard" navigates to `/dashboard?audit_id={id}`
5. Empty state shown when no audits exist
6. Pagination works for many audits
