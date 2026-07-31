from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import matplotlib
matplotlib.use("Agg")
from matplotlib import dates as mdates
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from mms_data_analysis import (
    MMSData,
    _convert_vector_coordinates,
    _converted_variable_name,
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
        "ve": np.array([[40.0, 50.0, 60.0], [50.0, 60.0, 70.0], [60.0, 70.0, 80.0]]),
        "ti_parallel": np.array([300.0, 600.0, 900.0]),
        "ti_perpendicular": np.array([30.0, 60.0, 90.0]),
        "te_parallel": np.array([100.0, 200.0, 300.0]),
        "te_perpendicular": np.array([10.0, 20.0, 30.0]),
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
        probe=1,
        series={
            "magnetic_field": "b",
            "ion_density": "ni",
            "electron_density": "ne",
            "ion_velocity": "vi",
            "electron_velocity": "ve",
            "ion_temperature_parallel": "ti_parallel",
            "ion_temperature_perpendicular": "ti_perpendicular",
            "electron_temperature_parallel": "te_parallel",
            "electron_temperature_perpendicular": "te_perpendicular",
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

    assert len(figure.axes) == 5
    assert figure._suptitle.get_text() == "MMS1 brst data (GSE)"
    assert figure.get_size_inches().tolist() == [10.0, 7.5]
    time_formatter = figure.axes[-1].xaxis.get_major_formatter()
    assert isinstance(time_formatter, mdates.DateFormatter)
    assert time_formatter.fmt == "%H:%M:%S"
    assert figure.axes[-1].get_xlabel() == "Time (UTC)\n1970 Jan 01"
    assert np.issubdtype(figure.axes[0].lines[0].get_xdata().dtype, np.datetime64)
    assert figure.axes[0].lines[0].get_xdata()[0] == np.datetime64("1970-01-01T00:00:00")
    assert figure.axes[0].get_ylabel() == r"$B$ [nT]"
    assert [line.get_color() for line in figure.axes[0].lines] == [
        "blue",
        "green",
        "red",
        "black",
    ]
    assert all(line.get_linewidth() == 0.75 for axis in figure.axes for line in axis.lines)
    assert figure.axes[1].get_ylabel() == r"$n$ [/cm$^3$]"
    assert len(figure.axes[1].lines) == 1
    assert figure.axes[2].get_ylabel() == r"$V_i$ [km/s]"
    assert figure.axes[3].get_ylabel() == r"$T_i$ [eV]"
    assert figure.axes[4].get_ylabel() == r"$T_e$ [eV]"
    assert all("Electron velocity" not in axis.get_ylabel() for axis in figure.axes)
    np.testing.assert_allclose(figure.axes[4].lines[0].get_ydata(), [40.0, 80.0, 120.0])


def test_plot_mms_data_title_shows_gsm_coordinates(mms_data: MMSData) -> None:
    gsm_data = MMSData(
        cadence=mms_data.cadence,
        probe=mms_data.probe,
        series=mms_data.series,
        coordinates="gsm",
    )

    figure = plot_mms_data(gsm_data)

    assert figure._suptitle.get_text() == "MMS1 brst data (GSM)"


def test_plot_mms_data_uses_pytplot_name_and_units_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    product = SimpleNamespace(times=np.array([0.0, 1.0]), y=np.array([2.0, 3.0]))

    def get_data(name: str, *, metadata: bool = False):
        assert name == "density"
        if metadata:
            return {
                "data_att": {"units": "cm^-3"},
                "plot_options": {
                    "yaxis_opt": {
                        "axis_label": "Ion number density",
                        "axis_subtitle": "[cm^-3]",
                    }
                },
            }
        return product

    monkeypatch.setitem(sys.modules, "pytplot", SimpleNamespace(get_data=get_data))

    figure = plot_mms_data(
        MMSData(cadence="fast", series={"ion_density": "density"})
    )

    assert figure.axes[0].get_ylabel() == r"$n$ [/cm$^3$]"
    assert figure.axes[0].get_legend().get_texts()[0].get_text() == "Ion number density"


def test_plot_mms_data_rejects_empty_products() -> None:
    with pytest.raises(ValueError, match="No plot-able"):
        plot_mms_data(MMSData(cadence="fast", series={}))


def test_load_auto_prefers_burst_then_falls_back_to_fast() -> None:
    requested: list[str] = []

    def loader(
        *, start: str, end: str, probe: int, cadence: str, coordinates: str
    ) -> dict[str, str]:
        requested.append(cadence)
        return {} if cadence == "brst" else {"magnetic_field": "mms1_fgm_b_gse_fast_l2"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        loader=loader,
    )

    assert requested == ["brst", "fast"]
    assert data.cadence == "fast"
    assert data.probe == 1
    assert data.series == {"magnetic_field": "mms1_fgm_b_gse_fast_l2"}


def test_load_burst_does_not_fall_back_to_fast() -> None:
    requested: list[str] = []

    def loader(
        *, start: str, end: str, probe: int, cadence: str, coordinates: str
    ) -> dict[str, str]:
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
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda _: SimpleNamespace(times=np.array([1_445_000_800.0]))
        ),
    )

    series = _load_pyspedas_products(
        start="2015-10-16 13:06:00", end="2015-10-16 13:07:00", probe=1, cadence="fast"
    )

    assert requests["fgm"]["data_rate"] == "srvy"
    assert requests["fpi"]["data_rate"] == "fast"
    assert series["magnetic_field"] == "mms1_fgm_b_gse_srvy_l2_bvec"


