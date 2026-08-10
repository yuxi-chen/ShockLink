# Executable SWMF Input Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Move the SWMF input generator into `tools/` as a documented, directly executable command with useful help output.

**Architecture:** Keep `tools/create_swmf_input.py` as a thin executable wrapper around `shocklink.mms_swmf.main()`. Keep argument parsing and runtime behavior in the package module, where parser help can be tested directly and reused by the tool.

**Tech Stack:** Python 3.11+, argparse, pytest, Ruff, Git executable mode

---

### Task 1: Move and make the entry point executable

**Files:**
- Delete: `examples/create_swmf_input.py`
- Create: `tools/create_swmf_input.py`
- Delete: `tests/test_swmf_example.py`
- Create: `tests/test_swmf_tool.py`

**Step 1: Write the failing entry-point test**

Move the test module to `tests/test_swmf_tool.py` and make it verify the new path before the tool exists:

```python
from __future__ import annotations

import ast
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "create_swmf_input.py"


def test_swmf_tool_is_an_executable_thin_entry_point() -> None:
    source = TOOL.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert os.access(TOOL, os.X_OK)
    assert TOOL.read_bytes().splitlines()[0] == b"#!/usr/bin/env python"
    assert [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)] == []
    assert "from shocklink.mms_swmf import main" in source
    assert "raise SystemExit(main())" in source
```

**Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_swmf_tool.py -q`

Expected: FAIL because `tools/create_swmf_input.py` does not exist.

**Step 3: Move the wrapper and add executable metadata**

Create the new tool with only the executable entry-point behavior:

```python
#!/usr/bin/env python
"""Generate an SWMF input file from interval-averaged MMS observations."""

from shocklink.mms_swmf import main


if __name__ == "__main__":
    raise SystemExit(main())
```

Remove `examples/create_swmf_input.py` and set mode `755` on the new file.

**Step 4: Run the test to verify it passes**

Run: `python -m pytest tests/test_swmf_tool.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add examples/create_swmf_input.py tools/create_swmf_input.py tests/test_swmf_example.py tests/test_swmf_tool.py
git commit -m "refactor: move SWMF input generator to tools"
```

### Task 2: Add comprehensive command help

**Files:**
- Modify: `src/shocklink/mms_swmf.py`
- Modify: `tests/test_swmf_tool.py`

**Step 1: Write the failing help test**

Add a subprocess test that executes `TOOL -h` with the worktree's `src/` prepended to `PYTHONPATH`, then asserts that help exits successfully and contains `usage:`, every option, defaults for input/probe/mode, `examples:`, and example commands for basic use and overrides.

**Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_swmf_tool.py::test_swmf_tool_help_explains_options_and_shows_examples -q`

Expected: FAIL because the current parser has neither detailed defaults nor examples.

**Step 3: Implement the enhanced parser help**

Update `parse_args()` to use `argparse.RawDescriptionHelpFormatter`, an epilog with direct `create_swmf_input.py` examples, and explicit help text for `--start-time`, `--probe`, and `--mode`. Preserve all existing argument names, choices, required flags, and defaults.

**Step 4: Run focused tests**

Run: `python -m pytest tests/test_swmf_tool.py tests/test_mms_swmf.py -q`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/shocklink/mms_swmf.py tests/test_swmf_tool.py
git commit -m "feat: document SWMF input command options"
```

### Task 3: Document usage and verify the feature

**Files:**
- Modify: `README.md`
- Modify: `tests/test_documentation.py`

**Step 1: Write the failing documentation test**

Add assertions that `README.md` references `./tools/create_swmf_input.py`, its `-h` command, the `mms` optional dependency, and no longer presents the removed examples path as the executable.

**Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_documentation.py -q`

Expected: FAIL because the README does not yet document the tool.

**Step 3: Add the README section**

Document `pip install -e ".[mms]"`, required start/end/output arguments, default template, generated `#STARTTIME` and `#SOLARWIND` values, a representative direct command, and `./tools/create_swmf_input.py -h`.

**Step 4: Run targeted verification**

Run: `python -m pytest tests/test_swmf_tool.py tests/test_mms_swmf.py tests/test_documentation.py -q`

Run: `ruff check tools/create_swmf_input.py src/shocklink/mms_swmf.py tests/test_swmf_tool.py tests/test_documentation.py`

Expected: all tests and lint checks pass.

**Step 5: Commit**

```bash
git add README.md tests/test_documentation.py docs/plans/2026-08-10-create-swmf-input-tool.md
git commit -m "docs: explain SWMF input generation"
```

### Task 4: Final verification and integration

**Step 1: Run the complete suite**

Run: `python -m pytest`

Expected: 323 or more tests pass, 3 integration tests skip, and no failures occur.

**Step 2: Run repository lint**

Run: `ruff check .`

Expected: PASS.

**Step 3: Inspect the final diff**

Run: `git status --short && git diff main...HEAD --check && git diff main...HEAD --stat`

Expected: only the approved tool, parser, tests, README, and planning document changes appear; whitespace validation passes.

**Step 4: Merge into main**

Return to the primary checkout and fast-forward `main` to the verified feature branch, preserving unrelated untracked files.
