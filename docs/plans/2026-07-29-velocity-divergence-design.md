# Velocity Divergence Design

## Goal

Add a generic PyVista dataset operation that calculates the divergence of the
velocity vector and stores it on the input dataset.

## Public API

Add this function to `shocklink.dataset`:

```python
def calc_velocity_divergence(
    dataset: pv.DataSet,
    *,
    velocity_name: str = "U [km/s]",
    output_name: str = "div(U)",
) -> pv.DataSet:
    ...
```

The function modifies `dataset` in place and returns the same object so callers
may either ignore the return value or chain it with other dataset operations.

## Calculation

The input velocity must be a three-component point-data array with shape
`(dataset.n_points, 3)`. The function will use PyVista's
`compute_derivative()` filter with gradient calculation disabled and
divergence enabled. This delegates spatial derivatives on structured and
unstructured meshes to VTK.

PyVista returns a filtered dataset rather than modifying the source. ShockLink
will copy only the calculated divergence point array back to the original
dataset. Existing arrays, topology, metadata, and object identity remain
unchanged. If `output_name` already exists, its values are replaced.

The default output name is unit-neutral because `shocklink.dataset` may receive
datasets whose coordinates use units other than Earth radii.

## Errors

Raise `DatasetError` when:

- `velocity_name` is absent from point data;
- the velocity array is not shaped `(dataset.n_points, 3)`;
- velocity values are non-finite;
- `output_name` is empty;
- PyVista cannot calculate the divergence;
- the filter does not produce a valid scalar point array.

## Testing

Use a PyVista image grid with the analytic vector field
`U = (x, y, z)`. Its divergence is exactly 3. Tests will verify the numeric
result, in-place object identity, custom input and output names, replacement of
an existing output, validation errors, and wrapped filter failures.
