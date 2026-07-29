# PyVista Tecplot Reader Design

## Goal

ShockLink will read BATSRUS three-dimensional Tecplot ASCII (`*.dat`) output
with PyVista and return a geometry-ready `pyvista.UnstructuredGrid` for magnetic
field-line analysis.

The implementation remains flat:

```text
src/shocklink/tecplot.py
```

## Observed Sample

The local sample `data/3d.dat` is a 1.3 GB BATSRUS FEPOINT Tecplot file. With
PyVista 0.48.4 and VTK 9.6.2, the native reader loads it in about 5.25 seconds as
a one-block `pyvista.MultiBlock` containing:

- 5,695,488 points;
- 5,809,895 hexahedral cells;
- approximately 886 MiB of VTK data; and
- scalar point arrays for coordinates, plasma quantities, magnetic-field
  components, and velocity components.

VTK leaves `grid.points` at `(0, 0, 0)` and exposes the physical coordinates as
`X [R]`, `Y [R]`, and `Z [R]`. ShockLink must repair the geometry before any
spatial operation.

## Public API

```python
from shocklink.tecplot import read_tecplot

grid = read_tecplot("data/3d.dat")
```

`read_tecplot` returns a `pyvista.UnstructuredGrid`. It accepts optional
coordinate, magnetic-field, and velocity component names for compatible
BATSRUS exports that use different labels.

## Normalization

The reader will:

1. validate that the input exists and has a `.dat` suffix;
2. read the file through PyVista's native `TecplotReader`;
3. require exactly one nonempty zone for the initial API;
4. assign `X [R]`, `Y [R]`, and `Z [R]` to `grid.points`;
5. combine `B_x [nT]`, `B_y [nT]`, and `B_z [nT]` into the `N x 3` point array
   `B [nT]`;
6. combine PyVista's imported `U_x [km_s]`, `U_y [km_s]`, and `U_z [km_s]`
   components into the `N x 3` point array `U [km/s]`; and
7. retain all original component arrays.

The returned grid shares PyVista/VTK-managed data where practical. Creating the
coordinate and vector matrices necessarily adds temporary or persistent array
storage; the implementation avoids extra deep copies beyond those required by
PyVista.

## Errors

Expected failures map to `shocklink.exceptions.DatasetError` with messages that
name the file or missing array:

- missing or non-file path;
- unsupported extension;
- PyVista/VTK read failure;
- zero or multiple nonempty zones;
- non-`UnstructuredGrid` zone;
- missing component arrays;
- component arrays with inconsistent lengths; or
- nonfinite coordinate values.

## Dependency and Data Policy

PyVista replaces the planned ParaView integration and becomes a normal runtime
dependency because reading 3D simulation data is a core ShockLink capability.
The 1.3 GB sample remains local and untracked; `data/*.dat` will be ignored.

## Testing

Fast unit tests use small synthetic PyVista grids and a stubbed raw reader to
exercise extraction, normalization, validation, and errors.

An integration test is marked separately and skipped unless the local sample is
present and explicitly requested. It verifies the real sample's point and cell
counts, corrected bounds, vector shapes, component ordering, and finite
coordinates. The implementation will be demonstrated by running that
integration test during development.
