# Tecplot Time Metadata Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Read the BATSRUS event timestamp from a Tecplot `.dat` header and preserve it as normalized UTC metadata on the returned PyVista grid.

**Architecture:** Add a small header parser to `shocklink.tecplot` that stops at the `ZONE` line, extracts the timestamp from `TITLE`, and normalizes it with the existing shared datetime utility. Keep `read_tecplot`'s return type unchanged and store the ISO-8601 value in `grid.field_data["time_event"]` after PyVista normalization.

**Tech Stack:** Python 3.11+, standard-library `re` and `pathlib`, PyVista, NumPy, pytest.

---

### Task 1: Parse and attach Tecplot event-time metadata

**Files:**
- Modify: `tests/test_tecplot.py:8-52`
- Modify: `tests/test_tecplot.py:55-68`
- Modify: `tests/test_tecplot.py:162`
- Modify: `src/shocklink/tecplot.py:5-19`
- Modify: `src/shocklink/tecplot.py:69-150`

**Step 1: Give every existing reader fixture a valid header**

Import the public metadata key with the reader, define the expected values, and
change `_sample_path` to write text instead of creating an empty file:

```python
from shocklink.tecplot import TIME_EVENT_KEY, read_tecplot


TITLE = 'TITLE="BATSRUS: 3D Data,2023/12/16 11:30:00.000"\n'
EXPECTED_TIME_EVENT = "2023-12-16T11:30:00.000+00:00"


def _sample_path(tmp_path: Path, *, header: str = TITLE) -> Path:
    path = tmp_path / "sample.dat"
    path.write_text(header, encoding="utf-8")
    return path
```

This preserves the intent of all current unit tests after a timestamp becomes
part of the supported input contract.

**Step 2: Write the failing metadata test**

Extend `test_read_tecplot_normalizes_geometry_and_vectors` with:

```python
assert np.asarray(grid.field_data[TIME_EVENT_KEY]).item() == EXPECTED_TIME_EVENT
```

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python -m pytest \
tests/test_tecplot.py::test_read_tecplot_normalizes_geometry_and_vectors -v
```

Expected: FAIL because `TIME_EVENT_KEY` is not yet exported (or, after adding
only the constant, because the `time_event` field-data array does not exist).

**Step 3: Write failing error-path tests**

Append tests that ensure header errors happen before PyVista is called:

```python
@pytest.mark.parametrize(
    ("header", "message"),
    [
        ('TITLE="BATSRUS: 3D Data"\nZONE T="3D"\n', "does not contain"),
        (
            'TITLE="BATSRUS: 3D Data,2023/13/16 11:30:00.000"\n',
            "Invalid BATSRUS event timestamp",
        ),
    ],
)
def test_read_tecplot_rejects_missing_or_invalid_event_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    header: str,
    message: str,
) -> None:
    def unexpected_read(_path: Path) -> pv.MultiBlock:
        pytest.fail("PyVista must not run for an invalid Tecplot header")

    monkeypatch.setattr(pv, "read", unexpected_read)

    with pytest.raises(DatasetError, match=message):
        read_tecplot(_sample_path(tmp_path, header=header))
```

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python -m pytest \
tests/test_tecplot.py::test_read_tecplot_rejects_missing_or_invalid_event_time -v
```

Expected: FAIL because the current reader neither validates nor parses the
header and reaches the `pytest.fail` callback.

**Step 4: Implement the private header parser**

Add imports, the public metadata key, and a narrowly anchored title pattern in
`src/shocklink/tecplot.py`:

```python
import re
from pathlib import Path

from shocklink.exceptions import DatasetError
from shocklink.utilities import parse_datetime

TIME_EVENT_KEY = "time_event"
_TITLE_TIMESTAMP_PATTERN = re.compile(
    r'^\s*TITLE\s*=.*,(?P<timestamp>\d{4}/\d{2}/\d{2}\s+'
    r'\d{2}:\d{2}:\d{2}(?:\.\d+)?)"\s*$',
    re.IGNORECASE,
)
```

Add this helper before `_components`:

