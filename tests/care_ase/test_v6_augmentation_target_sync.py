from pathlib import Path


def test_make_batch_transforms_target_cache_with_stock_spatial_call():
    source = Path("scripts/training/care_ase/run_care_ase_r2_chunk.py").read_text(encoding="utf-8")
    body = source[source.index("def make_batch") : source.index("def append_csv")]

    assert "apply_stock_training_transform_with_targets" in body
    assert "regression_target_patch=regression_patch" in body
    assert "segmentation_extra_patch=segmentation_patch" in body
    assert body.index("apply_stock_training_transform_with_targets") < body.index(
        "target_cache_patch = _unpack_transformed_target_cache"
    )
    assert "preprocessed_full_case_grid_sliced_to_initial_patch_then_stock_spatial_transform_synced" in body
