# Continue SWMF Run Numbers Design

## Goal

Continue new SWMF result numbering after the highest existing numbered result
directory instead of restarting at `run001` for every invocation.

## Design

Before building jobs, scan the run directory's `res/` directory for directories
whose names match `run<digits>_*`. Parse the numeric prefix, take the maximum,
and assign the first new result `maximum + 1`; use `001` when no matching
directory exists. Ignore files and unrelated directory names. Keep a minimum
width of three digits, allowing numbering above 999 without truncation.

PARAM inputs remain lexicographically sorted and receive consecutive result
numbers. Existing-destination preflight remains in place as a final safety
check.

## Testing and Documentation

Replace the obsolete collision test with a test containing non-contiguous
existing results (for example `run001_*` and `run005_*`) and verify new jobs use
`run006_*` and `run007_*`. Verify unrelated files and directories do not affect
numbering. Update `examples/README.md` and run focused and full test suites.
