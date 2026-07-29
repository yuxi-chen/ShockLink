# Bow-Shock Normal Field Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a public function that calculates a finite, outward unit-normal vector at every point of a regular bow-shock surface array, filling interior and edge gaps before differentiation.

**Architecture:** Keep the domain operation in the existing flat `shocklink.bowshock` module. Validate and copy the surface and coordinate inputs, fill missing values with SciPy linear interpolation plus nearest-neighbor fallback, calculate coordinate-aware gradients with NumPy, and assemble positive-X unit normals without mutating caller data.

**Tech Stack:** Python 3.11–3.13, NumPy, SciPy `griddata`, pytest, Ruff, PyVista for the existing real-data integration path.

---

Use `@superpowers:test-driven-development` for every behavior change below. Before reporting completion, use `@superpowers:verification-before-completion`.

### Task 1: Define the analytic normal-field contract

**Files:**
- Create: `tests/bowshock/test_normals.py`
- Modify: `src/shocklink/bowshock.py`
- Modify: `pyproject.toml`

**Step 1: Write failing tests for a plane and a paraboloid**

Create `tests/bowshock/test_normals.py` with a small surface helper and two analytic tests:

```python
import numpy as np

from shocklink.bowshock import calc_bow_shock_normals


def _surface_grid(
    y: np.ndarray,
    z: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    return np.meshgrid(y, z, indexing="ij")


def test_calc_bow_shock_normals_matches_plane_on_nonuniform_grid() -> None:
    y = np.array([-2.0, -0.5, 1.0, 3.0])
    z = np.array([-3.0, -1.0, 0.5, 2.5])
    yy, zz = _surface_grid(y, z)
    surface = 5.0 + 0.25 * yy - 0.5 * zz
    expected = np.array([1.0, -0.25, 0.5])
    expected /= np.linalg.norm(expected)

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert normals.shape == surface.shape + (3,)
    np.testing.assert_allclose(normals, expected, atol=1.0e-12)
    np.testing.assert_allclose(np.linalg.norm(normals, axis=-1), 1.0)
    assert np.all(normals[..., 0] > 0.0)


def test_calc_bow_shock_normals_matches_paraboloid() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-3.0, 3.0, 7)
    yy, zz = _surface_grid(y, z)
    surface = 10.0 - 0.5 * (yy**2 + zz**2)
    expected = np.stack((np.ones_like(yy), yy, zz), axis=-1)
    expected /= np.linalg.norm(expected, axis=-1, keepdims=True)

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    np.testing.assert_allclose(normals, expected, atol=1.0e-12)
```

**Step 2: Run the focused tests and confirm they fail**

Run:

```bash
python -m pytest tests/bowshock/test_normals.py -q
```

Expected: collection fails because `calc_bow_shock_normals` does not exist.

**Step 3: Add SciPy as a core dependency**

In `pyproject.toml`, add:

```toml
"scipy>=1.14.1",
```

This preserves the package's declared Python 3.11–3.13 support.

**Step 4: Implement the finite-surface calculation**

In `src/shocklink/bowshock.py`:

- import `griddata` from `scipy.interpolate`;
- add a `_normal_axis()` helper that reuses `_surface_axis()` and requires at
  least three coordinates;
- add a `_normal_surface()` helper that converts to a private `float64` copy,
  checks shape, rejects nonnumeric input and infinities, and permits `NaN`;
- add `calc_bow_shock_normals()`.

The public calculation should follow:

```python
dx_dy, dx_dz = np.gradient(
    filled_surface,
    y_values,
    z_values,
    edge_order=2,
)
normal_components = np.stack(
    (np.ones_like(filled_surface), -dx_dy, -dx_dz),
    axis=-1,
)
normal_magnitudes = np.linalg.norm(
    normal_components,
    axis=-1,
    keepdims=True,
)
normals = normal_components / normal_magnitudes
```

For this task, a fully finite surface can be copied directly into
`filled_surface`. Add `"calc_bow_shock_normals"` to the module's `__all__`.

