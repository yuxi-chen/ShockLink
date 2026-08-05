# MMS–Bow-Shock Connection Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Find the closest intersection between the extracted bow shock and the straight line through MMS in the interval-averaged GSM magnetic-field direction, then provide acute-angle 2D and complete 3D visualizations.

**Architecture:** Add an optional acute mode to the existing normal-angle calculation, then introduce a flat `shocklink.connectivity` module. The module triangulates only observed cells of `surface_x(y,z)`, performs scale-normalized vectorized line–triangle intersection tests, returns a self-contained connection result, and owns the two plots. Existing bow-shock extraction and MMS loading remain independent inputs to this integration layer.

**Tech Stack:** Python 3.11+, NumPy, PyVista/VTK, Matplotlib from the existing `mms` extra, pytest, Ruff.

---

Implementation takes place in `.worktrees/mms-shock-connection-plan` on branch
`feature/mms-shock-connection-plan`. Use
`@superpowers:test-driven-development` for Tasks 1–6 and
`@superpowers:verification-before-completion` before Task 7 claims success.

### Task 1: Add the acute shock-angle convention

**Files:**
- Modify: `tests/bowshock/test_normals.py:193`
- Modify: `src/shocklink/bowshock.py:971`

**Step 1: Write the failing acute-angle tests**

Keep the existing directed-angle test and add:

```python
def test_calc_bow_shock_normal_angle_supports_acute_convention() -> None:
    normals = np.array(
        [
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
        ]
    )

    angles = calc_bow_shock_normal_angle(
        normals,
        [-2.0, 0.0, 0.0],
        acute=True,
    )

    np.testing.assert_allclose(angles, [0.0, 0.0, 90.0, 45.0])
    assert np.all((angles >= 0.0) & (angles <= 90.0))


def test_calc_bow_shock_normal_angle_keeps_directed_default() -> None:
    angle = calc_bow_shock_normal_angle([1.0, 0.0, 0.0], [-1.0, 0.0, 0.0])

    assert angle == pytest.approx(180.0)


@pytest.mark.parametrize("acute", [None, 0, 1, "yes"])
def test_calc_bow_shock_normal_angle_requires_boolean_acute(acute: object) -> None:
    with pytest.raises(DatasetError, match="acute must be a boolean"):
        calc_bow_shock_normal_angle(
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            acute=acute,  # type: ignore[arg-type]
        )
```

**Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src pytest tests/bowshock/test_normals.py -q
```

Expected: the new tests fail because `acute` is not accepted.

**Step 3: Implement the backward-compatible option**

Change the signature and dot-product section to:

```python
def calc_bow_shock_normal_angle(
    normals: ArrayLike,
    vector: ArrayLike,
    *,
    acute: bool = False,
) -> NDArray[np.float64]:
    """Return directed or acute angles between normals and a reference vector.

    Parameters
    ----------
    normals : array-like
        Finite real normal vectors with shape ``(..., 3)``.
    vector : array-like
        Finite real reference vector with shape ``(3,)``.
    acute : bool, default False
        If false, return directed angles in ``[0, 180]``. If true, use the
        absolute normalized dot product and return acute angles in ``[0, 90]``.
    """
    if not isinstance(acute, bool):
        raise DatasetError("acute must be a boolean")

    # Retain the existing input validation and normalization here.
    dot_products = np.sum(normal_unit * vector_unit, axis=-1)
    if acute:
        dot_products = np.abs(dot_products)
    return np.degrees(np.arccos(np.clip(dot_products, -1.0, 1.0)))
```

Update the `Returns` and `Raises` docstring sections to state both ranges and
the boolean validation.

**Step 4: Run the focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src pytest tests/bowshock/test_normals.py -q
```

Expected: all normal and angle tests pass.

**Step 5: Commit**

```bash
git add src/shocklink/bowshock.py tests/bowshock/test_normals.py
git commit -m "feat: support acute shock-normal angles"
```

### Task 2: Build the observed triangulated shock surface

**Files:**
- Create: `tests/test_connectivity.py`
- Create: `src/shocklink/connectivity.py`
- Modify: `tests/test_module_boundaries.py`

**Step 1: Write failing triangulation tests**

Start `tests/test_connectivity.py` with an analytic surface helper and a direct
test of the module-private mesh builder:

