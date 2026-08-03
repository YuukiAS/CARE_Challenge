import pytest
import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import CAREASEStageScheduler, build_optimizer, run_formal_optimizer_step


def test_missing_microbatch_fail_closed_before_optimizer_step():
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    batch = {
        "image": torch.zeros(1, 3, 8, 64, 64),
        "availability": torch.ones(1, 3),
        "seg": torch.zeros(1, 8, 64, 64, dtype=torch.long),
    }
    with pytest.raises(ValueError, match="exactly four microbatches"):
        run_formal_optimizer_step(
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            microbatches=[batch, batch, batch],
            global_step=0,
            gradient_accumulation=4,
            autocast_enabled=False,
        )
