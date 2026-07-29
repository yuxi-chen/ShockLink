# Bow-Shock Surface Array Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract the X location of minimum `div(U)` at every coordinate on a user-defined regular Y-Z grid and return those locations as a two-dimensional NumPy array.

**Architecture:** Add a domain-specific `get_bow_shock_surface()` operation to `shocklink.bowshock`. It will create regular X probes for requested Y-Z columns, sample an extracted PyVista region in reusable-locator chunks, and reduce each column to its strongest-compression X coordinate while retaining `NaN` for invalid columns.

**Tech Stack:** Python 3.11+, NumPy, PyVista 0.48+, VTK static cell locator, pytest

---

Implement this plan with @superpowers:test-driven-development. Before
reporting completion, use @superpowers:verification-before-completion.

### Task 1: Recover a known compression surface

**Files:**
- Create: `tests/bowshock/test_surface.py`
- Modify: `src/shocklink/bowshock.py:3-14`
- Modify: `src/shocklink/bowshock.py:337-342`

**Step 1: Write the failing analytic-surface test**

Create `tests/bowshock/test_surface.py`:

```python
import numpy as np
import pyvista as pv

from shocklink.bowshock import get_bow_shock_surface


def _compression_grid(*, name: str = "div(U)") -> pv.ImageData:
    grid = pv.ImageData(
        dimensions=(65, 17, 13),
        spacing=(0.125, 0.25, 0.25),
        origin=(0.0, -2.0, -1.5),
    )
    x, y, z = grid.points.T
    surface_x = 6.0 - 0.25 * y**2 - 0.5 * z**2
    compression = -np.exp(-((x - surface_x) / 0.18) ** 2)
    expansion = 3.0 * np.exp(-((x - (surface_x - 1.0)) / 0.18) ** 2)
    grid.point_data[name] = compression + expansion
    return grid


def _expected_surface(y: np.ndarray, z: np.ndarray) -> np.ndarray:
    yy, zz = np.meshgrid(y, z, indexing="ij")
    return 6.0 - 0.25 * yy**2 - 0.5 * zz**2


def test_get_bow_shock_surface_recovers_minimum_divergence_layer() -> None:
    y = np.array([-1.5, 0.25, 1.75])
    z = np.array([-1.25, 0.5])

    surface = get_bow_shock_surface(
        _compression_grid(),
        y=y,
        z=z,
        x_resolution=321,
    )

    assert surface.shape == (len(y), len(z))
    np.testing.assert_allclose(
        surface,
        _expected_surface(y, z),
        atol=0.15,
    )
```

The positive expansion peak is three times larger in absolute magnitude than
the negative compression peak. Recovering the expected surface therefore
demonstrates that the implementation selects minimum `div(U)`, not maximum
`abs(div(U))`.

**Step 2: Run the test to verify it fails**

Run:

```bash
python -m pytest tests/bowshock/test_surface.py -q
```

Expected: collection fails because `get_bow_shock_surface` is not defined.

**Step 3: Implement the single-batch sampling path**

In `src/shocklink/bowshock.py`, extend the NumPy typing import and add the VTK
locator import:

```python
from numpy.typing import ArrayLike, NDArray
from vtkmodules.vtkCommonDataModel import vtkStaticCellLocator
```

Add this initial implementation before `fit_bow_shock()`:

