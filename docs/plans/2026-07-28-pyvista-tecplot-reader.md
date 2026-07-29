# PyVista Tecplot Reader Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a PyVista-based reader that converts BATSRUS Tecplot ASCII data into a geometry-ready `UnstructuredGrid` with magnetic-field and velocity vectors.

**Architecture:** Add one flat `shocklink.tecplot` module. Let PyVista/VTK parse topology and arrays, then normalize the single loaded zone by promoting coordinate components to `grid.points` and composing vector components without adding simulation-specific analysis behavior.

**Tech Stack:** Python 3.11+, PyVista 0.48+, NumPy, pytest, VTK's Tecplot reader.

---

### Task 1: Add the normalized Tecplot reader

**Files:**
- Modify: `pyproject.toml`
- Create: `src/shocklink/tecplot.py`
- Create: `tests/test_tecplot.py`

**Step 1: Add PyVista as a runtime dependency**

Replace the optional direct VTK extra with:

```toml
dependencies = [
  "numpy>=1.26",
  "pyvista>=0.48",
]
```

PyVista owns its compatible VTK dependency.

**Step 2: Write failing reader tests**

Create a small raw PyVista `UnstructuredGrid` with zero-valued points and these
point arrays:

```python
"X [R]", "Y [R]", "Z [R]"
"B_x [nT]", "B_y [nT]", "B_z [nT]"
"U_x [km_s]", "U_y [km_s]", "U_z [km_s]"
```

Monkeypatch `pyvista.read` to return `pyvista.MultiBlock([raw_grid])` and test:

```python
grid = read_tecplot(path)

np.testing.assert_allclose(grid.points, expected_points)
np.testing.assert_allclose(grid["B [nT]"], expected_b)
np.testing.assert_allclose(grid["U [km/s]"], expected_u)
assert isinstance(grid, pv.UnstructuredGrid)
```

Also verify original component arrays remain present.

Add focused tests for:

- missing input;
- non-`.dat` input;
- zero nonempty zones;
- multiple nonempty zones;
- non-`UnstructuredGrid` zone;
- a missing component array;
- inconsistent component lengths; and
- nonfinite coordinates.

**Step 3: Run tests to verify they fail**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/test_tecplot.py -v`

Expected: FAIL because `shocklink.tecplot` does not exist.

**Step 4: Implement the minimal public API**

```python
def read_tecplot(
    path: str | Path,
    *,
    coordinate_components: tuple[str, str, str] = (
        "X [R]",
        "Y [R]",
        "Z [R]",
    ),
    magnetic_components: tuple[str, str, str] = (
        "B_x [nT]",
        "B_y [nT]",
        "B_z [nT]",
    ),
    velocity_components: tuple[str, str, str] = (
        "U_x [km_s]",
        "U_y [km_s]",
        "U_z [km_s]",
    ),
    magnetic_name: str = "B [nT]",
    velocity_name: str = "U [km/s]",
) -> pyvista.UnstructuredGrid:
    ...
```

Implementation details:

- validate the source path before calling PyVista;
- wrap PyVista read exceptions in `DatasetError` with the path;
- accept PyVista's `MultiBlock` result and select exactly one nonempty block;
- validate the block type;
- use a private `_components` helper to validate and column-stack three point
  arrays;
- validate coordinate finiteness;
- assign coordinates to `grid.points`;
- assign the two vector matrices to `grid.point_data`; and
- return the normalized grid.

Do not delete or rename imported component arrays.

**Step 5: Run the reader and full test suites**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/test_tecplot.py -v`

Expected: PASS.

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q`

Expected: all tests PASS.

**Step 6: Commit**

```bash
git add pyproject.toml src/shocklink/tecplot.py tests/test_tecplot.py
git commit -m "feat: read BATSRUS Tecplot data with PyVista"
```

### Task 2: Add the real sample integration test and example

**Files:**
- Modify: `.gitignore`
- Modify: `pyproject.toml`
- Create: `tests/integration/test_tecplot_sample.py`
- Create: `examples/read_tecplot.py`

**Step 1: Ignore large local simulation outputs**

Add:

```gitignore
data/*.dat
```

Do not add the 1.3 GB sample to Git or package artifacts.

Register an `integration` pytest marker in `pyproject.toml`.

**Step 2: Write the integration test**

Skip unless `SHOCKLINK_RUN_LARGE_DATA_TESTS=1` and `data/3d.dat` exists. Test:

```python
grid = read_tecplot(sample)

assert grid.n_points == 5_695_488
assert grid.n_cells == 5_809_895
assert grid.bounds == pytest.approx((-220, 31.5, -126, 126, -126, 126))
assert grid["B [nT]"].shape == (grid.n_points, 3)
assert grid["U [km/s]"].shape == (grid.n_points, 3)
np.testing.assert_allclose(
    grid["B [nT]"][:10, 0],
    grid["B_x [nT]"][:10],
)
np.testing.assert_allclose(
    grid["U [km/s]"][:10, 2],
    grid["U_z [km_s]"][:10],
)
```

**Step 3: Run the test to verify it fails before normalization exists**

This test is added after Task 1, so validate its effectiveness by temporarily
monkeypatching the vector or coordinate normalization to no-op, observe the
expected assertion failure, restore the implementation, and rerun.

**Step 4: Add a runnable example**

`examples/read_tecplot.py` accepts an optional path argument defaulting to
`data/3d.dat`, calls `read_tecplot`, and prints the grid summary, bounds, point
arrays, and active vectors. It does not open an interactive plotter.

**Step 5: Run the real sample**

Run:

```bash
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src \
python -m pytest tests/integration/test_tecplot_sample.py -v
```

Expected: PASS using the local 1.3 GB sample.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python examples/read_tecplot.py data/3d.dat
```

Expected: summary reports corrected nonzero bounds plus `B [nT]` and
`U [km/s]`.

**Step 6: Commit**

```bash
git add .gitignore pyproject.toml tests/integration/test_tecplot_sample.py examples/read_tecplot.py
git commit -m "test: verify PyVista reader with BATSRUS sample"
```

### Task 3: Remove stale ParaView planning and verify the distribution

**Files:**
- Modify: `docs/plans/2026-07-28-shocklink-repository.md`
- Modify: `tests/test_source_layout.py`

**Step 1: Write a failing planning assertion**

Extend the planning regression test to reject references to `ParaView`,
`pvpython`, or `shocklink.paraview` in the repository implementation plan.

**Step 2: Run it to verify it fails**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/test_source_layout.py -v`

Expected: FAIL because the older implementation plan still describes ParaView.

**Step 3: Replace the stale plan section**

Rewrite the integration task around flat `src/shocklink/tecplot.py`, PyVista,
the normalized vectors, and the opt-in sample test. Update dependencies,
commands, documentation targets, and CI descriptions accordingly.

**Step 4: Run final verification**

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q`

Expected: all ordinary tests PASS with the large integration test skipped.

Run the large integration test again.

Build the wheel and inspect it to verify:

- `shocklink/tecplot.py` is present;
- no `data/*.dat` file is included; and
- package metadata requires PyVista.

**Step 5: Commit**

```bash
git add docs/plans/2026-07-28-shocklink-repository.md tests/test_source_layout.py docs/plans/2026-07-28-pyvista-tecplot-reader-design.md docs/plans/2026-07-28-pyvista-tecplot-reader.md
git commit -m "docs: replace ParaView plan with PyVista reader"
```
