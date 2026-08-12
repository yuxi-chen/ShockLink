"""Write SWMF parameter files from already calculated input values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import math
from pathlib import Path
import re


STARTTIME_FIELDS = ("iYear", "iMonth", "iDay", "iHour", "iMinute", "iSecond", "FracSecond")
SOLARWIND_FIELDS = (
    "SwNDim",
    "SwTDim",
    "SwUxDim",
    "SwUyDim",
    "SwUzDim",
    "SwBxDim",
    "SwByDim",
    "SwBzDim",
)


@dataclass(frozen=True)
class SolarWindValues:
    """Solar-wind values in the units expected by the SWMF template."""

    density: float
    temperature_kelvin: float
    velocity: tuple[float, float, float]
    magnetic_field: tuple[float, float, float]

    def __post_init__(self) -> None:
        values = (
            ("density", self.density),
            ("temperature_kelvin", self.temperature_kelvin),
            *(
                (f"velocity_{component}", value)
                for component, value in zip("xyz", self.velocity, strict=True)
            ),
            *(
                (f"magnetic_field_{component}", value)
                for component, value in zip("xyz", self.magnetic_field, strict=True)
            ),
        )
        for name, value in values:
            if not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite")


@dataclass(frozen=True)
class MMSLocation:
    """MMS GSM position in Earth radii."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        for name, value in zip(("x", "y", "z"), (self.x, self.y, self.z), strict=True):
            if not math.isfinite(float(value)):
                raise ValueError(f"MMS location {name} must be finite")


@dataclass(frozen=True)
class MMSParamValues:
    """MMS connection values embedded in a generated SWMF PARAM file."""

    time: datetime
    magnetic_field: tuple[float, float, float]
    location: MMSLocation | None


def _format_number(value: float) -> str:
    return f"{value:.12g}"


def _param_section_values(
    lines: list[str], marker: str, fields: tuple[str, ...]
) -> dict[str, str]:
    """Read scalar values from one named PARAM section."""

    markers = [index for index, line in enumerate(lines) if line.strip() == marker]
    if len(markers) != 1:
        raise ValueError(f"PARAM file must contain exactly one {marker} section")
    start = markers[0] + 1
    end = next(
        (
            index
            for index in range(start, len(lines))
            if lines[index].lstrip().startswith("#")
            or lines[index].strip() == marker.removeprefix("#")
        ),
        len(lines),
    )
    values: dict[str, str] = {}
    for field in fields:
        matches = [
            line.split()[0]
            for line in lines[start:end]
            if re.match(rf"^\s*\S+\s+{re.escape(field)}(?:\s|$)", line)
        ]
        if len(matches) != 1:
            raise ValueError(f"PARAM section {marker} must contain exactly one {field}")
        values[field] = matches[0]
    return values


def _param_float(value: str, name: str) -> float:
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"PARAM value {name} must be numeric") from error
    if not math.isfinite(number):
        raise ValueError(f"PARAM value {name} must be finite")
    return number


def _mms_location_values(lines: list[str]) -> dict[str, str] | None:
    """Read coordinates following the explicit MMS-location comment."""

    markers = [
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("! MMS Location at ")
    ]
    if not markers:
        return None
    if len(markers) != 1:
        raise ValueError("PARAM file must contain at most one MMS location block")
    values: dict[str, str] = {}
    for line in lines[markers[0] + 1 :]:
        match = re.match(r"^\s*(\S+)\s+(GSM_[XYZ])(?:\s|$)", line)
        if match:
            field = match.group(2)
            if field in values:
                raise ValueError(f"PARAM MMS location contains duplicate {field}")
            values[field] = match.group(1)
            if len(values) == 3:
                return values
        if line.lstrip().startswith("#"):
            break
    missing = [field for field in ("GSM_X", "GSM_Y", "GSM_Z") if field not in values]
    raise ValueError(f"PARAM MMS location is missing: {', '.join(missing)}")


def read_mms_param_file(path: str | Path) -> MMSParamValues:
    """Read the MMS timestamp, averaged field, and location from PARAM.in.

    Parameters
    ----------
    path
        SWMF PARAM file produced by :func:`shocklink.mms_swmf.create_swmf_input`.

    Returns
    -------
    MMSParamValues
        UTC effective time, averaged GSM magnetic field in nT, and MMS GSM
        position in Earth radii.

    Raises
    ------
    ValueError
        If the file is unreadable or lacks valid required fields.
    """

    source = Path(path)
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ValueError(f"could not read PARAM file {source}: {error}") from error

    start_values = _param_section_values(
        lines,
        "#STARTTIME",
        ("iYear", "iMonth", "iDay", "iHour", "iMinute", "iSecond", "FracSecond"),
    )
    try:
        calendar = {
            "year": int(_param_float(start_values["iYear"], "iYear")),
            "month": int(_param_float(start_values["iMonth"], "iMonth")),
            "day": int(_param_float(start_values["iDay"], "iDay")),
            "hour": int(_param_float(start_values["iHour"], "iHour")),
            "minute": int(_param_float(start_values["iMinute"], "iMinute")),
            "second": int(_param_float(start_values["iSecond"], "iSecond")),
        }
        fraction = _param_float(start_values["FracSecond"], "FracSecond")
        if not 0.0 <= fraction < 1.0:
            raise ValueError("PARAM value FracSecond must be in [0, 1)")
        timestamp = datetime(**calendar, tzinfo=UTC) + timedelta(seconds=fraction)
    except (OverflowError, TypeError, ValueError) as error:
        if isinstance(error, ValueError) and str(error).startswith("PARAM value"):
            raise
        raise ValueError("PARAM #STARTTIME values do not form a valid UTC time") from error

    solar_values = _param_section_values(
        lines,
        "#SOLARWIND",
        ("SwBxDim", "SwByDim", "SwBzDim"),
    )
    magnetic_field = tuple(
        _param_float(solar_values[f"SwB{axis}Dim"], f"SwB{axis}Dim")
        for axis in "xyz"
    )
    location_values = _mms_location_values(lines)
    location = None
    if location_values is not None:
        location = MMSLocation(
            *(
                _param_float(location_values[f"GSM_{axis}"], f"GSM_{axis}")
                for axis in "XYZ"
            )
        )
    return MMSParamValues(timestamp, magnetic_field, location)


