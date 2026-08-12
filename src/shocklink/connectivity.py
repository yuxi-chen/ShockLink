"""Straight magnetic-field connection to an extracted bow shock."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pyvista as pv
from numpy.typing import ArrayLike, NDArray

from shocklink.exceptions import DatasetError, GeometryError
from shocklink.bowshock import calc_bow_shock_normal_angle

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

NORMAL_NAME = "shock_normal"
ANGLE_NAME = "theta_Bn [deg]"


def _frozen(values: ArrayLike) -> NDArray[np.float64]:
    array = np.array(values, dtype=np.float64, copy=True)
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class ShockIntersection:
    point: NDArray[np.float64]
    line_parameter: float
    distance: float
    face_index: int
    barycentric: NDArray[np.float64]
    shock_normal: NDArray[np.float64]
    theta_bn_deg: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "point", _frozen(self.point))
        object.__setattr__(self, "barycentric", _frozen(self.barycentric))
        object.__setattr__(self, "shock_normal", _frozen(self.shock_normal))


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

    def __post_init__(self) -> None:
        for name in (
            "mms_position",
            "bavg",
            "field_direction",
            "y",
            "z",
            "theta_bn_deg",
        ):
            object.__setattr__(self, name, _frozen(getattr(self, name)))
        object.__setattr__(self, "surface_mesh", self.surface_mesh.copy(deep=True))

    @property
    def selected_intersection(self) -> ShockIntersection:
        return self.intersections[0]


def _real_array(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Return a real float64 copy, preserving NaNs for later validation."""
    try:
        array = np.array(values, dtype=np.float64, copy=True)
    except (TypeError, ValueError) as error:
        raise DatasetError(f"{label} must contain real numeric values") from error
    if np.iscomplexobj(values):
        raise DatasetError(f"{label} must contain real numeric values")
    return array


