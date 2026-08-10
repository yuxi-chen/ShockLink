from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
import pyvista as pv

from shocklink.connectivity import (
    ShockConnection,
    ShockIntersection,
    _build_surface_mesh,
    analyze_shock_connection,
    plot_shock_angle_contour,
    plot_shock_connection_3d,
)
from shocklink.exceptions import DatasetError, GeometryError


def _plane_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y = np.array([-1.0, 0.0, 1.0])
    z = np.array([-1.0, 0.0, 1.0])
    surface_x = np.full((3, 3), 5.0)
    normals = np.zeros((3, 3, 3))
    normals[..., 0] = 1.0
    return y, z, surface_x, normals


def test_build_surface_mesh_uses_only_complete_observed_quads() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    theta = np.full(surface_x.shape, 30.0)
    theta[0, 0] = np.nan

    mesh = _build_surface_mesh(surface_x, normals, theta, y=y, z=z)

    assert isinstance(mesh, pv.PolyData)
    assert mesh.n_cells == 6
    assert mesh.n_points == 8
    assert set(mesh.point_data) >= {"shock_normal", "theta_Bn [deg]"}
    np.testing.assert_allclose(mesh.point_data["theta_Bn [deg]"], 30.0)


def test_build_surface_mesh_winds_every_face_toward_positive_x() -> None:
    y, z, surface_x, normals = _plane_inputs()
    mesh = _build_surface_mesh(
        surface_x, normals, np.full(surface_x.shape, 45.0), y=y, z=z
    )
    face_normals = mesh.compute_normals(
        point_normals=False, cell_normals=True, auto_orient_normals=False
    ).cell_data["Normals"]
    assert np.all(face_normals[:, 0] > 0.0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"y": [1.0, 0.0, 2.0]}, "Y must be strictly increasing"),
        ({"surface_x": np.zeros((2, 2))}, "surface must have shape"),
        ({"normals": np.zeros((3, 3, 2))}, "normals must have shape"),
        ({"surface_x": np.full((3, 3), np.inf)}, "surface must not contain infinity"),
        ({"normals": np.full((3, 3, 3), np.nan)}, "normals must be finite"),
    ],
)
def test_build_surface_mesh_validates_inputs(
    kwargs: dict[str, object], message: str
) -> None:
    y, z, surface_x, normals = _plane_inputs()
    values: dict[str, object] = {
        "surface_x": surface_x,
        "normals": normals,
        "theta_bn_deg": np.zeros((3, 3)),
        "y": y,
        "z": z,
    }
    values.update(kwargs)
    with pytest.raises((DatasetError, GeometryError), match=message):
        _build_surface_mesh(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_angle", [np.nan, np.inf, -np.inf])
def test_build_surface_mesh_rejects_nonfinite_angles_on_observed_points(
    bad_angle: float,
) -> None:
    y, z, surface_x, normals = _plane_inputs()
    theta = np.full(surface_x.shape, 30.0)
    theta[1, 1] = bad_angle

    with pytest.raises(
        DatasetError, match="angle must be finite where surface is observed"
    ):
        _build_surface_mesh(surface_x, normals, theta, y=y, z=z)


def test_build_surface_mesh_allows_angle_nan_at_missing_surface_points() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    theta = np.full(surface_x.shape, 30.0)
    theta[0, 0] = np.nan

    mesh = _build_surface_mesh(surface_x, normals, theta, y=y, z=z)

    assert mesh.n_cells == 6


def test_build_surface_mesh_allows_nonfinite_point_data_at_surface_holes() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    normals[0, 0] = np.nan
    theta = np.full(surface_x.shape, 30.0)
    theta[0, 0] = np.nan

    mesh = _build_surface_mesh(surface_x, normals, theta, y=y, z=z)

    assert mesh.n_cells == 6


def test_build_surface_mesh_rejects_nonfinite_normals_on_observed_points() -> None:
    y, z, surface_x, normals = _plane_inputs()
    normals[1, 1] = np.nan

    with pytest.raises(
        DatasetError, match="normals must be finite where surface is observed"
    ):
        _build_surface_mesh(
            surface_x, normals, np.full(surface_x.shape, 30.0), y=y, z=z
        )


def test_build_surface_mesh_rejects_surface_with_no_complete_cells() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[:, :] = np.nan

    with pytest.raises(GeometryError, match="no complete observed cells"):
        _build_surface_mesh(
            surface_x, normals, np.full(surface_x.shape, 30.0), y=y, z=z
        )


def test_analyze_shock_connection_finds_shared_vertex_once() -> None:
    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x, normals, y=y, z=z, mms_position=[0.0, 0.0, 0.0], bavg=[2.0, 0.0, 0.0]
    )
    assert isinstance(result, ShockConnection)
    assert len(result.intersections) == 1
    hit = result.selected_intersection
    assert isinstance(hit, ShockIntersection)
    np.testing.assert_allclose(hit.point, [5.0, 0.0, 0.0])
    assert hit.line_parameter == pytest.approx(5.0)
    assert hit.distance == pytest.approx(5.0)
    np.testing.assert_allclose(hit.shock_normal, [1.0, 0.0, 0.0])
    assert hit.theta_bn_deg == pytest.approx(0.0)
    np.testing.assert_allclose(result.field_direction, [1.0, 0.0, 0.0])
    np.testing.assert_allclose(result.theta_bn_deg, 0.0)


