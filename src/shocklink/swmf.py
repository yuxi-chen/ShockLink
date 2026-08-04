"""Write SWMF parameter files from already calculated input values."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
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


def _format_number(value: float) -> str:
    return f"{value:.12g}"


def _replace_section(
    lines: list[str], marker: str, fields: tuple[str, ...], values: tuple[str, ...]
) -> None:
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


def replace_param_values(
    template: str, start_time: datetime, solar_wind: SolarWindValues
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
    _replace_section(lines, "#STARTTIME", STARTTIME_FIELDS, start_values)
    _replace_section(lines, "#SOLARWIND", SOLARWIND_FIELDS, solar_values)
    return "".join(lines)


def generate_param_file(
    template_path: str | Path,
    output_path: str | Path,
    start_time: datetime,
    solar_wind: SolarWindValues,
) -> None:
    """Read a template, update two sections, and write a new parameter file."""
    with Path(template_path).open(newline="") as source:
        template = source.read()
    result = replace_param_values(template, start_time, solar_wind)
    with Path(output_path).open("w", newline="") as destination:
        destination.write(result)
