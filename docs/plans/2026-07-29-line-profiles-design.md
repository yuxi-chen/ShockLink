# Line Profile Design

## Goal

Extract interpolated values along arbitrary lines in any compatible PyVista
dataset, while providing a convenient profile along the GSM X axis.

## Public API

```python
profile = sample_line(
    dataset,
    pointa=(-40.0, 0.0, 0.0),
    pointb=(30.0, 0.0, 0.0),
    resolution=1000,
)

x_axis_profile = get_x_axis_profile(dataset)
```

Both functions return `pyvista.PolyData`. Its points are the sampled line
coordinates and its point data contains the interpolated source arrays.

## Responsibilities

`sample_line()` is the generic primitive. It validates finite three-component
endpoints, a positive integer resolution, and an optional finite nonnegative
tolerance, then delegates interpolation to PyVista's `sample_over_line()`.
It wraps filter failures in `DatasetError` and verifies that a nonempty
`PolyData` result was produced.

`get_x_axis_profile()` is a thin wrapper. It takes optional `y`, `z`,
`resolution`, and `tolerance` arguments; derives endpoints from the dataset's
finite, strictly increasing X bounds; and delegates to `sample_line()`.

The default resolution is 1,000 intervals (1,001 points). This avoids
PyVista's default of one interval per mesh cell, which is too expensive for
large 3D simulation grids. Any partially out-of-domain samples remain visible
through PyVista's valid-point mask rather than being removed.

## Testing

Tests will sample analytic fields on a small image grid to verify interpolated
coordinates and scalar/vector values, parameter forwarding by the X-axis
wrapper, validation errors, and wrapped PyVista failures.
