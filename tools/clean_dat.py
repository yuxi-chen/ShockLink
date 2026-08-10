#!/usr/bin/env python
"""Clean Tecplot variable names in one or more ASCII DAT files in place."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Sequence


class CleanDatError(RuntimeError):
    """Raised when a Tecplot DAT header cannot be cleaned."""


_UNIT_PATTERN = re.compile(r"\s*\[(.*?)]")
_COORDINATE_PATTERN = re.compile(r'"([xyzXYZ])\s+\w*"')


def _clean_variables_line(line: str) -> str:
    if line.endswith("\r\n"):
        body, newline = line[:-2], "\r\n"
    elif line.endswith("\n") or line.endswith("\r"):
        body, newline = line[:-1], line[-1]
    else:
        body, newline = line, ""

    cleaned = _UNIT_PATTERN.sub("", body)
    cleaned = _COORDINATE_PATTERN.sub(r'"\1"', cleaned)
    padding = len(line.encode("utf-8")) - len((cleaned + newline).encode("utf-8"))
    if padding < 0:
        raise CleanDatError("cleaned VARIABLES line is longer than the original")
    return f"{cleaned}{' ' * padding}{newline}"


def clean_dat(dat_path: str | Path) -> str:
    """Clean the ``VARIABLES`` header in *dat_path* without shifting file data.

    Bracketed units are removed from every variable name. Coordinate names such
    as ``X R`` are reduced to ``X``. The rewritten line is padded to its
    original byte length and overwritten in place. The original header line is
    returned.
    """

    path = Path(dat_path)
    if not path.is_file():
        raise CleanDatError(f"input file does not exist: {path}")
    if path.suffix.lower() != ".dat":
        raise CleanDatError(f"input file must use the .dat suffix: {path}")

    try:
        with path.open("r+b") as stream:
            while True:
                offset = stream.tell()
                raw_line = stream.readline()
                if not raw_line:
                    break
                try:
                    line = raw_line.decode("utf-8")
                except UnicodeDecodeError as error:
                    raise CleanDatError(
                        f"could not decode Tecplot header in {path}: {error}"
                    ) from error

                stripped = line.lstrip().upper()
                if stripped.startswith("VARIABLES"):
                    cleaned = _clean_variables_line(line).encode("utf-8")
                    if len(cleaned) != len(raw_line):
                        raise CleanDatError(
                            "cleaned VARIABLES line changed the file byte length"
                        )
                    stream.seek(offset)
                    stream.write(cleaned)
                    return line
                if stripped.startswith("ZONE"):
                    break
    except CleanDatError:
        raise
    except OSError as error:
        raise CleanDatError(f"could not clean {path}: {error}") from error

    raise CleanDatError(f"Tecplot header in {path} lacks a VARIABLES declaration")


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
        except CleanDatError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2
        print(f"cleaned {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
