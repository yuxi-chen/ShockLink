import warnings

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


@pytest.mark.parametrize("axis_name", ["y", "z"])
def test_calc_bow_shock_normals_rejects_complex_axis(
    axis_name: str,
) -> None:
    coordinates = {
        "y": np.arange(3.0),
        "z": np.arange(3.0),
    }
    coordinates[axis_name] = np.array([0.0, 1.0 + 1.0j, 2.0])

    with warnings.catch_warnings():
        warnings.simplefilter("error", np.exceptions.ComplexWarning)
        with pytest.raises(DatasetError, match="real numbers"):
            calc_bow_shock_normals(
                np.zeros((3, 3)),
                y=coordinates["y"],
                z=coordinates["z"],
            )


@pytest.mark.parametrize(
    ("axis_name", "values"),
    [
        ("y", np.array(["0", "1", "2"])),
        (
            "z",
            np.arange(
                "2020-01-01",
                "2020-01-04",
                dtype="datetime64[D]",
            ),
        ),
        ("y", np.arange(3).astype("timedelta64[D]")),
        ("z", np.array([False, True, True])),
    ],
    ids=["numeric-strings", "datetime", "timedelta", "boolean"],
)
def test_calc_bow_shock_normals_rejects_nonnumeric_axis_dtype(
    axis_name: str,
    values: np.ndarray,
) -> None:
    coordinates = {
        "y": np.arange(3.0),
        "z": np.arange(3.0),
    }
    coordinates[axis_name] = values

    with pytest.raises(DatasetError, match="numbers"):
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


def test_calc_bow_shock_normals_rejects_complex_surface() -> None:
    surface = np.zeros((3, 3), dtype=np.complex128)
    surface[1, 1] = 1.0j

    with warnings.catch_warnings():
        warnings.simplefilter("error", np.exceptions.ComplexWarning)
        with pytest.raises(DatasetError, match="real numbers"):
            calc_bow_shock_normals(
                surface,
                y=np.arange(3.0),
                z=np.arange(3.0),
            )


