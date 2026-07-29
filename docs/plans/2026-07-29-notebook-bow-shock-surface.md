# Notebook Bow-Shock Surface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Calculate the bow-shock X-coordinate array from `data/3d.dat` in the example notebook and display it as a static Y-Z heat map.

**Architecture:** Extend the existing Tecplot notebook after shock-region extraction, reusing `get_bow_shock_surface()` without changing source modules. Structural notebook tests define the clean cell workflow, and an executed copy outside the repository verifies the complete 1.3 GB real-data path.

**Tech Stack:** Python 3.11+, NumPy, PyVista 0.48+, Jupyter/nbconvert, nbformat, pytest

---

Implement this plan with @superpowers:test-driven-development. Before
reporting completion, use @superpowers:verification-before-completion.

### Task 1: Calculate and validate the surface array in the notebook

**Files:**
- Modify: `tests/test_notebook.py:19-95`
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Add failing notebook-workflow assertions**

In `test_notebook_covers_read_cut_validate_and_plot_workflow()`, add these
items to `required_fragments`:

```python
        "get_bow_shock_surface",
        "SURFACE_Y",
        "SURFACE_Z",
        "SURFACE_X_RANGE",
        "SURFACE_X_RESOLUTION",
        "SURFACE_CHUNK_SIZE",
        "surface_x",
```

Replace:

```python
    assert "from shocklink.bowshock import fit_bow_shock" in code
```

with:

```python
    assert "from shocklink.bowshock import (" in code
    assert "fit_bow_shock" in code
    assert "get_bow_shock_surface" in code
```

After the shock-region assertions, add:

```python
    assert "surface_x = get_bow_shock_surface(" in code
    assert "shock_region," in code
    assert "y=SURFACE_Y" in code
    assert "z=SURFACE_Z" in code
    assert "x_range=SURFACE_X_RANGE" in code
    assert "x_resolution=SURFACE_X_RESOLUTION" in code
    assert "chunk_size=SURFACE_CHUNK_SIZE" in code
    assert (
        "surface_x.shape == (len(SURFACE_Y), len(SURFACE_Z))"
        in code
    )
    assert "finite_surface.any()" in code
    assert "finite_surface[center_index]" in code
    assert code.index("shock_region = extract_shockfit_range(") < code.index(
        "surface_x = get_bow_shock_surface("
    )
```

In `test_notebook_is_portable_and_documents_launch()`, add:

```python
    assert "SURFACE_Y = np.linspace(-20.0, 20.0, 81)" in all_source
    assert "SURFACE_Z = np.linspace(-20.0, 20.0, 81)" in all_source
    assert "SURFACE_X_RANGE = (-40.0, 20.0)" in all_source
    assert "SURFACE_X_RESOLUTION = 241" in all_source
    assert "SURFACE_CHUNK_SIZE = 256" in all_source
```

**Step 2: Run the notebook tests and verify they fail**

Run:

```bash
python -m pytest tests/test_notebook.py -q
```

Expected: the workflow and portability tests fail because the notebook does
not contain the surface extraction.

**Step 3: Extend the notebook introduction and imports**

Update the first markdown cell so its first paragraph says:

```markdown
This notebook reads the local BATSRUS Tecplot sample, fits the bow shock from
velocity divergence, extracts a `shockfit` neighborhood, creates a planar cut,
plots pressure and `div(U)`, and extracts the maximum-compression bow-shock
surface as a Y-Z heat map.
```

Replace the bow-shock import in the setup cell with:

```python
from shocklink.bowshock import (
    extract_shockfit_range,
    fit_bow_shock,
    get_bow_shock_surface,
)
```

**Step 4: Add surface configuration**

In the configuration cell, after `SCALARS = "p"`, add:

```python
SURFACE_Y = np.linspace(-20.0, 20.0, 81)
SURFACE_Z = np.linspace(-20.0, 20.0, 81)
SURFACE_X_RANGE = (-40.0, 20.0)
SURFACE_X_RESOLUTION = 241
SURFACE_CHUNK_SIZE = 256
```

**Step 5: Add a calculation and validation cell**

Insert a new code cell immediately after the cell that creates
`shock_region` and `cut`:

```python
surface_x = get_bow_shock_surface(
    shock_region,
    y=SURFACE_Y,
    z=SURFACE_Z,
    x_range=SURFACE_X_RANGE,
    x_resolution=SURFACE_X_RESOLUTION,
    chunk_size=SURFACE_CHUNK_SIZE,
)
finite_surface = np.isfinite(surface_x)
center_index = (len(SURFACE_Y) // 2, len(SURFACE_Z) // 2)

assert surface_x.shape == (len(SURFACE_Y), len(SURFACE_Z))
assert finite_surface.any()
assert finite_surface[center_index]

finite_values = surface_x[finite_surface]
finite_fraction = 100.0 * finite_surface.mean()
print(f"Surface array shape: {surface_x.shape}")
print(
    f"Finite surface points: {finite_surface.sum():,}/{surface_x.size:,} "
    f"({finite_fraction:.1f}%)"
)
print(
    f"Bow-shock X range: {finite_values.min():.3f} to "
    f"{finite_values.max():.3f} R"
)
```

Leave its `execution_count` as `null` and `outputs` as an empty list.

**Step 6: Run the notebook tests**

Run:

```bash
python -m pytest tests/test_notebook.py -q
```

Expected: all notebook tests pass; the existing figure count remains two.

**Step 7: Commit the calculation workflow**

```bash
git add examples/tecplot_2d_cut.ipynb tests/test_notebook.py
git commit -m "docs: calculate bow-shock surface in notebook"
```

