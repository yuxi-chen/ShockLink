# MMS–bow-shock connection design

## Goal

Given an extracted bow-shock surface, its outward normals, an interval-averaged
MMS position, and the interval-averaged magnetic field `Bavg`, determine where
the straight line through MMS in the `Bavg` direction intersects the extracted
shock. Plot the acute shock-normal angle over the full extracted surface in 2D,
mark the selected intersection, and provide a 3D view containing Earth, the
shock, MMS, the field line, and the intersection.

All coordinates use GSM and Earth radii. `Bavg` uses GSM components; its
magnitude does not affect the line or angle.

## Scientific conventions

The magnetic field line is the infinite straight line

```text
r(s) = r_MMS + s * Bavg_hat
```

where `Bavg_hat` is the normalized interval-averaged magnetic field. Both signs
of `s` are considered, so the intersection can lie along or opposite the
directed field vector. If the line crosses the extracted shock more than once,
the selected connection is the valid intersection with minimum `abs(s)`, which
is the point closest to MMS. All deduplicated crossings remain available for
diagnostics.

The plotted angle follows the acute shock convention

```text
theta_Bn = degrees(acos(abs(dot(Bavg_hat, normal_hat))))
```

and therefore lies in `[0, 90]` degrees. The absolute dot product makes parallel
and antiparallel fields equivalent. Existing callers of
`calc_bow_shock_normal_angle` retain the current directed `[0, 180]` result;
the function gains an explicit `acute=True` option for this workflow.

## Approach

Triangulate the extracted `surface_x(y, z)` height map and use exact
line–triangle intersections. Each Y–Z quad whose four X samples are finite is
split into two consistently wound triangles with outward `+X` orientation.
Quads touching a missing sample are omitted, so neither intersection analysis
nor visualization silently fills unsupported shock coverage.

This approach is preferred to solving a sampled scalar root against an
interpolated height map because it finds every ordinary crossing, including
crossings on both sides of MMS, without a step-size-dependent search. It is
preferred to an analytic paraboloid intersection because it uses the extracted
shock displayed in the figures rather than the preliminary fitted surface.

The intersection calculation uses a scale-normalized Möller–Trumbore test.
Hits on triangle edges or vertices can be reported by neighboring faces, so
coincident points are merged within a relative geometry tolerance. The signed
line parameter is retained. The local shock normal is barycentrically
interpolated from the triangle's vertex normals and renormalized before
calculating the local acute angle.

## Public API and result model

Add a flat `shocklink.connectivity` module. It owns the MMS-to-shock integration
without moving generic Tecplot loading, MMS downloading, or bow-shock
extraction out of their existing modules.

The primary numerical entry point is:

```python
connection = analyze_shock_connection(
    surface_x,
    normals,
    y=y,
    z=z,
    mms_position=mms_position,
    bavg=bavg,
)
```

It returns a `ShockConnection` containing:

- the validated MMS position and original `Bavg`;
- the normalized field-line direction;
- the Y and Z axes;
- an acute angle grid with `NaN` wherever `surface_x` was unavailable;
- a triangulated PyVista surface carrying vertex normals and angle scalars;
- every deduplicated `ShockIntersection`; and
- the index/property for the closest selected intersection.

Each `ShockIntersection` records its 3D point, signed line parameter, distance
from MMS, source face, barycentric weights, interpolated shock normal, and local
acute angle. Array data stored by the result records is copied so caller input
mutation cannot change reported coordinates or vectors.

The API consumes the existing outputs directly. A caller gets `surface_x` and
`normals` from `shocklink.bowshock`, while the MMS workflow supplies the three
`satellite_location_*` and `magnetic_field_*` averages. Core geometry never
downloads MMS data or assumes a time window.

## Two-dimensional visualization

`plot_shock_angle_contour(connection, ax=None, ...)` uses Matplotlib and returns
the figure and axes. It displays `theta_Bn` on the Y–Z plane with fixed
`0`–`90` degree contour levels and a degree-labelled color bar. Missing shock
coverage stays masked. The selected intersection appears at `(Y, Z)` with a
contrasting marker and an annotation containing its GSM `(X, Y, Z)` coordinates
and local angle. Axes use `Y_GSM [R_E]`, `Z_GSM [R_E]`, and equal spatial aspect.

Matplotlib remains lazily imported because it is provided by the existing MMS
optional dependency set. Supplying an axes object allows composition with
larger figures and headless unit tests.

## Three-dimensional visualization

`plot_shock_connection_3d(connection, plotter=None, show=True, ...)` uses
PyVista and returns the active plotter. It adds:

- a unit-radius Earth sphere at the GSM origin;
- the triangulated extracted shock colored by `theta_Bn` on `[0, 90]`;
- MMS as a labelled point;
- the selected intersection as a contrasting labelled point;
- a line from MMS through the selected intersection, continued a short distance
  beyond the surface so the crossing is visible; and
- a `Bavg` direction arrow rooted at MMS.

The view includes GSM axes and an angle color bar. `plotter` and `show` options
support notebook composition and off-screen testing.

## Error handling

Raise `DatasetError` for malformed numeric inputs: incompatible shapes,
nonfinite coordinates or normals, a zero/nonfinite `Bavg`, invalid axes, or a
surface/normal shape mismatch. Raise `GeometryError` when the validated shock
has no complete triangular cells, the infinite line does not cross the
observed shock coverage, or an overlapping coplanar line makes the intersection
non-unique.

Ordinary multiple intersections are not errors. They are deduplicated and
sorted by distance from MMS. A missing intersection is reported explicitly
rather than replaced with the closest surface point.

No coordinate transform is attempted. Documentation and docstrings require MMS
and simulation inputs to share GSM coordinates and Earth-radius distance units.

## Example workflow

Add a runnable example that combines the existing APIs:

1. Read one Tecplot `.dat` file and extract/smooth the bow shock.
2. Load a user-selected MMS interval in GSM.
3. Calculate the plotted MMS averages.
4. Assemble `mms_position` and `bavg` from the average component keys.
5. Analyze the straight-line connection.
6. Print the selected intersection and local angle.
7. Display the 2D contour and 3D scene.

The MMS interval remains explicit. The example reports the Tecplot event time
so the user can verify temporal alignment, but it does not silently choose or
alter an averaging window.

## Testing

Synthetic tests cover:

- known line–plane intersections;
- two crossings of a curved height map with selection of the closest;
- selected intersections for positive and negative signed line parameters;
- parallel, antiparallel, perpendicular, and oblique acute angles;
- preservation of the existing directed angle default;
- omission of quads around `NaN` surface samples;
- shared-edge hit deduplication;
- barycentric normal interpolation and local angle calculation;
- all input validation and no-intersection errors;
- 2D contour range, missing-data mask, labels, and marker coordinates; and
- off-screen 3D actors for Earth, shock, MMS, the field line, arrow, and
  intersection.

An opt-in large-data smoke test reuses the local Tecplot sample and supplied
synthetic MMS position/`Bavg`. It verifies a finite connection and plot-ready
result without performing a network download. The complete ordinary test suite,
Ruff checks, and `git diff --check` run before the feature branch is merged into
`main`.
