# DESIGN.md: Legal Analyzer App

## Brand and Mood
- **3 Words for the Mood:** Editorial, Authoritative, Restrained.
- **3 Words to Avoid:** Playful, Glossy-SaaS, Cluttered.
- **Theme:** Warm Light Theme (Archival paper aesthetic with precision ink typography).

---

## Colour Tokens

Every color token is strictly derived from legal document paper stock and archival law reviews. No gradients, no glassmorphism, and no secondary decorative accent hues.

```css
:root {
  /* Canvas & Structural Backgrounds */
  --bg-page: #FBFBF9;          /* Warm off-white, unbleached legal rag paper */
  --bg-surface: #FFFFFF;       /* Crisp white surface for cards and table rows */
  --bg-subtle: #F4F4F0;        /* Inset table headers, muted callout boxes */

  /* Text & Ink Tokens */
  --text-main: #111827;        /* Near-black legal ink (high contrast, WCAG AAA) */
  --text-muted: #6B7280;       /* Neutral docket gray for metadata and captions */
  --text-inverse: #FFFFFF;     /* Contrast text for primary buttons & dark badges */

  /* Hairline Borders */
  --border-subtle: #E5E5E0;    /* 1px hairline rule separating sections and rows */
  --border-dark: #111827;      /* 1px dark hairline for active borders and focus */

  /* Single Accent Palette: Deep Navy */
  --accent-primary: #1B2A4A;   /* Deep Navy: Used solely for primary CTA & header */
  --accent-hover: #0F172A;     /* Navy hover state */
  --accent-tint: #EEF2F6;      /* 4% navy tint for table selection / active state */

  /* Semantic Risk Indicators (Functional, never decorative) */
  --risk-low: #166534;         /* Forest green: standard/balanced term */
  --risk-low-bg: #F0FDF4;
  --risk-low-border: #BBF7D0;

  --risk-medium: #854D0E;      /* Muted amber: ambiguous or one-sided clause */
  --risk-medium-bg: #FEFCE8;
  --risk-medium-border: #FEF08A;

  --risk-high: #991B1B;        /* Crimson red: severe exposure or missing term */
  --risk-high-bg: #FEF2F2;
  --risk-high-border: #FECACA;
}
```

---

## Typography

Strict hierarchy inspired by legal memorandums and classic law journals. Contrast is created through font pairings, scale, and uppercase tracking rather than multiple colors.

- **Heading Font:** `Playfair Display` (serif) — Georgia fallback. Weight: 400 (normal) and 600 (semibold).
- **Body & UI Font:** `Inter` (clean sans-serif) — IBM Plex Sans / system-ui fallback. Weight: 400 (regular), 500 (medium), 600 (semibold).
- **Monospace Font (Clauses & Citations):** `JetBrains Mono` / `Courier New` for raw extracted text and statutory references.

### Scale & Hierarchy
| Level | Font Family | Size | Weight | Line Height | Tracking | Usage |
|---|---|---|---|---|---|---|
| Display / Hero | Serif | 44px (2.75rem) | 400 Regular | 1.15 | -0.02em | Landing page hero statement |
| H1 (Page Title) | Serif | 32px (2.00rem) | 600 Semibold | 1.20 | -0.015em | Dashboard & Document header |
| H2 (Section Head) | Serif | 22px (1.375rem) | 600 Semibold | 1.30 | -0.01em | Table & Card group headings |
| H3 (Card / Group) | Serif | 17px (1.0625rem) | 600 Semibold | 1.35 | 0em | Clause card titles & matrix keys |
| Subheading / Eyebrow | Sans | 11px (0.6875rem) | 700 Bold | 1.40 | +0.12em (ALL CAPS) | Category labels, badge headers |
| Body Main | Sans | 14px (0.875rem) | 400 Regular | 1.55 | 0em | Paragraphs, explanations, notes |
| Body Small / Meta | Sans | 12px (0.75rem) | 400 / 500 | 1.45 | 0em | Table cell text, timestamps, tags |
| Legal Disclaimers | Sans | 11px (0.6875rem) | 400 Regular | 1.50 | 0.01em | Mandatory disclaimer blocks |

---

## Spacing and Layout

- **Base Unit:** 4px grid (scale: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px).
- **Max Widths:**
  - Landing Marketing: `max-w-5xl` (1024px) for reading focus.
  - Document & Split-Pane Workspace: Full viewport `w-full` with 16px padding on mobile, 32px on desktop.
  - Reports (Print Mode): `max-w-4xl` (896px) centered, mimicking standard Letter / A4 margin proportions.
