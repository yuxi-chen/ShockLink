# Tecplot DAT to VTM Converter Design

**Goal:** Add a standalone tool that converts an ASCII Tecplot `.dat` file to a VTK multiblock `.vtm` file while preserving every zone exactly as PyVista reads it.

## Scope

The tool will live at `tools/convert_dat_to_vtm.py`. It will perform only a PyVista read followed by a multiblock save. It will not normalize coordinates, combine zones, infer AMR hierarchy, filter data, or add derived arrays.

The command-line interface will be:

```bash
python tools/convert_dat_to_vtm.py input.dat [output.vtm] [--delete-input]
```

When the output argument is omitted, the tool will use the input path with its suffix replaced by `.vtm`. The optional `--delete-input` flag will remove the source `.dat` only after the read and save complete successfully. Any conversion failure leaves the source untouched.

## Data flow

1. Parse and validate the input and output paths.
2. Call `pyvista.read(input_path)`.
3. Require the returned object to be `pyvista.MultiBlock`, since each Tecplot zone must remain a separate block.
4. Call `dataset.save(output_path)` with no data transformation.
5. If requested, delete the source `.dat` after the save returns successfully.
6. Report the output path and number of blocks.

The VTM metadata file and all sidecar files written by VTK must remain together for later reading.

## Error handling

The tool will reject missing inputs, non-`.dat` inputs, non-`.vtm` outputs, an output path equal to the input path, and non-multiblock reader results. PyVista read/write exceptions will be converted to concise command-line errors with a nonzero exit status. Input deletion is attempted only after a successful save.

## Testing

Tests will use a small two-zone ASCII Tecplot fixture and exercise the script through its callable conversion function and command-line entry point. They will reload the generated VTM and verify the number/order of blocks, block names, dataset types, geometry, and arrays. Separate tests will cover default and explicit output names, successful input deletion, and preservation of the input when reading or writing fails.

## Documentation

The repository README will document the command, default output naming, the opt-in deletion flag, and the requirement to retain the `.vtm` sidecar files.
