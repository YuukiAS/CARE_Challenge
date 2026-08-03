import pytest

from src.care_myocardium.training.care_ase_runtime import validate_resume_payload


def _payload():
    return {
        "fold": 1,
        "config": {"fold": 1, "checkpoint_path": "/missing/stock.pt"},
        "effective_contract_sha256": "contract",
        "critical_source_manifest_sha256": "critical",
        "split_file_sha256": "split",
        "actual_train_case_ids_sha256": "actual",
        "hard_negative_manifest_sha256": "hard",
        "area_reference_receipt_sha256": "area",
        "stock_checkpoint_sha256": "MISSING",
        "formal_resumable": True,
        "accumulation_microbatch_cursor": 0,
        "next_optimizer_step_micro_descriptor_sha256": "next",
    }


def test_cross_fold_resume_is_rejected_before_sampler_restore():
    with pytest.raises(RuntimeError, match="payload_fold"):
        validate_resume_payload(
            _payload(),
            requested_fold=4,
            expected_effective_contract_sha256="contract",
            expected_critical_source_manifest_sha256="critical",
            expected_split_file_sha256="split",
            expected_actual_train_case_ids_sha256="actual",
            expected_hard_negative_manifest_sha256="hard",
            expected_area_reference_receipt_sha256="area",
        )


def test_resume_rejects_contract_and_next_bundle_mismatch():
    payload = _payload()
    payload["next_optimizer_step_micro_descriptor_sha256"] = "UNSET"
    with pytest.raises(RuntimeError, match="effective_contract_sha256"):
        validate_resume_payload(
            payload,
            requested_fold=1,
            expected_effective_contract_sha256="new-contract",
            expected_critical_source_manifest_sha256="critical",
            expected_split_file_sha256="split",
            expected_actual_train_case_ids_sha256="actual",
            expected_hard_negative_manifest_sha256="hard",
            expected_area_reference_receipt_sha256="area",
        )
