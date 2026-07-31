"""Download MMS FGM and FPI moments with pySPEDAS.

The optional :mod:`pyspedas` dependency is imported only when data is loaded,
so this module can also be imported by tests and notebooks before it is
installed.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pprint import pprint
import sys

import numpy as np


Cadence = str
MMSLoader = Callable[..., Mapping[str, str]]


@dataclass(frozen=True)
class MMSData:
    """Named pytplot variables returned for one MMS probe and cadence."""

    cadence: Cadence
    series: Mapping[str, str]


@dataclass(frozen=True)
class _TimeSeries:
    """Resolved pytplot values together with their source metadata."""

    times: np.ndarray
    values: np.ndarray
    name: str | None
    units: str | None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for one MMS data interval."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="Start time, e.g. '2015-10-16 13:06:00'.")
    parser.add_argument("--end", required=True, help="End time, e.g. '2015-10-16 13:07:00'.")
    parser.add_argument("--probe", type=int, default=1, choices=range(1, 5), help="MMS probe (1-4).")
    parser.add_argument(
        "--mode",
        choices=("auto", "brst", "fast"),
        default="auto",
        help="Cadence: auto prefers burst and falls back to fast (default).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Download, summarize, and display one MMS data interval."""
    arguments = parse_args(argv)
    try:
        data = load_mms_data(
            arguments.start, arguments.end, probe=arguments.probe, mode=arguments.mode
        )
    except Exception as error:
        print(f"Could not download MMS data: {error}", file=sys.stderr)
        return 1
    if not data.series:
        print(
            "No MMS data were available for this interval. Try --mode fast or another time range.",
            file=sys.stderr,
        )
        return 1

    try:
        print(f"Loaded MMS{arguments.probe} {data.cadence} data.")
        pprint(summarize_data(data))
        figure = plot_mms_data(data)
        figure.show()
    except Exception as error:
        print(f"Could not analyze MMS data: {error}", file=sys.stderr)
        return 1
    return 0


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
    # FPI's survey product is called ``fast``; the corresponding FGM survey
    # product is named ``srvy`` in the MMS archive.
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
    loaded = set(fgm_variables or []) | set(fpi_variables or [])
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
    }
    start_time = _parse_utc_time(start)
    end_time = _parse_utc_time(end)
    return {
        name: variable
        for name, variable in expected.items()
        if variable in loaded and _has_samples_in_interval(variable, start_time, end_time)
    }


def summarize_data(data: MMSData) -> dict[str, dict[str, float] | dict[str, dict[str, float]]]:
    """Return finite-value statistics for each loaded MMS time series.

    Scalar products are summarized directly.  Vector products are summarized
    by their GSE ``x``, ``y``, and ``z`` components.
    """
    summary: dict[str, dict[str, float] | dict[str, dict[str, float]]] = {}
    for name, product in _resolve_series(data).items():
        values = product.values
        if values.ndim == 1:
            summary[name] = _statistics(values)
            continue

        components: dict[str, dict[str, float]] = {}
        for index in range(values.shape[1]):
            label = ("x", "y", "z")[index] if index < 3 else f"component_{index}"
            components[label] = _statistics(values[:, index])
        summary[name] = components
    return summary


def plot_mms_data(data: MMSData):
    """Plot all available MMS magnetic-field and FPI moment products.

    The figure contains only panels whose source products are available.
    """
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError as error:  # pragma: no cover - optional dependency
        raise ImportError(
            "MMS plotting requires Matplotlib; install it with `pip install -e '.[mms]'`."
        ) from error

    series = _resolve_series(data)
    panels: list[Callable[[object], None]] = []

    if "magnetic_field" in series:
        panels.append(lambda axis: _plot_magnetic_field(axis, series["magnetic_field"]))
    densities = [name for name in ("ion_density", "electron_density") if name in series]
    if densities:
        panels.append(lambda axis: _plot_density(axis, series, densities))
    for species in ("ion", "electron"):
        name = f"{species}_velocity"
        if name in series:
            panels.append(
                lambda axis, name=name, species=species: _plot_vector(
                    axis, series[name], f"{species.title()} velocity", "km/s"
                )
            )
    for species in ("ion", "electron"):
        for suffix, label in (
            ("temperature", "temperature"),
            ("temperature_parallel", "parallel temperature"),
            ("temperature_perpendicular", "perpendicular temperature"),
        ):
            name = f"{species}_{suffix}"
            if name in series:
                panels.append(
                    lambda axis, name=name, title=f"{species.title()} {label}": _plot_scalar(
                        axis, series[name], title, "eV"
                    )
                )

    if not panels:
        raise ValueError("No plot-able MMS time series were loaded.")

    figure, axes = plt.subplots(
        len(panels),
        1,
        sharex=True,
        squeeze=False,
        figsize=(12, max(6, 2 * len(panels))),
    )
    flat_axes = axes[:, 0]
    for axis, draw_panel in zip(flat_axes, panels, strict=True):
        draw_panel(axis)
        axis.legend(loc="best")
        axis.grid(visible=True, alpha=0.3)
    time_locator = mdates.AutoDateLocator()
    flat_axes[-1].xaxis.set_major_locator(time_locator)
    flat_axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S", tz=UTC))
    flat_axes[-1].set_xlabel(f"Time (UTC)\n{_date_caption(series)}")
    figure.suptitle(f"MMS {data.cadence} data")
    figure.tight_layout()
    return figure


