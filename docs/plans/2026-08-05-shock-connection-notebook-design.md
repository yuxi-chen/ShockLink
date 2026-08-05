# Shock connection notebook design

## Goal

Fill `examples/shock_connection.ipynb` with an interactive counterpart to
`examples/mms_bow_shock_connection.py`. It will use an explicit MMS interval,
load GSM MMS data, derive the averaged position and `Bavg`, calculate the
closest straight-line shock intersection, and display the acute 0–90 degree
angle contour plus the 3D connection scene.

## Design

The notebook is a clean, unexecuted notebook with six stages: requirements and
launch instructions; editable parameters; public imports; Tecplot shock
extraction and smoothing; MMS loading and connection diagnostics; and 2D/3D
visualization. PyVista uses the static Jupyter backend. All intermediate names
remain visible so users can inspect the surface, normals, averages, and result.

The notebook calls only public ShockLink APIs and keeps network-dependent MMS
loading explicit. It does not duplicate numerical algorithms or embed outputs.
Structural tests validate notebook format, clean execution metadata, import and
call order, GSM loading, diagnostics, both plotting calls, and portable paths.
