from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from shocklink.swmf import (
    SolarWindValues,
    average_to_solar_wind,
    generate_param_file,
    midpoint_time,
    replace_param_values,
)


TEMPLATE = """#STARTTIME
2023 iYear
12 iMonth
16 iDay
11 iHour
30 iMinute
0 iSecond
0 FracSecond
#SOLARWIND
5.63 SwNDim
1e5 SwTDim
-500 SwUxDim
0 SwUyDim
0 SwUzDim
-7.52 SwBxDim
2.67 SwByDim
2.67 SwBzDim
"""


def test_midpoint_time_and_start_fields_handle_fractional_seconds() -> None:
    midpoint = midpoint_time("2018-12-19 19:40:00", "2018-12-19 19:52:01")

    assert midpoint == datetime(2018, 12, 19, 19, 46, 0, 500000, tzinfo=UTC)


def test_average_to_solar_wind_sums_temperatures_and_converts_to_kelvin() -> None:
    values = average_to_solar_wind(
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

    assert values == SolarWindValues(
        density=5.0,
        temperature_kelvin=5.0 * 11604.51812,
        velocity=(-400.0, 20.0, 30.0),
        magnetic_field=(-5.0, 2.0, 1.0),
    )


def test_replace_param_values_updates_only_target_sections() -> None:
    template = (
        "header\n"
        "#STARTTIME\n"
        "2023\t\t iYear\n12\t\t iMonth\n16\t\t iDay\n"
        "11\t\t iHour\n30\t\t iMinute\n0\t\t iSecond\n0\t\t FracSecond\n"
        "untouched-start\n"
        "#SOLARWIND\n"
        "5.63\t\t SwNDim  [n/cc]\n1e5\t\t SwTDim  [K]\n"
        "-500\t\t SwUxDim [km/s]\n0\t\t SwUyDim [km/s]\n0\t\t SwUzDim [km/s]\n"
        "-7.52\t\t SwBxDim [nT]\n2.67\t\t SwByDim [nT]\n2.67\t\t SwBzDim [nT]\n"
        "untouched-end\n"
    )
    result = replace_param_values(
        template,
        datetime(2018, 12, 19, 19, 46, 0, 500000, tzinfo=UTC),
        SolarWindValues(5.0, 58022.5906, (-400.0, 20.0, 30.0), (-5.0, 2.0, 1.0)),
    )

    assert "2018\t\t iYear" in result
    assert "46\t\t iMinute" in result
    assert "0.5\t\t FracSecond" in result
    assert "5\t\t SwNDim  [n/cc]" in result
    assert "58022.5906\t\t SwTDim  [K]" in result
    assert "-400\t\t SwUxDim [km/s]" in result
    assert "header\n" in result
    assert "untouched-start\n" in result
    assert "untouched-end\n" in result


def test_generate_param_file_preserves_crlf_line_endings(tmp_path: Path) -> None:
    template = tmp_path / "PARAM.in"
    output = tmp_path / "PARAM.generated"
    template.write_bytes(TEMPLATE.replace("\n", "\r\n").encode())

    generate_param_file(
        template,
        output,
        datetime(2018, 12, 19, 19, 46, tzinfo=UTC),
        SolarWindValues(1.0, 2.0, (3.0, 4.0, 5.0), (6.0, 7.0, 8.0)),
    )

    generated = output.read_bytes()
    assert b"\r\n" in generated
    assert b"\n" not in generated.replace(b"\r\n", b"")


def test_average_to_solar_wind_rejects_missing_or_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="electron_temperature"):
        average_to_solar_wind({"ion_density": 1.0, "ion_temperature": 1.0})

    with pytest.raises(ValueError, match="ion_density"):
        average_to_solar_wind(
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


def test_main_loads_gsm_data_and_uses_interval_midpoint(tmp_path: Path, monkeypatch, capsys) -> None:
    import importlib

    swmf = importlib.import_module("shocklink.swmf")

    template = tmp_path / "PARAM.in"
    output = tmp_path / "PARAM.generated"
    template.write_text(TEMPLATE)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        swmf,
        "_load_mms_data",
        lambda *args, **kwargs: calls.append({"args": args, **kwargs})
        or SimpleNamespace(series={"magnetic_field": "b"}),
    )
    monkeypatch.setattr(
        swmf,
        "_average_plotted_values",
        lambda _data: {
            "ion_density": 5.0,
            "ion_temperature": 2.0,
            "electron_temperature": 3.0,
            "ion_velocity_x": -400.0,
            "ion_velocity_y": 20.0,
            "ion_velocity_z": 30.0,
            "magnetic_field_x": -5.0,
            "magnetic_field_y": 2.0,
            "magnetic_field_z": 1.0,
        },
    )

    result = swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--input",
            str(template),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert calls == [
        {
            "args": ("2018-12-19 19:40:00", "2018-12-19 19:52:00"),
            "probe": 1,
            "mode": "auto",
            "coordinates": "gsm",
        }
    ]
    assert "2018 iYear" in output.read_text()
    assert "46 iMinute" in output.read_text()
    assert "Wrote SWMF input" in capsys.readouterr().out


def test_main_honors_explicit_start_time(tmp_path: Path, monkeypatch) -> None:
    import importlib

    swmf = importlib.import_module("shocklink.swmf")

    template = tmp_path / "PARAM.in"
    output = tmp_path / "PARAM.generated"
    template.write_text(TEMPLATE)
    monkeypatch.setattr(swmf, "_load_mms_data", lambda *_args, **_kwargs: SimpleNamespace(series={"b": "b"}))
    monkeypatch.setattr(
        swmf,
        "_average_plotted_values",
        lambda _data: {
            "ion_density": 1.0,
            "ion_temperature": 1.0,
            "electron_temperature": 1.0,
            "ion_velocity_x": 1.0,
            "ion_velocity_y": 1.0,
            "ion_velocity_z": 1.0,
            "magnetic_field_x": 1.0,
            "magnetic_field_y": 1.0,
            "magnetic_field_z": 1.0,
        },
    )
    result = swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--start-time",
            "2018-12-19 19:52:00",
            "--input",
            str(template),
            "--output",
            str(output),
        ]
    )

    assert result == 0
    assert "2018 iYear" in output.read_text()
    assert "52 iMinute" in output.read_text()


def test_main_reports_loader_failure(monkeypatch, capsys) -> None:
    import importlib

    swmf = importlib.import_module("shocklink.swmf")

    monkeypatch.setattr(
        swmf,
        "_load_mms_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    result = swmf.main(
        [
            "--mms-start",
            "2018-12-19 19:40:00",
            "--mms-end",
            "2018-12-19 19:52:00",
            "--output",
            "/tmp/unused-param.in",
        ]
    )

    assert result == 1
    assert "Could not create SWMF input" in capsys.readouterr().err
