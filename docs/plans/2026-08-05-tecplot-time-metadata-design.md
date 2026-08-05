# Tecplot Time Metadata Design

## Goal

Preserve the BATSRUS event timestamp embedded in a Tecplot `.dat` header when
`read_tecplot` loads the dataset, so later PyVista-based processing can recover
the time from the returned grid.

## Design

Before calling PyVista, `read_tecplot` will inspect the small text header and
extract the timestamp at the end of the `TITLE` line, such as
`2023/12/16 11:30:00.000`. A private helper will stop at the `ZONE` declaration
instead of reading the numerical body. It will normalize the slash-separated
BATSRUS timestamp through the existing `shocklink.utilities.parse_datetime`
function and serialize it as an ISO-8601 UTC value with millisecond precision.

After PyVista returns and the single zone is normalized, the reader will attach
the value to `grid.field_data["time_event"]`. This keeps the existing
`UnstructuredGrid` return type and places the timestamp in PyVista dataset
metadata, where downstream filters and file writers can preserve it. Callers
can recover the scalar string with
`str(np.asarray(grid.field_data["time_event"]).reshape(-1)[0])` and parse it
with `parse_datetime` when a Python `datetime` is needed.

The timestamp is required because the supported BATSRUS input contract says it
is present in the header. A missing `TITLE` timestamp, an invalid calendar
value, or a header read failure will raise `DatasetError` with the source path.
Existing path validation, PyVista exception wrapping, geometry replacement,
and vector construction remain unchanged.

## Testing

Unit tests will use real text in the temporary `.dat` fixture while continuing
to monkeypatch `pyvista.read`. They will verify exact normalized metadata for a
valid millisecond timestamp and actionable failures for missing and malformed
timestamps. The large sample integration test will assert that `data/3d.dat`
produces `2023-12-16T11:30:00.000+00:00`. The focused Tecplot tests and then the
full suite will protect the current reader behavior.
