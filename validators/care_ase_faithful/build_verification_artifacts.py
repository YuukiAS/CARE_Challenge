#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    validate_evidence,
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
LAUNCH_ORIGIN_DEVELOP_SHA = "e628bd14582350b265567ef5ec70b1d74d273b3b"
LAUNCH_VERIFIER_WORKTREE_HEAD = "e628bd14582350b265567ef5ec70b1d74d273b3b"
REQUIRED_FREEZE_ARTIFACTS = [
    "verification_contract.json",
    "public_test_manifest.json",
    "protected_known_bad_manifest.json",
    "verifier_fingerprint.json",
    "verifier_session_receipt.json",
    "verifier_freeze_receipt.json",
]


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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fingerprint_input_paths() -> list[Path]:
    paths = [
        VALIDATOR_PATH,
        BUILDER_PATH,
        TEST_PATH,
        VERIFICATION_DIR / "verification_contract.json",
        VERIFICATION_DIR / "public_test_manifest.json",
        VERIFICATION_DIR / "protected_known_bad_manifest.json",
        VERIFICATION_DIR / "public_reference_evidence.json",
        VERIFICATION_DIR / "verifier_local_commands_recorded_in_manifests.json",
    ]
    paths.extend(sorted((VERIFICATION_DIR / "protected_reports").glob("*.json")))
    return paths


def fingerprint_file_hashes(contract_hash: str) -> dict[str, str]:
    file_hashes = {str(path.relative_to(ROOT)): sha256_file(path) for path in fingerprint_input_paths() if path.exists()}
    file_hashes["automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md"] = contract_hash
    return file_hashes


def _record_error(errors: list[str], condition: bool, message: str) -> None:
    if not condition:
        errors.append(message)


def check_only() -> int:
    errors: list[str] = []
    contract_hash = sha256_file(CONTRACT_PATH)
    _record_error(errors, contract_hash == FROZEN_CONTRACT_SHA256, f"frozen contract sha mismatch: {contract_hash}")

    for name in REQUIRED_FREEZE_ARTIFACTS:
        _record_error(errors, (VERIFICATION_DIR / name).is_file(), f"missing required freeze artifact: {name}")
    for name in (
        "public_reference_evidence.json",
        "public_reference_validation_result.json",
        "verifier_local_commands_recorded_in_manifests.json",
    ):
        _record_error(errors, (VERIFICATION_DIR / name).is_file(), f"missing supporting artifact: {name}")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2

    verification_contract = load_json(VERIFICATION_DIR / "verification_contract.json")
    public_reference = load_json(VERIFICATION_DIR / "public_reference_evidence.json")
    public_result = load_json(VERIFICATION_DIR / "public_reference_validation_result.json")
    public_manifest = load_json(VERIFICATION_DIR / "public_test_manifest.json")
    protected_manifest = load_json(VERIFICATION_DIR / "protected_known_bad_manifest.json")
    command_log = load_json(VERIFICATION_DIR / "verifier_local_commands_recorded_in_manifests.json")
    fingerprint = load_json(VERIFICATION_DIR / "verifier_fingerprint.json")
    freeze_receipt = load_json(VERIFICATION_DIR / "verifier_freeze_receipt.json")

    _record_error(errors, verification_contract.get("schema") == "CARE_ASE_FAITHFUL_VERIFICATION_CONTRACT_V1", "verification_contract.schema")
    _record_error(errors, verification_contract.get("task_id") == TASK_ID, "verification_contract.task_id")
    _record_error(errors, verification_contract.get("request_nonce") == REQUEST_NONCE, "verification_contract.request_nonce")
    _record_error(errors, verification_contract.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256, "verification_contract.frozen_contract_sha256")
    _record_error(errors, verification_contract.get("protected_known_bad_categories") == KNOWN_BAD_CATEGORIES, "verification_contract.protected_known_bad_categories")
    _record_error(errors, verification_contract.get("required_loss_terms") == list(reference_evidence()["losses"]["terms"].keys()), "verification_contract.required_loss_terms")
    _record_error(errors, verification_contract.get("required_metric_interfaces") == reference_evidence()["evaluation_interface"]["metrics"], "verification_contract.required_metric_interfaces")

    _record_error(errors, public_reference == reference_evidence(), "public_reference_evidence does not match validator reference")
    reference_failures = validate_evidence(public_reference, verification_contract)
    _record_error(errors, not reference_failures, f"public reference validation failures: {reference_failures}")
    _record_error(errors, public_result.get("exit_code") == 0, "public_reference_validation_result.exit_code")

    safe_commands = public_manifest.get("repository_safe_commands", [])
    _record_error(errors, len(safe_commands) == 3, "public_test_manifest.repository_safe_commands_count")
    for command in safe_commands:
        _record_error(errors, command.get("exit_code") == 0, f"repository_safe_command_failed: {command.get('purpose')}")
    _record_error(errors, command_log.get("repository_safe_commands") == safe_commands, "command_log.repository_safe_commands_mismatch")

    expected_ids = [item["id"] for item in KNOWN_BAD_CATEGORIES]
    known_bad_invocations = protected_manifest.get("known_bad_invocations", [])
    _record_error(errors, protected_manifest.get("count") == 24, "protected_manifest.count")
    _record_error(errors, protected_manifest.get("all_returned_nonzero") is True, "protected_manifest.all_returned_nonzero")
    _record_error(errors, [item.get("id") for item in known_bad_invocations] == expected_ids, "protected_manifest.known_bad_id_order")
    _record_error(errors, command_log.get("protected_known_bad_invocations") == known_bad_invocations, "command_log.protected_known_bad_mismatch")
    for item in known_bad_invocations:
        report_path = ROOT / item.get("report_path", "")
        _record_error(errors, item.get("exit_code") != 0, f"known_bad_exit_zero: {item.get('id')}")
        _record_error(errors, item.get("passed_fail_closed") is True, f"known_bad_not_fail_closed: {item.get('id')}")
        _record_error(errors, report_path.is_file(), f"missing known_bad_report: {item.get('id')}")
        if report_path.is_file():
            report = load_json(report_path)
            _record_error(errors, report.get("known_bad_case_id") == item.get("id"), f"known_bad_report_id_mismatch: {item.get('id')}")
            _record_error(errors, report.get("passed") is False, f"known_bad_report_passed: {item.get('id')}")
            _record_error(errors, int(report.get("failure_count", 0)) > 0, f"known_bad_report_no_failures: {item.get('id')}")
            _record_error(errors, item.get("report_sha256") == sha256_file(report_path), f"known_bad_report_sha_mismatch: {item.get('id')}")

    file_hashes = fingerprint_file_hashes(contract_hash)
    digest = sha256_bytes(json.dumps(file_hashes, sort_keys=True).encode("utf-8"))
    _record_error(errors, fingerprint.get("file_hashes") == file_hashes, "verifier_fingerprint.file_hashes")
    _record_error(errors, fingerprint.get("fingerprint_sha256") == digest, "verifier_fingerprint.fingerprint_sha256")
    _record_error(errors, fingerprint.get("protected_known_bad_count") == 24, "verifier_fingerprint.protected_known_bad_count")
    _record_error(errors, fingerprint.get("protected_known_bad_all_nonzero") is True, "verifier_fingerprint.protected_known_bad_all_nonzero")

    _record_error(errors, freeze_receipt.get("state_for_controller") == "VERIFIER_FROZEN", "freeze_receipt.state_for_controller")
    _record_error(errors, freeze_receipt.get("required_artifacts") == REQUIRED_FREEZE_ARTIFACTS, "freeze_receipt.required_artifacts")
    _record_error(errors, freeze_receipt.get("verifier_fingerprint_sha256") == digest, "freeze_receipt.verifier_fingerprint_sha256")
    _record_error(errors, freeze_receipt.get("protected_known_bad_count") == 24, "freeze_receipt.protected_known_bad_count")
    _record_error(errors, freeze_receipt.get("protected_known_bad_all_nonzero") is True, "freeze_receipt.protected_known_bad_all_nonzero")
    _record_error(errors, freeze_receipt.get("executor_may_start_after_controller_freezes_this_commit") is True, "freeze_receipt.executor_start_gate")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print("verification artifact package is stable")
    return 0


