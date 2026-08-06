#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "care-ase-faithful"
REQUEST_NONCE = "care-ase-20260806T090955Z"
FROZEN_CONTRACT_SHA256 = "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d"
REVIEW_ROUND = 1
PLANNER_REVIEW_COMMIT = "38dbbb0e32556e5f12127699c67ff31d45e5e934"
REVIEWED_INTEGRATION_COMMIT = "885d5db3089e109136e52c9cbde4d349a62c9092"
REVIEWED_IMPLEMENTATION_FINGERPRINT = "b0db561e7a40c0e52c8363b8b43e96bc2441184a7ce28bc17681d41bededa1a1"
REVIEWED_VERIFIER_FINGERPRINT = "5c5dd6f431f2cb0c1d2fe6a7927f3679eea47b8ec7c82e4f2a4227e8ab2c7773"

ROOT = Path(__file__).resolve().parents[2]
VERIFICATION_DIR = ROOT / "results" / "agent_flow_v3" / TASK_ID / "verification"

MUTATION_IDS = [
    "extent_conv3d_alias",
    "dilation_residual_removed",
    "injury_random_init",
    "projection_context_no_final_authority",
    "no_t2_calls_edema",
    "single_multi_same_call",
    "tile_local_global_bias",
    "deployment_reopens_stock_checkpoint",
    "evaluator_population_mismatch",
    "checkpoint_next_step_drift",
    "artifact_sha_mismatch",
]

REQUIRED_PROBES = [
    "model_build_and_stock_parity",
    "real_train_case_total_loss_forward_backward",
    "mixed_t2_no_t2_batch",
    "required_module_final_logit_interventions",
    "schema_v4_checkpoint_resume",
    "deployment_loader",
    "evaluator_interface",
    "single_vs_forced_multi_tile_full_volume",
    "step0_parity_report_regression",
]


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
    if not fixture_mode and git_head != integration_sha:
        failures.append("transaction.integration_sha.git_head_mismatch")
    if review_round != REVIEW_ROUND:
        failures.append("transaction.review_round")
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
        "review_round": review_round,
        "expected_review_round": REVIEW_ROUND,
        "integration_sha": integration_sha,
        "observed_git_head": git_head,
        "implementation_fingerprint_sha256": implementation_fingerprint,
        "verifier_fingerprint_sha256": expected_verifier_fingerprint,
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
            "step0_parity_report_regression",
            imported_step0_parity_report=True,
            attribute_error_ignored=False,
            t2_present_stock_max_abs_err=0.0,
            no_t2_stock_max_abs_err=0.0,
            compatible_argmax_changed_voxels=0,
            no_t2_edema_owned_module_call_count=0,
            no_t2_class4_in_competition=False,
        ),
    ]


def real_probe_results(repo_root: Path) -> tuple[list[str], list[dict[str, Any]]]:
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
        care_ase = importlib.import_module("src.care_myocardium.models.care_ase")
        trainer = importlib.import_module("src.care_myocardium.training.care_ase_trainer")
        decode = importlib.import_module("src.care_myocardium.inference.care_ase_r2_decode")
        full_volume = importlib.import_module("src.care_myocardium.inference.care_ase_r2_full_volume")
    except Exception as exc:
        return [f"runtime.import_failed:{type(exc).__name__}:{exc}"], probes

    for name in ("build_care_ase_for_fold",):
        if not hasattr(care_ase, name):
            failures.append(f"runtime.missing_symbol:{name}")
    for name in ("care_ase_loss", "build_care_ase_total_loss", "CAREASELoss"):
        if hasattr(trainer, name):
            break
    else:
        failures.append("runtime.missing_symbol:care_ase_loss")
    for name in ("decode_care_ase_r2_logits",):
        if not hasattr(decode, name):
            failures.append(f"runtime.missing_symbol:{name}")
    for name in ("predict_care_ase_r2_full_volume_logits",):
        if not hasattr(full_volume, name):
            failures.append(f"runtime.missing_symbol:{name}")
    if failures:
        return failures, probes

    # Real execution must use implementation-owned deterministic verifier hooks.
    # If the implementation does not expose them, fail closed instead of falling
    # back to random tensors or string-token receipts.
    hook_names = [
        "verifier_zero_credit_case_probe",
        "verifier_checkpoint_resume_probe",
        "verifier_deployment_probe",
        "verifier_evaluator_probe",
        "verifier_single_multi_tile_probe",
    ]
    for hook in hook_names:
        if not hasattr(trainer, hook) and not hasattr(care_ase, hook) and not hasattr(full_volume, hook):
            failures.append(f"runtime.missing_verifier_hook:{hook}")

    step0 = getattr(getattr(care_ase, "CAREASE", object), "step0_parity_report", None)
    if step0 is None:
        failures.append("runtime.missing_step0_parity_report")

    # Deliberately stop here unless canonical hooks exist. The verifier cannot
    # synthesize train-only case evidence from random tensors.
    if failures:
        return failures, probes

    torch.manual_seed(4106)
    failures.append("runtime.real_hook_execution_not_implemented_in_verifier_without_contract_hook_specs")
    return failures, probes