### Task 2: Add the static Y-Z heat map

**Files:**
- Modify: `tests/test_notebook.py:19-95`
- Modify: `examples/tecplot_2d_cut.ipynb`

**Step 1: Add failing visualization assertions**

In `test_notebook_covers_read_cut_validate_and_plot_workflow()`, add:

```python
    assert "surface_y, surface_z = np.meshgrid(" in code
    assert 'indexing="ij"' in code
    assert "surface_map = pv.StructuredGrid(" in code
    assert 'surface_map.point_data["Bow-shock X [R]"]' in code
    assert 'surface_x.ravel(order="F")' in code
    assert 'scalars="Bow-shock X [R]"' in code
    assert 'nan_color="lightgray"' in code
    assert "surface_plotter.view_yz()" in code
    assert "surface_plotter.enable_parallel_projection()" in code
    assert "surface_plotter.show_grid()" in code
```

Change:

```python
    assert code.count('show(jupyter_backend="static")') == 2
```

to:

```python
    assert code.count('show(jupyter_backend="static")') == 3
```

**Step 2: Run the notebook test and verify it fails**

Run:

```bash
python -m pytest tests/test_notebook.py -q
```

Expected: the visualization assertions and figure count fail.

**Step 3: Add the Y-Z heat-map cell**

Insert this code cell immediately after the surface calculation cell:

```python
surface_y, surface_z = np.meshgrid(
    SURFACE_Y,
    SURFACE_Z,
    indexing="ij",
)
surface_map = pv.StructuredGrid(
    np.zeros_like(surface_y),
    surface_y,
    surface_z,
)
surface_map.point_data["Bow-shock X [R]"] = surface_x.ravel(order="F")

surface_plotter = pv.Plotter()
surface_plotter.add_mesh(
    surface_map,
    scalars="Bow-shock X [R]",
    cmap="viridis",
    nan_color="lightgray",
    show_edges=False,
    scalar_bar_args={"title": "Bow-shock X [R]"},
)
surface_plotter.view_yz()
surface_plotter.enable_parallel_projection()
surface_plotter.show_grid()
surface_plotter.show(jupyter_backend="static")
```

Keep the existing pressure and `div(U)` plotting cells unchanged. Leave the
new cell clean.

**Step 4: Run the notebook tests**

Run:

```bash
python -m pytest tests/test_notebook.py -q
```

Expected: all notebook tests pass with three required static figures.

**Step 5: Commit the visualization**

```bash
git add examples/tecplot_2d_cut.ipynb tests/test_notebook.py
git commit -m "docs: visualize bow-shock surface in yz plane"
```

### Task 3: Execute the complete notebook on `data/3d.dat`

**Files:**
- Verify: `examples/tecplot_2d_cut.ipynb`
- Verify: `/tmp/tecplot_2d_cut.executed.ipynb`

**Step 1: Confirm the input data exists**

Run:

```bash
test -f data/3d.dat
du -h data/3d.dat
```

Expected: the file exists and is approximately 1.3 GB.

**Step 2: Execute an external notebook copy**

Run:

```bash
python -m jupyter nbconvert \
  --to notebook \
  --execute examples/tecplot_2d_cut.ipynb \
  --output /tmp/tecplot_2d_cut.executed.ipynb \
  --ExecutePreprocessor.timeout=900
```

Expected: nbconvert exits successfully and writes only the `/tmp` output.

**Step 3: Inspect the executed notebook**

Run:

```bash
python -c 'import nbformat; p=nbformat.read("/tmp/tecplot_2d_cut.executed.ipynb", as_version=4); errors=[o for c in p.cells for o in c.get("outputs", []) if o.get("output_type")=="error"]; text="\n".join(o.get("text", "") for c in p.cells for o in c.get("outputs", []) if o.get("output_type")=="stream"); assert not errors, errors; assert "Surface array shape: (81, 81)" in text; assert "Finite surface points:" in text; assert "Bow-shock X range:" in text; print(text)'
```

Expected: no cell errors and the surface summary reports finite values.

**Step 4: Verify the source notebook is still clean**

Run:

```bash
python -m pytest \
  tests/test_notebook.py::test_notebook_is_valid_and_clean \
  -q
```

Expected: `1 passed`.

### Task 4: Run repository verification

**Files:**
- Verify: `examples/tecplot_2d_cut.ipynb`
- Verify: `tests/test_notebook.py`

**Step 1: Run focused tests**

Run:

```bash
python -m pytest tests/test_notebook.py tests/bowshock/test_surface.py -q
```

Expected: all focused tests pass.

**Step 2: Run static checks**

Run:

```bash
python -m ruff check src tests
python -m ruff format --check src tests
```

Expected: both commands succeed.

**Step 3: Run the complete default suite**

Run:

```bash
python -m pytest -q
```

Expected: all default tests pass; opt-in large-data integration tests remain
skipped because the notebook execution already exercised the real file.

**Step 4: Inspect repository state**

Run:

```bash
git diff --check
git status --short --branch
```

Expected: no whitespace errors or unintended files. Preserve the existing
untracked `pressure-z0.png`. Do not add the executed notebook under `/tmp`.

**Step 5: Review the requirements**

Confirm:

- the notebook reads `ROOT / "data/3d.dat"`;
- `get_bow_shock_surface()` consumes `shock_region`;
- the returned shape is `(81, 81)` with Y as axis 0 and Z as axis 1;
- the center and at least one array element are finite;
- the Y-Z map uses color to represent X and is not warped;
- pressure, `div(U)`, and surface plots all remain present;
- the committed notebook has no execution counts or outputs;
- no source module, dependency, or package-layout change was introduced.
