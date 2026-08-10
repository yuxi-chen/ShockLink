# Default Bow-Shock Surface Axes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Give `get_bow_shock_surface` default Y and Z grids equal to `np.linspace(-30, 30, 241)`.

**Architecture:** Store each default as a private, read-only module-level NumPy array and reference those arrays from the keyword-only function signature. The existing coordinate validation and surface sampling remain unchanged.

**Tech Stack:** Python, NumPy, PyVista, pytest

---

### Task 1: Default transverse axes

**Files:**
- Modify: `src/shocklink/bowshock.py:663-683`
- Test: `tests/bowshock/test_surface.py`

**Step 1: Write the failing test**

Add a test that calls `get_bow_shock_surface` without `y` or `z` on a small
dataset and asserts that the result shape is `(241, 241)`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/bowshock/test_surface.py::test_get_bow_shock_surface_uses_default_transverse_axes -q`

Expected: FAIL because `y` and `z` are required keyword-only arguments.

**Step 3: Write minimal implementation**

Add read-only defaults created with `np.linspace(-30.0, 30.0, 241)` and assign
them as the `y` and `z` defaults. Update the parameter documentation with the
default range and count.

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/bowshock/test_surface.py::test_get_bow_shock_surface_uses_default_transverse_axes -q`

Expected: PASS.

**Step 5: Verify broader behavior**

Run: `python -m pytest tests/bowshock/test_surface.py -q`

Expected: all surface tests pass.

**Step 6: Commit**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_surface.py docs/plans/2026-08-10-default-surface-axes-design.md docs/plans/2026-08-10-default-surface-axes.md
git commit -m "feat: default bow-shock surface axes"
```
