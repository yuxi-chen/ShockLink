# Default SWMF Output Name Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `--output` optional and generate `PARAM_YYYYMMDD_HHMMSS.in` from the effective UTC SWMF start time.

**Architecture:** Keep filename derivation in `mms_swmf.main()` after interval parsing and explicit start-time normalization. The parser returns `None` when `--output` is omitted; explicit output paths continue unchanged.

**Tech Stack:** Python datetime/argparse, pytest, Ruff

---

### Task 1: Add failing output-name tests

**Files:**
- Modify: `tests/test_mms_swmf.py`
- Modify: `tests/test_swmf_tool.py`

**Step 1: Write the failing tests**

Update parser tests to allow omitted `--output` and assert `arguments.output is None`. Extend the mocked `main()` workflow test to omit `--output` and assert `generate_param_file()` receives `PARAM_20181219_194600.in`. Add a workflow test with `--start-time 2018-12-19T14:52:00-05:00` and assert the output is `PARAM_20181219_195200.in`. Keep a case asserting an explicit output path is preserved. Update the executable-help test to expect that output is optional and document the generated filename pattern.

**Step 2: Run tests to verify failure**

Run: `python -m pytest tests/test_mms_swmf.py tests/test_swmf_tool.py -q`

Expected: FAIL because `--output` is currently required and `main()` has no default-name derivation.

### Task 2: Implement timestamp-based default output

**Files:**
- Modify: `src/shocklink/mms_swmf.py`
- Modify: `README.md`

**Step 1: Make the smallest implementation change**

Make `--output` optional with `default=None`. After computing the effective UTC
`start_time`, assign `output = arguments.output or f"PARAM_{start_time:%Y%m%d_%H%M%S}.in"`; pass and report `output`. Keep explicit output values unchanged.

Update parser help/epilog and README examples to explain the default filename.

**Step 2: Run focused verification**

Run: `python -m pytest tests/test_mms_swmf.py tests/test_swmf_tool.py tests/test_documentation.py -q`

Run: `ruff check src/shocklink/mms_swmf.py tests/test_mms_swmf.py tests/test_swmf_tool.py`

Expected: all tests and lint checks pass.

**Step 3: Commit**

```bash
git add src/shocklink/mms_swmf.py tests/test_mms_swmf.py tests/test_swmf_tool.py README.md docs/plans/2026-08-10-default-swmf-output-name.md
git commit -m "feat: default SWMF output to timestamped filename"
```

### Task 3: Full verification and integration

Run `python -m pytest`, `git diff --check`, and changed-file Ruff checks. Fast-forward the verified branch into `main`, rerun the full suite on merged `main`, then remove the worktree and branch.
