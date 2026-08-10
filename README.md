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

Source checkouts include
[docs/bow-shock-workflow.md](https://github.com/yuxi-chen/ShockLink/blob/main/docs/bow-shock-workflow.md),
which explains the scientific conventions and provides a copy-paste Python
example. They also include the same pipeline as the runnable script
[examples/bow_shock_workflow.py](https://github.com/yuxi-chen/ShockLink/blob/main/examples/bow_shock_workflow.py).

The final call:

```python
normals = calc_bow_shock_normals(surface_x, y=y, z=z)
```

returns outward unit-normal components `(nx, ny, nz)` with a strictly positive
X component.

## Examples

The [MMS–bow-shock connection guide](https://github.com/yuxi-chen/ShockLink/blob/main/docs/mms-bow-shock-connection.md)
and runnable [connection example](https://github.com/yuxi-chen/ShockLink/blob/main/examples/mms_bow_shock_connection.py)
show the acute 0–90° angle and closest straight-line intersection workflow.

In a source checkout,
[examples/README.md](https://github.com/yuxi-chen/ShockLink/blob/main/examples/README.md)
lists the notebook and command-line examples.

## Tecplot to VTK conversion

Convert every zone in an ASCII Tecplot `.dat` file to a VTK multiblock `.vtm`
file without normalizing or combining the zones:

```bash
python tools/convert_dat_to_vtm.py path/to/input.dat
```

The output defaults to `path/to/input.vtm`. Provide a second positional argument
to choose another output path:

```bash
python tools/convert_dat_to_vtm.py input.dat output.vtm
```

To remove the source file only after a successful conversion, add
`--delete-input`:

```bash
python tools/convert_dat_to_vtm.py input.dat --delete-input
```

The `.vtm` file may reference generated `.vts`, `.vti`, or `.vtu` sidecar files;
keep those files and directories together with the `.vtm` file when moving or
reopening the converted dataset.

## Status

ShockLink is pre-alpha research software. Validate the detection and resolution
for each simulation before using results in scientific analysis.
