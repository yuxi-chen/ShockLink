# MMS Module Simplification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move reusable MMS loading, analysis, plotting, and CLI behavior into the installable `shocklink.mms` feature while reducing the example script to a thin executable smoke test.

**Architecture:** Keep the repository's flat source layout. `shocklink.mms` is a stable public façade over focused private modules for shared data, loading, analysis, plotting, and CLI orchestration; private modules depend on `_mms_data` and never import the façade. Preserve the existing `MMSData` boundary, public signatures, lazy optional dependencies, notebook flow, numerical output, and plot appearance.

**Tech Stack:** Python 3.11+, NumPy, Matplotlib, pySPEDAS/pytplot, pytest, nbformat, Ruff, Hatchling

**Design:** `docs/plans/2026-08-03-mms-module-simplification-design.md`

---

## Compatibility contract

The completed refactor must support:

```python
from shocklink.mms import (
    MMSData,
    average_plotted_values,
    load_mms_data,
    main,
    parse_args,
    plot_mms_data,
    summarize_data,
)
```

Do not change these public call signatures. Do not import `pyspedas`,
`pytplot`, or `matplotlib.pyplot` merely by importing `shocklink.mms`.

During Tasks 1–6, keep `examples/mms_data_analysis.py` intact so the old tests
continue to provide regression coverage while equivalent package-facing tests
are added. Reduce the example and delete the obsolete test module only in Task
7, after all behavior has moved.

### Task 1: Create the shared MMS data layer and initial façade

**Files:**

- Create: `src/shocklink/_mms_data.py`
- Create: `src/shocklink/mms.py`
- Create: `tests/mms/conftest.py`
- Create: `tests/mms/test_data.py`
- Reference: `examples/mms_data_analysis.py:19-58,426-604`
- Reference: `tests/test_mms_data_analysis.py:1-118,236-268`

**Step 1: Write failing data-layer tests**

Create `tests/mms/conftest.py` with the existing deterministic `mms_data`
fixture. Import `MMSData` from `shocklink.mms`, not from the example. Keep all
fixture products so later analysis and plotting tests can reuse it.

Create `tests/mms/test_data.py` with focused tests for:

```python
def test_temperature_unit_conversion_is_reversible() -> None:
    values_ev = np.array([0.0, 1.0, 10.0, 100.0])
    values_k = _ev_to_kelvin(values_ev)
    np.testing.assert_allclose(values_k, values_ev * 11604.51812)
    np.testing.assert_allclose(_kelvin_to_ev(values_k), values_ev)


def test_resolve_series_clips_to_requested_interval(monkeypatch) -> None:
    # pytplot returns samples at 0, 10, and 20 seconds.
    # MMSData requests the inclusive interval [10, 20].
    resolved = _resolve_series(data)
    np.testing.assert_array_equal(
        resolved["ion_density"].times,
        np.array(
            ["1970-01-01T00:00:10", "1970-01-01T00:00:20"],
            dtype="datetime64[s]",
        ),
    )
    np.testing.assert_array_equal(
        resolved["ion_density"].values,
        np.array([2.0, 3.0]),
    )


def test_total_temperature_uses_one_parallel_and_two_perpendicular_directions(
    mms_data,
) -> None:
    temperature = _total_temperature(_resolve_series(mms_data), "ion")
    np.testing.assert_allclose(temperature.values, [120.0, 240.0, 360.0])
```

Import underscored algorithms from `shocklink._mms_data`; only `MMSData` is
public.

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/mms/test_data.py
```

Expected: FAIL during collection because `shocklink.mms` and
`shocklink._mms_data` do not exist.

**Step 3: Implement the shared data module**

Move these definitions from `examples/mms_data_analysis.py` into
`src/shocklink/_mms_data.py`:

- `Cadence`, `CoordinateSystem`, `EARTH_RADIUS_KM`, and `EV_TO_K`;
- `MMSData`;
- `_TimeSeries`, renamed to `ResolvedSeries`;
- `_ev_to_kelvin` and `_kelvin_to_ev`;
- `_resolve_series`, `_to_datetime64`, and `_parse_utc_time`;
- `_total_temperature`, `_finite_mean`, and `_mean_position_earth_radii`;
- `_metadata_text` and `_nested_metadata`, simplified to units only.

Remove the unused `name` field while moving the resolved model:

```python
@dataclass(frozen=True)
class ResolvedSeries:
    times: np.ndarray
    values: np.ndarray
    units: str | None = None
