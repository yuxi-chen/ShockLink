# Repository Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify redundant tests and historical documentation while preserving
the supported ShockLink APIs and documenting the algorithms used by the repo.

**Architecture:** Keep implementation modules in `src/shocklink`, executable
wrappers in `tools/`, and user-facing examples in `examples/`. Consolidate
algorithm explanations in `docs/algorithms.md`; consolidate repository checks
in `tests/test_architecture.py` and `tests/test_examples.py`.

**Tech Stack:** Python, pytest, NumPy, PyVista, Markdown, setuptools.

---

### Task 1: Record the cleanup design

- Add this design and implementation plan.
- Commit the temporary plan documents so the approved scope is auditable.

### Task 2: Consolidate algorithm documentation

- Add `docs/algorithms.md` covering data normalization, divergence, shock
  fitting/sampling, smoothing, normals, connectivity, MMS, SWMF mapping, and
  plotting semantics.
- Update README and example links to the consolidated guide.
- Remove the two redundant workflow guides.

### Task 3: Merge redundant tests

- Merge package/constants/module-boundary checks into `test_architecture.py`.
- Merge documentation/notebook/example and CLI smoke checks into
  `test_examples.py`.
- Remove historical source-layout assertions and the superseded test modules.

### Task 4: Remove historical artifacts

- Delete all files under `docs/plans/` after the lasting documentation is in
  place.
- Keep runnable examples and scientific regression tests.

### Task 5: Verify and integrate

- Run the focused tests, full pytest suite, lint checks, and package build.
- Review the diff, commit the cleanup branch, and merge it into `main`.
