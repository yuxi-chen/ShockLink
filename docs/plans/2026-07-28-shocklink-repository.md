# ShockLink Repository Scaffold Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a tested, pip-installable ShockLink repository scaffold for 3D MHD field-line-to-bow-shock connectivity analysis with PyVista data access.

**Architecture:** Use a flat `src/shocklink` layout with a backend-independent scientific core and a PyVista-based `shocklink.tecplot` reader. Keep the initial scientific behavior deliberately small: validated configuration, explicit domain models, backend protocols, normalized simulation data, connectivity status records, and CLI entry points form stable seams for later algorithms.

**Tech Stack:** Python 3.11+, NumPy, PyVista, VTK, standard-library TOML and `argparse`, Hatchling, pytest, Ruff, mypy, GitHub Actions.

---

### Task 1: Establish packaging and import boundaries

**Files:**
- Create: `pyproject.toml`
- Create: `src/shocklink/__init__.py`
- Create: `src/shocklink/py.typed`
- Create: `tests/test_package.py`

**Step 1: Write the failing package test**

```python
from importlib.metadata import version

import shocklink


def test_package_exposes_installed_version() -> None:
    assert shocklink.__version__ == version("shocklink")


def test_import_does_not_load_pyvista() -> None:
    import sys

    assert "pyvista" not in sys.modules
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_package.py -v`

Expected: FAIL because the project and package do not exist.

**Step 3: Add the minimal package**

Create a PEP 621 `pyproject.toml` using Hatchling, distribution name
`shocklink`, version `0.1.0`, Python `>=3.11`, NumPy and PyVista as required
scientific dependencies, and `src/shocklink` as the wheel package. Add optional
`test` and `dev` dependency groups.

Expose the installed version without importing optional backends:

```python
"""Tools for magnetic field-line connectivity to the bow shock."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("shocklink")
except PackageNotFoundError:
    __version__ = "0+unknown"

__all__ = ["__version__"]
```

**Step 4: Install the editable package and run the test**

Run: `python -m pip install -e ".[test]"`

Run: `python -m pytest tests/test_package.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml src/shocklink tests/test_package.py
git commit -m "build: establish ShockLink package"
```

### Task 2: Define errors, coordinate metadata, and analysis configuration

**Files:**
- Create: `src/shocklink/exceptions.py`
- Create: `src/shocklink/core.py`
- Create: `src/shocklink/config.py`
- Create: `tests/core/test_models.py`
- Create: `tests/test_config.py`
- Create: `examples/configs/basic.toml`

**Step 1: Write failing model and configuration tests**

Cover:

```python
def test_coordinate_system_rejects_empty_units() -> None:
    with pytest.raises(ValueError, match="length_unit"):
        CoordinateSystem(name="GSM", length_unit="")


def test_load_config_reads_required_analysis_fields(tmp_path: Path) -> None:
    path = tmp_path / "analysis.toml"
    path.write_text(
        """
        [dataset]
        path = "run/output.vtu"
        magnetic_field = "B"
        coordinate_system = "GSM"

        [bow_shock]
        surface = "run/bow_shock.vtp"

        [analysis]
        tolerance = 0.01
        """
    )
    config = load_config(path)
    assert config.dataset.magnetic_field == "B"
    assert config.analysis.tolerance == pytest.approx(0.01)


def test_load_config_rejects_nonpositive_tolerance(tmp_path: Path) -> None:
    ...
```