```python
def _read_time_event(source: Path) -> str:
    """Return the header event time as an ISO-8601 UTC string."""

    try:
        with source.open(encoding="utf-8") as stream:
            for line in stream:
                stripped = line.lstrip()
                if stripped.upper().startswith("ZONE"):
                    break
                if not stripped.upper().startswith("TITLE"):
                    continue

                match = _TITLE_TIMESTAMP_PATTERN.match(line)
                if match is None:
                    break

                raw_time = match.group("timestamp")
                try:
                    parsed = parse_datetime(raw_time.replace("/", "-"))
                except ValueError as error:
                    raise DatasetError(
                        f"Invalid BATSRUS event timestamp in {source}: {raw_time}"
                    ) from error
                return parsed.isoformat(timespec="milliseconds")
    except (OSError, UnicodeError) as error:
        raise DatasetError(f"Could not read Tecplot header {source}: {error}") from error

    raise DatasetError(
        f"Tecplot header in {source} does not contain a BATSRUS event timestamp"
    )
```

The loop terminates at `ZONE`, so it cannot scan the large numeric section of
the BATSRUS file. The existing utility treats this timezone-free simulation
timestamp as UTC.

**Step 5: Attach the metadata in `read_tecplot`**

Immediately after extension validation, parse the header before invoking
PyVista:

```python
time_event = _read_time_event(source)
```

After assigning the normalized vector arrays, attach the scalar string:

```python
grid.field_data[TIME_EVENT_KEY] = time_event
```

Update the docstring's return and error sections to say that the returned grid
contains the UTC event timestamp in `field_data["time_event"]`, and that a
missing or invalid timestamp raises `DatasetError`. Export the key:

```python
__all__ = ["TIME_EVENT_KEY", "read_tecplot"]
```

**Step 6: Run the focused reader tests**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest tests/test_tecplot.py -v
```

Expected: all Tecplot unit tests PASS, including the valid, missing, and invalid
timestamp cases.

**Step 7: Commit the tested reader behavior**

```bash
git add src/shocklink/tecplot.py tests/test_tecplot.py
git commit -m "feat: preserve Tecplot event time metadata"
```

### Task 2: Verify metadata against the BATSRUS sample and full suite

**Files:**
- Modify: `tests/integration/test_tecplot_sample.py:20`
- Modify: `tests/integration/test_tecplot_sample.py:43-55`

**Step 1: Add the real-header assertion**

Import the key:

```python
from shocklink.tecplot import TIME_EVENT_KEY, read_tecplot
```

In `test_real_batsrus_sample_has_geometry_and_vector_fields`, add:

```python
assert (
    np.asarray(grid.field_data[TIME_EVENT_KEY]).item()
    == "2023-12-16T11:30:00.000+00:00"
)
```

This ties the unit-level parser to the actual first line of `data/3d.dat`.

**Step 2: Run the sample integration test**

From the feature worktree, point the test at the ignored sample in the main
checkout:

```bash
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 \
SHOCKLINK_TECPLOT_SAMPLE=/Users/yuxichen/dev/ShockGeo/data/3d.dat \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python -m pytest \
tests/integration/test_tecplot_sample.py::test_real_batsrus_sample_has_geometry_and_vector_fields \
-v
```

Expected: PASS with the exact UTC ISO timestamp above as well as the existing
geometry and vector assertions.

**Step 3: Run formatting and the full test suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m ruff check \
src/shocklink/tecplot.py tests/test_tecplot.py \
tests/integration/test_tecplot_sample.py
```

Expected: PASS with no lint errors.

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
```

Expected: 269 tests PASS and the three opt-in large-data tests are skipped in
the ordinary suite. If the test count changes before execution, require zero
failures rather than the exact count.

**Step 4: Commit the integration coverage**

```bash
git add tests/integration/test_tecplot_sample.py
git commit -m "test: verify Tecplot event time on sample"
```

### Task 3: Integrate the verified feature

**Files:**
- No source changes.

**Step 1: Confirm the feature branch is clean**

Run:

```bash
git status --short
```

Expected: no output.

**Step 2: Merge directly into `main` per repository policy**

From `/Users/yuxichen/dev/ShockGeo`:

```bash
git switch main
git merge --ff-only feat/tecplot-time-metadata
```

Expected: a successful fast-forward merge.

**Step 3: Verify the integrated checkout**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
```

Expected: all tests PASS with only the three opt-in integration tests skipped.
