from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import shocklink.mms_swmf as mms_swmf
from shocklink.constants import CARTESIAN_COMPONENTS
from shocklink.mms_swmf import solar_wind_from_averages
from shocklink.swmf import MMSLocation, SolarWindValues


def test_solar_wind_from_averages_maps_mms_values() -> None:
    result = solar_wind_from_averages(
        {
            "ion_density": 5.0,
            "ion_temperature": 2.0,
            "electron_temperature": 3.0,
            "ion_velocity_x": -400.0,
            "ion_velocity_y": 20.0,
            "ion_velocity_z": 30.0,
            "magnetic_field_x": -5.0,
            "magnetic_field_y": 2.0,
            "magnetic_field_z": 1.0,
        }
    )

    assert result == SolarWindValues(
        density=5.0,
        temperature_kelvin=5.0 * 11604.51812,
        velocity=(-400.0, 20.0, 30.0),
        magnetic_field=(-5.0, 2.0, 1.0),
    )


@pytest.mark.parametrize(
    "missing",
    [
        "ion_density",
        "ion_temperature",
        "electron_temperature",
        "ion_velocity_x",
        "ion_velocity_y",
        "ion_velocity_z",
        "magnetic_field_x",
        "magnetic_field_y",
        "magnetic_field_z",
    ],
)
def test_solar_wind_from_averages_reports_missing_values(missing: str) -> None:
    averages = {
        "ion_density": 1.0,
        "ion_temperature": 1.0,
        "electron_temperature": 1.0,
        "ion_velocity_x": 1.0,
        "ion_velocity_y": 1.0,
        "ion_velocity_z": 1.0,
        "magnetic_field_x": 1.0,
        "magnetic_field_y": 1.0,
        "magnetic_field_z": 1.0,
    }
    del averages[missing]

    with pytest.raises(ValueError, match=missing):
        solar_wind_from_averages(averages)


def test_solar_wind_from_averages_rejects_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="ion_density"):
        solar_wind_from_averages(
            {
                "ion_density": float("nan"),
                "ion_temperature": 1.0,
                "electron_temperature": 1.0,
                "ion_velocity_x": 1.0,
                "ion_velocity_y": 1.0,
                "ion_velocity_z": 1.0,
                "magnetic_field_x": 1.0,
                "magnetic_field_y": 1.0,
                "magnetic_field_z": 1.0,
            }
        )


def test_mms_location_from_averages_maps_gsm_earth_radii() -> None:
    assert mms_swmf.mms_location_from_averages(
        {
            "satellite_location_x": 10.8,
            "satellite_location_y": 9.9,
            "satellite_location_z": -5.5,
        }
    ) == MMSLocation(10.8, 9.9, -5.5)


@pytest.mark.parametrize("prefix", ["ion_velocity", "magnetic_field"])
@pytest.mark.parametrize("component", CARTESIAN_COMPONENTS)
def test_vector_average_requires_every_component(prefix: str, component: str) -> None:
    averages = {
        "ion_density": 1.0,
        "ion_temperature": 1.0,
        "electron_temperature": 1.0,
        "ion_velocity_x": 1.0,
        "ion_velocity_y": 1.0,
        "ion_velocity_z": 1.0,
        "magnetic_field_x": 1.0,
        "magnetic_field_y": 1.0,
        "magnetic_field_z": 1.0,
    }
    del averages[f"{prefix}_{component}"]

    with pytest.raises(ValueError, match=f"{prefix}_{component}"):
        solar_wind_from_averages(averages)


def test_vector_average_collects_cartesian_components() -> None:
    from shocklink.mms_swmf import _vector_average

    averages = {
        f"velocity_{component}": index
        for index, component in enumerate(CARTESIAN_COMPONENTS)
    }
    assert _vector_average(averages, "velocity") == (0.0, 1.0, 2.0)


def _averages() -> dict[str, float]:
    return {
        "ion_density": 5.0,
        "ion_temperature": 2.0,
        "electron_temperature": 3.0,
        "ion_velocity_x": -400.0,
        "ion_velocity_y": 20.0,
        "ion_velocity_z": 30.0,
        "magnetic_field_x": -5.0,
        "magnetic_field_y": 2.0,
        "magnetic_field_z": 1.0,
        "satellite_location_x": 10.8,
        "satellite_location_y": 9.9,
        "satellite_location_z": -5.5,
    }


