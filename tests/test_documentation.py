import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
WORKFLOW_GUIDE = ROOT / "docs/bow-shock-workflow.md"
WORKFLOW_EXAMPLE = ROOT / "examples/bow_shock_workflow.py"


def test_project_uses_root_readme_for_package_metadata() -> None:
    metadata = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert metadata["project"]["readme"] == "README.md"
    assert README.is_file()


def test_root_readme_describes_and_links_bow_shock_workflow() -> None:
    text = README.read_text()
    assert "ShockLink" in text
    assert "pip install" in text
    assert "docs/bow-shock-workflow.md" in text
    assert "examples/bow_shock_workflow.py" in text
    assert "calc_bow_shock_normals" in text
