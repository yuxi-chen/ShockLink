# MMS plot location, averages, and temperature units design

## Goal

Add the selected MMS spacecraft's interval-averaged GSM location to the
figure title/subtitle, return means for the variables actually plotted, and
keep total temperatures in eV on the left-hand y-axis.

## Data and architecture

The default pySPEDAS loader will optionally request the MEC ephemeris product
`mmsN_mec_r_gsm` for the selected probe and cadence. The position is retained
as a named series in `MMSData`, filtered to the requested interval like the
science products, and never receives a plot panel. Missing MEC data will not
prevent the FGM/FPI plot from being produced.

The title/subtitle will include the finite mean position converted from the MEC
product's km units to Earth radii, for example
`MMS1 position (GSM): (1.23, -0.45, 0.11) $R_E$`. The annotation is omitted
when no finite position samples are available.

The existing `summarize_data` API remains available for full finite-value
statistics. A new `average_plotted_values(data)` API returns only the means of
the products shown by `plot_mms_data`: magnetic-field X/Y/Z and magnitude, ion
density, ion-velocity X/Y/Z, and plotted total ion/electron temperatures. The
CLI and notebook will display this result.

Total temperature remains `(T_parallel + 2*T_perpendicular) / 3` in eV at the
data boundary and in the plot. Temperature tick labels and y-axis labels stay
on the left, using `$T_i$ [eV]` / `$T_e$ [eV]`.

## Alternatives

Native MEC GSM position is preferred over transforming a GSE position because
MEC already publishes the required geocentric frame. An external ephemeris
service is rejected because it adds another network dependency and failure
mode.

## Failure handling and compatibility

MEC loading is optional. A missing or empty position series only removes the
position annotation. Invalid or non-finite position samples are ignored when
computing the mean. Existing GSE/GSM vector selection, cadence fallback,
temperature formula, and existing summary statistics remain unchanged.

## Testing

Tests will mock MEC and pytplot data without network access. They will verify
MEC variable selection and interval filtering, GSM position means and title
annotation with product units, plotted-variable mean keys/values, eV
temperature values on left-side axes, missing-MEC tolerance, and unchanged
existing plot panels.
