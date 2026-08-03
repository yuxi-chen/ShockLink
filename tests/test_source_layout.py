from pathlib import Path
import subprocess


def test_shocklink_source_package_is_flat_except_mms_domain() -> None:
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
        and not path.startswith("src/shocklink/mms/")
    ]

    assert nested == []


def test_mms_domain_is_an_explicit_nested_package_exception() -> None:
    root = Path(__file__).resolve().parents[1]
    tracked = subprocess.run(
        ["git", "ls-files", "src/shocklink/mms"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()

    assert "src/shocklink/mms/__init__.py" in tracked
    assert "src/shocklink/mms/data.py" in tracked
    assert "src/shocklink/mms/loading.py" in tracked
    assert "src/shocklink/mms/analysis.py" in tracked
    assert "src/shocklink/mms/plotting.py" in tracked
    assert "src/shocklink/mms/cli.py" in tracked


def test_repository_plan_describes_flat_source_modules() -> None:
    root = Path(__file__).resolve().parents[1]
    plan = (root / "docs/plans/2026-07-28-shocklink-repository.md").read_text()

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


def test_repository_plan_uses_pyvista_instead_of_paraview() -> None:
    root = Path(__file__).resolve().parents[1]
    plan = (root / "docs/plans/2026-07-28-shocklink-repository.md").read_text()

    assert "paraview" not in plan.lower()
    assert "pvpython" not in plan.lower()
    assert "PyVista" in plan
    assert "src/shocklink/tecplot.py" in plan
