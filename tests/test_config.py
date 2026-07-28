from pathlib import Path

import pytest

from shocklink.config import load_config
from shocklink.exceptions import ConfigurationError


def _write_config(path: Path, *, tolerance: str = "0.01") -> None:
    path.write_text(
        f"""
[dataset]
path = "run/output.vtu"
magnetic_field = "B"
coordinate_system = "GSM"

[bow_shock]
surface = "run/bow_shock.vtp"

[analysis]
tolerance = {tolerance}
""".strip()
    )


def test_load_config_reads_required_analysis_fields(tmp_path: Path) -> None:
    path = tmp_path / "analysis.toml"
    _write_config(path)

    config = load_config(path)

    assert config.dataset.path == Path("run/output.vtu")
    assert config.dataset.magnetic_field == "B"
    assert config.dataset.coordinate_system == "GSM"
    assert config.bow_shock.surface == Path("run/bow_shock.vtp")
    assert config.analysis.tolerance == pytest.approx(0.01)


def test_load_config_rejects_nonpositive_tolerance(tmp_path: Path) -> None:
    path = tmp_path / "analysis.toml"
    _write_config(path, tolerance="0.0")

    with pytest.raises(ConfigurationError, match="tolerance"):
        load_config(path)


def test_load_config_wraps_missing_file() -> None:
    with pytest.raises(ConfigurationError, match="does not exist"):
        load_config("missing.toml")


def test_load_config_wraps_invalid_toml(tmp_path: Path) -> None:
    path = tmp_path / "analysis.toml"
    path.write_text("[dataset\n")

    with pytest.raises(ConfigurationError, match="Invalid TOML"):
        load_config(path)


def test_load_config_reports_missing_required_key(tmp_path: Path) -> None:
    path = tmp_path / "analysis.toml"
    path.write_text(
        """
[dataset]
path = "run/output.vtu"

[bow_shock]
surface = "run/bow_shock.vtp"

[analysis]
tolerance = 0.01
""".strip()
    )

    with pytest.raises(ConfigurationError, match="magnetic_field"):
        load_config(path)
