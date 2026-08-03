import pytest

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import CAREASEStageScheduler, build_optimizer, load_care_ase_checkpoint, save_care_ase_checkpoint


def test_checkpoint_load_rejects_bad_sidecar(tmp_path):
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    ckpt = tmp_path / "checkpoint_step00001.pt"
    save_care_ase_checkpoint(
        ckpt,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        global_step=1,
        stage_id="A",
        next_batch_hash="next",
        loss_history_tail=[],
        sampler_state={"next_optimizer_step_micro_descriptor_sha256": "next"},
    )
    ckpt.with_suffix(".pt.sha256").write_text("bad  checkpoint_step00001.pt\n", encoding="utf-8")
    with pytest.raises(ValueError, match="sidecar SHA mismatch"):
        load_care_ase_checkpoint(ckpt, restore_rng=False)