```

Centralize interval representations:

```python
@dataclass(frozen=True)
class TimeBounds:
    start: datetime
    end: datetime

    @classmethod
    def from_strings(cls, start: str, end: str) -> TimeBounds:
        return cls(_parse_utc_datetime(start), _parse_utc_datetime(end))

    @property
    def unix(self) -> tuple[float, float]:
        return self.start.timestamp(), self.end.timestamp()

    @property
    def numpy(self) -> tuple[np.datetime64, np.datetime64]:
        return (
            np.datetime64(self.start.replace(tzinfo=None)),
            np.datetime64(self.end.replace(tzinfo=None)),
        )
```

Validate that start is not after end in `from_strings`. Use the same bounds in
series clipping and later loading/plotting code. Preserve inclusive clipping.

Create the initial public façade:

```python
from shocklink._mms_data import MMSData

__all__ = ["MMSData"]
```

Do not modify `shocklink.__init__`.

**Step 4: Run the focused and legacy tests**

Run:

```bash
pytest -q tests/mms/test_data.py tests/test_mms_data_analysis.py \
  -k "temperature or clips_samples"
```

Expected: PASS. Both the new package data layer and legacy implementation are
temporarily covered.

**Step 5: Commit**

```bash
git add src/shocklink/_mms_data.py src/shocklink/mms.py tests/mms
git commit -m "refactor: add shared MMS data layer"
```

### Task 2: Move loading and coordinate conversion

**Files:**

- Create: `src/shocklink/_mms_loading.py`
- Create: `tests/mms/test_loading.py`
- Modify: `src/shocklink/mms.py`
- Reference: `examples/mms_data_analysis.py:117-295`
- Reference: `tests/test_mms_data_analysis.py:274-438,462-645`

**Step 1: Write failing package-facing loading tests**

Transfer the existing tests for:

- automatic burst-to-fast fallback;
- explicit burst mode;
- invalid mode and coordinate rejection before loading;
- positional loader compatibility;
- FGM `srvy` versus FPI `fast` requests;
- optional MEC GSM position loading;
- missing MEC support;
- products outside the requested interval;
- default GSE and explicit GSM propagation;
- conversion of all vector products;
- scalar-only GSM behavior;
- deterministic converted names;
- failed and exceptional `cotrans` calls.

Change public imports to:

```python
from shocklink.mms import MMSData, load_mms_data
```

Import only conversion helpers directly from `shocklink._mms_loading`.

Add one lazy-import test:

```python
def test_importing_public_mms_api_does_not_import_pyspedas() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import shocklink.mms; "
            "assert 'pyspedas' not in sys.modules; "
            "assert 'pytplot' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/mms/test_loading.py
```

Expected: FAIL because `load_mms_data` is not exported and
`shocklink._mms_loading` does not exist.

**Step 3: Implement the loading module**

Move the existing loader and conversion behavior into
`src/shocklink/_mms_loading.py`:

```python
def load_mms_data(
    start: str,
    end: str,
    probe: int = 1,
    mode: str = "auto",
    loader: MMSLoader | None = None,
    coordinates: CoordinateSystem = "gse",
) -> MMSData:
    ...
```

Move `_load_pyspedas_products`, `_has_samples_in_interval`,
`_converted_variable_name`, and `_convert_vector_coordinates`. Replace repeated
`_parse_utc_time` calls with `TimeBounds.from_strings(...).unix`.

Keep imports lazy:

```python
def _load_pyspedas_products(...):
    from pyspedas.projects import mms
    ...


def _has_samples_in_interval(...):
    from pytplot import get_data
    ...
```

Do not change expected product names or current error text. Inline the trivial
`_has_usable_series` helper as `if any(series.values())`.

Export the loader from `shocklink.mms`:

```python
from shocklink._mms_data import MMSData
from shocklink._mms_loading import load_mms_data

