# Notebook Bow-Shock Surface Design

## Goal

Exercise `get_bow_shock_surface()` against the real `data/3d.dat` workflow in
`examples/tecplot_2d_cut.ipynb`, validate the resulting two-dimensional array,
and display it as a face-on Y-Z heat map.

The source notebook remains clean: no execution counts or saved outputs.

## Notebook Flow

Keep the existing read, divergence, paraboloid fit, shock-region extraction,
2D cut, pressure plot, and `div(U)` plot. Extend the bow-shock import to
include `get_bow_shock_surface`.

Add configurable surface-sampling values:

```python
SURFACE_Y = np.linspace(-20.0, 20.0, 81)
SURFACE_Z = np.linspace(-20.0, 20.0, 81)
SURFACE_X_RANGE = (-40.0, 20.0)
SURFACE_X_RESOLUTION = 241
SURFACE_CHUNK_SIZE = 256
```

After creating `shock_region`, calculate:

```python
surface_x = get_bow_shock_surface(
    shock_region,
    y=SURFACE_Y,
    z=SURFACE_Z,
    x_range=SURFACE_X_RANGE,
    x_resolution=SURFACE_X_RESOLUTION,
    chunk_size=SURFACE_CHUNK_SIZE,
)
```

The explicit X range concentrates the 241 samples on the plotted dayside
region instead of distributing them over the full extracted-grid bounds.
Chunking limits temporary probe memory while reusing the function's cell
locator.

## Validation and Summary

Require:

- `surface_x.shape == (len(SURFACE_Y), len(SURFACE_Z))`;
- at least one finite surface value;
- the central `y=0, z=0` surface value is finite.

Print the array shape, finite count and percentage, and finite minimum and
maximum X values. Missing columns remain `NaN` and are not treated as a
notebook failure unless the central column is missing or the entire array is
invalid.

## Y-Z Visualization

Create two `ij`-indexed coordinate arrays from `SURFACE_Y` and `SURFACE_Z`.
Build a flat `pyvista.StructuredGrid` at `x=0`, and attach the surface array
as point data named `"Bow-shock X [R]"`. Flatten the scalar array with Fortran
ordering so it matches VTK structured-grid point ordering.

Display the grid with:

- `"Bow-shock X [R]"` as the color scalar and color-bar title;
- a perceptually ordered colormap;
- an explicit color for `NaN` values;
- `view_yz()` and parallel projection;
- grid axes;
- the notebook's existing static Jupyter backend.

This is a flat heat map: Y and Z are geometric axes, while color represents
the extracted X coordinate. It does not warp or triangulate the surface.

## Notebook Tests

Extend `tests/test_notebook.py` to require:

- the `get_bow_shock_surface` import and call;
- all surface configuration variables;
- use of `shock_region` as the input;
- array-shape and finite-center assertions;
- `pv.StructuredGrid`, `"Bow-shock X [R]"`, Fortran flattening, `view_yz()`,
  and parallel projection;
- three static `show()` calls: pressure, `div(U)`, and the Y-Z surface map.

Retain all current cleanliness, portability, array, cut, and plotting
assertions.

## Real-Data Verification

Run the structural notebook tests first. Then execute the complete notebook
against `data/3d.dat` with `nbconvert`, writing the executed copy outside the
repository. Inspect the executed notebook for cell errors and confirm the
surface summary contains finite values and the third static visualization.

Finally, rerun the complete default test suite and verify the committed
notebook still has no saved output or execution counts.

No source-module or dependency changes are in scope.
