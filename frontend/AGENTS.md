<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This project uses Next.js 16 and React 19. APIs, conventions, and file structure may differ from older training data. Read the relevant guide in `node_modules/next/dist/docs/` before changing framework-sensitive code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

# Frontend Agent Guide

## Scope

These instructions apply to `frontend/`. The UI is a Next.js App Router application for the FairLens audit dashboard.

## Stack

- Next.js 16 App Router
- React 19
- TypeScript
- Tailwind CSS v4
- Planned component/UI sources: shadcn/ui, Aceternity UI, HeroUI, and Magic UI
- Planned charting: Recharts unless a feature explicitly calls for custom rendering

Before importing any third-party component, confirm the package exists in `package.json`. At the time this guide was written, shadcn/ui, Aceternity, HeroUI, Magic UI, Recharts, Axios, Lucide, and React Dropzone were not installed.

## Component Library Rules

- Use shadcn/ui for stable primitives: buttons, inputs, forms, dialogs, sheets, tabs, tables, cards, badges, toast/sonner, and command menus.
- Use Aceternity UI for high-impact marketing/dashboard effects: animated backgrounds, spotlight cards, tracing beams, moving borders, and hero sections. Keep these effects outside dense data tables.
- Use HeroUI for accessible application widgets when it materially speeds up delivery: select, modal, dropdown, pagination, tooltip, popover, and complex form controls.
- Use Magic UI for tasteful animated accents: shimmer buttons, marquee sections, border beams, number tickers, and empty states.
- Do not mix multiple libraries for the same primitive in one screen. Pick one source for buttons/forms/modals per route unless there is a clear reason.
- Wrap imported library components in local components when they become part of the product system.

## Design Rules

- Preserve a serious trust-oriented product feel. FairLens deals with bias, audits, and compliance; avoid toy-like visuals.
- Use bold visual hierarchy for dashboards: risk level, dataset status, and next action must be immediately visible.
- Do not rely on generic purple gradients, default starter layouts, or unstyled component dumps.
- Keep charts legible before decorative. Heatmaps, metric cards, and reports need contrast, labels, legends, and keyboard-accessible detail.
- Support desktop and tablet layouts first, then make mobile states usable instead of simply squeezed.
- Use motion sparingly for comprehension: upload progress, pipeline status, card reveal, hover detail, and report navigation.

## Next.js And React Rules

- Prefer Server Components by default. Add `"use client"` only for state, browser APIs, effects, drag/drop, charts, or event handlers.
- Keep data-fetching and API helpers in `lib/`.
- Keep shared visual components in `components/`.
- Use route folders under `app/` for pages: `dashboard`, `dashboard/report`, and `history`.
- Do not hard-code backend URLs in components. Use `NEXT_PUBLIC_API_URL` through a single API client.
- Keep query-param parsing close to the route page and pass typed props into components.

## API Contract Rules

- Match backend routes from `../features/*.md` until real backend schemas exist.
- Centralize API calls in `lib/api.ts`; avoid raw `fetch` or Axios calls scattered through components.
- Handle loading, empty, failed, running, and completed audit states explicitly.
- Poll audit status only while the audit is not terminal. Stop polling on `completed` or `failed`.

## Quality Bar

- Type component props and API responses explicitly.
- Do not suppress TypeScript or ESLint errors without a specific comment explaining why.
- Prefer accessible components with labels, focus states, and keyboard behavior.
- Keep generated or copied component-library code minimal and remove unused variants.

## Commands

```bash
npm install
npm run dev
npm run build
npm run lint
```

Run `npm run build` before handing off substantial frontend changes.
