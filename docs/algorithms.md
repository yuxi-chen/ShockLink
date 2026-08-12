# ShockLink algorithms and data conventions

This guide describes the implemented ShockLink pipeline, including its data
contracts, numerical steps, failure modes, and scientific approximations. The
linked source modules remain the authority for defaults and validation.

## End-to-end data flow

The connection workflow is:

```text
BATSRUS DAT/VTM
  -> normalized geometry, B, U, and event time
  -> div(U)
  -> paraboloid landmark fit and shockfit residual
  -> near-fit cell extraction
  -> strongest-compression X(Y,Z) samples
  -> NaN-aware smoothing and outward normals
  -> acute theta_Bn map and observed-cell triangles
  -> straight MMS field-line intersections
  -> nearest intersection and 2D/3D outputs

MMS interval
  -> pySPEDAS products in GSM
  -> finite interval averages and interpolated spacecraft position
  -> SWMF #STARTTIME, #SOLARWIND, and MMS-location records
```

`build_mms_bow_shock_connection()` composes the simulation branch. The MMS
loader and SWMF generator compose the observation branch. Keeping these
operations separate makes the numerical core usable without invoking plotting
or command-line code.

## Coordinate and field conventions

ShockLink uses geocentric solar magnetospheric (GSM) coordinates. X is directed
along the Sun--Earth line; position is measured in Earth radii (`R_E`), magnetic
field in nT, and velocity in km/s. BATSRUS component arrays are combined into
point vectors named `B [nT]` and `U [km/s]`. A regular shock surface is indexed
as `surface_x[i, j] = X(Y[i], Z[j])`: Y is axis 0 and Z is axis 1.

## Input loading and normalization

`load_simulation()` accepts an ASCII Tecplot `.dat`, a VTK multiblock `.vtm`,
or a directory containing `.vtm` files. Directory input selects the
lexicographically first VTM filename. DAT event time comes from the header
`TITLE`; VTM event time comes from root `field_data["time_event"]`. Both are
normalized to ISO-8601 UTC.

The loader requires PyVista to return a `MultiBlock`, recursively visits
nonempty dataset leaves, preserves the original hierarchy, and normalizes each
leaf independently. Coordinate component arrays replace the PyVista geometry
when present. Magnetic and velocity components are combined without changing
their values. A one-zone multiblock returns its dataset directly; multiple
zones retain the multiblock container.

Implementation: [`io.py`](../src/shocklink/io.py).

## Velocity compression

For velocity field \(\mathbf U=(U_x,U_y,U_z)\), the compression diagnostic is

```text
div(U) = dUx/dx + dUy/dy + dUz/dz.
```

`calc_velocity_divergence()` delegates spatial differentiation to PyVista's
point-data derivative filter. It validates that the input is a finite
`(n_points, 3)` vector and that the result is a finite `(n_points,)` scalar
before copying it onto the original dataset. The strongest compression is the
minimum valid `div(U)`. Its physical units follow the input coordinate and
velocity units; ShockLink does not rescale them.

Implementation: [`dataset.py`](../src/shocklink/dataset.py).

## Paraboloid landmark selection

`fit_bow_shock()` first samples the X axis and selects the finite point with the
most negative divergence as the nose \(p_0\). It then samples a Y-directed line
at `p0.x - x_offset`, selecting the strongest compression independently on the
negative-Y and positive-Y sides as flank landmarks \(p_1\) and \(p_2\).

The axisymmetric model is

```text
x_fit(y,z) = x0 - a * (y^2 + z^2),  a > 0.
```

With \(r_i^2=y_i^2+z_i^2\) and \(d_i=x_0-x_i\), the two flank samples determine
the least-squares curvature

```text
a = sum(r_i^2 * d_i) / sum(r_i^4).
```

Degenerate landmarks or nonpositive curvature are rejected. Every simulation
point receives the signed residual

```text
shockfit = x - x_fit(y,z).
```

This fit limits the later search region; it is not the final shock surface.

Implementation: [`bowshock.py`](../src/shocklink/bowshock.py).

## Residual-region extraction

