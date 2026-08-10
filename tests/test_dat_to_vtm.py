from __future__ import annotations

import subprocess
import importlib.util
import os
from pathlib import Path

import numpy as np
import pyvista as pv
import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPOSITORY_ROOT / "tools" / "convert_dat_to_vtm.py"


_SPEC = importlib.util.spec_from_file_location("convert_dat_to_vtm", TOOL)
assert _SPEC is not None and _SPEC.loader is not None
converter = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(converter)


def _write_two_zone_dat(
    path: Path,
    *,
    title: str = 'TITLE = "BATSRUS: two zones,2023/12/16 11:30:00.000"',
) -> Path:
    path.write_text(
        f'''{title}
VARIABLES = "X [R]" "Y [R]" "Z [R]" "rho [amu/cm^3]"
ZONE T="zone-a", I=2, J=2, K=2, DATAPACKING=POINT
0 0 0 1
1 0 0 2
0 1 0 3
1 1 0 4
0 0 1 5
1 0 1 6
0 1 1 7
1 1 1 8
ZONE T="zone-b", I=2, J=2, K=2, DATAPACKING=POINT
2 0 0 11
3 0 0 12
2 1 0 13
3 1 0 14
2 0 1 15
3 0 1 16
2 1 1 17
3 1 1 18
''',
        encoding="utf-8",
    )
    return path


def _run_converter(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(TOOL), *args],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_converter_is_executable_and_help_shows_examples() -> None:
    assert os.access(TOOL, os.X_OK)
    assert TOOL.read_bytes().splitlines()[0] == b"#!/usr/bin/env python"

    result = _run_converter("-h")

    assert "usage:" in result.stdout
    assert "--delete-input" in result.stdout
    assert "output directory" in result.stdout
    assert "cleaned in place" in result.stdout
    assert "examples:" in result.stdout
    assert "convert_dat_to_vtm.py input.dat\n" in result.stdout
    assert "convert_dat_to_vtm.py input.dat custom_vtk" in result.stdout
    assert "convert_dat_to_vtm.py input.dat --delete-input" in result.stdout


def test_converter_preserves_all_zones_and_uses_default_output(
    tmp_path: Path,
) -> None:
    source = _write_two_zone_dat(tmp_path / "sample.dat")
    original_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)

    result = _run_converter(str(source))

    container = tmp_path / "sample_vtk"
    output = container / "sample.vtm"
    assert output.is_file()
    assert (container / "sample").is_dir()
    assert {path.name for path in container.iterdir()} == {"sample.vtm", "sample"}
    assert "2 blocks" in result.stdout
    reloaded = pv.read(output)
    assert isinstance(reloaded, pv.MultiBlock)
    assert reloaded.n_blocks == 2
    assert reloaded.field_data["time_event"].item() == (
        "2023-12-16T11:30:00.000+00:00"
    )
    assert reloaded.get_block_name(0) == "zone-a"
    assert reloaded.get_block_name(1) == "zone-b"
    first, second = reloaded
    assert isinstance(first, pv.StructuredGrid)
    assert isinstance(second, pv.StructuredGrid)
    np.testing.assert_allclose(first.points[:, 0], [0, 1, 0, 1, 0, 1, 0, 1])
    np.testing.assert_allclose(first["rho"], [1, 2, 3, 4, 5, 6, 7, 8])
    np.testing.assert_allclose(second.points[:, 0], [2, 3, 2, 3, 2, 3, 2, 3])
    np.testing.assert_allclose(second["rho"], [11, 12, 13, 14, 15, 16, 17, 18])
    assert source.is_file()
    cleaned_lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    assert cleaned_lines[0] == original_lines[0]
    assert cleaned_lines[2:] == original_lines[2:]
    assert cleaned_lines[1].rstrip() == 'VARIABLES = "X" "Y" "Z" "rho"'


def test_converter_accepts_explicit_output_directory(tmp_path: Path) -> None:
    source = _write_two_zone_dat(tmp_path / "input.dat")
    container = tmp_path / "custom_vtk"

    _run_converter(str(source), str(container))

    output = container / "input.vtm"
    assert output.is_file()
    assert isinstance(pv.read(output), pv.MultiBlock)


def test_converter_deletes_input_only_when_requested(tmp_path: Path) -> None:
    source = _write_two_zone_dat(tmp_path / "input.dat")

    _run_converter(str(source), "--delete-input")

    assert (tmp_path / "input_vtk" / "input.vtm").is_file()
    assert not source.exists()


def test_converter_rejects_invalid_paths_without_deleting_input(
    tmp_path: Path,
) -> None:
    source = _write_two_zone_dat(tmp_path / "input.dat")
    wrong_input = tmp_path / "input.txt"
    wrong_input.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(converter.ConversionError, match=r"\.dat"):
        converter.convert(wrong_input, delete_input=True)
    output_file = tmp_path / "not-a-directory"
    output_file.write_text("occupied", encoding="utf-8")
    with pytest.raises(converter.ConversionError, match="directory"):
        converter._paths(source, output_file)

    assert source.exists()


def test_converter_retains_input_when_read_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = _write_two_zone_dat(tmp_path / "input.dat")

    def fail_read(_path: Path) -> pv.MultiBlock:
        raise RuntimeError("reader failed")

    monkeypatch.setattr(converter.pv, "read", fail_read)

    with pytest.raises(converter.ConversionError, match="could not read"):
        converter.convert(source, delete_input=True)

    assert source.exists()
    assert source.read_text(encoding="utf-8").splitlines()[1].rstrip() == (
        'VARIABLES = "X" "Y" "Z" "rho"'
    )
    assert not (tmp_path / "input_vtk").exists()


def test_converter_retains_input_when_write_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = _write_two_zone_dat(tmp_path / "input.dat")
    dataset = pv.MultiBlock([pv.PolyData()])
    monkeypatch.setattr(converter.pv, "read", lambda _path: dataset)

    def fail_save(_self, _path: Path) -> None:
        raise RuntimeError("writer failed")

    monkeypatch.setattr(pv.MultiBlock, "save", fail_save)

    with pytest.raises(converter.ConversionError, match="could not write"):
        converter.convert(source, delete_input=True)

    assert source.exists()


def test_converter_requires_multiblock_reader_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = _write_two_zone_dat(tmp_path / "input.dat")
    monkeypatch.setattr(converter.pv, "read", lambda _path: pv.PolyData())

    with pytest.raises(converter.ConversionError, match="expected MultiBlock"):
        converter.convert(source)


@pytest.mark.parametrize(
    ("title", "message"),
    [
        ('TITLE = "BATSRUS: two zones"', "timestamp"),
        (
            'TITLE = "BATSRUS: two zones,2023/13/16 11:30:00.000"',
            "timestamp",
        ),
    ],
)
def test_converter_requires_valid_simulation_time(
    tmp_path: Path,
    title: str,
    message: str,
) -> None:
    source = _write_two_zone_dat(tmp_path / "input.dat", title=title)

    with pytest.raises(converter.ConversionError, match=message):
        converter.convert(source)

    assert not (tmp_path / "input_vtk").exists()