def test_analyze_shock_connection_searches_both_field_directions() -> None:
    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x,
        normals,
        y=y,
        z=z,
        mms_position=[0.0, 0.0, 0.0],
        bavg=[-4.0, 0.0, 0.0],
    )
    assert result.selected_intersection.line_parameter == pytest.approx(-5.0)


def test_analyze_shock_connection_selects_crossing_closest_to_mms() -> None:
    y = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    z = np.array([-1.0, 0.0, 1.0])
    yy, zz = np.meshgrid(y, z, indexing="ij")
    surface_x = yy**2
    normals = np.stack((np.ones_like(yy), -2.0 * yy, np.zeros_like(zz)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    result = analyze_shock_connection(
        surface_x, normals, y=y, z=z, mms_position=[1.0, 0.8, 0.0], bavg=[0.0, 3.0, 0.0]
    )
    assert len(result.intersections) == 2
    np.testing.assert_allclose(result.selected_intersection.point, [1.0, 1.0, 0.0])
    assert result.selected_intersection.line_parameter == pytest.approx(0.2)
    assert result.intersections[1].line_parameter == pytest.approx(-1.8)


def test_analyze_masks_holes_and_freezes_arrays() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    result = analyze_shock_connection(
        surface_x, normals, y=y, z=z, mms_position=[0.0, 0.0, 0.0], bavg=[1.0, 0.0, 0.0]
    )
    assert np.isnan(result.theta_bn_deg[0, 0])
    with pytest.raises(ValueError):
        result.mms_position[0] = 2.0


def test_analyze_rejects_no_intersection_and_bad_inputs() -> None:
    y, z, surface_x, normals = _plane_inputs()
    with pytest.raises(GeometryError, match="does not intersect"):
        analyze_shock_connection(
            surface_x,
            normals,
            y=y,
            z=z,
            mms_position=[0.0, 0.0, 10.0],
            bavg=[0.0, 1.0, 0.0],
        )
    with pytest.raises(DatasetError):
        analyze_shock_connection(
            surface_x, normals, y=y, z=z, mms_position=[0.0, 0.0], bavg=[1.0, 0.0, 0.0]
        )
    with pytest.raises(DatasetError):
        analyze_shock_connection(
            surface_x,
            normals,
            y=y,
            z=z,
            mms_position=[0.0, 0.0, 0.0],
            bavg=[0.0, 0.0, 0.0],
        )


def test_coplanar_displaced_line_is_not_ambiguous() -> None:
    y, z, surface_x, normals = _plane_inputs()
    with pytest.raises(GeometryError, match="does not intersect"):
        analyze_shock_connection(
            surface_x,
            normals,
            y=y,
            z=z,
            mms_position=[5.0, 2.0, 0.0],
            bavg=[0.0, 0.0, 1.0],
        )


def test_coplanar_overlapping_line_is_ambiguous() -> None:
    y, z, surface_x, normals = _plane_inputs()
    with pytest.raises(GeometryError, match="ambiguous"):
        analyze_shock_connection(
            surface_x,
            normals,
            y=y,
            z=z,
            mms_position=[5.0, 0.0, 0.0],
            bavg=[0.0, 0.0, 1.0],
        )


def test_plot_shock_angle_contour_masks_holes_and_marks_intersection() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    result = analyze_shock_connection(
        surface_x, normals, y=y, z=z, mms_position=[0.0, 0.0, 0.0], bavg=[1.0, 0.0, 0.0]
    )
    fig, ax = plt.subplots()
    figure, returned = plot_shock_angle_contour(result, ax=ax)
    assert figure is fig
    assert returned is ax
    assert ax.get_aspect() in (1.0, "equal")
    assert ax.get_xlabel() == r"Y [R$_E$]"
    assert ax.get_ylabel() == r"Z [R$_E$]"
    assert ax.xaxis.label.get_size() == 26
    assert ax.yaxis.label.get_size() == 26
    assert ax.xaxis.get_ticklabels()[0].get_size() == 22
    assert ax.xaxis.majorTicks[0].tick1line.get_markersize() == 9
    assert ax.xaxis.majorTicks[0].tick1line.get_markeredgewidth() == 2.5
    assert any(
        "intersection" in str(coll.get_label()).lower() for coll in ax.collections
    )
    assert len(ax.texts) >= 1
    plt.close(fig)


def test_plot_shock_angle_contour_rejects_levels_outside_fixed_range() -> None:
    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x, normals, y=y, z=z, mms_position=[0.0, 0.0, 0.0], bavg=[1.0, 0.0, 0.0]
    )
    with pytest.raises(DatasetError, match="between 0 and 90"):
        plot_shock_angle_contour(result, levels=[-1.0, 45.0, 90.0])
    with pytest.raises(DatasetError, match="between 0 and 90"):
        plot_shock_angle_contour(result, levels=[0.0, 45.0, 91.0])
    with pytest.raises(DatasetError, match="finite and strictly increasing"):
        plot_shock_angle_contour(result, levels=[0.0, "bad", 90.0])


def test_plot_shock_angle_contour_matches_reference_style(monkeypatch) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tight_layout_calls = []
    monkeypatch.setattr(
        plt, "tight_layout", lambda *args, **kwargs: tight_layout_calls.append((args, kwargs))
    )

    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x,
        normals,
        y=y,
        z=z,
        mms_position=[0.0, 0.0, 0.0],
        bavg=[1.0, 0.0, 0.0],
    )
    result = replace(
        result,
        theta_bn_deg=np.array(
            [[30.0, 45.0, 60.0], [40.0, 50.0, 70.0], [20.0, 55.0, 80.0]]
        ),
    )

    figure, ax = plot_shock_angle_contour(
        result, cmap="plasma", yrange=[-5.0, 15.0], zrange=[-10.0, 10.0]
    )

    assert figure.get_size_inches().tolist() == [10.0, 8.0]
    assert ax.get_xlim() == (-5.0, 15.0)
    assert ax.get_ylim() == (-10.0, 10.0)
    assert ax.get_xlabel() == r"Y [R$_E$]"
    assert ax.get_ylabel() == r"Z [R$_E$]"
    assert any("MMS (GSM)" in text.get_text() for text in ax.texts)
    assert any("IMF =" in text.get_text() for text in ax.texts)
    assert any("Intersection =" in text.get_text() for text in ax.texts)
    assert any("45°" in text.get_text() for text in ax.texts)
    assert any("50°" in text.get_text() for text in ax.texts)
    assert any(text.get_color() == "red" for text in ax.texts)
    white_lines = [line for line in ax.lines if line.get_color() == "white"]
    assert len(white_lines) == 2
    assert any(np.all(np.asarray(line.get_xdata()) == 0.0) for line in white_lines)
    assert any(np.all(np.asarray(line.get_ydata()) == 0.0) for line in white_lines)
    annotation = next(text for text in ax.texts if text.get_text() == "(0.00°)")
    assert annotation.get_position() == (3.0, 0.0)
    assert annotation.get_transform() == ax.transData
    assert figure.axes[-1].get_yticks().tolist() == list(range(10, 91, 10))
    assert figure.axes[-1].get_ylabel() == r"$\theta_{BN}$"
    assert figure.axes[-1].yaxis.label.get_size() == 26
    assert figure.axes[-1].yaxis.get_ticklabels()[0].get_size() == 22
    assert tight_layout_calls == [((), {})]
    plt.close(figure)


