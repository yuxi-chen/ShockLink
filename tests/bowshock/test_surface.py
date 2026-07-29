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


def test_get_bow_shock_surface_chunks_columns_without_changing_results(
    monkeypatch,
) -> None:
    grid = _compression_grid()
    y = np.array([-1.5, 0.0, 1.5])
    z = np.array([-1.0, 1.0])
    original_sample = pv.PolyData.sample
    calls = 0

    def count_sample_calls(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original_sample(self, *args, **kwargs)

    monkeypatch.setattr(pv.PolyData, "sample", count_sample_calls)

    chunked = get_bow_shock_surface(
        grid,
        y=y,
        z=z,
        x_resolution=161,
        chunk_size=2,
    )

    assert calls == 3
    calls = 0
    single_batch = get_bow_shock_surface(
        grid,
        y=y,
        z=z,
        x_resolution=161,
        chunk_size=100,
    )
    assert calls == 1
    np.testing.assert_array_equal(chunked, single_batch)


def test_get_bow_shock_surface_keeps_invalid_columns_as_nan() -> None:
    surface = get_bow_shock_surface(
        _compression_grid(),
        y=np.array([-3.0, 0.0, 3.0]),
        z=np.array([0.0]),
        x_resolution=161,
        chunk_size=1,
    )

    assert surface.shape == (3, 1)
    assert np.isnan(surface[0, 0])
    assert np.isfinite(surface[1, 0])
    assert np.isnan(surface[2, 0])


def test_get_bow_shock_surface_accepts_custom_name_and_x_range() -> None:
    y = np.array([0.0])
    z = np.array([0.0])

    surface = get_bow_shock_surface(
        _compression_grid(name="compression"),
        y=y,
        z=z,
        divergence_name="compression",
        x_range=(5.0, 7.0),
        x_resolution=81,
        chunk_size=1,
    )

    np.testing.assert_allclose(surface, [[6.0]], atol=0.05)


def test_get_bow_shock_surface_does_not_modify_input() -> None:
    grid = _compression_grid()
    original_points = np.array(grid.points, copy=True)
    original_names = list(grid.point_data)
    original_divergence = np.array(grid.point_data["div(U)"], copy=True)

    get_bow_shock_surface(
        grid,
        y=np.array([0.0]),
        z=np.array([0.0]),
        x_resolution=81,
        chunk_size=1,
    )

    np.testing.assert_array_equal(grid.points, original_points)
    assert list(grid.point_data) == original_names
    np.testing.assert_array_equal(
        grid.point_data["div(U)"],
        original_divergence,
    )