def test_default_loader_discards_products_outside_requested_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mms = ModuleType("mms")
    mms.fgm = lambda **_: ["mms1_fgm_b_gse_srvy_l2_bvec"]  # type: ignore[attr-defined]
    mms.fpi = lambda **_: []  # type: ignore[attr-defined]
    projects = ModuleType("pyspedas.projects")
    projects.mms = mms  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", ModuleType("pyspedas"))
    monkeypatch.setitem(sys.modules, "pyspedas.projects", projects)
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda _: SimpleNamespace(times=np.array([1_445_000_800.0]))
        ),
    )

    series = _load_pyspedas_products(
        start="2018-12-19 19:40:00", end="2018-12-19 19:52:00", probe=1, cadence="fast"
    )

    assert series == {}


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
            "--coordinates",
            "gsm",
        ]
    )

    assert arguments.start == "2015-10-16 13:06:00"
    assert arguments.end == "2015-10-16 13:07:00"
    assert arguments.probe == 3
    assert arguments.mode == "fast"
    assert arguments.coordinates == "gsm"


def test_load_mms_data_defaults_to_gse() -> None:
    requested: list[str] = []

    def loader(
        *, start: str, end: str, probe: int, cadence: str, coordinates: str
    ) -> dict[str, str]:
        requested.append(coordinates)
        return {"magnetic_field": "mms1_fgm_b_gse_brst_l2_bvec"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        mode="brst",
        loader=loader,
    )

    assert requested == ["gse"]
    assert data.coordinates == "gse"


def test_load_mms_data_propagates_explicit_gsm_to_loader() -> None:
    requested: list[str] = []

    def loader(
        *, start: str, end: str, probe: int, cadence: str, coordinates: str
    ) -> dict[str, str]:
        requested.append(coordinates)
        return {"magnetic_field": "mms1_fgm_b_gse_brst_l2_bvec"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        mode="brst",
        coordinates="gsm",
        loader=loader,
    )

    assert requested == ["gsm"]
    assert data.coordinates == "gsm"


def test_load_mms_data_preserves_positional_loader_slot() -> None:
    def loader(
        *, start: str, end: str, probe: int, cadence: str, coordinates: str
    ) -> dict[str, str]:
        return {"magnetic_field": "mms1_fgm_b_gse_brst_l2_bvec"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        1,
        "brst",
        loader,
    )

    assert data.coordinates == "gse"


