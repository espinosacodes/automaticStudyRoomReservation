"""Official receipt handling must never submit twice or invent a receipt."""

from datetime import date
from unittest.mock import MagicMock

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import main
from core.config import Account
from core.confirmation import (
    activity_code,
    pdf_has_content,
    room_code_from_label,
    stored_end,
)


def test_stored_end_is_one_minute_before_the_booked_end():
    assert stored_end("10:00") == "0959"
    assert stored_end("08:00") == "0759"
    assert stored_end("21:00") == "2059"


def test_activity_code_maps_labels_and_passes_codes_through():
    assert activity_code("Reunión") == "REU"
    assert activity_code("REU") == "REU"
    assert activity_code("Taller") == "TAL"


def test_room_code_from_label():
    assert room_code_from_label("Sala de estudio 204BI [Capacidad espacio: 10]") == "204BI"
    assert room_code_from_label("no code here") == ""


def test_pdf_has_content_rejects_blank_receipts(tmp_path):
    blank = b"%PDF-1.5\n" + b"x" * 900
    assert not pdf_has_content(blank, "204BI")
    assert not pdf_has_content(b"<html>Error</html>", "204BI")


def test_capture_fetches_official_pdf_after_confirm(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = MagicMock()

    def fake_fetch(page_arg, **kwargs):
        out = kwargs["out"]
        out.parent.mkdir(exist_ok=True)
        out.write_bytes(b"%PDF-1.4 fake")
        return out

    monkeypatch.setattr(main, "fetch_official_pdf", fake_fetch)
    result = main.capture_confirmation(
        page,
        target=date(2026, 9, 28),
        start="08:00",
        end="10:00",
        room_label="Sala de estudio 204BI [Capacidad espacio: 10]",
        activity="Reunión",
        username="1054857884",
        label="2026-09-28_0800-1000",
    )
    assert result == "bookings/confirmation_2026-09-28_0800-1000.pdf"
    assert (tmp_path / result).exists()
    page.get_by_role.return_value.click.assert_called_with()
    assert page.get_by_role.return_value.click.call_count == 2  # FINALIZAR and CONFIRMAR
    page.wait_for_function.assert_called_once()


def test_missing_receipt_does_not_confirm_twice(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = MagicMock()

    def fake_fetch(page_arg, **kwargs):
        raise PlaywrightTimeoutError("No download")

    monkeypatch.setattr(main, "fetch_official_pdf", fake_fetch)
    result = main.capture_confirmation(
        page,
        target=date(2026, 9, 28),
        start="08:00",
        end="10:00",
        room_label="Sala de estudio 204BI [Capacidad espacio: 10]",
        activity="Reunión",
        username="1054857884",
        label="2026-09-28_0800-1000",
    )
    assert result == ""
    assert page.get_by_role.return_value.click.call_count == 2
    page.wait_for_function.assert_called_once()


def test_uncertain_submission_is_not_retried(monkeypatch):
    browser = MagicMock()
    for helper in ("login", "open_add_reserve", "accept_requester_step"):
        monkeypatch.setattr(main, helper, MagicMock())
    monkeypatch.setattr(main, "fill_reservation", MagicMock(return_value="204BI"))
    capture = MagicMock(side_effect=PlaywrightTimeoutError("Confirmation unknown"))
    monkeypatch.setattr(main, "capture_confirmation", capture)
    results = main.run_day(
        browser,
        [Account("test-a", "secret"), Account("test-b", "secret")],
        [("08:00", "10:00")],
        date(2026, 9, 28),
        False,
    )
    assert results[0]["status"] == "unconfirmed"
    capture.assert_called_once()


def test_unselectable_date_skips_the_rest_of_the_day(monkeypatch):
    browser = MagicMock()
    calls = []

    def fake_run_block(browser_arg, account, target_date, start, end, dry_run):
        calls.append(account.username)
        return {
            "start": start,
            "end": end,
            "account": account.username,
            "room": "",
            "status": "failed",
            "detail": "timeout: date 2026-09-28 is not selectable in the portal",
        }

    monkeypatch.setattr(main, "run_block", fake_run_block)
    results = main.run_day(
        browser,
        [Account("test-a", "secret"), Account("test-b", "secret")],
        [("08:00", "10:00"), ("10:00", "12:00"), ("12:00", "14:00")],
        date(2026, 9, 28),
        False,
    )
    assert [item["status"] for item in results] == ["failed", "skipped", "skipped"]
    assert calls == ["test-a"]  # one attempt, then the day is abandoned
