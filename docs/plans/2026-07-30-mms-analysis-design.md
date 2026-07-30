# MMS satellite-data analysis design

## Goal

Provide a runnable MMS analysis example and notebook that download a selected
time interval of magnetic-field and FPI plasma-moment data, visualize it, and
report compact interval statistics.

## Scope and location

The implementation will live in `examples/mms_data_analysis.py`, rather than
the core `shocklink` package. MMS observations are a complementary workflow to
ShockLink's simulation-analysis library, and keeping the code as an example
avoids making pySPEDAS a mandatory package dependency.

An accompanying `examples/mms_data_analysis.ipynb` will call the same public
functions so the workflow can be tested and explored interactively.

## Interface

The script accepts a start time, end time, probe number (default MMS1), and
`--mode` with `auto`, `brst`, or `fast` values. `auto` tries burst data first,
then retries fast-survey data when burst products are unavailable. Explicit
`brst` and `fast` requests do not silently switch cadence.

## Data and plotting

Data loading uses pySPEDAS MMS FGM and FPI loaders. It requests magnetic-field
vectors, ion/electron number density, bulk-velocity vectors, and available
scalar, parallel, and perpendicular temperatures. A Matplotlib figure shows
magnetic-field components and magnitude, species densities, velocity
components, and temperatures. Missing products are skipped with a clear
message rather than failing the complete run.

## Analysis and failures

The loader returns an object containing the loaded cadence and named time
series. The analysis routine calculates per-series sample count, mean, minimum,
and maximum, and the command-line entry point prints those results. Loader
errors and an interval with no usable data produce actionable messages.

## Dependencies and tests

pySPEDAS and Matplotlib will be an optional `mms` dependency group. Tests will
use dependency injection/mocking to exercise cadence selection, variable
collection, statistics, and plot creation without downloading data. The
notebook will have a non-network structural test only.
