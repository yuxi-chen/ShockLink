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
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""examples:
  mms_bow_shock_connection.py data/3d.dat
  mms_bow_shock_connection.py data/3d.dat --output-directory results
  mms_bow_shock_connection.py data/3d.dat --three-d-output both
  mms_bow_shock_connection.py data/3d.dat --mms-start "2023-12-16 11:29:30" --mms-end "2023-12-16 11:30:30""",
    )
    parser.add_argument("path", type=Path, help="simulation DAT file or VTM directory")
    parser.add_argument(
        "--output-directory",
        type=Path,
        default=Path("."),
        help="directory for saved plots (default: current directory)",
    )
    parser.add_argument(
        "--output-prefix",
        default="shock_connection",
        help="prefix for output filenames (default: shock_connection)",
    )
    parser.add_argument(
        "--three-d-output",
        choices=("png", "html", "both"),
        default="png",
        help="3D output format (default: png; html requires Trame)",
    )
    parser.add_argument(
        "--dpi", type=int, default=300, help="PNG resolution in dots per inch"
    )
    parser.add_argument(
        "--mms-window-seconds",
        type=float,
        default=300.0,
        help="symmetric MMS interval around the simulation event (default: 300)",
    )
    parser.add_argument("--mms-start", help="explicit MMS interval start (UTC)")
    parser.add_argument("--mms-end", help="explicit MMS interval end (UTC)")
    parser.add_argument(
        "--probe", type=int, choices=range(1, 5), default=1, help="MMS probe"
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "brst", "fast"),
        default="auto",
        help="MMS data mode (default: auto)",
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
    """Run the connection workflow and return its process status."""

    args = _parser().parse_args(argv)
    try:
        result = build_mms_bow_shock_connection(
            args.path,
            mms_window_seconds=args.mms_window_seconds,
            mms_start=args.mms_start,
            mms_end=args.mms_end,
            probe=args.probe,
            mode=args.mode,
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
    print(f"MMS interval: {result.mms_start} to {result.mms_end} (MMS{args.probe}, GSM)")
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
