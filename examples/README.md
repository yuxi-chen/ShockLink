# ShockLink Examples

## Bow-shock workflow

The [algorithm guide](../docs/algorithms.md) explains the full
Tecplot-to-normal pipeline and its array/sign conventions.

Download or clone ShockLink, then install the repository in editable mode from
its root before running copied examples or examples from outside the checkout:

```bash
pip install -e .
```

## Extract bow-shock notebook

Install ShockLink with the notebook tools from the repository root:

```bash
pip install -e ".[notebook]"
```

Make sure the untracked BATSRUS sample is available at `data/3d.dat`, then
launch:

```bash
jupyter lab examples/extract_shock.ipynb
```

The notebook exposes the input file, Y-Z surface grid, X search range,
smoothing width, and reference vector near the top. It reads the local sample,
calculates `div(U)`, extracts and smooths the bow-shock surface, then plots the
surface and normal angle on the Y-Z plane.

The key parameters are:

- `DATA_PATH`: Tecplot `*.dat` input;
- `SURFACE_Y` and `SURFACE_Z`: the transverse sampling coordinates;
- `SURFACE_X_RANGE`: X search bounds;
- `SMOOTHING_SIGMA`: Gaussian smoothing width in grid cells; and
- `REFERENCE_VECTOR`: direction compared with outward shock normals.

The sample is about 1.3 GB. Reading and normalizing it uses roughly 1 GB before
the cut and rendering allocations. The data file, notebook outputs, and
checkpoints are not committed.

### MMS–bow-shock connection

The standard ShockLink installation includes pySPEDAS and Matplotlib. Read
[the algorithm guide](../docs/algorithms.md), then run:

```bash
python tools/mms_bow_shock_connection.py data/3d.dat \
  --param-file results/PARAM_20181219_194600.in \
  --output-directory results --three-d-output both
```

The tool reads the timestamp and averaged magnetic field from the PARAM file
created by `create_swmf_input.py`. When the file contains a `! MMS Location at`
block, that GSM position is used; otherwise the tool downloads MMS data to
interpolate the position. The 2D angle map is saved as PNG; the 3D view can be saved as PNG,
interactive HTML, or both with
`--three-d-output`. By default, `xxx.dat` produces
`xxx_shock_connection_2d.png` and `xxx_shock_connection_3d.png`; use
`--output-prefix` to override the filename prefix. HTML export requires
`pip install "pyvista[jupyter]"`.

## MMS satellite-data analysis

For batch creation of SWMF inputs, edit the ``EVENTS`` list in
[`create_swmf_inputs.py`](create_swmf_inputs.py), then run:

```bash
python examples/create_swmf_inputs.py
```

After the editable install, the script can also be copied elsewhere and run
without setting `PYTHONPATH`; it locates the default template from the
ShockLink checkout.

The script creates one `PARAM_*.in` file per `(start, end)` interval and saves
the MMS quick-look plot beside each file by default.

### Sequential SWMF batch runs

[`run_swmf_inputs.py`](run_swmf_inputs.py) runs a directory of generated PARAM
files from an SWMF `run/` directory. For example:

```bash
cd /path/to/SWMF/run
python /path/to/ShockLink/examples/run_swmf_inputs.py /path/to/param-files
```

The script sorts `PARAM_*.in` files lexicographically and processes them one at
a time. For each input, it:

1. copies the input to `PARAM.in`;
2. runs `mpiexec ./SWMF.exe`, writing stdout and stderr to `runlog` and waiting
   for completion; and
3. runs `./PostProc.pl res/runNNN_<input-suffix>`.

For example, the first input named
`PARAM_20171207_075400_20171207_080600.in` is postprocessed into
`res/run001_20171207_075400_20171207_080600`. The next input uses `run002`, and
so on. If `res/` already contains matching result directories, numbering starts
one above the highest numeric prefix; for example, existing `run001_*` through
`run005_*` results make the next result `run006_*`. Gaps are not reused, and
unrelated names and files are ignored. The script creates `res/` if necessary.
If SWMF or postprocessing fails, the batch stops immediately and leaves the
active `PARAM.in` and `runlog` in the run directory for diagnosis. Before
starting, it also checks every planned result path and stops if any already
exists, preventing an accidental rerun from mixing with earlier results.

MMS loading and plotting packages are included in the standard installation.
Launch the notebook for a short MMS interval after installing the notebook
tools. Automatic mode prefers burst data and uses fast survey data when burst
is not available:

```bash
pip install -e ".[notebook]"
jupyter lab examples/mms_example.ipynb
```

The reusable implementation is provided by `shocklink.mms`; the example
notebook uses the same public workflow directly:

```python
from shocklink.mms import load_mms_data, plot_mms_data
```

Vectors use GSE coordinates by default. When `COORDINATES = "gsm"` is selected,
pySPEDAS transforms the magnetic-field and bulk-velocity vectors to
time-dependent GSM coordinates; scalar density and temperature products remain
unchanged:

Set `START`, `END`, `PROBE`, `MODE`, and `COORDINATES = "gsm"` in the notebook
to select this interval and coordinate system.

The figure subtitle reports the interval-averaged MMS position in GSM and
Earth radii (`$R_E$`) when MEC ephemeris data are available. The command also prints means for the
displayed variables; total ion/electron temperatures and their means are
shown in eV on the left-hand plot axis, with a linked K scale on the right for
the same temperature lines.

For interactive exploration, launch `jupyter lab examples/mms_example.ipynb`.
The notebook exposes the time range, probe, `auto`/`brst`/`fast` mode, and GSE
or GSM coordinate selection near the top, then uses the same public loading,
summary, and plotting functions.

The reusable loading, cut, plotting, and MMS functions are available from
`shocklink.io`, `shocklink.dataset`, and `shocklink.mms`; use those APIs from
Python when a notebook is not appropriate.
