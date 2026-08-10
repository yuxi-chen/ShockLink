# MMS Location at Effective Start Time Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace interval-averaged MMS position in generated SWMF inputs with the linearly interpolated GSM position at the effective SWMF start time.

**Architecture:** Add a public MMS analysis helper that resolves MEC samples and performs bounded component-wise linear interpolation at a requested UTC timestamp. `create_swmf_input()` will continue averaging plasma and field quantities over the interval, but will construct `MMSLocation` from this point-in-time helper using the explicit start time or interval midpoint.

**Tech Stack:** Python datetime, NumPy datetime/interpolation, pytest, Ruff

---

### Task 1: Add a bounded point-in-time MMS position helper

**Files:**
- Modify: `src/shocklink/mms/analysis.py`
- Modify: `src/shocklink/mms/__init__.py`
- Modify: `tests/mms/test_analysis.py`
- Modify: `tests/mms/test_public_api.py`

**Step 1: Write the failing interpolation tests**

Add tests for the wished-for public API:

```python
from shocklink.mms import position_at_time_earth_radii


def test_position_at_time_interpolates_between_mec_samples(mms_data):
    result = position_at_time_earth_radii(
        mms_data,
        "1970-01-01T00:00:00.500000Z",
    )
    assert result == pytest.approx((1.0, -0.5, 0.1))
```

Use a varying-position fixture so the expected midpoint differs from the
arithmetic interval mean. Add separate tests proving that an exact timestamp
returns the recorded sample, an in-between timestamp interpolates every
component, rows with any nonfinite coordinate are excluded, malformed or
missing position data raise `ValueError`, out-of-range targets raise instead of
extrapolating, and one finite sample succeeds only for an exact timestamp.

Update `EXPECTED_PUBLIC_NAMES` in `tests/mms/test_public_api.py` to include
`position_at_time_earth_radii`.

**Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/mms/test_analysis.py tests/mms/test_public_api.py -q
```

Expected: FAIL because the helper is not defined or exported.

**Step 3: Implement the minimal interpolation helper**

In `src/shocklink/mms/analysis.py`, add:

```python
def position_at_time_earth_radii(
    data: MMSData,
    time: str | datetime,
) -> tuple[float, float, float]:
    """Return the linearly interpolated GSM position at *time* in Earth radii."""
```

Implementation requirements:

1. Normalize string, naive-datetime, and aware-datetime inputs to UTC using the
   same convention as `parse_datetime()`.
2. Resolve `satellite_location` through `_resolve_series(data)` so interval
   clipping and pytplot compatibility remain centralized.
3. Require an `N x >=3` value array and retain only rows with a valid timestamp
   and three finite coordinates.
4. Sort by timestamp and make timestamps strictly increasing before
   interpolation, retaining the first finite row for duplicates.
5. Reject targets outside the retained timestamp range with a clear error that
   identifies the requested time and available range.
6. Use `numpy.interp` independently for X, Y, and Z, divide by
   `EARTH_RADIUS_KM`, verify the result is finite, and return three floats.

Export the helper from `shocklink.mms.__init__` and add it to `__all__` without
introducing eager optional-dependency imports.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/mms/test_analysis.py tests/mms/test_public_api.py -q
ruff check src/shocklink/mms/analysis.py src/shocklink/mms/__init__.py \
  tests/mms/test_analysis.py tests/mms/test_public_api.py
```

Expected: all checks pass.

**Step 5: Commit**

```bash
git add src/shocklink/mms/analysis.py src/shocklink/mms/__init__.py \
  tests/mms/test_analysis.py tests/mms/test_public_api.py
git commit -m "feat: interpolate MMS position at a timestamp"
```

### Task 2: Use the effective SWMF start time for location

**Files:**
- Modify: `src/shocklink/mms_swmf.py`
- Modify: `tests/test_mms_swmf.py`

**Step 1: Write failing integration tests**

