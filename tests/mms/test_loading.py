from __future__ import annotations

from types import ModuleType, SimpleNamespace
import sys

import numpy as np
import pytest

from shocklink._mms_loading import (
    _converted_variable_name,
    _convert_vector_coordinates,
    _load_pyspedas_products,
)
from shocklink.mms import load_mms_data


def test_load_auto_prefers_burst_then_falls_back_to_fast() -> None:
    requested: list[str] = []

    def loader(**kwargs: object) -> dict[str, str]:
        requested.append(str(kwargs["cadence"]))
        return {} if kwargs["cadence"] == "brst" else {"magnetic_field": "b"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        loader=loader,
    )

    assert requested == ["brst", "fast"]
    assert data.cadence == "fast"
    assert data.start == "2015-10-16 13:06:00"


def test_load_burst_does_not_fall_back_to_fast() -> None:
    requested: list[str] = []

    def loader(**kwargs: object) -> dict[str, str]:
        requested.append(str(kwargs["cadence"]))
        return {}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        mode="brst",
        loader=loader,
    )

    assert requested == ["brst"]
    assert data.series == {}


@pytest.mark.parametrize("mode", ["survey", "burst", "slow"])
def test_load_rejects_invalid_mode(mode: str) -> None:
    with pytest.raises(ValueError, match="mode"):
        load_mms_data("2015-10-16", "2015-10-17", mode=mode, loader=lambda **_: {})


def test_default_loader_uses_survey_fgm_and_fast_fpi(
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
        start="2015-10-16 13:06:00",
        end="2015-10-16 13:07:00",
        probe=1,
        cadence="fast",
    )

    assert requests["fgm"]["data_rate"] == "srvy"
    assert requests["fpi"]["data_rate"] == "fast"
    assert series["magnetic_field"] == "mms1_fgm_b_gse_srvy_l2_bvec"


def test_default_loader_requests_optional_mec_position(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: dict[str, dict[str, object]] = {}
    mms = ModuleType("mms")
    mms.fgm = lambda **_: []  # type: ignore[attr-defined]
    mms.fpi = lambda **_: []  # type: ignore[attr-defined]

    def mec(**kwargs: object) -> list[str]:
        requests["mec"] = kwargs
        return ["mms1_mec_r_gsm"]

    mms.mec = mec  # type: ignore[attr-defined]
    projects = ModuleType("pyspedas.projects")
    projects.mms = mms  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyspedas", ModuleType("pyspedas"))
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
    )

    assert requests["mec"]["data_rate"] == "srvy"
    assert series["satellite_location"] == "mms1_mec_r_gsm"


def test_load_mms_data_propagates_coordinate_selection() -> None:
    requested: list[str] = []

    def loader(**kwargs: object) -> dict[str, str]:
        requested.append(str(kwargs["coordinates"]))
        return {"magnetic_field": "b"}

    data = load_mms_data(
        "2015-10-16 13:06:00",
        "2015-10-16 13:07:00",
        mode="brst",
        coordinates="gsm",
        loader=loader,
    )

    assert requested == ["gsm"]
    assert data.coordinates == "gsm"


def test_default_loader_converts_all_available_vectors_to_gsm(
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

    assert series["magnetic_field"] == "mms1_fgm_b_gsm_srvy_l2_bvec"
    assert series["ion_velocity"] == "mms1_dis_bulkv_gsm_fast"
    assert series["electron_velocity"] == "mms1_des_bulkv_gsm_fast"
    assert [call["name_in"] for call in transformed] == [
        "mms1_fgm_b_gse_srvy_l2_bvec",
        "mms1_dis_bulkv_gse_fast",
        "mms1_des_bulkv_gse_fast",
    ]


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


def test_converted_variable_name_falls_back_to_suffix() -> None:
    assert _converted_variable_name("custom_vector", "gsm") == "custom_vector_gsm"
