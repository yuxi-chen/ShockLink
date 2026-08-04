# Python Production Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Simplify `src/shocklink` by centralizing shared constants and utilities, removing dead helpers, and merging equivalent local validation logic without changing public behavior.

**Architecture:** `shocklink.constants` owns shared physical and Cartesian constants, while `shocklink.utilities` owns reusable time and conversion behavior. Domain modules retain configuration and validators specific to their errors, and only equivalent private helpers are consolidated.

**Tech Stack:** Python 3.11+, NumPy, dataclasses, argparse, pytest, Ruff.

---

### Task 1: Centralize shared physical and Cartesian constants

**Files:**
- Create: `src/shocklink/constants.py`
- Create: `tests/test_constants.py`
- Modify: `src/shocklink/mms/data.py`
- Modify: `src/shocklink/mms/analysis.py`
- Modify: `src/shocklink/mms/plotting.py`
- Modify: `src/shocklink/mms_swmf.py`
- Test: `tests/mms/test_analysis.py`
- Test: `tests/mms/test_plotting.py`
- Test: `tests/test_mms_swmf.py`

**Step 1: Write the failing ownership test**

Create `tests/test_constants.py`:

```python
from __future__ import annotations

import ast
from pathlib import Path

from shocklink.constants import (
    CARTESIAN_COMPONENTS,
    EARTH_RADIUS_KM,
    EV_TO_K,
)


ROOT = Path(__file__).resolve().parents[1]


def test_shared_constants_have_expected_values() -> None:
    assert CARTESIAN_COMPONENTS == ("x", "y", "z")
    assert EARTH_RADIUS_KM == 6371.2
    assert EV_TO_K == 11604.51812


def test_shared_constants_are_defined_only_in_constants_module() -> None:
    definitions: dict[str, list[str]] = {
        name: [] for name in ("CARTESIAN_COMPONENTS", "EARTH_RADIUS_KM", "EV_TO_K")
    }
    for path in (ROOT / "src/shocklink").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in definitions:
                    definitions[target.id].append(path.name)
    assert definitions == {
        "CARTESIAN_COMPONENTS": ["constants.py"],
        "EARTH_RADIUS_KM": ["constants.py"],
        "EV_TO_K": ["constants.py"],
    }
```

**Step 2: Run the test and verify RED**

Run: `PYTHONPATH=src pytest tests/test_constants.py -q`

Expected: collection fails with `ModuleNotFoundError: shocklink.constants`.

**Step 3: Add the constants module**

Create `src/shocklink/constants.py`:

```python
"""Shared physical and coordinate constants."""

CARTESIAN_COMPONENTS = ("x", "y", "z")
EARTH_RADIUS_KM = 6371.2
EV_TO_K = 11604.51812
```

Do not add SWMF labels, Tecplot field names, plotting configuration, or dataset
metadata keys.

**Step 4: Replace duplicate definitions and tuples**

- Remove `EARTH_RADIUS_KM` and `EV_TO_K` definitions from `mms/data.py` and
  import them from `shocklink.constants`.
- Remove `EV_TO_K` from `mms_swmf.py` and import it.
- Use `CARTESIAN_COMPONENTS` in `mms/analysis.py`, `mms/plotting.py`, and
  `mms_swmf.py` for component loops and labels.
- Keep component colors local to plotting and zip them with the shared
  component tuple.

**Step 5: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src pytest tests/test_constants.py tests/mms/test_analysis.py tests/mms/test_plotting.py tests/test_mms_swmf.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/shocklink/constants.py src/shocklink/mms/data.py src/shocklink/mms/analysis.py src/shocklink/mms/plotting.py src/shocklink/mms_swmf.py tests/test_constants.py
git commit -m "refactor: centralize shared physical constants"
```

### Task 2: Consolidate time bounds and temperature conversions

**Files:**
- Modify: `src/shocklink/utilities.py`
- Modify: `src/shocklink/mms/data.py`
- Modify: `src/shocklink/mms/loading.py`
- Modify: `src/shocklink/mms/plotting.py`
- Modify: `src/shocklink/mms_swmf.py`
- Modify: `tests/test_utilities.py`
- Modify: `tests/mms/test_data.py`
- Test: `tests/mms/test_loading.py`
- Test: `tests/mms/test_plotting.py`

**Step 1: Move the behavior contract to utility tests**

Add tests to `tests/test_utilities.py` before moving implementation:

```python
import numpy as np