def test_plot_shock_connection_3d_uses_reference_axis_and_colorbar_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x, normals, y=y, z=z, mms_position=[0.0, 0.0, 0.0], bavg=[1.0, 0.0, 0.0]
    )
    plotter = pv.Plotter(off_screen=True)
    axes_kwargs: dict[str, str] = {}
    scalar_bar_args: dict[str, str] = {}
    original_add_mesh = plotter.add_mesh

    monkeypatch.setattr(plotter, "add_axes", lambda **kwargs: axes_kwargs.update(kwargs))

    def record_mesh(*args, **kwargs):
        if kwargs.get("name") == "bow_shock":
            scalar_bar_args.update(kwargs["scalar_bar_args"])
        return original_add_mesh(*args, **kwargs)

    monkeypatch.setattr(plotter, "add_mesh", record_mesh)
    plot_shock_connection_3d(result, plotter=plotter, show=False)

    assert axes_kwargs == {
        "xlabel": r"X [R$_E$]",
        "ylabel": r"Y [R$_E$]",
        "zlabel": r"Z [R$_E$]",
    }
    assert scalar_bar_args["title"] == r"$\theta_{BN}$"
    plotter.close()


def test_plot_shock_connection_3d_adds_named_actors() -> None:
    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x, normals, y=y, z=z, mms_position=[0.0, 0.0, 0.0], bavg=[1.0, 0.0, 0.0]
    )
    plotter = pv.Plotter(off_screen=True)
    returned = plot_shock_connection_3d(result, plotter=plotter, show=False)
    assert returned is plotter
    names = set(plotter.actors)
    assert {
        "earth",
        "bow_shock",
        "mms",
        "intersection",
        "field_line",
        "bavg_arrow",
    } <= names
    plotter.close()


def test_plot_shock_connection_3d_zero_distance_hit_has_continuation() -> None:
    y, z, surface_x, normals = _plane_inputs()
    theta = np.zeros(surface_x.shape)
    mesh = _build_surface_mesh(surface_x, normals, theta, y=y, z=z)
    mms = np.array([5.0, 0.0, 0.0])
    hit = ShockIntersection(mms, 0.0, 0.0, 0, [1.0, 0.0, 0.0], [1.0, 0.0, 0.0], 0.0)
    result = ShockConnection(
        mms,
        np.array([1.0, 0.0, 0.0]),
        np.array([1.0, 0.0, 0.0]),
        y,
        z,
        theta,
        mesh,
        (hit,),
    )
    plotter = pv.Plotter(off_screen=True)
    plot_shock_connection_3d(result, plotter=plotter, show=False)
    line_points = plotter.actors["field_line"].mapper.dataset.points
    assert np.linalg.norm(line_points[-1] - line_points[0]) > 0.0
    plotter.close()
