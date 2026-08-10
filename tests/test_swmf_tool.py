from __future__ import annotations

import ast
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "create_swmf_input.py"


def test_swmf_tool_is_an_executable_thin_entry_point() -> None:
    source = TOOL.read_text(encoding="utf-8")
    tree = ast.parse(source)

    assert os.access(TOOL, os.X_OK)
    assert TOOL.read_bytes().splitlines()[0] == b"#!/usr/bin/env python"
    assert [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)] == []
    assert "from shocklink.mms_swmf import main" in source
    assert "raise SystemExit(main())" in source


def test_swmf_tool_help_explains_options_and_shows_examples() -> None:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(ROOT / "src"), environment.get("PYTHONPATH")))
    )

    result = subprocess.run(
        [str(TOOL), "-h"],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "usage:" in result.stdout
    for option in (
        "--mms-start",
        "--mms-end",
        "--output",
        "--input",
        "--start-time",
        "--probe",
        "--mode",
    ):
        assert option in result.stdout
    assert "default: data/Param/PARAM.in.Earth" in result.stdout
    assert "default: 1" in result.stdout
    assert "default: auto" in result.stdout
    assert "examples:" in result.stdout
    assert "create_swmf_input.py --mms-start" in result.stdout
    assert "--probe 2 --mode brst" in result.stdout
    assert "--input custom/PARAM.in --start-time" in result.stdout
