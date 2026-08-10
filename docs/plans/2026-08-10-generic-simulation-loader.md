# Generic Simulation Loader Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add `shocklink.io.load_simulation()` for normalized Tecplot DAT and converted VTK VTM inputs while preserving the existing `shocklink.tecplot.read_tecplot()` import.

**Architecture:** Move format loading and normalization into a generic `shocklink.io` module. Dispatch time extraction by suffix, normalize every PyVista dataset leaf recursively, return one dataset directly or preserve a multi-zone `MultiBlock`, and leave `shocklink.tecplot` as a thin compatibility facade.

**Tech Stack:** Python 3.11+, NumPy, PyVista/VTK, pytest, Ruff

---

### Task 1: Establish the generic DAT-loading API

**Files:**
- Create: `src/shocklink/io.py`
- Create: `tests/test_io.py`
- Reference: `src/shocklink/tecplot.py`
- Reference: `tests/test_tecplot.py`

**Step 1: Write the failing primary-API tests**

Create `tests/test_io.py` by adapting the existing Tecplot tests to import:

```python
from shocklink.io import TIME_EVENT_KEY, load_simulation
```

Cover the existing DAT contract:

```python
grid = load_simulation(sample_dat)
assert isinstance(grid, pv.UnstructuredGrid)
np.testing.assert_allclose(grid.points, EXPECTED_POINTS)
np.testing.assert_allclose(grid["B [nT]"], EXPECTED_B)
np.testing.assert_allclose(grid["U [km/s]"], EXPECTED_U)
assert np.asarray(grid.field_data[TIME_EVENT_KEY]).item() == EXPECTED_TIME_EVENT
```

Retain tests for explicit component overrides, missing paths, unsupported suffixes, wrapped PyVista failures, missing vectors, nonfinite coordinates, and invalid DAT timestamps. Add one test whose arrays use the converter-cleaned names `X`, `Y`, `Z`, `B_x`, `B_y`, `B_z`, `U_x`, `U_y`, and `U_z` and verify automatic detection.

**Step 2: Run the new tests to verify they fail**

Run:

```bash
pytest -q tests/test_io.py
```

Expected: test collection fails with `ModuleNotFoundError: No module named 'shocklink.io'`.

**Step 3: Implement the minimal DAT loader**

Create `src/shocklink/io.py` with:

```python
TIME_EVENT_KEY = "time_event"

COORDINATE_COMPONENT_CANDIDATES = (
    ("X [R]", "Y [R]", "Z [R]"),
    ("X", "Y", "Z"),
)
MAGNETIC_COMPONENT_CANDIDATES = (
    ("B_x [nT]", "B_y [nT]", "B_z [nT]"),
    ("B_x", "B_y", "B_z"),
)
VELOCITY_COMPONENT_CANDIDATES = (
    ("U_x [km_s]", "U_y [km_s]", "U_z [km_s]"),
    ("U_x [km/s]", "U_y [km/s]", "U_z [km/s]"),
    ("U_x", "U_y", "U_z"),
)
```

Add helpers that:

- parse DAT time with the existing title regex and `parse_datetime`;
- resolve an explicit component triplet or the first complete candidate triplet;
- validate scalar array dimensions and point counts;
- retain finite existing geometry if no coordinate candidate is present;
- compose normalized magnetic and velocity vectors without removing scalar arrays.

Implement the initial signature:

```python
def load_simulation(
    path: str | Path,
    *,
    coordinate_components: tuple[str, str, str] | None = None,
    magnetic_components: tuple[str, str, str] | None = None,
    velocity_components: tuple[str, str, str] | None = None,
    magnetic_name: str = "B [nT]",
    velocity_name: str = "U [km/s]",
) -> pv.DataSet | pv.MultiBlock:
```

For this task, accept `.dat`, require the PyVista root to be `MultiBlock`, require exactly one nonempty `pv.DataSet`, normalize it, attach time metadata, and return it. Export only `TIME_EVENT_KEY` and `load_simulation`.

**Step 4: Run focused tests to verify they pass**

Run:

```bash
pytest -q tests/test_io.py
```

Expected: all new DAT-loader tests pass.

**Step 5: Commit the DAT loader**

Run:

```bash
git add src/shocklink/io.py tests/test_io.py
git commit -m "feat: add generic simulation loader"
```

### Task 2: Add VTM and multi-zone loading

**Files:**
- Modify: `src/shocklink/io.py`
- Modify: `tests/test_io.py`

**Step 1: Write failing VTM round-trip tests**

Use real PyVista saves under `tmp_path`, not a mocked reader. Construct a root `MultiBlock`, set:

