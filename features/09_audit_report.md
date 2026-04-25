# Feature 09: Audit Report Viewer & PDF Export

## Overview

A dedicated report viewer page that renders the LLM-generated markdown audit report with rich formatting. Users can read the report in-browser and download it as a PDF.

---

## Frontend Page

### Route: `/dashboard/report?audit_id={id}`

**File:** `frontend/app/dashboard/report/page.tsx`

### Layout

1. **Report Header** — Dataset name, date, overall risk badge, download button
2. **Report Body** — Rendered markdown with styled headings, lists, code blocks, and severity badges
3. **Sidebar Navigation** — Sticky table of contents generated from report headings (Executive Summary, Finding 1, Finding 2, etc.)
4. **Action Bar** — "Download PDF", "Copy Markdown", "Share" buttons

### Markdown Rendering

Use a markdown renderer (e.g., `react-markdown` with `remark-gfm`) to render the `content_md` from the report API.

**Install:**
```bash
npm install react-markdown remark-gfm
```

**Custom styling for report elements:**
- `# FAIRLENS AUDIT REPORT` → large styled header with logo
- `## Finding X:` → card-like sections with severity color accent
- `CRITICAL` / `HIGH` / `MEDIUM` / `LOW` text → rendered as colored badges
- Metric values → highlighted with monospace font
- Tables → styled with dark theme borders
- Code blocks → syntax highlighted

---

## PDF Export

### Backend Endpoint: `GET /api/audit/{audit_id}/report/pdf`

**File:** `backend/routes/report.py`

Two approaches (implement one):

**Option A: Server-side PDF generation**
- Use `weasyprint` or `markdown2` + `pdfkit` to convert markdown → HTML → PDF
- Add FairLens header/footer with branding
- Return PDF as a file download response

**Option B: Client-side PDF generation**
- Use `html2canvas` + `jspdf` in the frontend
- Capture the rendered report div and convert to PDF
- Simpler but lower quality

**Recommended: Option A (server-side) for consistent, high-quality output.**

```python
@router.get("/audit/{audit_id}/report/pdf")
async def download_report_pdf(audit_id: str, db: AsyncSession = Depends(get_db)):
    # 1. Fetch report from database
    # 2. Convert markdown to styled HTML
    # 3. Generate PDF with weasyprint
    # 4. Return as StreamingResponse with content-type application/pdf
    pass
```

---

## API Endpoint

### `GET /api/audit/{audit_id}/report`

Returns the report markdown:
```json
{
  "audit_id": "...",
  "report": "# FAIRLENS AUDIT REPORT\n\n**Dataset:** ...",
  "created_at": "2026-04-25T12:00:00Z"
}
```

---

## Design

- **Report viewer:** Clean white/light background for readability (contrast with dashboard's dark theme)
- **Print-friendly:** CSS `@media print` styles for good print output
- **Sticky TOC:** Left sidebar with clickable section links, highlights current section
- **Severity badges:** Inline colored pills (CRITICAL = red bg, HIGH = orange, etc.)

---

## Verification

1. Report page renders the full markdown report with proper formatting
2. TOC sidebar navigates to correct sections
3. Severity keywords render as colored badges
4. PDF download produces a well-formatted document
5. PDF includes all sections, metrics, and recommendations
6. "Copy Markdown" copies raw markdown to clipboard