```python
from __future__ import annotations

import numpy as np
import pytest
import pyvista as pv

from shocklink.connectivity import _build_surface_mesh
from shocklink.exceptions import DatasetError, GeometryError


def _plane_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    y = np.array([-1.0, 0.0, 1.0])
    z = np.array([-1.0, 0.0, 1.0])
    surface_x = np.full((3, 3), 5.0)
    normals = np.zeros((3, 3, 3))
    normals[..., 0] = 1.0
    return y, z, surface_x, normals


def test_build_surface_mesh_uses_only_complete_observed_quads() -> None:
    y, z, surface_x, normals = _plane_inputs()
    surface_x[0, 0] = np.nan
    theta = np.full(surface_x.shape, 30.0)
    theta[0, 0] = np.nan

    mesh = _build_surface_mesh(
        surface_x,
        normals,
        theta,
        y=y,
        z=z,
    )

    assert isinstance(mesh, pv.PolyData)
    assert mesh.n_cells == 6  # Three complete quads, two triangles each.
    assert mesh.n_points == 8
    assert set(mesh.point_data) >= {"shock_normal", "theta_Bn [deg]"}
    np.testing.assert_allclose(mesh.point_data["theta_Bn [deg]"], 30.0)


def test_build_surface_mesh_winds_every_face_toward_positive_x() -> None:
    y, z, surface_x, normals = _plane_inputs()
    mesh = _build_surface_mesh(
        surface_x,
        normals,
        np.full(surface_x.shape, 45.0),
        y=y,
        z=z,
    )

    face_normals = mesh.compute_normals(
        point_normals=False,
        cell_normals=True,
        auto_orient_normals=False,
    ).cell_data["Normals"]
    assert np.all(face_normals[:, 0] > 0.0)
```

Add validation cases for decreasing axes, a surface shape mismatch, a normal
shape mismatch, infinity in `surface_x`, and nonfinite normal components.

In `tests/test_module_boundaries.py`, assert that importing
`shocklink.connectivity` does not import `shocklink.mms`, `pytplot`, or
`pyspedas`. Matplotlib must also remain unloaded until the 2D plot is called.

**Step 2: Run the focused tests and verify RED**

Run:

```bash
PYTHONPATH=src pytest tests/test_connectivity.py tests/test_module_boundaries.py -q
```

Expected: collection fails because `shocklink.connectivity` does not exist.

**Step 3: Add validated mesh construction**

Create `src/shocklink/connectivity.py` with lazy Matplotlib use and these
module-level names:

```python
"""Straight magnetic-field connection to an extracted bow shock."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import ArrayLike, NDArray
import pyvista as pv

from shocklink.bowshock import calc_bow_shock_normal_angle
from shocklink.exceptions import DatasetError, GeometryError

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

NORMAL_NAME = "shock_normal"
ANGLE_NAME = "theta_Bn [deg]"
```

Add local validators with these contracts:

```python
def _real_array(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Return a private real float64 copy or raise DatasetError."""


def _axis(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Require a finite strictly increasing 1D axis with at least two values."""


def _vector(values: ArrayLike, *, label: str, nonzero: bool) -> NDArray[np.float64]:
    """Require exactly three finite values and optionally nonzero magnitude."""
```

Implement `_build_surface_mesh` as follows:

```python
def _build_surface_mesh(
    surface_x: ArrayLike,
    normals: ArrayLike,
    theta_bn_deg: ArrayLike,
    *,
    y: ArrayLike,
    z: ArrayLike,
) -> pv.PolyData:
    y_values = _axis(y, label="Y")
    z_values = _axis(z, label="Z")
    surface = _real_array(surface_x, label="Bow-shock surface")
    normal_values = _real_array(normals, label="Bow-shock normals")
    angles = _real_array(theta_bn_deg, label="Shock-normal angle")
    shape = (len(y_values), len(z_values))
    if surface.shape != shape:
        raise DatasetError(f"Bow-shock surface must have shape {shape}")
    if normal_values.shape != shape + (3,):
        raise DatasetError(f"Bow-shock normals must have shape {shape + (3,)}")
    if angles.shape != shape:
        raise DatasetError(f"Shock-normal angle must have shape {shape}")
    if np.isinf(surface).any():
        raise DatasetError("Bow-shock surface must not contain infinity")
    if not np.isfinite(normal_values).all():
        raise DatasetError("Bow-shock normals must be finite")

    valid = np.isfinite(surface)
    yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
    point_ids = np.full(shape, -1, dtype=np.int64)
    point_ids[valid] = np.arange(np.count_nonzero(valid), dtype=np.int64)
    points = np.column_stack((surface[valid], yy[valid], zz[valid]))

    faces: list[tuple[int, int, int]] = []
    for i in range(shape[0] - 1):
        for j in range(shape[1] - 1):
            if not valid[i : i + 2, j : j + 2].all():
                continue
            p00 = int(point_ids[i, j])
            p10 = int(point_ids[i + 1, j])
            p01 = int(point_ids[i, j + 1])
            p11 = int(point_ids[i + 1, j + 1])
            faces.extend(((p00, p10, p01), (p10, p11, p01)))

    vtk_faces = np.empty((len(faces), 4), dtype=np.int64)
    if faces:
        vtk_faces[:, 0] = 3
        vtk_faces[:, 1:] = np.asarray(faces, dtype=np.int64)
    mesh = pv.PolyData(points, vtk_faces.reshape(-1))
    mesh.point_data[NORMAL_NAME] = normal_values[valid]
    mesh.point_data[ANGLE_NAME] = angles[valid]
    return mesh
```