def test_parse_args_accepts_workflow_options() -> None:
    arguments = mms_swmf.parse_args(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--plot",
            "false",
            "--input",
            "template.in",
            "--output",
            "generated.in",
            "--start-time",
            "2018-12-19 19:52:00",
            "--probe",
            "3",
            "--mode",
            "fast",
        ]
    )

    assert arguments.mms_start == "2018-12-19 19:40:00"
    assert arguments.mms_end == "2018-12-19 19:52:00"
    assert arguments.input == "template.in"
    assert arguments.output == "generated.in"
    assert arguments.start_time == "2018-12-19 19:52:00"
    assert arguments.probe == 3
    assert arguments.mode == "fast"
    assert arguments.plot is False


def test_parse_args_allows_omitted_output() -> None:
    arguments = mms_swmf.parse_args(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
        ]
    )

    assert arguments.output is None
    assert arguments.plot is True


def test_parse_args_finds_default_template_outside_repository(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    arguments = mms_swmf.parse_args(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--output",
            "generated.in",
        ]
    )

    expected = (
        Path(mms_swmf.__file__).resolve().parents[2]
        / "data"
        / "Param"
        / "PARAM.in.Earth"
    )
    assert Path(arguments.input) == expected
    assert Path(arguments.input).is_file()


def test_parse_args_preserves_explicit_relative_template(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    arguments = mms_swmf.parse_args(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--output",
            "generated.in",
            "--input",
            "custom/PARAM.in",
        ]
    )

    assert arguments.input == "custom/PARAM.in"


def _stub_mms_generation(monkeypatch, calls: dict[str, object]) -> None:
    monkeypatch.setattr(
        mms_swmf,
        "load_mms_data",
        lambda *args, **kwargs: calls.update(load=(args, kwargs))
        or SimpleNamespace(series={"magnetic_field": "b"}),
    )
    monkeypatch.setattr(mms_swmf, "average_plotted_values", lambda _data: _averages())
    monkeypatch.setattr(
        mms_swmf,
        "position_at_time_earth_radii",
        lambda _data, time: calls.update(position_time=time)
        or (10.8, 9.9, -5.5),
    )

    def write_output(template, output, start_time, solar_wind, location) -> None:
        calls["write"] = (template, output, start_time, solar_wind, location)

    monkeypatch.setattr(mms_swmf, "generate_param_file", write_output)


def test_create_swmf_input_exposes_all_workflow_options(
    tmp_path: Path, monkeypatch
) -> None:
    calls: dict[str, object] = {}
    _stub_mms_generation(monkeypatch, calls)
    output = tmp_path / "custom.in"
    start_time = datetime(2018, 12, 19, 19, 52, tzinfo=UTC)

    result = mms_swmf.create_swmf_input(
        "2018-12-19 19:40:00",
        "2018-12-19 19:52:00",
        output=output,
        input="template.in",
        start_time=start_time,
        probe=3,
        mode="fast",
        plot=False,
    )

    assert result == output
    assert calls["load"] == (
        ("2018-12-19 19:40:00", "2018-12-19 19:52:00"),
        {"probe": 3, "mode": "fast", "coordinates": "gsm"},
    )
    template, path, effective_time, _solar_wind, _location = calls["write"]
    assert template == "template.in"
    assert path == output
    assert effective_time == start_time
    assert calls["position_time"] == start_time


def test_create_swmf_input_saves_mms_plot_when_requested(
    tmp_path: Path, monkeypatch
) -> None:
    calls: dict[str, object] = {}
    _stub_mms_generation(monkeypatch, calls)

    class Figure:
        def savefig(self, path: Path, **kwargs: object) -> None:
            calls["plot"] = (path, kwargs)

    monkeypatch.setattr(mms_swmf, "plot_mms_data", lambda _data: Figure())
    monkeypatch.chdir(tmp_path)

    mms_swmf.create_swmf_input(
        "2018-12-19 19:40:00",
        "2018-12-19 19:52:00",
        output=tmp_path / "generated.in",
        plot=True,
    )

    assert calls["plot"] == (
        tmp_path / "mms_20181219_194000_20181219_195200.png",
        {"bbox_inches": "tight"},
    )


def test_parse_args_accepts_mms_plot_flag() -> None:
    arguments = mms_swmf.parse_args(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--plot",
            "true",
        ]
    )

    assert arguments.plot is True


def test_create_swmf_input_defaults_output_from_interval_midpoint(
    monkeypatch,
) -> None:
    calls: dict[str, object] = {}
    _stub_mms_generation(monkeypatch, calls)

    result = mms_swmf.create_swmf_input(
        "2018-12-19 19:40:00",
        "2018-12-19 19:52:00",
        plot=False,
    )

    assert result == Path("PARAM_20181219_194600.in")
    assert calls["write"][1] == result
    assert calls["position_time"] == datetime(2018, 12, 19, 19, 46, tzinfo=UTC)


