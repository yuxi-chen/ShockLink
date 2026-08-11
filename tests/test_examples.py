from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path
import subprocess

import nbformat
import pytest

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.io import load_simulation


ROOT = Path(__file__).resolve().parents[1]
ALGORITHMS = ROOT / "docs/algorithms.md"
WORKFLOW_EXAMPLE = ROOT / "examples/bow_shock_workflow.py"

PUBLIC_WORKFLOW_API = (
    load_simulation,
    calc_velocity_divergence,
    fit_bow_shock,
    extract_shockfit_range,
    get_bow_shock_surface,
    calc_bow_shock_normals,
)


@pytest.mark.parametrize("function", PUBLIC_WORKFLOW_API)
def test_public_workflow_docstrings_have_numpy_sections(function: object) -> None:
    docstring = inspect.getdoc(function)
    assert docstring is not None
    for section in ("Parameters", "Returns", "Raises"):
        assert f"{section}\n{'-' * len(section)}" in docstring


def test_algorithm_guide_covers_the_public_pipeline() -> None:
    text = ALGORITHMS.read_text()
    for required in (
        "calc_velocity_divergence",
        "fit_bow_shock",
        "extract_shockfit_range",
        "get_bow_shock_surface",
        "calc_bow_shock_normals",
        "shockfit = x - x_fit",
        "surface_x[i, j]",
        "(1, -∂x_s/∂y, -∂x_s/∂z)",
        "theta_Bn",
        "Möller--Trumbore",
        "GSM",
        "R_E",
    ):
        assert required in text
    assert "../src/shocklink/bowshock.py" in text
    assert "../src/shocklink/connectivity.py" in text


def test_readmes_link_the_consolidated_guide_and_examples() -> None:
    readme = (ROOT / "README.md").read_text()
    examples = (ROOT / "examples/README.md").read_text()
    assert "docs/algorithms.md" in readme
    assert "../docs/algorithms.md" in examples
    assert "examples/bow_shock_workflow.py" in readme
    assert "tools/mms_bow_shock_connection.py" in readme
    assert "tools/create_swmf_input.py" in readme
    assert ALGORITHMS.is_file()


def test_workflow_example_compiles_and_uses_public_api() -> None:
    source = WORKFLOW_EXAMPLE.read_text()
    compile(source, str(WORKFLOW_EXAMPLE), "exec")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("shocklink.")
        for alias in node.names
    }
    assert set(name.__name__ for name in PUBLIC_WORKFLOW_API) <= imports
    assert "finite_surface_values:" in source


def _assert_clean_notebook(path: Path) -> str:
    notebook = nbformat.read(path, as_version=4)
    nbformat.validate(notebook)
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    ast.parse(code, str(path))
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is None
            assert cell.outputs == []
    assert "/Users/" not in "\n".join(cell.source for cell in notebook.cells)
    return code


@pytest.mark.parametrize(
    "name",
    ("extract_shock.ipynb", "mms_example.ipynb", "shock_connection.ipynb"),
)
def test_example_notebooks_are_valid_clean_and_portable(name: str) -> None:
    code = _assert_clean_notebook(ROOT / "examples" / name)
    assert "load_simulation" in code or "load_mms_data" in code


def test_connection_notebook_preserves_the_simplified_default_grid() -> None:
    source = (ROOT / "examples/shock_connection.ipynb").read_text()
    assert "SURFACE_AXIS = np.linspace(-30.0, 30.0, 241)" in source
    assert "SURFACE_Y" not in source
    assert "SURFACE_Z" not in source


def _tool_environment() -> dict[str, str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(ROOT / "src"), environment.get("PYTHONPATH")))
    )
    return environment


def test_connection_tool_help_describes_3d_outputs() -> None:
    result = subprocess.run(
        [str(ROOT / "tools/mms_bow_shock_connection.py"), "-h"],
        cwd=ROOT,
        env=_tool_environment(),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--three-d-output" in result.stdout
    assert "png" in result.stdout and "html" in result.stdout


def test_swmf_tool_is_thin_and_helpful() -> None:
    tool = ROOT / "tools/create_swmf_input.py"
    source = tool.read_text()
    assert os.access(tool, os.X_OK)
    assert source.startswith("#!/usr/bin/env python")
    assert "from shocklink.mms_swmf import main" in source
    assert "raise SystemExit(main())" in source

    result = subprocess.run(
        [str(tool), "-h"], cwd=ROOT, env=_tool_environment(), check=True,
        capture_output=True, text=True,
    )
    for option in ("--mms-start", "--mms-end", "--input", "--start-time", "--probe", "--mode"):
        assert option in result.stdout
    assert "PARAM_YYYYMMDD_HHMMSS.in" in result.stdout
