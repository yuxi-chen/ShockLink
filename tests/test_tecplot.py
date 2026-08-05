from pathlib import Path

import numpy as np
import pyvista as pv
import pytest

from shocklink.exceptions import DatasetError
from shocklink.tecplot import read_tecplot


TITLE = 'TITLE="BATSRUS: 3D Data,2023/12/16 11:30:00.000"\n'
EXPECTED_TIME_EVENT = "2023-12-16T11:30:00.000+00:00"
TIME_EVENT_KEY = "time_event"


EXPECTED_POINTS = np.array(
    [
        [-2.0, -1.0, 0.0],
        [0.0, 1.0, 2.0],
        [3.0, 4.0, 5.0],
    ]
)
EXPECTED_B = np.array(
    [
        [1.0, 4.0, 7.0],
        [2.0, 5.0, 8.0],
        [3.0, 6.0, 9.0],
    ]
)
EXPECTED_U = np.array(
    [
        [-10.0, 1.0, 4.0],
        [-20.0, 2.0, 5.0],
        [-30.0, 3.0, 6.0],
    ]
)


def _raw_grid() -> pv.UnstructuredGrid:
    grid = pv.UnstructuredGrid()
    grid.points = np.zeros_like(EXPECTED_POINTS)
    grid.point_data["X [R]"] = EXPECTED_POINTS[:, 0]
    grid.point_data["Y [R]"] = EXPECTED_POINTS[:, 1]
    grid.point_data["Z [R]"] = EXPECTED_POINTS[:, 2]
    grid.point_data["B_x [nT]"] = EXPECTED_B[:, 0]
    grid.point_data["B_y [nT]"] = EXPECTED_B[:, 1]
    grid.point_data["B_z [nT]"] = EXPECTED_B[:, 2]
    grid.point_data["U_x [km_s]"] = EXPECTED_U[:, 0]
    grid.point_data["U_y [km_s]"] = EXPECTED_U[:, 1]
    grid.point_data["U_z [km_s]"] = EXPECTED_U[:, 2]
    return grid


def _sample_path(tmp_path: Path, *, header: str = TITLE) -> Path:
    path = tmp_path / "sample.dat"
    path.write_text(header, encoding="utf-8")
    return path


def test_read_tecplot_normalizes_geometry_and_vectors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    grid = read_tecplot(_sample_path(tmp_path))

    assert isinstance(grid, pv.UnstructuredGrid)
    np.testing.assert_allclose(grid.points, EXPECTED_POINTS)
    np.testing.assert_allclose(grid["B [nT]"], EXPECTED_B)
    np.testing.assert_allclose(grid["U [km/s]"], EXPECTED_U)
    assert np.asarray(grid.field_data[TIME_EVENT_KEY]).item() == EXPECTED_TIME_EVENT
    assert "B_x [nT]" in grid.point_data
    assert "U_x [km_s]" in grid.point_data


def test_read_tecplot_accepts_component_name_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    raw.point_data["x"] = raw.point_data.pop("X [R]")
    raw.point_data["y"] = raw.point_data.pop("Y [R]")
    raw.point_data["z"] = raw.point_data.pop("Z [R]")
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    grid = read_tecplot(
        _sample_path(tmp_path),
        coordinate_components=("x", "y", "z"),
    )

    np.testing.assert_allclose(grid.points, EXPECTED_POINTS)


def test_read_tecplot_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="does not exist"):
        read_tecplot(tmp_path / "missing.dat")


def test_read_tecplot_rejects_non_dat_input(tmp_path: Path) -> None:
    path = tmp_path / "sample.vtu"
    path.touch()

    with pytest.raises(DatasetError, match=r"\.dat"):
        read_tecplot(path)


def test_read_tecplot_wraps_pyvista_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_path: Path) -> pv.MultiBlock:
        raise RuntimeError("reader failed")

    monkeypatch.setattr(pv, "read", fail)

    with pytest.raises(DatasetError, match="Could not read.*sample.dat"):
        read_tecplot(_sample_path(tmp_path))


@pytest.mark.parametrize(
    "blocks",
    [
        [],
        [None],
        [_raw_grid(), _raw_grid()],
    ],
)
def test_read_tecplot_requires_exactly_one_nonempty_zone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    blocks: list[pv.UnstructuredGrid | None],
) -> None:
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock(blocks))

    with pytest.raises(DatasetError, match="exactly one nonempty zone"):
        read_tecplot(_sample_path(tmp_path))


def test_read_tecplot_requires_an_unstructured_grid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    surface = pv.PolyData(EXPECTED_POINTS)
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([surface]))

    with pytest.raises(DatasetError, match="UnstructuredGrid"):
        read_tecplot(_sample_path(tmp_path))


def test_read_tecplot_reports_missing_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    del raw.point_data["B_z [nT]"]
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    with pytest.raises(DatasetError, match=r"B_z \[nT\]"):
        read_tecplot(_sample_path(tmp_path))


def test_read_tecplot_rejects_nonfinite_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    raw.point_data["X [R]"][0] = np.nan
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    with pytest.raises(DatasetError, match="finite"):
        read_tecplot(_sample_path(tmp_path))


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ('TITLE="BATSRUS: 3D Data"\nZONE T="3D"\n', "does not contain"),
        (
            'TITLE="BATSRUS: 3D Data,2023/13/16 11:30:00.000"\n',
            "Invalid BATSRUS event timestamp",
        ),
    ],
)
def test_read_tecplot_rejects_missing_or_invalid_event_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    header: str,
    message: str,
) -> None:
    def unexpected_read(_path: Path) -> pv.MultiBlock:
        pytest.fail("PyVista must not run for an invalid Tecplot header")

    monkeypatch.setattr(pv, "read", unexpected_read)

    with pytest.raises(DatasetError, match=message):
        read_tecplot(_sample_path(tmp_path, header=header))
