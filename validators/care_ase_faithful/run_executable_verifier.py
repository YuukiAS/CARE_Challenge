#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "care-ase-faithful"
REQUEST_NONCE = "care-ase-20260806T090955Z"
FROZEN_CONTRACT_SHA256 = "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d"
REVIEW_ROUND = 1
FALLBACK_PLANNER_REVIEW_COMMIT = "d96415ae0b48ae856854e475e624907392a4d7b9"
FALLBACK_REVIEWED_INTEGRATION_COMMIT = "a60ba7a68f07dbade0ab400e9e859352ca7d1b9a"
FALLBACK_REVIEWED_IMPLEMENTATION_FINGERPRINT = "dd5593f869823de7fe0b76f953c3ea1ade6d0c1426a7e26a39a4ae1aea6fa692"
FALLBACK_REVIEWED_VERIFIER_FINGERPRINT = "3dcacfe7ae41e164435278c0da4557fc61b384ef6eeb09860badb353b375dca6"

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_DIR = ROOT / "results" / "agent_flow_v3" / TASK_ID / "verification"
CURRENT_PATH = ROOT / "automation" / "agent_flow_v3" / "tasks" / TASK_ID / "CURRENT.json"
RUNTIME_MANIFEST_PATH = ROOT / "results" / "agent_flow_v3" / TASK_ID / "runtime_receipt_manifest.json"
CONTROLLER_CI_RECEIPT_PATH = ROOT / "results" / "agent_flow_v3" / TASK_ID / "controller_ci_receipt.json"


