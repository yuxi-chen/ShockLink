# MMS module simplification design

## Purpose

Move the reusable MMS loading, analysis, and plotting implementation out of
`examples/mms_data_analysis.py` and into the installable `shocklink` package.
The example script and notebook will exercise the package API without owning
scientific or plotting logic.

The refactor is behavior-preserving. Existing cadence selection, GSE/GSM
conversion, interval clipping, statistics, plotted averages, plot appearance,
temperature conversion, spacecraft-location reporting, and error messages
remain covered by tests.

## Current problems

`examples/mms_data_analysis.py` is currently 698 lines and combines six
responsibilities:

1. CLI argument parsing and command execution.
2. pySPEDAS download and product-name selection.
3. GSE-to-GSM coordinate conversion.
4. pytplot resolution, metadata handling, and interval clipping.
5. numerical summaries and derived quantities.
6. Matplotlib panel construction and formatting.

The 645-line `tests/test_mms_data_analysis.py` mirrors this coupling. Plotting,
loading, analysis, and CLI tests share one module, making focused changes and
failures harder to understand.

The review also found small sources of accidental complexity:

- `_TimeSeries.name` and the corresponding name-metadata lookup are no longer
  used by plotting or analysis.
- `_plot_scalar` is unused.
- interval parsing and bounds construction are repeated in loading, series
  resolution, and plotting.
- `plot_mms_data` uses closures to describe a fixed panel sequence.
- implementation tests import private helpers from an example script rather
  than from the package that owns the behavior.

## Goals

- Make MMS analysis an installable `shocklink.mms` feature.
- Keep the existing user-facing API stable.
- Keep optional pySPEDAS and Matplotlib imports lazy.
- Keep the top-level package clean by grouping the MMS domain in an explicit
  `src/shocklink/mms/` subpackage.
- Give each source and test module one clear responsibility.
- Remove confirmed dead code and centralize shared interval behavior.
- Keep `examples/mms_data_analysis.py` as a minimal executable smoke test.
- Make `examples/mms_example.ipynb` import the package API directly.

## Non-goals

- Change downloaded MMS products or scientific formulas.
- Add new plots, command-line options, coordinate systems, or statistics.
- Make pySPEDAS or Matplotlib required core dependencies.
- Redesign the notebook workflow or plot styling.
- Preserve imports of underscored helpers from the old example module.
- Change unrelated source modules or introduce nested packages for domains
  that do not need their own cohesive API.

## Public API

`shocklink.mms` is the stable public façade. It exports:

```python
from shocklink.mms import (
    MMSData,
    average_plotted_values,
    load_mms_data,
    main,
    parse_args,
    plot_mms_data,
    summarize_data,
)
```

Function signatures and return values remain compatible with the current
example module. `MMSData` keeps the same fields and defaults. Importing
`shocklink` or `shocklink.mms` must not import pySPEDAS, pytplot, or Matplotlib
until the corresponding operation is called.

The root `shocklink.__init__` will not re-export MMS names. Users opt into the
optional feature explicitly with `from shocklink import mms` or imports from
`shocklink.mms`.

## Source architecture

The general package remains flat, with MMS as the explicit domain-package
exception:

### `src/shocklink/mms/__init__.py`

Public façade only. It imports and re-exports the supported names from the
private MMS modules and defines `__all__`. It contains no downloading,
analysis, or plotting implementation.

### `src/shocklink/mms/data.py`

Owns shared data concepts and transformations:

- `MMSData` and the internal resolved time-series dataclass;
- MMS constants and type aliases;
- UTC interval parsing and conversion to NumPy/Matplotlib bounds;
- pytplot variable resolution and interval clipping;
- total-temperature derivation;
- shared finite-value and spacecraft-position helpers.

An internal interval object or a single interval-bounds helper will parse
`start` and `end` once per operation and supply consistent Unix, NumPy, and
Python datetime representations. This removes repeated ad hoc conversions
without changing the public string-based API.

### `src/shocklink/mms/loading.py`

Owns external MMS acquisition:

- `load_mms_data` and automatic burst-to-fast fallback;
- pySPEDAS FGM, FPI, and optional MEC requests;
- expected pytplot product-name construction;
- validation that returned products overlap the interval;
- optional vector conversion with `pyspedas.cotrans`;
- coordinate-conversion error reporting.

pySPEDAS and pytplot imports remain inside functions so a base ShockLink
installation can import the MMS API without optional dependencies.

### `src/shocklink/mms/analysis.py`

Owns pure numerical outputs:

- `summarize_data`;
- `average_plotted_values`;
- scalar/vector statistics;
- names of quantities included in the default plot averages.

