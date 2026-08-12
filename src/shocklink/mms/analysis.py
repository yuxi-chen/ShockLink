"""Pure numerical summaries for MMS observations."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np

from shocklink.constants import CARTESIAN_COMPONENTS
from shocklink.constants import EARTH_RADIUS_KM
from shocklink.utilities import parse_datetime

from .data import (
    _finite_mean,
    _mean_position_earth_radii,
    _resolve_series,
    _total_temperature,
)
from .data import MMSData, ResolvedSeries


PLOTTED_DIRECT_PRODUCTS = ("magnetic_field", "ion_density", "ion_velocity")


def _add_product_averages(
    averages: dict[str, float],
    *,
    key: str,
    values: np.ndarray,
) -> None:
    """Add scalar or Cartesian component means for one plotted product."""

    if values.ndim == 1:
        averages[key] = _finite_mean(values)
        return
    for index, component in enumerate(CARTESIAN_COMPONENTS):
        if index < values.shape[1]:
            averages[f"{key}_{component}"] = _finite_mean(values[:, index])
    if key == "magnetic_field" and values.shape[1] >= 3:
        averages["magnetic_field_magnitude"] = _finite_mean(
            np.linalg.norm(values[:, :3], axis=1)
        )


def _add_position_averages(
    averages: dict[str, float],
    series: dict[str, ResolvedSeries],
) -> None:
    """Add mean GSM position components when they are available."""

    position = _mean_position_earth_radii(series)
    if position is None:
        return
    for component, value in zip(CARTESIAN_COMPONENTS, position, strict=True):
        averages[f"satellite_location_{component}"] = float(value)


def _add_temperature_averages(
    averages: dict[str, float],
    series: dict[str, ResolvedSeries],
) -> None:
    """Add total ion and electron temperatures when available."""

    for species in ("ion", "electron"):
        product = _total_temperature(series, species)
        if product is not None:
            averages[f"{species}_temperature"] = _finite_mean(product.values)


def summarize_data(
    data: MMSData,
) -> dict[str, dict[str, float] | dict[str, dict[str, float]]]:
    """Return finite-value statistics for every loaded MMS time series."""
    summary: dict[str, dict[str, float] | dict[str, dict[str, float]]] = {}
    for name, product in _resolve_series(data).items():
        values = product.values
        if values.ndim == 1:
            summary[name] = _statistics(values)
            continue

        components: dict[str, dict[str, float]] = {}
        for index in range(values.shape[1]):
            label = (
                CARTESIAN_COMPONENTS[index]
                if index < len(CARTESIAN_COMPONENTS)
                else f"component_{index}"
            )
            components[label] = _statistics(values[:, index])
        summary[name] = components
    return summary


def average_plotted_values(data: MMSData) -> dict[str, float]:
    """Return finite means for the variables shown by the default plot."""
    series = _resolve_series(data)
    averages: dict[str, float] = {}
    for key in PLOTTED_DIRECT_PRODUCTS:
        product = series.get(key)
        if product is None:
            continue
        _add_product_averages(averages, key=key, values=product.values)
    _add_position_averages(averages, series)
    _add_temperature_averages(averages, series)
    return averages


def position_at_time_earth_radii(
    data: MMSData,
    time: str | datetime,
) -> tuple[float, float, float]:
    """Return the bounded linearly interpolated GSM position at *time*."""
    if isinstance(time, datetime):
        target = (
            time.replace(tzinfo=UTC) if time.tzinfo is None else time.astimezone(UTC)
        )
    else:
        target = parse_datetime(time)
    target_ns = np.datetime64(target.replace(tzinfo=None), "ns").astype(np.int64)

    position = _resolve_series(data).get("satellite_location")
    if position is None:
        raise ValueError("satellite_location data is required")
    values = np.asarray(position.values)
    if values.ndim != 2 or values.shape[1] < 3:
        raise ValueError("satellite_location must have at least three components")

    timestamps = position.times.astype("datetime64[ns]")
    if len(timestamps) != len(values):
        raise ValueError(
            "satellite_location timestamps and values must have matching lengths"
        )
    timestamp_ns = timestamps.astype(np.int64)
    valid = ~np.isnat(timestamps) & np.all(np.isfinite(values[:, :3]), axis=1)
    if not np.any(valid):
        raise ValueError("satellite_location has no finite timestamped positions")
    timestamp_ns = timestamp_ns[valid]
    values = values[valid, :3]
    order = np.argsort(timestamp_ns, kind="stable")
    timestamp_ns = timestamp_ns[order]
    values = values[order]
    unique_times, unique_indices = np.unique(timestamp_ns, return_index=True)
    values = values[unique_indices]

    if target_ns < unique_times[0] or target_ns > unique_times[-1]:
        raise ValueError(
            f"requested time {target.isoformat()} is outside available "
            f"position range {unique_times[0]} to {unique_times[-1]}"
        )
    interpolated = np.array(
        [
            np.interp(target_ns, unique_times, values[:, component])
            for component in range(3)
        ]
    )
    result = interpolated / EARTH_RADIUS_KM
    if not np.all(np.isfinite(result)):
        raise ValueError("interpolated satellite_location is not finite")
    return tuple(float(value) for value in result)


def _statistics(values: np.ndarray) -> dict[str, float]:
    finite_values = values[np.isfinite(values)]
    if not len(finite_values):
        return {
            "count": 0,
            "mean": float("nan"),
            "min": float("nan"),
            "max": float("nan"),
        }
    return {
        "count": int(len(finite_values)),
        "mean": float(np.mean(finite_values)),
        "min": float(np.min(finite_values)),
        "max": float(np.max(finite_values)),
    }
