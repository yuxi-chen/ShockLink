"""TOML configuration for ShockLink analyses."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shocklink.exceptions import ConfigurationError


@dataclass(frozen=True, slots=True)
class DatasetConfig:
    """Simulation dataset inputs."""

    path: Path
    magnetic_field: str
    coordinate_system: str

    def __post_init__(self) -> None:
        if not self.magnetic_field.strip():
            raise ValueError("dataset.magnetic_field must not be empty")
        if not self.coordinate_system.strip():
            raise ValueError("dataset.coordinate_system must not be empty")


@dataclass(frozen=True, slots=True)
class BowShockConfig:
    """Bow-shock surface input."""

    surface: Path


@dataclass(frozen=True, slots=True)
class AnalysisOptions:
    """Numerical options shared by connectivity analyses."""

    tolerance: float

    def __post_init__(self) -> None:
        if self.tolerance <= 0:
            raise ValueError("analysis.tolerance must be positive")


@dataclass(frozen=True, slots=True)
class ShockLinkConfig:
    """Complete supported ShockLink configuration."""

    dataset: DatasetConfig
    bow_shock: BowShockConfig
    analysis: AnalysisOptions


def _table(data: dict[str, Any], name: str) -> dict[str, Any]:
    value = data.get(name)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Missing or invalid [{name}] table")
    return value


def _required(table: dict[str, Any], table_name: str, key: str) -> Any:
    try:
        return table[key]
    except KeyError as error:
        raise ConfigurationError(f"Missing required key: {table_name}.{key}") from error


def load_config(path: str | Path) -> ShockLinkConfig:
    """Load and validate a ShockLink TOML configuration."""

    config_path = Path(path)
    try:
        with config_path.open("rb") as stream:
            raw = tomllib.load(stream)
    except FileNotFoundError as error:
        raise ConfigurationError(
            f"Configuration file does not exist: {config_path}"
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigurationError(f"Invalid TOML in {config_path}: {error}") from error

    dataset = _table(raw, "dataset")
    bow_shock = _table(raw, "bow_shock")
    analysis = _table(raw, "analysis")

    try:
        return ShockLinkConfig(
            dataset=DatasetConfig(
                path=Path(_required(dataset, "dataset", "path")),
                magnetic_field=str(
                    _required(dataset, "dataset", "magnetic_field")
                ),
                coordinate_system=str(
                    _required(dataset, "dataset", "coordinate_system")
                ),
            ),
            bow_shock=BowShockConfig(
                surface=Path(_required(bow_shock, "bow_shock", "surface"))
            ),
            analysis=AnalysisOptions(
                tolerance=float(_required(analysis, "analysis", "tolerance"))
            ),
        )
    except ConfigurationError:
        raise
    except (TypeError, ValueError) as error:
        raise ConfigurationError(f"Invalid configuration: {error}") from error
