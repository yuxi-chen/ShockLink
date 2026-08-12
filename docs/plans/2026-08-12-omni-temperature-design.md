# OMNI temperature and charge-neutral MMS inputs

## Goal

Use MMS electron density as the ion-density estimate under charge neutrality,
and replace MMS ion/electron temperature products with cleaned OMNI proton
temperature in plots and SWMF input generation.

## Design

The MMS loader requests OMNI one-minute data and records its `T` product as
`omni_temperature`. The MMS loader no longer treats MMS ion density or
temperature moments as required products. The resolved display series maps
`electron_density` to the public `ion_density` product so downstream summaries
and SWMF generation retain their existing interfaces while making the
assumption explicit in labels and documentation.

OMNI temperatures are filtered to finite values, metadata-defined fill values
and valid bounds, and numeric all-9 placeholders (for example `99999`,
`9999.9`, and `9999999`). The cleaned series is the only temperature panel and
its mean is doubled to represent equal ion and electron contributions and is
used as kelvin in SWMF input generation. If the requested
interval has no valid OMNI samples, loading/averaging raises a clear error;
there is no MMS-temperature fallback.

Tests cover OMNI loader requests, density mapping, fill-value cleaning,
plot-panel structure, interval averages, and the no-valid-temperature error.
