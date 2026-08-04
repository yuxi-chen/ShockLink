# SWMF Module Boundary Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `shocklink.swmf` independent of MMS by moving time utilities to a shared module and moving MMS-to-SWMF calculations and CLI orchestration to `shocklink.mms_swmf`.

**Architecture:** `shocklink.utilities` owns generic UTC parsing and midpoint calculation, `shocklink.swmf` owns only validated SWMF values and template writing, and `shocklink.mms_swmf` is the one-way integration layer that loads MMS data and passes completed inputs into SWMF. The example script remains a thin entry point.

**Tech Stack:** Python 3.11+, dataclasses, `argparse`, pathlib, existing `shocklink.mms` API, pytest, Ruff.

---

### Task 1: Extract shared datetime utilities

**Files:**
- Create: `src/shocklink/utilities.py`
- Create: `tests/test_utilities.py`
- Modify: `src/shocklink/mms/data.py`
- Test: `tests/mms/test_data.py`
- Test: `tests/mms/test_loading.py`

**Step 1: Write failing utility tests**

Add focused tests specifying this API:

```python
from datetime import UTC, datetime, timedelta, timezone

import pytest

from shocklink.utilities import midpoint_datetime, parse_datetime


def test_parse_datetime_treats_naive_input_as_utc() -> None:
    assert parse_datetime("2018-12-19 19:52:00") == datetime(
        2018, 12, 19, 19, 52, tzinfo=UTC
    )


def test_parse_datetime_converts_an_offset_to_utc() -> None:
    assert parse_datetime("2018-12-19T14:52:00-05:00") == datetime(
        2018, 12, 19, 19, 52, tzinfo=UTC
    )


def test_midpoint_datetime_preserves_fractional_seconds() -> None:
    start = datetime(2018, 12, 19, 19, 40, tzinfo=UTC)
    end = datetime(2018, 12, 19, 19, 52, 1, tzinfo=UTC)
    assert midpoint_datetime(start, end) == datetime(
        2018, 12, 19, 19, 46, 0, 500000, tzinfo=UTC
    )


def test_midpoint_datetime_rejects_reversed_bounds() -> None:
    later = datetime(2018, 12, 19, 19, 52, tzinfo=UTC)
    earlier = later - timedelta(minutes=1)
    with pytest.raises(ValueError, match="start time must not be after end time"):
        midpoint_datetime(later, earlier)
```

**Step 2: Run the new tests and verify RED**

Run: `PYTHONPATH=src pytest tests/test_utilities.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: shocklink.utilities`.

**Step 3: Implement the minimal utility module**

Create `parse_datetime` using `datetime.fromisoformat`, `Z` normalization,
naive-as-UTC handling, and UTC conversion. Create `midpoint_datetime` using
`start + (end - start) / 2` after validating ordering.

**Step 4: Reuse the parser from MMS data handling**

In `src/shocklink/mms/data.py`, import `parse_datetime` from
`shocklink.utilities`, remove `_parse_utc_datetime`, and update
`TimeBounds.from_strings` and `_parse_utc_time` to call the shared helper.
Do not change the `TimeBounds` API or clipping behavior.

**Step 5: Run focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src pytest tests/test_utilities.py tests/mms/test_data.py tests/mms/test_loading.py -q
```

Expected: PASS.

**Step 6: Commit the extraction**

```bash
git add src/shocklink/utilities.py src/shocklink/mms/data.py tests/test_utilities.py
git commit -m "refactor: share UTC datetime utilities"
```

### Task 2: Make the SWMF module a pure writer

**Files:**
- Modify: `src/shocklink/swmf.py`
- Modify: `tests/test_swmf.py`
- Modify: `tests/test_module_boundaries.py`

**Step 1: Add failing boundary and value-validation tests**

Add an AST-based boundary test that fails when `src/shocklink/swmf.py`
imports `shocklink.mms`, `shocklink.mms_swmf`, or their members. Add a test
that direct construction rejects nonfinite values:

```python
def test_solar_wind_values_reject_nonfinite_fields() -> None:
    with pytest.raises(ValueError, match="density"):
        SolarWindValues(
            density=float("nan"),
            temperature_kelvin=1.0,
            velocity=(1.0, 2.0, 3.0),
            magnetic_field=(4.0, 5.0, 6.0),
        )
