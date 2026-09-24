# AGENTS.md — automaticStudyRoomReservation

> Repo: `automaticStudyRoomReservation`. Automates daily library room booking at `https://banner9.icesi.edu.co/ic_reservas` for a quiet 10 person work room, 08:00 to 20:00 Mon to Fri, with Playwright. Optional status page on `reservation.getcuria.us`.

## Stack and commands

- **Runtime:** Python 3.11 + Playwright (Python) for automation. Node 22 + pnpm 9 only for the optional status page (`apps/web`).
- **Automation (Python):**
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  playwright install chromium
  python main.py --headed        # local run with visible browser
  python main.py --dry-run       # no submit, screenshots only
  ```
- **Status page (optional, Node):**
  ```bash
  pnpm install
  pnpm --filter web dev          # http://localhost:5173
  pnpm --filter web build
  ```
- **Tests / checks:**
  ```bash
  ruff check . && ruff format --check .
  pytest -q
  pnpm --filter web typecheck
  ```

## Project structure

```
main.py                 # Playwright entry: login -> addReserve -> submit (6 blocks, 2h each)
core/
  config.py             # env + reservationTime.json loading
  reservation.py        # pure date/time helpers + split_into_blocks (unit-tested)
  browser.py            # Playwright browser factory
.github/workflows/
  reserve.yml           # cron at 23:59 America/Bogota
docs/
  SPEC.md               # functional spec (source of truth for behavior)
  ARCHITECTURE.md       # infra + deployment
  DESIGN.md             # design tokens reused from Curia / Valance
apps/web/               # optional status page for reservation.getcuria.us
credentials.json        # NEVER committed (gitignored)
reservationTime.json    # default schedule, committed as example only
```

## Conventions for agents

1. **English on disk.** Code, comments, commit messages, and docs are English only. Chat can be Spanish; files never.
2. **Laziest solution wins.** Reuse stdlib / existing helpers before adding deps. No abstraction with one implementation. No new dependency without asking.
3. **Credentials never touch git.** Read from `BANNER_USERNAME` / `BANNER_PASSWORD` env vars in CI. Local fallback is `credentials.json` (gitignored) or interactive prompt. Never log raw passwords. Mask in logs.
4. **Playwright is the only browser dep.** Do not reintroduce Selenium or webdriver-manager. Use `playwright install chromium` and `playwright.config` equivalent in Python.
5. **One shared helper for dates.** All callers use `core/reservation.py:get_next_reservation_date` and `split_into_blocks`. Do not duplicate day-mapping or block-splitting logic. Weekend skip (Sat, Sun to Mon) lives in the same helper.
6. **Every non-trivial change needs a runnable check.** One `pytest` case or an `assert` in `__main__` is enough. No test scaffolding for one-liners.
7. **Design reuse.** Optional web UI reuses tokens from `curia/.claude/skills/defi-landing-design/SKILL.md` and Valance typography (Figtree) / palette (`#74B93C` primary). See `docs/DESIGN.md`. Do not invent a new palette.
8. **Domain.** Production status page, if shipped, is `reservation.getcuria.us` (Cloudflare, `getcuria.us` zone). No other domain without approval.
9. **Commits.** Conventional Commits. No push to `main` without explicit user approval. Never commit `.env`, `credentials.json`, `encryption_key.key`, or screenshots with session cookies.
10. **Verify before claiming done.** Run the command you changed and paste output, or explain why it cannot run offline (`banner9` is intranet-only).

## What not to do

- Do not add Terraform, multi-cloud, service mesh, or observability stack. This repo is a cron + a script.
- Do not store credentials in Firestore/Supabase unless the spec explicitly upgrades to multi-tenant.
- Do not add em dashes or en dashes to any output. Use periods or commas.
- Do not create Artifact pages. Write local files instead.

## Secrets and local setup

Create `.env` (gitignored):

```
BANNER_USERS_JSON=[{"username":"1111542730","password":"..."}, ...accounts]
RESERVATION_ACTIVITY=Reunión
RESERVATION_PEOPLE=10
# RESERVATION_ROOM is optional. With people=10 the portal offers the 10 person
# room "Sala de estudio 204BI"; leave it empty to pick the only offered room.
```

Single account fallback for local dry run:

```
BANNER_USERNAME=1111542730
BANNER_PASSWORD=your_password
```

Or use `credentials.json`:

```json
{ "username": "1111542730", "password": "your_password" }
```

And `reservationTime.json` (optional override, otherwise 08:00 to 20:00 split into 6 blocks is auto-generated):

```json
[{ "day": "Monday", "startTime": "08:00", "endTime": "10:00" }]
```

GitHub Actions secrets: `BANNER_USERS_JSON` (required for 6 blocks), optionally `BANNER_USERNAME` / `BANNER_PASSWORD` for single block fallback. See `docs/ARCHITECTURE.md`.

## References

- Target site: `https://banner9.icesi.edu.co/ic_reservas/login` and `/addReserve`
- Sibling design source: `../curia/.claude/skills/defi-landing-design/SKILL.md` and `../Valance/docs` (Figtree + `#74B93C` palette)
- Prior implementation (archived): `git show 0da084c:studyRoomReservation.py` (Selenium, now replaced)
