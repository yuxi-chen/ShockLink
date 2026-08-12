from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import numpy as np

from shocklink.constants import EV_TO_K
from shocklink.mms.data import _clean_omni_temperature, _resolve_series, _total_temperature
from shocklink.mms import MMSData
from shocklink.utilities import ev_to_kelvin, kelvin_to_ev


def test_temperature_unit_conversion_is_reversible() -> None:
    values_ev = np.array([0.0, 1.0, 10.0, 100.0])

    values_k = ev_to_kelvin(values_ev)

    np.testing.assert_allclose(values_k, values_ev * EV_TO_K)
    np.testing.assert_allclose(kelvin_to_ev(values_k), values_ev)


def test_resolve_series_clips_to_requested_interval(monkeypatch) -> None:
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


def test_resolve_series_uses_bundled_pyspedas_registry(monkeypatch) -> None:
    pyspedas = ModuleType("pyspedas")
    pyspedas.get_data = lambda *_args, **_kwargs: SimpleNamespace(  # type: ignore[attr-defined]
        times=np.array([0.0]), y=np.array([2.0])
    )
    monkeypatch.setitem(sys.modules, "pyspedas", pyspedas)
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(get_data=lambda *_args, **_kwargs: None),
    )

    resolved = _resolve_series(
        MMSData(cadence="fast", series={"ion_density": "density"})
    )

    np.testing.assert_array_equal(resolved["ion_density"].values, [2.0])


def test_total_temperature_uses_one_parallel_and_two_perpendicular_directions(
    mms_data,
) -> None:
    temperature = _total_temperature(_resolve_series(mms_data), "ion")

    np.testing.assert_allclose(temperature.values, [120.0, 240.0, 360.0])


def test_clean_omni_temperature_removes_fill_and_all_nines() -> None:
    product = SimpleNamespace(
        times=np.arange(5.0),
        values=np.array([100000.0, 99999.0, 9999.9, np.nan, 200000.0]),
        units="K",
    )

    cleaned = _clean_omni_temperature(product, fill_value=99999.0)

    np.testing.assert_array_equal(cleaned.values, [100000.0, 200000.0])
    np.testing.assert_array_equal(cleaned.times, [0.0, 4.0])


def test_resolve_series_prefers_electron_density_for_ion_density(monkeypatch) -> None:
    products = {
        "ni": SimpleNamespace(times=np.array([0.0]), y=np.array([1.0])),
        "ne": SimpleNamespace(times=np.array([0.0]), y=np.array([4.0])),
    }
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(get_data=lambda name, **_: products.get(name)),
    )

    resolved = _resolve_series(
        MMSData(cadence="fast", series={"ion_density": "ni", "electron_density": "ne"})
    )

    np.testing.assert_array_equal(resolved["ion_density"].values, [4.0])
