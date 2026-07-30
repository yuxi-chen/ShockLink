# Bow-Shock Workflow Documentation Design

## Goal

Document the complete ShockLink workflow for deriving an outward bow-shock
normal field from a BATSRUS Tecplot dataset:

```text
Tecplot data
  -> velocity divergence
  -> paraboloid fit
  -> near-shock region
  -> regular Y-Z surface array
  -> outward unit normals
```

The documentation must be useful both to a new package user and to a
maintainer reading the numerical implementation.

## Audience

The primary audience is a space-physics researcher using ShockLink from
Python or a notebook. Readers are expected to understand NumPy arrays and
basic MHD quantities, but they should not need to infer ShockLink's array
conventions, sign conventions, or interpolation choices from source code.

The secondary audience is a developer maintaining the PyVista and NumPy
implementation.

## Documentation Structure

Use a layered structure:

1. Add a root `README.md` with the project purpose, installation commands, a
   concise workflow overview, and links to detailed documentation and
   examples.
2. Configure `README.md` as the project README in `pyproject.toml`, so the
   same introduction is available on PyPI.
3. Add `docs/bow-shock-workflow.md` as the detailed scientific and API guide.
4. Add `examples/bow_shock_workflow.py` as a runnable command-line example
   using the same sequence documented in the guide.
5. Expand the public docstrings and add targeted implementation comments in
   the existing flat `src/shocklink/` modules.
6. Link the new workflow from `examples/README.md`.

Do not add a package subdirectory or move any existing public function.

## Workflow Guide

The detailed guide will present a copy-paste example equivalent to:

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
region = extract_shockfit_range(grid, lower=-5.0, upper=5.0)

y = np.linspace(-40.0, 40.0, 81)
z = np.linspace(-40.0, 40.0, 81)
surface_x = get_bow_shock_surface(region, y=y, z=z)
normals = calc_bow_shock_normals(surface_x, y=y, z=z)
```

The guide will explain each stage:

- `read_tecplot()` reads one Tecplot zone, assigns the coordinate arrays to
  PyVista geometry, and assembles magnetic and velocity vector arrays.
- `calc_velocity_divergence()` adds `div(U)` to the dataset in place.
- The most negative `div(U)` identifies the strongest local compression.
- `fit_bow_shock()` identifies the shock nose and two flank locations, fits
  `x = x0 - a(y**2 + z**2)`, and stores the signed `shockfit` residual.
- `extract_shockfit_range()` restricts expensive sampling to a band around
  the fitted paraboloid; the documented default example uses `[-5, 5]`.
- `get_bow_shock_surface()` samples each requested `(y, z)` column and stores
  the X location of the most negative sampled divergence:

  ```text
  surface_x[i, j] = x of the bow shock at (y[i], z[j])
  ```

- `calc_bow_shock_normals()` fills missing surface values, differentiates the
  height map with the actual Y and Z coordinates, and returns:

  ```text
  normals.shape == surface_x.shape + (3,)
  normals[i, j] = (nx, ny, nz)
  ```

## Normal Geometry

Parameterize the regular surface as:

```text
r(y, z) = (x_s(y, z), y, z)
```

The outward cross product of its coordinate tangents is:

```text
n_raw = (1, -dx_s/dy, -dx_s/dz)
```

Normalize this vector at each grid point. The convention `nx > 0` selects the
sunward/upstream direction and removes the two-sided normal ambiguity.

The guide will state that Y indexes array axis 0, Z indexes array axis 1, and
the final component axis stores X, Y, and Z vector components.

## Missing Values and Numerical Choices

Document the two-stage surface fill:

1. Linear `scipy.interpolate.griddata` interpolation fills gaps inside the
   convex hull of valid samples.
2. Nearest-neighbor interpolation fills unresolved edge and corner gaps.
3. Original finite surface samples are restored exactly before
   differentiation.

The guide will note that normals in nearest-extrapolated edge regions can be
less accurate than normals inside the measured footprint.

Document that `np.gradient` uses the supplied coordinate vectors and
second-order boundary differences. Explain that normalization is scaled
before calculating the vector magnitude so extremely steep but finite
surfaces do not overflow.

## Runnable Example

Add `examples/bow_shock_workflow.py`. It will:

- accept the Tecplot path as a positional argument;
- expose practical transverse-grid and X-sampling resolution options;
- execute the complete workflow without opening a graphical window;
- print the fitted nose position and curvature;
- print the surface and normal array shapes;
- print the number of finite surface values;
- print the minimum X-normal component;
- print the maximum unit-length error.

The example will use public ShockLink functions only. It will not duplicate
private interpolation or geometry logic.

## Public Docstrings and Source Comments

Expand the docstrings of these public functions:

- `shocklink.tecplot.read_tecplot`
- `shocklink.dataset.calc_velocity_divergence`
- `shocklink.bowshock.fit_bow_shock`
- `shocklink.bowshock.extract_shockfit_range`
- `shocklink.bowshock.get_bow_shock_surface`
- `shocklink.bowshock.calc_bow_shock_normals`

Use scientific Python sections for parameters, returns, raises, and important
notes. Include mutation behavior, expected array shapes, field-name defaults,
sign conventions, and units where known.

Add inline comments only where they explain a scientific or numerical
decision:

- selecting the most negative divergence;
- locating the nose and two flanks for the paraboloid fit;
- restoring measured samples after interpolation;
- constructing the positive-X normal;
- scaling before normalization.

Do not add comments that merely translate individual Python statements into
English.

## Errors and Input Requirements

The guide will summarize `DatasetError` cases relevant to the workflow:

- missing or malformed Tecplot component arrays;
- missing, nonnumeric, or nonfinite velocity/divergence arrays;
- invalid sampling axes or resolutions;
- insufficient or degenerate finite surface samples;
- malformed interpolation results;
- invalid or nonfinite normal output.

For normal calculation, explicitly document that:

- Y and Z must be real, finite, strictly increasing 1D arrays with at least
  three values;
- `surface_x` must have shape `(len(y), len(z))`;
- `NaN` represents a missing surface location and is filled;
- infinity, complex data, text, dates, and booleans are rejected;
- caller inputs are not modified.

## Verification

Add documentation-oriented tests that verify:

- the root README is configured in project metadata;
- the workflow guide and example reference all required public functions;
- the documented surface and normal shape conventions are present;
- the example script imports and compiles;
- the example has no private ShockLink imports.

Run:

- documentation-focused tests;
- Ruff lint and formatting checks;
- the complete default test suite;
- the example against `data/3d.dat`;
- a package build in a temporary output directory to verify README metadata.

## Non-Goals

- Do not change the numerical algorithms or public API behavior.
- Do not modify the clean notebook.
- Do not add a documentation framework such as Sphinx or MkDocs yet.
- Do not add plotting behavior to the workflow script.
- Do not document field-line tracing that has not yet been implemented.
