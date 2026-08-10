from pathlib import Path

import numpy as np
import pyvista as pv
import pytest

from shocklink.exceptions import DatasetError
from shocklink.io import TIME_EVENT_KEY, load_simulation


TITLE = 'TITLE="BATSRUS: 3D Data,2023/12/16 11:30:00.000"\n'
EXPECTED_TIME_EVENT = "2023-12-16T11:30:00.000+00:00"

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


def _raw_grid(*, cleaned: bool = False) -> pv.UnstructuredGrid:
    grid = pv.UnstructuredGrid()
    grid.points = np.zeros_like(EXPECTED_POINTS)
    coordinate_names = ("X", "Y", "Z") if cleaned else ("X [R]", "Y [R]", "Z [R]")
    magnetic_names = (
        ("B_x", "B_y", "B_z")
        if cleaned
        else ("B_x [nT]", "B_y [nT]", "B_z [nT]")
    )
    velocity_names = (
        ("U_x", "U_y", "U_z")
        if cleaned
        else ("U_x [km_s]", "U_y [km_s]", "U_z [km_s]")
    )
    for name, values in zip(coordinate_names, EXPECTED_POINTS.T, strict=True):
        grid.point_data[name] = values
    for name, values in zip(magnetic_names, EXPECTED_B.T, strict=True):
        grid.point_data[name] = values
    for name, values in zip(velocity_names, EXPECTED_U.T, strict=True):
        grid.point_data[name] = values
    return grid


def _sample_path(tmp_path: Path, *, header: str = TITLE) -> Path:
    path = tmp_path / "sample.dat"
    path.write_text(header, encoding="utf-8")
    return path


def _cleaned_leaf(*, structured: bool) -> pv.DataSet:
    if structured:
        grid = pv.StructuredGrid()
        grid.dimensions = (3, 1, 1)
        grid.points = EXPECTED_POINTS
        for name, values in zip(("B_x", "B_y", "B_z"), EXPECTED_B.T, strict=True):
            grid.point_data[name] = values
        for name, values in zip(("U_x", "U_y", "U_z"), EXPECTED_U.T, strict=True):
            grid.point_data[name] = values
    else:
        grid = _raw_grid(cleaned=True)
        grid.points = EXPECTED_POINTS
    return grid


def _write_single_vtm(tmp_path: Path, *, structured: bool = True) -> Path:
    root = pv.MultiBlock()
    root["zone-a"] = _cleaned_leaf(structured=structured)
    root.field_data[TIME_EVENT_KEY] = EXPECTED_TIME_EVENT
    path = tmp_path / "sample.vtm"
    root.save(path)
    return path


def test_load_simulation_normalizes_dat_geometry_vectors_and_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    grid = load_simulation(_sample_path(tmp_path))

    assert isinstance(grid, pv.UnstructuredGrid)
    np.testing.assert_allclose(grid.points, EXPECTED_POINTS)
    np.testing.assert_allclose(grid["B [nT]"], EXPECTED_B)
    np.testing.assert_allclose(grid["U [km/s]"], EXPECTED_U)
    assert np.asarray(grid.field_data[TIME_EVENT_KEY]).item() == EXPECTED_TIME_EVENT


def test_load_simulation_detects_converter_cleaned_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid(cleaned=True)
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    grid = load_simulation(_sample_path(tmp_path))

    np.testing.assert_allclose(grid.points, EXPECTED_POINTS)
    np.testing.assert_allclose(grid["B [nT]"], EXPECTED_B)
    np.testing.assert_allclose(grid["U [km/s]"], EXPECTED_U)


def test_load_simulation_accepts_component_name_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    raw.point_data["x"] = raw.point_data.pop("X [R]")
    raw.point_data["y"] = raw.point_data.pop("Y [R]")
    raw.point_data["z"] = raw.point_data.pop("Z [R]")
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    grid = load_simulation(
        _sample_path(tmp_path),
        coordinate_components=("x", "y", "z"),
    )

    np.testing.assert_allclose(grid.points, EXPECTED_POINTS)


def test_load_simulation_retains_existing_geometry_without_coordinate_arrays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    raw.points = EXPECTED_POINTS
    for name in ("X [R]", "Y [R]", "Z [R]"):
        del raw.point_data[name]
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    grid = load_simulation(_sample_path(tmp_path))

    np.testing.assert_allclose(grid.points, EXPECTED_POINTS)


def test_load_simulation_rejects_missing_input(tmp_path: Path) -> None:
    with pytest.raises(DatasetError, match="does not exist"):
        load_simulation(tmp_path / "missing.dat")


def test_load_simulation_rejects_unsupported_suffix(tmp_path: Path) -> None:
    path = tmp_path / "sample.vtu"
    path.touch()

    with pytest.raises(DatasetError, match=r"\.dat or \.vtm"):
        load_simulation(path)


