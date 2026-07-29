# Notebook `div(U)` Figure Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a second `div(U)` figure to the notebook while retaining the pressure figure and fitted-shock overlays.

**Architecture:** Both figures consume the same extracted-region 2D cut. The pressure figure includes pressure isolines and a fitted-shock contour; the divergence figure has an independent scalar map and fitted-shock contour.

**Tech Stack:** Python, PyVista, Jupyter Notebook, pytest

---

### Task 1: Define two plot workflows

**Files:**
- Modify: `tests/test_notebook.py`

**Step 1: Write failing assertions**

Require:

```python
pressure_plotter = plot_2d_cut(cut, scalars="p", ...)
pressure_contours = cut.contour(isosurfaces=15, scalars="P [nPa]")
pressure_plotter.add_mesh(pressure_contours, ...)
pressure_plotter.add_mesh(pressure_shock_contour, ...)

divu_plotter = plot_2d_cut(cut, scalars="div(U)", ...)
divu_plotter.add_mesh(divu_shock_contour, ...)
```

Require two calls to `show(jupyter_backend="static")`.

**Step 2: Verify RED**

Run notebook tests and expect failures because only one plot exists and the
current pressure contour uses `div(U)`.

### Task 2: Update the notebook

**Files:**
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Correct the pressure cell**

Rename its plotter and shock contour variables with a `pressure_` prefix,
change pressure isolines to `"P [nPa]"`, and retain the pressure background.

**Step 2: Populate the final cell**

Create `divu_plotter` using `scalars="div(U)"` and the existing X/Y ranges.
Create a separate `divu_shock_contour`, add it as a thick white line, and show
the second static figure.

**Step 3: Verify GREEN**

Run notebook tests and expect all to pass.

### Task 3: Verify and commit

Execute both rendering pipelines against `data/3d.dat` and the extracted
`[-5, 5]` shock region, confirming nonempty contours. Run the complete suite
and commit:

```bash
git add examples/tecplot_2d_cut.ipynb tests/test_notebook.py
git commit -m "docs: add divu notebook figure"
```