Use vectorized array construction instead of the nested loop if it remains
equally readable; the public behavior and face winding must stay identical.

**Step 4: Run the focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=src pytest tests/test_connectivity.py tests/test_module_boundaries.py -q
```

Expected: all new mesh and boundary tests pass.

**Step 5: Commit**

```bash
git add src/shocklink/connectivity.py tests/test_connectivity.py tests/test_module_boundaries.py
git commit -m "feat: triangulate observed bow-shock coverage"
```

### Task 3: Find and select exact straight-line intersections

**Files:**
- Modify: `tests/test_connectivity.py`
- Modify: `src/shocklink/connectivity.py`

**Step 1: Write failing result and intersection tests**

Add public imports and the known-plane test:

```python
from shocklink.connectivity import (
    ShockConnection,
    ShockIntersection,
    analyze_shock_connection,
)


def test_analyze_shock_connection_finds_shared_vertex_once() -> None:
    y, z, surface_x, normals = _plane_inputs()

    result = analyze_shock_connection(
        surface_x,
        normals,
        y=y,
        z=z,
        mms_position=[0.0, 0.0, 0.0],
        bavg=[2.0, 0.0, 0.0],
    )

    assert isinstance(result, ShockConnection)
    assert len(result.intersections) == 1
    hit = result.selected_intersection
    assert isinstance(hit, ShockIntersection)
    np.testing.assert_allclose(hit.point, [5.0, 0.0, 0.0])
    assert hit.line_parameter == pytest.approx(5.0)
    assert hit.distance == pytest.approx(5.0)
    np.testing.assert_allclose(hit.shock_normal, [1.0, 0.0, 0.0])
    assert hit.theta_bn_deg == pytest.approx(0.0)
    np.testing.assert_allclose(result.field_direction, [1.0, 0.0, 0.0])
    np.testing.assert_allclose(result.theta_bn_deg, 0.0)
```

Add the opposite-directed-field test:

```python
def test_analyze_shock_connection_searches_both_field_directions() -> None:
    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x,
        normals,
        y=y,
        z=z,
        mms_position=[0.0, 0.0, 0.0],
        bavg=[-4.0, 0.0, 0.0],
    )

    assert result.selected_intersection.line_parameter == pytest.approx(-5.0)
    assert result.selected_intersection.theta_bn_deg == pytest.approx(0.0)
