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

## SWMF input generation

Install ShockLink with the optional MMS dependencies from a development
checkout:

```bash
pip install -e ".[mms]"
```

Generate an SWMF parameter file from interval-averaged MMS observations in GSM
coordinates:

```bash
./tools/create_swmf_input.py --mms-start "2018-12-19 19:40:00" \
  --mms-end "2018-12-19 19:52:00"
```

The command uses `data/Param/PARAM.in.Earth` as its default template. It updates
the template's `#STARTTIME` and `#SOLARWIND` values and records the averaged MMS
location. By default, the start time is the midpoint of the MMS interval; use
`--start-time` to override it. Probe 1 and automatic burst/fast data selection
are the defaults, with `--probe` and `--mode` available for explicit selection.
When `--output` is omitted, the file is named
`PARAM_YYYYMMDD_HHMMSS.in` using the effective UTC start time. Supply
`--output` to choose a different filename.

Show all template, time, probe, and data-mode options with:

```bash
./tools/create_swmf_input.py -h
```

## Tecplot to VTK conversion

Convert every zone in an ASCII Tecplot `.dat` file to a VTK multiblock `.vtm`
file without normalizing or combining the zones:

```bash
./tools/convert_dat_to_vtm.py path/to/input.dat
```

The output defaults to one container directory beside the input:

```text
path/to/input_vtk/
├── input.vtm
└── input/
    └── generated VTK sidecar files
```

Provide a second positional argument to choose another container directory:

```bash
./tools/convert_dat_to_vtm.py input.dat custom_vtk
```

To remove the source file only after a successful conversion, add
`--delete-input`:

```bash
./tools/convert_dat_to_vtm.py input.dat --delete-input
```

Show the complete usage and examples with:

```bash
./tools/convert_dat_to_vtm.py -h
```

The container keeps the `.vtm` metadata and its generated `.vts`, `.vti`, or
`.vtu` sidecar files together. Move or copy the complete container directory
when relocating the converted dataset.

When the Tecplot `TITLE` contains a BATSRUS simulation timestamp, the converted
VTM root exposes it as `field_data["time_event"]`, normalized to an ISO-8601 UTC
string such as `2023-12-16T11:30:00.000+00:00`.

## Status

ShockLink is pre-alpha research software. Validate the detection and resolution
for each simulation before using results in scientific analysis.
