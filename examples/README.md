# ShockLink Examples

## Complete bow-shock workflow

The [bow-shock workflow guide](../docs/bow-shock-workflow.md) explains the
full Tecplot-to-normal pipeline and its array/sign conventions.

Run the non-graphical example:

```bash
PYTHONPATH=src python examples/bow_shock_workflow.py data/3d.dat
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

## Python scripts

## MMS satellite-data analysis

Install the optional MMS tools, then download and plot a short MMS interval.
Automatic mode prefers burst data and uses fast survey data when burst is not
available:

```bash
pip install -e ".[mms]"
python examples/mms_data_analysis.py \
  --start "2015-10-16 13:06:00" --end "2015-10-16 13:07:00" --probe 1 --mode auto
```

Vectors use GSE coordinates by default. When `--coordinates gsm` is selected,
pySPEDAS transforms the magnetic-field and bulk-velocity vectors to
time-dependent GSM coordinates; scalar density and temperature products remain
unchanged:

```bash
python examples/mms_data_analysis.py \
  --start "2018-12-19 19:40:00" \
  --end "2018-12-19 19:52:00" \
  --probe 1 --mode auto \
  --coordinates gsm
```

The figure subtitle reports the interval-averaged MMS position in GSM and
Earth radii (`$R_E$`) when MEC ephemeris data are available. The command also prints means for the
displayed variables; total ion/electron temperatures and their means are
shown in eV on the left-hand plot axis.

For interactive exploration, launch `jupyter lab examples/mms_example.ipynb`.
The notebook exposes the time range, probe, `auto`/`brst`/`fast` mode, and GSE
or GSM coordinate selection near the top, then uses the same public loading,
summary, and plotting functions as the script.

Read and summarize the sample:

```bash
PYTHONPATH=src python examples/read_tecplot.py data/3d.dat
```

Open an interactive pressure cut:

```bash
PYTHONPATH=src python examples/plot_2d_cut.py data/3d.dat
```

Save a pressure-cut screenshot:

```bash
PYTHONPATH=src python examples/plot_2d_cut.py data/3d.dat \
  --screenshot pressure-cut.png
```

Limit the displayed world-coordinate range without cropping the cut:

```bash
PYTHONPATH=src python examples/plot_2d_cut.py data/3d.dat \
  --xrange -40 30 --yrange -60 60
```

The same limits can be combined with `--screenshot`.
