# SWMF MMS Input Generator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate a new SWMF Earth parameter file whose `#STARTTIME` and `#SOLARWIND` values come from an MMS GSM interval.

**Architecture:** Keep pure timestamp, mapping, and template-editing logic in `src/shocklink/swmf.py`; reuse `shocklink.mms.load_mms_data` and `average_plotted_values` at the orchestration boundary. Expose a thin executable example script.

**Tech Stack:** Python 3.11+, dataclasses, `argparse`, existing ShockLink MMS API, pytest.

---

### Task 1: Add failing pure-helper tests

**Files:**
- Create: `tests/test_swmf.py`

**Step 1: Write the failing tests**

Cover midpoint and explicit timestamp formatting, MMS average mapping with the required temperature conversion, marker-aware replacement of the two sections, preservation of unrelated template text, and errors for missing labels/nonfinite values.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_swmf.py -q`

Expected: collection or import failures because `shocklink.swmf` does not yet exist.

### Task 2: Implement pure SWMF generation helpers

**Files:**
- Create: `src/shocklink/swmf.py`

**Step 1: Implement minimal behavior**

Add a `SolarWindValues` dataclass, UTC parser and midpoint helper, conversion from `average_plotted_values` output, start-time field formatting, section-scoped label replacement, and `generate_param_file(template, output, start_time, solar_wind)`.

Require finite density, temperature, velocity components, and magnetic-field components. Preserve line endings and all untouched lines; raise `ValueError` for malformed sections and `FileNotFoundError`/`OSError` from file operations.

**Step 2: Run pure tests**

Run: `pytest tests/test_swmf.py -q`

Expected: PASS.

### Task 3: Add failing CLI tests and executable entry point

**Files:**
- Modify: `tests/test_swmf.py`
- Create: `examples/create_swmf_input.py`

**Step 1: Write failing CLI tests**

Mock `load_mms_data` and `average_plotted_values` to verify that the CLI loads the requested interval in GSM, uses the midpoint by default, honors `--start-time`, writes the requested output, and returns a nonzero result for MMS failures or empty averages.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_swmf.py -q`

Expected: FAIL because `main` and the executable entry point do not yet exist.

### Task 4: Implement CLI orchestration

**Files:**
- Modify: `src/shocklink/swmf.py`
- Create: `examples/create_swmf_input.py`

**Step 1: Implement the CLI**

Add arguments for `--mms-start`, `--mms-end`, required `--output`, optional `--input` defaulting to `data/Param/PARAM.in.Earth`, optional `--start-time`, `--probe` (1–4, default 1), and `--mode` (`auto`, `brst`, `fast`, default `auto`). Load with `coordinates="gsm"`, compute averages, generate the output, and report actionable errors with exit code 1.

**Step 2: Run CLI tests**

Run: `pytest tests/test_swmf.py -q`

Expected: PASS.

### Task 5: Verify integration and repository quality

**Files:**
- Modify: `tests/test_swmf.py` if needed for final coverage

**Step 1: Run focused and full tests**

Run: `pytest tests/test_swmf.py -q` and then `pytest -q`.

Expected: focused tests pass and the full suite remains at least 228 passed with no new failures.

**Step 2: Run static checks**

Run: `ruff check src/shocklink/swmf.py examples/create_swmf_input.py tests/test_swmf.py`

Expected: no lint errors.

**Step 3: Commit the implementation**

```bash
git add src/shocklink/swmf.py examples/create_swmf_input.py tests/test_swmf.py docs/plans/2026-08-04-swmf-input-generator-design.md docs/plans/2026-08-04-swmf-input-generator.md
git commit -m "feat: generate SWMF input from MMS averages"
```
