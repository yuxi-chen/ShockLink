"""Triangulated bow-shock geometry."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

from shocklink.exceptions import GeometryError


@dataclass(frozen=True, slots=True)
class BowShockSurface:
    """A named triangular surface representing a bow shock."""

    vertices: ArrayLike
    faces: ArrayLike
    name: str = "bow_shock"

    def __post_init__(self) -> None:
        vertices = np.array(self.vertices, dtype=np.float64, copy=True)
        raw_faces = np.asarray(self.faces)

        if vertices.ndim != 2 or vertices.shape[1:] != (3,):
            raise GeometryError("surface vertices must be an N x 3 array")
        if len(vertices) < 3:
            raise GeometryError("a surface requires at least three vertices")
        if not np.isfinite(vertices).all():
            raise GeometryError("surface vertices must be finite")
        if raw_faces.ndim != 2 or raw_faces.shape[1:] != (3,):
            raise GeometryError("surface faces must be an M x 3 array")
        if not np.issubdtype(raw_faces.dtype, np.integer):
            raise GeometryError("surface faces must contain integer vertex indices")

        faces = np.array(raw_faces, dtype=np.int64, copy=True)
        if faces.size and (faces.min() < 0 or faces.max() >= len(vertices)):
            raise GeometryError("surface face contains an invalid vertex index")
        if not self.name.strip():
            raise ValueError("surface name must not be empty")

        vertices.setflags(write=False)
        faces.setflags(write=False)
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "faces", faces)
