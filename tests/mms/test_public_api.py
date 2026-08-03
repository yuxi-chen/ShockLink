from __future__ import annotations

import subprocess
import sys


EXPECTED_PUBLIC_NAMES = {
    "MMSData",
    "average_plotted_values",
    "load_mms_data",
    "main",
    "parse_args",
    "plot_mms_data",
    "summarize_data",
}


def test_mms_public_api_is_explicit() -> None:
    import shocklink.mms as mms

    assert set(mms.__all__) == EXPECTED_PUBLIC_NAMES
    assert all(hasattr(mms, name) for name in EXPECTED_PUBLIC_NAMES)


def test_importing_mms_keeps_optional_dependencies_lazy() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import shocklink.mms; "
            "assert 'pyspedas' not in sys.modules; "
            "assert 'pytplot' not in sys.modules; "
            "assert 'matplotlib.pyplot' not in sys.modules",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
