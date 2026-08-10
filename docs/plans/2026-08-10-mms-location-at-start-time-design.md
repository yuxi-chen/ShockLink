# MMS Location at Effective Start Time Design

**Goal:** Write the MMS spacecraft location at the exact effective SWMF start
time instead of averaging spacecraft positions across the observation interval.

## Design

The effective timestamp remains the explicit `start_time` when supplied and the
MMS interval midpoint otherwise. Magnetic field, density, velocity, and
temperature values remain finite means over the full interval. Only spacecraft
location changes semantics.

Add a reusable MMS analysis helper that resolves the GSM MEC position series and
linearly interpolates its finite XYZ samples at a requested UTC timestamp. The
helper returns the position in Earth radii. Exact sample timestamps return the
recorded sample; timestamps between samples use component-wise linear
interpolation. Missing position data, fewer than one usable sample, or a target
outside the finite sample range raise a clear error rather than extrapolating.

`create_swmf_input()` will calculate the effective start time before constructing
the MMS location, call the new helper, and pass that location to the existing
parameter-file generator. `average_plotted_values()` remains unchanged because
plots and summaries still use interval-averaged position.

Tests will cover exact samples, between-sample interpolation, finite-row
filtering, out-of-range and missing-data errors, midpoint selection, explicit
start-time selection, and public API/documentation updates.