__all__ = ["MMSData", "load_mms_data"]
```

**Step 4: Run focused loading tests**

Run:

```bash
pytest -q tests/mms/test_loading.py tests/test_mms_data_analysis.py \
  -k "load or loader or coordinate or converts or mec"
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/shocklink/_mms_loading.py src/shocklink/mms.py \
  tests/mms/test_loading.py
git commit -m "refactor: move MMS loading into shocklink"
```

### Task 3: Move summaries and plotted averages

**Files:**

- Create: `src/shocklink/_mms_analysis.py`
- Create: `tests/mms/test_analysis.py`
- Modify: `src/shocklink/mms.py`
- Reference: `examples/mms_data_analysis.py:297-346,511-571`
- Reference: `tests/test_mms_data_analysis.py:81-117`

**Step 1: Write failing analysis tests**

Transfer the existing summary and average tests to
`tests/mms/test_analysis.py`, importing only public functions:

```python
from shocklink.mms import average_plotted_values, summarize_data
```

Retain assertions that default plotted averages include magnetic field,
DIS density, ion velocity, ion/electron total temperatures, and mean GSM
position in Earth radii while excluding DES density and electron velocity.

Add finite-value coverage:

```python
def test_summary_ignores_nonfinite_values(monkeypatch) -> None:
    # Resolve [1.0, nan, inf, 3.0].
    assert summarize_data(data)["ion_density"] == {
        "count": 2,
        "mean": 2.0,
        "min": 1.0,
        "max": 3.0,
    }
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/mms/test_analysis.py
```

Expected: FAIL because the analysis functions are not exported.

**Step 3: Implement the analysis module**

Move `summarize_data`, `average_plotted_values`, `_statistics`, and any
analysis-only constants to `src/shocklink/_mms_analysis.py`. Import shared
resolution, temperature, position, and finite-mean helpers from `_mms_data`.

Keep the plotted-average product list declarative:

```python
PLOTTED_DIRECT_PRODUCTS = (
    "magnetic_field",
    "ion_density",
    "ion_velocity",
)
```

Export both public functions from `shocklink.mms` and append them to `__all__`.

**Step 4: Run focused analysis tests**

Run:

```bash
pytest -q tests/mms/test_analysis.py tests/test_mms_data_analysis.py \
  -k "summarize or average"
```

Expected: PASS with identical values from package and legacy paths.

**Step 5: Commit**

```bash
git add src/shocklink/_mms_analysis.py src/shocklink/mms.py \
  tests/mms/test_analysis.py
git commit -m "refactor: move MMS analysis into shocklink"
```

### Task 4: Move figure construction and simplify panel selection

**Files:**

- Create: `src/shocklink/_mms_plotting.py`
- Create: `tests/mms/test_plotting.py`
- Modify: `src/shocklink/mms.py`
- Reference: `examples/mms_data_analysis.py:348-424,504-530,604-696`
- Reference: `tests/test_mms_data_analysis.py:119-272`

**Step 1: Write failing plotting tests**

Transfer all current plot tests to `tests/mms/test_plotting.py`. Import
`MMSData` and `plot_mms_data` from `shocklink.mms`.

Preserve assertions for:

- five default panels in magnetic field, DIS density, ion velocity, ion
  temperature, electron temperature order;
- blue/green/red/black vector colors and 0.75 line width;
- compact LaTeX component labels and horizontal legends;
- scalar panels without legends;
- eV left axes and linked K right axes without offset text;
- GSM frame and mean-position title text in Earth radii;
- exact requested x limits, UTC labels, and date caption;
- compact figure size and vertical spacing;
- absence of DES density and electron velocity panels;
- `ValueError` when no plot-able series are resolved.

Add a panel-order test that does not rely on closures:

```python
def test_build_panels_returns_fixed_default_order(mms_data) -> None:
    panels = _build_panels(_resolve_series(mms_data))
    assert [panel.kind for panel in panels] == [
        "magnetic_field",
        "ion_density",
        "ion_velocity",
        "ion_temperature",
        "electron_temperature",
    ]
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/mms/test_plotting.py
```

Expected: FAIL because `plot_mms_data` and `_mms_plotting` do not exist.

**Step 3: Implement the plotting module**

Move all Matplotlib behavior to `src/shocklink/_mms_plotting.py`. Keep
Matplotlib imports inside `plot_mms_data` and `_plot_temperature`.

Replace the list of lambdas with an explicit internal specification:

```python
@dataclass(frozen=True)
class PlotPanel:
    kind: str
    product: ResolvedSeries
    renderer: Callable[[Axes, ResolvedSeries], None]


