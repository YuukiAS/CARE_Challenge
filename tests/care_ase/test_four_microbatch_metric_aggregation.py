import torch

import src.care_myocardium.training.care_ase_trainer as trainer
from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import CAREASEStageScheduler, build_optimizer, run_formal_optimizer_step


def test_four_microbatch_metrics_are_averaged_not_last_micro(monkeypatch):
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)

    def fixture_loss(_outputs, batch, *, collect_metrics=True):
        value = float(batch["metric_value"])
        loss = next(param for param in model.parameters() if param.requires_grad).sum() * 0.0 + torch.tensor(value, dtype=torch.float32)
        return loss, {"fixture_metric": value} if collect_metrics else {}

    monkeypatch.setattr(trainer, "care_ase_loss", fixture_loss)
    batches = []
    for value in (1.0, 3.0, 5.0, 7.0):
        batches.append(
            {
                "image": torch.zeros(1, 3, 8, 64, 64),
                "availability": torch.ones(1, 3),
                "seg": torch.zeros(1, 8, 64, 64, dtype=torch.long),
                "metric_value": value,
            }
        )
    result = run_formal_optimizer_step(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        microbatches=batches,
        global_step=0,
        gradient_accumulation=4,
        autocast_enabled=False,
    )
    assert result["metrics"]["fixture_metric"] == 4.0
    assert result["metric_aggregation"] == "mean_over_four_microbatches"
