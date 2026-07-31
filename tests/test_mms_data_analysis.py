from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from mms_data_analysis import (
    MMSData,
    _load_pyspedas_products,
    load_mms_data,
    parse_args,
    plot_mms_data,
    summarize_data,
)


@pytest.fixture
def mms_data(monkeypatch: pytest.MonkeyPatch) -> MMSData:
    timestamps = np.array([0.0, 1.0, 2.0])
    values = {
        "b": np.array([[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]]),
        "ni": np.array([1.0, 2.0, 3.0]),
        "ne": np.array([4.0, 5.0, 6.0]),
        "vi": np.array([[10.0, 20.0, 30.0], [20.0, 40.0, 60.0], [30.0, 60.0, 90.0]]),
        "te": np.array([100.0, 200.0, 300.0]),
    }
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda name: SimpleNamespace(times=timestamps, y=values[name])
        ),
    )
    return MMSData(
        cadence="brst",
        series={
            "magnetic_field": "b",
            "ion_density": "ni",
            "electron_density": "ne",
            "ion_velocity": "vi",
            "electron_temperature": "te",
        },
    )


def test_summarize_data_reports_scalar_and_vector_component_statistics(
    mms_data: MMSData,
) -> None:
    summary = summarize_data(mms_data)

    assert summary["ion_density"] == {
        "count": 3,
        "mean": 2.0,
        "min": 1.0,
        "max": 3.0,
    }
    assert summary["magnetic_field"]["x"] == {
        "count": 3,
        "mean": 2.0,
        "min": 1.0,
        "max": 3.0,
    }
    assert summary["ion_velocity"]["z"]["max"] == 90.0


def test_plot_mms_data_draws_available_products(mms_data: MMSData) -> None:
    figure = plot_mms_data(mms_data)

    assert len(figure.axes) == 4
    assert figure.get_size_inches().tolist() == [14.0, 16.0]
    assert np.issubdtype(figure.axes[0].lines[0].get_xdata().dtype, np.datetime64)
    assert figure.axes[0].lines[0].get_xdata()[0] == np.datetime64("1970-01-01T00:00:00")
    assert figure.axes[0].get_ylabel() == "B (nT)"
    assert figure.axes[1].get_ylabel() == "Density (cm⁻³)"
    assert figure.axes[2].get_ylabel() == "Ion velocity (km/s)"
    assert figure.axes[3].get_ylabel() == "Electron temperature (eV)"


def test_plot_mms_data_uses_pytplot_name_and_units_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = SimpleNamespace(times=np.array([0.0, 1.0]), y=np.array([2.0, 3.0]))

    def get_data(name: str, *, metadata: bool = False):
        assert name == "density"
        if metadata:
            return {
                "data_att": {"units": "cm^-3"},
                "plot_options": {"ytitle": "Ion number density"},
            }
        return product

    monkeypatch.setitem(sys.modules, "pytplot", SimpleNamespace(get_data=get_data))

    figure = plot_mms_data(
        MMSData(cadence="fast", series={"ion_density": "density"})
    )

    assert figure.axes[0].get_ylabel() == "Ion number density (cm^-3)"
    assert figure.axes[0].get_legend().get_texts()[0].get_text() == "Ion number density"


def test_plot_mms_data_rejects_empty_products() -> None:
    with pytest.raises(ValueError, match="No plot-able"):
        plot_mms_data(MMSData(cadence="fast", series={}))


def test_load_auto_prefers_burst_then_falls_back_to_fast() -> None:
    requested: list[str] = []

    def loader(*, start: str, end: str, probe: int, cadence: str) -> dict[str, str]:
        requested.append(cadence)
        return {} if cadence == "brst" else {"magnetic_field": "mms1_fgm_b_gse_fast_l2"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        loader=loader,
    )

    assert requested == ["brst", "fast"]
    assert data.cadence == "fast"
    assert data.series == {"magnetic_field": "mms1_fgm_b_gse_fast_l2"}


def test_load_burst_does_not_fall_back_to_fast() -> None:
    requested: list[str] = []

    def loader(*, start: str, end: str, probe: int, cadence: str) -> dict[str, str]:
        requested.append(cadence)
        return {}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        mode="brst",
        loader=loader,
    )

    assert requested == ["brst"]
    assert data.cadence == "brst"
    assert data.series == {}


@pytest.mark.parametrize("mode", ["survey", "burst", "slow"])
def test_load_rejects_invalid_mode(mode: str) -> None:
    with pytest.raises(ValueError, match="mode"):
        load_mms_data("2015-10-16", "2015-10-17", mode=mode, loader=lambda **_: {})


def test_default_loader_uses_fgm_survey_products_for_fast_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: dict[str, dict[str, object]] = {}
    mms = ModuleType("mms")

    def fgm(**kwargs: object) -> list[str]:
        requests["fgm"] = kwargs
        return ["mms1_fgm_b_gse_srvy_l2_bvec"]

    def fpi(**kwargs: object) -> list[str]:
        requests["fpi"] = kwargs
        return ["mms1_dis_numberdensity_fast"]

    mms.fgm = fgm  # type: ignore[attr-defined]
    mms.fpi = fpi  # type: ignore[attr-defined]
    projects = ModuleType("pyspedas.projects")
    projects.mms = mms  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", ModuleType("pyspedas"))
    monkeypatch.setitem(sys.modules, "pyspedas.projects", projects)

    series = _load_pyspedas_products(
        start="2015-10-16 13:06:00", end="2015-10-16 13:07:00", probe=1, cadence="fast"
    )

    assert requests["fgm"]["data_rate"] == "srvy"
    assert requests["fpi"]["data_rate"] == "fast"
    assert series["magnetic_field"] == "mms1_fgm_b_gse_srvy_l2_bvec"


def test_cli_parse_args_accepts_mms_interval_probe_and_cadence() -> None:
    arguments = parse_args(
        [
            "--start",
            "2015-10-16 13:06:00",
            "--end",
            "2015-10-16 13:07:00",
            "--probe",
            "3",
            "--mode",
            "fast",
        ]
    )

    assert arguments.start == "2015-10-16 13:06:00"
    assert arguments.end == "2015-10-16 13:07:00"
    assert arguments.probe == 3
    assert arguments.mode == "fast"
