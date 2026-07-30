# Bow-Shock Workflow Documentation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add layered user and developer documentation for the complete Tecplot-to-bow-shock-normal workflow, including a PyPI README and a runnable real-data example.

**Architecture:** Keep user-facing material in a root README, one focused workflow guide, and one public-API example script. Expand the existing public function docstrings and add only scientifically meaningful inline comments; protect the documentation contract with lightweight structural tests and leave numerical behavior unchanged.

**Tech Stack:** Markdown, Python 3.11–3.13, NumPy-style docstrings, argparse, pytest, Ruff, Hatchling, build, and Twine.

---

Use `@superpowers:test-driven-development` for documentation contracts and
the runnable example. Before reporting completion, use
`@superpowers:verification-before-completion`.

### Task 1: Add the package and PyPI README

**Files:**
- Create: `README.md`
- Create: `tests/test_documentation.py`
- Modify: `pyproject.toml:5-26`

**Step 1: Write the failing README metadata tests**

Create `tests/test_documentation.py`:

```python
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
```

**Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
```

Expected: failures because `README.md` and `project.readme` do not exist.

**Step 3: Configure the package README**

Add this field below `description` in `pyproject.toml`:

```toml
readme = "README.md"
```

**Step 4: Create the root README**

Create a concise `README.md` with these sections and content:

````markdown
# ShockLink

ShockLink analyzes magnetic field-line connectivity to the bow shock in 3D
MHD magnetosphere simulations. Its current workflow reads BATSRUS Tecplot
data with PyVista, derives velocity compression, extracts a regular bow-shock
surface, and calculates outward unit normals.

## Installation

Install the package:

```bash
pip install shocklink
```

For a development checkout:

```bash
pip install -e ".[dev,notebook]"
```

## Bow-shock workflow

The implemented analysis sequence is:

```text
Tecplot -> div(U) -> paraboloid fit -> near-shock region
        -> regular Y-Z surface -> outward unit normals
```

See the [bow-shock workflow guide](docs/bow-shock-workflow.md) for the
scientific conventions and a copy-paste Python example. The same pipeline is
available as [a runnable script](examples/bow_shock_workflow.py).

The final call:

```python
normals = calc_bow_shock_normals(surface_x, y=y, z=z)
```

returns `(nx, ny, nz)` with a strictly positive X component.

## Examples

See [examples/README.md](examples/README.md) for the notebook and command-line
examples.

## Status

ShockLink is pre-alpha research software. Validate resolutions and detected
shock geometry for each simulation before using results in scientific
analysis.
````

Adjust line wrapping while preserving the content and links.

**Step 5: Run the README tests and verify GREEN**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
```

Expected: 2 tests pass.

**Step 6: Commit**

```bash
git add README.md pyproject.toml tests/test_documentation.py
git commit -m "docs: add ShockLink package README"
```

### Task 2: Write the detailed workflow guide

**Files:**
- Create: `docs/bow-shock-workflow.md`
- Modify: `examples/README.md`
- Modify: `tests/test_documentation.py`

**Step 1: Write failing workflow-content tests**

Add:

```python
PUBLIC_WORKFLOW_FUNCTIONS = (
    "read_tecplot",
    "calc_velocity_divergence",
    "fit_bow_shock",
    "extract_shockfit_range",
    "get_bow_shock_surface",
    "calc_bow_shock_normals",
)


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


def test_examples_readme_links_workflow_guide_and_script() -> None:
    text = (ROOT / "examples/README.md").read_text()

    assert "../docs/bow-shock-workflow.md" in text
    assert "bow_shock_workflow.py" in text
```

**Step 2: Run the new tests and verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
```

Expected: failures because the workflow guide and links do not exist.

**Step 3: Create the workflow guide**

Create `docs/bow-shock-workflow.md` with these sections:

1. `# Bow-shock surface and normal workflow`
2. `## Scientific conventions`
3. `## Complete Python example`
4. `## Step 1: Read and normalize Tecplot data`
5. `## Step 2: Calculate velocity divergence`
6. `## Step 3: Fit a paraboloid`
7. `## Step 4: Extract the near-shock region`
8. `## Step 5: Extract the regular surface array`
9. `## Step 6: Calculate outward normals`
10. `## Missing surface values`
11. `## Resolution and memory`
12. `## Errors and validation`

The complete example must be:

