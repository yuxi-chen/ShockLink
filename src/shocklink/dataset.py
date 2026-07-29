"""Create and visualize cuts from PyVista datasets."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pyvista as pv
from numpy.typing import NDArray

from shocklink.exceptions import DatasetError

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


def _resolve_scalar_name(cut: pv.PolyData, requested: str) -> str:
    """Resolve an exact, case-insensitive, or pressure-alias array name."""

    names = list(cut.point_data.keys()) + list(cut.cell_data.keys())
    if requested in names:
        return requested

    lowered = {name.lower(): name for name in names}
    if requested.strip().lower() in {"p", "pressure"}:
        for candidate in ("P [nPa]", "p", "P", "pressure"):
            if candidate in names:
                return candidate
            if candidate.lower() in lowered:
                return lowered[candidate.lower()]

    match = lowered.get(requested.strip().lower())
    if match is not None:
        return match

    available = ", ".join(names) if names else "<none>"
    raise DatasetError(
        f"Scalar array {requested!r} is unavailable. Available arrays: {available}"
    )


def _cut_plane_metadata(
    cut: pv.PolyData,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Read and validate plane metadata stored by :func:`get_2d_cut`."""

    missing = [
        key
        for key in (CUT_NORMAL_KEY, CUT_ORIGIN_KEY)
        if key not in cut.field_data
    ]
    if missing:
        raise DatasetError(
            f"Cut is missing plane metadata: {', '.join(missing)}"
        )

    normal_values = np.asarray(cut.field_data[CUT_NORMAL_KEY]).reshape(-1)
    origin_values = np.asarray(cut.field_data[CUT_ORIGIN_KEY]).reshape(-1)
    normal = _normal_vector(normal_values)
    origin = _vector3(origin_values, label="origin")
    return normal, origin


def _view_up(normal: NDArray[np.float64]) -> NDArray[np.float64]:
    """Return a stable in-plane camera up vector."""

    z_axis = np.array([0.0, 0.0, 1.0])
    reference = (
        np.array([0.0, 1.0, 0.0])
        if abs(float(np.dot(normal, z_axis))) > 0.9
        else z_axis
    )
    projected = reference - np.dot(reference, normal) * normal
    return projected / np.linalg.norm(projected)


def _plot_range(
    value: Sequence[float] | None,
    *,
    name: str,
) -> tuple[float, float] | None:
    """Validate an optional, strictly increasing plot range."""

    if value is None:
        return None
    try:
        limits = np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DatasetError(f"{name} must contain two numeric values") from error
    if limits.shape != (2,):
        raise DatasetError(f"{name} must contain exactly two values")
    if not np.isfinite(limits).all():
        raise DatasetError(f"{name} must contain finite values")
    if limits[0] >= limits[1]:
        raise DatasetError(f"{name} minimum must be less than its maximum")
    return float(limits[0]), float(limits[1])


def plot_2d_cut(
    cut: pv.PolyData,
    *,
    scalars: str = "p",
    xrange: Sequence[float] | None = None,
    yrange: Sequence[float] | None = None,
    plotter: pv.Plotter | None = None,
    show: bool = True,
    cmap: str = "viridis",
    **mesh_kwargs: object,
) -> pv.Plotter:
    """Plot a planar cut, colored by pressure by default."""

    if not isinstance(cut, pv.PolyData):
        raise DatasetError(
            f"2D cut must be PolyData; received {type(cut).__name__}"
        )
    if cut.n_points == 0 or cut.n_cells == 0:
        raise DatasetError("Cannot plot an empty 2D cut")

    normal, _origin = _cut_plane_metadata(cut)
    scalar_name = _resolve_scalar_name(cut, scalars)
    xlimits = _plot_range(xrange, name="xrange")
    ylimits = _plot_range(yrange, name="yrange")

    supplied_bar_args = mesh_kwargs.pop("scalar_bar_args", None)
    if supplied_bar_args is None:
        scalar_bar_args: dict[str, object] = {}
    elif isinstance(supplied_bar_args, Mapping):
        scalar_bar_args = dict(supplied_bar_args)
    else:
        raise DatasetError("scalar_bar_args must be a mapping")
    scalar_bar_args.setdefault("title", scalar_name)

    active_plotter = plotter if plotter is not None else pv.Plotter()
    active_plotter.add_mesh(
        cut,
        scalars=scalar_name,
        cmap=cmap,
        scalar_bar_args=scalar_bar_args,
        **mesh_kwargs,
    )
    active_plotter.add_axes()
    active_plotter.view_vector(normal, viewup=_view_up(normal))
    active_plotter.enable_parallel_projection()
    if xlimits is not None or ylimits is not None:
        bounds = cut.bounds
        active_plotter.reset_camera(
            bounds=(
                *(xlimits or (bounds.x_min, bounds.x_max)),
                *(ylimits or (bounds.y_min, bounds.y_max)),
                bounds.z_min,
                bounds.z_max,
            ),
            render=False,
        )
    if show:
        active_plotter.show()
    return active_plotter


__all__ = ["get_2d_cut", "plot_2d_cut"]
