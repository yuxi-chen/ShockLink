"""Pure numerical summaries for MMS observations."""

from __future__ import annotations

import numpy as np

from .data import (
    _finite_mean,
    _mean_position_earth_radii,
    _resolve_series,
    _total_temperature,
)
from .data import MMSData


PLOTTED_DIRECT_PRODUCTS = ("magnetic_field", "ion_density", "ion_velocity")


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
            label = ("x", "y", "z")[index] if index < 3 else f"component_{index}"
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
        if product.values.ndim == 1:
            averages[key] = _finite_mean(product.values)
            continue
        for index, component in enumerate(("x", "y", "z")):
            if index < product.values.shape[1]:
                averages[f"{key}_{component}"] = _finite_mean(
                    product.values[:, index]
                )
        if key == "magnetic_field" and product.values.shape[1] >= 3:
            averages["magnetic_field_magnitude"] = _finite_mean(
                np.linalg.norm(product.values[:, :3], axis=1)
            )

    position = _mean_position_earth_radii(series)
    if position is not None:
        for component, value in zip(("x", "y", "z"), position, strict=True):
            averages[f"satellite_location_{component}"] = float(value)
    for species in ("ion", "electron"):
        product = _total_temperature(series, species)
        if product is not None:
            averages[f"{species}_temperature"] = _finite_mean(product.values)
    return averages


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
