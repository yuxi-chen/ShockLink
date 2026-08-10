# Executable DAT-to-VTM Tool Design

**Goal:** Allow the existing Tecplot converter to run directly as a Unix-style executable and make `-h` show practical command examples.

## Design

Add `#!/usr/bin/env python3` as the first line of `tools/convert_dat_to_vtm.py` and store the file with executable permissions. Keep the existing Python entry point and conversion behavior unchanged.

Configure `argparse.ArgumentParser` with `RawDescriptionHelpFormatter` and an epilog containing examples for default output naming, an explicit output path, and `--delete-input`. Both `-h` and `--help` remain provided by argparse and exit successfully without attempting a conversion.

Tests will invoke the tool directly rather than through `sys.executable`, assert that the repository file is executable, and verify that `-h` displays the usage line, all options, and the examples. Existing conversion tests will continue to prove the executable path performs the same raw multiblock conversion.
