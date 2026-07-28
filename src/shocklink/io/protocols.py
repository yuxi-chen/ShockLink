"""Structural interfaces implemented by simulation-data backends."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from numpy.typing import NDArray

from shocklink.bowshock import BowShockSurface
from shocklink.core import DatasetMetadata
from shocklink.fieldlines import FieldLine, SeedPoint


@runtime_checkable
class SimulationDataset(Protocol):
    """Minimum interface exposed by a loaded MHD simulation."""

    @property
    def metadata(self) -> DatasetMetadata:
        """Return the dataset's scientific metadata."""

    @property
    def points(self) -> NDArray:
        """Return dataset coordinates as an N x 3 array."""

    def vector_array(self, name: str) -> NDArray:
        """Return a named point-centered vector array."""


@runtime_checkable
class FieldLineTracer(Protocol):
    """Trace magnetic field lines through a loaded dataset."""

    def trace(
        self,
        dataset: SimulationDataset,
        seeds: Sequence[SeedPoint],
    ) -> Sequence[FieldLine]:
        """Trace and return one or more field lines."""


@runtime_checkable
class BowShockDetector(Protocol):
    """Find or load a bow-shock surface for a dataset."""

    def detect(self, dataset: SimulationDataset) -> BowShockSurface:
        """Return the detected bow-shock surface."""
