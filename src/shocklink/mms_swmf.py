"""Build SWMF inputs from MMS analysis results."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import math
import sys

from shocklink.constants import EV_TO_K
from shocklink.mms import average_plotted_values, load_mms_data
from shocklink.swmf import SolarWindValues
from shocklink.swmf import generate_param_file
from shocklink.utilities import TimeBounds, midpoint_datetime, parse_datetime




def _required_average(averages: Mapping[str, float], name: str) -> float:
    try:
        value = float(averages[name])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"MMS average {name!r} is required") from error
    if not math.isfinite(value):
        raise ValueError(f"MMS average {name!r} must be finite")
    return value


def solar_wind_from_averages(averages: Mapping[str, float]) -> SolarWindValues:
    """Map GSM MMS averages to SWMF solar-wind values."""
    density = _required_average(averages, "ion_density")
    ion_temperature = _required_average(averages, "ion_temperature")
    electron_temperature = _required_average(averages, "electron_temperature")
    velocity = tuple(
        _required_average(averages, f"ion_velocity_{component}")
        for component in "xyz"
    )
    magnetic_field = tuple(
        _required_average(averages, f"magnetic_field_{component}")
        for component in "xyz"
    )
    return SolarWindValues(
        density=density,
        temperature_kelvin=(ion_temperature + electron_temperature) * EV_TO_K,
        velocity=velocity,  # type: ignore[arg-type]
        magnetic_field=magnetic_field,  # type: ignore[arg-type]
    )


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


def main(argv: list[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        data = load_mms_data(
            arguments.mms_start,
            arguments.mms_end,
            probe=arguments.probe,
            mode=arguments.mode,
            coordinates="gsm",
        )
        if not data.series:
            raise RuntimeError("No MMS data were available for this interval")
        solar_wind = solar_wind_from_averages(average_plotted_values(data))
        bounds = TimeBounds.from_strings(arguments.mms_start, arguments.mms_end)
        start_time = (
            parse_datetime(arguments.start_time)
            if arguments.start_time
            else midpoint_datetime(bounds.start, bounds.end)
        )
        generate_param_file(arguments.input, arguments.output, start_time, solar_wind)
    except Exception as error:
        print(f"Could not create SWMF input: {error}", file=sys.stderr)
        return 1
    print(f"Wrote SWMF input to {arguments.output}")
    return 0
