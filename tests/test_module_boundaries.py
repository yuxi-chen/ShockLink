import ast
from pathlib import Path

import shocklink.tecplot as tecplot


def test_generic_dataset_operations_are_separate_from_tecplot() -> None:
    from shocklink import dataset

    assert callable(dataset.get_2d_cut)
    assert callable(dataset.plot_2d_cut)
    assert tecplot.__all__ == ["read_tecplot"]
    assert not hasattr(tecplot, "get_2d_cut")
    assert not hasattr(tecplot, "plot_2d_cut")


def test_mms_private_modules_do_not_import_public_facade() -> None:
    root = Path(__file__).resolve().parents[1]
    for module in (
        "data.py",
        "loading.py",
        "analysis.py",
        "plotting.py",
        "cli.py",
    ):
        tree = ast.parse((root / "src/shocklink/mms" / module).read_text())
        imported_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert "shocklink.mms" not in imported_modules


def test_swmf_does_not_import_mms_or_integration_workflow() -> None:
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / "src/shocklink/swmf.py").read_text())
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert "shocklink.mms" not in imported_modules
    assert "shocklink.mms_swmf" not in imported_modules
    assert "load_mms_data" not in imported_names
    assert "average_plotted_values" not in imported_names
