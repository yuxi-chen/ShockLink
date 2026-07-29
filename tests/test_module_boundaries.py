import shocklink.tecplot as tecplot


def test_generic_dataset_operations_are_separate_from_tecplot() -> None:
    from shocklink import dataset

    assert callable(dataset.get_2d_cut)
    assert callable(dataset.plot_2d_cut)
    assert tecplot.__all__ == ["read_tecplot"]
    assert not hasattr(tecplot, "get_2d_cut")
    assert not hasattr(tecplot, "plot_2d_cut")
