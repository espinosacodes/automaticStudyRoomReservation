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

- `WeekCalendar`: Calendly-style poll. Left rail (date, window, room), SUN–SAT
  columns with hour rows, hatched weekends, booked 2h chips spanning two rows
  with the PDF link, bottom bar with held count and a dark Run now button.
  Each day column owns its cells; never use grid auto-placement across header
  and body trees.
- `RunsHistory`: pricing-style cards in a grid, latest run highlighted with an
  orange border and a Latest badge, blocks as check rows (green check booked,
  dash skipped, cross failed, clock dry run).
- `ArchitectureDiagram`: inline SVG flow — accounts and viewer (orange),
  compute (blue), dashed routes box listing the six blocks, dispatch Cron
  (blue), Data & Storage column (pink), Worker coordinator (blue), browser
  mock showing the page. Size every node to its longest label.

## What not to design

- No dark mode in v1.
- No second accent color. No gradients or glassmorphism.
- No custom illustration. Use Lucide icons only.

## Hosting note

Build with `pnpm --filter web build` and deploy the `reservation` Worker with
`wrangler deploy`. Custom domain `reservation.getcuria.us` is a Worker custom
domain on the `getcuria.us` zone. Booking PDFs ship inside `dist/bookings/`
and are served only to logged-in sessions.
