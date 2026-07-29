# 2D Plot Ranges Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add validated `xrange` and `yrange` camera limits to `plot_2d_cut()` without changing plotted data.

**Architecture:** Convert each supplied range into a validated two-value NumPy array, fill omitted axes from `cut.bounds`, and reset the already-oriented parallel camera to the resulting world-coordinate bounds.

**Tech Stack:** Python 3.11+, NumPy, PyVista, pytest, real BATSRUS sample.

---

### Task 1: Add test-driven camera ranges

**Files:**
- Modify: `tests/test_tecplot_plot.py`
- Modify: `src/shocklink/tecplot.py`

**Step 1: Extend the recording plotter**

Record `reset_camera(bounds=..., render=...)` calls.

**Step 2: Write failing tests**

Test:

```python
plot_2d_cut(
    cut,
    xrange=(-0.25, 0.5),
    yrange=(-0.75, 0.25),
    plotter=plotter,
    show=False,
)

assert plotter.camera_bounds == pytest.approx(
    (-0.25, 0.5, -0.75, 0.25, cut.bounds.z_min, cut.bounds.z_max)
)
assert plotter.mesh is cut
```

Also verify:

- omitted limits do not call `reset_camera`;
- one omitted axis uses the cut's complete bounds;
- malformed, nonnumeric, nonfinite, equal, and reversed limits raise
  `DatasetError`; and
- errors identify `xrange` or `yrange`.

**Step 3: Run tests to verify they fail**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python -m pytest tests/test_tecplot_plot.py -v
```

Expected: FAIL because `plot_2d_cut` does not accept the new parameters as
camera controls.

**Step 4: Implement minimal range handling**

Add:

```python
xrange: Sequence[float] | None = None
yrange: Sequence[float] | None = None
```

Use a private helper to validate each range. After `view_vector()` and
`enable_parallel_projection()`, call:

```python
plotter.reset_camera(
    bounds=(x_min, x_max, y_min, y_max, z_min, z_max),
    render=False,
)
```

only when at least one range is supplied.

**Step 5: Run focused and complete tests**

Run the focused plotting tests, then the full ordinary suite.

Expected: all tests PASS.

**Step 6: Commit directly to main**

```bash
git add src/shocklink/tecplot.py tests/test_tecplot_plot.py
git commit -m "feat: limit 2D plot camera ranges"
```

### Task 2: Expose ranges in the example and verify real rendering

**Files:**
- Modify: `examples/plot_2d_cut.py`
- Modify: `examples/README.md`

**Step 1: Add CLI range arguments**

Add `--xrange MIN MAX` and `--yrange MIN MAX`, then forward them to
`plot_2d_cut()`.

**Step 2: Update example documentation**

Document:

```bash
PYTHONPATH=src python examples/plot_2d_cut.py data/3d.dat \
  --xrange -40 30 --yrange -60 60
```

**Step 3: Render the restricted real-data view**

Run outside the sandbox:

```bash
PYTHONPATH=src python examples/plot_2d_cut.py data/3d.dat \
  --xrange -40 30 --yrange -60 60 \
  --screenshot /tmp/shocklink-pressure-limited.png
```

Visually verify that the plot is restricted and retains the pressure scalar bar.

**Step 4: Run final verification**

Run ordinary tests, the real-data integration suite, and build the wheel.
Confirm the user's untracked `pressure-z0.png` remains untouched.

**Step 5: Commit directly to main**

```bash
git add examples/plot_2d_cut.py examples/README.md docs/plans/2026-07-29-plot-ranges-design.md docs/plans/2026-07-29-plot-ranges.md
git commit -m "docs: demonstrate limited 2D plot ranges"
```
