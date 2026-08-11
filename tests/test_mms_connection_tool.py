from __future__ import annotations

import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "mms_bow_shock_connection.py"


def test_connection_tool_help_describes_outputs() -> None:
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

    assert "--output-directory" in result.stdout
    assert "--three-d-output" in result.stdout
    assert "png" in result.stdout
    assert "html" in result.stdout
