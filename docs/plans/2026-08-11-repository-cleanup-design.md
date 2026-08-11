# Repository cleanup design

## Goal

Reduce maintenance overhead without removing the public scientific workflow.
The cleanup consolidates lasting algorithm documentation, merges overlapping
architecture/example tests, and removes historical planning artifacts.

## Decisions

- Preserve the public `src/`, `tools/`, and `examples/` interfaces.
- Keep scientific behavior tests split by domain; merge only redundant
  repository-layout, documentation, notebook, and CLI contract checks.
- Replace the two overlapping workflow guides with one maintained
  `docs/algorithms.md` guide that links each algorithm to its implementation.
- Delete `docs/plans/` after the implementation is complete. The design and
  implementation plan are temporary process artifacts, not user-facing docs.

## Verification

Run the focused merged tests while editing, then run the complete test suite,
lint/format checks, and a package build before merging into `main`.
