# Default SWMF Output Name Design

**Goal:** Give the SWMF input generator a deterministic timestamp-based output
filename when `--output` is omitted.

## Design

Make `--output` optional. After the MMS data are averaged and the effective
SWMF start time is selected, derive the default output path as
`PARAM_YYYYMMDD_HHMMSS.in` using that UTC start time. The effective time is the
explicit `--start-time` when provided; otherwise it is the MMS interval
midpoint. An explicit `--output` remains unchanged.

The parser help and examples will show that `--output` is optional and explain
the generated filename. Tests will cover midpoint-derived naming, explicit
start-time naming, and preservation of an explicitly supplied output path.
Existing template resolution and SWMF generation behavior remain unchanged.
