"""Triangulated bow-shock geometry."""

from dataclasses import dataclass

import numpy as np
import pyvista as pv
from numpy.typing import ArrayLike, NDArray
from scipy.interpolate import griddata
from vtkmodules.vtkCommonDataModel import vtkStaticCellLocator

from shocklink.dataset import (
    calc_velocity_divergence,
    get_x_axis_profile,
    sample_line,
)
from shocklink.exceptions import DatasetError, GeometryError


@dataclass(frozen=True, slots=True)
class BowShockParaboloid:
    """Axisymmetric bow-shock fit directed along the X axis."""

    loc0: ArrayLike
    loc1: ArrayLike
    loc2: ArrayLike
    curvature: float

    def __post_init__(self) -> None:
        for name in ("loc0", "loc1", "loc2"):
            try:
                location = np.array(
                    getattr(self, name),
                    dtype=np.float64,
                    copy=True,
                )
            except (TypeError, ValueError) as error:
                raise GeometryError(
                    f"{name} must contain exactly three finite values"
                ) from error
            if location.shape != (3,):
                raise GeometryError(f"{name} must contain exactly three values")
            if not np.isfinite(location).all():
                raise GeometryError(f"{name} must contain finite values")
            location.setflags(write=False)
            object.__setattr__(self, name, location)

        if not np.allclose(self.loc0[1:], 0.0, rtol=0.0, atol=1.0e-12):
            raise GeometryError("loc0 must lie on the X axis")
        if self.loc1[1] >= 0.0:
            raise GeometryError("loc1 must lie on the negative Y side")
        if self.loc2[1] <= 0.0:
            raise GeometryError("loc2 must lie on the positive Y side")

        try:
            curvature = float(self.curvature)
        except (TypeError, ValueError) as error:
            raise GeometryError("curvature must be a finite positive value") from error
        if not np.isfinite(curvature):
            raise GeometryError("curvature must be finite")
        if curvature <= 0.0:
            raise GeometryError("curvature must be positive")
        object.__setattr__(self, "curvature", curvature)

    def x_at(self, y: ArrayLike, z: ArrayLike) -> np.ndarray:
        """Evaluate the fitted surface at transverse coordinates."""

        y_values = np.asarray(y, dtype=np.float64)
        z_values = np.asarray(z, dtype=np.float64)
        return np.asarray(self.loc0[0] - self.curvature * (y_values**2 + z_values**2))

    def residual_at(
        self,
        x: ArrayLike,
        y: ArrayLike,
        z: ArrayLike,
    ) -> np.ndarray:
        """Return the signed X residual from the fitted surface."""

        return np.asarray(x, dtype=np.float64) - self.x_at(y, z)


@dataclass(frozen=True, slots=True)
class BowShockSurface:
    """A named triangular surface representing a bow shock."""

    vertices: ArrayLike
    faces: ArrayLike
    name: str = "bow_shock"

    def __post_init__(self) -> None:
        vertices = np.array(self.vertices, dtype=np.float64, copy=True)
        raw_faces = np.asarray(self.faces)

        if vertices.ndim != 2 or vertices.shape[1:] != (3,):
            raise GeometryError("surface vertices must be an N x 3 array")
        if len(vertices) < 3:
            raise GeometryError("a surface requires at least three vertices")
        if not np.isfinite(vertices).all():
            raise GeometryError("surface vertices must be finite")
        if raw_faces.ndim != 2 or raw_faces.shape[1:] != (3,):
            raise GeometryError("surface faces must be an M x 3 array")
        if not np.issubdtype(raw_faces.dtype, np.integer):
            raise GeometryError("surface faces must contain integer vertex indices")

        faces = np.array(raw_faces, dtype=np.int64, copy=True)
        if faces.size and (faces.min() < 0 or faces.max() >= len(vertices)):
            raise GeometryError("surface face contains an invalid vertex index")
        if not self.name.strip():
            raise ValueError("surface name must not be empty")

        vertices.setflags(write=False)
        faces.setflags(write=False)
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "faces", faces)