from shocklink.constants import EV_TO_K
from shocklink.utilities import TimeBounds, ev_to_kelvin, kelvin_to_ev


def test_temperature_conversions_are_reversible() -> None:
    values = np.array([0.0, 1.0, 10.0])
    assert np.allclose(ev_to_kelvin(values), values * EV_TO_K)
    assert np.allclose(kelvin_to_ev(ev_to_kelvin(values)), values)


def test_time_bounds_expose_utc_unix_and_numpy_values() -> None:
    bounds = TimeBounds.from_strings(
        "2018-12-19 19:40:00", "2018-12-19 19:52:00"
    )
    assert bounds.start.tzinfo is UTC
    assert bounds.unix == (1545248400.0, 1545249120.0)
    assert bounds.numpy == (
        np.datetime64("2018-12-19T19:40:00"),
        np.datetime64("2018-12-19T19:52:00"),
    )
```

Keep the existing MMS data conversion test temporarily so RED verifies the
new owner is missing rather than deleting coverage first.

**Step 2: Run utility tests and verify RED**

Run: `PYTHONPATH=src pytest tests/test_utilities.py -q`

Expected: import failures because the utilities do not yet expose the moved
objects.

**Step 3: Implement shared conversion and bounds behavior**

Move `TimeBounds` from `mms/data.py` to `utilities.py`. Import `EV_TO_K` from
`constants.py` and add:

```python
def ev_to_kelvin(values: object) -> np.ndarray:
    return np.asarray(values) * EV_TO_K


def kelvin_to_ev(values: object) -> np.ndarray:
    return np.asarray(values) / EV_TO_K
```

Keep `parse_datetime` and `midpoint_datetime` unchanged.

**Step 4: Update consumers and remove dead helpers**

- Import `TimeBounds` into `mms/data.py` and `mms/loading.py` from utilities.
- Import conversion functions into `mms/plotting.py` from utilities.
- Replace `_ev_to_kelvin`/`_kelvin_to_ev` uses and remove those wrappers from
  `mms/data.py`.
- Remove unused `_parse_utc_time` from `mms/data.py`.
- In `mms_swmf.main`, construct one `TimeBounds` and use
  `midpoint_datetime(bounds.start, bounds.end)` instead of parsing both strings
  separately.
- Move the old conversion test from `tests/mms/test_data.py` to utility tests.

**Step 5: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src pytest tests/test_utilities.py tests/mms/test_data.py tests/mms/test_loading.py tests/mms/test_plotting.py tests/test_mms_swmf.py -q
```

Expected: PASS.

**Step 6: Commit**

```bash
git add src/shocklink/utilities.py src/shocklink/mms/data.py src/shocklink/mms/loading.py src/shocklink/mms/plotting.py src/shocklink/mms_swmf.py tests/test_utilities.py tests/mms/test_data.py
git commit -m "refactor: consolidate time and temperature utilities"
```

### Task 3: Simplify MMS component mapping

**Files:**
- Modify: `src/shocklink/mms_swmf.py`
- Modify: `src/shocklink/mms/analysis.py`
- Modify: `src/shocklink/mms/plotting.py`
- Modify: `tests/test_mms_swmf.py`
- Test: `tests/mms/test_analysis.py`
- Test: `tests/mms/test_plotting.py`

**Step 1: Add a failing complete-vector mapping test**

Add a parameterized test showing that both vector families require exactly the
same Cartesian-component behavior:

