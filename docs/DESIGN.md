# Design — automaticStudyRoomReservation

> Reuses existing tokens. No new palette. Applies only to the optional status page at `collegeautomation.getcuria.us`.

## Source

- Primary: `../curia/.claude/skills/defi-landing-design/SKILL.md` (Curia video-hero landing system: React + Vite + Tailwind v4 + motion + lucide-react, navy/slate palette, Helvetica, rounded containers, glass cards).
- Secondary: `../Valance` brand tokens extracted from the Valance Figma and chat (Figtree typography, green primary). Valance `docs` and `00003106-ValanceV1.zip` are the reference.

When the two disagree, Curia is the shell and Valance is the accent. The automation has no UI; the design only matters for the optional status page.

## Tokens for the status page

### Typography

| Role | Token | Value |
|---|---|---|
| Display and headings | Figtree ExtraBold / Bold | `Display/L` 60px to `H1` 48px, `-2%` tracking, matching Valance spec |
| Body | Figtree Regular | `Body/Medium` 16px / 26px |
| Mono for logs | ui-monospace | timestamps and run ids |
| Font import | `@font-face` Figtree from Google Fonts | `font-display: swap` |

Curia's Helvetica remains for marketing pages. For this utility page, Figtree is the correct voice because the users are ICESI students, not Curia prospects.

### Palette

| Token | Value | Use |
|---|---|---|
| Primary | `#74B93C` | success badge, primary button, accent ring |
| Primary hover | `#86C957` | hover |
| Primary light | `#E8F6DB` | success background |
| Charcoal 900 | `#111827` | headings on light |
| Charcoal 700 | `#374151` | body text |
| Gray 200 | `#E5E7EB` | card border |
| Gray 50 | `#F8FAFC` | page background |
| White | `#FFFFFF` | cards |
| Success | `#22C55E` | last run succeeded |
| Error | `#EF4444` | last run failed |
| Warning | `#F59E0B` | retry or rate limited |

Do not introduce purple, teal, or any new brand color.

### Layout

- Single column, max `max-w-3xl`, centered, `bg-[#F8FAFC]` page, white rounded cards `rounded-2xl` with `border border-[#E5E7EB]`.
- Top nav: small, `collegeautomation.getcuria.us` on left, `ICESI` badge on right. No marketing hero. This is a utility page, not a landing.
- Hero section: one line status: `Last run: success at 2026-09-23 23:59 Bogota` plus `Next: 2026-09-24 18:00` and a `View screenshots` link.
- Cards: last 5 runs in a table (date, time range, account masked, result, screenshot link).
- Empty state: `No runs yet. Trigger manually from GitHub Actions.` with a CTA to `workflow_dispatch`.

### Components

Reuse from Curia `apps/web/src/components`:

- `Card`, `Section`, `Eyebrow`, `Reveal` from `ui.jsx` if you scaffold `apps/web`. Copy, do not fork.
- Icons from `lucide-react`: `CheckCircle`, `XCircle`, `Clock`, `Calendar`.
- Animation: no page-wide motion in v1. One subtle `whileInView` fade on the status card is enough.

## What not to design

- No marketing hero with video. No pricing table. No auth forms.
- No dark mode in v1.
- No custom illustration. Use Lucide icons only.

## Hosting note

The page is static. Build with `pnpm --filter web build` and deploy to Cloudflare Pages. Custom domain `collegeautomation.getcuria.us` is set in the Cloudflare dashboard for the `getcuria.us` zone. No Worker routing needed.
