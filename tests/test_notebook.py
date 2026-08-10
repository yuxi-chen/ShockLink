from pathlib import Path
import ast
import sys
import tomllib

import nbformat

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "examples/extract_shock.ipynb"
MMS_NOTEBOOK = ROOT / "examples/mms_example.ipynb"
CONNECTION_NOTEBOOK = ROOT / "examples/shock_connection.ipynb"


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
        "load_simulation",
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
    assert "from shocklink.mms import" in code
    assert "from mms_data_analysis import" not in code
    assert "load_mms_data(" in code
    assert "coordinates=COORDINATES" in code
    assert "summarize_data(" in code
    assert "average_plotted_values(" in code
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
        if cell.cell_type == "code" and 'MODE = "auto"' in cell.source
    )
    for setting in ["START =", "END =", "PROBE =", "MODE =", "COORDINATES ="]:
        assert setting in parameter_cell

    assert "GSM" in markdown
    assert "averages" in markdown
    assert "eV" in markdown
    assert "left axis in eV" in markdown
    assert "right axis in K" in markdown


def test_mms_notebook_imports_package_when_jupyter_starts_at_repository_root(
    monkeypatch,
) -> None:
    notebook = nbformat.read(MMS_NOTEBOOK, as_version=4)
    setup = next(cell.source for cell in notebook.cells if cell.cell_type == "code")
    monkeypatch.chdir(ROOT)
    monkeypatch.delitem(sys.modules, "shocklink.mms", raising=False)

    namespace: dict[str, object] = {}
    exec(setup, namespace)

    assert "load_mms_data" in namespace
    assert "plot_mms_data" in namespace


def _connection_notebook() -> nbformat.NotebookNode:
    return nbformat.read(CONNECTION_NOTEBOOK, as_version=4)


def test_connection_notebook_is_valid_clean_and_uses_public_workflow() -> None:
    notebook = _connection_notebook()
    nbformat.validate(notebook)
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    ast.parse(code)

    for fragment in [
        "load_simulation",
        "calc_velocity_divergence",
        "fit_bow_shock",
        "extract_shockfit_range",
        "get_bow_shock_surface",
        "smooth_bow_shock_surface",
        "calc_bow_shock_normals",
        "load_mms_data",
        'coordinates="gsm"',
        "average_plotted_values",
        "analyze_shock_connection",
        "plot_shock_angle_contour",
        "plot_shock_connection_3d",
        "TIME_EVENT_KEY",
        "selected_intersection",
    ]:
        assert fragment in code

    assert code.index("fit = fit_bow_shock(grid)") < code.index(
        "shock_region = extract_shockfit_range("
    )
    assert code.index("shock_region = extract_shockfit_range(") < code.index(
        "mms_data = load_mms_data("
    )
    assert code.index("mms_data = load_mms_data(") < code.index(
        "connection = analyze_shock_connection("
    )
    assert code.index("connection = analyze_shock_connection(") < code.index(
        "plot_shock_angle_contour(connection)"
    )

    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is None
            assert cell.outputs == []


def test_connection_notebook_documents_launch_and_portable_parameters() -> None:
    notebook = _connection_notebook()
    source = "\n".join(cell.source for cell in notebook.cells)
    code = "\n".join(cell.source for cell in notebook.cells if cell.cell_type == "code")
    tree = ast.parse(code)
    surface_call = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "get_bow_shock_surface"
    )

    assert 'DATA_PATH = Path("../data/3d.dat")' in source
    assert "MMS_WINDOW_SECONDS = 300.0" in source
    assert "SURFACE_AXIS = np.linspace(-30.0, 30.0, 241)" in source
    assert "TRANSVERSE_LIMIT" not in source
    assert "SURFACE_RESOLUTION" not in source
    assert "SURFACE_Y" not in source
    assert "SURFACE_Z" not in source
    assert {keyword.arg for keyword in surface_call.keywords}.isdisjoint({"y", "z"})
    assert code.count("y=SURFACE_AXIS") == 2
    assert code.count("z=SURFACE_AXIS") == 2
    assert "parse_datetime" in source
    assert "event_time" in source
    assert "mms_start =" in source
    assert "mms_end =" in source
    assert "jupyter lab examples/shock_connection.ipynb" in source
    assert 'pv.set_jupyter_backend("static")' in source
    assert 'plotter.show(jupyter_backend="static")' in source
    assert "/Users/" not in source
