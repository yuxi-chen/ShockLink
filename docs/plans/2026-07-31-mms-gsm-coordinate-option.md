# MMS GSM Coordinate Option Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep GSE as the default MMS vector frame and add an opt-in GSM conversion to the Python API, CLI, notebook, summaries, and plots.

**Architecture:** Always load the existing GSE FGM/FPI products, then transform each available vector tplot variable with pySPEDAS `cotrans` when GSM is selected. Record the selected frame on `MMSData`, while leaving scalar density and temperature variables unchanged and retaining the existing cadence fallback.

**Tech Stack:** Python 3.11+, pySPEDAS/pytplot, NumPy, Matplotlib, Jupyter/nbformat, pytest

---

Use @superpowers:test-driven-development for every behavior change and
@superpowers:verification-before-completion before integration. Work in the
existing `.worktrees/mms-gsm-coordinate-option` worktree and preserve all
unrelated user changes.

### Task 1: Add and propagate the coordinate selection

**Files:**
- Modify: `examples/mms_data_analysis.py:15-115`
- Test: `tests/test_mms_data_analysis.py:143-225`

**Step 1: Write failing API and CLI tests**

Update custom loader fakes to accept `coordinates: str`. Add these tests:

```python
def test_load_mms_data_defaults_to_gse() -> None:
    requested: list[str] = []

    def loader(
        *, start: str, end: str, probe: int, cadence: str, coordinates: str
    ) -> dict[str, str]:
        requested.append(coordinates)
        return {"magnetic_field": "mms1_fgm_b_gse_brst_l2_bvec"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        mode="brst",
        loader=loader,
    )

    assert requested == ["gse"]
    assert data.coordinates == "gse"


def test_load_mms_data_rejects_invalid_coordinates_before_loading() -> None:
    def loader(**_: object) -> dict[str, str]:
        pytest.fail("invalid coordinates must be rejected before loading")

    with pytest.raises(ValueError, match="coordinates"):
        load_mms_data(
            "2015-10-16",
            "2015-10-17",
            coordinates="sm",
            loader=loader,
        )
```

Extend `test_cli_parse_args_accepts_mms_interval_probe_and_cadence` with
`["--coordinates", "gsm"]` and:

```python
assert arguments.coordinates == "gsm"
```

Add a default assertion by calling `parse_args` without the option in a small
separate test:

```python
def test_cli_coordinates_default_to_gse() -> None:
    arguments = parse_args(
        ["--start", "2015-10-16", "--end", "2015-10-17"]
    )

    assert arguments.coordinates == "gse"
```

**Step 2: Run the focused tests and verify failure**

Run:

```bash
pytest -q \
  tests/test_mms_data_analysis.py::test_load_mms_data_defaults_to_gse \
  tests/test_mms_data_analysis.py::test_load_mms_data_rejects_invalid_coordinates_before_loading \
  tests/test_mms_data_analysis.py::test_cli_parse_args_accepts_mms_interval_probe_and_cadence \
  tests/test_mms_data_analysis.py::test_cli_coordinates_default_to_gse
```

Expected: failures because the argument and `MMSData.coordinates` do not yet
exist.

**Step 3: Implement coordinate selection and propagation**

In `examples/mms_data_analysis.py`, import `Literal`, define the coordinate
type, and extend the data object:

```python
from typing import Literal

CoordinateSystem = Literal["gse", "gsm"]


@dataclass(frozen=True)
class MMSData:
    """Named pytplot variables returned for one MMS probe and cadence."""

    cadence: Cadence
    series: Mapping[str, str]
    probe: int | None = None
    coordinates: CoordinateSystem = "gse"
```

Add the parser option:

```python
parser.add_argument(
    "--coordinates",
    choices=("gse", "gsm"),
    default="gse",
    help="Vector coordinates: GSE (default) or time-dependent GSM.",
)
```

Pass `coordinates=arguments.coordinates` from `main`. Extend
`load_mms_data` as follows:

