"""Fetch the official confirmation PDF for an existing reservation.

The portal generates ConstanciaDeReservaDeEspacio.pdf through JasperReports.
The report URL is built purely from booking fields, so any already-reserved
booking can have its official receipt regenerated:

    python -m tools.fetch_confirmation 2026-09-25 08:00 10:00 204BI REU 1054857884

Read only against existing bookings. It never creates a reservation.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main as automation  # noqa: E402
from core import config  # noqa: E402
from core.browser import BrowserSession  # noqa: E402
from core.confirmation import fetch_official_pdf  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch an official confirmation PDF.")
    parser.add_argument("target_date", help="booking date as YYYY-MM-DD")
    parser.add_argument("start", help="booked block start as HH:MM")
    parser.add_argument("end", help="booked block end as HH:MM")
    parser.add_argument("room_code", help="room code, e.g. 204BI")
    parser.add_argument("activity", help="activity code or label, e.g. REU or Reunión")
    parser.add_argument("username", help="document number that owns the booking")
    parser.add_argument("--password-env", default="", help="env var holding the password")
    parser.add_argument("--password", default="", help="password (prefer --password-env)")
    parser.add_argument(
        "--account-index", type=int, default=-1, help="use credentials.json entry instead"
    )
    parser.add_argument("--out", default="", help="output path, defaults into bookings/")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    automation.configure_logging(False)
    target = date.fromisoformat(args.target_date)

    if args.account_index >= 0:
        account = config.load_accounts()[args.account_index]
        username, password = account.username, account.password
    else:
        username = args.username
        password = os.environ.get(args.password_env, "") if args.password_env else args.password
    if not password:
        raise SystemExit("no password: use --account-index or --password-env")

    stamp = f"{target.isoformat()}_{args.start.replace(':', '')}-{args.end.replace(':', '')}"
    out = Path(args.out) if args.out else Path(f"bookings/confirmation_{stamp}.pdf")
    out.parent.mkdir(exist_ok=True)

    with BrowserSession(headless=True) as browser:
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(30_000)
        automation.login(page, username, password)
        try:
            saved = fetch_official_pdf(
                page,
                target=target,
                start=args.start,
                end=args.end,
                room_code=args.room_code,
                activity=args.activity,
                username=username,
                out=out,
            )
        finally:
            context.close()
    print(f"saved {saved} ({saved.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
