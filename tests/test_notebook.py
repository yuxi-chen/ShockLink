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
        '"div(U)"',
        '"B [nT]"',
        '"U [km/s]"',
        'plotter.show(jupyter_backend="static")',
    ]

    for fragment in required_fragments:
        assert fragment in code

    assert "from shocklink.dataset import (" in code
    assert "from shocklink.tecplot import read_tecplot" in code
    assert "calc_velocity_divergence" in code
    assert "calc_velocity_divergence(grid)" in code
    assert 'SCALARS = "div(U)"' in code
    assert '"div(U)"' in code


def test_notebook_is_portable_and_documents_launch() -> None:
    notebook = _notebook()
    all_source = "\n".join(cell.source for cell in notebook.cells)

    assert 'DATA_PATH = ROOT / "data/3d.dat"' in all_source
    assert 'NORMAL = "z"' in all_source
    assert 'SCALARS = "div(U)"' in all_source
    assert "jupyter lab examples/tecplot_2d_cut.ipynb" in all_source
    assert "/Users/" not in all_source
    assert "pressure-z0.png" not in all_source


def test_large_local_data_is_excluded_from_source_distribution() -> None:
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)

    excluded = project["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"]

    assert "/data" in excluded
