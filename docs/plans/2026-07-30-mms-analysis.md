# MMS Satellite-Data Analysis Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reusable MMS pySPEDAS example script and runnable notebook that prefer burst data, fall back to fast survey in automatic mode, plot MMS FGM/FPI measurements, and summarize the interval.

**Architecture:** Keep observational-data code in `examples/mms_data_analysis.py` so the core ShockLink package remains simulation focused. The module exposes loader, analysis, and plotting functions; its CLI and notebook use those same functions. pySPEDAS calls are isolated behind an injected loader for deterministic, network-free tests.

**Tech Stack:** Python 3.11+, pySPEDAS, pytplot, NumPy, Matplotlib, pytest.

---

### Task 1: Declare the optional MMS dependency set

**Files:**
- Modify: `pyproject.toml`
- Test: `tests/test_package.py`

**Step 1: Write the failing test**

Add a test that loads `pyproject.toml` and asserts the `mms` optional dependency group contains `pyspedas` and `matplotlib`.

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_package.py::test_mms_extra_declares_analysis_dependencies -v`

Expected: FAIL because the `mms` group does not exist.

**Step 3: Write minimal implementation**

Add:

```toml
mms = [
  "matplotlib>=3.8",
  "pyspedas>=1.7",
]
```

under `[project.optional-dependencies]`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_package.py::test_mms_extra_declares_analysis_dependencies -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml tests/test_package.py
git commit -m "build: add MMS analysis dependencies"
```

### Task 2: Load and select MMS products

**Files:**
- Create: `examples/mms_data_analysis.py`
- Create: `tests/test_mms_data_analysis.py`

**Step 1: Write the failing tests**

Test that `load_mms_data(..., mode="auto")` invokes a supplied burst loader first and selects fast only after it returns no usable data. Test that explicit `brst` does not call fast, and invalid modes raise `ValueError`.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mms_data_analysis.py -k 'load or mode' -v`

Expected: FAIL because the module and loader do not exist.

**Step 3: Write minimal implementation**

Implement a `MMSData` dataclass plus `load_mms_data(start, end, probe=1, mode="auto", loader=None)`. The default loader imports pySPEDAS lazily and requests FGM magnetic fields and FPI ion/electron moments for the requested cadence. It returns usable time-series handles and records the chosen cadence. `auto` attempts `brst` then `fast`; explicit modes only make their requested call.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mms_data_analysis.py -k 'load or mode' -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: load MMS FGM and FPI data"
```

### Task 3: Analyze and plot loaded data

**Files:**
- Modify: `examples/mms_data_analysis.py`
- Modify: `tests/test_mms_data_analysis.py`

**Step 1: Write the failing tests**

Add an in-memory time-series fixture. Test that `summarize_data` returns count, mean, minimum, and maximum for valid scalar/vector components, and `plot_mms_data` returns a Matplotlib figure with the expected populated panels while skipping missing optional products.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mms_data_analysis.py -k 'summarize or plot' -v`

Expected: FAIL because analysis and plotting functions do not exist.

**Step 3: Write minimal implementation**

Implement `summarize_data(data)` and `plot_mms_data(data)`. Plot FGM components and magnitude, ion/electron density, species velocity components, and each available temperature. Resolve pytplot variables at the boundary, preserve original sample timestamps, and put physical units/variable names in labels. Raise a clear error when no series can be plotted.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mms_data_analysis.py -k 'summarize or plot' -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: plot and summarize MMS measurements"
```

### Task 4: Add CLI and test notebook

**Files:**
- Modify: `examples/mms_data_analysis.py`
- Create: `examples/mms_data_analysis.ipynb`
- Modify: `examples/README.md`
- Modify: `tests/test_mms_data_analysis.py`
- Modify: `tests/test_notebook.py`

**Step 1: Write the failing tests**

Test `parse_args` for `--start`, `--end`, `--probe`, and `--mode`; test that the notebook is syntactically valid and imports/calls the public loader and plotting functions without embedded output.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_mms_data_analysis.py -k cli -v && pytest tests/test_notebook.py -k mms -v`

Expected: FAIL because the CLI/notebook documentation is absent.

**Step 3: Write minimal implementation**

Add `main()` and argument parsing. It loads the requested interval, prints summary statistics, displays the figure, and returns a nonzero status with an actionable error message on download/no-data failure. Add a clean notebook with editable time-range/mode cells and calls to the example module. Document installation using `pip install -e ".[mms]"` and a sample command.

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_mms_data_analysis.py -k cli -v && pytest tests/test_notebook.py -k mms -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py examples/mms_data_analysis.ipynb examples/README.md tests/test_mms_data_analysis.py tests/test_notebook.py
git commit -m "docs: add runnable MMS analysis notebook"
```

### Task 5: Validate the complete change

**Files:**
- Verify: all changed files

**Step 1: Run targeted tests**

Run: `pytest tests/test_mms_data_analysis.py tests/test_notebook.py tests/test_package.py -v`

Expected: PASS.

**Step 2: Run the full test suite**

Run: `pytest`

Expected: PASS with the existing integration skips only.

**Step 3: Review the final diff**

Run: `git diff main...HEAD --check && git status --short`

Expected: no whitespace errors and a clean working tree.

**Step 4: Commit the plan**

```bash
git add docs/plans/2026-07-30-mms-analysis.md
git commit -m "docs: plan MMS analysis example"
```
