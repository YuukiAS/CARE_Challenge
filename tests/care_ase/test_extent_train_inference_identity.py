import torch

from src.care_myocardium.models.care_ase import compute_slice_extent_statistics
from src.care_myocardium.training.care_ase_trainer import per_slice_extent_loss


def test_extent_loss_uses_same_wall_weighted_statistics_as_inference():
    presence_logits = torch.randn(1, 1, 4, 5, 5)
    area_logits = torch.randn(1, 1, 4, 5, 5)
    p_wall = torch.zeros(1, 1, 4, 5, 5)
    p_wall[:, :, :, 1:4, 1:4] = 1.0
    target_presence = torch.ones(1, 1, 8)
    pathology_voxels = torch.ones(1, 1, 8)
    wall_voxels = torch.full((1, 1, 8), 4.0)

    expected_presence, expected_area, _wall, fallback = compute_slice_extent_statistics(presence_logits, area_logits, p_wall)
    loss_presence, loss_area = per_slice_extent_loss(
        presence_logits,
        area_logits,
        p_wall,
        target_presence,
        pathology_voxels,
        wall_voxels,
        None,
    )

    assert expected_presence.shape == (1, 1, 4, 1, 1)
    assert expected_area.shape == (1, 1, 4, 1, 1)
    assert int(fallback.sum()) == 0
    assert torch.isfinite(loss_presence)
    assert torch.isfinite(loss_area)