- **Surfaces & Borders:** Flat surfaces only. **1px hairline solid borders** (`border border-[var(--border-subtle)]`). **0px border-radius** on core containers, cards, tables, and buttons (sharp editorial corners or maximum `rounded-xs` / 2px).
- **Breakpoints:**
  - Mobile: `390px` (iPhone 14/15 base).
  - Tablet: `768px` (iPad vertical / dual column collapse).
  - Desktop: `1440px` (high-density split-pane contract view).

---

## Components

### 1. Buttons
- **Primary:** Deep navy background (`#1B2A4A`), white text, 1px border (`#1B2A4A`), sharp corners (`rounded-none`), height 36px (compact) or 44px (touch). Hover: `#0F172A`. No shadows.
- **Secondary / Outline:** White or transparent background, `#111827` ink text, 1px hairline border (`#E5E5E0`), hover background `#F4F4F0`.
- **Destructive:** White background, Crimson text (`#991B1B`), 1px border (`#FECACA`), hover background `#FEF2F2`.

### 2. Cards & Split Panes
- Pure white background (`#FFFFFF`), 1px border (`#E5E5E0`), zero box-shadow (`shadow-none`).
- Generous internal padding: 24px desktop, 16px mobile.
- Section dividers: 1px hairline horizontal rule (`#E5E5E0`).

### 3. Tables (First-Class Primitive)
- Generous row height: `min-h-[48px]`.
- Sticky header with `#F4F4F0` background and 1px bottom border.
- Right-aligned numerical columns (scores, clause counts, dates).
- Hover state: subtle background change to `#FBFBF9`. No zebra striping.

### 4. Risk & Confidence Badges
- Inline rectangular badges: `rounded-none`, uppercase font-mono or font-sans tracking-widest, size `10px` or `11px`.
- High Risk: Red border (`#FECACA`), light red background (`#FEF2F2`), red text (`#991B1B`).
- Medium Risk: Amber border (`#FEF08A`), light amber background (`#FEFCE8`), dark amber text (`#854D0E`).
- Low Risk: Green border (`#BBF7D0`), light green background (`#F0FDF4`), forest green text (`#166534`).
- Confidence Score: Format `CONFIDENCE: 94%` or `SAFETY SCORE: 72/100`.

### 5. Empty & Loading States
- Never show generic spinners or emoji ("No files yet 🎉").
- Skeletons: Exact wireframe shapes matching real table rows or split-pane text blocks using subtle pulsing background (`#E5E5E0`).
- Empty State: Centered 1px hairline border box with formal legal tone: *"No documents currently under review. Upload an NDA, SaaS Agreement, or Service Contract to begin clause triage."*

---

## Motion Rules

- **Principle:** Restrained and purpose-driven. Movement only occurs when it reflects physical paper or state progression.
- **Duration & Easing:**
  - Micro-interactions (hover, drawer toggle): 150ms ease-out.
  - Page transitions: None or 200ms instantaneous fade.
  - Clause highlight sync: Smooth scroll into view (250ms cubic-bezier(0.2, 0, 0, 1)) when clicking a flagged clause from the audit pane.
- **Accessibility:** Full `prefers-reduced-motion` compliance. All animated shifts become instantaneous cuts.

---

## Imagery & 3D Guidelines

- **No Stock People:** Never use photographs of smiling actors holding laptops, abstract glowing neon brain graphics, or 3D cartoon avatars.
- **Document Realism:** Hero imagery is grounded in physical paper contracts, letterpress debossing, high-resolution macro photography of contract signatures, or a tactile 3D paper memorandum.
- **3D Hero Asset:** A physically rendered legal document on a desk with directional warm studio lighting, responding with a gentle tilt (max 3 degrees) to cursor movement, with an immediate flat SVG fallback on mobile viewports (<768px).

---

## Do and Do Not

### DO
1. **DO** maintain strict 1px hairline borders and flat surfaces throughout every dashboard view.
2. **DO** include the visible statutory disclaimer on every screen and exportable memorandum.
3. **DO** present tables as high-density, cleanly aligned data grids with right-aligned numerical values.
4. **DO** pair classical serif headlines with sharp, legible sans-serif UI typography.
5. **DO** design custom wireframe skeleton loaders shaped like the real content.

### DO NOT
1. **DO NOT** use purple, violet, cyan, or neon gradients anywhere in the application.
2. **DO NOT** add glossy drop shadows, frosted glassmorphism, or rounded 24px corners.
3. **DO NOT** use decorative icons inside circular pastel bubbles next to features.
4. **DO NOT** write playful, casual, or exclamation-heavy copy (e.g., "Woohoo! Analysis done!").
5. **DO NOT** hide or obscure the AI confidence score or the warning that this is not a licensed attorney.
