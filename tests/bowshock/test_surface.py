import numpy as np
import pytest
import pyvista as pv

from shocklink import bowshock
from shocklink.bowshock import get_bow_shock_surface
from shocklink.exceptions import DatasetError


def _compression_grid(*, name: str = "div(U)") -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(65, 17, 13),
        spacing=(0.125, 0.25, 0.25),
        origin=(0.0, -2.0, -1.5),
    )
    x, y, z = grid.points.T
    surface_x = 6.0 - 0.25 * y**2 - 0.5 * z**2
    compression = -np.exp(-(((x - surface_x) / 0.18) ** 2))
    expansion = 3.0 * np.exp(-(((x - (surface_x - 1.0)) / 0.18) ** 2))
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


def test_get_bow_shock_surface_refines_quadratic_minimum_between_samples(
    monkeypatch,
) -> None:
    vertex = 3.25

    def sample_quadratic(self, *_args, **_kwargs):
        sampled = pv.PolyData(self.points)
        sampled.point_data["div(U)"] = (self.points[:, 0] - vertex) ** 2
        sampled.point_data["vtkValidPointMask"] = np.ones(self.n_points, dtype=np.uint8)
        return sampled

    monkeypatch.setattr(pv.PolyData, "sample", sample_quadratic)
    arguments = {
        "y": [0.0],
        "z": [0.0],
        "x_range": (0.0, 6.0),
        "x_resolution": 7,
    }

    discrete = get_bow_shock_surface(_compression_grid(), **arguments)
    refined = get_bow_shock_surface(
        _compression_grid(),
        refine_minimum=True,
        **arguments,
    )

    np.testing.assert_array_equal(discrete, [[3.0]])
    np.testing.assert_allclose(refined, [[vertex]])


@pytest.mark.parametrize(
    ("values", "valid", "minimum", "expected"),
    [
        ([0.0, 1.0, 2.0], [True, True, True], 0, 0.0),
        ([2.0, 1.0, 2.0], [True, False, True], 1, 1.0),
        ([2.0, 1.0, 1.0], [True, True, True], 1, 1.0),
        ([1.0, 1.0, 1.0], [True, True, True], 1, 1.0),
        ([0.0, 1.0, 0.0], [True, True, True], 1, 1.0),
        ([3.0, 1.0, 0.0], [True, True, True], 1, 1.0),
    ],
    ids=(
        "endpoint",
        "invalid-neighbor",
        "non-strict-minimum",
        "flat-curvature",
        "nonpositive-curvature",
        "vertex-outside-bracket",
    ),
)
def test_refine_surface_minima_keeps_discrete_location_when_unsafe(
    values: list[float],
    valid: list[bool],
    minimum: int,
    expected: float,
) -> None:
    refined = bowshock._refine_surface_minima(
        x_values=np.array([0.0, 1.0, 2.0]),
        sampled_divergence=np.array([values]),
        valid=np.array([valid]),
        minima=np.array([minimum]),
    )

    np.testing.assert_array_equal(refined, [expected])


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"divergence_name": ""}, "name must not be empty"),
        ({"y": []}, "Y coordinates must be a nonempty 1D array"),
        ({"y": [[0.0, 1.0]]}, "Y coordinates must be a nonempty 1D array"),
        ({"y": [0.0, np.nan]}, "Y coordinates must be finite"),
        ({"y": [0.0, 0.0]}, "Y coordinates must be strictly increasing"),
        ({"z": [1.0, 0.0]}, "Z coordinates must be strictly increasing"),
        ({"x_range": (1.0,)}, "X range must contain two values"),
        ({"x_range": (0.0, np.inf)}, "X range must be finite"),
        ({"x_range": (2.0, 1.0)}, "X range must be strictly increasing"),
        ({"x_resolution": 1}, "X resolution must be an integer of at least 2"),
        ({"x_resolution": True}, "X resolution must be an integer of at least 2"),
        ({"chunk_size": 0}, "Chunk size must be a positive integer"),
        ({"chunk_size": 1.5}, "Chunk size must be a positive integer"),
        ({"refine_minimum": 1}, "Refine minimum must be a boolean"),
    ],
)
def test_get_bow_shock_surface_rejects_invalid_arguments(
    changes: dict[str, object],
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "y": np.array([-1.0, 0.0, 1.0]),
        "z": np.array([-1.0, 0.0, 1.0]),
        "x_resolution": 81,
        "chunk_size": 2,
    }
    arguments.update(changes)

    with pytest.raises(DatasetError, match=message):
        get_bow_shock_surface(_compression_grid(), **arguments)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing", "unavailable"),
        ("vector", "point scalar"),
        ("nonfinite", "must be finite"),
        ("nonnumeric", "must be numeric"),
    ],
)
def test_get_bow_shock_surface_rejects_invalid_divergence(
    change: str,
    message: str,
) -> None:
    grid = _compression_grid()
    if change == "missing":
        del grid.point_data["div(U)"]
    elif change == "vector":
        grid.point_data["div(U)"] = np.zeros((grid.n_points, 3))
    elif change == "nonfinite":
        values = np.array(grid.point_data["div(U)"], copy=True)
        values[0] = np.nan
        grid.point_data["div(U)"] = values
    else:
        grid.point_data["div(U)"] = np.full(grid.n_points, "invalid")

    with pytest.raises(DatasetError, match=message):
        get_bow_shock_surface(grid, y=[0.0], z=[0.0])


def test_get_bow_shock_surface_rejects_invalid_default_x_bounds() -> None:
    grid = pv.ImageData(dimensions=(1, 2, 2))
    grid.point_data["div(U)"] = np.zeros(grid.n_points)

    with pytest.raises(DatasetError, match="X bounds"):
        get_bow_shock_surface(grid, y=[0.0], z=[0.0])


def test_get_bow_shock_surface_wraps_sampling_failure(monkeypatch) -> None:
    def fail_sampling(self, *_args, **_kwargs):
        raise RuntimeError("VTK failed")

    monkeypatch.setattr(pv.PolyData, "sample", fail_sampling)

    with pytest.raises(
        DatasetError,
        match="Could not sample bow-shock surface: VTK failed",
    ):
        get_bow_shock_surface(
            _compression_grid(),
            y=[0.0],
            z=[0.0],
        )


def test_get_bow_shock_surface_rejects_malformed_sample(monkeypatch) -> None:
    def malformed_sample(self, *_args, **_kwargs):
        return pv.PolyData(self.points)

    monkeypatch.setattr(pv.PolyData, "sample", malformed_sample)

    with pytest.raises(DatasetError, match="missing sampled divergence"):
        get_bow_shock_surface(
            _compression_grid(),
            y=[0.0],
            z=[0.0],
        )
