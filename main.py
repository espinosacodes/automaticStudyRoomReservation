"""Playwright entry point.

Flow per 2 hour block, verified against the live portal:

  login -> home -> click the AGREGAR RESERVA card -> requester step
  (CONTINUAR) -> reservation step -> fill actividad, fecha, horas, personas,
  espacio fisico -> screenshot -> FINALIZAR (unless dry run).

The portal is a Material UI wizard, so the date and time pickers are driven
through their dialogs and the selects through their listboxes. Five blocks are
booked with rotating Banner accounts because the portal caps a booking at two
hours per user.

Usage:
    python main.py [--headed] [--dry-run] [--debug]
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import Browser, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from core import config
from core.browser import DEFAULT_TIMEOUT_MS, BrowserSession
from core.confirmation import fetch_official_pdf, room_code_from_label
from core.reservation import (
    DAY_NAMES,
    get_next_reservation_date,
    mask_username,
    now_bogota,
    split_into_blocks,
)

STATUS_FILE = Path("status.json")
STATUS_HISTORY = 30

# FINALIZAR runs server side validation before the CONFIRMAR modal appears,
# which takes far longer than any local render. Every other wait keeps the
# short default.
CONFIRM_TIMEOUT_MS = 60_000
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


class AccountLimit(Exception):
    """The portal refused the booking for this account (e.g. 2h daily max)."""


class InvalidCredentials(Exception):
    """The portal rejected the username or password at login."""


def short_timeout(exc: Exception) -> str:
    """Condense a Playwright timeout to one line, keeping the waited locator.

    The first line alone ("Locator.click: Timeout ... exceeded") never says
    which element hung, so the "waiting for ..." call log line is appended.
    """
    lines = str(exc).splitlines()
    head = lines[0] if lines else "timeout"
    if "waiting for" in head:
        return head
    waiting = next((line.strip() for line in lines if "waiting for" in line), "")
    return f"{head} ({waiting})".strip() if waiting else head


def save_failure_shot(page: Page, label: str) -> None:
    """Best effort screenshot of the portal state at failure.

    The workflow uploads ``*.png`` as artifacts, so this lands next to the
    ``before_submit`` shots for post run diagnosis.
    """
    try:
        page.screenshot(path=f"failure_{label}.png", full_page=True)
    except Exception:
        pass


# --------------------------------------------------------------------------
# CLI and logging
# --------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Automate study room reservations.")
    parser.add_argument("--headed", action="store_true", help="show the browser window")
    parser.add_argument("--dry-run", action="store_true", help="fill the form but never submit")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    parser.add_argument(
        "--target-date",
        default=os.getenv("RESERVATION_DATE") or None,
        help="weekday to reserve in YYYY-MM-DD format, within the next two days",
    )
    return parser.parse_args(argv)


def configure_logging(debug: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


# --------------------------------------------------------------------------
# Portal interaction
# --------------------------------------------------------------------------
def is_infra_failure(detail: str) -> bool:
    """True when the detail looks like runner network trouble, not a bad account.

    A single goto timeout must not consume the whole account pool. Callers use
    this to abort the day fast instead of retrying the same unreachable portal
    with every remaining account.
    """
    text = (detail or "").lower()
    markers = ("page.goto", "net::", "err_connection", "err_timed_out", "econnreset")
    return any(marker in text for marker in markers)


def login(page: Page, username: str, password: str) -> None:
    """Fill the login form and wait until the home calendar is interactive.

    The login page itself contains the word "Bienvenido", so the reliable
    success marker is the home only navigation link. The portal is reachable
    locally but GitHub runners see occasional egress timeouts, so goto gets
    two extra tries before the block is marked as infra trouble.
    """
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            page.goto(config.LOGIN_URL, wait_until="domcontentloaded")
            break
        except PlaywrightTimeoutError as exc:
            last_error = exc
            logger.warning("Login goto attempt %d failed: %s", attempt + 1, short_timeout(exc))
            page.wait_for_timeout(1000)
    else:
        raise PlaywrightTimeoutError(f"login page unreachable: {short_timeout(last_error)}")
    page.wait_for_selector("#username", timeout=DEFAULT_TIMEOUT_MS)
    page.fill("#username", username)
    page.fill("#password", password)
    page.click("button[type='submit']")
    try:
        page.wait_for_selector("a[href='/ic_reservas/addReserve']", timeout=DEFAULT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        # A bare timeout hides the portal's own verdict, so check for its
        # rejection dialog first and fail fast with a clear reason. Text
        # lookup: the portal modals render without an accessible dialog role.
        body_text = page.locator("body").inner_text()
        if re.search(r"contrase\w*.*inv\w*lid|invalid credentials", body_text, re.IGNORECASE):
            dismiss = page.locator("button", has_text=re.compile(r"^\s*OK\s*$"))
            if dismiss.count():
                dismiss.first.click()
            raise InvalidCredentials("portal rejected username or password")
        raise


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


def _open_menu_options(page: Page, control_id: str):
    """Open a MUI select and return its option locator.

    A fixed sleep races the portal: the menu sometimes opens before its items
    render, which used to read as an empty room list. Wait for the first item
    instead, and return whatever is there after a bounded wait.
    """
    page.locator(f"#{control_id}").click()
    options = page.get_by_role("option")
    try:
        options.first.wait_for(timeout=4000)
    except PlaywrightTimeoutError:
        pass
    return options


def select_option(page: Page, control_id: str, wanted: str, *, exact: bool = False) -> str:
    """Open a MUI select by id and choose an option.

    Matches ``wanted`` against the option label (substring, or exact when
    ``exact``) and falls back to the first option. Returns the chosen label.
    """
    options = _open_menu_options(page, control_id)
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

    cells = page.get_by_role("gridcell", name=str(target.day), exact=True)
    cell = None
    for index in range(cells.count()):
        candidate = cells.nth(index)
        try:
            if candidate.is_visible() and not candidate.is_disabled():
                cell = candidate
                break
        except PlaywrightTimeoutError:
            continue
    if cell is None:
        cell = cells.first
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


def _room_capacity(label: str) -> int | None:
    """Read the capacity out of a room label like 'Sala ... [Capacidad espacio: 10]'."""
    match = re.search(r"Capacidad\s+espacio:\s*(\d+)", label, re.IGNORECASE)
    return int(match.group(1)) if match else None


def rank_rooms(labels: list[str], preferred: str, people: str) -> list[str]:
    """Order room options best first.

    A label containing ``preferred`` wins whenever it is offered. Otherwise the
    largest room available comes first, because the real goal is to hold a study
    room for the whole day, so losing the preferred room must never lose the
    block. ``people`` is only used to keep the sort deterministic when two rooms
    share a capacity.
    """
    wanted = int(people) if str(people).isdigit() else 0

    def key(label: str):
        is_preferred = bool(preferred) and preferred.lower() in label.lower()
        capacity = _room_capacity(label) or 0
        # Preferred first, then largest capacity, then closest to the request.
        return (not is_preferred, -capacity, abs(capacity - wanted))

    return sorted(labels, key=key)


def people_fallback_counts(people: str) -> list[str]:
    """People counts to try, from requested down to 1.

    The portal filters rooms by headcount, so when nothing is free for 10 the
    run retries with 9, 8, and so on. Any room beats a lost block.
    """
    if str(people).isdigit() and int(people) > 1:
        return [str(n) for n in range(int(people), 0, -1)]
    return [str(people)]


def list_room_options(page: Page) -> list[str]:
    """Return the room labels currently offered by the Espacio fisico select.

    The menu is always dismissed, even when empty: a lingering modal overlay
    would block the next people count retry.
    """
    options = _open_menu_options(page, "place")
    labels = [(options.nth(i).inner_text() or "").strip() for i in range(options.count())]
    page.keyboard.press("Escape")
    page.wait_for_timeout(200)
    return [label for label in labels if label]


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
    """Fill the reservation step. Returns the selected room label.

    Prefers ``room``; when it is not offered, picks the best available room by
    capacity so a taken 10 person room does not lose the block. Raises
    ``RoomUnavailable`` only when the portal offers no room at all.
    """
    selected_activity = select_option(page, "activityName", activity)
    logger.info("Activity: %s", selected_activity)

    pick_date(page, target)
    pick_time(page, 0, start)
    pick_time(page, 1, end)

    # People count drives which rooms are offered, so it must be set before the
    # room list is fetched. Wait for the portal's own availability call so the
    # menu below reads fresh data instead of racing it. If no fresh call fires
    # (value unchanged), fall back to a short settle. When nothing is free for
    # the requested headcount, walk down to 1: any room beats a lost block.
    available: list[str] = []
    selected_people = ""
    for count in people_fallback_counts(people):
        try:
            with page.expect_response(re.compile(r"availableByUser"), timeout=8000):
                selected_people = select_option(page, "peopleQuantity", count, exact=True)
        except PlaywrightTimeoutError:
            selected_people = select_option(page, "peopleQuantity", count, exact=True)
            page.wait_for_timeout(1200)
        available = list_room_options(page)
        if available:
            break
        logger.info("No rooms for %s people, trying fewer", count)
    logger.info("People: %s", selected_people)

    if not available:
        raise RoomUnavailable(f"no room free for {start}-{end}")

    ranked = rank_rooms(available, room, selected_people)
    wanted = ranked[0]
    selected_room = select_option(page, "place", wanted)
    if not selected_room:
        # The label changed between listing and selecting, fall back to values.
        selected_room = available[0]
        page.locator("#place").click()
        page.wait_for_timeout(400)
        page.get_by_role("option").first.click()
    if selected_room != wanted:
        logger.info("Preferred room not offered, using %s", selected_room)
    logger.info("Room: %s", selected_room)

    # The room menu sometimes stays open after selection, and its modal
    # overlay then blocks the FINALIZAR button. Dismiss it explicitly.
    page.keyboard.press("Escape")
    page.wait_for_timeout(300)

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


def capture_confirmation(
    page: Page,
    *,
    target: date,
    start: str,
    end: str,
    room_label: str,
    activity: str,
    username: str,
    label: str,
) -> str:
    """FINALIZAR then CONFIRMAR, then fetch the guaranteed-full official PDF.

    The click on CONFIRMAR creates the booking. The download the portal emits at
    creation time is often blank, so the receipt is fetched deterministically
    through the Jasper report instead, using the stored end time. Returns the
    saved path, or an empty string when the receipt could not be fetched (the
    booking itself still succeeded).
    """
    logger.info("Block %s-%s: clicking FINALIZAR", start, end)
    finalize = page.get_by_role("button", name=re.compile(r"FINALIZAR", re.IGNORECASE))
    try:
        finalize.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        raise PlaywrightTimeoutError(f"FINALIZAR never visible: {short_timeout(exc)}") from exc
    try:
        finalize.scroll_into_view_if_needed(timeout=DEFAULT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        pass
    try:
        finalize.click(timeout=DEFAULT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        logger.warning("Block %s-%s: FINALIZAR blocked, retrying forced click", start, end)
        try:
            finalize.click(timeout=DEFAULT_TIMEOUT_MS, force=True)
        except PlaywrightTimeoutError as exc:
            msg = f"FINALIZAR click timed out: {short_timeout(exc)}"
            raise PlaywrightTimeoutError(msg) from exc

    logger.info("Block %s-%s: clicking CONFIRMAR", start, end)
    # Text lookup, not role lookup: the portal modals render without an
    # accessible dialog role, so get_by_role never resolves their buttons
    # even though they are plainly visible on screen.
    confirm = page.locator("button", has_text=re.compile(r"^\s*CONFIRMAR\s*$", re.IGNORECASE))
    try:
        confirm.wait_for(state="visible", timeout=CONFIRM_TIMEOUT_MS)
    except PlaywrightTimeoutError as exc:
        # The button never appeared, so the portal may have refused instead.
        # Read the page text for its verdict before reporting a bare timeout.
        body_text = page.locator("body").inner_text()
        refused = re.search(r"No es posible continuar[\s\S]{0,300}", body_text, re.IGNORECASE)
        if refused:
            reason = " ".join(refused.group(0).split())
            logger.warning("Block %s-%s refused by portal: %s", start, end, reason)
            dismiss = page.locator("button", has_text=re.compile(r"^\s*OK\s*$"))
            if dismiss.count():
                dismiss.first.click()
                page.wait_for_timeout(400)
            raise AccountLimit(f"portal refused: {reason[:200]}")
        raise PlaywrightTimeoutError(f"CONFIRMAR never visible: {short_timeout(exc)}") from exc
    try:
        confirm.scroll_into_view_if_needed(timeout=DEFAULT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        pass
    try:
        confirm.click(timeout=DEFAULT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        logger.warning("Block %s-%s: CONFIRMAR blocked, retrying forced click", start, end)
        try:
            confirm.click(timeout=DEFAULT_TIMEOUT_MS, force=True)
        except PlaywrightTimeoutError as exc:
            msg = f"CONFIRMAR click timed out: {short_timeout(exc)}"
            raise PlaywrightTimeoutError(msg) from exc

    # Booking confirmation and PDF delivery are independent outcomes.
    page.wait_for_function(
        "() => /registrada con .xito/i.test(document.body.innerText)",
        timeout=CONFIRM_TIMEOUT_MS,
    )

    out = Path("bookings") / f"confirmation_{label}.pdf"
    out.parent.mkdir(exist_ok=True)
    try:
        fetch_official_pdf(
            page,
            target=target,
            start=start,
            end=end,
            room_code=room_code_from_label(room_label),
            activity=activity,
            username=username,
            out=out,
        )
    except Exception:
        logger.warning("Booking confirmed, but its official PDF could not be fetched")
        return ""
    logger.info("Saved official confirmation: %s", out.name)
    return str(out)


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

    submission_started = False
    context = browser.new_context(accept_downloads=True)
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
            submission_started = True
            pdf_path = capture_confirmation(
                page,
                target=target_date,
                start=start,
                end=end,
                room_label=room,
                activity=config.activity_name(),
                username=account.username,
                label=f"{target_date.isoformat()}_{label}",
            )
            result.update(
                account=mask_username(account.username),
                room=room,
                status="success",
                detail="reservation submitted",
                pdf=pdf_path,
                pdf_status="captured" if pdf_path else "missing",
                confirmation_run_url=(
                    f"https://github.com/espinosacodes/automaticStudyRoomReservation/actions/runs/{os.environ['GITHUB_RUN_ID']}"
                    if pdf_path and os.getenv("GITHUB_RUN_ID", "").isdigit()
                    else ""
                ),
            )
        return result
    except RoomUnavailable as exc:
        logger.warning("Block %s unavailable: %s", f"{start}-{end}", exc)
        result.update(status="unavailable", detail=str(exc))
        return result
    except AccountLimit as exc:
        # The account hit the portal quota for this date. It stays consumed
        # and run_day retries the same block with the next account.
        logger.warning("Block %s account limited: %s", f"{start}-{end}", exc)
        result.update(status="account-limit", detail=str(exc))
        save_failure_shot(page, label)
        return result
    except InvalidCredentials as exc:
        logger.warning("Block %s bad credentials: %s", f"{start}-{end}", exc)
        result.update(status="bad-credentials", detail=str(exc))
        return result
    except PlaywrightTimeoutError as exc:
        detail = f"timeout: {short_timeout(exc)}"
        save_failure_shot(page, label)
        logger.warning(
            "Block %s failed with %s: %s",
            f"{start}-{end}",
            mask_username(account.username),
            detail,
        )
        if is_infra_failure(detail):
            result.update(status="infra-failure", detail=detail)
        else:
            result["detail"] = detail
        return result
    except Exception as exc:  # noqa: BLE001 - one block must not abort the day
        result["detail"] = str(exc).splitlines()[0]
        save_failure_shot(page, label)
        logger.warning("Block %s errored: %s", f"{start}-{end}", result["detail"])
        return result
    finally:
        if submission_started and result["status"] != "success":
            submission_error = result.get("detail", "").strip()
            result.update(
                status="unconfirmed",
                detail=(
                    "Submission needs portal verification. Automatic retry stopped. "
                    f"Last error: {submission_error}"
                    if submission_error
                    else "Submission needs portal verification. Automatic retry stopped."
                ),
            )
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
    pending = list(blocks)
    while pending:
        start, end = pending.pop(0)
        result: dict | None = None
        attempts = 0
        while pool and attempts < len(accounts):
            account = pool.pop(0)
            attempts += 1
            result = run_block(browser, account, target_date, start, end, dry_run)
            if "not selectable" in result.get("detail", ""):
                break  # date-wide problem, another account cannot fix it
            if result.get("status") == "infra-failure":
                pool.insert(0, account)  # network trouble, keep the account
                break
            if result["status"] == "unavailable":
                pool.insert(0, account)  # nothing booked, keep the account
                break
            if result["status"] in {"success", "dry-run", "unconfirmed"}:
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

        if result.get("status") == "infra-failure":
            logger.warning("Portal unreachable, skipping the rest of the day")
            for rest_start, rest_end in pending:
                results.append(
                    {
                        "start": rest_start,
                        "end": rest_end,
                        "account": "",
                        "room": "",
                        "status": "skipped",
                        "detail": f"portal unreachable, skipped {rest_start}-{rest_end}",
                    }
                )
            break

        if "not selectable" in result.get("detail", ""):
            # Every block shares the date, so retrying it is pure waste.
            # Skip the rest of the day instead of burning accounts.
            logger.warning("Date %s outside the portal window, skipping the rest", target_date)
            for rest_start, rest_end in pending:
                results.append(
                    {
                        "start": rest_start,
                        "end": rest_end,
                        "account": "",
                        "room": "",
                        "status": "skipped",
                        "detail": f"date {target_date} outside the portal window",
                    }
                )
            break
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
    try:
        target_date = get_next_reservation_date(requested_date=args.target_date)
    except ValueError as exc:
        logger.error("Invalid reservation date: %s", exc)
        return 2
    if target_date is None:
        logger.info(
            "No bookable weekday inside the portal window. "
            "Friday nights have nothing to do: the weekend is skipped by choice "
            "and Monday sits outside the +2 day picker window."
        )
        return 0
    blocks = build_schedule(target_date)
    if len(accounts) < len(blocks):
        logger.warning(
            "Only %d account(s) for %d block(s): a fully free day cannot be "
            "covered, the last block(s) will end with no-account.",
            len(accounts),
            len(blocks),
        )
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

    failed = [
        item
        for item in results
        if item["status"]
        in {"failed", "unconfirmed", "no-account", "account-limit", "bad-credentials", "infra-failure"}
    ]
    if failed:
        logger.error("%d block(s) failed", len(failed))
        return 1
    logger.info("All %d block(s) ok", len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