```

Add a two-crossing selection test:

```python
def test_analyze_shock_connection_selects_crossing_closest_to_mms() -> None:
    y = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    z = np.array([-1.0, 0.0, 1.0])
    yy, zz = np.meshgrid(y, z, indexing="ij")
    surface_x = yy**2
    normals = np.stack((np.ones_like(yy), -2.0 * yy, np.zeros_like(zz)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)

    result = analyze_shock_connection(
        surface_x,
        normals,
        y=y,
        z=z,
        mms_position=[1.0, 0.8, 0.0],
        bavg=[0.0, 3.0, 0.0],
    )

    assert len(result.intersections) == 2
    np.testing.assert_allclose(result.selected_intersection.point, [1.0, 1.0, 0.0])
    assert result.selected_intersection.line_parameter == pytest.approx(0.2)
    assert result.intersections[1].line_parameter == pytest.approx(-1.8)
```

Also add tests that:

- `theta_bn_deg` is `NaN` where `surface_x` is `NaN`;
- caller arrays are not modified and result coordinate/vector arrays are read-only;
- a center `NaN` in a 3-by-3 surface raises `GeometryError` for no triangles;
- a line parallel to and displaced from a plane raises `GeometryError` containing
  `does not intersect`;
- malformed MMS position, zero `bavg`, nonpositive/nonfinite tolerance, and
  incompatible shapes raise `DatasetError`; and
- intersections overlapping a triangle coplanarly raise an `ambiguous` geometry
  error rather than returning an arbitrary endpoint.

**Step 2: Run the tests and verify RED**

Run:

```bash
PYTHONPATH=src pytest tests/test_connectivity.py -q
```

Expected: imports fail because the public records and analysis function do not
exist.

**Step 3: Add immutable result records**

Add a helper that copies arrays and sets `write=False`, then define:

```python
@dataclass(frozen=True, slots=True)
class ShockIntersection:
    point: NDArray[np.float64]
    line_parameter: float
    distance: float
    face_index: int
    barycentric: NDArray[np.float64]
    shock_normal: NDArray[np.float64]
    theta_bn_deg: float


@dataclass(frozen=True, slots=True)
class ShockConnection:
    mms_position: NDArray[np.float64]
    bavg: NDArray[np.float64]
    field_direction: NDArray[np.float64]
    y: NDArray[np.float64]
    z: NDArray[np.float64]
    theta_bn_deg: NDArray[np.float64]
    surface_mesh: pv.PolyData
    intersections: tuple[ShockIntersection, ...]

    @property
    def selected_intersection(self) -> ShockIntersection:
        """Return the intersection closest to MMS."""
        return self.intersections[0]
```

Only the analysis function constructs these records. Copy/freeze every NumPy
field there, sort `intersections` by `distance`, and deep-copy the mesh into the
result.

**Step 4: Implement scale-normalized vectorized intersections**

Add `_line_triangle_intersections(mesh, origin, direction, tolerance)`. Normalize
all vertex offsets by one positive geometry scale before the Möller–Trumbore
calculation:

```python
faces = mesh.faces.reshape(-1, 4)[:, 1:]
vertices = np.asarray(mesh.points, dtype=np.float64)
scale = max(float(np.linalg.norm(vertices - origin, axis=1).max()), 1.0)
triangles = (vertices[faces] - origin) / scale
v0 = triangles[:, 0]
edge1 = triangles[:, 1] - v0
edge2 = triangles[:, 2] - v0
pvec = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
determinant = np.einsum("ij,ij->i", edge1, pvec)
nonparallel = np.abs(determinant) > tolerance
inverse = np.zeros_like(determinant)
inverse[nonparallel] = 1.0 / determinant[nonparallel]
tvec = -v0
u = np.einsum("ij,ij->i", tvec, pvec) * inverse
qvec = np.cross(tvec, edge1)
v = np.einsum("j,ij->i", direction, qvec) * inverse
s_scaled = np.einsum("ij,ij->i", edge2, qvec) * inverse
inside = (
    nonparallel
    & (u >= -tolerance)
    & (v >= -tolerance)
    & (u + v <= 1.0 + tolerance)
)
```

For every `inside` face, calculate:

```python
barycentric = np.array([1.0 - u[index] - v[index], u[index], v[index]])
line_parameter = float(s_scaled[index] * scale)
point = origin + line_parameter * direction
normal = barycentric @ mesh.point_data[NORMAL_NAME][faces[index]]
normal /= np.linalg.norm(normal)
theta = float(calc_bow_shock_normal_angle(normal, direction, acute=True))
```

For near-parallel candidates, project the line and triangle to the two
coordinates orthogonal to the dominant triangle-normal component. Raise
`GeometryError("Field line overlaps the shock surface; intersection is ambiguous")`
only when the coplanar infinite line actually overlaps the projected triangle;
a merely parallel displaced line is not ambiguous.

Sort candidate records by `abs(line_parameter)`. Deduplicate neighboring hits
whose physical points differ by no more than `tolerance * scale`; retain the
first face because barycentric interpolation is identical on a shared edge when
vertex normals are shared.

**Step 5: Implement the public analysis function**

Use this exact signature and data flow:

```python
def analyze_shock_connection(
    surface_x: ArrayLike,
    normals: ArrayLike,
    *,
    y: ArrayLike,
    z: ArrayLike,
    mms_position: ArrayLike,
    bavg: ArrayLike,
    tolerance: float = 1.0e-9,
) -> ShockConnection:
    """Analyze a straight GSM field-line connection to the extracted shock."""
    y_values = _axis(y, label="Y")
    z_values = _axis(z, label="Z")
    surface = _real_array(surface_x, label="Bow-shock surface")
    normal_values = _real_array(normals, label="Bow-shock normals")
    mms = _vector(mms_position, label="MMS position", nonzero=False)
    field = _vector(bavg, label="Bavg", nonzero=True)
    try:
        relative_tolerance = float(tolerance)
    except (TypeError, ValueError) as error:
        raise DatasetError("Intersection tolerance must be finite and positive") from error
    if not np.isfinite(relative_tolerance) or relative_tolerance <= 0.0:
        raise DatasetError("Intersection tolerance must be finite and positive")

    expected = (len(y_values), len(z_values))
    if surface.shape != expected:
        raise DatasetError(f"Bow-shock surface must have shape {expected}")
    if normal_values.shape != expected + (3,):
        raise DatasetError(f"Bow-shock normals must have shape {expected + (3,)}")

    direction = field / np.linalg.norm(field)
    full_angles = calc_bow_shock_normal_angle(
        normal_values,
        field,
        acute=True,
    )
    angles = np.where(np.isfinite(surface), full_angles, np.nan)
    mesh = _build_surface_mesh(
        surface,
        normal_values,
        angles,
        y=y_values,
        z=z_values,
    )
    if mesh.n_cells == 0:
        raise GeometryError("Extracted bow shock has no complete triangular cells")
    intersections = _line_triangle_intersections(
        mesh,
        origin=mms,
        direction=direction,
        tolerance=relative_tolerance,
    )
    if not intersections:
        raise GeometryError("Straight MMS field line does not intersect observed shock coverage")
    return ShockConnection(...)
```

Finish the NumPy-style `Parameters`, `Returns`, `Raises`, and `Notes` sections.
The notes must state the GSM, Earth-radius, infinite-line, both-direction,
closest-hit, and acute-angle conventions.

Expose only these names:

```python
__all__ = [
    "ShockConnection",
    "ShockIntersection",
    "analyze_shock_connection",
    "plot_shock_angle_contour",
    "plot_shock_connection_3d",
]
```

The plot names can be exported before their implementation in Task 4 only if
temporary stubs are avoided; add them to `__all__` in Task 4 otherwise.

**Step 6: Run focused and neighboring tests**

Run:

```bash
PYTHONPATH=src pytest tests/test_connectivity.py tests/bowshock/test_normals.py -q
```

Expected: all tests pass.

**Step 7: Commit**

```bash
git add src/shocklink/connectivity.py tests/test_connectivity.py
git commit -m "feat: find closest MMS shock intersection"
```

### Task 4: Add the 2D contour and 3D connection plots

**Files:**
- Modify: `tests/test_connectivity.py`
- Modify: `src/shocklink/connectivity.py`

**Step 1: Write failing 2D plot tests**

Set the Agg backend at the top of `tests/test_connectivity.py`, then add:

```python
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from shocklink.connectivity import plot_shock_angle_contour


def test_plot_shock_angle_contour_marks_selected_intersection() -> None:
    y, z, surface_x, normals = _plane_inputs()
    normals[..., 0] = np.sqrt(0.5)
    normals[..., 1] = np.sqrt(0.5)
    result = analyze_shock_connection(
        surface_x,
        normals,
        y=y,
        z=z,
        mms_position=[0.0, 0.0, 0.0],
        bavg=[1.0, 0.0, 0.0],
    )

    figure, axes = plot_shock_angle_contour(result)

    assert axes.get_xlabel() == r"$Y_{GSM}$ [$R_E$]"
    assert axes.get_ylabel() == r"$Z_{GSM}$ [$R_E$]"
    assert axes.get_aspect() in (1.0, "equal")
    marker = next(collection for collection in axes.collections if collection.get_label() == "Intersection")
    np.testing.assert_allclose(marker.get_offsets(), [[0.0, 0.0]])
    assert figure.axes[-1].get_ylabel() == r"$\theta_{Bn}$ [deg]"
    assert any("(5.000, 0.000, 0.000)" in text.get_text() for text in axes.texts)
    plt.close(figure)
```

Add a masked-surface test that places one `NaN` in `surface_x`, chooses an
intersection away from the hole, calls the plot, and confirms the contour's
source array remains masked there. Also verify an explicitly supplied axes is
reused.

**Step 2: Write the failing 3D actor test**

```python
from shocklink.connectivity import plot_shock_connection_3d


def test_plot_shock_connection_3d_adds_required_scene_actors() -> None:
    y, z, surface_x, normals = _plane_inputs()
    result = analyze_shock_connection(
        surface_x,
        normals,
        y=y,
        z=z,
        mms_position=[0.0, 0.0, 0.0],
        bavg=[1.0, 0.0, 0.0],
    )
    plotter = pv.Plotter(off_screen=True)
    try:
        returned = plot_shock_connection_3d(result, plotter=plotter, show=False)
        assert returned is plotter
        assert {
            "earth",
            "bow_shock",
            "mms",
            "field_line",
            "bavg_arrow",
            "intersection",
        } <= set(plotter.renderer.actors)
    finally:
        plotter.close()
```

**Step 3: Run plotting tests and verify RED**

Run:

```bash
PYTHONPATH=src pytest tests/test_connectivity.py -q
```

Expected: plot imports or assertions fail because the functions do not exist.

**Step 4: Implement the 2D contour**

Use a lazy import and this signature:

```python
def plot_shock_angle_contour(
    connection: ShockConnection,
    *,
    ax: Axes | None = None,
    levels: ArrayLike | None = None,
    cmap: str = "viridis",
) -> tuple[Figure, Axes]:
```

On missing Matplotlib, raise an `ImportError` that recommends
`pip install -e '.[mms]'`. Default to `np.linspace(0.0, 90.0, 19)`, require a
finite strictly increasing 1D level array spanning exactly 0 through 90, then:

```python
figure, axes = plt.subplots() if ax is None else (ax.figure, ax)
masked = np.ma.masked_invalid(connection.theta_bn_deg.T)
contour = axes.contourf(
    connection.y,
    connection.z,
    masked,
    levels=level_values,
    cmap=cmap,
    vmin=0.0,
    vmax=90.0,
)
colorbar = figure.colorbar(contour, ax=axes)
colorbar.set_label(r"$\theta_{Bn}$ [deg]")
hit = connection.selected_intersection
axes.scatter(
    [hit.point[1]],
    [hit.point[2]],
    marker="*",
    s=120,
    color="cyan",
    edgecolor="black",
    label="Intersection",
    zorder=5,
)
axes.annotate(
    f"Intersection: ({hit.point[0]:.3f}, {hit.point[1]:.3f}, {hit.point[2]:.3f}) $R_E$\n"
    f"$\\theta_{{Bn}}$ = {hit.theta_bn_deg:.2f}°",
    (hit.point[1], hit.point[2]),
    xytext=(8, 8),
    textcoords="offset points",
)
axes.set_xlabel(r"$Y_{GSM}$ [$R_E$]")
axes.set_ylabel(r"$Z_{GSM}$ [$R_E$]")
axes.set_aspect("equal")
return figure, axes
```

**Step 5: Implement the 3D scene**

Use this signature:

```python
def plot_shock_connection_3d(
    connection: ShockConnection,
    *,
    plotter: pv.Plotter | None = None,
    show: bool = True,
    cmap: str = "viridis",
) -> pv.Plotter:
```

Create or reuse the plotter. Add actors with the exact stable names asserted by
the test:

```python
active = plotter if plotter is not None else pv.Plotter()
active.add_mesh(
    pv.Sphere(radius=1.0, center=(0.0, 0.0, 0.0)),
    color="royalblue",
    name="earth",
)
active.add_mesh(
    connection.surface_mesh,
    scalars=ANGLE_NAME,
    clim=(0.0, 90.0),
    cmap=cmap,
    opacity=0.75,
    scalar_bar_args={"title": "theta_Bn [deg]"},
    name="bow_shock",
)
```

Add MMS and intersection with `add_points`, distinct colors, point size at
least 12, and names `mms` and `intersection`. Add point labels `MMS` and
`Intersection` without replacing those named point actors.

Let `delta = hit.point - connection.mms_position`. The visible line ends at
`hit.point + 0.1 * delta`; if MMS is exactly on the shock, instead use one Earth
radius along the signed field direction. Add `pv.Line` as `field_line`.
Add a `bavg_arrow` rooted at MMS with direction `field_direction` and a visible
magnitude `max(0.25 * hit.distance, 1.0)`. Add axes, use an isometric view, and
call `active.show()` only when `show` is true.

**Step 6: Run plotting and MMS regression tests**

Run:

```bash
PYTHONPATH=src pytest tests/test_connectivity.py tests/mms/test_plotting.py -q
```

Expected: all tests pass without opening windows.

**Step 7: Commit**

```bash
git add src/shocklink/connectivity.py tests/test_connectivity.py
git commit -m "feat: plot MMS bow-shock connection"
```

### Task 5: Add the end-to-end example and user guide

**Files:**
- Create: `examples/mms_bow_shock_connection.py`
- Create: `docs/mms-bow-shock-connection.md`
- Modify: `examples/README.md`
- Modify: `README.md`
- Modify: `tests/test_documentation.py`

**Step 1: Write failing documentation and example tests**

Add constants in `tests/test_documentation.py`:

```python
CONNECTION_GUIDE = ROOT / "docs/mms-bow-shock-connection.md"
CONNECTION_EXAMPLE = ROOT / "examples/mms_bow_shock_connection.py"
```

Add tests that require:

```python
def test_connection_guide_documents_scientific_conventions() -> None:
    text = CONNECTION_GUIDE.read_text()
    for required in (
        "analyze_shock_connection",
        "plot_shock_angle_contour",
        "plot_shock_connection_3d",
        "r(s)",
        "0–90",
        "closest",
        "GSM",
        "R_E",
    ):
        assert required in text


def test_connection_example_compiles_and_uses_public_api() -> None:
    source = CONNECTION_EXAMPLE.read_text()
    compile(source, str(CONNECTION_EXAMPLE), "exec")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        and node.module is not None
        and node.module.startswith("shocklink.")
        for alias in node.names
    }
    assert {
        "analyze_shock_connection",
        "plot_shock_angle_contour",
        "plot_shock_connection_3d",
        "load_mms_data",
        "average_plotted_values",
    } <= imports
    assert all(not name.startswith("_") for name in imports)
