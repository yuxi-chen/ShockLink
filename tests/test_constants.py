from __future__ import annotations

import ast
from pathlib import Path

from shocklink.constants import CARTESIAN_COMPONENTS, EARTH_RADIUS_KM, EV_TO_K


ROOT = Path(__file__).resolve().parents[1]


def test_shared_constants_have_expected_values() -> None:
    assert CARTESIAN_COMPONENTS == ("x", "y", "z")
    assert EARTH_RADIUS_KM == 6371.2
    assert EV_TO_K == 11604.51812


def test_shared_constants_are_defined_only_in_constants_module() -> None:
    definitions: dict[str, list[str]] = {
        name: [] for name in ("CARTESIAN_COMPONENTS", "EARTH_RADIUS_KM", "EV_TO_K")
    }
    for path in (ROOT / "src/shocklink").rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in definitions:
                    definitions[target.id].append(path.name)
    assert definitions == {
        "CARTESIAN_COMPONENTS": ["constants.py"],
        "EARTH_RADIUS_KM": ["constants.py"],
        "EV_TO_K": ["constants.py"],
    }
