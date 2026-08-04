"""Build SWMF inputs from MMS analysis results."""

from __future__ import annotations

from collections.abc import Mapping
import math

from shocklink.swmf import SolarWindValues


EV_TO_K = 11604.51812


def _required_average(averages: Mapping[str, float], name: str) -> float:
    try:
        value = float(averages[name])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"MMS average {name!r} is required") from error
    if not math.isfinite(value):
        raise ValueError(f"MMS average {name!r} must be finite")
    return value


def solar_wind_from_averages(averages: Mapping[str, float]) -> SolarWindValues:
    """Map GSM MMS averages to SWMF solar-wind values."""
    density = _required_average(averages, "ion_density")
    ion_temperature = _required_average(averages, "ion_temperature")
    electron_temperature = _required_average(averages, "electron_temperature")
    velocity = tuple(
        _required_average(averages, f"ion_velocity_{component}")
        for component in "xyz"
    )
    magnetic_field = tuple(
        _required_average(averages, f"magnetic_field_{component}")
        for component in "xyz"
    )
    return SolarWindValues(
        density=density,
        temperature_kelvin=(ion_temperature + electron_temperature) * EV_TO_K,
        velocity=velocity,  # type: ignore[arg-type]
        magnetic_field=magnetic_field,  # type: ignore[arg-type]
    )
