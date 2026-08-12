# MMS Core Dependencies Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make MMS loading and plotting dependencies part of every ShockLink installation.

**Architecture:** Move Matplotlib from the `mms` extra into core project dependencies, then align installation documentation with editable source-based installation. Preserve separate extras only for development and notebook applications.

**Tech Stack:** Python packaging (`pyproject.toml`), pytest, Markdown.

---

### Task 1: Lock the package contract with a failing test

**Files:**
- Modify: `tests/test_architecture.py`

**Step 1:** Change the metadata test to require `matplotlib>=3.8` in
`project.dependencies` and require that `mms` is absent from
`project.optional-dependencies`.

**Step 2:** Run
`PYTHONPATH=src pytest -q tests/test_architecture.py::test_package_metadata_and_mms_dependencies_are_declared`
and confirm it fails against the existing metadata.

### Task 2: Move MMS plotting support into the standard installation

**Files:**
- Modify: `pyproject.toml`

**Step 1:** Add `matplotlib>=3.8` to `project.dependencies` and remove the
`mms` optional-dependency group.

**Step 2:** Rerun the focused metadata test and confirm it passes.

### Task 3: Align installation documentation

**Files:**
- Modify: `README.md`
- Modify: `examples/README.md`

**Step 1:** Replace PyPI-oriented and `.[mms]` instructions with source checkout
and `pip install -e .` instructions so repository data remains available.

**Step 2:** Run `rg -n 'PyPI|\.\[mms\]' README.md examples/README.md` and confirm
there are no stale instructions.

### Task 4: Verify and integrate

**Files:**
- Verify all changed files.

**Step 1:** Run `PYTHONPATH=src pytest -q` and `git diff --check`.

**Step 2:** Commit the implementation, merge the feature branch into `main`,
and rerun the full suite on the merged result.
