# Shock-Fit Range Extraction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract an inclusive `shockfit` point range and its associated cells as a PyVista `UnstructuredGrid`.

**Architecture:** The bow-shock module validates the domain-specific residual and range, constructs a point mask, and delegates topology extraction to PyVista. The source dataset remains unchanged, while original point and cell IDs are retained in the returned grid.

**Tech Stack:** Python, NumPy, PyVista, pytest

---

### Task 1: Define inclusive extraction

**Files:**
- Create: `tests/bowshock/test_extract.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Write a failing test**

Create an image grid whose point-data `shockfit` is the X coordinate. Call:

```python
region = extract_shockfit_range(
    grid,
    lower=-0.5,
    upper=0.5,
)
```

Assert the result is `pyvista.UnstructuredGrid`, includes points on both
boundaries, retains `shockfit`, and contains `vtkOriginalPointIds` and
`vtkOriginalCellIds`.

**Step 2: Verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/bowshock/test_extract.py -q
```

Expected: import failure because `extract_shockfit_range` is absent.

**Step 3: Implement and verify GREEN**

Validate the named point scalar and finite ordered limits. Build:

```python
mask = np.isfinite(values) & (values >= lower) & (values <= upper)
```

Call:

```python
dataset.extract_points(
    mask,
    adjacent_cells=adjacent_cells,
    include_cells=True,
    pass_point_ids=True,
    pass_cell_ids=True,
)
```

Require `UnstructuredGrid`, export the function, and rerun the focused test.

### Task 2: Cover topology modes and errors

**Files:**
- Modify: `tests/bowshock/test_extract.py`

**Step 1: Add tests**

Verify:

- `adjacent_cells=True` includes cells touching selected points;
- `adjacent_cells=False` includes only fully selected cells;
- custom `shockfit_name`;
- inclusive equal limits;
- non-finite `shockfit` exclusion;
- an empty selection returns an empty grid;
- missing/malformed point arrays;
- empty names, invalid limits, and non-boolean cell mode;
- wrapped extraction errors and invalid return types.

**Step 2: Run focused tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest \
  tests/bowshock/test_extract.py tests/bowshock/test_fit.py \
  tests/bowshock/test_models.py -q
```

Expected: all focused tests pass.

### Task 3: Verify and commit

Run the complete test suite, exercise extraction on the fitted sample data,
build the wheel, verify the flat package layout, and preserve the modified
notebook and untracked `pressure-z0.png`.

Commit only:

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_extract.py
git commit -m "feat: extract shockfit range"
```
