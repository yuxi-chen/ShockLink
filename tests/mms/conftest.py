from __future__ import annotations

import sys
from types import SimpleNamespace

import numpy as np
import pytest

from shocklink.mms import MMSData


@pytest.fixture
def mms_data(monkeypatch: pytest.MonkeyPatch) -> MMSData:
    timestamps = np.array([0.0, 1.0, 2.0])
    values = {
        "b": np.array(
            [[1.0, 2.0, 3.0], [2.0, 4.0, 6.0], [3.0, 6.0, 9.0]]
        ),
        "ni": np.array([1.0, 2.0, 3.0]),
        "ne": np.array([4.0, 5.0, 6.0]),
        "vi": np.array(
            [[10.0, 20.0, 30.0], [20.0, 40.0, 60.0], [30.0, 60.0, 90.0]]
        ),
        "ve": np.array(
            [[40.0, 50.0, 60.0], [50.0, 60.0, 70.0], [60.0, 70.0, 80.0]]
        ),
        "location": np.array(
            [
                [6371.2, -3185.6, 637.12],
                [6371.2, -3185.6, 637.12],
                [6371.2, -3185.6, 637.12],
            ]
        ),
        "ti_parallel": np.array([300.0, 600.0, 900.0]),
        "ti_perpendicular": np.array([30.0, 60.0, 90.0]),
        "te_parallel": np.array([100.0, 200.0, 300.0]),
        "te_perpendicular": np.array([10.0, 20.0, 30.0]),
    }
    monkeypatch.setitem(
        sys.modules,
        "pytplot",
        SimpleNamespace(
            get_data=lambda name, **_: SimpleNamespace(
                times=timestamps, y=values[name]
            )
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
            "satellite_location": "location",
            "ion_temperature_parallel": "ti_parallel",
            "ion_temperature_perpendicular": "ti_perpendicular",
            "electron_temperature_parallel": "te_parallel",
            "electron_temperature_perpendicular": "te_perpendicular",
        },
    )
