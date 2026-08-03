from __future__ import annotations

import sys
from types import SimpleNamespace

import matplotlib

matplotlib.use("Agg")
from matplotlib import dates as mdates
import numpy as np

from shocklink.mms.data import _resolve_series
from shocklink.mms.plotting import _build_panels
from shocklink.mms import MMSData, plot_mms_data


def test_build_panels_returns_fixed_default_order(mms_data) -> None:
    panels = _build_panels(_resolve_series(mms_data))

    assert [panel.kind for panel in panels] == [
        "magnetic_field",
        "ion_density",
        "ion_velocity",
        "ion_temperature",
        "electron_temperature",
    ]


def test_plot_mms_data_draws_available_products(mms_data) -> None:
    figure = plot_mms_data(mms_data)

    assert len(figure.axes) == 5
    assert figure._suptitle.get_text() == (
        "MMS1 brst data (GSE)\nMMS1 position (GSM): (1.00, -0.50, 0.10) $R_E$"
    )
    assert figure.get_size_inches().tolist() == [10.0, 7.5]
    vertical_gap = figure.axes[0].get_position().y0 - figure.axes[1].get_position().y1
    assert vertical_gap < 0.02
    assert isinstance(figure.axes[-1].xaxis.get_major_formatter(), mdates.DateFormatter)
    assert figure.axes[-1].xaxis.get_major_formatter().fmt == "%H:%M:%S"
    assert figure.axes[-1].get_xlabel() == "Time (UTC)\n1970 Jan 01"
    assert np.issubdtype(figure.axes[0].lines[0].get_xdata().dtype, np.datetime64)
    assert figure.axes[0].get_ylabel() == r"$B$ [nT]"
    assert [line.get_color() for line in figure.axes[0].lines] == [
        "blue",
        "green",
        "red",
        "black",
    ]
    assert [line.get_label() for line in figure.axes[0].lines] == [
        r"$B_x$",
        r"$B_y$",
        r"$B_z$",
        r"$|B|$",
    ]
    assert figure.axes[0].get_legend()._ncols == 4
    assert figure.axes[1].get_ylabel() == r"$n$ [/cm$^3$]"
    assert figure.axes[1].get_legend() is None
    assert figure.axes[2].get_ylabel() == r"$V_i$ [km/s]"
    assert [line.get_label() for line in figure.axes[2].lines] == [
        r"$V_{i,x}$",
        r"$V_{i,y}$",
        r"$V_{i,z}$",
    ]
    assert figure.axes[3].get_ylabel() == r"$T_i$ [eV]"
    assert figure.axes[4].get_ylabel() == r"$T_e$ [eV]"
    assert figure.axes[3].get_legend() is None
    assert figure.axes[4].get_legend() is None
    assert figure.axes[3].child_axes[0].get_ylabel() == "[K]"
    assert figure.axes[4].child_axes[0].get_ylabel() == "[K]"
    figure.canvas.draw()
    assert figure.axes[3].child_axes[0].yaxis.get_offset_text().get_text() == ""
    assert figure.axes[4].child_axes[0].yaxis.get_offset_text().get_text() == ""


def test_plot_mms_data_uses_exact_requested_time_limits(monkeypatch) -> None:
    product = SimpleNamespace(
        times=np.array([0.0, 10.0, 20.0]),
        y=np.array([1.0, 2.0, 3.0]),
    )
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(get_data=lambda *_args, **_kwargs: product),
    )

    figure = plot_mms_data(
        MMSData(
            cadence="fast",
            series={"ion_density": "density"},
            start="1970-01-01 00:00:10",
            end="1970-01-01 00:00:20",
        )
    )

    np.testing.assert_allclose(
        figure.axes[0].get_xlim(),
        mdates.date2num(
            np.array(
                ["1970-01-01T00:00:10", "1970-01-01T00:00:20"],
                dtype="datetime64[s]",
            )
        ),
    )


def test_plot_mms_data_rejects_empty_products() -> None:
    import pytest

    with pytest.raises(ValueError, match="No plot-able"):
        plot_mms_data(MMSData(cadence="fast", series={}))
