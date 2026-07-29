import numpy as np
import pyvista as pv
import pytest

from shocklink.dataset import get_x_axis_profile, sample_line
from shocklink.exceptions import DatasetError


def _volume() -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(3, 3, 3),
        spacing=(1.0, 1.0, 1.0),
        origin=(-1.0, -1.0, -1.0),
    )
    x, y, z = grid.points.T
    grid.point_data["f"] = x + 2.0 * y + 3.0 * z
    return grid


def test_sample_line_interpolates_an_arbitrary_profile() -> None:
    profile = sample_line(
        _volume(),
        pointa=(-1.0, -1.0, -1.0),
        pointb=(1.0, 1.0, 1.0),
        resolution=4,
    )

    assert isinstance(profile, pv.PolyData)
    assert profile.n_points == 5
    np.testing.assert_allclose(
        profile.points,
        np.linspace((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), 5),
    )
    np.testing.assert_allclose(profile.point_data["f"], [-6, -3, 0, 3, 6])


def test_get_x_axis_profile_uses_bounds_and_transverse_coordinates() -> None:
    profile = get_x_axis_profile(
        _volume(),
        y=1.0,
        z=-1.0,
        resolution=2,
    )

    np.testing.assert_allclose(
        profile.points,
        [(-1.0, 1.0, -1.0), (0.0, 1.0, -1.0), (1.0, 1.0, -1.0)],
    )
    np.testing.assert_allclose(profile.point_data["f"], [-2, -1, 0])


@pytest.mark.parametrize(
    ("pointa", "pointb", "resolution", "tolerance", "message"),
    [
        ((0.0, 0.0), (1.0, 0.0, 0.0), 1, None, "line start"),
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0, None, "resolution"),
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), True, None, "resolution"),
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1, -1.0, "tolerance"),
        ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1, np.nan, "tolerance"),
    ],
)
def test_sample_line_rejects_invalid_arguments(
    pointa: tuple[float, ...],
    pointb: tuple[float, ...],
    resolution: int,
    tolerance: float | None,
    message: str,
) -> None:
    with pytest.raises(DatasetError, match=message):
        sample_line(
            _volume(),
            pointa=pointa,
            pointb=pointb,
            resolution=resolution,
            tolerance=tolerance,
        )


def test_get_x_axis_profile_rejects_invalid_coordinates_and_bounds() -> None:
    with pytest.raises(DatasetError, match="coordinates"):
        get_x_axis_profile(_volume(), y=np.nan)

    flat_grid = pv.ImageData(dimensions=(1, 3, 3))
    with pytest.raises(DatasetError, match="X bounds"):
        get_x_axis_profile(flat_grid)


def test_sample_line_wraps_filter_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_sampling(
        self: pv.ImageData,
        *_args: object,
        **_kwargs: object,
    ) -> pv.PolyData:
        raise RuntimeError("VTK failed")

    monkeypatch.setattr(pv.ImageData, "sample_over_line", fail_sampling)

    with pytest.raises(DatasetError, match="Could not sample dataset along line"):
        sample_line(
            _volume(),
            pointa=(-1.0, 0.0, 0.0),
            pointb=(1.0, 0.0, 0.0),
        )


def test_sample_line_rejects_invalid_filter_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def empty_profile(
        self: pv.ImageData,
        *_args: object,
        **_kwargs: object,
    ) -> pv.PolyData:
        return pv.PolyData()

    monkeypatch.setattr(pv.ImageData, "sample_over_line", empty_profile)

    with pytest.raises(DatasetError, match="empty profile"):
        sample_line(
            _volume(),
            pointa=(-1.0, 0.0, 0.0),
            pointb=(1.0, 0.0, 0.0),
        )
