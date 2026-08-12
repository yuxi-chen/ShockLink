from __future__ import annotations

import ast
import inspect
import os
import runpy
import subprocess
import sys
from pathlib import Path
from types import ModuleType

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
    assert "examples/README.md" in readme
    assert "tools/mms_bow_shock_connection.py" in readme
    assert "tools/create_swmf_input.py" in readme
    assert ALGORITHMS.is_file()


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


@pytest.mark.parametrize("name", ("mms_example.ipynb", "shock_connection.ipynb"))
def test_mms_notebooks_use_current_installation_command(name: str) -> None:
    source = (ROOT / "examples" / name).read_text()

    assert ".[mms" not in source
    assert "pip install -e " in source


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
    assert "--param-file" in result.stdout
    assert "--mms-window-seconds" not in result.stdout
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
        [str(tool), "-h"],
        cwd=ROOT,
        env=_tool_environment(),
        check=True,
        capture_output=True,
        text=True,
    )
    for option in (
        "--mms-start",
        "--mms-end",
        "--input",
        "--start-time",
        "--probe",
        "--mode",
        "--plot",
    ):
        assert option in result.stdout
    assert "PARAM_YYYYMMDD_HHMMSS.in" in result.stdout


def test_swmf_batch_example_is_executable_helpful_and_documented() -> None:
    script = ROOT / "examples/run_swmf_inputs.py"
    assert os.access(script, os.X_OK)

    result = subprocess.run(
        [str(script), "--help"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "input_directory" in result.stdout
    assert "sequentially" in result.stdout
    assert "runNNN_<input-suffix>" in result.stdout
    assert "run_swmf_inputs.py" in (ROOT / "examples/README.md").read_text()


def test_create_swmf_inputs_uses_writable_local_dependency_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("MPLBACKEND", "MPLCONFIGDIR", "SPACEPY", "SPEDAS_DATA_DIR"):
        monkeypatch.delenv(name, raising=False)

    calls: list[tuple[Path, Path]] = []
    dependency = ModuleType("shocklink.mms_swmf")

    def create_swmf_input(
        _start: str, _end: str, *, output: Path, input: Path, **_kwargs
    ) -> Path:
        calls.append((output, input))
        return output

    dependency.create_swmf_input = create_swmf_input  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "shocklink.mms_swmf", dependency)
    namespace = runpy.run_path(str(ROOT / "examples/create_swmf_inputs.py"))

    output_directory = tmp_path / "results"
    outputs = namespace["create_inputs"](
        [("2023-12-16 08:30:00", "2023-12-16 11:00:00")],
        output_directory=output_directory,
        plot=False,
    )

    cache = output_directory / ".cache"
    assert os.environ["MPLBACKEND"] == "Agg"
    assert Path(os.environ["MPLCONFIGDIR"]) == cache / "matplotlib"
    assert Path(os.environ["SPACEPY"]) == cache / "spacepy"
    assert Path(os.environ["SPEDAS_DATA_DIR"]) == cache / "spedas"
    assert outputs == [output for output, _input in calls]
    assert [input for _output, input in calls] == [ROOT / "data/Param/PARAM.in.Earth"]


def test_copied_create_swmf_inputs_finds_repository_template(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dependency = ModuleType("shocklink.mms_swmf")

    def create_swmf_input(
        _start: str, _end: str, *, output: Path, input: Path, **_kwargs
    ) -> Path:
        assert input == ROOT / "data/Param/PARAM.in.Earth"
        return output

    dependency.create_swmf_input = create_swmf_input  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "shocklink.mms_swmf", dependency)

    copied_script = tmp_path / "create_swmf_inputs.py"
    copied_script.write_text((ROOT / "examples/create_swmf_inputs.py").read_text())
    namespace = runpy.run_path(str(copied_script))

    namespace["create_inputs"](
        [("2023-12-16 08:30:00", "2023-12-16 11:00:00")],
        output_directory=tmp_path / "results",
        plot=False,
    )
