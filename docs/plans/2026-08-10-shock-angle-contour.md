# Shock Angle Contour Styling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `plot_shock_angle_contour` visually similar to the reference `plot_2d_theta` plot while preserving ShockLink’s reusable API and validation guarantees.

**Architecture:** Keep all rendering in `src/shocklink/connectivity.py`. Extend the function with optional style/range arguments, derive safe default limits from the selected intersection, and render the filled map, threshold isolines, metadata, and annotation on the existing or newly-created axes. Add focused Agg-backend tests in `tests/test_connectivity.py`; do not alter the geometry/data model.

**Tech Stack:** Python 3, NumPy, Matplotlib, pytest.

---

### Task 1: Add failing tests for reference-style output

**Files:**
- Modify: `tests/test_connectivity.py` near `test_plot_shock_angle_contour_masks_holes_and_marks_intersection`

**Step 1: Write the failing test**

Add Agg-backend tests that call `plot_shock_angle_contour` with the existing plane fixture and assert:

- the default figure size is `(10, 8)` when no axes is supplied;
- default filled contours use the requested dense level count and `viridis` colormap;
- the colorbar has 10-degree ticks and a `theta_BN` degree label;
- 45° and 50° dashed contour lines are present when the data spans them;
- limits are symmetric and selected from the reference buckets;
- text includes MMS, IMF, and Intersection metadata;
- the intersection marker/angle annotation is red;
- explicit `cmap`, `yrange`, and `zrange` values are honored.

Retain the existing tests for masking, supplied axes, and invalid levels.

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_connectivity.py -k plot_shock_angle_contour -v`

Expected: the new assertions fail because the current function lacks the added arguments, reference styling, metadata, and adaptive limits.

### Task 2: Implement compatible plotting options and defaults

**Files:**
- Modify: `src/shocklink/connectivity.py:315-380`

**Step 1: Add the minimal API changes**

Extend the signature with keyword-only `cmap: str = "viridis"`, `yrange: ArrayLike | None = None`, and `zrange: ArrayLike | None = None`. Preserve existing `ax` and `levels` behavior.

**Step 2: Implement safe range selection and validation**

Use the selected intersection’s Y/Z coordinates to choose symmetric default bounds in the sequence ±15, ±20, ±25, ±28, matching the reference thresholds. If either explicit range is supplied, require both and validate each as a finite two-value increasing range. Do not mutate caller axes limits beyond the function’s intended plot configuration.

**Step 3: Implement reference-style rendering**

Use dense default levels over 0–90°, the selected colormap, reference-like font sizes/tick widths, 10° colorbar ticks, and the reference axis labels. Add dashed 45° black and 50° blue contours only when those values are within the finite data range, with degree labels. Keep masked invalid cells masked.

**Step 4: Implement intersection and metadata presentation**

Render the selected intersection as a red marker, add a nearby red local-angle label, and place formatted MMS, IMF, and full intersection coordinate strings below the axes using axes-relative coordinates. Keep the existing full GSM coordinate annotation or replace it with equivalent visible information.

**Step 5: Preserve figure/axes composition behavior**

Create a 10×8-inch figure only when `ax is None`; reuse supplied axes and its figure. Apply layout tightening to the created figure without changing global `matplotlib.rcParams`.

### Task 3: Verify behavior and regression safety

**Files:**
- Test: `tests/test_connectivity.py`
- Modify: `src/shocklink/connectivity.py`

**Step 1: Run focused tests**

Run: `pytest tests/test_connectivity.py -k plot_shock_angle_contour -v`

Expected: all focused plotting tests pass.

**Step 2: Run the full test suite**

Run: `pytest -q`

Expected: the full suite passes with no failures.

**Step 3: Review the diff**

Run: `git diff --check && git diff -- src/shocklink/connectivity.py tests/test_connectivity.py`

Expected: no whitespace errors, no unrelated file changes, and the public function documentation describes the new options and styling.

**Step 4: Commit the implementation**

```bash
git add src/shocklink/connectivity.py tests/test_connectivity.py
git commit -m "feat: style shock angle contour like reference plot"
```