def _axis(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Validate a finite, strictly increasing coordinate axis."""
    axis = _real_array(values, label=label)
    if axis.ndim != 1 or axis.size < 2:
        raise DatasetError(
            f"{label} must be a one-dimensional axis with at least two values"
        )
    if not np.isfinite(axis).all():
        raise DatasetError(f"{label} must be finite")
    if not np.all(np.diff(axis) > 0.0):
        raise DatasetError(f"{label} must be strictly increasing")
    return axis


def _vector(values: ArrayLike, *, label: str, nonzero: bool) -> NDArray[np.float64]:
    """Validate a finite three-component vector."""
    vector = _real_array(values, label=label)
    if vector.shape != (3,):
        raise DatasetError(f"{label} must contain exactly three values")
    if not np.isfinite(vector).all():
        raise DatasetError(f"{label} must be finite")
    if nonzero and np.linalg.norm(vector) == 0.0:
        raise DatasetError(f"{label} must be nonzero")
    return vector


def _build_surface_mesh(
    surface_x: ArrayLike,
    normals: ArrayLike,
    theta_bn_deg: ArrayLike,
    *,
    y: ArrayLike,
    z: ArrayLike,
) -> pv.PolyData:
    """Triangulate complete, observed cells of an X(Y, Z) shock surface."""
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
    valid = np.isfinite(surface)
    if not np.isfinite(normal_values[valid]).all():
        raise DatasetError("Bow-shock normals must be finite where surface is observed")
    if not np.isfinite(angles[valid]).all():
        raise DatasetError(
            "Shock-normal angle must be finite where surface is observed"
        )

    yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
    cell_valid = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:] & valid[1:, 1:]
    if not np.any(cell_valid):
        raise GeometryError("Bow-shock surface contains no complete observed cells")

    point_ids = np.full(shape, -1, dtype=np.int64)
    point_ids[valid] = np.arange(np.count_nonzero(valid), dtype=np.int64)
    points = np.column_stack((surface[valid], yy[valid], zz[valid]))

    faces: list[tuple[int, int, int]] = []
    for i, j in zip(*np.nonzero(cell_valid)):
        p00 = int(point_ids[i, j])
        p10 = int(point_ids[i + 1, j])
        p01 = int(point_ids[i, j + 1])
        p11 = int(point_ids[i + 1, j + 1])
        faces.extend(((p00, p10, p01), (p10, p11, p01)))

    vtk_faces = np.empty((len(faces), 4), dtype=np.int64)
    vtk_faces[:, 0] = 3
    vtk_faces[:, 1:] = np.asarray(faces, dtype=np.int64)
    mesh = pv.PolyData(points, vtk_faces.reshape(-1))
    mesh.point_data[NORMAL_NAME] = normal_values[valid]
    mesh.point_data[ANGLE_NAME] = angles[valid]
    return mesh


def _cross2(a: NDArray[np.float64], b: NDArray[np.float64]) -> float:
    """Return the scalar cross product of two 2D vectors."""

    return float(a[0] * b[1] - a[1] * b[0])


def _line_overlaps_triangle(
    triangle: NDArray[np.float64],
    direction: NDArray[np.float64],
    normal: NDArray[np.float64],
    *,
    tolerance: float,
) -> bool:
    """Return whether an origin-centered coplanar line overlaps a triangle."""

    drop = int(np.argmax(np.abs(normal)))
    keep = [axis for axis in range(3) if axis != drop]
    triangle_2d = triangle[:, keep]
    direction_2d = direction[keep]
    origin_2d = np.zeros(2)
    signs = [
        _cross2(
            triangle_2d[(index + 1) % 3] - triangle_2d[index],
            origin_2d - triangle_2d[index],
        )
        for index in range(3)
    ]
    if min(signs) >= -tolerance or max(signs) <= tolerance:
        return True

    for index in range(3):
        start = triangle_2d[index]
        edge = triangle_2d[(index + 1) % 3] - start
        denominator = _cross2(direction_2d, edge)
        if abs(denominator) > tolerance:
            if 0.0 <= _cross2(start, direction_2d) / denominator <= 1.0:
                return True
        elif abs(_cross2(start, direction_2d)) <= tolerance:
            return True
    return False


def _reject_coplanar_overlaps(
    triangles: NDArray[np.float64],
    edge1: NDArray[np.float64],
    edge2: NDArray[np.float64],
    tvec: NDArray[np.float64],
    nonparallel: NDArray[np.bool_],
    *,
    direction: NDArray[np.float64],
    tolerance: float,
) -> None:
    """Reject lines that have infinitely many points on a mesh triangle."""

    for index in np.flatnonzero(~nonparallel):
        normal = np.cross(edge1[index], edge2[index])
        magnitude = np.linalg.norm(normal)
        if magnitude == 0.0:
            continue
        coplanar = abs(float(np.dot(normal, tvec[index]))) <= tolerance * magnitude
        if coplanar and _line_overlaps_triangle(
            triangles[index], direction, normal, tolerance=tolerance
        ):
            raise GeometryError(
                "Field line overlaps the shock surface; intersection is ambiguous"
            )


def _intersection_hits(
    mesh: pv.PolyData,
    faces: NDArray[np.int64],
    inside: NDArray[np.bool_],
    u: NDArray[np.float64],
    v: NDArray[np.float64],
    parameters: NDArray[np.float64],
    *,
    origin: NDArray[np.float64],
    direction: NDArray[np.float64],
) -> list[ShockIntersection]:
    """Build sorted intersection records for accepted mesh faces."""

    normals = np.asarray(mesh.point_data[NORMAL_NAME], dtype=np.float64)
    result: list[ShockIntersection] = []
    for index in np.flatnonzero(inside):
        barycentric = np.array([1.0 - u[index] - v[index], u[index], v[index]])
        parameter = float(parameters[index])
        point = origin + parameter * direction
        shock_normal = barycentric @ normals[faces[index]]
        magnitude = np.linalg.norm(shock_normal)
        if not np.isfinite(magnitude) or magnitude == 0.0:
            raise GeometryError(
                "Shock normal at intersection must be finite and nonzero"
            )
        shock_normal = shock_normal / magnitude
        theta = float(calc_bow_shock_normal_angle(shock_normal, direction, acute=True))
        result.append(
            ShockIntersection(
                point,
                parameter,
                abs(parameter),
                int(index),
                barycentric,
                shock_normal,
                theta,
            )
        )
    return sorted(result, key=lambda hit: hit.distance)


def _unique_hits(
    hits: list[ShockIntersection],
    *,
    absolute_tolerance: float,
) -> list[ShockIntersection]:
    """Remove consecutive, distance-sorted hits at the same mesh location."""

    unique: list[ShockIntersection] = []
    for hit in hits:
        if (
            not unique
            or np.linalg.norm(hit.point - unique[-1].point) > absolute_tolerance
        ):
            unique.append(hit)
    return unique


def _line_triangle_intersections(
    mesh: pv.PolyData,
    *,
    origin: NDArray[np.float64],
    direction: NDArray[np.float64],
    tolerance: float,
) -> list[ShockIntersection]:
    faces = np.asarray(mesh.faces).reshape(-1, 4)[:, 1:]
    vertices = np.asarray(mesh.points, dtype=np.float64)
    scale = max(float(np.linalg.norm(vertices - origin, axis=1).max()), 1.0)
    triangles = (vertices[faces] - origin) / scale
    v0 = triangles[:, 0]
    edge1 = triangles[:, 1] - v0
    edge2 = triangles[:, 2] - v0
    pvec = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
    determinant = np.einsum("ij,ij->i", edge1, pvec)
    inverse = np.zeros_like(determinant)
    nonparallel = np.abs(determinant) > tolerance
    inverse[nonparallel] = 1.0 / determinant[nonparallel]
    tvec = -v0
    u = np.einsum("ij,ij->i", tvec, pvec) * inverse
    qvec = np.cross(tvec, edge1)
    v = np.einsum("j,ij->i", direction, qvec) * inverse
    s_scaled = np.einsum("ij,ij->i", edge2, qvec) * inverse
    inside = (
        nonparallel & (u >= -tolerance) & (v >= -tolerance) & (u + v <= 1.0 + tolerance)
    )

    _reject_coplanar_overlaps(
        triangles,
        edge1,
        edge2,
        tvec,
        nonparallel,
        direction=direction,
        tolerance=tolerance,
    )
    hits = _intersection_hits(
        mesh,
        faces,
        inside,
        u,
        v,
        s_scaled * scale,
        origin=origin,
        direction=direction,
    )
    return _unique_hits(hits, absolute_tolerance=tolerance * scale)


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
    """Analyze an infinite straight GSM field line and its bow-shock hits."""
    y_values = _axis(y, label="Y")
    z_values = _axis(z, label="Z")
    surface = _real_array(surface_x, label="Bow-shock surface")
    normal_values = _real_array(normals, label="Bow-shock normals")
    mms = _vector(mms_position, label="MMS position", nonzero=False)
    field = _vector(bavg, label="Bavg", nonzero=True)
    try:
        relative_tolerance = float(tolerance)
    except (TypeError, ValueError) as error:
        raise DatasetError(
            "Intersection tolerance must be finite and positive"
        ) from error
    if not np.isfinite(relative_tolerance) or relative_tolerance <= 0.0:
        raise DatasetError("Intersection tolerance must be finite and positive")
    expected = (len(y_values), len(z_values))
    if surface.shape != expected:
        raise DatasetError(f"Bow-shock surface must have shape {expected}")
    if normal_values.shape != expected + (3,):
        raise DatasetError(f"Bow-shock normals must have shape {expected + (3,)}")
    direction = field / np.linalg.norm(field)
    angles = np.full(expected, np.nan, dtype=np.float64)
    valid = np.isfinite(surface)
    if np.isfinite(normal_values[valid]).all():
        angles[valid] = calc_bow_shock_normal_angle(
            normal_values[valid], field, acute=True
        )
    else:
        raise DatasetError("Bow-shock normals must be finite where surface is observed")
    mesh = _build_surface_mesh(surface, normal_values, angles, y=y_values, z=z_values)
    intersections = _line_triangle_intersections(
        mesh, origin=mms, direction=direction, tolerance=relative_tolerance
    )
    if not intersections:
        raise GeometryError(
            "Straight MMS field line does not intersect observed shock coverage"
        )
    return ShockConnection(
        mms, field, direction, y_values, z_values, angles, mesh, tuple(intersections)
    )


def _contour_levels(values: ArrayLike | None) -> NDArray[np.float64]:
    """Return validated contour levels spanning the acute-angle domain."""

    if values is None:
        return np.linspace(0.0, 90.0, 201)
    try:
        levels = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as error:
        raise DatasetError(
            "Contour levels must be finite and strictly increasing"
        ) from error
    if levels.ndim != 1 or levels.size < 2:
        raise DatasetError("Contour levels must contain at least two values")
    if not np.isfinite(levels).all() or np.any(np.diff(levels) <= 0.0):
        raise DatasetError("Contour levels must be finite and strictly increasing")
    if (
        levels[0] != 0.0
        or levels[-1] != 90.0
        or np.any((levels < 0.0) | (levels > 90.0))
    ):
        raise DatasetError("Contour levels must span values between 0 and 90 degrees")
    return levels


def _plot_range(values: ArrayLike, *, label: str) -> tuple[float, float]:
    """Return one finite, increasing plot range."""

    try:
        bounds = np.asarray(values, dtype=float)
    except (TypeError, ValueError) as error:
        raise DatasetError(
            f"{label} must contain two finite increasing values"
        ) from error
    if bounds.shape != (2,) or not np.isfinite(bounds).all() or bounds[0] >= bounds[1]:
        raise DatasetError(f"{label} must contain two finite increasing values")
    return float(bounds[0]), float(bounds[1])


def _connection_plot_limits(
    hit: ShockIntersection,
    *,
    yrange: ArrayLike | None,
    zrange: ArrayLike | None,
) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return explicit or reference-style symmetric Y-Z plot limits."""

    if (yrange is None) != (zrange is None):
        raise DatasetError("yrange and zrange must be supplied together")
    if yrange is not None and zrange is not None:
        return _plot_range(yrange, label="yrange"), _plot_range(zrange, label="zrange")

    maximum = max(abs(float(hit.point[1])), abs(float(hit.point[2])))
    for threshold, limit in ((13.0, 15.0), (18.0, 20.0), (23.0, 25.0)):
        if maximum < threshold:
            return (-limit, limit), (-limit, limit)
    return (-28.0, 28.0), (-28.0, 28.0)


def _draw_reference_contours(
    ax: Axes,
    connection: ShockConnection,
    angles: np.ma.MaskedArray,
) -> None:
    """Draw the optional 45° and 50° reference contours."""

    finite_angles = angles.compressed()
    for threshold, color in ((45.0, "black"), (50.0, "blue")):
        if (
            finite_angles.size
            and finite_angles.min() <= threshold <= finite_angles.max()
        ):
            contour = ax.contour(
                connection.y,
                connection.z,
                angles,
                colors=color,
                linestyles="--",
                linewidths=3.5,
                levels=[threshold],
            )
            ax.clabel(contour, fmt="%1.0f°", fontsize=16, colors=color)


def _toward_center(value: float, bounds: tuple[float, float], step: float) -> float:
    center = 0.5 * (bounds[0] + bounds[1])
    distance = center - value
    return value + np.sign(distance) * min(abs(distance), step)


def _draw_connection_metadata(
    ax: Axes,
    connection: ShockConnection,
    hit: ShockIntersection,
    *,
    simulation_time: str | None,
) -> None:
    """Draw vector, position, and optional timestamp captions."""

    mms = ", ".join(f"{value:.1f}" for value in connection.mms_position)
    field = ", ".join(f"{value:.1f}" for value in connection.bavg)
    point = ", ".join(f"{value:.1f}" for value in hit.point)
    ax.text(
        -0.15, -0.2, f"MMS (GSM): ({mms}) [R$_E$]", transform=ax.transAxes, fontsize=12
    )
    ax.text(0.35, -0.2, f"IMF = ({field}) [nT]", transform=ax.transAxes, fontsize=12)
    ax.text(
        0.7,
        -0.2,
        f"Intersection = ({point}) [R$_E$]",
        transform=ax.transAxes,
        fontsize=12,
    )
    if simulation_time is not None:
        ax.text(
            -0.15,
            -0.3,
            f"Simulation time: {simulation_time}",
            transform=ax.transAxes,
            fontsize=12,
        )


def plot_shock_angle_contour(
    connection: ShockConnection,
    *,
    ax: object | None = None,
    levels: ArrayLike | None = None,
    cmap: str = "viridis",
    yrange: ArrayLike | None = None,
    zrange: ArrayLike | None = None,
    simulation_time: str | None = None,
) -> tuple[Figure, Axes]:
    """Plot the acute shock-normal angle on the extracted Y-Z shock map.

    Matplotlib is imported only when this function is called.  The supplied
    axes is reused and returned; otherwise a new axes is created.  Returns
    ``(figure, axes)`` (a Matplotlib ``Figure`` and ``Axes`` pair).  ``cmap``
    selects the filled-contour colormap, while ``yrange`` and ``zrange`` can
    override the symmetric reference-style default plot limits.
    ``simulation_time`` adds the simulation timestamp to the metadata below
    the plot when supplied.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:  # pragma: no cover - depends on optional extra
        raise ImportError("plot_shock_angle_contour requires matplotlib") from error
    created_figure = ax is None
    if ax is None:
        _, ax = plt.subplots(figsize=(10.0, 8.0))
    angles = np.ma.masked_invalid(np.asarray(connection.theta_bn_deg, dtype=float).T)
    contour_levels = _contour_levels(levels)
    mesh = ax.contourf(
        connection.y,
        connection.z,
        angles,
        levels=contour_levels,
        vmin=0.0,
        vmax=90.0,
        cmap=cmap,
    )
    colorbar = ax.figure.colorbar(mesh, ax=ax)
    colorbar.set_ticks(np.arange(10.0, 91.0, 10.0))
    colorbar.set_label(r"$\theta_{BN}$", fontsize=26)
    colorbar.ax.tick_params(labelsize=22)
    ax.axvline(0.0, color="white", linewidth=1.5, zorder=4)
    ax.axhline(0.0, color="white", linewidth=1.5, zorder=4)
    hit = connection.selected_intersection
    ax.scatter(
        [hit.point[1]],
        [hit.point[2]],
        color="red",
        s=100,
        edgecolors="white",
        zorder=5,
        label="intersection",
    )
    _draw_reference_contours(ax, connection, angles)
    y_limits, z_limits = _connection_plot_limits(hit, yrange=yrange, zrange=zrange)

    ax.text(
        _toward_center(float(hit.point[1]), y_limits, 3.0),
        _toward_center(float(hit.point[2]), z_limits, 2.5),
        f"({hit.theta_bn_deg:.2f}°)",
        color="red",
        fontsize=24,
    )

    _draw_connection_metadata(
        ax,
        connection,
        hit,
        simulation_time=simulation_time,
    )

    ax.set_xlabel(r"Y [R$_E$]", fontsize=26)
    ax.set_ylabel(r"Z [R$_E$]", fontsize=26)
    ax.tick_params(axis="both", labelsize=22, width=2.5, length=9)
    ax.set_xlim(y_limits)
    ax.set_ylim(z_limits)
    ax.set_aspect("equal", adjustable="box")
    # ax.set_title("Bow-shock magnetic connection angle", fontsize=24)
    if created_figure:
        ax.figure.subplots_adjust(bottom=0.22)
    plt.tight_layout()
    return ax.figure, ax


def plot_shock_connection_3d(
    connection: ShockConnection,
    *,
    plotter: pv.Plotter | None = None,
    show: bool = True,
) -> pv.Plotter:
    """Render Earth, the colored shock, MMS, and its straight field connection."""
    if plotter is None:
        plotter = pv.Plotter()
    hit = connection.selected_intersection
    mms = np.asarray(connection.mms_position, dtype=float)
    hit_point = np.asarray(hit.point, dtype=float)
    direction_to_hit = (
        np.asarray(connection.field_direction)
        if hit.line_parameter == 0.0
        else np.sign(hit.line_parameter) * np.asarray(connection.field_direction)
    )
    extension = max(hit.distance * 0.2, 0.1)
    line_end = hit_point + extension * direction_to_hit

    plotter.add_mesh(
        pv.Sphere(radius=1.0), color="cornflowerblue", name="earth", smooth_shading=True
    )
    plotter.add_mesh(
        connection.surface_mesh,
        scalars=ANGLE_NAME,
        clim=(0.0, 90.0),
        cmap="viridis",
        name="bow_shock",
        show_scalar_bar=True,
        scalar_bar_args={"title": r"$\theta_{BN}$", "vertical": True},
    )
    plotter.add_mesh(pv.Sphere(radius=0.08, center=mms), color="red", name="mms")
    plotter.add_mesh(
        pv.Sphere(radius=0.1, center=hit_point), color="yellow", name="intersection"
    )
    plotter.add_mesh(
        pv.Line(mms, line_end), color="white", line_width=4, name="field_line"
    )
    arrow_scale = max(0.5, 0.25 * max(hit.distance, 1.0))
    plotter.add_mesh(
        pv.Arrow(
            start=mms,
            direction=np.asarray(connection.field_direction),
            scale=arrow_scale,
        ),
        color="orange",
        name="bavg_arrow",
    )
    try:
        plotter.add_point_labels(
            np.vstack((mms, hit_point)),
            ["MMS", "intersection"],
            name="connection_labels",
            point_size=0,
            font_size=14,
            shape=None,
            always_visible=True,
        )
    except TypeError:  # compatibility with older PyVista point-label signatures
        plotter.add_point_labels(
            np.vstack((mms, hit_point)),
            ["MMS", "intersection"],
            name="connection_labels",
        )
    plotter.add_axes(
        xlabel=r"X [R$_E$]",
        ylabel=r"Y [R$_E$]",
        zlabel=r"Z [R$_E$]",
    )
    plotter.show_grid()
    if show:
        plotter.show()
    return plotter


__all__ = [
    "ShockConnection",
    "ShockIntersection",
    "analyze_shock_connection",
    "plot_shock_angle_contour",
    "plot_shock_connection_3d",
]
