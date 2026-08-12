#!/usr/bin/env python
"""Run and postprocess a directory of SWMF PARAM inputs sequentially."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import shutil
import subprocess
import sys


def _require_executable(path: Path, name: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{name} was not found at {path}")
    if not os.access(path, os.X_OK):
        raise PermissionError(f"{name} is not executable: {path}")


def run_param_files(
    input_directory: str | Path, *, run_directory: str | Path | None = None
) -> list[Path]:
    """Run and postprocess all ``PARAM_*.in`` files in sorted order."""

    inputs = Path(input_directory).expanduser().resolve()
    run = (
        Path.cwd().resolve() if run_directory is None else Path(run_directory).resolve()
    )
    if not inputs.is_dir():
        raise NotADirectoryError(f"PARAM input directory was not found: {inputs}")
    if not run.is_dir():
        raise NotADirectoryError(f"SWMF run directory was not found: {run}")

    _require_executable(run / "SWMF.exe", "SWMF.exe")
    _require_executable(run / "PostProc.pl", "PostProc.pl")
    if shutil.which("mpiexec") is None:
        raise FileNotFoundError("mpiexec was not found on PATH")

    param_files = sorted(path for path in inputs.glob("PARAM_*.in") if path.is_file())
    if not param_files:
        raise ValueError(f"no PARAM_*.in files were found in {inputs}")

    jobs: list[tuple[Path, Path]] = []
    for index, param_file in enumerate(param_files, start=1):
        suffix = param_file.name.removeprefix("PARAM_").removesuffix(".in")
        jobs.append((param_file, Path("res") / f"run{index:03d}_{suffix}"))
    existing_results = [run / result for _, result in jobs if (run / result).exists()]
    if existing_results:
        names = ", ".join(str(path) for path in existing_results)
        raise FileExistsError(f"result destination already exists: {names}")

    (run / "res").mkdir(exist_ok=True)
    results: list[Path] = []
    for index, (param_file, relative_result) in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] Running {param_file.name}")
        shutil.copy2(param_file, run / "PARAM.in")

        try:
            with (run / "runlog").open("w") as runlog:
                subprocess.run(
                    ["mpiexec", "./SWMF.exe"],
                    cwd=run,
                    stdout=runlog,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"SWMF failed for {param_file.name} with exit status "
                f"{error.returncode}; see {run / 'runlog'}"
            ) from error

        print(f"[{index}/{len(jobs)}] Postprocessing to {relative_result}")
        try:
            subprocess.run(
                ["./PostProc.pl", str(relative_result)],
                cwd=run,
                check=True,
            )
        except subprocess.CalledProcessError as error:
            raise RuntimeError(
                f"postprocessing failed for {param_file.name} with exit status "
                f"{error.returncode}"
            ) from error
        results.append(run / relative_result)

    return results


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run each PARAM_*.in file sequentially from the current SWMF run "
            "directory, then postprocess it into res/runNNN_<input-suffix>."
        )
    )
    parser.add_argument("input_directory", help="directory containing PARAM_*.in files")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_param_files(args.input_directory)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
