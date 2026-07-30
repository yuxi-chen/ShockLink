import numpy as np
import pytest

import shocklink.bowshock as bowshock
from shocklink.bowshock import calc_bow_shock_normal_angle, calc_bow_shock_normals
from shocklink.exceptions import DatasetError


def _surface_grid(
    y: np.ndarray,
    z: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    return np.meshgrid(y, z, indexing="ij")


def test_calc_bow_shock_normals_matches_plane_on_nonuniform_grid() -> None:
    y = np.array([-2.0, -0.5, 1.0, 3.0])
    z = np.array([-3.0, -1.0, 0.5, 2.5])
    yy, zz = _surface_grid(y, z)
    surface = 5.0 + 0.25 * yy - 0.5 * zz
    expected = np.array([1.0, -0.25, 0.5])
    expected /= np.linalg.norm(expected)

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert normals.shape == (len(y), len(z), 3)
    assert np.isfinite(normals).all()
    np.testing.assert_allclose(
        normals,
        np.broadcast_to(expected, normals.shape),
        atol=1.0e-12,
    )
    np.testing.assert_allclose(np.linalg.norm(normals, axis=-1), 1.0)
    assert np.all(normals[..., 0] > 0.0)


def test_calc_bow_shock_normals_matches_paraboloid() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-3.0, 3.0, 7)
    yy, zz = _surface_grid(y, z)
    surface = 10.0 - 0.5 * (yy**2 + zz**2)
    expected = np.stack((np.ones_like(yy), yy, zz), axis=-1)
    expected /= np.linalg.norm(expected, axis=-1, keepdims=True)

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    np.testing.assert_allclose(normals, expected, atol=1.0e-12)


def test_calc_bow_shock_normals_interpolates_interior_hole() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-2.0, 2.0, 5)
    yy, zz = _surface_grid(y, z)
    surface = 4.0 + 0.5 * yy - 0.25 * zz
    surface[2, 2] = np.nan
    expected = np.array([1.0, -0.5, 0.25])
    expected /= np.linalg.norm(expected)

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert np.isfinite(normals).all()
    np.testing.assert_allclose(
        normals,
        np.broadcast_to(expected, normals.shape),
        atol=1.0e-12,
    )


def test_calc_bow_shock_normals_fills_edge_and_corner_gaps() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-2.0, 2.0, 5)
    yy, zz = _surface_grid(y, z)
    surface = 6.0 - 0.2 * yy**2 - 0.3 * zz**2
    surface[0, :] = np.nan
    surface[-1, -1] = np.nan

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert np.isfinite(normals).all()
    np.testing.assert_allclose(np.linalg.norm(normals, axis=-1), 1.0)
    assert np.all(normals[..., 0] > 0.0)


@pytest.mark.parametrize(
    ("axis_name", "values", "message"),
    [
        ("y", [], "nonempty 1D"),
        ("z", [0.0, 1.0], "at least three"),
        ("y", [0.0, 1.0], "at least three"),
        ("z", [[0.0, 1.0, 2.0]], "nonempty 1D"),
        ("y", ["zero", "one", "two"], "numbers"),
        ("z", [0.0, 1.0, 10**1000], "numbers"),
        ("z", [0.0, np.nan, 2.0], "finite"),
        ("y", [0.0, 1.0, np.inf], "finite"),
        ("z", [0.0, 1.0, 1.0], "strictly increasing"),
        ("y", [0.0, 2.0, 1.0], "strictly increasing"),
    ],
    ids=[
        "empty-y",
        "short-z",
        "short-y",
        "multidimensional-z",
        "nonnumeric-y",
        "overflow-z",
        "nan-z",
        "infinite-y",
        "duplicate-z",
        "decreasing-y",
    ],
)
def test_calc_bow_shock_normals_rejects_invalid_axis(
    axis_name: str,
    values: object,
    message: str,
) -> None:
    coordinates = {
        "y": np.arange(3.0),
        "z": np.arange(3.0),
    }
    coordinates[axis_name] = values

    with pytest.raises(DatasetError, match=message):
        calc_bow_shock_normals(
            np.zeros((3, 3)),
            y=coordinates["y"],
            z=coordinates["z"],
        )