```python
def _surface_probe_source(
    dataset: pv.DataSet,
    *,
    divergence_name: str,
    divergence: np.ndarray,
) -> pv.DataSet:
    """Return a shallow geometry copy containing only divergence data."""

    source = dataset.copy(deep=False)
    source.point_data.clear()
    source.point_data[divergence_name] = divergence
    source.cell_data.clear()
    source.field_data.clear()
    return source


def get_bow_shock_surface(
    dataset: pv.DataSet,
    *,
    y: ArrayLike,
    z: ArrayLike,
    divergence_name: str = "div(U)",
    x_resolution: int = 512,
    x_range: tuple[float, float] | None = None,
) -> NDArray[np.float64]:
    """Return strongest-compression X locations on a regular Y-Z grid."""

    y_values = np.asarray(y, dtype=np.float64)
    z_values = np.asarray(z, dtype=np.float64)
    divergence = np.asarray(dataset.point_data[divergence_name])
    if x_range is None:
        bounds = dataset.bounds
        x_limits = (float(bounds.x_min), float(bounds.x_max))
    else:
        x_limits = x_range
    x_values = np.linspace(
        x_limits[0],
        x_limits[1],
        x_resolution,
        dtype=np.float64,
    )

    yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
    column_y = yy.reshape(-1)
    column_z = zz.reshape(-1)
    points = np.empty(
        (len(column_y) * len(x_values), 3),
        dtype=np.float64,
    )
    points[:, 0] = np.tile(x_values, len(column_y))
    points[:, 1] = np.repeat(column_y, len(x_values))
    points[:, 2] = np.repeat(column_z, len(x_values))

    source = _surface_probe_source(
        dataset,
        divergence_name=divergence_name,
        divergence=divergence,
    )
    locator = vtkStaticCellLocator()
    locator.SetDataSet(source)
    locator.BuildLocator()
    sampled = pv.PolyData(points).sample(
        source,
        locator=locator,
        pass_cell_data=False,
        pass_point_data=False,
        pass_field_data=False,
    )
    sampled_divergence = np.asarray(
        sampled.point_data[divergence_name]
    ).reshape(len(column_y), len(x_values))
    valid = np.asarray(
        sampled.point_data["vtkValidPointMask"]
    ).astype(bool).reshape(len(column_y), len(x_values))
    valid &= np.isfinite(sampled_divergence)

    surface = np.full(len(column_y), np.nan, dtype=np.float64)
    has_valid = valid.any(axis=1)
    candidates = np.where(valid, sampled_divergence, np.inf)
    minima = np.argmin(candidates, axis=1)
    surface[has_valid] = x_values[minima[has_valid]]
    return surface.reshape(len(y_values), len(z_values))
```

Add `"get_bow_shock_surface"` to `bowshock.__all__`.

This is deliberately the smallest path needed for the analytic test.
Validation, chunking, and exception translation come in later tasks.

**Step 4: Run the analytic test**

Run:

```bash
python -m pytest tests/bowshock/test_surface.py -q
```

Expected: `1 passed`.

**Step 5: Commit the core behavior**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_surface.py
git commit -m "feat: detect bow-shock surface on yz grid"
```

### Task 2: Chunk columns and preserve invalid locations

**Files:**
- Modify: `tests/bowshock/test_surface.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Add failing chunking and gap tests**

Append:

```python
def test_get_bow_shock_surface_chunks_columns_without_changing_results(
    monkeypatch,
) -> None:
    grid = _compression_grid()
    y = np.array([-1.5, 0.0, 1.5])
    z = np.array([-1.0, 1.0])
    original_sample = pv.PolyData.sample
    calls = 0

    def count_sample_calls(self, *args, **kwargs):
        nonlocal calls
        calls += 1
        return original_sample(self, *args, **kwargs)

    monkeypatch.setattr(pv.PolyData, "sample", count_sample_calls)

    chunked = get_bow_shock_surface(
        grid,
        y=y,
        z=z,
        x_resolution=161,
        chunk_size=2,
    )

    assert calls == 3
    calls = 0
    single_batch = get_bow_shock_surface(
        grid,
        y=y,
        z=z,
        x_resolution=161,
        chunk_size=100,
    )
    assert calls == 1
    np.testing.assert_array_equal(chunked, single_batch)


def test_get_bow_shock_surface_keeps_invalid_columns_as_nan() -> None:
    surface = get_bow_shock_surface(
        _compression_grid(),
        y=np.array([-3.0, 0.0, 3.0]),
        z=np.array([0.0]),
        x_resolution=161,
        chunk_size=1,
    )

    assert surface.shape == (3, 1)
    assert np.isnan(surface[0, 0])
    assert np.isfinite(surface[1, 0])
    assert np.isnan(surface[2, 0])


def test_get_bow_shock_surface_accepts_custom_name_and_x_range() -> None:
    y = np.array([0.0])
    z = np.array([0.0])

    surface = get_bow_shock_surface(
        _compression_grid(name="compression"),
        y=y,
        z=z,
        divergence_name="compression",
        x_range=(5.0, 7.0),
        x_resolution=81,
        chunk_size=1,
    )

    np.testing.assert_allclose(surface, [[6.0]], atol=0.05)


def test_get_bow_shock_surface_does_not_modify_input() -> None:
    grid = _compression_grid()
    original_points = np.array(grid.points, copy=True)
    original_names = list(grid.point_data)
    original_divergence = np.array(grid.point_data["div(U)"], copy=True)

    get_bow_shock_surface(
        grid,
        y=np.array([0.0]),
        z=np.array([0.0]),
        x_resolution=81,
        chunk_size=1,
    )

    np.testing.assert_array_equal(grid.points, original_points)
    assert list(grid.point_data) == original_names
    np.testing.assert_array_equal(
        grid.point_data["div(U)"],
        original_divergence,
    )
```

