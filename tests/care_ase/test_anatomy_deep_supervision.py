import pytest
import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import care_ase_loss


def test_anatomy_half_deep_supervision_enters_loss():
    model = build_care_ase_for_fold(2)
    sample = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    seg = torch.zeros(1, 8, 64, 64, dtype=torch.long)
    outputs = model(sample, availability, global_step=0)

    loss, metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    assert torch.isfinite(loss)
    assert "anatomy_half_ce" in metrics
    assert "anatomy_half_dice" in metrics

    del outputs["anatomy"]["half_logits4"]
    with pytest.raises(KeyError):
        care_ase_loss(outputs, {"seg": seg, "availability": availability})
