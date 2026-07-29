import numpy as np
import pyvista as pv
import pytest

from shocklink.bowshock import extract_shockfit_range
from shocklink.exceptions import DatasetError


def _grid(*, name: str = "shockfit") -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(5, 2, 2),
        spacing=(0.5, 1.0, 1.0),
        origin=(-1.0, 0.0, 0.0),
    )
    grid.point_data[name] = grid.points[:, 0]
    return grid


def test_extract_shockfit_range_returns_cells_and_original_ids() -> None:
    region = extract_shockfit_range(
        _grid(),
        lower=-0.5,
        upper=0.5,
    )

    assert isinstance(region, pv.UnstructuredGrid)
    assert region.n_points > 0
    assert region.n_cells > 0
    assert "shockfit" in region.point_data
    assert "vtkOriginalPointIds" in region.point_data
    assert "vtkOriginalCellIds" in region.cell_data
    selected_values = region.point_data["shockfit"]
    assert np.any(selected_values == -0.5)
    assert np.any(selected_values == 0.5)


def test_extract_shockfit_range_controls_adjacent_cell_selection() -> None:
    adjacent = extract_shockfit_range(
        _grid(),
        lower=-0.5,
        upper=0.5,
        adjacent_cells=True,
    )
    exclusive = extract_shockfit_range(
        _grid(),
        lower=-0.5,
        upper=0.5,
        adjacent_cells=False,
    )

    assert adjacent.n_cells == 4
    assert exclusive.n_cells == 2
    assert adjacent.n_points > exclusive.n_points


def test_extract_shockfit_range_accepts_custom_name_and_equal_limits() -> None:
    region = extract_shockfit_range(
        _grid(name="fit residual"),
        lower=0.0,
        upper=0.0,
        shockfit_name="fit residual",
    )

    assert region.n_points > 0
    assert np.any(region.point_data["fit residual"] == 0.0)


def test_extract_shockfit_range_excludes_nonfinite_values() -> None:
    grid = _grid()
    values = np.array(grid.point_data["shockfit"], copy=True)
    values[values == 0.0] = np.nan
    grid.point_data["shockfit"] = values

    region = extract_shockfit_range(
        grid,
        lower=0.0,
        upper=0.0,
    )

    assert isinstance(region, pv.UnstructuredGrid)
    assert region.n_points == 0
    assert region.n_cells == 0


def test_extract_shockfit_range_allows_empty_selection() -> None:
    region = extract_shockfit_range(
        _grid(),
        lower=10.0,
        upper=11.0,
    )

    assert isinstance(region, pv.UnstructuredGrid)
    assert region.n_points == 0
    assert region.n_cells == 0


def test_extract_shockfit_range_requires_scalar_point_array() -> None:
    grid = _grid()
    grid.point_data["shockfit"] = np.zeros((grid.n_points, 3))

    with pytest.raises(DatasetError, match="point scalar"):
        extract_shockfit_range(grid, lower=-1.0, upper=1.0)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"shockfit_name": ""}, "name must not be empty"),
        ({"shockfit_name": "missing"}, "unavailable"),
        ({"lower": np.nan}, "finite numbers"),
        ({"upper": np.inf}, "finite numbers"),
        ({"lower": 2.0, "upper": 1.0}, "must not exceed"),
        ({"adjacent_cells": 1}, "must be a boolean"),
    ],
)
def test_extract_shockfit_range_rejects_invalid_arguments(
    changes: dict[str, object],
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "lower": -0.5,
        "upper": 0.5,
    }
    arguments.update(changes)

    with pytest.raises(DatasetError, match=message):
        extract_shockfit_range(_grid(), **arguments)


def test_extract_shockfit_range_wraps_pyvista_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_extraction(
        self: pv.ImageData,
        *_args: object,
        **_kwargs: object,
    ) -> pv.UnstructuredGrid:
        raise RuntimeError("VTK failed")

    monkeypatch.setattr(pv.ImageData, "extract_points", fail_extraction)

    with pytest.raises(
        DatasetError,
        match="Could not extract shockfit range: VTK failed",
    ):
        extract_shockfit_range(_grid(), lower=-0.5, upper=0.5)


def test_extract_shockfit_range_requires_unstructured_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def wrong_type(
        self: pv.ImageData,
        *_args: object,
        **_kwargs: object,
    ) -> pv.PolyData:
        return pv.PolyData()

    monkeypatch.setattr(pv.ImageData, "extract_points", wrong_type)

    with pytest.raises(DatasetError, match="expected UnstructuredGrid"):
        extract_shockfit_range(_grid(), lower=-0.5, upper=0.5)
