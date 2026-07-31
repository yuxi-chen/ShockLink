from pathlib import Path
import ast
import sys
import tomllib

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "examples/extract_shock.ipynb"
MMS_NOTEBOOK = ROOT / "examples/mms_example.ipynb"


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def test_notebook_is_valid_and_clean() -> None:
    notebook = _notebook()

    nbformat.validate(notebook)
    assert len(notebook.cells) >= 5
    assert notebook.cells[0].cell_type == "markdown"
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is None
            assert cell.outputs == []


def test_notebook_covers_the_compact_shock_extraction_pipeline() -> None:
    notebook = _notebook()
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")

    required_fragments = [
        "read_tecplot",
        "calc_velocity_divergence",
        "fit_bow_shock",
        "extract_shockfit_range",
        "get_2d_cut",
        "plot_2d_cut",
        "get_bow_shock_surface",
        "refine_minimum=True",
        "smooth_bow_shock_surface",
        "SMOOTHING_SIGMA",
        "calc_bow_shock_normals",
        "calc_bow_shock_normal_angle",
        "surface_x_raw",
        "surface_x",
        "normal_angle_deg",
        "fig, axes = plt.subplots(1, 2",
        'label="Bow-shock X [R]"',
        'label="Angle to reference vector [deg]"',
    ]
    for fragment in required_fragments:
        assert fragment in code

    assert code.index("fit = fit_bow_shock(grid)") < code.index(
        "shock_region = extract_shockfit_range("
    )
    assert code.index("shock_region = extract_shockfit_range(") < code.index(
        "cut = get_2d_cut(shock_region, normal=CUT_NORMAL, origin=CUT_ORIGIN)"
    )
    assert code.index(
        "cut = get_2d_cut(shock_region, normal=CUT_NORMAL, origin=CUT_ORIGIN)"
    ) < code.index("surface_x_raw = get_bow_shock_surface(")
    assert code.index("surface_x_raw = get_bow_shock_surface(") < code.index(
        "surface_x = smooth_bow_shock_surface("
    )


def test_notebook_is_portable_and_documents_launch() -> None:
    all_source = "\n".join(cell.source for cell in _notebook().cells)

    assert 'DATA_PATH = Path("../data/3d.dat")' in all_source
    assert "SURFACE_Y = np.linspace(-25.0, 25.0, 401)" in all_source
    assert "SURFACE_Z = np.linspace(-25.0, 25.0, 401)" in all_source
    assert "jupyter lab examples/extract_shock.ipynb" in all_source
    assert "/Users/" not in all_source


def test_large_local_data_is_excluded_from_source_distribution() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)

    excluded = project["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]

    assert "/data" in excluded


def test_mms_notebook_is_valid_clean_and_uses_public_example_api() -> None:
    notebook = nbformat.read(MMS_NOTEBOOK, as_version=4)

    nbformat.validate(notebook)
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    ast.parse(code)
    assert "from mms_data_analysis import" in code
    assert "load_mms_data(" in code
    assert "summarize_data(" in code
    assert "plot_mms_data(" in code
    assert 'print(f"{name}: {series}")' in code
    assert "series.label" not in code
    assert "--start" not in code
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is None
            assert cell.outputs == []


def test_mms_notebook_guides_the_full_analysis_workflow() -> None:
    notebook = nbformat.read(MMS_NOTEBOOK, as_version=4)
    markdown = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "markdown"
    )

    for heading in [
        "## Requirements",
        "## Parameters",
        "## Download MMS data",
        "## Inspect loaded products",
        "## Summary statistics",
        "## Plot data",
        "## Troubleshooting",
    ]:
        assert heading in markdown

    parameter_cell = next(
        cell.source
        for cell in notebook.cells
        if cell.cell_type == "code" and "MODE = \"auto\"" in cell.source
    )
    for setting in ["START =", "END =", "PROBE =", "MODE ="]:
        assert setting in parameter_cell


def test_mms_notebook_imports_example_when_jupyter_starts_at_repository_root(
    monkeypatch,
) -> None:
    notebook = nbformat.read(MMS_NOTEBOOK, as_version=4)
    setup = next(cell.source for cell in notebook.cells if cell.cell_type == "code")
    monkeypatch.chdir(ROOT)
    monkeypatch.delitem(sys.modules, "mms_data_analysis", raising=False)

    namespace: dict[str, object] = {}
    exec(setup, namespace)

    assert "load_mms_data" in namespace
