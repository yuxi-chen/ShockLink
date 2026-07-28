"""Backend-independent field-line geometry."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from shocklink.exceptions import GeometryError


def _point(value: ArrayLike, *, label: str) -> NDArray[np.float64]:
    point = np.array(value, dtype=np.float64, copy=True)
    if point.shape != (3,):
        raise GeometryError(f"{label} must contain exactly three coordinates")
    if not np.isfinite(point).all():
        raise GeometryError(f"{label} coordinates must be finite")
    point.setflags(write=False)
    return point


@dataclass(frozen=True, slots=True)
class SeedPoint:
    """A named starting position for field-line tracing."""

    identifier: str
    position: ArrayLike

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("seed identifier must not be empty")
        object.__setattr__(self, "position", _point(self.position, label="position"))


@dataclass(frozen=True, slots=True)
class FieldLine:
    """An ordered magnetic field-line polyline."""

    identifier: str
    points: ArrayLike
    seed_id: str | None = None

    def __post_init__(self) -> None:
        if not self.identifier.strip():
            raise ValueError("field-line identifier must not be empty")
        points = np.array(self.points, dtype=np.float64, copy=True)
        if points.ndim != 2 or points.shape[1:] != (3,):
            raise GeometryError("field-line points must be an N x 3 array")
        if len(points) < 2:
            raise GeometryError("a field line requires at least two points")
        if not np.isfinite(points).all():
            raise GeometryError("field-line points must be finite")
        points.setflags(write=False)
        object.__setattr__(self, "points", points)


__all__ = ["FieldLine", "SeedPoint"]
