"""Environment and file configuration loading.

Secrets come from env vars in CI and from a gitignored ``credentials.json``
locally. Nothing here logs a raw password.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

LOGIN_URL = "https://banner9.icesi.edu.co/ic_reservas/login"
HOME_URL = "https://banner9.icesi.edu.co/ic_reservas/"
ADD_RESERVE_URL = "https://banner9.icesi.edu.co/ic_reservas/addReserve"

DEFAULT_SCHEDULE_FILE = Path("reservationTime.json")
LOCAL_CREDENTIALS_FILE = Path("credentials.json")


@dataclass(frozen=True)
class Account:
    """A single Banner account used for one 2 hour block."""

    username: str
    password: str


def _account_from_mapping(item: dict) -> Account:
    return Account(username=str(item["username"]), password=str(item["password"]))


def load_accounts() -> list[Account]:
    """Load the credential rotation pool.

    Priority: ``BANNER_USERS_JSON`` (JSON array), then
    ``BANNER_USERNAME`` / ``BANNER_PASSWORD`` (single account), then the
    local gitignored ``credentials.json``.
    """
    raw = os.getenv("BANNER_USERS_JSON")
    accounts: list[Account] = []
    if raw:
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"BANNER_USERS_JSON is not valid JSON: {exc}") from exc
        if not isinstance(parsed, list):
            raise SystemExit("BANNER_USERS_JSON must be a JSON array")
        accounts = [_account_from_mapping(item) for item in parsed]

    if not accounts:
        username = os.getenv("BANNER_USERNAME")
        password = os.getenv("BANNER_PASSWORD")
        if username and password:
            accounts.append(Account(username=username, password=password))

    if not accounts and LOCAL_CREDENTIALS_FILE.exists():
        data = json.loads(LOCAL_CREDENTIALS_FILE.read_text())
        if isinstance(data, list):
            accounts = [_account_from_mapping(item) for item in data]
        else:
            accounts = [_account_from_mapping(data)]

    if not accounts:
        raise SystemExit(
            "No credentials found. Set BANNER_USERS_JSON or "
            "BANNER_USERNAME/BANNER_PASSWORD, or create credentials.json."
        )
    return accounts


def load_schedule_override(path: Path = DEFAULT_SCHEDULE_FILE) -> list[dict] | None:
    """Return ``reservationTime.json`` contents when present, else ``None``.

    The auto generated 08:00 to 20:00 split is the default. This file only
    exists to override that default.
    """
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return None
    return data or None


def room_name() -> str:
    """Exact room label or id to look for in the portal, e.g. ``Sala 10p``."""
    return os.getenv("RESERVATION_ROOM", "").strip()


def activity_name() -> str:
    return os.getenv("RESERVATION_ACTIVITY", "Reunión").strip()


def people_count() -> str:
    # Drives which rooms the portal offers. 10 surfaces the 10 person room.
    return os.getenv("RESERVATION_PEOPLE", "10").strip()
