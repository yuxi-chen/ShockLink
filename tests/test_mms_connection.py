from __future__ import annotations

from datetime import UTC, datetime
from inspect import signature
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from matplotlib.figure import Figure

import shocklink.mms_connection as workflow


def test_connection_plot_dpi_defaults_to_600() -> None:
    assert signature(workflow.save_mms_bow_shock_connection_plots).parameters["dpi"].default == 600


def test_build_workflow_uses_values_from_param_file(monkeypatch) -> None:
    grid = SimpleNamespace(
        field_data={"time_event": np.array(["2023-12-16T11:30:00+00:00"])},
    )
    connection = object()
    calls: list[str] = []

    monkeypatch.setattr(workflow, "load_simulation", lambda path: grid)
    monkeypatch.setattr(
        workflow,
        "calc_velocity_divergence",
        lambda value: calls.append("divergence"),
    )
    monkeypatch.setattr(workflow, "fit_bow_shock", lambda value: calls.append("fit"))
    monkeypatch.setattr(
        workflow,
        "extract_shockfit_range",
        lambda value, **kwargs: calls.append("range") or value,
    )
    monkeypatch.setattr(
        workflow,
        "get_bow_shock_surface",
        lambda value, **kwargs: calls.append("surface") or np.zeros((2, 2)),
    )
    monkeypatch.setattr(
        workflow,
        "smooth_bow_shock_surface",
        lambda value, **kwargs: calls.append("smooth") or value,
    )
    monkeypatch.setattr(
        workflow,
        "calc_bow_shock_normals",
        lambda value, **kwargs: calls.append("normals") or np.zeros((2, 2, 3)),
    )
    monkeypatch.setattr(
        workflow,
        "read_mms_param_file",
        lambda path: SimpleNamespace(
            time=datetime(2023, 12, 16, 11, 30, tzinfo=UTC),
            magnetic_field=(1.0, 0.0, 0.0),
            location=SimpleNamespace(x=1.0, y=2.0, z=3.0),
        ),
    )
    monkeypatch.setattr(workflow, "analyze_shock_connection", lambda *args, **kwargs: connection)

    result = workflow.build_mms_bow_shock_connection(
        "sample.dat", param_file="PARAM.in"
    )

    assert result.connection is connection
    assert result.mms_time == "2023-12-16T11:30:00+00:00"
    assert np.array_equal(result.mms_position, [1.0, 2.0, 3.0])
    assert np.array_equal(result.bavg, [1.0, 0.0, 0.0])
    assert calls == ["divergence", "fit", "range", "surface", "smooth", "normals"]

    monkeypatch.setattr(
        workflow,
        "read_mms_param_file",
        lambda path: SimpleNamespace(
            time=datetime(2023, 12, 16, 11, 30, tzinfo=UTC),
            magnetic_field=(1.0, 0.0, 0.0),
            location=None,
        ),
    )
    monkeypatch.setattr(workflow, "load_mms_data", lambda *args, **kwargs: "mms-data")
    monkeypatch.setattr(
        workflow,
        "position_at_time_earth_radii",
        lambda data, time: (4.0, 5.0, 6.0),
    )
    fallback = workflow.build_mms_bow_shock_connection(
        "sample.dat", param_file="PARAM.in"
    )
    assert np.array_equal(fallback.mms_position, [4.0, 5.0, 6.0])


def test_save_workflow_plots_supports_both_3d_formats(tmp_path: Path, monkeypatch) -> None:
    class Plotter:
        def screenshot(self, path, **kwargs):
            Path(path).write_bytes(b"png")

        def export_html(self, path):
            Path(path).write_text("<html></html>", encoding="utf-8")

        def close(self):
            pass

    monkeypatch.setattr(workflow, "plot_shock_angle_contour", lambda *args, **kwargs: (Figure(), object()))
    monkeypatch.setattr(workflow, "plot_shock_connection_3d", lambda *args, **kwargs: Plotter())
    result = SimpleNamespace(connection=object(), simulation_time="2023-12-16T11:30:00+00:00")

    paths = workflow.save_mms_bow_shock_connection_plots(
        result,
        tmp_path,
        output_prefix="sample",
        three_d_output="both",
    )

    assert paths.two_d == tmp_path / "sample_2d.png"
    assert paths.three_d_png == tmp_path / "sample_3d.png"
    assert paths.three_d_html == tmp_path / "sample_3d.html"
    assert all(path.is_file() for path in (paths.two_d, paths.three_d_png, paths.three_d_html))


def test_save_workflow_plots_defaults_to_input_stem(tmp_path: Path, monkeypatch) -> None:
    class Plotter:
        def screenshot(self, path, **kwargs):
            Path(path).write_bytes(b"png")

        def close(self):
            pass

    monkeypatch.setattr(workflow, "plot_shock_angle_contour", lambda *args, **kwargs: (Figure(), object()))
    monkeypatch.setattr(workflow, "plot_shock_connection_3d", lambda *args, **kwargs: Plotter())
    result = SimpleNamespace(
        connection=object(),
        simulation_time="2023-12-16T11:30:00+00:00",
        input_stem="sample",
    )

    paths = workflow.save_mms_bow_shock_connection_plots(result, tmp_path)

    assert paths.two_d == tmp_path / "sample_shock_connection_2d.png"
    assert paths.three_d_png == tmp_path / "sample_shock_connection_3d.png"
