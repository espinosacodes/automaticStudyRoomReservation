# Architecture — automaticStudyRoomReservation

> Companion to SPEC.md. Minimal infra: a Python script plus a cron. No servers to babysit.

## Overview

```
GitHub Actions (cron 23:59 Bogota)
  -> checkout -> setup-python -> pip install -> playwright install chromium
  -> python main.py (env secrets)
  -> screenshots artifact + log
  -> optional: upload status.json to R2 / Pages for reservation.getcuria.us
```

Local:
```
developer -> python main.py --headed --dry-run -> screenshots
```

## Components

| Piece | Tech | Why |
|---|---|---|
| Automation | Python 3.11 + `playwright` | Replaces Selenium. One dep, official browser install, headless by default in CI |
| Date helper | `core/reservation.py` pure function | Unit-testable without a browser |
| Browser factory | `core/browser.py` | One place for headless, timeout, user-agent |
| Config | `core/config.py` | Loads `reservationTime.json` plus env overrides. No new dep |
| Cron | `.github/workflows/reserve.yml` | Free, scales to zero, no server. Cloudflare cron is alternative but Actions is simpler |
| Status page (optional) | Vite + Tailwind v4 + motion, Cloudflare Pages | Reuses curia pattern. `reservation.getcuria.us` via existing `getcuria.us` zone |

## Data flow

1. Load credentials: parse `BANNER_USERS_JSON` (need 6 entries for 08:00 to 20:00). Fallback to single `BANNER_USERNAME`/`BANNER_PASSWORD` or `credentials.json` for dry run. Mask in logs.
2. Compute next weekday. Skip Saturday and Sunday to Monday. Split `08:00` to `20:00` into six 2 hour blocks via `split_into_blocks`. If `reservationTime.json` is present it overrides the auto split.
3. For each `(date, start, end, credential)` in order: `browser.new_context()` -> `page.goto(login)` -> fill and submit -> wait for `Bienvenido` -> `page.click(AGREGAR RESERVA)` -> fill `addReserve` form with that block and `RESERVATION_ROOM` -> screenshot before and after -> assert -> close context. Continue on single block failure.

## Secrets

- Local: `credentials.json` (gitignored) or `.env`.
- CI: GitHub repository secrets `BANNER_USERNAME`, `BANNER_PASSWORD`, optionally `BANNER_USERS_JSON`.
- Never log passwords. Mask usernames in logs.
- No encryption file on disk. The old `cryptography` + `encryption_key.key` pattern is dropped; env vars are the secret store.

## Deployment

### GitHub Actions

`.github/workflows/reserve.yml`:

```yaml
on:
  schedule: [{ cron: '59 4 * * *' }]  # 23:59 America/Bogota = 04:59 UTC
  workflow_dispatch:
concurrency: { group: reserve, cancel-in-progress: false }
jobs:
  reserve:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt && playwright install chromium --with-deps
      - run: python main.py
        env:
          BANNER_USERNAME: ${{ secrets.BANNER_USERNAME }}
          BANNER_PASSWORD: ${{ secrets.BANNER_PASSWORD }}
          BANNER_USERS_JSON: ${{ secrets.BANNER_USERS_JSON }}
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: screenshots, path: "*.png" }
```

Timezone note: GitHub cron is UTC only. Use `59 4 * * *` for 23:59 Bogota (UTC-5, no DST). Verify around DST edge if university changes window.

### Cloudflare (status page only)

- Reuse `curia/wrangler.jsonc` pattern. Target `reservation.getcuria.us` as custom domain on Pages.
- Account `b080a52ee18c00011e5ed3b151545943` already owns `getcuria.us`.
- No Worker needed unless you want an API. Static JSON is enough for v1.
- Deploys only on `main` push, manual trigger otherwise.

## What we do not build

- No Terraform, no GKE, no service mesh, no observability stack.
- No queue. One cron, one run at a time.
- No database for reservations. The portal is the source of truth.
- No auth on the status page in v1.

## Failure handling

- Per block isolation: login timeout retries once with next credential for that block, else mark block failed and continue to next block. One block failing does not abort the whole day, because each block uses a separate account and the 2 hour limit is per user anyway.
- Weekend skip: if target is Sat or Sun, exit 0 without booking.
- Form validation error: screenshot plus log per block, continue.
- Network flake: Playwright `wait_for_selector` timeout 10s, no job-level retry in v1.

## Alternatives considered

- Keep Selenium: rejected, Playwright is faster, auto-waits, single `playwright install` instead of `webdriver-manager`.
- Cloudflare Workers cron with browser: rejected, Workers cannot run Playwright. Would need a container service for no benefit.
- Supabase for credential vault: rejected for v1, adds infra for a single secret. Revisit only if you need a UI for friends to self-serve credentials.
