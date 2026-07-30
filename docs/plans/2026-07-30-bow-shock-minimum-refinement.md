# Bow-shock Minimum Refinement Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optionally refine discrete `div(U)` minima to bounded three-point parabolic vertices.

**Architecture:** Keep the current per-column argmin. When `refine_minimum=True`, a private helper replaces only eligible discrete X locations with a local parabola vertex; all other columns retain their discrete X location. The default remains unchanged.

**Tech Stack:** Python, NumPy, PyVista, pytest, Ruff.

---

### Task 1: Test the refinement contract

**Files:**
- Modify: `tests/bowshock/test_surface.py`

**Step 1: Write failing tests**

Test a non-grid-aligned quadratic `div(U)` minimum with `refine_minimum=True`; assert the result is its vertex. Assert the default remains the discrete X point. Add fallback tests for endpoint minima, invalid neighbors, non-strict minima, nonpositive curvature, and out-of-bracket vertices.

**Step 2: Verify RED**

Run: `PYTHONPATH=src pytest tests/bowshock/test_surface.py -q`

Expected: the new keyword is unsupported.

### Task 2: Implement the bounded three-point vertex

**Files:**
- Modify: `src/shocklink/bowshock.py:605-745`
- Test: `tests/bowshock/test_surface.py`

**Step 1: Add the option**

Add `refine_minimum: bool = False` and reject non-booleans with `DatasetError`.

**Step 2: Add the helper and comments**

Use `offset = spacing * (f_left - f_right) / (2 * (f_left - 2*f_center + f_right))`. Accept only an interior index with valid finite neighbors, a strict local minimum, finite positive curvature, and a finite offset within one spacing. Use `np.errstate`; otherwise retain the discrete X point. Explain the local parabola and safeguards in code comments.

**Step 3: Integrate and document**

Use the helper only when enabled and update `get_bow_shock_surface` docstring.

**Step 4: Verify GREEN**

Run: `PYTHONPATH=src pytest tests/bowshock/test_surface.py -q`

Expected: all pass.

**Step 5: Commit**

Commit source and test files with message `feat: refine bow-shock surface minima`.

### Task 3: Verify the branch

**Files:**
- Verify only.

**Step 1:** Run `PYTHONPATH=src pytest`.

**Step 2:** Run `ruff check src tests examples --ignore E402`, `ruff format --check src tests examples/bow_shock_workflow.py examples/read_tecplot.py examples/plot_2d_cut.py`, and `git diff --check`.
