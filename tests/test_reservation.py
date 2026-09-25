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
        # Thursday -> Friday
        (datetime(2026, 9, 24, 9, 0), date(2026, 9, 25)),
        # Friday -> Saturday is skipped, so Monday
        (datetime(2026, 9, 25, 9, 0), date(2026, 9, 28)),
        # Saturday -> Sunday is skipped, so Monday
        (datetime(2026, 9, 26, 9, 0), date(2026, 9, 28)),
        # Sunday -> Monday
        (datetime(2026, 9, 27, 9, 0), date(2026, 9, 28)),
        # Monday -> Tuesday
        (datetime(2026, 9, 28, 9, 0), date(2026, 9, 29)),
    ],
)
def test_get_next_reservation_date(now, expected):
    assert get_next_reservation_date(now) == expected


def test_get_next_reservation_date_never_lands_on_a_weekend():
    for day in range(1, 15):
        target = get_next_reservation_date(datetime(2026, 9, day, 9, 0))
        assert target.weekday() < 5, target


def test_get_next_reservation_date_anchors_to_bogota_time():
    # 04:59 UTC on Tuesday is 23:59 Monday in Bogota, so the target is Tuesday.
    # A naive UTC reading would wrongly target Wednesday.
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


def test_rank_rooms_prefers_requested_then_largest_available():
    from main import rank_rooms

    room_10 = "Sala de estudio 204BI [Capacidad espacio: 10]"
    room_6a = "Sala de estudio 313BI [Capacidad espacio: 6]"
    room_4 = "Sala de estudio 203BI [Capacidad espacio: 4]"

    # Preferred room always wins when offered.
    assert rank_rooms([room_6a, room_10], "204BI", "10")[0] == room_10
    # Without the preferred room, the largest available wins.
    assert rank_rooms([room_4, room_6a], "", "10")[0] == room_6a
    # A room smaller than requested is still better than losing the block.
    assert rank_rooms([room_4], "", "10") == [room_4]
    # Largest wins regardless of the requested count.
    assert rank_rooms([room_4, room_10], "", "4")[0] == room_10
