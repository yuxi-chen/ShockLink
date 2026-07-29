from pathlib import Path
import tomllib

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "examples/tecplot_2d_cut.ipynb"


def _notebook() -> nbformat.NotebookNode:
    return nbformat.read(NOTEBOOK, as_version=4)


def test_notebook_is_valid_and_clean() -> None:
    notebook = _notebook()

    nbformat.validate(notebook)
    assert len(notebook.cells) >= 7
    assert notebook.cells[0].cell_type == "markdown"
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is None
            assert cell.outputs == []


def test_notebook_covers_read_cut_validate_and_plot_workflow() -> None:
    notebook = _notebook()
    code = "\n".join(
        cell.source for cell in notebook.cells if cell.cell_type == "code"
    )

    required_fragments = [
        "read_tecplot",
        "get_2d_cut",
        "plot_2d_cut",
        "DATA_PATH",
        "NORMAL",
        "ORIGIN",
        "SCALARS",
        'pv.set_jupyter_backend("static")',
        '"P [nPa]"',
        '"div(U)"',
        '"shockfit"',
        '"B [nT]"',
        '"U [km/s]"',
        'show(jupyter_backend="static")',
    ]

    for fragment in required_fragments:
        assert fragment in code

    assert "from shocklink.dataset import (" in code
    assert "from shocklink.tecplot import read_tecplot" in code
    assert "calc_velocity_divergence" in code
    assert "calc_velocity_divergence(grid)" in code
    assert "from shocklink.bowshock import fit_bow_shock" in code
    assert "fit = fit_bow_shock(grid)" in code
    assert "extract_shockfit_range" in code
    assert "SHOCKFIT_RANGE = [3-x0, x0+5]" in code
    assert "shock_region = extract_shockfit_range(" in code
    assert "lower=SHOCKFIT_RANGE[0]" in code
    assert "upper=SHOCKFIT_RANGE[1]" in code
    assert "cut = get_2d_cut(shock_region, normal=NORMAL, origin=ORIGIN)" in code
    assert "vtkOriginalPointIds" in code
    assert "vtkOriginalCellIds" in code
    assert code.index("fit = fit_bow_shock(grid)") < code.index(
        "shock_region = extract_shockfit_range("
    )
    assert code.index("shock_region = extract_shockfit_range(") < code.index(
        "cut = get_2d_cut(shock_region"
    )
    assert 'SCALARS = "p"' in code
    assert '"div(U)"' in code
    assert "fit.loc0" in code
    assert "fit.loc1" in code
    assert "fit.loc2" in code
    assert "fit.curvature" in code
    assert 'pressure_plotter = plot_2d_cut(cut, scalars="p"' in code
    assert "pressure_contours = cut.contour(" in code
    assert "isosurfaces=15" in code
    assert 'scalars="P [nPa]"' in code
    assert "pressure_shock_contour = cut.contour(" in code
    assert "isosurfaces=[0.0]" in code
    assert 'scalars="shockfit"' in code
    assert "pressure_plotter.add_mesh(pressure_contours" in code
    assert "pressure_plotter.add_mesh(pressure_shock_contour" in code
    assert 'divu_plotter = plot_2d_cut(cut, scalars="div(U)"' in code
    assert "divu_shock_contour = cut.contour(" in code
    assert "divu_plotter.add_mesh(divu_shock_contour" in code
    assert code.count('show(jupyter_backend="static")') == 2


def test_notebook_is_portable_and_documents_launch() -> None:
    notebook = _notebook()
    all_source = "\n".join(cell.source for cell in notebook.cells)

    assert 'DATA_PATH = ROOT / "data/3d.dat"' in all_source
    assert 'NORMAL = "z"' in all_source
    assert 'SCALARS = "p"' in all_source
    assert "SHOCKFIT_RANGE = [3-x0, x0+5]" in all_source
    assert "jupyter lab examples/tecplot_2d_cut.ipynb" in all_source
    assert "/Users/" not in all_source
    assert "pressure-z0.png" not in all_source


def test_large_local_data_is_excluded_from_source_distribution() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)

    excluded = project["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]

    assert "/data" in excluded
