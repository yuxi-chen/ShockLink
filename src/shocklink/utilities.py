"""Small shared utilities for ShockLink workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np

from shocklink.constants import EV_TO_K


def parse_datetime(value: str) -> datetime:
    """Parse an ISO-like timestamp and return it normalized to UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"invalid timestamp {value!r}; use ISO format") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def midpoint_datetime(start: datetime, end: datetime) -> datetime:
    """Return the midpoint of two ordered datetimes."""
    if start > end:
        raise ValueError("start time must not be after end time")
    return start + (end - start) / 2


@dataclass(frozen=True)
class TimeBounds:
    """Inclusive UTC bounds with common numeric representations."""

    start: datetime
    end: datetime

    @classmethod
    def from_strings(cls, start: str, end: str) -> "TimeBounds":
        parsed = cls(parse_datetime(start), parse_datetime(end))
        if parsed.start > parsed.end:
            raise ValueError("start time must not be after end time")
        return parsed

    @property
    def unix(self) -> tuple[float, float]:
        return self.start.timestamp(), self.end.timestamp()

    @property
    def numpy(self) -> tuple[np.datetime64, np.datetime64]:
        return (
            np.datetime64(self.start.replace(tzinfo=None)),
            np.datetime64(self.end.replace(tzinfo=None)),
        )


def ev_to_kelvin(values: object) -> np.ndarray:
    """Convert electron-volts to Kelvin."""
    return np.asarray(values) * EV_TO_K


def kelvin_to_ev(values: object) -> np.ndarray:
    """Convert Kelvin to electron-volts."""
    return np.asarray(values) / EV_TO_K
