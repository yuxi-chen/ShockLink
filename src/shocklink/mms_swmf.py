"""Build SWMF inputs from MMS analysis results."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import math
import sys

from shocklink.constants import CARTESIAN_COMPONENTS, EV_TO_K
from shocklink.mms import average_plotted_values, load_mms_data
from shocklink.swmf import MMSLocation, SolarWindValues, generate_param_file
from shocklink.utilities import TimeBounds, midpoint_datetime, parse_datetime




def _required_average(averages: Mapping[str, float], name: str) -> float:
    try:
        value = float(averages[name])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"MMS average {name!r} is required") from error
    if not math.isfinite(value):
        raise ValueError(f"MMS average {name!r} must be finite")
    return value


def _vector_average(
    averages: Mapping[str, float], prefix: str
) -> tuple[float, float, float]:
    x, y, z = (
        _required_average(averages, f"{prefix}_{component}")
        for component in CARTESIAN_COMPONENTS
    )
    return x, y, z


def solar_wind_from_averages(averages: Mapping[str, float]) -> SolarWindValues:
    """Map GSM MMS averages to SWMF solar-wind values."""
    density = _required_average(averages, "ion_density")
    ion_temperature = _required_average(averages, "ion_temperature")
    electron_temperature = _required_average(averages, "electron_temperature")
    velocity = _vector_average(averages, "ion_velocity")
    magnetic_field = _vector_average(averages, "magnetic_field")
    return SolarWindValues(
        density=density,
        temperature_kelvin=(ion_temperature + electron_temperature) * EV_TO_K,
        velocity=velocity,
        magnetic_field=magnetic_field,
    )


def mms_location_from_averages(averages: Mapping[str, float]) -> MMSLocation:
    """Map interval-averaged GSM MMS position values in Earth radii."""
    x, y, z = _vector_average(averages, "satellite_location")
    return MMSLocation(x, y, z)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''examples:
  create_swmf_input.py --mms-start "2018-12-19 19:40:00" --mms-end "2018-12-19 19:52:00" --output generated.in
  create_swmf_input.py --mms-start "2017-01-01 00:00:00" --mms-end "2017-01-01 00:05:00" --output generated.in --probe 2 --mode brst
  create_swmf_input.py --mms-start "2018-12-19 19:40:00" --mms-end "2018-12-19 19:52:00" --output generated.in --input custom/PARAM.in --start-time "2018-12-19 19:45:00"''',
    )
    parser.add_argument(
        "--mms-start", required=True, help="MMS observation interval start time"
    )
    parser.add_argument(
        "--mms-end", required=True, help="MMS observation interval end time"
    )
    parser.add_argument(
        "--output", required=True, help="output SWMF parameter file to create"
    )
    parser.add_argument(
        "--input",
        default="data/Param/PARAM.in.Earth",
        help="template (default: data/Param/PARAM.in.Earth)",
    )
    parser.add_argument(
        "--start-time",
        help="override the MMS interval midpoint used for #STARTTIME",
    )
    parser.add_argument(
        "--probe",
        type=int,
        choices=range(1, 5),
        default=1,
        help="MMS spacecraft number (default: 1)",
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "brst", "fast"),
        default="auto",
        help="data rate (default: auto; auto prefers burst, then fast)",
    )
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
        averages = average_plotted_values(data)
        solar_wind = solar_wind_from_averages(averages)
        location = mms_location_from_averages(averages)
        bounds = TimeBounds.from_strings(arguments.mms_start, arguments.mms_end)
        start_time = (
            parse_datetime(arguments.start_time)
            if arguments.start_time
            else midpoint_datetime(bounds.start, bounds.end)
        )
        generate_param_file(
            arguments.input, arguments.output, start_time, solar_wind, location
        )
    except Exception as error:
        print(f"Could not create SWMF input: {error}", file=sys.stderr)
        return 1
    print(f"Wrote SWMF input to {arguments.output}")
    return 0
