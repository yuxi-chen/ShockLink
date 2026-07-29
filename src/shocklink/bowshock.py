"""Triangulated bow-shock geometry."""

from dataclasses import dataclass

import numpy as np
import pyvista as pv
from numpy.typing import ArrayLike

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


def fit_bow_shock(
    dataset: pv.DataSet,
    *,
    divergence_name: str = "div(U)",
    velocity_name: str = "U [km/s]",
    x_offset: float = 2.0,
    axis_resolution: int = 1000,
    cross_resolution: int = 1000,
) -> BowShockParaboloid:
    """Detect maximum compression and fit an X-directed paraboloid."""

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

    return BowShockParaboloid(
        loc0=loc0,
        loc1=loc1,
        loc2=loc2,
        curvature=curvature,
    )


__all__ = [
    "BowShockParaboloid",
    "BowShockSurface",
    "fit_bow_shock",
]
