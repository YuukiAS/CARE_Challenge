import torch
import pytest

import src.care_myocardium.training.care_ase_trainer as trainer
from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import CAREASEStageScheduler, build_optimizer, run_formal_optimizer_step


def test_formal_optimizer_step_rejects_nonfinite_loss(monkeypatch):
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)

    def nan_loss(_outputs, _batch, *, collect_metrics=True):
        param = next(param for param in model.parameters() if param.requires_grad)
        return param.sum() * torch.tensor(float("nan")), {}

    monkeypatch.setattr(trainer, "care_ase_loss", nan_loss)
    batch = {
        "image": torch.zeros(1, 3, 8, 64, 64),
        "availability": torch.ones(1, 3),
        "seg": torch.zeros(1, 8, 64, 64, dtype=torch.long),
    }
    with pytest.raises(FloatingPointError, match="non-finite CARE-ASE microbatch loss"):
        run_formal_optimizer_step(
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            microbatches=[batch, batch, batch, batch],
            global_step=0,
            gradient_accumulation=4,
            autocast_enabled=False,
        )