Also test missing files, malformed TOML, and missing required keys map to
`ConfigurationError`.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/core/test_models.py tests/test_config.py -v`

Expected: FAIL because the modules do not exist.

**Step 3: Implement minimal typed models**

Define:

- `ShockLinkError`
- `ConfigurationError`
- `DatasetError`
- `GeometryError`
- `BackendUnavailableError`
- frozen `CoordinateSystem`
- frozen `DatasetMetadata`
- frozen `DatasetConfig`
- frozen `BowShockConfig`
- frozen `AnalysisOptions`
- frozen `ShockLinkConfig`
- `load_config(path: str | Path) -> ShockLinkConfig`

Use `tomllib`, dataclasses, and explicit validation. Preserve paths as `Path`
objects but do not require referenced simulation files to exist during config
parsing so configurations can be validated before data staging.

**Step 4: Add a documented example configuration**

Create `examples/configs/basic.toml` containing dataset, bow-shock, field-line
seed, analysis tolerance, and output sections. Keep unsupported future options
commented and labeled.

**Step 5: Run tests**

Run: `python -m pytest tests/core/test_models.py tests/test_config.py -v`

Expected: PASS.

**Step 6: Commit**

```bash
git add src/shocklink/exceptions.py src/shocklink/core src/shocklink/config.py tests examples/configs/basic.toml
git commit -m "feat: add core configuration models"
```

### Task 3: Add scientific domain seams

**Files:**
- Create: `src/shocklink/io.py`
- Create: `src/shocklink/fieldlines.py`
- Create: `src/shocklink/bowshock.py`
- Create: `src/shocklink/connectivity.py`
- Create: `tests/fieldlines/test_models.py`
- Create: `tests/bowshock/test_models.py`
- Create: `tests/connectivity/test_models.py`

**Step 1: Write failing domain-model tests**

Test these invariants:

- a field line contains an `N x 3` finite coordinate array with at least two
  points;
- a bow-shock surface contains finite `N x 3` vertices and triangular `M x 3`
  integer faces;
- connectivity records expose one of `connected`, `not_connected`,
  `ambiguous`, or `incomplete`;
- a connected result requires at least one intersection;
- intersection locations are three-dimensional and have a nonnegative path
  distance.

Example:

```python
def test_connected_result_requires_intersection() -> None:
    with pytest.raises(ValueError, match="intersection"):
        ConnectivityResult(
            field_line_id="line-1",
            status=ConnectivityStatus.CONNECTED,
        )
```

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/fieldlines tests/bowshock tests/connectivity -v`

Expected: FAIL because the domain modules do not exist.

**Step 3: Implement the minimal domain models**

Create frozen dataclasses:

- `SeedPoint(identifier, position)`
- `FieldLine(identifier, points, seed_id=None)`
- `BowShockSurface(vertices, faces, name="bow_shock")`
- `Intersection(position, path_distance, surface_cell=None)`
- `ConnectivityStatus(str, Enum)`
- `ConnectivityResult(field_line_id, status, intersections=(), message=None)`

Normalize arrays with `numpy.asarray`, validate shape and finiteness in
`__post_init__`, and mark stored arrays read-only. Define runtime-checkable
protocols `SimulationDataset`, `FieldLineTracer`, and `BowShockDetector` without
implementing a concrete simulation backend.

**Step 4: Run tests**

Run: `python -m pytest tests/fieldlines tests/bowshock tests/connectivity -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/shocklink/io src/shocklink/fieldlines src/shocklink/bowshock src/shocklink/connectivity tests
git commit -m "feat: define ShockLink scientific domain models"
```

### Task 4: Read and normalize Tecplot data with PyVista

**Files:**
- Create: `src/shocklink/tecplot.py`
- Create: `tests/test_tecplot.py`
- Create: `tests/integration/test_tecplot_sample.py`

**Step 1: Write failing reader tests**

```python
def test_read_tecplot_normalizes_geometry_and_vectors(
    tmp_path, monkeypatch
) -> None:
    raw = synthetic_batsrus_grid()
    monkeypatch.setattr(pyvista, "read", lambda _path: pyvista.MultiBlock([raw]))

    grid = read_tecplot(tmp_path / "sample.dat")

    np.testing.assert_allclose(grid.points, expected_points)
    np.testing.assert_allclose(grid["B [nT]"], expected_b)
    np.testing.assert_allclose(grid["U [km/s]"], expected_u)
```

Also test missing files, unsupported extensions, zone counts, zone types,
missing component arrays, and invalid coordinates.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_tecplot.py -v`

Expected: FAIL because the reader module does not exist.

**Step 3: Implement Tecplot normalization**

Use PyVista's native Tecplot reader, select one nonempty unstructured zone,
assign imported coordinate components to `grid.points`, and compose `B [nT]`
and `U [km/s]` vector arrays. Map expected failures to `DatasetError`.

**Step 4: Run tests**

Run: `python -m pytest tests/test_tecplot.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/shocklink/tecplot.py tests/test_tecplot.py tests/integration/test_tecplot_sample.py
git commit -m "feat: read BATSRUS Tecplot data with PyVista"
```

### Task 5: Provide useful command-line entry points

**Files:**
- Create: `src/shocklink/cli.py`
- Modify: `pyproject.toml`
- Create: `tests/cli/test_main.py`

**Step 1: Write failing CLI tests**

Use `subprocess.run` to verify:

- `shocklink --version` prints the installed version;
- `shocklink validate examples/configs/basic.toml` returns zero;
- invalid configuration returns exit code 2 and a concise message on stderr;
- `shocklink analyze ...` validates configuration, then reports that the
  format-specific pipeline is not yet implemented without a traceback.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/cli/test_main.py -v`

