# VTK Output Container Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Write the VTM metadata file and every generated sidecar beneath one `_vtk` output directory.

**Architecture:** Derive a container directory independently from the metadata filename: `sample.dat` maps to container `sample_vtk/` and metadata `sample_vtk/sample.vtm`. Keep the raw PyVista read/save path and post-save input deletion unchanged.

**Tech Stack:** Python 3.11+, pathlib, PyVista 0.48+, argparse, pytest.

---

### Task 1: Specify the new output layout

**Files:**
- Modify: `tests/test_dat_to_vtm.py`

**Step 1: Write failing tests**

Change the default-output test to expect:

```python
container = tmp_path / "sample_vtk"
metadata = container / "sample.vtm"
assert metadata.is_file()
assert (container / "sample").is_dir()
```

Assert the reloaded metadata still preserves both zones and arrays. Change the explicit-output test so its second argument is a directory such as `tmp_path / "custom_vtk"`, with metadata at `custom_vtk/input.vtm`. Update deletion tests to expect `input_vtk/input.vtm`.

Update the help test to assert that the positional argument and examples describe an output directory.

**Step 2: Run tests to verify failure**

Run: `pytest tests/test_dat_to_vtm.py -q`

Expected: layout and help assertions fail against the current direct `.vtm` output behavior.

### Task 2: Derive and create the output container

**Files:**
- Modify: `tools/convert_dat_to_vtm.py`

**Step 1: Implement minimal path behavior**

Replace the optional output-file interpretation with an optional output-directory interpretation. For source `sample.dat`:

```python
container = output_directory or source.with_name(f"{source.stem}_vtk")
destination = container / source.with_suffix(".vtm").name
```

Reject a container path that already exists as a non-directory. Create the container before calling `dataset.save(destination)`. Keep the `MultiBlock` unchanged and unlink the source only after save returns successfully.

Update argparse help, success output, and epilog examples to call the second argument an output directory.

**Step 2: Run focused tests**

Run: `pytest tests/test_dat_to_vtm.py -q`

Expected: all converter tests pass, including default/custom layouts and deletion safety.

### Task 3: Update documentation and verify

**Files:**
- Modify: `README.md`

**Step 1: Document the layout**

Show `sample_vtk/sample.vtm`, explain that the optional second argument names the container directory, and retain the `-h` and `--delete-input` examples.

**Step 2: Run checks**

Run: `ruff check tools/convert_dat_to_vtm.py tests/test_dat_to_vtm.py`

Run: `pytest -q`

Expected: lint passes and all non-opt-in tests pass.

**Step 3: Commit**

```bash
git add README.md tools/convert_dat_to_vtm.py tests/test_dat_to_vtm.py
git commit -m "feat: group VTM outputs in container directory"
```