```

Remove MMS mapping, midpoint, and CLI expectations from `tests/test_swmf.py`;
those behaviors will move to Task 3. Keep and strengthen the template
replacement and CRLF-preservation tests.

**Step 2: Run tests and verify RED**

Run:

```bash
PYTHONPATH=src pytest tests/test_swmf.py tests/test_module_boundaries.py -q
```

Expected: FAIL because `SolarWindValues` does not validate direct inputs and
`swmf.py` still imports MMS functions inside wrappers.

**Step 3: Remove non-SWMF responsibilities**

Delete from `src/shocklink/swmf.py`:

- `EV_TO_K`;
- `_parse_datetime` and `midpoint_time`;
- `_required_average` and `average_to_solar_wind`;
- `parse_args`, `_load_mms_data`, `_average_plotted_values`, and `main`;
- the `argparse`, `math`, and `sys` imports no longer needed afterward.

Add `SolarWindValues.__post_init__` to validate that density, temperature,
all three velocity components, and all three magnetic-field components are
finite. Keep `replace_param_values` and `generate_param_file` behavior and
signatures unchanged.

**Step 4: Run tests and verify GREEN**

Run:

```bash
PYTHONPATH=src pytest tests/test_swmf.py tests/test_module_boundaries.py -q
```

Expected: PASS.

**Step 5: Commit the pure boundary**

```bash
git add src/shocklink/swmf.py tests/test_swmf.py tests/test_module_boundaries.py
git commit -m "refactor: isolate SWMF parameter writing"
```

### Task 3: Add the MMS-to-SWMF integration module

**Files:**
- Create: `src/shocklink/mms_swmf.py`
- Create: `tests/test_mms_swmf.py`

**Step 1: Write failing mapping tests**

Specify the integration API with a pure mapping test:

```python
from shocklink.mms_swmf import solar_wind_from_averages
from shocklink.swmf import SolarWindValues


def test_solar_wind_from_averages_maps_mms_values() -> None:
    result = solar_wind_from_averages(
        {
            "ion_density": 5.0,
            "ion_temperature": 2.0,
            "electron_temperature": 3.0,
            "ion_velocity_x": -400.0,
            "ion_velocity_y": 20.0,
            "ion_velocity_z": 30.0,
            "magnetic_field_x": -5.0,
            "magnetic_field_y": 2.0,
            "magnetic_field_z": 1.0,
        }
    )

    assert result == SolarWindValues(
        density=5.0,
        temperature_kelvin=5.0 * 11604.51812,
        velocity=(-400.0, 20.0, 30.0),
        magnetic_field=(-5.0, 2.0, 1.0),
    )
