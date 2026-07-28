# Flat ShockLink Package Layout Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace every source subpackage under `src/shocklink/` with a flat, domain-named module without changing public imports or behavior.

**Architecture:** Move each domain implementation from `<domain>/models.py` or `io/protocols.py` into `<domain>.py`, then remove the package directories. Retain domain names so public imports remain compatible, and add a Git-layout regression test that rejects tracked directories beneath `src/shocklink/`.

**Tech Stack:** Python 3.11+, pytest, Git.

---

### Task 1: Enforce and implement the flat source layout

**Files:**
- Create: `tests/test_source_layout.py`
- Create: `src/shocklink/bowshock.py`
- Create: `src/shocklink/connectivity.py`
- Create: `src/shocklink/core.py`
- Create: `src/shocklink/fieldlines.py`
- Create: `src/shocklink/io.py`
- Delete: `src/shocklink/bowshock/__init__.py`
- Delete: `src/shocklink/bowshock/models.py`
- Delete: `src/shocklink/connectivity/__init__.py`
- Delete: `src/shocklink/connectivity/models.py`
- Delete: `src/shocklink/core/__init__.py`
- Delete: `src/shocklink/core/models.py`
- Delete: `src/shocklink/fieldlines/__init__.py`
- Delete: `src/shocklink/fieldlines/models.py`
- Delete: `src/shocklink/io/__init__.py`
- Delete: `src/shocklink/io/protocols.py`

**Step 1: Write the failing structural regression test**

```python
from pathlib import Path
import subprocess


def test_shocklink_source_package_is_flat() -> None:
    root = Path(__file__).resolve().parents[1]
    tracked = subprocess.run(
        ["git", "ls-files", "src/shocklink"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    nested = [
        path
        for path in tracked
        if len(Path(path).relative_to("src/shocklink").parts) > 1
    ]
    assert nested == []
```

**Step 2: Run the test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_source_layout.py -v`

Expected: FAIL and list the currently tracked domain subpackage files.

**Step 3: Flatten domain implementations**

For each domain, move the implementation into a same-named `.py` module and
remove its package directory. Preserve these public imports:

```python
from shocklink.bowshock import BowShockSurface
from shocklink.connectivity import (
    ConnectivityResult,
    ConnectivityStatus,
    Intersection,
)
from shocklink.core import CoordinateSystem, DatasetMetadata
from shocklink.fieldlines import FieldLine, SeedPoint
from shocklink.io import BowShockDetector, FieldLineTracer, SimulationDataset
```

Update internal imports in `io.py` to import those flat public modules.

**Step 4: Stage moves so the structural test observes the intended Git layout**

Run:

```bash
git add src/shocklink tests/test_source_layout.py
```

**Step 5: Run the structural and behavioral tests**

Run: `PYTHONPATH=src python -m pytest tests/test_source_layout.py -v`

Expected: PASS.

Run: `PYTHONPATH=src python -m pytest -v`

Expected: all tests PASS.

**Step 6: Commit**

```bash
git commit -m "refactor: flatten ShockLink source package"
```

### Task 2: Align planning documentation and verify packaging

**Files:**
- Modify: `docs/plans/2026-07-28-shocklink-repository.md`

**Step 1: Add a failing documentation regression assertion**

Extend `tests/test_source_layout.py` to assert that the repository
implementation plan does not describe any source package directory such as
`src/shocklink/core/`.

**Step 2: Run the documentation assertion to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_source_layout.py -v`

Expected: FAIL because the original implementation plan lists subpackages.

**Step 3: Update the implementation plan**

Replace source package paths with the approved flat module paths and state that
future ParaView and CLI integrations must be `paraview.py` and `cli.py`.

**Step 4: Run complete verification**

Run: `PYTHONPATH=src python -m pytest -v`

Expected: all tests PASS.

Run: `python -m pip wheel . --no-deps --wheel-dir /tmp/shocklink-wheel`

Expected: one `shocklink-0.1.0` wheel builds successfully.

Inspect the wheel archive and verify `shocklink/` contains Python files and
`py.typed`, with no nested package directories.

**Step 5: Commit**

```bash
git add docs/plans/2026-07-28-shocklink-repository.md tests/test_source_layout.py
git commit -m "docs: align plan with flat package layout"
```
