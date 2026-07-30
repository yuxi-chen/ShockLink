"""Read and normalize BATSRUS Tecplot data with PyVista."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyvista as pv
from numpy.typing import NDArray

from shocklink.exceptions import DatasetError

DEFAULT_COORDINATE_COMPONENTS = ("X [R]", "Y [R]", "Z [R]")
DEFAULT_MAGNETIC_COMPONENTS = ("B_x [nT]", "B_y [nT]", "B_z [nT]")
DEFAULT_VELOCITY_COMPONENTS = (
    "U_x [km_s]",
    "U_y [km_s]",
    "U_z [km_s]",
)


def _components(
    grid: pv.UnstructuredGrid,
    names: tuple[str, str, str],
    *,
    label: str,
) -> NDArray[np.number]:
    """Return three scalar point arrays as one vector matrix."""

    missing = [name for name in names if name not in grid.point_data]
    if missing:
        raise DatasetError(f"Missing {label} component array(s): {', '.join(missing)}")

    arrays = [np.asarray(grid.point_data[name]) for name in names]
    invalid = [
        name
        for name, values in zip(names, arrays, strict=True)
        if values.ndim != 1 or len(values) != grid.n_points
    ]
    if invalid:
        raise DatasetError(
            f"Invalid {label} component length or shape: {', '.join(invalid)}"
        )
    return np.column_stack(arrays)


def _single_zone(data: pv.MultiBlock, *, source: Path) -> pv.UnstructuredGrid:
    """Extract the sole nonempty unstructured zone."""

    zones = [
        block
        for block in data
        if block is not None and (block.n_points > 0 or block.n_cells > 0)
    ]
    if len(zones) != 1:
        raise DatasetError(
            f"Expected exactly one nonempty zone in {source}; found {len(zones)}"
        )

    zone = zones[0]
    if not isinstance(zone, pv.UnstructuredGrid):
        raise DatasetError(
            f"Tecplot zone in {source} must be an UnstructuredGrid; "
            f"received {type(zone).__name__}"
        )
    return zone


def read_tecplot(
    path: str | Path,
    *,
    coordinate_components: tuple[str, str, str] = DEFAULT_COORDINATE_COMPONENTS,
    magnetic_components: tuple[str, str, str] = DEFAULT_MAGNETIC_COMPONENTS,
    velocity_components: tuple[str, str, str] = DEFAULT_VELOCITY_COMPONENTS,
    magnetic_name: str = "B [nT]",
    velocity_name: str = "U [km/s]",
) -> pv.UnstructuredGrid:
    """Read one Tecplot zone and normalize its geometry and vector fields.

    Parameters
    ----------
    path : str or pathlib.Path
        Existing ``.dat`` Tecplot file containing exactly one nonempty zone.
    coordinate_components, magnetic_components, velocity_components : tuple of str
        Names of the three scalar point arrays holding the X/Y/Z coordinates,
        magnetic field, and velocity components, respectively.  Each component
        must be a one-dimensional array with one value per grid point.
    magnetic_name, velocity_name : str
        Names assigned to the normalized ``(n_points, 3)`` magnetic and velocity
        point-data arrays.

    Returns
    -------
    pyvista.UnstructuredGrid
        The input zone with points replaced by the finite coordinate array and
        normalized vector point data.  Magnetic and velocity samples are kept as
        read, so missing values may remain in these vector arrays.

    Raises
    ------
    DatasetError
        If the path is not an existing ``.dat`` file, the reader does not return
        one nonempty unstructured zone, or required coordinate/vector arrays are
        absent or have incompatible shapes.  Coordinates must be finite.
    """

    source = Path(path)
    if not source.is_file():
        raise DatasetError(f"Tecplot file does not exist: {source}")
    if source.suffix.lower() != ".dat":
        raise DatasetError(f"Tecplot input must use the .dat extension: {source}")

    try:
        loaded = pv.read(source)
    except Exception as error:
        raise DatasetError(f"Could not read Tecplot file {source}: {error}") from error

    if not isinstance(loaded, pv.MultiBlock):
        raise DatasetError(
            f"Tecplot reader returned {type(loaded).__name__} for {source}; "
            "expected MultiBlock"
        )

    grid = _single_zone(loaded, source=source)
    coordinates = _components(
        grid,
        coordinate_components,
        label="coordinate",
    )
    if not np.isfinite(coordinates).all():
        raise DatasetError(f"Coordinate arrays in {source} must contain finite values")

    magnetic_field = _components(
        grid,
        magnetic_components,
        label="magnetic-field",
    )
    velocity = _components(
        grid,
        velocity_components,
        label="velocity",
    )

    grid.points = coordinates
    grid.point_data[magnetic_name] = magnetic_field
    grid.point_data[velocity_name] = velocity
    return grid


__all__ = ["read_tecplot"]
