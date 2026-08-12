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
        "omni_t": np.array([100000.0, 200000.0, 300000.0]),
        "vi": np.array(
            [[10.0, 20.0, 30.0], [20.0, 40.0, 60.0], [30.0, 60.0, 90.0]]
        ),
        "location": np.array(
            [
                [6371.2, -3185.6, 637.12],
                [6371.2, -3185.6, 637.12],
                [6371.2, -3185.6, 637.12],
            ]
        ),
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
            "omni_temperature": "omni_t",
            "ion_velocity": "vi",
            "satellite_location": "location",
        },
    )
