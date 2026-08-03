import pytest

from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import (
    CAREASEStageScheduler,
    build_optimizer,
    load_care_ase_checkpoint,
    save_care_ase_checkpoint,
)


def _formal_kwargs():
    return {
        "training_source_commit_sha": "a" * 40,
        "review_packet_commit_sha": "b" * 40,
        "origin_main_sha": "b" * 40,
        "origin_main_at_review_request_sha": "b" * 40,
        "effective_contract_sha256": "contract",
        "external_review_permit_sha256": "permit",
        "critical_source_manifest_sha256": "critical",
        "split_file_sha256": "split-file",
        "split_case_lists_sha256": "split-cases",
        "actual_train_case_ids_sha256": "actual-train",
        "hard_negative_manifest_sha256": "hard-negative",
        "area_reference_receipt_sha256": "area",
        "case_metadata_sha256": "case-meta",
        "plans_hash": "plans",
        "stock_checkpoint_hash": "stock",
        "augmentation_contract_sha256": "augmentation",
        "full_case_target_profile_manifest_sha256": "profile",
        "full_case_target_cache_manifest_sha256": "cache",
        "environment_determinism_manifest_sha256": "environment",
        "formal_resumable": True,
    }


def test_formal_checkpoint_schema_v4_refuses_short_smoke_placeholder(tmp_path):
    model = build_care_ase_for_fold(2)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    kwargs = _formal_kwargs()
    kwargs["review_packet_commit_sha"] = "SHORT_SMOKE_NO_FORMAL_CREDIT"
    with pytest.raises(ValueError, match="placeholder provenance"):
        save_care_ase_checkpoint(
            tmp_path / "bad.pt",
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            global_step=1,
            stage_id="A",
            next_batch_hash="next",
            loss_history_tail=[],
            sampler_state={
                "sampler_rng_state": "dummy",
                "next_optimizer_step_micro_descriptor_sha256": "next",
                "next_optimizer_step_micro_descriptor_bundle": [{"case_id": "fixture"}],
                "micro_patch_rng_state": "dummy",
            },
            **kwargs,
        )


def test_formal_checkpoint_schema_v4_roundtrip_with_full_provenance(tmp_path):
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
        sampler_state={
            "sampler_rng_state": "dummy",
            "next_optimizer_step_micro_descriptor_sha256": "next",
            "next_optimizer_step_micro_descriptor_bundle": [{"case_id": "fixture"}],
            "micro_patch_rng_state": "dummy",
        },
        **_formal_kwargs(),
    )
    _model, payload = load_care_ase_checkpoint(ckpt, restore_rng=False)
    assert payload["schema_version"] == 4
    assert payload["formal_resumable"] is True
    assert payload["effective_contract_sha256"] == "contract"