```python
def load_mms_data(
    start: str,
    end: str,
    probe: int = 1,
    mode: str = "auto",
    coordinates: CoordinateSystem = "gse",
    loader: MMSLoader | None = None,
) -> MMSData:
    if mode not in {"auto", "brst", "fast"}:
        raise ValueError("mode must be one of 'auto', 'brst', or 'fast'")
    if coordinates not in {"gse", "gsm"}:
        raise ValueError("coordinates must be either 'gse' or 'gsm'")

    load = loader or _load_pyspedas_products
    cadences = ("brst", "fast") if mode == "auto" else (mode,)
    for cadence in cadences:
        series = dict(
            load(
                start=start,
                end=end,
                probe=probe,
                cadence=cadence,
                coordinates=coordinates,
            )
        )
        if _has_usable_series(series) or mode != "auto":
            return MMSData(
                cadence=cadence,
                series=series,
                probe=probe,
                coordinates=coordinates,
            )

    return MMSData(
        cadence="fast", series={}, probe=probe, coordinates=coordinates
    )
```

Update every custom loader in the tests to accept the new keyword. Do not
change cadence fallback behavior.

**Step 4: Run the complete MMS test module**

Run: `pytest -q tests/test_mms_data_analysis.py`

Expected: all current tests and the new selection tests pass.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: add MMS coordinate selection"
```

### Task 2: Convert all loaded vectors from GSE to GSM

**Files:**
- Modify: `examples/mms_data_analysis.py:117-174`
- Test: `tests/test_mms_data_analysis.py:190-270`

**Step 1: Write failing conversion tests**

Add a reusable loader fixture inside the GSM test or use local module fakes.
The core success test should load one scalar and all three vector products:

```python
def test_default_loader_converts_all_vectors_to_gsm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transformed: list[dict[str, str]] = []
    mms = ModuleType("mms")
    mms.fgm = lambda **_: ["mms1_fgm_b_gse_srvy_l2_bvec"]  # type: ignore[attr-defined]
    mms.fpi = lambda **_: [  # type: ignore[attr-defined]
        "mms1_dis_numberdensity_fast",
        "mms1_dis_bulkv_gse_fast",
        "mms1_des_bulkv_gse_fast",
    ]

    def cotrans(**kwargs: str) -> int:
        transformed.append(kwargs)
        return 1

    pyspedas = ModuleType("pyspedas")
    pyspedas.cotrans = cotrans  # type: ignore[attr-defined]
    projects = ModuleType("pyspedas.projects")
    projects.mms = mms  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", pyspedas)
    monkeypatch.setitem(sys.modules, "pyspedas.projects", projects)
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda _: SimpleNamespace(times=np.array([1_545_248_400.0]))
        ),
    )

    series = _load_pyspedas_products(
        start="2018-12-19 19:40:00",
        end="2018-12-19 19:52:00",
        probe=1,
        cadence="fast",
        coordinates="gsm",
    )

    assert series == {
        "magnetic_field": "mms1_fgm_b_gsm_srvy_l2_bvec",
        "ion_density": "mms1_dis_numberdensity_fast",
        "ion_velocity": "mms1_dis_bulkv_gsm_fast",
        "electron_velocity": "mms1_des_bulkv_gsm_fast",
    }
    assert [call["name_in"] for call in transformed] == [
        "mms1_fgm_b_gse_srvy_l2_bvec",
        "mms1_dis_bulkv_gse_fast",
        "mms1_des_bulkv_gse_fast",
    ]
    assert all(call["coord_in"] == "gse" for call in transformed)
    assert all(call["coord_out"] == "gsm" for call in transformed)
```

Add focused tests for unchanged GSE and failure:

```python
def test_gse_variable_name_falls_back_to_suffix_without_coordinate_token() -> None:
    assert _converted_variable_name("custom_vector", "gsm") == "custom_vector_gsm"


