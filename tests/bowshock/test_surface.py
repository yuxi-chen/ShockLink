import numpy as np
import pyvista as pv

from shocklink.bowshock import get_bow_shock_surface


def _compression_grid(*, name: str = "div(U)") -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(65, 17, 13),
        spacing=(0.125, 0.25, 0.25),
        origin=(0.0, -2.0, -1.5),
    )
    x, y, z = grid.points.T
    surface_x = 6.0 - 0.25 * y**2 - 0.5 * z**2
    compression = -np.exp(-((x - surface_x) / 0.18) ** 2)
    expansion = 3.0 * np.exp(-((x - (surface_x - 1.0)) / 0.18) ** 2)
    grid.point_data[name] = compression + expansion
    return grid


def _expected_surface(y: np.ndarray, z: np.ndarray) -> np.ndarray:
    yy, zz = np.meshgrid(y, z, indexing="ij")
    return 6.0 - 0.25 * yy**2 - 0.5 * zz**2


def test_get_bow_shock_surface_recovers_minimum_divergence_layer() -> None:
    y = np.array([-1.5, 0.25, 1.75])
    z = np.array([-1.25, 0.5])

    surface = get_bow_shock_surface(
        _compression_grid(),
        y=y,
        z=z,
        x_resolution=321,
    )

    assert surface.shape == (len(y), len(z))
    np.testing.assert_allclose(
        surface,
        _expected_surface(y, z),
        atol=0.15,
    )
