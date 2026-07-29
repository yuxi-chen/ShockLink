# Bow-Shock Surface Array Design

## Goal

Extract the simulated bow shock from an existing shock-fit region as a
two-dimensional height map. At every requested transverse coordinate
`(y, z)`, the bow-shock X coordinate is the location where `div(U)` is most
negative.

The first implementation does not smooth, extrapolate, or triangulate the
surface.

## Public API

Add this domain-specific operation to `shocklink.bowshock`:

```python
surface_x = get_bow_shock_surface(
    shock_region,
    y=np.linspace(-20.0, 20.0, 161),
    z=np.linspace(-20.0, 20.0, 161),
    divergence_name="div(U)",
    x_resolution=512,
    x_range=None,
    chunk_size=1024,
)
```

The input is any compatible PyVista dataset, including the
`UnstructuredGrid` returned by `extract_shockfit_range()`.

`y` and `z` are finite, strictly increasing one-dimensional coordinate
arrays. When `x_range` is omitted, use the input dataset's X bounds. An
explicit `x_range=(x_min, x_max)` restricts the search to that interval.

Return a floating-point NumPy array with shape `(len(y), len(z))`. Its array
convention is:

```text
surface_x[i, j] = x of minimum div(U) at (y[i], z[j])
```

If a column has no valid sample, store `NaN` at that position. The function
does not modify the input dataset.

## Sampling Algorithm

Build a regular set of `x_resolution` X coordinates over the selected search
range. Form the Cartesian sampling columns for the requested Y and Z
coordinates using `ij` indexing.

Process a configurable number of flattened Y-Z columns at a time:

1. Construct one `pyvista.PolyData` containing every X sample for the current
   column chunk.
2. Sample `div(U)` from the input region with PyVista's enclosing-cell
   interpolation and static-cell locator.
3. Read `vtkValidPointMask` and reshape both the divergence values and mask to
   `(columns_in_chunk, x_resolution)`.
4. Exclude invalid and non-finite sampled values.
5. Select the X index of the minimum remaining divergence in each column.
6. Store the corresponding X coordinate in the correct `(y, z)` array
   position. Leave a column as `NaN` when it has no valid samples.

Chunking bounds temporary memory without changing the numerical result. It
also avoids invoking a separate VTK line-sampling filter for every `(y, z)`
coordinate.

## Alternatives Considered

### One line filter per Y-Z coordinate

Calling `sample_over_line()` for each column is direct and memory efficient,
but a useful surface would require thousands of separate VTK filter
invocations. The repeated setup cost makes it unsuitable as the default.

### Bin native mesh points

Assigning existing points to regular Y-Z bins would be fast, but results would
depend on adaptive-mesh point density and bin boundaries. Empty bins and
unequal cell sizes could make the surface discontinuous or biased. Enclosing-
cell interpolation evaluates the requested coordinates more consistently.

## Validation and Errors

Raise `DatasetError` when:

- the divergence name is empty;
- the named point array is missing, nonnumeric, non-finite, or not a scalar
  with one value per dataset point;
- `y` or `z` is not a nonempty, finite, strictly increasing 1D array;
- `x_range` does not contain two finite, strictly increasing values;
- the default dataset X bounds are non-finite or non-increasing;
- `x_resolution` is not an integer of at least two;
- `chunk_size` is not a positive integer;
- PyVista sampling fails;
- sampled divergence or validity arrays have unexpected shapes.

A valid sampling grid that does not intersect the input region is not an
error. Return an all-`NaN` surface.

## Testing

Use a small synthetic grid containing a compression layer centered on a known
surface `x = f(y, z)`. Verify:

- the result shape and `(y, z)` orientation;
- recovery of X within the configured X-sampling tolerance;
- selection of minimum `div(U)`, rather than maximum absolute divergence;
- identical results for different chunk sizes;
- `NaN` output for columns outside the source;
- custom divergence names and X ranges;
- validation failures and wrapped PyVista sampling failures;
- no mutation of the input dataset.

Add an opt-in large-data smoke test that reads `data/3d.dat`, calculates
`div(U)`, fits the paraboloid, extracts the shock-fit region, and verifies that
surface extraction produces a correctly shaped array with finite bow-shock
locations.
