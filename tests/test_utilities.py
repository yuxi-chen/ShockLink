from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from shocklink.constants import EV_TO_K
from shocklink.utilities import (
    TimeBounds,
    ev_to_kelvin,
    kelvin_to_ev,
    midpoint_datetime,
    parse_datetime,
)


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


def test_temperature_conversions_are_reversible() -> None:
    values = np.array([0.0, 1.0, 10.0])
    np.testing.assert_allclose(ev_to_kelvin(values), values * EV_TO_K)
    np.testing.assert_allclose(kelvin_to_ev(ev_to_kelvin(values)), values)


def test_time_bounds_expose_utc_unix_and_numpy_values() -> None:
    bounds = TimeBounds.from_strings(
        "2018-12-19 19:40:00", "2018-12-19 19:52:00"
    )
    assert bounds.start.tzinfo is UTC
    assert bounds.unix == (1545248400.0, 1545249120.0)
    assert bounds.numpy == (
        np.datetime64("2018-12-19T19:40:00"),
        np.datetime64("2018-12-19T19:52:00"),
    )
