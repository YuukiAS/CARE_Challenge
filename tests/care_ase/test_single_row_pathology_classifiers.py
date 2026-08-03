import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold


def test_pathology_classifiers_are_single_stock_rows():
    model = build_care_ase_for_fold(2)

    for branch, expected_class in ((model.scar_branch, 5), (model.edema_branch, 4)):
        assert branch.class_index == expected_class
        assert len(branch.seg_layers) == 2
        for seg_layer in branch.seg_layers:
            assert seg_layer.out_channels == 1
            assert seg_layer.weight.shape[0] == 1
            assert seg_layer.bias is None or seg_layer.bias.shape[0] == 1

    sample = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    outputs = model(sample, availability, global_step=0, disable_extent_wall=True)

    assert outputs["scar"]["half_logit"].shape[1] == 1
    assert outputs["scar"]["full_logit"].shape[1] == 1
    assert outputs["edema"]["half_logit"].shape[1] == 1
    assert outputs["edema"]["full_logit"].shape[1] == 1
    assert outputs["scar"]["half_logits6"].shape[1] == 6
    assert outputs["edema"]["half_logits6"].shape[1] == 6
    assert torch.count_nonzero(outputs["scar"]["half_logits6"][:, :5]).item() == 0
    assert torch.count_nonzero(outputs["edema"]["half_logits6"][:, :4]).item() == 0
    assert torch.count_nonzero(outputs["edema"]["half_logits6"][:, 5:]).item() == 0


def test_no_duplicate_scar_extent_presence_module_or_parameter():
    model = build_care_ase_for_fold(2)

    named_modules = dict(model.named_modules())
    named_parameters = dict(model.named_parameters())
    assert "component_heads.scar_extent_presence" not in named_modules
    assert not any("scar_extent_presence" in name for name in named_parameters)
