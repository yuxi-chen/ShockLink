# Continue SWMF Run Numbers Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Start each SWMF batch after the highest existing `res/run<number>_*` directory.

**Architecture:** Add a small result-index discovery helper to the standalone runner and use its return value when constructing jobs. Preserve sorted inputs, sequential execution, and collision preflight.

**Tech Stack:** Python standard library, regular expressions, pytest, Markdown.

---

### Task 1: Specify continued numbering

**Files:**
- Modify: `tests/test_run_swmf_inputs.py`

**Step 1:** Replace the obsolete exact-collision test with a test that creates
`run001_*` and `run005_*` directories plus unrelated entries.

**Step 2:** Assert two new sorted inputs use `run006_*` and `run007_*`.

**Step 3:** Run the focused test and confirm it fails because numbering still
starts at `001`.

### Task 2: Implement index discovery

**Files:**
- Modify: `examples/run_swmf_inputs.py`

**Step 1:** Add a helper that scans directories matching `run<digits>_*` and
returns one greater than the maximum, defaulting to one.

**Step 2:** Build new job names starting from that value while retaining
three-digit minimum formatting and collision checks.

**Step 3:** Run `PYTHONPATH=src pytest -q tests/test_run_swmf_inputs.py` and
confirm all runner tests pass.

### Task 3: Document, verify, and integrate

**Files:**
- Modify: `examples/README.md`

**Step 1:** Explain how existing result directories determine `NNN`.

**Step 2:** Run Ruff, focused tests, the full suite, and `git diff --check`.

**Step 3:** Commit, review, merge into `main`, verify again, and remove the
temporary worktree.