```

Also assert that both root and examples READMEs link the new guide/example, and
that the example contains required `--mms-start`, `--mms-end`, `--probe`, and
`--mode` flags.

**Step 2: Run documentation tests and verify RED**

Run:

```bash
PYTHONPATH=src pytest tests/test_documentation.py -q
```

Expected: failures for missing guide and example.

**Step 3: Create the runnable integration example**

Implement `examples/mms_bow_shock_connection.py` with a `main()` that:

```python
grid = read_tecplot(arguments.path)
calc_velocity_divergence(grid)
fit_bow_shock(grid)
shock_region = extract_shockfit_range(
    grid,
    lower=arguments.shockfit_range[0],
    upper=arguments.shockfit_range[1],
)
y = np.linspace(-arguments.transverse_limit, arguments.transverse_limit, arguments.surface_resolution)
z = np.linspace(-arguments.transverse_limit, arguments.transverse_limit, arguments.surface_resolution)
surface_x_raw = get_bow_shock_surface(
    shock_region,
    y=y,
    z=z,
    x_resolution=arguments.x_resolution,
    refine_minimum=True,
)
surface_x = smooth_bow_shock_surface(surface_x_raw, sigma=arguments.smoothing_sigma)
normals = calc_bow_shock_normals(surface_x, y=y, z=z)