```python
root.field_data[TIME_EVENT_KEY] = EXPECTED_TIME_EVENT
root["zone-a"] = structured_or_unstructured_grid
root.save(tmp_path / "sample.vtm")
```

Add tests that prove:

- a single-zone VTM returns its native `StructuredGrid` or `UnstructuredGrid` type;
- valid VTK points are retained when coordinate scalar arrays are absent;
- cleaned scalar component names produce `B [nT]` and `U [km/s]`;
- root `time_event` is copied to the directly returned zone;
- malformed or missing root time metadata raises `DatasetError` before normalization.

**Step 2: Run the single-zone VTM tests to verify they fail**

Run:

```bash
pytest -q tests/test_io.py -k "vtm and not multizone"
```

Expected: failures report that `.vtm` is unsupported.

**Step 3: Implement VTM dispatch and metadata loading**

Extend `load_simulation()` to accept `{'.dat', '.vtm'}`. For `.vtm`, read and validate exactly one root `time_event` value, normalize it with `parse_datetime`, and produce the same millisecond ISO-8601 representation as DAT loading. Keep the `MultiBlock` root requirement.

Generalize component helpers and normalization from `UnstructuredGrid` to `pv.DataSet`. If no coordinate arrays are resolved, validate and preserve `dataset.points`.

**Step 4: Verify single-zone VTM tests pass**

Run:

```bash
pytest -q tests/test_io.py -k "vtm and not multizone"
```

Expected: all selected tests pass.

**Step 5: Write failing recursive multi-zone tests**

Add a VTM fixture containing:

- named structured and unstructured zones;
- one `None` or empty block;
- one nested named `MultiBlock`.

Assert that `load_simulation()` returns the root `MultiBlock`, preserves block count, names, order, empty entries, nesting, and leaf types, and normalizes every nonempty dataset leaf. Add failures for a root with no nonempty datasets and a non-dataset leaf such as `pv.Table`.

Also adapt the DAT multi-zone test so two PyVista zones return a `MultiBlock` instead of raising the legacy single-zone error.

**Step 6: Run multi-zone tests to verify they fail**

Run:

```bash
pytest -q tests/test_io.py -k "multizone or nested or empty or unsupported_leaf"
```

Expected: failures show that the loader still requires one zone or does not preserve recursive blocks.

**Step 7: Implement recursive normalization**

Add a recursive walker that:

```python
def _dataset_leaves(
    block: pv.MultiBlock,
    *,
    source: Path,
    block_path: tuple[str, ...] = (),
) -> list[tuple[tuple[str, ...], pv.DataSet]]:
    ...
```

Walk blocks by index without rebuilding containers. Preserve `None` and empty `pv.DataSet` blocks, recurse into nested `MultiBlock` objects, reject other block types, and collect nonempty dataset leaves with readable block paths. Normalize collected leaves in place and attach the event time to each. Return the sole leaf when the count is one; otherwise return the original root.

**Step 8: Run all loader tests**

Run:

```bash
pytest -q tests/test_io.py
```

Expected: all DAT, VTM, and multi-zone tests pass.

**Step 9: Commit VTM and multi-zone support**

Run:

```bash
git add src/shocklink/io.py tests/test_io.py
git commit -m "feat: load VTM simulation datasets"
```

### Task 3: Replace Tecplot implementation with a compatibility facade

**Files:**
- Modify: `src/shocklink/tecplot.py`
- Modify: `tests/test_tecplot.py`
- Modify: `tests/test_module_boundaries.py`

**Step 1: Write failing compatibility and boundary tests**

Reduce `tests/test_tecplot.py` to focused compatibility behavior:

```python
from shocklink import tecplot

def test_read_tecplot_delegates_to_generic_loader(monkeypatch, tmp_path):
    expected = pv.UnstructuredGrid()
    monkeypatch.setattr(tecplot, "load_simulation", lambda *args, **kwargs: expected)
    assert tecplot.read_tecplot(tmp_path / "sample.vtm") is expected
```

Verify that all keyword arguments are forwarded and that:

```python
tecplot.__all__ == ["TIME_EVENT_KEY", "read_tecplot"]
shocklink.io.__all__ == ["TIME_EVENT_KEY", "load_simulation"]
```

Add an AST-based boundary assertion that `shocklink.tecplot` imports its implementation from `shocklink.io` and contains no PyVista parsing or normalization helpers.

**Step 2: Run compatibility tests to verify they fail**

Run:

```bash
pytest -q tests/test_tecplot.py tests/test_module_boundaries.py
```

Expected: delegation/boundary assertions fail because `tecplot.py` still owns the implementation.

**Step 3: Implement the compatibility facade**

