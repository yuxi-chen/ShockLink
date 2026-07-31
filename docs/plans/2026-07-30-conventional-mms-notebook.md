# Conventional MMS Notebook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restructure the MMS example notebook into an output-free, guided Jupyter workflow.

**Architecture:** Only the notebook and its structural tests change. Existing `mms_data_analysis` functions remain the single implementation for downloading, summarizing, and plotting.

**Tech Stack:** Jupyter nbformat, pytest, Python.

---

### Task 1: Test and create the guided notebook layout

**Files:**
- Modify: `examples/mms_data_analysis.ipynb`
- Modify: `tests/test_notebook.py`

**Step 1: Write the failing test**

Add a structural test requiring Markdown headings for Requirements, Parameters,
Download MMS data, Inspect loaded products, Summary statistics, Plot data, and
Troubleshooting; assert an editable parameter cell and zero saved outputs.

**Step 2: Run the test to verify it fails**

Run: `pytest tests/test_notebook.py -k mms -v`

Expected: FAIL because the guided headings are absent.

**Step 3: Implement the minimal layout**

Replace the compact notebook with Markdown guidance and separate code cells for
imports, editable settings, loading/status, product inspection, summary, and
plotting. Keep the root-compatible import setup, `MODE = "auto"`, empty
outputs, and null execution counts.

**Step 4: Run the test to verify it passes**

Run: `pytest tests/test_notebook.py -k mms -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add examples/mms_data_analysis.ipynb tests/test_notebook.py
git commit -m "docs: guide MMS analysis notebook workflow"
```

### Task 2: Verify and merge

**Files:**
- Verify: changed notebook and tests

**Step 1: Run focused validation**

Run: `pytest tests/test_notebook.py tests/test_mms_data_analysis.py -v`

Expected: PASS.

**Step 2: Run full validation**

Run: `pytest`

Expected: PASS with expected integration skips.
