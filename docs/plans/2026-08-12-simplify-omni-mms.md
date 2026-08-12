# Simplify OMNI/MMS Data Flow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove unused MMS downloads and centralize OMNI total-temperature normalization.

**Architecture:** The default loader requests only the four MMS sources used by the SWMF workflow and loads OMNI once per interval. `_resolve_series` becomes the sole normalization boundary for charge-neutral density and total temperature, leaving plotting and analysis as simple consumers.

**Tech Stack:** Python, NumPy, pySPEDAS, Matplotlib, pytest.

---

### Task 1: Define the smaller loader contract

**Files:**
- Modify: `tests/mms/test_loading.py`
- Modify: `src/shocklink/mms/loading.py`

1. Add assertions that FPI requests only electron density and ion velocity and that OMNI is requested once during automatic cadence fallback.
2. Run the focused tests and confirm they fail for the current broad request/repeated load.
3. Split interval-level OMNI loading from cadence-level MMS loading, retain OMNI across fallback, and remove unused expected products/conversions.
4. Run `PYTHONPATH=src pytest tests/mms/test_loading.py -q`.

### Task 2: Centralize normalized temperature

**Files:**
- Modify: `tests/mms/test_data.py`
- Modify: `tests/mms/test_analysis.py`
- Modify: `tests/mms/test_plotting.py`
- Modify: `src/shocklink/mms/data.py`
- Modify: `src/shocklink/mms/analysis.py`
- Modify: `src/shocklink/mms/plotting.py`

1. Add tests that `_resolve_series` always returns a valid total-temperature series, using interval bounds for fallback timestamps.
2. Run focused tests and confirm the missing centralized behavior fails.
3. Move fallback insertion into `_resolve_series`; remove fallback branches from plotting and analysis.
4. Delete obsolete MMS-temperature helpers, imports, fixture products, and tests.
5. Run `PYTHONPATH=src pytest tests/mms -q`.

### Task 3: Verify and integrate

**Files:** All changed files.

1. Run `ruff check src tests`.
2. Run `PYTHONPATH=src pytest -q`.
3. Review `git diff main...HEAD`, commit, and merge into `main`.