mms_data = load_mms_data(
    arguments.mms_start,
    arguments.mms_end,
    probe=arguments.probe,
    mode=arguments.mode,
    coordinates="gsm",
)
averages = average_plotted_values(mms_data)
mms_position = np.array([averages[f"satellite_location_{axis}"] for axis in "xyz"])
bavg = np.array([averages[f"magnetic_field_{axis}"] for axis in "xyz"])
connection = analyze_shock_connection(
    surface_x,
    normals,
    y=y,
    z=z,
    mms_position=mms_position,
    bavg=bavg,
)
```

Print the Tecplot `TIME_EVENT_KEY`, requested MMS interval, Bavg, selected
intersection, signed line parameter, distance, and local angle. Then call both
public plot functions, display the Matplotlib figure non-blocking, and let the
PyVista plotter own the blocking window. Catch expected ShockLink/MMS/data errors
at the CLI boundary and return a nonzero exit status with a concise message.

Expose practical extraction options copied from `bow_shock_workflow.py`, but do
not introduce output formats, configuration files, or automatic time-window
selection in this feature.

**Step 4: Write the workflow guide and README links**

The guide must include:

- the straight infinite-line equation and both-direction convention;
- the acute `theta_Bn` equation and `[0, 90]` range;
- closest-crossing selection and behavior for multiple/no crossings;
- GSM and Earth-radius requirements;
- a copy-paste API example using existing shock and MMS outputs;
- descriptions of both plots and missing-coverage masking;
- the example command; and
- limitations: straight Bavg line, no field integration, and extracted-surface
  resolution controls the intersection geometry.

Link the guide from `README.md`. Add this runnable command to `examples/README.md`:

```bash
PYTHONPATH=src python examples/mms_bow_shock_connection.py data/3d.dat \
  --mms-start "2023-12-16 11:29:30" \
  --mms-end "2023-12-16 11:30:30" \
  --probe 1 --mode auto