def test_coordinate_conversion_reports_failed_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pyspedas = ModuleType("pyspedas")
    pyspedas.cotrans = lambda **_: 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", pyspedas)

    with pytest.raises(RuntimeError, match="mms1_dis_bulkv_gse_fast"):
        _convert_vector_coordinates(
            {"ion_velocity": "mms1_dis_bulkv_gse_fast"}, "gsm"
        )
```

Import `_converted_variable_name` and `_convert_vector_coordinates` at the top
of the test module.

**Step 2: Run tests and verify failure**

Run:

```bash
pytest -q tests/test_mms_data_analysis.py -k "converts_all_vectors or converted_variable or conversion_reports"
```

Expected: failures because the helper functions and loader parameter do not
exist.

**Step 3: Implement deterministic vector conversion**

Add the vector keys and helpers:

```python
VECTOR_SERIES = ("magnetic_field", "ion_velocity", "electron_velocity")


def _converted_variable_name(variable: str, coordinates: CoordinateSystem) -> str:
    token = "_gse_"
    if token in variable:
        return variable.replace(token, f"_{coordinates}_", 1)
    return f"{variable}_{coordinates}"


def _convert_vector_coordinates(
    series: Mapping[str, str], coordinates: CoordinateSystem
) -> dict[str, str]:
    converted = dict(series)
    if coordinates == "gse":
        return converted

    from pyspedas import cotrans

    for product_name in VECTOR_SERIES:
        source = converted.get(product_name)
        if source is None:
            continue
        destination = _converted_variable_name(source, coordinates)
        result = cotrans(
            name_in=source,
            name_out=destination,
            coord_in="gse",
            coord_out=coordinates,
        )
        if result != 1:
            raise RuntimeError(
                f"Could not convert MMS vector {source!r} from GSE to GSM."
            )
        converted[product_name] = destination
    return converted
```

Extend `_load_pyspedas_products` with
`coordinates: CoordinateSystem = "gse"`. Build the filtered mapping in a
local variable, then return:

```python
return _convert_vector_coordinates(series, coordinates)
```

Keep `varformat="*_fgm_b_gse_*"` and `"*bulkv_gse*"`; GSM is derived from
these source variables.

**Step 4: Run focused and module tests**

Run:

```bash
pytest -q tests/test_mms_data_analysis.py -k "coordinates or converts or conversion"
pytest -q tests/test_mms_data_analysis.py
```

Expected: all tests pass and the GSE-only loader test records no transform
calls.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: convert MMS vectors to GSM"
```

### Task 3: Make summaries and figures coordinate-aware

**Files:**
- Modify: `examples/mms_data_analysis.py:176-255`
- Test: `tests/test_mms_data_analysis.py:64-145`

**Step 1: Write failing plot-title tests**

Update the existing plot assertion for the fixture's default GSE frame:

```python
assert figure._suptitle.get_text() == "MMS1 brst data (GSE)"
```

Add:

```python
def test_plot_mms_data_identifies_gsm_coordinates(
    mms_data: MMSData,
) -> None:
    gsm_data = MMSData(
        cadence=mms_data.cadence,
        series=mms_data.series,
        probe=mms_data.probe,
        coordinates="gsm",
    )

    figure = plot_mms_data(gsm_data)

    assert figure._suptitle.get_text() == "MMS1 brst data (GSM)"
```

**Step 2: Run the tests and verify failure**

Run:

```bash
pytest -q \
  tests/test_mms_data_analysis.py::test_plot_mms_data_draws_available_products \
  tests/test_mms_data_analysis.py::test_plot_mms_data_identifies_gsm_coordinates
```

Expected: title assertions fail because coordinates are not displayed.

**Step 3: Implement coordinate-aware output**

Replace the plot title assignment with:

```python
figure.suptitle(
    f"{spacecraft} {data.cadence} data ({data.coordinates.upper()})"
)
```

