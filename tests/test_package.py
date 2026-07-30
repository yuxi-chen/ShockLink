from importlib.metadata import version
from pathlib import Path
import tomllib

import shocklink


def test_package_exposes_installed_version() -> None:
    assert shocklink.__version__ == version("shocklink")


def test_import_does_not_load_paraview() -> None:
    import sys

    assert "paraview" not in sys.modules


def test_mms_extra_declares_analysis_dependencies() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    dependencies = pyproject["project"]["optional-dependencies"]["mms"]

    assert any(dependency.startswith("pyspedas") for dependency in dependencies)
    assert any(dependency.startswith("matplotlib") for dependency in dependencies)
