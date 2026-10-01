# Design — automaticStudyRoomReservation

> Applies to the status page at `reservation.getcuria.us`. Override approved:
> the page uses the Cloudflare product-page system, not the old green palette.
> Source of truth is `apps/web/src/styles.css` plus the
> `cloudflare-design-system` skill (`.claude/skills/cloudflare-design-system/`).

## Source

- Primary: Cloudflare Workers product pages (warm paper `#FFFBF5`, orange
  `#F6821F` actions, `#313131` ink, dot grid, hairline tables, pill controls,
  engineering diagrams). No Tailwind; tokens live in `styles.css`.
- Reference screens: Calendly meeting-poll week view (sidebar + SUN–SAT grid +
  bottom action bar), Cloudflare primitives grid, pricing tiers with a featured
  card, and the platform infrastructure flow diagram.

## Tokens for the status page

### Typography

| Role | Token | Value |
|---|---|---|
| Display and headings | Inter 650 | `clamp(34px, 5vw, 52px)`, `-4.5%` tracking |
| Body | Inter Regular | 14px / 1.6 |
| Mono for data | ui-monospace stack | times, room codes, account ids |

### Palette

| Token | Value | Use |
|---|---|---|
| Paper | `#FFFBF5` | page canvas + dot grid |
| Ink | `#313131` | headings, body |
| Primary | `#F6821F` | primary button, active pill, booked chips |
| Diagram blue | `#2F7FD0` | compute / dispatch / coordinator nodes |
| Diagram pink | `#B832A0` | data and storage nodes |
| Success | `#2F7D4F` | booked check |
| Error | `#C0392B` | failed block |
| Warning | `#B26A00` | partial, dry run |

Success green is reserved for check marks, never for primary actions.

### Layout

- Page column, max 1080px. Sticky topbar with brand left, auth right.
- Hero with stat grid, then sections: Reservations (receipt table), Week
  (meeting-poll calendar), How this runs (flow diagram), History (run cards).
- Date picker is a pill tab switcher, not a select.

### Components

- `Sidebar`: a vertical rail replacing the old topbar. Brand, section links
  (Reservations, Week, Run history, How it works), the signed-in member, ICESI
  portal, and sign out. The active section is tracked with an
  `IntersectionObserver` scrollspy. Below 980px it collapses to a top rail with
  the links in a single row.
- Glass surfaces: the sidebar is not the only glass panel. The stat grid, the
  bookings table, the week calendar, the run cards, the diagram, and the pill
  tabs are all `data-optical` with a translucent surface (`--glass`) and a
  frosted `backdrop-filter`, so the same refraction reads across the page.
  Six plates on the dashboard.
- `Atmosphere` and `GlassOptics`: a drifting mesh gradient, with a real WebGL
  refraction pass (`@ybouane/liquidglass`) over inert plates positioned on
  `[data-optical]` elements. Text always stays in the DOM above the optics.
  If WebGL is unavailable the plates are dropped and the frosted CSS surfaces
  remain. The optics re-scan on element identity changes, not just counts,
  because panels mount and get replaced as data loads.
- `WeekCalendar`: Calendly-style poll. Left rail (date, window, room), SUN–SAT
  columns with hour rows, hatched weekends, booked 2h chips spanning two rows
  with the PDF link, bottom bar with held count and a dark Run now button.
  Each day column owns its cells; never use grid auto-placement across header
  and body trees. Day headers are buttons that select the day. Week navigation
  (previous, next, This week) lives in the section header and only changes the
  week shown, never the selected reservations day.
- `RunsHistory`: pricing-style cards in a grid, latest run highlighted with an
  orange border and a Latest badge, blocks as check rows (green check booked,
  dash skipped, cross failed, clock dry run).
- `ArchitectureDiagram`: inline SVG flow — accounts and viewer (orange),
  compute (blue), dashed routes box listing the five blocks, dispatch Cron
  (blue), Data & Storage column (pink), Worker coordinator (blue), browser
  mock showing the page. Below 860px it swaps to a readable stacked list
  instead of a shrunken SVG. Size every node to its longest label.

### Responsive

Verified with assertions from 320px to 1440px, no horizontal page scroll.

| Width | Behaviour |
|---|---|
| over 980px | sidebar rail, four stat columns |
| 981px to 981px | sidebar becomes a top rail, stats 2 up |
| 720px and below | bookings table stacks as label/value rows |
| 700px and below | weekend columns drop out of the week grid, run cards go single column |
| 360px and below | stats fall to a single column |

The stat grid uses explicit `repeat(4/2/1)` columns rather than `auto-fit`, so
there is never an orphan cell leaving a tinted gap. Anything that genuinely
cannot shrink (the week grid) lives inside its own `overflow-x` scroller; the
page itself must never scroll sideways.

### Layering

Paint order matters more than z-index numbers here. The atmosphere and the
optical layer are siblings of the shell, not children of it: a positioned
child with `z-index: 0` inside the shell paints above the shell's static
content and hides the page. Keep background and optics outside the content
container, and give the content container its own stacking level.

## What not to design

- No dark mode in v1.
- No second accent color. No gradients or glassmorphism.
- No custom illustration. Use Lucide icons only.

## Hosting note

Build with `pnpm --filter web build` and deploy the `reservation` Worker with
`wrangler deploy`. Custom domain `reservation.getcuria.us` is a Worker custom
domain on the `getcuria.us` zone. Booking PDFs ship inside `dist/bookings/`
and are served only to logged-in sessions.
