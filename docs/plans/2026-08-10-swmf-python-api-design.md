# SWMF Python API Design

**Goal:** Expose the MMS-to-SWMF input workflow as a reusable Python function
for scripts and notebooks while retaining the existing CLI.

## Design

Add `shocklink.mms_swmf.create_swmf_input()` with the complete CLI option set as
keyword arguments:

```python
create_swmf_input(
    mms_start: str,
    mms_end: str,
    *,
    output: str | Path | None = None,
    input: str | Path = _DEFAULT_TEMPLATE,
    start_time: str | datetime | None = None,
    probe: int = 1,
    mode: Literal["auto", "brst", "fast"] = "auto",
) -> Path
```

The function owns MMS loading, averaging, timestamp selection, default output
naming, template generation, and validation. It returns the generated output
path and lets exceptions propagate to Python callers. `main()` becomes a thin
argument-parsing/error-reporting adapter that calls the function and returns its
existing process status. The default template remains repository-relative via
the existing absolute module-derived path; explicit `input` values are
unchanged.

Document both direct CLI and Python/notebook usage. Tests will cover all options,
default and explicit output names, datetime/string start-time inputs, return
value, and CLI delegation/error behavior.
