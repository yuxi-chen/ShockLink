# Sequential SWMF Input Runner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a tested example script that sequentially runs and postprocesses a directory of SWMF PARAM inputs.

**Architecture:** Keep orchestration in a standalone Python example with a callable function and a small CLI. Use real subprocesses backed by fake test executables to verify command order and filesystem behavior.

**Tech Stack:** Python standard library, pytest, POSIX executable test fixtures, Markdown.

---

### Task 1: Specify sequential orchestration

**Files:**
- Create: `tests/test_run_swmf_inputs.py`

**Step 1:** Add a test that creates PARAM files out of order plus fake
`mpiexec`, `SWMF.exe`, and `PostProc.pl` executables.

**Step 2:** Assert that simulations and postprocessing alternate in sorted
order, result names use `run001`, `run002`, and each result receives its
corresponding `runlog`.

**Step 3:** Run `PYTHONPATH=src pytest -q tests/test_run_swmf_inputs.py` and
confirm failure because `examples/run_swmf_inputs.py` does not exist.

### Task 2: Implement the runner

**Files:**
- Create: `examples/run_swmf_inputs.py`
- Modify: `tests/test_run_swmf_inputs.py`

**Step 1:** Implement PARAM discovery, validation, copying, sequential SWMF
execution, log redirection, numbered postprocessing, and CLI parsing.

**Step 2:** Add a failure test proving an SWMF error stops before
postprocessing or subsequent inputs.

**Step 3:** Run `PYTHONPATH=src pytest -q tests/test_run_swmf_inputs.py` and
confirm all runner tests pass.

### Task 3: Document and verify

**Files:**
- Modify: `examples/README.md`
- Modify: `tests/test_examples.py`

**Step 1:** Document invocation from an SWMF `run/` directory, ordering,
result naming, sequential behavior, and failure behavior.

**Step 2:** Add an example-structure test checking that the script is
executable and offers useful `--help` output.

**Step 3:** Run focused tests, then `PYTHONPATH=src pytest -q` and
`git diff --check`.

**Step 4:** Commit, review, merge into `main`, rerun the full suite, and remove
the temporary worktree.