@pytest.mark.parametrize(
    ("probe", "mode"),
    [(0, "auto"), (1, "invalid")],
)
def test_create_swmf_input_rejects_invalid_probe_or_mode(probe: int, mode: str) -> None:
    with pytest.raises(ValueError):
        mms_swmf.create_swmf_input(
            "2018-12-19 19:40:00",
            "2018-12-19 19:52:00",
            probe=probe,
            mode=mode,
        )


def test_main_loads_gsm_data_uses_midpoint_and_passes_values(
    monkeypatch, capsys
) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        mms_swmf,
        "load_mms_data",
        lambda *args, **kwargs: calls.update(load=(args, kwargs))
        or SimpleNamespace(series={"magnetic_field": "b"}),
    )
    monkeypatch.setattr(mms_swmf, "average_plotted_values", lambda _data: _averages())
    monkeypatch.setattr(
        mms_swmf,
        "position_at_time_earth_radii",
        lambda _data, time: calls.update(position_time=time)
        or (1.1, 2.2, 3.3),
    )

    def write_output(template, output, start_time, solar_wind, location) -> None:
        calls["write"] = (template, output, start_time, solar_wind, location)

    monkeypatch.setattr(mms_swmf, "generate_param_file", write_output)

    result = mms_swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--plot",
            "false",
        ]
    )

    assert result == 0
    assert calls["load"] == (
        ("2018-12-19 19:40:00", "2018-12-19 19:52:00"),
        {"probe": 1, "mode": "auto", "coordinates": "gsm"},
    )
    template, path, start_time, solar_wind, location = calls["write"]
    assert template == (
        Path(mms_swmf.__file__).resolve().parents[2]
        / "data"
        / "Param"
        / "PARAM.in.Earth"
    )
    assert path == Path("PARAM_20181219_194600.in")
    assert start_time == datetime(2018, 12, 19, 19, 46, tzinfo=UTC)
    assert solar_wind == solar_wind_from_averages(_averages())
    assert location == MMSLocation(1.1, 2.2, 3.3)
    assert calls["position_time"] == datetime(2018, 12, 19, 19, 46, tzinfo=UTC)
    assert "Wrote SWMF input to PARAM_20181219_194600.in" in capsys.readouterr().out


def test_main_honors_explicit_start_time(monkeypatch) -> None:
    position_times: list[datetime] = []
    monkeypatch.setattr(
        mms_swmf,
        "load_mms_data",
        lambda *_args, **_kwargs: SimpleNamespace(series={"magnetic_field": "b"}),
    )
    monkeypatch.setattr(mms_swmf, "average_plotted_values", lambda _data: _averages())
    monkeypatch.setattr(
        mms_swmf,
        "position_at_time_earth_radii",
        lambda _data, time: position_times.append(time)
        or (1.1, 2.2, 3.3),
    )
    captured: list[tuple[datetime, Path]] = []
    monkeypatch.setattr(
        mms_swmf,
        "generate_param_file",
        lambda _template, output, start_time, _solar_wind, _location: captured.append(
            (start_time, output)
        ),
    )

    result = mms_swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--start-time",
            "2018-12-19T14:52:00-05:00",
            "--plot",
            "false",
        ]
    )

    assert result == 0
    assert captured == [
        (
            datetime(2018, 12, 19, 19, 52, tzinfo=UTC),
            Path("PARAM_20181219_195200.in"),
        )
    ]
    assert position_times == [datetime(2018, 12, 19, 19, 52, tzinfo=UTC)]


def test_main_reports_mms_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        mms_swmf,
        "load_mms_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    result = mms_swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--output",
            "generated.in",
        ]
    )

    assert result == 1
    assert "Could not create SWMF input" in capsys.readouterr().err


def test_main_delegates_to_create_swmf_input(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def create(mms_start, mms_end, **kwargs):
        captured.update(mms_start=mms_start, mms_end=mms_end, **kwargs)
        return Path("PARAM_20181219_194600.in")

    monkeypatch.setattr(mms_swmf, "create_swmf_input", create)

    result = mms_swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--plot",
            "true",
        ]
    )

    assert result == 0
    assert captured == {
        "mms_start": "2018-12-19 19:40:00",
        "mms_end": "2018-12-19 19:52:00",
        "output": None,
        "input": mms_swmf._DEFAULT_TEMPLATE,
        "start_time": None,
        "probe": 1,
        "mode": "auto",
        "plot": True,
    }
    assert "Wrote SWMF input to PARAM_20181219_194600.in" in capsys.readouterr().out
