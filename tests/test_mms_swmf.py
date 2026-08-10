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


def test_main_loads_gsm_data_uses_midpoint_and_passes_values(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    calls: dict[str, object] = {}

    monkeypatch.setattr(
        mms_swmf,
        "load_mms_data",
        lambda *args, **kwargs: calls.update(load=(args, kwargs))
        or SimpleNamespace(series={"magnetic_field": "b"}),
    )
    monkeypatch.setattr(mms_swmf, "average_plotted_values", lambda _data: _averages())

    def write_output(template, output, start_time, solar_wind, location) -> None:
        calls["write"] = (template, output, start_time, solar_wind, location)

    monkeypatch.setattr(mms_swmf, "generate_param_file", write_output)

    output = tmp_path / "generated.in"
    result = mms_swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--output",
            str(output),
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
    assert path == str(output)
    assert start_time == datetime(2018, 12, 19, 19, 46, tzinfo=UTC)
    assert solar_wind == solar_wind_from_averages(_averages())
    assert location == mms_swmf.mms_location_from_averages(_averages())
    assert f"Wrote SWMF input to {output}" in capsys.readouterr().out


def test_main_honors_explicit_start_time(monkeypatch) -> None:
    monkeypatch.setattr(
        mms_swmf,
        "load_mms_data",
        lambda *_args, **_kwargs: SimpleNamespace(series={"magnetic_field": "b"}),
    )
    monkeypatch.setattr(mms_swmf, "average_plotted_values", lambda _data: _averages())
    captured: list[datetime] = []
    monkeypatch.setattr(
        mms_swmf,
        "generate_param_file",
        lambda _template, _output, start_time, _solar_wind, _location: captured.append(start_time),
    )

    result = mms_swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--start-time",
            "2018-12-19T14:52:00-05:00",
            "--output",
            "generated.in",
        ]
    )

    assert result == 0
    assert captured == [datetime(2018, 12, 19, 19, 52, tzinfo=UTC)]


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