```

Add parameterized missing/nonfinite-average tests that identify each required
key.

**Step 2: Run mapping tests and verify RED**

Run: `PYTHONPATH=src pytest tests/test_mms_swmf.py -q`

Expected: FAIL during collection with `ModuleNotFoundError: shocklink.mms_swmf`.

**Step 3: Implement the pure mapping function**

Create `src/shocklink/mms_swmf.py` with `EV_TO_K`, a small required-finite
average helper, and `solar_wind_from_averages`. Return a fully constructed
`SolarWindValues`; do not modify or write a template in this function.

**Step 4: Run mapping tests and verify GREEN**

Run: `PYTHONPATH=src pytest tests/test_mms_swmf.py -q`

Expected: mapping tests PASS.

**Step 5: Commit the mapping layer**

```bash
git add src/shocklink/mms_swmf.py tests/test_mms_swmf.py
git commit -m "feat: map MMS averages to SWMF values"
```

### Task 4: Move CLI orchestration to the integration module

**Files:**
- Modify: `src/shocklink/mms_swmf.py`
- Modify: `tests/test_mms_swmf.py`
- Modify: `examples/create_swmf_input.py`

**Step 1: Write failing CLI tests**

Move the former SWMF CLI scenarios into `tests/test_mms_swmf.py`. Patch names
owned by `shocklink.mms_swmf` and verify:

- `load_mms_data` receives the exact interval, probe, mode, and
  `coordinates="gsm"`;
- the default start time passed to `generate_param_file` is the parsed
  interval midpoint;
- `--start-time` passes the explicitly parsed UTC time instead;
- the mapped `SolarWindValues` is passed to `generate_param_file`;
- empty MMS data, loading errors, invalid times, and file errors return 1 with
  the existing `Could not create SWMF input:` prefix;
- success reports the output path and returns 0.

Also add a parser test for the existing options: `--mms-start`, `--mms-end`,
`--input`, `--output`, `--start-time`, `--probe`, and `--mode`.

**Step 2: Run CLI tests and verify RED**

Run: `PYTHONPATH=src pytest tests/test_mms_swmf.py -q`

Expected: FAIL because `mms_swmf` does not yet define `parse_args` or `main`.

**Step 3: Implement orchestration**

Move the existing CLI parser and `main` behavior into
`src/shocklink/mms_swmf.py`. Import the public MMS loading and averaging
functions there. Parse interval strings with `utilities.parse_datetime`, use
`utilities.midpoint_datetime` when no override is given, construct the
solar-wind state with `solar_wind_from_averages`, and call
`swmf.generate_param_file` with the completed values.

Keep `coordinates="gsm"` fixed and retain all current CLI defaults and output
messages.

**Step 4: Point the example at the integration module**

Change the entry point to:

```python
from shocklink.mms_swmf import main


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 5: Run integration tests and verify GREEN**

Run:

```bash
PYTHONPATH=src pytest tests/test_mms_swmf.py tests/test_swmf.py tests/test_utilities.py -q
```

Expected: PASS.

**Step 6: Commit the orchestration move**

```bash
git add src/shocklink/mms_swmf.py examples/create_swmf_input.py tests/test_mms_swmf.py
git commit -m "refactor: move MMS SWMF workflow to integration module"
```

### Task 5: Verify boundaries and repository behavior

**Files:**
- Modify: `docs/plans/2026-08-04-swmf-module-boundary-refactor-design.md` only if implementation discoveries require corrections

**Step 1: Confirm no MMS dependency remains in SWMF**

Run:

```bash
rg -n "mms|argparse|parse_datetime|midpoint|EV_TO_K" src/shocklink/swmf.py
```

Expected: no matches.

**Step 2: Run focused tests**

Run:

```bash
PYTHONPATH=src pytest tests/test_utilities.py tests/test_swmf.py tests/test_mms_swmf.py tests/test_module_boundaries.py tests/mms -q
```

Expected: PASS.

**Step 3: Run lint**

Run:

```bash
ruff check src/shocklink/utilities.py src/shocklink/swmf.py src/shocklink/mms_swmf.py examples/create_swmf_input.py tests/test_utilities.py tests/test_swmf.py tests/test_mms_swmf.py tests/test_module_boundaries.py
```

Expected: no lint errors.

**Step 4: Run the complete test suite**

Run: `PYTHONPATH=src pytest -q`

Expected: all tests pass with no new warnings or failures.

**Step 5: Confirm the user's template edit is untouched**

Run: `git status --short data/Param/PARAM.in.Earth`

Expected: the refactor has not staged or committed this path. In the original
working tree, the user's existing modification remains intact.

**Step 6: Commit any final test-only adjustments**

If verification required test or documentation corrections:

```bash
git add tests docs/plans/2026-08-04-swmf-module-boundary-refactor-design.md
git commit -m "test: verify MMS SWMF module boundaries"
```
