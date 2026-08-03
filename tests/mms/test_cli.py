from __future__ import annotations

import ast
from pathlib import Path

from shocklink.mms import main, parse_args


ROOT = Path(__file__).resolve().parents[2]


def test_cli_parse_args_accepts_interval_probe_cadence_and_coordinates() -> None:
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


def test_cli_coordinates_default_to_gse() -> None:
    arguments = parse_args(["--start", "2015-10-16", "--end", "2015-10-17"])

    assert arguments.coordinates == "gse"


def test_main_reports_download_failure(monkeypatch, capsys) -> None:
    import shocklink._mms_cli as cli

    def raising_loader(*_args, **_kwargs):
        raise RuntimeError("network unavailable")

    monkeypatch.setattr(cli, "load_mms_data", raising_loader)

    result = main(["--start", "2018-12-19", "--end", "2018-12-20"])

    assert result == 1
    assert "Could not download MMS data" in capsys.readouterr().err


def test_main_reports_empty_data(monkeypatch, capsys) -> None:
    import shocklink._mms_cli as cli
    from shocklink.mms import MMSData

    monkeypatch.setattr(
        cli,
        "load_mms_data",
        lambda *_args, **_kwargs: MMSData(cadence="fast", series={}),
    )

    result = main(["--start", "2018-12-19", "--end", "2018-12-20"])

    assert result == 1
    assert "No MMS data were available" in capsys.readouterr().err


def test_main_runs_summary_average_and_plot_workflow(monkeypatch, capsys) -> None:
    import shocklink._mms_cli as cli
    from shocklink.mms import MMSData

    calls: list[str] = []
    data = MMSData(cadence="fast", series={"magnetic_field": "b"})
    monkeypatch.setattr(cli, "load_mms_data", lambda *_args, **_kwargs: data)
    monkeypatch.setattr(cli, "summarize_data", lambda _data: calls.append("summary") or {})
    monkeypatch.setattr(
        cli,
        "average_plotted_values",
        lambda _data: calls.append("average") or {},
    )

    class Figure:
        def show(self) -> None:
            calls.append("show")

    monkeypatch.setattr(cli, "plot_mms_data", lambda _data: calls.append("plot") or Figure())

    result = main(["--start", "2018-12-19", "--end", "2018-12-20"])

    assert result == 0
    assert calls == ["summary", "average", "plot", "show"]
    assert "Loaded MMS1 fast data" in capsys.readouterr().out


def test_example_is_a_thin_mms_entry_point() -> None:
    source = (ROOT / "examples/mms_data_analysis.py").read_text()
    tree = ast.parse(source)
    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

    assert functions == []
    assert "from shocklink.mms import main" in source
    assert "raise SystemExit(main())" in source