```python
import numpy as np

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.tecplot import read_tecplot

grid = read_tecplot("data/3d.dat")
calc_velocity_divergence(grid)
fit = fit_bow_shock(grid)
shock_region = extract_shockfit_range(
    grid,
    lower=-5.0,
    upper=5.0,
)

y = np.linspace(-40.0, 40.0, 81)
z = np.linspace(-40.0, 40.0, 81)
surface_x = get_bow_shock_surface(
    shock_region,
    y=y,
    z=z,
)
normals = calc_bow_shock_normals(
    surface_x,
    y=y,
    z=z,
)

assert surface_x.shape == (81, 81)
assert normals.shape == surface_x.shape + (3,)
```

Explain:

- `calc_velocity_divergence()` modifies `grid` in place.
- Compression is selected by the most negative `div(U)`.
- The fit is `x = x0 - a(y**2 + z**2)`.
- `shockfit` is the signed residual from that fit and `[-5, 5]` limits the
  sampling region.
- `surface_x[i, j]` corresponds to `(y[i], z[j])`.
- The parameterization `r(y,z) = (x_s(y,z), y, z)` gives raw outward normal
  `(1, -dx_s/dy, -dx_s/dz)`.
- `nx > 0` means sunward/upstream.
- Linear interpolation fills interior NaNs and nearest interpolation fills
  unresolved edges; measured finite values are restored before gradients.
- Edge extrapolation is less accurate.
- The 1.3 GB sample has material read/sampling memory costs.
- Y/Z and surface validation rules from the approved design.

Do not claim that the paraboloid is the final shock surface; explain that it
only restricts the region for subsequent divergence-based sampling.

**Step 4: Link the guide and script from the examples README**

Add a leading section:

````markdown
## Complete bow-shock workflow

The [bow-shock workflow guide](../docs/bow-shock-workflow.md) explains the
full Tecplot-to-normal pipeline and its array/sign conventions.

Run the non-graphical example:

```bash
PYTHONPATH=src python examples/bow_shock_workflow.py data/3d.dat
```
````

Keep all existing notebook and 2D-cut documentation.

**Step 5: Run the documentation tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
```

Expected: all documentation tests pass.

**Step 6: Commit**

```bash
git add docs/bow-shock-workflow.md examples/README.md tests/test_documentation.py
git commit -m "docs: explain bow-shock analysis workflow"
```

### Task 3: Add the runnable workflow example

**Files:**
- Create: `examples/bow_shock_workflow.py`
- Modify: `tests/test_documentation.py`

**Step 1: Write failing example-structure tests**

Add:

```python
import ast


def test_workflow_example_compiles_and_uses_only_public_api() -> None:
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
    imported_names = {
        alias.name
        for node in shocklink_imports
        for alias in node.names
    }
    assert set(PUBLIC_WORKFLOW_FUNCTIONS) <= imported_names
    assert all(not name.startswith("_") for name in imported_names)


def test_workflow_example_reports_surface_and_normal_quality() -> None:
    source = WORKFLOW_EXAMPLE.read_text()

    assert "surface_shape:" in source
    assert "normal_shape:" in source
    assert "finite_surface_values:" in source
    assert "minimum_normal_x:" in source
    assert "maximum_unit_length_error:" in source
```

**Step 2: Run the new tests and verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
```

Expected: failures because `examples/bow_shock_workflow.py` does not exist.

**Step 3: Create the public-API example**

Create:

