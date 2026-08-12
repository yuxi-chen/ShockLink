# SWMF runner rename and batch connection processing

## Goal

Bring the documentation up to date, give the sequential SWMF runner a shorter
name, and provide a small example script for processing every completed SWMF
result directory.

## Design

Rename `examples/run_swmf_inputs.py` to `examples/run_swmf.py`, preserving its
existing sequential execution and continuation behavior. Rename its focused
test module and update all current documentation references.

Add `examples/process_swmf_results.py`. The script scans sorted immediate
children matching `res/runNNN*`. For each run, it uses `runNNN*/PARAM.in` and
recursively discovers `*.dat` and `*.vtm`; the lexicographically greatest full
relative filename is selected as the latest simulation output. Missing inputs
and processing exceptions are reported to standard error and skipped. The
script calls the public `build_mms_bow_shock_connection()` and
`save_mms_bow_shock_connection_plots()` APIs directly, writing figures into
the same run directory with the established simulation-stem output names.

Update `README.md`, `examples/README.md`, and `docs/algorithms.md` for the
charge-neutral density, cleaned/doubled OMNI temperature, 100,000 K fallback,
runner rename, and batch result workflow. Correct stale explanatory text in
the MMS example notebook without adding notebook outputs.

Tests cover the rename, latest-file selection, successful API calls, per-run
skips, exception continuation, output location, executability, and current
documentation references.