@pytest.mark.parametrize(
    ("surface", "message"),
    [
        ([["not-a-number"] * 3 for _ in range(3)], "numeric"),
        (np.zeros((2, 3)), "shape"),
        (np.full((3, 3), np.inf), "infinity"),
        (np.full((3, 3), -np.inf), "infinity"),
    ],
    ids=["nonnumeric", "wrong-shape", "positive-infinity", "negative-infinity"],
)
def test_calc_bow_shock_normals_rejects_invalid_surface(
    surface: object,
    message: str,
) -> None:
    with pytest.raises(DatasetError, match=message):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_requires_three_finite_surface_samples() -> None:
    surface = np.full((3, 3), np.nan)
    surface[0, :2] = (1.0, 2.0)

    with pytest.raises(DatasetError, match="at least three"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_rejects_collinear_interpolation_samples() -> None:
    surface = np.full((4, 4), np.nan)
    surface[1, :] = np.arange(4.0)

    with pytest.raises(DatasetError, match="Could not interpolate"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(4.0),
            z=np.arange(4.0),
        )


def test_calc_bow_shock_normals_does_not_mutate_inputs() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-3.0, 3.0, 5)
    yy, zz = _surface_grid(y, z)
    surface = 5.0 + 0.25 * yy - 0.5 * zz
    surface[2, 2] = np.nan
    original_surface = surface.copy()
    original_y = y.copy()
    original_z = z.copy()

    calc_bow_shock_normals(surface, y=y, z=z)

    assert np.array_equal(surface, original_surface, equal_nan=True)
    np.testing.assert_array_equal(y, original_y)
    np.testing.assert_array_equal(z, original_z)


def test_calc_bow_shock_normal_angle_measures_direction_in_degrees() -> None:
    normals = np.array(
        [
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )

    angles = calc_bow_shock_normal_angle(normals, [2.0, 0.0, 0.0])

    assert angles.shape == (3,)
    np.testing.assert_allclose(angles, [0.0, 180.0, 90.0], atol=1.0e-12)


def test_calc_bow_shock_normal_angle_preserves_leading_normal_shape() -> None:
    normals = np.zeros((2, 3, 3))
    normals[..., 2] = 4.0

    angles = calc_bow_shock_normal_angle(normals, [0.0, 0.0, 3.0])

    assert angles.shape == (2, 3)
    np.testing.assert_array_equal(angles, np.zeros((2, 3)))


@pytest.mark.parametrize(
    ("normals", "vector", "message"),
    [
        (np.ones((2, 2)), [1.0, 0.0, 0.0], "shape"),
        (["x", "y", "z"], [1.0, 0.0, 0.0], "numeric"),
        (np.array([1.0 + 0.0j, 0.0, 0.0]), [1.0, 0.0, 0.0], "real"),
        (np.array([np.nan, 0.0, 0.0]), [1.0, 0.0, 0.0], "finite"),
        (np.zeros(3), [1.0, 0.0, 0.0], "positive"),
        (np.array([1.0, 0.0, 0.0]), [1.0, 0.0], "shape"),
        (np.array([1.0, 0.0, 0.0]), ["x", "y", "z"], "numeric"),
        (np.array([1.0, 0.0, 0.0]), [1.0 + 0.0j, 0.0, 0.0], "real"),
        (np.array([1.0, 0.0, 0.0]), [np.inf, 0.0, 0.0], "finite"),
        (np.array([1.0, 0.0, 0.0]), [0.0, 0.0, 0.0], "positive"),
    ],
)
def test_calc_bow_shock_normal_angle_rejects_invalid_inputs(
    normals: object,
    vector: object,
    message: str,
) -> None:
    with pytest.raises(DatasetError, match=message):
        calc_bow_shock_normal_angle(normals, vector)


def test_calc_bow_shock_normal_angle_is_public() -> None:
    assert "calc_bow_shock_normal_angle" in bowshock.__all__
