---
name: cloudflare-design-system
description: Build or restyle frontend UI in the Cloudflare product-page design language, the system used across Santiago's projects. Covers the warm paper canvas, the orange action colour, the dot grid, pill controls, hairline tables, status pills, the engineering architecture diagram, and the week calendar. Use this whenever a request involves building a page, dashboard, status page, admin view, or any React UI that should match Santiago's house style, and also when asked for "the Cloudflare look", "our design system", or a "clean/light dashboard". Trigger it even when the request only says "make a page" or "build a UI" without naming a style, because these projects default to this system.
---

# Cloudflare design system

A light, engineering-flavoured UI system. It reads like a Cloudflare product
page: warm off-white canvas, one confident orange for action, near-black ink,
thin hairlines, pill-shaped controls, and diagrams that look like real
architecture rather than decoration.

The reference implementation lives in
`apps/web/src/styles.css` in `automaticStudyRoomReservation`. That file is the
source of truth for exact values. This skill explains the system and the
reasoning, so new work stays consistent rather than copying a snapshot.

## Why this system

It is deliberately restrained. There is one accent colour and it is reserved for
action and focus, so a page reads as a tool rather than a marketing page. The dot
grid gives the empty space texture without a gradient or an image. Hairlines
replace card shadows for structure, which keeps dense data readable. Follow the
reasoning, not just the hex values, because a page that uses the tokens but
scatters orange everywhere will feel wrong even though every value is correct.

## Colour

Define these as CSS custom properties on `:root`, never as one-off literals.

| Token | Value | Use |
|---|---|---|
| `--paper` | `#fffbf5` | page canvas |
| `--paper-deep` | `#f7f2e9` | table headers, hour gutters, legend strips |
| `--ink` | `#313131` | primary text |
| `--ink-soft` | `#595959` | body copy, descriptions |
| `--ink-faint` | `#8c8c8c` | labels, metadata, eyebrows |
| `--orange` | `#f6821f` | primary action, active state, focus |
| `--orange-hover` | `#e0721a` | hover on action |
| `--orange-soft` | `#fef0e3` | booked chips, accent node fill |
| `--orange-line` | `#f8cfa4` | border of an orange-soft surface |
| `--line` | `#e8e0d4` | default hairline |
| `--line-strong` | `#d9cfbe` | diagram edges, ghost button border |
| `--dot` | `#e3d9c9` | dot grid colour |

Status colours are separate from the accent and never borrow orange:

| Token | Value | Meaning |
|---|---|---|
| `--ok` / `--ok-soft` | `#2f7d4f` / `#e8f3ec` | succeeded |
| `--warn` / `--warn-soft` | `#b26a00` / `#fdf1dc` | partial, dry run |
| `--bad` / `--bad-soft` | `#c0392b` / `#fbeae7` | failed |
| `--busy` | `#6b7280` | unavailable, pending, neutral |

The rule that keeps it coherent: **orange means "you can act here" or "this is
the thing we hold"**. If orange is on a surface that is neither actionable nor a
primary highlight, it is a mistake.

## Canvas and dot grid

The page background is the paper colour plus a radial dot grid. This gives the
large empty areas in these utility pages something to sit on.

```css
body {
  background-color: var(--paper);
  background-image: radial-gradient(var(--dot) 1px, transparent 1px);
  background-size: 22px 22px;
  background-position: -1px -1px;
}
```

Keep the grid subtle. If it is visible as a pattern rather than as texture, the
contrast between `--dot` and `--paper` is too high.

## Typography

System sans stack, no webfont fetch. A monospace family is used for anything
machine-generated: times, room codes, account ids, dates in tables, JSON paths.
That distinction matters, because it lets a reader tell data from prose at a
glance.

```css
--font-display: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-body:    'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
--font-mono:    ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, monospace;
```

- Body: `14px`, line-height `1.6`.
- Page title (`h1`): `clamp(34px, 5vw, 52px)`, weight `650`, line-height `1.06`, letter-spacing `-0.045em`.
- Section title (`h2`): `30px`, weight `650`, letter-spacing `-0.035em`.
- Stat value: `26px`, weight `650`, letter-spacing `-0.03em` (mono variant `20px`).
- Eyebrow: `11px`, weight `700`, uppercase, letter-spacing `0.14em`, `--orange`.
- Body copy: `--ink-soft`. Labels and metadata: `--ink-faint`.

## Shape and spacing

- Pills and buttons: fully rounded, `border-radius: 999px`.
- Cards and tables: `border-radius: 14px`.
- Fields: `border-radius: 10px`.
- Page column: `max-width: 1080px`, `padding: 0 24px 96px`.
- Section rhythm: `margin-top: 48px`.

Cards carry a hairline border and a very soft shadow, never a heavy one:

```css
--shadow-card: 0 1px 2px rgb(49 49 49 / 4%), 0 12px 32px -20px rgb(49 49 49 / 22%);
```

## Components

### Buttons

`.button` is orange fill, white label, min-height `40px`, padding `0 18px`,
weight `600`. `.button.ghost` is white with `--line-strong` border for the
secondary action, and it is the correct choice next to a primary button so the
two are not competing. Disabled state drops opacity to `0.45`.

