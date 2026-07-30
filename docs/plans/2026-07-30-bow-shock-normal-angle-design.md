# Bow-shock normal-angle design

## Goal

Calculate the angle, in degrees, between each outward bow-shock normal and one
user-supplied reference vector. Add the calculation and a Y-Z visualization to
the Tecplot workflow notebook.

## API

Add `calc_bow_shock_normal_angle(normals, vector)` to `shocklink.bowshock`.

- `normals` is an array whose final axis has length three, typically the
  `(len(y), len(z), 3)` output of `calc_bow_shock_normals`.
- `vector` is one finite, nonzero three-component reference vector.
- The return value has shape `normals.shape[:-1]`, is expressed in degrees,
  and lies in the closed interval `[0, 180]`.
- `0` degrees denotes alignment with the outward normal; `180` degrees denotes
  the opposite direction.

The calculation normalizes both operands, clips the dot product to `[-1, 1]`
to control floating-point roundoff, and applies `arccos` followed by degrees
conversion. It raises `DatasetError` for malformed, nonnumeric, nonfinite, or
zero-length inputs.

## Notebook

The Tecplot notebook will define a configurable `REFERENCE_VECTOR`, calculate
angles from its existing `normals` array, and display the angle as a Y-Z
heatmap with a degree-labelled color bar. The default vector is `[-1, 0, 0]`.

## Testing

Unit tests will cover aligned, opposite, perpendicular, and general normal
arrays; normalization of an unnormalized reference vector; shape preservation;
and invalid vectors. Notebook tests will assert the new calculation and degree
plot are present, while notebook execution remains skipped for the large local
sample.
