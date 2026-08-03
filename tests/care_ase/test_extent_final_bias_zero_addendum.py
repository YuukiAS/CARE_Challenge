from types import SimpleNamespace

import torch

from src.care_myocardium.models.care_ase import CAREASE


def _dummy_model():
    return SimpleNamespace(
        scar_area_reference=torch.tensor(0.2),
        edema_area_reference=torch.tensor(0.2),
        extent_wall_ramp=CAREASE.extent_wall_ramp,
        _sigmoid_logit_center=CAREASE._sigmoid_logit_center,
    )


def _components():
    value = torch.full((1, 1, 2, 4, 4), 6.0, requires_grad=True)
    return {
        "scar_extent_presence": value,
        "scar_extent_area": value.clone().detach().requires_grad_(True),
        "edema_extent_presence": value.clone().detach().requires_grad_(True),
        "edema_extent_area": value.clone().detach().requires_grad_(True),
    }


def test_extent_all_invalid_final_bias_zero():
    components = _components()
    p_wall = torch.ones((1, 1, 2, 4, 4), requires_grad=True)
    valid = torch.zeros_like(p_wall)
    bias = CAREASE._extent_bias(_dummy_model(), components, p_wall, pathology="scar", global_step=2000, valid_spatial_mask=valid)
    assert float(bias.abs().max()) == 0.0
    bias.sum().backward()
    assert float(components["scar_extent_presence"].grad.abs().max()) == 0.0
    assert float(components["scar_extent_area"].grad.abs().max()) == 0.0
    assert p_wall.grad is None


def test_extent_partial_hw_final_bias_zero_for_masked_slice():
    components = _components()
    p_wall = torch.ones((1, 1, 2, 4, 4), requires_grad=True)
    valid = torch.ones_like(p_wall)
    valid[:, :, 1] = 0.0
    bias = CAREASE._extent_bias(_dummy_model(), components, p_wall, pathology="edema", global_step=2000, valid_spatial_mask=valid)
    assert float(bias[:, :, 1].abs().max()) == 0.0
    assert float(bias[:, :, 0].abs().max()) > 0.0


def test_extent_valid_slice_unaffected_by_other_invalid_slice():
    components_a = _components()
    components_b = {key: tensor.clone().detach().requires_grad_(True) for key, tensor in components_a.items()}
    p_wall_a = torch.ones((1, 1, 2, 4, 4))
    p_wall_b = p_wall_a.clone()
    valid_a = torch.ones_like(p_wall_a)
    valid_b = torch.ones_like(p_wall_b)
    valid_b[:, :, 1] = 0.0
    bias_a = CAREASE._extent_bias(_dummy_model(), components_a, p_wall_a, pathology="scar", global_step=2000, valid_spatial_mask=valid_a)
    bias_b = CAREASE._extent_bias(_dummy_model(), components_b, p_wall_b, pathology="scar", global_step=2000, valid_spatial_mask=valid_b)
    assert torch.allclose(bias_a[:, :, 0], bias_b[:, :, 0])


def test_extent_padding_logit_invariance_for_unpadded_region():
    components = _components()
    p_wall = torch.ones((1, 1, 2, 4, 4))
    valid = torch.ones_like(p_wall)
    base_bias = CAREASE._extent_bias(_dummy_model(), components, p_wall, pathology="scar", global_step=10000, valid_spatial_mask=valid)

    padded_components = {key: torch.nn.functional.pad(tensor.detach(), (0, 2, 0, 2, 0, 1)).requires_grad_(True) for key, tensor in components.items()}
    padded_wall = torch.nn.functional.pad(p_wall, (0, 2, 0, 2, 0, 1))
    padded_valid = torch.nn.functional.pad(valid, (0, 2, 0, 2, 0, 1))
    padded_bias = CAREASE._extent_bias(_dummy_model(), padded_components, padded_wall, pathology="scar", global_step=10000, valid_spatial_mask=padded_valid)
    assert torch.allclose(base_bias, padded_bias[:, :, :2, :4, :4], atol=1e-6)
    assert float(padded_bias[:, :, 2:].abs().max()) == 0.0
