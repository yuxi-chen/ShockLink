#!/usr/bin/env python
"""Create SWMF PARAM files for a list of MMS observation intervals.

Run from the repository root after installing the MMS extras::

    PYTHONPATH=src python examples/create_swmf_inputs.py

Edit ``EVENTS`` below to process the intervals needed for a study.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from shocklink.mms_swmf import create_swmf_input


# Each event is an MMS observation interval: (UTC start, UTC end).
EVENTS = [
    ("2018-12-19 19:40:00", "2018-12-19 19:52:00"),
    ("2019-01-01 00:20:00", "2019-01-01 00:30:00"),
]


def create_inputs(
    events: Iterable[tuple[str, str]],
    *,
    output_directory: str | Path = "results",
    probe: int = 1,
    mode: str = "auto",
    plot: bool = True,
) -> list[Path]:
    """Create one PARAM file for every ``(start, end)`` event.

    Parameters
    ----------
    events
        Iterable of UTC MMS interval pairs.
    output_directory
        Directory for generated PARAM files and optional MMS plots.
    probe
        MMS spacecraft number passed to :func:`create_swmf_input`.
    mode
        MMS data mode: ``auto``, ``brst``, or ``fast``.
    plot
        Whether to save the interval MMS quick-look plot.

    Returns
    -------
    list[pathlib.Path]
        Paths of the generated PARAM files, in event order.
    """

    destination = Path(output_directory)
    destination.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for start, end in events:
        start_tag = start.replace("-", "").replace(":", "").replace(" ", "_")
        end_tag = end.replace("-", "").replace(":", "").replace(" ", "_")
        output = destination / f"PARAM_{start_tag}_{end_tag}.in"
        path = create_swmf_input(
            start,
            end,
            output=output,
            probe=probe,
            mode=mode,
            plot=plot,
        )
        print(f"Created {path} for {start} to {end}")
        outputs.append(path)
    return outputs


if __name__ == "__main__":
    create_inputs(EVENTS)
