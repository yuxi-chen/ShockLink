import pytest

from shocklink.connectivity import (
    ConnectivityResult,
    ConnectivityStatus,
    Intersection,
)
from shocklink.exceptions import GeometryError


def test_connectivity_status_values_are_stable_strings() -> None:
    assert {status.value for status in ConnectivityStatus} == {
        "connected",
        "not_connected",
        "ambiguous",
        "incomplete",
    }


def test_connected_result_requires_intersection() -> None:
    with pytest.raises(ValueError, match="intersection"):
        ConnectivityResult(
            field_line_id="line-1",
            status=ConnectivityStatus.CONNECTED,
        )


def test_connected_result_preserves_intersections() -> None:
    intersection = Intersection(position=[1.0, 2.0, 3.0], path_distance=4.5)

    result = ConnectivityResult(
        field_line_id="line-1",
        status=ConnectivityStatus.CONNECTED,
        intersections=[intersection],
    )

    assert result.intersections == (intersection,)
    assert not intersection.position.flags.writeable


def test_intersection_rejects_negative_path_distance() -> None:
    with pytest.raises(GeometryError, match="path_distance"):
        Intersection(position=[1.0, 2.0, 3.0], path_distance=-0.1)
