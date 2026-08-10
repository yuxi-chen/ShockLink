from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPOSITORY_ROOT / "tools" / "clean_dat.py"


_SPEC = importlib.util.spec_from_file_location("clean_dat", TOOL)
assert _SPEC is not None and _SPEC.loader is not None
cleaner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cleaner)


def _write_unit_bearing_dat(path: Path) -> Path:
    path.write_bytes(
        b'TITLE="BATSRUS: 3D Data,2023/12/16 11:30:00.000"\n'
        b'VARIABLES ="X [R]", "Y [R]", "Z [R]", "Rho [amu/cm^3]", '
        b'"U_x [km/s]"\n'
        b'ZONE T="zone-a", I=2, J=1, K=1, DATAPACKING=POINT\n'
        b"0 0 0 1 2\n"
        b"1 0 0 3 4\n"
    )
    return path


def test_clean_dat_rewrites_only_variables_line_in_place(tmp_path: Path) -> None:
    source = _write_unit_bearing_dat(tmp_path / "input.dat")
    original = source.read_bytes()
    original_lines = original.splitlines(keepends=True)

    original_header = cleaner.clean_dat(source)

    cleaned = source.read_bytes()
    cleaned_lines = cleaned.splitlines(keepends=True)
    assert original_header == original_lines[1].decode()
    assert len(cleaned) == len(original)
    assert cleaned_lines[0] == original_lines[0]
    assert cleaned_lines[2:] == original_lines[2:]
    assert cleaned_lines[1].rstrip(b" \r\n") == (
        b'VARIABLES ="X", "Y", "Z", "Rho", "U_x"'
    )


def test_clean_dat_is_idempotent(tmp_path: Path) -> None:
    source = _write_unit_bearing_dat(tmp_path / "input.dat")

    cleaner.clean_dat(source)
    cleaned_once = source.read_bytes()
    cleaner.clean_dat(source)

    assert source.read_bytes() == cleaned_once


def test_clean_dat_executable_supports_help_and_multiple_files(
    tmp_path: Path,
) -> None:
    first = _write_unit_bearing_dat(tmp_path / "first.dat")
    second = _write_unit_bearing_dat(tmp_path / "second.dat")

    assert os.access(TOOL, os.X_OK)
    help_result = subprocess.run(
        [str(TOOL), "-h"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    run_result = subprocess.run(
        [str(TOOL), str(first), str(second)],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "usage:" in help_result.stdout
    assert "examples:" in help_result.stdout
    assert "cleaned" in run_result.stdout
    assert "[" not in first.read_text(encoding="utf-8").splitlines()[1]
    assert "[" not in second.read_text(encoding="utf-8").splitlines()[1]
