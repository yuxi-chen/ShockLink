"""Triangulated bow-shock geometry."""

from dataclasses import dataclass

import numpy as np
import pyvista as pv
from numpy.typing import ArrayLike, NDArray
from vtkmodules.vtkCommonDataModel import vtkStaticCellLocator

from shocklink.dataset import (
    calc_velocity_divergence,
    get_x_axis_profile,
    sample_line,
)
from shocklink.exceptions import DatasetError, GeometryError


@dataclass(frozen=True, slots=True)
class BowShockParaboloid:
    """Axisymmetric bow-shock fit directed along the X axis."""

    loc0: ArrayLike
    loc1: ArrayLike
    loc2: ArrayLike
    curvature: float

    def __post_init__(self) -> None:
        for name in ("loc0", "loc1", "loc2"):
            try:
                location = np.array(
                    getattr(self, name),
                    dtype=np.float64,
                    copy=True,
                )
            except (TypeError, ValueError) as error:
                raise GeometryError(
                    f"{name} must contain exactly three finite values"
                ) from error
            if location.shape != (3,):
                raise GeometryError(
                    f"{name} must contain exactly three values"
                )
            if not np.isfinite(location).all():
                raise GeometryError(f"{name} must contain finite values")
            location.setflags(write=False)
            object.__setattr__(self, name, location)

        if not np.allclose(self.loc0[1:], 0.0, rtol=0.0, atol=1.0e-12):
            raise GeometryError("loc0 must lie on the X axis")
        if self.loc1[1] >= 0.0:
            raise GeometryError("loc1 must lie on the negative Y side")
        if self.loc2[1] <= 0.0:
            raise GeometryError("loc2 must lie on the positive Y side")

        try:
            curvature = float(self.curvature)
        except (TypeError, ValueError) as error:
            raise GeometryError("curvature must be a finite positive value") from error
        if not np.isfinite(curvature):
            raise GeometryError("curvature must be finite")
        if curvature <= 0.0:
            raise GeometryError("curvature must be positive")
        object.__setattr__(self, "curvature", curvature)

    def x_at(self, y: ArrayLike, z: ArrayLike) -> np.ndarray:
        """Evaluate the fitted surface at transverse coordinates."""

        y_values = np.asarray(y, dtype=np.float64)
        z_values = np.asarray(z, dtype=np.float64)
        return np.asarray(
            self.loc0[0]
            - self.curvature * (y_values**2 + z_values**2)
        )

    def residual_at(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
    ) -> np.ndarray:
        """Return the signed X residual from the fitted surface."""

        return np.asarray(x, dtype=np.float64) - self.x_at(y, z)


@dataclass(frozen=True, slots=True)
class BowShockSurface:
    """A named triangular surface representing a bow shock."""

    vertices: ArrayLike
    faces: ArrayLike
    name: str = "bow_shock"

    def __post_init__(self) -> None:
        vertices = np.array(self.vertices, dtype=np.float64, copy=True)
        raw_faces = np.asarray(self.faces)

        if vertices.ndim != 2 or vertices.shape[1:] != (3,):
            raise GeometryError("surface vertices must be an N x 3 array")
        if len(vertices) < 3:
            raise GeometryError("a surface requires at least three vertices")
        if not np.isfinite(vertices).all():
            raise GeometryError("surface vertices must be finite")
        if raw_faces.ndim != 2 or raw_faces.shape[1:] != (3,):
            raise GeometryError("surface faces must be an M x 3 array")
        if not np.issubdtype(raw_faces.dtype, np.integer):
            raise GeometryError("surface faces must contain integer vertex indices")

        faces = np.array(raw_faces, dtype=np.int64, copy=True)
        if faces.size and (faces.min() < 0 or faces.max() >= len(vertices)):
            raise GeometryError("surface face contains an invalid vertex index")
        if not self.name.strip():
            raise ValueError("surface name must not be empty")

        vertices.setflags(write=False)
        faces.setflags(write=False)
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "faces", faces)