`extract_shockfit_range()` selects points whose finite residual is inside an
inclusive `[lower, upper]` interval and asks PyVista for their cells. Adjacent
cells are included by default so interpolation near the residual boundary
retains support. Nonfinite residuals never enter the mask.

## Regular Y--Z surface sampling

For every requested `(y,z)` column, `get_bow_shock_surface()` samples a regular
finite X interval and chooses

```text
x_shock(y,z) = x[argmin_x div(U)(x,y,z)].
```

VTK's valid-point mask and finite divergence jointly define valid samples.
Columns without a valid sample return `NaN`; a dataset without cells returns an
all-NaN surface. The algorithm intentionally imposes no negative-divergence
threshold and no continuity constraint between neighboring columns. Weak or
positive minima can therefore be selected and must be judged scientifically.

Sampling is processed in Y-Z column chunks. One reusable static cell locator
accelerates interpolation without copying unrelated point, cell, or field
arrays into the probe result.

## Minimum refinement

An optional local refinement estimates the vertex of the three-point parabola
around an interior discrete minimum. With uniform X spacing \(h\) and samples
\(f_{-1}, f_0, f_{+1}\), its offset from the center is

```text
delta = h * (f_-1 - f_+1) / (2 * (f_-1 - 2*f_0 + f_+1)).
```

The refined point is accepted only when both neighbors are valid and finite,
the center is a strict minimum, curvature is finite and positive, and
`abs(delta) <= h`. Otherwise ShockLink retains the discrete minimum.

Implementation for extraction, sampling, and refinement:
[`bowshock.py`](../src/shocklink/bowshock.py).

## Surface smoothing and missing values

The optional Gaussian smoother filters the finite values and their support
weights separately:

```text
smoothed = G(surface where finite, else 0) / G(finite_mask).
```

This normalized convolution prevents missing columns from behaving like
physical zeros. By default, the original NaN mask is restored after smoothing,
so unsupported columns remain visible.

## Gap filling, derivatives, and outward normals

Normals require derivatives on a complete regular grid. Missing surface values
are filled in two stages: linear interpolation within the finite samples'
convex support, then nearest-neighbor extrapolation at remaining edges and
corners. Original finite samples are restored exactly before differentiation.
At least three non-collinear finite samples are required.

For the graph surface

```text
r(y,z) = (x_s(y,z), y, z),
```

the positive-X cross product is

```text
n_raw = r_y cross r_z = (1, -dx_s/dy, -dx_s/dz).
```

NumPy gradients use the supplied Y and Z coordinates, including nonuniform
spacing. Components are scaled before norm evaluation to avoid overflow, then
normalized. Returned normals are finite unit vectors with strictly positive X
components. The original surface mask should still be used when interpreting
normals near unsupported regions.

Implementation: [`bowshock.py`](../src/shocklink/bowshock.py).

## Shock angle

The directed angle between a normal and magnetic field spans 0--180 degrees.
The connection workflow uses the polarity-independent acute convention

```text
theta_Bn = degrees(acos(clip(abs(dot(n_hat, B_hat)), 0, 1))),
```

which spans 0--90 degrees. Inputs are normalized with scale-safe arithmetic,
and clipping protects `acos` from roundoff outside its mathematical domain.

## Surface triangulation

Only observed surface values participate in connectivity. A regular Y-Z quad
is accepted when all four corner X values are finite, then split into two
triangles with consistent vertex order. Interpolated gap-fill values used for
normal derivatives never create triangles across missing observations. Normal
and angle arrays are attached to the compact PyVista mesh as point data.

## Straight field-line intersection

The MMS field line is modeled as infinite and straight:

```text
p(s) = p_MMS + s * B_hat,  -infinity < s < infinity.
```

Triangles are translated by `p_MMS` and divided by a characteristic distance
before a vectorized Möller--Trumbore intersection test. This scaling makes the
relative tolerance less sensitive to the absolute coordinate magnitude.
Accepted barycentric coordinates interpolate the triangle's vertex normals;
the normal is renormalized before computing the local acute angle.

Parallel triangles are checked separately. A line lying in a triangle plane
and overlapping its interior or edges has infinitely many intersections and is
reported as ambiguous. Hits are sorted by `abs(s)`, and coincident hits from a
shared triangle edge are deduplicated within the scaled tolerance. The first
remaining hit is the intersection nearest MMS.

