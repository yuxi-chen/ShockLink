from pathlib import Path
import subprocess


def test_shocklink_source_package_is_flat() -> None:
    root = Path(__file__).resolve().parents[1]
    tracked = subprocess.run(
        ["git", "ls-files", "src/shocklink"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    nested = [
        path
        for path in tracked
        if len(Path(path).relative_to("src/shocklink").parts) > 1
    ]

    assert nested == []
