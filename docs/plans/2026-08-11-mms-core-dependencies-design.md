# MMS Core Dependencies Design

## Goal

Install all packages required by ShockLink's MMS loading, analysis, and plotting
workflows with the standard `pip install .` command.

## Design

`pyspedas` is already a core dependency. Move `matplotlib>=3.8`, the only member
of the `mms` optional-dependency group, into `project.dependencies` and remove
the empty `mms` extra. Keep notebook applications and development tools optional
because they are not required to use the MMS API.

Update the root and examples READMEs so source-download installation uses
`pip install -e .`, MMS documentation no longer mentions an extra, and the
installed package remains linked to repository-level data files.

## Verification

Update the package-metadata test to require both `pyspedas` and `matplotlib` as
core dependencies and to reject an `mms` extra. Run the focused metadata and
documentation tests, search for stale `.[mms]` instructions, then run the full
test suite.
