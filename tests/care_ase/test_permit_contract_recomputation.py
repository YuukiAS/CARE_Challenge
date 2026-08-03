import json

import pytest

import src.care_myocardium.training.care_ase_runtime as chunk


def _permit(tmp_path, **overrides):
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
    payload.update(overrides)
    path = tmp_path / "permit.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _patch_git(monkeypatch):
    monkeypatch.setattr(chunk, "git_fetch_origin_main", lambda: None)
    monkeypatch.setattr(chunk, "git_sha", lambda ref: "b" * 40)
    monkeypatch.setattr(chunk, "worktree_dirty_paths", lambda: [])
    monkeypatch.setattr(chunk, "effective_contract_sha256", lambda: "contract")
    monkeypatch.setattr(chunk, "combined_source_hash", lambda: "critical")
    monkeypatch.setattr(chunk, "combined_source_hash_at_commit", lambda _ref: "critical")
    monkeypatch.setattr(chunk, "review_packet_contains_implementation_source", lambda _review, _impl: True)
    monkeypatch.setattr(
        chunk.subprocess,
        "run",
        lambda *args, **kwargs: type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})(),
    )


def test_external_permit_recomputes_effective_contract(monkeypatch, tmp_path):
    _patch_git(monkeypatch)
    path = _permit(tmp_path, effective_contract_sha256="old-contract")
    with pytest.raises(RuntimeError, match="effective contract mismatch"):
        chunk.verify_external_review_permit(path, expected_environment_determinism_manifest_sha256="environment")


def test_external_permit_rejects_dirty_worktree(monkeypatch, tmp_path):
    _patch_git(monkeypatch)
    monkeypatch.setattr(chunk, "worktree_dirty_paths", lambda: [" M src/care_myocardium/models/care_ase.py"])
    with pytest.raises(RuntimeError, match="clean worktree"):
        chunk.verify_external_review_permit(_permit(tmp_path), expected_environment_determinism_manifest_sha256="environment")


def test_external_permit_records_live_contract_and_manifest(monkeypatch, tmp_path):
    _patch_git(monkeypatch)
    permit = chunk.verify_external_review_permit(_permit(tmp_path), expected_environment_determinism_manifest_sha256="environment")
    assert permit["current_effective_contract_sha256"] == "contract"
    assert permit["current_critical_source_manifest_sha256"] == "critical"
    assert permit["current_environment_determinism_manifest_sha256"] == "environment"
