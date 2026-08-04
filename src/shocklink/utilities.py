"""Small shared utilities for ShockLink workflows."""

from __future__ import annotations

from datetime import UTC, datetime


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
