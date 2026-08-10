"""Convert a Tecplot ASCII DAT file to a VTK multiblock VTM file."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

import pyvista as pv


class ConversionError(RuntimeError):
    """Raised when a DAT-to-VTM conversion cannot be completed."""


def _paths(
    input_path: str | Path,
    output_path: str | Path | None,
) -> tuple[Path, Path]:
    source = Path(input_path)
    if not source.is_file():
        raise ConversionError(f"input file does not exist: {source}")
    if source.suffix.lower() != ".dat":
        raise ConversionError(f"input file must use the .dat suffix: {source}")

    destination = (
        Path(output_path)
        if output_path is not None
        else source.with_suffix(".vtm")
    )
    if destination.suffix.lower() != ".vtm":
        raise ConversionError(f"output file must use the .vtm suffix: {destination}")
    if source.resolve() == destination.resolve():
        raise ConversionError("input and output paths must be different")
    return source, destination


def convert(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    delete_input: bool = False,
) -> pv.MultiBlock:
    """Convert all Tecplot zones in *input_path* to a VTM multiblock file.

    The dataset returned by PyVista is passed directly to ``save``. No zones,
    coordinates, arrays, or metadata are normalized or otherwise modified.
    """

    source, destination = _paths(input_path, output_path)
    try:
        dataset = pv.read(source)
    except Exception as error:
        raise ConversionError(f"could not read {source}: {error}") from error

    if not isinstance(dataset, pv.MultiBlock):
        raise ConversionError(
            "Tecplot reader returned "
            f"{type(dataset).__name__}; expected MultiBlock"
        )

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        dataset.save(destination)
    except Exception as error:
        raise ConversionError(f"could not write {destination}: {error}") from error

    if delete_input:
        try:
            source.unlink()
        except OSError as error:
            raise ConversionError(
                f"conversion succeeded, but could not delete {source}: {error}"
            ) from error

    return dataset


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Tecplot ASCII .dat file")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        help="VTM output path (default: input path with a .vtm suffix)",
    )
    parser.add_argument(
        "--delete-input",
        action="store_true",
        help="delete the input .dat file after a successful conversion",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line converter and return its process status."""

    args = _parser().parse_args(argv)
    try:
        dataset = convert(args.input, args.output, delete_input=args.delete_input)
    except ConversionError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    output = args.output or args.input.with_suffix(".vtm")
    print(f"wrote {output} ({dataset.n_blocks} blocks)")
    if args.delete_input:
        print(f"deleted {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