@pytest.mark.parametrize("structured", [True, False])
def test_load_simulation_reads_single_vtm_and_preserves_geometry_type(
    tmp_path: Path, structured: bool
) -> None:
    source = _write_single_vtm(tmp_path, structured=structured)

    grid = load_simulation(source)

    assert isinstance(grid, pv.StructuredGrid if structured else pv.UnstructuredGrid)
    np.testing.assert_allclose(grid.points, EXPECTED_POINTS)
    np.testing.assert_allclose(grid["B [nT]"], EXPECTED_B)
    np.testing.assert_allclose(grid["U [km/s]"], EXPECTED_U)
    assert np.asarray(grid.field_data[TIME_EVENT_KEY]).item() == EXPECTED_TIME_EVENT


def test_load_simulation_rejects_vtm_without_time_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.vtm"
    source.touch()
    loaded = pv.MultiBlock([_cleaned_leaf(structured=True)])
    monkeypatch.setattr(pv, "read", lambda _path: loaded)

    with pytest.raises(DatasetError, match="time_event"):
        load_simulation(source)


def test_load_simulation_wraps_pyvista_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(_path: Path) -> pv.MultiBlock:
        raise RuntimeError("reader failed")

    monkeypatch.setattr(pv, "read", fail)

    with pytest.raises(DatasetError, match="Could not read.*sample.dat"):
        load_simulation(_sample_path(tmp_path))


def test_load_simulation_rejects_dat_with_no_nonempty_zones(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([]))

    with pytest.raises(DatasetError, match="nonempty"):
        load_simulation(_sample_path(tmp_path))


def test_load_simulation_returns_multiblock_for_multiple_dat_zones(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _raw_grid(cleaned=True)
    second = _raw_grid(cleaned=True)
    loaded = pv.MultiBlock()
    loaded["zone-a"] = first
    loaded["zone-b"] = second
    monkeypatch.setattr(pv, "read", lambda _path: loaded)

    result = load_simulation(_sample_path(tmp_path))

    assert result is loaded
    assert isinstance(result, pv.MultiBlock)
    assert result.n_blocks == 2
    assert result.get_block_name(0) == "zone-a"
    assert result.get_block_name(1) == "zone-b"
    for block in result:
        np.testing.assert_allclose(block["B [nT]"], EXPECTED_B)
        assert np.asarray(block.field_data[TIME_EVENT_KEY]).item() == EXPECTED_TIME_EVENT


def _multizone_vtm_root() -> pv.MultiBlock:
    root = pv.MultiBlock()
    root["zone-a"] = _cleaned_leaf(structured=True)
    root["empty"] = pv.PolyData()
    nested = pv.MultiBlock()
    nested["zone-b"] = _cleaned_leaf(structured=False)
    root["nested"] = nested
    root.field_data[TIME_EVENT_KEY] = EXPECTED_TIME_EVENT
    return root


def test_load_simulation_preserves_nested_vtm_multiblock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.vtm"
    source.touch()
    loaded = _multizone_vtm_root()
    monkeypatch.setattr(pv, "read", lambda _path: loaded)

    result = load_simulation(source)

    assert result is loaded
    assert result.get_block_name(0) == "zone-a"
    assert result.get_block_name(1) == "empty"
    assert result.get_block_name(2) == "nested"
    assert isinstance(result[2], pv.MultiBlock)
    assert result[2].get_block_name(0) == "zone-b"
    assert result[1].n_points == 0
    np.testing.assert_allclose(result[0]["B [nT]"], EXPECTED_B)
    np.testing.assert_allclose(result[2][0]["U [km/s]"], EXPECTED_U)


def test_load_simulation_rejects_unsupported_vtm_leaf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "sample.vtm"
    source.touch()
    loaded = pv.MultiBlock()
    loaded["table"] = pv.Table()
    loaded.field_data[TIME_EVENT_KEY] = EXPECTED_TIME_EVENT
    monkeypatch.setattr(pv, "read", lambda _path: loaded)

    with pytest.raises(DatasetError, match="Unsupported non-dataset block"):
        load_simulation(source)


def test_load_simulation_reports_missing_component(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    del raw.point_data["B_z [nT]"]
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    with pytest.raises(DatasetError, match=r"B_z.*nT"):
        load_simulation(_sample_path(tmp_path))


def test_load_simulation_rejects_nonfinite_coordinates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = _raw_grid()
    raw.point_data["X [R]"][0] = np.nan
    monkeypatch.setattr(pv, "read", lambda _path: pv.MultiBlock([raw]))

    with pytest.raises(DatasetError, match="finite"):
        load_simulation(_sample_path(tmp_path))


@pytest.mark.parametrize(
    ("header", "message"),
    [
        ('TITLE="BATSRUS: 3D Data"\nZONE T="3D"\n', "does not contain"),
        (
            'TITLE="BATSRUS: 3D Data,2023/13/16 11:30:00.000"\n',
            "Invalid DAT event timestamp",
        ),
    ],
)
def test_load_simulation_rejects_missing_or_invalid_dat_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    header: str,
    message: str,
) -> None:
    def unexpected_read(_path: Path) -> pv.MultiBlock:
        pytest.fail("PyVista must not run for an invalid DAT header")

    monkeypatch.setattr(pv, "read", unexpected_read)

    with pytest.raises(DatasetError, match=message):
        load_simulation(_sample_path(tmp_path, header=header))
