# Simplified Shock Connection Notebook Design

## Goal

Make `examples/shock_connection.ipynb` easier to configure and read while
preserving its complete bow-shock-to-MMS connection workflow.

## Design

Use the new default transverse axes when extracting the bow-shock surface.
Replace the duplicated Y and Z arrays and their range/resolution configuration
with one `SURFACE_AXIS` array used only by normal calculation and connectivity.
Keep the analysis stages, plots, and useful diagnostics intact.

Clean all saved code-cell outputs and execution counts. Restore the documented
portable input path, `../data/3d.dat`, so the notebook remains a clean source
artifact and satisfies its existing portability contract.

## Testing

Strengthen the notebook source test to require the single-axis form and omitted
surface-extraction axis arguments. Run all notebook tests plus the full suite,
allowing only failures already established as unrelated before this cleanup.
