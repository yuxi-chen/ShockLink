from __future__ import annotations

import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/process_swmf_results.py"


def test_processes_latest_simulation_and_skips_incomplete_runs(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    results = tmp_path / "res"
    first = results / "run001_first"
    (first / "zz_nested").mkdir(parents=True)
    (first / "PARAM.in").write_text("param")
    (first / "z_latest.vtm").write_text("latest")
    (first / "zz_nested/a_older.dat").write_text("older")

    missing_param = results / "run002_missing_param"
    missing_param.mkdir()
    (missing_param / "output.dat").write_text("simulation")

    missing_simulation = results / "run003_missing_simulation"
    missing_simulation.mkdir()
    (missing_simulation / "PARAM.in").write_text("param")

    failed = results / "run004_failed"
    failed.mkdir()
    (failed / "PARAM.in").write_text("param")
    (failed / "output.dat").write_text("simulation")

    last = results / "run005_last"
    last.mkdir()
    (last / "PARAM.in").write_text("param")
    (last / "output.dat").write_text("simulation")

    calls: list[tuple[Path, Path]] = []
    saved: list[Path] = []
    dependency = ModuleType("shocklink.mms_connection")

    def build(path: Path, *, param_file: Path):
        calls.append((path, param_file))
        if path.parent == failed:
            raise RuntimeError("bad simulation")
        return SimpleNamespace(input_stem=path.stem)

    def save(result, output_directory: Path):
        saved.append(output_directory)
        return SimpleNamespace(two_d=output_directory / f"{result.input_stem}_2d.png")

    dependency.build_mms_bow_shock_connection = build  # type: ignore[attr-defined]
    dependency.save_mms_bow_shock_connection_plots = save  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "shocklink.mms_connection", dependency)
    namespace = runpy.run_path(str(SCRIPT))

    processed = namespace["process_results"](results)

    assert calls == [
        (first / "z_latest.vtm", first / "PARAM.in"),
        (failed / "output.dat", failed / "PARAM.in"),
        (last / "output.dat", last / "PARAM.in"),
    ]
    assert saved == [first, last]
    assert processed == [first, last]
    errors = capsys.readouterr().err
    assert "run002_missing_param" in errors
    assert "run003_missing_simulation" in errors
    assert "run004_failed" in errors
    assert "bad simulation" in errors


def test_batch_result_script_is_executable() -> None:
    assert SCRIPT.stat().st_mode & 0o111