**Step 2: Run the new tests to verify the public API is incomplete**

Run:

```bash
python -m pytest tests/bowshock/test_surface.py -q
```

Expected: failures report that `chunk_size` is an unexpected argument.

**Step 3: Refactor the sampler into reusable-locator chunks**

Add `chunk_size: int = 1024` to `get_bow_shock_surface()`. Replace the
single-batch point construction and reduction with:

```python
    surface = np.full(len(column_y), np.nan, dtype=np.float64)
    for start in range(0, len(column_y), chunk_size):
        stop = min(start + chunk_size, len(column_y))
        count = stop - start
        points = np.empty(
            (count * len(x_values), 3),
            dtype=np.float64,
        )
        points[:, 0] = np.tile(x_values, count)
        points[:, 1] = np.repeat(column_y[start:stop], len(x_values))
        points[:, 2] = np.repeat(column_z[start:stop], len(x_values))

        sampled = pv.PolyData(points).sample(
            source,
            locator=locator,
            pass_cell_data=False,
            pass_point_data=False,
            pass_field_data=False,
        )
        sampled_divergence = np.asarray(
            sampled.point_data[divergence_name]
        ).reshape(count, len(x_values))
        valid = np.asarray(
            sampled.point_data["vtkValidPointMask"]
        ).astype(bool).reshape(count, len(x_values))
        valid &= np.isfinite(sampled_divergence)

        chunk_surface = np.full(count, np.nan, dtype=np.float64)
        has_valid = valid.any(axis=1)
        candidates = np.where(valid, sampled_divergence, np.inf)
        minima = np.argmin(candidates, axis=1)
        chunk_surface[has_valid] = x_values[minima[has_valid]]
        surface[start:stop] = chunk_surface

    return surface.reshape(len(y_values), len(z_values))
```

Create the source and `vtkStaticCellLocator` once before the loop. Do not
rebuild the locator for each chunk.

**Step 4: Run the surface tests**

Run:

```bash
python -m pytest tests/bowshock/test_surface.py -q
```

Expected: `5 passed`.

**Step 5: Commit chunking and gap behavior**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_surface.py
git commit -m "feat: chunk bow-shock surface sampling"
```

### Task 3: Validate inputs and translate sampling failures

**Files:**
- Modify: `tests/bowshock/test_surface.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Add failing argument-validation tests**

Add `pytest` and `DatasetError` imports, then append:

```python
import pytest

from shocklink.exceptions import DatasetError


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"divergence_name": ""}, "name must not be empty"),
        ({"y": []}, "Y coordinates must be a nonempty 1D array"),
        ({"y": [[0.0, 1.0]]}, "Y coordinates must be a nonempty 1D array"),
        ({"y": [0.0, np.nan]}, "Y coordinates must be finite"),
        ({"y": [0.0, 0.0]}, "Y coordinates must be strictly increasing"),
        ({"z": [1.0, 0.0]}, "Z coordinates must be strictly increasing"),
        ({"x_range": (1.0,)}, "X range must contain two values"),
        ({"x_range": (0.0, np.inf)}, "X range must be finite"),
        ({"x_range": (2.0, 1.0)}, "X range must be strictly increasing"),
        ({"x_resolution": 1}, "X resolution must be an integer of at least 2"),
        ({"x_resolution": True}, "X resolution must be an integer of at least 2"),
        ({"chunk_size": 0}, "Chunk size must be a positive integer"),
        ({"chunk_size": 1.5}, "Chunk size must be a positive integer"),
    ],
)
def test_get_bow_shock_surface_rejects_invalid_arguments(
    changes: dict[str, object],
    message: str,
) -> None:
    arguments: dict[str, object] = {
        "y": np.array([-1.0, 0.0, 1.0]),
        "z": np.array([-1.0, 0.0, 1.0]),
        "x_resolution": 81,
        "chunk_size": 2,
    }
    arguments.update(changes)

    with pytest.raises(DatasetError, match=message):
        get_bow_shock_surface(_compression_grid(), **arguments)
```

