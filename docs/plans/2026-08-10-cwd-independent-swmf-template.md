# CWD-Independent SWMF Template Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve the default SWMF template from the ShockGeo repository regardless of the command's working directory.

**Architecture:** Define one absolute repository-template constant beside the CLI parser and use it only as argparse's default. Explicit `--input` values remain untouched and therefore retain caller-relative semantics.

**Tech Stack:** Python pathlib, argparse, pytest, Ruff

---

### Task 1: Make only the default template location-independent

**Files:**
- Modify: `src/shocklink/mms_swmf.py:8-10,59-99`
- Modify: `tests/test_mms_swmf.py:144-170,180-215`

**Step 1: Write failing parser regression tests**

Add tests which change to `tmp_path`, parse the required arguments without
`--input`, and assert that `arguments.input` is the absolute repository
`data/Param/PARAM.in.Earth` path and exists. Add a complementary parse asserting
that `--input custom/PARAM.in` remains exactly that relative path.

Update the main-workflow expectation so `generate_param_file()` receives the
repository template path.

**Step 2: Run tests and verify the default-path test fails**

Run: `python -m pytest tests/test_mms_swmf.py -q`

Expected: FAIL because the default remains `data/Param/PARAM.in.Earth` relative
to `tmp_path`.

**Step 3: Implement the minimal fix**

Import `Path` and define:

```python
_DEFAULT_TEMPLATE = (
    Path(__file__).resolve().parents[2] / "data" / "Param" / "PARAM.in.Earth"
)
```

Use `_DEFAULT_TEMPLATE` as the `--input` default. Do not change its `type`, so
explicit input strings remain unchanged. Keep the concise, portable help text.

**Step 4: Run focused verification**

Run: `python -m pytest tests/test_mms_swmf.py tests/test_swmf_tool.py -q`

Run: `ruff check src/shocklink/mms_swmf.py tests/test_mms_swmf.py tests/test_swmf_tool.py`

Expected: all checks pass.

**Step 5: Commit**

```bash
git add src/shocklink/mms_swmf.py tests/test_mms_swmf.py docs/plans/2026-08-10-cwd-independent-swmf-template.md
git commit -m "fix: resolve default SWMF template from repository"
```

### Task 2: Verify and integrate

**Step 1:** Run `python -m pytest` and confirm no failures.

**Step 2:** Run changed-file Ruff checks and `git diff --check`.

**Step 3:** Fast-forward the verified branch into `main`, rerun the full suite
on merged `main`, and remove the merged worktree and branch.