**Step 5: Run the focused tests and confirm they pass**

Run:

```bash
python -m pytest tests/bowshock/test_normals.py -q
```

Expected: 2 tests pass.

**Step 6: Commit**

```bash
git add pyproject.toml src/shocklink/bowshock.py tests/bowshock/test_normals.py
git commit -m "feat: calculate bow-shock normal field"
```

### Task 2: Fill missing surface values before differentiation

**Files:**
- Modify: `tests/bowshock/test_normals.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Write failing interpolation tests**

Add tests that cover both interpolation stages:

```python
def test_calc_bow_shock_normals_interpolates_interior_hole() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-2.0, 2.0, 5)
    yy, zz = _surface_grid(y, z)
    surface = 4.0 + 0.5 * yy - 0.25 * zz
    surface[2, 2] = np.nan
    expected = np.array([1.0, -0.5, 0.25])
    expected /= np.linalg.norm(expected)

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert np.isfinite(normals).all()
    np.testing.assert_allclose(normals, expected, atol=1.0e-12)


def test_calc_bow_shock_normals_fills_edge_and_corner_gaps() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-2.0, 2.0, 5)
    yy, zz = _surface_grid(y, z)
    surface = 6.0 - 0.2 * yy**2 - 0.3 * zz**2
    surface[0, :] = np.nan
    surface[-1, -1] = np.nan

    normals = calc_bow_shock_normals(surface, y=y, z=z)

    assert np.isfinite(normals).all()
    np.testing.assert_allclose(np.linalg.norm(normals, axis=-1), 1.0)
    assert np.all(normals[..., 0] > 0.0)
```

Do not assert exact analytic normals in nearest-extrapolated edge regions;
nearest fallback deliberately prioritizes a complete field over edge accuracy.

**Step 2: Run the new tests and confirm they fail**

Run:

```bash
python -m pytest tests/bowshock/test_normals.py \
  -k "interpolates or fills_edge" -q
```

Expected: failures caused by non-finite normal output.

**Step 3: Implement linear interpolation and nearest fallback**

Add a private helper that:

1. returns the copied input immediately when every value is finite;
2. requires at least three finite samples when gaps exist;
3. creates the Y-Z mesh with `indexing="ij"`;
4. calls `griddata(valid_points, valid_values, (yy, zz), method="linear")`;
5. fills every still-missing target with a second `griddata(...,
   method="nearest")` call;
6. restores the original finite samples exactly;
7. raises `DatasetError` if interpolation fails or leaves a non-finite result.

Use `Exception` as the wrapper boundary around SciPy calls so Qhull,
`ValueError`, and other interpolation failures receive one stable public
`DatasetError` contract without catching process-level interrupts.

**Step 4: Run the focused test file**

Run:

```bash
python -m pytest tests/bowshock/test_normals.py -q
```

Expected: all tests in the file pass.

**Step 5: Commit**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_normals.py
git commit -m "feat: interpolate gaps in bow-shock surfaces"
```

### Task 3: Complete validation and immutability coverage

**Files:**
- Modify: `tests/bowshock/test_normals.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Write failing input-validation tests**

Add tests for:

- `y` or `z` with fewer than three entries;
- multidimensional, non-finite, duplicate, or decreasing axes;
- nonnumeric `surface_x`;
- a surface with the wrong shape;
- positive or negative infinity in the surface;
- fewer than three finite surface values when interpolation is required;
- finite samples that are collinear and make linear interpolation degenerate;
- a monkeypatched `griddata` failure;
- a monkeypatched interpolation result that remains non-finite.

Use `pytest.mark.parametrize` for table-driven argument errors and match clear
`DatasetError` message fragments such as `"at least three"`, `"shape"`,
`"numeric"`, `"infinity"`, and `"Could not interpolate"`.

**Step 2: Write the immutability and public-export test**

```python
def test_calc_bow_shock_normals_does_not_modify_inputs() -> None:
    y = np.linspace(-2.0, 2.0, 5)
    z = np.linspace(-3.0, 3.0, 7)
    yy, zz = _surface_grid(y, z)
    surface = 5.0 - yy**2 - zz**2
    surface[0, 0] = np.nan
    original_surface = surface.copy()
    original_y = y.copy()
    original_z = z.copy()

    calc_bow_shock_normals(surface, y=y, z=z)

    np.testing.assert_array_equal(surface, original_surface)
    np.testing.assert_array_equal(y, original_y)
    np.testing.assert_array_equal(z, original_z)


