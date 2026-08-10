import os
from pathlib import Path

import numpy as np
import pytest
import pyvista as pv

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.connectivity import analyze_shock_connection
from shocklink.dataset import (
    calc_velocity_divergence,
    get_2d_cut,
    plot_2d_cut,
)
from shocklink.exceptions import DatasetError
from shocklink.io import TIME_EVENT_KEY, load_simulation

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SAMPLE = Path(
    os.environ.get(
        "SHOCKLINK_TECPLOT_SAMPLE",
        REPOSITORY_ROOT / "data/3d.dat",
    )
)
RUN_LARGE_TESTS = os.environ.get("SHOCKLINK_RUN_LARGE_DATA_TESTS") == "1"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not RUN_LARGE_TESTS or not SAMPLE.is_file(),
        reason=(
            "set SHOCKLINK_RUN_LARGE_DATA_TESTS=1 and provide data/3d.dat "
            "or SHOCKLINK_TECPLOT_SAMPLE"
        ),
    ),
]


def test_real_batsrus_sample_has_geometry_and_vector_fields() -> None:
    grid = load_simulation(SAMPLE)

    assert grid.n_points == 5_695_488
    assert grid.n_cells == 5_809_895
    assert grid.bounds == pytest.approx((-220.0, 31.5, -126.0, 126.0, -126.0, 126.0))
    assert grid["B [nT]"].shape == (grid.n_points, 3)
    assert grid["U [km/s]"].shape == (grid.n_points, 3)
    assert (
        np.asarray(grid.field_data[TIME_EVENT_KEY]).item()
        == "2023-12-16T11:30:00.000+00:00"
    )
    np.testing.assert_allclose(grid["B [nT]"][:10, 0], grid["B_x [nT]"][:10])
    np.testing.assert_allclose(
        grid["U [km/s]"][:10, 2],
        grid["U_z [km_s]"][:10],
    )


def test_real_batsrus_sample_supports_equatorial_pressure_plot() -> None:
    grid = load_simulation(SAMPLE)

    with pytest.raises(DatasetError, match="PolyData"):
        plot_2d_cut(grid, show=False)  # type: ignore[arg-type]

    cut = get_2d_cut(grid)

    assert cut.n_points > 0
    assert cut.n_cells > 0
    np.testing.assert_allclose(cut.points[:, 2], 0.0, atol=1e-6)
    assert {"P [nPa]", "B [nT]", "U [km/s]"} <= set(cut.point_data)

    plotter = pv.Plotter(off_screen=True)
    try:
        assert plot_2d_cut(cut, plotter=plotter, show=False) is plotter
    finally:
        plotter.close()


def test_real_batsrus_sample_extracts_bow_shock_surface_array() -> None:
    grid = load_simulation(SAMPLE)
    calc_velocity_divergence(grid)
    fit = fit_bow_shock(grid)
    region = extract_shockfit_range(
        grid,
        lower=3.0 - fit.loc0[0],
        upper=fit.loc0[0] + 5.0,
    )
    y = np.linspace(-5.0, 5.0, 5)
    z = np.linspace(-5.0, 5.0, 5)

    surface = get_bow_shock_surface(
        region,
        y=y,
        z=z,
        x_resolution=161,
        chunk_size=5,
    )

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert normals.shape == surface.shape + (3,)
    assert np.isfinite(normals).all()
    np.testing.assert_allclose(np.linalg.norm(normals, axis=-1), 1.0)
    assert np.all(normals[..., 0] > 0.0)
    assert surface.shape == (len(y), len(z))
    assert np.isfinite(surface).any()
    finite = surface[np.isfinite(surface)]
    assert finite.min() >= region.bounds.x_min
    assert finite.max() <= region.bounds.x_max

    connection = analyze_shock_connection(
        surface,
        normals,
        y=y,
        z=z,
        mms_position=(0.0, 0.0, 0.0),
        bavg=(1.0, 0.0, 0.0),
    )

    assert len(connection.intersections) >= 1
    assert np.isfinite(connection.selected_intersection.point).all()
    assert connection.selected_intersection.distance > 0.0
    assert 0.0 <= connection.selected_intersection.theta_bn_deg <= 90.0
    assert connection.surface_mesh.n_cells > 0