def _replace_section(
    lines: list[str], marker: str, fields: tuple[str, ...], values: tuple[str, ...]
) -> int:
    try:
        marker_index = next(index for index, line in enumerate(lines) if line.strip() == marker)
    except StopIteration as error:
        raise ValueError(f"template is missing {marker} section") from error

    field_indices: dict[str, int] = {}
    for index in range(marker_index + 1, len(lines)):
        if lines[index].lstrip().startswith("#"):
            break
        for field in fields:
            if re.search(rf"\b{re.escape(field)}\b", lines[index]):
                if field in field_indices:
                    raise ValueError(f"template contains duplicate {field}")
                field_indices[field] = index
    missing = [field for field in fields if field not in field_indices]
    if missing:
        raise ValueError(f"template section {marker} is missing: {', '.join(missing)}")

    for field, value in zip(fields, values, strict=True):
        index = field_indices[field]
        line = lines[index]
        content = line.rstrip("\r\n")
        match = re.match(r"^(?P<lead>\s*)\S+(?P<between>\s+)(?P<rest>.*)$", content)
        if match is None:
            raise ValueError(f"cannot replace {field} in template")
        newline = line[len(content) :]
        lines[index] = (
            f"{match.group('lead')}{value}{match.group('between')}{match.group('rest')}{newline}"
        )
    return max(field_indices.values())


def _location_lines(
    start_time: datetime, location: MMSLocation, newline: str
) -> list[str]:
    timestamp = start_time.strftime("%Y-%m-%d %H:%M:%S")
    if start_time.microsecond:
        timestamp += f".{start_time.microsecond:06d}".rstrip("0")
    return [
        f"! MMS Location at {timestamp}{newline}",
        f"{_format_number(location.x):<21}GSM_X{newline}",
        f"{_format_number(location.y):<21}GSM_Y{newline}",
        f"{_format_number(location.z):<21}GSM_Z{newline}",
    ]


def _replace_location(
    lines: list[str], start_index: int, start_time: datetime, location: MMSLocation
) -> None:
    newline = "\r\n" if lines[start_index].endswith("\r\n") else "\n"
    replacement = _location_lines(start_time, location, newline)
    location_start = start_index + 1
    if location_start >= len(lines) or lines[location_start].strip():
        lines.insert(location_start, newline)
        location_start += 1
    else:
        location_start += 1
    if lines[location_start : location_start + 1] and lines[location_start].startswith(
        "! MMS Location at "
    ):
        lines[location_start : location_start + 4] = replacement
        return
    lines[location_start:location_start] = replacement


def replace_param_values(
    template: str,
    start_time: datetime,
    solar_wind: SolarWindValues,
    location: MMSLocation | None = None,
) -> str:
    """Replace the STARTTIME and SOLARWIND values in a template string."""
    start_time = start_time.astimezone(UTC)
    start_values = (
        str(start_time.year),
        str(start_time.month),
        str(start_time.day),
        str(start_time.hour),
        str(start_time.minute),
        str(start_time.second),
        _format_number(start_time.microsecond / 1_000_000),
    )
    solar_values = (
        _format_number(solar_wind.density),
        _format_number(solar_wind.temperature_kelvin),
        *(_format_number(value) for value in solar_wind.velocity),
        *(_format_number(value) for value in solar_wind.magnetic_field),
    )
    lines = template.splitlines(keepends=True)
    start_section_end = _replace_section(lines, "#STARTTIME", STARTTIME_FIELDS, start_values)
    if location is not None:
        _replace_location(lines, start_section_end, start_time, location)
    _replace_section(lines, "#SOLARWIND", SOLARWIND_FIELDS, solar_values)
    return "".join(lines)


def generate_param_file(
    template_path: str | Path,
    output_path: str | Path,
    start_time: datetime,
    solar_wind: SolarWindValues,
    location: MMSLocation | None = None,
) -> None:
    """Read a template, update two sections, and write a new parameter file."""
    with Path(template_path).open(newline="") as source:
        template = source.read()
    result = replace_param_values(template, start_time, solar_wind, location)
    with Path(output_path).open("w", newline="") as destination:
        destination.write(result)
