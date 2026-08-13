#!/usr/bin/env python
"""Clean Tecplot variable names in one or more ASCII DAT files in place."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src"
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from shocklink.clean_dat import clean_dat


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  clean_dat.py input.dat
  clean_dat.py first.dat second.dat""",
    )
    parser.add_argument(
        "inputs",
        type=Path,
        nargs="+",
        help="Tecplot ASCII .dat files to modify in place",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Clean command-line inputs and return a process status."""

    args = _parser().parse_args(argv)
    for source in args.inputs:
        try:
            clean_dat(source)
        except Exception as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        print(f"cleaned {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
