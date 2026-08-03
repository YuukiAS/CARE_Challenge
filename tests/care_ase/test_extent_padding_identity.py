import torch

from src.care_myocardium.models.care_ase import compute_slice_extent_statistics
from src.care_myocardium.training.care_ase_trainer import per_slice_extent_loss


def test_extent_statistics_zero_for_all_invalid_padding_slice():
    presence_logits = torch.full((1, 1, 2, 4, 4), 8.0, requires_grad=True)
    area_logits = torch.full((1, 1, 2, 4, 4), 8.0, requires_grad=True)
    p_wall = torch.ones_like(presence_logits)
    valid = torch.zeros_like(presence_logits)

    presence, area, wall, fallback = compute_slice_extent_statistics(presence_logits, area_logits, p_wall, valid)
    assert torch.count_nonzero(presence) == 0
    assert torch.count_nonzero(area) == 0
    assert torch.count_nonzero(wall) == 0
    assert bool(fallback.all())

    loss = presence.sum() + area.sum()
    loss.backward()
    assert float(presence_logits.grad.abs().max()) == 0.0
    assert float(area_logits.grad.abs().max()) == 0.0


def test_per_slice_extent_loss_masks_all_invalid_padding_slice():
    presence_logits = torch.full((1, 1, 2, 4, 4), 8.0, requires_grad=True)
    area_logits = torch.full((1, 1, 2, 4, 4), 8.0, requires_grad=True)
    p_wall = torch.ones_like(presence_logits)
    valid = torch.zeros_like(presence_logits)
    target_presence = torch.ones(1, 1, 2)
    pathology_voxels = torch.ones(1, 1, 2)
    wall_voxels = torch.ones(1, 1, 2)

    presence_loss, area_loss = per_slice_extent_loss(
        presence_logits,
        area_logits,
        p_wall,
        target_presence,
        pathology_voxels,
        wall_voxels,
        case_valid=torch.ones(1),
        valid_spatial_mask=valid,
    )
    loss = presence_loss + area_loss
    assert float(loss.detach()) == 0.0
    loss.backward()
    assert float(presence_logits.grad.abs().max()) == 0.0
    assert float(area_logits.grad.abs().max()) == 0.0
