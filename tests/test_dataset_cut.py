import numpy as np
import pyvista as pv
import pytest

from shocklink.exceptions import DatasetError
from shocklink.dataset import get_2d_cut


def _volume() -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(3, 3, 3),
        spacing=(1.0, 1.0, 1.0),
        origin=(-1.0, -1.0, -1.0),
    )
    points = grid.points
    grid.point_data["P [nPa]"] = points[:, 0] + points[:, 1] + points[:, 2]
    grid.point_data["B [nT]"] = np.column_stack(
        (points[:, 0], points[:, 1], points[:, 2])
    )
    grid.point_data["U [km/s]"] = np.column_stack(
        (2.0 * points[:, 0], 2.0 * points[:, 1], 2.0 * points[:, 2])
    )
    return grid


def test_get_2d_cut_defaults_to_equatorial_plane() -> None:
    cut = get_2d_cut(_volume())

    assert isinstance(cut, pv.PolyData)
    assert cut.n_points > 0
    np.testing.assert_allclose(cut.points[:, 2], 0.0)
    np.testing.assert_allclose(
        np.asarray(cut.field_data["shocklink_cut_normal"]).reshape(-1),
        [0.0, 0.0, 1.0],
    )
    np.testing.assert_allclose(
        np.asarray(cut.field_data["shocklink_cut_origin"]).reshape(-1),
        [0.0, 0.0, 0.0],
    )
    assert {"P [nPa]", "B [nT]", "U [km/s]"} <= set(cut.point_data)


@pytest.mark.parametrize(
    ("normal", "component"),
    [
        ("x", 0),
        ("Y", 1),
        ("z", 2),
    ],
)
def test_get_2d_cut_accepts_axis_aliases(
    normal: str, component: int
) -> None:
    cut = get_2d_cut(_volume(), normal=normal)

    np.testing.assert_allclose(cut.points[:, component], 0.0)


def test_get_2d_cut_accepts_arbitrary_plane() -> None:
    normal = np.array([1.0, 1.0, 0.0])
    origin = np.array([0.5, 0.0, 0.0])

    cut = get_2d_cut(_volume(), normal=normal, origin=origin)

    normalized = normal / np.linalg.norm(normal)
    distances = (cut.points - origin) @ normalized
    np.testing.assert_allclose(distances, 0.0, atol=1e-12)
    np.testing.assert_allclose(
        np.asarray(cut.field_data["shocklink_cut_normal"]).reshape(-1),
        normalized,
    )


def test_get_2d_cut_can_generate_triangles() -> None:
    cut = get_2d_cut(_volume(), generate_triangles=True)

    assert cut.is_all_triangles


@pytest.mark.parametrize(
    "normal",
    [
        "longitude",
        (0.0, 0.0, 0.0),
        (1.0, 2.0),
        (1.0, np.nan, 0.0),
    ],
)
def test_get_2d_cut_rejects_invalid_normal(
    normal: str | tuple[float, ...],
) -> None:
    with pytest.raises(DatasetError, match="normal"):
        get_2d_cut(_volume(), normal=normal)


@pytest.mark.parametrize(
    "origin",
    [
        (0.0, 0.0),
        (0.0, np.inf, 0.0),
    ],
)
def test_get_2d_cut_rejects_invalid_origin(
    origin: tuple[float, ...],
) -> None:
    with pytest.raises(DatasetError, match="origin"):
        get_2d_cut(_volume(), origin=origin)


def test_get_2d_cut_rejects_plane_outside_grid() -> None:
    with pytest.raises(DatasetError, match="does not intersect"):
        get_2d_cut(_volume(), origin=(0.0, 0.0, 10.0))


def test_get_2d_cut_wraps_pyvista_filter_failure() -> None:
    class BrokenGrid:
        def slice(self, **_kwargs: object) -> pv.PolyData:
            raise RuntimeError("filter failed")

    with pytest.raises(DatasetError, match="Could not create 2D cut"):
        get_2d_cut(BrokenGrid())  # type: ignore[arg-type]
