# SWMF Runner and Batch Connections Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rename the SWMF runner, batch-process completed simulations into MMS connection figures, and align documentation with current data handling.

**Architecture:** Keep both examples as editable, constant-driven scripts. The connection batch script calls the public workflow API directly and isolates errors per run directory; documentation describes the same data flow and filenames exercised by tests.

**Tech Stack:** Python, pathlib, ShockLink public APIs, pytest, Markdown, nbformat JSON.

---

### Task 1: Rename the sequential runner

**Files:**
- Rename: `examples/run_swmf_inputs.py` to `examples/run_swmf.py`
- Rename: `tests/test_run_swmf_inputs.py` to `tests/test_run_swmf.py`
- Modify: `tests/test_examples.py`

1. Update tests to require the new path and reject stale references.
2. Run the focused tests and confirm failure.
3. Rename the script/test and update test constants.
4. Run `PYTHONPATH=src pytest tests/test_run_swmf.py tests/test_examples.py -q`.

### Task 2: Add batch result processing

**Files:**
- Create: `examples/process_swmf_results.py`
- Create: `tests/test_process_swmf_results.py`

1. Test sorted `runNNN*` discovery, recursive lexicographic latest `*.dat`/`*.vtm` selection, local `PARAM.in`, output directory, and skip/continue behavior.
2. Run the focused test and confirm failure because the script is absent.
3. Implement the minimal public-API batch loop and executable script.
4. Run `PYTHONPATH=src pytest tests/test_process_swmf_results.py -q`.

### Task 3: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `examples/README.md`
- Modify: `docs/algorithms.md`
- Modify: `examples/mms_example.ipynb`
- Modify: `tests/test_examples.py`

1. Add assertions for current runner/batch references and current density/temperature wording.
2. Run documentation tests and confirm stale content fails.
3. Update Markdown and notebook narrative.
4. Validate notebooks and run `PYTHONPATH=src pytest tests/test_examples.py -q`.

### Task 4: Verify and integrate

1. Run `ruff check src tests` and `git diff --check`.
2. Run `PYTHONPATH=src pytest -q`.
3. Review the diff, commit, merge into `main`, rerun the full suite, and remove the worktree.
