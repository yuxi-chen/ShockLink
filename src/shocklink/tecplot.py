"""Read and normalize BATSRUS Tecplot data with PyVista."""

from __future__ import annotations

from collections.abc import Sequence
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
CUT_NORMAL_KEY = "shocklink_cut_normal"
CUT_ORIGIN_KEY = "shocklink_cut_origin"

_AXIS_NORMALS = {
    "x": np.array([1.0, 0.0, 0.0]),
    "y": np.array([0.0, 1.0, 0.0]),
    "z": np.array([0.0, 0.0, 1.0]),
}


def _vector3(value: Sequence[float], *, label: str) -> NDArray[np.float64]:
    """Validate a finite three-component vector."""

    try:
        vector = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DatasetError(f"Cut {label} must contain three numbers") from error
    if vector.shape != (3,):
        raise DatasetError(f"Cut {label} must contain exactly three values")
    if not np.isfinite(vector).all():
        raise DatasetError(f"Cut {label} must contain finite values")
    return vector


def _normal_vector(
    normal: str | Sequence[float],
) -> NDArray[np.float64]:
    """Resolve an axis alias or normalize a numeric plane normal."""

    if isinstance(normal, str):
        try:
            return _AXIS_NORMALS[normal.strip().lower()].copy()
        except KeyError as error:
            raise DatasetError(
                "Cut normal must be 'x', 'y', 'z', or a three-component vector"
            ) from error

    vector = _vector3(normal, label="normal")
    magnitude = np.linalg.norm(vector)
    if magnitude == 0.0:
        raise DatasetError("Cut normal must be nonzero")
    return vector / magnitude


def get_2d_cut(
    grid: pv.DataSet,
    *,
    normal: str | Sequence[float] = "z",
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    generate_triangles: bool = False,
) -> pv.PolyData:
    """Return a planar PyVista cut, defaulting to the GSM equatorial plane."""

    cut_normal = _normal_vector(normal)
    cut_origin = _vector3(origin, label="origin")

    try:
        cut = grid.slice(
            normal=cut_normal,
            origin=cut_origin,
            generate_triangles=generate_triangles,
        )
    except Exception as error:
        raise DatasetError(f"Could not create 2D cut: {error}") from error

    if not isinstance(cut, pv.PolyData):
        raise DatasetError(
            f"PyVista slice returned {type(cut).__name__}; expected PolyData"
        )
    if cut.n_points == 0 or cut.n_cells == 0:
        raise DatasetError("Cut plane does not intersect the dataset")

    cut.field_data[CUT_NORMAL_KEY] = cut_normal
    cut.field_data[CUT_ORIGIN_KEY] = cut_origin
    return cut


def _components(
    grid: pv.UnstructuredGrid,
    names: tuple[str, str, str],
    *,
    label: str,
) -> NDArray[np.number]:
    """Return three scalar point arrays as one vector matrix."""

    missing = [name for name in names if name not in grid.point_data]
    if missing:
        raise DatasetError(
            f"Missing {label} component array(s): {', '.join(missing)}"
        )

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
    """Read one Tecplot zone and normalize its geometry and vector fields."""

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


__all__ = ["get_2d_cut", "read_tecplot"]
