# Shock-Fit Residual and Notebook Overlay Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add the fitted paraboloid residual to the dataset and overlay its zero contour on a pressure contour plot.

**Architecture:** `BowShockParaboloid` evaluates both fitted X and signed residual. `fit_bow_shock()` writes the residual into point data only after a valid fit. The notebook uses that array to generate a geometric contour independently of the pressure visualization.

**Tech Stack:** Python, NumPy, PyVista, Jupyter Notebook, pytest

---

### Task 1: Define residual evaluation

**Files:**
- Modify: `tests/bowshock/test_models.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Write a failing test**

For the model `x0=10`, `a=0.5`, assert:

```python
fit.residual_at(8.0, 2.0, 0.0) == 0.0
fit.residual_at(9.0, 2.0, 0.0) == 1.0
```

Also verify array inputs.

**Step 2: Verify RED**

Run the bow-shock model tests and expect failure because `residual_at` is
absent.

**Step 3: Implement and verify GREEN**

Implement:

```python
return np.asarray(x) - self.x_at(y, z)
```

Run the focused model tests and expect all to pass.

### Task 2: Write `shockfit` into the source dataset

**Files:**
- Modify: `tests/bowshock/test_fit.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Write failing tests**

After fitting the analytic grid, assert:

- `shockfit` exists in point data;
- it equals `fit.residual_at(x, y, z)` at every point;
- residual is zero at `loc0`, `loc1`, and `loc2`;
- `shockfit_name="fit residual"` uses the custom name;
- an existing output array is replaced;
- empty and whitespace-only names raise `DatasetError`.

**Step 2: Verify RED**

Run `tests/bowshock/test_fit.py`; expect missing-array or unexpected-keyword
failures.

**Step 3: Implement and verify GREEN**

Add `shockfit_name: str = "shockfit"` to `fit_bow_shock()`. Validate it before
calculation. After constructing the model, calculate the residual from
`dataset.points`, assign a copied point array, and return the fit.

### Task 3: Define the notebook visualization

**Files:**
- Modify: `tests/test_notebook.py`
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Write failing notebook expectations**

Require:

```python
from shocklink.bowshock import fit_bow_shock
fit = fit_bow_shock(grid)
SCALARS = "p"
pressure_contours = cut.contour(isosurfaces=15, scalars="P [nPa]")
shock_contour = cut.contour(isosurfaces=[0.0], scalars="shockfit")
```

Also require both `plotter.add_mesh()` overlay calls and printed fit
coefficients.

**Step 2: Verify RED**

Run notebook tests and expect workflow failures.

**Step 3: Update the notebook**

Calculate and report the fit before slicing. Validate `P [nPa]`, `div(U)`, and
`shockfit`. Plot pressure with the existing range, add thin dark pressure
isolines without a scalar bar, add the thick high-contrast shock contour, and
show the static plot. Keep cells unexecuted and output-free.

**Step 4: Verify GREEN**

Run notebook tests and expect all to pass.

### Task 4: Final verification

Run all tests, execute the fit and contour construction against `data/3d.dat`
at practical diagnostic resolutions, build the wheel, and inspect the flat
source layout. Commit source/tests first and the notebook/tests second so the
scientific API and example history remain clear.
