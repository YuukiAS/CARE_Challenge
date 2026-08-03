import json

import pytest

from src.care_myocardium.training import care_ase_runtime as runtime


def _sha(path):
    return runtime.sha256_file(path)


def _bundle(tmp_path, *, fold=1):
    h1 = tmp_path / "hard1.json"
    h4 = tmp_path / "hard4.json"
    c1 = tmp_path / "cache1.json"
    c4 = tmp_path / "cache4.json"
    for path in (h1, h4, c1, c4):
        path.write_text(path.name + "\n", encoding="utf-8")
    payload = {
        "implementation_source_commit_sha": "a" * 40,
        "review_packet_commit_sha": "b" * 40,
        "effective_contract_sha256": "contract",
        "hard_negative_manifest_fold1_path": str(h1),
        "hard_negative_manifest_fold1_sha256": _sha(h1),
        "hard_negative_manifest_fold4_path": str(h4),
        "hard_negative_manifest_fold4_sha256": _sha(h4),
        "full_case_target_cache_manifest_fold1_path": str(c1),
        "full_case_target_cache_manifest_fold1_sha256": _sha(c1),
        "full_case_target_cache_manifest_fold4_path": str(c4),
        "full_case_target_cache_manifest_fold4_sha256": _sha(c4),
        "direct_stock_oof_provenance_manifest_sha256": "oof",
        "area_reference_receipt_sha256": "area",
    }
    payload["bundle_payload_sha256"] = runtime.json_sha(payload)
    path = tmp_path / "formal_runtime_input_bundle.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def _post_commit_bound_bundle(tmp_path):
    path, payload = _bundle(tmp_path)
    payload.pop("review_packet_commit_sha")
    payload["review_packet_sha_binding_mode"] = "external_review_request_and_external_permit"
    payload.pop("bundle_payload_sha256", None)
    payload["bundle_payload_sha256"] = runtime.json_sha(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path, payload


def test_commit_b_formal_runtime_input_bundle_verifies_paths_and_shas(tmp_path):
    path, _payload = _bundle(tmp_path)
    loaded = runtime.load_formal_runtime_input_bundle(
        path,
        fold=1,
        implementation_source_sha="a" * 40,
        review_packet_sha="b" * 40,
        effective_contract_sha256_expected="contract",
    )
    assert loaded["target_builder_provenance"] == "full_case_target_cache_manifest_verified"
    assert loaded["verified_for_fold"] == 1


def test_commit_b_self_sha_is_bound_by_permit_not_bundle(tmp_path):
    path, _payload = _post_commit_bound_bundle(tmp_path)
    loaded = runtime.load_formal_runtime_input_bundle(
        path,
        fold=1,
        implementation_source_sha="a" * 40,
        review_packet_sha="b" * 40,
        effective_contract_sha256_expected="contract",
    )
    assert loaded["review_packet_sha_binding_mode"] == "external_review_request_and_external_permit"


def test_self_referential_commit_b_sha_in_post_commit_bundle_rejected(tmp_path):
    path, payload = _post_commit_bound_bundle(tmp_path)
    payload["review_packet_commit_sha"] = "b" * 40
    payload.pop("bundle_payload_sha256", None)
    payload["bundle_payload_sha256"] = runtime.json_sha(payload)
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="must not embed a self-referential"):
        runtime.load_formal_runtime_input_bundle(
            path,
            fold=1,
            implementation_source_sha="a" * 40,
            review_packet_sha="b" * 40,
            effective_contract_sha256_expected="contract",
        )


def test_untracked_or_tampered_runtime_manifest_rejected(tmp_path):
    path, payload = _bundle(tmp_path)
    hard = tmp_path / "hard1.json"
    hard.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="SHA mismatch"):
        runtime.load_formal_runtime_input_bundle(
            path,
            fold=1,
            implementation_source_sha=payload["implementation_source_commit_sha"],
            review_packet_sha=payload["review_packet_commit_sha"],
            effective_contract_sha256_expected=payload["effective_contract_sha256"],
        )


def test_commit_a_checkout_without_commit_b_bundle_rejected(tmp_path):
    with pytest.raises(RuntimeError, match="bundle is missing"):
        runtime.load_formal_runtime_input_bundle(
            tmp_path / "missing.json",
            fold=1,
            implementation_source_sha="a" * 40,
            review_packet_sha="b" * 40,
            effective_contract_sha256_expected="contract",
        )
