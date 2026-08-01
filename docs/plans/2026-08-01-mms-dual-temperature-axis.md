# MMS Dual Temperature Axis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a linked kelvin scale on the right of each MMS temperature panel while retaining one eV-valued line and the existing eV scale on the left.

**Architecture:** Keep total-temperature data and plotted lines in eV. Add reusable eV↔K conversion helpers and create a Matplotlib `secondary_yaxis` on each temperature panel so the right scale automatically follows the left limits without plotting duplicate data.

**Tech Stack:** Python 3.11+, NumPy, Matplotlib, pytest, nbformat/Jupyter

---

Use @superpowers:test-driven-development for the behavior change and
@superpowers:verification-before-completion before integration. Work in a
dedicated feature worktree created from `main`.

### Task 1: Define and test the eV/K conversion

**Files:**

- Modify: `examples/mms_data_analysis.py:20-30`
- Test: `tests/test_mms_data_analysis.py:12-30`

**Step 1: Write failing conversion tests**

Import `_ev_to_kelvin` and `_kelvin_to_ev` in
`tests/test_mms_data_analysis.py`, then add:

```python
def test_temperature_unit_conversion_is_reversible() -> None:
    values_ev = np.array([0.0, 1.0, 10.0, 100.0])

    values_k = _ev_to_kelvin(values_ev)

    np.testing.assert_allclose(values_k, values_ev * 11604.51812)
    np.testing.assert_allclose(_kelvin_to_ev(values_k), values_ev)
```

**Step 2: Run the test and verify failure**

Run:

```bash
pytest -q tests/test_mms_data_analysis.py::test_temperature_unit_conversion_is_reversible
```

Expected: collection fails because the two conversion helpers do not exist.

**Step 3: Implement the conversion helpers**

Add near the plotting constants in `examples/mms_data_analysis.py`:

```python
EV_TO_K = 11604.51812


def _ev_to_kelvin(values: object) -> np.ndarray:
    return np.asarray(values) * EV_TO_K


def _kelvin_to_ev(values: object) -> np.ndarray:
    return np.asarray(values) / EV_TO_K
```

These helpers intentionally accept scalars or arrays because Matplotlib may
call secondary-axis functions with either form.

**Step 4: Run the focused test**

Run:

```bash
pytest -q tests/test_mms_data_analysis.py::test_temperature_unit_conversion_is_reversible
```

Expected: PASS.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "test: define MMS temperature conversion"
```

### Task 2: Add the linked right-hand kelvin axes

**Files:**

- Modify: `examples/mms_data_analysis.py:620-635`
- Test: `tests/test_mms_data_analysis.py:108-145`

**Step 1: Write failing plot tests**

Extend `test_plot_mms_data_draws_available_products`:

```python
ion_axis = figure.axes[3]
electron_axis = figure.axes[4]

assert ion_axis.get_ylabel() == r"$T_i$ [eV]"
assert electron_axis.get_ylabel() == r"$T_e$ [eV]"
assert ion_axis.yaxis.get_label_position() == "left"
assert electron_axis.yaxis.get_label_position() == "left"
assert len(ion_axis.lines) == 1
assert len(electron_axis.lines) == 1
np.testing.assert_allclose(electron_axis.lines[0].get_ydata(), [40.0, 80.0, 120.0])

ion_kelvin_axis = ion_axis.child_axes[0]
electron_kelvin_axis = electron_axis.child_axes[0]
assert ion_kelvin_axis.get_ylabel() == r"$T_i$ [K]"
assert electron_kelvin_axis.get_ylabel() == r"$T_e$ [K]"
assert ion_kelvin_axis.yaxis.get_label_position() == "right"
assert electron_kelvin_axis.yaxis.get_label_position() == "right"
```

Also keep the existing assertion `len(figure.axes) == 5`; a secondary axis
must not add a sixth or seventh primary panel.

**Step 2: Run the focused plot test and verify failure**

Run:

```bash
pytest -q tests/test_mms_data_analysis.py::test_plot_mms_data_draws_available_products
```

Expected: FAIL because the temperature panels have no child secondary axes.

**Step 3: Implement one secondary axis per temperature panel**

Update `_plot_temperature`:

```python
def _plot_temperature(axis: object, product: _TimeSeries, fallback_name: str) -> None:
    axis.plot(
        product.times,
        product.values,
        linewidth=PLOT_LINE_WIDTH,
        label=product.name or fallback_name,
    )
    axis.set_ylabel(f"{fallback_name} [eV]")
    kelvin_axis = axis.secondary_yaxis(
        "right",
        functions=(_ev_to_kelvin, _kelvin_to_ev),
    )
    kelvin_axis.set_ylabel(f"{fallback_name} [K]")
```

Do not call `axis.twinx`, do not add another `plot` call, and do not modify
`_total_temperature` or `average_plotted_values`.

**Step 4: Run MMS plot and module tests**

Run:

```bash
pytest -q tests/test_mms_data_analysis.py::test_plot_mms_data_draws_available_products
pytest -q tests/test_mms_data_analysis.py
```

Expected: all MMS tests pass; each temperature panel has one line and one
linked right-side K scale.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: add MMS kelvin temperature axes"
```

### Task 3: Document the dual temperature units

**Files:**

- Modify: `examples/mms_example.ipynb:154-162`
- Modify: `examples/README.md:73-78`
- Test: `tests/test_notebook.py:90-140`

**Step 1: Write a failing notebook documentation test**

Add to `test_mms_notebook_guides_the_full_analysis_workflow`:

```python
assert "left axis in eV" in markdown
assert "right axis in K" in markdown
```

**Step 2: Run the test and verify failure**

Run:

```bash
pytest -q tests/test_notebook.py -k mms
```

Expected: FAIL because the notebook only describes the left eV axis.

**Step 3: Update notebook and README text**

Update the notebook's Plot Data markdown to state that each total-temperature
panel has one eV-valued line, a left eV scale, and a linked right K scale.
Update the README with the same description. Preserve null execution counts
and empty cell outputs.

**Step 4: Run notebook tests**

Run:

```bash
pytest -q tests/test_notebook.py -k mms
```

Expected: all selected notebook tests pass.

**Step 5: Commit**

```bash
git add examples/mms_example.ipynb examples/README.md tests/test_notebook.py
git commit -m "docs: explain MMS dual temperature axes"
```

### Task 4: Verify and integrate

**Step 1: Run static checks**

```bash
python -m compileall -q examples tests
ruff check examples/mms_data_analysis.py tests/test_mms_data_analysis.py tests/test_notebook.py
git diff --check main...HEAD
```

Expected: all commands exit successfully with no errors.

**Step 2: Run the full test suite**

```bash
pytest -q
```

Expected: all tests pass; the existing NumPy ABI warning may remain.

**Step 3: Inspect the final diff**

```bash
git status --short
git diff --stat main...HEAD
```

Expected: clean status and changes limited to the MMS example, its tests,
notebook, and README.

**Step 4: Fast-forward merge into main**

From `/Users/yuxichen/dev/ShockGeo`:

```bash
git merge --ff-only <implementation-branch>
pytest -q
```

Expected: the implementation fast-forwards into `main` and the full suite
passes from the merged checkout.
