# Shock Connection Notebook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a clean `shock_connection.ipynb` that mirrors the end-to-end MMS bow-shock connection script interactively.

**Architecture:** Keep the notebook as a thin public-API workflow: load Tecplot and MMS data, derive existing outputs, call `analyze_shock_connection`, and call the reusable 2D/3D plotters. Add structural tests without executing the large-data/network notebook.

**Tech Stack:** Jupyter/nbformat, NumPy, PyVista, ShockLink public APIs, pytest.

---

### Task 1: Add notebook structure tests

**Files:**
- Modify: `tests/test_notebook.py`

Write tests requiring `examples/shock_connection.ipynb` to be valid, clean, and
contain public imports, parameter names, `load_mms_data(..., coordinates="gsm")`,
`average_plotted_values`, `analyze_shock_connection`, both plot calls, event and
intersection diagnostics, and portable `DATA_PATH`/launch instructions. Assert
shock extraction precedes MMS loading and analysis follows both.

Run `PYTHONPATH=src pytest tests/test_notebook.py -q` and observe RED because the
new notebook is empty.

### Task 2: Build the notebook

**Files:**
- Modify: `examples/shock_connection.ipynb`

Create markdown and code cells with no execution counts or outputs. Use editable
parameters matching the script, import only public names, use `pv.set_jupyter_backend("static")`,
perform the extraction/MMS/connection pipeline, print diagnostics, and render
`plot_shock_angle_contour` and `plot_shock_connection_3d(show=False)` followed by
`plotter.show(jupyter_backend="static")`.

Run notebook structure tests, `nbformat.validate`, Python AST compilation of code
cells, Ruff on changed Python tests, and `git diff --check`.

### Task 3: Verify and integrate

Run the complete `PYTHONPATH=src pytest -q` suite, inspect notebook cleanliness,
fast-forward the feature branch into `main`, rerun the suite on the merged
checkout, and remove the temporary worktree/branch.