```python
@pytest.mark.parametrize("prefix", ["ion_velocity", "magnetic_field"])
@pytest.mark.parametrize("component", CARTESIAN_COMPONENTS)
def test_solar_wind_mapping_requires_every_vector_component(
    prefix: str, component: str
) -> None:
    averages = _averages()
    del averages[f"{prefix}_{component}"]
    with pytest.raises(ValueError, match=f"{prefix}_{component}"):
        solar_wind_from_averages(averages)
```

This may pass against current code; if so, first add an internal contract test
for the planned `_vector_average` helper and verify its missing import fails.

**Step 2: Extract the shared vector collector**

In `mms_swmf.py`, add:

```python
def _vector_average(
    averages: Mapping[str, float], prefix: str
) -> tuple[float, float, float]:
    x, y, z = (
        _required_average(averages, f"{prefix}_{component}")
        for component in CARTESIAN_COMPONENTS
    )
    return x, y, z
```

Use it for both velocity and magnetic field. This removes the two duplicate
generator expressions and their type-ignore comments.

**Step 3: Simplify component iteration in analysis and plotting**

- In `mms/analysis.py`, use a small `_component_label(index)` helper that
  returns the shared Cartesian name or `component_<index>` for higher
  dimensions. Reuse `CARTESIAN_COMPONENTS` for average and position loops.
- In `mms/plotting.py`, iterate over
  `zip(CARTESIAN_COMPONENTS, ("blue", "green", "red"), strict=True)` and slice
  by the available component count rather than independently indexing two
  literal tuples.

