from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "validators" / "care_ase_faithful" / "validate_contract_evidence.py"
EXECUTABLE_VERIFIER = ROOT / "validators" / "care_ase_faithful" / "run_executable_verifier.py"
CONTRACT = ROOT / "results" / "agent_flow_v3" / "care-ase-faithful" / "verification" / "verification_contract.json"

TASK_ID = "care-ase-faithful"
REQUEST_NONCE = "care-ase-20260806T090955Z"
FROZEN_CONTRACT_SHA256 = "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d"

REQUIRED_LOSSES = [
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

REQUIRED_METRICS = [
    "blood_pool_adjacent_fp",
    "casewise_help_harm",
    "centerB_centerC_subgroup",
    "component_count",
    "dice",
    "exact_hd",
    "hd95",
    "lesion_recall",
    "precision",
    "remote_fp_count",
    "remote_fp_volume",
    "sensitivity",
    "sentinel_case",
    "small_lesion_recall",
    "volume_ratio",
]

CRITICAL_SOURCE_PATHS = [
    "src/care_myocardium/models/care_ase/__init__.py",
    "src/care_myocardium/models/care_ase/core.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "src/care_myocardium/inference/care_ase_r2_full_volume.py",
]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_sha(payload: Any) -> str:
    return _sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def _json_sha_without_self(payload: dict[str, Any], field: str) -> str:
    clone = dict(payload)
    clone.pop(field, None)
    return _json_sha(clone)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _reference_evidence() -> dict[str, Any]:
    result = _run_validator("--emit-reference")
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return json.loads(result.stdout)


def _compliant_core_source() -> str:
    return '''
from torch import nn
import torch

class SliceExtentHead(nn.Module):
    def __init__(self, C):
        super().__init__()
        self.sequence = nn.Sequential(
            nn.Conv1d(C, 64, 3, padding=1),
            nn.GroupNorm(8, 64),
            nn.SiLU(),
            nn.Conv1d(64, 64, 3, padding=1),
            nn.SiLU(),
        )
        self.presence = nn.Conv1d(64, 1, 1)
        self.area = nn.Conv1d(64, 1, 1)
    def forward(self, x, wall, mask):
        masked_average = x.mean((-1, -2))
        masked_max = x.amax((-1, -2))
        pooled = 0.5 * masked_average + 0.5 * masked_max
        hidden = self.sequence(pooled)
        return self.presence(hidden), self.area(hidden).sigmoid()

class EdemaDilationContextBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.d1 = nn.Conv3d(channels, channels, 3, padding=1, dilation=1)
        self.d2 = nn.Conv3d(channels, channels, 3, padding=2, dilation=2)
        self.d4 = nn.Conv3d(channels, channels, 3, padding=4, dilation=4)
    def forward(self, feature):
        identity = feature
        residual = self.d1(feature) + self.d2(feature) + self.d4(feature)
        return residual + identity

def initialize_injury_classifier_from_stock_mean(stock):
    stock_class4_class5_mean = torch.stack([stock.weight[4], stock.weight[5]], dim=0).mean(dim=0)
    class_index=4
    class_index=5
    return stock_class4_class5_mean

class ComponentHeads(nn.Module):
    def __init__(self):
        super().__init__()
        self.scar_extent_head = SliceExtentHead(32)
        self.edema_extent_head = SliceExtentHead(32)
'''


def _bad_extent_core_source() -> str:
    return '''
from torch import nn

class EdemaDilationContextBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.dilated = nn.ModuleDict({
            "1": nn.Sequential(nn.Conv3d(channels, channels, 3, padding=1, dilation=1), nn.Conv3d(channels, 1, 1)),
            "2": nn.Sequential(nn.Conv3d(channels, channels, 3, padding=2, dilation=2), nn.Conv3d(channels, 1, 1)),
            "4": nn.Sequential(nn.Conv3d(channels, channels, 3, padding=4, dilation=4), nn.Conv3d(channels, 1, 1)),
        })
    def forward(self, feature):
        return {key: block(feature) for key, block in self.dilated.items()}

class ComponentHeads(nn.Module):
    def __init__(self, quarter_channels):
        super().__init__()
        self.scar_quarter_occupancy = nn.Conv3d(quarter_channels, 1, 1)
        self.scar_extent_area = nn.Conv3d(quarter_channels, 1, 1)
        self.edema_extent_presence = nn.Conv3d(quarter_channels, 1, 1)
    def forward(self, quarter):
        scar_quarter_occupancy = self.scar_quarter_occupancy(quarter)
        return {"scar_extent_presence": scar_quarter_occupancy}
'''


def _receipt(path: Path, name: str, payload: dict[str, Any]) -> dict[str, Any]:
    command = {"entrypoint": name, "zero_credit": True}
    stdout = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
    receipt = {
        "schema": "CARE_ASE_FAITHFUL_ZERO_CREDIT_PROBE_RECEIPT_V2",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "probe": name,
        "executed": True,
        "exit_code": 0,
        "command": command,
        "command_sha256": _json_sha(command),
        "stdout_sha256": _sha256_bytes(stdout),
        "stderr_sha256": _sha256_bytes(b""),
        "zero_credit": True,
        "formal_training_started": False,
        "outer_accessed": False,
        "docker_or_upload": False,
        "payload": payload,
    }
    _write_json(path, receipt)
    _write_json(path.with_name(path.name.replace("_receipt.json", "_stdout.json")), payload)
    return receipt


def _build_strict_fixture(tmp: Path, *, core_source: str | None = None) -> Path:
    evidence = _reference_evidence()
    fixture_root = tmp / "fixture"
    source_root = fixture_root / "source"
    implementation = fixture_root / "implementation"
    for rel in CRITICAL_SOURCE_PATHS:
        path = source_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith("core.py"):
            path.write_text(core_source or _compliant_core_source(), encoding="utf-8")
        elif rel.endswith("__init__.py"):
            path.write_text("from .core import SliceExtentHead\n", encoding="utf-8")
        else:
            path.write_text("# strict verifier fixture\n", encoding="utf-8")

    source_manifest = {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_SOURCE_MANIFEST_V2",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "source_root": str(source_root.relative_to(ROOT)),
        "file_hashes": {rel: _sha256_file(source_root / rel) for rel in CRITICAL_SOURCE_PATHS},
        "missing_files": [],
    }
    source_manifest["source_manifest_sha256"] = _json_sha_without_self(source_manifest, "source_manifest_sha256")
    source_manifest_path = implementation / "implementation_source_manifest.json"
    _write_json(source_manifest_path, source_manifest)

    static_checks = {"schema": "STATIC", "all_static_tokens_present": True}
    static_checks["static_architecture_checks_sha256"] = _json_sha_without_self(static_checks, "static_architecture_checks_sha256")
    architecture = {"schema": "ARCH", "topology": "compliant"}
    architecture["architecture_signature_sha256"] = _json_sha_without_self(architecture, "architecture_signature_sha256")
    parameter_registry = {"schema": "PARAMS", "owners": "compliant"}
    parameter_registry["parameter_owner_registry_sha256"] = _json_sha_without_self(parameter_registry, "parameter_owner_registry_sha256")
    _write_json(implementation / "static_architecture_checks.json", static_checks)
    _write_json(implementation / "architecture_signature.json", architecture)
    _write_json(implementation / "parameter_owner_registry.json", parameter_registry)

    loss_terms = {
        name: {"value": 0.125, "denominator": 8 + index, "included_in_total": True}
        for index, name in enumerate(REQUIRED_LOSSES)
    }
    forward_backward = _receipt(
        implementation / "forward_backward_probe_receipt.json",
        "forward_backward_probe",
        {
            "status": "PASS",
            "probe_type": "real_train_case_total_loss_two_backward",
            "input_origin": "train_only_dataset501_case_tensor",
            "random_tensor_used": False,
            "constant_denominator_count": 0,
            "train_case_ids": {"scar": "Case001", "edema_t2_present": "Case002"},
            "mixed_batch_no_t2": {
                "case_id": "Case003",
                "edema_owned_module_call_count": 0,
                "edema_supervision_rows": 0,
                "edema_parameter_grad_abs_sum": 0.0,
            },
            "total_loss_terms": loss_terms,
        },
    )
    inference = _receipt(
        implementation / "inference_probe_receipt.json",
        "inference_probe",
        {
            "status": "PASS",
            "probe_type": "real_case_single_vs_forced_multi_tile",
            "case_id": "Case001",
            "single_tile_path": "canonical_full_volume",
            "forced_multi_tile_path": "canonical_full_volume",
            "single_tile_call_id": "single",
            "forced_multi_tile_call_id": "forced_multi",
            "patch_size_equals_input": False,
            "forced_multi_tile_count": 8,
            "single_vs_forced_multi_tile_max_abs_diff": 0.0,
            "global_bias_application_count": 1,
        },
    )
    _receipt(
        implementation / "checkpoint_resume_probe_receipt.json",
        "checkpoint_resume_probe",
        {
            "status": "PASS",
            "schema_version": 4,
            "request_nonce": "care-ase-20260806T090955Z",
            "frozen_contract_sha256": "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d",
            "next_step_matches_uninterrupted": True,
            "rng_and_cursor_state_matches": True,
        },
    )
    _receipt(
        implementation / "deployment_load_probe_receipt.json",
        "deployment_load_probe",
        {
            "status": "PASS",
            "self_contained_load": True,
            "opened_stock_checkpoint_after_deployment_load": False,
        },
    )
    _receipt(
        implementation / "evaluator_smoke_receipt.json",
        "evaluator_smoke",
        {
            "status": "PASS",
            "same_case_population": True,
            "same_tta_decode_metric_interface": True,
            "metrics": REQUIRED_METRICS,
        },
    )
    _receipt(
        implementation / "hard_negative_binding_receipt.json",
        "hard_negative_binding",
        {
            "status": "PASS",
            "case_id": "Case004",
            "oof_prediction_bound": True,
            "mask_sha256": "a" * 64,
            "coordinate_sha256": "b" * 64,
            "checkpoint_sha256": "c" * 64,
            "grid_sha256": "d" * 64,
        },
    )

    evidence["source_manifest_sha256"] = source_manifest["source_manifest_sha256"]
    evidence["static_architecture_checks_sha256"] = static_checks["static_architecture_checks_sha256"]
    evidence["architecture_signature_sha256"] = architecture["architecture_signature_sha256"]
    evidence["parameter_owner_registry_sha256"] = parameter_registry["parameter_owner_registry_sha256"]
    evidence["runtime_receipts"]["forward_backward_probe"] = {
        key: forward_backward[key] for key in ("executed", "command_sha256", "exit_code", "stdout_sha256", "stderr_sha256")
    }
    evidence["runtime_receipts"]["inference_probe"] = {
        key: inference[key] for key in ("executed", "command_sha256", "exit_code", "stdout_sha256", "stderr_sha256")
    }
    evidence["receipt_paths"] = {
        "source_manifest": str(source_manifest_path.relative_to(ROOT)),
        "static_architecture_checks": str((implementation / "static_architecture_checks.json").relative_to(ROOT)),
        "architecture_signature": str((implementation / "architecture_signature.json").relative_to(ROOT)),
        "parameter_owner_registry": str((implementation / "parameter_owner_registry.json").relative_to(ROOT)),
        "forward_backward_probe": str((implementation / "forward_backward_probe_receipt.json").relative_to(ROOT)),
        "inference_probe": str((implementation / "inference_probe_receipt.json").relative_to(ROOT)),
        "checkpoint_resume_probe": str((implementation / "checkpoint_resume_probe_receipt.json").relative_to(ROOT)),
        "deployment_load_probe": str((implementation / "deployment_load_probe_receipt.json").relative_to(ROOT)),
        "evaluator_smoke": str((implementation / "evaluator_smoke_receipt.json").relative_to(ROOT)),
        "hard_negative_binding": str((implementation / "hard_negative_binding_receipt.json").relative_to(ROOT)),
    }
    evidence_path = implementation / "implementation_evidence.json"
    _write_json(evidence_path, evidence)
    return evidence_path


class VerifierPackageTests(unittest.TestCase):
    def test_real_cnn_single_multi_diff_is_diagnostic_not_hard_gate(self) -> None:
        spec = importlib.util.spec_from_file_location("care_ase_executable_verifier", EXECUTABLE_VERIFIER)
        if spec is None or spec.loader is None:
            self.fail("cannot import executable verifier")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        policy = module.real_cnn_single_multi_context_diagnostic_policy()
        self.assertIs(policy["blocking"], False)
        self.assertIs(policy["diagnostic_only"], True)
        self.assertIsNone(policy["contract_source_path"])
        self.assertNotIn(
            "real_care_ase_single_full_context_vs_forced_tile_local_diff",
            {item["name"] for item in module.BLOCKING_NUMERIC_THRESHOLDS},
        )

    def test_fresh_model_disable_flag_delta_is_diagnostic_not_hard_gate(self) -> None:
        spec = importlib.util.spec_from_file_location("care_ase_executable_verifier", EXECUTABLE_VERIFIER)
        if spec is None or spec.loader is None:
            self.fail("cannot import executable verifier")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        probes = module.fixture_probe_results()
        diagnostic_probe = {
            "name": "required_module_final_logit_interventions",
            "status": "PASS",
            "intervention_max_abs_by_module": {
                "all_named_evidence": 0.0,
                "edema_boundary": 0.0,
                "edema_context_and_dilation": 0.0,
                "edema_injury": 0.0,
                "extent_wall": 0.0,
                "scar_context": 0.0,
                "scar_proposal": 0.0,
            },
            "all_changed_intended_final_logits": False,
            "blocking": False,
            "diagnostic_only": True,
            "fresh_zero_initialized_disable_flag_delta_required": False,
        }
        probes = [
            diagnostic_probe if probe["name"] == "required_module_final_logit_interventions" else probe
            for probe in probes
        ]
        authority_probe = next(probe for probe in probes if probe["name"] == "required_module_final_authority_oracle")
        self.assertEqual(authority_probe["status"], "PASS")
        self.assertTrue(authority_probe["no_disable_flag_final_logit_contribution"])

        observed = {probe["name"] for probe in probes}
        coverage_failures = [f"executable_probe.missing:{name}" for name in module.REQUIRED_PROBES if name not in observed]
        probe_failures = [f"executable_probe.failed:{probe['name']}" for probe in probes if probe.get("status") != "PASS"]
        self.assertEqual(coverage_failures, [])
        self.assertNotIn("executable_probe.failed:required_module_final_logit_interventions", probe_failures)
        self.assertEqual(probe_failures, [])

    def test_loss_semantic_oracle_is_required_and_independent(self) -> None:
        spec = importlib.util.spec_from_file_location("care_ase_executable_verifier", EXECUTABLE_VERIFIER)
        if spec is None or spec.loader is None:
            self.fail("cannot import executable verifier")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertIn("loss_semantic_oracle", module.REQUIRED_PROBES)
        threshold_names = {item["name"] for item in module.BLOCKING_NUMERIC_THRESHOLDS}
        self.assertIn("loss_semantic_oracle_reference_match", threshold_names)
        probes = {probe["name"]: probe for probe in module.fixture_probe_results()}
        semantic = probes["loss_semantic_oracle"]
        self.assertEqual(semantic["status"], "PASS")
        self.assertIs(semantic["reference_uses_implementation_loss_helper"], False)
        self.assertTrue(semantic["injury_dice_bce"]["matches_reference"])
        self.assertTrue(semantic["scar_component_adaptive_tversky"]["matches_reference"])
        self.assertTrue(semantic["unique_allowed_loss_set"]["no_extra_weighted_auxiliary_objective"])

    def test_loss_formula_runtime_mutations_are_required(self) -> None:
        runner_spec = importlib.util.spec_from_file_location("care_ase_executable_verifier", EXECUTABLE_VERIFIER)
        validator_spec = importlib.util.spec_from_file_location("care_ase_contract_validator", VALIDATOR)
        builder = ROOT / "validators" / "care_ase_faithful" / "build_verification_artifacts.py"
        builder_spec = importlib.util.spec_from_file_location("care_ase_artifact_builder", builder)
        for spec in (runner_spec, validator_spec, builder_spec):
            if spec is None or spec.loader is None:
                self.fail("cannot import verifier package module")
        runner = importlib.util.module_from_spec(runner_spec)
        validator = importlib.util.module_from_spec(validator_spec)
        builder_module = importlib.util.module_from_spec(builder_spec)
        runner_spec.loader.exec_module(runner)
        validator_spec.loader.exec_module(validator)
        validator_dir = str(VALIDATOR.parent)
        inserted = validator_dir not in sys.path
        if inserted:
            sys.path.insert(0, validator_dir)
        try:
            builder_spec.loader.exec_module(builder_module)
        finally:
            if inserted:
                sys.path.remove(validator_dir)

        required = {
            "injury_dice_bce_replaced_by_focal",
            "scar_component_tversky_plus_occupancy_lambda025",
            "scar_component_tversky_blended_occupancy_half",
            "partial_hw_cross_z_presequence_mask_removed",
            "checkpoint_current_contract_provenance_drift",
            "runtime_manifest_round0_reused",
            "runtime_manifest_missing_nonce",
            "runtime_manifest_missing_frozen_contract",
            "runtime_manifest_old_integration",
            "runtime_manifest_old_implementation_fingerprint",
            "runtime_manifest_old_verifier_fingerprint",
            "runtime_manifest_receipt_sha_drift",
        }
        self.assertTrue(required.issubset(set(runner.MUTATION_IDS)))
        self.assertTrue(required.issubset(set(validator.REQUIRED_EXECUTABLE_MUTATION_IDS)))
        self.assertTrue(required.issubset(set(builder_module.EXECUTABLE_MUTATION_IDS)))
        self.assertIn("partial_hw_slice_extent_head_cross_z_gradient", set(runner.REQUIRED_PROBES))
        self.assertIn("partial_hw_slice_extent_head_cross_z_gradient", set(validator.REQUIRED_EXECUTABLE_PROBES))

    def test_verifier_fingerprint_excludes_runtime_execution_receipts(self) -> None:
        builder = ROOT / "validators" / "care_ase_faithful" / "build_verification_artifacts.py"
        builder_spec = importlib.util.spec_from_file_location("care_ase_artifact_builder", builder)
        if builder_spec is None or builder_spec.loader is None:
            self.fail("cannot import artifact builder")
        validator_dir = str(VALIDATOR.parent)
        inserted = validator_dir not in sys.path
        if inserted:
            sys.path.insert(0, validator_dir)
        try:
            builder_module = importlib.util.module_from_spec(builder_spec)
            builder_spec.loader.exec_module(builder_module)
        finally:
            if inserted:
                sys.path.remove(validator_dir)
        fingerprint_names = {path.name for path in builder_module.fingerprint_input_paths()}
        self.assertNotIn("executable_verifier_receipt.json", fingerprint_names)
        self.assertNotIn("transaction_gate_receipt.json", fingerprint_names)
        self.assertNotIn("runtime_mutation_manifest.json", fingerprint_names)
        self.assertNotIn("integrated_implementation_validation_result.json", fingerprint_names)
        self.assertNotIn("verification_contract.json", fingerprint_names)
        self.assertNotIn("public_test_manifest.json", fingerprint_names)
        self.assertNotIn("protected_known_bad_manifest.json", fingerprint_names)

        file_hashes_a = builder_module.fingerprint_file_hashes(builder_module.FROZEN_CONTRACT_SHA256)
        file_hashes_b = builder_module.fingerprint_file_hashes(builder_module.FROZEN_CONTRACT_SHA256)
        digest_a = builder_module.sha256_bytes(json.dumps(file_hashes_a, sort_keys=True).encode("utf-8"))
        digest_b = builder_module.sha256_bytes(json.dumps(file_hashes_b, sort_keys=True).encode("utf-8"))
        runtime_tuple_a = {
            "integration_sha": "d643c80ce15aa77a28ffb0bec6661afac5be3237",
            "implementation_fingerprint_sha256": "dd5593f869823de7fe0b76f953c3ea1ade6d0c1426a7e26a39a4ae1aea6fa692",
        }
        runtime_tuple_b = {
            "integration_sha": "0" * 40,
            "implementation_fingerprint_sha256": "f" * 64,
        }
        self.assertNotEqual(runtime_tuple_a, runtime_tuple_b)
        self.assertEqual(digest_a, digest_b)

    def test_transaction_gate_rejects_old_ci_run_for_current_integration(self) -> None:
        runner_spec = importlib.util.spec_from_file_location("care_ase_executable_verifier", EXECUTABLE_VERIFIER)
        if runner_spec is None or runner_spec.loader is None:
            self.fail("cannot import executable verifier")
        runner = importlib.util.module_from_spec(runner_spec)
        runner_spec.loader.exec_module(runner)

        def valid_runtime_manifest() -> dict[str, Any]:
            receipt_paths = list(runner.REQUIRED_RUNTIME_MANIFEST_ARTIFACTS.values())
            return {
                "schema": "CARE_AGENT_FLOW_V3_RUNTIME_RECEIPT_MANIFEST",
                "task_id": runner.TASK_ID,
                "request_nonce": runner.REQUEST_NONCE,
                "frozen_contract_sha256": runner.FROZEN_CONTRACT_SHA256,
                "review_round": runner.REVIEW_ROUND,
                "integration_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
                "implementation_fingerprint_sha256": runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
                "verifier_fingerprint_sha256": runner.REVIEWED_VERIFIER_FINGERPRINT,
                "receipts": receipt_paths,
                "receipt_sha256s": {path: _sha256_file(ROOT / path) for path in receipt_paths},
            }

        evidence = {
            "task_id": runner.TASK_ID,
            "request_nonce": runner.REQUEST_NONCE,
            "frozen_contract_sha256": runner.FROZEN_CONTRACT_SHA256,
            "implementation_fingerprint_sha256": runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
        }
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp_path = Path(tmp)
            current_path = tmp_path / "CURRENT.json"
            runtime_manifest_path = tmp_path / "runtime_receipt_manifest.json"
            ci_receipt_path = tmp_path / "controller_ci_receipt.json"
            old_ci_sha = "491ba697e7a51712d9d04fc27824e4efa018827a"
            current_path.write_text(
                json.dumps(
                    {
                        "task_id": runner.TASK_ID,
                        "request_nonce": runner.REQUEST_NONCE,
                        "frozen_contract_sha256": runner.FROZEN_CONTRACT_SHA256,
                        "integration_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
                        "implementation_fingerprint_sha256": runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
                        "verifier_fingerprint_sha256": runner.REVIEWED_VERIFIER_FINGERPRINT,
                    }
                ),
                encoding="utf-8",
            )
            runtime_manifest_path.write_text(
                json.dumps(valid_runtime_manifest()),
                encoding="utf-8",
            )
            original_current = runner.CURRENT_PATH
            original_manifest = runner.RUNTIME_MANIFEST_PATH
            original_ci = runner.CONTROLLER_CI_RECEIPT_PATH
            try:
                runner.CURRENT_PATH = current_path
                runner.RUNTIME_MANIFEST_PATH = runtime_manifest_path
                runner.CONTROLLER_CI_RECEIPT_PATH = ci_receipt_path
                ci_cases = [
                    (
                        "old_head",
                        {
                            "github_actions_head_sha": old_ci_sha,
                            "checked_commit_sha": old_ci_sha,
                            "github_actions_conclusion": "success",
                        },
                        "transaction.hosted_ci.head_sha_not_exact_integration",
                    ),
                    (
                        "pending",
                        {
                            "github_actions_head_sha": runner.REVIEWED_INTEGRATION_COMMIT,
                            "checked_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
                            "github_actions_conclusion": "in_progress",
                        },
                        "transaction.hosted_ci.conclusion",
                    ),
                    (
                        "failed",
                        {
                            "github_actions_head_sha": runner.REVIEWED_INTEGRATION_COMMIT,
                            "checked_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
                            "github_actions_conclusion": "failure",
                        },
                        "transaction.hosted_ci.conclusion",
                    ),
                ]
                for label, ci_payload, expected_failure in ci_cases:
                    ci_receipt_path.write_text(json.dumps(ci_payload), encoding="utf-8")
                    failures, transaction = runner.transaction_gate(
                        repo_root=ROOT,
                        evidence=evidence,
                        review_round=runner.REVIEW_ROUND,
                        integration_sha=runner.REVIEWED_INTEGRATION_COMMIT,
                        implementation_fingerprint=runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
                        expected_verifier_fingerprint=runner.REVIEWED_VERIFIER_FINGERPRINT,
                        fixture_mode=False,
                    )
                    self.assertIn(expected_failure, failures, label)
                    if label == "old_head":
                        self.assertNotEqual(transaction["hosted_ci_head_sha"], runner.REVIEWED_INTEGRATION_COMMIT)
            finally:
                runner.CURRENT_PATH = original_current
                runner.RUNTIME_MANIFEST_PATH = original_manifest
                runner.CONTROLLER_CI_RECEIPT_PATH = original_ci

    def test_transaction_gate_rejects_stale_runtime_manifest_bindings(self) -> None:
        runner_spec = importlib.util.spec_from_file_location("care_ase_executable_verifier", EXECUTABLE_VERIFIER)
        if runner_spec is None or runner_spec.loader is None:
            self.fail("cannot import executable verifier")
        runner = importlib.util.module_from_spec(runner_spec)
        runner_spec.loader.exec_module(runner)

        receipt_paths = list(runner.REQUIRED_RUNTIME_MANIFEST_ARTIFACTS.values())
        base_manifest = {
            "schema": "CARE_AGENT_FLOW_V3_RUNTIME_RECEIPT_MANIFEST",
            "task_id": runner.TASK_ID,
            "request_nonce": runner.REQUEST_NONCE,
            "frozen_contract_sha256": runner.FROZEN_CONTRACT_SHA256,
            "review_round": runner.REVIEW_ROUND,
            "integration_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
            "implementation_fingerprint_sha256": runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
            "verifier_fingerprint_sha256": runner.REVIEWED_VERIFIER_FINGERPRINT,
            "receipts": receipt_paths,
            "receipt_sha256s": {path: _sha256_file(ROOT / path) for path in receipt_paths},
        }
        current = {
            "task_id": runner.TASK_ID,
            "request_nonce": runner.REQUEST_NONCE,
            "frozen_contract_sha256": runner.FROZEN_CONTRACT_SHA256,
            "integration_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
            "implementation_fingerprint_sha256": runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
            "verifier_fingerprint_sha256": runner.REVIEWED_VERIFIER_FINGERPRINT,
            "ci_checked_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
            "ci_run_actual_head_sha": runner.REVIEWED_INTEGRATION_COMMIT,
        }
        ci_receipt = {
            "github_actions_head_sha": runner.REVIEWED_INTEGRATION_COMMIT,
            "checked_commit_sha": runner.REVIEWED_INTEGRATION_COMMIT,
            "github_actions_conclusion": "success",
        }
        evidence = {
            "task_id": runner.TASK_ID,
            "request_nonce": runner.REQUEST_NONCE,
            "frozen_contract_sha256": runner.FROZEN_CONTRACT_SHA256,
            "implementation_fingerprint_sha256": runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
        }
        cases: list[tuple[str, str, Any]] = [
            ("review_round", "transaction.runtime_manifest.review_round", 0),
            ("request_nonce", "transaction.runtime_manifest.request_nonce", None),
            ("frozen_contract_sha256", "transaction.runtime_manifest.frozen_contract_sha256", None),
            ("integration_commit_sha", "transaction.runtime_manifest.integration_commit_sha", "0" * 40),
            ("implementation_fingerprint_sha256", "transaction.runtime_manifest.implementation_fingerprint_sha256", "1" * 64),
            ("verifier_fingerprint_sha256", "transaction.runtime_manifest.verifier_fingerprint_sha256", "2" * 64),
        ]
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            tmp_path = Path(tmp)
            current_path = tmp_path / "CURRENT.json"
            runtime_manifest_path = tmp_path / "runtime_receipt_manifest.json"
            ci_receipt_path = tmp_path / "controller_ci_receipt.json"
            current_path.write_text(json.dumps(current), encoding="utf-8")
            ci_receipt_path.write_text(json.dumps(ci_receipt), encoding="utf-8")
            original_current = runner.CURRENT_PATH
            original_manifest = runner.RUNTIME_MANIFEST_PATH
            original_ci = runner.CONTROLLER_CI_RECEIPT_PATH
            try:
                runner.CURRENT_PATH = current_path
                runner.RUNTIME_MANIFEST_PATH = runtime_manifest_path
                runner.CONTROLLER_CI_RECEIPT_PATH = ci_receipt_path
                for field, expected_failure, value in cases:
                    manifest = dict(base_manifest)
                    if value is None:
                        manifest.pop(field, None)
                    else:
                        manifest[field] = value
                    runtime_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    failures, _transaction = runner.transaction_gate(
                        repo_root=ROOT,
                        evidence=evidence,
                        review_round=runner.REVIEW_ROUND,
                        integration_sha=runner.REVIEWED_INTEGRATION_COMMIT,
                        implementation_fingerprint=runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
                        expected_verifier_fingerprint=runner.REVIEWED_VERIFIER_FINGERPRINT,
                        fixture_mode=False,
                    )
                    self.assertIn(expected_failure, failures, field)

                manifest = dict(base_manifest)
                manifest["receipt_sha256s"] = dict(base_manifest["receipt_sha256s"])
                manifest["receipt_sha256s"][runner.REQUIRED_RUNTIME_MANIFEST_ARTIFACTS["implementation_evidence"]] = "0" * 64
                runtime_manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                failures, _transaction = runner.transaction_gate(
                    repo_root=ROOT,
                    evidence=evidence,
                    review_round=runner.REVIEW_ROUND,
                    integration_sha=runner.REVIEWED_INTEGRATION_COMMIT,
                    implementation_fingerprint=runner.REVIEWED_IMPLEMENTATION_FINGERPRINT,
                    expected_verifier_fingerprint=runner.REVIEWED_VERIFIER_FINGERPRINT,
                    fixture_mode=False,
                )
                self.assertIn("transaction.runtime_manifest.artifact_sha256:implementation_evidence", failures)
            finally:
                runner.CURRENT_PATH = original_current
                runner.RUNTIME_MANIFEST_PATH = original_manifest
                runner.CONTROLLER_CI_RECEIPT_PATH = original_ci

    def test_public_reference_fixture_requires_explicit_override(self) -> None:
        reference = _run_validator("--emit-reference")
        self.assertEqual(reference.returncode, 0, reference.stderr)
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            evidence_path = Path(tmp) / "reference_evidence.json"
            evidence_path.write_text(reference.stdout, encoding="utf-8")
            strict = _run_validator("--verification-contract", str(CONTRACT), "--evidence", str(evidence_path.relative_to(ROOT)))
            self.assertNotEqual(strict.returncode, 0, strict.stdout + strict.stderr)
            strict_payload = json.loads(strict.stdout)
            self.assertIn("artifact_binding.receipt_paths.missing", strict_payload["failures"])

            fixture = _run_validator(
                "--verification-contract",
                str(CONTRACT),
                "--evidence",
                str(evidence_path.relative_to(ROOT)),
                "--allow-public-reference-fixture",
            )
            self.assertEqual(fixture.returncode, 0, fixture.stdout + fixture.stderr)

    def test_strict_artifact_bound_fixture_requires_production_verifier_execution(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            evidence_path = _build_strict_fixture(Path(tmp))
            result = _run_validator("--verification-contract", str(CONTRACT), "--evidence", str(evidence_path.relative_to(ROOT)))
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            failures = set(json.loads(result.stdout)["failures"])
            self.assertTrue(
                "verifier_owned.executable_verifier_receipt.missing" in failures
                or "verifier_owned.runtime_mutation_manifest.missing" in failures
                or "verifier_owned.transaction_gate_receipt.missing" in failures
                or "verifier_owned.executable.not_fixture" in failures
                or "verifier_owned.executable.passed" in failures
                or any(item.startswith("verifier_owned.executable.runtime_binding_path:") for item in failures)
                or any(item.startswith("verifier_owned.executable.runtime_binding_sha:") for item in failures)
            )

    def test_receipt_hash_mismatch_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            evidence_path = _build_strict_fixture(Path(tmp))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["runtime_receipts"]["forward_backward_probe"]["stdout_sha256"] = "0" * 64
            evidence_path.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result = _run_validator("--verification-contract", str(CONTRACT), "--evidence", str(evidence_path.relative_to(ROOT)))
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertIn("kb18.forward_backward_probe.stdout_sha_bound", payload["failures"])

    def test_conv3d_extent_alias_topology_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            evidence_path = _build_strict_fixture(Path(tmp), core_source=_bad_extent_core_source())
            result = _run_validator("--verification-contract", str(CONTRACT), "--evidence", str(evidence_path.relative_to(ROOT)))
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            failures = set(json.loads(result.stdout)["failures"])
            self.assertIn("kb11.slice_extent_head.class", failures)
            self.assertIn("kb11.scar_extent_presence_not_occupancy_alias", failures)

    def test_forged_random_input_and_constant_denominators_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            evidence_path = _build_strict_fixture(Path(tmp))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            fb_path = ROOT / evidence["receipt_paths"]["forward_backward_probe"]
            fb = json.loads(fb_path.read_text(encoding="utf-8"))
            fb["payload"]["random_tensor_used"] = True
            fb["payload"]["input_origin"] = "torch.randn"
            fb["payload"]["constant_denominator_count"] = len(REQUIRED_LOSSES)
            for term in fb["payload"]["total_loss_terms"].values():
                term["denominator"] = 1
            stdout = json.dumps(fb["payload"], indent=2, sort_keys=True, default=str).encode("utf-8")
            fb["stdout_sha256"] = _sha256_bytes(stdout)
            _write_json(fb_path, fb)
            result = _run_validator("--verification-contract", str(CONTRACT), "--evidence", str(evidence_path.relative_to(ROOT)))
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            failures = set(json.loads(result.stdout)["failures"])
            self.assertIn("kb18.forward_backward.no_random_tensor", failures)
            self.assertIn("kb13.runtime_loss.no_constant_denominator_count", failures)

    def test_reused_single_multi_tile_call_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            evidence_path = _build_strict_fixture(Path(tmp))
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            inf_path = ROOT / evidence["receipt_paths"]["inference_probe"]
            inf = json.loads(inf_path.read_text(encoding="utf-8"))
            inf["payload"]["single_tile_call_id"] = "same"
            inf["payload"]["forced_multi_tile_call_id"] = "same"
            inf["payload"]["patch_size_equals_input"] = True
            inf["payload"]["forced_multi_tile_count"] = 1
            stdout = json.dumps(inf["payload"], indent=2, sort_keys=True, default=str).encode("utf-8")
            inf["stdout_sha256"] = _sha256_bytes(stdout)
            _write_json(inf_path, inf)
            result = _run_validator("--verification-contract", str(CONTRACT), "--evidence", str(evidence_path.relative_to(ROOT)))
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
            failures = set(json.loads(result.stdout)["failures"])
            self.assertIn("kb12.inference.distinct_call_ids", failures)
            self.assertIn("kb12.inference.patch_not_equal_input", failures)
            self.assertIn("kb12.inference.forced_multi_tile_count", failures)

    def test_executable_mutation_runner_returns_nonzero(self) -> None:
        runner = ROOT / "validators" / "care_ase_faithful" / "run_executable_verifier.py"
        care_root = Path(os.environ.get("CARE_VERIFIER_RUNTIME_CARE_ROOT", "/users/a/e/aereinh/CARE"))
        runtime_python = Path(os.environ.get("CARE_VERIFIER_RUNTIME_PYTHON", str(care_root / "envs" / "env_CARE" / "bin" / "python")))
        if not runtime_python.is_file():
            self.skipTest(f"CARE runtime python not available: {runtime_python}")
        env = dict(os.environ)
        env.setdefault("CARE_ROOT", str(care_root))
        env.setdefault("nnUNet_raw", str(care_root / "data" / "nnUNet" / "nnUNet_raw"))
        env.setdefault("nnUNet_preprocessed", str(care_root / "data" / "nnUNet" / "nnUNet_preprocessed"))
        env.setdefault("nnUNet_results", str(care_root / "data" / "nnUNet" / "nnUNet_results"))
        env.setdefault("MPLCONFIGDIR", "/users/a/e/aereinh/.tmp/codex-verifier/matplotlib")
        result = subprocess.run(
            [str(runtime_python), str(runner), "--mutation-id", "artifact_sha_mismatch"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["mutation_id"], "artifact_sha_mismatch")
        self.assertIs(payload["fixture_mode"], False)
        self.assertIs(payload["mutation_executed"], True)
        self.assertEqual(payload["mutation_applied"], "tracked_runtime_artifact_bytes_changed_after_receipt_sha_recording")
        self.assertEqual(len(payload["mutated_fingerprint_sha256"]), 64)

    def test_all_protected_known_bad_cases_fail_closed(self) -> None:
        listed = _run_validator("--list-known-bad")
        self.assertEqual(listed.returncode, 0, listed.stderr)
        known_bad_cases = json.loads(listed.stdout)
        self.assertEqual(len(known_bad_cases), 24)

        for case in known_bad_cases:
            result = _run_validator("--known-bad-id", case["id"])
            self.assertNotEqual(result.returncode, 0, case["id"])
            payload = json.loads(result.stdout)
            self.assertIs(payload["passed"], False)
            self.assertGreater(payload["failure_count"], 0)

    def test_generated_protected_manifest_records_all_nonzero_invocations(self) -> None:
        manifest_path = ROOT / "results" / "agent_flow_v3" / "care-ase-faithful" / "verification" / "protected_known_bad_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["count"], 24)
        self.assertIs(manifest["all_returned_nonzero"], True)
        self.assertEqual(
            sorted(item["contract_category"] for item in manifest["known_bad_invocations"]),
            list(range(1, 25)),
        )
        for item in manifest["known_bad_invocations"]:
            self.assertNotEqual(item["exit_code"], 0, item["id"])
            self.assertIs(item["passed_fail_closed"], True)


if __name__ == "__main__":
    unittest.main()
