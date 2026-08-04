"""Generate SWMF parameter files from MMS solar-wind averages."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import math
from pathlib import Path
import re
import sys


EV_TO_K = 11604.51812
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


def _parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"invalid timestamp {value!r}; use ISO format") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def midpoint_time(start: str, end: str) -> datetime:
    """Return the UTC midpoint of an inclusive MMS interval."""
    start_time = _parse_datetime(start)
    end_time = _parse_datetime(end)
    if start_time > end_time:
        raise ValueError("MMS start time must not be after end time")
    return start_time + (end_time - start_time) / 2


def _required_average(averages: dict[str, float], name: str) -> float:
    try:
        value = float(averages[name])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"MMS average {name!r} is required") from error
    if not math.isfinite(value):
        raise ValueError(f"MMS average {name!r} must be finite")
    return value


def average_to_solar_wind(averages: dict[str, float]) -> SolarWindValues:
    """Map MMS plotted averages to SWMF solar-wind parameters."""
    density = _required_average(averages, "ion_density")
    ion_temperature = _required_average(averages, "ion_temperature")
    electron_temperature = _required_average(averages, "electron_temperature")
    velocity = tuple(
        _required_average(averages, f"ion_velocity_{component}")
        for component in ("x", "y", "z")
    )
    magnetic_field = tuple(
        _required_average(averages, f"magnetic_field_{component}")
        for component in ("x", "y", "z")
    )
    return SolarWindValues(
        density=density,
        temperature_kelvin=(ion_temperature + electron_temperature) * EV_TO_K,
        velocity=velocity,  # type: ignore[arg-type]
        magnetic_field=magnetic_field,  # type: ignore[arg-type]
    )


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
        match = re.match(r"^(?P<lead>\s*)\S+(?P<between>\s+)(?P<rest>.*)$", line.rstrip("\r\n"))
        if match is None:
            raise ValueError(f"cannot replace {field} in template")
        newline = line[len(line.rstrip("\r\n")) :]
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mms-start", required=True, help="MMS interval start time")
    parser.add_argument("--mms-end", required=True, help="MMS interval end time")
    parser.add_argument("--output", required=True, help="Output SWMF parameter file")
    parser.add_argument(
        "--input", default="data/Param/PARAM.in.Earth", help="SWMF template path"
    )
    parser.add_argument("--start-time", help="Override the MMS midpoint for #STARTTIME")
    parser.add_argument("--probe", type=int, choices=range(1, 5), default=1)
    parser.add_argument("--mode", choices=("auto", "brst", "fast"), default="auto")
    return parser.parse_args(argv)


def _load_mms_data(*args: object, **kwargs: object):
    from shocklink.mms import load_mms_data

    return load_mms_data(*args, **kwargs)


def _average_plotted_values(data: object) -> dict[str, float]:
    from shocklink.mms import average_plotted_values

    return average_plotted_values(data)  # type: ignore[arg-type]


def main(argv: list[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        data = _load_mms_data(
            arguments.mms_start,
            arguments.mms_end,
            probe=arguments.probe,
            mode=arguments.mode,
            coordinates="gsm",
        )
        if not data.series:
            raise RuntimeError("No MMS data were available for this interval")
        solar_wind = average_to_solar_wind(_average_plotted_values(data))
        start_time = (
            _parse_datetime(arguments.start_time)
            if arguments.start_time
            else midpoint_time(arguments.mms_start, arguments.mms_end)
        )
        generate_param_file(arguments.input, arguments.output, start_time, solar_wind)
    except Exception as error:
        print(f"Could not create SWMF input: {error}", file=sys.stderr)
        return 1
    print(f"Wrote SWMF input to {arguments.output}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