**Step 2: Add failing dataset and PyVista-failure tests**

Append:

```python
@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("missing", "unavailable"),
        ("vector", "point scalar"),
        ("nonfinite", "must be finite"),
        ("nonnumeric", "must be numeric"),
    ],
)
def test_get_bow_shock_surface_rejects_invalid_divergence(
    change: str,
    message: str,
) -> None:
    grid = _compression_grid()
    if change == "missing":
        del grid.point_data["div(U)"]
    elif change == "vector":
        grid.point_data["div(U)"] = np.zeros((grid.n_points, 3))
    elif change == "nonfinite":
        values = np.array(grid.point_data["div(U)"], copy=True)
        values[0] = np.nan
        grid.point_data["div(U)"] = values
    else:
        grid.point_data["div(U)"] = np.full(grid.n_points, "invalid")

    with pytest.raises(DatasetError, match=message):
        get_bow_shock_surface(grid, y=[0.0], z=[0.0])


def test_get_bow_shock_surface_rejects_invalid_default_x_bounds() -> None:
    grid = pv.ImageData(dimensions=(1, 2, 2))
    grid.point_data["div(U)"] = np.zeros(grid.n_points)

    with pytest.raises(DatasetError, match="X bounds"):
        get_bow_shock_surface(grid, y=[0.0], z=[0.0])


def test_get_bow_shock_surface_wraps_sampling_failure(monkeypatch) -> None:
    def fail_sampling(self, *_args, **_kwargs):
        raise RuntimeError("VTK failed")

    monkeypatch.setattr(pv.PolyData, "sample", fail_sampling)

    with pytest.raises(
        DatasetError,
        match="Could not sample bow-shock surface: VTK failed",
    ):
        get_bow_shock_surface(
            _compression_grid(),
            y=[0.0],
            z=[0.0],
        )


def test_get_bow_shock_surface_rejects_malformed_sample(monkeypatch) -> None:
    def malformed_sample(self, *_args, **_kwargs):
        return pv.PolyData(self.points)

    monkeypatch.setattr(pv.PolyData, "sample", malformed_sample)

    with pytest.raises(DatasetError, match="missing sampled divergence"):
        get_bow_shock_surface(
            _compression_grid(),
            y=[0.0],
            z=[0.0],
        )
```

**Step 3: Run tests to verify validation failures**

Run:

```bash
python -m pytest tests/bowshock/test_surface.py -q
```

Expected: the new validation and exception-translation cases fail.

**Step 4: Add reusable validators**

Add these private helpers before `get_bow_shock_surface()`:

