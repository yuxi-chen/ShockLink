from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from shocklink.swmf import (
    MMSLocation,
    SolarWindValues,
    generate_param_file,
    read_mms_param_file,
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


def test_solar_wind_values_reject_nonfinite_fields() -> None:
    with pytest.raises(ValueError, match="density"):
        SolarWindValues(
            density=float("nan"),
            temperature_kelvin=1.0,
            velocity=(1.0, 2.0, 3.0),
            magnetic_field=(4.0, 5.0, 6.0),
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


def test_read_mms_param_file_extracts_time_field_and_location(
    tmp_path: Path,
) -> None:
    source = tmp_path / "PARAM.in"
    source.write_text(
        replace_param_values(
            TEMPLATE,
            datetime(2018, 12, 19, 19, 46, 0, 500000, tzinfo=UTC),
            SolarWindValues(1.0, 2.0, (3.0, 4.0, 5.0), (6.0, 7.0, 8.0)),
            MMSLocation(10.8, 9.9, -5.5),
        ),
        encoding="utf-8",
    )

    result = read_mms_param_file(source)

    assert result.time == datetime(2018, 12, 19, 19, 46, 0, 500000, tzinfo=UTC)
    assert result.magnetic_field == (6.0, 7.0, 8.0)
    assert result.location == MMSLocation(10.8, 9.9, -5.5)


def test_read_mms_param_file_allows_missing_mms_location(
    tmp_path: Path,
) -> None:
    source = tmp_path / "PARAM.in"
    source.write_text(TEMPLATE, encoding="utf-8")

    assert read_mms_param_file(source).location is None


def test_read_mms_param_file_stops_at_legacy_unmarked_section(
    tmp_path: Path,
) -> None:
    source = tmp_path / "PARAM.in"
    source.write_text(
        TEMPLATE
        + "SOLARWIND\n"
        + "5.844 SwNDim\n100000 SwTDim\n"
        + "-460 SwUxDim\n59 SwUyDim\n-31 SwUzDim\n"
        + "-6 SwBxDim\n0.5 SwByDim\n2.5 SwBzDim\n",
        encoding="utf-8",
    )

    result = read_mms_param_file(source)

    assert result.magnetic_field == (-7.52, 2.67, 2.67)


def test_read_mms_param_file_ignores_unmarked_gsm_coordinates(
    tmp_path: Path,
) -> None:
    source = tmp_path / "PARAM.in"
    source.write_text(
        replace_param_values(
            TEMPLATE,
            datetime(2018, 12, 19, 19, 46, tzinfo=UTC),
            SolarWindValues(1.0, 2.0, (3.0, 4.0, 5.0), (6.0, 7.0, 8.0)),
        ).replace(
            "#SOLARWIND\n",
            "10.8 GSM_X\n9.9 GSM_Y\n-5.5 GSM_Z\n#SOLARWIND\n",
        ),
        encoding="utf-8",
    )

    result = read_mms_param_file(source)

    assert result.location is None


def test_replace_param_values_rejects_malformed_sections() -> None:
    with pytest.raises(ValueError, match="missing: SwBzDim"):
        replace_param_values(
            TEMPLATE.replace("2.67 SwBzDim\n", ""),
            datetime(2018, 12, 19, 19, 46, tzinfo=UTC),
            SolarWindValues(1.0, 2.0, (3.0, 4.0, 5.0), (6.0, 7.0, 8.0)),
        )


def test_replace_param_values_adds_mms_location_after_starttime() -> None:
    result = replace_param_values(
        TEMPLATE,
        datetime(2020, 12, 9, 8, 0, 8, tzinfo=UTC),
        SolarWindValues(1.0, 2.0, (3.0, 4.0, 5.0), (6.0, 7.0, 8.0)),
        MMSLocation(10.8, 9.9, -5.5),
    )

    location = (
        "! MMS Location at 2020-12-09 08:00:08\n"
        "10.8                 GSM_X\n"
        "9.9                  GSM_Y\n"
        "-5.5                 GSM_Z\n"
    )
    assert location in result
    assert "0 FracSecond\n\n! MMS Location at 2020-12-09 08:00:08\n" in result
    assert result.index(location) > result.index("#STARTTIME")
    assert result.index(location) < result.index("#SOLARWIND")
