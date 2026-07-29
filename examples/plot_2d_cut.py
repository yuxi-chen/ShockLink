"""Plot a planar pressure cut from a BATSRUS Tecplot file."""

from __future__ import annotations

import argparse
from pathlib import Path

import pyvista as pv

from shocklink.tecplot import get_2d_cut, plot_2d_cut, read_tecplot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("data/3d.dat"),
        help="BATSRUS Tecplot ASCII file (default: data/3d.dat)",
    )
    parser.add_argument(
        "--normal",
        choices=("x", "y", "z"),
        default="z",
        help="cut-plane normal axis (default: z)",
    )
    parser.add_argument(
        "--origin",
        nargs=3,
        type=float,
        metavar=("X", "Y", "Z"),
        default=(0.0, 0.0, 0.0),
        help="point on the cut plane (default: 0 0 0)",
    )
    parser.add_argument(
        "--scalars",
        default="p",
        help="array used to color the cut (default: p, resolving to P [nPa])",
    )
    parser.add_argument(
        "--xrange",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="limit the displayed world X range",
    )
    parser.add_argument(
        "--yrange",
        nargs=2,
        type=float,
        metavar=("MIN", "MAX"),
        help="limit the displayed world Y range",
    )
    parser.add_argument(
        "--screenshot",
        type=Path,
        help="write a PNG instead of opening an interactive window",
    )
    args = parser.parse_args()

    grid = read_tecplot(args.path)
    cut = get_2d_cut(grid, normal=args.normal, origin=args.origin)

    if args.screenshot is None:
        plot_2d_cut(
            cut,
            scalars=args.scalars,
            xrange=args.xrange,
            yrange=args.yrange,
        )
        return

    plotter = pv.Plotter(off_screen=True)
    plot_2d_cut(
        cut,
        scalars=args.scalars,
        xrange=args.xrange,
        yrange=args.yrange,
        plotter=plotter,
        show=False,
    )
    plotter.show(screenshot=str(args.screenshot))
    print(f"wrote: {args.screenshot}")


if __name__ == "__main__":
    main()
