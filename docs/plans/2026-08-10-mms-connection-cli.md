# MMS Connection CLI and API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Provide a reusable Python API for the notebook's MMS bow-shock workflow and a `tools/` CLI that saves 2D and selectable 3D plots.

**Architecture:** `shocklink.mms_connection` owns interval resolution, simulation/MMS orchestration, result dataclasses, and plot-file saving. `tools/mms_bow_shock_connection.py` owns argparse, user-facing output, and process status. The old example entry point is relocated to the tools interface.

**Tech Stack:** Python, NumPy, PyVista, Matplotlib, pySPEDAS, argparse, pathlib, pytest

---

### Task 1: Define the API and CLI contracts

**Files:**
- Create: `tests/test_mms_connection.py`
- Create: `tests/test_mms_connection_tool.py`

Write failing tests for event-centered MMS intervals, pipeline orchestration,
PNG/HTML/both output modes, and CLI help flags.

### Task 2: Implement reusable workflow functions

**Files:**
- Create: `src/shocklink/mms_connection.py`

Implement the result/path dataclasses, interval resolution, notebook-equivalent
analysis pipeline, and off-screen plot exporters. Keep CLI parsing out of the
source module.

### Task 3: Implement the tools CLI

**Files:**
- Create: `tools/mms_bow_shock_connection.py`
- Delete: `examples/mms_bow_shock_connection.py`

Expose simulation path, MMS interval, output directory/prefix, 3D format, and
analysis settings through argparse. Report output paths and return nonzero on
workflow or export errors.

### Task 4: Update documentation and contracts

**Files:**
- Modify: `README.md`
- Modify: `examples/README.md`
- Modify: `docs/mms-bow-shock-connection.md`
- Modify: `tests/test_documentation.py`

Document automatic event-centered intervals, static PNG/interactive HTML output,
the Trame requirement, and direct Python API usage.

### Task 5: Verify and integrate

Run targeted tests and Ruff, then the full suite. Commit the implementation and
merge the verified branch into `main`.
