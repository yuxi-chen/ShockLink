# Tecplot 2D Cut Notebook Design

## Goal

Add a clean Jupyter notebook that exercises ShockLink's complete sample
workflow:

1. locate and read `data/3d.dat`;
2. inspect the normalized three-dimensional PyVista grid;
3. extract a configurable planar cut; and
4. plot pressure inline.

The notebook lives at:

```text
examples/tecplot_2d_cut.ipynb
```

## Notebook Structure

The notebook contains:

1. a Markdown introduction with launch instructions and the large-data warning;
2. a setup cell that imports PyVista and ShockLink while locating the repository
   root whether Jupyter starts from the root or `examples/`;
3. a parameter cell defining `DATA_PATH`, `NORMAL`, `ORIGIN`, and `SCALARS`;
4. a read cell that times `read_tecplot()` and displays the grid summary,
   corrected bounds, and available point arrays;
5. a cut cell that calls `get_2d_cut()` and reports its size, bounds, and arrays;
6. validation assertions for planarity and the pressure, magnetic-field, and
   velocity arrays; and
7. a plot cell that calls `plot_2d_cut(show=False)` and displays the result
   using PyVista's built-in static Jupyter backend.

The defaults are the real local sample, the GSM equatorial plane (`Z = 0`), and
pressure alias `p`.

## Environment Behavior

The notebook adds the repository's `src/` directory to `sys.path` only when the
package is not already importable. This lets it work both after
`pip install -e .` and directly from a source checkout.

PyVista uses `jupyter_backend="static"` because Jupyter, nbformat, nbconvert,
and ipykernel are installed locally while the optional Trame stack is not.

## Clean Artifact Policy

The committed `.ipynb` contains no execution counts or cell outputs. Generated
`.ipynb_checkpoints/` directories are ignored.

Verification executes a temporary notebook copy outside the repository. The
executed copy and its embedded static plot remain temporary, so neither the
1.3 GB input nor rendered binary output enters Git.

## Validation

Automated tests parse the notebook with nbformat and verify:

- valid notebook format;
- expected cell order and key API calls;
- no committed outputs or execution counts;
- the static PyVista backend;
- parameter defaults; and
- no absolute, machine-specific source path.

A real execution through nbconvert verifies every cell against `data/3d.dat`.
Because macOS VTK requires a Cocoa OpenGL context, the execution may need to run
outside the filesystem sandbox, just like the already verified screenshot
workflow.
