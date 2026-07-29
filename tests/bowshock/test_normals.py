import numpy as np

from shocklink.bowshock import calc_bow_shock_normals


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

    assert normals.shape == surface.shape + (3,)
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
