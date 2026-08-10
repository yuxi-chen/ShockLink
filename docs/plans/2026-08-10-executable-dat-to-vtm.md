# Executable DAT-to-VTM Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `tools/convert_dat_to_vtm.py` directly executable and add useful examples to its `-h/--help` output.

**Architecture:** Preserve the existing conversion API and CLI arguments. Add only a portable Python shebang, executable file mode, and argparse help formatting with a literal examples epilog.

**Tech Stack:** Python 3.11+, argparse, pytest, POSIX executable permissions.

---

### Task 1: Specify executable and help behavior

**Files:**
- Modify: `tests/test_dat_to_vtm.py`

**Step 1: Write failing tests**

Add a test that asserts `os.access(TOOL, os.X_OK)` and invokes `[str(TOOL), "-h"]`. Assert exit status zero and help text containing `usage:`, `--delete-input`, and examples for default output, explicit output, and input deletion.

Update the existing subprocess helper to invoke `TOOL` directly so the conversion tests exercise the executable entry point.

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_dat_to_vtm.py -q`

Expected: FAIL because the tool lacks executable mode and its help lacks examples.

### Task 2: Add executable entry point and help examples

**Files:**
- Modify: `tools/convert_dat_to_vtm.py`

**Step 1: Implement minimal behavior**

Add `#!/usr/bin/env python` as the first line so the executable uses the active project or virtual-environment interpreter. Configure the argument parser with `formatter_class=argparse.RawDescriptionHelpFormatter` and an epilog containing:

```text
examples:
  convert_dat_to_vtm.py input.dat
  convert_dat_to_vtm.py input.dat output.vtm
  convert_dat_to_vtm.py input.dat --delete-input
```

Set the tool file mode executable without changing conversion behavior.

**Step 2: Run focused tests**

Run: `pytest tests/test_dat_to_vtm.py -q`

Expected: all converter tests pass.

### Task 3: Verify and integrate

**Files:**
- Modify: `README.md`

**Step 1: Update documented invocations**

Show direct `./tools/convert_dat_to_vtm.py` usage and mention `-h`.

**Step 2: Run checks**

Run: `ruff check tools/convert_dat_to_vtm.py tests/test_dat_to_vtm.py`

Run: `pytest -q`

Expected: lint is clean and all non-opt-in tests pass.

**Step 3: Commit**

```bash
git add README.md tools/convert_dat_to_vtm.py tests/test_dat_to_vtm.py
git commit -m "feat: make DAT-to-VTM tool executable"
```
