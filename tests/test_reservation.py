"""Unit tests for the pure reservation helpers."""

from datetime import UTC, date, datetime

import pytest

from core.reservation import (
    get_next_reservation_date,
    mask_username,
    split_into_blocks,
)


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        # Monday 23:59 -> Tuesday
        (datetime(2026, 9, 21, 23, 59), date(2026, 9, 22)),
        # Friday 23:59 -> Saturday is skipped to Monday
        (datetime(2026, 9, 25, 23, 59), date(2026, 9, 28)),
        # Saturday 23:59 -> Sunday skipped to Monday
        (datetime(2026, 9, 26, 23, 59), date(2026, 9, 28)),
        # Thursday morning -> Friday
        (datetime(2026, 9, 24, 9, 0), date(2026, 9, 25)),
    ],
)
def test_get_next_reservation_date(now, expected):
    assert get_next_reservation_date(now) == expected


def test_get_next_reservation_date_anchors_to_bogota_time():
    # 04:59 UTC on Tuesday is 23:59 Monday in Bogota, so the target is Tuesday.
    # A naive UTC reading would wrongly book Wednesday.
    utc_now = datetime(2026, 9, 22, 4, 59, tzinfo=UTC)
    assert get_next_reservation_date(utc_now) == date(2026, 9, 22)


def test_split_into_six_two_hour_blocks():
    blocks = split_into_blocks(date(2026, 9, 22))
    assert blocks == [
        ("2026-09-22", "08:00", "10:00"),
        ("2026-09-22", "10:00", "12:00"),
        ("2026-09-22", "12:00", "14:00"),
        ("2026-09-22", "14:00", "16:00"),
        ("2026-09-22", "16:00", "18:00"),
        ("2026-09-22", "18:00", "20:00"),
    ]


def test_split_clamps_last_block():
    blocks = split_into_blocks(date(2026, 9, 22), start="08:00", end="11:00", block_hours=2)
    assert blocks == [
        ("2026-09-22", "08:00", "10:00"),
        ("2026-09-22", "10:00", "11:00"),
    ]


def test_split_accepts_iso_string_and_rejects_bad_range():
    assert split_into_blocks("2026-09-22", start="08:00", end="09:00", block_hours=1) == [
        ("2026-09-22", "08:00", "09:00")
    ]
    with pytest.raises(ValueError):
        split_into_blocks("2026-09-22", start="10:00", end="08:00")


def test_mask_username():
    assert mask_username("1111542730") == "1111****30"
    assert mask_username("123") == "1**"
    assert mask_username("") == ""