```

**Step 5: Run documentation, source-layout, and compile checks**

Run:

```bash
PYTHONPATH=src pytest tests/test_documentation.py tests/test_source_layout.py -q
python -m py_compile examples/mms_bow_shock_connection.py
```

Expected: all tests and compilation pass.

**Step 6: Commit**

```bash
git add README.md docs/mms-bow-shock-connection.md examples/README.md \
  examples/mms_bow_shock_connection.py tests/test_documentation.py
git commit -m "docs: add MMS bow-shock connection workflow"
```

### Task 6: Add opt-in real-data coverage

**Files:**
- Modify: `tests/integration/test_tecplot_sample.py`

**Step 1: Extend the existing bow-shock extraction integration test**

Import `analyze_shock_connection`. After the existing surface and normal
assertions in `test_real_batsrus_sample_extracts_bow_shock_surface_array`, add:

```python
connection = analyze_shock_connection(
    surface,
    normals,
    y=y,
    z=z,
    mms_position=(0.0, 0.0, 0.0),
    bavg=(1.0, 0.0, 0.0),
)

assert len(connection.intersections) >= 1
assert np.isfinite(connection.selected_intersection.point).all()
assert connection.selected_intersection.distance > 0.0
assert 0.0 <= connection.selected_intersection.theta_bn_deg <= 90.0
assert connection.surface_mesh.n_cells > 0
```

This supplied seed and field line exercise the real extracted nose without a
network-dependent MMS request.

**Step 2: Run the ordinary integration file and verify the expected skip**

Run:

```bash
PYTHONPATH=src pytest tests/integration/test_tecplot_sample.py -q
```

Expected: all tests skip unless `SHOCKLINK_RUN_LARGE_DATA_TESTS=1` is set.

**Step 3: Run the opt-in real-data test**

When `data/3d.dat` is present, run:

```bash
SHOCKLINK_RUN_LARGE_DATA_TESTS=1 PYTHONPATH=src \
  pytest tests/integration/test_tecplot_sample.py::test_real_batsrus_sample_extracts_bow_shock_surface_array -q
