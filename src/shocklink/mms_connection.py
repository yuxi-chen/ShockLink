"""Build and export MMS magnetic connections to simulated bow shocks.

The public functions in this module reproduce the end-to-end workflow from the
MMS connection notebook without exposing command-line concerns.  The companion
tool in ``tools/mms_bow_shock_connection.py`` is a thin adapter over this API.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
from shocklink.swmf import read_mms_param_file
from shocklink.utilities import parse_datetime

# Surface extraction supplies this as its Y/Z default.  The downstream normal
# and intersection routines still need the matching coordinates explicitly.
_SURFACE_AXIS = np.linspace(-30.0, 30.0, 241)
_SURFACE_AXIS.setflags(write=False)


@dataclass(frozen=True, slots=True)
class MMSBowShockConnection:
    """Analysis result and metadata for one MMS bow-shock connection.

    The array attributes are defensive, read-only float64 copies, so callers
    can safely retain a result while passing derived arrays elsewhere.

    Attributes
    ----------
    connection
        Geometric field-line/shock intersection result.
    input_stem
        Original simulation filename without its suffix; used as the default
        plot-output prefix.
    simulation_time
        UTC simulation event timestamp in ISO-8601 form.
    mms_time
        UTC effective time read from the PARAM file used for the averages.
    surface_x
        Smoothed sampled shock X positions indexed by Y then Z.
    normals
        Outward shock normals corresponding to ``surface_x``.
    mms_position
        Interval-averaged MMS GSM position in Earth radii.
    bavg
        Interval-averaged MMS magnetic-field vector in GSM nT.
    """

    connection: ShockConnection
    input_stem: str
    simulation_time: str
    mms_time: str
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
    """Paths written by :func:`save_mms_bow_shock_connection_plots`.

    Attributes
    ----------
    two_d
        Saved PNG contour of the shock-normal angle.
    three_d_png
        Saved static 3D PNG, or ``None`` when PNG was not requested.
    three_d_html
        Saved interactive 3D HTML scene, or ``None`` when HTML was not
        requested.
    """

    two_d: Path
    three_d_png: Path | None
    three_d_html: Path | None


def _event_time(dataset: pv.DataSet) -> datetime:
    """Return the single normalized simulation event time from field data."""

    if TIME_EVENT_KEY not in dataset.field_data:
        raise ValueError(f"simulation lacks field_data[{TIME_EVENT_KEY!r}]")
    values = np.asarray(dataset.field_data[TIME_EVENT_KEY]).reshape(-1)
    if values.size != 1:
        raise ValueError(f"simulation must contain exactly one {TIME_EVENT_KEY!r}")
    return parse_datetime(str(values[0]))


def build_mms_bow_shock_connection(
    simulation_path: str | Path,
    *,
    param_file: str | Path,
    x_resolution: int = 512,
    chunk_size: int = 1024,
    smoothing_sigma: float = 5.0,
    shockfit_range: tuple[float, float] = (-5.0, 5.0),
) -> MMSBowShockConnection:
    """Build the notebook's complete simulation-to-MMS connection result.

    The PARAM file supplies the effective MMS time, interval-averaged GSM
    magnetic field, and MMS GSM position. No MMS products are downloaded by
    this function.

    Parameters
    ----------
    simulation_path
        DAT file, VTM file, or directory containing a VTM simulation output.
    param_file
        PARAM.in file produced by ``create_swmf_input()``.
    x_resolution
        Number of X samples used for each bow-shock surface column.
    chunk_size
        Number of Y-Z columns sampled in one batch.
    smoothing_sigma
        Gaussian smoothing width in surface-grid cells.
    shockfit_range
        Lower and upper residual bounds used to retain cells near the fitted
        bow shock.

    Returns
    -------
    MMSBowShockConnection
        Connection geometry, source intervals, sampled arrays, and average MMS
        vectors.

    Raises
    ------
    ValueError
        If public workflow options or required MMS averages are invalid.
    DatasetError, GeometryError
        If the simulation cannot support a valid observed shock connection.
    """

    if len(shockfit_range) != 2:
        raise ValueError("shockfit_range must contain lower and upper bounds")

    grid = load_simulation(simulation_path)
    event = _event_time(grid)
    param_values = read_mms_param_file(param_file)
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

    mms_position = np.asarray(
        [param_values.location.x, param_values.location.y, param_values.location.z],
        dtype=np.float64,
    )
    bavg = np.asarray(param_values.magnetic_field, dtype=np.float64)
    connection = analyze_shock_connection(
        surface_x,
        normals,
        y=_SURFACE_AXIS,
        z=_SURFACE_AXIS,
        mms_position=mms_position,
        bavg=bavg,
    )
    return MMSBowShockConnection(
        connection=connection,
        input_stem=Path(simulation_path).stem,
        simulation_time=event.isoformat(),
        mms_time=param_values.time.isoformat(),
        surface_x=surface_x,
        normals=normals,
        mms_position=mms_position,
        bavg=bavg,
    )


def save_mms_bow_shock_connection_plots(
    result: MMSBowShockConnection,
    output_directory: str | Path,
    *,
    output_prefix: str | None = None,
    three_d_output: Literal["png", "html", "both"] = "png",
    dpi: int = 600,
) -> ConnectionPlotPaths:
    """Save the 2D angle map and selected 3D connection views.

    The 2D angle contour is always written as PNG. The 3D scene is rendered
    off-screen so command-line use does not require a display; HTML output uses
    PyVista's Trame exporter.

    Parameters
    ----------
    result
        Completed connection workflow to render.
    output_directory
        Directory created as needed to contain the generated files.
    output_prefix
        Filename prefix before ``_2d.png``, ``_3d.png``, and ``_3d.html``.
        When omitted, use ``{input_stem}_shock_connection``.
    three_d_output
        Requested 3D format: static PNG, interactive HTML, or both.
    dpi
        Positive resolution for the 2D PNG.

    Returns
    -------
    ConnectionPlotPaths
        Paths of the files written during this call.

    Raises
    ------
    ValueError
        If output options are invalid.
    RuntimeError
        If interactive HTML output is requested without Trame installed.
    """

    if three_d_output not in {"png", "html", "both"}:
        raise ValueError("three_d_output must be one of: png, html, both")
    if output_prefix is not None and not output_prefix.strip():
        raise ValueError("output_prefix must not be empty")
    if not isinstance(dpi, int) or dpi <= 0:
        raise ValueError("dpi must be a positive integer")

    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    prefix = output_prefix or f"{result.input_stem}_shock_connection"
    two_d_path = destination / f"{prefix}_2d.png"
    three_d_png = (
        destination / f"{prefix}_3d.png"
        if three_d_output in {"png", "both"}
        else None
    )
    three_d_html = (
        destination / f"{prefix}_3d.html"
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
    "save_mms_bow_shock_connection_plots",
]
