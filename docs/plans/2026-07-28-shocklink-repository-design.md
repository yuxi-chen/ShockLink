# ShockLink Repository Design

## Purpose

ShockLink is a Python package for analyzing three-dimensional magnetohydrodynamic
(MHD) magnetosphere simulations and determining how magnetic field lines connect
to the bow shock. It combines a normal, pip-installable scientific Python core
with optional ParaView pipelines executed through `pvpython`.

The distribution and import package are both named `shocklink`; the project is
presented as **ShockLink**.

## Architecture

ShockLink uses a modular core with a thin ParaView integration layer. Scientific
data models, geometry, connectivity, configuration, and result records must not
import ParaView. ParaView-specific readers, filters, tracing pipelines, and
export helpers live under `shocklink.paraview` and are loaded only when used.

This separation allows:

- `pip install shocklink` to work without ParaView;
- core unit tests to run in ordinary Python environments;
- ParaView analyses to run with `pvpython`; and
- future data backends to be added without rewriting the analysis model.

## Package Components

```text
src/shocklink/
├── core/          # Shared data models and coordinate conventions
├── io/            # Simulation-data interfaces
├── fieldlines/    # Seed definitions and field-line trace results
├── bowshock/      # Shock surfaces and intersection detection
├── connectivity/  # Field-line-to-shock classification
├── paraview/      # Optional ParaView readers and pipelines
├── cli/           # Command-line entry points
└── config.py      # Validated analysis configuration
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
- `paraview` contains optional runtime checks, readers, tracing pipelines, and
  export helpers.
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

Importing `shocklink` must never require ParaView. Attempting a ParaView-specific
operation outside ParaView will raise a clear backend error explaining that the
operation should be run with `pvpython`.

CLI commands return nonzero exit codes for invalid input and print concise,
actionable messages without exposing internal tracebacks by default.

## Testing and Verification

Core tests use small synthetic datasets and cover:

- configuration parsing and validation;
- data-model invariants;
- geometry and intersection behavior;
- connectivity classification;
- CLI validation behavior; and
- ParaView import isolation.

ParaView integration tests are marked separately and skipped when ParaView is
unavailable. Ordinary CI runs formatting, linting, type checking, unit tests,
and package builds without installing ParaView.

The wheel and source distribution are inspected to ensure required package data,
type information, and documentation are included.

## Repository Documentation

The scaffold includes:

- a README with project scope, installation, and quick-start examples;
- architecture and scientific-convention documentation;
- a documented TOML configuration example;
- a small synthetic workflow example;
- ParaView and `pvpython` usage guidance;
- contributor setup and test commands;
- license, changelog, and citation metadata; and
- CI configuration suitable for a future PyPI release.

Publishing credentials and an automatic production release are intentionally
outside the initial scaffold.
