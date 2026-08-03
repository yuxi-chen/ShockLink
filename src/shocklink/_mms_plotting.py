"""Matplotlib rendering for MMS observations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial

import numpy as np

from shocklink._mms_data import (
    MMSData,
    ResolvedSeries,
    TimeBounds,
    _ev_to_kelvin,
    _kelvin_to_ev,
    _mean_position_earth_radii,
    _resolve_series,
    _total_temperature,
)


PLOT_LINE_WIDTH = 0.75


@dataclass(frozen=True)
class PlotPanel:
    kind: str
    product: ResolvedSeries
    renderer: Callable[[object, ResolvedSeries], None]


def _build_panels(series: Mapping[str, ResolvedSeries]) -> list[PlotPanel]:
    panels: list[PlotPanel] = []
    product = series.get("magnetic_field")
    if product is not None:
        panels.append(PlotPanel("magnetic_field", product, _plot_magnetic_field))
    product = series.get("ion_density")
    if product is not None:
        panels.append(PlotPanel("ion_density", product, _plot_density))
    product = series.get("ion_velocity")
    if product is not None:
        panels.append(
            PlotPanel(
                "ion_velocity",
                product,
                partial(_plot_vector, fallback_name=r"$V_i$", fallback_units="[km/s]"),
            )
        )
    for species, symbol in (("ion", "i"), ("electron", "e")):
        temperature = _total_temperature(series, species)
        if temperature is not None:
            panels.append(
                PlotPanel(
                    f"{species}_temperature",
                    temperature,
                    partial(_plot_temperature, fallback_name=rf"$T_{symbol}$"),
                )
            )
    return panels


def plot_mms_data(data: MMSData):
    """Plot all available MMS products using the established panel layout."""
    try:
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
    except ImportError as error:  # pragma: no cover - optional dependency
        raise ImportError(
            "MMS plotting requires Matplotlib; install it with `pip install -e '.[mms]'`."
        ) from error

    series = _resolve_series(data)
    panels = _build_panels(series)
    if not panels:
        raise ValueError("No plot-able MMS time series were loaded.")

    figure, axes = plt.subplots(
        len(panels),
        1,
        sharex=True,
        squeeze=False,
        figsize=(10, max(5, 1.5 * len(panels))),
    )
    flat_axes = axes[:, 0]
    for axis, panel in zip(flat_axes, panels, strict=True):
        panel.renderer(axis, panel.product)
        handles, _ = axis.get_legend_handles_labels()
        if handles:
            axis.legend(
                loc="best",
                ncols=len(handles),
                columnspacing=0.8,
                handletextpad=0.3,
                borderaxespad=0.2,
            )
        axis.grid(visible=True, alpha=0.3)

    time_locator = mdates.AutoDateLocator()
    flat_axes[-1].xaxis.set_major_locator(time_locator)
    flat_axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S", tz=UTC))
    if data.start is not None and data.end is not None:
        bounds = TimeBounds.from_strings(data.start, data.end)
        flat_axes[-1].set_xlim(bounds.start, bounds.end)
    flat_axes[-1].set_xlabel(f"Time (UTC)\n{_date_caption(series)}")

    spacecraft = f"MMS{data.probe}" if data.probe is not None else "MMS"
    title = f"{spacecraft} {data.cadence} data ({data.coordinates.upper()})"
    position_caption = _position_caption(series, spacecraft)
    if position_caption is not None:
        title = f"{title}\n{position_caption}"
    figure.suptitle(title)
    figure.tight_layout(h_pad=0.1)
    figure.subplots_adjust(hspace=0.02)
    return figure


def _date_caption(series: Mapping[str, ResolvedSeries]) -> str:
    earliest = min(np.min(product.times) for product in series.values())
    day = np.datetime_as_string(earliest.astype("datetime64[D]"), unit="D")
    return datetime.strptime(day, "%Y-%m-%d").strftime("%Y %b %d")


def _position_caption(
    series: Mapping[str, ResolvedSeries], spacecraft: str
) -> str | None:
    mean = _mean_position_earth_radii(series)
    if mean is None:
        return None
    return (
        f"{spacecraft} position (GSM): "
        f"({mean[0]:.2f}, {mean[1]:.2f}, {mean[2]:.2f}) $R_E$"
    )


def _axis_label(product: ResolvedSeries, fallback_name: str, fallback_units: str) -> str:
    units = product.units or fallback_units
    if units.startswith("[") and units.endswith("]"):
        return f"{fallback_name} {units}"
    return f"{fallback_name} ({units})" if units else fallback_name


def _plot_magnetic_field(axis: object, product: ResolvedSeries) -> None:
    _plot_vector(axis, product, fallback_name=r"$B$", fallback_units="[nT]")
    if product.values.ndim == 2 and product.values.shape[1] >= 3:
        axis.plot(
            product.times,
            np.linalg.norm(product.values[:, :3], axis=1),
            color="black",
            linewidth=PLOT_LINE_WIDTH,
            label=r"$|B|$",
        )


def _plot_density(axis: object, product: ResolvedSeries) -> None:
    axis.plot(product.times, product.values, linewidth=PLOT_LINE_WIDTH)
    axis.set_ylabel(r"$n$ [/cm$^3$]")


def _plot_vector(
    axis: object,
    product: ResolvedSeries,
    fallback_name: str,
    fallback_units: str,
) -> None:
    times, values = product.times, product.values
    if values.ndim == 1:
        axis.plot(times, values, linewidth=PLOT_LINE_WIDTH, label=fallback_name)
    else:
        for index in range(min(values.shape[1], 3)):
            component = ("x", "y", "z")[index]
            axis.plot(
                times,
                values[:, index],
                color=("blue", "green", "red")[index],
                linewidth=PLOT_LINE_WIDTH,
                label=_vector_component_label(fallback_name, component),
            )
    axis.set_ylabel(_axis_label(product, fallback_name, fallback_units))


def _plot_temperature(
    axis: object,
    product: ResolvedSeries,
    fallback_name: str,
) -> None:
    from matplotlib.ticker import FuncFormatter

    axis.plot(product.times, product.values, linewidth=PLOT_LINE_WIDTH)
    axis.set_ylabel(f"{fallback_name} [eV]")
    kelvin_axis = axis.secondary_yaxis(
        "right", functions=(_ev_to_kelvin, _kelvin_to_ev)
    )
    kelvin_axis.set_ylabel("[K]")
    kelvin_axis.yaxis.set_major_formatter(FuncFormatter(_format_kelvin_tick))


def _format_kelvin_tick(value: float, _position: float | None = None) -> str:
    if value == 0:
        return "0"
    exponent = int(np.floor(np.log10(abs(value))))
    if abs(exponent) >= 3:
        coefficient = value / 10**exponent
        return rf"${coefficient:g}\times10^{{{exponent}}}$"
    return f"{value:g}"


def _vector_component_label(fallback_name: str, component: str) -> str:
    symbol = fallback_name.strip("$")
    if symbol == "V_i":
        return rf"$V_{{i,{component}}}$"
    return rf"${symbol}_{component}$"
