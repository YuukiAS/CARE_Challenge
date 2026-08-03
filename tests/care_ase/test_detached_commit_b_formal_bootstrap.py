import json

import pytest

from tests.care_ase.test_commit_b_formal_runtime_input_binding import _bundle
from src.care_myocardium.training import care_ase_runtime as runtime


def _permit(tmp_path):
    payload = {
        "decision": "PRETRAINING_EXTERNAL_REVIEW_PASS",
        "reviewed_candidate_commit_sha": "a" * 40,
        "implementation_source_sha": "a" * 40,
        "review_packet_commit_sha": "b" * 40,
        "formal_execution_checkout_commit_sha": "b" * 40,
        "origin_main_at_review_request": "b" * 40,
        "effective_contract_sha256": "contract",
        "critical_source_manifest_sha256": "critical",
        "environment_determinism_manifest_sha256": "environment",
        "formal_runtime_input_bundle_sha256": "bundle",
        "created_utc": "2026-08-03T00:00:00Z",
    }
    path = tmp_path / "permit.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _patch_git(monkeypatch, *, head="b", manifest_a="critical", manifest_b="critical"):
    monkeypatch.setattr(runtime, "git_fetch_origin_main", lambda: None)
    monkeypatch.setattr(runtime, "git_sha", lambda ref: (head * 40)[:40])
    monkeypatch.setattr(runtime, "worktree_dirty_paths", lambda: [])
    monkeypatch.setattr(runtime, "effective_contract_sha256", lambda: "contract")
    monkeypatch.setattr(runtime, "combined_source_hash", lambda: "critical")
    monkeypatch.setattr(runtime, "combined_source_hash_at_commit", lambda ref: manifest_a if str(ref).startswith("a") else manifest_b)
    monkeypatch.setattr(runtime, "review_packet_contains_implementation_source", lambda _review, _impl: True)
    monkeypatch.setattr(
        runtime.subprocess,
        "run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )


def test_detached_commit_b_is_required_for_formal_permit(monkeypatch, tmp_path):
    _patch_git(monkeypatch, head="a")
    with pytest.raises(RuntimeError, match="Commit B checkout"):
        runtime.verify_external_review_permit(_permit(tmp_path), expected_environment_determinism_manifest_sha256="environment")


def test_commit_a_b_critical_source_identity_required(monkeypatch, tmp_path):
    _patch_git(monkeypatch, head="b", manifest_a="changed", manifest_b="critical")
    with pytest.raises(RuntimeError, match="critical source tree changed"):
        runtime.verify_external_review_permit(_permit(tmp_path), expected_environment_determinism_manifest_sha256="environment")


def test_detached_commit_b_bundle_can_be_loaded_after_permit(monkeypatch, tmp_path):
    _patch_git(monkeypatch, head="b")
    permit = runtime.verify_external_review_permit(_permit(tmp_path), expected_environment_determinism_manifest_sha256="environment")
    bundle_path, _ = _bundle(tmp_path)
    loaded = runtime.load_formal_runtime_input_bundle(
        bundle_path,
        fold=1,
        implementation_source_sha=permit["implementation_source_sha"],
        review_packet_sha=permit["review_packet_commit_sha"],
        effective_contract_sha256_expected=permit["effective_contract_sha256"],
    )
    assert loaded["implementation_source_commit_sha"] == "a" * 40
