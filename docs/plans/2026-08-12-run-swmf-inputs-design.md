# Sequential SWMF Input Runner Design

## Goal

Provide an example script that runs every `PARAM_*.in` file from a selected
directory, one at a time, from an SWMF `run/` directory and postprocesses each
successful run into a numbered result directory.

## Design

Add `examples/run_swmf_inputs.py` with a positional input-directory argument.
The script uses the current working directory as the SWMF run directory,
validates `SWMF.exe`, `PostProc.pl`, `mpiexec`, and the input files, then sorts
the PARAM files lexicographically. For each file it copies the file to
`PARAM.in`, runs `mpiexec ./SWMF.exe` with stdout and stderr written to
`runlog`, waits for success, and invokes `./PostProc.pl` with
`res/runNNN_<input-suffix>`.

Runs are strictly sequential because they share `PARAM.in`, `runlog`, and the
SWMF output area. A failed simulation or postprocessing command stops the batch
immediately and leaves the active `PARAM.in` and `runlog` in place for
diagnosis. The script creates `res/` if needed.

## Testing

Use temporary fake `mpiexec`, `SWMF.exe`, and `PostProc.pl` executables to
verify sorting, sequential execution, filename mapping, log redirection, and
postprocessing destinations without launching SWMF. Add a failure test proving
that postprocessing and later inputs are skipped after an SWMF error. Document
the command in `examples/README.md` and run the full test suite.
