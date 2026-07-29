# Bow-Shock Paraboloid Fit Design

## Goal

Identify the bow shock from strong compression, represented by large
`-div(U)`, and fit an axisymmetric paraboloid from three detected locations.

## Public API

Add to `shocklink.bowshock`:

```python
fit = fit_bow_shock(
    dataset,
    divergence_name="div(U)",
    velocity_name="U [km/s]",
    x_offset=2.0,
    axis_resolution=1000,
    cross_resolution=1000,
)
```

The function returns an immutable `BowShockParaboloid` with:

- `loc0`: shock nose detected on the X axis;
- `loc1`: shock intersection on the negative-Y side;
- `loc2`: shock intersection on the positive-Y side;
- `curvature`: fitted positive coefficient `a`;
- `x_at(y, z)`: evaluate the fitted surface.

The fitted surface is:

```text
x = x0 - a * (y**2 + z**2)
```

where `x0 = loc0[0]`.

## Detection

If `divergence_name` is absent from point data, call
`calc_velocity_divergence()` using `velocity_name` and store the derived array
on the input dataset.

Use `get_x_axis_profile()` to sample the full X axis at `y=z=0`. Ignore
samples that PyVista marks invalid and all non-finite divergence values.
Select the sample that maximizes `-div(U)`, equivalently the most negative
`div(U)`, as `loc0`.

Set the cross-line X coordinate to `loc0[0] - x_offset`. Sample the complete
dataset Y range at that X coordinate and `z=0` using `sample_line()`. Select
the most negative valid divergence value at `y<0` as `loc1` and independently
at `y>0` as `loc2`.

No threshold or smoothing is applied in this first implementation. The method
therefore follows the stated maximum-compression algorithm without introducing
simulation-dependent parameters.

## Fit

For each side point, define:

```text
delta_x_i = x0 - x_i
radius2_i = y_i**2 + z_i**2
```

Estimate the positive coefficient by least squares:

```text
a = sum(radius2_i * delta_x_i) / sum(radius2_i**2)
```

The two side points need not be perfectly symmetric. Retaining the detected
points exposes any asymmetry for inspection while the fitted model remains
axisymmetric.

## Errors

Raise clear ShockLink errors for:

- missing or malformed divergence data;
- no valid profile samples;
- no valid compression peak on either side of `y=0`;
- non-finite or nonpositive offsets and resolutions;
- a cross-line outside the dataset X bounds;
- degenerate points or a non-finite/nonpositive fitted curvature.

## Testing

Use a synthetic structured grid with a negative compression layer centered on
a known paraboloid. Verify the detected locations and recovered curvature
within sampling tolerance. Add tests for automatic divergence calculation,
valid-point masks, missing side peaks, out-of-bounds offsets, and invalid model
geometry. Run the existing dataset and bow-shock tests to guard module
boundaries.
