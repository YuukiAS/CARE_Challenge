#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_contract_evidence import (
    FROZEN_CONTRACT_SHA256,
    KNOWN_BAD_CATEGORIES,
    REQUEST_NONCE,
    TASK_ID,
    reference_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_DIR = ROOT / "results" / "agent_flow_v3" / TASK_ID / "verification"
CONTRACT_PATH = ROOT / "automation" / "agent_flow_v3" / "tasks" / TASK_ID / "FROZEN_CONTRACT.md"
CURRENT_PATH = ROOT / "automation" / "agent_flow_v3" / "tasks" / TASK_ID / "CURRENT.json"
REQUEST_PATH = ROOT / "automation" / "agent_flow_v3" / "tasks" / TASK_ID / "REQUEST.json"
VALIDATOR_PATH = ROOT / "validators" / "care_ase_faithful" / "validate_contract_evidence.py"
BUILDER_PATH = ROOT / "validators" / "care_ase_faithful" / "build_verification_artifacts.py"
TEST_PATH = ROOT / "tests" / "care_ase_faithful" / "test_verifier_package.py"
LAUNCH_ORIGIN_DEVELOP_SHA = "4234dd1f2380563acc27f4af8aff226f4b95431e"
LAUNCH_VERIFIER_WORKTREE_HEAD = "4234dd1f2380563acc27f4af8aff226f4b95431e"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(completed.stderr.encode("utf-8")),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current")
    observed_origin_develop = git("rev-parse", "origin/develop")
    contract_hash = sha256_file(CONTRACT_PATH)
    if contract_hash != FROZEN_CONTRACT_SHA256:
        raise SystemExit(f"frozen contract sha mismatch: {contract_hash}")

    verification_contract = {
        "schema": "CARE_ASE_FAITHFUL_VERIFICATION_CONTRACT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_path": str(CONTRACT_PATH.relative_to(ROOT)),
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "validator": str(VALIDATOR_PATH.relative_to(ROOT)),
        "evidence_schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_EVIDENCE_V1",
        "exit_code_semantics": {
            "0": "all required faithful-implementation evidence is present and internally consistent",
            "2": "fail-closed contract violation or missing evidence",
        },
        "required_loss_terms": list(reference_evidence()["losses"]["terms"].keys()),
        "required_metric_interfaces": reference_evidence()["evaluation_interface"]["metrics"],
        "protected_known_bad_categories": KNOWN_BAD_CATEGORIES,
        "executor_boundary": {
            "may_read_public_manifest": True,
            "must_not_edit": ["tests/**", "validators/**", "automation/agent_flow_v3/schema.json", "prompts/blueprints/**"],
            "must_produce_real_runtime_receipts": True,
        },
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "verification_contract.json", verification_contract)

    public_reference_path = VERIFICATION_DIR / "public_reference_evidence.json"
    write_json(public_reference_path, reference_evidence())
    public_command = [
        sys.executable,
        str(VALIDATOR_PATH.relative_to(ROOT)),
        "--verification-contract",
        str((VERIFICATION_DIR / "verification_contract.json").relative_to(ROOT)),
        "--evidence",
        str(public_reference_path.relative_to(ROOT)),
    ]
    public_result = run_command(public_command)
    write_json(VERIFICATION_DIR / "public_reference_validation_result.json", public_result)

    protected_results = []
    for item in KNOWN_BAD_CATEGORIES:
        report_path = VERIFICATION_DIR / "protected_reports" / f"{item['id']}.json"
        command = [
            sys.executable,
            str(VALIDATOR_PATH.relative_to(ROOT)),
            "--verification-contract",
            str((VERIFICATION_DIR / "verification_contract.json").relative_to(ROOT)),
            "--known-bad-id",
            item["id"],
            "--report-json",
            str(report_path.relative_to(ROOT)),
        ]
        result = run_command(command)
        protected_results.append(
            {
                **item,
                "command": command,
                "exit_code": result["exit_code"],
                "stdout_sha256": result["stdout_sha256"],
                "stderr_sha256": result["stderr_sha256"],
                "report_path": str(report_path.relative_to(ROOT)),
                "report_sha256": sha256_file(report_path) if report_path.exists() else None,
                "passed_fail_closed": result["exit_code"] != 0,
            }
        )

    public_manifest = {
        "schema": "CARE_ASE_FAITHFUL_PUBLIC_TEST_MANIFEST_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "public_tests": [
            {
                "path": str(TEST_PATH.relative_to(ROOT)),
                "purpose": "validator reference evidence passes and all known-bad ids fail closed through subprocess invocation",
            }
        ],
        "public_reference_evidence_path": str(public_reference_path.relative_to(ROOT)),
        "public_reference_validation": public_result,
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "public_test_manifest.json", public_manifest)

    protected_manifest = {
        "schema": "CARE_ASE_FAITHFUL_PROTECTED_KNOWN_BAD_MANIFEST_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "count": len(protected_results),
        "all_returned_nonzero": all(item["passed_fail_closed"] for item in protected_results),
        "known_bad_invocations": protected_results,
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "protected_known_bad_manifest.json", protected_manifest)

    command_log = {
        "schema": "CARE_ASE_FAITHFUL_VERIFIER_COMMAND_LOG_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "created_utc": now,
        "artifact_builder_command": [sys.executable, str(BUILDER_PATH.relative_to(ROOT))],
        "public_reference_validation": public_result,
        "protected_known_bad_invocations": protected_results,
    }
    write_json(VERIFICATION_DIR / "verifier_local_commands_recorded_in_manifests.json", command_log)

    session_receipt = {
        "schema": "CARE_AGENT_FLOW_V3_ROLE_RECEIPT",
        "role": "verifier",
        "thread_id": "019fd76a-5628-7972-ac2f-59bbd81b1587",
        "invalid_prior_thread_id": "019fd2ea-92b5-7601-a323-9ac3d87d4a2d",
        "codex_home": "/users/a/e/aereinh/.codex-homes/CARE_care-ase-faithful_VERIFIER",
        "worktree": str(ROOT),
        "local_branch": branch,
        "pid_or_process_status": f"artifact_builder_pid:{os.getpid()}",
        "log_path": str((VERIFICATION_DIR / "verifier_local_commands_recorded_in_manifests.json").relative_to(ROOT)),
        "state_path": str(CURRENT_PATH.relative_to(ROOT)),
        "write_scope": [
            "tests/**",
            "validators/**",
            "automation/agent_flow_v3/**",
            "results/agent_flow_v3/care-ase-faithful/verification/**",
        ],
        "forbidden_scope": [
            "src/**",
            "scripts/training/**",
            "scripts/inference/**",
            "jobs/**",
            "configs/**",
            "prompts/blueprints/**",
            "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        ],
        "last_commit_sha": head,
        "controller_verified_launch_origin_develop_sha": LAUNCH_ORIGIN_DEVELOP_SHA,
        "controller_verified_launch_verifier_worktree_head": LAUNCH_VERIFIER_WORKTREE_HEAD,
        "observed_origin_develop_sha_at_artifact_build": observed_origin_develop,
        "started_utc": now,
        "updated_utc": now,
        "python_executable": sys.executable,
    }
    write_json(VERIFICATION_DIR / "verifier_session_receipt.json", session_receipt)

    fingerprint_inputs = [
        VALIDATOR_PATH,
        BUILDER_PATH,
        TEST_PATH,
        VERIFICATION_DIR / "verification_contract.json",
        VERIFICATION_DIR / "public_test_manifest.json",
        VERIFICATION_DIR / "protected_known_bad_manifest.json",
        VERIFICATION_DIR / "public_reference_evidence.json",
        VERIFICATION_DIR / "verifier_local_commands_recorded_in_manifests.json",
    ]
    fingerprint_inputs.extend(sorted((VERIFICATION_DIR / "protected_reports").glob("*.json")))
    file_hashes = {str(path.relative_to(ROOT)): sha256_file(path) for path in fingerprint_inputs if path.exists()}
    file_hashes["automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md"] = contract_hash
    digest = sha256_bytes(json.dumps(file_hashes, sort_keys=True).encode("utf-8"))
    fingerprint = {
        "schema": "CARE_ASE_FAITHFUL_VERIFIER_FINGERPRINT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "fingerprint_sha256": digest,
        "file_hashes": file_hashes,
        "protected_known_bad_count": len(protected_results),
        "protected_known_bad_all_nonzero": all(item["passed_fail_closed"] for item in protected_results),
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "verifier_fingerprint.json", fingerprint)

    freeze_receipt = {
        "schema": "CARE_ASE_FAITHFUL_VERIFIER_FREEZE_RECEIPT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "state_for_controller": "VERIFIER_FROZEN",
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "verifier_fingerprint_sha256": digest,
        "verifier_worktree_head_before_freeze_commit": head,
        "controller_verified_launch_origin_develop_sha": LAUNCH_ORIGIN_DEVELOP_SHA,
        "controller_verified_launch_verifier_worktree_head": LAUNCH_VERIFIER_WORKTREE_HEAD,
        "observed_origin_develop_sha_at_freeze": observed_origin_develop,
        "verifier_branch": branch,
        "required_artifacts": [
            "verification_contract.json",
            "public_test_manifest.json",
            "protected_known_bad_manifest.json",
            "verifier_fingerprint.json",
            "verifier_session_receipt.json",
            "verifier_freeze_receipt.json",
        ],
        "public_reference_exit_code": public_result["exit_code"],
        "protected_known_bad_count": len(protected_results),
        "protected_known_bad_all_nonzero": all(item["passed_fail_closed"] for item in protected_results),
        "executor_may_start_after_controller_freezes_this_commit": True,
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "verifier_freeze_receipt.json", freeze_receipt)
    return 0 if public_result["exit_code"] == 0 and all(item["passed_fail_closed"] for item in protected_results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
