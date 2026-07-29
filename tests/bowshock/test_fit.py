import numpy as np
import pyvista as pv
import pytest

import shocklink.bowshock as bowshock
from shocklink.bowshock import fit_bow_shock
from shocklink.exceptions import DatasetError


def _paraboloid_compression_grid() -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(25, 33, 3),
        spacing=(0.5, 0.25, 1.0),
        origin=(0.0, -4.0, -1.0),
    )
    x, y, z = grid.points.T
    residual = x - (10.0 - 0.5 * (y**2 + z**2))
    grid.point_data["div(U)"] = -np.exp(-((residual / 0.15) ** 2))
    return grid


def test_fit_bow_shock_recovers_analytic_paraboloid() -> None:
    fit = fit_bow_shock(
        _paraboloid_compression_grid(),
        x_offset=2.0,
        axis_resolution=240,
        cross_resolution=320,
    )

    np.testing.assert_allclose(fit.loc0, (10.0, 0.0, 0.0), atol=0.03)
    np.testing.assert_allclose(fit.loc1, (8.0, -2.0, 0.0), atol=0.03)
    np.testing.assert_allclose(fit.loc2, (8.0, 2.0, 0.0), atol=0.03)
    assert fit.curvature == pytest.approx(0.5, abs=0.02)
    assert fit.x_at(3.0, 0.0) == pytest.approx(5.5, abs=0.2)


def _profile(
    points: list[tuple[float, float, float]],
    divergence: list[float],
    *,
    valid: list[int] | None = None,
) -> pv.PolyData:
    profile = pv.PolyData(np.asarray(points))
    profile.point_data["div(U)"] = divergence
    if valid is not None:
        profile.point_data["vtkValidPointMask"] = valid
    return profile


def test_fit_bow_shock_calculates_missing_divergence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grid = _paraboloid_compression_grid()
    expected = np.array(grid.point_data["div(U)"], copy=True)
    del grid.point_data["div(U)"]
    grid.point_data["U [km/s]"] = np.zeros((grid.n_points, 3))
    calls: list[tuple[str, str]] = []

    def calculate(
        dataset: pv.DataSet,
        *,
        velocity_name: str,
        output_name: str,
    ) -> pv.DataSet:
        calls.append((velocity_name, output_name))
        dataset.point_data[output_name] = expected
        return dataset

    monkeypatch.setattr(bowshock, "calc_velocity_divergence", calculate)

    fit = fit_bow_shock(
        grid,
        axis_resolution=240,
        cross_resolution=320,
    )

    assert calls == [("U [km/s]", "div(U)")]
    assert fit.loc0[0] == pytest.approx(10.0, abs=0.03)


def test_fit_bow_shock_ignores_invalid_axis_samples(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grid = _paraboloid_compression_grid()
    axis_profile = _profile(
        [(2.0, 0.0, 0.0), (10.0, 0.0, 0.0)],
        [-100.0, -1.0],
        valid=[0, 1],
    )
    monkeypatch.setattr(
        bowshock,
        "get_x_axis_profile",
        lambda *_args, **_kwargs: axis_profile,
    )

    fit = fit_bow_shock(grid, cross_resolution=320)

    assert fit.loc0[0] == pytest.approx(10.0)


def test_fit_bow_shock_requires_a_peak_on_each_y_side(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    grid = _paraboloid_compression_grid()
    cross_profile = _profile(
        [(8.0, 0.0, 0.0), (8.0, 2.0, 0.0)],
        [-1.0, -2.0],
    )
    monkeypatch.setattr(
        bowshock,
        "sample_line",
        lambda *_args, **_kwargs: cross_profile,
    )

    with pytest.raises(DatasetError, match="negative-Y"):
        fit_bow_shock(grid, axis_resolution=240)


def test_fit_bow_shock_rejects_vector_divergence() -> None:
    grid = _paraboloid_compression_grid()
    grid.point_data["div(U)"] = np.zeros((grid.n_points, 3))

    with pytest.raises(DatasetError, match="point scalar"):
        fit_bow_shock(grid)


@pytest.mark.parametrize("x_offset", [0.0, -1.0, np.nan])
def test_fit_bow_shock_rejects_invalid_offset(x_offset: float) -> None:
    with pytest.raises(DatasetError, match="finite and positive"):
        fit_bow_shock(
            _paraboloid_compression_grid(),
            x_offset=x_offset,
        )


def test_fit_bow_shock_rejects_cross_line_outside_grid() -> None:
    with pytest.raises(DatasetError, match="outside dataset bounds"):
        fit_bow_shock(
            _paraboloid_compression_grid(),
            x_offset=20.0,
            axis_resolution=240,
        )


def test_fit_bow_shock_rejects_invalid_sampling_resolution() -> None:
    with pytest.raises(DatasetError, match="resolution"):
        fit_bow_shock(
            _paraboloid_compression_grid(),
            axis_resolution=0,
        )
