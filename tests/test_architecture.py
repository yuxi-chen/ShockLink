from __future__ import annotations

import ast
from importlib.metadata import version
from pathlib import Path
import subprocess
import sys
import tomllib

import shocklink
import shocklink.io as simulation_io
from shocklink.constants import CARTESIAN_COMPONENTS, EARTH_RADIUS_KM, EV_TO_K


ROOT = Path(__file__).resolve().parents[1]


def test_package_metadata_and_mms_dependencies_are_declared() -> None:
    assert shocklink.__version__ == version("shocklink")
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["readme"] == "README.md"
    assert metadata["project"]["urls"]["Documentation"].endswith("docs/algorithms.md")
    assert any(dependency.startswith("pyspedas") for dependency in metadata["project"]["dependencies"])
    assert "matplotlib>=3.8" in metadata["project"]["dependencies"]
    assert "mms" not in metadata["project"]["optional-dependencies"]


def test_import_does_not_load_optional_paraview() -> None:
    assert "paraview" not in sys.modules


def test_shared_constants_are_centralized() -> None:
    assert CARTESIAN_COMPONENTS == ("x", "y", "z")
    assert EARTH_RADIUS_KM == 6371.2
    assert EV_TO_K == 11604.51812

    names = {"CARTESIAN_COMPONENTS", "EARTH_RADIUS_KM", "EV_TO_K"}
    definitions: dict[str, list[str]] = {name: [] for name in names}
    for path in (ROOT / "src/shocklink").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in definitions:
                        definitions[target.id].append(path.name)
    assert definitions == {name: ["constants.py"] for name in names}


def test_module_boundaries_keep_optional_workflows_lazy() -> None:
    from shocklink import dataset

    assert callable(dataset.get_2d_cut)
    assert callable(dataset.plot_2d_cut)
    assert simulation_io.__all__ == ["TIME_EVENT_KEY", "load_simulation"]
    assert callable(simulation_io.load_simulation)

    for module in ("data.py", "loading.py", "analysis.py", "plotting.py", "cli.py"):
        tree = ast.parse((ROOT / "src/shocklink/mms" / module).read_text())
        imported = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert "shocklink.mms" not in imported

    tree = ast.parse((ROOT / "src/shocklink/swmf.py").read_text())
    imported_modules = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "shocklink.mms" not in imported_modules
    assert "shocklink.mms_swmf" not in imported_modules
    assert {"load_mms_data", "average_plotted_values"}.isdisjoint(imported_names)


def test_connectivity_import_has_no_mms_plotting_side_effects() -> None:
    probe = (
        "import sys; import shocklink.connectivity; "
        "print(','.join(name for name in ('shocklink.mms','pytplot','pyspedas','matplotlib') "
        "if name in sys.modules))"
    )
    result = subprocess.run([sys.executable, "-c", probe], check=True, capture_output=True, text=True)
    assert result.stdout.strip() == ""