def build_artifacts() -> int:
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

    unittest_result = run_command([sys.executable, "-m", "unittest", "tests.care_ase_faithful.test_verifier_package"])
    v3_validator_result = run_command([sys.executable, "scripts/automation/validate_agent_flow_v3.py", "--repo-root", "."])
    public_manifest["repository_safe_commands"] = [
        {
            "purpose": "public reference evidence validates under the frozen contract",
            **public_result,
        },
        {
            "purpose": "verifier unittest package exercises public reference and all protected known-bad categories",
            **unittest_result,
        },
        {
            "purpose": "Agent-Flow v3 request/current deterministic state validation",
            **v3_validator_result,
        },
    ]
    write_json(VERIFICATION_DIR / "public_test_manifest.json", public_manifest)

    command_log = {
        "schema": "CARE_ASE_FAITHFUL_VERIFIER_COMMAND_LOG_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "created_utc": now,
        "artifact_builder_command": [sys.executable, str(BUILDER_PATH.relative_to(ROOT))],
        "repository_safe_commands": public_manifest["repository_safe_commands"],
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

    file_hashes = fingerprint_file_hashes(contract_hash)
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
            *REQUIRED_FREEZE_ARTIFACTS,
        ],
        "public_reference_exit_code": public_result["exit_code"],
        "protected_known_bad_count": len(protected_results),
        "protected_known_bad_all_nonzero": all(item["passed_fail_closed"] for item in protected_results),
        "executor_may_start_after_controller_freezes_this_commit": True,
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "verifier_freeze_receipt.json", freeze_receipt)
    return (
        0
        if public_result["exit_code"] == 0
        and unittest_result["exit_code"] == 0
        and v3_validator_result["exit_code"] == 0
        and all(item["passed_fail_closed"] for item in protected_results)
        else 2
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify CARE-ASE faithful verifier artifacts.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args(argv)
    if args.repo_root.resolve() != ROOT:
        parser.error(f"--repo-root must resolve to {ROOT}")
    if args.check_only:
        return check_only()
    return build_artifacts()


if __name__ == "__main__":
    raise SystemExit(main())
