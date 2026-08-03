from __future__ import annotations

import numpy as np

from shocklink.mms import MMSData, average_plotted_values, summarize_data


def test_summarize_data_reports_scalar_and_vector_statistics(mms_data) -> None:
    summary = summarize_data(mms_data)

    assert summary["ion_density"] == {
        "count": 3,
        "mean": 2.0,
        "min": 1.0,
        "max": 3.0,
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
    assert averages["ion_density"] == 2.0
    assert averages["ion_velocity_z"] == 60.0
    assert averages["satellite_location_x"] == 1.0
    assert averages["satellite_location_y"] == -0.5
    assert averages["satellite_location_z"] == 0.1
    assert averages["ion_temperature"] == 240.0
    assert averages["electron_temperature"] == 80.0
    assert "electron_density" not in averages
    assert "electron_velocity_x" not in averages
