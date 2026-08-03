import torch

from src.care_myocardium.models.care_ase import compute_slice_extent_statistics


def test_extent_empty_wall_records_fallback_per_slice():
    presence_logits = torch.zeros(2, 1, 3, 4, 4)
    area_logits = torch.zeros(2, 1, 3, 4, 4)
    p_wall = torch.zeros(2, 1, 3, 4, 4)

    _presence, _area, _wall, fallback = compute_slice_extent_statistics(presence_logits, area_logits, p_wall)

    assert tuple(fallback.shape) == (2, 1, 3, 1, 1)
    assert int(fallback.sum()) == 6
