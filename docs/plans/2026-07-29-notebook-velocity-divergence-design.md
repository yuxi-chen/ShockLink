# Notebook Velocity Divergence Design

## Goal

Replace the pressure visualization in the Tecplot 2D-cut notebook with the
divergence of the velocity vector.

## Data Flow

After loading the Tecplot volume, the notebook will call
`calc_velocity_divergence(grid)`. The calculation writes `div(U)` into the
original grid's point data. The existing planar slice then interpolates that
derived field onto the cut, and the existing PyVista plot cell displays it.

This preserves the correct order of operations: velocity divergence is a
three-dimensional spatial derivative and must be computed before slicing.

## Notebook Changes

- Import `calc_velocity_divergence` with the other generic dataset functions.
- Describe the notebook as plotting velocity divergence rather than pressure.
- Set `SCALARS = "div(U)"`.
- Calculate divergence immediately after `read_tecplot()` and report the new
  point array.
- Require `div(U)` in cut validation and retain magnetic-field and velocity
  checks.
- Keep the user's existing X/Y plot limits and all notebook-cleanliness rules.

## Testing

The notebook structural test will require the generic calculation import, the
calculation call, and the `div(U)` scalar selection. The notebook remains
unexecuted and contains no saved outputs.
