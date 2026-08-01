# MMS Plot Location, Averages, and Temperature Units Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add interval-averaged GSM spacecraft location annotations, plotted-variable averages, and right-axis kelvin temperature plots to the MMS example.

**Architecture:** Load optional native MEC GSM position data alongside the existing FGM/FPI products, retain it in `MMSData`, and use it only for a title/subtitle annotation. Add a separate `average_plotted_values` function so existing full summaries remain backward compatible. Convert total temperature from eV to K only in the plotting layer and place temperature labels/ticks on the right.

**Tech Stack:** Python 3.11+, pySPEDAS/pytplot, NumPy, Matplotlib, Jupyter/nbformat, pytest

---

Use @superpowers:test-driven-development for each task and
@superpowers:verification-before-completion before integration. Work in the
`.worktrees/mms-plot-location-averages` worktree.

### Task 1: Load optional GSM spacecraft position

**Files:**
- Modify: `examples/mms_data_analysis.py:25-215`
- Test: `tests/test_mms_data_analysis.py:1-280`

**Step 1: Write failing tests**

Add a `satellite_location` series key to the test loader fixture and verify
that `_load_pyspedas_products` requests MEC with `data_rate="srvy"` for fast
mode, `varformat="*_r_gsm"`, and records the expected variable only when it
has samples in the requested interval. Add a missing-MEC test where the fake
MMS module has no `mec` attribute and assert that FGM/FPI products still load.

```python
def test_default_loader_requests_mec_gsm_position_for_fast_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: dict[str, dict[str, object]] = {}
    mms = ModuleType("mms")
    mms.fgm = lambda **_: []  # type: ignore[attr-defined]
    mms.fpi = lambda **_: []  # type: ignore[attr-defined]

    def mec(**kwargs: object) -> list[str]:
        requests["mec"] = kwargs
        return ["mms1_mec_r_gsm"]

    mms.mec = mec  # type: ignore[attr-defined]
    # Install matching pyspedas.projects and pytplot fakes with an in-range sample.
    ...

    series = _load_pyspedas_products(
        start="2018-12-19 19:40:00", end="2018-12-19 19:52:00",
        probe=1, cadence="fast"
    )

    assert requests["mec"]["data_rate"] == "srvy"
    assert requests["mec"]["varformat"] == "*_r_gsm"
    assert series["satellite_location"] == "mms1_mec_r_gsm"
```

**Step 2: Run the focused test and verify failure**

Run: `pytest -q tests/test_mms_data_analysis.py -k mec`

Expected: FAIL because MEC is not requested and `satellite_location` does not
exist.

**Step 3: Implement the optional MEC load**

Add the expected variable:

```python
"satellite_location": f"{prefix}mec_r_gsm",
```

Use the cadence mapping already used for FGM (`"srvy" if cadence == "fast"
else cadence`). If `getattr(mms, "mec", None)` is callable, request:

```python
mms.mec(
    trange=trange,
    probe=probe_id,
    data_rate=mec_cadence,
    level="l2",
    varformat="*_r_gsm",
    time_clip=True,
)
```

Add the returned variables to the loaded set and retain
`satellite_location` only if `_has_samples_in_interval` succeeds. Do not call
coordinate conversion for this series.

**Step 4: Run the MMS module**

Run: `pytest -q tests/test_mms_data_analysis.py`

Expected: all existing and new MEC tests pass.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: load MMS GSM spacecraft position"
```

### Task 2: Compute means for plotted variables and annotate position

**Files:**
- Modify: `examples/mms_data_analysis.py:260-350`
- Test: `tests/test_mms_data_analysis.py:65-180`

**Step 1: Write failing tests**

Add a test that calls `average_plotted_values` with the existing fixture and
asserts keys/values for B components, B magnitude, ion density, ion velocity,
and total temperatures. Electron density/velocity and parallel/perpendicular
temperature source series must not appear.

```python
def test_average_plotted_values_returns_only_displayed_means(mms_data: MMSData) -> None:
    averages = average_plotted_values(mms_data)

    assert averages["magnetic_field_x"] == pytest.approx(2.0)
    assert averages["magnetic_field_magnitude"] == pytest.approx(
        np.mean(np.linalg.norm([[1, 2, 3], [2, 4, 6], [3, 6, 9]], axis=1))
    )
    assert averages["ion_density"] == pytest.approx(2.0)
    assert averages["ion_velocity_z"] == pytest.approx(60.0)
    assert averages["ion_temperature"] == pytest.approx(400.0)
    assert averages["electron_temperature"] == pytest.approx(40.0)
    assert "electron_density" not in averages
    assert "electron_velocity_x" not in averages
