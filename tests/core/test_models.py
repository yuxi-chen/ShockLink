import pytest

from shocklink.core import CoordinateSystem, DatasetMetadata


def test_coordinate_system_rejects_empty_units() -> None:
    with pytest.raises(ValueError, match="length_unit"):
        CoordinateSystem(name="GSM", length_unit="")


def test_coordinate_system_normalizes_name() -> None:
    coordinates = CoordinateSystem(name=" gsm ", length_unit="R_E")

    assert coordinates.name == "GSM"


def test_dataset_metadata_rejects_empty_magnetic_field_name() -> None:
    with pytest.raises(ValueError, match="magnetic_field"):
        DatasetMetadata(
            magnetic_field=" ",
            coordinates=CoordinateSystem(name="GSM", length_unit="R_E"),
        )
