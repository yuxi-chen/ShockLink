# VTK Time Metadata Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extract the Tecplot simulation timestamp and preserve it as time_event field data in the VTM output.

**Architecture:** Add a small header parser to the standalone converter using datetime and a strict BATSRUS TITLE timestamp pattern. Parse before pv.read, attach the normalized string to the root MultiBlock.field_data, then save the unchanged zones and metadata together.

**Tech Stack:** Python 3.11+, datetime, pathlib, PyVista 0.48+, pytest.

---

### Task 1: Add failing timestamp round-trip tests

**Files:**
- Modify: tests/test_dat_to_vtm.py

**Step 1: Write failing tests**

Update the fixture title to include 2023/12/16 11:30:00.000. After reloading the VTM, assert:

~~~python
assert reloaded.field_data["time_event"].item() == (
    "2023-12-16T11:30:00.000+00:00"
)
~~~

Add tests for a missing timestamp and an invalid date, asserting a conversion error and that no output metadata file is created.

**Step 2: Run tests to verify failure**

Run: pytest tests/test_dat_to_vtm.py -q

Expected: timestamp assertion fails because the current converter does not attach time_event; malformed-header tests fail because conversion currently proceeds.

### Task 2: Parse and attach simulation time

**Files:**
- Modify: tools/convert_dat_to_vtm.py

**Step 1: Implement minimal parser**

Add a compiled case-insensitive TITLE regex that captures YYYY/MM/DD HH:MM:SS[.fraction], parse with datetime.strptime, attach timezone.utc, and return isoformat(timespec="milliseconds"). Scan only the header before the first ZONE; raise ConversionError for missing, unreadable, or invalid timestamps.

Call the parser before pv.read, then assign:

~~~python
dataset.field_data["time_event"] = time_event
~~~

Keep all existing raw zone data and output-container behavior unchanged.

**Step 2: Run focused tests**

Run: pytest tests/test_dat_to_vtm.py -q

Expected: timestamp round-trip and malformed-header tests pass.

### Task 3: Document and verify

**Files:**
- Modify: README.md

**Step 1: Document metadata**

Explain that converted VTM files expose field_data["time_event"] as a normalized UTC ISO-8601 string.

**Step 2: Run checks**

Run: ruff check tools/convert_dat_to_vtm.py tests/test_dat_to_vtm.py

Run: pytest -q

Expected: lint is clean and all non-opt-in tests pass.

**Step 3: Commit**

~~~bash
git add README.md tools/convert_dat_to_vtm.py tests/test_dat_to_vtm.py
git commit -m "feat: preserve Tecplot simulation time in VTM"
~~~