```

Add a title test with a `satellite_location` pytplot series whose finite mean
is `(2, -1, 0.5)` and assert the subtitle contains
`MMS1 position (GSM): (2.00, -1.00, 0.50) R_E`.

**Step 2: Run tests and verify failure**

Run: `pytest -q tests/test_mms_data_analysis.py -k "average_plotted or position"`

Expected: FAIL because the new API and position annotation do not exist.

**Step 3: Implement plotted means and annotation helpers**

Add:

```python
def average_plotted_values(data: MMSData) -> dict[str, float]:
    series = _resolve_series(data)
    averages: dict[str, float] = {}
    for key in ("magnetic_field", "ion_density", "ion_velocity"):
        product = series.get(key)
        if product is None:
            continue
        if product.values.ndim == 1:
            averages[key] = _finite_mean(product.values)
        else:
            for index, component in enumerate(("x", "y", "z")):
                if index < product.values.shape[1]:
                    averages[f"{key}_{component}"] = _finite_mean(product.values[:, index])
            if key == "magnetic_field" and product.values.shape[1] >= 3:
                averages["magnetic_field_magnitude"] = _finite_mean(
                    np.linalg.norm(product.values[:, :3], axis=1)
                )
    for species in ("ion", "electron"):
        product = _total_temperature(series, species)
        if product is not None:
            averages[f"{species}_temperature"] = _finite_mean(product.values)
    return averages
```

Use a `_finite_mean` helper that returns `nan` when no finite values exist.
Add `_position_caption(series)` that filters finite rows of
`satellite_location`, computes the three-column mean, and returns the exact
formatted caption or `None`. Add the caption as a second line in `figure.suptitle`
when available; leave the existing title unchanged otherwise.

Update `main` to print `average_plotted_values(data)` after the full summary.

**Step 4: Run focused and full MMS tests**

Run: `pytest -q tests/test_mms_data_analysis.py`

Expected: all tests pass.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: report MMS plotted averages"
```

### Task 3: Plot temperatures in kelvin on the right axis

**Files:**
- Modify: `examples/mms_data_analysis.py:300-365, 430-470`
- Test: `tests/test_mms_data_analysis.py:85-125`

**Step 1: Write failing tests**

Update temperature-axis assertions:

```python
assert figure.axes[3].get_ylabel() == r"$T_i$ [K]"
assert figure.axes[4].get_ylabel() == r"$T_e$ [K]"
assert figure.axes[3].yaxis.get_label_position() == "right"
assert figure.axes[4].yaxis.get_label_position() == "right"
np.testing.assert_allclose(
    figure.axes[4].lines[0].get_ydata(),
    np.array([40.0, 80.0, 120.0]) * 11604.51812,
)
```

**Step 2: Run the test and verify failure**

Run: `pytest -q tests/test_mms_data_analysis.py::test_plot_mms_data_draws_available_products`

Expected: FAIL because temperatures are still eV on the left axis.

**Step 3: Implement kelvin right-axis plotting**

Define:

```python
EV_TO_K = 11604.51812
```

When drawing a temperature panel, pass `temperature.values * EV_TO_K` to a
temperature-specific helper that sets the right-side label and ticks:

```python
def _plot_temperature(axis: object, product: _TimeSeries, fallback_name: str) -> None:
    axis.plot(
        product.times,
        product.values * EV_TO_K,
        linewidth=PLOT_LINE_WIDTH,
        label=product.name or fallback_name,
    )
    axis.yaxis.set_label_position("right")
    axis.yaxis.tick_right()
    axis.set_ylabel(fallback_name + " [K]")
```

Use math-text fallback names `$T_i$` and `$T_e$`. Keep `_total_temperature`
unchanged in eV so averages and existing science semantics remain explicit.

**Step 4: Run the MMS module**

Run: `pytest -q tests/test_mms_data_analysis.py`

Expected: all tests pass.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: plot MMS temperatures in kelvin"
```

### Task 4: Update notebook and README output

**Files:**
- Modify: `examples/mms_example.ipynb`
- Modify: `examples/README.md`
- Test: `tests/test_notebook.py`

**Step 1: Write failing notebook/documentation tests**

Require notebook code to import and call `average_plotted_values`, and require
markdown to mention GSM position, averages, and kelvin temperature output.

**Step 2: Run tests and verify failure**

Run: `pytest -q tests/test_notebook.py -k mms`

Expected: FAIL because the notebook does not display plotted averages or
describe the new title/temperature behavior.

**Step 3: Update notebook and README**

Import `average_plotted_values`, add a code cell after summary statistics:

```python
averages = average_plotted_values(data)
averages
```

Update plot markdown to mention the GSM position subtitle, plotted means, and
right-axis temperatures in K. Update README with the same behavior and API
name. Preserve clean notebook metadata: no outputs and null execution counts.

**Step 4: Run notebook and full tests**

Run: `pytest -q tests/test_notebook.py -k mms` then `pytest -q`.

Expected: all tests pass with only the existing NumPy ABI warning if present.

**Step 5: Commit**

```bash
git add examples/mms_example.ipynb examples/README.md tests/test_notebook.py
git commit -m "docs: show MMS averages and temperature units"
```

### Task 5: Verify and integrate

**Step 1: Run static checks**

```bash
python -m compileall -q examples tests
git diff --check main...HEAD
```

**Step 2: Run the full suite**

```bash
pytest -q
```

Expected: all tests pass; existing environment warnings are acceptable.

**Step 3: Inspect status and merge**

```bash
git status --short
git merge --ff-only feat/mms-plot-location-averages
pytest -q
```

Expected: clean branch, fast-forward integration, and a passing test suite in
the merged `main` checkout.
