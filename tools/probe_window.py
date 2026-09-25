"""Measure when a target day's room becomes bookable.

The portal allows reservations up to a maximum of 3 days ahead (its own rule
text) instead of opening one nightly batch, so there is no documented HH:MM
opening to schedule against. This probe answers the question empirically.

    python -m tools.probe_window 2026-09-27 --room 204BI

It opens the wizard once, then for each block sets the date and times and reads
the room list straight from the portal's own endpoint that the Espacio fisico
select uses. The setter helpers are read-only and never submit.

Read only. It never creates a reservation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main as automation  # noqa: E402
from core import config  # noqa: E402
from core.browser import BrowserSession  # noqa: E402
from core.reservation import now_bogota, split_into_blocks  # noqa: E402

PROBE_LOG = Path("window_probe.json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure portal booking availability.")
    parser.add_argument("target_date", help="target date as YYYY-MM-DD")
    parser.add_argument(
        "--room", default=config.room_name(), help="room label substring to require"
    )
    parser.add_argument(
        "--people", default=config.people_count(), help="people count that drives the room list"
    )
    parser.add_argument(
        "--every", type=int, default=0, help="seconds between polls, 0 for a single check"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="total seconds to keep polling, 0 for a single check",
    )
    parser.add_argument(
        "--account-index", type=int, default=0, help="which account from the pool to probe with"
    )
    return parser.parse_args(argv)


def as_api_date(target: date) -> str:
    return target.strftime("%d-%m-%Y")


def available_rooms(page, target: date, start: str, end: str, people: str) -> list[str]:
    """Return the room labels the portal offers for one block, or an empty list.

    Reads the portal's own availability endpoint, which is exactly what the
    Espacio fisico select consumes. No clicks, so no MUI popover to dismiss.
    """
    response = page.request.get(
        f"{config.API_BASE}/rooms/availableByUser",
        params={
            "startTime": start.replace(":", ""),
            "endTime": end.replace(":", ""),
            "date": as_api_date(target),
            "bldgCode": config.BUILDING_CODE,
            "peopleQuantity": people,
        },
    )
    if response.status != 200:
        return []
    return [str(item.get("descripcion", "")) for item in response.json()]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    automation.configure_logging(False)

    target = date.fromisoformat(args.target_date)
    accounts = config.load_accounts()
    account = accounts[args.account_index % len(accounts)]
    blocks = [(start, end) for _date, start, end in split_into_blocks(target)]
    observations: list[dict] = []
    first_bookable: dict | None = None

    with BrowserSession(headless=True) as browser:
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(25_000)
        automation.login(page, account.username, account.password)
        print(
            f"target {target.isoformat()} ({target.strftime('%A')}), probing {len(blocks)} block(s)"
        )

        deadline = now_bogota() + timedelta(seconds=args.duration)
        while True:
            stamp = now_bogota().isoformat(timespec="seconds")
            found: list[dict] = []
            for start, end in blocks:
                try:
                    labels = available_rooms(page, target, start, end, args.people)
                except Exception as exc:  # noqa: BLE001 - probing must not abort
                    labels = []
                    print(f"  {stamp} {start}-{end} probe error: {str(exc).splitlines()[0]}")
                matches = (
                    [label for label in labels if args.room.lower() in label.lower()]
                    if args.room
                    else labels
                )
                print(f"  {stamp} {start}-{end} -> {len(labels)} option(s), {len(matches)} match")
                if matches:
                    found.append({"start": start, "end": end, "room": matches[0]})
            observations.append({"at": stamp, "matches": found})
            if found and first_bookable is None:
                first_bookable = {"at": stamp, "blocks": found}
                print(f"FIRST BOOKABLE at {stamp}: {json.dumps(found)}")

            if args.duration <= 0 or now_bogota() >= deadline:
                break
            page.wait_for_timeout(args.every * 1000)

        context.close()

    PROBE_LOG.write_text(
        json.dumps(
            {
                "target_date": target.isoformat(),
                "room": args.room,
                "people": args.people,
                "started_at": observations[0]["at"] if observations else None,
                "finished_at": observations[-1]["at"] if observations else None,
                "first_bookable": first_bookable,
                "observations": observations,
            },
            indent=2,
        )
    )
    print(f"wrote {PROBE_LOG}")
    return 0 if first_bookable else 1


if __name__ == "__main__":
    sys.exit(main())
