# Package simplification design

## Goal

Simplify ShockLink's internal implementation and improve its documentation
without changing its public API, defaults, exception behavior, array layouts,
or scientific results.

## Approach

Use the existing test suite as the compatibility boundary. Start with the
repeated input-validation and workflow code shared by the simulation,
bow-shock, connectivity, MMS, and SWMF modules. Introduce small private helpers
only when they remove meaningful duplication or flatten nested control flow.
Keep domain-specific validation and error messages close to the public
operation that owns them.

The large numerical routines will remain in their current public modules.
Moving them into a new package hierarchy would increase import and regression
risk without improving the algorithms themselves. Refactoring will instead
extract cohesive private operations, clarify intermediate values, and remove
redundant branches while retaining the current computations in the same order.

## Compatibility and error handling

All documented imports and function signatures remain valid. Numerical arrays
retain their dtype, shape, indexing convention, missing-value behavior, and
read-only guarantees. Existing domain exceptions and validation messages remain
stable unless a test demonstrates that a message is misleading.

## Algorithm documentation

Expand `docs/algorithms.md` into a complete pipeline description covering:

1. input formats, normalization, and multiblock traversal;
2. velocity divergence and paraboloid fitting;
3. residual-region extraction and regular surface sampling;
4. minimum refinement, missing values, smoothing, and normals;
5. shock-angle calculation and triangulation;
6. straight-line/triangle intersections and hit selection;
7. MMS averaging, coordinate handling, PARAM generation, and plotting; and
8. assumptions, failure modes, and scientific validation limits.

Equations will define the numerical steps, while source links identify the
implementation boundary for each stage.

## Testing

Add focused characterization tests before each internal refactor. Run targeted
tests during development, static checks after code changes, and the complete
test suite once before integration. A final diff review will check that no
public exports, defaults, or scientific conventions changed.
