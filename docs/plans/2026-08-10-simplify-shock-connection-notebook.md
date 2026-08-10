# Simplify Shock Connection Notebook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify `shock_connection.ipynb` by relying on default extraction axes and removing duplicated notebook configuration.

**Architecture:** The extraction call omits `y` and `z`, while one local `SURFACE_AXIS` supplies the matching coordinates to normal and connectivity APIs. Notebook metadata is cleaned and the portable data path is restored without changing the scientific workflow.

**Tech Stack:** Jupyter Notebook JSON, Python, NumPy, nbformat, pytest

---

### Task 1: Specify the simplified notebook source

**Files:**
- Modify: `tests/test_notebook.py`

**Step 1:** Add assertions requiring `SURFACE_AXIS`, rejecting the duplicated axis/range variables, and confirming the extraction call omits explicit `y` and `z`.

**Step 2:** Run `PYTHONPATH=src python -m pytest tests/test_notebook.py::test_connection_notebook_documents_launch_and_portable_parameters -q`.

Expected: FAIL because the current notebook uses duplicated Y/Z configuration and the nonportable path.

### Task 2: Simplify and clean the notebook

**Files:**
- Modify: `examples/shock_connection.ipynb`

**Step 1:** Set `DATA_PATH = Path("../data/3d.dat")`, define one `SURFACE_AXIS`, omit `y` and `z` from `get_bow_shock_surface`, and pass the shared axis to normals and connectivity.

**Step 2:** Clear all code-cell outputs and execution counts.

**Step 3:** Run `PYTHONPATH=src python -m pytest tests/test_notebook.py -q`.

Expected: all notebook tests pass.

**Step 4:** Run `python -m ruff check tests/test_notebook.py`.

Expected: PASS.

### Task 3: Commit the notebook cleanup

**Files:**
- Modify: `examples/shock_connection.ipynb`
- Modify: `tests/test_notebook.py`
- Create: `docs/plans/2026-08-10-simplify-shock-connection-notebook-design.md`
- Create: `docs/plans/2026-08-10-simplify-shock-connection-notebook.md`

**Step 1:** Review `git diff --check` and the notebook source diff.

**Step 2:** Commit with `git commit -m "docs: simplify shock connection notebook"`.
