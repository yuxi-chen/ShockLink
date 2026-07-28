from importlib.metadata import version

import shocklink


def test_package_exposes_installed_version() -> None:
    assert shocklink.__version__ == version("shocklink")


def test_import_does_not_load_paraview() -> None:
    import sys

    assert "paraview" not in sys.modules
