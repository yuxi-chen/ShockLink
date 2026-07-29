# Notebook `div(U)` Figure Design

## Goal

Keep the pressure visualization and add a separate `div(U)` visualization,
with the fitted bow-shock contour overlaid on both.

## Pressure Figure

The existing plot remains pressure-colored using `SCALARS = "p"`. Correct its
isolines to use `"P [nPa]"`:

```python
pressure_contours = cut.contour(
    isosurfaces=15,
    scalars="P [nPa]",
)
```

Overlay the thick white `shockfit = 0` contour and display the plot with its
pressure scalar bar.

## Divergence Figure

Use the notebook's existing empty final cell for a second independent plot:

```python
divu_plotter = plot_2d_cut(
    cut,
    scalars="div(U)",
    show=False,
    xrange=[-40, 20],
    yrange=[-20, 20],
)
```

Generate and add a thick white `shockfit = 0` contour, then display the plot
with its own `div(U)` scalar bar. The second figure does not add pressure
isolines, keeping the compression field visually readable.

## Testing

Notebook tests will distinguish `pressure_plotter` and `divu_plotter`, require
the correct scalar for each, verify pressure isolines use `"P [nPa]"`, require
both fitted-shock overlays, and require two static `show()` calls. All notebook
cells remain unexecuted and output-free.
