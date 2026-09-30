# Fix reserve failures - ODD feature document

## Objective
Restore the scheduled `reserve` workflow to green for a fully free day, without changing booking behavior.

## Problem
Recent runs fail in three modes:
1. 2026-09-29 scheduled: all 5 blocks reach the confirmation dialog, then `CONFIRMAR` click times out. Screenshot shows the dialog open with a visible enabled CONFIRMAR button, so the locator `page.locator("[role='dialog']").first` likely picks a stale hidden picker dialog instead of the confirmation dialog.
2. 2026-09-30 scheduled: `Page.goto` to login times out for all 5 accounts. Portal returns HTTP 200 locally in 0.07s, so this is runner egress flakiness. Current `run_day` burns the whole account pool retrying the same network failure on the first block.
3. Recurring: `FINALIZAR` click or scroll times out on late blocks, and only 5 accounts exist for 6 blocks.

## Why
The 23:59 Bogota cron must book the next weekday before others take the rooms. Every red run loses the day.

## Scope
- `main.py` confirmation and submit flow only.
- `core/browser.py` and `core/reservation.py` helpers if needed for retry or timeout.
- Unit tests for new pure logic.
- Authorized: local edits and `pytest`, `ruff check`. Not authorized: push to `main`, PR creation, remote workflow rerun, credential changes.

## Constraints
- Keep Playwright as the only browser dep.
- Never log raw passwords. Mask usernames.
- English code and comments only. No em dashes.
- Do not commit `.env`, `credentials.json`, or screenshots with session data.

## Tasks
- [x] T1 Confirm dialog locator targets the confirmation dialog by text, not first dialog in DOM.
- [x] T2 Add bounded retry for `Page.goto` login with fail fast on infra failure so one network blip does not consume all accounts.
- [x] T3 Harden FINALIZAR and CONFIRMAR clicks with scroll into view and one forced retry, preserving `unconfirmed` semantics.
- [x] T4 Keep account pool intact on network errors and on `unavailable`, consume only on real booking attempts.
- [x] T5 Add or update unit tests for pool handling and dialog selection logic, run `pytest -q` and `ruff check`.
- [x] T6 Verify with dry run friendly check and report per task proof, plus note on the missing 6th account.

## Acceptance criteria
- Confirmation dialog is located by `Confirmacion de nueva reserva` text or CONFIRMAR button scope, never by first dialog index.
- A single `goto` timeout retries at most twice, then aborts the day as infra failure instead of burning 5 accounts.
- FINALIZAR and CONFIRMAR each scroll into view before click, with one forced retry on timeout.
- `pytest -q` and `ruff check .` pass locally.
- No credential or screenshot files committed.

## Applicable checks
- `pytest -q`
- `ruff check .`
- `python main.py --help` (no network)

## Progress
- 2026-09-30: explored 13 runs, identified three failure modes, created this document.

## Verification evidence
- `.venv/bin/python -m pytest -q`: 22 passed.
- `.venv/bin/python -m ruff check .`: All checks passed.
- `.venv/bin/python -m ruff format --check .`: 22 files already formatted.
- `.venv/bin/python main.py --help`: prints usage, no network needed.
- Engram mirror: pending, project not registered in store, local file is source of truth.

## Next step
- Await user decision on 6th account and whether to push the branch or open a PR.
