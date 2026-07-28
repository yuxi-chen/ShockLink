import numpy as np
import pytest

from shocklink.exceptions import GeometryError
from shocklink.fieldlines import FieldLine, SeedPoint


def test_seed_point_requires_three_finite_coordinates() -> None:
    with pytest.raises(GeometryError, match="three"):
        SeedPoint(identifier="seed-1", position=[1.0, 2.0])


def test_field_line_stores_read_only_xyz_points() -> None:
    line = FieldLine(
        identifier="line-1",
        points=[[0.0, 0.0, 0.0], [1.0, 2.0, 3.0]],
        seed_id="seed-1",
    )

    assert line.points.shape == (2, 3)
    assert not line.points.flags.writeable
    np.testing.assert_allclose(line.points[-1], [1.0, 2.0, 3.0])


@pytest.mark.parametrize(
    ("points", "message"),
    [
        ([[0.0, 0.0, 0.0]], "at least two"),
        ([[0.0, 0.0], [1.0, 1.0]], "N x 3"),
        ([[0.0, 0.0, 0.0], [1.0, np.inf, 3.0]], "finite"),
    ],
)
def test_field_line_rejects_invalid_geometry(
    points: list[list[float]], message: str
) -> None:
    with pytest.raises(GeometryError, match=message):
        FieldLine(identifier="line-1", points=points)
