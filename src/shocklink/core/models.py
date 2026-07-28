"""Backend-independent metadata models."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class CoordinateSystem:
    """Name and length unit used by a simulation dataset."""

    name: str
    length_unit: str

    def __post_init__(self) -> None:
        name = self.name.strip().upper()
        length_unit = self.length_unit.strip()
        if not name:
            raise ValueError("coordinate-system name must not be empty")
        if not length_unit:
            raise ValueError("length_unit must not be empty")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "length_unit", length_unit)


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    """Metadata needed to interpret magnetic-vector data."""

    magnetic_field: str
    coordinates: CoordinateSystem
    source: Path | None = None

    def __post_init__(self) -> None:
        magnetic_field = self.magnetic_field.strip()
        if not magnetic_field:
            raise ValueError("magnetic_field must not be empty")
        object.__setattr__(self, "magnetic_field", magnetic_field)
