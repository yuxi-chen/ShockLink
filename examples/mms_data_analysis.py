"""Download MMS FGM and FPI moments with pySPEDAS.

The optional :mod:`pyspedas` dependency is imported only when data is loaded,
so this module can also be imported by tests and notebooks before it is
installed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass


Cadence = str
MMSLoader = Callable[..., Mapping[str, str]]


@dataclass(frozen=True)
class MMSData:
    """Named pytplot variables returned for one MMS probe and cadence."""

    cadence: Cadence
    series: Mapping[str, str]


def load_mms_data(
    start: str,
    end: str,
    probe: int = 1,
    mode: str = "auto",
    loader: MMSLoader | None = None,
) -> MMSData:
    """Load MMS magnetic field and ion/electron FPI moments.

    ``mode='auto'`` requests burst data first and uses fast survey data only
    when the burst request returns no usable time series.  Explicit ``brst``
    and ``fast`` modes make a single request.
    """
    if mode not in {"auto", "brst", "fast"}:
        raise ValueError("mode must be one of 'auto', 'brst', or 'fast'")

    load = loader or _load_pyspedas_products
    cadences = ("brst", "fast") if mode == "auto" else (mode,)
    for cadence in cadences:
        series = dict(load(start=start, end=end, probe=probe, cadence=cadence))
        if _has_usable_series(series) or mode != "auto":
            return MMSData(cadence=cadence, series=series)

    # ``auto`` always has at least the two cadences above.  This makes the
    # return type explicit if a future cadence set becomes empty.
    return MMSData(cadence="fast", series={})


def _has_usable_series(series: Mapping[str, str]) -> bool:
    return any(series.values())


def _load_pyspedas_products(
    *, start: str, end: str, probe: int, cadence: Cadence
) -> Mapping[str, str]:
    """Load the requested cadence and return the available moment variables."""
    try:
        from pyspedas.projects import mms
    except ImportError as error:  # pragma: no cover - exercised without optional extra
        raise ImportError(
            "MMS analysis requires pySPEDAS; install it with `pip install -e '.[mms]'`."
        ) from error

    trange = [start, end]
    probe_id = str(probe)
    fgm_variables = mms.fgm(
        trange=trange,
        probe=probe_id,
        data_rate=cadence,
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
    loaded = set(fgm_variables or []) | set(fpi_variables or [])
    prefix = f"mms{probe_id}_"
    expected = {
        "magnetic_field": f"{prefix}fgm_b_gse_{cadence}_l2_bvec",
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
    }
    return {name: variable for name, variable in expected.items() if variable in loaded}
