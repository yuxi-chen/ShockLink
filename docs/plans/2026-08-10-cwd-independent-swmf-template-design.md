# CWD-Independent SWMF Template Design

**Goal:** Make the default `PARAM.in.Earth` template available when the SWMF
input tool is executed outside the ShockGeo repository directory.

## Design

The failure occurs because `shocklink.mms_swmf.parse_args()` returns the literal
relative default `data/Param/PARAM.in.Earth`. Python resolves that path beneath
the caller's current working directory, so the bundled repository template is
not found when the command starts elsewhere.

Define the default template as an absolute `Path` derived from the location of
`src/shocklink/mms_swmf.py`, whose repository root is two parent directories
above the module. Use that path only as the argparse default. An explicitly
provided relative `--input` remains relative to the caller's current directory,
and output path behavior remains unchanged.

Tests will change the process working directory and verify that parsing without
`--input` still selects the repository template. A complementary test will
verify that an explicit relative template is preserved. Existing main-workflow
tests will confirm that the resolved default reaches `generate_param_file()`,
and command help will continue to describe the repository template without
exposing a machine-specific absolute path.
