"""Playwright entry point.

Login -> AGREGAR RESERVA -> fill the form for one 2 hour block -> screenshot
-> submit (unless dry run). Loops over the six blocks for the next weekday,
rotating Banner accounts so the 2 hour per user limit is respected.

Usage:
    python main.py [--headed] [--dry-run] [--debug]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
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

logger = logging.getLogger("reservation")


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
    """Fill the login form and wait for the session to be established."""
    page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#username", timeout=DEFAULT_TIMEOUT_MS)
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("button[type='submit']")
    page.wait_for_function(
        "() => document.body.innerText.includes('Bienvenido') "
        "|| !location.pathname.endsWith('/login')",
        timeout=DEFAULT_TIMEOUT_MS,
    )


def open_add_reserve(page: Page) -> None:
    """Click the AGREGAR RESERVA button and wait for the form page."""
    button = page.get_by_role("button", name=re.compile(r"AGREGAR.*RESERVA", re.IGNORECASE))
    button.first.click()
    page.wait_for_url(re.compile(r"/addReserve"), timeout=DEFAULT_TIMEOUT_MS)


def _choose_option(select, wanted: str) -> str:
    """Select the option matching ``wanted`` (case-insensitive substring).

    Falls back to the first non-empty option when nothing matches. Returns
    the chosen label for logging.
    """
    options = select.locator("option")
    entries: list[tuple[str | None, str]] = []
    for index in range(options.count()):
        option = options.nth(index)
        entries.append((option.get_attribute("value"), (option.inner_text() or "").strip()))

    if wanted:
        for value, label in entries:
            if value and wanted.lower() in label.lower():
                select.select_option(value=value)
                return label

    for value, label in entries:
        if value:
            select.select_option(value=value)
            return label
    return ""


def fill_reservation(
    page: Page,
    *,
    activity: str,
    target_date: str,
    start: str,
    end: str,
    room: str,
    people: str,
) -> str:
    """Fill the add reservation form. Returns the selected room label."""
    activity_input = page.locator("input[placeholder*='ctividad']").first
    activity_input.fill(activity)

    page.locator("input[type='date']").first.fill(target_date)
    times = page.locator("input[type='time']")
    times.nth(0).fill(start)
    times.nth(1).fill(end)

    building = page.locator("select[name*='edificio' i]").first
    if building.count():
        label = _choose_option(building, "")
        logger.debug("Selected building: %s", label)

    # The space list loads asynchronously after the building is picked.
    page.wait_for_timeout(2000)

    people_input = page.locator("input[type='number']").first
    if people_input.count():
        people_input.fill(people)

    room_select = page.locator(
        "select[name*='espacio' i], select[name*='sala' i], select[name*='room' i]"
    ).first
    chosen_room = ""
    if room_select.count():
        chosen_room = _choose_option(room_select, room)
        logger.info("Selected room: %s", chosen_room or "(first available)")

    observation = page.locator("textarea").first
    if observation.count():
        observation.fill("Automated reservation")

    return chosen_room


def submit_reservation(page: Page) -> None:
    """Click the submit button and wait for the confirmation marker."""
    button = page.get_by_role(
        "button", name=re.compile(r"Continuar|Solicitar|Reservar", re.IGNORECASE)
    )
    button.first.click()
    page.wait_for_function(
        "() => /exitosa|éxito|correctamente/i.test(document.body.innerText)",
        timeout=DEFAULT_TIMEOUT_MS,
    )


# --------------------------------------------------------------------------
# Scheduling
# --------------------------------------------------------------------------
def build_schedule(target_date) -> list[tuple[str, str, str]]:
    """Return the block list, honouring the optional reservationTime.json override.

    The override, when present, is filtered to the target weekday. If it
    yields nothing the auto 08:00 to 20:00 split is used.
    """
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
    candidates: list[config.Account],
    index: int,
    target_date: str,
    start: str,
    end: str,
    dry_run: bool,
) -> dict:
    """Run a single block, retrying login once with the next account."""
    label = f"{start.replace(':', '')}-{end.replace(':', '')}"
    result = {
        "start": start,
        "end": end,
        "account": "",
        "room": "",
        "status": "failed",
        "detail": "",
    }

    last_error = ""
    for candidate in candidates:
        context = browser.new_context()
        page = context.new_page()
        try:
            logger.info(
                "Block %s: logging in as %s",
                f"{start}-{end}",
                mask_username(candidate.username),
            )
            login(page, candidate.username, candidate.password)
            open_add_reserve(page)

            room = fill_reservation(
                page,
                activity=config.activity_name(),
                target_date=target_date,
                start=start,
                end=end,
                room=config.room_name(),
                people=config.people_count(),
            )

            page.screenshot(path=f"before_submit_{label}.png", full_page=True)

            if dry_run:
                logger.info("Block %s: dry run, not submitting", f"{start}-{end}")
                result.update(
                    account=mask_username(candidate.username),
                    room=room,
                    status="dry-run",
                    detail="form filled, submit skipped",
                )
            else:
                submit_reservation(page)
                page.screenshot(path=f"after_submit_{label}.png", full_page=True)
                result.update(
                    account=mask_username(candidate.username),
                    room=room,
                    status="success",
                    detail="reservation submitted",
                )
            return result
        except PlaywrightTimeoutError as exc:
            last_error = f"timeout: {exc}".splitlines()[0]
            logger.warning(
                "Block %s failed with %s: %s",
                f"{start}-{end}",
                mask_username(candidate.username),
                last_error,
            )
        except Exception as exc:  # noqa: BLE001 - one block must not abort the day
            last_error = str(exc)
            logger.warning("Block %s errored: %s", f"{start}-{end}", last_error)
        finally:
            context.close()

    result["detail"] = last_error
    return result


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

    results = []
    with BrowserSession(headless=not args.headed) as browser:
        for index, (_date, start, end) in enumerate(blocks):
            pool = [accounts[index % len(accounts)]]
            if len(accounts) > 1:
                pool.append(accounts[(index + 1) % len(accounts)])
            results.append(
                run_block(browser, pool, index, target_date.isoformat(), start, end, args.dry_run)
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