@pytest.mark.parametrize(
    "surface",
    [
        np.full((3, 3), "0"),
        np.full((3, 3), np.datetime64("2020-01-01")),
        np.full((3, 3), np.timedelta64(1, "D")),
        np.zeros((3, 3), dtype=np.bool_),
    ],
    ids=["numeric-strings", "datetime", "timedelta", "boolean"],
)
def test_calc_bow_shock_normals_rejects_nonnumeric_surface_dtype(
    surface: np.ndarray,
) -> None:
    with pytest.raises(DatasetError, match="numeric"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_accepts_integer_axes_and_surface() -> None:
    normals = calc_bow_shock_normals(
        np.zeros((3, 3), dtype=np.int32),
        y=[-1, 0, 1],
        z=np.arange(3, dtype=np.uint64),
    )

    expected = np.zeros((3, 3, 3))
    expected[..., 0] = 1.0
    np.testing.assert_array_equal(normals, expected)


def test_calc_bow_shock_normals_translates_surface_conversion_overflow() -> None:
    surface = [[10**1000, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]

    with pytest.raises(DatasetError, match="numeric"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_handles_extreme_finite_slope() -> None:
    y = np.array([-1.0, 0.0, 1.0])
    z = np.array([-1.0, 0.0, 1.0])
    yy, _ = _surface_grid(y, z)
    surface = 1.0e200 * yy

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert np.isfinite(normals).all()
    np.testing.assert_allclose(np.linalg.norm(normals, axis=-1), 1.0)
    assert np.all(normals[..., 0] > 0.0)
    np.testing.assert_allclose(normals[..., 1], -1.0)


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


def test_calc_bow_shock_normals_translates_griddata_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = np.zeros((3, 3))
    surface[1, 1] = np.nan

    def fail_griddata(*args: object, **kwargs: object) -> np.ndarray:
        raise RuntimeError("interpolator failed")

    monkeypatch.setattr(bowshock, "griddata", fail_griddata)

    with pytest.raises(DatasetError, match="Could not interpolate"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_rejects_wrong_interpolation_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = np.zeros((3, 3))
    surface[1, 1] = np.nan

    def wrong_shape_griddata(*args: object, **kwargs: object) -> np.ndarray:
        del args, kwargs
        return np.zeros((2, 2))

    monkeypatch.setattr(bowshock, "griddata", wrong_shape_griddata)

    with pytest.raises(DatasetError, match="Could not interpolate"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_rejects_broadcast_nearest_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = np.zeros((3, 3))
    surface[0, 0] = np.nan
    surface[2, 2] = np.nan
    methods: list[str] = []

    def broadcast_griddata(
        points: object,
        values: object,
        coordinates: tuple[np.ndarray, np.ndarray],
        *,
        method: str,
    ) -> np.ndarray:
        del points, values, coordinates
        methods.append(method)
        if method == "linear":
            return surface.copy()
        return np.array([0.0])

    monkeypatch.setattr(bowshock, "griddata", broadcast_griddata)

    with pytest.raises(DatasetError, match="Could not interpolate"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )
    assert methods == ["linear", "nearest"]


@pytest.mark.parametrize("complex_stage", ["linear", "nearest"])
def test_calc_bow_shock_normals_rejects_complex_interpolation_output(
    monkeypatch: pytest.MonkeyPatch,
    complex_stage: str,
) -> None:
    surface = np.zeros((3, 3))
    surface[1, 1] = np.nan

    def complex_griddata(
        points: object,
        values: object,
        coordinates: tuple[np.ndarray, np.ndarray],
        *,
        method: str,
    ) -> np.ndarray:
        del points, values, coordinates
        if method == "linear":
            if complex_stage == "linear":
                interpolated = np.zeros((3, 3), dtype=np.complex128)
                interpolated[1, 1] = 1.0j
                return interpolated
            return surface.copy()
        return np.array([1.0 + 1.0j])

    monkeypatch.setattr(bowshock, "griddata", complex_griddata)

    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        with pytest.raises(DatasetError, match="Could not interpolate"):
            calc_bow_shock_normals(
                surface,
                y=np.arange(3.0),
                z=np.arange(3.0),
            )
    assert not any(
        issubclass(warning.category, np.exceptions.ComplexWarning)
        for warning in caught_warnings
    )


def test_calc_bow_shock_normals_copies_read_only_interpolation_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = np.zeros((3, 3))
    surface[1, 1] = np.nan
    interpolated = np.zeros((3, 3))
    interpolated.setflags(write=False)

    def read_only_griddata(*args: object, **kwargs: object) -> np.ndarray:
        del args, kwargs
        return interpolated

    monkeypatch.setattr(bowshock, "griddata", read_only_griddata)

    normals = calc_bow_shock_normals(
        surface,
        y=np.arange(3.0),
        z=np.arange(3.0),
    )

    expected = np.zeros((3, 3, 3))
    expected[..., 0] = 1.0
    np.testing.assert_array_equal(normals, expected)


def test_calc_bow_shock_normals_restores_original_finite_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-2.0, 2.0, 5)
    yy, zz = _surface_grid(y, z)
    analytic_surface = 4.0 + 0.5 * yy - 0.25 * zz
    surface = analytic_surface.copy()
    surface[2, 2] = np.nan
    valid = np.isfinite(surface)
    methods: list[str] = []

    def perturbed_griddata(
        points: object,
        values: object,
        coordinates: tuple[np.ndarray, np.ndarray],
        *,
        method: str,
    ) -> np.ndarray:
        del points, values, coordinates
        methods.append(method)
        interpolated = analytic_surface.copy()
        interpolated[valid] += 1000.0
        return interpolated

    monkeypatch.setattr(bowshock, "griddata", perturbed_griddata)

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    expected = np.array([1.0, -0.5, 0.25])
    expected /= np.linalg.norm(expected)
    np.testing.assert_allclose(
        normals,
        np.broadcast_to(expected, normals.shape),
        atol=1.0e-12,
    )
    assert methods == ["linear"]


def test_calc_bow_shock_normals_rejects_nonfinite_interpolation_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    surface = np.zeros((3, 3))
    surface[1, 1] = np.nan

    def nonfinite_griddata(
        points: object,
        values: object,
        coordinates: tuple[np.ndarray, np.ndarray],
        *,
        method: str,
    ) -> np.ndarray:
        del points, values, method
        return np.full(np.shape(coordinates[0]), np.nan)

    monkeypatch.setattr(bowshock, "griddata", nonfinite_griddata)

    with pytest.raises(DatasetError, match="Could not interpolate"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


@pytest.mark.parametrize("infinite_value", [np.inf, -np.inf])
def test_calc_bow_shock_normals_rejects_infinite_linear_interpolation(
    monkeypatch: pytest.MonkeyPatch,
    infinite_value: float,
) -> None:
    surface = np.zeros((3, 3))
    surface[1, 1] = np.nan
    methods: list[str] = []

    def infinite_griddata(
        points: object,
        values: object,
        coordinates: tuple[np.ndarray, np.ndarray],
        *,
        method: str,
    ) -> np.ndarray:
        del points, values, coordinates
        methods.append(method)
        if method == "linear":
            interpolated = np.zeros((3, 3))
            interpolated[1, 1] = infinite_value
            return interpolated
        return np.array([0.0])

    monkeypatch.setattr(bowshock, "griddata", infinite_griddata)

    with pytest.raises(DatasetError, match="Could not interpolate"):
        calc_bow_shock_normals(
            surface,
            y=np.arange(3.0),
            z=np.arange(3.0),
        )
    assert methods == ["linear"]


def test_calc_bow_shock_normals_skips_interpolation_for_finite_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_griddata(*args: object, **kwargs: object) -> np.ndarray:
        pytest.fail("griddata was called for a fully finite surface")

    monkeypatch.setattr(bowshock, "griddata", fail_griddata)

    normals = calc_bow_shock_normals(
        np.zeros((3, 3)),
        y=np.arange(3.0),
        z=np.arange(3.0),
    )

    assert np.isfinite(normals).all()


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


def test_calc_bow_shock_normals_translates_gradient_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_gradient(*args: object, **kwargs: object) -> list[np.ndarray]:
        raise ValueError("gradient failed")

    monkeypatch.setattr(bowshock.np, "gradient", fail_gradient)

    with pytest.raises(DatasetError, match="Could not calculate"):
        calc_bow_shock_normals(
            np.zeros((3, 3)),
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_rejects_malformed_derivative_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def malformed_gradient(*args: object, **kwargs: object) -> list[np.ndarray]:
        del args, kwargs
        return [np.zeros((2, 3)), np.zeros((3, 3))]

    monkeypatch.setattr(bowshock.np, "gradient", malformed_gradient)

    with pytest.raises(DatasetError, match="derivative.*shape"):
        calc_bow_shock_normals(
            np.zeros((3, 3)),
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_rejects_complex_derivative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def complex_gradient(*args: object, **kwargs: object) -> list[np.ndarray]:
        del args, kwargs
        dx_dy = np.zeros((3, 3), dtype=np.complex128)
        dx_dy[1, 1] = 1.0j
        return [dx_dy, np.zeros((3, 3))]

    monkeypatch.setattr(bowshock.np, "gradient", complex_gradient)

    with warnings.catch_warnings():
        warnings.simplefilter("error", np.exceptions.ComplexWarning)
        with pytest.raises(DatasetError, match="derivatives.*real numbers"):
            calc_bow_shock_normals(
                np.zeros((3, 3)),
                y=np.arange(3.0),
                z=np.arange(3.0),
            )


def test_calc_bow_shock_normals_rejects_nonfinite_derivative(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def nonfinite_gradient(*args: object, **kwargs: object) -> list[np.ndarray]:
        del args, kwargs
        dx_dy = np.zeros((3, 3))
        dx_dy[1, 1] = np.nan
        return [dx_dy, np.zeros((3, 3))]

    monkeypatch.setattr(bowshock.np, "gradient", nonfinite_gradient)

    with pytest.raises(DatasetError, match="derivatives must be finite"):
        calc_bow_shock_normals(
            np.zeros((3, 3)),
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_rejects_malformed_normal_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def malformed_stack(*args: object, **kwargs: object) -> np.ndarray:
        del args, kwargs
        return np.zeros((3, 3, 2))

    monkeypatch.setattr(bowshock.np, "stack", malformed_stack)

    with pytest.raises(DatasetError, match="normal.*shape"):
        calc_bow_shock_normals(
            np.zeros((3, 3)),
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_rejects_nonfinite_normal_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    normal_components = np.zeros((3, 3, 3))
    normal_components[..., 0] = 1.0
    normal_components[1, 1, 1] = np.nan

    def nonfinite_stack(*args: object, **kwargs: object) -> np.ndarray:
        del args, kwargs
        return normal_components.copy()

    monkeypatch.setattr(bowshock.np, "stack", nonfinite_stack)

    with pytest.raises(DatasetError, match="normal.*finite"):
        calc_bow_shock_normals(
            np.zeros((3, 3)),
            y=np.arange(3.0),
            z=np.arange(3.0),
        )


def test_calc_bow_shock_normals_is_public() -> None:
    assert "calc_bow_shock_normals" in bowshock.__all__


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