Do not merge summary statistics with plotted averages; their outputs and
inclusion rules differ.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src pytest tests/test_mms_swmf.py tests/mms/test_analysis.py tests/mms/test_plotting.py -q
```

Expected: PASS with unchanged numerical assertions.

**Step 5: Commit**

```bash
git add src/shocklink/mms_swmf.py src/shocklink/mms/analysis.py src/shocklink/mms/plotting.py tests/test_mms_swmf.py
git commit -m "refactor: simplify MMS component handling"
```

### Task 4: Consolidate dataset finite-sequence conversion

**Files:**
- Modify: `src/shocklink/dataset.py`
- Modify: `tests/test_dataset_cut.py`
- Modify: `tests/test_dataset_plot.py`
- Test: `tests/test_dataset_profiles.py`

**Step 1: Strengthen conversion-error tests**

Add or retain focused tests for nonnumeric and nonfinite cut vectors and plot
ranges. Verify the exception remains `DatasetError` and that messages retain
the field name (`Cut origin`, `xrange`, or `yrange`).

Run:

```bash
PYTHONPATH=src pytest tests/test_dataset_cut.py tests/test_dataset_plot.py tests/test_dataset_profiles.py -q
```

Expected: PASS before refactoring; these are characterization tests.

**Step 2: Extract one conversion helper**

Add:

```python
def _float_array(
    value: Sequence[float], *, numeric_message: str
) -> NDArray[np.float64]:
    try:
        return np.asarray(value, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise DatasetError(numeric_message) from error
```

Use it in `_vector3` and `_plot_range`. Keep their existing shape, finite, and
ordering checks at the call sites so their messages and semantics do not
collapse into a generic validator.

Also use the helper for the `x_range` branch in dataset code only if the same
`DatasetError` contract and message can be preserved exactly.

**Step 3: Run dataset tests**

Run:

```bash
PYTHONPATH=src pytest tests/test_dataset_cut.py tests/test_dataset_plot.py tests/test_dataset_profiles.py tests/test_dataset_derivatives.py -q
```

Expected: PASS.

**Step 4: Commit**

```bash
git add src/shocklink/dataset.py tests/test_dataset_cut.py tests/test_dataset_plot.py
git commit -m "refactor: share dataset numeric conversion"
```

### Task 5: Merge equivalent bow-shock helpers

**Files:**
- Modify: `src/shocklink/bowshock.py`
- Modify: `tests/bowshock/test_normals.py`
- Test: `tests/bowshock/test_surface.py`

**Step 1: Add characterization tests for the helper boundaries**

Ensure public normal calculation still distinguishes:

- empty/non-1D axes;
- fewer than three samples;
- nonfinite or non-increasing axes;
- zero-length normal fields and reference vectors;
- very large finite vectors that require scale-safe normalization.

Run:

```bash
PYTHONPATH=src pytest tests/bowshock/test_normals.py -q
```

Expected: PASS before refactoring.

**Step 2: Merge axis validation**

Change `_surface_axis` to accept `minimum_size: int = 1`. After its existing
numeric, dimensionality, finite, and monotonic checks, add:

```python
if axis.size < minimum_size:
    raise DatasetError(
        f"{label} coordinates must contain at least {minimum_size} values"
    )
```

Replace `_normal_axis(values, label=...)` calls with
`_surface_axis(values, label=..., minimum_size=3)` and delete `_normal_axis`.
Special-case the message for `minimum_size == 3` if required to preserve the
current exact wording.

**Step 3: Extract scale-safe vector normalization**

Add a private helper that accepts arrays ending in three components and a
domain label, divides first by maximum absolute component and then by Euclidean
magnitude, and raises the existing positive-magnitude error. Use it for both
the normal field and the reference vector in `calc_bow_shock_normal_angle`.

Do not reuse this helper for surface-normal construction, which also enforces
positive X orientation and a different output shape contract.

**Step 4: Run bow-shock tests**

Run:

```bash
PYTHONPATH=src pytest tests/bowshock/test_normals.py tests/bowshock/test_surface.py tests/bowshock/test_models.py tests/bowshock/test_fit.py -q
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_normals.py
git commit -m "refactor: merge bow-shock validation helpers"
```

### Task 6: Audit remaining production duplication and verify the repository

**Files:**
- Modify: production or focused test files only if the audit finds a proven duplicate covered by existing requirements

**Step 1: Check shared-constant ownership and dead names**

Run:

```bash
rg -n "^EV_TO_K =|^EARTH_RADIUS_KM =|^CARTESIAN_COMPONENTS =" src/shocklink
rg -n "_parse_utc_time|_normal_axis|\(\"x\", \"y\", \"z\"\)" src/shocklink
```

Expected: shared constants appear only in `constants.py`; removed helpers and
repeated Cartesian tuples have no production matches.

**Step 2: Review remaining similarly named helpers semantically**

Inspect the remaining private helpers in `dataset.py`, `bowshock.py`,
`tecplot.py`, `swmf.py`, and `mms/`. Keep separate helpers whose input shapes,
exception types, or ownership differ. Record any additional merge in the
design doc before implementing it test-first.

Do not create a generic validation framework merely to eliminate short,
domain-specific checks.

**Step 3: Run module-boundary and public-API tests**

Run:

```bash
PYTHONPATH=src pytest tests/test_constants.py tests/test_utilities.py tests/test_module_boundaries.py tests/test_source_layout.py tests/mms/test_public_api.py -q
```

Expected: PASS.

**Step 4: Run Ruff**

Run:

```bash
ruff check src/shocklink tests/test_constants.py tests/test_utilities.py tests/test_module_boundaries.py
```

Expected: no lint errors.

**Step 5: Run the complete test suite**

Run: `PYTHONPATH=src pytest -q`

Expected: all tests pass with no new warnings or failures.

**Step 6: Confirm the unrelated template edit remains untouched**

Run: `git status --short data/Param/PARAM.in.Earth`

Expected: the implementation branch contains no changes to this file. In the
original working tree, the user's pre-existing modification remains present.

**Step 7: Commit any audit-only correction**

If the audit produced a small, verified correction:

```bash
git add <exact audited files>
git commit -m "refactor: finish production simplification audit"
```
