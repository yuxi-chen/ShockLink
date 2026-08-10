"""Load and normalize simulation datasets from DAT and VTM files."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pyvista as pv
from numpy.typing import NDArray

from shocklink.exceptions import DatasetError
from shocklink.utilities import parse_datetime

TIME_EVENT_KEY = "time_event"

COORDINATE_COMPONENT_CANDIDATES = (
    ("X [R]", "Y [R]", "Z [R]"),
    ("X", "Y", "Z"),
)
MAGNETIC_COMPONENT_CANDIDATES = (
    ("B_x [nT]", "B_y [nT]", "B_z [nT]"),
    ("B_x", "B_y", "B_z"),
)
VELOCITY_COMPONENT_CANDIDATES = (
    ("U_x [km_s]", "U_y [km_s]", "U_z [km_s]"),
    ("U_x [km/s]", "U_y [km/s]", "U_z [km/s]"),
    ("U_x", "U_y", "U_z"),
)

_TITLE_TIMESTAMP_PATTERN = re.compile(
    r"^\s*TITLE\s*=.*,(?P<timestamp>\d{4}/\d{2}/\d{2}\s+"
    r'\d{2}:\d{2}:\d{2}(?:\.\d+)?)"\s*$',
    re.IGNORECASE,
)


def _read_dat_time(source: Path) -> str:
    """Return a DAT header event time as an ISO-8601 UTC string."""

    try:
        with source.open(encoding="utf-8") as stream:
            for line in stream:
                stripped = line.lstrip()
                if stripped.upper().startswith("ZONE"):
                    break
                if not stripped.upper().startswith("TITLE"):
                    continue

                match = _TITLE_TIMESTAMP_PATTERN.match(line)
                if match is None:
                    break
                raw_time = match.group("timestamp")
                try:
                    parsed = parse_datetime(raw_time.replace("/", "-"))
                except ValueError as error:
                    raise DatasetError(
                        f"Invalid DAT event timestamp in {source}: {raw_time}"
                    ) from error
                return parsed.isoformat(timespec="milliseconds")
    except (OSError, UnicodeError) as error:
        raise DatasetError(f"Could not read DAT header {source}: {error}") from error

    raise DatasetError(
        f"DAT header in {source} does not contain a simulation event timestamp"
    )


def _read_vtm_time(data: pv.MultiBlock, *, source: Path) -> str:
    """Return and normalize the VTM root event time."""

    if TIME_EVENT_KEY not in data.field_data:
        raise DatasetError(
            f"VTM file {source} lacks root field_data[{TIME_EVENT_KEY!r}]"
        )
    values = np.asarray(data.field_data[TIME_EVENT_KEY]).reshape(-1)
    if values.size != 1:
        raise DatasetError(
            f"VTM file {source} must contain exactly one {TIME_EVENT_KEY!r} value"
        )
    raw_time = str(values[0])
    try:
        parsed = parse_datetime(raw_time)
    except ValueError as error:
        raise DatasetError(
            f"Invalid VTM {TIME_EVENT_KEY} in {source}: {raw_time}"
        ) from error
    return parsed.isoformat(timespec="milliseconds")


def _components(
    grid: pv.DataSet,
    names: tuple[str, str, str],
    *,
    label: str,
) -> NDArray[np.number]:
    """Return three scalar point arrays as one vector matrix."""

    missing = [name for name in names if name not in grid.point_data]
    if missing:
        raise DatasetError(f"Missing {label} component array(s): {', '.join(missing)}")

    arrays = [np.asarray(grid.point_data[name]) for name in names]
    invalid = [
        name
        for name, values in zip(names, arrays, strict=True)
        if values.ndim != 1 or len(values) != grid.n_points
    ]
    if invalid:
        raise DatasetError(
            f"Invalid {label} component length or shape: {', '.join(invalid)}"
        )
    return np.column_stack(arrays)


def _resolve_components(
    grid: pv.DataSet,
    requested: tuple[str, str, str] | None,
    candidates: tuple[tuple[str, str, str], ...],
    *,
    label: str,
) -> NDArray[np.number]:
    if requested is not None:
        return _components(grid, requested, label=label)

    for names in candidates:
        if all(name in grid.point_data for name in names):
            return _components(grid, names, label=label)

    expected = "; ".join(", ".join(names) for names in candidates)
    raise DatasetError(
        f"Missing {label} component array(s); expected one of: {expected}"
    )


def _normalize_dataset(
    grid: pv.DataSet,
    *,
    source: Path,
    time_event: str,
    coordinate_components: tuple[str, str, str] | None,
    magnetic_components: tuple[str, str, str] | None,
    velocity_components: tuple[str, str, str] | None,
    magnetic_name: str,
    velocity_name: str,
) -> pv.DataSet:
    if coordinate_components is not None or any(
        all(name in grid.point_data for name in names)
        for names in COORDINATE_COMPONENT_CANDIDATES
    ):
        coordinates = _resolve_components(
            grid,
            coordinate_components,
            COORDINATE_COMPONENT_CANDIDATES,
            label="coordinate",
        )
        if not np.isfinite(coordinates).all():
            raise DatasetError(
                f"Coordinate arrays in {source} must contain finite values"
            )
        grid.points = coordinates
    elif not np.isfinite(np.asarray(grid.points)).all():
        raise DatasetError(f"Coordinates in {source} must contain finite values")

    magnetic_field = _resolve_components(
        grid,
        magnetic_components,
        MAGNETIC_COMPONENT_CANDIDATES,
        label="magnetic-field",
    )
    velocity = _resolve_components(
        grid,
        velocity_components,
        VELOCITY_COMPONENT_CANDIDATES,
        label="velocity",
    )
    grid.point_data[magnetic_name] = magnetic_field
    grid.point_data[velocity_name] = velocity
    grid.field_data[TIME_EVENT_KEY] = time_event
    return grid


def _dataset_leaves(
    data: pv.MultiBlock,
    *,
    source: Path,
    block_path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], pv.DataSet]]:
    """Collect nonempty dataset leaves without rebuilding the containers."""

    leaves: list[tuple[tuple[str, ...], pv.DataSet]] = []
    for index in range(data.n_blocks):
        block = data[index]
        name = data.get_block_name(index) or str(index)
        current_path = (*block_path, name)
        if block is None:
            continue
        if isinstance(block, pv.MultiBlock):
            leaves.extend(
                _dataset_leaves(
                    block,
                    source=source,
                    block_path=current_path,
                )
            )
            continue
        if not isinstance(block, pv.DataSet):
            location = "/".join(current_path)
            raise DatasetError(
                f"Unsupported non-dataset block {location!r} in {source}: "
                f"{type(block).__name__}"
            )
        if block.n_points > 0 or block.n_cells > 0:
            leaves.append((current_path, block))
    return leaves


def load_simulation(
    path: str | Path,
    *,
    coordinate_components: tuple[str, str, str] | None = None,
    magnetic_components: tuple[str, str, str] | None = None,
    velocity_components: tuple[str, str, str] | None = None,
    magnetic_name: str = "B [nT]",
    velocity_name: str = "U [km/s]",
) -> pv.DataSet | pv.MultiBlock:
    """Load and normalize a DAT or VTM simulation dataset.

    Parameters
    ----------
    path : str or pathlib.Path
        Existing `.dat` or `.vtm` simulation file, or a directory containing
        a `.vtm` file. When a directory contains multiple `.vtm` files, the
        lexicographically first filename is selected.
    coordinate_components, magnetic_components, velocity_components : tuple of str, optional
        Explicit scalar component names. When omitted, both unit-bearing and
        converter-cleaned names are detected automatically.
    magnetic_name, velocity_name : str
        Names assigned to the normalized vector point-data arrays.

    Returns
    -------
    pyvista.DataSet or pyvista.MultiBlock
        One normalized dataset for a single nonempty zone, or the original
        multiblock hierarchy when multiple zones are present.

    Raises
    ------
    DatasetError
        If the input, metadata, topology, coordinates, or required vector
        components are invalid.
    """

    source = Path(path)
    if source.is_dir():
        candidates = sorted(
            (
                candidate
                for candidate in source.iterdir()
                if candidate.is_file() and candidate.suffix.lower() == ".vtm"
            ),
            key=lambda candidate: candidate.name.lower(),
        )
        if not candidates:
            raise DatasetError(f"Simulation directory contains no .vtm file: {source}")
        source = candidates[0]
    if not source.is_file():
        raise DatasetError(f"Simulation file does not exist: {source}")
    suffix = source.suffix.lower()
    if suffix not in {".dat", ".vtm"}:
        raise DatasetError(
            f"Simulation input must use the .dat or .vtm extension: {source}"
        )
    time_event = _read_dat_time(source) if suffix == ".dat" else None

    try:
        loaded = pv.read(source)
    except Exception as error:
        raise DatasetError(
            f"Could not read simulation file {source}: {error}"
        ) from error
    if not isinstance(loaded, pv.MultiBlock):
        raise DatasetError(
            f"Simulation reader returned {type(loaded).__name__} for {source}; "
            "expected MultiBlock"
        )

    if suffix == ".vtm":
        time_event = _read_vtm_time(loaded, source=source)
    assert time_event is not None
    loaded.field_data[TIME_EVENT_KEY] = time_event
    leaves = _dataset_leaves(loaded, source=source)
    if not leaves:
        raise DatasetError(f"Simulation file {source} has no nonempty dataset zones")

    for block_path, grid in leaves:
        try:
            _normalize_dataset(
                grid,
                source=source,
                time_event=time_event,
                coordinate_components=coordinate_components,
                magnetic_components=magnetic_components,
                velocity_components=velocity_components,
                magnetic_name=magnetic_name,
                velocity_name=velocity_name,
            )
        except DatasetError as error:
            location = "/".join(block_path)
            raise DatasetError(f"{source} block {location}: {error}") from error

    if len(leaves) == 1:
        return leaves[0][1]
    return loaded


__all__ = ["TIME_EVENT_KEY", "load_simulation"]
