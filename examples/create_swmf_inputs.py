#!/usr/bin/env python

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

# Each event is an MMS observation interval: (UTC start, UTC end).
EVENTS = [
    ("2023-12-16 08:30:00", "2023-12-16 11:00:00"),
    ("2017-12-07 07:54:00", "2017-12-07 08:06:00"),
    ("2025-03-02 15:50:00", "2025-03-02 16:10:00"),
]


def _configure_dependency_directories(cache_directory: Path) -> None:
    """Give plotting and MMS dependencies writable, headless-safe defaults."""

    cache = cache_directory.resolve()
    defaults = {
        "MPLBACKEND": "Agg",
        "MPLCONFIGDIR": str(cache / "matplotlib"),
        "SPACEPY": str(cache / "spacepy"),
        "SPEDAS_DATA_DIR": str(cache / "spedas"),
    }
    for name, value in defaults.items():
        os.environ.setdefault(name, value)


def create_inputs(
    events: Iterable[tuple[str, str]],
    *,
    output_directory: str | Path = "results",
    cache_directory: str | Path | None = None,
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
    cache_directory
        Writable directory for SpacePy, pySPEDAS, and Matplotlib state. By
        default, use ``<output_directory>/.cache``. Existing environment
        variable settings take precedence.
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
    dependency_cache = (
        destination / ".cache" if cache_directory is None else Path(cache_directory)
    )
    _configure_dependency_directories(dependency_cache)

    # pySPEDAS imports SpacePy, which initializes its configuration at import
    # time. Import only after writable dependency directories are configured.
    from shocklink.mms_swmf import create_swmf_input

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
