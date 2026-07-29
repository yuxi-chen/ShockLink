# ShockLink Repository Design

## Purpose

ShockLink is a Python package for analyzing three-dimensional magnetohydrodynamic
(MHD) magnetosphere simulations and determining how magnetic field lines connect
to the bow shock. It uses PyVista to read and normalize three-dimensional
simulation output inside a normal, pip-installable scientific Python package.

The distribution and import package are both named `shocklink`; the project is
presented as **ShockLink**.

## Architecture

ShockLink uses a modular scientific core with PyVista-based data readers.
Scientific data models, geometry, connectivity, configuration, and result
records remain independent from specific simulation formats. Tecplot-specific
loading and normalization live in `shocklink.tecplot`.

This separation allows:

- `pip install shocklink` to provide its supported 3D reader;
- core unit tests to run with small synthetic PyVista grids;
- BATSRUS Tecplot data to become geometry-ready PyVista grids; and
- future data backends to be added without rewriting the analysis model.

## Package Components

```text
src/shocklink/
├── core.py          # Shared data models and coordinate conventions
├── io.py            # Simulation-data interfaces
├── fieldlines.py    # Seed definitions and field-line trace results
├── bowshock.py      # Shock surfaces and intersection detection
├── connectivity.py  # Field-line-to-shock classification
├── tecplot.py       # PyVista-based Tecplot reader and normalization
├── cli.py           # Command-line entry points
└── config.py        # Validated analysis configuration
```

Responsibilities:

- `core` owns dataset metadata, coordinate-system declarations, points,
  polylines, surfaces, and analysis result records.
- `io` defines backend-independent dataset interfaces and leaves room for
  lightweight VTK support.
- `fieldlines` defines seed specifications and backend-independent trace
  results.
- `bowshock` represents bow-shock surfaces and exposes line/surface
  intersection interfaces.
- `connectivity` classifies field lines as connected, not connected, ambiguous,
  or incomplete.
- `tecplot` reads BATSRUS Tecplot output, repairs coordinates, and constructs
  magnetic-field and velocity vector arrays.
- `cli` exposes initial `shocklink analyze` and `shocklink validate` commands.
- `config.py` parses and validates TOML analysis configuration.

The first scaffold will define stable boundaries and representative behavior. It
will not claim complete scientific algorithms before exact input formats,
coordinate conventions, and shock-identification methods are specified.

## Data Flow

```text
3D MHD output
  → load dataset
  → identify or load bow-shock surface
  → seed and trace magnetic field lines
  → detect line/surface intersections
  → classify connectivity
  → export tables, geometry, and provenance metadata
```

Analysis results record their input path, selected variables, coordinate system,
numeric tolerances, and ShockLink version so results can be reproduced.

## Error Handling

ShockLink defines focused exception types for configuration errors, invalid or
missing simulation arrays, unsupported coordinate systems, malformed surfaces,
and unavailable optional backends.

Tecplot and PyVista read failures are converted into dataset errors with the
source path and actionable array or zone context.

CLI commands return nonzero exit codes for invalid input and print concise,
actionable messages without exposing internal tracebacks by default.

## Testing and Verification

Core tests use small synthetic datasets and cover:

- configuration parsing and validation;
- data-model invariants;
- geometry and intersection behavior;
- connectivity classification;
- CLI validation behavior; and
- Tecplot geometry and vector normalization.

Large-sample Tecplot integration tests are marked separately and skipped unless
the local dataset is explicitly enabled. Ordinary CI uses synthetic PyVista
grids for reader tests.

The wheel and source distribution are inspected to ensure required package data,
type information, and documentation are included.

## Repository Documentation

The scaffold includes:

- a README with project scope, installation, and quick-start examples;
- architecture and scientific-convention documentation;
- a documented TOML configuration example;
- a small synthetic workflow example;
- PyVista and Tecplot usage guidance;
- contributor setup and test commands;
- license, changelog, and citation metadata; and
- CI configuration suitable for a future PyPI release.

Publishing credentials and an automatic production release are intentionally
outside the initial scaffold.
