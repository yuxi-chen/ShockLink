# Bow-shock surface and normal workflow

This workflow reduces one BATSRUS Tecplot zone to a regular bow-shock surface
and a unit normal at every requested Y-Z coordinate. The paraboloid fit is a
search aid; the final surface is selected from the simulated velocity
compression.

## Scientific conventions

ShockLink uses the simulation's X direction as the bow-shock axis. The Tecplot
reader assigns the `X [R]`, `Y [R]`, and `Z [R]` component arrays to the
PyVista coordinate geometry. It also combines the magnetic components into
`B [nT]` and the velocity components into `U [km/s]`.

Compression is identified by the most negative value of `div(U)`, not by the
largest absolute value. The numerical units of `div(U)` follow from the
velocity and coordinate arrays supplied to PyVista; the workflow does not
assign it a separate fixed physical unit.

For each requested Y-Z column, the implementation selects the minimum finite
sampled `div(U)`. It applies no negativity test, magnitude threshold, or
continuity threshold. A column containing only positive divergence still
returns its minimum, and a selected point can represent weak compression,
expansion, or an unrelated structure. Treat the result as a candidate surface:
inspect the sampled divergence strength and surface continuity before using
it scientifically.

The initial axisymmetric fit is

```text
x = x0 - a(y**2 + z**2)
```

with positive curvature `a`. At every dataset point, `shockfit` is the signed
X residual

```text
shockfit = x - (x0 - a(y**2 + z**2))
```

so its sign distinguishes the two X sides of the fitted paraboloid. The fit
only restricts the region searched during the next sampling stage. It is not
the final shock surface.

The regular surface uses Y as array axis 0 and Z as array axis 1:
`surface_x[i, j]` is the detected X coordinate at `(y[i], z[j])`. For the
surface parameterization `r(y,z)=(x_s(y,z),y,z)`, the raw outward normal is
exactly `(1, -dx_s/dy, -dx_s/dz)`. The returned components are normalized and
ordered `(nx, ny, nz)`. The enforced orientation `nx > 0` points
sunward/upstream.

## Complete Python example

Run this example from the repository root after making `data/3d.dat`
available:

```python
import numpy as np

from shocklink.bowshock import (
    calc_bow_shock_normals,
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
from shocklink.dataset import calc_velocity_divergence
from shocklink.tecplot import read_tecplot

grid = read_tecplot("data/3d.dat")
calc_velocity_divergence(grid)
fit = fit_bow_shock(grid)
shock_region = extract_shockfit_range(
    grid,
    lower=-5.0,
    upper=5.0,
)

y = np.linspace(-40.0, 40.0, 81)
z = np.linspace(-40.0, 40.0, 81)
surface_x = get_bow_shock_surface(
    shock_region,
    y=y,
    z=z,
)
coverage_mask = np.isfinite(surface_x)
normals = calc_bow_shock_normals(
    surface_x,
    y=y,
    z=z,
)

assert surface_x.shape == (81, 81)
assert normals.shape == surface_x.shape + (3,)
```

`fit` contains the detected nose, two flank locations, and fitted curvature.
It is retained here so those diagnostics can be inspected even though the
subsequent calls use the `shockfit` array stored on `grid`.

## Step 1: Read and normalize Tecplot data

`read_tecplot("data/3d.dat")` reads exactly one nonempty Tecplot zone as a
PyVista `UnstructuredGrid`. It assigns the coordinate component arrays to the
grid geometry and builds the vector point arrays `B [nT]` and `U [km/s]`.
The returned grid therefore has physical point coordinates rather than
reader-generated point positions.

The default reader expects a `.dat` file and the component names exported by
BATSRUS. Custom component and output names can be passed when a file uses a
different convention.

## Step 2: Calculate velocity divergence

`calc_velocity_divergence(grid)` differentiates the point vector `U [km/s]`
on the dataset geometry and stores the point scalar `div(U)`. It mutates
`grid` in place and also returns that same grid. The downstream fit and
surface extraction interpret the lowest, most negative divergence as the
strongest compression.

## Step 3: Fit a paraboloid

`fit_bow_shock(grid)` first selects the strongest compression on the X axis.
It then samples a Y-directed line behind that nose and selects one compression
location on each side of Y=0. Those three locations determine
`x = x0 - a(y**2 + z**2)`.

The call adds the signed `shockfit` residual to `grid` in place and returns a
`BowShockParaboloid`. This smooth fit is deliberately approximate: it locates
a manageable neighborhood of the shock but does not replace the
divergence-based surface detection.

## Step 4: Extract the near-shock region

`extract_shockfit_range(grid, lower=-5.0, upper=5.0)` selects the inclusive
residual band `-5.0 <= shockfit <= 5.0` and returns an
`UnstructuredGrid`. With the default `adjacent_cells=True`, cells adjacent to
selected points are retained so the later interpolation has nearby cell
geometry. Those retained cells can include points whose `shockfit` values are
outside the exact residual limits.

Because `shockfit` is an X residual, `[-5.0, 5.0]` has the same coordinate
units as X and `shockfit`. This band is a dataset-specific search heuristic,
not a universal shock criterion. A band that is too wide includes unrelated
compression structures; a band that is too narrow can remove valid shock
cells. In either case the paraboloid is still only the region selector.

## Step 5: Extract the regular surface array

