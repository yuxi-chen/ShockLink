from pathlib import Path
import tomllib

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "examples/extract_shock.ipynb"


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

    assert "get_2d_cut" not in code
    assert "plot_2d_cut" not in code
    assert code.index("fit = fit_bow_shock(grid)") < code.index(
        "shock_region = extract_shockfit_range("
    )
    assert code.index("shock_region = extract_shockfit_range(") < code.index(
        "surface_x_raw = get_bow_shock_surface("
    )
    assert code.index("surface_x_raw = get_bow_shock_surface(") < code.index(
        "surface_x = smooth_bow_shock_surface("
    )


def test_notebook_is_portable_and_documents_launch() -> None:
    all_source = "\n".join(cell.source for cell in _notebook().cells)

    assert 'DATA_PATH = Path("data/3d.dat")' in all_source
    assert "jupyter lab examples/extract_shock.ipynb" in all_source
    assert "/Users/" not in all_source


def test_large_local_data_is_excluded_from_source_distribution() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)

    excluded = project["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]

    assert "/data" in excluded