def _build_panels(series: Mapping[str, ResolvedSeries]) -> list[PlotPanel]:
    panels: list[PlotPanel] = []
    if product := series.get("magnetic_field"):
        panels.append(PlotPanel("magnetic_field", product, _plot_magnetic_field))
    if product := series.get("ion_density"):
        panels.append(PlotPanel("ion_density", product, _plot_density))
    if product := series.get("ion_velocity"):
        panels.append(PlotPanel("ion_velocity", product, _plot_ion_velocity))
    for species in ("ion", "electron"):
        if temperature := _total_temperature(series, species):
            panels.append(
                PlotPanel(
                    f"{species}_temperature",
                    temperature,
                    partial(_plot_temperature, species=species),
                )
            )
    return panels
```

If truth-value checks on dataclass/array-bearing objects are ambiguous, use
explicit `is not None` checks. The code above describes ordering, not a reason
to rely on NumPy truthiness.

Use `TimeBounds` for exact x limits. Move `_date_caption`, `_position_caption`,
axis-label helpers, Kelvin tick formatting, and vector-label formatting into
this module.

Do not move `_plot_scalar`; it is unused and should be deleted. Do not restore
resolved-series name metadata; plot labels are explicitly specified.

Export `plot_mms_data` from `shocklink.mms` and append it to `__all__`.

**Step 4: Run focused plotting tests and render smoke test**

Run:

```bash
pytest -q tests/mms/test_plotting.py tests/test_mms_data_analysis.py \
  -k "plot_mms_data"
```

Expected: PASS.

Render the deterministic fixture with the Agg backend and save it to a
temporary path. Confirm visually that panel order, right temperature labels,
legends, and exact time bounds match the current figure. Do not commit the
rendered image.

**Step 5: Commit**

```bash
git add src/shocklink/_mms_plotting.py src/shocklink/mms.py \
  tests/mms/test_plotting.py
git commit -m "refactor: move MMS plotting into shocklink"
```

### Task 5: Move CLI orchestration

**Files:**

- Create: `src/shocklink/_mms_cli.py`
- Create: `tests/mms/test_cli.py`
- Modify: `src/shocklink/mms.py`
- Reference: `examples/mms_data_analysis.py:60-115`
- Reference: `tests/test_mms_data_analysis.py:439-461,533-539`

**Step 1: Write failing CLI tests**

Move parser tests into `tests/mms/test_cli.py` and import `parse_args` and
`main` from `shocklink.mms`.

Add orchestration tests using monkeypatched private dependencies:

```python
def test_main_reports_download_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(_mms_cli, "load_mms_data", raising_loader)
    assert main(["--start", "2018-12-19", "--end", "2018-12-20"]) == 1
    assert "Could not download MMS data" in capsys.readouterr().err


def test_main_runs_summary_average_and_plot_workflow(monkeypatch) -> None:
    # Return deterministic MMSData and record each downstream call.
    assert main(required_arguments) == 0
    assert calls == ["summarize", "average", "plot", "show"]
```

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/mms/test_cli.py
```

Expected: FAIL because CLI functions are not exported.

**Step 3: Implement the CLI module**

Move `parse_args` and `main` to `src/shocklink/_mms_cli.py`. Import private
feature functions directly:

```python
from shocklink._mms_analysis import average_plotted_values, summarize_data
from shocklink._mms_loading import load_mms_data
from shocklink._mms_plotting import plot_mms_data
```

Do not import `shocklink.mms` from a private module. Preserve current options,
defaults, printed summaries, errors, and exit codes.

Export `parse_args` and `main` from `shocklink.mms`. At this point its public
surface must be:

