from __future__ import annotations

import numpy as np
import pytest
import pyvista as pv

from shocklink.connectivity import _build_surface_mesh
from shocklink.exceptions import DatasetError, GeometryError


def _plane_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y = np.array([-1.0, 0.0, 1.0])
    z = np.array([-1.0, 0.0, 1.0])
    surface_x = np.full((3, 3), 5.0)
    normals = np.zeros((3, 3, 3))
    normals[..., 0] = 1.0
    return y, z, surface_x, normals


def test_build_surface_mesh_uses_only_complete_observed_quads() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    theta = np.full(surface_x.shape, 30.0)
    theta[0, 0] = np.nan

    mesh = _build_surface_mesh(surface_x, normals, theta, y=y, z=z)

    assert isinstance(mesh, pv.PolyData)
    assert mesh.n_cells == 6
    assert mesh.n_points == 8
    assert set(mesh.point_data) >= {"shock_normal", "theta_Bn [deg]"}
    np.testing.assert_allclose(mesh.point_data["theta_Bn [deg]"], 30.0)


def test_build_surface_mesh_winds_every_face_toward_positive_x() -> None:
    y, z, surface_x, normals = _plane_inputs()
    mesh = _build_surface_mesh(surface_x, normals, np.full(surface_x.shape, 45.0), y=y, z=z)
    face_normals = mesh.compute_normals(
        point_normals=False, cell_normals=True, auto_orient_normals=False
    ).cell_data["Normals"]
    assert np.all(face_normals[:, 0] > 0.0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"y": [1.0, 0.0, 2.0]}, "Y must be strictly increasing"),
        ({"surface_x": np.zeros((2, 2))}, "surface must have shape"),
        ({"normals": np.zeros((3, 3, 2))}, "normals must have shape"),
        ({"surface_x": np.full((3, 3), np.inf)}, "surface must not contain infinity"),
        ({"normals": np.full((3, 3, 3), np.nan)}, "normals must be finite"),
    ],
)
def test_build_surface_mesh_validates_inputs(kwargs: dict[str, object], message: str) -> None:
    y, z, surface_x, normals = _plane_inputs()
    values: dict[str, object] = {
        "surface_x": surface_x,
        "normals": normals,
        "theta_bn_deg": np.zeros((3, 3)),
        "y": y,
        "z": z,
    }
    values.update(kwargs)
    with pytest.raises((DatasetError, GeometryError), match=message):
        _build_surface_mesh(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_angle", [np.nan, np.inf, -np.inf])
def test_build_surface_mesh_rejects_nonfinite_angles_on_observed_points(
    bad_angle: float,
) -> None:
    y, z, surface_x, normals = _plane_inputs()
    theta = np.full(surface_x.shape, 30.0)
    theta[1, 1] = bad_angle

    with pytest.raises(DatasetError, match="angle must be finite where surface is observed"):
        _build_surface_mesh(surface_x, normals, theta, y=y, z=z)


def test_build_surface_mesh_allows_angle_nan_at_missing_surface_points() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    theta = np.full(surface_x.shape, 30.0)
    theta[0, 0] = np.nan

    mesh = _build_surface_mesh(surface_x, normals, theta, y=y, z=z)

    assert mesh.n_cells == 6
