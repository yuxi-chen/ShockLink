# ShockLink Examples

## Tecplot 2D cut notebook

Install ShockLink with the notebook tools from the repository root:

```bash
pip install -e ".[notebook]"
```

Make sure the untracked BATSRUS sample is available at `data/3d.dat`, then
launch:

```bash
jupyter lab examples/tecplot_2d_cut.ipynb
```

The notebook exposes four parameters near the top:

- `DATA_PATH`: Tecplot `*.dat` input;
- `NORMAL`: cut-plane normal (`"x"`, `"y"`, `"z"`, or a numeric vector);
- `ORIGIN`: a point on the cut plane; and
- `SCALARS`: the plotted array (`"p"` resolves to `P [nPa]`).

Its defaults read the local sample, extract the GSM equatorial plane (`Z = 0`),
validate pressure plus the magnetic and velocity vectors, and display a static
pressure plot inline.

The sample is about 1.3 GB. Reading and normalizing it uses roughly 1 GB before
the cut and rendering allocations. The data file, notebook outputs, and
checkpoints are not committed.

## Python scripts

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