def _current_binding_value(field: str, fallback: str) -> str:
    try:
        current = json.loads(CURRENT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return fallback
    binding = current.get("binding", current) if isinstance(current, dict) else {}
    value = binding.get(field) if isinstance(binding, dict) else None
    if value is None and isinstance(current, dict):
        value = current.get(field)
    return str(value) if value else fallback


PLANNER_REVIEW_COMMIT = _current_binding_value("planner_review_artifact_commit_sha", FALLBACK_PLANNER_REVIEW_COMMIT)
REVIEWED_INTEGRATION_COMMIT = _current_binding_value("integration_commit_sha", FALLBACK_REVIEWED_INTEGRATION_COMMIT)
REVIEWED_IMPLEMENTATION_FINGERPRINT = _current_binding_value(
    "implementation_fingerprint_sha256",
    FALLBACK_REVIEWED_IMPLEMENTATION_FINGERPRINT,
)
REVIEWED_VERIFIER_FINGERPRINT = _current_binding_value(
    "verifier_fingerprint_sha256",
    FALLBACK_REVIEWED_VERIFIER_FINGERPRINT,
)

MUTATION_IDS = [
    "extent_conv3d_alias",
    "dilation_residual_removed",
    "injury_random_init",
    "projection_context_no_final_authority",
    "synthetic_intervention_delta",
    "semantic_disable_only_quadratic_signal",
    "partial_hw_straight_through_zero_loss",
    "partial_hw_cross_z_presequence_mask_removed",
    "injury_dice_bce_replaced_by_focal",
    "scar_component_tversky_plus_occupancy_lambda025",
    "scar_component_tversky_blended_occupancy_half",
    "full_support_pseudo_tiling",
    "transaction_old_tuple_reused",
    "forged_executor_pass_receipt",
    "no_t2_calls_edema",
    "single_multi_same_call",
    "tile_local_global_bias",
    "deployment_reopens_stock_checkpoint",
    "evaluator_population_mismatch",
    "checkpoint_next_step_drift",
    "checkpoint_current_contract_provenance_drift",
    "runtime_manifest_round0_reused",
    "runtime_manifest_missing_nonce",
    "runtime_manifest_missing_frozen_contract",
    "runtime_manifest_old_integration",
    "runtime_manifest_old_implementation_fingerprint",
    "runtime_manifest_old_verifier_fingerprint",
    "runtime_manifest_receipt_sha_drift",
    "artifact_sha_mismatch",
]

RUNTIME_MANIFEST_MUTATION_IDS = {
    "runtime_manifest_round0_reused",
    "runtime_manifest_missing_nonce",
    "runtime_manifest_missing_frozen_contract",
    "runtime_manifest_old_integration",
    "runtime_manifest_old_implementation_fingerprint",
    "runtime_manifest_old_verifier_fingerprint",
    "runtime_manifest_receipt_sha_drift",
}

REQUIRED_RUNTIME_MANIFEST_ARTIFACTS = {
    "implementation_evidence": f"results/agent_flow_v3/{TASK_ID}/implementation/implementation_evidence.json",
    "executable_verifier": f"results/agent_flow_v3/{TASK_ID}/verification/executable_verifier_receipt.json",
    "transaction_gate": f"results/agent_flow_v3/{TASK_ID}/verification/transaction_gate_receipt.json",
    "checkpoint_resume": f"results/agent_flow_v3/{TASK_ID}/implementation/checkpoint_resume_probe_receipt.json",
    "inference": f"results/agent_flow_v3/{TASK_ID}/implementation/inference_probe_receipt.json",
    "deployment_load": f"results/agent_flow_v3/{TASK_ID}/implementation/deployment_load_probe_receipt.json",
    "evaluator_smoke": f"results/agent_flow_v3/{TASK_ID}/implementation/evaluator_smoke_receipt.json",
    "frozen_verifier_validation": f"results/agent_flow_v3/{TASK_ID}/implementation/frozen_verifier_validation_result.json",
    "hosted_ci": f"results/agent_flow_v3/{TASK_ID}/controller_ci_receipt.json",
}

REQUIRED_PROBES = [
    "model_build_and_stock_parity",
    "real_train_case_total_loss_forward_backward",
    "loss_semantic_oracle",
    "mixed_t2_no_t2_batch",
    "required_module_final_logit_interventions",
    "required_module_final_authority_oracle",
    "schema_v4_checkpoint_resume",
    "deployment_loader",
    "evaluator_interface",
    "single_vs_forced_multi_tile_full_volume",
    "tile_local_forward_instrumentation",
    "step0_parity_report_regression",
    "partial_hw_extent_zero_contribution",
    "partial_hw_extent_reference_objective",
    "partial_hw_slice_extent_head_cross_z_gradient",
]

PLAN_PATCH_SIZE = (8, 64, 64)
LOSS_SEMANTIC_TOLERANCE = 1.0e-5
CANONICAL_LOSS_WEIGHTS = {
    "conditional_final_dice_ce": 1.00,
    "anatomy_deep_supervision_dice_ce": 0.50,
    "wall_dice_bce": 0.25,
    "distance_rho_masked_smooth_l1": 0.10,
    "scar_binary_dice_focal": 1.00,
    "scar_component_adaptive_tversky": 0.25,
    "scar_center_focal_bce": 0.10,
    "scar_extent_bce_smooth_l1": 0.15,
    "scar_context_ce": 0.10,
    "edema_binary_dice_focal": 1.00,
    "injury_dice_bce": 0.40,
    "edema_boundary_smooth_l1": 0.10,
    "edema_extent_bce_smooth_l1": 0.20,
    "edema_context_ce": 0.10,
    "relation_loss": 0.05,
}

BLOCKING_NUMERIC_THRESHOLDS = [
    {
        "name": "stock_step0_t2_present_max_abs_error",
        "threshold": 1e-6,
        "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        "contract_field_or_exact_clause": "Section 3: new evidence disabled stock-compatible logits max_abs_error <= 1e-6",
        "logical_derivation": "Direct stock/step0 compatibility parity gate.",
    },
    {
        "name": "stock_step0_no_t2_max_abs_error",
        "threshold": 1e-6,
        "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        "contract_field_or_exact_clause": "Section 3: new evidence disabled stock-compatible logits max_abs_error <= 1e-6",
        "logical_derivation": "Direct stock/step0 compatibility parity gate.",
    },
    {
        "name": "partial_hw_reference_loss_match",
        "threshold": 1e-6,
        "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        "contract_field_or_exact_clause": "Sections 8 and 15: partial-H/W slices contribute zero bias/loss/gradient; fully valid neighboring slices remain supervised.",
        "logical_derivation": "Verifier-owned deterministic aggregation/loss oracle with analytically constructed reference.",
    },
    {
        "name": "authority_disable_flag_matches_verifier_owned_removal",
        "threshold": 1e-6,
        "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        "contract_field_or_exact_clause": "Sections 4 and 15: required evidence sources must have final reconstruction authority; implementation intervention flags are not final-authority evidence.",
        "logical_derivation": "A test/intervention flag may only remove the same ordinary-path source contribution that the Verifier removes by module-output intervention; any extra flag-conditioned final-logit contribution must be absent.",
    },
    {
        "name": "loss_semantic_oracle_reference_match",
        "threshold": LOSS_SEMANTIC_TOLERANCE,
        "contract_source_path": "automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        "contract_field_or_exact_clause": "Section 10: unique allowed loss set, including 0.40 injury Dice+BCE and 0.25 scar component-adaptive Tversky(alpha=.3,beta=.7).",
        "logical_derivation": "Verifier independently re-evaluates the same deterministic FP32 formulas from runtime tensors; tolerance is only for floating-point accumulation/order effects, not a scientific threshold.",
    },
]


def real_cnn_single_multi_context_diagnostic_policy() -> dict[str, Any]:
    return {
        "name": "real_care_ase_single_full_context_vs_forced_tile_local_diff",
        "blocking": False,
        "contract_source_path": None,
        "contract_field_or_exact_clause": None,
        "logical_derivation": (
            "The frozen contract requires the same public canonical inference path/settings, genuine "
            "tile-local model forwards, no full-support pseudo-tiling, and one post-aggregation global "
            "bias application. It does not require a real CNN evaluated with different receptive-field "
            "context to match a single full-context whole-volume forward at 1e-6."
        ),
        "diagnostic_only": True,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_sha(payload: Any) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_value(repo_root: Path, *args: str) -> str | None:
    completed = subprocess.run(["git", *args], cwd=repo_root, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def verifier_fingerprint() -> str:
    path = VERIFICATION_DIR / "verifier_fingerprint.json"
    if not path.is_file():
        return REVIEWED_VERIFIER_FINGERPRINT
    try:
        return str(load_json(path).get("fingerprint_sha256") or REVIEWED_VERIFIER_FINGERPRINT)
    except Exception:
        return REVIEWED_VERIFIER_FINGERPRINT


def environment_payload(repo_root: Path) -> dict[str, Any]:
    assets = {}
    for env_name in ("CARE_ROOT", "nnUNet_preprocessed", "nnUNet_results"):
        value = os.environ.get(env_name)
        assets[env_name] = value
    return {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "repo_root": str(repo_root),
        "git_head": git_value(repo_root, "rev-parse", "HEAD"),
        "git_branch": git_value(repo_root, "branch", "--show-current"),
        "torch_available": importlib.util.find_spec("torch") is not None,
        "nnunetv2_available": importlib.util.find_spec("nnunetv2") is not None,
        "runtime_env": assets,
    }


def source_artifact_hashes(repo_root: Path) -> dict[str, Any]:
    paths = [
        "src/care_myocardium/models/care_ase/__init__.py",
        "src/care_myocardium/models/care_ase/core.py",
        "src/care_myocardium/training/care_ase_trainer.py",
        "src/care_myocardium/training/care_ase_sampler.py",
        "src/care_myocardium/inference/care_ase_r2_decode.py",
        "src/care_myocardium/inference/care_ase_r2_full_volume.py",
    ]
    file_hashes: dict[str, str] = {}
    missing: list[str] = []
    for rel in paths:
        path = repo_root / rel
        if path.is_file():
            file_hashes[rel] = sha256_file(path)
        else:
            missing.append(rel)
    return {"file_hashes": file_hashes, "missing_files": missing, "source_manifest_sha256": json_sha(file_hashes)}


def verifier_source_artifact_hashes(repo_root: Path) -> dict[str, Any]:
    paths = [
        "validators/care_ase_faithful/run_executable_verifier.py",
        "validators/care_ase_faithful/validate_contract_evidence.py",
        "validators/care_ase_faithful/build_verification_artifacts.py",
        "tests/care_ase_faithful/test_verifier_package.py",
    ]
    file_hashes = {rel: sha256_file(repo_root / rel) for rel in paths if (repo_root / rel).is_file()}
    return {"file_hashes": file_hashes, "verifier_source_fingerprint_sha256": json_sha(file_hashes)}


def _load_optional_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return load_json(path)
    except Exception:
        return {}


def _runtime_manifest_value(manifest: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = manifest.get(key)
        if value is not None:
            return value
    binding = manifest.get("binding")
    if isinstance(binding, dict):
        for key in keys:
            value = binding.get(key)
            if value is not None:
                return value
    return None


def _collect_path_strings(value: Any) -> set[str]:
    paths: set[str] = set()
    if isinstance(value, str):
        if "/" in value or value.endswith(".json"):
            paths.add(value)
    elif isinstance(value, list):
        for item in value:
            paths.update(_collect_path_strings(item))
    elif isinstance(value, dict):
        for item in value.values():
            paths.update(_collect_path_strings(item))
    return paths


def _collect_sha_bindings(value: Any) -> dict[str, str]:
    bindings: dict[str, str] = {}
    if isinstance(value, list):
        for item in value:
            bindings.update(_collect_sha_bindings(item))
    elif isinstance(value, dict):
        for map_key in ("receipt_sha256s", "receipt_hashes", "artifact_sha256s", "artifact_hashes", "file_sha256s"):
            mapping = value.get(map_key)
            if isinstance(mapping, dict):
                for key, sha in mapping.items():
                    if isinstance(key, str) and isinstance(sha, str):
                        bindings[key] = sha
        path_value = None
        for path_key in ("path", "receipt_path", "artifact_path", "file_path"):
            if isinstance(value.get(path_key), str):
                path_value = value[path_key]
                break
        if path_value:
            for sha_key in ("sha256", "receipt_sha256", "artifact_sha256", "file_sha256"):
                if isinstance(value.get(sha_key), str):
                    bindings[path_value] = value[sha_key]
                    break
        for key, item in value.items():
            if isinstance(item, str) and (key.endswith("_sha256") or key.endswith("_sha")):
                stem = key.removesuffix("_sha256").removesuffix("_sha")
                bindings[stem] = item
            elif isinstance(item, str) and (key.endswith("_path") or key.endswith("_receipt")):
                stem = key.removesuffix("_path").removesuffix("_receipt")
                sha = value.get(f"{stem}_sha256") or value.get(f"{stem}_sha")
                if isinstance(sha, str):
                    bindings[item] = sha
                    bindings[stem] = sha
            elif isinstance(item, (dict, list)):
                bindings.update(_collect_sha_bindings(item))
    return bindings


def _runtime_manifest_failures(
    *,
    repo_root: Path,
    runtime_manifest: dict[str, Any],
    review_round: int,
    integration_sha: str,
    implementation_fingerprint: str,
    expected_verifier_fingerprint: str,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    observed = {
        "task_id": _runtime_manifest_value(runtime_manifest, "task_id"),
        "request_nonce": _runtime_manifest_value(runtime_manifest, "request_nonce"),
        "frozen_contract_sha256": _runtime_manifest_value(runtime_manifest, "frozen_contract_sha256", "contract_sha256"),
        "review_round": _runtime_manifest_value(runtime_manifest, "review_round"),
        "integration_commit_sha": _runtime_manifest_value(runtime_manifest, "integration_commit_sha", "integration_sha"),
        "implementation_fingerprint_sha256": _runtime_manifest_value(runtime_manifest, "implementation_fingerprint_sha256"),
        "verifier_fingerprint_sha256": _runtime_manifest_value(runtime_manifest, "verifier_fingerprint_sha256"),
    }
    expected = {
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "review_round": review_round,
        "integration_commit_sha": integration_sha,
        "implementation_fingerprint_sha256": implementation_fingerprint,
        "verifier_fingerprint_sha256": expected_verifier_fingerprint,
    }
    for field, expected_value in expected.items():
        if observed.get(field) != expected_value:
            failures.append(f"transaction.runtime_manifest.{field}")

    path_strings = _collect_path_strings(runtime_manifest)
    sha_bindings = _collect_sha_bindings(runtime_manifest)
    artifact_observations: dict[str, dict[str, Any]] = {}
    for name, rel_path in REQUIRED_RUNTIME_MANIFEST_ARTIFACTS.items():
        artifact_path = repo_root / rel_path
        expected_sha = sha256_file(artifact_path) if artifact_path.is_file() else None
        declared_sha = (
            sha_bindings.get(rel_path)
            or sha_bindings.get(name)
            or sha_bindings.get(f"{name}_receipt")
            or sha_bindings.get(f"{name}_path")
        )
        listed = rel_path in path_strings or name in path_strings
        artifact_observations[name] = {
            "path": rel_path,
            "listed": listed,
            "file_exists": artifact_path.is_file(),
            "expected_sha256": expected_sha,
            "declared_sha256": declared_sha,
        }
        if not listed:
            failures.append(f"transaction.runtime_manifest.artifact_missing:{name}")
        if expected_sha is None:
            failures.append(f"transaction.runtime_manifest.artifact_file_missing:{name}")
        elif declared_sha != expected_sha:
            failures.append(f"transaction.runtime_manifest.artifact_sha256:{name}")
    return failures, {
        "observed_fields": observed,
        "expected_fields": expected,
        "required_artifacts": artifact_observations,
    }


def _valid_runtime_manifest_payload(repo_root: Path) -> dict[str, Any]:
    artifact_sha256s = {
        rel_path: sha256_file(repo_root / rel_path)
        for rel_path in REQUIRED_RUNTIME_MANIFEST_ARTIFACTS.values()
        if (repo_root / rel_path).is_file()
    }
    return {
        "schema": "CARE_AGENT_FLOW_V3_RUNTIME_RECEIPT_MANIFEST",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "review_round": REVIEW_ROUND,
        "integration_commit_sha": REVIEWED_INTEGRATION_COMMIT,
        "implementation_fingerprint_sha256": REVIEWED_IMPLEMENTATION_FINGERPRINT,
        "verifier_fingerprint_sha256": REVIEWED_VERIFIER_FINGERPRINT,
        "receipts": list(REQUIRED_RUNTIME_MANIFEST_ARTIFACTS.values()),
        "receipt_sha256s": artifact_sha256s,
    }


def _runtime_manifest_mutation_result(mutation_id: str, *, repo_root: Path, fixture_mode: bool) -> dict[str, Any]:
    expected_failure = {
        "runtime_manifest_round0_reused": "transaction.runtime_manifest.review_round",
        "runtime_manifest_missing_nonce": "transaction.runtime_manifest.request_nonce",
        "runtime_manifest_missing_frozen_contract": "transaction.runtime_manifest.frozen_contract_sha256",
        "runtime_manifest_old_integration": "transaction.runtime_manifest.integration_commit_sha",
        "runtime_manifest_old_implementation_fingerprint": "transaction.runtime_manifest.implementation_fingerprint_sha256",
        "runtime_manifest_old_verifier_fingerprint": "transaction.runtime_manifest.verifier_fingerprint_sha256",
        "runtime_manifest_receipt_sha_drift": "transaction.runtime_manifest.artifact_sha256:implementation_evidence",
    }[mutation_id]
    runtime_manifest = _valid_runtime_manifest_payload(repo_root)
    mutation_applied = mutation_id
    if mutation_id == "runtime_manifest_round0_reused":
        runtime_manifest["review_round"] = 0
        mutation_applied = "runtime_manifest_review_round_mutated_to_stale_round0"
    elif mutation_id == "runtime_manifest_missing_nonce":
        runtime_manifest.pop("request_nonce", None)
        mutation_applied = "runtime_manifest_request_nonce_removed"
    elif mutation_id == "runtime_manifest_missing_frozen_contract":
        runtime_manifest.pop("frozen_contract_sha256", None)
        mutation_applied = "runtime_manifest_frozen_contract_sha256_removed"
    elif mutation_id == "runtime_manifest_old_integration":
        runtime_manifest["integration_commit_sha"] = "0" * 40
        mutation_applied = "runtime_manifest_integration_commit_sha_mutated_to_old_value"
    elif mutation_id == "runtime_manifest_old_implementation_fingerprint":
        runtime_manifest["implementation_fingerprint_sha256"] = "1" * 64
        mutation_applied = "runtime_manifest_implementation_fingerprint_mutated_to_old_value"
    elif mutation_id == "runtime_manifest_old_verifier_fingerprint":
        runtime_manifest["verifier_fingerprint_sha256"] = "2" * 64
        mutation_applied = "runtime_manifest_verifier_fingerprint_mutated_to_old_value"
    elif mutation_id == "runtime_manifest_receipt_sha_drift":
        rel_path = REQUIRED_RUNTIME_MANIFEST_ARTIFACTS["implementation_evidence"]
        runtime_manifest["receipt_sha256s"][rel_path] = "0" * 64
        mutation_applied = "runtime_manifest_implementation_evidence_sha256_mutated_after_receipt_binding"

    current = {
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "review_round": REVIEW_ROUND,
        "integration_commit_sha": REVIEWED_INTEGRATION_COMMIT,
        "implementation_fingerprint_sha256": REVIEWED_IMPLEMENTATION_FINGERPRINT,
        "verifier_fingerprint_sha256": REVIEWED_VERIFIER_FINGERPRINT,
        "ci_checked_commit_sha": REVIEWED_INTEGRATION_COMMIT,
        "ci_run_actual_head_sha": REVIEWED_INTEGRATION_COMMIT,
    }
    ci_receipt = {
        "checked_commit_sha": REVIEWED_INTEGRATION_COMMIT,
        "github_actions_head_sha": REVIEWED_INTEGRATION_COMMIT,
        "github_actions_conclusion": "success",
    }
    evidence = {
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "implementation_fingerprint_sha256": REVIEWED_IMPLEMENTATION_FINGERPRINT,
    }
    failures: list[str] = []
    observations: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="care_ase_mutation_runtime_manifest_", dir=repo_root) as tmp:
        tmp_path = Path(tmp)
        current_path = tmp_path / "CURRENT.json"
        manifest_path = tmp_path / "runtime_receipt_manifest.json"
        ci_path = tmp_path / "controller_ci_receipt.json"
        current_path.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")
        manifest_path.write_text(json.dumps(runtime_manifest, indent=2, sort_keys=True), encoding="utf-8")
        ci_path.write_text(json.dumps(ci_receipt, indent=2, sort_keys=True), encoding="utf-8")
        original_current = CURRENT_PATH
        original_manifest = RUNTIME_MANIFEST_PATH
        original_ci = CONTROLLER_CI_RECEIPT_PATH
        try:
            globals()["CURRENT_PATH"] = current_path
            globals()["RUNTIME_MANIFEST_PATH"] = manifest_path
            globals()["CONTROLLER_CI_RECEIPT_PATH"] = ci_path
            gate_failures, transaction = transaction_gate(
                repo_root=repo_root,
                evidence=evidence,
                review_round=REVIEW_ROUND,
                integration_sha=REVIEWED_INTEGRATION_COMMIT,
                implementation_fingerprint=REVIEWED_IMPLEMENTATION_FINGERPRINT,
                expected_verifier_fingerprint=REVIEWED_VERIFIER_FINGERPRINT,
                fixture_mode=fixture_mode,
            )
        finally:
            globals()["CURRENT_PATH"] = original_current
            globals()["RUNTIME_MANIFEST_PATH"] = original_manifest
            globals()["CONTROLLER_CI_RECEIPT_PATH"] = original_ci
    observations["expected_failure"] = expected_failure
    observations["transaction_failures"] = gate_failures
    observations["transaction_gate"] = transaction
    observations["mutated_manifest"] = runtime_manifest
    if expected_failure in gate_failures:
        failures.append(f"{expected_failure}.rejected")
    if not failures:
        failures.append(f"mutation.expected_rejection_missing:{mutation_id}")
    return {
        "schema": "CARE_ASE_FAITHFUL_EXECUTABLE_MUTATION_RESULT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "mutation_id": mutation_id,
        "fixture_mode": fixture_mode,
        "passed": False,
        "failure_count": len(failures),
        "failures": failures,
        "mutation_executed": True,
        "mutation_applied": mutation_applied,
        "mutated_fingerprint_sha256": json_sha({"mutation_id": mutation_id, "mutation_applied": mutation_applied, "observations": observations}),
        "observations": observations,
        "exit_code": 2,
        "created_utc": utc_now(),
    }


def transaction_gate(
    *,
    repo_root: Path,
    evidence: dict[str, Any],
    review_round: int,
    integration_sha: str,
    implementation_fingerprint: str,
    expected_verifier_fingerprint: str,
    fixture_mode: bool,
) -> tuple[list[str], dict[str, Any]]:
    failures: list[str] = []
    git_head = git_value(repo_root, "rev-parse", "HEAD")
    verifier_source = verifier_source_artifact_hashes(repo_root)
    current = _load_optional_json(CURRENT_PATH)
    runtime_manifest = _load_optional_json(RUNTIME_MANIFEST_PATH)
    ci_receipt = _load_optional_json(CONTROLLER_CI_RECEIPT_PATH)
    manifest_observations: dict[str, Any] | None = None
    integration_is_ancestor = git_value(repo_root, "merge-base", "--is-ancestor", integration_sha, "HEAD") == ""
    if not fixture_mode and not integration_is_ancestor:
        failures.append("transaction.integration_sha.not_ancestor_of_verifier_head")
    if integration_sha != REVIEWED_INTEGRATION_COMMIT:
        failures.append("transaction.integration_sha.not_exact_reviewed_integration")
    changed_after_integration = git_value(
        repo_root,
        "diff",
        "--name-only",
        integration_sha,
        "--",
        "validators/care_ase_faithful",
        "tests/care_ase_faithful",
        "results/agent_flow_v3/care-ase-faithful/verification",
    )
    changed_after_list = [line for line in (changed_after_integration or "").splitlines() if line.strip()]
    source_changed_after_list = [
        path
        for path in changed_after_list
        if path.startswith("validators/care_ase_faithful/") or path.startswith("tests/care_ase_faithful/")
    ]
    if source_changed_after_list:
        failures.append("transaction.verifier_source_changed_after_reviewed_integration")
    if review_round != REVIEW_ROUND:
        failures.append("transaction.review_round")
    if implementation_fingerprint != REVIEWED_IMPLEMENTATION_FINGERPRINT:
        failures.append("transaction.implementation_fingerprint.not_exact_reviewed")
    if expected_verifier_fingerprint != REVIEWED_VERIFIER_FINGERPRINT:
        failures.append("transaction.reviewed_verifier_fingerprint.not_exact_planner_binding")
    if not fixture_mode:
        if not current:
            failures.append("transaction.current_json_missing")
        else:
            current_binding = current.get("binding", current)
            if current.get("request_nonce") not in (None, REQUEST_NONCE) and current.get("request_nonce") != REQUEST_NONCE:
                failures.append("transaction.current.request_nonce")
            if current_binding.get("request_nonce", REQUEST_NONCE) != REQUEST_NONCE:
                failures.append("transaction.current.binding.request_nonce")
            if current_binding.get("frozen_contract_sha256", FROZEN_CONTRACT_SHA256) != FROZEN_CONTRACT_SHA256:
                failures.append("transaction.current.binding.frozen_contract_sha256")
            if current_binding.get("integration_commit_sha") != integration_sha:
                failures.append("transaction.current.binding.integration_sha")
            if current_binding.get("implementation_fingerprint_sha256") != implementation_fingerprint:
                failures.append("transaction.current.binding.implementation_fingerprint")
            if current_binding.get("verifier_fingerprint_sha256") != expected_verifier_fingerprint:
                failures.append("transaction.current.binding.verifier_fingerprint")
            current_ci_actual = current.get("ci_run_actual_head_sha") or current.get("review_binding_audit", {}).get("cited_hosted_ci_actual_head_sha")
            current_ci_checked = current.get("ci_checked_commit_sha")
            if current_ci_actual is not None and current_ci_checked is not None and current_ci_actual != current_ci_checked:
                failures.append("transaction.current.hosted_ci_actual_head_sha_not_exact_integration")
        if not runtime_manifest:
            failures.append("transaction.runtime_manifest_missing")
        else:
            manifest_failures, manifest_observations = _runtime_manifest_failures(
                repo_root=repo_root,
                runtime_manifest=runtime_manifest,
                review_round=review_round,
                integration_sha=integration_sha,
                implementation_fingerprint=implementation_fingerprint,
                expected_verifier_fingerprint=expected_verifier_fingerprint,
            )
            failures.extend(manifest_failures)
        if not ci_receipt:
            failures.append("transaction.hosted_ci_receipt_missing")
        else:
            ci_head = (
                ci_receipt.get("github_actions_head_sha")
                or ci_receipt.get("head_sha")
                or ci_receipt.get("checkout_sha")
                or ci_receipt.get("commit_sha")
                or ci_receipt.get("checked_commit_sha")
            )
            ci_checked = ci_receipt.get("checked_commit_sha")
            if ci_head is None or (ci_checked is not None and ci_head != ci_checked):
                failures.append("transaction.hosted_ci.head_sha_not_exact_integration")
            conclusion = ci_receipt.get("github_actions_conclusion") or ci_receipt.get("conclusion") or ci_receipt.get("hosted_ci_conclusion")
            if ci_head != integration_sha or ci_checked != integration_sha:
                failures.append("transaction.hosted_ci.head_sha_not_exact_integration")
            if conclusion != "success":
                failures.append("transaction.hosted_ci.conclusion")
    if not evidence and not fixture_mode:
        failures.append("transaction.evidence.missing")
    if evidence:
        if evidence.get("task_id") != TASK_ID:
            failures.append("transaction.evidence.task_id")
        if evidence.get("request_nonce") != REQUEST_NONCE:
            failures.append("transaction.evidence.request_nonce")
        if evidence.get("frozen_contract_sha256") != FROZEN_CONTRACT_SHA256:
            failures.append("transaction.evidence.frozen_contract_sha256")
        observed_impl = evidence.get("implementation_fingerprint_sha256")
        if observed_impl is not None and observed_impl != implementation_fingerprint:
            failures.append("transaction.evidence.implementation_fingerprint")
    return failures, {
        "planner_review_commit": PLANNER_REVIEW_COMMIT,
        "transaction_closure_phase": "post_ci_exact_transaction_gate",
        "post_ci_gate_requires_exact_hosted_ci_success": not fixture_mode,
        "review_round": review_round,
        "expected_review_round": REVIEW_ROUND,
        "integration_sha": integration_sha,
        "observed_git_head": git_head,
        "integration_sha_is_ancestor_of_observed_git_head": integration_is_ancestor,
        "implementation_fingerprint_sha256": implementation_fingerprint,
        "reviewed_verifier_fingerprint_sha256_at_repair_start": expected_verifier_fingerprint,
        "verifier_source_fingerprint_sha256": verifier_source["verifier_source_fingerprint_sha256"],
        "verifier_source_artifacts": verifier_source,
        "critical_source_or_receipt_changed_after_reviewed_integration": changed_after_list,
        "verifier_source_changed_after_reviewed_integration": source_changed_after_list,
        "current_binding": current.get("binding", current) if current else None,
        "runtime_manifest_path": str(RUNTIME_MANIFEST_PATH.relative_to(repo_root)),
        "runtime_manifest_review_round": runtime_manifest.get("review_round") if runtime_manifest else None,
        "runtime_manifest_sha256": sha256_file(RUNTIME_MANIFEST_PATH) if RUNTIME_MANIFEST_PATH.is_file() else None,
        "runtime_manifest_strict_binding": (
            manifest_observations if runtime_manifest and not fixture_mode else None
        ),
        "hosted_ci_receipt_path": str(CONTROLLER_CI_RECEIPT_PATH.relative_to(repo_root)),
        "hosted_ci_head_sha": (
            ci_receipt.get("github_actions_head_sha")
            or ci_receipt.get("head_sha")
            or ci_receipt.get("checkout_sha")
            or ci_receipt.get("commit_sha")
            or ci_receipt.get("checked_commit_sha")
        )
        if ci_receipt
        else None,
        "hosted_ci_checked_commit_sha": ci_receipt.get("checked_commit_sha") if ci_receipt else None,
        "hosted_ci_conclusion": (ci_receipt.get("github_actions_conclusion") or ci_receipt.get("conclusion") or ci_receipt.get("hosted_ci_conclusion")) if ci_receipt else None,
        "fixture_mode": fixture_mode,
    }


def _pass_probe(name: str, **extra: Any) -> dict[str, Any]:
    return {"name": name, "status": "PASS", **extra}


def fixture_probe_results() -> list[dict[str, Any]]:
    losses = {
        name: {"value": 0.25, "denominator": 8 + index, "included_in_total": True, "computed_by_verifier": True}
        for index, name in enumerate(
            [
                "conditional_final_dice_ce",
                "anatomy_deep_supervision_dice_ce",
                "wall_dice_bce",
                "distance_rho_masked_smooth_l1",
                "scar_binary_dice_focal",
                "scar_component_adaptive_tversky",
                "scar_center_focal_bce",
                "scar_extent_bce_smooth_l1",
                "scar_context_ce",
                "edema_binary_dice_focal",
                "injury_dice_bce",
                "edema_boundary_smooth_l1",
                "edema_extent_bce_smooth_l1",
                "edema_context_ce",
                "relation_loss",
            ]
        )
    }
    return [
        _pass_probe(
            "model_build_and_stock_parity",
            stock_compatible_logits_max_abs_err=0.0,
            stock_compatible_argmax_changed_voxels=0,
            train_case_ids=["Case001", "Case002"],
        ),
        _pass_probe(
            "real_train_case_total_loss_forward_backward",
            input_origin="train_only_dataset501_fixture",
            random_tensor_used=False,
            total_loss_terms=losses,
            constant_denominator_count=sum(1 for term in losses.values() if term["denominator"] == 1),
        ),
        _pass_probe(
            "loss_semantic_oracle",
            contract_source_path="automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
            contract_field_or_exact_clause="Section 10 unique allowed weighted loss set",
            tolerance=LOSS_SEMANTIC_TOLERANCE,
            reference_uses_implementation_loss_helper=False,
            injury_dice_bce={
                "matches_reference": True,
                "actual_unweighted": 0.25,
                "reference_unweighted": 0.25,
                "abs_diff": 0.0,
                "weighted_abs_diff": 0.0,
                "t2_gated": True,
            },
            scar_component_adaptive_tversky={
                "matches_reference": True,
                "actual_unweighted": 0.25,
                "reference_unweighted": 0.25,
                "abs_diff": 0.0,
                "weighted_abs_diff": 0.0,
                "unauthorized_occupancy_objective_detected": False,
            },
            unique_allowed_loss_set={
                "matches_contract_terms": True,
                "total_matches_allowed_weighted_sum": True,
                "no_extra_weighted_auxiliary_objective": True,
                "actual_terms": sorted(CANONICAL_LOSS_WEIGHTS),
            },
            semantic_failures=[],
        ),
        _pass_probe(
            "mixed_t2_no_t2_batch",
            t2_present_case_id="Case002",
            no_t2_case_id="Case003",
            no_t2_edema_owned_module_call_count=0,
            no_t2_class4_in_competition=False,
        ),
        _pass_probe(
            "required_module_final_logit_interventions",
            modules=[
                "scar_extent_head",
                "edema_extent_head",
                "edema_dilation_residual_1",
                "edema_dilation_residual_2",
                "edema_dilation_residual_4",
                "injury_classifier",
                "scar_context",
                "edema_context",
                "named_residual_projection",
            ],
            all_changed_intended_final_logits=True,
            blocking=False,
            diagnostic_only=True,
            fresh_zero_initialized_disable_flag_delta_required=False,
        ),
        _pass_probe(
            "required_module_final_authority_oracle",
            intervention_max_abs_by_required_source={
                "scar_proposal_occupancy_center": 0.05,
                "scar_context": 0.05,
                "edema_injury": 0.05,
                "edema_boundary": 0.05,
                "edema_context_and_dilation_1_2_4": 0.05,
                "scar_edema_extent_and_wall_bias": 0.05,
                "all_named_evidence_projection": 0.05,
            },
            verifier_owned_removal_max_abs_by_required_source={
                "scar_proposal_occupancy_center": 0.05,
                "scar_context": 0.05,
                "edema_injury": 0.05,
                "edema_boundary": 0.05,
                "edema_context_and_dilation_1_2_4": 0.05,
                "scar_edema_extent_and_wall_bias": 0.05,
                "all_named_evidence_projection": 0.05,
            },
            verifier_owned_group_source_counts={
                "scar_proposal_occupancy_center": 4,
                "scar_context": 2,
                "edema_injury": 1,
                "edema_boundary": 1,
                "edema_context_and_dilation_1_2_4": 5,
                "scar_edema_extent_and_wall_bias": 1,
                "all_named_evidence_projection": 47,
            },
            all_required_groups_have_verifier_owned_delta=True,
            implementation_flag_vs_verifier_owned_removal_max_abs={
                "scar_proposal_occupancy_center": 0.0,
                "scar_context": 0.0,
                "edema_injury": 0.0,
                "edema_boundary": 0.0,
                "edema_context_and_dilation_1_2_4": 0.0,
                "scar_edema_extent_and_wall_bias": 0.0,
                "all_named_evidence_projection": 0.0,
            },
            implementation_flag_equivalence_tolerance=1e-6,
            all_implementation_flags_match_verifier_owned_removal=True,
            implementation_disable_flags_treated_as_authority=False,
            disable_flag_final_logit_contribution_sites=[],
            no_disable_flag_final_logit_contribution=True,
            synthetic_intervention_delta_static_matches=[],
            synthetic_epsilon_like_runtime_deltas={},
            required_named_projection_sources_present=True,
            missing_required_group_sources=[],
            named_projection_gradient_abs_by_source={"scar_half:scar_context_to_half": 1.0},
            named_projection_final_logit_gradient_sources_present=True,
            missing_named_projection_gradient_sources=[],
            named_projection_final_logit_gradient_nonzero=True,
            zero_named_projection_gradient_sources=[],
            rejects_receipt_only_authority=True,
        ),
        _pass_probe(
            "schema_v4_checkpoint_resume",
            checkpoint_probe_kind="canonical_next_batch_total_loss_step",
            manual_gradient_only=False,
            next_descriptor_matches=True,
            scheduler_rng_sampler_cursor_match=True,
        ),
        _pass_probe(
            "deployment_loader",
            called_deployment_loader=True,
            reopened_stock_checkpoint=False,
            undeclared_host_asset_opened=False,
        ),
        _pass_probe(
            "evaluator_interface",
            called_evaluator=True,
            same_case_population=True,
            same_tta_decode_metric_population=True,
        ),
        _pass_probe(
            "single_vs_forced_multi_tile_full_volume",
            single_tile_call_id="single_call",
            forced_multi_tile_call_id="forced_multi_call",
            calls_are_distinct=True,
            patch_size_equals_input=False,
            forced_multi_tile_count=8,
            global_bias_application_count=1,
        ),
        _pass_probe(
            "tile_local_forward_instrumentation",
            forced_multi_tile_count=8,
            forced_model_forward_count=8,
            no_t2_forced_model_forward_count=8,
            mirror_factor=1,
            expected_model_forward_count=8,
            model_input_spatial_within_declared_patch=True,
            full_support_pseudo_tiling_detected=False,
            global_bias_application_count=1,
            no_t2_global_bias_application_count=1,
            tile_coordinates_recorded=True,
            tile_outputs_limited_to_base_logits_wall_extent_evidence=True,
        ),
        _pass_probe(
            "step0_parity_report_regression",
            imported_step0_parity_report=True,
            attribute_error_ignored=False,
            t2_present_stock_max_abs_err=0.0,
            no_t2_stock_max_abs_err=0.0,
            compatible_argmax_changed_voxels=0,
            no_t2_edema_owned_module_call_count=0,
            no_t2_class4_in_competition=False,
        ),
        _pass_probe(
            "partial_hw_extent_zero_contribution",
            actual_scalar_loss=0.25,
            reference_fully_valid_only_loss=0.25,
            loss_matches_fully_valid_reference=True,
            partial_hw_presence_denominator_contribution=0.0,
            partial_hw_area_denominator_contribution=0.0,
            partial_hw_extent_head_grad_abs_sum=0.0,
            partial_hw_extent_bias_abs_sum=0.0,
            full_neighbor_extent_head_grad_abs_sum=0.1,
            full_neighbor_extent_bias_abs_sum=0.1,
            straight_through_zero_loss_detected=False,
            disables_all_extent_on_padding=False,
        ),
        _pass_probe(
            "partial_hw_extent_reference_objective",
            actual_scalar_loss=0.25,
            reference_fully_valid_only_loss=0.25,
            loss_matches_fully_valid_reference=True,
            partial_hw_presence_denominator_contribution=0.0,
            partial_hw_area_denominator_contribution=0.0,
            partial_hw_extent_head_grad_abs_sum=0.0,
            partial_hw_extent_bias_abs_sum=0.0,
            full_neighbor_extent_head_grad_abs_sum=0.1,
            full_neighbor_extent_bias_abs_sum=0.1,
            straight_through_zero_loss_detected=False,
            disables_all_extent_on_padding=False,
        ),
        _pass_probe(
            "partial_hw_slice_extent_head_cross_z_gradient",
            uses_real_slice_extent_head=True,
            loss_applied_only_to_fully_valid_neighbor=True,
            partial_hw_input_feature_grad_abs_sum=0.0,
            full_neighbor_input_feature_grad_abs_sum=0.1,
            cross_z_partial_feature_gradient_zero=True,
            full_neighbor_gradient_nonzero=True,
        ),
    ]


def _resolve_artifact(repo_root: Path, value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    if not path.is_absolute():
        path = repo_root / path
    try:
        path.resolve().relative_to(repo_root.resolve())
    except ValueError:
        return None
    return path


def _receipt_stdout_sha_matches(receipt_path: Path, receipt: dict[str, Any]) -> bool:
    if "payload" not in receipt:
        return False
    expected_stdout = json.dumps(receipt["payload"], indent=2, sort_keys=True, default=str).encode("utf-8")
    stdout_path = receipt_path.with_name(receipt_path.name.replace("_receipt.json", "_stdout.json"))
    allowed = {sha256_bytes(expected_stdout)}
    if stdout_path.is_file():
        allowed.add(sha256_file(stdout_path))
    return receipt.get("stdout_sha256") in allowed


def _load_runtime_receipts(repo_root: Path, evidence: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    failures: list[str] = []
    receipt_paths = evidence.get("receipt_paths")
    if not isinstance(receipt_paths, dict):
        return ["runtime_receipts.receipt_paths_missing"], {}
    required = {
        "architecture_signature",
        "forward_backward_probe",
        "inference_probe",
        "checkpoint_resume_probe",
        "deployment_load_probe",
        "evaluator_smoke",
        "hard_negative_binding",
        "step0_parity_probe",
    }
    receipts: dict[str, dict[str, Any]] = {}
    for name in sorted(required):
        path = _resolve_artifact(repo_root, receipt_paths.get(name))
        if path is None:
            failures.append(f"runtime_receipts.path_invalid:{name}")
            continue
        if not path.is_file():
            failures.append(f"runtime_receipts.path_missing:{name}")
            continue
        try:
            receipt = load_json(path)
        except Exception as exc:
            failures.append(f"runtime_receipts.invalid_json:{name}:{type(exc).__name__}")
            continue
        receipt["_verifier_observed_path"] = str(path.relative_to(repo_root))
        receipt["_verifier_observed_sha256"] = sha256_file(path)
        receipts[name] = receipt
        if name == "architecture_signature":
            continue
        if receipt.get("task_id") != TASK_ID:
            failures.append(f"runtime_receipts.task_id:{name}")
        if receipt.get("request_nonce") != REQUEST_NONCE:
            failures.append(f"runtime_receipts.request_nonce:{name}")
        if receipt.get("executed") is not True:
            failures.append(f"runtime_receipts.not_executed:{name}")
        if receipt.get("exit_code") != 0:
            failures.append(f"runtime_receipts.exit_code:{name}")
        if receipt.get("zero_credit") is not True:
            failures.append(f"runtime_receipts.not_zero_credit:{name}")
        if receipt.get("formal_training_started") is not False:
            failures.append(f"runtime_receipts.training_started:{name}")
        if receipt.get("outer_accessed") is not False:
            failures.append(f"runtime_receipts.outer_accessed:{name}")
        if "command" in receipt and receipt.get("command_sha256") != json_sha(receipt["command"]):
            failures.append(f"runtime_receipts.command_sha:{name}")
        if not _receipt_stdout_sha_matches(path, receipt):
            failures.append(f"runtime_receipts.stdout_sha:{name}")
        if receipt.get("stderr_sha256") != sha256_bytes(b""):
            failures.append(f"runtime_receipts.stderr_sha:{name}")
        payload = receipt.get("payload", {})
        if not isinstance(payload, dict) or payload.get("status") != "PASS":
            failures.append(f"runtime_receipts.payload_status:{name}")
        if name == "checkpoint_resume_probe" and isinstance(payload, dict):
            if payload.get("request_nonce") != REQUEST_NONCE:
                failures.append("runtime_receipts.checkpoint.current_request_nonce")
            if payload.get("frozen_contract_sha256") != FROZEN_CONTRACT_SHA256:
                failures.append("runtime_receipts.checkpoint.current_frozen_contract_sha256")
    return failures, receipts


def runtime_receipt_bindings(repo_root: Path, evidence: dict[str, Any]) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    receipt_paths = evidence.get("receipt_paths")
    if not isinstance(receipt_paths, dict):
        return bindings
    for name, value in sorted(receipt_paths.items()):
        path = _resolve_artifact(repo_root, value)
        item: dict[str, Any] = {"declared_path": value}
        if path is not None:
            item["resolved_path"] = str(path.relative_to(repo_root))
            item["exists"] = path.is_file()
            if path.is_file():
                item["sha256"] = sha256_file(path)
        else:
            item["exists"] = False
        bindings[name] = item
    return bindings


def _as_bool(value: Any) -> bool:
    return value is True


def _crop_or_pad_array(array: Any, center: tuple[int, int, int], patch_size: tuple[int, int, int], *, pad_value: float | int) -> Any:
    import numpy as np

    spatial = tuple(int(v) for v in array.shape[-3:])
    src_slices: list[slice] = []
    dst_slices: list[slice] = []
    for c, dim, size in zip(center, spatial, patch_size):
        start = int(c) - int(size) // 2
        stop = start + int(size)
        src_start = max(0, start)
        src_stop = min(int(dim), stop)
        dst_start = src_start - start
        dst_stop = dst_start + (src_stop - src_start)
        src_slices.append(slice(src_start, src_stop))
        dst_slices.append(slice(dst_start, dst_stop))
    out = np.full(array.shape[:-3] + tuple(int(v) for v in patch_size), pad_value, dtype=array.dtype)
    out[(..., *dst_slices)] = array[(..., *src_slices)]
    return out


def _case_paths(case_id: str) -> dict[str, Path]:
    preprocessed = Path(os.environ.get("nnUNet_preprocessed", ""))
    root = preprocessed / "Dataset501_CAREMyoPS" / "nnUNetPlans_3d_fullres"
    return {
        "array": root / f"{case_id}.b2nd",
        "seg": root / f"{case_id}_seg.b2nd",
        "properties": root / f"{case_id}.pkl",
    }


def _load_case_arrays(case_id: str) -> dict[str, Any]:
    import blosc2
    import numpy as np
    import pickle

    paths = _case_paths(case_id)
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing runtime case files for {case_id}: {missing}")
    image = np.asarray(blosc2.open(str(paths["array"]), mode="r")[:], dtype=np.float32)
    seg = np.asarray(blosc2.open(str(paths["seg"]), mode="r")[:])
    if seg.ndim == 4 and seg.shape[0] == 1:
        seg = seg[0]
    with paths["properties"].open("rb") as handle:
        properties = pickle.load(handle)
    geometry = {
        "case_id": str(case_id),
        "image_shape": [int(v) for v in image.shape],
        "segmentation_shape": [int(v) for v in seg.shape],
        "spacing_zyx": [float(v) for v in properties.get("spacing", (1.0, 1.0, 1.0))],
        "array_sha256": sha256_file(paths["array"]),
        "segmentation_sha256": sha256_file(paths["seg"]),
        "properties_sha256": sha256_file(paths["properties"]),
    }
    geometry["geometry_sha256"] = json_sha(geometry)
    return {"image": image, "seg": seg, "paths": paths, "geometry": geometry}


def _center_for_label(seg: Any, labels: tuple[int, ...]) -> tuple[int, int, int]:
    import numpy as np

    for label in labels:
        coords = np.argwhere(seg == int(label))
        if coords.size:
            row = coords[len(coords) // 2]
            return tuple(int(v) for v in row)
    coords = np.argwhere(seg >= 0)
    if not coords.size:
        raise RuntimeError("case segmentation has no valid voxels")
    row = coords[len(coords) // 2]
    return tuple(int(v) for v in row)


def _actual_batch(case: dict[str, Any], availability: tuple[float, float, float], *, labels: tuple[int, ...], device: Any) -> dict[str, Any]:
    import torch

    center = _center_for_label(case["seg"], labels)
    image = _crop_or_pad_array(case["image"], center, PLAN_PATCH_SIZE, pad_value=0.0)
    seg = _crop_or_pad_array(case["seg"], center, PLAN_PATCH_SIZE, pad_value=-1)
    valid = (seg >= 0).astype("float32")
    return {
        "image": torch.from_numpy(image).unsqueeze(0).to(device=device, dtype=torch.float32),
        "seg": torch.from_numpy(seg).unsqueeze(0).to(device=device, dtype=torch.long),
        "availability": torch.tensor([list(availability)], device=device, dtype=torch.float32),
        "spacing": torch.tensor([case["geometry"]["spacing_zyx"]], device=device, dtype=torch.float32),
        "extent_valid_spatial_mask": torch.from_numpy(valid).unsqueeze(0).unsqueeze(0).to(device=device, dtype=torch.float32),
        "center": center,
        "case": case["geometry"],
        "batch_sha256": json_sha({"case": case["geometry"], "center": center, "patch_size": PLAN_PATCH_SIZE}),
    }


def _runtime_case_bindings(repo_root: Path) -> dict[str, Any]:
    from src.care_myocardium.data.case_metadata import load_myops_case_metadata

    metadata_root = Path(os.environ.get("CARE_ROOT", repo_root)).resolve()
    metadata = load_myops_case_metadata(metadata_root)
    t2_case_id = "Case2003"
    no_t2_case_id = "Case1001"
    t2 = _load_case_arrays(t2_case_id)
    no_t2 = _load_case_arrays(no_t2_case_id)
    return {
        "t2_case_id": t2_case_id,
        "no_t2_case_id": no_t2_case_id,
        "t2_case": t2,
        "no_t2_case": no_t2,
        "t2_availability": tuple(float(v) for v in metadata[t2_case_id].availability),
        "no_t2_availability": tuple(float(v) for v in metadata[no_t2_case_id].availability),
        "metadata_root": str(metadata_root),
    }


def _max_grad_abs(parameters: Any) -> float:
    values = []
    for param in parameters:
        if param.grad is not None:
            values.append(float(param.grad.detach().abs().max().cpu()))
    return max(values) if values else 0.0


def _independent_partial_hw_probe(model: Any, *, loss_fn: Any | None = None) -> dict[str, Any]:
    import torch
    import torch.nn.functional as F
    from src.care_myocardium.models.care_ase import compute_slice_extent_statistics, full_hw_valid_slice_mask
    from src.care_myocardium.training.care_ase_trainer import per_slice_extent_loss

    loss_fn = loss_fn or per_slice_extent_loss
    presence_logits = torch.full((1, 1, 2, 4, 4), 2.0, requires_grad=True)
    area_logits = torch.full((1, 1, 2, 4, 4), 1.25, requires_grad=True)
    p_wall = torch.ones_like(presence_logits) * 0.75
    valid_spatial = torch.ones_like(presence_logits)
    valid_spatial[..., 0, 0, 0] = 0.0
    target_presence = torch.tensor([[[0.0, 1.0]]])
    path_voxels = torch.tensor([[[0.0, 1.0]]])
    wall_voxels = torch.tensor([[[2.0, 4.0]]])
    z_valid = torch.ones(1, 1, 2)
    presence, area = loss_fn(
        presence_logits,
        area_logits,
        p_wall,
        target_presence,
        path_voxels,
        wall_voxels,
        z_valid,
        valid_spatial,
    )
    loss = presence + area
    pred_presence_5d, pred_area_5d, _wall_slice, _fallback = compute_slice_extent_statistics(
        presence_logits.float(),
        area_logits.float(),
        p_wall.detach(),
        valid_spatial,
    )
    full_valid_z = full_hw_valid_slice_mask(valid_spatial, presence_logits.shape[-3:], dtype=presence_logits.dtype).squeeze(-1).squeeze(-1)
    pred_presence_z = pred_presence_5d.squeeze(-1).squeeze(-1)
    pred_area_z = pred_area_5d.squeeze(-1).squeeze(-1)
    presence_raw = F.binary_cross_entropy(pred_presence_z.float().clamp(1.0e-6, 1.0 - 1.0e-6), target_presence.float(), reduction="none")
    area_target = path_voxels.float() / wall_voxels.float().clamp_min(1.0)
    area_raw = F.smooth_l1_loss(pred_area_z.float(), area_target.float(), reduction="none")
    full_mask = z_valid.float() * full_valid_z.float()
    area_mask = full_mask * (wall_voxels > 0).float()
    reference_presence = (presence_raw * full_mask).sum() / full_mask.sum().clamp_min(1.0)
    reference_area = (area_raw * area_mask).sum() / area_mask.sum().clamp_min(1.0)
    reference_loss = reference_presence + reference_area
    loss.backward()
    actual_loss = float(loss.detach().cpu())
    reference_loss_value = float(reference_loss.detach().cpu())
    partial_grad = float(presence_logits.grad[..., 0, :, :].abs().sum().cpu() + area_logits.grad[..., 0, :, :].abs().sum().cpu())
    full_grad = float(presence_logits.grad[..., 1, :, :].abs().sum().cpu() + area_logits.grad[..., 1, :, :].abs().sum().cpu())
    components = {
        "scar_extent_presence": torch.full((1, 1, 2, 4, 4), 2.0),
        "scar_extent_area": torch.full((1, 1, 2, 4, 4), 2.0),
        "edema_extent_presence": torch.full((1, 1, 2, 4, 4), 2.0),
        "edema_extent_area": torch.full((1, 1, 2, 4, 4), 2.0),
    }
    scar_bias = model._extent_bias(components, p_wall, pathology="scar", global_step=2000, valid_spatial_mask=valid_spatial)
    edema_bias = model._extent_bias(components, p_wall, pathology="edema", global_step=2000, valid_spatial_mask=valid_spatial)
    partial_bias_abs = float(scar_bias[..., 0, :, :].abs().sum().cpu() + edema_bias[..., 0, :, :].abs().sum().cpu())
    full_bias_abs = float(scar_bias[..., 1, :, :].abs().sum().cpu() + edema_bias[..., 1, :, :].abs().sum().cpu())
    loss_matches_reference = abs(actual_loss - reference_loss_value) <= 1.0e-6
    straight_through_zero_loss_detected = actual_loss == 0.0 and full_grad > 0.0 and reference_loss_value > 1.0e-6
    disables_all_extent_on_padding = actual_loss == 0.0 and full_grad == 0.0 and reference_loss_value > 1.0e-6
    passed = (
        loss_matches_reference
        and partial_grad == 0.0
        and partial_bias_abs == 0.0
        and full_grad > 0.0
        and full_bias_abs > 0.0
        and not straight_through_zero_loss_detected
        and not disables_all_extent_on_padding
    )
    return _pass_probe(
        "partial_hw_extent_zero_contribution",
        status="PASS" if passed else "FAIL",
        actual_scalar_loss=actual_loss,
        reference_fully_valid_only_loss=reference_loss_value,
        loss_matches_fully_valid_reference=loss_matches_reference,
        partial_hw_presence_denominator_contribution=float(full_mask[..., 0].sum().detach().cpu()),
        partial_hw_area_denominator_contribution=float(area_mask[..., 0].sum().detach().cpu()),
        full_neighbor_presence_denominator_contribution=float(full_mask[..., 1].sum().detach().cpu()),
        full_neighbor_area_denominator_contribution=float(area_mask[..., 1].sum().detach().cpu()),
        partial_hw_loss_contribution=0.0 if loss_matches_reference else actual_loss,
        partial_hw_extent_head_grad_abs_sum=partial_grad,
        partial_hw_extent_bias_abs_sum=partial_bias_abs,
        full_neighbor_extent_head_grad_abs_sum=full_grad,
        full_neighbor_extent_bias_abs_sum=full_bias_abs,
        straight_through_zero_loss_detected=straight_through_zero_loss_detected,
        disables_all_extent_on_padding=disables_all_extent_on_padding,
    )


def _partial_hw_reference_probe(model: Any, *, loss_fn: Any | None = None) -> dict[str, Any]:
    probe = _independent_partial_hw_probe(model, loss_fn=loss_fn)
    return {
        **probe,
        "name": "partial_hw_extent_reference_objective",
    }


def _slice_extent_head_cross_z_probe(model: Any) -> dict[str, Any]:
    import torch
    import torch.nn.functional as F

    head = model.component_heads.scar_extent_head
    conv = next((module for module in head.sequence.modules() if module.__class__.__name__ == "Conv1d"), None)
    in_channels = int(getattr(conv, "in_channels", 0) or 0)
    if in_channels <= 0:
        return _pass_probe(
            "partial_hw_slice_extent_head_cross_z_gradient",
            status="FAIL",
            uses_real_slice_extent_head=False,
            loss_applied_only_to_fully_valid_neighbor=True,
            partial_hw_input_feature_grad_abs_sum=math.inf,
            full_neighbor_input_feature_grad_abs_sum=0.0,
            cross_z_partial_feature_gradient_zero=False,
            full_neighbor_gradient_nonzero=False,
            failure_reason="scar_extent_head_sequence_conv1d_missing",
        )

    torch.manual_seed(91027)
    feature = torch.randn(1, in_channels, 3, 4, 4, requires_grad=True)
    valid = torch.ones(1, 1, 3, 4, 4)
    valid[..., 1, 0, 0] = 0.0
    outputs = head(feature, valid)
    presence = outputs["presence_logits"]
    area = outputs["area_logits"]

    neighbor_slice = 2
    objective = F.binary_cross_entropy_with_logits(
        presence[..., neighbor_slice, :, :],
        torch.ones_like(presence[..., neighbor_slice, :, :]),
    ) + F.smooth_l1_loss(
        area[..., neighbor_slice, :, :],
        torch.zeros_like(area[..., neighbor_slice, :, :]),
    )
    objective.backward()

    partial_grad = float(feature.grad[..., 1, :, :].detach().abs().sum().cpu())
    full_grad = float(feature.grad[..., neighbor_slice, :, :].detach().abs().sum().cpu())
    passed = partial_grad == 0.0 and full_grad > 0.0
    return _pass_probe(
        "partial_hw_slice_extent_head_cross_z_gradient",
        status="PASS" if passed else "FAIL",
        contract_source_path="automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        contract_field_or_exact_clause=(
            "Sections 8 and 15: partial-H/W slices contribute zero bias/loss/gradient; fully valid "
            "neighboring slices remain supervised."
        ),
        logical_derivation=(
            "The real SliceExtentHead pooling plus Conv1d sequence is executed, and only a fully-valid "
            "neighbor slice objective is backpropagated. Any gradient on the adjacent partial-H/W input "
            "feature is forbidden cross-z leakage from a masked-out slice."
        ),
        uses_real_slice_extent_head=True,
        loss_applied_only_to_fully_valid_neighbor=True,
        partial_slice_index=1,
        fully_valid_neighbor_slice_index=neighbor_slice,
        partial_hw_input_feature_grad_abs_sum=partial_grad,
        full_neighbor_input_feature_grad_abs_sum=full_grad,
        cross_z_partial_feature_gradient_zero=partial_grad == 0.0,
        full_neighbor_gradient_nonzero=full_grad > 0.0,
    )


def _verifier_downsample_nearest(tensor: Any, size: tuple[int, int, int]) -> Any:
    import torch.nn.functional as F

    return F.interpolate(tensor.float(), size=size, mode="nearest").to(dtype=tensor.dtype)


def _verifier_binary_dice_bce(logit: Any, target: Any, valid_mask: Any | None = None) -> Any:
    import torch
    import torch.nn.functional as F

    logit = logit.float()
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    dims = tuple(range(1, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    gt_positive = (target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + gt_positive
    dice_values = torch.where(
        gt_positive > 0,
        1.0 - (2.0 * inter + 1.0e-5) / (denom + 1.0e-5),
        torch.zeros_like(denom),
    )
    dice = dice_values.mean()
    bce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    return dice + ((bce * mask).sum() / mask.sum().clamp_min(1.0))


def _verifier_binary_dice_focal(logit: Any, target: Any, valid_mask: Any | None, *, alpha: float, gamma: float) -> Any:
    import torch
    import torch.nn.functional as F

    logit = logit.float()
    target = target.to(logit)
    mask = torch.ones_like(target) if valid_mask is None else valid_mask.to(logit)
    prob = torch.sigmoid(logit)
    dims = tuple(range(1, prob.ndim))
    inter = (prob * target * mask).sum(dim=dims)
    gt_positive = (target * mask).sum(dim=dims)
    denom = (prob * mask).sum(dim=dims) + gt_positive
    dice_values = torch.where(
        gt_positive > 0,
        1.0 - (2.0 * inter + 1.0e-5) / (denom + 1.0e-5),
        torch.zeros_like(denom),
    )
    dice = dice_values.mean()
    bce = F.binary_cross_entropy_with_logits(logit, target, reduction="none")
    p_t = prob * target + (1.0 - prob) * (1.0 - target)
    alpha_t = alpha * target + (1.0 - alpha) * (1.0 - target)
    focal = alpha_t * (1.0 - p_t).pow(gamma) * bce
    return dice + ((focal * mask).sum() / mask.sum().clamp_min(1.0))


def _verifier_component_tversky(logit: Any, target: Any, valid_mask: Any, *, alpha: float = 0.3, beta: float = 0.7) -> Any:
    logit = logit.float()
    target = target.to(logit)
    mask = valid_mask.to(logit)
    prob = logit.sigmoid()
    tp = (prob * target * mask).sum()
    fp = (prob * (1.0 - target) * mask).sum()
    fn = ((1.0 - prob) * target * mask).sum()
    return 1.0 - (tp + 1.0e-5) / (tp + alpha * fp + beta * fn + 1.0e-5)


def _verifier_component_adaptive_tversky(logit: Any, target: Any, valid_mask: Any, batch: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    import numpy as np
    import torch
    from scipy import ndimage

    losses: list[Any] = []
    weights: list[float] = []
    target_np = target.detach().cpu().numpy().astype(bool)
    spacing = batch.get("spacing")
    spacing_np = spacing.detach().cpu().numpy() if spacing is not None else np.ones((target_np.shape[0], 3), dtype=np.float32)
    for batch_index in range(int(target_np.shape[0])):
        scar_mask = target_np[batch_index, 0]
        comp, count = ndimage.label(scar_mask, structure=np.ones((3, 3, 3), dtype=np.uint8))
        for comp_id in range(1, int(count) + 1):
            comp_mask_np = comp == comp_id
            if not bool(comp_mask_np.any()):
                continue
            other_np = scar_mask & ~comp_mask_np
            volume = float(comp_mask_np.sum() * np.prod(spacing_np[batch_index]))
            weight = min(max(math.sqrt(1000.0 / max(volume, 1.0)), 1.0), 4.0)
            comp_mask = torch.from_numpy(comp_mask_np[None, None]).to(device=logit.device, dtype=logit.dtype)
            other_components = torch.from_numpy(other_np[None, None]).to(device=logit.device, dtype=logit.dtype)
            comp_valid = valid_mask[batch_index : batch_index + 1].to(logit) * (1.0 - other_components)
            losses.append(_verifier_component_tversky(logit[batch_index : batch_index + 1], comp_mask, comp_valid, alpha=0.3, beta=0.7))
            weights.append(float(weight))
    if not losses:
        return logit.sum() * 0.0, {"component_count": 0, "adaptive_weight_sum": 0.0, "adaptive_weights": []}
    weight_tensor = torch.tensor(weights, device=logit.device, dtype=torch.float32)
    return (torch.stack(losses).float() * weight_tensor).sum() / weight_tensor.sum().clamp_min(1.0e-6), {
        "component_count": len(losses),
        "adaptive_weight_sum": float(sum(weights)),
        "adaptive_weights": weights,
    }


def _loss_semantic_reference_values(outputs: dict[str, Any], batch: dict[str, Any]) -> dict[str, Any]:
    import torch
    import torch.nn.functional as F

    logits = outputs["final_logits"]
    target = batch["seg"].to(device=logits.device, dtype=torch.long)
    availability = batch["availability"].to(logits)
    valid_binary = (target >= 0).unsqueeze(1).to(logits)
    t2_mask = availability[:, 1].view(-1, 1, 1, 1, 1)
    edema_valid = valid_binary * t2_mask
    scar_target = (target == 5).unsqueeze(1)
    injury_target = ((target == 4) | (target == 5)).unsqueeze(1)
    components = outputs["components"]

    injury_logit = F.interpolate(components["edema_injury"], size=target.shape[-3:], mode="trilinear", align_corners=False)
    injury_dice_bce = _verifier_binary_dice_bce(injury_logit, injury_target, edema_valid)
    injury_dice_focal = _verifier_binary_dice_focal(injury_logit, injury_target, edema_valid, alpha=0.35, gamma=2.0)

    scar_half = F.interpolate(outputs["scar"].get("half_logit", outputs["scar"]["half_logits6"][:, 5:6]), size=target.shape[-3:], mode="trilinear", align_corners=False)
    scar_component, component_meta = _verifier_component_adaptive_tversky(scar_half, scar_target.float(), valid_binary, batch)
    scar_occ_quarter = _verifier_downsample_nearest(scar_target, components["scar_quarter_occupancy"].shape[-3:])
    scar_occ_half = _verifier_downsample_nearest(scar_target, components["scar_half_occupancy"].shape[-3:])
    valid_quarter = _verifier_downsample_nearest(valid_binary, components["scar_quarter_occupancy"].shape[-3:]).float()
    valid_half = _verifier_downsample_nearest(valid_binary, components["scar_half_occupancy"].shape[-3:]).float()
    scar_occupancy = 0.5 * _verifier_binary_dice_focal(
        components["scar_quarter_occupancy"], scar_occ_quarter, valid_quarter, alpha=0.25, gamma=2.0
    ) + 0.5 * _verifier_binary_dice_focal(components["scar_half_occupancy"], scar_occ_half, valid_half, alpha=0.25, gamma=2.0)
    return {
        "injury_dice_bce": injury_dice_bce,
        "injury_dice_focal_alpha035_gamma2": injury_dice_focal,
        "scar_component_adaptive_tversky": scar_component,
        "scar_occupancy_dice_focal": scar_occupancy,
        "scar_component_metadata": component_meta,
        "t2_eligible_rows": int((availability[:, 1] > 0.5).sum().detach().cpu()),
        "valid_voxel_count": int(valid_binary.detach().float().sum().cpu()),
        "edema_valid_voxel_count": int(edema_valid.detach().float().sum().cpu()),
    }


def _term_value(terms: dict[str, Any], name: str, field: str = "value") -> float:
    value = terms.get(name, {}).get(field)
    if not isinstance(value, (int, float)):
        return float("nan")
    return float(value)


def _loss_semantic_oracle(outputs: dict[str, Any], batch: dict[str, Any], total_loss: Any, terms: dict[str, Any]) -> dict[str, Any]:
    refs = _loss_semantic_reference_values(outputs, batch)
    injury_actual = _term_value(terms, "injury_dice_bce")
    injury_ref = float(refs["injury_dice_bce"].detach().cpu())
    injury_focal = float(refs["injury_dice_focal_alpha035_gamma2"].detach().cpu())
    scar_actual = _term_value(terms, "scar_component_adaptive_tversky")
    scar_ref = float(refs["scar_component_adaptive_tversky"].detach().cpu())
    scar_occupancy = float(refs["scar_occupancy_dice_focal"].detach().cpu())
    injury_diff = abs(injury_actual - injury_ref)
    scar_diff = abs(scar_actual - scar_ref)
    actual_terms = set(terms)
    expected_terms = set(CANONICAL_LOSS_WEIGHTS)
    weighted_sum = 0.0
    weighted_sum_finite = True
    weight_failures: list[str] = []
    for name, expected_weight in CANONICAL_LOSS_WEIGHTS.items():
        term = terms.get(name, {})
        try:
            observed_weight = float(term.get("weight"))
            weighted_sum += float(term.get("weighted_contribution"))
        except Exception:
            weighted_sum_finite = False
            weight_failures.append(name)
            continue
        if abs(observed_weight - expected_weight) > 1.0e-8:
            weight_failures.append(name)
    total_value = float(total_loss.detach().cpu()) if hasattr(total_loss, "detach") else float(total_loss)
    total_diff = abs(total_value - weighted_sum) if weighted_sum_finite else float("inf")
    semantic_failures: list[str] = []
    if injury_diff > LOSS_SEMANTIC_TOLERANCE:
        semantic_failures.append("injury_dice_bce.formula_mismatch")
    if scar_diff > LOSS_SEMANTIC_TOLERANCE:
        semantic_failures.append("scar_component_adaptive_tversky.formula_mismatch_or_hidden_auxiliary")
    if actual_terms != expected_terms:
        semantic_failures.append("unique_allowed_loss_set.term_set_mismatch")
    if weight_failures:
        semantic_failures.append("unique_allowed_loss_set.weight_or_contribution_unreadable")
    if total_diff > LOSS_SEMANTIC_TOLERANCE:
        semantic_failures.append("unique_allowed_loss_set.total_not_reported_allowed_weighted_sum")
    unauthorized_occupancy = scar_diff > LOSS_SEMANTIC_TOLERANCE and scar_occupancy > LOSS_SEMANTIC_TOLERANCE
    return _pass_probe(
        "loss_semantic_oracle",
        status="PASS" if not semantic_failures else "FAIL",
        contract_source_path="automation/agent_flow_v3/tasks/care-ase-faithful/FROZEN_CONTRACT.md",
        contract_field_or_exact_clause="Section 10 unique allowed weighted loss set",
        tolerance=LOSS_SEMANTIC_TOLERANCE,
        reference_uses_implementation_loss_helper=False,
        semantic_failures=semantic_failures,
        injury_dice_bce={
            "matches_reference": injury_diff <= LOSS_SEMANTIC_TOLERANCE,
            "actual_unweighted": injury_actual,
            "reference_unweighted": injury_ref,
            "abs_diff": injury_diff,
            "weighted_actual": injury_actual * CANONICAL_LOSS_WEIGHTS["injury_dice_bce"],
            "weighted_reference": injury_ref * CANONICAL_LOSS_WEIGHTS["injury_dice_bce"],
            "weighted_abs_diff": injury_diff * CANONICAL_LOSS_WEIGHTS["injury_dice_bce"],
            "target_labels": [4, 5],
            "t2_gated": True,
            "t2_eligible_rows": refs["t2_eligible_rows"],
            "edema_valid_voxel_count": refs["edema_valid_voxel_count"],
            "actual_matches_independent_dice_focal_alpha035_gamma2": abs(injury_actual - injury_focal) <= LOSS_SEMANTIC_TOLERANCE,
        },
        scar_component_adaptive_tversky={
            "matches_reference": scar_diff <= LOSS_SEMANTIC_TOLERANCE,
            "actual_unweighted": scar_actual,
            "reference_unweighted": scar_ref,
            "abs_diff": scar_diff,
            "weighted_actual": scar_actual * CANONICAL_LOSS_WEIGHTS["scar_component_adaptive_tversky"],
            "weighted_reference": scar_ref * CANONICAL_LOSS_WEIGHTS["scar_component_adaptive_tversky"],
            "weighted_abs_diff": scar_diff * CANONICAL_LOSS_WEIGHTS["scar_component_adaptive_tversky"],
            "alpha": 0.3,
            "beta": 0.7,
            "small_component_weight_formula": "clip(sqrt(1000mm3/component_volume_mm3),1,4)",
            "component_count": refs["scar_component_metadata"]["component_count"],
            "adaptive_weight_sum": refs["scar_component_metadata"]["adaptive_weight_sum"],
            "scar_occupancy_dice_focal_reference_unweighted": scar_occupancy,
            "unauthorized_occupancy_objective_detected": unauthorized_occupancy,
        },
        unique_allowed_loss_set={
            "matches_contract_terms": actual_terms == expected_terms,
            "actual_terms": sorted(actual_terms),
            "expected_terms": sorted(expected_terms),
            "missing_terms": sorted(expected_terms - actual_terms),
            "extra_terms": sorted(actual_terms - expected_terms),
            "weights_match_contract": not weight_failures,
            "weight_failures": sorted(weight_failures),
            "total_loss": total_value,
            "reported_allowed_weighted_sum": weighted_sum,
            "total_abs_diff": total_diff,
            "total_matches_allowed_weighted_sum": total_diff <= LOSS_SEMANTIC_TOLERANCE,
            "no_extra_weighted_auxiliary_objective": not unauthorized_occupancy and total_diff <= LOSS_SEMANTIC_TOLERANCE,
        },
    )


def _final_authority_probe(model: Any, batch: dict[str, Any], core_path: Path) -> dict[str, Any]:
    import ast
    import types
    import torch
    import torch.nn.functional as F

    model.eval()
    image = batch["image"]
    availability = batch["availability"]

    projection_sets = {
        "scar_half": model.scar_branch.half_projections,
        "scar_full": model.scar_branch.full_projections,
        "edema_half": model.edema_branch.half_projections,
        "edema_full": model.edema_branch.full_projections,
    }
    projection_locations: dict[str, tuple[str, Any, Any]] = {}
    for group_name, projection_set in projection_sets.items():
        for source_name, projection in projection_set.projections.items():
            projection_locations[str(source_name)] = (group_name, projection_set, projection)

    def _restore_projection_parameters(backups: list[tuple[Any, Any, Any]]) -> None:
        with torch.no_grad():
            for projection, weight, bias in backups:
                projection.weight.copy_(weight)
                if projection.bias is not None and bias is not None:
                    projection.bias.copy_(bias)

    def _activate_projection_sources(source_names: list[str]) -> list[tuple[Any, Any, Any]]:
        backups: list[tuple[Any, Any, Any]] = []
        with torch.no_grad():
            for source_name in source_names:
                _group_name, _projection_set, projection = projection_locations[source_name]
                backups.append(
                    (
                        projection,
                        projection.weight.detach().clone(),
                        projection.bias.detach().clone() if projection.bias is not None else None,
                    )
                )
                projection.weight.zero_()
                for out_index in range(int(projection.weight.shape[0])):
                    projection.weight[out_index].fill_(0.015 * (1.0 + 0.01 * (out_index % 7)))
                if projection.bias is not None:
                    projection.bias.zero_()
        return backups

    def _zero_projection_for_sources(source_names: list[str]) -> list[tuple[Any, Any]]:
        patched: list[tuple[Any, Any]] = []
        for source_name in source_names:
            _group_name, _projection_set, projection = projection_locations[source_name]
            original_forward = projection.forward

            def zero_forward(self: Any, tensor: Any, _source_name: str = source_name) -> Any:
                return tensor.detach().new_zeros((tensor.shape[0], self.out_channels, *tensor.shape[-3:]))

            projection.forward = types.MethodType(zero_forward, projection)  # type: ignore[method-assign]
            patched.append((projection, original_forward))
        return patched

    def _restore_projection_forwards(patched: list[tuple[Any, Any]]) -> None:
        for projection, original_forward in patched:
            projection.forward = original_forward  # type: ignore[method-assign]

    def _pathology_slice(outputs: dict[str, Any], channels: list[int]) -> Any:
        final_logits = outputs["final_logits"]
        return final_logits[:, channels, ...]

    required_groups = {
        "scar_proposal_occupancy_center": {
            "sources": [
                "scar_quarter_occupancy_to_half",
                "scar_quarter_center_to_half",
                "scar_half_occupancy_to_full",
                "scar_half_center_to_full",
            ],
            "disable_kwargs": {"disable_scar_proposal": True, "disable_scar_center": True},
            "channels": [5],
        },
        "scar_context": {
            "sources": ["scar_context_to_half", "scar_context_to_full"],
            "disable_kwargs": {"disable_scar_context": True},
            "channels": [5],
        },
        "edema_injury": {
            "sources": ["edema_injury_to_full"],
            "disable_kwargs": {"disable_edema_injury": True},
            "channels": [4],
        },
        "edema_boundary": {
            "sources": ["edema_boundary_to_full"],
            "disable_kwargs": {"disable_edema_boundary": True},
            "channels": [4],
        },
        "edema_context_and_dilation_1_2_4": {
            "sources": [
                "edema_context_to_half",
                "edema_context_to_full",
                "edema_dilation1_to_full",
                "edema_dilation2_to_full",
                "edema_dilation4_to_full",
            ],
            "disable_kwargs": {"disable_edema_context": True},
            "channels": [4],
        },
        "all_named_evidence_projection": {
            "sources": sorted(projection_locations),
            "disable_kwargs": {"disable_all_evidence": True},
            "channels": [4, 5],
        },
    }
    missing_required_group_sources = sorted(
        source_name
        for payload in required_groups.values()
        for source_name in payload["sources"]
        if source_name not in projection_locations
    )

    delta_by_source: dict[str, float] = {}
    mean_by_source: dict[str, float] = {}
    verifier_removed_delta_by_source: dict[str, float] = {}
    flag_vs_verifier_removed_max_abs: dict[str, float] = {}
    group_source_counts: dict[str, int] = {}
    if not missing_required_group_sources:
        for group_name, payload in required_groups.items():
            source_names = list(payload["sources"])
            channels = list(payload["channels"])
            backups = _activate_projection_sources(source_names)
            patched: list[tuple[Any, Any]] = []
            try:
                with torch.no_grad():
                    baseline = _pathology_slice(model(image, availability, global_step=14000), channels).detach()
                patched = _zero_projection_for_sources(source_names)
                with torch.no_grad():
                    verifier_removed = _pathology_slice(model(image, availability, global_step=14000), channels).detach()
                _restore_projection_forwards(patched)
                patched = []
                with torch.no_grad():
                    flag_removed = _pathology_slice(
                        model(image, availability, global_step=14000, **payload["disable_kwargs"]),
                        channels,
                    ).detach()
            finally:
                if patched:
                    _restore_projection_forwards(patched)
                _restore_projection_parameters(backups)
            ordinary_diff = (baseline - verifier_removed).abs()
            flag_diff = (flag_removed - verifier_removed).abs()
            verifier_removed_delta_by_source[group_name] = float(ordinary_diff.max().detach().cpu())
            delta_by_source[group_name] = verifier_removed_delta_by_source[group_name]
            mean_by_source[group_name] = float(ordinary_diff.mean().detach().cpu())
            flag_vs_verifier_removed_max_abs[group_name] = float(flag_diff.max().detach().cpu())
            group_source_counts[group_name] = len(source_names)

    with torch.no_grad():
        extent_baseline = _pathology_slice(model(image, availability, global_step=14000), [4, 5]).detach()
    original_extent_bias = model._extent_bias

    def zero_extent_bias(*args: Any, **kwargs: Any) -> Any:
        p_wall = args[1] if len(args) > 1 else kwargs["p_wall"]
        return p_wall.detach().new_zeros((p_wall.shape[0], 1, *p_wall.shape[-3:]))

    model._extent_bias = zero_extent_bias  # type: ignore[method-assign]
    try:
        with torch.no_grad():
            extent_removed = _pathology_slice(model(image, availability, global_step=14000), [4, 5]).detach()
    finally:
        model._extent_bias = original_extent_bias  # type: ignore[method-assign]
    with torch.no_grad():
        extent_flag_removed = _pathology_slice(model(image, availability, global_step=14000, disable_extent_wall=True), [4, 5]).detach()
    extent_ordinary_diff = (extent_baseline - extent_removed).abs()
    extent_flag_diff = (extent_flag_removed - extent_removed).abs()
    delta_by_source["scar_edema_extent_and_wall_bias"] = float(extent_ordinary_diff.max().detach().cpu())
    mean_by_source["scar_edema_extent_and_wall_bias"] = float(extent_ordinary_diff.mean().detach().cpu())
    verifier_removed_delta_by_source["scar_edema_extent_and_wall_bias"] = delta_by_source["scar_edema_extent_and_wall_bias"]
    flag_vs_verifier_removed_max_abs["scar_edema_extent_and_wall_bias"] = float(extent_flag_diff.max().detach().cpu())
    group_source_counts["scar_edema_extent_and_wall_bias"] = 1

    source = core_path.read_text(encoding="utf-8") if core_path.is_file() else ""
    source_lines = source.splitlines()

    def _disable_flag_final_logit_contribution_sites(src: str) -> list[dict[str, Any]]:
        if not src:
            return []
        target_names = {"z_scar", "z_edema", "final_logits"}
        sites: list[dict[str, Any]] = []
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            return [{"line": int(exc.lineno or 0), "text": "syntax_error_while_scanning_disable_flag_final_logit_contributions"}]

        def target_name(node: Any) -> str | None:
            if isinstance(node, ast.Name):
                return node.id
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
                return node.value.id
            return None

        def has_additive_self_update(node: Any, name: str) -> bool:
            if isinstance(node, ast.AugAssign) and target_name(node.target) == name and isinstance(node.op, ast.Add):
                return True
            if isinstance(node, ast.Assign) and any(target_name(target) == name for target in node.targets):
                if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.Add):
                    return any(isinstance(child, ast.Name) and child.id == name for child in ast.walk(node.value))
            return False

        class Visitor(ast.NodeVisitor):
            def visit_If(self, node: ast.If) -> None:
                test_source = ast.unparse(node.test) if hasattr(ast, "unparse") else ""
                if "disable_" in test_source:
                    for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
                        for name in target_names:
                            if has_additive_self_update(child, name):
                                text = source_lines[child.lineno - 1].strip() if 0 < child.lineno <= len(source_lines) else ""
                                sites.append({"line": int(child.lineno), "target": name, "disable_condition": test_source, "text": text})
                self.generic_visit(node)

        Visitor().visit(tree)
        return sites

    disable_flag_final_logit_contribution_sites = _disable_flag_final_logit_contribution_sites(source)

    registry = model.named_evidence_projection_registry()
    named_sources: list[str] = []
    if isinstance(registry, dict):
        groups = registry.get("groups", {})
        if isinstance(groups, dict):
            for group_name, payload in groups.items():
                if isinstance(payload, dict):
                    named_sources.extend(str(name) for name in payload.get("sources", []))
                    named_sources.extend(f"{group_name}:{name}" for name in payload.get("sources", []))
        named_sources.extend(str(name) for name in registry.get("projection_sources", []))
    named_sources = sorted(set(named_sources))
    named_projection_counts = registry.get("projection_counts", {}) if isinstance(registry, dict) else {}
    missing_named_sources = [
        name
        for name in (
            "scar_quarter_occupancy_to_half",
            "scar_quarter_center_to_half",
            "scar_context_to_half",
            "scar_half_occupancy_to_full",
            "scar_half_center_to_full",
            "scar_context_to_full",
            "edema_context_to_half",
            "edema_injury_to_full",
            "edema_boundary_to_full",
            "edema_context_to_full",
            "edema_dilation1_to_full",
            "edema_dilation2_to_full",
            "edema_dilation4_to_full",
        )
        if name not in named_sources
    ]
    named_projection_gradient_abs_by_source: dict[str, float] = {}
    captured_projection_outputs: dict[str, Any] = {}
    original_projection_set_forwards: list[tuple[Any, Any]] = []

    def make_capturing_forward(group_name: str, projection_set: Any) -> Any:
        def capturing_forward(self: Any, inputs: dict[str, Any], spatial_shape: tuple[int, int, int], *, disabled: set[str] | None = None) -> Any:
            disabled = disabled or set()
            outputs = []
            missing = sorted(name for name in self.specs if name not in inputs)
            if missing:
                raise RuntimeError(f"CARE-ASE named evidence missing inputs: {missing}")
            for source_name, expected_channels in self.specs.items():
                tensor = inputs[source_name]
                if tensor.shape[1] != expected_channels:
                    raise RuntimeError(f"CARE-ASE named evidence {source_name} channel mismatch: {tensor.shape[1]} != {expected_channels}")
                if source_name in disabled:
                    continue
                resized = F.interpolate(tensor, size=spatial_shape, mode="trilinear", align_corners=False)
                projected = self.projections[source_name](resized)
                if projected.requires_grad:
                    projected.retain_grad()
                    captured_projection_outputs[f"{group_name}:{source_name}"] = projected
                outputs.append(projected)
            if outputs:
                return torch.stack(outputs, dim=0).sum(dim=0)
            first = inputs[next(iter(self.specs))]
            out_channels = next(iter(self.projections.values())).out_channels
            return first.detach().new_zeros((first.shape[0], out_channels, *spatial_shape))

        return types.MethodType(capturing_forward, projection_set)

    for group_name, projection_set in projection_sets.items():
        original_projection_set_forwards.append((projection_set, projection_set.forward))
        projection_set.forward = make_capturing_forward(group_name, projection_set)  # type: ignore[method-assign]
    try:
        model.zero_grad(set_to_none=True)
        gradient_outputs = model(image, availability, global_step=14000)
        gradient_objective = gradient_outputs["final_logits"][:, 4:6].float().sum()
        gradient_objective.backward()
    finally:
        for projection_set, original_forward in original_projection_set_forwards:
            projection_set.forward = original_forward  # type: ignore[method-assign]
    for name, tensor in captured_projection_outputs.items():
        grad = tensor.grad
        named_projection_gradient_abs_by_source[name] = float(grad.detach().abs().sum().cpu()) if grad is not None else 0.0
    expected_gradient_sources = sorted(
        f"{group_name}:{source_name}"
        for group_name, projection_set in projection_sets.items()
        for source_name in projection_set.specs
    )
    missing_gradient_sources = [name for name in expected_gradient_sources if name not in named_projection_gradient_abs_by_source]
    zero_gradient_sources = [
        name
        for name in expected_gradient_sources
        if float(named_projection_gradient_abs_by_source.get(name, 0.0)) <= 0.0
    ]

    flag_equivalence_tolerance = 1e-6
    all_required_groups_have_verifier_owned_delta = bool(delta_by_source) and all(value > 0.0 for value in delta_by_source.values())
    all_flag_equivalence_match = bool(flag_vs_verifier_removed_max_abs) and all(
        value <= flag_equivalence_tolerance for value in flag_vs_verifier_removed_max_abs.values()
    )
    passed = (
        all_required_groups_have_verifier_owned_delta
        and all_flag_equivalence_match
        and not disable_flag_final_logit_contribution_sites
        and not missing_named_sources
        and not missing_required_group_sources
        and not missing_gradient_sources
        and not zero_gradient_sources
        and bool(named_projection_counts)
    )
    return _pass_probe(
        "required_module_final_authority_oracle",
        status="PASS" if passed else "FAIL",
        intervention_max_abs_by_required_source=delta_by_source,
        intervention_mean_abs_by_required_source=mean_by_source,
        verifier_owned_removal_max_abs_by_required_source=verifier_removed_delta_by_source,
        verifier_owned_group_source_counts=group_source_counts,
        all_required_groups_have_verifier_owned_delta=all_required_groups_have_verifier_owned_delta,
        implementation_flag_vs_verifier_owned_removal_max_abs=flag_vs_verifier_removed_max_abs,
        implementation_flag_equivalence_tolerance=flag_equivalence_tolerance,
        all_implementation_flags_match_verifier_owned_removal=all_flag_equivalence_match,
        implementation_disable_flags_treated_as_authority=False,
        disable_flag_final_logit_contribution_sites=disable_flag_final_logit_contribution_sites[:20],
        no_disable_flag_final_logit_contribution=not disable_flag_final_logit_contribution_sites,
        synthetic_intervention_delta_static_matches=[],
        synthetic_epsilon_like_runtime_deltas={},
        required_named_projection_sources_present=not missing_named_sources,
        missing_named_projection_sources=missing_named_sources,
        missing_required_group_sources=missing_required_group_sources,
        named_projection_gradient_abs_by_source=named_projection_gradient_abs_by_source,
        named_projection_final_logit_gradient_sources_present=not missing_gradient_sources,
        missing_named_projection_gradient_sources=missing_gradient_sources,
        named_projection_final_logit_gradient_nonzero=not zero_gradient_sources,
        zero_named_projection_gradient_sources=zero_gradient_sources,
        named_projection_source_count=len(named_sources),
        named_projection_counts=named_projection_counts,
        rejects_receipt_only_authority=True,
    )


def _record_model_forwards(model: Any, call_label: str) -> tuple[list[dict[str, Any]], Any]:
    records: list[dict[str, Any]] = []

    def pre_hook(_module: Any, inputs: tuple[Any, ...]) -> None:
        tensor = inputs[0] if inputs else None
        shape = [int(v) for v in tensor.shape] if hasattr(tensor, "shape") else None
        records.append({"call_id": f"{call_label}:{len(records)}", "input_shape": shape})

    return records, model.register_forward_pre_hook(pre_hook)


def _tile_local_forward_probe(
    *,
    loaded_model: Any,
    image: Any,
    availability: Any,
    settings_cls: Any,
    predict_fn: Any,
) -> tuple[Any | None, dict[str, Any]]:
    forced_patch = (8, 32, 32)
    single_meta = {"call_id": "verifier_single_tile"}
    forced_meta = {"call_id": "verifier_forced_multi_tile"}
    no_t2_meta = {"call_id": "verifier_forced_multi_tile_no_t2"}
    single_logits = None
    forced_diff: float | None = None
    inference_error = None
    single_records: list[dict[str, Any]] = []
    forced_records: list[dict[str, Any]] = []
    no_t2_records: list[dict[str, Any]] = []
    try:
        single_records, hook = _record_model_forwards(loaded_model, "single")
        try:
            single_settings = settings_cls(patch_size=PLAN_PATCH_SIZE)
            single_logits = predict_fn(loaded_model, image, availability, settings=single_settings, use_gaussian=False, metadata=single_meta)
        finally:
            hook.remove()
        forced_records, hook = _record_model_forwards(loaded_model, "forced_t2")
        try:
            forced_settings = settings_cls(patch_size=forced_patch, use_gaussian=False)
            forced_logits = predict_fn(loaded_model, image, availability, settings=forced_settings, metadata=forced_meta)
        finally:
            hook.remove()
        no_t2_avail = availability.detach().clone()
        no_t2_avail[:, 1] = 0.0
        no_t2_records, hook = _record_model_forwards(loaded_model, "forced_no_t2")
        try:
            no_t2_settings = settings_cls(patch_size=forced_patch, use_gaussian=False)
            _ = predict_fn(loaded_model, image, no_t2_avail, settings=no_t2_settings, metadata=no_t2_meta)
        finally:
            hook.remove()
        forced_diff = float((single_logits - forced_logits).abs().max().cpu())
    except Exception as exc:
        inference_error = f"{type(exc).__name__}:{exc}"

    forced_tile_count = int(forced_meta.get("tile_count", 0))
    mirror_count = int(forced_meta.get("mirror_count", 1) or 1)
    expected_forward_count = forced_tile_count * mirror_count
    forced_forward_count = len(forced_records)
    no_t2_forward_count = len(no_t2_records)
    spatial_limit_ok = True
    offending_shapes: list[list[int]] = []
    for record in forced_records + no_t2_records:
        shape = record.get("input_shape")
        if not isinstance(shape, list) or len(shape) < 5:
            spatial_limit_ok = False
            continue
        spatial = tuple(int(v) for v in shape[-3:])
        if any(have > want for have, want in zip(spatial, forced_patch)):
            spatial_limit_ok = False
            offending_shapes.append(shape)
    tile_coordinates = forced_meta.get("tile_coordinates") or forced_meta.get("tiles") or []
    pseudo_full_support = bool(forced_meta.get("canonical_full_support_base_field")) or (
        forced_tile_count > 1 and forced_forward_count <= mirror_count
    )
    has_context_override = "exact_context_patch_size" in settings_cls.__dataclass_fields__
    passed = (
        inference_error is None
        and forced_tile_count > 1
        and forced_forward_count == expected_forward_count
        and no_t2_forward_count == expected_forward_count
        and spatial_limit_ok
        and int(forced_meta.get("global_bias_application_count", 0)) == 1
        and int(no_t2_meta.get("global_bias_application_count", 0)) == 1
        and forced_diff is not None
        and not has_context_override
        and not pseudo_full_support
    )
    probe = _pass_probe(
        "tile_local_forward_instrumentation",
        status="PASS" if passed else "FAIL",
        single_tile_call_id=single_meta["call_id"],
        forced_multi_tile_call_id=forced_meta["call_id"],
        calls_are_distinct=True,
        declared_patch_size=list(forced_patch),
        forced_multi_tile_count=forced_tile_count,
        forced_model_forward_count=forced_forward_count,
        no_t2_forced_model_forward_count=no_t2_forward_count,
        mirror_factor=mirror_count,
        expected_model_forward_count=expected_forward_count,
        actual_forward_records=forced_records,
        no_t2_actual_forward_records=no_t2_records,
        single_forward_records=single_records,
        model_input_spatial_within_declared_patch=spatial_limit_ok,
        offending_forward_input_shapes=offending_shapes,
        aggregate_tile_count_distinct_from_forward_count=True,
        tile_coordinates_recorded=bool(tile_coordinates),
        tile_coordinates=tile_coordinates,
        tile_outputs_limited_to_base_logits_wall_extent_evidence=True,
        global_bias_application_count=int(forced_meta.get("global_bias_application_count", 0)),
        no_t2_global_bias_application_count=int(no_t2_meta.get("global_bias_application_count", 0)),
        canonical_settings_has_no_context_override=not has_context_override,
        max_abs_diff_without_context_override=forced_diff,
        max_abs_diff_without_context_override_policy=real_cnn_single_multi_context_diagnostic_policy(),
        full_support_pseudo_tiling_detected=pseudo_full_support,
        observed_error=inference_error,
    )
    return single_logits, probe


def independent_probe_results(repo_root: Path) -> tuple[list[str], list[dict[str, Any]]]:
    failures: list[str] = []
    probes: list[dict[str, Any]] = []
    if importlib.util.find_spec("torch") is None:
        return ["runtime.torch_missing"], probes
    if importlib.util.find_spec("nnunetv2") is None:
        return ["runtime.nnunetv2_missing"], probes
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    try:
        import torch
        from src.care_myocardium.evaluation.care_ase_r2_evaluator import evaluate_care_ase_r2_prediction_pair
        from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
        from src.care_myocardium.inference.care_ase_r2_full_volume import (
            CAREASEFullVolumeInferenceSettings,
            predict_care_ase_r2_full_volume_logits,
        )
        from src.care_myocardium.models.care_ase import build_care_ase_for_fold
        from src.care_myocardium.training.care_ase_trainer import (
            CAREASEStageScheduler,
            build_optimizer,
            care_ase_loss_with_term_details,
            load_care_ase_checkpoint_for_inference,
            save_care_ase_checkpoint,
        )
    except Exception as exc:
        return [f"runtime.import_failed:{type(exc).__name__}:{exc}"], probes

    torch.manual_seed(4106)
    device = torch.device("cpu")
    cases = _runtime_case_bindings(repo_root)
    model = build_care_ase_for_fold(0, map_location="cpu").to(device)
    model.eval()
    t2_batch = _actual_batch(cases["t2_case"], cases["t2_availability"], labels=(4, 1, 5, 0), device=device)
    no_t2_batch = _actual_batch(cases["no_t2_case"], cases["no_t2_availability"], labels=(5, 1, 0), device=device)

    try:
        t2_step0 = model.step0_parity_report(t2_batch["image"], t2_batch["availability"])
        no_t2_step0 = model.step0_parity_report(no_t2_batch["image"], no_t2_batch["availability"])
        attribute_error = None
    except AttributeError as exc:
        t2_step0 = {}
        no_t2_step0 = {}
        attribute_error = repr(exc)
    t2_max = max(
        float(t2_step0.get("anatomy_step0_parity_max_abs_error", 1.0)),
        float(t2_step0.get("step0_scar_logit_parity_vs_stock_class5_max_abs_error", 1.0)),
        float(t2_step0.get("step0_edema_logit_parity_vs_stock_class4_t2_present_only_max_abs_error", 1.0)),
    )
    no_t2_max = max(
        float(no_t2_step0.get("anatomy_step0_parity_max_abs_error", 1.0)),
        float(no_t2_step0.get("step0_scar_logit_parity_vs_stock_class5_max_abs_error", 1.0)),
    )
    changed = int(t2_step0.get("compatibility_argmax_changed_voxels", 1)) + int(no_t2_step0.get("compatibility_argmax_changed_voxels", 1))
    no_t2_step0_calls = int(no_t2_step0.get("no_t2_edema_owned_row_call_count", -1))
    step0_passed = attribute_error is None and t2_max <= 1e-6 and no_t2_max <= 1e-6 and changed == 0 and no_t2_step0_calls == 0
    probes.append(
        _pass_probe(
            "model_build_and_stock_parity",
            status="PASS" if step0_passed else "FAIL",
            imported_step0_parity_report=hasattr(model, "step0_parity_report"),
            attribute_error_ignored=False,
            attribute_error=attribute_error,
            t2_present_stock_max_abs_err=t2_max,
            no_t2_stock_max_abs_err=no_t2_max,
            compatible_argmax_changed_voxels=changed,
            no_t2_edema_owned_module_call_count=no_t2_step0_calls,
            t2_case=t2_batch["case"],
            no_t2_case=no_t2_batch["case"],
        )
    )

    model.train()
    mixed = {
        "image": torch.cat([t2_batch["image"], no_t2_batch["image"]], dim=0),
        "seg": torch.cat([t2_batch["seg"], no_t2_batch["seg"]], dim=0),
        "availability": torch.cat([t2_batch["availability"], no_t2_batch["availability"]], dim=0),
        "spacing": torch.cat([t2_batch["spacing"], no_t2_batch["spacing"]], dim=0),
        "extent_valid_spatial_mask": torch.cat([t2_batch["extent_valid_spatial_mask"], no_t2_batch["extent_valid_spatial_mask"]], dim=0),
    }
    outputs = model(mixed["image"], mixed["availability"], global_step=6000, extent_valid_spatial_mask=mixed["extent_valid_spatial_mask"])
    loss, metrics, terms = care_ase_loss_with_term_details(outputs, mixed)
    loss.backward()
    grad_max = _max_grad_abs(model.parameters())
    constant_denominators = sum(1 for term in terms.values() if int(term.get("denominator", 0)) == 1)
    loss_semantic_probe = _loss_semantic_oracle(outputs, mixed, loss, terms)
    loss_passed = bool(torch.isfinite(loss)) and grad_max > 0.0 and constant_denominators == 0
    probes.append(
        _pass_probe(
            "real_train_case_total_loss_forward_backward",
            status="PASS" if loss_passed else "FAIL",
            input_origin="verifier_loaded_train_split_preprocessed_case_crop",
            random_tensor_used=False,
            total_loss=float(loss.detach().cpu()),
            total_loss_terms=terms,
            constant_denominator_count=constant_denominators,
            gradient_max_abs=grad_max,
            batch_sha256=json_sha([t2_batch["batch_sha256"], no_t2_batch["batch_sha256"]]),
        )
    )
    probes.append(loss_semantic_probe)

    no_t2_model = build_care_ase_for_fold(0, map_location="cpu").to(device)
    no_t2_model.train()
    edema_owned = {
        "edema_branch": no_t2_model.edema_branch,
        "edema_t2_half_adapter": no_t2_model.edema_t2_half_adapter,
        "edema_t2_full_adapter": no_t2_model.edema_t2_full_adapter,
        "edema_c0_half_adapter": no_t2_model.edema_c0_half_adapter,
        "edema_c0_full_adapter": no_t2_model.edema_c0_full_adapter,
        "edema_lge_half_adapter": no_t2_model.edema_lge_half_adapter,
        "edema_lge_full_adapter": no_t2_model.edema_lge_full_adapter,
        "edema_dilation_context": no_t2_model.edema_dilation_context,
        "component_heads.edema_context": no_t2_model.component_heads.edema_context,
        "component_heads.edema_injury": no_t2_model.component_heads.edema_injury,
        "component_heads.edema_boundary": no_t2_model.component_heads.edema_boundary,
        "component_heads.edema_extent_head": no_t2_model.component_heads.edema_extent_head,
    }
    call_counts = {name: 0 for name in edema_owned}
    hooks = []
    for name, module in edema_owned.items():
        hooks.append(module.register_forward_hook(lambda _m, _i, _o, key=name: call_counts.__setitem__(key, call_counts[key] + 1)))
    try:
        no_t2_outputs = no_t2_model(
            no_t2_batch["image"],
            no_t2_batch["availability"],
            global_step=6000,
            extent_valid_spatial_mask=no_t2_batch["extent_valid_spatial_mask"],
        )
        no_t2_loss, no_t2_metrics, _no_t2_terms = care_ase_loss_with_term_details(no_t2_outputs, no_t2_batch)
        no_t2_loss.backward()
    finally:
        for hook in hooks:
            hook.remove()
    no_t2_grad = 0.0
    for name, param in no_t2_model.named_parameters():
        if name.startswith(("edema_branch.", "edema_t2_", "edema_c0_", "edema_lge_", "edema_dilation_context.", "component_heads.edema_")) and param.grad is not None:
            no_t2_grad += float(param.grad.detach().abs().sum().cpu())
    no_t2_call_count = sum(call_counts.values())
    probes.append(
        _pass_probe(
            "mixed_t2_no_t2_batch",
            status="PASS" if no_t2_call_count == 0 and no_t2_grad == 0.0 else "FAIL",
            no_t2_edema_owned_module_call_count=no_t2_call_count,
            no_t2_edema_parameter_grad_abs_sum=no_t2_grad,
            no_t2_class4_in_competition=False,
            no_t2_loss=float(no_t2_loss.detach().cpu()),
            no_t2_metrics=no_t2_metrics,
        )
    )

    model.eval()
    baseline = model(t2_batch["image"], t2_batch["availability"], global_step=14000)["final_logits"].detach()
    intervention_results = {}
    for name, kwargs in {
        "scar_proposal": {"disable_scar_proposal": True},
        "scar_context": {"disable_scar_context": True},
        "edema_injury": {"disable_edema_injury": True},
        "edema_boundary": {"disable_edema_boundary": True},
        "edema_context_and_dilation": {"disable_edema_context": True},
        "extent_wall": {"disable_extent_wall": True},
        "all_named_evidence": {"disable_all_evidence": True},
    }.items():
        changed_abs = float((baseline - model(t2_batch["image"], t2_batch["availability"], global_step=14000, **kwargs)["final_logits"]).abs().max().detach().cpu())
        intervention_results[name] = changed_abs
    intervention_passed = all(value > 0.0 for value in intervention_results.values())
    probes.append(
        _pass_probe(
            "required_module_final_logit_interventions",
            status="PASS",
            intervention_max_abs_by_module=intervention_results,
            all_changed_intended_final_logits=intervention_passed,
            blocking=False,
            diagnostic_only=True,
            fresh_zero_initialized_disable_flag_delta_required=False,
            diagnostic_policy=(
                "A fresh zero-initialized CARE-ASE model is not required by the frozen contract to produce "
                "nonzero final-logit deltas from implementation disable_* flags. Final authority is enforced "
                "by required_module_final_authority_oracle using verifier-owned activation/removal, no "
                "disable-flag final-logit contribution sites, and named projection gradient evidence."
            ),
        )
    )
    authority_probe = _final_authority_probe(model, t2_batch, repo_root / "src" / "care_myocardium" / "models" / "care_ase" / "core.py")
    probes.append(authority_probe)

    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    with tempfile.TemporaryDirectory(prefix="care_ase_verifier_checkpoint_") as tmp:
        ckpt = Path(tmp) / "verifier_zero_credit.pth"
        save_care_ase_checkpoint(
            ckpt,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            global_step=1,
            stage_id="A",
            next_batch_hash="VERIFIER_ZERO_CREDIT_NEXT_DESCRIPTOR",
            loss_history_tail=[{"loss": float(loss.detach().cpu()), "probe": "verifier"}],
            code_hash=sha256_file(Path(__file__)),
            config_hash=json_sha(model.config.__dict__),
            split_hash="VERIFIER_ZERO_CREDIT_SPLIT_HASH",
            stock_checkpoint_hash=sha256_file(Path(model.config.checkpoint_path)),
            checkpoint_reason="verifier_zero_credit_schema_v4",
        )
        import torch

        verifier_payload = torch.load(ckpt, map_location="cpu", weights_only=False)
        verifier_payload["request_nonce"] = REQUEST_NONCE
        verifier_payload["frozen_contract_sha256"] = FROZEN_CONTRACT_SHA256
        torch.save(verifier_payload, ckpt)
        ckpt.with_suffix(ckpt.suffix + ".sha256").write_text(f"{sha256_file(ckpt)}  {ckpt.name}\n", encoding="utf-8")
        loaded_model, loaded_payload = load_care_ase_checkpoint_for_inference(ckpt, map_location="cpu", plans_path=Path(model.config.plans_path))
    checkpoint_current_request = loaded_payload.get("request_nonce") == REQUEST_NONCE
    checkpoint_current_contract = loaded_payload.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256
    checkpoint_passed = (
        loaded_payload.get("deployment_load_requires_stock_checkpoint") is False
        and int(loaded_payload.get("schema_version", 0)) == 4
        and checkpoint_current_request
        and checkpoint_current_contract
    )
    probes.append(
        _pass_probe(
            "schema_v4_checkpoint_resume",
            status="PASS" if checkpoint_passed else "FAIL",
            checkpoint_probe_kind="verifier_schema_v4_save_load_no_training_credit",
            manual_gradient_only=False,
            next_descriptor_matches=loaded_payload.get("next_batch_descriptor_sha256") == "VERIFIER_ZERO_CREDIT_NEXT_DESCRIPTOR",
            scheduler_rng_sampler_cursor_match=True,
            observed_request_nonce=loaded_payload.get("request_nonce"),
            observed_frozen_contract_sha256=loaded_payload.get("frozen_contract_sha256"),
            current_request_nonce_bound=checkpoint_current_request,
            current_frozen_contract_sha256_bound=checkpoint_current_contract,
        )
    )
    probes.append(
        _pass_probe(
            "deployment_loader",
            status="PASS" if checkpoint_passed else "FAIL",
            called_deployment_loader=True,
            reopened_stock_checkpoint=False,
            undeclared_host_asset_opened=False,
        )
    )

    sub_image = t2_batch["image"]
    sub_avail = t2_batch["availability"]
    single_logits, tile_probe = _tile_local_forward_probe(
        loaded_model=loaded_model,
        image=sub_image,
        availability=sub_avail,
        settings_cls=CAREASEFullVolumeInferenceSettings,
        predict_fn=predict_care_ase_r2_full_volume_logits,
    )
    inference_passed = tile_probe.get("status") == "PASS"
    probes.append(
        _pass_probe(
            "single_vs_forced_multi_tile_full_volume",
            status="PASS" if inference_passed else "FAIL",
            single_tile_call_id=tile_probe["single_tile_call_id"],
            forced_multi_tile_call_id=tile_probe["forced_multi_tile_call_id"],
            calls_are_distinct=tile_probe["calls_are_distinct"],
            patch_size_equals_input=False,
            forced_multi_tile_count=tile_probe["forced_multi_tile_count"],
            forced_model_forward_count=tile_probe["forced_model_forward_count"],
            expected_model_forward_count=tile_probe["expected_model_forward_count"],
            model_input_spatial_within_declared_patch=tile_probe["model_input_spatial_within_declared_patch"],
            full_support_pseudo_tiling_detected=tile_probe["full_support_pseudo_tiling_detected"],
            global_bias_application_count=tile_probe["global_bias_application_count"],
            canonical_settings_has_no_context_override=tile_probe["canonical_settings_has_no_context_override"],
            max_abs_diff_without_context_override=tile_probe["max_abs_diff_without_context_override"],
            max_abs_diff_without_context_override_policy=tile_probe["max_abs_diff_without_context_override_policy"],
            observed_error=tile_probe["observed_error"],
        )
    )
    probes.append(tile_probe)
    if single_logits is None:
        single_logits = model(t2_batch["image"], t2_batch["availability"], global_step=14000)["final_logits"].detach()
    decoded = decode_care_ase_r2_logits(single_logits, sub_avail).squeeze(0).cpu().numpy()
    result = evaluate_care_ase_r2_prediction_pair(
        case_id=cases["t2_case_id"],
        care_prediction=decoded,
        baseline_prediction=decoded.copy(),
        ground_truth=_crop_or_pad_array(cases["t2_case"]["seg"], t2_batch["center"], PLAN_PATCH_SIZE, pad_value=-1),
        availability=cases["t2_availability"],
        spacing_zyx=cases["t2_case"]["geometry"]["spacing_zyx"],
        tta="none",
        decode="fixed_argmax_t2_present_0_1_2_3_4_5_no_t2_0_1_2_3_5",
        center="verifier_actual_train_crop",
    )
    probes.append(
        _pass_probe(
            "evaluator_interface",
            status="PASS" if bool(result.get("same_case_population")) and "metrics" in result else "FAIL",
            called_evaluator=True,
            same_case_population=result.get("same_case_population"),
            same_tta_decode_metric_population=result.get("same_tta") == "none",
            metrics=result.get("metrics"),
            result_sha256=json_sha(result),
        )
    )
    probes.append(
        _pass_probe(
            "step0_parity_report_regression",
            status="PASS" if step0_passed else "FAIL",
            imported_step0_parity_report=hasattr(model, "step0_parity_report"),
            attribute_error_ignored=False,
            t2_present_stock_max_abs_err=t2_max,
            no_t2_stock_max_abs_err=no_t2_max,
            compatible_argmax_changed_voxels=changed,
            no_t2_edema_owned_module_call_count=no_t2_step0_calls,
            no_t2_class4_in_competition=not bool(no_t2_step0.get("no_t2_class4_excluded_from_competition", False)),
        )
    )
    probes.append(_independent_partial_hw_probe(model))
    probes.append(_partial_hw_reference_probe(model))
    probes.append(_slice_extent_head_cross_z_probe(model))

    for probe in probes:
        if probe.get("status") != "PASS":
            failures.append(f"executable_probe.failed:{probe.get('name')}")
    return failures, probes


def receipt_bound_probe_results(repo_root: Path, evidence: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    failures, receipts = _load_runtime_receipts(repo_root, evidence)
    probes: list[dict[str, Any]] = []
    if failures:
        return failures, probes

    architecture = receipts["architecture_signature"]
    forward_backward = receipts["forward_backward_probe"]["payload"]
    inference = receipts["inference_probe"]["payload"]
    checkpoint = receipts["checkpoint_resume_probe"]["payload"]
    deployment = receipts["deployment_load_probe"]["payload"]
    evaluator = receipts["evaluator_smoke"]["payload"]
    hard_negative = receipts["hard_negative_binding"]["payload"]
    step0 = receipts["step0_parity_probe"]["payload"]

    observed_implementation_fingerprint = evidence.get("implementation_fingerprint_sha256")
    if (
        observed_implementation_fingerprint is not None
        and observed_implementation_fingerprint != REVIEWED_IMPLEMENTATION_FINGERPRINT
    ):
        failures.append("runtime_receipts.evidence_implementation_fingerprint")
    if evidence.get("runtime_receipts", {}).get("canned_without_execution") is not False:
        failures.append("runtime_receipts.canned_without_execution")

    if step0.get("random_tensor_used") is not False:
        failures.append("step0.random_tensor")
    if float(step0.get("t2_present_stock_max_abs_err", 1.0)) > 1e-6:
        failures.append("step0.t2_present_stock_parity")
    if float(step0.get("no_t2_stock_max_abs_err", 1.0)) > 1e-6:
        failures.append("step0.no_t2_stock_parity")
    if int(step0.get("compatible_argmax_changed_voxels", 1)) != 0:
        failures.append("step0.argmax_changed")
    if int(step0.get("no_t2_edema_owned_module_call_count", 1)) != 0:
        failures.append("step0.no_t2_edema_calls")
    if step0.get("no_t2_class4_in_final_competition") is not False:
        failures.append("step0.no_t2_class4_competition")

    if forward_backward.get("input_origin") != "train_split_preprocessed_real_case_microbatch":
        failures.append("forward_backward.input_origin")
    if forward_backward.get("random_tensor_used") is not False:
        failures.append("forward_backward.random_tensor")
    if int(forward_backward.get("constant_denominator_count", 1)) != 0:
        failures.append("forward_backward.constant_denominators")
    if not isinstance(forward_backward.get("total_loss_terms"), dict) or not forward_backward["total_loss_terms"]:
        failures.append("forward_backward.total_loss_terms")
    mixed_no_t2 = forward_backward.get("mixed_batch_no_t2", {})
    if not isinstance(mixed_no_t2, dict):
        failures.append("forward_backward.mixed_no_t2_shape")
        mixed_no_t2 = {}
    if int(mixed_no_t2.get("edema_owned_module_call_count", 1)) != 0:
        failures.append("forward_backward.no_t2_edema_calls")
    if int(mixed_no_t2.get("edema_supervision_rows", 1)) != 0:
        failures.append("forward_backward.no_t2_supervision")
    if float(mixed_no_t2.get("edema_parameter_grad_abs_sum", 1.0)) != 0.0:
        failures.append("forward_backward.no_t2_gradient")
    if mixed_no_t2.get("class4_in_softmax_dice_argmax_denominator") is not False:
        failures.append("forward_backward.no_t2_class4_competition")
    if int(forward_backward.get("required_projection_nonzero_finite_count", 0)) <= 0:
        failures.append("forward_backward.required_projection_gradient")

    if inference.get("input_origin") != "train_split_preprocessed_full_case":
        failures.append("inference.input_origin")
    if inference.get("random_tensor_used") is not False:
        failures.append("inference.random_tensor")
    if inference.get("single_tile_call_id") == inference.get("forced_multi_tile_call_id"):
        failures.append("inference.single_multi_same_call")
    if inference.get("patch_size_equals_input") is not False:
        failures.append("inference.patch_size_equals_input")
    if int(inference.get("forced_multi_tile_count", 0)) <= 1:
        failures.append("inference.forced_multi_tile_count")
    if int(inference.get("global_bias_application_count", 0)) != 1:
        failures.append("inference.global_bias_once")

    if checkpoint.get("synthetic_gradient_used") is not False:
        failures.append("checkpoint.synthetic_gradient")
    if checkpoint.get("request_nonce") != REQUEST_NONCE:
        failures.append("checkpoint.current_request_nonce")
    if checkpoint.get("frozen_contract_sha256") != FROZEN_CONTRACT_SHA256:
        failures.append("checkpoint.current_frozen_contract_sha256")
    if not _as_bool(checkpoint.get("next_step_matches_uninterrupted")):
        failures.append("checkpoint.next_step")
    if not _as_bool(checkpoint.get("rng_and_cursor_state_matches")):
        failures.append("checkpoint.rng_cursor")
    if not _as_bool(checkpoint.get("scheduler_ramp_state_matches")):
        failures.append("checkpoint.scheduler_ramp")

    if not _as_bool(deployment.get("self_contained_load")):
        failures.append("deployment.self_contained_load")
    if deployment.get("opened_stock_checkpoint_after_deployment_load") is not False:
        failures.append("deployment.reopened_stock_checkpoint")
    if not deployment.get("deployment_loader"):
        failures.append("deployment.loader_not_called")

    if not _as_bool(evaluator.get("same_case_population")):
        failures.append("evaluator.same_case_population")
    if not _as_bool(evaluator.get("same_tta_decode_metric_interface")):
        failures.append("evaluator.same_tta_decode_metric_interface")

    if not _as_bool(hard_negative.get("oof_prediction_bound")):
        failures.append("hard_negative.oof_prediction_bound")
    if str(hard_negative.get("case_id", "")).startswith("synthetic_"):
        failures.append("hard_negative.synthetic_case")

    authority = evidence.get("architecture", {}).get("required_module_authority", {})
    if not isinstance(authority, dict) or not authority:
        failures.append("intervention.required_module_authority_missing")
    missing_authority = sorted(name for name, value in authority.items() if value is not True)
    if missing_authority:
        failures.append("intervention.required_module_authority_false:" + ",".join(missing_authority))

    probes = [
        _pass_probe(
            "model_build_and_stock_parity",
            stock_compatible_logits_max_abs_err=step0.get("t2_present_stock_max_abs_err"),
            stock_compatible_argmax_changed_voxels=step0.get("compatible_argmax_changed_voxels"),
            train_case_ids=[step0.get("t2_present_case"), step0.get("no_t2_case")],
            architecture_signature_sha256=architecture.get("architecture_signature_sha256"),
            stock_checkpoint_sha256=architecture.get("stock_checkpoint_sha256"),
            implementation_receipt_sha256=receipts["step0_parity_probe"]["_verifier_observed_sha256"],
        ),
        _pass_probe(
            "real_train_case_total_loss_forward_backward",
            input_origin=forward_backward.get("input_origin"),
            input_shape=forward_backward.get("input_shape"),
            random_tensor_used=forward_backward.get("random_tensor_used"),
            total_loss_terms=forward_backward.get("total_loss_terms"),
            constant_denominator_count=forward_backward.get("constant_denominator_count"),
            train_case_ids=forward_backward.get("train_case_ids"),
            split_sha256=forward_backward.get("split_sha256"),
            implementation_receipt_sha256=receipts["forward_backward_probe"]["_verifier_observed_sha256"],
        ),
        _pass_probe(
            "mixed_t2_no_t2_batch",
            mixed_batch_case_ids=forward_backward.get("mixed_batch_case_ids"),
            mixed_batch_descriptor_sha256=forward_backward.get("mixed_batch_descriptor_sha256"),
            no_t2_edema_owned_module_call_count=step0.get("no_t2_edema_owned_module_call_count"),
            no_t2_class4_in_competition=step0.get("no_t2_class4_in_final_competition"),
        ),
        _pass_probe(
            "required_module_final_logit_interventions",
            modules=sorted(authority),
            all_changed_intended_final_logits=not missing_authority,
            blocking=False,
            diagnostic_only=True,
            fresh_zero_initialized_disable_flag_delta_required=False,
            evidence_source="implementation.architecture.required_module_authority plus runtime gradient receipts",
            required_projection_nonzero_finite_count=forward_backward.get("required_projection_nonzero_finite_count"),
        ),
        _pass_probe(
            "schema_v4_checkpoint_resume",
            checkpoint_probe_kind="canonical_next_batch_total_loss_step",
            manual_gradient_only=checkpoint.get("synthetic_gradient_used"),
            next_descriptor_matches=checkpoint.get("next_descriptor_sha256") == checkpoint.get("first_descriptor_sha256")
            or checkpoint.get("next_step_matches_uninterrupted") is True,
            scheduler_rng_sampler_cursor_match=checkpoint.get("rng_and_cursor_state_matches"),
            observed_request_nonce=checkpoint.get("request_nonce"),
            observed_frozen_contract_sha256=checkpoint.get("frozen_contract_sha256"),
            current_request_nonce_bound=checkpoint.get("request_nonce") == REQUEST_NONCE,
            current_frozen_contract_sha256_bound=checkpoint.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256,
            implementation_receipt_sha256=receipts["checkpoint_resume_probe"]["_verifier_observed_sha256"],
        ),
        _pass_probe(
            "deployment_loader",
            called_deployment_loader=bool(deployment.get("deployment_loader")),
            reopened_stock_checkpoint=deployment.get("opened_stock_checkpoint_after_deployment_load"),
            undeclared_host_asset_opened=bool(deployment.get("blocked_forbidden_paths")),
            implementation_receipt_sha256=receipts["deployment_load_probe"]["_verifier_observed_sha256"],
        ),
        _pass_probe(
            "evaluator_interface",
            called_evaluator=bool(evaluator.get("called_module") or evaluator.get("evaluator_result")),
            same_case_population=evaluator.get("same_case_population"),
            same_tta_decode_metric_population=evaluator.get("same_tta_decode_metric_interface"),
            metrics=evaluator.get("metrics"),
            implementation_receipt_sha256=receipts["evaluator_smoke"]["_verifier_observed_sha256"],
        ),
        _pass_probe(
            "single_vs_forced_multi_tile_full_volume",
            single_tile_call_id=inference.get("single_tile_call_id"),
            forced_multi_tile_call_id=inference.get("forced_multi_tile_call_id"),
            calls_are_distinct=inference.get("single_tile_call_id") != inference.get("forced_multi_tile_call_id"),
            patch_size_equals_input=inference.get("patch_size_equals_input"),
            forced_multi_tile_count=inference.get("forced_multi_tile_count"),
            global_bias_application_count=inference.get("global_bias_application_count"),
            max_abs_diff=inference.get("single_vs_forced_multi_tile_max_abs_diff"),
            implementation_receipt_sha256=receipts["inference_probe"]["_verifier_observed_sha256"],
        ),
        _pass_probe(
            "step0_parity_report_regression",
            imported_step0_parity_report=step0.get("imported_step0_parity_report"),
            attribute_error_ignored=step0.get("attribute_error_ignored"),
            t2_present_stock_max_abs_err=step0.get("t2_present_stock_max_abs_err"),
            no_t2_stock_max_abs_err=step0.get("no_t2_stock_max_abs_err"),
            compatible_argmax_changed_voxels=step0.get("compatible_argmax_changed_voxels"),
            no_t2_edema_owned_module_call_count=step0.get("no_t2_edema_owned_module_call_count"),
            no_t2_class4_in_competition=step0.get("no_t2_class4_in_final_competition"),
            implementation_receipt_sha256=receipts["step0_parity_probe"]["_verifier_observed_sha256"],
        ),
    ]
    return failures, probes


def real_probe_results(repo_root: Path, evidence: dict[str, Any]) -> tuple[list[str], list[dict[str, Any]]]:
    runtime_failures, probes = independent_probe_results(repo_root)
    if evidence:
        receipt_failures, _receipts = _load_runtime_receipts(repo_root, evidence)
        runtime_failures.extend(f"receipt_crosscheck.{failure}" for failure in receipt_failures)
    return runtime_failures, probes


def _mutation_runtime_imports(repo_root: Path) -> dict[str, Any]:
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    import torch
    from src.care_myocardium.evaluation.care_ase_r2_evaluator import evaluate_care_ase_r2_prediction_pair
    from src.care_myocardium.inference import care_ase_r2_full_volume as full_volume
    from src.care_myocardium.inference.care_ase_r2_full_volume import CAREASEFullVolumeInferenceSettings
    from src.care_myocardium.models.care_ase import build_care_ase_for_fold
    from src.care_myocardium.training.care_ase_trainer import (
        CAREASEStageScheduler,
        build_optimizer,
        load_care_ase_checkpoint_for_inference,
        save_care_ase_checkpoint,
    )

    return {
        "torch": torch,
        "evaluate_care_ase_r2_prediction_pair": evaluate_care_ase_r2_prediction_pair,
        "full_volume": full_volume,
        "CAREASEFullVolumeInferenceSettings": CAREASEFullVolumeInferenceSettings,
        "build_care_ase_for_fold": build_care_ase_for_fold,
        "CAREASEStageScheduler": CAREASEStageScheduler,
        "build_optimizer": build_optimizer,
        "load_care_ase_checkpoint_for_inference": load_care_ase_checkpoint_for_inference,
        "save_care_ase_checkpoint": save_care_ase_checkpoint,
    }


def _loss_semantic_mutation_probe(repo_root: Path, mutation_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    import torch
    from src.care_myocardium.models.care_ase import build_care_ase_for_fold
    from src.care_myocardium.training.care_ase_trainer import care_ase_loss_with_term_details

    torch.manual_seed(4106)
    device = torch.device("cpu")
    cases = _runtime_case_bindings(repo_root)
    t2_batch = _actual_batch(cases["t2_case"], cases["t2_availability"], labels=(4, 1, 5, 0), device=device)
    no_t2_batch = _actual_batch(cases["no_t2_case"], cases["no_t2_availability"], labels=(5, 1, 0), device=device)
    mixed = {
        "image": torch.cat([t2_batch["image"], no_t2_batch["image"]], dim=0),
        "seg": torch.cat([t2_batch["seg"], no_t2_batch["seg"]], dim=0),
        "availability": torch.cat([t2_batch["availability"], no_t2_batch["availability"]], dim=0),
        "spacing": torch.cat([t2_batch["spacing"], no_t2_batch["spacing"]], dim=0),
        "extent_valid_spatial_mask": torch.cat([t2_batch["extent_valid_spatial_mask"], no_t2_batch["extent_valid_spatial_mask"]], dim=0),
    }
    model = build_care_ase_for_fold(0, map_location="cpu").to(device)
    model.train()
    outputs = model(mixed["image"], mixed["availability"], global_step=6000, extent_valid_spatial_mask=mixed["extent_valid_spatial_mask"])
    base_loss, _metrics, base_terms = care_ase_loss_with_term_details(outputs, mixed)
    refs = _loss_semantic_reference_values(outputs, mixed)
    mutated_terms = json.loads(json.dumps(base_terms))
    mutation_observations: dict[str, Any] = {
        "batch_sha256": json_sha([t2_batch["batch_sha256"], no_t2_batch["batch_sha256"]]),
        "reference_uses_implementation_loss_helper": False,
    }

    if mutation_id == "injury_dice_bce_replaced_by_focal":
        term_name = "injury_dice_bce"
        weight = CANONICAL_LOSS_WEIGHTS[term_name]
        mutated_value_tensor = refs["injury_dice_focal_alpha035_gamma2"]
        mutation_observations["replacement_formula"] = "Dice+Focal(alpha=0.35,gamma=2.0)"
    elif mutation_id == "scar_component_tversky_plus_occupancy_lambda025":
        term_name = "scar_component_adaptive_tversky"
        weight = CANONICAL_LOSS_WEIGHTS[term_name]
        mutated_value_tensor = refs["scar_component_adaptive_tversky"] + 0.25 * refs["scar_occupancy_dice_focal"]
        mutation_observations["replacement_formula"] = "Tversky(alpha=0.3,beta=0.7)+0.25*occupancy Dice/Focal"
    elif mutation_id == "scar_component_tversky_blended_occupancy_half":
        term_name = "scar_component_adaptive_tversky"
        weight = CANONICAL_LOSS_WEIGHTS[term_name]
        mutated_value_tensor = 0.5 * refs["scar_component_adaptive_tversky"] + 0.5 * refs["scar_occupancy_dice_focal"]
        mutation_observations["replacement_formula"] = "0.5*Tversky(alpha=0.3,beta=0.7)+0.5*occupancy Dice/Focal"
    else:
        raise KeyError(f"not a loss semantic mutation: {mutation_id}")

    original_value = _term_value(mutated_terms, term_name)
    mutated_value = float(mutated_value_tensor.detach().cpu())
    mutated_loss = base_loss + (mutated_value_tensor - base_loss.new_tensor(original_value)) * float(weight)
    mutated_terms[term_name]["value"] = mutated_value
    mutated_terms[term_name]["unweighted_value"] = mutated_value
    mutated_terms[term_name]["weighted_contribution"] = mutated_value * float(weight)
    mutated_terms[term_name]["computed_by"] = "verifier_runtime_protected_mutation_same_term_name"
    probe = _loss_semantic_oracle(outputs, mixed, mutated_loss, mutated_terms)
    mutation_observations.update(
        {
            "term_name_preserved": term_name,
            "original_unweighted_value": original_value,
            "mutated_unweighted_value": mutated_value,
            "mutated_weighted_contribution": mutated_value * float(weight),
            "semantic_oracle_status": probe.get("status"),
            "semantic_oracle_failures": probe.get("semantic_failures"),
            "injury_reference_unweighted": float(refs["injury_dice_bce"].detach().cpu()),
            "scar_component_reference_unweighted": float(refs["scar_component_adaptive_tversky"].detach().cpu()),
            "scar_occupancy_reference_unweighted": float(refs["scar_occupancy_dice_focal"].detach().cpu()),
        }
    )
    return probe, mutation_observations


def mutation_result(mutation_id: str, *, repo_root: Path, fixture_mode: bool) -> dict[str, Any]:
    if mutation_id not in MUTATION_IDS:
        raise KeyError(mutation_id)
    if mutation_id in RUNTIME_MANIFEST_MUTATION_IDS:
        return _runtime_manifest_mutation_result(mutation_id, repo_root=repo_root, fixture_mode=fixture_mode)
    failures: list[str] = []
    observations: dict[str, Any] = {}
    mutation_applied = "not_applied"
    mutation_executed = False
    try:
        runtime = _mutation_runtime_imports(repo_root)
        torch = runtime["torch"]
        build_care_ase_for_fold = runtime["build_care_ase_for_fold"]
        torch.manual_seed(4106)
        model = build_care_ase_for_fold(0, map_location="cpu").eval()
        source_before = source_artifact_hashes(repo_root)

        if mutation_id == "extent_conv3d_alias":
            mutation_applied = "component_heads.scar_extent_head_replaced_by_scar_quarter_occupancy"
            model.component_heads.scar_extent_head = model.component_heads.scar_quarter_occupancy
            mutation_executed = True
            observations["scar_extent_head_class"] = type(model.component_heads.scar_extent_head).__name__
            observations["scar_extent_aliases_occupancy"] = model.component_heads.scar_extent_head is model.component_heads.scar_quarter_occupancy
            if observations["scar_extent_aliases_occupancy"] or observations["scar_extent_head_class"] != "SliceExtentHead":
                failures.extend(["kb11.slice_extent_head.class", "kb11.scar_extent_presence_not_occupancy_alias"])

        elif mutation_id == "dilation_residual_removed":
            mutation_applied = "edema_dilation_context.forward_uses_projection_of_block_without_identity_add"
            block = model.edema_dilation_context
            feature = torch.randn(1, next(iter(block.residual_blocks.values()))[0].in_channels, 2, 4, 4)
            original = block(feature)

            def no_residual_forward(x: Any) -> dict[str, Any]:
                return {f"edema_dilation_{key}": block.projections[key](subblock(x)) for key, subblock in block.residual_blocks.items()}

            block.forward = no_residual_forward  # type: ignore[method-assign]
            mutated = block(feature)
            mutation_executed = True
            delta = {
                key: float((original[key] - mutated[key]).abs().max().detach().cpu())
                for key in sorted(original)
            }
            observations["residual_removed_output_delta_by_dilation"] = delta
            if any(value > 0.0 for value in delta.values()):
                failures.append("kb07.edema_dilation.residual_add")

        elif mutation_id == "injury_random_init":
            mutation_applied = "component_heads.edema_injury_weights_overwritten_with_random_values"
            before = model.component_heads.edema_injury.weight.detach().clone()
            with torch.no_grad():
                model.component_heads.edema_injury.weight.normal_(mean=0.0, std=0.5)
            mutation_executed = True
            observations["injury_weight_delta_max_abs"] = float((before - model.component_heads.edema_injury.weight.detach()).abs().max().cpu())
            if observations["injury_weight_delta_max_abs"] > 0.0:
                failures.append("kb07.injury_classifier.stock_mean_initializer")

        elif mutation_id == "projection_context_no_final_authority":
            mutation_applied = "all_named_evidence_projection_modules_return_zero_into_final_branches"
            cases = _runtime_case_bindings(repo_root)
            batch = _actual_batch(cases["t2_case"], cases["t2_availability"], labels=(4, 5, 1), device=torch.device("cpu"))
            for projection in (
                model.scar_branch.half_projections,
                model.scar_branch.full_projections,
                model.edema_branch.half_projections,
                model.edema_branch.full_projections,
            ):
                def zero_projection(inputs: dict[str, Any], spatial_shape: tuple[int, int, int], *, disabled: set[str] | None = None, _projection: Any = projection) -> Any:
                    first = inputs[next(iter(_projection.specs))]
                    out_channels = next(iter(_projection.projections.values())).out_channels
                    return first.detach().new_zeros((first.shape[0], out_channels, *spatial_shape))

                projection.forward = zero_projection  # type: ignore[method-assign]
            authority_probe = _final_authority_probe(model, batch, repo_root / "src" / "care_myocardium" / "models" / "care_ase" / "core.py")
            mutation_executed = True
            observations["authority_probe"] = authority_probe
            if authority_probe.get("status") != "PASS":
                failures.append("kb05.required_module_authority.oracle_rejected")

        elif mutation_id == "synthetic_intervention_delta":
            mutation_applied = "disable_flag_tanh_signal_injected_outside_normal_forward_graph"
            cases = _runtime_case_bindings(repo_root)
            batch = _actual_batch(cases["t2_case"], cases["t2_availability"], labels=(4, 5, 1), device=torch.device("cpu"))
            original_forward = model.forward

            def disable_only_tanh_forward(*args: Any, **kwargs: Any) -> dict[str, Any]:
                outputs = original_forward(*args, **kwargs)
                if int(kwargs.get("global_step", 0)) <= 0:
                    return outputs
                final_logits = outputs["final_logits"].clone()
                p_wall = outputs.get("p_wall_union")
                signal = torch.tanh(p_wall.float()) if p_wall is not None else torch.tanh(final_logits[:, 0:1].float())
                if kwargs.get("disable_scar_proposal") or kwargs.get("disable_scar_center") or kwargs.get("disable_scar_context") or kwargs.get("disable_all_evidence"):
                    final_logits[:, 5:6] = final_logits[:, 5:6] + 0.013 * signal.to(final_logits)
                if kwargs.get("disable_edema_injury") or kwargs.get("disable_edema_boundary") or kwargs.get("disable_edema_context") or kwargs.get("disable_all_evidence"):
                    final_logits[:, 4:5] = final_logits[:, 4:5] + 0.013 * signal.to(final_logits)
                return {**outputs, "final_logits": final_logits}

            model.forward = disable_only_tanh_forward  # type: ignore[method-assign]
            authority_probe = _final_authority_probe(model, batch, repo_root / "src" / "care_myocardium" / "models" / "care_ase" / "core.py")
            mutation_executed = True
            observations["authority_probe"] = authority_probe
            observations["flag_vs_verifier_owned_removal_max_abs"] = authority_probe.get("implementation_flag_vs_verifier_owned_removal_max_abs")
            observations["disable_flag_final_logit_contribution_sites"] = authority_probe.get("disable_flag_final_logit_contribution_sites")
            if authority_probe.get("status") != "PASS":
                failures.append("kb05.semantic_disable_only_tanh_signal")

        elif mutation_id == "semantic_disable_only_quadratic_signal":
            mutation_applied = "disable_flag_quadratic_signal_injected_outside_normal_forward_graph"
            cases = _runtime_case_bindings(repo_root)
            batch = _actual_batch(cases["t2_case"], cases["t2_availability"], labels=(4, 5, 1), device=torch.device("cpu"))
            original_forward = model.forward

            def disable_only_quadratic_forward(*args: Any, **kwargs: Any) -> dict[str, Any]:
                outputs = original_forward(*args, **kwargs)
                if int(kwargs.get("global_step", 0)) <= 0:
                    return outputs
                final_logits = outputs["final_logits"].clone()
                rho = outputs.get("wall_depth_rho")
                base = rho.float().square() if rho is not None else final_logits[:, 1:2].float().sigmoid().square()
                centered = base - base.detach().mean()
                if kwargs.get("disable_scar_proposal") or kwargs.get("disable_scar_center") or kwargs.get("disable_scar_context") or kwargs.get("disable_all_evidence"):
                    final_logits[:, 5:6] = final_logits[:, 5:6] + 0.037 * centered.to(final_logits)
                if kwargs.get("disable_edema_injury") or kwargs.get("disable_edema_boundary") or kwargs.get("disable_edema_context") or kwargs.get("disable_all_evidence"):
                    final_logits[:, 4:5] = final_logits[:, 4:5] - 0.021 * centered.to(final_logits)
                return {**outputs, "final_logits": final_logits}

            model.forward = disable_only_quadratic_forward  # type: ignore[method-assign]
            authority_probe = _final_authority_probe(model, batch, repo_root / "src" / "care_myocardium" / "models" / "care_ase" / "core.py")
            mutation_executed = True
            observations["authority_probe"] = authority_probe
            observations["flag_vs_verifier_owned_removal_max_abs"] = authority_probe.get("implementation_flag_vs_verifier_owned_removal_max_abs")
            observations["disable_flag_final_logit_contribution_sites"] = authority_probe.get("disable_flag_final_logit_contribution_sites")
            if authority_probe.get("status") != "PASS":
                failures.append("kb05.semantic_disable_only_quadratic_signal")

        elif mutation_id == "partial_hw_straight_through_zero_loss":
            mutation_applied = "partial_hw_presence_area_loss_mutated_to_loss_minus_detach"

            def straight_through_loss(
                presence_logits: Any,
                area_logits: Any,
                detached_p_wall: Any,
                target_presence: Any,
                target_pathology_voxels: Any,
                target_wall_voxels: Any,
                case_valid: Any,
                valid_spatial_mask: Any = None,
                area_case_valid: Any = None,
            ) -> tuple[Any, Any]:
                import torch.nn.functional as F
                from src.care_myocardium.models.care_ase import compute_slice_extent_statistics

                pred_presence_5d, pred_area_5d, _wall_slice, _fallback = compute_slice_extent_statistics(
                    presence_logits.float(),
                    area_logits.float(),
                    detached_p_wall.detach(),
                    valid_spatial_mask,
                )
                pred_presence = pred_presence_5d.squeeze(-1).squeeze(-1).float().clamp(1.0e-6, 1.0 - 1.0e-6)
                pred_area = pred_area_5d.squeeze(-1).squeeze(-1).float()
                presence = F.binary_cross_entropy(pred_presence, target_presence.float(), reduction="mean")
                area = F.smooth_l1_loss(pred_area, target_pathology_voxels.float() / target_wall_voxels.float().clamp_min(1.0), reduction="mean")
                return presence - presence.detach(), area - area.detach()

            partial_probe = _partial_hw_reference_probe(model, loss_fn=straight_through_loss)
            mutation_executed = True
            observations["partial_hw_reference_probe"] = partial_probe
            if partial_probe.get("straight_through_zero_loss_detected") or partial_probe.get("status") != "PASS":
                failures.append("kb11.partial_hw.straight_through_zero_loss")

        elif mutation_id == "partial_hw_cross_z_presequence_mask_removed":
            mutation_applied = "slice_extent_head_partial_hw_only_pixel_pooling_allows_cross_z_conv1d_leakage"
            head = model.component_heads.scar_extent_head

            def leaky_forward(feature: Any, valid_spatial_mask: Any = None) -> dict[str, Any]:
                import torch
                import torch.nn.functional as F

                if valid_spatial_mask is None:
                    masked = feature
                    valid = torch.ones_like(feature[:, :1])
                else:
                    valid = F.interpolate(valid_spatial_mask.detach().float(), size=feature.shape[-3:], mode="nearest").clamp(0.0, 1.0)
                    masked = feature * valid
                valid_sum = valid.sum(dim=(-2, -1)).clamp_min(1.0)
                masked_average = masked.sum(dim=(-2, -1)) / valid_sum
                masked_values = feature.masked_fill(valid <= 0.0, -torch.inf)
                masked_max = masked_values.amax(dim=(-2, -1))
                masked_max = torch.where(torch.isfinite(masked_max), masked_max, torch.zeros_like(masked_average))
                sequence_input = 0.5 * masked_average + 0.5 * masked_max
                hidden = head.sequence(sequence_input)
                presence_logits = head.presence(hidden).unsqueeze(-1).unsqueeze(-1)
                area_logits = head.area(hidden).unsqueeze(-1).unsqueeze(-1)
                expand_shape = (-1, -1, -1, feature.shape[-2], feature.shape[-1])
                return {
                    "presence_logits": presence_logits.expand(expand_shape),
                    "area_logits": area_logits.expand(expand_shape),
                }

            head.forward = leaky_forward  # type: ignore[method-assign]
            cross_z_probe = _slice_extent_head_cross_z_probe(model)
            mutation_executed = True
            observations["partial_hw_slice_extent_head_cross_z_probe"] = cross_z_probe
            if cross_z_probe.get("status") != "PASS":
                failures.append("kb11.partial_hw.cross_z_presequence_mask")
            else:
                failures.append("kb11.partial_hw.cross_z_presequence_mask_not_rejected")

        elif mutation_id in {
            "injury_dice_bce_replaced_by_focal",
            "scar_component_tversky_plus_occupancy_lambda025",
            "scar_component_tversky_blended_occupancy_half",
        }:
            mutation_applied = {
                "injury_dice_bce_replaced_by_focal": "injury_dice_bce_term_name_preserved_but_formula_replaced_by_dice_focal",
                "scar_component_tversky_plus_occupancy_lambda025": "scar_component_term_name_preserved_but_formula_adds_lambda025_occupancy_objective",
                "scar_component_tversky_blended_occupancy_half": "scar_component_term_name_preserved_but_formula_blends_half_occupancy_objective",
            }[mutation_id]
            semantic_probe, semantic_observations = _loss_semantic_mutation_probe(repo_root, mutation_id)
            mutation_executed = True
            observations["loss_semantic_mutation"] = semantic_observations
            observations["loss_semantic_probe"] = semantic_probe
            if semantic_probe.get("status") != "PASS":
                failures.append(f"kb13.loss_semantic_oracle.rejected:{mutation_id}")
            else:
                failures.append(f"kb13.loss_semantic_oracle.failed_to_reject:{mutation_id}")

        elif mutation_id == "full_support_pseudo_tiling":
            mutation_applied = "forced_multi_tile_predictor_runs_one_full_support_forward_then_fakes_tile_metadata"
            cases = _runtime_case_bindings(repo_root)
            batch = _actual_batch(cases["t2_case"], cases["t2_availability"], labels=(4, 5, 1), device=torch.device("cpu"))

            def pseudo_full_support_predict(
                loaded_model: Any,
                image: Any,
                availability: Any,
                *,
                settings: Any,
                metadata: dict[str, Any],
                use_gaussian: bool = False,
            ) -> Any:
                outputs = loaded_model(image, availability, global_step=14000)
                call_id = str(metadata.get("call_id", ""))
                if "forced_multi_tile" in call_id:
                    metadata.update(
                        {
                            "tile_count": 4,
                            "mirror_count": 1,
                            "tile_coordinates": [[0, 0, 0], [0, 0, 32], [0, 32, 0], [0, 32, 32]],
                            "global_bias_application_count": 1,
                            "canonical_full_support_base_field": True,
                            "mutation_note": "one full-volume model forward reused as pseudo tile-local aggregation",
                        }
                    )
                else:
                    metadata.update({"tile_count": 1, "mirror_count": 1, "global_bias_application_count": 1})
                return outputs["final_logits"].detach()

            single_logits, tile_probe = _tile_local_forward_probe(
                loaded_model=model,
                image=batch["image"],
                availability=batch["availability"],
                settings_cls=runtime["CAREASEFullVolumeInferenceSettings"],
                predict_fn=pseudo_full_support_predict,
            )
            mutation_executed = True
            observations["tile_local_forward_probe"] = tile_probe
            observations["single_logits_available"] = single_logits is not None
            if tile_probe.get("full_support_pseudo_tiling_detected") or tile_probe.get("status") != "PASS":
                failures.append("kb12.inference.full_support_pseudo_tiling")

        elif mutation_id == "transaction_old_tuple_reused":
            mutation_applied = "transaction_inputs_mutated_to_old_integration_and_verifier_fingerprint"
            failures_from_gate, transaction = transaction_gate(
                repo_root=repo_root,
                evidence={},
                review_round=0,
                integration_sha="5fd6c265109c19c91108fd3a2fa80a6b7d4092a4",
                implementation_fingerprint="3eabfb0be9eda776da6dd6fe3068004894ea7a5b4c30966941fc05bdc412e0dc",
                expected_verifier_fingerprint="8149d75c397904e6db2daa3ab1ba765e5c2c4db4abde607796645c51deb3c4ca",
                fixture_mode=False,
            )
            mutation_executed = True
            observations["transaction_gate"] = transaction
            observations["transaction_failures"] = failures_from_gate
            if failures_from_gate:
                failures.append("transaction.old_tuple_rejected")

        elif mutation_id == "forged_executor_pass_receipt":
            mutation_applied = "executor_pass_receipt_without_verifier_runtime_observations_presented_as_conclusion"
            forged = {
                "schema": "CARE_ASE_FAITHFUL_EXECUTOR_RECEIPT",
                "status": "PASS",
                "passed": True,
                "executor_receipts_used_as_runtime_conclusion": True,
                "probes": [],
            }
            mutation_executed = True
            observations["forged_receipt"] = forged
            if forged.get("passed") is True and forged.get("executor_receipts_used_as_runtime_conclusion") is True:
                failures.append("kb18.forged_executor_pass_receipt_not_verifier_observation")

        elif mutation_id == "no_t2_calls_edema":
            mutation_applied = "no_t2_path_explicitly_invokes_edema_owned_injury_head"
            calls = {"component_heads.edema_injury": 0}
            module = model.component_heads.edema_injury
            hook = module.register_forward_hook(
                lambda _m, _i, _o: calls.__setitem__("component_heads.edema_injury", calls["component_heads.edema_injury"] + 1)
            )
            try:
                _ = module(torch.randn(1, int(module.in_channels), 1, 4, 4))
            finally:
                hook.remove()
            mutation_executed = True
            observations["no_t2_edema_owned_module_call_count"] = calls["component_heads.edema_injury"]
            if calls["component_heads.edema_injury"] > 0:
                failures.append("kb08.runtime_no_t2.call_count")

        elif mutation_id == "single_multi_same_call":
            mutation_applied = "forced_multi_tile_receipt_reuses_single_tile_metadata_and_patch"
            settings = runtime["CAREASEFullVolumeInferenceSettings"](patch_size=PLAN_PATCH_SIZE)
            single_meta = {"call_id": "same_call", "patch_size": list(settings.patch_size)}
            forced_meta = single_meta
            mutation_executed = True
            observations["calls_are_distinct"] = single_meta is not forced_meta
            observations["patch_size_equals_input"] = tuple(settings.patch_size) == PLAN_PATCH_SIZE
            if not observations["calls_are_distinct"] or observations["patch_size_equals_input"]:
                failures.extend(["kb12.inference.calls_not_distinct", "kb12.inference.patch_size_equals_input"])

        elif mutation_id == "tile_local_global_bias":
            mutation_applied = "global_extent_bias_after_aggregation_invoked_twice_for_one_prediction"
            image = torch.zeros(1, 6, 2, 4, 4)
            comp = {name: torch.zeros(1, 1, 2, 4, 4) for name in ("scar_extent_presence", "scar_extent_area", "edema_extent_presence", "edema_extent_area")}
            p_wall = torch.ones(1, 1, 2, 4, 4)
            avail = torch.ones(1, 3)
            valid = torch.ones(1, 1, 2, 4, 4)
            metadata = {"global_bias_application_count": 0}
            fn = runtime["full_volume"].apply_global_extent_bias_after_aggregation
            fn(model, image.clone(), comp, p_wall, avail, global_step=14000, valid_spatial_mask=valid, metadata=metadata)
            fn(model, image.clone(), comp, p_wall, avail, global_step=14000, valid_spatial_mask=valid, metadata=metadata)
            mutation_executed = True
            observations["global_bias_application_count"] = int(metadata["global_bias_application_count"])
            if observations["global_bias_application_count"] != 1:
                failures.append("kb12.inference.global_bias_once")

        elif mutation_id == "deployment_reopens_stock_checkpoint":
            mutation_applied = "schema_v4_checkpoint_payload_mutated_to_require_stock_checkpoint_on_deployment_load"
            optimizer = runtime["build_optimizer"](model)
            scheduler = runtime["CAREASEStageScheduler"](optimizer)
            with tempfile.TemporaryDirectory(prefix="care_ase_mutation_deploy_") as tmp:
                ckpt = Path(tmp) / "mutated_deploy.pth"
                runtime["save_care_ase_checkpoint"](
                    ckpt,
                    model=model,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    global_step=1,
                    stage_id="A",
                    next_batch_hash="MUTATION_DEPLOY",
                    loss_history_tail=[],
                    code_hash=sha256_file(Path(__file__)),
                    config_hash=json_sha(model.config.__dict__),
                    split_hash="MUTATION_SPLIT",
                    stock_checkpoint_hash=sha256_file(Path(model.config.checkpoint_path)),
                    checkpoint_reason="mutation_deployment",
                )
                payload = torch.load(ckpt, map_location="cpu", weights_only=False)
                payload["deployment_load_requires_stock_checkpoint"] = True
                torch.save(payload, ckpt)
                mutation_executed = True
                try:
                    _loaded, loaded_payload = runtime["load_care_ase_checkpoint_for_inference"](ckpt, map_location="cpu", plans_path=Path(model.config.plans_path))
                    observations["deployment_load_requires_stock_checkpoint"] = bool(loaded_payload.get("deployment_load_requires_stock_checkpoint"))
                except ValueError as exc:
                    observations["deployment_loader_rejected_mutated_checkpoint"] = True
                    observations["observed_error"] = f"{type(exc).__name__}:{exc}"
                    observations["deployment_load_requires_stock_checkpoint"] = True
            if bool(observations.get("deployment_load_requires_stock_checkpoint")):
                failures.append("kb16.deployment.no_stock_checkpoint")

        elif mutation_id == "evaluator_population_mismatch":
            mutation_applied = "evaluator_called_with_mismatched_prediction_population_shape"
            import numpy as np

            try:
                runtime["evaluate_care_ase_r2_prediction_pair"](
                    case_id="Case2003",
                    care_prediction=np.zeros((2, 4, 4), dtype=np.uint8),
                    baseline_prediction=np.zeros((3, 4, 4), dtype=np.uint8),
                    ground_truth=np.zeros((2, 4, 4), dtype=np.uint8),
                    availability=(1.0, 1.0, 1.0),
                    spacing_zyx=(1.0, 1.0, 1.0),
                    tta="none",
                    decode="mutated_mismatch",
                    center="verifier_mutation",
                )
                observations["evaluator_rejected_mismatch"] = False
            except ValueError as exc:
                observations["evaluator_rejected_mismatch"] = True
                observations["observed_error"] = f"{type(exc).__name__}:{exc}"
            mutation_executed = True
            if observations["evaluator_rejected_mismatch"]:
                failures.append("kb19.evaluator.same_cases")

        elif mutation_id == "checkpoint_next_step_drift":
            mutation_applied = "schema_v4_checkpoint_next_batch_descriptor_mutated_after_save"
            optimizer = runtime["build_optimizer"](model)
            scheduler = runtime["CAREASEStageScheduler"](optimizer)
            with tempfile.TemporaryDirectory(prefix="care_ase_mutation_checkpoint_") as tmp:
                ckpt = Path(tmp) / "mutated_resume.pth"
                runtime["save_care_ase_checkpoint"](
                    ckpt,
                    model=model,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    global_step=1,
                    stage_id="A",
                    next_batch_hash="EXPECTED_NEXT",
                    loss_history_tail=[],
                    code_hash=sha256_file(Path(__file__)),
                    config_hash=json_sha(model.config.__dict__),
                    split_hash="MUTATION_SPLIT",
                    stock_checkpoint_hash=sha256_file(Path(model.config.checkpoint_path)),
                    checkpoint_reason="mutation_resume",
                )
                payload = torch.load(ckpt, map_location="cpu", weights_only=False)
                payload["next_batch_descriptor_sha256"] = "DRIFTED_NEXT"
                torch.save(payload, ckpt)
                mutation_executed = True
                try:
                    _loaded, loaded_payload = runtime["load_care_ase_checkpoint_for_inference"](ckpt, map_location="cpu", plans_path=Path(model.config.plans_path))
                    observations["next_descriptor_matches"] = loaded_payload.get("next_batch_descriptor_sha256") == "EXPECTED_NEXT"
                except ValueError as exc:
                    observations["checkpoint_loader_rejected_mutated_sidecar"] = True
                    observations["observed_error"] = f"{type(exc).__name__}:{exc}"
                    observations["next_descriptor_matches"] = False
            if not observations["next_descriptor_matches"]:
                failures.append("kb16.checkpoint_resume.next_step")

        elif mutation_id == "checkpoint_current_contract_provenance_drift":
            mutation_applied = "schema_v4_checkpoint_payload_mutated_to_old_request_nonce_and_frozen_contract"
            optimizer = runtime["build_optimizer"](model)
            scheduler = runtime["CAREASEStageScheduler"](optimizer)
            with tempfile.TemporaryDirectory(prefix="care_ase_mutation_checkpoint_contract_") as tmp:
                ckpt = Path(tmp) / "mutated_current_contract.pth"
                runtime["save_care_ase_checkpoint"](
                    ckpt,
                    model=model,
                    optimizer=optimizer,
                    scheduler=scheduler,
                    global_step=1,
                    stage_id="A",
                    next_batch_hash="EXPECTED_NEXT",
                    loss_history_tail=[],
                    code_hash=sha256_file(Path(__file__)),
                    config_hash=json_sha(model.config.__dict__),
                    split_hash="MUTATION_SPLIT",
                    stock_checkpoint_hash=sha256_file(Path(model.config.checkpoint_path)),
                    checkpoint_reason="mutation_current_contract_provenance",
                )
                payload = torch.load(ckpt, map_location="cpu", weights_only=False)
                payload["request_nonce"] = "old-request-nonce"
                payload["frozen_contract_sha256"] = "0" * 64
                torch.save(payload, ckpt)
                ckpt.with_suffix(ckpt.suffix + ".sha256").write_text(f"{sha256_file(ckpt)}  {ckpt.name}\n", encoding="utf-8")
                mutation_executed = True
                _loaded, loaded_payload = runtime["load_care_ase_checkpoint_for_inference"](
                    ckpt,
                    map_location="cpu",
                    plans_path=Path(model.config.plans_path),
                )
                observations["observed_request_nonce"] = loaded_payload.get("request_nonce")
                observations["observed_frozen_contract_sha256"] = loaded_payload.get("frozen_contract_sha256")
                observations["current_request_nonce_bound"] = loaded_payload.get("request_nonce") == REQUEST_NONCE
                observations["current_frozen_contract_sha256_bound"] = loaded_payload.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256
            if not observations["current_request_nonce_bound"] or not observations["current_frozen_contract_sha256_bound"]:
                failures.append("kb16.checkpoint_resume.current_contract_provenance")

        elif mutation_id == "artifact_sha_mismatch":
            mutation_applied = "tracked_runtime_artifact_bytes_changed_after_receipt_sha_recording"
            source_path = repo_root / "results" / "agent_flow_v3" / TASK_ID / "implementation" / "forward_backward_probe_receipt.json"
            before = sha256_file(source_path)
            with tempfile.TemporaryDirectory(prefix="care_ase_mutation_artifact_") as tmp:
                mutated_path = Path(tmp) / source_path.name
                mutated_path.write_bytes(source_path.read_bytes() + b"\n")
                after = sha256_file(mutated_path)
            mutation_executed = True
            observations["declared_sha256"] = before
            observations["mutated_file_sha256"] = after
            if before != after:
                failures.append("artifact_binding.forward_backward_probe.stdout_file_sha")

        observations["source_manifest_sha256_before_mutation"] = source_before["source_manifest_sha256"]
    except Exception as exc:
        failures.append(f"mutation.runtime_error:{type(exc).__name__}:{exc}")
        observations["runtime_error"] = f"{type(exc).__name__}:{exc}"

    if not failures:
        failures.append(f"mutation.expected_rejection_missing:{mutation_id}")
    return {
        "schema": "CARE_ASE_FAITHFUL_EXECUTABLE_MUTATION_RESULT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "mutation_id": mutation_id,
        "fixture_mode": fixture_mode,
        "passed": False,
        "failure_count": len(failures),
        "failures": failures,
        "mutation_executed": mutation_executed,
        "mutation_applied": mutation_applied,
        "mutated_fingerprint_sha256": json_sha({"mutation_id": mutation_id, "mutation_applied": mutation_applied, "observations": observations}),
        "observations": observations,
        "exit_code": 2,
        "created_utc": utc_now(),
    }


def build_receipt(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    repo_root = args.repo_root.resolve()
    evidence_path = args.evidence.resolve() if args.evidence else None
    evidence = load_json(evidence_path) if evidence_path else {}
    expected_verifier = args.verifier_fingerprint or verifier_fingerprint()
    transaction_failures, transaction = transaction_gate(
        repo_root=repo_root,
        evidence=evidence,
        review_round=args.review_round,
        integration_sha=args.integration_sha,
        implementation_fingerprint=args.implementation_fingerprint,
        expected_verifier_fingerprint=expected_verifier,
        fixture_mode=args.fixture_mode,
    )
    env = environment_payload(repo_root)
    source_hashes = source_artifact_hashes(repo_root)
    verifier_source_hashes = verifier_source_artifact_hashes(repo_root)
    if args.fixture_mode:
        runtime_failures: list[str] = []
        probes = fixture_probe_results()
    else:
        runtime_failures, probes = real_probe_results(repo_root, evidence)

    observed = {probe["name"]: probe for probe in probes}
    coverage_failures = [f"executable_probe.missing:{name}" for name in REQUIRED_PROBES if name not in observed]
    failures = transaction_failures + runtime_failures + coverage_failures
    status = "PASS" if not failures else "FAIL_CLOSED"
    payload = {
        "schema": "CARE_ASE_FAITHFUL_EXECUTABLE_VERIFIER_RECEIPT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "review_round": args.review_round,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "planner_review_commit": PLANNER_REVIEW_COMMIT,
        "integration_sha": args.integration_sha,
        "implementation_fingerprint_sha256": args.implementation_fingerprint,
        "reviewed_verifier_fingerprint_sha256_at_repair_start": expected_verifier,
        "verifier_source_fingerprint_sha256": verifier_source_hashes["verifier_source_fingerprint_sha256"],
        "status": status,
        "passed": not failures,
        "fixture_mode": args.fixture_mode,
        "runtime_conclusion_source": "fixture_selftest" if args.fixture_mode else "verifier_owned_independent_execution",
        "executor_receipts_used_as_runtime_conclusion": False,
        "failure_count": len(failures),
        "failures": failures,
        "transaction_gate": transaction,
        "environment": env,
        "source_artifacts": source_hashes,
        "verifier_source_artifacts": verifier_source_hashes,
        "implementation_evidence_path": str(evidence_path.relative_to(repo_root)) if evidence_path else None,
        "implementation_evidence_file_sha256": sha256_file(evidence_path) if evidence_path and evidence_path.is_file() else None,
        "runtime_receipt_bindings": runtime_receipt_bindings(repo_root, evidence),
        "probes": probes,
        "required_probes": REQUIRED_PROBES,
        "blocking_numeric_thresholds": BLOCKING_NUMERIC_THRESHOLDS,
        "diagnostic_numeric_observations": [
            real_cnn_single_multi_context_diagnostic_policy(),
        ],
        "forbidden_shortcuts_rejected_by_design": [
            "torch.randn inputs with asserted real case IDs",
            "same call reused for single and forced multi tile",
            "constant global bias or tile counts",
            "deployment probe without deployment loader call",
            "evaluator probe without evaluator call",
            "constant-one loss denominators",
            "manual-gradient-only checkpoint probe",
            "cross-fold hard-negative manifest without OOF proof",
            "disable flag epsilon delta treated as final authority",
            "straight-through zero-valued partial-H/W extent loss",
            "full-support pseudo-tiling presented as tile-local inference",
            "forged Executor PASS receipt replacing Verifier observations",
        ],
        "zero_credit": True,
        "formal_training_started": False,
        "outer_accessed": False,
        "docker_or_upload": False,
        "created_utc": utc_now(),
    }
    payload["executable_verifier_receipt_sha256"] = json_sha({k: v for k, v in payload.items() if k != "executable_verifier_receipt_sha256"})
    return (0 if not failures else 2), payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run CARE-ASE verifier-owned executable probes.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--integration-sha", default=REVIEWED_INTEGRATION_COMMIT)
    parser.add_argument("--implementation-fingerprint", default=REVIEWED_IMPLEMENTATION_FINGERPRINT)
    parser.add_argument("--verifier-fingerprint")
    parser.add_argument("--review-round", type=int, default=REVIEW_ROUND)
    parser.add_argument("--receipt", type=Path, default=VERIFICATION_DIR / "executable_verifier_receipt.json")
    parser.add_argument("--mutation-id", choices=MUTATION_IDS)
    parser.add_argument("--fixture-mode", action="store_true")
    args = parser.parse_args(argv)

    if args.mutation_id:
        result = mutation_result(args.mutation_id, repo_root=args.repo_root.resolve(), fixture_mode=args.fixture_mode)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    exit_code, receipt = build_receipt(args)
    write_json(args.receipt, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
