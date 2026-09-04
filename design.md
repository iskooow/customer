# Design — Customer Records Management

A locked design system for this app. Every page redesign reads this file before
emitting code. Do not regenerate per page — extend or amend this file when the
system needs to grow.

## Genre

modern-minimal — sharpened. Internal B2B admin: confident sans display, quiet
paper, brand-blue accent used as signal only (≤ 5 % per viewport), hairline
rules, pill primary CTA.

## Mood

sharp / technical. Tighter display tracking, mono numerals & kickers, crisp
data surfaces, declarative copy.

## Macrostructure family

Pick one base macrostructure per page-type family. Pages within a family share
the family's shape; they vary only in component archetypes.

- App shell:  **Workbench** — sidebar command center + topbar; dense ledger
  tables are the work surface.
- Dashboard:  **Stat-Led** — giant numbers lead; alert cards qualify them.
- List pages: **Workbench variant** — dense table, sticky header, mono
  numerals, status badges as data.

## Theme

```css
--color-paper:      oklch(0.99 0.002 242)   /* near-white, blue-tinted */
--color-paper-2:    oklch(0.97 0.004 242)   /* subtle panel */
--color-ink:        oklch(0.22 0.024 248)   /* deep blue-black */
--color-ink-2:      oklch(0.45 0.02 246)    /* muted ink */
--color-rule:       oklch(0.90 0.006 242)   /* hairline */
--color-accent:     oklch(0.588 0.158 242)  /* brand blue (sky-600) */
--color-accent-ink: oklch(0.99 0 0)         /* white on accent */
--color-focus:      oklch(0.707 0.165 254.624) /* sky-400 focus ring */

/* status — restrained tints on paper, ink text; only for badges */
--color-success: oklch(0.62 0.13 155)
--color-warning: oklch(0.75 0.15 80)
--color-danger:  oklch(0.58 0.19 25)
--color-info:    oklch(0.60 0.12 240)
```

## Typography

- Display: "Inter Tight", weight 600, tracking `-0.03em`
- Body:    "Inter", weight 400
- Mono:    "JetBrains Mono", weight 500 — kickers, metrics, numerals, table data
- Type scale anchor: `--text-display: clamp(2rem, 3vw + 0.75rem, 3.25rem)`

## Spacing

4-point named scale. The values live in `static/css/tokens.css`. Pages must use
named tokens (`var(--space-md)`), never raw values.

## Motion

- Easings: `--ease-out: cubic-bezier(0.16, 1, 0.3, 1)`
- Durations: `--dur-short: 150ms` (micro), `--dur-md: 220ms` (standard)
- Reveal pattern: none — pages are composed, not animated
- Reduced-motion fallback: opacity-only, ≤ 150 ms

## Microinteractions stance

- silent success — no celebratory toasts
- focus-visible rings only; hover delay 800 ms on tooltips, 0 ms on controls
- every interactive element carries 8 states: default, hover, focus,
  focus-visible, active, visited, disabled, aria-current

## CTA voice

- Primary CTA: pill, accent fill, `--color-accent-ink` text, focus ring
- Secondary CTA: pill, paper fill, hairline border, ink text

## Per-page allowances

- App pages MUST NOT use enrichment — function carries the page.
- Data (counts, days-left, statuses) renders in mono.

## What pages MUST share

- The wordmark block (monogram + wordmark, paper-on-accent tile)
- Accent placement (≤ 5 % per viewport)
- Display + body + mono fonts
- CTA voice (pill shape, radius, padding rhythm)
- Table voice (hairline rows, mono numerals, sticky header)

## What pages MAY differ on

- Dashboard vs list macrostructure (Stat-Led vs Workbench-ledger)
- Sidebar active-state treatment
- Hero-less app pages have no marquee / hero

## Exports

### tokens.css — shipped at `static/css/tokens.css`

```css
:root {
  --color-paper:      oklch(0.99 0.002 242);
  --color-paper-2:    oklch(0.97 0.004 242);
  --color-ink:        oklch(0.22 0.024 248);
  --color-ink-2:      oklch(0.45 0.02 246);
  --color-rule:       oklch(0.90 0.006 242);
  --color-accent:     oklch(0.588 0.158 242);
  --color-accent-ink: oklch(0.99 0 0);
  --color-focus:      oklch(0.707 0.165 254.624);

  --color-success:    oklch(0.62 0.13 155);
  --color-warning:    oklch(0.75 0.15 80);
  --color-danger:     oklch(0.58 0.19 25);
  --color-info:       oklch(0.60 0.12 240);

  --font-display: "Inter Tight", "Inter", system-ui, sans-serif;
  --font-body:    "Inter", system-ui, sans-serif;
  --font-mono:    "JetBrains Mono", ui-monospace, SFMono-Regular, monospace;

  --space-3xs: 0.25rem;  --space-2xs: 0.5rem;  --space-xs: 0.75rem;
  --space-sm:  1rem;     --space-md:  1.5rem;  --space-lg: 2rem;
  --space-xl:  3rem;     --space-2xl: 4.5rem;  --space-3xl: 7rem;

  --text-xs: 0.75rem;  --text-sm: 0.875rem; --text-md: 1.125rem;
  --text-lg: 1.375rem; --text-xl: 1.75rem;  --text-2xl: 2.25rem;
  --text-display: clamp(2rem, 3vw + 0.75rem, 3.25rem);

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --dur-short: 150ms;
  --dur-md: 220ms;
  --radius-card: 8px;
  --radius-input: 6px;
  --radius-pill: 999px;

  --shadow-sm: 0 1px 2px oklch(0.22 0.024 248 / 0.04);
  --shadow-md: 0 4px 12px oklch(0.22 0.024 248 / 0.06);
}
```

### Tailwind CDN mapping (this project)

`templates/base.html` loads `tokens.css` first, then maps tokens into
`tailwind.config` as `var(--token)` references so Tailwind emits runtime-
resolved values. Single source of truth stays in `tokens.css`.