def test_calc_bow_shock_normals_is_publicly_exported() -> None:
    import shocklink.bowshock as bowshock

    assert "calc_bow_shock_normals" in bowshock.__all__
```

Use `equal_nan=True` if required by the installed NumPy assertion behavior.

**Step 3: Run validation tests and confirm the new cases fail**

Run:

```bash
python -m pytest tests/bowshock/test_normals.py -q
```

Expected: the new validation cases fail until their explicit checks and error
translation are present.

**Step 4: Finish validation and stable error translation**

Complete the private validation helpers and wrap malformed derivative or
normal output in `DatasetError`. Ensure:

- the input surface and axes are never written to;
- original finite samples are restored after interpolation;
- the returned shape is exactly `(len(y), len(z), 3)`;
- all returned components are finite;
- all X components are strictly positive.

**Step 5: Run focused quality checks**

Run:

```bash
python -m pytest tests/bowshock/test_normals.py -q
python -m ruff check src/shocklink/bowshock.py tests/bowshock/test_normals.py
python -m ruff format --check src/shocklink/bowshock.py tests/bowshock/test_normals.py
```

Expected: all commands pass.

**Step 6: Commit**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_normals.py
git commit -m "test: validate bow-shock normal calculation"
```

### Task 4: Exercise normals on the real Tecplot sample

**Files:**
- Modify: `tests/integration/test_tecplot_sample.py`

**Step 1: Extend the existing bow-shock surface integration test**

Import `calc_bow_shock_normals` and, after extracting `surface`, add:

```python
normals = calc_bow_shock_normals(surface, y=y, z=z)

assert normals.shape == surface.shape + (3,)
assert np.isfinite(normals).all()
np.testing.assert_allclose(np.linalg.norm(normals, axis=-1), 1.0)
assert np.all(normals[..., 0] > 0.0)
```

This intentionally uses the existing opt-in `data/3d.dat` path and its
extracted shock region. Do not modify the notebook for this feature.

**Step 2: Run the real-data integration test**

Run:

```bash
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 \
python -m pytest \
  tests/integration/test_tecplot_sample.py::test_real_batsrus_sample_extracts_bow_shock_surface_array \
  -q
```

Expected: 1 test passes and the real surface produces finite outward unit
normals, including any locations filled from missing surface values.

**Step 3: Commit**

```bash
git add tests/integration/test_tecplot_sample.py
git commit -m "test: calculate normals on Tecplot sample"
```

### Task 5: Verify the complete package

**Files:**
- Verify only; modify code or tests only if a check exposes a real defect.

**Step 1: Run the focused bow-shock suite**

Run:

```bash
python -m pytest tests/bowshock -q
```

Expected: all bow-shock tests pass.

**Step 2: Run the complete default suite**

Run:

```bash
python -m pytest -q
```

Expected: all non-opt-in tests pass; large Tecplot tests are skipped unless
the environment variable is set.

**Step 3: Run project-wide static checks**

Run:

```bash
python -m ruff check src tests
python -m ruff format --check src tests
git diff --check
```

Expected: all commands exit successfully with no diagnostics.

**Step 4: Inspect scope and history**

Run:

```bash
git status --short
git log --oneline --decorate -8
```

Expected: only intentional work is present, the flat `src/shocklink/`
structure remains unchanged, and no notebook modification or generated
artifact was introduced.

**Step 5: Commit any verification-only corrections**

If verification required a correction, repeat the failing command and commit
only that correction:

```bash
git add <corrected-files>
git commit -m "fix: finalize bow-shock normal calculation"
```

If no correction was required, do not create an empty commit.
