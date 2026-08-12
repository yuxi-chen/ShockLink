# OMNI Temperature and Charge-Neutral MMS Inputs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Use MMS electron density as ion density and cleaned OMNI proton temperature in MMS plots and SWMF input generation.

**Architecture:** Extend the existing pySPEDAS loader to request OMNI one-minute `T`, preserving the existing `MMSData`/pytplot abstraction. Normalize the resolved series in the data layer: electron density becomes the displayed ion density and OMNI temperature is cleaned using metadata and placeholder rules. Plotting and averaging consume those normalized products, while SWMF uses the OMNI mean directly in kelvin and raises if no valid temperature exists.

**Tech Stack:** Python 3.11+, NumPy, Matplotlib, pySPEDAS/pytplot, pytest.

---

### Task 1: Add failing tests for OMNI loading and density mapping

**Files:**
- Modify: `tests/mms/test_loading.py`
- Modify: `tests/mms/test_data.py`

**Step 1: Write the failing tests**

Test that the loader calls `pyspedas.projects.omni.data` with the requested interval, one-minute datatype, and `varnames=["T"]`; test that resolved `ion_density` uses the electron-density variable when both are present; test that OMNI temperature fill values and all-9 placeholders are removed.

**Step 2: Run tests to verify failure**

Run: `pytest tests/mms/test_loading.py tests/mms/test_data.py -q`

Expected: FAIL because OMNI loading, density normalization, and cleaning do not yet exist.

**Step 3: Commit the failing tests**

```bash
git add tests/mms/test_loading.py tests/mms/test_data.py
git commit -m "test: define OMNI temperature and density behavior"
```

### Task 2: Implement OMNI loading and normalized series

**Files:**
- Modify: `src/shocklink/mms/loading.py`
- Modify: `src/shocklink/mms/data.py`

**Step 1: Implement the minimal loader changes**

Request OMNI `T` using `omni.data(trange=[start, end], datatype="1min", level="hro", varnames=["T"], time_clip=True)`. Store the returned `T` variable name in `MMSData.series` as `omni_temperature`, and make electron density the source for `ion_density` while retaining the source key for compatibility if useful.

**Step 2: Implement cleaning**

Read OMNI metadata for `FILLVAL`, `VALIDMIN`, and `VALIDMAX`; filter nonfinite values, metadata fill values, out-of-range values, and values whose decimal representation consists only of 9s (allowing one decimal point). Return an empty product when no samples remain.

**Step 3: Run targeted tests**

Run: `pytest tests/mms/test_loading.py tests/mms/test_data.py -q`

Expected: PASS.

**Step 4: Commit**

```bash
git add src/shocklink/mms/loading.py src/shocklink/mms/data.py
git commit -m "feat: load OMNI temperature and infer ion density"
```

### Task 3: Add failing plotting and analysis tests

**Files:**
- Modify: `tests/mms/test_plotting.py`
- Modify: `tests/mms/test_analysis.py`

**Step 1: Write tests**

Expect one `omni_temperature` panel instead of ion/electron temperature panels, with a Kelvin label and cleaned values. Expect `average_plotted_values` to return `omni_temperature` and no MMS temperature keys.

**Step 2: Run tests to verify failure**

Run: `pytest tests/mms/test_plotting.py tests/mms/test_analysis.py -q`

Expected: FAIL against the current two-temperature implementation.

### Task 4: Implement plotting and averaging

**Files:**
- Modify: `src/shocklink/mms/plotting.py`
- Modify: `src/shocklink/mms/analysis.py`

**Step 1: Implement the minimal behavior**

Build a single OMNI temperature panel, label it in kelvin, and include its finite mean in the plotted averages. Remove MMS ion/electron temperature panels and average keys.

**Step 2: Run targeted tests**

Run: `pytest tests/mms/test_plotting.py tests/mms/test_analysis.py -q`

Expected: PASS after updating fixtures/assertions for the approved behavior.

**Step 3: Commit**

```bash
git add src/shocklink/mms/plotting.py src/shocklink/mms/analysis.py tests/mms/test_plotting.py tests/mms/test_analysis.py
git commit -m "feat: plot and average OMNI temperature"
```

### Task 5: Add failing SWMF integration tests and use OMNI temperature

**Files:**
- Modify: `tests/test_mms_swmf.py`
- Modify: `src/shocklink/mms_swmf.py`

**Step 1: Write tests**

Change the average fixture to provide `omni_temperature` and assert it is used directly as kelvin. Add a test that missing/nonfinite OMNI temperature raises an error mentioning OMNI temperature.

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_mms_swmf.py -q`

Expected: FAIL because SWMF currently requires and sums MMS ion/electron temperatures.

**Step 3: Implement**

Require `omni_temperature` in `solar_wind_from_averages`, pass it directly to `SolarWindValues.temperature_kelvin`, and preserve the clear error path when no valid temperature was loaded.

**Step 4: Run targeted tests and commit**

Run: `pytest tests/test_mms_swmf.py -q`

```bash
git add src/shocklink/mms_swmf.py tests/test_mms_swmf.py
git commit -m "feat: use OMNI temperature for SWMF inputs"
```

### Task 6: Run the full verification suite

**Files:** None.

Run: `pytest -q`

Expected: all tests pass. Review `git diff main...HEAD`, then merge the verified branch into `main`.
