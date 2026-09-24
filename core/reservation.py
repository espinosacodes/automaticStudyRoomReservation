"""Pure date and time helpers for reservations.

No Playwright or network imports live here so the logic stays
unit-testable without a browser. Every caller must reuse these helpers
instead of duplicating the day mapping or the block splitting.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

# The university and therefore the booking window live in Bogota time. The
# GitHub cron fires at 23:59 Bogota which is 04:59 UTC the next day, so every
# date computation must be anchored here or the target day shifts by one.
BOGOTA_TZ = ZoneInfo("America/Bogota")

DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]

DEFAULT_START = "08:00"
DEFAULT_END = "20:00"
DEFAULT_BLOCK_HOURS = 2


def _to_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _to_hhmm(total_minutes: int) -> str:
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def now_bogota() -> datetime:
    """Current time in the university timezone."""
    return datetime.now(BOGOTA_TZ)


def get_next_reservation_date(now: datetime | None = None) -> date:
    """Return the next bookable weekday.

    The portal opens the next calendar day around 23:59, so the target is
    tomorrow. When tomorrow is Saturday or Sunday it is pushed forward to
    Monday, because the team never books weekends. Naive input is treated as
    Bogota time and aware input is converted to it.
    """
    moment = now or now_bogota()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=BOGOTA_TZ)
    moment = moment.astimezone(BOGOTA_TZ)
    target = moment.date() + timedelta(days=1)
    if target.weekday() == 5:  # Saturday -> Monday
        target += timedelta(days=2)
    elif target.weekday() == 6:  # Sunday -> Monday
        target += timedelta(days=1)
    return target


def split_into_blocks(
    target_date: date | datetime | str,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    block_hours: int = DEFAULT_BLOCK_HOURS,
) -> list[tuple[str, str, str]]:
    """Split an interval into back to back blocks.

    Returns a list of ``(iso_date, start, end)`` tuples. The final block is
    clamped to ``end`` so a non divisible interval never overflows.
    """
    if isinstance(target_date, datetime):
        target_date = target_date.date()
    if isinstance(target_date, str):
        target_date = date.fromisoformat(target_date)

    start_minutes = _to_minutes(start)
    end_minutes = _to_minutes(end)
    if end_minutes <= start_minutes:
        raise ValueError(f"end ({end}) must be after start ({start})")

    step = block_hours * 60
    if step <= 0:
        raise ValueError("block_hours must be positive")

    blocks: list[tuple[str, str, str]] = []
    cursor = start_minutes
    while cursor < end_minutes:
        next_cursor = min(cursor + step, end_minutes)
        blocks.append((target_date.isoformat(), _to_hhmm(cursor), _to_hhmm(next_cursor)))
        cursor = next_cursor
    return blocks


def mask_username(username: str) -> str:
    """Mask an account id, keeping the first four and last two characters."""
    if not username:
        return ""
    if len(username) <= 6:
        return username[0] + "*" * (len(username) - 1)
    return f"{username[:4]}{'*' * (len(username) - 6)}{username[-2:]}"
