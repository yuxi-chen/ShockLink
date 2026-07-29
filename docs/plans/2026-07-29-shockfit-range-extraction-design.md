# Shock-Fit Range Extraction Design

## Goal

Extract the mesh region associated with an inclusive range of the fitted
bow-shock residual and return it as a PyVista `UnstructuredGrid`.

## Public API

Add to `shocklink.bowshock`:

```python
region = extract_shockfit_range(
    dataset,
    lower=-0.5,
    upper=0.5,
    shockfit_name="shockfit",
    adjacent_cells=True,
)
```

The function selects finite point values satisfying:

```text
lower <= shockfit <= upper
```

and returns the result of PyVista point extraction as an
`UnstructuredGrid`.

## Cell Semantics

With the default `adjacent_cells=True`, include every cell that touches at
least one selected point. This is appropriate for a thin neighborhood around
`shockfit = 0`, because cells crossing the range boundary remain available for
plotting and filters. Some returned cell points may consequently have values
outside the requested range.

With `adjacent_cells=False`, include only cells whose points are all selected.
This is stricter and may return few or no cells for a narrow range.

Always use `include_cells=True`, `pass_point_ids=True`, and
`pass_cell_ids=True`. The returned grid therefore preserves connectivity and
provides `vtkOriginalPointIds` and `vtkOriginalCellIds`.

## Validation and Errors

Raise `DatasetError` when:

- `shockfit_name` is empty;
- the named array is absent from point data;
- the array is not a scalar with one value per dataset point;
- limits are nonnumeric or non-finite;
- `lower > upper`;
- `adjacent_cells` is not a boolean;
- PyVista extraction fails or returns a type other than
  `pyvista.UnstructuredGrid`.

Non-finite `shockfit` values are excluded from the mask. A valid range that
selects no points returns an empty `UnstructuredGrid`.

## Testing

Use a small image grid with known `shockfit` values. Verify inclusive
boundaries, original IDs, adjacent versus exclusive cell selection, custom
array naming, empty extraction, validation errors, non-finite exclusion, and
wrapped PyVista failures.
