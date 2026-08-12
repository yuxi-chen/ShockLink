# Simplify OMNI/MMS data flow

## Goal

Keep only the observations required to generate the SWMF input and make one
data-layer operation responsible for producing the total-temperature series.

## Design

The default loader requests MMS magnetic field, electron density, ion velocity,
and spacecraft position, plus OMNI proton temperature. It does not download MMS
ion density, electron velocity, or MMS temperatures. The generic `MMSData`
mapping remains capable of carrying caller-provided series.

The data layer maps electron density to ion density under charge neutrality. It
also cleans OMNI proton temperature, doubles valid samples under the assumption
that electron and ion temperatures are equal, and inserts the 100,000 K total
temperature fallback when no valid OMNI samples remain. Plotting, summaries,
and SWMF generation consume that single normalized series.

OMNI is loaded once per interval and reused if automatic MMS cadence selection
falls back from burst to fast. Obsolete MMS-temperature calculation and plotting
helpers are removed. Tests verify the smaller download request, cadence fallback,
normalization, plotting, and averaging.
