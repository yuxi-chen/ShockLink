# Generic Dataset Operations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move generic PyVista cut and plot operations out of `shocklink.tecplot` and into the flat `shocklink.dataset` module.

**Architecture:** `shocklink.tecplot` remains the format adapter: it reads and normalizes Tecplot data and publicly exports only `read_tecplot`. `shocklink.dataset` accepts already-loaded PyVista datasets and owns planar slicing, cut metadata, scalar selection, camera limits, and plotting without depending on the source file format.

**Tech Stack:** Python 3.10+, PyVista, NumPy, pytest, Hatchling

---

### Task 1: Define the module boundary with a failing test

**Files:**
- Create: `tests/test_module_boundaries.py`

**Step 1: Write the failing test**

Add:

```python
import shocklink.tecplot as tecplot


def test_generic_dataset_operations_are_separate_from_tecplot() -> None:
    from shocklink import dataset

    assert callable(dataset.get_2d_cut)
    assert callable(dataset.plot_2d_cut)
    assert tecplot.__all__ == ["read_tecplot"]
    assert not hasattr(tecplot, "get_2d_cut")
    assert not hasattr(tecplot, "plot_2d_cut")
```

This test encodes both sides of the requested boundary: generic functions exist
in `shocklink.dataset`, and `shocklink.tecplot` does not retain compatibility
aliases.

**Step 2: Run the focused test and verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/test_module_boundaries.py -q
```

Expected: FAIL because `shocklink.dataset` does not exist.

**Step 3: Commit the failing boundary test**

```bash
git add tests/test_module_boundaries.py
git commit -m "test: define generic dataset module boundary"
```

### Task 2: Move the generic implementation

**Files:**
- Create: `src/shocklink/dataset.py`
- Modify: `src/shocklink/tecplot.py`

**Step 1: Create the generic module**

Move these public functions and all helpers/constants used only by them from
`tecplot.py` to `dataset.py`:

```python
CUT_NORMAL_KEY = "shocklink_cut_normal"
CUT_ORIGIN_KEY = "shocklink_cut_origin"


def get_2d_cut(
    grid: pv.DataSet,
    *,
    normal: str | Sequence[float] = "z",
    origin: Sequence[float] = (0.0, 0.0, 0.0),
    generate_triangles: bool = False,
) -> pv.PolyData:
    ...


def plot_2d_cut(
    cut: pv.PolyData,
    *,
    scalars: str = "p",
    xrange: Sequence[float] | None = None,
    yrange: Sequence[float] | None = None,
    plotter: pv.Plotter | None = None,
    show: bool = True,
    cmap: str = "viridis",
    **mesh_kwargs: object,
) -> pv.Plotter:
    ...


__all__ = ["get_2d_cut", "plot_2d_cut"]
```

Move `_AXIS_NORMALS`, `_vector3`, `_normal_vector`,
`_resolve_scalar_name`, `_cut_plane_metadata`, `_view_up`, and `_plot_range`
with them. Preserve their implementations and behavior.

**Step 2: Reduce the Tecplot public surface**

Keep the Tecplot defaults, `_components`, `_single_zone`, and `read_tecplot`
in `tecplot.py`. Remove imports used only by the moved code and set:

```python
__all__ = ["read_tecplot"]
```

Do not add re-exports or lazy compatibility aliases.

**Step 3: Run the focused boundary test and verify GREEN**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/test_module_boundaries.py -q
```

Expected: 1 passed.

**Step 4: Commit the module split**

```bash
git add src/shocklink/dataset.py src/shocklink/tecplot.py
git commit -m "refactor: separate generic dataset operations"
```

### Task 3: Move tests to the generic API

**Files:**
- Move: `tests/test_tecplot_cut.py` to `tests/test_dataset_cut.py`
- Move: `tests/test_tecplot_plot.py` to `tests/test_dataset_plot.py`
- Modify: `tests/test_dataset_cut.py`
- Modify: `tests/test_dataset_plot.py`
- Modify: `tests/integration/test_tecplot_sample.py`

**Step 1: Rename focused test files**

Use repository-aware moves so history follows the tests:

```bash
git mv tests/test_tecplot_cut.py tests/test_dataset_cut.py
git mv tests/test_tecplot_plot.py tests/test_dataset_plot.py
```

**Step 2: Update imports**

In both renamed focused tests, import the public functions and cut metadata
constants from `shocklink.dataset`. In the integration test, use:

```python
from shocklink.dataset import get_2d_cut, plot_2d_cut
from shocklink.tecplot import read_tecplot
```

Keep all assertions unchanged so the refactor cannot alter behavior.

**Step 3: Run focused tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest \
  tests/test_module_boundaries.py \
  tests/test_dataset_cut.py \
  tests/test_dataset_plot.py -q
```

Expected: all focused tests pass.

**Step 4: Commit the test migration**

```bash
git add tests/test_module_boundaries.py tests/test_dataset_cut.py \
  tests/test_dataset_plot.py tests/integration/test_tecplot_sample.py
git commit -m "test: use generic dataset operations"
```

### Task 4: Update runnable examples

**Files:**
- Modify: `examples/plot_2d_cut.py`
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Update the script imports**

Use:

```python
from shocklink.dataset import get_2d_cut, plot_2d_cut
from shocklink.tecplot import read_tecplot
```

**Step 2: Update only the notebook import cell**

Replace the single combined Tecplot import with:

```python
from shocklink.dataset import get_2d_cut, plot_2d_cut
from shocklink.tecplot import read_tecplot
```

Preserve the user's uncommitted plot ranges, added cell, kernel metadata, and
all other notebook content.

**Step 3: Strengthen the notebook test**

Update `tests/test_notebook.py` to assert that the notebook source contains
both `from shocklink.dataset import` and
`from shocklink.tecplot import read_tecplot`.

**Step 4: Run example-related tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/test_notebook.py tests/test_module_boundaries.py -q
```

Expected: all tests pass.

**Step 5: Commit code-owned example changes separately**

Commit `examples/plot_2d_cut.py` and `tests/test_notebook.py`. Do not commit the
user-modified notebook unless the user explicitly requests that all of its
existing uncommitted changes be included.

```bash
git add examples/plot_2d_cut.py tests/test_notebook.py
git commit -m "docs: use generic dataset API in examples"
```

The notebook import edit will remain in the working tree alongside the user's
pre-existing notebook changes.

### Task 5: Verify behavior, integration, and packaging

**Files:**
- Verify: `src/shocklink/dataset.py`
- Verify: `src/shocklink/tecplot.py`
- Verify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Run the complete ordinary suite**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
```

Expected: all ordinary tests pass, with only large-data tests skipped.

**Step 2: Run sample-data integration**

```bash
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src python -m pytest tests/integration/test_tecplot_sample.py -q
```

Expected: both sample-data tests pass.

**Step 3: Build and inspect the wheel**

```bash
python -m build --wheel --outdir /tmp/shocklink-dataset-dist
unzip -l /tmp/shocklink-dataset-dist/shocklink-0.1.0-py3-none-any.whl
```

Expected: the wheel contains both `shocklink/dataset.py` and
`shocklink/tecplot.py`, with no source subdirectories or cache directories.

**Step 4: Check repository scope**

```bash
git status --short --branch
find src/shocklink -mindepth 1 -type d -print
```

Expected: implementation commits are on `main`, no directory exists under
`src/shocklink`, and the user's `pressure-z0.png` plus pre-existing notebook
changes remain preserved.
