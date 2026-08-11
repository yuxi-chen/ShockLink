"""Build SWMF inputs from MMS analysis results."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import UTC, datetime
import math
from pathlib import Path
import sys
from typing import Literal

from shocklink.constants import CARTESIAN_COMPONENTS, EV_TO_K
from shocklink.mms import (
    average_plotted_values,
    load_mms_data,
    position_at_time_earth_radii,
    plot_mms_data,
)
from shocklink.swmf import MMSLocation, SolarWindValues, generate_param_file
from shocklink.utilities import TimeBounds, midpoint_datetime, parse_datetime


_DEFAULT_TEMPLATE = (
    Path(__file__).resolve().parents[2] / "data" / "Param" / "PARAM.in.Earth"
)



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


def create_swmf_input(
    mms_start: str,
    mms_end: str,
    *,
    output: str | Path | None = None,
    input: str | Path = _DEFAULT_TEMPLATE,
    start_time: str | datetime | None = None,
    probe: int = 1,
    mode: Literal["auto", "brst", "fast"] = "auto",
    plot_output: str | Path | None = None,
) -> Path:
    """Create an SWMF input file from interval-averaged MMS observations.

    Parameters
    ----------
    mms_start, mms_end
        MMS observation interval bounds.
    output
        Destination path. If omitted, use the UTC effective start time to name
        the file ``PARAM_YYYYMMDD_HHMMSS.in``.
    input
        SWMF template path.
    start_time
        Optional UTC start time override as an ISO string or datetime.
    probe
        MMS spacecraft number from 1 through 4.
    mode
        MMS data mode: ``auto``, ``brst``, or ``fast``.
    plot_output
        Optional path for saving the multi-panel MMS quick-look plot. When
        provided, the plot is generated from the loaded data used for the
        SWMF averages.

    Returns
    -------
    pathlib.Path
        The generated output path.

    Raises
    ------
    ValueError
        If ``probe`` or ``mode`` is invalid, or MMS values/timestamps are
        invalid.
    """
    if probe not in range(1, 5):
        raise ValueError("probe must be between 1 and 4")
    if mode not in {"auto", "brst", "fast"}:
        raise ValueError("mode must be one of: auto, brst, fast")

    bounds = TimeBounds.from_strings(mms_start, mms_end)
    if start_time is None:
        effective_start_time = midpoint_datetime(bounds.start, bounds.end)
    elif isinstance(start_time, datetime):
        if start_time.tzinfo is None:
            effective_start_time = start_time.replace(tzinfo=UTC)
        else:
            effective_start_time = start_time.astimezone(UTC)
    else:
        effective_start_time = parse_datetime(start_time)

    data = load_mms_data(
        mms_start,
        mms_end,
        probe=probe,
        mode=mode,
        coordinates="gsm",
    )
    if not data.series:
        raise RuntimeError("No MMS data were available for this interval")
    averages = average_plotted_values(data)
    solar_wind = solar_wind_from_averages(averages)
    location = MMSLocation(
        *position_at_time_earth_radii(data, effective_start_time)
    )

    if plot_output is not None:
        plot_path = Path(plot_output)
        plot_path.parent.mkdir(parents=True, exist_ok=True)
        figure = plot_mms_data(data)
        figure.savefig(plot_path, bbox_inches="tight")

    output_path = (
        Path(f"PARAM_{effective_start_time:%Y%m%d_%H%M%S}.in")
        if output is None
        else Path(output)
    )
    generate_param_file(
        input, output_path, effective_start_time, solar_wind, location
    )
    return output_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
epilog='''examples:
  create_swmf_input.py --mms-start "2018-12-19 19:40:00" --mms-end "2018-12-19 19:52:00"
  create_swmf_input.py --mms-start "2017-01-01 00:00:00" --mms-end "2017-01-01 00:05:00" --output generated.in --probe 2 --mode brst
  create_swmf_input.py --mms-start "2018-12-19 19:40:00" --mms-end "2018-12-19 19:52:00" --input custom/PARAM.in --start-time "2018-12-19 19:45:00"''',
    )
    parser.add_argument(
        "--mms-start", required=True, help="MMS observation interval start time"
    )
    parser.add_argument(
        "--mms-end", required=True, help="MMS observation interval end time"
    )
    parser.add_argument(
        "--output",
        help="output SWMF parameter file (default: PARAM_YYYYMMDD_HHMMSS.in)",
    )
    parser.add_argument(
        "--input",
        default=_DEFAULT_TEMPLATE,
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
    parser.add_argument(
        "--plot-output",
        type=Path,
        help="save the MMS quick-look plot to this path",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_args(argv)
    try:
        output = create_swmf_input(
            arguments.mms_start,
            arguments.mms_end,
            output=arguments.output,
            input=arguments.input,
            start_time=arguments.start_time,
            probe=arguments.probe,
            mode=arguments.mode,
            plot_output=arguments.plot_output,
        )
    except Exception as error:
        print(f"Could not create SWMF input: {error}", file=sys.stderr)
        return 1
    print(f"Wrote SWMF input to {output}")
    if arguments.plot_output is not None:
        print(f"Wrote MMS plot to {arguments.plot_output}")
    return 0
