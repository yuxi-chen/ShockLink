"""Reusable MMS-to-bow-shock connection workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import math
from pathlib import Path
from typing import Literal

import numpy as np
import pyvista as pv
from numpy.typing import NDArray

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
    smooth_bow_shock_surface,
)
from shocklink.connectivity import (
    ShockConnection,
    analyze_shock_connection,
    plot_shock_angle_contour,
    plot_shock_connection_3d,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.io import TIME_EVENT_KEY, load_simulation
from shocklink.mms import average_plotted_values, load_mms_data
from shocklink.utilities import parse_datetime

_SURFACE_AXIS = np.linspace(-30.0, 30.0, 241)
_SURFACE_AXIS.setflags(write=False)


@dataclass(frozen=True, slots=True)
class MMSBowShockConnection:
    """Analysis result and metadata for one MMS bow-shock connection."""

    connection: ShockConnection
    simulation_time: str
    mms_start: str
    mms_end: str
    surface_x: NDArray[np.float64]
    normals: NDArray[np.float64]
    mms_position: NDArray[np.float64]
    bavg: NDArray[np.float64]

    def __post_init__(self) -> None:
        for name in (
            "surface_x",
            "normals",
            "mms_position",
            "bavg",
        ):
            value = np.array(getattr(self, name), dtype=np.float64, copy=True)
            value.setflags(write=False)
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class ConnectionPlotPaths:
    """Paths written by :func:`save_mms_bow_shock_connection_plots`."""

    two_d: Path
    three_d_png: Path | None
    three_d_html: Path | None


def _event_time(dataset: pv.DataSet) -> datetime:
    if TIME_EVENT_KEY not in dataset.field_data:
        raise ValueError(f"simulation lacks field_data[{TIME_EVENT_KEY!r}]")
    values = np.asarray(dataset.field_data[TIME_EVENT_KEY]).reshape(-1)
    if values.size != 1:
        raise ValueError(f"simulation must contain exactly one {TIME_EVENT_KEY!r}")
    return parse_datetime(str(values[0]))


def _datetime_value(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    return parse_datetime(value)


def resolve_mms_interval(
    event_time: str | datetime,
    *,
    window_seconds: float = 300.0,
    start: str | datetime | None = None,
    end: str | datetime | None = None,
) -> tuple[str, str]:
    """Resolve an MMS interval from an event time or explicit bounds."""

    if (start is None) != (end is None):
        raise ValueError("both start and end must be provided together")
    if start is not None and end is not None:
        start_time = _datetime_value(start)
        end_time = _datetime_value(end)
        if start_time > end_time:
            raise ValueError("MMS start time must not be after end time")
        return start_time.isoformat(), end_time.isoformat()

    try:
        seconds = float(window_seconds)
    except (TypeError, ValueError) as error:
        raise ValueError("MMS window must be positive and finite") from error
    if not math.isfinite(seconds) or seconds <= 0.0:
        raise ValueError("MMS window must be positive and finite")
    center = _datetime_value(event_time)
    half_window = timedelta(seconds=seconds / 2.0)
    return (center - half_window).isoformat(), (center + half_window).isoformat()


def _average_vector(averages: dict[str, float], prefix: str) -> NDArray[np.float64]:
    try:
        values = [float(averages[f"{prefix}_{axis}"]) for axis in "xyz"]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"MMS averages lack finite {prefix} components") from error
    vector = np.asarray(values, dtype=np.float64)
    if not np.isfinite(vector).all():
        raise ValueError(f"MMS averages lack finite {prefix} components")
    return vector


def build_mms_bow_shock_connection(
    simulation_path: str | Path,
    *,
    mms_window_seconds: float = 300.0,
    mms_start: str | datetime | None = None,
    mms_end: str | datetime | None = None,
    probe: int = 1,
    mode: Literal["auto", "brst", "fast"] = "auto",
    x_resolution: int = 512,
    chunk_size: int = 1024,
    smoothing_sigma: float = 5.0,
    shockfit_range: tuple[float, float] = (-5.0, 5.0),
) -> MMSBowShockConnection:
    """Build the notebook's complete simulation-to-MMS connection result."""

    if probe not in range(1, 5):
        raise ValueError("probe must be between 1 and 4")
    if mode not in {"auto", "brst", "fast"}:
        raise ValueError("mode must be one of: auto, brst, fast")
    if len(shockfit_range) != 2:
        raise ValueError("shockfit_range must contain lower and upper bounds")

    grid = load_simulation(simulation_path)
    event = _event_time(grid)
    start, end = resolve_mms_interval(
        event,
        window_seconds=mms_window_seconds,
        start=mms_start,
        end=mms_end,
    )
    calc_velocity_divergence(grid)
    fit_bow_shock(grid)
    shock_region = extract_shockfit_range(
        grid,
        lower=shockfit_range[0],
        upper=shockfit_range[1],
    )
    raw_surface = get_bow_shock_surface(
        shock_region,
        x_resolution=x_resolution,
        chunk_size=chunk_size,
        refine_minimum=True,
    )
    surface_x = smooth_bow_shock_surface(raw_surface, sigma=smoothing_sigma)
    normals = calc_bow_shock_normals(
        surface_x,
        y=_SURFACE_AXIS,
        z=_SURFACE_AXIS,
    )

    mms_data = load_mms_data(
        start,
        end,
        probe=probe,
        mode=mode,
        coordinates="gsm",
    )
    averages = average_plotted_values(mms_data)
    mms_position = _average_vector(averages, "satellite_location")
    bavg = _average_vector(averages, "magnetic_field")
    connection = analyze_shock_connection(
        surface_x,
        normals,
        y=_SURFACE_AXIS,
        z=_SURFACE_AXIS,
        mms_position=mms_position,
        bavg=bavg,
    )
    return MMSBowShockConnection(
        connection,
        event.isoformat(),
        start,
        end,
        surface_x,
        normals,
        mms_position,
        bavg,
    )


