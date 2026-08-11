#!/usr/bin/env python
"""Clean Tecplot variable names in one or more ASCII DAT files in place."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Sequence


def clean_dat(datPath):
    # Clean BATSRUS *.dat file
    # 1) If 'VARIABLES'contain '[' or ']', Paraview will fail.
    # So, remove these characters from *.dat file
    # 2) It seems Paraview assumes the name of the coordinate is 'x', 'y', 'z',
    #  and it can not contain other non-empty characters.
    # For example. 'X AU' will fail.

    f = open(datPath, "r+")
    # Assume 'VARIABLES' is in the first 10 lines
    for i in range(10):
        p0 = f.tell()
        line = f.readline()
        if line.find("VARIABLES") != -1:
            p1 = f.tell()
            break
    # Remove the unit.
    lineNew = re.sub(r"\s*?\[(.*?)\]", r"", line)

    # Example: "X AU" -> "X"
    lineNew = re.sub(r'"([xyzXYZ])(\s+?)(\w*?)"', r'''"\1"''', lineNew)

    # Remove '\n'
    lineNew = re.sub(r"\n", r"", lineNew)
    # Padding space so that lineNew's length is the same as line's
    lineNew += (len(line) - len(lineNew) - 1) * " " + "\n"

    f.seek(p0)
    f.write(lineNew)
    f.close()

    return line


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
