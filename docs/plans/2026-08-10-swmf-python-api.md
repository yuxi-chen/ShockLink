# SWMF Python API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Expose the complete SWMF input workflow as a reusable Python function and make the CLI delegate to it.

**Architecture:** Add `create_swmf_input()` in `shocklink.mms_swmf` with the same options as the CLI, returning the generated `Path` and propagating exceptions. Keep `main()` responsible only for argparse, user-facing error handling, status output, and process code.

**Tech Stack:** Python pathlib/datetime/typing, argparse, pytest, Ruff, Markdown

---

### Task 1: Add failing API and delegation tests

**Files:**
- Modify: `tests/test_mms_swmf.py`
- Modify: `tests/test_swmf_tool.py`
- Modify: `tests/test_documentation.py`

**Step 1: Write failing tests**

Add a direct `create_swmf_input()` test with mocked MMS loading and generation,
passing all CLI options (`mms_start`, `mms_end`, `output`, `input`,
`start_time`, `probe`, `mode`) and asserting the returned `Path`, loader
arguments, GSM coordinates, and generated values. Add tests for default output,
datetime start-time input, invalid probe/mode rejection, and CLI delegation.
Assert the README includes a Python/notebook usage snippet and the public API
name.

**Step 2: Run focused tests to verify failure**

Run: `python -m pytest tests/test_mms_swmf.py tests/test_swmf_tool.py tests/test_documentation.py -q`

Expected: FAIL because `create_swmf_input` is not defined and documentation is absent.

### Task 2: Implement and document the public API

**Files:**
- Modify: `src/shocklink/mms_swmf.py`
- Modify: `README.md`

**Step 1: Implement the function**

Add the typed `create_swmf_input()` function with all CLI options. Validate
`probe` in 1–4 and `mode` in `auto`/`brst`/`fast`; accept string or datetime
`start_time`, normalize to UTC, use the existing repository-derived default
template, derive the timestamped output when omitted, call the existing MMS
loader and generator, and return `Path(output)`.

**Step 2: Refactor `main()`**

Keep parser behavior unchanged, call `create_swmf_input()` with parsed values,
print the returned path on success, and preserve the existing stderr/error-code
behavior on exceptions.

**Step 3: Document script/notebook usage**

Add a README Python example showing all options and the returned `Path`, while
retaining the CLI example.

**Step 4: Run focused verification**

Run: `python -m pytest tests/test_mms_swmf.py tests/test_swmf_tool.py tests/test_documentation.py -q`

Run: `ruff check src/shocklink/mms_swmf.py tests/test_mms_swmf.py tests/test_swmf_tool.py tests/test_documentation.py`

Expected: all checks pass.

**Step 5: Commit**

```bash
git add src/shocklink/mms_swmf.py tests/test_mms_swmf.py tests/test_swmf_tool.py tests/test_documentation.py README.md docs/plans/2026-08-10-swmf-python-api.md
git commit -m "feat: expose SWMF input generation Python API"
```

### Task 3: Full verification and integration

Run `python -m pytest`, `git diff --check`, and changed-file Ruff checks. Fast-forward the verified branch into `main`, rerun the full suite on merged `main`, then remove the worktree and branch.
