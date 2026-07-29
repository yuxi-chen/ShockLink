import os
from pathlib import Path

import numpy as np
import pytest

from shocklink.tecplot import read_tecplot

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
    grid = read_tecplot(SAMPLE)

    assert grid.n_points == 5_695_488
    assert grid.n_cells == 5_809_895
    assert grid.bounds == pytest.approx(
        (-220.0, 31.5, -126.0, 126.0, -126.0, 126.0)
    )
    assert grid["B [nT]"].shape == (grid.n_points, 3)
    assert grid["U [km/s]"].shape == (grid.n_points, 3)
    np.testing.assert_allclose(grid["B [nT]"][:10, 0], grid["B_x [nT]"][:10])
    np.testing.assert_allclose(
        grid["U [km/s]"][:10, 2],
        grid["U_z [km_s]"][:10],
    )
