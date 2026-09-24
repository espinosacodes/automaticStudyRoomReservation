"""Playwright entry point.

Flow per 2 hour block, verified against the live portal:

  login -> home -> click the AGREGAR RESERVA card -> requester step
  (CONTINUAR) -> reservation step -> fill actividad, fecha, horas, personas,
  espacio fisico -> screenshot -> FINALIZAR (unless dry run).

The portal is a Material UI wizard, so the date and time pickers are driven
through their dialogs and the selects through their listboxes. Six blocks are
booked with rotating Banner accounts because the portal caps a booking at two
hours per user.

Usage:
    python main.py [--headed] [--dry-run] [--debug]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import Browser, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from core import config
from core.browser import DEFAULT_TIMEOUT_MS, BrowserSession
from core.reservation import (
    DAY_NAMES,
    get_next_reservation_date,
    mask_username,
    now_bogota,
    split_into_blocks,
)

STATUS_FILE = Path("status.json")
STATUS_HISTORY = 30

# The portal has no "Study Session" option. "Reunion" (meeting) is the closest
# fit for a quiet work session and can be overridden with RESERVATION_ACTIVITY.
ACTIVITY_OPTIONS = [
    "Capacitacion",
    "Examen",
    "Examen final",
    "Examen multitudinario",
    "Practica de Laboratorio",
    "Reunion",
    "Seminario",
    "Taller",
]

ES_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

logger = logging.getLogger("reservation")


class RoomUnavailable(Exception):
    """No room matching the requested size was free for the block."""


# --------------------------------------------------------------------------
# CLI and logging
# --------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate study room reservations.")
    parser.add_argument("--headed", action="store_true", help="show the browser window")
    parser.add_argument("--dry-run", action="store_true", help="fill the form but never submit")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    return parser.parse_args(argv)


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


# --------------------------------------------------------------------------
# Portal interaction
# --------------------------------------------------------------------------
def login(page: Page, username: str, password: str) -> None:
    """Fill the login form and wait until the home calendar is interactive.

    The login page itself contains the word "Bienvenido", so the reliable
    success marker is the home only navigation link.
    """
    page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#username", timeout=DEFAULT_TIMEOUT_MS)
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("button[type='submit']")
    page.wait_for_selector("a[href='/ic_reservas/addReserve']", timeout=DEFAULT_TIMEOUT_MS)


def open_add_reserve(page: Page) -> None:
    """Open the add reservation wizard through the AGREGAR RESERVA card.

    The card link navigates client side. Navigating the URL directly, or using
    the sidebar link, loses the in-memory user state and crashes the route.
    """
    card = page.get_by_role("link", name=re.compile(r"AGREGAR", re.IGNORECASE))
    card.first.click()
    page.wait_for_url(re.compile(r"/addReserve"), timeout=DEFAULT_TIMEOUT_MS)
    # The requester step renders the personal information fields.
    page.wait_for_selector("#name", timeout=DEFAULT_TIMEOUT_MS)


def accept_requester_step(page: Page) -> None:
    """Step 1 only shows the requester info; CONTINUAR moves to the form."""
    page.get_by_role("button", name="CONTINUAR").click()
    page.wait_for_selector("#activityName", timeout=DEFAULT_TIMEOUT_MS)


def select_option(page: Page, control_id: str, wanted: str, *, exact: bool = False) -> str:
    """Open a MUI select by id and choose an option.

    Matches ``wanted`` against the option label (substring, or exact when
    ``exact``) and falls back to the first option. Returns the chosen label.
    """
    page.locator(f"#{control_id}").click()
    page.wait_for_timeout(400)
    options = page.get_by_role("option")
    count = options.count()
    labels = [(options.nth(i).inner_text() or "").strip() for i in range(count)]

    if wanted:
        for index, label in enumerate(labels):
            hit = label == wanted if exact else wanted.lower() in label.lower()
            if hit:
                options.nth(index).click()
                return label

    if count:
        options.first.click()
        return labels[0]
    return ""


def _open_picker_month(page: Page) -> tuple[int, int]:
    label = page.locator("[role='dialog'] [id$='-grid-label']").first.inner_text().strip()
    month_name, year = label.split()[-2], label.split()[-1]
    return int(year), ES_MONTHS.get(month_name.lower(), 1)


def pick_date(page: Page, target: date) -> None:
    """Set the date picker to ``target``, navigating months when needed."""
    page.locator("input[aria-label^='Choose date']").click()
    page.wait_for_timeout(500)

    for _ in range(18):
        year, month = _open_picker_month(page)
        if (year, month) == (target.year, target.month):
            break
        forward = (year, month) < (target.year, target.month)
        button = page.get_by_role("button", name="Next month" if forward else "Previous month")
        if button.is_disabled():
            raise PlaywrightTimeoutError(f"target month {target} is outside the picker window")
        button.click()
        page.wait_for_timeout(300)

    cell = page.get_by_role("gridcell", name=str(target.day), exact=True)
    if cell.is_disabled():
        raise PlaywrightTimeoutError(f"date {target} is not selectable in the portal")
    cell.click()
    page.wait_for_timeout(200)
    page.get_by_role("button", name="OK", exact=True).click()
    page.wait_for_timeout(400)


def _to_12h(hhmm: str) -> tuple[int, int, str]:
    hour, minute = (int(part) for part in hhmm.split(":"))
    meridiem = "AM" if hour < 12 else "PM"
    return (hour % 12 or 12), minute, meridiem


def pick_time(page: Page, index: int, hhmm: str) -> None:
    """Set the start (index 0) or end (index 1) time via the clock dialog.

    MUI's clock numbers sit under an overlay that swallows synthetic clicks, so
    the options are clicked with ``force=True``, which still reaches the clock
    face and selects the hour by position.
    """
    hour12, minute, meridiem = _to_12h(hhmm)
    page.locator("input[aria-label^='Choose time']").nth(index).click()
    page.wait_for_timeout(500)
    # Switch AM/PM first: the clock disables numbers outside the active
    # meridiem, so PM hours cannot be picked while AM is selected.
    page.get_by_role("button", name=meridiem, exact=True).click(force=True)
    page.wait_for_timeout(300)
    page.locator(f"[role=option][aria-label='{hour12} hours']").click(force=True)
    page.wait_for_timeout(400)
    page.locator(f"[role=option][aria-label='{minute:02d} minutes']").click(force=True)
    page.wait_for_timeout(300)
    page.get_by_role("button", name="OK", exact=True).click()
    page.wait_for_timeout(400)


def fill_reservation(
    page: Page,
    *,
    activity: str,
    target: date,
    start: str,
    end: str,
    room: str,
    people: str,
) -> str:
    """Fill the reservation step. Returns the selected room label."""
    selected_activity = select_option(page, "activityName", activity)
    logger.info("Activity: %s", selected_activity)

    pick_date(page, target)
    pick_time(page, 0, start)
    pick_time(page, 1, end)

    # People count drives which rooms are offered, so it must be set before the
    # room list is fetched.
    selected_people = select_option(page, "peopleQuantity", people, exact=True)
    logger.info("People: %s", selected_people)
    page.wait_for_timeout(1500)

    selected_room = select_option(page, "place", room)
    logger.info("Room: %s", selected_room or "(first available)")
    if not selected_room:
        raise RoomUnavailable(f"no {people} person room free for {start}-{end}")

    observation = page.locator("#details")
    if observation.count():
        observation.fill("Automated reservation")

    return selected_room


def submit_reservation(page: Page) -> None:
    """FINALIZAR runs validation, then a confirmation modal must be accepted.

    Only CONFIRMAR creates the reservation, after which the portal shows
    "Tu reserva ha sido registrada con exito".
    """
    page.get_by_role("button", name="FINALIZAR").click()
    page.get_by_role("button", name="CONFIRMAR").click()
    page.wait_for_function(
        "() => /registrada con .xito/i.test(document.body.innerText)",
        timeout=DEFAULT_TIMEOUT_MS,
    )


# --------------------------------------------------------------------------
# Scheduling
# --------------------------------------------------------------------------
def build_schedule(target_date: date) -> list[tuple[str, str, str]]:
    """Return the block list, honouring the optional reservationTime.json override."""
    override = config.load_schedule_override()
    if override:
        day_name = DAY_NAMES[target_date.weekday()]
        blocks: list[tuple[str, str, str]] = []
        for entry in override:
            entry_day = entry.get("day")
            if entry_day and entry_day != day_name:
                continue
            blocks.append((target_date.isoformat(), entry["startTime"], entry["endTime"]))
        if blocks:
            return blocks
    return split_into_blocks(target_date)


# --------------------------------------------------------------------------
# One reservation block
# --------------------------------------------------------------------------
def run_block(
    browser: Browser,
    account: config.Account,
    target_date: date,
    start: str,
    end: str,
    dry_run: bool,
) -> dict:
    """Run a single block with one account."""
    label = f"{start.replace(':', '')}-{end.replace(':', '')}"
    result = {
        "start": start,
        "end": end,
        "account": "",
        "room": "",
        "status": "failed",
        "detail": "",
    }

    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(DEFAULT_TIMEOUT_MS)
    try:
        logger.info(
            "Block %s: logging in as %s",
            f"{start}-{end}",
            mask_username(account.username),
        )
        login(page, account.username, account.password)
        open_add_reserve(page)
        accept_requester_step(page)

        room = fill_reservation(
            page,
            activity=config.activity_name(),
            target=target_date,
            start=start,
            end=end,
            room=config.room_name(),
            people=config.people_count(),
        )

        page.screenshot(path=f"before_submit_{label}.png", full_page=True)

        if dry_run:
            logger.info("Block %s: dry run, not submitting", f"{start}-{end}")
            result.update(
                account=mask_username(account.username),
                room=room,
                status="dry-run",
                detail="form filled, submit skipped",
            )
        else:
            submit_reservation(page)
            page.screenshot(path=f"after_submit_{label}.png", full_page=True)
            result.update(
                account=mask_username(account.username),
                room=room,
                status="success",
                detail="reservation submitted",
            )
        return result
    except RoomUnavailable as exc:
        logger.warning("Block %s unavailable: %s", f"{start}-{end}", exc)
        result.update(status="unavailable", detail=str(exc))
        return result
    except PlaywrightTimeoutError as exc:
        result["detail"] = f"timeout: {exc}".splitlines()[0]
        logger.warning(
            "Block %s failed with %s: %s",
            f"{start}-{end}",
            mask_username(account.username),
            result["detail"],
        )
        return result
    except Exception as exc:  # noqa: BLE001 - one block must not abort the day
        result["detail"] = str(exc)
        logger.warning("Block %s errored: %s", f"{start}-{end}", result["detail"])
        return result
    finally:
        context.close()


def run_day(
    browser: Browser,
    accounts: list[config.Account],
    blocks: list[tuple[str, str]],
    target_date: date,
    dry_run: bool,
) -> list[dict]:
    """Book the blocks, one account each, never reusing a consumed account.

    The portal limits every user to a single 2 hour block per day, so an
    account that books cannot serve another block. An account is only consumed
    when its block actually books, so an unavailable block returns it to the
    pool for a later block.
    """
    pool = list(accounts)
    results: list[dict] = []
    for start, end in blocks:
        result: dict | None = None
        attempts = 0
        while pool and attempts < len(accounts):
            account = pool.pop(0)
            attempts += 1
            result = run_block(browser, account, target_date, start, end, dry_run)
            if result["status"] == "unavailable":
                pool.insert(0, account)  # nothing booked, keep the account
                break
            if result["status"] in {"success", "dry-run"}:
                break
            # Login or form failure: the account may be bad, so try the next one.

        if result is None:
            logger.warning("Block %s-%s skipped: no account left", start, end)
            result = {
                "start": start,
                "end": end,
                "account": "",
                "room": "",
                "status": "no-account",
                "detail": "no account left for this block",
            }
        results.append(result)
    return results


# --------------------------------------------------------------------------
# Status output for the web page
# --------------------------------------------------------------------------
def write_status(record: dict) -> None:
    """Prepend the fresh run to status.json, keeping a bounded history."""
    runs: list[dict] = []
    if STATUS_FILE.exists():
        try:
            runs = json.loads(STATUS_FILE.read_text()).get("runs", [])
        except (json.JSONDecodeError, AttributeError):
            runs = []
    runs.insert(0, record)
    payload = {
        "generated_at": now_bogota().isoformat(timespec="seconds"),
        "runs": runs[:STATUS_HISTORY],
    }
    STATUS_FILE.write_text(json.dumps(payload, indent=2))
    logger.info("Wrote %s", STATUS_FILE)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    configure_logging(args.debug)

    started_at = now_bogota()
    accounts = config.load_accounts()
    target_date = get_next_reservation_date()
    blocks = build_schedule(target_date)
    logger.info(
        "Target %s (%s): %d block(s), %d account(s)",
        target_date.isoformat(),
        DAY_NAMES[target_date.weekday()],
        len(blocks),
        len(accounts),
    )

    with BrowserSession(headless=not args.headed) as browser:
        results = run_day(
            browser,
            accounts,
            [(start, end) for _date, start, end in blocks],
            target_date,
            args.dry_run,
        )

    succeeded = sum(1 for item in results if item["status"] in {"success", "dry-run"})
    record = {
        "run_at": started_at.isoformat(timespec="seconds"),
        "target_date": target_date.isoformat(),
        "dry_run": args.dry_run,
        "blocks": results,
        "summary": {
            "total": len(results),
            "succeeded": succeeded,
            "failed": len(results) - succeeded,
        },
    }
    write_status(record)

    failed = [item for item in results if item["status"] == "failed"]
    if failed:
        logger.error("%d block(s) failed", len(failed))
        return 1
    logger.info("All %d block(s) ok", len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