`get_bow_shock_surface(shock_region, y=y, z=z)` samples X-directed columns at
every pair in the requested regular Y-Z grid. In each column it selects the X
coordinate with the minimum finite sampled `div(U)`. There is no sign,
magnitude, or cross-column continuity requirement. A column with only positive
divergence still produces its minimum, so the selected location may be weak
compression, expansion, or unrelated structure.

The result has shape `(len(y), len(z))`. Y is axis 0 and Z is axis 1, so
`surface_x[i, j]` maps to `(y[i], z[j])`. The function does not modify
`shock_region`. A `NaN` means that the column had no valid sampled point in the
search region and X range; it is not proof that no physical shock exists.
Inspect divergence strength and surface continuity rather than treating every
finite value as an automatically validated shock detection.

## Step 6: Calculate outward normals

`calc_bow_shock_normals(surface_x, y=y, z=z)` fills any supported missing
surface values, differentiates X with respect to the supplied coordinates,
constructs `(1, -dx_s/dy, -dx_s/dz)`, and normalizes the result. Its shape is
`surface_x.shape + (3,)`, with the final axis ordered `(nx, ny, nz)`.

The derivatives use the actual Y and Z coordinate arrays, including
nonuniform spacing, rather than assuming unit index spacing. NumPy's
second-order boundary treatment is used. Every output vector has unit length
and strictly positive X component, so `nx > 0`.

## Missing surface values

`get_bow_shock_surface` leaves an unsampled column as `NaN`.
`calc_bow_shock_normals` accepts those gaps and uses two interpolation stages:

1. `linear` interpolation fills interior NaNs inside the finite samples'
   two-dimensional support.
2. `nearest` interpolation fills unresolved edge and corner values outside
   that support.

Linear interpolation fills any interior NaN pattern inside the valid samples'
convex hull, including a large hole. It does not impose a maximum gap size or
verify that the missing region follows the shock.

After filling gaps, the original measured finite values are restored exactly
before gradients are calculated. Nearest-neighbor edge extrapolation supplies
a complete field, but normals near extrapolated edges and corners are less
accurate than normals surrounded by measured surface values.

The returned normals do not encode which surface values were measured and
which were interpolated. Preserve `coverage_mask = np.isfinite(surface_x)`
before calling `calc_bow_shock_normals`, as shown in the complete example.
Exclude heavily filled regions from analysis or sensitivity-test results
against alternate coverage and resolution choices. A complete, finite normal
field can still be scientifically unsupported where surface coverage is poor.

Interpolation needs at least three finite samples spanning a nondegenerate
two-dimensional geometry. Too few samples, collinear samples, or another
degenerate interpolation layout raises an error instead of silently producing
normals.

## Resolution and memory

The sample `data/3d.dat` is about 1.3 GB. Reading it, assigning geometry, and
building vector fields require substantial memory beyond the file itself.
Sampling also allocates temporary PyVista points and arrays.

The main resolution tradeoffs are:

- `axis_resolution` and `cross_resolution` in `fit_bow_shock` control the
  number of samples used to locate the nose and flanks.
- The lengths of `y` and `z` set the number of X-directed columns. Doubling
  both creates four times as many columns and four times as many surface
  values and normals.
- `x_resolution` in `get_bow_shock_surface` controls samples per column.
  Increasing it reduces nominal X sample spacing, but does not guarantee
  improved localization or scientific accuracy.
- `chunk_size` controls how many columns are sampled together. A smaller
  chunk lowers peak temporary memory but requires more sampling calls; it
  does not change the requested grid.

For fixed bounds, total sampling work scales approximately with the number of
columns times `x_resolution`, while each chunk's temporary point allocation
scales approximately with its column count times `x_resolution`. These are
not strict linear relationships because PyVista/VTK lookup, interpolation,
allocation, and per-chunk overhead also contribute.

Choose resolutions by checking convergence of the detected surface and
normals. Finer arrays cannot recover structure absent from the simulation
mesh, and they carry real runtime and memory costs.

## Errors and validation

The public functions raise `DatasetError` for invalid input data or sampling
failures. A degenerate fitted paraboloid can also raise `GeometryError`.
Important rules for this workflow are:

- Y and Z coordinates must be real numeric, finite, nonempty 1D arrays in
  strictly increasing order. Normal calculation requires at least three
  values on each axis for second-order boundary derivatives.
- `surface_x` must be a real numeric array with shape
  `(len(y), len(z))`. `NaN` marks an interpolatable gap, but positive or
  negative infinity is rejected. Complex, boolean, string, date-like, and
  other non-real or nonnumeric categories are rejected rather than coerced.
- Missing-surface interpolation fails when the finite samples are too few or
  geometrically degenerate, or when interpolation returns a malformed or
  nonfinite result.
- Surface extraction requires a finite scalar divergence point array, finite
  increasing X bounds, an integer `x_resolution` of at least two, and a
  positive integer `chunk_size`.
- `calc_velocity_divergence` intentionally modifies `grid`, and
  `fit_bow_shock` intentionally adds `shockfit` to it. In contrast,
  `get_bow_shock_surface` does not modify its dataset, and
  `calc_bow_shock_normals` works on private copies without modifying
  `surface_x`, `y`, or `z`.

Treat a raised validation error or an unexpectedly large NaN region as a
signal to inspect the input fields, residual band, coordinate coverage, and
sampling resolution before using the geometry scientifically.