```python
def _surface_axis(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Return a validated regular-surface coordinate axis."""

    try:
        axis = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DatasetError(
            f"{label} coordinates must contain numbers"
        ) from error
    if axis.ndim != 1 or axis.size == 0:
        raise DatasetError(
            f"{label} coordinates must be a nonempty 1D array"
        )
    if not np.isfinite(axis).all():
        raise DatasetError(f"{label} coordinates must be finite")
    if axis.size > 1 and np.any(np.diff(axis) <= 0.0):
        raise DatasetError(
            f"{label} coordinates must be strictly increasing"
        )
    return axis


def _surface_integer(
    value: int,
    *,
    label: str,
    minimum: int,
) -> int:
    """Return a validated integer surface-extraction option."""

    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        if minimum == 1:
            raise DatasetError(f"{label} must be a positive integer")
        raise DatasetError(
            f"{label} must be an integer of at least {minimum}"
        )
    result = int(value)
    if result < minimum:
        if minimum == 1:
            raise DatasetError(f"{label} must be a positive integer")
        raise DatasetError(
            f"{label} must be an integer of at least {minimum}"
        )
    return result


def _surface_divergence(
    dataset: pv.DataSet,
    *,
    divergence_name: str,
) -> np.ndarray:
    """Return validated finite divergence point data."""

    if not isinstance(divergence_name, str) or not divergence_name.strip():
        raise DatasetError("Divergence array name must not be empty")
    if divergence_name not in dataset.point_data:
        raise DatasetError(
            f"Divergence array {divergence_name!r} is unavailable in point data"
        )
    divergence = np.asarray(dataset.point_data[divergence_name])
    if divergence.shape != (dataset.n_points,):
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be a point scalar"
        )
    try:
        finite = np.isfinite(divergence).all()
    except TypeError as error:
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be numeric"
        ) from error
    if not finite:
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be finite"
        )
    return divergence


def _surface_x_values(
    dataset: pv.DataSet,
    *,
    x_range: tuple[float, float] | None,
    x_resolution: int,
) -> NDArray[np.float64]:
    """Return validated regular X sampling coordinates."""

    if x_range is None:
        bounds = dataset.bounds
        limits = np.asarray(
            (bounds.x_min, bounds.x_max),
            dtype=np.float64,
        )
        label = "Dataset X bounds"
    else:
        try:
            limits = np.asarray(x_range, dtype=np.float64)
        except (TypeError, ValueError) as error:
            raise DatasetError("X range must contain two numbers") from error
        label = "X range"
    if limits.shape != (2,):
        raise DatasetError(f"{label} must contain two values")
    if not np.isfinite(limits).all():
        raise DatasetError(f"{label} must be finite")
    if limits[0] >= limits[1]:
        raise DatasetError(f"{label} must be strictly increasing")
    resolution = _surface_integer(
        x_resolution,
        label="X resolution",
        minimum=2,
    )
    return np.linspace(
        limits[0],
        limits[1],
        resolution,
        dtype=np.float64,
    )
```

At the start of `get_bow_shock_surface()`, replace direct conversions with:

```python
    y_values = _surface_axis(y, label="Y")
    z_values = _surface_axis(z, label="Z")
    divergence = _surface_divergence(
        dataset,
        divergence_name=divergence_name,
    )
    x_values = _surface_x_values(
        dataset,
        x_range=x_range,
        x_resolution=x_resolution,
    )
    columns_per_chunk = _surface_integer(
        chunk_size,
        label="Chunk size",
        minimum=1,
    )
```

Use `columns_per_chunk` in the range loop.

If the validated dataset has no cells, return the initialized all-`NaN`
surface before constructing the locator.

Wrap only the PyVista call:

```python
        try:
            sampled = pv.PolyData(points).sample(
                source,
                locator=locator,
                pass_cell_data=False,
                pass_point_data=False,
                pass_field_data=False,
            )
        except Exception as error:
            raise DatasetError(
                f"Could not sample bow-shock surface: {error}"
            ) from error
```

Before reshaping, validate:

```python
        expected_points = count * len(x_values)
        if sampled.n_points != expected_points:
            raise DatasetError(
                "Bow-shock sampler returned an unexpected point count"
            )
        if divergence_name not in sampled.point_data:
            raise DatasetError(
                "Bow-shock sampler is missing sampled divergence "
                f"{divergence_name!r}"
            )
        if "vtkValidPointMask" not in sampled.point_data:
            raise DatasetError(
                "Bow-shock sampler is missing vtkValidPointMask"
            )
        sampled_divergence = np.asarray(
            sampled.point_data[divergence_name]
        )
        point_mask = np.asarray(
            sampled.point_data["vtkValidPointMask"]
        )
        if sampled_divergence.shape != (expected_points,):
            raise DatasetError(
                "Bow-shock sampler returned invalid divergence data"
            )
        if point_mask.shape != (expected_points,):
            raise DatasetError(
                "Bow-shock sampler returned an invalid point mask"
            )
```

Then reshape the validated arrays as in Task 2. Catch a `TypeError` from
`np.isfinite(sampled_divergence)` and translate it to a sampled-divergence
`DatasetError`.

