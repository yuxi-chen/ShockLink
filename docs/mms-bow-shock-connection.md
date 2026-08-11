# MMS–bow-shock magnetic connection

This workflow connects an interval-averaged MMS position to an extracted
BATSRUS bow shock using a straight field line. In GSM coordinates and Earth
radii (`R_E`), the line is

\[
r(s)=r_{MMS}+s\,\hat B_{avg},\qquad -\infty<s<\infty.
\]

The observed shock is triangulated, and all line/surface crossings are found.
The `closest` crossing to MMS is selected when multiple crossings exist; no
crossing in observed coverage raises a geometry error. Missing shock samples
remain masked in the 2D plot.

The local acute shock angle is

\[
\theta_{Bn}=\cos^{-1}(|\hat B_{avg}\cdot\hat n|),
\]

reported over 0–90 degrees. `analyze_shock_connection` returns the selected
intersection and diagnostics. `plot_shock_angle_contour` shows the Y–Z angle
map and intersection marker; `plot_shock_connection_3d` shows Earth, colored
shock, MMS, the line, Bavg arrow, and intersection.

Both the Tecplot surface and MMS products must already be in GSM and use
`R_E` (Bavg remains in nT). A complete example using the public APIs is:

```python
import numpy as np
from shocklink.connectivity import analyze_shock_connection, plot_shock_angle_contour, plot_shock_connection_3d

connection = analyze_shock_connection(surface_x, normals, y=y, z=z,
    mms_position=mms_position_gsm_re, bavg=bavg_gsm_nt)
plot_shock_angle_contour(connection)
plot_shock_connection_3d(connection)
```

Run the end-to-end tool. It derives a symmetric five-minute MMS interval from
the simulation event and saves a 2D PNG plus a static 3D PNG by default:

```bash
pip install -e ".[mms]"
PYTHONPATH=src python tools/mms_bow_shock_connection.py data/3d.dat \
  --output-directory results --probe 1 --mode auto
```

Select 3D output with `--three-d-output png`, `html`, or `both`. HTML export
requires `pip install "pyvista[jupyter]"`. Use `--mms-start` and `--mms-end`
together to override the event-derived interval.

Python callers can use the reusable source interface directly:

```python
from shocklink.mms_connection import (
    build_mms_bow_shock_connection,
    save_mms_bow_shock_connection_plots,
)

result = build_mms_bow_shock_connection("data/3d.dat")
paths = save_mms_bow_shock_connection_plots(
    result, "results", three_d_output="both"
)
```

The straight Bavg line is an approximation: it does not integrate a spatially
varying magnetic field. Surface resolution, smoothing, and extraction limits
control the intersection geometry. Validate these choices for each simulation.
