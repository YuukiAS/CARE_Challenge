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
    PLANNER_REVIEW_COMMIT,
    REQUEST_NONCE,
    REVIEWED_IMPLEMENTATION_FINGERPRINT,
    REVIEWED_INTEGRATION_COMMIT,
    REVIEWED_VERIFIER_FINGERPRINT,
    REVIEW_ROUND,
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
EXECUTABLE_VERIFIER_PATH = ROOT / "validators" / "care_ase_faithful" / "run_executable_verifier.py"
IMPLEMENTATION_EVIDENCE_PATH = ROOT / "results" / "agent_flow_v3" / TASK_ID / "implementation" / "implementation_evidence.json"
CARE_RUNTIME_ROOT = Path(os.environ.get("CARE_VERIFIER_RUNTIME_CARE_ROOT", "/users/a/e/aereinh/CARE"))
CARE_RUNTIME_PYTHON = Path(os.environ.get("CARE_VERIFIER_RUNTIME_PYTHON", str(CARE_RUNTIME_ROOT / "envs" / "env_CARE" / "bin" / "python")))
LAUNCH_ORIGIN_DEVELOP_SHA = "eee6bc4b37e920d0b3bba893edc8ce3c45b81139"
LAUNCH_VERIFIER_WORKTREE_HEAD = "eee6bc4b37e920d0b3bba893edc8ce3c45b81139"
CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED = True
REQUIRED_FREEZE_ARTIFACTS = [
    "verification_contract.json",
    "public_test_manifest.json",
    "protected_known_bad_manifest.json",
    "verifier_fingerprint.json",
    "verifier_session_receipt.json",
    "verifier_freeze_receipt.json",
    "executable_verifier_receipt.json",
    "runtime_mutation_manifest.json",
    "transaction_gate_receipt.json",
    "executable_verifier_local_fail_closed_receipt.json",
    "integrated_implementation_validation_result.json",
]

EXECUTABLE_MUTATION_IDS = [
    "extent_conv3d_alias",
    "dilation_residual_removed",
    "injury_random_init",
    "projection_context_no_final_authority",
    "synthetic_intervention_delta",
    "semantic_disable_only_quadratic_signal",
    "partial_hw_straight_through_zero_loss",
    "full_support_pseudo_tiling",
    "transaction_old_tuple_reused",
    "forged_executor_pass_receipt",
    "no_t2_calls_edema",
    "single_multi_same_call",
    "tile_local_global_bias",
    "deployment_reopens_stock_checkpoint",
    "evaluator_population_mismatch",
    "checkpoint_next_step_drift",
    "artifact_sha_mismatch",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def runtime_env() -> dict[str, str]:
    env = dict(os.environ)
    env.setdefault("CARE_ROOT", str(CARE_RUNTIME_ROOT))
    env.setdefault("nnUNet_raw", str(CARE_RUNTIME_ROOT / "data" / "nnUNet" / "nnUNet_raw"))
    env.setdefault("nnUNet_preprocessed", str(CARE_RUNTIME_ROOT / "data" / "nnUNet" / "nnUNet_preprocessed"))
    env.setdefault("nnUNet_results", str(CARE_RUNTIME_ROOT / "data" / "nnUNet" / "nnUNet_results"))
    env.setdefault("MPLCONFIGDIR", "/users/a/e/aereinh/.tmp/codex-verifier/matplotlib")
    return env


def run_command(command: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, env=env)
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(completed.stderr.encode("utf-8")),
        "stdout_tail": completed.stdout[-2000:],
        "stderr_tail": completed.stderr[-2000:],
    }


def run_command_with_output(command: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False, env=env)
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
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


def active_verifier_thread_id() -> str:
    thread_id_path = Path("/users/a/e/aereinh/.agent-flow-v3/care-ase-faithful/verifier_thread_id")
    if thread_id_path.is_file():
        value = thread_id_path.read_text(encoding="utf-8").strip()
        if value:
            return value
    return "019fd7c1-2d99-74b2-8c95-68ed129613e8"