**Step 5: Run the complete unit-test file**

Run:

```bash
python -m pytest tests/bowshock/test_surface.py -q
```

Expected: all surface tests pass.

**Step 6: Run neighboring bow-shock tests**

Run:

```bash
python -m pytest tests/bowshock -q
```

Expected: all bow-shock tests pass.

**Step 7: Commit validation**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_surface.py
git commit -m "test: validate bow-shock surface sampling"
```

### Task 4: Add opt-in real-data coverage

**Files:**
- Modify: `tests/integration/test_tecplot_sample.py:8-10`
- Modify: `tests/integration/test_tecplot_sample.py:68`

**Step 1: Add the real-data smoke test**

Extend the imports:

```python
from shocklink.bowshock import (
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import (
    calc_velocity_divergence,
    get_2d_cut,
    plot_2d_cut,
)
```

Append:

```python
def test_real_batsrus_sample_extracts_bow_shock_surface_array() -> None:
    grid = read_tecplot(SAMPLE)
    calc_velocity_divergence(grid)
    fit = fit_bow_shock(grid)
    region = extract_shockfit_range(
        grid,
        lower=3.0 - fit.loc0[0],
        upper=fit.loc0[0] + 5.0,
    )
    y = np.linspace(-5.0, 5.0, 5)
    z = np.linspace(-5.0, 5.0, 5)

    surface = get_bow_shock_surface(
        region,
        y=y,
        z=z,
        x_resolution=161,
        chunk_size=5,
    )

    assert surface.shape == (len(y), len(z))
    assert np.isfinite(surface).any()
    finite = surface[np.isfinite(surface)]
    assert finite.min() >= region.bounds.x_min
    assert finite.max() <= region.bounds.x_max
```

**Step 2: Run the standard integration module**

Run:

```bash
python -m pytest tests/integration/test_tecplot_sample.py -q
```

Expected: all tests are skipped unless
`SHOCKLINK_RUN_LARGE_DATA_TESTS=1`.

**Step 3: Run only the new real-data test**

Run:

```bash
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 \
python -m pytest \
  tests/integration/test_tecplot_sample.py::test_real_batsrus_sample_extracts_bow_shock_surface_array \
  -q
```

Expected: `1 passed`. Record the finite-cell count and runtime in the work
log. If memory usage is excessive, reduce `chunk_size`; do not change the
surface definition.

**Step 4: Commit integration coverage**

```bash
git add tests/integration/test_tecplot_sample.py
git commit -m "test: cover bow-shock surface on sample data"
```

### Task 5: Verify the complete repository

**Files:**
- Verify: `src/shocklink/bowshock.py`
- Verify: `tests/bowshock/test_surface.py`
- Verify: `tests/integration/test_tecplot_sample.py`

**Step 1: Check formatting and static quality**

Run:

```bash
python -m ruff check src tests
python -m ruff format --check src tests
```

Expected: both commands succeed with no findings.

If formatting fails, run `python -m ruff format` only on files changed by this
plan, then rerun both checks.

**Step 2: Run focused regression tests**

Run:

```bash
python -m pytest \
  tests/bowshock/test_surface.py \
  tests/bowshock/test_extract.py \
  tests/bowshock/test_fit.py \
  tests/bowshock/test_models.py \
  -q
```

Expected: all focused tests pass.

**Step 3: Run the complete default suite**

Run:

```bash
python -m pytest -q
```

Expected: all default tests pass, with large-data integration tests skipped.

**Step 4: Inspect the final change set**

Run:

```bash
git diff --check
git status --short --branch
```

Expected: no whitespace errors and no unintended changes. Preserve the
pre-existing untracked `pressure-z0.png`.

**Step 5: Review the implementation**

Confirm:

- `tecplot.py` still contains only Tecplot-reading operations;
- `get_bow_shock_surface()` lives in `bowshock.py`;
- the return value is exactly a floating-point `(len(y), len(z))` array;
- `argmin(div(U))` is used instead of `argmax(abs(div(U)))`;
- one static-cell locator is reused across all chunks;
- invalid columns remain `NaN`;
- no subdirectories were added beneath `src/shocklink`;
- no notebook changes or smoothing behavior entered the scope.
