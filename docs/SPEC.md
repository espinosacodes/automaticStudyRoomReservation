# SPEC — automaticStudyRoomReservation

> Status: draft for approval. Source of truth once approved. Stack: Python + Playwright. Optional status page on `reservation.getcuria.us`.

## 1. Problem

The ICESI PDG classrooms are overcrowded and full of distractions. Unemployed students camp in the PDG and treat it as a hangout, so people who actually work (Santiago, David Dulce, Manuel and teammates who are SSR engineers) cannot find a quiet place to do deep work.

The workaround is the library study rooms at `https://banner9.icesi.edu.co/ic_reservas`. The team needs one room for about 10 people, booked for others to treat as a private lock-in where only workers are inside. The portal opens new slots after 23:59, and rooms are gone within minutes, so manual booking fails every night.

WhatsApp context (Valance group, 2026-09-21 to 2026-09-23):
- S Espinosa requested `user y contrasena de https://banner9.icesi.edu.co/ic_reservas` to automate reservations for the whole semester with Playwright.
- Plan stated: use Playwright headless on a GitHub Action cron at 23:59 which is when the next day slot opens.
- Credentials shared in chat for 4 accounts (S. Castillo, D. Dulce x2, M. Salazar, S. Espinosa) to enable multi-user rotation. Passwords are not recorded here. All credentials must stay in GitHub Secrets or local `credentials.json` (gitignored), never in the repo.

## 2. Goals

- Reserve the 10 person library room automatically every night at 23:59 America/Bogota, covering 08:00 to 20:00 Monday to Friday, so the team has a quiet work room all day.
- Run unattended for the whole semester. No manual login.
- Work around the portal restriction of 2 hours per booking per user by distributing consecutive 2 hour blocks across multiple Banner accounts (08:00-10:00, 10:00-12:00, 12:00-14:00, 14:00-16:00, 16:00-18:00, 18:00-20:00). Each block uses a different account from the rotation pool.
- Reduce contention and rate limit risk by rotating accounts on failure.
- Visible result: screenshots and log, optional tiny status page.

## 3. Non-goals

- No general university automation. Only `/ic_reservas/login` and `/ic_reservas/addReserve`.
- No seat selection UI beyond what the portal already provides. No calendar sync in v1.
- No multi-tenant SaaS, no Firestore, no Supabase for credentials in v1. File plus env vars is enough.
- No Terraform or infra beyond GitHub Actions and optionally Cloudflare Pages.

## 4. Users and inputs

- Single operator (Santiago) configures the cron. Friends contribute their Banner credentials for rotation to cover the 6 daily blocks.
- Inputs per reservation:
  - `BANNER_USERS_JSON` (GitHub Secret) as JSON array of `{ username, password }` with at least 6 entries for the 08:00 to 20:00 coverage. Fallback local is `credentials.json` or env `BANNER_USERNAME` / `BANNER_PASSWORD` for single block dry runs.
  - `reservationTime.json`: committed example array of 2 hour blocks, e.g. `[{ "day": "Monday", "startTime": "08:00", "endTime": "10:00" }, { "day": "Monday", "startTime": "10:00", "endTime": "12:00" }, ...]`. In practice the script generates the 6 blocks for the next weekday automatically, so this file is only an override.
  - `RESERVATION_ROOM` optional: label or code of the 10 person room. With `RESERVATION_PEOPLE=10` the portal offers `Sala de estudio 204BI` and that is picked automatically; set this only to require a specific room. Env override `RESERVATION_PEOPLE` (default `10`) drives which rooms appear.
  - `RESERVATION_ACTIVITY` (default `Reunión`). The portal offers Capacitación, Examen, Examen final, Examen multitudinario, Práctica de Laboratorio, Reunión, Seminario, Taller. It has no "Study Session".

## 5. Functional spec

### 5.1 Login

1. Navigate to `https://banner9.icesi.edu.co/ic_reservas/login`.
2. Fill `#username` and `#password`, click `button[type='submit']`.
3. Wait for `Bienvenido` marker or URL change away from `/login`. On timeout, retry once with next credential in rotation.
4. On failure, save `before_login.png`, log masked username, exit non-zero so Actions shows red.

### 5.2 Compute next reservation date and split into 2 hour blocks

Reuse one helper: `core/reservation.py:get_next_reservation_date` plus a new pure helper `core/reservation.py:split_into_blocks(date, start="08:00", end="20:00", block_hours=2)`.

- Map `Monday` to `Sunday` to 0 to 6.
- Compute next weekday target. The booking window opens at 23:59 for the next calendar day, so if today is Monday 23:59, target is Tuesday. If target is Saturday or Sunday, skip to Monday. No weekend bookings.
- For the target date `YYYY-MM-DD`, split `08:00` to `20:00` into six 2 hour blocks: `08:00-10:00`, `10:00-12:00`, `12:00-14:00`, `14:00-16:00`, `16:00-18:00`, `18:00-20:00`.
- Return `[(date, start, end), ...]` list. The caller assigns each block to the next credential in `BANNER_USERS_JSON` in order, so the 2 hour per user limit is respected.
- Both helpers are pure, unit-tested, no Playwright dependency.

### 5.3 Add reservations (one per block, sequential)

For each `(date, startTime, endTime, credential)` in order:

