from __future__ import annotations

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from mms_data_analysis import load_mms_data


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
