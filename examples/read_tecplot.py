"""Read and summarize a BATSRUS Tecplot file with ShockLink."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from shocklink.tecplot import read_tecplot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("data/3d.dat"),
        help="BATSRUS Tecplot ASCII file (default: data/3d.dat)",
    )
    args = parser.parse_args()

    started = time.perf_counter()
    grid = read_tecplot(args.path)
    elapsed = time.perf_counter() - started

    print(grid)
    print(f"source: {args.path}")
    print(f"load_seconds: {elapsed:.3f}")
    print(f"bounds: {tuple(float(value) for value in grid.bounds)}")
    print(f"point_arrays: {list(grid.point_data.keys())}")
    print("vector_arrays: ['B [nT]', 'U [km/s]']")


if __name__ == "__main__":
    main()
