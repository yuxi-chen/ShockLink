from typing import Any

import numpy as np
import pyvista as pv
import pytest

from shocklink.exceptions import DatasetError
from shocklink.tecplot import (
    CUT_NORMAL_KEY,
    CUT_ORIGIN_KEY,
    plot_2d_cut,
)


class RecordingPlotter:
    def __init__(self) -> None:
        self.mesh: pv.PolyData | None = None
        self.mesh_kwargs: dict[str, Any] = {}
        self.axes_added = False
        self.view_normal: np.ndarray | None = None
        self.view_up: np.ndarray | None = None
        self.parallel_projection_enabled = False
        self.camera_bounds: tuple[float, ...] | None = None
        self.camera_render: bool | None = None
        self.show_called = False

    def add_mesh(self, mesh: pv.PolyData, **kwargs: Any) -> None:
        self.mesh = mesh
        self.mesh_kwargs = kwargs

    def add_axes(self) -> None:
        self.axes_added = True

    def view_vector(
        self,
        vector: np.ndarray,
        viewup: np.ndarray | None = None,
    ) -> None:
        self.view_normal = np.asarray(vector)
        self.view_up = None if viewup is None else np.asarray(viewup)

    def enable_parallel_projection(self) -> None:
        self.parallel_projection_enabled = True

    def reset_camera(
        self,
        bounds: tuple[float, ...] | None = None,
        render: bool = True,
    ) -> None:
        self.camera_bounds = bounds
        self.camera_render = render

    def show(self) -> None:
        self.show_called = True


def _cut() -> pv.PolyData:
    cut = pv.Plane(i_resolution=1, j_resolution=1)
    cut.point_data["P [nPa]"] = np.arange(cut.n_points, dtype=float)
    cut.point_data["Temperature"] = np.arange(cut.n_points, dtype=float) + 10.0
    cut.field_data[CUT_NORMAL_KEY] = np.array([0.0, 0.0, 1.0])
    cut.field_data[CUT_ORIGIN_KEY] = np.array([0.0, 0.0, 0.0])
    return cut


def test_plot_2d_cut_defaults_to_pressure_without_showing() -> None:
    plotter = RecordingPlotter()
    cut = _cut()

    result = plot_2d_cut(
        cut,
        plotter=plotter,  # type: ignore[arg-type]
        show=False,
    )

    assert result is plotter
    assert plotter.mesh is cut
    assert plotter.mesh_kwargs["scalars"] == "P [nPa]"
    assert plotter.mesh_kwargs["cmap"] == "viridis"
    assert plotter.mesh_kwargs["scalar_bar_args"]["title"] == "P [nPa]"
    assert plotter.axes_added
    assert plotter.parallel_projection_enabled
    assert plotter.camera_bounds is None
    np.testing.assert_allclose(plotter.view_normal, [0.0, 0.0, 1.0])
    assert not plotter.show_called


def test_plot_2d_cut_resolves_pressure_alias() -> None:
    plotter = RecordingPlotter()

    plot_2d_cut(
        _cut(),
        scalars="pressure",
        plotter=plotter,  # type: ignore[arg-type]
        show=False,
    )

    assert plotter.mesh_kwargs["scalars"] == "P [nPa]"


def test_plot_2d_cut_resolves_case_insensitive_scalar() -> None:
    plotter = RecordingPlotter()

    plot_2d_cut(
        _cut(),
        scalars="temperature",
        plotter=plotter,  # type: ignore[arg-type]
        show=False,
    )

    assert plotter.mesh_kwargs["scalars"] == "Temperature"


def test_plot_2d_cut_shows_by_default() -> None:
    plotter = RecordingPlotter()

    plot_2d_cut(_cut(), plotter=plotter)  # type: ignore[arg-type]

    assert plotter.show_called


def test_plot_2d_cut_creates_plotter_when_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plotter = RecordingPlotter()
    monkeypatch.setattr(pv, "Plotter", lambda: plotter)

    result = plot_2d_cut(_cut(), show=False)

    assert result is plotter


