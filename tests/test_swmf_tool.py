from __future__ import annotations

import ast
import os
from pathlib import Path


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
