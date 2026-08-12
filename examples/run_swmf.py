#!/usr/bin/env python
"""Run and postprocess a directory of SWMF PARAM inputs sequentially."""

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


# Edit this path before running the script. It is relative to the SWMF run/
# directory from which this script is executed.
INPUT_DIRECTORY = Path("param-files")

input_directory = (Path.cwd() / INPUT_DIRECTORY).resolve()
run_directory = Path.cwd()
if not input_directory.is_dir():
    print(f"error: input directory was not found: {input_directory}", file=sys.stderr)
    sys.exit(1)

for executable in (run_directory / "SWMF.exe", run_directory / "PostProc.pl"):
    if not executable.is_file() or not os.access(executable, os.X_OK):
        print(f"error: executable was not found: {executable}", file=sys.stderr)
        sys.exit(1)
if shutil.which("mpiexec") is None:
    print("error: mpiexec was not found on PATH", file=sys.stderr)
    sys.exit(1)

param_files = sorted(input_directory.glob("PARAM_*.in"))
if not param_files:
    print(
        f"error: no PARAM_*.in files were found in {input_directory}", file=sys.stderr
    )
    sys.exit(1)

result_directory = run_directory / "res"
highest_run = 0
if result_directory.is_dir():
    for path in result_directory.iterdir():
        match = re.match(r"^run(\d+)_", path.name)
        if path.is_dir() and match:
            highest_run = max(highest_run, int(match.group(1)))

jobs = []
for number, param_file in enumerate(param_files, start=highest_run + 1):
    suffix = param_file.name[len("PARAM_") : -len(".in")]
    jobs.append((param_file, Path("res") / f"run{number:03d}_{suffix}"))

for _, result in jobs:
    if (run_directory / result).exists():
        print(
            f"error: result destination already exists: {run_directory / result}",
            file=sys.stderr,
        )
        sys.exit(1)

result_directory.mkdir(exist_ok=True)
for number, (param_file, result) in enumerate(jobs, start=1):
    print(f"[{number}/{len(jobs)}] Running {param_file.name}")
    shutil.copy2(param_file, run_directory / "PARAM.in")

    with (run_directory / "runlog").open("w") as runlog:
        subprocess.run(
            ["mpiexec", "./SWMF.exe"],
            cwd=run_directory,
            stdout=runlog,
            stderr=subprocess.STDOUT,
            check=True,
        )

    print(f"[{number}/{len(jobs)}] Postprocessing to {result}")
    subprocess.run(["./PostProc.pl", str(result)], cwd=run_directory, check=True)
