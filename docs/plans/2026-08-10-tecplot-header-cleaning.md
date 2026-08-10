# Tecplot Header Cleaning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Clean unit-bearing Tecplot variable headers in place before converting every zone to VTM.

**Architecture:** A standalone `tools/clean_dat.py` owns the reusable, same-length header rewrite. The VTM converter imports that function, runs it after validation and time extraction, and then passes the cleaned file directly to PyVista without modifying the returned zones.

**Tech Stack:** Python 3, pathlib, regular expressions, PyVista, pytest

---

### Task 1: Add the reusable standalone cleaner

**Files:**
- Create: `tools/clean_dat.py`
- Create: `tests/test_clean_dat.py`

**Step 1: Write failing tests**

Add tests that import the tool, clean `"X [R]"`, `"Y [R]"`, and `"Z [R]"` to exact coordinate names, remove units from physical variable names, preserve file size and all content following the header, support multiple input files from the executable CLI, and reject a file without `VARIABLES`.

**Step 2: Verify the tests fail**

Run: `pytest -q tests/test_clean_dat.py`

Expected: collection fails because `tools/clean_dat.py` does not exist.

**Step 3: Implement the cleaner**

Create an executable script with `CleanDatError`, `clean_dat(path)`, an argparse `-h` interface, and `main()`. Scan only until the first `ZONE`, rewrite the `VARIABLES` line using the existing two regular-expression transformations, preserve its newline and character count by padding it with spaces, and overwrite that exact line in place.

**Step 4: Verify the tests pass**

Run: `pytest -q tests/test_clean_dat.py`

Expected: all cleaner tests pass.

**Step 5: Commit**

Run:

```bash
git add tools/clean_dat.py tests/test_clean_dat.py
git commit -m "feat: add reusable Tecplot DAT cleaner"
```

### Task 2: Clean DAT input before conversion

**Files:**
- Modify: `tools/convert_dat_to_vtm.py`
- Modify: `tests/test_dat_to_vtm.py`

**Step 1: Write failing converter tests**

Change the Tecplot fixture to use unit-bearing variable names. Assert that conversion permanently cleans the source header, keeps all zone/data text unchanged, produces nonzero structured-grid coordinates, preserves the physical array under its cleaned name, and retains the already-cleaned input if PyVista reading fails.

**Step 2: Verify the tests fail**

Run: `pytest -q tests/test_dat_to_vtm.py`

Expected: geometry assertions fail because the converter has not called `clean_dat()`.

**Step 3: Integrate the cleaner**

Import `clean_dat` and `CleanDatError` from the sibling tool. Call the cleaner after `_read_time_event(source)` and before `pv.read(source)`, translate errors to `ConversionError`, and update module/help text to state that the DAT header is cleaned in place before conversion.

**Step 4: Verify targeted tests pass**

Run: `pytest -q tests/test_clean_dat.py tests/test_dat_to_vtm.py`

Expected: all cleaner and converter tests pass.

**Step 5: Commit**

Run:

```bash
git add tools/convert_dat_to_vtm.py tests/test_dat_to_vtm.py
git commit -m "fix: clean Tecplot coordinates before VTM conversion"
```

### Task 3: Verify and integrate

**Files:**
- Verify all changed files

**Step 1: Run syntax and help checks**

Run: `python -m py_compile tools/clean_dat.py tools/convert_dat_to_vtm.py`

Run: `tools/clean_dat.py -h && tools/convert_dat_to_vtm.py -h`

Expected: commands exit successfully and document in-place cleaning.

**Step 2: Run the complete test suite**

Run: `pytest -q`

Expected: all tests pass, apart from documented skips and any pre-existing warning.

**Step 3: Review the diff**

Run: `git diff main...HEAD --check && git status --short`

Expected: no whitespace errors and a clean feature worktree.

**Step 4: Merge into main**

Fast-forward the verified feature branch into `main`, rerun the targeted tests on `main`, and remove the temporary worktree and branch without touching untracked user data.
