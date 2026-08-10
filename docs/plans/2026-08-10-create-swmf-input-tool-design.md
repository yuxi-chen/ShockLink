# Executable SWMF Input Tool Design

**Goal:** Move the SWMF input generator entry point from `examples/` to
`tools/`, make it directly executable, and document its command-line use.

## Design

Replace `examples/create_swmf_input.py` with an executable
`tools/create_swmf_input.py`. The tool remains a thin entry point that imports
and calls `shocklink.mms_swmf.main()`, keeping data loading, averaging, input
generation, and error handling in the reusable package module. Add a Unix
shebang and a concise module docstring, and store the new file with executable
permissions.

Enhance the parser in `shocklink.mms_swmf` with clear help for every argument,
raw-description formatting, and examples showing the required MMS interval and
output, selection of a probe and data mode, and overrides for the template and
SWMF start time. The command's existing defaults and generation behavior remain
unchanged.

Add a README section describing the optional MMS installation, generated SWMF
sections, default template, and direct `./tools/create_swmf_input.py` usage.
Replace the old example-entry-point test with tool tests that verify the new
location, executable bit, shebang, thin delegation, and useful `-h` output.
Existing package tests continue to cover input generation and runtime errors.

Historical planning documents retain their original paths as records of the
earlier implementation.
