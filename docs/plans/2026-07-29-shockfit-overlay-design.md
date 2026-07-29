# Shock-Fit Residual and Notebook Overlay Design

## Goal

Store the fitted bow-shock paraboloid as a signed point-data residual and
visualize its zero contour over pressure in the Tecplot notebook.

## Dataset Variable

Extend `fit_bow_shock()` with:

```python
fit = fit_bow_shock(
    dataset,
    shockfit_name="shockfit",
)
```

After the three locations and coefficients are fitted, add this scalar to the
input dataset:

```text
shockfit = x - [x0 - a * (y**2 + z**2)]
```

The fitted bow-shock surface is exactly `shockfit = 0`. Negative and positive
values identify opposite sides of the fitted surface. The array is point data,
has one finite value per dataset point, and replaces an existing array with the
same name. An empty output name raises `DatasetError`.

Add `BowShockParaboloid.residual_at(x, y, z)` and use it to calculate the
dataset array, keeping one authoritative implementation of the equation.

## Notebook Workflow

The notebook will:

1. read the Tecplot grid;
2. calculate `div(U)`;
3. call `fit_bow_shock(grid)`;
4. print `loc0`, `loc1`, `loc2`, `x0`, and curvature `a`;
5. create the existing Z=0 cut and validate `shockfit`;
6. plot pressure as the colored background;
7. overlay pressure isolines;
8. overlay a thicker contrasting `shockfit = 0` contour.

The existing X/Y display ranges remain unchanged. Pressure returns as the
background scalar because it is the requested physical context; `div(U)`
remains available for detection and inspection.

## Plot Layers

Use `plot_2d_cut(cut, scalars="p", show=False, ...)` for the pressure color
map and scalar bar. Generate pressure isolines with:

```python
pressure_contours = cut.contour(
    isosurfaces=15,
    scalars="P [nPa]",
)
```

Add them as thin dark lines without a second scalar bar. Generate the fitted
shock with:

```python
shock_contour = cut.contour(
    isosurfaces=[0.0],
    scalars="shockfit",
)
```

Add it as a thick high-contrast line.

## Testing

Extend the analytic bow-shock test to verify the exact residual equation,
zero residual at all detected locations, custom naming, and replacement of an
existing array. Notebook structural tests will require the fit call, pressure
background, both contour calls, and both overlay layers while continuing to
enforce clean unexecuted cells.
