"""MMS pySPEDAS loading and coordinate conversion."""

from __future__ import annotations

from collections.abc import Callable, Mapping

import numpy as np

from shocklink.utilities import TimeBounds

from .data import CoordinateSystem, MMSData, _get_tplot_data


MMSLoader = Callable[..., Mapping[str, str]]
VECTOR_SERIES = ("magnetic_field", "ion_velocity", "electron_velocity")


def load_mms_data(
    start: str,
    end: str,
    probe: int = 1,
    mode: str = "auto",
    loader: MMSLoader | None = None,
    coordinates: CoordinateSystem = "gse",
) -> MMSData:
    """Load MMS magnetic field and FPI moments for one interval."""
    if mode not in {"auto", "brst", "fast"}:
        raise ValueError("mode must be one of 'auto', 'brst', or 'fast'")
    if coordinates not in {"gse", "gsm"}:
        raise ValueError("coordinates must be either 'gse' or 'gsm'")
    TimeBounds.from_strings(start, end)

    load = loader or _load_pyspedas_products
    cadences = ("brst", "fast") if mode == "auto" else (mode,)
    for cadence in cadences:
        series = dict(
            load(
                start=start,
                end=end,
                probe=probe,
                cadence=cadence,
                coordinates=coordinates,
            )
        )
        mms_products = {
            name: variable
            for name, variable in series.items()
            if name != "omni_temperature"
        }
        if any(mms_products.values()) or mode != "auto":
            return MMSData(
                cadence=cadence,
                series=series,
                probe=probe,
                coordinates=coordinates,
                start=start,
                end=end,
            )

    return MMSData(
        cadence="fast",
        series={},
        probe=probe,
        coordinates=coordinates,
        start=start,
        end=end,
    )


def _load_pyspedas_products(
    *,
    start: str,
    end: str,
    probe: int,
    cadence: str,
    coordinates: CoordinateSystem = "gse",
) -> Mapping[str, str]:
    """Request MMS products and return the available pytplot names."""
    try:
        from pyspedas import projects
        mms = projects.mms
    except ImportError as error:  # pragma: no cover - optional dependency
        raise ImportError("MMS analysis requires the installed pySPEDAS package.") from error

    trange = [start, end]
    omni_loader = getattr(projects, "omni", None)
    if omni_loader is not None:
        omni_loader.data(
            trange=trange,
            datatype="1min",
            level="hro",
            varnames=["T"],
            time_clip=True,
        )
    probe_id = str(probe)
    fgm_cadence = "srvy" if cadence == "fast" else cadence
    fgm_variables = mms.fgm(
        trange=trange,
        probe=probe_id,
        data_rate=fgm_cadence,
        level="l2",
        varformat="*_fgm_b_gse_*",
        time_clip=True,
    )
    fpi_variables = mms.fpi(
        trange=trange,
        probe=probe_id,
        data_rate=cadence,
        level="l2",
        datatype=["dis-moms", "des-moms"],
        varformat=["*numberdensity*", "*bulkv_gse*", "*temp*"],
        time_clip=True,
    )
    mec_variables: list[str] = []
    mec_loader = getattr(mms, "mec", None)
    if callable(mec_loader):
        mec_cadence = "srvy" if cadence == "fast" else cadence
        mec_variables = mec_loader(
            trange=trange,
            probe=probe_id,
            data_rate=mec_cadence,
            level="l2",
            varformat="*_r_gsm",
            time_clip=True,
        ) or []

    loaded = set(fgm_variables or []) | set(fpi_variables or []) | set(mec_variables)
    prefix = f"mms{probe_id}_"
    expected = {
        "magnetic_field": f"{prefix}fgm_b_gse_{fgm_cadence}_l2_bvec",
        "ion_density": f"{prefix}dis_numberdensity_{cadence}",
        "electron_density": f"{prefix}des_numberdensity_{cadence}",
        "ion_velocity": f"{prefix}dis_bulkv_gse_{cadence}",
        "electron_velocity": f"{prefix}des_bulkv_gse_{cadence}",
        "ion_temperature": f"{prefix}dis_temp_{cadence}",
        "electron_temperature": f"{prefix}des_temp_{cadence}",
        "ion_temperature_parallel": f"{prefix}dis_temppara_{cadence}",
        "electron_temperature_parallel": f"{prefix}des_temppara_{cadence}",
        "ion_temperature_perpendicular": f"{prefix}dis_tempperp_{cadence}",
        "electron_temperature_perpendicular": f"{prefix}des_tempperp_{cadence}",
        "satellite_location": f"{prefix}mec_r_gsm",
        "omni_temperature": "T",
    }
    bounds = TimeBounds.from_strings(start, end)
    start_time, end_time = bounds.unix
    selected = {
        name: variable
        for name, variable in expected.items()
        if variable in loaded and _has_samples_in_interval(variable, start_time, end_time)
    }
    if omni_loader is not None and _has_samples_in_interval("T", start_time, end_time):
        selected["omni_temperature"] = "T"
    return _convert_vector_coordinates(selected, coordinates)


def _has_samples_in_interval(variable: str, start: float, end: float) -> bool:
    """Return whether a pytplot variable has data inside the interval."""
    product = _get_tplot_data(variable)
    if product is None:
        return False
    try:
        times = product.times
    except AttributeError:
        times = product[0]
    timestamps = np.asarray(times)
    if not len(timestamps):
        return False
    if timestamps.dtype.kind == "M":
        timestamps = timestamps.astype("datetime64[ns]").astype("int64") / 1_000_000_000
    return bool(np.any((timestamps >= start) & (timestamps <= end)))


def _converted_variable_name(variable: str, coordinates: CoordinateSystem) -> str:
    token = "_gse_"
    if token in variable:
        return variable.replace(token, f"_{coordinates}_", 1)
    return f"{variable}_{coordinates}"


def _convert_vector_coordinates(
    series: Mapping[str, str], coordinates: CoordinateSystem
) -> dict[str, str]:
    converted = dict(series)
    if coordinates == "gse":
        return converted

    available = [
        (product_name, converted[product_name])
        for product_name in VECTOR_SERIES
        if product_name in converted
    ]
    if not available:
        return converted

    try:
        from pyspedas import cotrans
    except ImportError as error:  # pragma: no cover - optional dependency
        raise ImportError("GSM conversion requires the installed pySPEDAS package.") from error

    for product_name, source in available:
        destination = _converted_variable_name(source, coordinates)
        try:
            result = cotrans(
                name_in=source,
                name_out=destination,
                coord_in="gse",
                coord_out=coordinates,
            )
        except Exception as error:
            raise RuntimeError(
                f"Could not convert MMS vector {source!r} from GSE to GSM."
            ) from error
        if result != 1:
            raise RuntimeError(
                f"Could not convert MMS vector {source!r} from GSE to GSM."
            )
        converted[product_name] = destination
    return converted
