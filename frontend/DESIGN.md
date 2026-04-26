# Design

## Theme
Dark mode default (Zinc-950 background) with a high-end, Vercel-core aesthetic.

## Colors
- **Background:** `zinc-950`
- **Surface:** `zinc-900` to `#0a0a0a` (pure dark) with `border-slate-800`
- **Accent:** Emerald-500 (single sharp accent, no mixed gradients)
- **Text:** White for primary, `zinc-400` for secondary.

## Typography
- **Primary Font:** Geist (via `next/font/google`). Do NOT use Inter.
- **Display:** Left-aligned, `text-6xl+`, `tracking-tighter`.

## Layout
- **Hero:** Asymmetrical layout. Left-aligned typography, right-aligned abstract UI/data visualization. `min-h-[100dvh]` (no `h-screen`).
- **Features:** Bento grid / Masonry layout using CSS Grid. No generic 3-column identical cards.
- **Depth:** Diffusion shadows, liquid glass refraction, 1px borders.

## Motion
- **Library:** Framer Motion
- **Curves:** Staggered, refined reveals with `ease-out` curves (e.g., `cubic-bezier(0.16, 1, 0.3, 1)`). NO `ease-in`.
- **Interactions:** Subtle scale-down (`scale: 0.99`, `translateY: -2px`) on button press, spring physics for hover states. Magnetic hover/liquid glass effects.

## Components
- **Icons:** `lucide-react`. No emojis.
