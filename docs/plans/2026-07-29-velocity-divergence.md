# Velocity Divergence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add an in-place `calc_velocity_divergence()` operation for PyVista datasets.

**Architecture:** The generic `shocklink.dataset` module validates a point-based velocity vector, delegates mesh derivatives to PyVista/VTK, and copies only the resulting divergence array back to the original dataset. Tecplot I/O remains independent.

**Tech Stack:** Python 3.10+, NumPy, PyVista 0.48+, pytest

---

### Task 1: Specify the analytic calculation

**Files:**
- Create: `tests/test_dataset_derivatives.py`

**Step 1: Write failing tests**

Create an image grid with `U = (x, y, z)` and assert:

```python
result = calc_velocity_divergence(grid)

assert result is grid
np.testing.assert_allclose(grid.point_data["div(U)"], 3.0)
```

Add a second test using custom velocity and output names. Assert that an
existing output array is replaced.

**Step 2: Verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/test_dataset_derivatives.py -q
```

Expected: test collection fails because `calc_velocity_divergence` is absent.

### Task 2: Implement the minimal calculation

**Files:**
- Modify: `src/shocklink/dataset.py`

**Step 1: Add input validation**

Require a nonempty output name and a finite velocity array shaped
`(dataset.n_points, 3)`. Raise `DatasetError` for violations.

**Step 2: Calculate and copy divergence**

Use:

```python
derived = dataset.compute_derivative(
    scalars=velocity_name,
    gradient=False,
    divergence=output_name,
    preference="point",
)
dataset.point_data[output_name] = np.asarray(
    derived.point_data[output_name]
).copy()
return dataset
```

Wrap filter errors and validate that the result is a finite scalar point array.
Add `calc_velocity_divergence` to `dataset.__all__`.

**Step 3: Verify GREEN**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/test_dataset_derivatives.py -q
```

Expected: calculation tests pass.

### Task 3: Add validation coverage

**Files:**
- Modify: `tests/test_dataset_derivatives.py`

**Step 1: Add parameterized validation tests**

Cover missing velocity, malformed velocity shape, non-finite values, empty
output name, wrapped PyVista failure, and invalid derivative output.

**Step 2: Run focused dataset tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest \
  tests/test_dataset_derivatives.py \
  tests/test_dataset_cut.py \
  tests/test_dataset_plot.py \
  tests/test_module_boundaries.py -q
```

Expected: all focused tests pass.

**Step 3: Commit**

```bash
git add src/shocklink/dataset.py tests/test_dataset_derivatives.py
git commit -m "feat: calculate velocity divergence"
```

### Task 4: Finish examples and verification

**Files:**
- Modify: `examples/plot_2d_cut.py`
- Modify: `examples/tecplot_2d_cut.ipynb`
- Modify: `tests/test_notebook.py`

Update the pending module-refactor imports to use `shocklink.dataset`, changing
only the notebook import cell and preserving all user edits.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=src python -m pytest tests/integration/test_tecplot_sample.py -q
```

Build the wheel and verify it contains both `shocklink/dataset.py` and
`shocklink/tecplot.py`, with no directory under `src/shocklink`.