```python
__all__ = [
    "MMSData",
    "average_plotted_values",
    "load_mms_data",
    "main",
    "parse_args",
    "plot_mms_data",
    "summarize_data",
]
```

**Step 4: Run CLI and package tests**

Run:

```bash
pytest -q tests/mms/test_cli.py tests/mms/test_loading.py \
  tests/mms/test_analysis.py tests/mms/test_plotting.py
```

Expected: PASS.

**Step 5: Commit**

```bash
git add src/shocklink/_mms_cli.py src/shocklink/mms.py tests/mms/test_cli.py
git commit -m "refactor: expose MMS workflow through shocklink"
```

### Task 6: Define the public boundary and lazy-dependency contract

**Files:**

- Create: `tests/mms/test_public_api.py`
- Modify: `tests/test_module_boundaries.py`
- Verify: `src/shocklink/mms.py`
- Verify: `src/shocklink/__init__.py`

**Step 1: Write public API tests**

Create:

```python
EXPECTED_PUBLIC_NAMES = {
    "MMSData",
    "average_plotted_values",
    "load_mms_data",
    "main",
    "parse_args",
    "plot_mms_data",
    "summarize_data",
}


def test_mms_public_api_is_explicit() -> None:
    import shocklink.mms as mms
    assert set(mms.__all__) == EXPECTED_PUBLIC_NAMES
    assert all(hasattr(mms, name) for name in EXPECTED_PUBLIC_NAMES)


def test_importing_mms_keeps_optional_dependencies_lazy() -> None:
    # Run in a fresh subprocess and assert pyspedas, pytplot, and
    # matplotlib.pyplot are absent from sys.modules.
    ...
```

Extend `tests/test_module_boundaries.py` to assert that `_mms_analysis`,
`_mms_loading`, and `_mms_plotting` import `_mms_data` rather than importing
the public `shocklink.mms` façade. Use AST inspection or a small source-text
check; do not import optional dependencies to test this boundary.

**Step 2: Run the boundary tests**

Run:

```bash
pytest -q tests/mms/test_public_api.py tests/test_module_boundaries.py \
  tests/test_source_layout.py
```

Expected: PASS. If lazy imports fail, move the offending optional import
inside the operation that uses it. If a private module imports the façade,
replace that dependency with the owning private module.

**Step 3: Run an installed-package import smoke test**

Run:

```bash
python -c "from shocklink.mms import MMSData, load_mms_data, plot_mms_data"
```

Expected: exit 0 without requiring a network connection.

**Step 4: Commit**

```bash
git add tests/mms/test_public_api.py tests/test_module_boundaries.py \
  src/shocklink/mms.py src/shocklink/_mms_*.py
git commit -m "test: define public MMS package boundary"
```

### Task 7: Update notebook and documentation imports

**Files:**

- Modify: `examples/mms_example.ipynb`
- Modify: `examples/README.md:48-82`
- Modify: `tests/test_notebook.py:64-130`

**Step 1: Write failing notebook expectations**

Update the notebook tests to require:

```python
assert "from shocklink.mms import" in code
assert "from mms_data_analysis import" not in code
```

Replace the test that manipulates `sys.path` and imports the example with a
test that executes the setup cell from the repository root and confirms the
public package names are available.

**Step 2: Run tests to verify they fail**

Run:

```bash
pytest -q tests/test_notebook.py -k mms
```

Expected: FAIL because the notebook still imports the example module.

**Step 3: Update the notebook and README**

In the notebook setup cell, remove `Path`, `sys`, and example-directory path
manipulation. Use:

```python
from shocklink.mms import (
    average_plotted_values,
    load_mms_data,
    plot_mms_data,
    summarize_data,
)
```

Preserve cell ordering, parameters, markdown guidance, empty outputs, and null
execution counts.

Update `examples/README.md` to state that reusable behavior lives in
`shocklink.mms`, show one direct Python import, and retain the existing CLI and
notebook commands.

**Step 4: Run notebook and documentation tests**

Run:

```bash
pytest -q tests/test_notebook.py tests/test_documentation.py tests/mms
```

Expected: PASS.

**Step 5: Commit**

