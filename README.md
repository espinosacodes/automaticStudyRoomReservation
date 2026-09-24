# automaticStudyRoomReservation

Automates the nightly reservation of a 10 person library study room at ICESI
(`https://banner9.icesi.edu.co/ic_reservas`), 08:00 to 20:00 Monday to Friday,
using Playwright. A small status page lives at
[reservation.getcuria.us](https://reservation.getcuria.us).

The portal caps each account at 2 hours per booking, so the day is split into
six 2 hour blocks and each block uses a different account from a rotation pool.

## How it works

1. GitHub Actions fires at `23:59 America/Bogota` (`59 4 * * *` UTC).
2. `main.py` computes the next weekday (weekends roll forward to Monday),
   splits 08:00 to 20:00 into six 2 hour blocks, and logs in per block with a
   different account.
3. Each block fills the `addReserve` form, screenshots before and after, and
   submits. One failing block never aborts the day.
4. Screenshots and `status.json` are uploaded as artifacts and the status page
   is redeployed with the fresh data.

## Stack

- **Automation:** Python 3.11 + Playwright (`main.py`, `core/*`).
- **Status page:** Vite + React + Tailwind v4 + motion + lucide-react
  (`apps/web`), deployed to Cloudflare as the `reservation` Worker with the
  `reservation.getcuria.us` custom domain (`wrangler.jsonc`).

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
playwright install chromium
```

Add credentials (gitignored), then dry run:

```bash
cp credentials.example.json credentials.json   # then edit it
python main.py --headed --dry-run
```

`credentials.json` can be a single `{ "username", "password" }` object or a JSON
array for the rotation. CI reads `BANNER_USERS_JSON` instead.

## Portal notes (verified against the live site)

- The `addReserve` route is a two step Material UI wizard. Step 1 is the
  requester info (`CONTINUAR`); step 2 holds actividad, fecha, horas, número de
  personas, espacio físico, observación (`FINALIZAR`).
- It must be opened by clicking the `AGREGAR RESERVA` card. Navigating the URL
  directly, or using the sidebar link, drops the in-memory session and crashes
  the route.
- Activities are: Capacitación, Examen, Examen final, Examen multitudinario,
  Práctica de Laboratorio, Reunión, Seminario, Taller. There is no "Study
  Session", so the default is `Reunión`.
- `Número de personas` filters the room list. With `10` the portal offers
  `Sala de estudio 204BI [Capacidad espacio: 10]`, the 10 person room. If that
  room is already booked for a block, the block is reported as `unavailable`.
- Valid reservation hours are Monday to Friday 07:00 to 21:00.
- Each user can hold only one 2 hour block per day, so six blocks need six
  distinct accounts. The runner never reuses an account within a run and frees
  one back to the pool when its block is unavailable.
- `FINALIZAR` only validates. A confirmation modal then appears and `CONFIRMAR`
  is what creates the reservation, after which the portal shows
  "Tu reserva ha sido registrada con éxito".

## Checks

```bash
ruff check . && ruff format --check .
pytest -q
pnpm --filter web typecheck
pnpm --filter web build
```

## Deploy

```bash
pnpm install
pnpm --filter web build
pnpm exec wrangler deploy     # needs CLOUDFLARE_API_TOKEN
```

See `docs/SPEC.md`, `docs/ARCHITECTURE.md`, and `docs/DESIGN.md` for details.

## Required GitHub configuration

Secrets: `BANNER_USERS_JSON` (six accounts, JSON array), `CLOUDFLARE_API_TOKEN`.
Variables: `RESERVATION_ROOM`, `RESERVATION_ACTIVITY`.