def _resolve_series(data: MMSData) -> dict[str, _TimeSeries]:
    """Resolve pytplot names at the plotting boundary and retain timestamps."""
    try:
        from pytplot import get_data
    except ImportError as error:  # pragma: no cover - optional dependency
        raise ImportError(
            "MMS analysis requires pySPEDAS; install it with `pip install -e '.[mms]'`."
        ) from error

    resolved: dict[str, _TimeSeries] = {}
    for name, variable in data.series.items():
        product = get_data(variable)
        if product is None:
            continue
        try:
            times, values = product.times, product.y
        except AttributeError:
            times, values = product[0], product[1]
        values_array = np.asarray(values)
        if values_array.ndim not in (1, 2) or not len(values_array):
            continue
        try:
            metadata = get_data(variable, metadata=True) or {}
        except TypeError:
            metadata = {}
        resolved[name] = _TimeSeries(
            times=_to_datetime64(times),
            values=values_array,
            name=_metadata_text(metadata, "name"),
            units=_metadata_text(metadata, "units"),
        )
    return resolved


def _to_datetime64(times: object) -> np.ndarray:
    """Convert pySPEDAS Unix timestamps to calendar timestamps for plotting."""
    timestamps = np.asarray(times)
    if np.issubdtype(timestamps.dtype, np.datetime64):
        return timestamps
    return timestamps.astype("datetime64[s]")


def _parse_utc_time(value: str) -> float:
    """Parse the ISO-like time strings accepted by the MMS example."""
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp.timestamp()


def _has_samples_in_interval(variable: str, start: float, end: float) -> bool:
    """Return whether a pytplot variable has data inside the requested interval."""
    from pytplot import get_data

    product = get_data(variable)
    if product is None:
        return False
    try:
        times = product.times
    except AttributeError:
        times = product[0]
    timestamps = np.asarray(times)
    if not len(timestamps):
        return False
    if np.issubdtype(timestamps.dtype, np.datetime64):
        timestamps = timestamps.astype("datetime64[ns]").astype(np.int64) / 1_000_000_000
    return bool(np.any((timestamps >= start) & (timestamps <= end)))


def _date_caption(series: Mapping[str, _TimeSeries]) -> str:
    """Format the first plotted UTC date in the same compact style as MMS plots."""
    earliest = min(np.min(product.times) for product in series.values())
    day = np.datetime_as_string(earliest.astype("datetime64[D]"), unit="D")
    return datetime.strptime(day, "%Y-%m-%d").strftime("%Y %b %d")


def _statistics(values: np.ndarray) -> dict[str, float]:
    finite_values = values[np.isfinite(values)]
    if not len(finite_values):
        return {"count": 0, "mean": float("nan"), "min": float("nan"), "max": float("nan")}
    return {
        "count": int(len(finite_values)),
        "mean": float(np.mean(finite_values)),
        "min": float(np.min(finite_values)),
        "max": float(np.max(finite_values)),
    }


def _metadata_text(metadata: object, field: str) -> str | None:
    """Read common pytplot metadata locations, accepting incomplete products."""
    if not isinstance(metadata, Mapping):
        return None
    if field == "name":
        candidates = (
            metadata.get("name"),
            metadata.get("var_name"),
            _nested_metadata(metadata, "plot_options", "ytitle"),
            _nested_metadata(metadata, "plot_options", "yaxis_opt", "axis_label"),
        )
    else:
        candidates = (
            _nested_metadata(metadata, "plot_options", "yaxis_opt", "axis_subtitle"),
            metadata.get("units"),
            _nested_metadata(metadata, "data_att", "units"),
            _nested_metadata(metadata, "plot_options", "yaxis_opt", "units"),
        )
    return next((str(value) for value in candidates if value), None)


def _nested_metadata(metadata: Mapping[str, object], *keys: str) -> object | None:
    value: object = metadata
    for key in keys:
        if not isinstance(value, Mapping):
            return None
        value = value.get(key)
    return value


def _axis_label(product: _TimeSeries, fallback_name: str, fallback_units: str) -> str:
    name = product.name or fallback_name
    units = product.units or fallback_units
    if units.startswith("[") and units.endswith("]"):
        return f"{name} {units}"
    return f"{name} ({units})" if units else name


def _plot_magnetic_field(axis: object, product: _TimeSeries) -> None:
    _plot_vector(axis, product, "B", "nT")
    times, values = product.times, product.values
    if values.ndim == 2 and values.shape[1] >= 3:
        axis.plot(times, np.linalg.norm(values[:, :3], axis=1), label=f"{product.name or 'B'} magnitude")


def _plot_density(
    axis: object,
    series: Mapping[str, _TimeSeries],
    names: list[str],
) -> None:
    for name in names:
        product = series[name]
        axis.plot(product.times, product.values, label=product.name or name.removesuffix("_density").title())
    axis.set_ylabel(_axis_label(series[names[0]], "Density", "cm⁻³"))


def _plot_vector(axis: object, product: _TimeSeries, fallback_name: str, fallback_units: str) -> None:
    times, values = product.times, product.values
    label = product.name or fallback_name
    if values.ndim == 1:
        axis.plot(times, values, label=label)
    else:
        for index in range(min(values.shape[1], 3)):
            component = ("x", "y", "z")[index]
            axis.plot(times, values[:, index], label=f"{label} {component}")
    axis.set_ylabel(_axis_label(product, fallback_name, fallback_units))


def _plot_scalar(axis: object, product: _TimeSeries, fallback_name: str, fallback_units: str) -> None:
    axis.plot(product.times, product.values, label=product.name or fallback_name)
    axis.set_ylabel(_axis_label(product, fallback_name, fallback_units))


if __name__ == "__main__":
    raise SystemExit(main())
