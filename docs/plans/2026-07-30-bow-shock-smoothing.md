# Bow-shock Surface Smoothing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Smooth regular bow-shock X surfaces with a NaN-aware Gaussian filter.

**Architecture:** Add one public `bowshock.py` function and export it. It validates a two-dimensional real surface, validates scalar or `(2,)` positive Gaussian widths, filters values and weights separately with `scipy.ndimage.gaussian_filter`, and optionally restores the input NaN mask.

**Tech Stack:** NumPy, SciPy, pytest, Ruff.

---

### Task 1: Test the public smoothing behavior

**Files:**
- Modify: `tests/bowshock/test_surface.py`

**Step 1:** Add failing tests for reduced central perturbation, NaN-aware smoothing, `preserve_nan` behavior, unmodified input, invalid surface/sigma/options, and public export.

**Step 2:** Run `PYTHONPATH=src pytest tests/bowshock/test_surface.py -q` and confirm the import fails.

### Task 2: Implement and verify

**Files:**
- Modify: `src/shocklink/bowshock.py`
- Test: `tests/bowshock/test_surface.py`

**Step 1:** Add `smooth_bow_shock_surface` and a NumPy-style docstring. Use normalized Gaussian convolution and comments describing why values and weights are filtered separately.

**Step 2:** Run the focused test suite until green, then Ruff and the full test suite.

**Step 3:** Commit source and tests as `feat: smooth bow-shock surfaces`.
