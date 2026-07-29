# Generic Dataset Operations Design

## Goal

Separate file-format I/O from operations on loaded PyVista datasets.
`shocklink.tecplot` will expose only the Tecplot reader, while planar slicing
and plotting will work through a format-independent module.

## Public API

Create the flat module `shocklink.dataset` with:

```python
from shocklink.dataset import get_2d_cut, plot_2d_cut
from shocklink.tecplot import read_tecplot
```

`shocklink.tecplot.__all__` will contain only `read_tecplot`. It may retain
private helpers and constants needed to validate and normalize Tecplot data,
but it will not re-export the generic functions. This is an intentional
import-path change that enforces the module boundary.

## Responsibilities

`shocklink.tecplot` owns:

- reading `.dat` files through PyVista;
- validating Tecplot zones and arrays;
- normalizing coordinates;
- creating magnetic-field and velocity vectors.

`shocklink.dataset` owns:

- validating plane normals and origins;
- creating planar cuts from any compatible PyVista dataset;
- storing and reading cut-plane metadata;
- selecting scalar arrays;
- validating optional display ranges;
- plotting cuts with PyVista.

No subdirectory will be added under `src/shocklink`.

## Behavior and Errors

The existing behavior remains unchanged. Cuts default to the equatorial plane,
plots default to pressure, and `xrange` and `yrange` control the camera view
without cropping the data. Existing `DatasetError` validation messages and
PyVista return types remain in place.

## Callers and Documentation

Tests, integration tests, command-line examples, and the notebook will import
cut and plot functions from `shocklink.dataset`. The notebook already has
uncommitted user changes, so only its relevant import statement will be
changed. Historical design and implementation plans will remain unchanged as
records of earlier decisions.

## Testing

Tests will first assert the new public module boundary and fail while the
functions remain in `shocklink.tecplot`. After the move, the focused cut and
plot tests, the complete unit suite, and the sample-data integration tests will
verify that behavior is preserved. A wheel build will confirm both modules are
packaged in the flat source layout.
