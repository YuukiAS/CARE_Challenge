import pytest

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import CAREASEStageScheduler, build_optimizer, save_care_ase_checkpoint


def test_early_training_complete_token_rejected(tmp_path):
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    with pytest.raises(ValueError, match="TRAINING_COMPLETE"):
        save_care_ase_checkpoint(
            tmp_path / "checkpoint_step00001.pt",
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            global_step=1,
            stage_id="A",
            next_batch_hash="TRAINING_COMPLETE",
            loss_history_tail=[],
            sampler_state={"next_optimizer_step_micro_descriptor_sha256": "TRAINING_COMPLETE"},
        )
