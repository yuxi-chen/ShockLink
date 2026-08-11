"""Shared MMS data models and pytplot resolution helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

import numpy as np

from shocklink.constants import EARTH_RADIUS_KM
from shocklink.utilities import TimeBounds


Cadence = Literal["brst", "fast"] | str
CoordinateSystem = Literal["gse", "gsm"]


@dataclass(frozen=True)
class MMSData:
    """Named pytplot variables returned for one MMS probe and cadence."""

    cadence: Cadence
    series: Mapping[str, str]
    probe: int | None = None
    coordinates: CoordinateSystem = "gse"
    start: str | None = None
    end: str | None = None


@dataclass(frozen=True)
class ResolvedSeries:
    """Resolved pytplot values together with source units."""

    times: np.ndarray
    values: np.ndarray
    units: str | None = None


def _get_tplot_data(variable: str, *, metadata: bool = False) -> object:
    """Read a variable from bundled or legacy pytplot storage."""

    bundled_available = False
    try:
        from pyspedas import get_data as get_bundled_data
    except ImportError:  # pragma: no cover - compatibility with pySPEDAS 1.x
        pass
    else:
        bundled_available = True
        product = (
            get_bundled_data(variable, metadata=True)
            if metadata
            else get_bundled_data(variable)
        )
        if product is not None:
            return product

    try:
        from pytplot import get_data as get_legacy_data
    except ImportError as error:  # pragma: no cover - optional dependency
        if bundled_available:
            return None
        raise ImportError(
            "MMS analysis requires the installed pySPEDAS package."
        ) from error
    if metadata:
        return get_legacy_data(variable, metadata=True)
    return get_legacy_data(variable)


def _resolve_series(data: MMSData) -> dict[str, ResolvedSeries]:
    """Resolve pytplot names while retaining timestamps and units."""
    bounds = (
        TimeBounds.from_strings(data.start, data.end)
        if data.start is not None and data.end is not None
        else None
    )
    resolved: dict[str, ResolvedSeries] = {}
    for name, variable in data.series.items():
        product = _get_tplot_data(variable)
        if product is None:
            continue
        try:
            times, values = product.times, product.y
        except AttributeError:
            times, values = product[0], product[1]
        values_array = np.asarray(values)
        if values_array.ndim not in (1, 2) or not len(values_array):
            continue
        times_array = _to_datetime64(times)
        if bounds is not None:
            start_time, end_time = bounds.numpy
            interval = (times_array >= start_time) & (times_array <= end_time)
            times_array = times_array[interval]
            values_array = values_array[interval]
            if not len(times_array):
                continue
        try:
            metadata = _get_tplot_data(variable, metadata=True) or {}
        except TypeError:
            metadata = {}
        resolved[name] = ResolvedSeries(
            times=times_array,
            values=values_array,
            units=_metadata_text(metadata, "units"),
        )
    return resolved


def _to_datetime64(times: object) -> np.ndarray:
    """Convert pySPEDAS Unix timestamps to calendar timestamps."""
    timestamps = np.asarray(times)
    if np.issubdtype(timestamps.dtype, np.datetime64):
        return timestamps
    return timestamps.astype("datetime64[s]")


def _total_temperature(
    series: Mapping[str, ResolvedSeries], species: str
) -> ResolvedSeries | None:
    """Return ``(T_parallel + 2*T_perpendicular) / 3``."""
    parallel = series.get(f"{species}_temperature_parallel")
    perpendicular = series.get(f"{species}_temperature_perpendicular")
    if parallel is None or perpendicular is None:
        return series.get(f"{species}_temperature")

    times, parallel_indices, perpendicular_indices = np.intersect1d(
        parallel.times, perpendicular.times, return_indices=True
    )
    if not len(times):
        return None
    values = (
        parallel.values[parallel_indices] + 2 * perpendicular.values[perpendicular_indices]
    ) / 3
    return ResolvedSeries(
        times=times,
        values=values,
        units=parallel.units or perpendicular.units,
    )


def _finite_mean(values: np.ndarray) -> float:
    finite_values = values[np.isfinite(values)]
    return float(np.mean(finite_values)) if len(finite_values) else float("nan")


def _mean_position_earth_radii(
    series: Mapping[str, ResolvedSeries],
) -> np.ndarray | None:
    position = series.get("satellite_location")
    if position is None or position.values.ndim != 2 or position.values.shape[1] < 3:
        return None
    values = position.values[:, :3]
    finite = np.all(np.isfinite(values), axis=1)
    if not np.any(finite):
        return None
    return np.mean(values[finite], axis=0) / EARTH_RADIUS_KM


def _metadata_text(metadata: object, field: str) -> str | None:
    """Read units from common pytplot metadata locations."""
    if not isinstance(metadata, Mapping):
        return None
    candidates = (
        _nested_metadata(metadata, "plot_options", "yaxis_opt", "axis_subtitle"),
        metadata.get("units"),
        _nested_metadata(metadata, "data_att", "units"),
        _nested_metadata(metadata, "plot_options", "yaxis_opt", "units"),
    )
    return next((str(value) for value in candidates if value), None)


def _nested_metadata(metadata: Mapping[str, object], *keys: str) -> object | None:
    value: object = metadata
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value
