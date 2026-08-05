"""Straight magnetic-field connection to an extracted bow shock."""

from __future__ import annotations

import numpy as np
import pyvista as pv
from numpy.typing import ArrayLike, NDArray

from shocklink.exceptions import DatasetError, GeometryError

NORMAL_NAME = "shock_normal"
ANGLE_NAME = "theta_Bn [deg]"


def _real_array(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Return a real float64 copy, preserving NaNs for later validation."""
    try:
        array = np.array(values, dtype=np.float64, copy=True)
    except (TypeError, ValueError) as error:
        raise DatasetError(f"{label} must contain real numeric values") from error
    if np.iscomplexobj(values):
        raise DatasetError(f"{label} must contain real numeric values")
    return array


def _axis(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Validate a finite, strictly increasing coordinate axis."""
    axis = _real_array(values, label=label)
    if axis.ndim != 1 or axis.size < 2:
        raise DatasetError(f"{label} must be a one-dimensional axis with at least two values")
    if not np.isfinite(axis).all():
        raise DatasetError(f"{label} must be finite")
    if not np.all(np.diff(axis) > 0.0):
        raise DatasetError(f"{label} must be strictly increasing")
    return axis


def _vector(values: ArrayLike, *, label: str, nonzero: bool) -> NDArray[np.float64]:
    """Validate a finite three-component vector."""
    vector = _real_array(values, label=label)
    if vector.shape != (3,):
        raise DatasetError(f"{label} must contain exactly three values")
    if not np.isfinite(vector).all():
        raise DatasetError(f"{label} must be finite")
    if nonzero and np.linalg.norm(vector) == 0.0:
        raise DatasetError(f"{label} must be nonzero")
    return vector


def _build_surface_mesh(
    surface_x: ArrayLike,
    normals: ArrayLike,
    theta_bn_deg: ArrayLike,
    *,
    y: ArrayLike,
    z: ArrayLike,
) -> pv.PolyData:
    """Triangulate complete, observed cells of an X(Y, Z) shock surface."""
    y_values = _axis(y, label="Y")
    z_values = _axis(z, label="Z")
    surface = _real_array(surface_x, label="Bow-shock surface")
    normal_values = _real_array(normals, label="Bow-shock normals")
    angles = _real_array(theta_bn_deg, label="Shock-normal angle")
    shape = (len(y_values), len(z_values))
    if surface.shape != shape:
        raise DatasetError(f"Bow-shock surface must have shape {shape}")
    if normal_values.shape != shape + (3,):
        raise DatasetError(f"Bow-shock normals must have shape {shape + (3,)}")
    if angles.shape != shape:
        raise DatasetError(f"Shock-normal angle must have shape {shape}")
    if np.isinf(surface).any():
        raise DatasetError("Bow-shock surface must not contain infinity")
    valid = np.isfinite(surface)
    if not np.isfinite(normal_values[valid]).all():
        raise DatasetError("Bow-shock normals must be finite where surface is observed")
    if not np.isfinite(angles[valid]).all():
        raise DatasetError("Shock-normal angle must be finite where surface is observed")

    yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
    cell_valid = (
        valid[:-1, :-1]
        & valid[1:, :-1]
        & valid[:-1, 1:]
        & valid[1:, 1:]
    )
    if not np.any(cell_valid):
        raise GeometryError("Bow-shock surface contains no complete observed cells")

    point_ids = np.full(shape, -1, dtype=np.int64)
    point_ids[valid] = np.arange(np.count_nonzero(valid), dtype=np.int64)
    points = np.column_stack((surface[valid], yy[valid], zz[valid]))

    faces: list[tuple[int, int, int]] = []
    for i, j in zip(*np.nonzero(cell_valid)):
        p00 = int(point_ids[i, j])
        p10 = int(point_ids[i + 1, j])
        p01 = int(point_ids[i, j + 1])
        p11 = int(point_ids[i + 1, j + 1])
        faces.extend(((p00, p10, p01), (p10, p11, p01)))

    vtk_faces = np.empty((len(faces), 4), dtype=np.int64)
    vtk_faces[:, 0] = 3
    vtk_faces[:, 1:] = np.asarray(faces, dtype=np.int64)
    mesh = pv.PolyData(points, vtk_faces.reshape(-1))
    mesh.point_data[NORMAL_NAME] = normal_values[valid]
    mesh.point_data[ANGLE_NAME] = angles[valid]
    return mesh