Update the generation stubs to expose a dedicated
`position_at_time_earth_radii` call. Add assertions that the function requests
position at the exact interval midpoint by default and at the normalized
explicit UTC timestamp when `start_time` is supplied. Assert that the
`MMSLocation` passed to `generate_param_file()` comes from the interpolated
point rather than the `satellite_location_*` interval means. Add an error test
showing that interpolation failures propagate from the Python API and retain
the existing CLI error message/status through `main()`.

Use deliberately different interval-average and point-in-time coordinates so
the old path cannot satisfy the tests.

**Step 2: Run tests to verify failure**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_mms_swmf.py -q
```

Expected: FAIL because generation still reads location from interval averages.

**Step 3: Refactor `create_swmf_input()`**

Import `position_at_time_earth_radii` from `shocklink.mms`. Compute
`TimeBounds` and the normalized effective start time immediately after argument
validation. Keep `average_plotted_values(data)` for magnetic field, density,
velocity, and temperatures. Replace:

```python
location = mms_location_from_averages(averages)
```

with:

```python
location = MMSLocation(*position_at_time_earth_radii(data, effective_start_time))
```

Do not change output naming, CLI arguments, or error handling.
`mms_location_from_averages()` may remain for compatibility, but input
generation must no longer use it.

**Step 4: Run focused tests**

Run:

```bash
PYTHONPATH=src python -m pytest tests/test_mms_swmf.py tests/test_swmf_tool.py -q
ruff check src/shocklink/mms_swmf.py tests/test_mms_swmf.py
```

Expected: all checks pass.

**Step 5: Commit**

```bash
git add src/shocklink/mms_swmf.py tests/test_mms_swmf.py
git commit -m "fix: sample MMS location at SWMF start time"
```

### Task 3: Document the scientific semantics

**Files:**
- Modify: `README.md`
- Modify: `tests/test_documentation.py`

**Step 1: Write the failing documentation test**

Extend `test_root_readme_documents_swmf_input_tool()` to require language that
the MMS GSM position is linearly interpolated at the effective UTC start time,
which is the interval midpoint unless `start_time` or `--start-time` is given.

**Step 2: Run the test to verify failure**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_documentation.py::test_root_readme_documents_swmf_input_tool -q
```

Expected: FAIL because the README currently describes an averaged location.

**Step 3: Update the README**

State that plasma and field inputs remain interval averages, while GSM position
is linearly interpolated at the effective start time. Explain that the default
time is the midpoint and an explicit start time selects both `#STARTTIME` and
the location timestamp.

**Step 4: Run focused regression tests**

Run:

```bash
PYTHONPATH=src python -m pytest \
  tests/test_documentation.py tests/mms/test_analysis.py \
  tests/mms/test_public_api.py tests/test_mms_swmf.py tests/test_swmf_tool.py -q
ruff check src/shocklink/mms/analysis.py src/shocklink/mms/__init__.py \
  src/shocklink/mms_swmf.py tests/mms/test_analysis.py \
  tests/mms/test_public_api.py tests/test_mms_swmf.py \
  tests/test_documentation.py
```

Expected: all checks pass.

**Step 5: Commit**

```bash
git add README.md tests/test_documentation.py \
  docs/plans/2026-08-10-mms-location-at-start-time.md
git commit -m "docs: explain point-in-time MMS location"
```

### Task 4: Full verification and integration

**Step 1: Run the complete suite against the worktree source**

Run: `PYTHONPATH=src python -m pytest`

Expected: all unit tests pass and only the existing large-data integration tests
skip.

**Step 2: Verify changed-file lint and whitespace**

Run:

```bash
ruff check src/shocklink/mms/analysis.py src/shocklink/mms/__init__.py \
  src/shocklink/mms_swmf.py tests/mms/test_analysis.py \
  tests/mms/test_public_api.py tests/test_mms_swmf.py \
  tests/test_documentation.py
git diff --check
```

Expected: all checks pass.

**Step 3: Review the final scope**

Run: `git status --short && git diff main...HEAD --stat`

Expected: only approved interpolation, integration, tests, documentation, and
plan files are changed.

**Step 4: Integrate according to repository workflow**

Fast-forward the verified branch into `main`, rerun the full test suite on
merged `main`, then remove the merged worktree and branch. Preserve unrelated
untracked data and generated files.
