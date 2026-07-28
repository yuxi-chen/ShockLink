"""Connectivity classification and intersection records."""

from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import ArrayLike

from shocklink.exceptions import GeometryError


class ConnectivityStatus(str, Enum):
    """Supported field-line connectivity classifications."""

    CONNECTED = "connected"
    NOT_CONNECTED = "not_connected"
    AMBIGUOUS = "ambiguous"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class Intersection:
    """A field-line intersection with a bow-shock surface."""

    position: ArrayLike
    path_distance: float
    surface_cell: int | None = None

    def __post_init__(self) -> None:
        position = np.array(self.position, dtype=np.float64, copy=True)
        if position.shape != (3,):
            raise GeometryError(
                "intersection position must contain exactly three coordinates"
            )
        if not np.isfinite(position).all():
            raise GeometryError("intersection position must be finite")
        if not np.isfinite(self.path_distance) or self.path_distance < 0:
            raise GeometryError("intersection path_distance must be nonnegative")
        if self.surface_cell is not None and self.surface_cell < 0:
            raise GeometryError("intersection surface_cell must be nonnegative")
        position.setflags(write=False)
        object.__setattr__(self, "position", position)


@dataclass(frozen=True, slots=True)
class ConnectivityResult:
    """Connectivity classification for one traced field line."""

    field_line_id: str
    status: ConnectivityStatus
    intersections: tuple[Intersection, ...] = ()
    message: str | None = None

    def __post_init__(self) -> None:
        if not self.field_line_id.strip():
            raise ValueError("field_line_id must not be empty")
        intersections = tuple(self.intersections)
        if self.status is ConnectivityStatus.CONNECTED and not intersections:
            raise ValueError("connected result requires at least one intersection")
        object.__setattr__(self, "intersections", intersections)
