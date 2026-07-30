import ast
import re
import tomllib
from pathlib import Path

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


def test_project_uses_root_readme_for_package_metadata() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["readme"] == "README.md"
    assert README.is_file()


def test_root_readme_describes_bow_shock_workflow_source_paths() -> None:
    text = README.read_text()
    assert "ShockLink" in text
    assert "pip install shocklink" in text
    assert "](docs/" not in text
    assert "](examples/" not in text
    assert "`docs/bow-shock-workflow.md`" in text
    assert "`examples/bow_shock_workflow.py`" in text
    assert "`examples/README.md`" in text
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
