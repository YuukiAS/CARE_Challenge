import torch

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import (
    CAREASEStageScheduler,
    CHECKPOINT_SCHEMA_VERSION,
    build_optimizer,
    load_care_ase_checkpoint,
    save_care_ase_checkpoint,
)


def test_checkpoint_schema_v3_full_reload(tmp_path):
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    scheduler.step(0)
    ckpt = tmp_path / "checkpoint_step00001.pt"

    save_care_ase_checkpoint(
        ckpt,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        global_step=1,
        stage_id="A",
        next_batch_hash="next-bundle",
        loss_history_tail=[],
        sampler_state={
            "sampler_rng_state": "dummy",
            "next_optimizer_step_micro_descriptor_sha256": "next-bundle",
            "next_optimizer_step_micro_descriptor_bundle": [{"case_id": "fixture"}],
        },
        training_source_commit_sha="source",
        origin_main_sha="source",
        effective_contract_sha256="contract",
        external_review_permit_sha256="permit",
        critical_source_manifest_sha256="critical",
    )

    reloaded, payload = load_care_ase_checkpoint(ckpt, restore_rng=False)
    assert payload["schema_version"] == CHECKPOINT_SCHEMA_VERSION == 3
    assert payload["training_source_commit_sha"] == "source"
    assert payload["critical_source_manifest_sha256"] == "critical"
    assert ckpt.with_suffix(".pt.sha256").is_file()
    assert set(model.state_dict()) == set(reloaded.state_dict())