It consumes resolved series from `data.py` and contains no loading or
Matplotlib code.

### `src/shocklink/mms/plotting.py`

Owns figure construction:

- `plot_mms_data`;
- fixed panel ordering and panel specifications;
- scalar, vector, magnetic-field, and temperature renderers;
- component colors and compact legends;
- linked eV/K temperature axes and tick formatting;
- UTC time formatting, exact interval limits, title, date, and GSM position;
- figure sizing and subplot spacing.

Panel specifications replace closures in `plot_mms_data`. Each specification
contains the resolved product, renderer, and label information required to
draw one panel. The special derived-temperature panels are constructed
explicitly after the direct product panels.

### `src/shocklink/mms/cli.py`

Owns `parse_args` and `main`. It orchestrates public loading, analysis, and
plotting operations and retains current exit codes and user-facing errors.

Dependencies point inward toward `data.py`; feature modules do not
import the public `mms` façade. This prevents circular imports.

## Example and notebook

`examples/mms_data_analysis.py` becomes:

```python
from shocklink.mms import main


if __name__ == "__main__":
    raise SystemExit(main())
```

It verifies that an installed ShockLink package can execute the MMS workflow,
but it contains no reusable logic.

`examples/mms_example.ipynb` imports public names from `shocklink.mms`. Its
inputs, cells, output-free structure, and behavior stay unchanged.

## Data flow

```text
example / notebook
        |
        v
    shocklink.mms public façade
        |
        +--> CLI orchestration
        |
        +--> loading --> MMSData with pytplot variable handles
        |                   |
        |                   v
        +------------> series resolution and interval clipping
                            |
                            +--> summaries / averages
                            |
                            +--> plotting / derived temperatures
```

`MMSData` remains the boundary between downloading and later operations. This
preserves the existing notebook flow and allows deterministic tests to inject
pytplot data without network access.

## Error handling

- Invalid cadence and coordinate choices fail before any loader call.
- Missing optional dependencies raise the existing actionable `ImportError`
  messages at operation boundaries.
- Failed coordinate conversion retains the source variable in the error and
  chains the original exception.
- Missing products are omitted as today; no plot-able products still raise
  `ValueError`.
- CLI download and analysis failures retain separate messages and exit code 1.

Moving code must not broaden exception handling or silently replace invalid
data.

## Testing strategy

Split the current test module by responsibility:

- `tests/mms/conftest.py`: shared deterministic pytplot fixture.
- `tests/mms/test_loading.py`: cadence, pySPEDAS calls, MEC, interval product
  validation, and GSE/GSM conversion.
- `tests/mms/test_analysis.py`: summaries, averages, total temperature, finite
  values, and Earth-radius position.
- `tests/mms/test_plotting.py`: panel selection/order, labels, colors, legends,
  layout, time limits, temperature axes, and titles.
- `tests/mms/test_cli.py`: parser defaults/options and CLI outcomes.
- `tests/mms/test_public_api.py`: `shocklink.mms` exports and lazy optional
  dependency imports.

Tests will import public behavior from `shocklink.mms`. Tests for genuinely
internal algorithms may import the owning private module, but the public API
test defines the compatibility contract.

Notebook and source-layout tests will be updated to require package imports
and to continue enforcing the flat top-level source convention while allowing
the documented MMS domain-package exception. Every move uses a red-green
cycle: add the destination-facing test, observe failure, move the minimum
behavior, and run the focused suite before the next responsibility.

## Migration sequence

1. Define the public API contract and add the nested MMS package skeleton.
2. Move shared models and interval/series resolution.
3. Move loading and coordinate conversion.
4. Move summaries and averages.
5. Move plotting.
6. Move CLI orchestration and reduce the example script.
7. Update notebook and documentation imports.
8. Remove the obsolete monolithic tests and dead implementation.
9. Run focused, notebook, source-layout, and full-suite verification.

Each stage preserves a runnable test suite and is committed independently.

## Alternatives considered

### Reorganize the example file in place

This has the smallest diff but leaves reusable scientific behavior outside the
installed package and keeps one large, coupled module. It does not satisfy the
new ownership requirement.

### Keep all MMS modules flat

This avoids changing the source-layout rule but leaves six domain files mixed
with unrelated top-level modules. The explicit MMS subpackage is cleaner and
is now covered by a targeted source-layout exception test.

### Put all behavior in `src/shocklink/mms.py`

This moves ownership to the package but merely relocates the 698-line problem.
The façade plus focused private modules is preferred because it separates
dependencies and responsibilities without expanding the public namespace.
