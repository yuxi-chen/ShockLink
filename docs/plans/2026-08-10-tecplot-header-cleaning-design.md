# Tecplot Header Cleaning Design

## Goal

Make Tecplot files whose coordinate variables include units, such as `"X [R]"`, readable by VTK before converting them to VTM.

## Design

Move the existing `data/clean_dat.py` utility into `tools/clean_dat.py` and expose its `clean_dat()` function for reuse. The function scans the Tecplot header for `VARIABLES`, removes bracketed unit text, shortens only the `X`, `Y`, and `Z` coordinate names to those exact names, and pads the replacement so it occupies the same number of characters as the original line. It then overwrites only that header line in place; zone declarations and numerical records are not read, rewritten, or normalized.

`tools/convert_dat_to_vtm.py` will import and call `clean_dat(source)` after validating the source and extracting its simulation timestamp, but before calling `pyvista.read`. Cleaning is permanent and happens before conversion, so the source remains cleaned if reading or writing VTK later fails. `--delete-input` continues to delete the cleaned source only after VTM output succeeds.

## Error handling

The cleaner will reject nonexistent files, non-DAT paths, files without a `VARIABLES` declaration in the Tecplot header, and rewrites that would be longer than the original line. It will preserve the original newline convention and report failures through a dedicated exception. The converter will translate cleaner failures into its existing `ConversionError` interface.

## Verification

Tests will demonstrate the red/green behavior for in-place header cleaning, byte-length preservation, unchanged zone/data content, converter invocation order, correct nonzero VTK geometry for unit-bearing coordinates, and input retention after downstream conversion failure. Existing converter and full project tests will then be run.
