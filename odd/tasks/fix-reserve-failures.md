# Fix reserve failures - ODD feature document

## Objective
Restore the scheduled `reserve` workflow to green for a fully free day, using 5 accounts for 08:00 to 18:00.

## Problem
Recent runs fail in three modes:
1. 2026-09-29 scheduled: all 5 blocks reach the confirmation dialog, then `CONFIRMAR` click times out. Screenshot shows the dialog open with a visible enabled CONFIRMAR button, so the locator `page.locator("[role='dialog']").first` likely picks a stale hidden picker dialog instead of the confirmation dialog.
2. 2026-09-30 scheduled: `Page.goto` to login times out for all 5 accounts. Portal returns HTTP 200 locally in 0.07s, so this is runner egress flakiness. Current `run_day` burns the whole account pool retrying the same network failure on the first block.
3. Recurring: `FINALIZAR` click or scroll times out on late blocks, and only 5 accounts exist for 6 blocks.
4. 2026-09-30 15:47 UTC run on the merged fix: new failure on target 2026-10-01. Date picker `gridcell` name `1` resolves to 2 elements, strict mode violation, so every account errors on the first block and the day is lost. From Monday Sep 28 onward no room was booked because each day hit one of these blockers.

## Why
The 23:59 Bogota cron must book the next weekday before others take the rooms. Every red run loses the day.

## Scope
- `main.py` confirmation, date picker, and submit flow.
- `core/reservation.py` product window and `core/config.py` override text.
- `reservationTime.json` Monday example.
- Unit tests for new logic.
- Authorized: direct work on `main` per user approval, plus `pytest`, `ruff check`, push to `main`. Not authorized: PR creation, remote workflow dispatch, credential changes.

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
- [x] T7 Keep 5 accounts covering 08:00 to 18:00, drop the 18:00 to 20:00 block from defaults, override, and tests.
- [x] T8 Fix date picker day duplicates by preferring the visible enabled gridcell, so Oct 1 style dates book.
- [x] T9 Sync docs and web copy to five blocks 08:00 to 18:00, including capacity 5 and diagram blocks.

## Acceptance criteria
- Confirmation dialog is located by `Confirmacion de nueva reserva` text or CONFIRMAR button scope, never by first dialog index.
- A single `goto` timeout retries at most twice, then aborts the day as infra failure instead of burning 5 accounts.
- FINALIZAR and CONFIRMAR each scroll into view before click, with one forced retry on timeout.
- Default schedule is five blocks 08:00 to 18:00, matching 5 accounts, with no `no-account` warning on a free day.
- Date picker with duplicate day cells picks the visible enabled one.
- `pytest -q` and `ruff check .` pass locally.
- No credential or screenshot files committed.

## Applicable checks
- `pytest -q`
- `ruff check .`
- `python main.py --help` (no network)

## Progress
- 2026-09-30: explored 13 runs, identified three failure modes, created this document.
- 2026-09-30: implemented T1 to T6 on branch `fix/reserve-reliability`, commit `c5fe013`, merged as `4329e8d`.
- 2026-09-30: implemented T7 and T8 directly on `main` per user approval (5 blocks 08:00 to 18:00, date picker duplicate fix).

## Verification evidence
- `.venv/bin/python -m pytest -q`: 23 passed.
- `.venv/bin/python -m ruff check .`: All checks passed.
- `pnpm --filter web typecheck`: clean.
- `pnpm --filter web build`: success, 779ms.
- `split_into_blocks(date(2026,10,1))`: five blocks 08:00 to 18:00, matching 5 accounts.
- Cron `59 4 * * *` is 23:59 Bogota (UTC-5), which matches the requested 11:59pm slot opening. No cron change needed.
- Engram mirror: pending, project not registered in store, local file is source of truth.

## Next step
- Push `main` and monitor the next 23:59 Bogota scheduled run for target 2026-10-01.