def test_plot_2d_cut_forwards_mesh_and_scalar_bar_options() -> None:
    plotter = RecordingPlotter()

    plot_2d_cut(
        _cut(),
        plotter=plotter,  # type: ignore[arg-type]
        show=False,
        cmap="plasma",
        opacity=0.5,
        scalar_bar_args={"title": "Pressure", "vertical": True},
    )

    assert plotter.mesh_kwargs["cmap"] == "plasma"
    assert plotter.mesh_kwargs["opacity"] == 0.5
    assert plotter.mesh_kwargs["scalar_bar_args"] == {
        "title": "Pressure",
        "vertical": True,
    }


def test_plot_2d_cut_applies_xrange_and_yrange_to_camera() -> None:
    plotter = RecordingPlotter()
    cut = _cut()

    plot_2d_cut(
        cut,
        plotter=plotter,  # type: ignore[arg-type]
        show=False,
        xrange=(-0.25, 0.5),
        yrange=(-0.75, 0.25),
    )

    assert plotter.mesh is cut
    assert plotter.camera_bounds == pytest.approx(
        (-0.25, 0.5, -0.75, 0.25, cut.bounds.z_min, cut.bounds.z_max)
    )
    assert plotter.camera_render is False
    assert "xrange" not in plotter.mesh_kwargs
    assert "yrange" not in plotter.mesh_kwargs


def test_plot_2d_cut_uses_full_axis_when_one_range_is_omitted() -> None:
    plotter = RecordingPlotter()
    cut = _cut()

    plot_2d_cut(
        cut,
        plotter=plotter,  # type: ignore[arg-type]
        show=False,
        xrange=(-0.25, 0.25),
    )

    assert plotter.camera_bounds == pytest.approx(
        (
            -0.25,
            0.25,
            cut.bounds.y_min,
            cut.bounds.y_max,
            cut.bounds.z_min,
            cut.bounds.z_max,
        )
    )


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("xrange", (0.0,)),
        ("xrange", ("low", "high")),
        ("xrange", (0.0, np.nan)),
        ("yrange", (1.0, 1.0)),
        ("yrange", (1.0, -1.0)),
    ],
)
def test_plot_2d_cut_rejects_invalid_range(
    name: str,
    value: tuple[object, ...],
) -> None:
    kwargs = {name: value}

    with pytest.raises(DatasetError, match=name):
        plot_2d_cut(
            _cut(),
            plotter=RecordingPlotter(),  # type: ignore[arg-type]
            show=False,
            **kwargs,
        )


def test_plot_2d_cut_rejects_missing_scalar() -> None:
    with pytest.raises(DatasetError, match="Available arrays"):
        plot_2d_cut(
            _cut(),
            scalars="density",
            plotter=RecordingPlotter(),  # type: ignore[arg-type]
            show=False,
        )


@pytest.mark.parametrize("missing_key", [CUT_NORMAL_KEY, CUT_ORIGIN_KEY])
def test_plot_2d_cut_requires_plane_metadata(missing_key: str) -> None:
    cut = _cut()
    del cut.field_data[missing_key]

    with pytest.raises(DatasetError, match="metadata"):
        plot_2d_cut(
            cut,
            plotter=RecordingPlotter(),  # type: ignore[arg-type]
            show=False,
        )


def test_plot_2d_cut_rejects_malformed_plane_metadata() -> None:
    cut = _cut()
    cut.field_data[CUT_NORMAL_KEY] = np.array([0.0, 1.0])

    with pytest.raises(DatasetError, match="normal"):
        plot_2d_cut(
            cut,
            plotter=RecordingPlotter(),  # type: ignore[arg-type]
            show=False,
        )


def test_plot_2d_cut_rejects_empty_cut() -> None:
    empty = pv.PolyData()
    empty.field_data[CUT_NORMAL_KEY] = np.array([0.0, 0.0, 1.0])
    empty.field_data[CUT_ORIGIN_KEY] = np.array([0.0, 0.0, 0.0])

    with pytest.raises(DatasetError, match="empty"):
        plot_2d_cut(
            empty,
            plotter=RecordingPlotter(),  # type: ignore[arg-type]
            show=False,
        )


def test_plot_2d_cut_requires_polydata() -> None:
    with pytest.raises(DatasetError, match="PolyData"):
        plot_2d_cut(
            pv.ImageData(),
            plotter=RecordingPlotter(),  # type: ignore[arg-type]
            show=False,
        )
