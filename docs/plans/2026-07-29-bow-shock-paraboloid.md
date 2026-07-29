# Bow-Shock Paraboloid Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Detect three maximum-compression locations from `-div(U)` and fit an axisymmetric bow-shock paraboloid.

**Architecture:** The domain-specific fit lives in `shocklink.bowshock` and reuses the generic derivative and line-profile operations from `shocklink.dataset`. Detection operates on valid sampled point data; an immutable model stores the three points and fitted curvature.

**Tech Stack:** Python, NumPy, PyVista, pytest

---

### Task 1: Define the paraboloid model

**Files:**
- Modify: `tests/bowshock/test_models.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Write failing model tests**

Create `BowShockParaboloid` with:

```python
loc0 = (10.0, 0.0, 0.0)
loc1 = (8.0, -2.0, 0.0)
loc2 = (8.0, 2.0, 0.0)
curvature = 0.5
```

Assert locations are immutable arrays and `x_at(2, 0) == 8`. Add validation
tests for malformed/non-finite locations, an off-axis nose, incorrectly signed
side points, and nonpositive curvature.

**Step 2: Verify RED**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python -m pytest tests/bowshock/test_models.py -q
```

Expected: import failure because `BowShockParaboloid` is absent.

**Step 3: Implement and verify GREEN**

Add the frozen, slotted dataclass and export it. Run the focused test and
expect all model tests to pass.

### Task 2: Detect and fit a synthetic shock

**Files:**
- Create: `tests/bowshock/test_fit.py`
- Modify: `src/shocklink/bowshock.py`

**Step 1: Write the failing analytic test**

Create an image grid with:

```python
residual = x - (10.0 - 0.5 * (y**2 + z**2))
div_u = -np.exp(-(residual / 0.15) ** 2)
```

Call:

```python
fit = fit_bow_shock(
    grid,
    x_offset=2.0,
    axis_resolution=240,
    cross_resolution=320,
)
```

Assert `loc0 ≈ (10, 0, 0)`, side locations are approximately `(8, -2, 0)`
and `(8, 2, 0)`, curvature is approximately `0.5`, and `x_at()` evaluates the
known surface.

**Step 2: Verify RED**

Run the fit test and expect import failure because `fit_bow_shock` is absent.

**Step 3: Implement detection**

If `div(U)` is absent, call `calc_velocity_divergence()`. Validate an existing
point scalar array. Sample the X axis, filter non-finite values and
`vtkValidPointMask == 0`, then choose `argmax(-div(U))`.

Sample the full Y bounds at `x=loc0[0]-x_offset, z=0`. Independently choose the
maximum `-div(U)` among valid negative-Y and positive-Y samples.

**Step 4: Implement the fit**

Calculate:

```python
radius2 = y**2 + z**2
delta_x = x0 - x
curvature = np.sum(radius2 * delta_x) / np.sum(radius2**2)
```

Return `BowShockParaboloid`.

**Step 5: Verify GREEN**

Run the analytic fit test and expect it to pass.

### Task 3: Cover automatic calculation and failures

**Files:**
- Modify: `tests/bowshock/test_fit.py`

**Step 1: Add tests**

Cover:

- automatic `calc_velocity_divergence()` when `div(U)` is absent;
- reuse of an existing divergence array;
- invalid/non-scalar divergence;
- valid-point masks;
- no valid negative- or positive-Y peak;
- nonpositive/non-finite `x_offset`;
- cross-line X outside dataset bounds;
- invalid resolutions delegated from dataset sampling;
- nonphysical fitted curvature.

Use monkeypatching only at the filter boundary where constructing the failure
geometrically would obscure the behavior.

**Step 2: Run focused tests**

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest \
  tests/bowshock/test_models.py tests/bowshock/test_fit.py \
  tests/test_dataset_profiles.py tests/test_dataset_derivatives.py -q
```

Expected: all focused tests pass.

**Step 3: Commit**

```bash
git add src/shocklink/bowshock.py \
  tests/bowshock/test_models.py tests/bowshock/test_fit.py
git commit -m "feat: fit bow-shock paraboloid"
```

### Task 4: Verify the repository and package

Run the full ordinary suite, build a wheel, inspect the flat package layout,
and ensure the only unrelated working-tree item remains `pressure-z0.png`.
For the large sample, run the fit with reduced diagnostic resolutions and
report the detected locations and curvature without adding generated files.
