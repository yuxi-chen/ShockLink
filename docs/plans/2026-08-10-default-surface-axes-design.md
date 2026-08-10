# Default Bow-Shock Surface Axes Design

## Goal

Allow `get_bow_shock_surface(dataset)` to omit `y` and `z`, using 241 evenly
spaced coordinates from -30 through 30 for each axis.

## Design

Define private, read-only NumPy arrays for the default Y and Z coordinates and
use them as the keyword defaults in `get_bow_shock_surface`. Explicit caller
values continue through the existing validation and sampling path unchanged.
Document the defaults in the function docstring.

## Testing

Add a public-API regression test that omits both axes and verifies the returned
surface has the expected `(241, 241)` shape. Keep existing tests for explicit
axes unchanged to protect backward compatibility.
