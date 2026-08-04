# Python Production Simplification Design

## Purpose

Reduce duplication and unnecessary helper surface across `src/shocklink`
without changing public APIs, numerical results, CLI behavior, or domain error
contracts. Consolidation is based on shared meaning, not merely similar-looking
code.

Tests and examples may be updated to verify the production refactor, but their
local fixtures and helpers are not themselves consolidation targets.

## Approach

Use targeted semantic consolidation:

- centralize genuinely shared physical and coordinate constants;
- move reusable conversions and time-bound behavior into utilities;
- reuse one Cartesian-component definition throughout MMS calculations;
- remove private helpers with no production callers;
- merge local validation helpers only when their accepted inputs and errors
  remain clear;
- retain separate functions when their domain responsibility differs.

This avoids an all-purpose validation or constants dumping ground.

## Shared constants

Create `src/shocklink/constants.py` with:

```python
EV_TO_K = 11604.51812
EARTH_RADIUS_KM = 6371.2
CARTESIAN_COMPONENTS = ("x", "y", "z")
```

These values are shared by more than one MMS or MMS-to-SWMF module and have a
single domain meaning.

The following remain local to their owners:

- SWMF section field labels;
- Tecplot default array names;
- dataset field-data keys and axis-normal arrays;
- MMS product lists and vector-series lists;
- plot line widths, colors, and formatting choices.

## Utilities and time bounds

`src/shocklink/utilities.py` becomes the shared home for:

- `parse_datetime`;
- `midpoint_datetime`;
- `TimeBounds` with Unix and NumPy representations;
- `ev_to_kelvin` and `kelvin_to_ev`.

`mms.data`, `mms.loading`, `mms.plotting`, and `mms_swmf` import these shared
definitions. The duplicate conversion constant and wrappers are removed from
MMS data, and the unused `_parse_utc_time` helper is deleted.

## MMS simplification

MMS modules import `CARTESIAN_COMPONENTS` rather than repeating literal
`("x", "y", "z")` tuples. The MMS-to-SWMF mapping uses one local helper to
collect a named three-component vector, eliminating duplicated generator
expressions while retaining required-key and finite-value validation.

The two CLIs keep separate parsers. Their time flag names and outputs differ,
and a shared parser abstraction would add indirection without a stable shared
interface.

## Local validation consolidation

### Dataset

Add one private finite numeric sequence converter used by `_vector3` and
`_plot_range`. Shape, ordering, and domain-specific error messages remain at
the call sites. This shares conversion and finite-value mechanics without
coupling dataset behavior to bow-shock geometry.

### Bow shock

- Replace `_normal_axis` with a `minimum_size` option on `_surface_axis`.
- Extract robust unit-vector normalization used by both the normal field and
  reference vector in `calc_bow_shock_normal_angle`.
- Keep specialized surface, divergence, interpolation, integer, and geometry
  validators separate because they enforce distinct shapes and exception
  contracts.

The large `bowshock.py` is not split in this change. Splitting modules is an
architectural reorganization rather than consolidation of similar behavior.

## Dependency boundaries

`constants.py` imports nothing. `utilities.py` may import NumPy and shared
constants. Domain modules depend inward on those two modules; neither imports
MMS, SWMF, dataset, or bow-shock modules.

Existing boundaries remain:

- `swmf.py` does not import MMS;
- private MMS modules do not import the public MMS facade;
- optional pySPEDAS, pytplot, and Matplotlib imports remain lazy.

## Error handling and compatibility

Public function signatures and exports remain unchanged. Existing exception
types and actionable error text are preserved. Private helpers may move or be
removed; underscored imports are not compatibility promises, but existing
tests are migrated to the new owner where appropriate.

## Testing

- Add a constants ownership test that rejects duplicate definitions of shared
  constants in production modules.
- Move temperature-conversion and `TimeBounds` tests to utility tests.
- Keep focused MMS, dataset, bow-shock, SWMF, and module-boundary tests green at
  each refactor step.
- Run Ruff and the complete test suite before integration.

The existing uncommitted modification to `data/Param/PARAM.in.Earth` is not in
scope and must remain untouched.