```python
"""Extract a bow-shock surface and outward normals from BATSRUS Tecplot data."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.tecplot import read_tecplot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        type=Path,
        default=Path("data/3d.dat"),
        help="BATSRUS Tecplot ASCII file (default: data/3d.dat)",
    )
    parser.add_argument(
        "--transverse-limit",
        type=float,
        default=40.0,
        help="sample Y and Z from -LIMIT to +LIMIT (default: 40)",
    )
    parser.add_argument(
        "--surface-resolution",
        type=int,
        default=81,
        help="number of Y and Z coordinates (default: 81)",
    )
    parser.add_argument(
        "--x-resolution",
        type=int,
        default=512,
        help="samples along each X column (default: 512)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1024,
        help="Y-Z columns sampled per chunk (default: 1024)",
    )
    parser.add_argument(
        "--shockfit-range",
        nargs=2,
        type=float,
        metavar=("LOWER", "UPPER"),
        default=(-5.0, 5.0),
        help="inclusive shockfit residual range (default: -5 5)",
    )
    args = parser.parse_args()

    grid = read_tecplot(args.path)
    calc_velocity_divergence(grid)
    fit = fit_bow_shock(grid)
    shock_region = extract_shockfit_range(
        grid,
        lower=args.shockfit_range[0],
        upper=args.shockfit_range[1],
    )

    y = np.linspace(
        -args.transverse_limit,
        args.transverse_limit,
        args.surface_resolution,
    )
    z = np.linspace(
        -args.transverse_limit,
        args.transverse_limit,
        args.surface_resolution,
    )
    surface_x = get_bow_shock_surface(
        shock_region,
        y=y,
        z=z,
        x_resolution=args.x_resolution,
        chunk_size=args.chunk_size,
    )
    normals = calc_bow_shock_normals(surface_x, y=y, z=z)

    finite_surface = np.isfinite(surface_x)
    unit_error = np.abs(np.linalg.norm(normals, axis=-1) - 1.0)
    print(f"fit_nose_x: {fit.loc0[0]:.6g}")
    print(f"fit_curvature: {fit.curvature:.6g}")
    print(f"surface_shape: {surface_x.shape}")
    print(f"normal_shape: {normals.shape}")
    print(
        "finite_surface_values: "
        f"{np.count_nonzero(finite_surface)}/{surface_x.size}"
    )
    print(f"minimum_normal_x: {normals[..., 0].min():.6g}")
    print(f"maximum_unit_length_error: {unit_error.max():.3e}")


if __name__ == "__main__":
    main()
```

Let Ruff apply any required line wrapping without changing the output labels.

**Step 4: Run focused tests and CLI help**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
PYTHONPATH=src python examples/bow_shock_workflow.py --help
python -m ruff check examples/bow_shock_workflow.py tests/test_documentation.py
python -m ruff format --check examples/bow_shock_workflow.py tests/test_documentation.py
```

Expected: tests and Ruff pass; help lists all five options.

**Step 5: Commit**

```bash
git add examples/bow_shock_workflow.py tests/test_documentation.py
git commit -m "docs: add bow-shock workflow example"
```

### Task 4: Expand public API docstrings and scientific comments

**Files:**
- Modify: `src/shocklink/tecplot.py:69-89`
- Modify: `src/shocklink/dataset.py:23-29`
- Modify: `src/shocklink/bowshock.py:164-214`
- Modify: `src/shocklink/bowshock.py:575-597`
- Modify: `src/shocklink/bowshock.py:681-706`
- Modify: `src/shocklink/bowshock.py:709-720`
- Modify: `tests/test_documentation.py`

**Step 1: Write failing public-docstring tests**

Add:

```python
import inspect

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.tecplot import read_tecplot


PUBLIC_WORKFLOW_CALLABLES = (
    read_tecplot,
    calc_velocity_divergence,
    fit_bow_shock,
    extract_shockfit_range,
    get_bow_shock_surface,
    calc_bow_shock_normals,
)


def test_public_workflow_functions_have_structured_docstrings() -> None:
    for function in PUBLIC_WORKFLOW_CALLABLES:
        docstring = inspect.getdoc(function)
        assert docstring is not None
        assert "\nParameters\n----------" in docstring
        assert "\nReturns\n-------" in docstring
        assert "\nRaises\n------" in docstring


def test_normal_docstring_defines_shape_orientation_and_missing_values() -> None:
    docstring = inspect.getdoc(calc_bow_shock_normals)

    assert docstring is not None
    assert "(len(y), len(z))" in docstring
    assert "(len(y), len(z), 3)" in docstring
    assert "(nx, ny, nz)" in docstring
    assert "positive X" in docstring
    assert "NaN" in docstring
```

**Step 2: Run the new tests and verify RED**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
```

Expected: failures because current public docstrings are one-line summaries.

**Step 3: Expand each public docstring**

Use NumPy-style docstrings with:

- a one-sentence summary;
- `Parameters`, including defaults and expected field names;
- `Returns`, including PyVista or NumPy types and shapes;
- `Raises`, naming `DatasetError` and the relevant categories;
- `Notes` where mutation, units, sign convention, or interpolation requires
  explanation.

Required function-specific content:

- `read_tecplot`: one Tecplot zone; coordinate reassignment; `B [nT]` and
  `U [km/s]`; returns the same normalized `UnstructuredGrid`.
- `calc_velocity_divergence`: modifies and returns the input dataset; point
  vector shape `(dataset.n_points, 3)`; output scalar point array.
