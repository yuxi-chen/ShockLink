#!/usr/bin/env python
"""Create MMS bow-shock connection figures for completed SWMF runs."""

from __future__ import annotations

from pathlib import Path
import sys

from shocklink.mms_connection import (
    build_mms_bow_shock_connection,
    save_mms_bow_shock_connection_plots,
)


# Run this script from the SWMF run directory, or edit this path.
RESULT_DIRECTORY = Path("res")


def _latest_simulation(run_directory: Path) -> Path | None:
    candidates = [
        path
        for pattern in ("*.dat", "*.vtm")
        for path in run_directory.rglob(pattern)
        if path.is_file()
    ]
    return max(
        candidates,
        key=lambda path: (path.name, path.relative_to(run_directory).as_posix()),
        default=None,
    )


def process_results(result_directory: str | Path = RESULT_DIRECTORY) -> list[Path]:
    """Process valid ``runNNN*`` directories and return successful runs."""
    root = Path(result_directory)
    runs = sorted(path for path in root.glob("run[0-9][0-9][0-9]*") if path.is_dir())
    processed: list[Path] = []
    for run in runs:
        param_file = run / "PARAM.in"
        simulation = _latest_simulation(run)
        if not param_file.is_file():
            print(f"Skipping {run}: PARAM.in was not found", file=sys.stderr)
            continue
        if simulation is None:
            print(f"Skipping {run}: no *.dat or *.vtm file was found", file=sys.stderr)
            continue
        try:
            result = build_mms_bow_shock_connection(
                simulation,
                param_file=param_file,
            )
            paths = save_mms_bow_shock_connection_plots(result, run)
        except Exception as error:
            print(f"Skipping {run}: {error}", file=sys.stderr)
            continue
        print(f"Processed {run}: {paths.two_d}")
        processed.append(run)
    return processed


if __name__ == "__main__":
    process_results()
