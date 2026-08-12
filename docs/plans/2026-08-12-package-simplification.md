# Package Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce internal complexity across ShockLink while preserving its public API and numerical behavior, and document the complete scientific algorithm.

**Architecture:** Keep the existing public modules and move cohesive validation, geometry, and presentation branches into private helpers within those modules. Characterization tests define compatibility before each refactor; no new public abstraction is introduced.

**Tech Stack:** Python 3.11+, NumPy, SciPy, PyVista, Matplotlib, pytest, Ruff

---

### Task 1: Establish the compatibility baseline

**Files:**
- Inspect: `pyproject.toml`
- Test: `tests/`

**Step 1: Install the worktree in editable test mode**

Run: `python -m pip install -e '.[test]'`

Expected: installation succeeds using the current worktree.

**Step 2: Run the complete suite**

Run: `pytest -q`

Expected: all non-integration tests pass; if they do not, stop and report the baseline failure.

**Step 3: Record complexity hotspots**

Run: `ruff check src --select C901,PLR0911,PLR0912,PLR0915`

Expected: existing complexity findings in `bowshock.py`, `connectivity.py`, `dataset.py`, `io.py`, and `mms/analysis.py` provide the refactoring target.

### Task 2: Simplify bow-shock validation and sampling

**Files:**
- Modify: `src/shocklink/bowshock.py`
- Test: `tests/bowshock/test_models.py`
- Test: `tests/bowshock/test_extract.py`
- Test: `tests/bowshock/test_surface.py`
- Test: `tests/bowshock/test_normals.py`

**Step 1: Add characterization tests**

Add focused tests for immutable copied model locations, extraction option
validation, surface sampling with invalid probe masks, and scale-safe normal
normalization. Assert existing result arrays and domain-error messages.

**Step 2: Verify the characterization tests**

Run: `pytest -q tests/bowshock`

Expected: tests pass before refactoring, proving they characterize current behavior.

**Step 3: Extract cohesive private helpers**

Refactor `BowShockParaboloid.__post_init__`, `extract_shockfit_range`,
`_normal_components`, and `get_bow_shock_surface`. Helpers should separately
validate scalar/model fields, extraction parameters, normalize vector fields,
and reduce sampled probe chunks. Preserve operation order, error text, copies,
NaN masks, and dtypes.

**Step 4: Verify bow-shock behavior and complexity**

Run: `pytest -q tests/bowshock`

Run: `ruff check src/shocklink/bowshock.py --select C901,PLR0911,PLR0912,PLR0915`

Expected: tests pass and the targeted functions no longer trigger findings.

**Step 5: Commit**

```bash
git add src/shocklink/bowshock.py tests/bowshock
git commit -m "refactor: simplify bow shock internals"
```

### Task 3: Simplify connectivity geometry and plotting

**Files:**
- Modify: `src/shocklink/connectivity.py`
- Test: `tests/test_connectivity.py`

**Step 1: Add characterization tests**

Add tests that lock down coplanar-line ambiguity, duplicate intersection
removal, custom plot ranges, default plot ranges, and contour-level validation.

**Step 2: Verify the characterization tests**

Run: `pytest -q tests/test_connectivity.py`

Expected: tests pass before refactoring.

**Step 3: Extract geometry and plot helpers**

Move coplanar overlap detection, hit construction/deduplication, contour-level
validation, plot-bound calculation, and metadata rendering into narrowly named
private helpers. Keep Möller--Trumbore arithmetic, tolerance scaling, selected
hit ordering, visual defaults, and lazy Matplotlib import unchanged.

**Step 4: Verify connectivity behavior and complexity**

Run: `pytest -q tests/test_connectivity.py`

Run: `ruff check src/shocklink/connectivity.py --select C901,PLR0911,PLR0912,PLR0915`

Expected: tests pass and the two targeted public/private functions no longer trigger findings.

**Step 5: Commit**

```bash
git add src/shocklink/connectivity.py tests/test_connectivity.py
git commit -m "refactor: simplify connectivity workflow"
```

### Task 4: Simplify simulation and MMS orchestration

**Files:**
- Modify: `src/shocklink/dataset.py`
- Modify: `src/shocklink/io.py`
- Modify: `src/shocklink/mms/analysis.py`
- Test: `tests/test_dataset_derivatives.py`
- Test: `tests/test_io.py`
- Test: `tests/mms/test_analysis.py`

**Step 1: Add characterization tests**

Cover derivative-filter result validation, input-path resolution for DAT/VTM
and VTM directories, and component/magnitude averaging with missing products.
Assert current return types and error messages.

**Step 2: Verify the characterization tests**

Run: `pytest -q tests/test_dataset_derivatives.py tests/test_io.py tests/mms/test_analysis.py`

Expected: tests pass before refactoring.

**Step 3: Extract orchestration helpers**

Separate derivative-result validation from filter invocation, source discovery
from format loading, and per-product averaging from result assembly. Do not
change supported file formats, field names, finite-value policy, or averaging
formulae.

**Step 4: Verify workflow behavior and complexity**

Run: `pytest -q tests/test_dataset_derivatives.py tests/test_io.py tests/mms/test_analysis.py`

Run: `ruff check src/shocklink/dataset.py src/shocklink/io.py src/shocklink/mms/analysis.py --select C901,PLR0911,PLR0912,PLR0915`

Expected: tests pass and targeted complexity findings are removed.

**Step 5: Commit**

```bash
git add src/shocklink/dataset.py src/shocklink/io.py src/shocklink/mms/analysis.py tests
git commit -m "refactor: simplify data workflows"
```

### Task 5: Complete the algorithm guide

**Files:**
- Modify: `docs/algorithms.md`
- Modify: `README.md`
- Test: `tests/test_architecture.py`

**Step 1: Add documentation checks**

Extend the architecture test to verify that the guide names every pipeline
stage and links to the correct current implementation modules, including the
`shocklink.mms` package rather than the removed `mms.py` module.

**Step 2: Run the check to verify it fails**

Run: `pytest -q tests/test_architecture.py`

Expected: failure because the guide does not yet include every required stage or correct source link.

**Step 3: Rewrite the guide around data flow and equations**

Document inputs and normalization; divergence; paraboloid landmark selection;
residual extraction; chunked sampling; parabolic refinement; NaN-aware
smoothing; gap filling and normals; angle calculation; triangulation;
scaled Möller--Trumbore intersection and deduplication; MMS interpolation and
averaging; PARAM mapping; outputs; complexity; and scientific limitations.
Keep README's overview concise and point to the guide.

**Step 4: Verify documentation checks**

Run: `pytest -q tests/test_architecture.py`

Expected: pass.

**Step 5: Commit**

```bash
git add README.md docs/algorithms.md tests/test_architecture.py
git commit -m "docs: explain the complete ShockLink algorithm"
```

### Task 6: Verify, review, and integrate

**Files:**
- Review: all changed files

**Step 1: Run static checks**

Run: `ruff check src tests`

Run: `ruff format --check src tests`

Expected: both pass.

**Step 2: Run the complete suite once**

Run: `pytest -q`

Expected: all tests pass.

**Step 3: Inspect compatibility and scope**

Run: `git diff main...HEAD --check`

Run: `git diff main...HEAD --stat`

Review public signatures, imports, defaults, exception types/messages, array
shape conventions, and numerical operation order.

**Step 4: Commit any review corrections**

Stage only relevant files and commit with a focused message.

**Step 5: Merge to main**

From the primary checkout, merge `refactor/simplify-package` into `main` with a
non-interactive Git command, rerun `pytest -q`, then remove the worktree.