Change the `summarize_data` docstring so it says vector products are summarized
by their X, Y, and Z components in `data.coordinates`, rather than claiming
they are always GSE. No summary keys or numerical behavior should change.

Update the CLI status line to include the selected frame:

```python
print(
    f"Loaded MMS{arguments.probe} {data.cadence} "
    f"data in {data.coordinates.upper()}."
)
```

**Step 4: Run the MMS tests**

Run: `pytest -q tests/test_mms_data_analysis.py`

Expected: all tests pass.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.py tests/test_mms_data_analysis.py
git commit -m "feat: label MMS vector coordinates"
```

### Task 4: Expose the option in the notebook and documentation

**Files:**
- Modify: `examples/mms_example.ipynb`
- Modify: `examples/README.md:48-65`
- Test: `tests/test_notebook.py:90-135`

**Step 1: Write failing notebook tests**

Extend the parameter-cell assertion:

```python
for setting in ["START =", "END =", "PROBE =", "MODE =", "COORDINATES ="]:
    assert setting in parameter_cell
```

In `test_mms_notebook_is_valid_clean_and_uses_public_example_api`, add:

```python
assert "coordinates=COORDINATES" in code
```

**Step 2: Run notebook tests and verify failure**

Run: `pytest -q tests/test_notebook.py -k mms`

Expected: failures because the notebook has no coordinate setting.

**Step 3: Update the notebook**

Use `apply_patch` on the notebook JSON. Add this setting to the `mms-settings`
cell:

```python
COORDINATES = "gse"  # change to "gsm" for GSM vector components
```

Update the call in the `mms-download` cell:

```python
data = load_mms_data(
    START,
    END,
    probe=PROBE,
    mode=MODE,
    coordinates=COORDINATES,
)
```

Make the status line show `data.coordinates.upper()`. Explain in the Parameters
markdown that the setting changes magnetic-field and velocity vectors only;
density and temperature are scalars. Keep all execution counts null and all
outputs empty.

**Step 4: Document CLI and API usage**

In `examples/README.md`, state that GSE is the default and add a GSM example:

```bash
python examples/mms_data_analysis.py \
  --start "2018-12-19 19:40:00" \
  --end "2018-12-19 19:52:00" \
  --probe 1 --mode auto --coordinates gsm
```

Mention that B and bulk velocity are transformed with pySPEDAS while scalar
products are unchanged.

**Step 5: Run notebook and MMS tests**

Run:

```bash
pytest -q tests/test_notebook.py -k mms
pytest -q tests/test_mms_data_analysis.py
```

Expected: all selected tests pass.

**Step 6: Commit**

```bash
git add examples/mms_example.ipynb examples/README.md tests/test_notebook.py
git commit -m "docs: expose MMS coordinate selection"
```

### Task 5: Verify the complete feature and integrate it

**Files:**
- Verify: `examples/mms_data_analysis.py`
- Verify: `examples/mms_example.ipynb`
- Verify: `examples/README.md`
- Verify: `tests/test_mms_data_analysis.py`
- Verify: `tests/test_notebook.py`

**Step 1: Run static repository checks relevant to the edited files**

Run:

```bash
python -m compileall -q examples/mms_data_analysis.py
git diff --check main...HEAD
```

Expected: both commands exit successfully with no output.

**Step 2: Run the full test suite**

Run: `pytest -q`

Expected: all tests pass; existing environment warnings may remain but no new
failures are acceptable.

**Step 3: Inspect the final diff and history**

Run:

```bash
git status --short
git log --oneline main..HEAD
git diff --stat main...HEAD
```

Expected: clean status, the design plus focused feature commits, and changes
limited to the approved design, example, tests, notebook, and README.

**Step 4: Fast-forward merge into main**

From `/Users/yuxichen/dev/ShockGeo`, run:

```bash
git merge --ff-only docs/mms-gsm-coordinate-option
pytest -q
```

Expected: the branch fast-forwards into `main` and the full suite passes from
the merged checkout.