```

Expected: PASS with a finite selected intersection. If the fixed origin line
does not cross the observed finite coverage for the local sample, inspect the
already extracted `surface` and choose a deterministic Y–Z coordinate with
finite surrounding cells; do not weaken the assertion or fabricate a closest
point.

**Step 4: Commit**

```bash
git add tests/integration/test_tecplot_sample.py
git commit -m "test: cover real-data shock connection"
```

### Task 7: Verify and integrate into `main`

**Files:**
- Verify all modified files.

**Step 1: Run focused connectivity tests**

Run:

```bash
PYTHONPATH=src pytest tests/test_connectivity.py tests/bowshock/test_normals.py -q
```

Expected: all pass.

**Step 2: Run the complete ordinary test suite once**

Run:

```bash
PYTHONPATH=src pytest -q
```

Expected: all ordinary tests pass; only opt-in large-data integration tests are
skipped.

**Step 3: Run static and formatting verification**

Run:

```bash
ruff check src tests examples
ruff format --check src tests examples
git diff --check
git status --short
```

Expected: all checks pass and the feature worktree is clean.

**Step 4: Review the branch scope**

Run:

```bash
git log --oneline main..HEAD
git diff --stat main...HEAD
git diff --name-only main...HEAD
```

Expected: only the approved angle option, connectivity module/tests, example,
documentation, and integration coverage are present.

**Step 5: Fast-forward merge directly into `main`**

From `/Users/yuxichen/dev/ShockGeo`:

```bash
git status --short
git merge --ff-only feature/mms-shock-connection-plan
```

Expected: the clean `main` checkout fast-forwards to the verified feature tip.

**Step 6: Verify the integrated checkout**

Run from `/Users/yuxichen/dev/ShockGeo`:

```bash
PYTHONPATH=src pytest -q
git status --short
```

Expected: the suite still passes and `main` is clean.

**Step 7: Remove the finished worktree**

After confirming the merge and clean state:

```bash
git worktree remove .worktrees/mms-shock-connection-plan
git branch -d feature/mms-shock-connection-plan
```

Expected: the feature is retained on `main`; only the temporary worktree and
merged local branch name are removed.
