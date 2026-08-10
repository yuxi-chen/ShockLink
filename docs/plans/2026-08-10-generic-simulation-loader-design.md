# Generic Simulation Loader Design

## Goal

Provide one public loader for original Tecplot `.dat` files and converted VTK multiblock `.vtm` files without exposing a source-format name in the primary module or function.

## Public API and compatibility

The primary API will be:

```python
from shocklink.io import TIME_EVENT_KEY, load_simulation

data = load_simulation("data/3d_vtk/3d.vtm")
```

The implementation moves from `shocklink.tecplot` to `shocklink.io`. The new module exports only `TIME_EVENT_KEY` and `load_simulation`.

`shocklink.tecplot` remains as a small compatibility facade. Its existing `read_tecplot()` function delegates to `load_simulation()` with the same keyword arguments, so existing callers continue to work. New documentation and examples use `shocklink.io`.

## Supported inputs and return values

`load_simulation()` accepts `.dat` and `.vtm` files and rejects all other suffixes.

- If the input contains exactly one nonempty zone, the loader returns that PyVista dataset directly.
- If the input contains multiple nonempty zones, it returns the original `pyvista.MultiBlock` with block names, ordering, empty entries, and nesting preserved.
- Empty inputs and unsupported non-dataset leaves raise `DatasetError`.

The single-zone return type is generalized from `UnstructuredGrid` to `pyvista.DataSet`, allowing converted structured zones to retain their native VTK type. Existing unstructured Tecplot inputs still return `UnstructuredGrid`.

## Loading and time metadata

Path validation happens before PyVista is called. Both formats are loaded with `pyvista.read()` and must produce a `MultiBlock` root.

For `.dat`, the event time is parsed from the `TITLE` header before loading, using the existing timestamp behavior. For `.vtm`, the event time is read from root `field_data["time_event"]`, validated as one parseable value, and normalized to the same millisecond ISO-8601 UTC representation. The normalized value remains on the multiblock root and is copied to every nonempty dataset leaf so a directly returned zone has identical metadata.

## Geometry and vector normalization

Every nonempty dataset leaf is normalized independently.

Coordinate handling uses this order:

1. If the caller supplies `coordinate_components`, require and use those arrays.
2. Otherwise, use the first complete recognized triplet: unit-bearing `X/Y/Z` arrays or cleaned `X/Y/Z` arrays.
3. If no recognized coordinate arrays are present, retain the existing finite VTK points. This is the expected converted-VTM path because recognized Tecplot coordinates are already stored as geometry.

Magnetic and velocity components follow the same explicit-override-then-detection rule. Detection recognizes both the existing unit-bearing names and the cleaned names written by the converter. The loader composes `B [nT]` and `U [km/s]` without deleting scalar components. Missing or invalid component arrays raise `DatasetError` with the affected zone path and field type.

Coordinates must be finite. Magnetic and velocity values preserve the existing behavior and may contain missing values.

## Multiblock behavior

Normalization walks nested `MultiBlock` containers recursively and replaces no containers or block names. Empty blocks are retained. Each nonempty `pyvista.DataSet` leaf is normalized in place. The loader counts nonempty dataset leaves after traversal: one leaf is unwrapped for convenience and compatibility; two or more return the root multiblock.

## Error handling

All public failures use `DatasetError`, including missing paths, unsupported suffixes, PyVista read failures, wrong root types, missing or malformed time metadata, empty multiblocks, unsupported leaf types, invalid coordinates, and missing vector components. Messages include the source path and, for nested VTM data, the block path when relevant.

## Documentation and migration

User-facing code moves to `load_simulation()`:

- Rename `examples/read_tecplot.py` to `examples/load_simulation.py`.
- Update the workflow examples, notebooks, example README, and current documentation.
- Update unit and integration tests to exercise the primary API.
- Keep focused compatibility tests for `shocklink.tecplot.read_tecplot()`.
- Do not rewrite historical plans, which document the repository state at the time they were created.

## Testing

Tests will cover:

- existing `.dat` geometry, vector, override, timestamp, and error behavior;
- cleaned component-name detection;
- a real temporary single-zone `.vtm` round trip;
- structured and unstructured dataset leaves;
- root time recovery and propagation;
- multi-zone return behavior with names, order, empty blocks, and nesting preserved;
- malformed VTM metadata and unsupported leaves;
- the legacy import and wrapper;
- migrated examples, notebooks, documentation, and module boundaries.

Implementation follows test-driven development: each new behavior is first captured by a failing focused test, followed by targeted tests, formatting/static checks, and the full suite.
