"""Extract a bow-shock surface and outward normals from BATSRUS Tecplot data."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import calc_velocity_divergence
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
    parser.add_argument(
        "--transverse-limit",
        type=float,
        default=40.0,
        help="sample Y and Z from -LIMIT to +LIMIT (default: 40)",
    )
    parser.add_argument(
        "--surface-resolution",
        type=int,
        default=81,
        help="number of Y and Z coordinates (default: 81)",
    )
    parser.add_argument(
        "--x-resolution",
        type=int,
        default=512,
        help="samples along each X column (default: 512)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024,
        help="Y-Z columns sampled per chunk (default: 1024)",
    )
    parser.add_argument(
        "--shockfit-range",
        nargs=2,
        type=float,
        metavar=("LOWER", "UPPER"),
        default=(-5.0, 5.0),
        help="inclusive shockfit residual range (default: -5 5)",
    )
    args = parser.parse_args()

    grid = read_tecplot(args.path)
    calc_velocity_divergence(grid)
    fit = fit_bow_shock(grid)
    shock_region = extract_shockfit_range(
        grid,
        lower=args.shockfit_range[0],
        upper=args.shockfit_range[1],
    )

    y = np.linspace(
        -args.transverse_limit,
        args.transverse_limit,
        args.surface_resolution,
    )
    z = np.linspace(
        -args.transverse_limit,
        args.transverse_limit,
        args.surface_resolution,
    )
    surface_x = get_bow_shock_surface(
        shock_region,
        y=y,
        z=z,
        x_resolution=args.x_resolution,
        chunk_size=args.chunk_size,
    )
    normals = calc_bow_shock_normals(surface_x, y=y, z=z)

    finite_surface = np.isfinite(surface_x)
    unit_error = np.abs(np.linalg.norm(normals, axis=-1) - 1.0)
    print(f"fit_nose_x: {fit.loc0[0]:.6g}")
    print(f"fit_curvature: {fit.curvature:.6g}")
    print(f"surface_shape: {surface_x.shape}")
    print(f"normal_shape: {normals.shape}")
    print(f"finite_surface_values: {np.count_nonzero(finite_surface)}/{surface_x.size}")
    print(f"minimum_normal_x: {normals[..., 0].min():.6g}")
    print(f"maximum_unit_length_error: {unit_error.max():.3e}")


if __name__ == "__main__":
    main()
