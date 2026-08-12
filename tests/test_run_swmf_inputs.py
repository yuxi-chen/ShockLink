from __future__ import annotations

import os
from pathlib import Path
import runpy

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/run_swmf_inputs.py"


def _write_executable(path: Path, source: str) -> None:
    path.write_text(source)
    path.chmod(0o755)


def test_runs_param_files_sequentially_in_sorted_order(
    tmp_path: Path, monkeypatch
) -> None:
    input_directory = tmp_path / "inputs"
    input_directory.mkdir()
    (input_directory / "PARAM_20200102_000000_20200102_010000.in").write_text("second")
    (input_directory / "PARAM_20200101_000000_20200101_010000.in").write_text("first")

    run_directory = tmp_path / "run"
    run_directory.mkdir()
    result_directory = run_directory / "res"
    (result_directory / "run001_previous").mkdir(parents=True)
    (result_directory / "run005_previous").mkdir()
    (result_directory / "run900").mkdir()
    (result_directory / "run777_file").write_text("not a result directory")
    order_path = run_directory / "order.txt"
    _write_executable(
        run_directory / "SWMF.exe",
        "#!/bin/sh\n"
        f'printf "swmf:%s\\n" "$(cat PARAM.in)" >> "{order_path}"\n'
        'printf "runlog:%s\\n" "$(cat PARAM.in)"\n',
    )
    _write_executable(
        run_directory / "PostProc.pl",
        "#!/bin/sh\n"
        f'printf "post:%s:%s\\n" "$(cat PARAM.in)" "$1" >> "{order_path}"\n'
        'mkdir -p "$1"\n'
        'cp runlog "$1/runlog"\n',
    )

    binary_directory = tmp_path / "bin"
    binary_directory.mkdir()
    _write_executable(binary_directory / "mpiexec", '#!/bin/sh\nexec "$@"\n')
    monkeypatch.setenv(
        "PATH", f"{binary_directory}{os.pathsep}{os.environ.get('PATH', '')}"
    )

    namespace = runpy.run_path(str(SCRIPT))
    results = namespace["run_param_files"](input_directory, run_directory=run_directory)

    assert order_path.read_text().splitlines() == [
        "swmf:first",
        "post:first:res/run006_20200101_000000_20200101_010000",
        "swmf:second",
        "post:second:res/run007_20200102_000000_20200102_010000",
    ]
    assert results == [
        run_directory / "res/run006_20200101_000000_20200101_010000",
        run_directory / "res/run007_20200102_000000_20200102_010000",
    ]
    assert (results[0] / "runlog").read_text() == "runlog:first\n"
    assert (results[1] / "runlog").read_text() == "runlog:second\n"
    assert (run_directory / "PARAM.in").read_text() == "second"


def test_stops_batch_when_swmf_fails(tmp_path: Path, monkeypatch) -> None:
    input_directory = tmp_path / "inputs"
    input_directory.mkdir()
    first_name = "PARAM_20200101_000000_20200101_010000.in"
    (input_directory / first_name).write_text("first")
    (input_directory / "PARAM_20200102_000000_20200102_010000.in").write_text("second")

    run_directory = tmp_path / "run"
    run_directory.mkdir()
    _write_executable(
        run_directory / "SWMF.exe",
        '#!/bin/sh\nprintf "simulation failed\\n" >&2\nexit 7\n',
    )
    postprocess_marker = run_directory / "postprocessed"
    _write_executable(
        run_directory / "PostProc.pl",
        f'#!/bin/sh\ntouch "{postprocess_marker}"\n',
    )
    binary_directory = tmp_path / "bin"
    binary_directory.mkdir()
    _write_executable(binary_directory / "mpiexec", '#!/bin/sh\nexec "$@"\n')
    monkeypatch.setenv(
        "PATH", f"{binary_directory}{os.pathsep}{os.environ.get('PATH', '')}"
    )

    namespace = runpy.run_path(str(SCRIPT))
    with pytest.raises(RuntimeError, match=first_name):
        namespace["run_param_files"](input_directory, run_directory=run_directory)

    assert not postprocess_marker.exists()
    assert (run_directory / "PARAM.in").read_text() == "first"
    assert (run_directory / "runlog").read_text() == "simulation failed\n"


def test_stops_batch_when_postprocessing_fails(tmp_path: Path, monkeypatch) -> None:
    input_directory = tmp_path / "inputs"
    input_directory.mkdir()
    first_name = "PARAM_20200101_000000_20200101_010000.in"
    (input_directory / first_name).write_text("first")
    (input_directory / "PARAM_20200102_000000_20200102_010000.in").write_text("second")

    run_directory = tmp_path / "run"
    run_directory.mkdir()
    swmf_runs = run_directory / "swmf_runs"
    _write_executable(
        run_directory / "SWMF.exe",
        "#!/bin/sh\n"
        f'cat PARAM.in >> "{swmf_runs}"\n'
        'printf "runlog:%s\\n" "$(cat PARAM.in)"\n',
    )
    _write_executable(run_directory / "PostProc.pl", "#!/bin/sh\nexit 9\n")
    binary_directory = tmp_path / "bin"
    binary_directory.mkdir()
    _write_executable(binary_directory / "mpiexec", '#!/bin/sh\nexec "$@"\n')
    monkeypatch.setenv(
        "PATH", f"{binary_directory}{os.pathsep}{os.environ.get('PATH', '')}"
    )

    namespace = runpy.run_path(str(SCRIPT))
    with pytest.raises(RuntimeError, match=first_name):
        namespace["run_param_files"](input_directory, run_directory=run_directory)

    assert swmf_runs.read_text() == "first"
    assert (run_directory / "PARAM.in").read_text() == "first"
    assert (run_directory / "runlog").read_text() == "runlog:first\n"