### Stat grid

`.card-grid` is a 1px-gap grid where the gap reveals the `--line` background, so
the cells share hairlines instead of each owning a border. Each `.stat` is a
white cell with a small uppercase label, a large value, and an optional hint.
This is the standard way to open a dashboard: four facts, then detail below.

### Tables

Tables are the default for any list of records. Header row on `--paper-deep`,
uppercase `11px` labels, `13px` cells, hairline row dividers, hover on
`--paper`, and no zebra striping. Wrap in `.table-wrap` for the border and
radius. Machine values get `.mono`.

### Status pills

`.pill` with a tone class: `.ok`, `.warn`, `.bad`, `.busy`. `11px`, weight
`600`, rounded. Use them inline in a table cell so a row's outcome is scannable.
Always render the human label next to the colour, because colour alone fails for
colour-blind readers.

### Sidebar and liquid glass

Navigation is a left rail, not a topbar, with the section links, the signed-in
member, and sign out. Mark it `data-optical` so the glass layer refracts the
mesh gradient behind it.

Liquid glass is a real WebGL refraction pass (`@ybouane/liquidglass`) over inert
plates positioned on `[data-optical]` elements, with a drifting mesh gradient
(`@paper-design/shaders-react`) as the thing being refracted. Two rules keep it
from becoming a mess:

- **Semantic content stays in the DOM above the optics.** The plates are
  decorative and inert; text, links, and buttons live above them so they stay
  crisp, selectable, and accessible. Never render readable labels into the
  shader.
- **Degrade, do not break.** If WebGL is unavailable, drop the plates and keep
  the frosted CSS surface (`backdrop-filter`). Reduced-motion stops the mesh
  drift and freezes the heartbeat.

**The Layering Rule.** Put the atmosphere and the optical layer as siblings of
the content container, never inside it. A positioned child with `z-index: 0`
inside a container paints above that container's static content, which silently
hides the page behind the background. Give the content container its own
stacking level instead.

### Calendar

The week view is a flex row of day columns, each stacking its own time cells.
Do **not** build it with CSS grid auto-placement across separate header and body
trees: the browser will place cells into the wrong tracks and booked items drift
into the wrong day. One day column owns its cells, always.

For a meeting-poll feel, add a left rail with the facts (date, window, room),
SUN to SAT headers with day numbers, hour rows, hatched weekend columns, booked
blocks as chips spanning their rows with a colored left border, and a bottom bar
with the held count plus one dark action button. A two hour booking renders one
chip in its start cell sized to cover both rows; the covered cell stays empty.

### Pill tabs

Date or view pickers are a pill container (border, full radius, white) holding
plain buttons; the active one is orange fill with a white label. Use buttons
with `aria-pressed`, not a select, so all options stay visible.

### Run cards

History reads as pricing-style cards in a grid. The latest card gets an orange
border and a Latest badge. Each row is a feature-comparison row: a green check
for done, a dash for skipped, a cross for failed, a clock for pending. Keep the
rows compact and scannable.

### Architecture diagram

Diagrams are inline SVG, not images, drawn to look like real infrastructure:
a left-to-right flow of users, compute, a dashed routes box listing the actual
items, the dispatch namespace, a Data and Storage column, the coordinator, and
a browser mock showing the page. Columns get their own accent (orange for
actors, blue for compute and delivery, pink for data). Size every node to its
longest label; a box that fits the title but clips the sub-label is the most
common way these diagrams break. See
`references/architecture-diagram.md` for the node and edge helpers and the flow
pattern used in the reference implementation.

## Interaction

- One focus style: `outline: 2px solid var(--orange); outline-offset: 3px`.
- Transitions `150ms` to `240ms`, colour and opacity only.
- Entrance motion is a single subtle fade-and-rise on section reveal, via
  `motion` (the `motion/react` package). Nothing animates on scroll past its
  own section, and reduced-motion preferences must disable it.
- Never animate layout properties.

## Print

Reports and lists often need a PDF, and the browser's own print is enough. Hide
chrome with a `.no-print` class on the topbar, hero, diagram, calendar, and
footer, and keep only the record table. Reset the background to white and drop
card borders and shadows so the printout reads as a document.

## React conventions

- Plain React function components, one component per file, PascalCase file names.
- Styles live in the token stylesheet, not in utility-class soup. This system
  does not use Tailwind.
- Keep a small primitives module (`Section`, `StatCard`, `StatusPill`) rather
  than repeating markup.
- Keep data shaping out of the display component: a pure helper such as
  `collectBookings(runs)` builds the rows, the component renders them.
- Only claim a feature works after asserting on real output. Screenshots look
  convincing and hide wrong data. Prefer a check that reads the render tree,
  for example asserting which column a value landed in, over eyeballing an image.

## Do not

- Do not add a second accent colour.
- Do not use orange for body text or large fills beyond `--orange-soft`.
- Do not reintroduce a dark theme.
- Do not use heavy shadows, gradients, or glassmorphism.
- Do not use Tailwind for this system.

## Reference files

- `references/architecture-diagram.md`: node and edge helpers, the diagram
  pattern, and how to lay out groups and flow.
