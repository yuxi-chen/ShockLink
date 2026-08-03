from __future__ import annotations

import numpy as np

from shocklink.mms.data import (
    _ev_to_kelvin,
    _kelvin_to_ev,
    _resolve_series,
    _total_temperature,
)
from shocklink.mms import MMSData


def test_temperature_unit_conversion_is_reversible() -> None:
    values_ev = np.array([0.0, 1.0, 10.0, 100.0])

    values_k = _ev_to_kelvin(values_ev)

    np.testing.assert_allclose(values_k, values_ev * 11604.51812)
    np.testing.assert_allclose(_kelvin_to_ev(values_k), values_ev)


def test_resolve_series_clips_to_requested_interval(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    product = SimpleNamespace(
        times=np.array([0.0, 10.0, 20.0]),
        y=np.array([1.0, 2.0, 3.0]),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(get_data=lambda *_args, **_kwargs: product),
    )

    resolved = _resolve_series(
        MMSData(
            cadence="fast",
            series={"ion_density": "density"},
            start="1970-01-01 00:00:10",
            end="1970-01-01 00:00:20",
        )
    )

    np.testing.assert_array_equal(
        resolved["ion_density"].times,
        np.array(
            ["1970-01-01T00:00:10", "1970-01-01T00:00:20"],
            dtype="datetime64[s]",
        ),
    )
    np.testing.assert_array_equal(resolved["ion_density"].values, [2.0, 3.0])


def test_total_temperature_uses_one_parallel_and_two_perpendicular_directions(
    mms_data,
) -> None:
    temperature = _total_temperature(_resolve_series(mms_data), "ion")

    np.testing.assert_allclose(temperature.values, [120.0, 240.0, 360.0])
