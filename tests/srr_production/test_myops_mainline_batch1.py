from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = REPO_ROOT / "scripts/srr_production/validate_myops_mainline.py"
ENTRYPOINTS = REPO_ROOT / "configs/srr_production/entrypoints.yaml"
OUT = REPO_ROOT / "results/srr_production/code_maturity"


def run_validator_known_bad(name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--known-bad", name],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_batch1_authority_remains_nontraining_blocked_for_batch2() -> None:
    cfg = yaml.safe_load(ENTRYPOINTS.read_text(encoding="utf-8"))
    assert cfg["formal_training_status"] == "BLOCKED_PENDING_BATCH2B_INFERENCE_AND_FAIR_EVALUATION"
    assert cfg["formal_entrypoints"] == []
    candidate = next(row for row in cfg["candidate_entrypoints"] if row["id"] == "myops_batch1_mainline_validator")
    assert candidate["formal_authority"] is False


def test_batch1_oof_manifest_and_receipts_are_real() -> None:
    manifest = json.loads((OUT / "batch1_anchor_oof_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "COMPLETE_RAW_REAL_OOF_ANCHOR"
    assert manifest["case_count"] == 220
    assert manifest["unique_cases"] == 220
    assert manifest["fold_counts"] == {"0": 44, "1": 44, "2": 44, "3": 44, "4": 44}
    assert all(row["is_oof"] for row in manifest["entries"])
    first = manifest["entries"][0]
    assert first["anchor_semantics"] == "raw_oof_anchor_unmodified"
    for key in ("probability_sha256", "prediction_sha256", "checkpoint_sha256", "split_hash", "preprocessing_hash"):
        assert len(first[key]) == 64


def test_batch1_smoke_receipts_show_required_controls() -> None:
    intervention = json.loads((OUT / "batch1_intervention_receipt.json").read_text(encoding="utf-8"))
    assert intervention["optimizer_step_count"] == 0
    assert intervention["slurm_job_count"] == 0
    assert intervention["formal_training_count"] == 0
    assert intervention["anchor_identity_max_abs_delta"] == 0.0
    assert intervention["invalid_missing_slot_gate_max"] == 0.0
    assert intervention["memory_intervention_proposal_delta_mean"] > 0.0
    assert intervention["memory_intervention_final_delta_mean"] > 0.0
    roundtrip = json.loads((OUT / "batch1_checkpoint_roundtrip.json").read_text(encoding="utf-8"))
    assert roundtrip["max_tensor_delta_after_reload"] == 0.0
    forward = json.loads((OUT / "batch1_real_case_forward_receipt.json").read_text(encoding="utf-8"))
    assert forward["final_output_mode"] == "anchor_bounded_srr_correction"
    assert forward["no_t2_edema_correction_abs_max"] == 0.0
    assert forward["no_t2_exact_zero"]["status"] == "PASS"


def test_batch2a_required_receipts_are_complete() -> None:
    required = [
        "batch2a_shared_builder_contract.json",
        "batch2a_prototype_crossfit_audit.json",
        "batch2a_no_t2_exact_zero_receipt.json",
        "batch2a_known_bad_execution_report.json",
        "batch2a_checkpoint_resume_receipt.json",
    ]
    for name in required:
        assert (OUT / name).is_file(), name
    contract = json.loads((OUT / "batch2a_shared_builder_contract.json").read_text(encoding="utf-8"))
    assert contract["status"] == "BATCH_2A_SHARED_PRODUCTION_COMPONENTS_CONTRACT_NONTRAINING"
    assert contract["authority_status_after_batch2a"] == "BATCH_2A_BATCH1_CLOSURE_COMPLETE"
    audit = json.loads((OUT / "batch2a_prototype_crossfit_audit.json").read_text(encoding="utf-8"))
    assert audit["status"] == "REAL_CASEWISE_PROTOTYPE_MEMORY_READY"
    assert audit["zero_count_slot_policy"] == "masked_out_of_similarity"
    no_t2 = json.loads((OUT / "batch2a_no_t2_exact_zero_receipt.json").read_text(encoding="utf-8"))
    assert no_t2["status"] == "PASS"
    assert no_t2["candidate_probability_abs_max"] == 0.0
    assert no_t2["soft_roi_abs_max"] == 0.0
    assert no_t2["refinement_residual_abs_max"] == 0.0
    assert no_t2["bounded_correction_abs_max"] == 0.0
    assert no_t2["loss_value"] == 0.0
    assert no_t2["edema_owned_grad_abs_sum"] == 0.0
    checkpoint = json.loads((OUT / "batch2a_checkpoint_resume_receipt.json").read_text(encoding="utf-8"))
    assert checkpoint["schema_version"] == 2
    assert checkpoint["optimizer_param_groups_match"] is True
    assert checkpoint["rng_next_sampling_match"] is True
    assert checkpoint["global_step_not_reset"] is True
    assert checkpoint["epoch_not_reset"] is True


def test_batch1_known_bad_fixtures_are_rejected() -> None:
    for fixture in (
        "deterministic_prototype",
        "prototype_missing_provenance",
        "validation_leakage",
        "current_case_leakage",
        "no_t2_edema_nonzero",
        "missing_modality_slot_nonzero",
        "pattern_sip_no_router_grad",
        "memory_no_effect",
        "pure_srr_production",
        "non_oof_anchor",
        "checkpoint_resets_state",
        "legacy_b6_chain",
    ):
        result = run_validator_known_bad(fixture)
        assert result.returncode != 0
        assert "REJECTED" in result.stdout
        assert fixture in result.stdout
