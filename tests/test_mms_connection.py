from __future__ import annotations

from datetime import UTC, datetime
from inspect import signature
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from matplotlib.figure import Figure

import shocklink.mms_connection as workflow


def test_connection_plot_dpi_defaults_to_600() -> None:
    assert signature(workflow.save_mms_bow_shock_connection_plots).parameters["dpi"].default == 600


def test_resolve_mms_interval_defaults_to_symmetric_window() -> None:
    start, end = workflow.resolve_mms_interval(
        datetime(2023, 12, 16, 11, 30, tzinfo=UTC),
        window_seconds=300.0,
    )

    assert start == "2023-12-16T11:27:30+00:00"
    assert end == "2023-12-16T11:32:30+00:00"


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"start": "2023-12-16T11:30:00+00:00"}, "both"),
        ({"end": "2023-12-16T11:30:00+00:00"}, "both"),
        ({"window_seconds": 0.0}, "positive"),
    ],
)
def test_resolve_mms_interval_rejects_invalid_overrides(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        workflow.resolve_mms_interval(
            datetime(2023, 12, 16, 11, 30, tzinfo=UTC),
            **kwargs,
        )


def test_build_workflow_derives_interval_and_uses_public_pipeline(monkeypatch) -> None:
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
        "load_mms_data",
        lambda *args, **kwargs: calls.append("mms") or object(),
    )
    monkeypatch.setattr(
        workflow,
        "average_plotted_values",
        lambda value: {
            "satellite_location_x": 1.0,
            "satellite_location_y": 2.0,
            "satellite_location_z": 3.0,
            "magnetic_field_x": 1.0,
            "magnetic_field_y": 0.0,
            "magnetic_field_z": 0.0,
        },
    )
    monkeypatch.setattr(workflow, "analyze_shock_connection", lambda *args, **kwargs: connection)

    result = workflow.build_mms_bow_shock_connection("sample.dat", mms_window_seconds=60.0)

    assert result.connection is connection
    assert result.mms_start == "2023-12-16T11:29:30+00:00"
    assert result.mms_end == "2023-12-16T11:30:30+00:00"
    assert calls == ["divergence", "fit", "range", "surface", "smooth", "normals", "mms"]


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
