# Bow-Shock Normal Field Design

## Goal

Calculate an outward unit-normal vector at every coordinate of the regular
bow-shock height map returned by `get_bow_shock_surface()`.

Missing surface values are interpolated before differentiation. Both interior
gaps and gaps at the edge of the measured surface footprint are filled.

## Public API

Add this domain-specific operation to `shocklink.bowshock`:

```python
normals = calc_bow_shock_normals(
    surface_x,
    y=y_values,
    z=z_values,
)
```

The inputs follow the existing surface-array convention:

```text
surface_x[i, j] = x of the bow shock at (y[i], z[j])
```

Return a floating-point array with shape `(len(y), len(z), 3)`, where:

```text
normals[i, j] = (n_x, n_y, n_z)
```

Every returned vector has unit magnitude. Use the outward orientation with a
strictly positive X component, so the normal at the shock nose points
sunward/upstream. Do not modify the input surface or coordinate arrays.

## Geometry

Parameterize the surface by:

```text
r(y, z) = (x_s(y, z), y, z)
```

Its coordinate tangents are:

```text
r_y = (dx_s/dy, 1, 0)
r_z = (dx_s/dz, 0, 1)
```

Their outward cross product is:

```text
r_y x r_z = (1, -dx_s/dy, -dx_s/dz)
```

Normalize this vector at every Y-Z coordinate:

```text
n = (1, -dx_s/dy, -dx_s/dz)
    / sqrt(1 + (dx_s/dy)**2 + (dx_s/dz)**2)
```

The fixed positive first component removes the two-sided normal ambiguity.

## Missing-Value Interpolation

Preserve all original finite `surface_x` values.

When the array contains `NaN`:

1. Build the regular Y-Z target mesh with `indexing="ij"`.
2. Use `scipy.interpolate.griddata(..., method="linear")` to fill points
   inside the convex hull of valid samples.
3. Use `griddata(..., method="nearest")` only for values that remain missing,
   including points outside the convex hull and edge gaps.
4. Restore original finite samples exactly before differentiation.

Require at least three non-collinear finite samples when interpolation is
needed. Translate a degenerate SciPy/Qhull interpolation failure into a
`DatasetError`.

Nearest-neighbor edge extrapolation makes the function defined across the
entire grid, but normals in extrapolated edge regions may be less accurate
than normals inside the measured footprint.

## Derivatives

Use:

```python
dx_dy, dx_dz = np.gradient(
    filled_surface,
    y,
    z,
    edge_order=2,
)
```

Passing the actual coordinate vectors supports both uniform and nonuniform
strictly increasing grids. Requiring at least three coordinates along both Y
and Z permits second-order one-sided differences at the boundaries.

## Validation and Errors

Reuse the bow-shock module's coordinate-axis validation and raise
`DatasetError` when:

- `y` or `z` is not a finite, strictly increasing 1D array with at least
  three values;
- `surface_x` is nonnumeric;
- its shape is not `(len(y), len(z))`;
- it contains positive or negative infinity;
- interpolation is required but fewer than three non-collinear finite values
  are available;
- SciPy interpolation fails or leaves non-finite values;
- derivative or normalization output is malformed or non-finite.

An entirely finite surface does not invoke interpolation.

## Dependency

Add:

```toml
"scipy>=1.14.1",
```

to the core project dependencies. SciPy 1.14.1 provides Python 3.13 support,
matching ShockLink's declared Python 3.11-3.13 range.

## Testing

Add focused tests that verify:

- a planar surface returns its exact constant analytic normal;
- a paraboloid returns the expected outward normal field;
- nonuniform Y/Z coordinates are handled correctly;
- every vector has unit magnitude and a positive X component;
- linear interpolation fills an interior hole;
- nearest interpolation fills edge and corner gaps;
- original finite values and input arrays are not modified;
- shape, type, infinity, short-axis, insufficient-finite-data, and degenerate
  interpolation errors are translated to `DatasetError`;
- the function is publicly exported from `shocklink.bowshock`;
- the complete existing suite remains green after adding SciPy.

No notebook change is part of this feature.