def test_load_mms_data_rejects_invalid_coordinates_before_loading() -> None:
    def loader(**_: object) -> dict[str, str]:
        pytest.fail("invalid coordinates must be rejected before loading")

    with pytest.raises(ValueError, match="coordinates"):
        load_mms_data(
            "2015-10-16",
            "2015-10-17",
            coordinates="sm",
            loader=loader,
        )


def test_cli_coordinates_default_to_gse() -> None:
    arguments = parse_args(
        ["--start", "2015-10-16", "--end", "2015-10-17"]
    )

    assert arguments.coordinates == "gse"


def test_default_loader_converts_all_vectors_to_gsm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transformed: list[dict[str, str]] = []
    mms = ModuleType("mms")
    mms.fgm = lambda **_: ["mms1_fgm_b_gse_srvy_l2_bvec"]  # type: ignore[attr-defined]
    mms.fpi = lambda **_: [  # type: ignore[attr-defined]
        "mms1_dis_numberdensity_fast",
        "mms1_dis_bulkv_gse_fast",
        "mms1_des_bulkv_gse_fast",
    ]

    def cotrans(**kwargs: str) -> int:
        transformed.append(kwargs)
        return 1

    pyspedas = ModuleType("pyspedas")
    pyspedas.cotrans = cotrans  # type: ignore[attr-defined]
    projects = ModuleType("pyspedas.projects")
    projects.mms = mms  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", pyspedas)
    monkeypatch.setitem(sys.modules, "pyspedas.projects", projects)
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda _: SimpleNamespace(times=np.array([1_545_248_400.0]))
        ),
    )

    series = _load_pyspedas_products(
        start="2018-12-19 19:40:00",
        end="2018-12-19 19:52:00",
        probe=1,
        cadence="fast",
        coordinates="gsm",
    )

    assert series == {
        "magnetic_field": "mms1_fgm_b_gsm_srvy_l2_bvec",
        "ion_density": "mms1_dis_numberdensity_fast",
        "ion_velocity": "mms1_dis_bulkv_gsm_fast",
        "electron_velocity": "mms1_des_bulkv_gsm_fast",
    }
    assert [call["name_in"] for call in transformed] == [
        "mms1_fgm_b_gse_srvy_l2_bvec",
        "mms1_dis_bulkv_gse_fast",
        "mms1_des_bulkv_gse_fast",
    ]
    assert all(call["coord_in"] == "gse" for call in transformed)
    assert all(call["coord_out"] == "gsm" for call in transformed)


def test_gse_variable_name_falls_back_to_suffix_without_coordinate_token() -> None:
    assert _converted_variable_name("custom_vector", "gsm") == "custom_vector_gsm"


def test_gse_coordinate_conversion_is_a_noop() -> None:
    series = {
        "magnetic_field": "mms1_fgm_b_gse_srvy_l2_bvec",
        "ion_velocity": "mms1_dis_bulkv_gse_fast",
    }

    assert _convert_vector_coordinates(series, "gse") == series


def test_gsm_scalar_only_conversion_is_a_noop_without_pyspedas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(sys.modules, "pyspedas", raising=False)
    series = {"ion_density": "mms1_dis_numberdensity_fast"}

    assert _convert_vector_coordinates(series, "gsm") == series


def test_coordinate_conversion_reports_failed_product(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pyspedas = ModuleType("pyspedas")
    pyspedas.cotrans = lambda **_: 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", pyspedas)

    with pytest.raises(RuntimeError, match="mms1_dis_bulkv_gse_fast"):
        _convert_vector_coordinates(
            {"ion_velocity": "mms1_dis_bulkv_gse_fast"}, "gsm"
        )


def test_coordinate_conversion_wraps_cotrans_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pyspedas = ModuleType("pyspedas")

    def cotrans(**_: str) -> int:
        raise ValueError("missing transformation metadata")

    pyspedas.cotrans = cotrans  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", pyspedas)

    with pytest.raises(RuntimeError, match="mms1_fgm_b_gse_fast_l2_bvec") as error:
        _convert_vector_coordinates(
            {"magnetic_field": "mms1_fgm_b_gse_fast_l2_bvec"}, "gsm"
        )

    assert isinstance(error.value.__cause__, ValueError)
