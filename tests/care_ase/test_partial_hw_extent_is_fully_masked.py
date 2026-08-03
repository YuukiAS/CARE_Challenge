import torch

from src.care_myocardium.training.care_ase_trainer import per_slice_extent_loss


def _extent_loss_with_z_mask(mask_value: float):
    presence_logits = torch.full((1, 1, 2, 4, 4), 2.0, requires_grad=True)
    area_logits = torch.full((1, 1, 2, 4, 4), 2.0, requires_grad=True)
    p_wall = torch.ones_like(presence_logits)
    valid_spatial = torch.ones_like(presence_logits)
    target_presence = torch.ones(1, 1, 2)
    path_voxels = torch.ones(1, 1, 2)
    wall_voxels = torch.ones(1, 1, 2) * 2
    z_mask = torch.full((1, 1, 2), float(mask_value))
    presence, area = per_slice_extent_loss(
        presence_logits,
        area_logits,
        p_wall,
        target_presence,
        path_voxels,
        wall_voxels,
        z_mask,
        valid_spatial,
    )
    loss = presence + area
    loss.backward()
    return float(loss.detach()), float(presence_logits.grad.abs().max()), float(area_logits.grad.abs().max())


def test_partial_hw_patch_masks_presence_area_and_gradient():
    loss, presence_grad, area_grad = _extent_loss_with_z_mask(0.0)
    assert loss == 0.0
    assert presence_grad == 0.0
    assert area_grad == 0.0


def test_full_hw_patch_allows_extent_supervision():
    loss, presence_grad, area_grad = _extent_loss_with_z_mask(1.0)
    assert loss > 0.0
    assert presence_grad > 0.0
    assert area_grad > 0.0
