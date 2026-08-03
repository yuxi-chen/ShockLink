"""Command-line orchestration for the MMS analysis workflow."""

from __future__ import annotations

import argparse
from pprint import pprint
import sys

from .analysis import average_plotted_values, summarize_data
from .loading import load_mms_data
from .plotting import plot_mms_data


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for one MMS data interval."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start", required=True, help="Start time, e.g. '2015-10-16 13:06:00'."
    )
    parser.add_argument(
        "--end", required=True, help="End time, e.g. '2015-10-16 13:07:00'."
    )
    parser.add_argument(
        "--probe", type=int, default=1, choices=range(1, 5), help="MMS probe (1-4)."
    )
    parser.add_argument(
        "--mode",
        choices=("auto", "brst", "fast"),
        default="auto",
        help="Cadence: auto prefers burst and falls back to fast (default).",
    )
    parser.add_argument(
        "--coordinates",
        choices=("gse", "gsm"),
        default="gse",
        help="Vector coordinates: GSE (default) or time-dependent GSM.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Download, summarize, and display one MMS data interval."""
    arguments = parse_args(argv)
    try:
        data = load_mms_data(
            arguments.start,
            arguments.end,
            probe=arguments.probe,
            mode=arguments.mode,
            coordinates=arguments.coordinates,
        )
    except Exception as error:
        print(f"Could not download MMS data: {error}", file=sys.stderr)
        return 1
    if not data.series:
        print(
            "No MMS data were available for this interval. Try --mode fast or another time range.",
            file=sys.stderr,
        )
        return 1

    try:
        print(
            f"Loaded MMS{arguments.probe} {data.cadence} data "
            f"in {data.coordinates.upper()}."
        )
        pprint(summarize_data(data))
        pprint(average_plotted_values(data))
        figure = plot_mms_data(data)
        figure.show()
    except Exception as error:
        print(f"Could not analyze MMS data: {error}", file=sys.stderr)
        return 1
    return 0
