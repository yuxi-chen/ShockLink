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


def test_repository_plan_describes_flat_source_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    plan = (
        root / "docs/plans/2026-07-28-shocklink-repository.md"
    ).read_text()

    nested_source_paths = [
        "src/shocklink/bowshock/",
        "src/shocklink/connectivity/",
        "src/shocklink/core/",
        "src/shocklink/fieldlines/",
        "src/shocklink/io/",
        "src/shocklink/paraview/",
        "src/shocklink/cli/",
    ]

    assert [path for path in nested_source_paths if path in plan] == []
