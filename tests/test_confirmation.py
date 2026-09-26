"""Official download handling must never submit twice or invent a receipt."""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

import main
from core.config import Account


@pytest.mark.parametrize(
    "contents,expected", [(b"%PDF-1.7\nportal receipt", True), (b"<html>Error</html>", False)]
)
def test_capture_validates_official_download(tmp_path, monkeypatch, contents, expected):
    monkeypatch.chdir(tmp_path)
    page = MagicMock()
    download = page.expect_download.return_value.__enter__.return_value.value
    download.save_as.side_effect = lambda path: Path(path).write_bytes(contents)
    result = main.capture_confirmation(page, "2026-09-28_0800-1000")
    assert bool(result) is expected
    assert list(tmp_path.rglob("*.pdf")) == ([tmp_path / result] if expected else [])
    page.get_by_role.return_value.click.assert_called_with()
    assert page.get_by_role.return_value.click.call_count == 2  # FINALIZAR and CONFIRMAR


def test_missing_download_does_not_confirm_twice(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    page = MagicMock()
    page.expect_download.return_value.__exit__.side_effect = PlaywrightTimeoutError("No download")
    assert main.capture_confirmation(page, "2026-09-28_0800-1000") == ""
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
