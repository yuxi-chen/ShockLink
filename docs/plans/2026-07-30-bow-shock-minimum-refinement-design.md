# Bow-shock minimum-refinement design

## Goal

Reduce X-grid quantization in `get_bow_shock_surface` by refining each
interior discrete minimum of sampled `div(U)` with a bounded three-point
parabolic fit.

## API

Add `refine_minimum: bool = False` to `get_bow_shock_surface`. The default
preserves the current discrete X-location output. When enabled, each eligible
column returns the vertex of a parabola through the selected minimum and its
two immediate X neighbors.

## Algorithm

For a column with discrete minimum index `i`, use the uniformly spaced samples
`(x[i-1], f[i-1])`, `(x[i], f[i])`, and `(x[i+1], f[i+1])`, where
`f = div(U)`. With X spacing `h`, calculate:

```text
offset = h * (f[i-1] - f[i+1]) / (2 * (f[i-1] - 2*f[i] + f[i+1]))
```

and return `x[i] + offset` only if all three samples are valid and finite,
the index is interior, the centre is a strict local minimum, the curvature is
positive and finite, and the vertex lies in the neighboring bracket. Otherwise
return the original discrete X location. Invalid columns remain `NaN`.

## Rationale

The refinement improves the source of the apparent step function without
smoothing across separate Y-Z columns or assuming a global shock shape. A
bounded fallback avoids extrapolating noisy, flat, boundary, or malformed
profiles.

## Testing

Use synthetic sampled divergence profiles to verify exact sub-grid vertices,
the default discrete behavior, and fallbacks for boundary, invalid-neighbor,
non-minimum, nonpositive-curvature, and out-of-bracket cases. Update public
documentation and comments so the fitting safeguards remain understandable.
