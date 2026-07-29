# Notebook Velocity Divergence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the pressure plot in the Tecplot 2D-cut notebook with a velocity-divergence plot.

**Architecture:** Compute `div(U)` on the loaded three-dimensional PyVista dataset, slice the resulting point array with the existing cut workflow, and plot the derived scalar on the existing plane.

**Tech Stack:** Python, PyVista, NumPy, Jupyter Notebook, pytest

---

### Task 1: Define notebook expectations

**Files:**
- Modify: `tests/test_notebook.py`

**Step 1: Write a failing test**

Require these fragments in the notebook's code:

```python
"calc_velocity_divergence"
"calc_velocity_divergence(grid)"
'SCALARS = "div(U)"'
'"div(U)"'
```

**Step 2: Verify RED**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \\
  python -m pytest tests/test_notebook.py -q
```

Expected: the workflow test fails because the notebook has not yet calculated
or selected velocity divergence.

### Task 2: Replace pressure with velocity divergence

**Files:**
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Update imports and prose**

Import `calc_velocity_divergence` from `shocklink.dataset` and describe the
notebook as plotting velocity divergence.

**Step 2: Compute before slicing**

Immediately after reading the 3D grid, call:

```python
calc_velocity_divergence(grid)
```

Set `SCALARS = "div(U)"`, retain the existing plot limits, and require
`div(U)` in the cut validation set.

**Step 3: Verify GREEN**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \\
  python -m pytest tests/test_notebook.py -q
```

Expected: all notebook tests pass.

### Task 3: Final verification

**Step 1: Run all ordinary tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
```

**Step 2: Confirm notebook scope**

```bash
git diff --cached -- examples/tecplot_2d_cut.ipynb
```

Expected: the staged notebook includes both the user's existing range/metadata
edits and the approved divergence workflow. The user-owned `pressure-z0.png`
remains untracked.

**Step 3: Commit**

```bash
git add examples/tecplot_2d_cut.ipynb tests/test_notebook.py
git commit -m "docs: plot velocity divergence in notebook"
```
