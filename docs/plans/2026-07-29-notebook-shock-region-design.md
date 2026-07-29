# Notebook Shock-Region Workflow Design

## Goal

Reduce the fitted 3D simulation dataset to a `shockfit` neighborhood before
creating the 2D cut, then use that extracted region for every downstream
notebook operation.

## Workflow

The notebook retains the complete grid through velocity-divergence calculation
and bow-shock fitting. These operations require the global X-axis and Y-line
profiles.

Add the configurable parameter:

```python
SHOCKFIT_RANGE = [-5.0, 5.0]
```

After `fit_bow_shock(grid)` has added `shockfit`, extract:

```python
shock_region = extract_shockfit_range(
    grid,
    lower=SHOCKFIT_RANGE[0],
    upper=SHOCKFIT_RANGE[1],
)
```

Then create:

```python
cut = get_2d_cut(
    shock_region,
    normal=NORMAL,
    origin=ORIGIN,
)
```

The cut validation, pressure background, pressure isolines, fitted-shock
contour, and plot all operate on this reduced region.

## Reporting

Print the extracted region's point and cell counts, bounds, point arrays, and
the presence of `vtkOriginalPointIds` and `vtkOriginalCellIds`. This makes the
topological expansion from adjacent-cell extraction visible to notebook users.

The full grid remains available in memory for exploration, but it is no longer
used by the cut or plotting cells.

## Testing

Notebook tests will require the extraction import, the exact
`SHOCKFIT_RANGE = [-5.0, 5.0]` parameter, construction of `shock_region`, and
`get_2d_cut(shock_region, ...)`. They will also verify extraction appears
before slicing in notebook source order and that all cells remain clean and
unexecuted.