def save_mms_bow_shock_connection_plots(
    result: MMSBowShockConnection,
    output_directory: str | Path,
    *,
    output_prefix: str = "shock_connection",
    three_d_output: Literal["png", "html", "both"] = "png",
    dpi: int = 300,
) -> ConnectionPlotPaths:
    """Save the 2D angle map and selected 3D connection views."""

    if three_d_output not in {"png", "html", "both"}:
        raise ValueError("three_d_output must be one of: png, html, both")
    if not output_prefix.strip():
        raise ValueError("output_prefix must not be empty")
    if not isinstance(dpi, int) or dpi <= 0:
        raise ValueError("dpi must be a positive integer")

    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    two_d_path = destination / f"{output_prefix}_2d.png"
    three_d_png = (
        destination / f"{output_prefix}_3d.png"
        if three_d_output in {"png", "both"}
        else None
    )
    three_d_html = (
        destination / f"{output_prefix}_3d.html"
        if three_d_output in {"html", "both"}
        else None
    )

    figure, _ = plot_shock_angle_contour(
        result.connection,
        simulation_time=result.simulation_time,
    )
    try:
        figure.savefig(two_d_path, dpi=dpi, bbox_inches="tight")
    finally:
        import matplotlib.pyplot as plt

        plt.close(figure)

    plotter: pv.Plotter | None = None
    try:
        if three_d_png is not None or three_d_html is not None:
            plotter = plot_shock_connection_3d(
                result.connection,
                plotter=pv.Plotter(off_screen=True),
                show=False,
            )
            if three_d_png is not None:
                plotter.screenshot(three_d_png, return_img=False)
            if three_d_html is not None:
                try:
                    plotter.export_html(three_d_html)
                except ImportError as error:
                    raise RuntimeError(
                        "HTML export requires Trame; install it with "
                        "`pip install 'pyvista[jupyter]'`"
                    ) from error
    finally:
        if plotter is not None:
            plotter.close()

    return ConnectionPlotPaths(two_d_path, three_d_png, three_d_html)


__all__ = [
    "ConnectionPlotPaths",
    "MMSBowShockConnection",
    "build_mms_bow_shock_connection",
    "resolve_mms_interval",
    "save_mms_bow_shock_connection_plots",
]
