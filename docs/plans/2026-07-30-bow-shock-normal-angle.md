# Bow-shock Normal Angle Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a degree-valued angle field between outward bow-shock normals and one reference vector, with tests and a Tecplot-notebook visualization.

**Architecture:** Keep normal construction and angle calculation separate. `calc_bow_shock_normal_angle` accepts any real finite normal array with final dimension three plus one reference vector, normalizes both, and returns a scalar angle for every normal. The notebook reuses its existing `normals` array and plots the result on the existing Y-Z surface grid.

**Tech Stack:** Python 3.11+, NumPy, PyVista workflow, pytest, nbformat.

---

### Task 1: Add normal-angle unit tests

**Files:**
- Modify: `tests/bowshock/test_normals.py`

**Step 1: Write failing tests**

Import `calc_bow_shock_normal_angle` and add tests for:

```python
def test_calc_bow_shock_normal_angle_returns_degrees_for_known_directions() -> None:
    normals = np.array([
        [[1.0, 0.0, 0.0], [-1.0, 0.0, 0.0]],
        [[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    ])
    angles = calc_bow_shock_normal_angle(normals, vector=(2.0, 0.0, 0.0))
    np.testing.assert_allclose(angles, [[0.0, 180.0], [90.0, 90.0]])
```

Add parameterized invalid-input tests for a final axis other than three,
nonfinite normals, zero normal vectors, a zero reference vector, and a
nonfinite reference vector. Assert `DatasetError` and useful error text.

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src pytest tests/bowshock/test_normals.py -q`

Expected: import failure because the new function does not exist.

### Task 2: Implement the public angle function

**Files:**
- Modify: `src/shocklink/bowshock.py`

**Step 1: Add minimal validation and calculation**

Add `calc_bow_shock_normal_angle` after `calc_bow_shock_normals`. Reuse the
module's real-numeric validation helper where suitable. Require
`normals.shape[-1] == 3`, require all components finite, calculate each normal
magnitude, and reject zero-length normals. Convert the reference vector to a
finite `(3,)` float array and reject a zero magnitude. Normalize with division,
compute `np.sum(unit_normals * unit_vector, axis=-1)`, clip it to `[-1, 1]`,
and return `np.degrees(np.arccos(dot))`.

Document the input shapes, `[0, 180]` degree range, and orientation semantics
with NumPy-style `Parameters`, `Returns`, and `Raises` sections. Add the
function to `__all__`.

**Step 2: Run unit tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/bowshock/test_normals.py -q`

Expected: all normal tests pass.

**Step 3: Commit**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_normals.py
git commit -m "feat: add bow-shock normal angle"
```

### Task 3: Add notebook calculation and plot checks

**Files:**
- Modify: `examples/tecplot_2d_cut.ipynb`
- Modify: `tests/test_notebook.py`

**Step 1: Write failing notebook-content tests**

Assert the notebook imports `calc_bow_shock_normal_angle`, defines
`REFERENCE_VECTOR`, calculates `normal_angle_deg`, and includes a degree
labelled Y-Z visualization.

**Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src pytest tests/test_notebook.py -q`

Expected: content assertion failure for the missing angle workflow.

### Task 4: Extend the Tecplot notebook

**Files:**
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Update the existing setup/import cell**

Import `calc_bow_shock_normal_angle` and set
`REFERENCE_VECTOR = np.array([-1.0, 0.0, 0.0])` with a short explanatory
comment.

**Step 2: Calculate angle after normals**

After the existing `calc_bow_shock_normals` call, compute:

```python
normal_angle_deg = calc_bow_shock_normal_angle(normals, REFERENCE_VECTOR)
```

Validate `normal_angle_deg.shape == surface_x.shape` and include its finite
range in the notebook's printed diagnostics.

**Step 3: Add an angle visualization cell**

Create a Y-Z `matplotlib` `pcolormesh` or equivalent plot of
`normal_angle_deg`, set labels `Y [R]`, `Z [R]`, and add a colorbar labelled
`Angle to reference vector [deg]`. Keep the notebook clean: no saved outputs
or execution counts.

**Step 4: Run notebook tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/test_notebook.py -q`

Expected: all notebook checks pass.

**Step 5: Commit**

```bash
git add examples/tecplot_2d_cut.ipynb tests/test_notebook.py
git commit -m "docs: plot bow-shock normal angle"
```

### Task 5: Final verification

**Files:**
- Verify only.

**Step 1: Run the complete test suite**

Run: `PYTHONPATH=src pytest`

Expected: all non-integration tests pass; the three local-sample integration
tests remain skipped.

**Step 2: Run style and notebook checks**

Run:

```bash
ruff check src tests examples --ignore E402
ruff format --check src tests examples/bow_shock_workflow.py examples/read_tecplot.py examples/plot_2d_cut.py
git diff --check
```

Expected: all checks pass. E402 is ignored only for the notebook setup cell,
which intentionally adjusts the import path.
