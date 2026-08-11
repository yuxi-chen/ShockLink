#!/usr/bin/env python
"""Build an MMS bow-shock connection and save 2D/3D plots."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from shocklink.mms_connection import (
    build_mms_bow_shock_connection,
    save_mms_bow_shock_connection_plots,
)


def _parser() -> argparse.ArgumentParser:
    """Create the command-line interface for the reusable workflow API."""

    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  mms_bow_shock_connection.py data/3d.dat --param-file results/PARAM.in
  mms_bow_shock_connection.py data/3d.dat --output-directory results
  mms_bow_shock_connection.py data/3d.dat --three-d-output both
  mms_bow_shock_connection.py data/3d.dat --param-file PARAM.in --three-d-output both""",
    )
    parser.add_argument("path", type=Path, help="simulation DAT file or VTM directory")
    parser.add_argument(
        "--param-file",
        type=Path,
        required=True,
        help="PARAM.in file created by create_swmf_input.py",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("."),
        help="directory for saved plots (default: current directory)",
    )
    parser.add_argument(
        "--output-prefix",
        help="prefix for output filenames (default: input stem plus _shock_connection)",
    )
    parser.add_argument(
        "--three-d-output",
        choices=("png", "html", "both"),
        default="png",
        help="3D output format (default: png; html requires Trame)",
    )
    parser.add_argument(
        "--dpi", type=int, default=600, help="PNG resolution in dots per inch (default: 600)"
    )
    parser.add_argument("--x-resolution", type=int, default=512)
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--smoothing-sigma", type=float, default=5.0)
    parser.add_argument(
        "--shockfit-range",
        nargs=2,
        type=float,
        default=(-5.0, 5.0),
        metavar=("LOWER", "UPPER"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the connection workflow and return its process status.

    Parameters
    ----------
    argv
        Optional command-line arguments excluding the executable name. Omit to
        parse the process command line.

    Returns
    -------
    int
        Zero after all requested plots are written; one after a workflow or
        export error has been reported on standard error.
    """

    args = _parser().parse_args(argv)
    try:
        result = build_mms_bow_shock_connection(
            args.path,
            param_file=args.param_file,
            x_resolution=args.x_resolution,
            chunk_size=args.chunk_size,
            smoothing_sigma=args.smoothing_sigma,
            shockfit_range=tuple(args.shockfit_range),
        )
        paths = save_mms_bow_shock_connection_plots(
            result,
            args.output_directory,
            output_prefix=args.output_prefix,
            three_d_output=args.three_d_output,
            dpi=args.dpi,
        )
    except Exception as error:
        print(f"Could not build MMS bow-shock connection: {error}", file=sys.stderr)
        return 1

    hit = result.connection.selected_intersection
    print(f"Simulation time: {result.simulation_time}")
    print(f"MMS PARAM time: {result.mms_time} (GSM)")
    print(f"Bavg [nT]: {result.bavg}")
    print(f"Intersection [R_E]: {hit.point}")
    print(f"Distance from MMS: {hit.distance:.6g} R_E")
    print(f"theta_Bn: {hit.theta_bn_deg:.3f} deg")
    print(f"Wrote 2D plot: {paths.two_d}")
    if paths.three_d_png is not None:
        print(f"Wrote 3D PNG: {paths.three_d_png}")
    if paths.three_d_html is not None:
        print(f"Wrote 3D HTML: {paths.three_d_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
