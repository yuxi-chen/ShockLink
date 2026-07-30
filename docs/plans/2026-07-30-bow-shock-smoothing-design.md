# Bow-shock surface smoothing design

Add `smooth_bow_shock_surface(surface_x, sigma=1.0, preserve_nan=True)`.
It will use SciPy normalized Gaussian convolution: filter the finite values and
their validity weights separately, then divide. This prevents NaN gaps from
being treated as zeros. By default, original NaN locations stay NaN; the input
array is not modified. `sigma` is in Y-Z grid cells and may be a scalar or
two-component `(y_sigma, z_sigma)` value.

Tests will cover smoothing a local perturbation, NaN-aware behavior, retained
NaNs, optional filling, invalid shapes/options, and input immutability.
