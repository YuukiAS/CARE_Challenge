from pathlib import Path

from src.care_myocardium.training.care_ase_augmentation import build_stock_augmentation_contract


def test_stock_augmentation_contract_reads_nnunet_trainer_runtime_binding():
    contract = build_stock_augmentation_contract(Path("data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"))

    assert contract.trainer_source_path.endswith("nnUNetTrainer.py")
    assert contract.final_patch_size == (20, 256, 256)
    assert contract.initial_patch_size[0] == 20
    assert contract.initial_patch_size[1] >= 256
    assert contract.initial_patch_size[2] >= 256
    assert contract.dummy_2d is True
    assert contract.spatial_padding_value_seg == -1
    assert contract.scale_range == (0.7, 1.4)
    assert set(contract.mirror_axes) == {0, 1, 2}
    assert "dummy_2d" in contract.z_axis_semantics
