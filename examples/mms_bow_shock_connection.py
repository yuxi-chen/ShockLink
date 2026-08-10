"""Connect an interval-averaged MMS GSM field to an extracted bow shock."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
    smooth_bow_shock_surface,
)
from shocklink.connectivity import (
    analyze_shock_connection,
    plot_shock_angle_contour,
    plot_shock_connection_3d,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.mms import average_plotted_values, load_mms_data
from shocklink.io import TIME_EVENT_KEY, load_simulation


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="BATSRUS Tecplot ASCII file")
    parser.add_argument("--mms-start", required=True, help="MMS interval start (UTC)")
    parser.add_argument("--mms-end", required=True, help="MMS interval end (UTC)")
    parser.add_argument("--probe", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--mode", choices=("auto", "brst", "fast"), default="auto")
    parser.add_argument("--transverse-limit", type=float, default=40.0)
    parser.add_argument("--surface-resolution", type=int, default=81)
    parser.add_argument("--x-resolution", type=int, default=512)
    parser.add_argument("--chunk-size", type=int, default=1024)
    parser.add_argument("--smoothing-sigma", type=float, default=1.0)
    parser.add_argument(
        "--shockfit-range",
        nargs=2,
        type=float,
        default=(-5.0, 5.0),
        metavar=("LOWER", "UPPER"),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        grid = load_simulation(args.path)
        calc_velocity_divergence(grid)
        fit_bow_shock(grid)
        region = extract_shockfit_range(
            grid, lower=args.shockfit_range[0], upper=args.shockfit_range[1]
        )
        y = np.linspace(
            -args.transverse_limit, args.transverse_limit, args.surface_resolution
        )
        z = np.linspace(
            -args.transverse_limit, args.transverse_limit, args.surface_resolution
        )
        raw = get_bow_shock_surface(
            region,
            y=y,
            z=z,
            x_resolution=args.x_resolution,
            chunk_size=args.chunk_size,
            refine_minimum=True,
        )
        surface_x = smooth_bow_shock_surface(raw, sigma=args.smoothing_sigma)
        normals = calc_bow_shock_normals(surface_x, y=y, z=z)
        mms = load_mms_data(
            args.mms_start,
            args.mms_end,
            probe=args.probe,
            mode=args.mode,
            coordinates="gsm",
        )
        averages = average_plotted_values(mms)
        mms_position = np.array(
            [averages[f"satellite_location_{axis}"] for axis in "xyz"]
        )
        bavg = np.array([averages[f"magnetic_field_{axis}"] for axis in "xyz"])
        connection = analyze_shock_connection(
            surface_x, normals, y=y, z=z, mms_position=mms_position, bavg=bavg
        )
    except Exception as error:
        print(f"Could not build MMS bow-shock connection: {error}", file=sys.stderr)
        return 1

    event = np.asarray(grid.field_data.get(TIME_EVENT_KEY, "unknown")).reshape(-1)[0]
    hit = connection.selected_intersection
    print(f"Tecplot event: {event}")
    print(f"MMS interval: {args.mms_start} to {args.mms_end} (MMS{args.probe}, GSM)")
    print(f"Bavg [nT]: {bavg}")
    print(f"Intersection [R_E]: {hit.point}")
    print(f"Line parameter: {hit.line_parameter:.6g}; distance: {hit.distance:.6g} R_E")
    print(f"theta_Bn: {hit.theta_bn_deg:.3f} deg")
    try:
        figure, _ = plot_shock_angle_contour(connection)
        figure.show()
        plot_shock_connection_3d(connection)
    except Exception as error:
        print(f"Could not plot MMS bow-shock connection: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
