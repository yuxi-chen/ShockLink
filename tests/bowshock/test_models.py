import numpy as np
import pytest

from shocklink.bowshock import BowShockParaboloid, BowShockSurface
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


def test_bow_shock_paraboloid_stores_fit_and_evaluates_surface() -> None:
    fit = BowShockParaboloid(
        loc0=(10.0, 0.0, 0.0),
        loc1=(8.0, -2.0, 0.0),
        loc2=(8.0, 2.0, 0.0),
        curvature=0.5,
    )

    np.testing.assert_allclose(fit.loc0, (10.0, 0.0, 0.0))
    np.testing.assert_allclose(fit.loc1, (8.0, -2.0, 0.0))
    np.testing.assert_allclose(fit.loc2, (8.0, 2.0, 0.0))
    assert not fit.loc0.flags.writeable
    assert not fit.loc1.flags.writeable
    assert not fit.loc2.flags.writeable
    assert fit.x_at(2.0, 0.0) == pytest.approx(8.0)
    assert fit.residual_at(8.0, 2.0, 0.0) == pytest.approx(0.0)
    assert fit.residual_at(9.0, 2.0, 0.0) == pytest.approx(1.0)
    np.testing.assert_allclose(
        fit.residual_at(
            np.array([8.0, 9.0]),
            np.array([2.0, 2.0]),
            0.0,
        ),
        [0.0, 1.0],
    )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"loc0": (10.0, 0.0)}, "exactly three"),
        ({"loc1": (8.0, np.nan, 0.0)}, "finite"),
        ({"loc0": (10.0, 1.0, 0.0)}, "X axis"),
        ({"loc1": (8.0, 2.0, 0.0)}, "negative Y"),
        ({"loc2": (8.0, -2.0, 0.0)}, "positive Y"),
        ({"curvature": 0.0}, "positive"),
        ({"curvature": np.inf}, "finite"),
    ],
)
def test_bow_shock_paraboloid_rejects_invalid_geometry(
    changes: dict[str, object],
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "loc0": (10.0, 0.0, 0.0),
        "loc1": (8.0, -2.0, 0.0),
        "loc2": (8.0, 2.0, 0.0),
        "curvature": 0.5,
    }
    arguments.update(changes)

    with pytest.raises(GeometryError, match=message):
        BowShockParaboloid(**arguments)
