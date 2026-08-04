# SWMF Module Boundary Refactor Design

## Purpose

Separate generic SWMF parameter-file generation from MMS acquisition and
analysis. `shocklink.swmf` will receive an already calculated start time and
solar-wind state; it will not import MMS functions, interpret MMS average
names, calculate an MMS interval midpoint, or own the command-line workflow.

This design supersedes the module boundaries in
`2026-08-04-swmf-input-generator-design.md` while preserving the generator's
CLI and output behavior.

## Dependency direction

```text
shocklink.utilities
        ^
        |
shocklink.mms.data          shocklink.swmf
        ^                         ^
        |                         |
        +---- shocklink.mms_swmf -+
                       ^
                       |
          examples/create_swmf_input.py
```

`shocklink.mms_swmf` is the only package module that understands both MMS and
SWMF. Neither `shocklink.swmf` nor `shocklink.utilities` imports MMS.

## Modules

### `src/shocklink/utilities.py`

Own shared UTC time helpers:

- `parse_datetime(value: str) -> datetime` parses ISO-like strings, treats
  naive values as UTC, converts aware values to UTC, and reports invalid
  values clearly.
- `midpoint_datetime(start: datetime, end: datetime) -> datetime` returns the
  midpoint and rejects reversed intervals.

`src/shocklink/mms/data.py` will use `parse_datetime` instead of maintaining a
private duplicate parser. Its public behavior remains unchanged.

### `src/shocklink/swmf.py`

Own only the SWMF representation and writer:

- `SolarWindValues`;
- validation that all supplied SWMF values are finite;
- marker-aware replacement of `#STARTTIME` and `#SOLARWIND`;
- input/output file handling with line-ending preservation.

The module accepts a timezone-aware or naive `datetime` and a fully populated
`SolarWindValues`. It contains no MMS imports, MMS average-key mapping,
temperature conversion, interval parsing, `argparse`, or CLI `main`.

### `src/shocklink/mms_swmf.py`

Own the integration workflow:

- map the MMS averages to `SolarWindValues`;
- calculate `(ion_temperature + electron_temperature) * 11604.51812` K;
- parse the MMS bounds and choose their midpoint unless `--start-time`
  overrides it;
- load MMS data in GSM coordinates;
- define CLI arguments and error handling;
- pass the calculated `datetime` and `SolarWindValues` to
  `swmf.generate_param_file`.

### `examples/create_swmf_input.py`

Remain a thin executable entry point, importing only `main` from
`shocklink.mms_swmf`.

## Data flow

1. The CLI parses the MMS interval and output options.
2. `mms_swmf` loads and averages MMS data in GSM.
3. `mms_swmf` converts the averages into `SolarWindValues`.
4. `utilities` parses the requested times and calculates the default midpoint.
5. `mms_swmf` passes both completed values into `swmf.generate_param_file`.
6. `swmf` updates the template without knowing where either value originated.

## Error handling

- Invalid timestamps and reversed intervals fail before file generation.
- Missing or nonfinite MMS averages identify the offending average name.
- A directly constructed `SolarWindValues` containing nonfinite data is also
  rejected at the SWMF boundary.
- MMS download/analysis and file errors retain the existing CLI prefix and
  nonzero return code.
- Malformed `#STARTTIME` or `#SOLARWIND` sections retain the existing detailed
  validation errors.

## Testing

- `tests/test_utilities.py` covers UTC parsing, timezone conversion, midpoint
  calculation, fractional seconds, and reversed intervals.
- `tests/test_swmf.py` covers only SWMF value validation and template/file
  generation.
- `tests/test_mms_swmf.py` covers MMS average mapping, temperature conversion,
  GSM loading, midpoint/override selection, CLI success, and CLI failure.
- A module-boundary test asserts that `shocklink.swmf` does not import MMS or
  the integration module.

The existing uncommitted edit to `data/Param/PARAM.in.Earth` is outside the
refactor and must not be modified or overwritten.
