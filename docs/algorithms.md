# ShockLink algorithms and data conventions

This guide records the scientific assumptions and numerical algorithms used by
the public ShockLink workflow. It is intentionally implementation-oriented:
the linked modules are the source of truth for defaults and validation.

## Coordinate and field conventions

ShockLink uses GSM coordinates with X along the Sun--Earth line and distances
in Earth radii (`R_E`). BATSRUS component arrays (`X [R]`, `Y [R]`, `Z [R]`)
are assigned to the PyVista geometry. Magnetic components are combined into
`B [nT]`; velocity components are combined into `U [km/s]`.

The loader accepts Tecplot DAT and VTK/VTM inputs, preserves multiple zones as
a `MultiBlock`, and walks the leaf datasets when a calculation needs a point
array. This keeps file-format handling separate from the numerical routines.
See [`io.py`](../src/shocklink/io.py) and [`dataset.py`](../src/shocklink/dataset.py).

## Velocity compression

`calc_velocity_divergence` differentiates the point vector `U [km/s]` on the
dataset geometry with PyVista's derivative filter and stores `div(U)` in the
point data. The most negative finite value is treated as the strongest local
compression. No fixed physical unit is assigned to the divergence; its units
follow the input velocity and coordinate units.

See [`dataset.py`](../src/shocklink/dataset.py).

## Bow-shock fit and candidate surface

The fit is an axisymmetric paraboloid,

```text
x_fit = x0 - a * (y**2 + z**2),  a > 0
```

The nose and two Y-flank locations are selected from compression samples; the
three points determine `x0` and `a`. Every point receives the signed residual

```text
shockfit = x - x_fit
```

The residual only narrows the cells searched later. The final regular surface
is found from the simulated compression rather than from the fitted curve.
`fit_bow_shock` computes the fit and writes the residual; then
`extract_shockfit_range` keeps cells around an inclusive residual interval and
can retain neighboring cells for interpolation.

See [`bowshock.py`](../src/shocklink/bowshock.py), including
`calc_bow_shock_normals` for the final normal field.

## Regular Y--Z surface sampling

`get_bow_shock_surface` probes a finite X interval for every requested
`(y, z)` column
and chooses the X coordinate with the minimum finite `div(U)`. It deliberately
does not require negative divergence, a magnitude threshold, or continuity
with adjacent columns: positive or weak minima can therefore be candidates.
Columns with no valid samples are returned as `NaN`.

Sampling is chunked to bound temporary VTK point allocations. A local
parabolic refinement can improve the X estimate around a discrete minimum;
the refinement is accepted only when its neighborhood is finite and
well-conditioned. The returned array uses Y as axis 0 and Z as axis 1:
`surface_x[i, j]` corresponds to `(y[i], z[j])`.

See [`bowshock.py`](../src/shocklink/bowshock.py).

## Surface smoothing and missing values

The optional Gaussian smoother is NaN-aware. It convolves both the data with
NaNs replaced by zero and a finite-value coverage mask, then divides the two
convolutions. This prevents missing columns from biasing neighboring values.
The original mask is retained so unsupported regions remain visibly masked.

See [`bowshock.py`](../src/shocklink/bowshock.py).

## Outward normals

For the graph surface `r(y,z) = (x_s(y,z), y, z)`, the unnormalized outward
normal is

```text
n = (1, -∂x_s/∂y, -∂x_s/∂z).
```

Gradients use the supplied Y and Z coordinates, including nonuniform spacing.
Missing surface values are filled in two stages: linear interpolation inside
the finite samples' support, followed by nearest-neighbor extrapolation at
edges and corners. Measured finite values are restored exactly before taking
gradients. Normals are normalized and oriented so `nx > 0`; retain the
original finite mask when interpreting edge normals.

See [`bowshock.py`](../src/shocklink/bowshock.py).

## Shock angle and magnetic connectivity

The acute shock angle is computed from the unit magnetic-field direction and
unit shock normal:

```text
theta_Bn = acos(abs(dot(B_hat, n_hat)))
```

The absolute value reports the 0--90 degree acute angle independent of field
polarity. The sampled surface is triangulated from complete observed Y--Z
quads only. A straight field line through the interval-averaged MMS position
is intersected with those triangles using a scaled Möller--Trumbore test.
Parallel/coplanar cases are treated as ambiguous, duplicate hits are removed,
and the hit nearest to MMS is selected by default.

See [`connectivity.py`](../src/shocklink/connectivity.py) and
[`mms_connection.py`](../src/shocklink/mms_connection.py).

## MMS and SWMF preprocessing

MMS products are loaded for an explicit interval or a symmetric interval
derived from the simulation event. Vector products are transformed to GSM when
requested; finite samples are averaged, and the averaged position is converted
to `R_E`. Missing burst products can fall back to fast survey products in
`auto` mode.

SWMF input generation maps the interval averages into the template's
`#STARTTIME` and `#SOLARWIND` records. Temperature products are converted from
eV to K only when writing the template's temperature fields; magnetic fields,
density, velocity, and position retain their documented units.
The optional `plot=True` API argument and CLI `--plot` flag save the multi-panel
MMS quick-look figure generated from the same loaded interval. The filename is
`mms_YYYYMMDD_HHMMSS_YYYYMMDD_HHMMSS.png`, based on the requested interval,
and is placed beside the generated SWMF input.

See [`mms.py`](../src/shocklink/mms.py) and
[`mms_swmf.py`](../src/shocklink/mms_swmf.py).

## Plot outputs and scientific limits

The 2D plot shows the Y--Z angle map with unsupported cells masked. The 3D
plot shows the triangulated shock, Earth, MMS, the straight field line,
magnetic-field arrow, and the selected intersection. The CLI writes
`xxx_shock_connection_2d.png` and `xxx_shock_connection_3d.png` by default for
an input named `xxx.dat`; 3D output can additionally be HTML.

The paraboloid, straight field line, finite-column minimum, and interpolated
normal field are practical approximations. Resolution and residual limits can
change the selected surface and intersection, so convergence and coverage
checks are required before scientific interpretation.