Implementation: [`connectivity.py`](../src/shocklink/connectivity.py).

## MMS loading, averaging, and coordinates

MMS loading uses pySPEDAS FGM, FPI, and MEC products. Automatic cadence tries
burst data first, then fast data. Magnetic field and plasma velocities are
converted from GSE to GSM when requested; spacecraft position is loaded from
MEC in GSM. Series are clipped to the requested inclusive interval.

Statistics and SWMF inputs use finite samples only. Vector components are
averaged independently. Magnetic magnitude is averaged from each sample's
three-component norm, rather than taking the norm of the mean vector. Total
species temperature is

```text
T = (T_parallel + 2*T_perpendicular) / 3
```

on timestamps shared by both products. The spacecraft location used by the
connection workflow is linearly interpolated at the effective UTC time after
invalid samples are removed, times are stably sorted, and duplicate timestamps
are collapsed. Kilometres are converted to Earth radii only at the final step.

Implementation: [`mms/loading.py`](../src/shocklink/mms/loading.py),
[`mms/data.py`](../src/shocklink/mms/data.py), and
[`mms/analysis.py`](../src/shocklink/mms/analysis.py).

## SWMF PARAM generation

`create_swmf_input()` uses the requested interval midpoint as the effective
start time unless explicitly overridden. It writes that time to `#STARTTIME`,
maps finite ion density, velocity, and magnetic averages to `#SOLARWIND`, and
stores the interpolated GSM MMS location in a nearby annotated block. Ion and
electron temperatures are added and converted from eV to K for the template.
The original template structure, comments, whitespace, and newline style are
otherwise retained.

If a later connection run finds the MMS-location block, it uses that stored
position. Older PARAM files without the block trigger an MMS download over a
five-minute window centered on the PARAM time and interpolate the position.

Implementation: [`mms_swmf.py`](../src/shocklink/mms_swmf.py),
[`swmf.py`](../src/shocklink/swmf.py), and
[`mms_connection.py`](../src/shocklink/mms_connection.py).

## Plot and file outputs

The 2D plot masks unsupported cells, shows the acute angle on Y-Z, marks the
nearest intersection, and optionally draws 45° and 50° reference contours. The
3D plot shows the observed triangulated shock, Earth, MMS, the field line, and
the selected hit. CLI output defaults to
`<input>_shock_connection_2d.png` and `<input>_shock_connection_3d.png`; the 3D
scene can also be exported as HTML. MMS-to-SWMF generation can save a separate
multi-panel quick-look plot for the requested interval.

## Computational cost

Let `Ny * Nz` be the number of surface columns, `Nx` the X resolution, `C` the
column chunk size, and `T` the number of observed surface triangles.

- Surface interpolation performs `Ny * Nz * Nx` probe evaluations. Temporary
  probe storage is `O(C * Nx)` rather than `O(Ny * Nz * Nx)`.
- Smoothing, gap filling, gradients, and angle calculation operate on the
  `Ny * Nz` surface grid. SciPy interpolation may dominate gap filling for
  sparse, irregular support.
- Field-line intersection is vectorized over `T` triangles and uses `O(T)`
  temporary arrays.

Increasing X resolution improves discrete localization; increasing Y-Z
resolution improves surface and normal resolution. Both require convergence
checks because they can change the selected intersection.

## Failure modes and validation

ShockLink rejects missing or incorrectly shaped vectors, nonnumeric or
nonfinite required data, unordered axes and ranges, empty simulation zones,
degenerate paraboloid landmarks, insufficient surface support, invalid normal
fields, coplanar line/surface overlap, and field lines with no intersection in
observed coverage. These are represented by `DatasetError` or `GeometryError`
in the numerical pipeline and by `ValueError` for malformed MMS/SWMF inputs.

Successful execution does not prove that a selected compression minimum is a
physical bow shock. The paraboloid search region, finite-column minimum,
Gaussian smoothing, interpolated normal field, and straight field line are
deliberate approximations. Inspect coverage, vary residual and grid settings,
and establish convergence before scientific interpretation.
