# Line Profile Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add generic line sampling and an X-axis profile helper to `shocklink.dataset`.

**Architecture:** `sample_line()` validates arbitrary endpoints and delegates interpolation to PyVista. `get_x_axis_profile()` derives the standard \(y=z=0\) X-axis endpoints from dataset bounds and delegates to the generic sampler.

**Tech Stack:** Python, NumPy, PyVista, pytest

---

### Task 1: Define an analytic arbitrary-line profile

**Files:**
- Create: `tests/test_dataset_profiles.py`

**Step 1: Write a failing test**

Build an image grid with point scalar `f = x + 2y + 3z`, then sample from
`(-1, -1, -1)` to `(1, 1, 1)` at four intervals. Assert `PolyData`, five
points, expected coordinates, and interpolated values `[-6, -3, 0, 3, 6]`.

**Step 2: Verify RED**

Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/test_dataset_profiles.py -q`.

Expected: import failure because `sample_line` is absent.

### Task 2: Implement generic line sampling

**Files:**
- Modify: `src/shocklink/dataset.py`

**Step 1: Validate inputs**

Reuse `_vector3()` for endpoints. Require a positive integer resolution and an
optional finite, nonnegative tolerance.

**Step 2: Delegate to PyVista**

Call `dataset.sample_over_line(pointa, pointb, resolution=resolution,
tolerance=tolerance)`. Wrap errors in `DatasetError`, require a nonempty
`PolyData`, and export `sample_line`.

**Step 3: Verify GREEN**

Run the focused profile test. Expected: pass.

### Task 3: Add the X-axis wrapper and validation coverage

**Files:**
- Modify: `src/shocklink/dataset.py`
- Modify: `tests/test_dataset_profiles.py`

**Step 1: Write tests**

Assert `get_x_axis_profile(grid, resolution=4)` samples the X bounds with
`y=z=0`. Cover custom `y`/`z`, invalid endpoint/resolution/tolerance input,
invalid X bounds, wrapped filter failures, and invalid filter output.

**Step 2: Implement wrapper**

Validate X bounds and delegate to `sample_line()` using `(bounds.x_min, y, z)`
and `(bounds.x_max, y, z)`. Export `get_x_axis_profile`.

**Step 3: Run focused dataset tests**

Run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/test_dataset_profiles.py tests/test_dataset_derivatives.py tests/test_dataset_cut.py tests/test_dataset_plot.py -q`.

Expected: all pass.

### Task 4: Final verification and commit

Run the full suite and build a wheel. Verify the flat source layout remains
unchanged, then commit `src/shocklink/dataset.py` and
`tests/test_dataset_profiles.py` with message `feat: sample generic dataset line profiles`.
