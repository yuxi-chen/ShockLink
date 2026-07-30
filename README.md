# ShockLink

ShockLink analyzes magnetic field-line connectivity to the bow shock in 3D MHD
magnetosphere simulations. Its current workflow reads BATSRUS Tecplot data with
PyVista, derives velocity compression, extracts a regular bow-shock surface,
and calculates outward unit normals.

## Installation

When a ShockLink release is published on PyPI, install it with:

```bash
pip install shocklink
```

For a development checkout:

```bash
pip install -e ".[dev,notebook]"
```

## Bow-shock workflow

The implemented analysis sequence is:

```text
Tecplot -> div(U) -> paraboloid fit -> near-shock region -> regular Y-Z surface -> outward unit normals
```

See the [bow-shock workflow guide](docs/bow-shock-workflow.md) for the
scientific conventions and a copy-paste Python example. The same pipeline is
available as [a runnable script](examples/bow_shock_workflow.py).

The final call:

```python
normals = calc_bow_shock_normals(surface_x, y=y, z=z)
```

returns outward unit-normal components `(nx, ny, nz)` with a strictly positive
X component.

## Examples

See [examples/README.md](examples/README.md) for the notebook and command-line
examples.

## Status

ShockLink is pre-alpha research software. Validate the detection and resolution
for each simulation before using results in scientific analysis.