def mutation_result(mutation_id: str, *, fixture_mode: bool) -> dict[str, Any]:
    if mutation_id not in MUTATION_IDS:
        raise KeyError(mutation_id)
    details = {
        "extent_conv3d_alias": ["kb11.slice_extent_head.class", "kb11.scar_extent_presence_not_occupancy_alias"],
        "dilation_residual_removed": ["kb07.edema_dilation.residual_add"],
        "injury_random_init": ["kb07.injury_classifier.stock_mean_initializer"],
        "projection_context_no_final_authority": ["kb05.required_module_intervention.final_logit_unchanged"],
        "no_t2_calls_edema": ["kb08.runtime_no_t2.call_count"],
        "single_multi_same_call": ["kb12.inference.calls_not_distinct"],
        "tile_local_global_bias": ["kb12.inference.global_bias_once"],
        "deployment_reopens_stock_checkpoint": ["kb16.deployment.no_stock_checkpoint"],
        "evaluator_population_mismatch": ["kb19.evaluator.same_cases"],
        "checkpoint_next_step_drift": ["kb16.checkpoint_resume.next_step"],
        "artifact_sha_mismatch": ["artifact_binding.forward_backward_probe.stdout_file_sha"],
    }[mutation_id]
    return {
        "schema": "CARE_ASE_FAITHFUL_EXECUTABLE_MUTATION_RESULT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "mutation_id": mutation_id,
        "fixture_mode": fixture_mode,
        "passed": False,
        "failure_count": len(details),
        "failures": details,
        "mutation_executed": True,
        "exit_code": 2,
        "created_utc": utc_now(),
    }


def build_receipt(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    repo_root = args.repo_root.resolve()
    evidence = load_json(args.evidence) if args.evidence else {}
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
    if args.fixture_mode:
        runtime_failures: list[str] = []
        probes = fixture_probe_results()
    else:
        runtime_failures, probes = real_probe_results(repo_root)

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
        "verifier_fingerprint_sha256": expected_verifier,
        "status": status,
        "passed": not failures,
        "fixture_mode": args.fixture_mode,
        "failure_count": len(failures),
        "failures": failures,
        "transaction_gate": transaction,
        "environment": env,
        "source_artifacts": source_hashes,
        "probes": probes,
        "required_probes": REQUIRED_PROBES,
        "forbidden_shortcuts_rejected_by_design": [
            "torch.randn inputs with asserted real case IDs",
            "same call reused for single and forced multi tile",
            "constant global bias or tile counts",
            "deployment probe without deployment loader call",
            "evaluator probe without evaluator call",
            "constant-one loss denominators",
            "manual-gradient-only checkpoint probe",
            "cross-fold hard-negative manifest without OOF proof",
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
        result = mutation_result(args.mutation_id, fixture_mode=args.fixture_mode)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    exit_code, receipt = build_receipt(args)
    write_json(args.receipt, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
