# Tecplot 2D Cut Notebook Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a clean, validated Jupyter notebook that reads the real BATSRUS Tecplot sample, extracts a configurable 2D cut, and plots pressure inline.

**Architecture:** Keep the notebook as an example client of the public ShockLink API. Validate its committed JSON and cell semantics with a fast nbformat test, then execute a temporary copy through nbconvert for real-data verification without committing outputs.

**Tech Stack:** Jupyter, nbformat, nbconvert, IPython kernel, PyVista static notebook backend, pytest, local `data/3d.dat`.

---

### Task 1: Add a clean, structurally validated notebook

**Files:**
- Modify: `pyproject.toml`
- Modify: `.gitignore`
- Create: `tests/test_notebook.py`
- Create: `examples/tecplot_2d_cut.ipynb`

**Step 1: Add notebook dependency metadata**

Add `nbformat>=5` to the `test` extra and add:

```toml
notebook = [
  "ipykernel>=6",
  "jupyterlab>=4",
  "nbconvert>=7",
  "nbformat>=5",
]
```

Add `.ipynb_checkpoints/` to `.gitignore`.

**Step 2: Write the failing notebook test**

Use `nbformat.read` and `nbformat.validate`. Assert:

```python
NOTEBOOK = ROOT / "examples/tecplot_2d_cut.ipynb"

def test_notebook_is_valid_and_clean() -> None:
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type == "code":
            assert cell.execution_count is None
            assert cell.outputs == []
```

Add tests that concatenate code sources and require:

- `read_tecplot`;
- `get_2d_cut`;
- `plot_2d_cut`;
- `DATA_PATH`, `NORMAL`, `ORIGIN`, and `SCALARS`;
- `pv.set_jupyter_backend("static")`;
- planarity and required-array assertions; and
- `plotter.show(jupyter_backend="static")`.

Reject `/Users/`, `pressure-z0.png`, and other machine-specific paths or
generated artifacts.

**Step 3: Run the test to verify it fails**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python -m pytest tests/test_notebook.py -v
```

Expected: FAIL because the notebook does not exist.

**Step 4: Create the clean notebook**

Create a version-4 notebook with:

1. Markdown title, purpose, install command, launch command, and memory warning.
2. Setup code:
   - import `Path`, `sys`, `time`, NumPy, and PyVista;
   - find the repository root from the current directory or its parents;
   - add `ROOT / "src"` to `sys.path` when needed;
   - import the three public ShockLink functions; and
   - set the static Jupyter backend.
3. Parameters:

   ```python
   DATA_PATH = ROOT / "data/3d.dat"
   NORMAL = "z"
   ORIGIN = (0.0, 0.0, 0.0)
   SCALARS = "p"
   ```

4. Timed `read_tecplot()` plus grid summary, bounds, and arrays.
5. `get_2d_cut()` plus cut summary, bounds, and arrays.
6. Assertions for `Z = 0` and `P [nPa]`, `B [nT]`, and `U [km/s]`.
7. `plot_2d_cut(show=False)` followed by static inline display.

All code cells have `execution_count: null` and `outputs: []`.

**Step 5: Run notebook tests and the ordinary suite**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
python -m pytest tests/test_notebook.py -v
```

Expected: PASS.

Run: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q`

Expected: all ordinary tests PASS.

**Step 6: Commit**

```bash
git add pyproject.toml .gitignore tests/test_notebook.py examples/tecplot_2d_cut.ipynb
git commit -m "docs: add clean Tecplot analysis notebook"
```

### Task 2: Execute a temporary notebook and document usage

**Files:**
- Create: `examples/README.md`
- Modify: `docs/plans/2026-07-28-shocklink-repository-design.md`

**Step 1: Execute into a temporary directory**

Create a unique temporary output directory and run:

```bash
MPLCONFIGDIR=<temporary-cache> \
XDG_CACHE_HOME=<temporary-cache> \
PYTHONPATH=src \
jupyter nbconvert \
  --to notebook \
  --execute examples/tecplot_2d_cut.ipynb \
  --output tecplot_2d_cut.executed.ipynb \
  --output-dir <temporary-output> \
  --ExecutePreprocessor.timeout=300
```

On macOS, run outside the sandbox so VTK's Cocoa backend can create an OpenGL
context.

Expected: all cells execute and the final output contains a static PNG.

**Step 2: Inspect executed output**

Parse the temporary notebook and assert:

- no output has `output_type == "error"`;
- every code cell has an execution count;
- the final plotting cell contains `image/png`; and
- grid and cut summary outputs are present.

**Step 3: Verify the committed notebook stayed clean**

Run the notebook regression test again and inspect `git diff` to confirm
execution did not modify the source `.ipynb`.

**Step 4: Document launch and parameter usage**

Create `examples/README.md` with:

```bash
pip install -e ".[notebook]"
jupyter lab examples/tecplot_2d_cut.ipynb
```

Explain `DATA_PATH`, `NORMAL`, `ORIGIN`, and `SCALARS`, the approximate memory
footprint, and that the 1.3 GB data file remains untracked.

Update the repository design's documentation list to include the notebook.

**Step 5: Run final verification**

Run:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python -m pytest -q
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 \
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src \
python -m pytest tests/integration/test_tecplot_sample.py -q
```

Build the wheel and source distribution. Verify:

- the wheel remains the flat Python package only;
- the source distribution includes the clean notebook and examples;
- neither distribution contains `data/3d.dat`, executed notebooks, or PNG
  output; and
- the working tree still contains the user's unrelated untracked
  `pressure-z0.png` unchanged.

**Step 6: Commit**

```bash
git add examples/README.md docs/plans/2026-07-28-shocklink-repository-design.md docs/plans/2026-07-29-tecplot-notebook-design.md docs/plans/2026-07-29-tecplot-notebook.md
git commit -m "docs: explain Tecplot notebook workflow"
```