Expected: FAIL because no console script exists.

**Step 3: Implement the CLI**

Use standard-library `argparse`. Add:

```toml
[project.scripts]
shocklink = "shocklink.cli:main"
```

Keep stdout for successful machine-readable or user-requested output and stderr
for diagnostics. Map configuration failures to exit code 2 and unavailable or
unimplemented analysis backends to exit code 3.

**Step 4: Run tests**

Run: `python -m pytest tests/cli/test_main.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml src/shocklink/cli tests/cli
git commit -m "feat: add ShockLink command line"
```

### Task 6: Add repository documentation and project hygiene

**Files:**
- Create: `README.md`
- Create: `LICENSE`
- Create: `CHANGELOG.md`
- Create: `CITATION.cff`
- Create: `CONTRIBUTING.md`
- Create: `docs/architecture.md`
- Create: `docs/scientific-conventions.md`
- Create: `docs/tecplot.md`
- Create: `examples/README.md`
- Create: `.gitignore`
- Create: `.editorconfig`
- Create: `tests/test_documentation.py`

**Step 1: Write failing documentation checks**

Test that:

- all local Markdown links from the README resolve;
- the documented config path exists;
- the README contains installation and `read_tecplot` usage;
- `CITATION.cff` names ShockLink and the current version.

**Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_documentation.py -v`

Expected: FAIL because documentation files do not exist.

**Step 3: Write concise repository documentation**

Document current capabilities separately from planned capabilities. State
coordinate-system and unit assumptions explicitly and warn that a dataset's
metadata must be verified before scientific interpretation. Explain PyVista
Tecplot loading, coordinate repair, vector construction, and the opt-in
large-sample integration test.

Use a BSD 3-Clause license. Leave author identities out of `CITATION.cff` until
the maintainers provide them; include title, version, license, and repository
type only.

**Step 4: Run documentation tests**

Run: `python -m pytest tests/test_documentation.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add README.md LICENSE CHANGELOG.md CITATION.cff CONTRIBUTING.md docs examples .gitignore .editorconfig tests/test_documentation.py
git commit -m "docs: add ShockLink project guidance"
```

### Task 7: Add quality gates and verify distributions

**Files:**
- Modify: `pyproject.toml`
- Create: `.github/workflows/ci.yml`
- Create: `.github/workflows/release.yml`
- Create: `tests/test_distribution.py`

**Step 1: Write the distribution-content test**

Build a wheel into a temporary directory and assert it includes:

- every `shocklink` subpackage;
- `shocklink/py.typed`; and
- no test or example data in the wheel.

Do not upload a release from tests.

**Step 2: Run the test to verify the build expectation**

Run: `python -m pytest tests/test_distribution.py -v`

Expected: FAIL until build tooling and package inclusion are complete.

**Step 3: Configure tools and CI**

Add strict, scoped Ruff and mypy settings to `pyproject.toml`. CI runs on Python
3.11, 3.12, and 3.13 and performs:

```bash
python -m ruff check .
python -m ruff format --check .
python -m mypy src
python -m pytest
python -m build
python -m twine check dist/*
```

Create a release workflow triggered by GitHub releases that uses PyPI trusted
publishing, but protect it with a named `pypi` environment and do not trigger or
publish anything during scaffold creation.

**Step 4: Run all quality gates**

Run: `python -m ruff check .`

Run: `python -m ruff format --check .`

Run: `python -m mypy src`

Run: `python -m pytest`

Run: `python -m build`

Run: `python -m twine check dist/*`

Expected: all commands PASS.

**Step 5: Inspect repository state**

Run: `git status --short`

Expected: only the implementation plan is uncommitted, or the worktree is clean
after including it in the final commit.

**Step 6: Commit**

```bash
git add pyproject.toml .github tests/test_distribution.py docs/plans/2026-07-28-shocklink-repository.md
git commit -m "ci: verify ShockLink package quality"
```