- `fit_bow_shock`: strongest `-div(U)` at the nose and two flanks; equation
  `x = x0 - a(y**2 + z**2)`; adds signed `shockfit`; may calculate
  divergence if absent.
- `extract_shockfit_range`: inclusive residual range; `adjacent_cells`
  behavior; returns `pyvista.UnstructuredGrid`.
- `get_bow_shock_surface`: Y-axis-0/Z-axis-1 convention; most negative
  divergence; missing columns remain NaN; return shape `(len(y), len(z))`;
  X resolution and chunk-memory tradeoff.
- `calc_bow_shock_normals`: input/output shapes, `(nx, ny, nz)`, positive-X
  orientation, linear-plus-nearest fill, no input mutation, and edge accuracy
  note.

Do not alter signatures or production statements while editing docstrings.

**Step 4: Add targeted scientific comments**

Add concise comments immediately before:

- nose and flank profile selections in `fit_bow_shock`;
- minimum-divergence selection in `get_bow_shock_surface`;
- restoration of finite samples in `_fill_normal_surface_gaps`;
- positive-X raw normal construction and scaled normalization in
  `_normal_components`.

Example comments:

```python
# Compression is strongest where div(U) is most negative.
```

```python
# Restore measured values exactly; interpolation is used only for gaps.
```

```python
# r_y x r_z gives the outward (+X) normal (1, -dx/dy, -dx/dz).
```

```python
# Scale first so finite but extremely steep slopes cannot overflow the norm.
```

Do not comment straightforward validation or assignment statements.

**Step 5: Run documentation and affected module tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_documentation.py \
  tests/test_tecplot.py \
  tests/test_dataset_derivatives.py \
  tests/bowshock \
  -q
python -m ruff check src tests/test_documentation.py
python -m ruff format --check src tests/test_documentation.py
```

Expected: all commands pass.

**Step 6: Commit**

```bash
git add \
  src/shocklink/tecplot.py \
  src/shocklink/dataset.py \
  src/shocklink/bowshock.py \
  tests/test_documentation.py
git commit -m "docs: document bow-shock workflow APIs"
```

### Task 5: Verify documentation, real workflow, and package metadata

**Files:**
- Verify only; change files only if a check exposes a documentation defect.

**Step 1: Run documentation and complete test suites**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_documentation.py -q
PYTHONPATH=src python -m pytest -q
```

Expected: all documentation and default tests pass; large-data integration
tests remain skipped by default.

**Step 2: Run the example against the real sample**

Use a small verification grid while exercising every public workflow stage:

```bash
PYTHONPATH=src python examples/bow_shock_workflow.py \
  /Users/yuxichen/dev/ShockGeo/data/3d.dat \
  --transverse-limit 5 \
  --surface-resolution 5 \
  --x-resolution 161 \
  --chunk-size 5
```

Expected output includes:

```text
surface_shape: (5, 5)
normal_shape: (5, 5, 3)
finite_surface_values: 25/25
```

`minimum_normal_x` must be positive and
`maximum_unit_length_error` must be near machine precision.

**Step 3: Run project-wide static checks**

Run:

```bash
python -m ruff check src tests examples
python -m ruff format --check src tests examples
git diff --check
```

Expected: all commands exit successfully.

**Step 4: Build and validate package metadata outside the repository**

Run:

```bash
documentation_build_dir=$(mktemp -d /tmp/shocklink-doc-build.XXXXXX)
python -m build --no-isolation --outdir "$documentation_build_dir"
python -m twine check "$documentation_build_dir"/*
```

Expected: wheel and source distribution build successfully; Twine reports
both distributions as `PASSED`, proving the README renders as package
metadata.

**Step 5: Inspect final scope**

Run:

```bash
git status --short
git diff --stat 1e3df48..HEAD
git diff --name-status 1e3df48..HEAD
git ls-files 'src/shocklink/*/*'
```

Expected:

- only README, workflow guide/example, examples README, metadata, docstrings,
  comments, and documentation tests changed;
- no notebook changes;
- no tracked subdirectory under `src/shocklink/`;
- worktree clean.

**Step 6: Commit verification corrections only if needed**

If a verification command exposed a real defect, fix it, rerun the exact
failed command, and commit only the correction:

```bash
git add <corrected-files>
git commit -m "docs: finalize bow-shock workflow guide"
```

Do not create an empty commit when no correction is required.