def _valid_profile_samples(
    profile: pv.PolyData,
    *,
    divergence_name: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return profile points, divergence, and a valid-sample mask."""

    if divergence_name not in profile.point_data:
        raise DatasetError(
            f"Line profile is missing divergence array {divergence_name!r}"
        )
    values = np.asarray(profile.point_data[divergence_name])
    if values.shape != (profile.n_points,):
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be a point scalar"
        )
    try:
        valid = np.isfinite(values)
    except TypeError as error:
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be numeric"
        ) from error
    valid &= np.isfinite(profile.points).all(axis=1)
    if "vtkValidPointMask" in profile.point_data:
        point_mask = np.asarray(profile.point_data["vtkValidPointMask"])
        if point_mask.shape != (profile.n_points,):
            raise DatasetError("Line profile has an invalid point mask")
        valid &= point_mask.astype(bool)
    return np.asarray(profile.points), values, valid


def _strongest_compression(
    points: np.ndarray,
    divergence: np.ndarray,
    candidates: np.ndarray,
    *,
    label: str,
) -> np.ndarray:
    """Return the candidate location that maximizes ``-div(U)``."""

    indices = np.flatnonzero(candidates)
    if len(indices) == 0:
        raise DatasetError(f"No valid {label} compression samples were found")
    selected = indices[np.argmax(-divergence[indices])]
    return np.array(points[selected], dtype=np.float64, copy=True)


def extract_shockfit_range(
    dataset: pv.DataSet,
    *,
    lower: float,
    upper: float,
    shockfit_name: str = "shockfit",
    adjacent_cells: bool = True,
) -> pv.UnstructuredGrid:
    """Extract cells associated with an inclusive shock-fit residual range."""

    if not isinstance(shockfit_name, str) or not shockfit_name.strip():
        raise DatasetError("Shockfit array name must not be empty")
    if shockfit_name not in dataset.point_data:
        raise DatasetError(
            f"Shockfit array {shockfit_name!r} is unavailable in point data"
        )
    values = np.asarray(dataset.point_data[shockfit_name])
    if values.shape != (dataset.n_points,):
        raise DatasetError(
            f"Shockfit array {shockfit_name!r} must be a point scalar"
        )
    try:
        lower_limit = float(lower)
        upper_limit = float(upper)
    except (TypeError, ValueError) as error:
        raise DatasetError("Shockfit range limits must be finite numbers") from error
    if not np.isfinite((lower_limit, upper_limit)).all():
        raise DatasetError("Shockfit range limits must be finite numbers")
    if lower_limit > upper_limit:
        raise DatasetError(
            "Shockfit range lower limit must not exceed upper limit"
        )
    if not isinstance(adjacent_cells, bool):
        raise DatasetError("adjacent_cells must be a boolean")

    try:
        finite = np.isfinite(values)
    except TypeError as error:
        raise DatasetError(
            f"Shockfit array {shockfit_name!r} must be numeric"
        ) from error
    mask = finite & (values >= lower_limit) & (values <= upper_limit)
    try:
        extracted = dataset.extract_points(
            mask,
            adjacent_cells=adjacent_cells,
            include_cells=True,
            pass_point_ids=True,
            pass_cell_ids=True,
        )
    except Exception as error:
        raise DatasetError(
            f"Could not extract shockfit range: {error}"
        ) from error
    if not isinstance(extracted, pv.UnstructuredGrid):
        raise DatasetError(
            "PyVista shockfit extraction returned "
            f"{type(extracted).__name__}; expected UnstructuredGrid"
        )
    return extracted


def _surface_probe_source(
    dataset: pv.DataSet,
    *,
    divergence_name: str,
    divergence: np.ndarray,
) -> pv.DataSet:
    """Return a shallow geometry copy containing only divergence data."""

    source = dataset.copy(deep=False)
    source.point_data.clear()
    source.point_data[divergence_name] = divergence
    source.cell_data.clear()
    source.field_data.clear()
    return source


def get_bow_shock_surface(
    dataset: pv.DataSet,
    *,
    y: ArrayLike,
    z: ArrayLike,
    divergence_name: str = "div(U)",
    x_resolution: int = 512,
    x_range: tuple[float, float] | None = None,
    chunk_size: int = 1024,
) -> NDArray[np.float64]:
    """Return strongest-compression X locations on a regular Y-Z grid."""

    y_values = np.asarray(y, dtype=np.float64)
    z_values = np.asarray(z, dtype=np.float64)
    divergence = np.asarray(dataset.point_data[divergence_name])
    if x_range is None:
        bounds = dataset.bounds
        x_limits = (float(bounds.x_min), float(bounds.x_max))
    else:
        x_limits = x_range
    x_values = np.linspace(
        x_limits[0],
        x_limits[1],
        x_resolution,
        dtype=np.float64,
    )

    yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
    column_y = yy.reshape(-1)
    column_z = zz.reshape(-1)

    source = _surface_probe_source(
        dataset,
        divergence_name=divergence_name,
        divergence=divergence,
    )
    locator = vtkStaticCellLocator()
    locator.SetDataSet(source)
    locator.BuildLocator()

    surface = np.full(len(column_y), np.nan, dtype=np.float64)
    for start in range(0, len(column_y), chunk_size):
        stop = min(start + chunk_size, len(column_y))
        count = stop - start
        points = np.empty(
            (count * len(x_values), 3),
            dtype=np.float64,
        )
        points[:, 0] = np.tile(x_values, count)
        points[:, 1] = np.repeat(column_y[start:stop], len(x_values))
        points[:, 2] = np.repeat(column_z[start:stop], len(x_values))

        sampled = pv.PolyData(points).sample(
            source,
            locator=locator,
            pass_cell_data=False,
            pass_point_data=False,
            pass_field_data=False,
        )
        sampled_divergence = np.asarray(
            sampled.point_data[divergence_name]
        ).reshape(count, len(x_values))
        valid = (
            np.asarray(sampled.point_data["vtkValidPointMask"])
            .astype(bool)
            .reshape(count, len(x_values))
        )
        valid &= np.isfinite(sampled_divergence)

        chunk_surface = np.full(count, np.nan, dtype=np.float64)
        has_valid = valid.any(axis=1)
        candidates = np.where(valid, sampled_divergence, np.inf)
        minima = np.argmin(candidates, axis=1)
        chunk_surface[has_valid] = x_values[minima[has_valid]]
        surface[start:stop] = chunk_surface

    return surface.reshape(len(y_values), len(z_values))


def fit_bow_shock(
    dataset: pv.DataSet,
    *,
    divergence_name: str = "div(U)",
    velocity_name: str = "U [km/s]",
    shockfit_name: str = "shockfit",
    x_offset: float = 2.0,
    axis_resolution: int = 1000,
    cross_resolution: int = 1000,
) -> BowShockParaboloid:
    """Detect maximum compression and fit an X-directed paraboloid."""

    if not isinstance(shockfit_name, str) or not shockfit_name.strip():
        raise DatasetError("Bow-shock shockfit name must not be empty")

    try:
        offset = float(x_offset)
    except (TypeError, ValueError) as error:
        raise DatasetError("Bow-shock X offset must be finite and positive") from error
    if not np.isfinite(offset) or offset <= 0.0:
        raise DatasetError("Bow-shock X offset must be finite and positive")

    if divergence_name not in dataset.point_data:
        calc_velocity_divergence(
            dataset,
            velocity_name=velocity_name,
            output_name=divergence_name,
        )
    source_divergence = np.asarray(dataset.point_data[divergence_name])
    if source_divergence.shape != (dataset.n_points,):
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be a point scalar"
        )

    axis_profile = get_x_axis_profile(
        dataset,
        resolution=axis_resolution,
    )
    axis_points, axis_divergence, axis_valid = _valid_profile_samples(
        axis_profile,
        divergence_name=divergence_name,
    )
    loc0 = _strongest_compression(
        axis_points,
        axis_divergence,
        axis_valid,
        label="X-axis",
    )

    bounds = dataset.bounds
    cross_x = float(loc0[0] - offset)
    if (
        not np.isfinite(cross_x)
        or cross_x < bounds.x_min
        or cross_x > bounds.x_max
    ):
        raise DatasetError(
            "Bow-shock cross-line X coordinate lies outside dataset bounds"
        )
    y_min = float(bounds.y_min)
    y_max = float(bounds.y_max)
    if not np.isfinite((y_min, y_max)).all() or y_min >= 0.0 or y_max <= 0.0:
        raise DatasetError(
            "Dataset Y bounds must be finite and span both sides of zero"
        )

    cross_profile = sample_line(
        dataset,
        pointa=(cross_x, y_min, 0.0),
        pointb=(cross_x, y_max, 0.0),
        resolution=cross_resolution,
    )
    cross_points, cross_divergence, cross_valid = _valid_profile_samples(
        cross_profile,
        divergence_name=divergence_name,
    )
    loc1 = _strongest_compression(
        cross_points,
        cross_divergence,
        cross_valid & (cross_points[:, 1] < 0.0),
        label="negative-Y",
    )
    loc2 = _strongest_compression(
        cross_points,
        cross_divergence,
        cross_valid & (cross_points[:, 1] > 0.0),
        label="positive-Y",
    )

    side_locations = np.vstack((loc1, loc2))
    radius2 = np.sum(side_locations[:, 1:] ** 2, axis=1)
    delta_x = loc0[0] - side_locations[:, 0]
    denominator = float(np.sum(radius2**2))
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise GeometryError("Bow-shock side locations are degenerate")
    curvature = float(np.sum(radius2 * delta_x) / denominator)

    fit = BowShockParaboloid(
        loc0=loc0,
        loc1=loc1,
        loc2=loc2,
        curvature=curvature,
    )
    x, y, z = np.asarray(dataset.points).T
    dataset.point_data[shockfit_name] = fit.residual_at(x, y, z).copy()
    return fit


__all__ = [
    "BowShockParaboloid",
    "BowShockSurface",
    "extract_shockfit_range",
    "fit_bow_shock",
    "get_bow_shock_surface",
]
