"""Backward-compatible facade for the generic simulation loader."""

from __future__ import annotations

from pathlib import Path

import pyvista as pv

from shocklink.io import TIME_EVENT_KEY, load_simulation

DEFAULT_COORDINATE_COMPONENTS = ("X [R]", "Y [R]", "Z [R]")
DEFAULT_MAGNETIC_COMPONENTS = ("B_x [nT]", "B_y [nT]", "B_z [nT]")
DEFAULT_VELOCITY_COMPONENTS = ("U_x [km_s]", "U_y [km_s]", "U_z [km_s]")


def read_tecplot(
    path: str | Path,
    *,
    coordinate_components: tuple[str, str, str] | None = None,
    magnetic_components: tuple[str, str, str] | None = None,
    velocity_components: tuple[str, str, str] | None = None,
    magnetic_name: str = "B [nT]",
    velocity_name: str = "U [km/s]",
) -> pv.DataSet | pv.MultiBlock:
    """Load a DAT or VTM file through :func:`shocklink.io.load_simulation`.

    New code should import ``load_simulation`` from ``shocklink.io`` directly.
    This wrapper remains for callers using the original function name.
    """

    return load_simulation(
        path,
        coordinate_components=coordinate_components,
        magnetic_components=magnetic_components,
        velocity_components=velocity_components,
        magnetic_name=magnetic_name,
        velocity_name=velocity_name,
    )


__all__ = ["TIME_EVENT_KEY", "read_tecplot"]
