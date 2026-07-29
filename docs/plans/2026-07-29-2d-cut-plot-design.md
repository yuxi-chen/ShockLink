# 2D Cut and Plot Design

## Goal

ShockLink will extract a planar two-dimensional cut from a normalized PyVista
simulation grid and plot that cut with pressure as the default color field.
Both functions live in the existing flat module:

```text
src/shocklink/tecplot.py
```

## Public API

```python
from shocklink.tecplot import get_2d_cut, plot_2d_cut

cut = get_2d_cut(
    grid,
    normal="z",
    origin=(0.0, 0.0, 0.0),
)

plotter = plot_2d_cut(
    cut,
    scalars="p",
    show=True,
)
```

The default plane is the GSM equatorial plane, `Z = 0`. Callers may provide an
arbitrary three-component normal and origin.

## Cut Behavior

`get_2d_cut()` delegates interpolation and cell intersection to PyVista's slice
filter and returns `pyvista.PolyData`. The cut retains interpolated point and
cell arrays, including pressure plus the normalized magnetic-field and velocity
vectors.

The function:

- accepts axis aliases `"x"`, `"y"`, and `"z"` or a numeric normal;
- validates that the normal is finite and nonzero;
- validates that the origin contains three finite coordinates;
- optionally asks PyVista to triangulate the cut;
- raises `DatasetError` when the plane is invalid or does not intersect the
  dataset; and
- records the normalized plane normal and origin in field data so plotting can
  recover the intended view.

## Plot Behavior

`plot_2d_cut()` accepts a cut produced by `get_2d_cut()`. Its default
`scalars="p"` resolves case-insensitively to the sample's actual pressure array,
`P [nPa]`. The aliases `"p"` and `"pressure"` prefer `P [nPa]`, then fall back
to exact or case-insensitive matches for compatible datasets.

The plotting function:

- creates a PyVista `Plotter` unless one is supplied;
- colors the cut by pressure using a configurable colormap;
- labels the scalar bar with the resolved array name;
- orients the camera along the stored cut normal;
- enables parallel projection for an undistorted planar view;
- adds axes;
- displays interactively by default;
- supports `show=False` for notebooks, customization, and tests; and
- returns the `Plotter`.

Missing scalar arrays or missing plane metadata raise `DatasetError` with an
actionable message. Additional PyVista mesh keyword arguments may be supplied
without turning ShockLink into a wrapper for every plotting option.

## Testing

Fast unit tests use a small `pyvista.ImageData` volume with pressure and vector
arrays. They verify default and arbitrary planes, metadata, interpolated arrays,
invalid inputs, pressure alias resolution, plotter reuse, camera orientation,
and `show` behavior without opening a window.

The opt-in real-data integration test creates a `Z = 0` cut from
`data/3d.dat`, checks that the cut is nonempty and planar, confirms that
`P [nPa]`, `B [nT]`, and `U [km/s]` survive interpolation, and constructs the
pressure plot off-screen.
