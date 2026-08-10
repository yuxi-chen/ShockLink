# Shock Angle Contour Styling Design

## Goal

Update `plot_shock_angle_contour` so its output closely matches the publication-style `plot_2d_theta` visualization in `/Users/yuxichen/Research/Earth_shock/scripts/shock.py`, while preserving ShockLink's composable plotting API and data-validation behavior.

## Design

The function will use dense filled contours over the existing fixed 0–90 degree domain, with the reference colormap, larger publication-oriented typography, thicker ticks and contour lines, a degree-labelled colorbar, and dashed 45°/50° isolines. The selected shock intersection will be highlighted in red and labeled with its local angle. The plot will also include MMS position, averaged magnetic field, and full intersection metadata beneath the axes.

When no limits are supplied, Y and Z limits will be selected symmetrically from ±15, ±20, ±25, or ±28 based on the selected intersection location, matching the reference behavior. Optional `cmap`, `yrange`, and `zrange` arguments will support controlled customization. A caller-provided axes remains untouched in size and global style; only newly-created figures use the reference 10×8-inch size. Missing coverage remains masked, custom contour-level validation remains enforced, and the function continues returning `(figure, axes)`.

## Verification

Headless Matplotlib tests will verify the new default styling, adaptive limits, metadata text, red intersection annotation, optional explicit ranges, dashed threshold contours, custom colormap, and compatibility with a supplied axes. Existing masking, validation, and return-value tests will remain intact.
