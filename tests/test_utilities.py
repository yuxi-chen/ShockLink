from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from shocklink.utilities import midpoint_datetime, parse_datetime


def test_parse_datetime_treats_naive_input_as_utc() -> None:
    assert parse_datetime("2018-12-19 19:52:00") == datetime(
        2018, 12, 19, 19, 52, tzinfo=UTC
    )


def test_parse_datetime_converts_an_offset_to_utc() -> None:
    assert parse_datetime("2018-12-19T14:52:00-05:00") == datetime(
        2018, 12, 19, 19, 52, tzinfo=UTC
    )


def test_midpoint_datetime_preserves_fractional_seconds() -> None:
    start = datetime(2018, 12, 19, 19, 40, tzinfo=UTC)
    end = datetime(2018, 12, 19, 19, 52, 1, tzinfo=UTC)
    assert midpoint_datetime(start, end) == datetime(
        2018, 12, 19, 19, 46, 0, 500000, tzinfo=UTC
    )


def test_midpoint_datetime_rejects_reversed_bounds() -> None:
    later = datetime(2018, 12, 19, 19, 52, tzinfo=UTC)
    earlier = later - timedelta(minutes=1)
    with pytest.raises(ValueError, match="start time must not be after end time"):
        midpoint_datetime(later, earlier)


def test_parse_datetime_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="invalid timestamp"):
        parse_datetime("not a timestamp")
