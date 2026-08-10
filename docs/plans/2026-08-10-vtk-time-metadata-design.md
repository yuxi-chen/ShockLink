# VTK Time Metadata Design

**Goal:** Preserve the simulation timestamp from a Tecplot `TITLE` header in the converted VTM dataset.

## Metadata contract

The converter will parse a BATSRUS-style timestamp such as
`TITLE="BATSRUS: 3D Data,2023/12/16 11:30:00.000"` and normalize it to an ISO-8601 UTC string:

```text
2023-12-16T11:30:00.000+00:00
```

It will store that value in the root `pyvista.MultiBlock.field_data["time_event"]`. VTM reloads will therefore expose the timestamp without changing any zone geometry, arrays, or names.

## Error handling

The converter will reject a missing or malformed BATSRUS timestamp before invoking PyVista. This prevents a successful VTM conversion that silently loses the requested simulation-time metadata. Existing read/write and input-deletion safety behavior remains unchanged.

## Testing and documentation

The converter tests will include a timestamped two-zone fixture and verify the exact normalized value after reloading the generated VTM. Missing and invalid timestamps will be tested as failures, and the README will document the `time_event` field-data key.