```bash
git add examples/mms_example.ipynb examples/README.md tests/test_notebook.py
git commit -m "docs: use shocklink MMS package in examples"
```

### Task 8: Reduce the example and remove the legacy implementation

**Files:**

- Modify: `examples/mms_data_analysis.py`
- Delete: `tests/test_mms_data_analysis.py`
- Verify: `tests/mms/`

**Step 1: Add a failing thin-example test**

Add to `tests/mms/test_cli.py`:

```python
def test_example_is_a_thin_mms_entry_point() -> None:
    source = (ROOT / "examples/mms_data_analysis.py").read_text()
    tree = ast.parse(source)
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    assert functions == []
    assert "from shocklink.mms import main" in source
    assert "raise SystemExit(main())" in source
```

**Step 2: Run the test to verify it fails**

Run:

```bash
pytest -q tests/mms/test_cli.py::test_example_is_a_thin_mms_entry_point
```

Expected: FAIL because the example still contains the full implementation.

**Step 3: Replace the example with the smoke-test entry point**

Use exactly:

```python
"""Run the optional ShockLink MMS analysis workflow."""

from shocklink.mms import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Delete `tests/test_mms_data_analysis.py`; every retained behavior must already
exist in the focused package tests. Before deletion, compare its test names
against `tests/mms/` and account for each one.

**Step 4: Run all MMS and example tests**

Run:

```bash
pytest -q tests/mms tests/test_notebook.py tests/test_source_layout.py
```

Expected: PASS with no import path referring to private behavior in the
example script.

Run the example help command:

```bash
python examples/mms_data_analysis.py --help
```

Expected: exit 0 and the existing MMS CLI options.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/mms
git add -u tests/test_mms_data_analysis.py
git commit -m "refactor: reduce MMS example to package entry point"
```

### Task 9: Final cleanup and verification

**Files:**

- Verify: `src/shocklink/mms.py`
- Verify: `src/shocklink/_mms_data.py`
- Verify: `src/shocklink/_mms_loading.py`
- Verify: `src/shocklink/_mms_analysis.py`
- Verify: `src/shocklink/_mms_plotting.py`
- Verify: `src/shocklink/_mms_cli.py`
- Verify: `examples/mms_data_analysis.py`
- Verify: `examples/mms_example.ipynb`
- Verify: `tests/mms/`

**Step 1: Check for obsolete paths and dead code**

Run:

```bash
rg -n "from mms_data_analysis|sys.path.*examples|_plot_scalar|ResolvedSeries.*name" \
  src examples tests
```

Expected: no obsolete example imports, path manipulation, unused scalar
plotter, or resolved-series name field.

Run:

```bash
rg -n "^(def|class) " examples/mms_data_analysis.py src/shocklink/*mms*.py
```

Expected: the example defines no functions or classes; implementation is
owned by flat `src/shocklink` modules.

**Step 2: Run formatting, import, and compile checks**

Run:

```bash
ruff check src/shocklink examples/mms_data_analysis.py tests/mms \
  tests/test_notebook.py tests/test_module_boundaries.py
python -m compileall -q src/shocklink examples/mms_data_analysis.py tests/mms
git diff --check
```

Expected: all commands exit 0.

**Step 3: Run focused MMS verification**

Run:

```bash
pytest -q tests/mms tests/test_notebook.py tests/test_module_boundaries.py \
  tests/test_source_layout.py
```

Expected: all focused tests pass.

**Step 4: Run the full suite once before integration**

Run:

```bash
pytest -q
```

Expected: all tests pass, with only documented pre-existing skips or warnings.

**Step 5: Inspect the final diff**

Run:

```bash
git status --short
git diff --stat main...HEAD
git log --oneline main..HEAD
```

Expected: changes are limited to the MMS package modules, focused MMS tests,
thin example, notebook, README, and approved plan documents. Confirm every
task has its own commit and no rendered images or downloaded MMS data are
tracked.

**Step 6: Commit any verification-only corrections**

Only if Step 2–5 required corrections:

```bash
git add <corrected-files>
git commit -m "fix: complete MMS package migration"
```

Do not create an empty final commit.
