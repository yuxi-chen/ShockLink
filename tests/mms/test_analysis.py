from __future__ import annotations

import numpy as np
import pytest

from shocklink.mms import (
    MMSData,
    average_plotted_values,
    position_at_time_earth_radii,
    summarize_data,
)


def test_summarize_data_reports_scalar_and_vector_statistics(mms_data) -> None:
    summary = summarize_data(mms_data)

    assert summary["ion_density"] == {
        "count": 3,
        "mean": 5.0,
        "min": 4.0,
        "max": 6.0,
    }
    assert summary["magnetic_field"]["x"] == {
        "count": 3,
        "mean": 2.0,
        "min": 1.0,
        "max": 3.0,
    }
    assert summary["ion_velocity"]["z"]["max"] == 90.0


def test_summary_ignores_nonfinite_values(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda *_args, **_kwargs: SimpleNamespace(
                times=np.arange(4.0), y=np.array([1.0, np.nan, np.inf, 3.0])
            )
        ),
    )

    summary = summarize_data(
        MMSData(cadence="fast", series={"ion_density": "density"})
    )

    assert summary["ion_density"] == {
        "count": 2,
        "mean": 2.0,
        "min": 1.0,
        "max": 3.0,
    }


def test_average_plotted_values_returns_only_displayed_means(mms_data) -> None:
    averages = average_plotted_values(mms_data)

    assert averages["magnetic_field_x"] == 2.0
    assert averages["ion_density"] == 5.0
    assert averages["ion_velocity_z"] == 60.0
    assert averages["satellite_location_x"] == 1.0
    assert averages["satellite_location_y"] == -0.5
    assert averages["satellite_location_z"] == 0.1
    assert averages["omni_temperature"] == 400000.0
    assert "ion_temperature" not in averages
    assert "electron_temperature" not in averages
    assert "electron_density" not in averages
    assert "electron_velocity_x" not in averages


def test_average_plotted_values_uses_default_without_valid_omni_temperature() -> None:
    averages = average_plotted_values(MMSData(cadence="fast", series={}))

    assert averages["omni_temperature"] == 100000.0


def test_position_at_time_interpolates_between_mec_samples(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda *_args, **_kwargs: SimpleNamespace(
                times=np.array([0.0, 1.0, 2.0]),
                y=np.array([[6371.2, 0.0, 0.0], [12742.4, 6371.2, 0.0], [19071.6, 12742.4, 637.12]]),
            )
        ),
    )
    data = MMSData(cadence="fast", series={"satellite_location": "location"})

    result = position_at_time_earth_radii(data, "1970-01-01T00:00:00.500000Z")

    assert result == pytest.approx((1.5, 0.5, 0.0))


def test_position_at_time_filters_nonfinite_rows_and_rejects_out_of_range(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda *_args, **_kwargs: SimpleNamespace(
                times=np.array([0.0, 1.0, 2.0]),
                y=np.array([[6371.2, 0.0, 0.0], [np.nan, 1.0, 0.0], [19071.6, 2.0, 0.0]]),
            )
        ),
    )
    data = MMSData(cadence="fast", series={"satellite_location": "location"})

    assert position_at_time_earth_radii(
        data, "1970-01-01T00:00:01Z"
    ) == pytest.approx(((1.0 + 19071.6 / 6371.2) / 2, 1.0 / 6371.2, 0.0))
    with pytest.raises(ValueError, match="outside available"):
        position_at_time_earth_radii(data, "1969-12-31T23:59:59Z")


def test_position_at_time_rejects_missing_or_malformed_position(monkeypatch) -> None:
    import sys
    from types import SimpleNamespace

    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda *_args, **_kwargs: SimpleNamespace(
                times=np.array([0.0]), y=np.array([[1.0, 2.0]])
            )
        ),
    )
    data = MMSData(cadence="fast", series={"satellite_location": "location"})

    with pytest.raises(ValueError, match="at least three"):
        position_at_time_earth_radii(data, "1970-01-01T00:00:00Z")

    missing = MMSData(cadence="fast", series={})
    with pytest.raises(ValueError, match="satellite_location"):
        position_at_time_earth_radii(missing, "1970-01-01T00:00:00Z")
