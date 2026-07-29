# Notebook Shock-Region Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use the extracted `shockfit` region as the source of the notebook's 2D cut and every downstream operation.

**Architecture:** Global divergence and bow-shock fitting remain on the complete Tecplot grid. The notebook then creates a reduced `UnstructuredGrid` for `shockfit` in `[-5, 5]`, and all slicing, validation, contouring, and plotting operate on that region.

**Tech Stack:** Python, PyVista, Jupyter Notebook, pytest

---

### Task 1: Define the extracted-region workflow

**Files:**
- Modify: `tests/test_notebook.py`

**Step 1: Write failing assertions**

Require notebook source to contain:

```python
from shocklink.bowshock import extract_shockfit_range, fit_bow_shock
SHOCKFIT_RANGE = [-5.0, 5.0]
shock_region = extract_shockfit_range(
    grid,
    lower=SHOCKFIT_RANGE[0],
    upper=SHOCKFIT_RANGE[1],
)
cut = get_2d_cut(shock_region, normal=NORMAL, origin=ORIGIN)
```

Assert the extraction statement occurs after the fit call and before the cut
statement. Require reporting of original point and cell IDs.

**Step 2: Verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/test_notebook.py -q
```

Expected: workflow assertions fail because the notebook slices the full grid.

### Task 2: Use the extracted region

**Files:**
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Update setup and parameters**

Import `extract_shockfit_range` and add the exact range parameter
`SHOCKFIT_RANGE = [-5.0, 5.0]`.

**Step 2: Update the cut cell**

Create `shock_region`, print its counts/bounds/arrays and original-ID
availability, then call `get_2d_cut(shock_region, ...)`.

Leave all validation and plot cells operating on `cut`.

**Step 3: Verify GREEN**

Run notebook tests and expect all to pass.

### Task 3: Verify and commit

Run the complete test suite. Execute the read, divergence, fit, extraction,
cut, pressure-contour, and shock-contour pipeline on `data/3d.dat`; verify all
outputs are nonempty. Commit the notebook and test changes with:

```bash
git add examples/tecplot_2d_cut.ipynb tests/test_notebook.py
git commit -m "docs: cut extracted shock region in notebook"
```