1. Login with that credential at `https://banner9.icesi.edu.co/ic_reservas/login` (fill `#username` and `#password`, click `button[type='submit']`, wait for `Bienvenido` or URL change). On timeout, try next credential for that same block once, then mark block as failed and continue to next block.
2. Click button containing `AGREGAR` and `RESERVA`, wait for `/addReserve`.
3. Fill form:
   - Activity: `Study Session` (via `RESERVATION_ACTIVITY`).
   - Date: `YYYY-MM-DD`.
   - Start time: `startTime`.
   - End time: `endTime`.
   - Room: select the 10 person room. If the portal uses a dropdown or radio, pick value matching `RESERVATION_ROOM` env, else first available. Log the chosen room label.
4. Take `before_submit_{block}.png`.
5. Submit unless `--dry-run`. Take `after_submit_{block}.png`.
6. Assert success marker (portal confirmation text or URL change). Log masked username and block. On failure save artifact and continue; do not abort the whole day because one block failed.
7. Logout or clear context before next block to avoid session bleed.

Total per night: up to 6 sequential Playwright sessions. Each is independent so a rate limit on one account does not block the others.

### 5.4 CLI

```
python main.py [--headed] [--dry-run] [--debug]
```

- `--headed`: show browser, for local debugging.
- `--dry-run`: fill form, screenshots, do not submit.
- `--debug`: verbose logging.

### 5.5 Scheduling

- GitHub Actions workflow `.github/workflows/reserve.yml` with `cron: '59 4 * * *'` which is 23:59 America/Bogota (04:59 UTC next day). Also `workflow_dispatch` for manual run.
- Concurrency group `reserve` with `cancel-in-progress: false`.
- The job runs only if the computed target is Monday to Friday. If the target is Saturday or Sunday, it logs `skip: weekend` and exits 0.
- Upload `before_submit_*.png` and `after_submit_*.png` as artifact, always.
- One cron covers all 6 blocks. No per-block schedule. The script loops the 6 blocks internally, rotating credentials.

## 6. Security

- Never commit `credentials.json`, `.env`, `encryption_key.key`, `*.enc`, or screenshots with session data.
- In CI read only from `secrets.BANNER_USERNAME` / `secrets.BANNER_PASSWORD` or `secrets.BANNER_USERS_JSON`.
- Log only masked usernames: `1105****49`.
- Playwright `storageState` is not persisted between runs. Fresh login each time.
- No credential sharing in docs. WhatsApp examples above are not to be reused literally.

## 7. Optional status page

Only if you approve after v1 automation works.

- Domain: `reservation.getcuria.us` (Cloudflare, `getcuria.us` zone, account `b080a52ee18c00011e5ed3b151545943`). No new domain.
- Hosting: Cloudflare Pages or Workers static, same as `curia` (`wrangler.jsonc` pattern).
- Content: last run timestamp, next scheduled date, last screenshot thumbnail, success or failure badge. No auth in v1. Data is a JSON artifact fetched from GitHub Releases or R2.
- Build: `apps/web` with Vite + Tailwind + `motion` + `lucide-react`, reusing tokens from `curia/.claude/skills/defi-landing-design/SKILL.md` and Valance palette (`#74B93C` primary, Figtree). See `docs/DESIGN.md`.
- Deploy only after automation is green for 3 consecutive nights.

## 8. Verification

- Unit: `pytest tests/test_reservation.py` covers `get_next_reservation_date` edge cases (same day before and after startTime, week wrap, invalid day).
- Manual: `python main.py --dry-run --headed` locally produces both screenshots without submitting.
- CI: workflow run on push to a test branch with `BANNER_USERS_JSON` set to a test account, check artifact upload.
- `banner9` is intranet only, so full e2e cannot run off campus. Document this limitation in PR.

## 9. Portal constraints captured

- Each user can book only one 2 hour block per day (confirmed live on 2026-09-24). Six blocks therefore need six distinct accounts, and the automation never reuses an account within a run. An account is only consumed when its block actually books, so an unavailable block frees it for a later block.
- Confirmed room label: `Sala de estudio 204BI [Capacidad espacio: 10]` (code `204BI`), offered when `Número de personas` is 10.
- The `addReserve` route is a two step Material UI wizard (requester info, then the reservation form) and must be opened by clicking the `AGREGAR RESERVA` card so the in-memory session survives. Verified against the live portal on 2026-09-24.
- Activity options are academic Spanish labels; there is no "Study Session", so `Reunión` is the default.
- Valid booking hours are Monday to Friday 07:00 to 21:00. The date picker only enables the currently open window.
- When the 10 person room is already booked for a block the block is reported as `unavailable` and the rest continue.

## 10. Rollout plan

1. Approve this spec.
2. Implement `main.py` + `core/*` in Python + Playwright, replacing archived `studyRoomReservation.py` (Selenium). Keep diff minimal. Include `split_into_blocks` helper and weekend skip.
3. Add `reserve.yml` and test with `workflow_dispatch` in `--dry-run` mode for one Tuesday.
4. Run dry for 2 nights, then live with 6 accounts at 23:59 for Wednesday to Friday.
5. Decide on status page. If yes, scaffold `apps/web` after step 4.

## 11. Open questions for approval

- Confirm the 10 person room label or id in the portal so `RESERVATION_ROOM` can be set exactly.
- Do you have 6 distinct Banner accounts secured, or do we need to stagger fewer blocks and expand later?
- Confirm weekend rule: portal shows no Monday to Friday restriction itself, or do we skip Sat and Sun in code?
- Status page in v1 or after automation is proven?

Approve with comments or say `go` to start implementation.
