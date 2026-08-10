from pathlib import Path

import pyvista as pv
import pytest

import shocklink.tecplot as tecplot


def test_read_tecplot_delegates_to_generic_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = pv.UnstructuredGrid()
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def fake_loader(*args: object, **kwargs: object) -> pv.UnstructuredGrid:
        calls.append((args, kwargs))
        return expected

    monkeypatch.setattr(tecplot, "load_simulation", fake_loader)

    result = tecplot.read_tecplot(
        tmp_path / "sample.vtm",
        coordinate_components=("x", "y", "z"),
        magnetic_name="magnetic",
    )

    assert result is expected
    assert calls == [
        (
            (tmp_path / "sample.vtm",),
            {
                "coordinate_components": ("x", "y", "z"),
                "magnetic_components": None,
                "velocity_components": None,
                "magnetic_name": "magnetic",
                "velocity_name": "U [km/s]",
            },
        )
    ]


def test_tecplot_compatibility_exports_remain_stable() -> None:
    assert tecplot.__all__ == ["TIME_EVENT_KEY", "read_tecplot"]
    assert tecplot.TIME_EVENT_KEY == "time_event"
