import numpy as np
import pytest

from shocklink.bowshock import BowShockSurface
from shocklink.exceptions import GeometryError


def test_bow_shock_surface_stores_triangles_as_read_only_arrays() -> None:
    surface = BowShockSurface(
        vertices=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]],
        faces=[[0, 1, 2]],
    )

    assert surface.vertices.shape == (3, 3)
    assert surface.faces.shape == (1, 3)
    assert not surface.vertices.flags.writeable
    assert not surface.faces.flags.writeable


def test_bow_shock_surface_rejects_non_triangular_faces() -> None:
    with pytest.raises(GeometryError, match="M x 3"):
        BowShockSurface(
            vertices=np.eye(3),
            faces=[[0, 1, 2, 0]],
        )


def test_bow_shock_surface_rejects_out_of_range_indices() -> None:
    with pytest.raises(GeometryError, match="vertex index"):
        BowShockSurface(
            vertices=np.eye(3),
            faces=[[0, 1, 3]],
        )
