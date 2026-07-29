# 2D Plot Range Design

## Goal

Add optional `xrange` and `yrange` arguments to `plot_2d_cut()` so callers can
limit the displayed world-coordinate region without modifying the underlying
cut or its scalar values.

## Public API

```python
plot_2d_cut(
    cut,
    xrange=(-30.0, 20.0),
    yrange=(-40.0, 40.0),
)
```

Both parameters default to `None`, preserving the existing full-cut view.
Providing only one range uses the cut's complete bounds for the other axis.

## Semantics

The limits behave like Matplotlib axis limits:

- they alter the parallel-projection camera framing;
- they do not clip, extract, or copy the cut;
- they do not change pressure or color normalization;
- they use the cut's world `X` and `Y` coordinates; and
- they retain the cut's complete `Z` bounds.

After orienting the camera perpendicular to the cut, `plot_2d_cut()` calls
`Plotter.reset_camera()` with the requested `X/Y` limits and the cut's existing
`Z` bounds. This keeps the established arbitrary-plane camera behavior while
making the common `Z = 0` case analogous to `xlim` and `ylim`.

## Validation

Each supplied range must:

- contain exactly two numeric values;
- contain only finite values; and
- be strictly increasing.

Invalid ranges raise `DatasetError` and identify `xrange` or `yrange`.

## Testing

Recording-plotter tests verify full, partial, and omitted limits plus malformed,
nonfinite, equal, and reversed ranges. They also verify that the original cut is
still passed unchanged to `add_mesh`.

The real BATSRUS pressure cut is rendered once with restricted ranges to confirm
the resulting camera view visually.
