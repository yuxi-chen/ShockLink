import ast
import inspect
import re
import tomllib
from pathlib import Path

import pytest

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.tecplot import read_tecplot

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW_GUIDE = ROOT / "docs/bow-shock-workflow.md"
WORKFLOW_EXAMPLE = ROOT / "examples/bow_shock_workflow.py"

PUBLIC_WORKFLOW_FUNCTIONS = (
    "read_tecplot",
    "calc_velocity_divergence",
    "fit_bow_shock",
    "extract_shockfit_range",
    "get_bow_shock_surface",
    "calc_bow_shock_normals",
)

PUBLIC_WORKFLOW_API = (
    read_tecplot,
    calc_velocity_divergence,
    fit_bow_shock,
    extract_shockfit_range,
    get_bow_shock_surface,
    calc_bow_shock_normals,
)


@pytest.mark.parametrize("function", PUBLIC_WORKFLOW_API)
def test_public_workflow_api_docstrings_use_numpy_sections(function: object) -> None:
    """Public workflow functions document inputs, outputs, and failures."""

    docstring = inspect.getdoc(function)
    assert docstring is not None
    for section in ("Parameters", "Returns", "Raises"):
        assert f"{section}\n{'-' * len(section)}" in docstring


def test_bow_shock_api_docstrings_explain_key_data_conventions() -> None:
    """Workflow documentation records mutation, missing-data, and normal semantics."""

    assert "in place" in inspect.getdoc(calc_velocity_divergence).lower()
    assert "in place" in inspect.getdoc(fit_bow_shock).lower()
    assert "NaN" in inspect.getdoc(get_bow_shock_surface)
    normal_docstring = inspect.getdoc(calc_bow_shock_normals)
    assert "+X" in normal_docstring
    assert "(1, -dx/dy, -dx/dz)" in normal_docstring


def test_bow_shock_api_docstrings_explain_fitting_and_sampling_conventions() -> None:
    """Workflow documentation records fit, sampling, and normal conventions."""

    fit_docstring = inspect.getdoc(fit_bow_shock)
    assert "x = x0 - a(y**2 + z**2)" in fit_docstring
    assert "most-negative div(U)" in fit_docstring
    assert "shockfit = x - x_surface(y, z)" in fit_docstring

    surface_docstring = inspect.getdoc(get_bow_shock_surface)
    assert "X-resolution" in surface_docstring
    assert "chunk size" in surface_docstring
    assert "memory" in surface_docstring

    normal_docstring = inspect.getdoc(calc_bow_shock_normals)
    assert "(nx, ny, nz)" in normal_docstring
    assert "linear interpolation followed by nearest-neighbor" in normal_docstring
    assert "does not mutate" in normal_docstring
    assert "lower edge accuracy" in normal_docstring


def test_project_uses_root_readme_for_package_metadata() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["readme"] == "README.md"
    assert metadata["project"]["urls"] == {
        "Repository": "https://github.com/yuxi-chen/ShockLink",
        "Documentation": (
            "https://github.com/yuxi-chen/ShockLink/blob/main/"
            "docs/bow-shock-workflow.md"
        ),
    }
    assert README.is_file()


def test_root_readme_links_bow_shock_workflow_documentation_on_github() -> None:
    text = README.read_text()
    assert "ShockLink" in text
    assert "pip install shocklink" in text
    assert (
        "[docs/bow-shock-workflow.md]("
        "https://github.com/yuxi-chen/ShockLink/blob/main/"
        "docs/bow-shock-workflow.md)"
    ) in text
    assert (
        "[examples/bow_shock_workflow.py]("
        "https://github.com/yuxi-chen/ShockLink/blob/main/"
        "examples/bow_shock_workflow.py)"
    ) in text
    assert (
        "[examples/README.md]("
        "https://github.com/yuxi-chen/ShockLink/blob/main/examples/README.md)"
    ) in text
    assert "calc_bow_shock_normals" in text


def test_workflow_guide_documents_public_pipeline_and_array_conventions() -> None:
    text = WORKFLOW_GUIDE.read_text()
    for function_name in PUBLIC_WORKFLOW_FUNCTIONS:
        assert function_name in text
    assert "surface_x[i, j]" in text
    assert "normals.shape == surface_x.shape + (3,)" in text
    assert "(1, -dx_s/dy, -dx_s/dz)" in text
    assert "nx > 0" in text
    assert "linear" in text
    assert "nearest" in text
    assert "data/3d.dat" in text


def test_workflow_guide_contains_compilable_complete_python_example() -> None:
    python_blocks = re.findall(
        r"```python\n(.*?)\n```",
        WORKFLOW_GUIDE.read_text(),
        flags=re.DOTALL,
    )
    workflow_blocks = [
        block
        for block in python_blocks
        if all(
            f"{function_name}(" in block for function_name in PUBLIC_WORKFLOW_FUNCTIONS
        )
    ]
    assert len(workflow_blocks) == 1
    compile(workflow_blocks[0], str(WORKFLOW_GUIDE), "exec")


def test_examples_readme_links_workflow_guide() -> None:
    text = (ROOT / "examples/README.md").read_text()
    assert "../docs/bow-shock-workflow.md" in text
    assert "bow_shock_workflow.py" in text
    assert "PYTHONPATH=src python examples/bow_shock_workflow.py data/3d.dat" in text
    assert (ROOT / "docs/bow-shock-workflow.md").is_file()
    assert WORKFLOW_EXAMPLE.is_file()


def test_workflow_example_compiles_and_uses_only_public_api() -> None:
    assert WORKFLOW_EXAMPLE.is_file()
    source = WORKFLOW_EXAMPLE.read_text()
    compile(source, str(WORKFLOW_EXAMPLE), "exec")
    tree = ast.parse(source)

    shocklink_imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("shocklink.")
    ]
    imported_names = {alias.name for node in shocklink_imports for alias in node.names}
    assert set(PUBLIC_WORKFLOW_FUNCTIONS) <= imported_names
    assert all(not name.startswith("_") for name in imported_names)


def test_workflow_example_reports_surface_and_normal_quality() -> None:
    assert WORKFLOW_EXAMPLE.is_file()
    source = WORKFLOW_EXAMPLE.read_text()

    for label in (
        "surface_shape:",
        "normal_shape:",
        "finite_surface_values:",
        "minimum_normal_x:",
        "maximum_unit_length_error:",
    ):
        assert label in source
