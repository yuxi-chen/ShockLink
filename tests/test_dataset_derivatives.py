import numpy as np
import pyvista as pv
import pytest

from shocklink.dataset import calc_velocity_divergence
from shocklink.exceptions import DatasetError


def _linear_velocity_grid(*, name: str = "U [km/s]") -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(4, 4, 4),
        spacing=(0.5, 0.75, 1.25),
        origin=(-1.0, -1.5, -2.5),
    )
    points = np.asarray(grid.points)
    grid.point_data[name] = points.copy()
    return grid


def test_calc_velocity_divergence_modifies_and_returns_input() -> None:
    grid = _linear_velocity_grid()

    result = calc_velocity_divergence(grid)

    assert result is grid
    np.testing.assert_allclose(grid.point_data["div(U)"], 3.0)


def test_calc_velocity_divergence_accepts_custom_names_and_replaces_output() -> None:
    grid = _linear_velocity_grid(name="velocity")
    grid.point_data["velocity divergence"] = np.full(grid.n_points, -99.0)

    calc_velocity_divergence(
        grid,
        velocity_name="velocity",
        output_name="velocity divergence",
    )

    np.testing.assert_allclose(
        grid.point_data["velocity divergence"],
        3.0,
    )


def test_calc_velocity_divergence_requires_point_velocity() -> None:
    grid = _linear_velocity_grid()
    del grid.point_data["U [km/s]"]

    with pytest.raises(DatasetError, match="unavailable in point data"):
        calc_velocity_divergence(grid)


def test_calc_velocity_divergence_requires_three_components() -> None:
    grid = _linear_velocity_grid()
    grid.point_data["U [km/s]"] = np.zeros(grid.n_points)

    with pytest.raises(DatasetError, match=r"must have shape .*3"):
        calc_velocity_divergence(grid)


def test_calc_velocity_divergence_requires_finite_velocity() -> None:
    grid = _linear_velocity_grid()
    grid.point_data["U [km/s]"][0, 0] = np.nan

    with pytest.raises(DatasetError, match="must contain finite values"):
        calc_velocity_divergence(grid)


@pytest.mark.parametrize("output_name", ["", "   "])
def test_calc_velocity_divergence_requires_output_name(
    output_name: str,
) -> None:
    with pytest.raises(DatasetError, match="output name must not be empty"):
        calc_velocity_divergence(
            _linear_velocity_grid(),
            output_name=output_name,
        )


def test_calc_velocity_divergence_wraps_filter_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_filter(
        self: pv.ImageData,
        **kwargs: object,
    ) -> pv.DataSet:
        raise RuntimeError("VTK failed")

    monkeypatch.setattr(pv.ImageData, "compute_derivative", fail_filter)

    with pytest.raises(
        DatasetError,
        match="Could not calculate velocity divergence: VTK failed",
    ):
        calc_velocity_divergence(_linear_velocity_grid())


def test_calc_velocity_divergence_requires_filter_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def omit_output(
        self: pv.ImageData,
        **kwargs: object,
    ) -> pv.DataSet:
        return self.copy()

    monkeypatch.setattr(pv.ImageData, "compute_derivative", omit_output)

    with pytest.raises(DatasetError, match="did not produce 'div\\(U\\)'"):
        calc_velocity_divergence(_linear_velocity_grid())


def test_calc_velocity_divergence_requires_scalar_filter_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def malformed_output(
        self: pv.ImageData,
        **kwargs: object,
    ) -> pv.DataSet:
        result = pv.PolyData(np.zeros((1, 3)))
        result.point_data["div(U)"] = np.zeros(1)
        return result

    monkeypatch.setattr(
        pv.ImageData,
        "compute_derivative",
        malformed_output,
    )

    with pytest.raises(DatasetError, match="invalid result shape"):
        calc_velocity_divergence(_linear_velocity_grid())