Replace `src/shocklink/tecplot.py` with imports of `TIME_EVENT_KEY` and `load_simulation` plus a documented `read_tecplot()` wrapper with the same accepted keyword parameters as `load_simulation()`. The wrapper returns `load_simulation(path, ...)` without modifying its result.

Do not emit a runtime deprecation warning; existing notebooks and downstream users should remain quiet. Document the preferred new import in the wrapper docstring.

**Step 4: Run loader, compatibility, and boundary tests**

Run:

```bash
pytest -q tests/test_io.py tests/test_tecplot.py tests/test_module_boundaries.py
```

Expected: all selected tests pass.

**Step 5: Commit the module boundary change**

Run:

```bash
git add src/shocklink/tecplot.py tests/test_tecplot.py tests/test_module_boundaries.py
git commit -m "refactor: make tecplot loader a compatibility facade"
```

### Task 4: Migrate current documentation and examples

**Files:**
- Rename: `examples/read_tecplot.py` to `examples/load_simulation.py`
- Modify: `examples/README.md`
- Modify: `examples/bow_shock_workflow.py`
- Modify: `examples/plot_2d_cut.py`
- Modify: `examples/mms_bow_shock_connection.py`
- Modify: `examples/extract_shock.ipynb`
- Modify: `examples/shock_connection.ipynb`
- Modify: `docs/bow-shock-workflow.md`
- Modify: `tests/test_documentation.py`
- Modify: `tests/test_notebook.py`
- Modify: `tests/integration/test_tecplot_sample.py`

**Step 1: Write failing migration assertions**

Update documentation and notebook tests to require `from shocklink.io import ... load_simulation`, calls to `load_simulation(...)`, and the renamed example path. Retain a compatibility assertion only in `tests/test_tecplot.py`; current user-facing files should no longer import `shocklink.tecplot` or call `read_tecplot`.

Update the integration test to load the existing DAT sample through `load_simulation()` while retaining its scientific assertions.

**Step 2: Run migration tests to verify they fail**

Run:

```bash
pytest -q tests/test_documentation.py tests/test_notebook.py tests/integration/test_tecplot_sample.py
```

Expected: assertions fail because examples and notebooks still use the legacy API.

**Step 3: Rename and update user-facing files**

Rename the standalone reader example and update current Python examples, Markdown, and notebook code cells to use:

```python
from shocklink.io import TIME_EVENT_KEY, load_simulation

grid = load_simulation(path)
```

Update prose to state that `.dat` and `.vtm` are supported and that multi-zone inputs return `MultiBlock`. Where an example requires a single dataset for downstream analysis, validate the result and report a clear message if a `MultiBlock` is returned.

Do not edit historical files under `docs/plans/`.

**Step 4: Run migration and loader tests**

Run:

```bash
pytest -q tests/test_documentation.py tests/test_notebook.py tests/integration/test_tecplot_sample.py tests/test_io.py tests/test_tecplot.py
```

Expected: all selected tests pass; the large integration tests may skip when their local sample is unavailable.

**Step 5: Commit the migration**

Run:

```bash
git add docs/bow-shock-workflow.md examples tests/test_documentation.py tests/test_notebook.py tests/integration/test_tecplot_sample.py
git commit -m "docs: migrate examples to generic simulation loader"
```

### Task 5: Verify and integrate

**Files:**
- Verify all changed source, tests, documentation, examples, and notebooks

**Step 1: Run formatting and static checks**

Run:

```bash
ruff format --check src tests examples
ruff check src tests examples --ignore E402
python -m compileall -q src examples
git diff main...HEAD --check
```

Expected: all commands exit successfully with no formatting, lint, syntax, or whitespace errors.

**Step 2: Run focused loader tests**

Run:

```bash
pytest -q tests/test_io.py tests/test_tecplot.py tests/test_module_boundaries.py tests/test_documentation.py tests/test_notebook.py
```

Expected: all focused tests pass.

**Step 3: Run the complete suite**

Run:

```bash
pytest -q
```

Expected: all tests pass apart from documented skips and the pre-existing NumPy binary-compatibility warning.

**Step 4: Review public API and diff scope**

Run:

```bash
python -c "from shocklink.io import load_simulation; from shocklink.tecplot import read_tecplot; print(load_simulation.__name__, read_tecplot.__name__)"
git status --short
git diff --stat main...HEAD
```

Expected: both APIs import, the worktree is clean, and the diff contains only the approved loader, compatibility, tests, examples, documentation, and planning files.

**Step 5: Merge into main**

Following the repository workflow, fast-forward the verified feature branch into `main`, rerun the full suite on `main`, then remove the temporary worktree and merged branch. Preserve the untracked `data/clean_dat.py` and `data/3d_vtk/` files.
