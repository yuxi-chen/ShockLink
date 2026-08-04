from __future__ import annotations

import pytest

from shocklink.mms_swmf import solar_wind_from_averages
from shocklink.swmf import SolarWindValues


def test_solar_wind_from_averages_maps_mms_values() -> None:
    result = solar_wind_from_averages(
        {
            "ion_density": 5.0,
            "ion_temperature": 2.0,
            "electron_temperature": 3.0,
            "ion_velocity_x": -400.0,
            "ion_velocity_y": 20.0,
            "ion_velocity_z": 30.0,
            "magnetic_field_x": -5.0,
            "magnetic_field_y": 2.0,
            "magnetic_field_z": 1.0,
        }
    )

    assert result == SolarWindValues(
        density=5.0,
        temperature_kelvin=5.0 * 11604.51812,
        velocity=(-400.0, 20.0, 30.0),
        magnetic_field=(-5.0, 2.0, 1.0),
    )


@pytest.mark.parametrize(
    "missing",
    [
        "ion_density",
        "ion_temperature",
        "electron_temperature",
        "ion_velocity_x",
        "ion_velocity_y",
        "ion_velocity_z",
        "magnetic_field_x",
        "magnetic_field_y",
        "magnetic_field_z",
    ],
)
def test_solar_wind_from_averages_reports_missing_values(missing: str) -> None:
    averages = {
        "ion_density": 1.0,
        "ion_temperature": 1.0,
        "electron_temperature": 1.0,
        "ion_velocity_x": 1.0,
        "ion_velocity_y": 1.0,
        "ion_velocity_z": 1.0,
        "magnetic_field_x": 1.0,
        "magnetic_field_y": 1.0,
        "magnetic_field_z": 1.0,
    }
    del averages[missing]

    with pytest.raises(ValueError, match=missing):
        solar_wind_from_averages(averages)


def test_solar_wind_from_averages_rejects_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="ion_density"):
        solar_wind_from_averages(
            {
                "ion_density": float("nan"),
                "ion_temperature": 1.0,
                "electron_temperature": 1.0,
                "ion_velocity_x": 1.0,
                "ion_velocity_y": 1.0,
                "ion_velocity_z": 1.0,
                "magnetic_field_x": 1.0,
                "magnetic_field_y": 1.0,
                "magnetic_field_z": 1.0,
            }
        )
