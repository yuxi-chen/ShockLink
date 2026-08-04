# SWMF MMS Input Generator Design

## Purpose

Add a reusable generator that creates a new SWMF Earth parameter file from
`data/Param/PARAM.in.Earth`, replacing only `#STARTTIME` and `#SOLARWIND`
with values derived from an MMS interval.

## Behavior

The command accepts an MMS start and end timestamp. It loads MMS1 data in GSM
coordinates using the existing public MMS API, computes the plotted averages,
and maps them to SWMF values:

- ion density -> `SwNDim`;
- `(ion temperature + electron temperature) * 11604.51812` -> `SwTDim` in K;
- ion velocity x/y/z -> `SwUxDim`, `SwUyDim`, `SwUzDim`;
- magnetic-field x/y/z -> `SwBxDim`, `SwByDim`, `SwBzDim`.

By default, `#STARTTIME` is the UTC midpoint of the MMS interval. An optional
explicit start-time argument overrides that midpoint. The generated file is
written to a caller-selected output path; the source template is never
modified implicitly.

## Architecture

`src/shocklink/swmf.py` owns timestamp handling, MMS-to-SWMF value mapping,
marker-aware template replacement, file generation, and command-line
orchestration. The existing MMS package remains responsible for downloading
and averaging MMS data. `examples/create_swmf_input.py` is a thin executable
entry point that delegates to `shocklink.swmf.main`.

Template updates validate that each requested label occurs in its intended
section and preserve all non-target lines and formatting. Required averages
must be finite; missing products or invalid timestamps produce actionable
errors.

## Testing

Pure helper tests cover midpoint calculation, start-time formatting, value
mapping, exact section replacement, malformed templates, and preservation of
untouched content. CLI tests mock the MMS loader and verify GSM selection,
midpoint defaults, explicit overrides, output creation, and failures.