def fingerprint_input_paths() -> list[Path]:
    paths = [
        VALIDATOR_PATH,
        BUILDER_PATH,
        TEST_PATH,
        EXECUTABLE_VERIFIER_PATH,
        VERIFICATION_DIR / "verification_contract.json",
        VERIFICATION_DIR / "public_test_manifest.json",
        VERIFICATION_DIR / "protected_known_bad_manifest.json",
        VERIFICATION_DIR / "runtime_mutation_manifest.json",
        VERIFICATION_DIR / "transaction_gate_receipt.json",
        VERIFICATION_DIR / "executable_verifier_receipt.json",
        VERIFICATION_DIR / "executable_verifier_local_fail_closed_receipt.json",
        VERIFICATION_DIR / "integrated_implementation_validation_result.json",
        VERIFICATION_DIR / "public_reference_evidence.json",
        VERIFICATION_DIR / "verifier_local_commands_recorded_in_manifests.json",
    ]
    paths.extend(sorted((VERIFICATION_DIR / "runtime_mutation_reports").glob("*.json")))
    paths.extend(sorted((VERIFICATION_DIR / "protected_reports").glob("*.json")))
    return paths


def verifier_source_fingerprint() -> dict[str, Any]:
    paths = [VALIDATOR_PATH, BUILDER_PATH, TEST_PATH, EXECUTABLE_VERIFIER_PATH]
    file_hashes = {str(path.relative_to(ROOT)): sha256_file(path) for path in paths if path.is_file()}
    return {
        "file_hashes": file_hashes,
        "verifier_source_fingerprint_sha256": sha256_bytes(json.dumps(file_hashes, sort_keys=True).encode("utf-8")),
    }


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
    mutation_manifest = load_json(VERIFICATION_DIR / "runtime_mutation_manifest.json")
    executable_receipt = load_json(VERIFICATION_DIR / "executable_verifier_receipt.json")
    local_fail_closed_receipt = load_json(VERIFICATION_DIR / "executable_verifier_local_fail_closed_receipt.json")
    integrated_validation_result = load_json(VERIFICATION_DIR / "integrated_implementation_validation_result.json")
    transaction_receipt = load_json(VERIFICATION_DIR / "transaction_gate_receipt.json")
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
    reference_failures = validate_evidence(public_reference, verification_contract, require_artifacts=False)
    _record_error(errors, not reference_failures, f"public reference validation failures: {reference_failures}")
    _record_error(errors, public_result.get("exit_code") == 0, "public_reference_validation_result.exit_code")

    safe_commands = public_manifest.get("repository_safe_commands", [])
    _record_error(errors, len(safe_commands) == 5, "public_test_manifest.repository_safe_commands_count")
    for command in safe_commands:
        expected_exit_code = int(command.get("expected_exit_code", 0))
        _record_error(errors, command.get("exit_code") == expected_exit_code, f"repository_safe_command_failed: {command.get('purpose')}")
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

    _record_error(errors, transaction_receipt.get("schema") == "CARE_ASE_FAITHFUL_TRANSACTION_GATE_RECEIPT_V1", "transaction_receipt.schema")
    _record_error(errors, transaction_receipt.get("review_round") == REVIEW_ROUND, "transaction_receipt.review_round")
    _record_error(errors, transaction_receipt.get("planner_review_commit") == PLANNER_REVIEW_COMMIT, "transaction_receipt.planner_review_commit")
    _record_error(errors, transaction_receipt.get("integration_sha") == REVIEWED_INTEGRATION_COMMIT, "transaction_receipt.integration_sha")
    _record_error(errors, transaction_receipt.get("implementation_fingerprint_sha256") == REVIEWED_IMPLEMENTATION_FINGERPRINT, "transaction_receipt.implementation_fingerprint")
    _record_error(
        errors,
        transaction_receipt.get("reviewed_verifier_fingerprint_sha256_at_repair_start") == REVIEWED_VERIFIER_FINGERPRINT,
        "transaction_receipt.reviewed_verifier_fingerprint",
    )
    _record_error(errors, len(str(transaction_receipt.get("verifier_source_fingerprint_sha256", ""))) == 64, "transaction_receipt.verifier_source_fingerprint")
    _record_error(errors, len(str(transaction_receipt.get("executable_verifier_receipt_sha256", ""))) == 64, "transaction_receipt.executable_receipt_sha")
    _record_error(errors, transaction_receipt.get("status") == "PASS", "transaction_receipt.expected_pass")
    _record_error(errors, int(transaction_receipt.get("failure_count", 1)) == 0, "transaction_receipt.failure_count")

    _record_error(errors, executable_receipt.get("schema") == "CARE_ASE_FAITHFUL_EXECUTABLE_VERIFIER_RECEIPT_V1", "executable_receipt.schema")
    _record_error(errors, executable_receipt.get("review_round") == REVIEW_ROUND, "executable_receipt.review_round")
    _record_error(errors, executable_receipt.get("fixture_mode") is False, "executable_receipt.production_not_fixture")
    expected_executable_passed = not CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED
    expected_executable_status = "FAIL_CLOSED" if CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED else "PASS"
    _record_error(errors, executable_receipt.get("passed") is expected_executable_passed, "executable_receipt.current_implementation_passed")
    _record_error(errors, executable_receipt.get("status") == expected_executable_status, "executable_receipt.current_implementation_status")
    _record_error(errors, executable_receipt.get("integration_sha") == REVIEWED_INTEGRATION_COMMIT, "executable_receipt.integration_sha")
    _record_error(
        errors,
        executable_receipt.get("implementation_fingerprint_sha256") == REVIEWED_IMPLEMENTATION_FINGERPRINT,
        "executable_receipt.implementation_fingerprint",
    )
    _record_error(errors, executable_receipt.get("formal_training_started") is False, "executable_receipt.no_training")
    _record_error(errors, executable_receipt.get("outer_accessed") is False, "executable_receipt.no_outer")
    _record_error(errors, executable_receipt.get("runtime_conclusion_source") == "verifier_owned_independent_execution", "executable_receipt.conclusion_source")
    _record_error(errors, executable_receipt.get("executor_receipts_used_as_runtime_conclusion") is False, "executable_receipt.no_receipt_replay")
    environment = executable_receipt.get("environment", {})
    _record_error(errors, isinstance(environment, dict) and environment.get("torch_available") is True, "executable_receipt.torch_available")
    _record_error(errors, isinstance(environment, dict) and environment.get("nnunetv2_available") is True, "executable_receipt.nnunetv2_available")
    _record_error(errors, local_fail_closed_receipt.get("schema") == "CARE_ASE_FAITHFUL_EXECUTABLE_VERIFIER_RECEIPT_V1", "local_fail_closed_receipt.schema")
    _record_error(errors, local_fail_closed_receipt.get("fixture_mode") is False, "local_fail_closed_receipt.not_fixture")
    _record_error(errors, local_fail_closed_receipt.get("status") == "FAIL_CLOSED", "local_fail_closed_receipt.status")
    _record_error(errors, local_fail_closed_receipt.get("passed") is False, "local_fail_closed_receipt.passed")
    _record_error(errors, local_fail_closed_receipt.get("formal_training_started") is False, "local_fail_closed_receipt.no_training")
    _record_error(errors, local_fail_closed_receipt.get("outer_accessed") is False, "local_fail_closed_receipt.no_outer")
    _record_error(errors, integrated_validation_result.get("schema") == "CARE_ASE_FAITHFUL_VALIDATION_RESULT_V1", "integrated_validation_result.schema")
    _record_error(errors, integrated_validation_result.get("passed") is expected_executable_passed, "integrated_validation_result.current_implementation_passed")
    validation_failure_count = int(integrated_validation_result.get("failure_count", 1))
    _record_error(
        errors,
        validation_failure_count == 0 if expected_executable_passed else validation_failure_count > 0,
        "integrated_validation_result.failure_count",
    )

    mutation_invocations = mutation_manifest.get("mutation_invocations", [])
    _record_error(errors, mutation_manifest.get("schema") == "CARE_ASE_FAITHFUL_RUNTIME_MUTATION_MANIFEST_V1", "mutation_manifest.schema")
    _record_error(errors, mutation_manifest.get("review_round") == REVIEW_ROUND, "mutation_manifest.review_round")
    _record_error(errors, mutation_manifest.get("all_returned_nonzero") is True, "mutation_manifest.all_returned_nonzero")
    _record_error(errors, [item.get("mutation_id") for item in mutation_invocations] == EXECUTABLE_MUTATION_IDS, "mutation_manifest.id_order")
    for item in mutation_invocations:
        report_path = ROOT / item.get("report_path", "")
        _record_error(errors, item.get("exit_code") != 0, f"mutation_exit_zero: {item.get('mutation_id')}")
        _record_error(errors, report_path.is_file(), f"missing_mutation_report: {item.get('mutation_id')}")
        if report_path.is_file():
            _record_error(errors, item.get("report_sha256") == sha256_file(report_path), f"mutation_report_sha_mismatch: {item.get('mutation_id')}")
            report = load_json(report_path)
            _record_error(errors, report.get("fixture_mode") is False, f"mutation_report_fixture: {item.get('mutation_id')}")
            _record_error(errors, report.get("mutation_executed") is True, f"mutation_report_not_executed: {item.get('mutation_id')}")
            _record_error(errors, isinstance(report.get("mutation_applied"), str) and report.get("mutation_applied"), f"mutation_report_no_applied: {item.get('mutation_id')}")
            _record_error(errors, len(str(report.get("mutated_fingerprint_sha256", ""))) == 64, f"mutation_report_no_fingerprint: {item.get('mutation_id')}")

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
    _record_error(
        errors,
        freeze_receipt.get("current_reviewed_implementation_expected_fail_closed") is CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED,
        "freeze_receipt.current_expected_pass",
    )
    _record_error(errors, freeze_receipt.get("controller_may_continue_after_verifier_recheck") is True, "freeze_receipt.controller_continue_gate")

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
            "public_reference_fixture_bypass_forbidden": True,
            "strict_artifact_binding_required_for_executor_evidence": True,
        },
        "strict_artifact_binding": {
            "required_receipt_paths": [
                "source_manifest",
                "static_architecture_checks",
                "architecture_signature",
                "parameter_owner_registry",
                "forward_backward_probe",
                "inference_probe",
                "checkpoint_resume_probe",
                "deployment_load_probe",
                "evaluator_smoke",
                "hard_negative_binding",
            ],
            "critical_source_topology_checks": [
                "distinct Conv1d/GroupNorm scar and edema SliceExtentHead modules",
                "no scar extent alias to scar proposal occupancy",
                "edema dilation residual blocks at dilations 1, 2 and 4",
                "injury classifier initialized from stock class-4/class-5 mean",
                "real-case total-loss, no-T2, resume, deployment, evaluator and hard-negative receipts",
            ],
        },
        "verifier_owned_execution_gate": {
            "entrypoint": str(EXECUTABLE_VERIFIER_PATH.relative_to(ROOT)),
            "production_receipt_path": "results/agent_flow_v3/care-ase-faithful/verification/executable_verifier_receipt.json",
            "runtime_mutation_manifest_path": "results/agent_flow_v3/care-ase-faithful/verification/runtime_mutation_manifest.json",
            "transaction_gate_receipt_path": "results/agent_flow_v3/care-ase-faithful/verification/transaction_gate_receipt.json",
            "fixture_mode_allowed_for_verifier_selftest_only": True,
            "fixture_mode_forbidden_for_implementation_acceptance": True,
            "must_execute_without_random_tensor_substitution": True,
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
        "--allow-public-reference-fixture",
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

    executable_command = [
        str(CARE_RUNTIME_PYTHON),
        str(EXECUTABLE_VERIFIER_PATH.relative_to(ROOT)),
        "--evidence",
        str(IMPLEMENTATION_EVIDENCE_PATH.relative_to(ROOT)),
        "--review-round",
        str(REVIEW_ROUND),
        "--integration-sha",
        REVIEWED_INTEGRATION_COMMIT,
        "--implementation-fingerprint",
        REVIEWED_IMPLEMENTATION_FINGERPRINT,
        "--verifier-fingerprint",
        REVIEWED_VERIFIER_FINGERPRINT,
        "--receipt",
        "results/agent_flow_v3/care-ase-faithful/verification/executable_verifier_receipt.json",
    ]
    executable_result = run_command(executable_command, env=runtime_env())
    executable_receipt = load_json(VERIFICATION_DIR / "executable_verifier_receipt.json")
    transaction_gate = executable_receipt.get("transaction_gate", {})
    transaction_failures = [failure for failure in executable_receipt.get("failures", []) if str(failure).startswith("transaction.")]
    source_fp = verifier_source_fingerprint()
    transaction_receipt = {
        "schema": "CARE_ASE_FAITHFUL_TRANSACTION_GATE_RECEIPT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "review_round": REVIEW_ROUND,
        "planner_review_commit": PLANNER_REVIEW_COMMIT,
        "integration_sha": REVIEWED_INTEGRATION_COMMIT,
        "implementation_fingerprint_sha256": REVIEWED_IMPLEMENTATION_FINGERPRINT,
        "reviewed_verifier_fingerprint_sha256_at_repair_start": REVIEWED_VERIFIER_FINGERPRINT,
        "verifier_source_fingerprint_sha256": source_fp["verifier_source_fingerprint_sha256"],
        "verifier_source_artifacts": source_fp,
        "executable_verifier_receipt_sha256": sha256_file(VERIFICATION_DIR / "executable_verifier_receipt.json"),
        "planner_packet_sha": REVIEWED_INTEGRATION_COMMIT,
        "ci_checked_commit_sha": transaction_gate.get("hosted_ci_checked_commit_sha"),
        "current_state_sha": head,
        "runtime_manifest_sha": transaction_gate.get("runtime_manifest_sha256"),
        "hosted_ci_conclusion": transaction_gate.get("hosted_ci_conclusion"),
        "hosted_ci_head_sha": transaction_gate.get("hosted_ci_head_sha"),
        "stale_planner_reused_after_key_commit": bool(transaction_failures),
        "status": "PASS" if not transaction_failures else "FAIL_CLOSED",
        "failure_count": len(transaction_failures),
        "failures": transaction_failures,
        "transaction_gate": transaction_gate,
        "created_utc": now,
    }
    transaction_receipt["transaction_fingerprint_sha256"] = sha256_bytes(
        json.dumps(transaction_receipt, sort_keys=True, default=str).encode("utf-8")
    )
    write_json(VERIFICATION_DIR / "transaction_gate_receipt.json", transaction_receipt)
    local_fail_closed_command = [
        str(CARE_RUNTIME_PYTHON),
        str(EXECUTABLE_VERIFIER_PATH.relative_to(ROOT)),
        "--review-round",
        str(REVIEW_ROUND),
        "--integration-sha",
        REVIEWED_INTEGRATION_COMMIT,
        "--implementation-fingerprint",
        REVIEWED_IMPLEMENTATION_FINGERPRINT,
        "--verifier-fingerprint",
        REVIEWED_VERIFIER_FINGERPRINT,
        "--receipt",
        "results/agent_flow_v3/care-ase-faithful/verification/executable_verifier_local_fail_closed_receipt.json",
    ]
    local_fail_closed_result = run_command(local_fail_closed_command, env=runtime_env())
    integrated_report_path = VERIFICATION_DIR / "integrated_implementation_validation_result.json"
    integrated_validation_command = [
        sys.executable,
        str(VALIDATOR_PATH.relative_to(ROOT)),
        "--verification-contract",
        str((VERIFICATION_DIR / "verification_contract.json").relative_to(ROOT)),
        "--evidence",
        str(IMPLEMENTATION_EVIDENCE_PATH.relative_to(ROOT)),
        "--report-json",
        str(integrated_report_path.relative_to(ROOT)),
    ]
    integrated_validation_result = run_command(integrated_validation_command)

    mutation_results = []
    mutation_dir = VERIFICATION_DIR / "runtime_mutation_reports"
    for mutation_id in EXECUTABLE_MUTATION_IDS:
        report_path = mutation_dir / f"{mutation_id}.json"
        command = [
            str(CARE_RUNTIME_PYTHON),
            str(EXECUTABLE_VERIFIER_PATH.relative_to(ROOT)),
            "--mutation-id",
            mutation_id,
        ]
        result = run_command_with_output(command, env=runtime_env())
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(result["stdout"], encoding="utf-8")
        mutation_results.append(
            {
                "mutation_id": mutation_id,
                "command": command,
                "command_sha256": sha256_bytes(json.dumps(command, sort_keys=True).encode("utf-8")),
                "exit_code": result["exit_code"],
                "stdout_sha256": result["stdout_sha256"],
                "stderr_sha256": result["stderr_sha256"],
                "report_path": str(report_path.relative_to(ROOT)),
                "report_sha256": sha256_file(report_path),
                "passed_fail_closed": result["exit_code"] != 0,
            }
        )
    mutation_manifest = {
        "schema": "CARE_ASE_FAITHFUL_RUNTIME_MUTATION_MANIFEST_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "review_round": REVIEW_ROUND,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "count": len(mutation_results),
        "all_returned_nonzero": all(item["passed_fail_closed"] for item in mutation_results),
        "mutation_invocations": mutation_results,
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "runtime_mutation_manifest.json", mutation_manifest)
    integrated_validation_result = run_command(integrated_validation_command)

    unittest_result = run_command([sys.executable, "-m", "unittest", "tests.care_ase_faithful.test_verifier_package"])
    v3_validator_result = run_command([sys.executable, "scripts/automation/validate_agent_flow_v3.py", "--repo-root", "."])
    public_manifest["repository_safe_commands"] = [
        {
            "purpose": "public reference evidence validates under the frozen contract",
            "expected_exit_code": 0,
            **public_result,
        },
        {
            "purpose": "verifier unittest package exercises public reference and all protected known-bad categories",
            "expected_exit_code": 0,
            **unittest_result,
        },
        {
            "purpose": "Agent-Flow v3 request/current deterministic state validation",
            "expected_exit_code": 0,
            **v3_validator_result,
        },
        {
            "purpose": "verifier-owned executable receipt independently evaluates the current integrated implementation and fails closed for reentry3 causal-authority shortcuts",
            "expected_exit_code": 2 if CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED else 0,
            **executable_result,
        },
        {
            "purpose": "frozen validator evaluates integrated implementation evidence and fails closed with current verifier-owned runtime receipts",
            "expected_exit_code": 2 if CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED else 0,
            **integrated_validation_result,
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
        "runtime_mutation_invocations": mutation_results,
        "local_fail_closed_executable_probe": {
            "purpose": "verifier-owned real-mode executable probe can run independently without using Executor receipts as its conclusion",
            **local_fail_closed_result,
        },
        "integrated_implementation_validation": {
            "purpose": "frozen validator rejects current implementation evidence using executable verifier receipt",
            **integrated_validation_result,
            "report_path": str(integrated_report_path.relative_to(ROOT)),
            "report_sha256": sha256_file(integrated_report_path) if integrated_report_path.exists() else None,
        },
    }
    write_json(VERIFICATION_DIR / "verifier_local_commands_recorded_in_manifests.json", command_log)

    session_receipt = {
        "schema": "CARE_AGENT_FLOW_V3_ROLE_RECEIPT",
        "role": "verifier",
        "thread_id": active_verifier_thread_id(),
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
    source_fp = verifier_source_fingerprint()
    fingerprint = {
        "schema": "CARE_ASE_FAITHFUL_VERIFIER_FINGERPRINT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "fingerprint_sha256": digest,
        "verifier_source_fingerprint_sha256": source_fp["verifier_source_fingerprint_sha256"],
        "verifier_source_file_hashes": source_fp["file_hashes"],
        "transaction_fingerprint_sha256": load_json(VERIFICATION_DIR / "transaction_gate_receipt.json").get("transaction_fingerprint_sha256"),
        "executable_verifier_receipt_sha256": sha256_file(VERIFICATION_DIR / "executable_verifier_receipt.json"),
        "integrated_implementation_fingerprint_sha256": REVIEWED_IMPLEMENTATION_FINGERPRINT,
        "reviewed_integration_sha": REVIEWED_INTEGRATION_COMMIT,
        "file_hashes": file_hashes,
        "protected_known_bad_count": len(protected_results),
        "protected_known_bad_all_nonzero": all(item["passed_fail_closed"] for item in protected_results),
        "runtime_mutation_count": len(mutation_results),
        "runtime_mutation_all_nonzero": all(item["passed_fail_closed"] for item in mutation_results),
        "executable_verifier_production_exit_code": executable_result["exit_code"],
        "integrated_implementation_validation_exit_code": integrated_validation_result["exit_code"],
        "current_reviewed_implementation_expected_fail_closed": CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED,
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
        "runtime_mutation_manifest": str((VERIFICATION_DIR / "runtime_mutation_manifest.json").relative_to(ROOT)),
        "runtime_mutation_count": len(mutation_results),
        "runtime_mutation_all_nonzero": all(item["passed_fail_closed"] for item in mutation_results),
        "executable_verifier_receipt": str((VERIFICATION_DIR / "executable_verifier_receipt.json").relative_to(ROOT)),
        "executable_verifier_production_exit_code": executable_result["exit_code"],
        "integrated_implementation_validation_result": str((VERIFICATION_DIR / "integrated_implementation_validation_result.json").relative_to(ROOT)),
        "integrated_implementation_validation_exit_code": integrated_validation_result["exit_code"],
        "current_reviewed_implementation_expected_fail_closed": CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED,
        "executable_verifier_local_fail_closed_receipt": str((VERIFICATION_DIR / "executable_verifier_local_fail_closed_receipt.json").relative_to(ROOT)),
        "executable_verifier_local_fail_closed_exit_code": local_fail_closed_result["exit_code"],
        "controller_may_continue_after_verifier_recheck": True,
        "created_utc": now,
    }
    write_json(VERIFICATION_DIR / "verifier_freeze_receipt.json", freeze_receipt)
    return (
        0
        if public_result["exit_code"] == 0
        and unittest_result["exit_code"] == 0
        and v3_validator_result["exit_code"] == 0
        and executable_result["exit_code"] == (2 if CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED else 0)
        and integrated_validation_result["exit_code"] == (2 if CURRENT_REVIEWED_IMPLEMENTATION_EXPECTED_FAIL_CLOSED else 0)
        and local_fail_closed_result["exit_code"] == 2
        and all(item["passed_fail_closed"] for item in protected_results)
        and all(item["passed_fail_closed"] for item in mutation_results)
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