def _valid_profile_samples(
    profile: pv.PolyData,
    *,
    divergence_name: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return profile points, divergence, and a valid-sample mask."""

    if divergence_name not in profile.point_data:
        raise DatasetError(
            f"Line profile is missing divergence array {divergence_name!r}"
        )
    values = np.asarray(profile.point_data[divergence_name])
    if values.shape != (profile.n_points,):
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be a point scalar"
        )
    try:
        valid = np.isfinite(values)
    except TypeError as error:
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be numeric"
        ) from error
    valid &= np.isfinite(profile.points).all(axis=1)
    if "vtkValidPointMask" in profile.point_data:
        point_mask = np.asarray(profile.point_data["vtkValidPointMask"])
        if point_mask.shape != (profile.n_points,):
            raise DatasetError("Line profile has an invalid point mask")
        valid &= point_mask.astype(bool)
    return np.asarray(profile.points), values, valid


def _strongest_compression(
    points: np.ndarray,
    divergence: np.ndarray,
    candidates: np.ndarray,
    *,
    label: str,
) -> np.ndarray:
    """Return the candidate location that maximizes ``-div(U)``."""

    indices = np.flatnonzero(candidates)
    if len(indices) == 0:
        raise DatasetError(f"No valid {label} compression samples were found")
    # Strongest compression is the minimum div(U) among valid candidates.
    selected = indices[np.argmax(-divergence[indices])]
    return np.array(points[selected], dtype=np.float64, copy=True)


def extract_shockfit_range(
    dataset: pv.DataSet,
    *,
    lower: float,
    upper: float,
    shockfit_name: str = "shockfit",
    adjacent_cells: bool = True,
) -> pv.UnstructuredGrid:
    """Extract cells associated with an inclusive shock-fit residual range.

    Parameters
    ----------
    dataset : pyvista.DataSet
        Dataset containing the named point-scalar residual array.
    lower, upper : float
        Finite inclusive limits for ``lower <= shockfit <= upper``.
    shockfit_name : str, default "shockfit"
        Name of the ``(n_points,)`` residual point-data array, usually written by
        :func:`fit_bow_shock`.
    adjacent_cells : bool, default True
        Whether PyVista also extracts cells adjacent to selected points.

    Returns
    -------
    pyvista.UnstructuredGrid
        Extracted cells and points.  Nonfinite residual samples are excluded.

    Raises
    ------
    DatasetError
        If the residual array or limits are invalid, ``lower`` exceeds ``upper``,
        ``adjacent_cells`` is not boolean, or extraction does not produce an
        unstructured grid.
    """

    if not isinstance(shockfit_name, str) or not shockfit_name.strip():
        raise DatasetError("Shockfit array name must not be empty")
    if shockfit_name not in dataset.point_data:
        raise DatasetError(
            f"Shockfit array {shockfit_name!r} is unavailable in point data"
        )
    values = np.asarray(dataset.point_data[shockfit_name])
    if values.shape != (dataset.n_points,):
        raise DatasetError(f"Shockfit array {shockfit_name!r} must be a point scalar")
    try:
        lower_limit = float(lower)
        upper_limit = float(upper)
    except (TypeError, ValueError) as error:
        raise DatasetError("Shockfit range limits must be finite numbers") from error
    if not np.isfinite((lower_limit, upper_limit)).all():
        raise DatasetError("Shockfit range limits must be finite numbers")
    if lower_limit > upper_limit:
        raise DatasetError("Shockfit range lower limit must not exceed upper limit")
    if not isinstance(adjacent_cells, bool):
        raise DatasetError("adjacent_cells must be a boolean")

    try:
        finite = np.isfinite(values)
    except TypeError as error:
        raise DatasetError(
            f"Shockfit array {shockfit_name!r} must be numeric"
        ) from error
    mask = finite & (values >= lower_limit) & (values <= upper_limit)
    try:
        extracted = dataset.extract_points(
            mask,
            adjacent_cells=adjacent_cells,
            include_cells=True,
            pass_point_ids=True,
            pass_cell_ids=True,
        )
    except Exception as error:
        raise DatasetError(f"Could not extract shockfit range: {error}") from error
    if not isinstance(extracted, pv.UnstructuredGrid):
        raise DatasetError(
            "PyVista shockfit extraction returned "
            f"{type(extracted).__name__}; expected UnstructuredGrid"
        )
    return extracted


def _surface_probe_source(
    dataset: pv.DataSet,
    *,
    divergence_name: str,
    divergence: np.ndarray,
) -> pv.DataSet:
    """Return a shallow geometry copy containing only divergence data."""

    source = dataset.copy(deep=False)
    source.point_data.clear()
    source.point_data[divergence_name] = divergence
    source.cell_data.clear()
    source.field_data.clear()
    return source


def _real_numeric_array(
    values: ArrayLike,
    *,
    numeric_message: str,
    complex_message: str,
) -> NDArray[np.float64]:
    """Return a private float64 copy of real numeric input values."""

    try:
        raw_values = np.asarray(values)
    except (TypeError, ValueError, OverflowError) as error:
        raise DatasetError(numeric_message) from error
    if np.iscomplexobj(raw_values):
        raise DatasetError(complex_message)
    if raw_values.dtype.kind not in "iuf":
        raise DatasetError(numeric_message)
    try:
        return np.array(raw_values, dtype=np.float64, copy=True)
    except (TypeError, ValueError, OverflowError) as error:
        raise DatasetError(numeric_message) from error


def _surface_axis(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Return a validated regular-surface coordinate axis."""

    axis = _real_numeric_array(
        values,
        numeric_message=f"{label} coordinates must contain numbers",
        complex_message=f"{label} coordinates must contain real numbers",
    )
    if axis.ndim != 1 or axis.size == 0:
        raise DatasetError(f"{label} coordinates must be a nonempty 1D array")
    if not np.isfinite(axis).all():
        raise DatasetError(f"{label} coordinates must be finite")
    if axis.size > 1 and np.any(np.diff(axis) <= 0.0):
        raise DatasetError(f"{label} coordinates must be strictly increasing")
    return axis


def _normal_axis(values: ArrayLike, *, label: str) -> NDArray[np.float64]:
    """Return a coordinate axis suitable for normal differentiation."""

    axis = _surface_axis(values, label=label)
    if axis.size < 3:
        raise DatasetError(f"{label} coordinates must contain at least three values")
    return axis


def _normal_surface(
    surface_x: ArrayLike,
    *,
    shape: tuple[int, int],
) -> NDArray[np.float64]:
    """Return a validated private copy of a regular bow-shock surface."""

    surface = _real_numeric_array(
        surface_x,
        numeric_message="Bow-shock surface must be numeric",
        complex_message="Bow-shock surface must contain real numbers",
    )
    if surface.shape != shape:
        raise DatasetError(f"Bow-shock surface must have shape {shape}")
    if np.isinf(surface).any():
        raise DatasetError("Bow-shock surface must not contain infinity")
    return surface


def _normal_interpolation_result(
    values: ArrayLike,
    *,
    label: str,
    shape: tuple[int, ...],
) -> NDArray[np.float64]:
    """Return a private real interpolation result with the expected shape."""

    raw_values = np.asarray(values)
    if np.iscomplexobj(raw_values):
        raise ValueError(f"{label} interpolation must return real numbers")
    result = np.array(raw_values, dtype=np.float64, copy=True)
    if result.shape != shape:
        raise ValueError(
            f"{label} interpolation returned shape {result.shape}; expected {shape}"
        )
    return result


def _fill_normal_surface_gaps(
    surface: NDArray[np.float64],
    *,
    y_values: NDArray[np.float64],
    z_values: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Fill missing regular-surface samples before differentiation."""

    valid = np.isfinite(surface)
    if valid.all():
        return surface
    if np.count_nonzero(valid) < 3:
        raise DatasetError(
            "Bow-shock surface must contain at least three finite samples"
        )

    yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
    sample_points = np.column_stack((yy[valid], zz[valid]))
    sample_values = surface[valid]
    try:
        filled_surface = _normal_interpolation_result(
            griddata(
                sample_points,
                sample_values,
                (yy, zz),
                method="linear",
            ),
            label="linear",
            shape=surface.shape,
        )
        if np.isinf(filled_surface).any():
            raise ValueError("linear interpolation output contains infinity")
        missing = np.isnan(filled_surface)
        if missing.any():
            nearest_values = _normal_interpolation_result(
                griddata(
                    sample_points,
                    sample_values,
                    (yy[missing], zz[missing]),
                    method="nearest",
                ),
                label="nearest",
                shape=(int(np.count_nonzero(missing)),),
            )
            filled_surface[missing] = nearest_values
        # Preserve observed samples after interpolation fills only missing cells.
        filled_surface[valid] = surface[valid]
        if not np.isfinite(filled_surface).all():
            raise ValueError("interpolation output contains nonfinite values")
    except Exception as error:
        raise DatasetError(
            f"Could not interpolate bow-shock surface: {error}"
        ) from error

    return filled_surface


def _normal_derivatives(
    surface: NDArray[np.float64],
    *,
    y_values: NDArray[np.float64],
    z_values: NDArray[np.float64],
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return validated coordinate-aware surface derivatives."""

    try:
        # Second-order one-sided stencils retain lower edge accuracy than first order.
        derivatives = np.gradient(
            surface,
            y_values,
            z_values,
            edge_order=2,
        )
    except Exception as error:
        raise DatasetError(
            f"Could not calculate bow-shock surface derivatives: {error}"
        ) from error
    if not isinstance(derivatives, (list, tuple)) or len(derivatives) != 2:
        raise DatasetError(
            "Bow-shock surface derivatives must contain Y and Z components"
        )

    try:
        raw_dx_dy = np.asarray(derivatives[0])
        raw_dx_dz = np.asarray(derivatives[1])
    except (TypeError, ValueError, OverflowError) as error:
        raise DatasetError("Bow-shock surface derivatives must be numeric") from error
    if np.iscomplexobj(raw_dx_dy) or np.iscomplexobj(raw_dx_dz):
        raise DatasetError("Bow-shock surface derivatives must contain real numbers")
    try:
        dx_dy = np.asarray(raw_dx_dy, dtype=np.float64)
        dx_dz = np.asarray(raw_dx_dz, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise DatasetError("Bow-shock surface derivatives must be numeric") from error
    if dx_dy.shape != surface.shape or dx_dz.shape != surface.shape:
        raise DatasetError(
            f"Bow-shock surface derivatives must have shape {surface.shape}"
        )
    if not np.isfinite(dx_dy).all() or not np.isfinite(dx_dz).all():
        raise DatasetError("Bow-shock surface derivatives must be finite")
    return dx_dy, dx_dz


def _normal_components(
    dx_dy: NDArray[np.float64],
    dx_dz: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Construct validated outward unit-normal components."""

    surface_shape = dx_dy.shape
    expected_shape = surface_shape + (3,)
    try:
        # For r(y, z) = (x_s, y, z), r_y x r_z is +X-oriented (1, -dx/dy, -dx/dz).
        outward = np.stack(
            (np.ones(surface_shape, dtype=np.float64), -dx_dy, -dx_dz),
            axis=-1,
        )
    except Exception as error:
        raise DatasetError(f"Could not construct bow-shock normals: {error}") from error
    if outward.shape != expected_shape:
        raise DatasetError(f"Bow-shock normal field must have shape {expected_shape}")
    try:
        outward_is_finite = np.isfinite(outward).all()
    except TypeError as error:
        raise DatasetError("Bow-shock normal components must be numeric") from error
    if not outward_is_finite:
        raise DatasetError("Bow-shock normal components must be finite")

    try:
        # Scale components before normalization to avoid overflow in the magnitude.
        component_scale = np.max(np.abs(outward), axis=-1, keepdims=True)
        scaled_outward = outward / component_scale
        normal_magnitudes = np.hypot(
            np.hypot(scaled_outward[..., 0], scaled_outward[..., 1]),
            scaled_outward[..., 2],
        )
    except Exception as error:
        raise DatasetError(f"Could not normalize bow-shock normals: {error}") from error
    if (
        component_scale.shape != surface_shape + (1,)
        or not np.isfinite(component_scale).all()
        or np.any(component_scale <= 0.0)
        or normal_magnitudes.shape != surface_shape
        or not np.isfinite(normal_magnitudes).all()
        or np.any(normal_magnitudes <= 0.0)
    ):
        raise DatasetError("Bow-shock normal magnitudes must be finite and positive")

    try:
        normals = scaled_outward / normal_magnitudes[..., np.newaxis]
    except Exception as error:
        raise DatasetError(f"Could not normalize bow-shock normals: {error}") from error
    if normals.shape != expected_shape:
        raise DatasetError(f"Bow-shock normal field must have shape {expected_shape}")
    if not np.isfinite(normals).all():
        raise DatasetError("Bow-shock normal components must be finite")
    if not np.all(normals[..., 0] > 0.0):
        raise DatasetError("Bow-shock normal X components must be strictly positive")

    unit_magnitudes = np.hypot(
        np.hypot(normals[..., 0], normals[..., 1]),
        normals[..., 2],
    )
    if not np.allclose(unit_magnitudes, 1.0, rtol=1.0e-12, atol=1.0e-12):
        raise DatasetError("Bow-shock normals must have unit length")
    return normals


def _surface_integer(
    value: int,
    *,
    label: str,
    minimum: int,
) -> int:
    """Return a validated integer surface-extraction option."""

    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        if minimum == 1:
            raise DatasetError(f"{label} must be a positive integer")
        raise DatasetError(f"{label} must be an integer of at least {minimum}")
    result = int(value)
    if result < minimum:
        if minimum == 1:
            raise DatasetError(f"{label} must be a positive integer")
        raise DatasetError(f"{label} must be an integer of at least {minimum}")
    return result


def _surface_divergence(
    dataset: pv.DataSet,
    *,
    divergence_name: str,
) -> np.ndarray:
    """Return validated finite divergence point data."""

    if not isinstance(divergence_name, str) or not divergence_name.strip():
        raise DatasetError("Divergence array name must not be empty")
    if divergence_name not in dataset.point_data:
        raise DatasetError(
            f"Divergence array {divergence_name!r} is unavailable in point data"
        )
    divergence = np.asarray(dataset.point_data[divergence_name])
    if divergence.shape != (dataset.n_points,):
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be a point scalar"
        )
    try:
        finite = np.isfinite(divergence).all()
    except TypeError as error:
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be numeric"
        ) from error
    if not finite:
        raise DatasetError(f"Divergence array {divergence_name!r} must be finite")
    return divergence


def _surface_x_values(
    dataset: pv.DataSet,
    *,
    x_range: tuple[float, float] | None,
    x_resolution: int,
) -> NDArray[np.float64]:
    """Return validated regular X sampling coordinates."""

    if x_range is None:
        bounds = dataset.bounds
        limits = np.asarray(
            (bounds.x_min, bounds.x_max),
            dtype=np.float64,
        )
        label = "Dataset X bounds"
    else:
        try:
            limits = np.asarray(x_range, dtype=np.float64)
        except (TypeError, ValueError) as error:
            raise DatasetError("X range must contain two numbers") from error
        label = "X range"
    if limits.shape != (2,):
        raise DatasetError(f"{label} must contain two values")
    if not np.isfinite(limits).all():
        raise DatasetError(f"{label} must be finite")
    if limits[0] >= limits[1]:
        raise DatasetError(f"{label} must be strictly increasing")
    resolution = _surface_integer(
        x_resolution,
        label="X resolution",
        minimum=2,
    )
    return np.linspace(
        limits[0],
        limits[1],
        resolution,
        dtype=np.float64,
    )


def _refine_surface_minima(
    *,
    x_values: NDArray[np.float64],
    sampled_divergence: np.ndarray,
    valid: np.ndarray,
    minima: np.ndarray,
) -> NDArray[np.float64]:
    """Return bounded three-point parabolic refinements of discrete minima."""

    refined = x_values[minima].astype(np.float64, copy=True)
    interior = (minima > 0) & (minima < len(x_values) - 1)
    rows = np.flatnonzero(interior)
    if not len(rows):
        return refined

    centers = minima[rows]
    left = sampled_divergence[rows, centers - 1]
    center = sampled_divergence[rows, centers]
    right = sampled_divergence[rows, centers + 1]
    neighbors_valid = valid[rows, centers - 1] & valid[rows, centers + 1]
    finite = np.isfinite(left) & np.isfinite(center) & np.isfinite(right)
    strict_minimum = (center < left) & (center < right)
    curvature = left - 2.0 * center + right
    spacing = x_values[1] - x_values[0]

    # A three-point local parabola has vertex offset
    # h * (f_left - f_right) / (2 * (f_left - 2*f_center + f_right)).
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        offset = spacing * (left - right) / (2.0 * curvature)

    # Retain the discrete sample unless the neighbors are valid, the center is a
    # strict bowl-shaped minimum, and its finite vertex remains in the bracket.
    usable = (
        neighbors_valid
        & finite
        & strict_minimum
        & np.isfinite(curvature)
        & (curvature > 0.0)
        & np.isfinite(offset)
        & (np.abs(offset) <= spacing)
    )
    refined_rows = rows[usable]
    refined[refined_rows] += offset[usable]
    return refined


def get_bow_shock_surface(
    dataset: pv.DataSet,
    *,
    y: ArrayLike,
    z: ArrayLike,
    divergence_name: str = "div(U)",
    x_resolution: int = 512,
    x_range: tuple[float, float] | None = None,
    chunk_size: int = 1024,
    refine_minimum: bool = False,
) -> NDArray[np.float64]:
    """Sample strongest-compression X locations on a regular Y-Z grid.

    Parameters
    ----------
    dataset : pyvista.DataSet
        Dataset with a finite scalar divergence point-data array.
    y, z : array-like
        Strictly increasing one-dimensional transverse coordinates.  Their sizes
        define the first and second dimensions of the returned surface.
    divergence_name : str, default "div(U)"
        Name of the finite ``(n_points,)`` divergence point-data array.
    x_resolution : int, default 512
        Number of regular X samples per Y-Z column; it must be at least two.
        Higher X-resolution improves X-location sampling but increases memory per
        column and the total interpolation work.
    x_range : tuple of float, optional
        Finite increasing X sampling bounds.  Dataset X bounds are used when
        omitted.
    chunk_size : int, default 1024
        Positive number of Y-Z columns sampled in each batch.  A larger chunk size
        reduces batch overhead but increases memory because each batch holds
        ``chunk_size * x_resolution`` probe points.
    refine_minimum : bool, default False
        If true, replace eligible interior discrete minima with bounded vertices
        of local three-point parabolas.  The default returns the existing
        discrete sampled minima.

    Returns
    -------
    numpy.ndarray
        Float array ``surface_x`` with shape ``(len(y), len(z))``.  Element
        ``surface_x[i, j]`` is the sampled X position where ``div(U)`` is most
        negative along the column at ``(y[i], z[j])``.  Columns with no valid sampled data
        are ``NaN``; an input dataset with no cells therefore returns all NaNs.

    Raises
    ------
    DatasetError
        If coordinates, divergence data, sampling options, or sampler output are
        invalid, or if PyVista cannot sample the dataset.
    """

    y_values = _surface_axis(y, label="Y")
    z_values = _surface_axis(z, label="Z")
    divergence = _surface_divergence(
        dataset,
        divergence_name=divergence_name,
    )
    x_values = _surface_x_values(
        dataset,
        x_range=x_range,
        x_resolution=x_resolution,
    )
    columns_per_chunk = _surface_integer(
        chunk_size,
        label="Chunk size",
        minimum=1,
    )
    if not isinstance(refine_minimum, bool):
        raise DatasetError("Refine minimum must be a boolean")

    yy, zz = np.meshgrid(y_values, z_values, indexing="ij")
    column_y = yy.reshape(-1)
    column_z = zz.reshape(-1)
    surface = np.full(len(column_y), np.nan, dtype=np.float64)
    if dataset.n_cells == 0:
        return surface.reshape(len(y_values), len(z_values))

    source = _surface_probe_source(
        dataset,
        divergence_name=divergence_name,
        divergence=divergence,
    )
    locator = vtkStaticCellLocator()
    locator.SetDataSet(source)
    locator.BuildLocator()

    for start in range(0, len(column_y), columns_per_chunk):
        stop = min(start + columns_per_chunk, len(column_y))
        count = stop - start
        points = np.empty(
            (count * len(x_values), 3),
            dtype=np.float64,
        )
        points[:, 0] = np.tile(x_values, count)
        points[:, 1] = np.repeat(column_y[start:stop], len(x_values))
        points[:, 2] = np.repeat(column_z[start:stop], len(x_values))

        try:
            sampled = pv.PolyData(points).sample(
                source,
                locator=locator,
                pass_cell_data=False,
                pass_point_data=False,
                pass_field_data=False,
            )
        except Exception as error:
            raise DatasetError(
                f"Could not sample bow-shock surface: {error}"
            ) from error

        expected_points = count * len(x_values)
        if sampled.n_points != expected_points:
            raise DatasetError("Bow-shock sampler returned an unexpected point count")
        if divergence_name not in sampled.point_data:
            raise DatasetError(
                f"Bow-shock sampler is missing sampled divergence {divergence_name!r}"
            )
        if "vtkValidPointMask" not in sampled.point_data:
            raise DatasetError("Bow-shock sampler is missing vtkValidPointMask")
        sampled_divergence = np.asarray(sampled.point_data[divergence_name])
        point_mask = np.asarray(sampled.point_data["vtkValidPointMask"])
        if sampled_divergence.shape != (expected_points,):
            raise DatasetError("Bow-shock sampler returned invalid divergence data")
        if point_mask.shape != (expected_points,):
            raise DatasetError("Bow-shock sampler returned an invalid point mask")
        sampled_divergence = sampled_divergence.reshape(
            count,
            len(x_values),
        )
        valid = point_mask.astype(bool).reshape(count, len(x_values))
        try:
            valid &= np.isfinite(sampled_divergence)
        except TypeError as error:
            raise DatasetError(
                "Bow-shock sampler returned nonnumeric divergence data"
            ) from error

        chunk_surface = np.full(count, np.nan, dtype=np.float64)
        has_valid = valid.any(axis=1)
        candidates = np.where(valid, sampled_divergence, np.inf)
        # Per-column argmin selects the most-negative valid div(U) sample.
        minima = np.argmin(candidates, axis=1)
        chunk_surface[has_valid] = x_values[minima[has_valid]]
        if refine_minimum:
            refined = _refine_surface_minima(
                x_values=x_values,
                sampled_divergence=sampled_divergence,
                valid=valid,
                minima=minima,
            )
            chunk_surface[has_valid] = refined[has_valid]
        surface[start:stop] = chunk_surface

    return surface.reshape(len(y_values), len(z_values))


def calc_bow_shock_normals(
    surface_x: ArrayLike,
    *,
    y: ArrayLike,
    z: ArrayLike,
) -> NDArray[np.float64]:
    """Return outward unit normals for a regular bow-shock surface.

    Parameters
    ----------
    surface_x : array-like
        Real array with shape ``(len(y), len(z))`` whose values represent
        ``x_s(y, z)``.  NaNs mark missing samples and are interpolated before
        differentiation; infinity is not allowed.
    y, z : array-like
        Strictly increasing one-dimensional coordinate arrays, each with at
        least three entries.

    Returns
    -------
    numpy.ndarray
        Unit-normal array ``(nx, ny, nz)`` with shape
        ``surface_x.shape + (3,)``.  Normals use the raw vector
        ``(1, -dx/dy, -dx/dz)`` and are oriented toward +X, so every returned X
        component is strictly positive.

    Raises
    ------
    DatasetError
        If coordinate arrays or surface shape/data are invalid, fewer than three
        finite surface samples are available to fill NaNs, interpolation fails,
        or finite unit normals cannot be calculated.

    Notes
    -----
    NaNs are filled by linear interpolation followed by nearest-neighbor
    interpolation before differentiation.  The function does not mutate
    ``surface_x``.  Second-order edge stencils provide lower edge accuracy.
    """

    y_values = _normal_axis(y, label="Y")
    z_values = _normal_axis(z, label="Z")
    filled_surface = _normal_surface(
        surface_x,
        shape=(len(y_values), len(z_values)),
    )
    filled_surface = _fill_normal_surface_gaps(
        filled_surface,
        y_values=y_values,
        z_values=z_values,
    )

    dx_dy, dx_dz = _normal_derivatives(
        filled_surface,
        y_values=y_values,
        z_values=z_values,
    )
    return _normal_components(dx_dy, dx_dz)


def calc_bow_shock_normal_angle(
    normals: ArrayLike,
    vector: ArrayLike,
) -> NDArray[np.float64]:
    """Return angles between bow-shock normals and a reference vector.

    Parameters
    ----------
    normals : array-like
        Finite real normal vectors with shape ``(..., 3)``.  Each normal must
        have nonzero magnitude.
    vector : array-like
        Finite real reference vector with shape ``(3,)`` and nonzero magnitude.

    Returns
    -------
    numpy.ndarray
        Angles in degrees with shape ``normals.shape[:-1]``.  An outward normal
        aligned with ``vector`` has angle 0 degrees; an opposite normal has
        angle 180 degrees.

    Raises
    ------
    DatasetError
        If either input has an invalid shape or contains nonnumeric, complex,
        nonfinite, or zero-length vectors.
    """

    normal_values = _real_numeric_array(
        normals,
        numeric_message="Bow-shock normals must be numeric",
        complex_message="Bow-shock normals must contain real numbers",
    )
    if normal_values.ndim < 1 or normal_values.shape[-1] != 3:
        raise DatasetError("Bow-shock normals must have shape (..., 3)")
    if not np.isfinite(normal_values).all():
        raise DatasetError("Bow-shock normals must be finite")

    vector_values = _real_numeric_array(
        vector,
        numeric_message="Bow-shock reference vector must be numeric",
        complex_message="Bow-shock reference vector must contain real numbers",
    )
    if vector_values.shape != (3,):
        raise DatasetError("Bow-shock reference vector must have shape (3,)")
    if not np.isfinite(vector_values).all():
        raise DatasetError("Bow-shock reference vector must be finite")

    normal_scales = np.max(np.abs(normal_values), axis=-1)
    vector_scale = np.max(np.abs(vector_values))
    if np.any(normal_scales <= 0.0):
        raise DatasetError("Bow-shock normal magnitudes must be positive")
    if vector_scale <= 0.0:
        raise DatasetError("Bow-shock reference vector magnitude must be positive")

    normal_unit = normal_values / normal_scales[..., np.newaxis]
    normal_unit /= np.linalg.norm(normal_unit, axis=-1, keepdims=True)
    vector_unit = vector_values / vector_scale
    vector_unit /= np.linalg.norm(vector_unit)
    dot_products = np.sum(normal_unit * vector_unit, axis=-1)
    return np.degrees(np.arccos(np.clip(dot_products, -1.0, 1.0)))


def fit_bow_shock(
    dataset: pv.DataSet,
    *,
    divergence_name: str = "div(U)",
    velocity_name: str = "U [km/s]",
    shockfit_name: str = "shockfit",
    x_offset: float = 2.0,
    axis_resolution: int = 1000,
    cross_resolution: int = 1000,
) -> BowShockParaboloid:
    """Detect compression samples and fit an X-directed paraboloid in place.

    Parameters
    ----------
    dataset : pyvista.DataSet
        Dataset sampled along the X axis and a cross line.  It must provide a
        valid velocity vector array when ``divergence_name`` is absent.
    divergence_name : str, default "div(U)"
        Name of the scalar divergence point-data array.  If absent, divergence
        is calculated from ``velocity_name`` and added to ``dataset`` in place.
    velocity_name : str, default "U [km/s]"
        Name of the finite ``(n_points, 3)`` velocity point-data array used to
        calculate divergence when needed.
    shockfit_name : str, default "shockfit"
        Nonempty name for the fitted signed-X residual point-data array.
    x_offset : float, default 2.0
        Positive distance from the nose to the cross-line sampling location.
    axis_resolution, cross_resolution : int, default 1000
        Positive line-sampling resolutions for finding the nose and flank
        compression samples.

    Returns
    -------
    BowShockParaboloid
        Paraboloid ``x = x0 - a(y**2 + z**2)`` fitted from the strongest finite
        compression samples at the X-axis nose and the negative- and positive-Y
        flanks.

    Raises
    ------
    DatasetError
        If names, offset, divergence/velocity data, bounds, profiles, or sampled
        data are invalid, including missing or nonfinite compression samples.
    GeometryError
        If the selected flank locations are degenerate or cannot form a valid
        positive-curvature paraboloid.

    Notes
    -----
    The function mutates ``dataset`` in place by adding ``divergence_name`` when
    needed and always writing a ``(n_points,)`` ``shockfit_name`` residual array.
    Strongest compression maximizes ``-div(U)``, equivalently selecting the
    most-negative div(U) value.  The residual convention is
    ``shockfit = x - x_surface(y, z)``.
    """

    if not isinstance(shockfit_name, str) or not shockfit_name.strip():
        raise DatasetError("Bow-shock shockfit name must not be empty")

    try:
        offset = float(x_offset)
    except (TypeError, ValueError) as error:
        raise DatasetError("Bow-shock X offset must be finite and positive") from error
    if not np.isfinite(offset) or offset <= 0.0:
        raise DatasetError("Bow-shock X offset must be finite and positive")

    if divergence_name not in dataset.point_data:
        calc_velocity_divergence(
            dataset,
            velocity_name=velocity_name,
            output_name=divergence_name,
        )
    source_divergence = np.asarray(dataset.point_data[divergence_name])
    if source_divergence.shape != (dataset.n_points,):
        raise DatasetError(
            f"Divergence array {divergence_name!r} must be a point scalar"
        )

    axis_profile = get_x_axis_profile(
        dataset,
        resolution=axis_resolution,
    )
    axis_points, axis_divergence, axis_valid = _valid_profile_samples(
        axis_profile,
        divergence_name=divergence_name,
    )
    # Select the X-axis nose at the profile's most-negative valid div(U) sample.
    loc0 = _strongest_compression(
        axis_points,
        axis_divergence,
        axis_valid,
        label="X-axis",
    )

    bounds = dataset.bounds
    cross_x = float(loc0[0] - offset)
    if not np.isfinite(cross_x) or cross_x < bounds.x_min or cross_x > bounds.x_max:
        raise DatasetError(
            "Bow-shock cross-line X coordinate lies outside dataset bounds"
        )
    y_min = float(bounds.y_min)
    y_max = float(bounds.y_max)
    if not np.isfinite((y_min, y_max)).all() or y_min >= 0.0 or y_max <= 0.0:
        raise DatasetError(
            "Dataset Y bounds must be finite and span both sides of zero"
        )

    cross_profile = sample_line(
        dataset,
        pointa=(cross_x, y_min, 0.0),
        pointb=(cross_x, y_max, 0.0),
        resolution=cross_resolution,
    )
    cross_points, cross_divergence, cross_valid = _valid_profile_samples(
        cross_profile,
        divergence_name=divergence_name,
    )
    # Select paraboloid flanks independently on the negative- and positive-Y sides.
    loc1 = _strongest_compression(
        cross_points,
        cross_divergence,
        cross_valid & (cross_points[:, 1] < 0.0),
        label="negative-Y",
    )
    loc2 = _strongest_compression(
        cross_points,
        cross_divergence,
        cross_valid & (cross_points[:, 1] > 0.0),
        label="positive-Y",
    )

    side_locations = np.vstack((loc1, loc2))
    radius2 = np.sum(side_locations[:, 1:] ** 2, axis=1)
    delta_x = loc0[0] - side_locations[:, 0]
    denominator = float(np.sum(radius2**2))
    if not np.isfinite(denominator) or denominator <= 0.0:
        raise GeometryError("Bow-shock side locations are degenerate")
    curvature = float(np.sum(radius2 * delta_x) / denominator)

    fit = BowShockParaboloid(
        loc0=loc0,
        loc1=loc1,
        loc2=loc2,
        curvature=curvature,
    )
    x, y, z = np.asarray(dataset.points).T
    dataset.point_data[shockfit_name] = fit.residual_at(x, y, z).copy()
    return fit


__all__ = [
    "BowShockParaboloid",
    "BowShockSurface",
    "calc_bow_shock_normal_angle",
    "calc_bow_shock_normals",
    "extract_shockfit_range",
    "fit_bow_shock",
    "get_bow_shock_surface",
]
