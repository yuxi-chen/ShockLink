# MMS dual temperature-axis design

## Goal

Show each total-temperature line once in eV while labeling the same physical
scale in kelvin on a secondary right y-axis.

## Approach

Keep the current temperature values and line data in eV. After drawing each
ion/electron temperature line, attach a Matplotlib `secondary_yaxis` to the
right side of the same panel. Its forward and inverse functions are:

```python
T_K = T_eV * 11604.51812
T_eV = T_K / 11604.51812
```

The left axis remains `$T_i$ [eV]` or `$T_e$ [eV]`; the linked right axis is
`$T_i$ [K]` or `$T_e$ [K]`. Panning, zooming, and automatic y-limits remain
synchronized because the right axis is derived from the left axis. No second
line or converted temperature array is plotted, and plotted averages remain
in eV.

## Alternatives

A manually synchronized `twinx` axis could show the same conversion, but it
requires callbacks or repeated limit updates. Plotting a duplicate K-valued
line on `twinx` would visually overlap the eV line and violates the requirement
that there be one line. `secondary_yaxis` directly models a constant unit
conversion and is therefore preferred.

## Compatibility and tests

All data loading, total-temperature calculation, line colors, averages, and
left-axis behavior remain unchanged. Tests will verify the conversion in both
directions, unchanged eV line data, left/right labels, one temperature line per
panel, and the existing panel count. Notebook and README text will describe
the linked dual-unit axes.
