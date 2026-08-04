from __future__ import annotations

import ast
from pathlib import Path


def test_swmf_example_is_a_thin_entry_point() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "examples/create_swmf_input.py").read_text()
    tree = ast.parse(source)

    assert [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)] == []
    assert "from shocklink.mms_swmf import main" in source
    assert "raise SystemExit(main())" in source
