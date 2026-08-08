#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Callable


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


KNOWN_BAD_CATEGORIES = [
    {
        "id": "kb01_role_isolation_overlap",
        "contract_category": 1,
        "public_label": "role/session isolation overlap",
    },
    {
        "id": "kb02_trunk_inheritance_degraded",
        "contract_category": 2,
        "public_label": "stock trunk inheritance degraded",
    },
    {
        "id": "kb03_shallow_decoder_head",
        "contract_category": 3,
        "public_label": "shallow head substitutes for required decoders",
    },
    {
        "id": "kb04_stock_class_shortcut",
        "contract_category": 4,
        "public_label": "stock class shortcut enters normal forward",
    },
    {
        "id": "kb05_required_module_no_authority",
        "contract_category": 5,
        "public_label": "required module has no target/final authority",
    },
    {
        "id": "kb06_dead_gradient_double_zero",
        "contract_category": 6,
        "public_label": "double zero initialization dead gradient",
    },
    {
        "id": "kb07_modality_role_violation",
        "contract_category": 7,
        "public_label": "scar/edema modality ownership violated",
    },
    {
        "id": "kb08_no_t2_edema_leak",
        "contract_category": 8,
        "public_label": "no-T2 rows leak into edema graph or class-4 competition",
    },
    {
        "id": "kb09_auxiliary_only_context_extent",
        "contract_category": 9,
        "public_label": "context/extent/soft-wall are auxiliary only",
    },
    {
        "id": "kb10_hard_or_forbidden_mechanism",
        "contract_category": 10,
        "public_label": "hard ROI/wall/prototype/fixed-priority mechanism",
    },
    {
        "id": "kb11_patch_local_extent_or_invalid_bias",
        "contract_category": 11,
        "public_label": "patch-local extent or invalid-slice bias",
    },
    {
        "id": "kb12_tile_bias_or_path_fork",
        "contract_category": 12,
        "public_label": "tile-local final bias or single/multi path fork",
    },
    {
        "id": "kb13_loss_excluded_or_fake_denominator",
        "contract_category": 13,
        "public_label": "declared loss excluded or zero denominator counted",
    },
    {
        "id": "kb14_hard_negative_unbound",
        "contract_category": 14,
        "public_label": "hard negative lacks mask/coordinate/checkpoint/grid binding",
    },
    {
        "id": "kb15_unrecorded_sampler_fallback",
        "contract_category": 15,
        "public_label": "requested/resolved sampler category mismatch unrecorded",
    },
    {
        "id": "kb16_checkpoint_resume_drift",
        "contract_category": 16,
        "public_label": "checkpoint schema or exact resume is unsafe",
    },
    {
        "id": "kb17_early_checkpoint_final_ramp",
        "contract_category": 17,
        "public_label": "early checkpoint inference uses final-step ramp",
    },
    {
        "id": "kb18_canned_receipt_without_execution",
        "contract_category": 18,
        "public_label": "canned receipt without real execution evidence",
    },
    {
        "id": "kb19_patch_proxy_evaluator",
        "contract_category": 19,
        "public_label": "patch proxy or unfair evaluator substitutes full volume",
    },
    {
        "id": "kb20_incomplete_training_counted",
        "contract_category": 20,
        "public_label": "under-budget or non-terminal run counted as training",
    },
    {
        "id": "kb21_outer_selection_leak",
        "contract_category": 21,
        "public_label": "outer data used for selection",
    },
    {
        "id": "kb22_hidden_asset_or_old_wrapper",
        "contract_category": 22,
        "public_label": "hidden host asset or old wrapper bypass",
    },
    {
        "id": "kb23_dual_truth_implementation",
        "contract_category": 23,
        "public_label": "monolith and module implementation both runnable",
    },
    {
        "id": "kb24_metric_interface_missing",
        "contract_category": 24,
        "public_label": "required metric or sentinel interface missing",
    },
]


REQUIRED_LOSSES = {
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


REQUIRED_METRICS = {
    "dice",
    "hd95",
    "exact_hd",
    "precision",
    "sensitivity",
    "lesion_recall",
    "small_lesion_recall",
    "component_count",
    "remote_fp_count",
    "remote_fp_volume",
    "blood_pool_adjacent_fp",
    "volume_ratio",
    "casewise_help_harm",
    "centerB_centerC_subgroup",
    "sentinel_case",
}


REQUIRED_RECEIPT_PATHS = {
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
}

REQUIRED_EXECUTABLE_MUTATION_IDS = {
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
    "runtime_manifest_stale_round0",
    "runtime_manifest_missing_nonce",
    "runtime_manifest_missing_contract",
    "runtime_manifest_old_integration",
    "runtime_manifest_old_implementation_fingerprint",
    "runtime_manifest_old_verifier_fingerprint",
    "artifact_sha_mismatch",
}

REQUIRED_EXECUTABLE_PROBES = {
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
}

CRITICAL_SOURCE_PATHS = {
    "src/care_myocardium/models/care_ase/__init__.py",
    "src/care_myocardium/models/care_ase/core.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "src/care_myocardium/inference/care_ase_r2_full_volume.py",
}


def reference_evidence() -> dict[str, Any]:
    role_receipt = {
        "thread_id": "thread-controller",
        "codex_home": "/users/a/e/aereinh/.codex-homes/CARE_care-ase-faithful_CONTROLLER",
        "worktree": "/users/a/e/aereinh/CARE_agent_flow/care-ase-faithful/controller",
    }
    return {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_EVIDENCE_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "role_receipts": {
            "controller": role_receipt,
            "verifier": {
                **role_receipt,
                "thread_id": "thread-verifier",
                "codex_home": "/users/a/e/aereinh/.codex-homes/CARE_care-ase-faithful_VERIFIER",
                "worktree": "/users/a/e/aereinh/CARE_agent_flow/care-ase-faithful/verifier",
            },
            "executor": {
                **role_receipt,
                "thread_id": "thread-executor",
                "codex_home": "/users/a/e/aereinh/.codex-homes/CARE_care-ase-faithful_EXECUTOR",
                "worktree": "/users/a/e/aereinh/CARE_agent_flow/care-ase-faithful/executor",
            },
        },
        "architecture": {
            "stock_trunk": {
                "encoder_byte_coverage": 0.995,
                "bottleneck_byte_coverage": 1.0,
                "decoder_byte_coverage": 0.995,
                "deep_supervision_head_byte_coverage": 0.995,
                "channels_from_plan_introspection": True,
                "decoder_reset": False,
                "channels_shrunk": False,
                "trunk_permanently_frozen": False,
                "stock_compatible_logits_max_abs_err": 0.0,
                "stock_compatible_argmax_changed_voxels": 0,
                "encoder_and_shared_low_mid_decoder_run_once": True,
            },
            "pathology_decoders": {
                "scar_highest_two_scale_independent_decoder": True,
                "edema_highest_two_scale_independent_decoder": True,
                "d0_shallow_head_substitute": False,
                "stock_class4_5_normal_forward_shortcut": False,
                "scar_context_logits_enter_final_path": True,
                "edema_context_logits_enter_final_path": True,
            },
            "required_module_authority": {
                "modality_adapters_affect_final_logits": True,
                "scar_proposal_affects_final_logits": True,
                "edema_dilation_affects_final_logits": True,
                "context_affects_final_logits": True,
                "extent_affects_final_logits": True,
                "soft_wall_affects_final_logits": True,
            },
            "forbidden_mechanisms": {
                "hard_wall": False,
                "hard_roi": False,
                "bbox_crop": False,
                "local_refiner": False,
                "prototype_dictionary_query": False,
                "fixed_scar_priority": False,
            },
            "single_truth": {
                "canonical_package": "src/care_myocardium/models/care_ase",
                "legacy_imports_are_thin_forwarders": True,
                "monolith_runnable": False,
                "duplicate_runtime_truth": False,
            },
        },
        "modalities_and_gradients": {
            "adapters_active_initialized": True,
            "adapter_and_projection_double_zero": False,
            "scar_uses_lge_primary": True,
            "scar_uses_c0_auxiliary": True,
            "scar_uses_t2": False,
            "edema_uses_t2_primary": True,
            "edema_uses_c0_auxiliary": True,
            "edema_uses_lge_weak_context": True,
            "scar_c0_gate_initial_output": 0.2,
            "edema_c0_gate_initial_output": 0.2,
            "edema_lge_gate_initial_output": 0.05,
            "named_zero_residual_projections": True,
            "first_backward_required_projection_grad_nonzero_finite": True,
            "second_backward_adapter_gate_context_grad_nonzero_finite": True,
        },
        "no_t2_semantics": {
            "edema_owned_module_call_count": 0,
            "edema_supervision_rows": 0,
            "edema_negative_rows": 0,
            "edema_parameter_grad_abs_sum": 0.0,
            "class4_in_softmax_dice_argmax_denominator": False,
            "class5_decode_remaps_to_official_label5": True,
            "mixed_batch_safe_scatter": True,
        },
        "context_and_extent": {
            "anatomy_context_detached_before_pathology": True,
            "context_soft_wall_extent_have_final_authority": True,
            "full_case_extent_targets": True,
            "invalid_padding_partial_hw_bias_zero": True,
            "presence_area_validity_separate": True,
            "training_inference_compute_slice_extent_statistics_shared": True,
            "tile_outputs_base_logits_only": True,
            "global_bias_applied_once_after_aggregation": True,
            "single_tile_multi_tile_same_path": True,
            "ramp_formula": "piecewise_0_500_2000_or_deploy",
        },
        "losses": {
            "terms": {name: {"weight": weight, "included_in_total": True} for name, weight in REQUIRED_LOSSES.items()},
            "zero_denominator_claims_coverage": False,
            "per_loss_denominators_reported": True,
            "eligible_row_voxel_normalization": True,
            "fp32_sensitive_reductions": True,
        },
        "sampler_and_hard_negatives": {
            "scar_sampler_percentages": [35, 20, 20, 15, 10],
            "edema_sampler_percentages": [35, 20, 20, 15, 10],
            "edema_complete_center_cycle": "CenterB_CenterC_1_to_1_with_replacement_if_needed",
            "no_t2_edema_event_count": 0,
            "hard_negative_binding": {
                "mask_sha256": "1" * 64,
                "coordinate_sha256": "c" * 64,
                "checkpoint_sha256": "2" * 64,
                "grid_sha256": "3" * 64,
                "case_id": "Case0001",
            },
            "requested_resolved_mismatches": [],
        },
        "checkpoint_and_resume": {
            "schema_version": 4,
            "self_contained_deployment": True,
            "cross_fold_resume_rejected": True,
            "contract_manifest_environment_drift_rejected": True,
            "reload_next_step_matches_uninterrupted": True,
            "reload_validation_advances_training_rng": False,
            "nonfinite_blocks_optimizer_commit": True,
            "early_checkpoint_uses_saved_step_ramp": True,
            "early_checkpoint_uses_final_step_ramp": False,
        },
        "runtime_receipts": {
            "forward_backward_probe": {
                "executed": True,
                "command_sha256": "f" * 64,
                "exit_code": 0,
                "stdout_sha256": "a" * 64,
                "stderr_sha256": "b" * 64,
            },
            "inference_probe": {
                "executed": True,
                "command_sha256": "4" * 64,
                "exit_code": 0,
                "stdout_sha256": "d" * 64,
                "stderr_sha256": "e" * 64,
            },
            "canned_without_execution": False,
        },
        "evaluation_interface": {
            "canonical_full_volume_only": True,
            "patch_proxy_evaluator": False,
            "fair_baseline_same_cases_tta_decode_population": True,
            "metrics": sorted(REQUIRED_METRICS),
        },
        "formal_training_accounting": {
            "claims_formal_training": False,
            "completed_optimizer_steps": 0,
            "visited_stages": [],
            "pending_or_preempted_counted": False,
            "stage_b_or_c_skipped": False,
        },
        "data_boundary": {
            "outer_used_for_threshold": False,
            "outer_used_for_coefficients": False,
            "outer_used_for_checkpoint": False,
            "outer_used_for_source_selection": False,
            "hidden_host_asset_required": False,
            "old_wrapper_bypasses_new_implementation": False,
        },
    }


def _get(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted)
        current = current[part]
    return current


def _require(failures: list[str], condition: bool, code: str) -> None:
    if not condition:
        failures.append(code)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_sha(payload: Any) -> str:
    return _sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def _payload_sha_without_self(payload: dict[str, Any], field: str) -> str:
    clone = copy.deepcopy(payload)
    clone.pop(field, None)
    return _json_sha(clone)


def _resolve_artifact(path_value: Any, *, root: Path = ROOT) -> Path | None:
    if not isinstance(path_value, str) or not path_value:
        return None
    path = Path(path_value)
    if path.is_absolute():
        return None
    return root / path


def _load_artifact(
    failures: list[str],
    receipt_paths: dict[str, Any],
    name: str,
    *,
    root: Path = ROOT,
) -> tuple[Path | None, dict[str, Any] | None]:
    path = _resolve_artifact(receipt_paths.get(name), root=root)
    if path is None:
        failures.append(f"artifact_binding.{name}.path_not_relative")
        return None, None
    if not path.is_file():
        failures.append(f"artifact_binding.{name}.missing")
        return path, None
    try:
        return path, load_json(path)
    except Exception as exc:  # pragma: no cover - reported as validation failure.
        failures.append(f"artifact_binding.{name}.invalid_json:{type(exc).__name__}")
        return path, None


def _source_root(source_manifest: dict[str, Any], source_manifest_path: Path, *, root: Path = ROOT) -> Path:
    declared = source_manifest.get("source_root")
    if isinstance(declared, str) and declared:
        resolved = _resolve_artifact(declared, root=root)
        if resolved is not None:
            return resolved
    if source_manifest_path.is_relative_to(root):
        return root
    return source_manifest_path.parent


def _class_body(source: str, class_name: str) -> str:
    match = re.search(rf"^class\s+{re.escape(class_name)}\b.*?(?=^class\s+\w|\Z)", source, flags=re.M | re.S)
    return match.group(0) if match else ""


def _check_source_manifest_and_topology(
    failures: list[str],
    source_manifest_path: Path,
    source_manifest: dict[str, Any],
    evidence: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    declared_sha = source_manifest.get("source_manifest_sha256")
    _require(failures, _is_sha256(declared_sha), "artifact_binding.source_manifest.sha256_shape")
    if _is_sha256(declared_sha):
        _require(
            failures,
            declared_sha == _payload_sha_without_self(source_manifest, "source_manifest_sha256"),
            "artifact_binding.source_manifest.sha256_recomputed",
        )
        _require(failures, evidence.get("source_manifest_sha256") == declared_sha, "artifact_binding.source_manifest.evidence_sha")

    file_hashes = source_manifest.get("file_hashes", {})
    _require(failures, isinstance(file_hashes, dict), "artifact_binding.source_manifest.file_hashes_dict")
    source_root = _source_root(source_manifest, source_manifest_path, root=root)
    missing_declared = set(source_manifest.get("missing_files", []))
    for rel in CRITICAL_SOURCE_PATHS:
        if rel in missing_declared:
            failures.append(f"artifact_binding.source_manifest.critical_missing:{rel}")
            continue
        source_path = source_root / rel
        if not source_path.is_file():
            failures.append(f"artifact_binding.source_manifest.critical_file_absent:{rel}")
            continue
        _require(failures, file_hashes.get(rel) == _sha256_file(source_path), f"artifact_binding.source_manifest.hash:{rel}")

    core_path = source_root / "src/care_myocardium/models/care_ase/core.py"
    if not core_path.is_file():
        failures.append("kb03.source_topology.core_missing")
        return
    core = core_path.read_text(encoding="utf-8")
    slice_head = _class_body(core, "SliceExtentHead")
    _require(failures, bool(slice_head), "kb11.slice_extent_head.class")
    _require(failures, slice_head.count("nn.Conv1d(") >= 4, "kb11.slice_extent_head.conv1d_count")
    _require(failures, "nn.GroupNorm(8, 64)" in slice_head or "nn.GroupNorm(num_groups=8, num_channels=64)" in slice_head, "kb11.slice_extent_head.groupnorm")
    _require(failures, "masked" in slice_head.lower() and "max" in slice_head.lower(), "kb11.slice_extent_head.masked_avg_max")
    _require(failures, "self.scar_extent_head = SliceExtentHead" in core, "kb11.scar_extent_head.distinct_module")
    _require(failures, "self.edema_extent_head = SliceExtentHead" in core, "kb11.edema_extent_head.distinct_module")
    _require(failures, '"scar_extent_presence": scar_quarter_occupancy' not in core, "kb11.scar_extent_presence_not_occupancy_alias")
    _require(failures, "self.scar_extent_area = nn.Conv3d" not in core, "kb11.scar_extent_not_conv3d_area_head")
    _require(failures, "self.edema_extent_presence = nn.Conv3d" not in core, "kb11.edema_extent_not_conv3d_presence_head")

    dilation = _class_body(core, "EdemaDilationContextBlock")
    _require(failures, bool(dilation), "kb07.edema_dilation.class")
    _require(failures, "Residual" in dilation or "residual" in dilation.lower(), "kb07.edema_dilation.residual_named")
    _require(failures, re.search(r"\+\s*(identity|residual|feature|x)\b", dilation) is not None, "kb07.edema_dilation.residual_add")
    for value in (1, 2, 4):
        _require(failures, f"dilation={value}" in dilation or f"({value}," in dilation, f"kb07.edema_dilation.{value}")

    injury_tokens = (
        "initialize_injury_classifier_from_stock_mean",
        "stock_class4_class5_mean",
        "class-4/class-5",
    )
    _require(failures, any(token in core for token in injury_tokens), "kb07.injury_classifier.stock_mean_initializer")
    _require(failures, ("class_index=4" in core or "[4]" in core) and ("class_index=5" in core or "[5]" in core), "kb07.injury_classifier.stock_rows_4_5")
    _require(failures, "mean(" in core, "kb07.injury_classifier.mean_operation")


def _check_runtime_receipt_payloads(
    failures: list[str],
    receipt_payloads: dict[str, dict[str, Any]],
    evidence: dict[str, Any],
) -> None:
    runtime_receipts = evidence.get("runtime_receipts", {})
    for name in ("forward_backward_probe", "inference_probe"):
        receipt = receipt_payloads.get(name, {})
        declared = runtime_receipts.get(name, {})
        _require(failures, declared.get("command_sha256") == receipt.get("command_sha256"), f"kb18.{name}.command_sha_bound")
        _require(failures, declared.get("stdout_sha256") == receipt.get("stdout_sha256"), f"kb18.{name}.stdout_sha_bound")
        _require(failures, declared.get("stderr_sha256") == receipt.get("stderr_sha256"), f"kb18.{name}.stderr_sha_bound")

    fb_payload = receipt_payloads.get("forward_backward_probe", {}).get("payload", {})
    _require(failures, fb_payload.get("status") == "PASS", "kb18.forward_backward.payload_status")
    _require(failures, "synthetic" not in str(fb_payload.get("probe_type", "")).lower(), "kb18.forward_backward.not_synthetic")
    _require(failures, fb_payload.get("random_tensor_used") is not True, "kb18.forward_backward.no_random_tensor")
    _require(failures, "random" not in str(fb_payload.get("input_origin", "")).lower(), "kb18.forward_backward.input_origin_not_random")
    _require(failures, bool(fb_payload.get("train_case_ids", {}).get("scar")), "kb13.forward_backward.real_scar_case")
    _require(failures, bool(fb_payload.get("train_case_ids", {}).get("edema_t2_present")), "kb13.forward_backward.real_edema_case")
    _require(failures, bool(fb_payload.get("mixed_batch_no_t2", {}).get("case_id")), "kb08.forward_backward.no_t2_mixed_case")
    loss_terms = fb_payload.get("total_loss_terms", {})
    numeric_denominators: list[int] = []
    for name in REQUIRED_LOSSES:
        term = loss_terms.get(name, {})
        _require(failures, term.get("included_in_total") is True, f"kb13.runtime_loss.{name}.included")
        _require(failures, int(term.get("denominator", 0)) > 0 or term.get("correctly_excluded") is True, f"kb13.runtime_loss.{name}.denominator")
        if isinstance(term.get("denominator"), int):
            numeric_denominators.append(int(term["denominator"]))
        value = term.get("value")
        _require(failures, isinstance(value, (int, float)) and math.isfinite(float(value)), f"kb13.runtime_loss.{name}.finite")
    _require(failures, not numeric_denominators or any(value != 1 for value in numeric_denominators), "kb13.runtime_loss.not_all_constant_one_denominators")
    _require(failures, int(fb_payload.get("constant_denominator_count", 0)) == 0, "kb13.runtime_loss.no_constant_denominator_count")
    no_t2 = fb_payload.get("mixed_batch_no_t2", {})
    _require(failures, int(no_t2.get("edema_owned_module_call_count", -1)) == 0, "kb08.runtime_no_t2.call_count")
    _require(failures, int(no_t2.get("edema_supervision_rows", -1)) == 0, "kb08.runtime_no_t2.supervision")
    _require(failures, float(no_t2.get("edema_parameter_grad_abs_sum", 1.0)) == 0.0, "kb08.runtime_no_t2.grad")

    inf_payload = receipt_payloads.get("inference_probe", {}).get("payload", {})
    _require(failures, inf_payload.get("status") == "PASS", "kb18.inference.payload_status")
    _require(failures, "synthetic" not in str(inf_payload.get("probe_type", "")).lower(), "kb19.inference.not_synthetic")
    _require(failures, bool(inf_payload.get("case_id")), "kb19.inference.real_case_id")
    _require(failures, inf_payload.get("single_tile_path") == inf_payload.get("forced_multi_tile_path"), "kb12.inference.same_canonical_path")
    if "single_tile_call_id" in inf_payload or "forced_multi_tile_call_id" in inf_payload:
        _require(failures, inf_payload.get("single_tile_call_id") != inf_payload.get("forced_multi_tile_call_id"), "kb12.inference.distinct_call_ids")
    _require(failures, inf_payload.get("patch_size_equals_input") is not True, "kb12.inference.patch_not_equal_input")
    if "forced_multi_tile_count" in inf_payload:
        _require(failures, int(inf_payload.get("forced_multi_tile_count", 0)) > 1, "kb12.inference.forced_multi_tile_count")
    try:
        diff = float(inf_payload.get("single_vs_forced_multi_tile_max_abs_diff"))
    except (TypeError, ValueError):
        diff = math.nan
    _require(failures, math.isfinite(diff), "kb12.inference.single_multi_diff_diagnostic_finite")
    _require(failures, int(inf_payload.get("global_bias_application_count", 0)) == 1, "kb12.inference.global_bias_once")

    checkpoint_payload = receipt_payloads.get("checkpoint_resume_probe", {}).get("payload", {})
    _require(failures, checkpoint_payload.get("status") == "PASS", "kb16.checkpoint_resume.payload_status")
    _require(failures, checkpoint_payload.get("schema_version") == 4, "kb16.checkpoint_resume.schema_v4")
    _require(failures, checkpoint_payload.get("request_nonce") == REQUEST_NONCE, "kb16.checkpoint_resume.current_request_nonce")
    _require(
        failures,
        checkpoint_payload.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256,
        "kb16.checkpoint_resume.current_frozen_contract_sha256",
    )
    _require(failures, checkpoint_payload.get("next_step_matches_uninterrupted") is True, "kb16.checkpoint_resume.next_step")
    _require(failures, checkpoint_payload.get("rng_and_cursor_state_matches") is True, "kb16.checkpoint_resume.rng_cursor")

    deployment_payload = receipt_payloads.get("deployment_load_probe", {}).get("payload", {})
    _require(failures, deployment_payload.get("status") == "PASS", "kb22.deployment.payload_status")
    _require(failures, deployment_payload.get("self_contained_load") is True, "kb16.deployment.self_contained")
    _require(failures, deployment_payload.get("opened_stock_checkpoint_after_deployment_load") is False, "kb16.deployment.no_stock_checkpoint")

    evaluator_payload = receipt_payloads.get("evaluator_smoke", {}).get("payload", {})
    _require(failures, evaluator_payload.get("status") == "PASS", "kb19.evaluator.payload_status")
    _require(failures, evaluator_payload.get("same_case_population") is True, "kb19.evaluator.same_cases")
    _require(failures, evaluator_payload.get("same_tta_decode_metric_interface") is True, "kb19.evaluator.same_tta_decode_metrics")
    _require(failures, REQUIRED_METRICS.issubset(set(evaluator_payload.get("metrics", []))), "kb24.evaluator.metrics")

    hard_negative_payload = receipt_payloads.get("hard_negative_binding", {}).get("payload", {})
    _require(failures, hard_negative_payload.get("status") == "PASS", "kb14.hard_negative.payload_status")
    _require(failures, str(hard_negative_payload.get("case_id", "")).startswith("synthetic_") is False, "kb14.hard_negative.real_case")
    _require(failures, hard_negative_payload.get("oof_prediction_bound") is True, "kb14.hard_negative.oof_prediction")
    for field in ("mask_sha256", "coordinate_sha256", "checkpoint_sha256", "grid_sha256"):
        _require(failures, _is_sha256(hard_negative_payload.get(field)), f"kb14.hard_negative.{field}")


def _load_verification_artifact(failures: list[str], name: str, filename: str) -> dict[str, Any] | None:
    path = VERIFICATION_DIR / filename
    if not path.is_file():
        failures.append(f"verifier_owned.{name}.missing")
        return None
    try:
        return load_json(path)
    except Exception as exc:  # pragma: no cover - reported as validation failure.
        failures.append(f"verifier_owned.{name}.invalid_json:{type(exc).__name__}")
        return None


def _check_verifier_owned_execution(failures: list[str], evidence: dict[str, Any]) -> None:
    executable = _load_verification_artifact(failures, "executable_verifier_receipt", "executable_verifier_receipt.json")
    mutation_manifest = _load_verification_artifact(failures, "runtime_mutation_manifest", "runtime_mutation_manifest.json")
    transaction_receipt = _load_verification_artifact(failures, "transaction_gate_receipt", "transaction_gate_receipt.json")

    if executable is not None:
        _require(failures, executable.get("schema") == "CARE_ASE_FAITHFUL_EXECUTABLE_VERIFIER_RECEIPT_V1", "verifier_owned.executable.schema")
        _require(failures, executable.get("task_id") == TASK_ID, "verifier_owned.executable.task_id")
        _require(failures, executable.get("request_nonce") == REQUEST_NONCE, "verifier_owned.executable.request_nonce")
        _require(failures, executable.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256, "verifier_owned.executable.frozen_contract_sha256")
        _require(failures, executable.get("review_round") == REVIEW_ROUND, "verifier_owned.executable.review_round")
        _require(failures, executable.get("planner_review_commit") == PLANNER_REVIEW_COMMIT, "verifier_owned.executable.planner_review_commit")
        _require(failures, executable.get("integration_sha") == REVIEWED_INTEGRATION_COMMIT, "verifier_owned.executable.integration_sha")
        _require(
            failures,
            executable.get("implementation_fingerprint_sha256") == REVIEWED_IMPLEMENTATION_FINGERPRINT,
            "verifier_owned.executable.implementation_fingerprint",
        )
        _require(
            failures,
            executable.get("reviewed_verifier_fingerprint_sha256_at_repair_start") == REVIEWED_VERIFIER_FINGERPRINT,
            "verifier_owned.executable.reviewed_verifier_fingerprint",
        )
        _require(failures, _is_sha256(executable.get("verifier_source_fingerprint_sha256")), "verifier_owned.executable.verifier_source_fingerprint")
        _require(failures, executable.get("passed") is True, "verifier_owned.executable.passed")
        _require(failures, executable.get("status") == "PASS", "verifier_owned.executable.status")
        _require(failures, executable.get("fixture_mode") is not True, "verifier_owned.executable.not_fixture")
        _require(failures, executable.get("runtime_conclusion_source") == "verifier_owned_independent_execution", "verifier_owned.executable.conclusion_source")
        _require(failures, executable.get("executor_receipts_used_as_runtime_conclusion") is False, "verifier_owned.executable.no_receipt_replay")
        _require(failures, executable.get("formal_training_started") is False, "verifier_owned.executable.no_training")
        _require(failures, executable.get("outer_accessed") is False, "verifier_owned.executable.no_outer")
        _require(failures, executable.get("docker_or_upload") is False, "verifier_owned.executable.no_docker_upload")
        environment = executable.get("environment", {})
        if isinstance(environment, dict):
            _require(failures, environment.get("torch_available") is True, "verifier_owned.executable.torch_available")
            _require(failures, environment.get("nnunetv2_available") is True, "verifier_owned.executable.nnunetv2_available")
            _require(failures, str(environment.get("python_executable", "")).endswith("/envs/env_CARE/bin/python"), "verifier_owned.executable.care_runtime_python")
        else:
            failures.append("verifier_owned.executable.environment")
        receipt_sha = executable.get("executable_verifier_receipt_sha256")
        if _is_sha256(receipt_sha):
            _require(
                failures,
                receipt_sha == _payload_sha_without_self(executable, "executable_verifier_receipt_sha256"),
                "verifier_owned.executable.sha_recomputed",
            )
        else:
            failures.append("verifier_owned.executable.sha_shape")
        runtime_bindings = executable.get("runtime_receipt_bindings")
        evidence_receipt_paths = evidence.get("receipt_paths")
        _require(failures, isinstance(runtime_bindings, dict), "verifier_owned.executable.runtime_bindings")
        _require(failures, isinstance(evidence_receipt_paths, dict), "verifier_owned.executable.evidence_receipt_paths")
        if isinstance(runtime_bindings, dict) and isinstance(evidence_receipt_paths, dict):
            for name, declared in sorted(evidence_receipt_paths.items()):
                bound = runtime_bindings.get(name)
                if not isinstance(bound, dict):
                    failures.append(f"verifier_owned.executable.runtime_binding_missing:{name}")
                    continue
                _require(failures, bound.get("declared_path") == declared, f"verifier_owned.executable.runtime_binding_path:{name}")
                artifact_path = _resolve_artifact(declared)
                if artifact_path is None or not artifact_path.is_file():
                    failures.append(f"verifier_owned.executable.runtime_binding_artifact_missing:{name}")
                elif _is_sha256(bound.get("sha256")):
                    _require(
                        failures,
                        bound.get("sha256") == _sha256_file(artifact_path),
                        f"verifier_owned.executable.runtime_binding_sha:{name}",
                    )
                else:
                    failures.append(f"verifier_owned.executable.runtime_binding_sha_shape:{name}")
        probe_names = {str(probe.get("name")) for probe in executable.get("probes", []) if isinstance(probe, dict)}
        _require(failures, REQUIRED_EXECUTABLE_PROBES.issubset(probe_names), "verifier_owned.executable.required_probes")
        by_name = {str(probe.get("name")): probe for probe in executable.get("probes", []) if isinstance(probe, dict)}
        loss_probe = by_name.get("real_train_case_total_loss_forward_backward", {})
        _require(failures, loss_probe.get("random_tensor_used") is False, "verifier_owned.executable.no_random_tensor_input")
        _require(failures, int(loss_probe.get("constant_denominator_count", 1)) == 0, "verifier_owned.executable.no_constant_loss_denominators")
        loss_semantic = by_name.get("loss_semantic_oracle", {})
        _require(failures, loss_semantic.get("status") == "PASS", "verifier_owned.loss_semantic.status")
        _require(
            failures,
            loss_semantic.get("reference_uses_implementation_loss_helper") is False,
            "verifier_owned.loss_semantic.independent_reference",
        )
        injury_semantic = loss_semantic.get("injury_dice_bce", {}) if isinstance(loss_semantic.get("injury_dice_bce"), dict) else {}
        scar_semantic = (
            loss_semantic.get("scar_component_adaptive_tversky", {})
            if isinstance(loss_semantic.get("scar_component_adaptive_tversky"), dict)
            else {}
        )
        unique_loss_set = (
            loss_semantic.get("unique_allowed_loss_set", {})
            if isinstance(loss_semantic.get("unique_allowed_loss_set"), dict)
            else {}
        )
        _require(failures, injury_semantic.get("matches_reference") is True, "verifier_owned.loss_semantic.injury_dice_bce_formula")
        _require(failures, injury_semantic.get("t2_gated") is True, "verifier_owned.loss_semantic.injury_t2_gated")
        _require(
            failures,
            scar_semantic.get("matches_reference") is True,
            "verifier_owned.loss_semantic.scar_component_tversky_formula",
        )
        _require(
            failures,
            scar_semantic.get("unauthorized_occupancy_objective_detected") is False,
            "verifier_owned.loss_semantic.no_scar_occupancy_hidden_auxiliary",
        )
        _require(failures, unique_loss_set.get("matches_contract_terms") is True, "verifier_owned.loss_semantic.unique_allowed_terms")
        _require(
            failures,
            unique_loss_set.get("total_matches_allowed_weighted_sum") is True,
            "verifier_owned.loss_semantic.total_allowed_weighted_sum",
        )
        _require(
            failures,
            unique_loss_set.get("no_extra_weighted_auxiliary_objective") is True,
            "verifier_owned.loss_semantic.no_extra_weighted_auxiliary",
        )
        tile_probe = by_name.get("single_vs_forced_multi_tile_full_volume", {})
        _require(failures, tile_probe.get("calls_are_distinct") is True, "verifier_owned.executable.single_multi_distinct_calls")
        _require(failures, tile_probe.get("patch_size_equals_input") is False, "verifier_owned.executable.patch_smaller_than_input")
        _require(failures, int(tile_probe.get("forced_multi_tile_count", 0)) > 1, "verifier_owned.executable.forced_multi_tile_count")
        _require(
            failures,
            int(tile_probe.get("forced_model_forward_count", 0)) == int(tile_probe.get("expected_model_forward_count", -1)),
            "verifier_owned.executable.tile_forward_count",
        )
        _require(failures, tile_probe.get("model_input_spatial_within_declared_patch") is True, "verifier_owned.executable.tile_forward_patch_limited")
        _require(failures, tile_probe.get("full_support_pseudo_tiling_detected") is False, "verifier_owned.executable.no_full_support_pseudo_tiling")
        _require(failures, int(tile_probe.get("global_bias_application_count", 0)) == 1, "verifier_owned.executable.global_bias_once")
        _require(failures, tile_probe.get("canonical_settings_has_no_context_override") is True, "verifier_owned.executable.no_probe_only_context_override")
        _require(failures, tile_probe.get("observed_error") in (None, ""), "verifier_owned.executable.no_multitile_runtime_error")
        tile_instrumentation = by_name.get("tile_local_forward_instrumentation", {})
        _require(failures, int(tile_instrumentation.get("forced_multi_tile_count", 0)) > 1, "verifier_owned.executable.instrumented_tile_count")
        _require(
            failures,
            int(tile_instrumentation.get("forced_model_forward_count", 0)) == int(tile_instrumentation.get("expected_model_forward_count", -1)),
            "verifier_owned.executable.instrumented_forward_count",
        )
        _require(
            failures,
            int(tile_instrumentation.get("no_t2_forced_model_forward_count", 0)) == int(tile_instrumentation.get("expected_model_forward_count", -1)),
            "verifier_owned.executable.instrumented_no_t2_forward_count",
        )
        _require(failures, tile_instrumentation.get("model_input_spatial_within_declared_patch") is True, "verifier_owned.executable.instrumented_patch_limit")
        _require(failures, tile_instrumentation.get("full_support_pseudo_tiling_detected") is False, "verifier_owned.executable.instrumented_no_full_support")
        _require(failures, int(tile_instrumentation.get("global_bias_application_count", 0)) == 1, "verifier_owned.executable.instrumented_global_bias_once")
        _require(failures, int(tile_instrumentation.get("no_t2_global_bias_application_count", 0)) == 1, "verifier_owned.executable.instrumented_no_t2_global_bias_once")
        _require(failures, tile_instrumentation.get("tile_outputs_limited_to_base_logits_wall_extent_evidence") is True, "verifier_owned.executable.instrumented_tile_output_scope")
        authority_probe = by_name.get("required_module_final_authority_oracle", {})
        _require(failures, authority_probe.get("implementation_disable_flags_treated_as_authority") is False, "verifier_owned.authority.no_disable_flag_authority")
        _require(failures, authority_probe.get("all_required_groups_have_verifier_owned_delta") is True, "verifier_owned.authority.required_group_delta")
        _require(failures, authority_probe.get("all_implementation_flags_match_verifier_owned_removal") is True, "verifier_owned.authority.flag_matches_verifier_removal")
        _require(failures, authority_probe.get("no_disable_flag_final_logit_contribution") is True, "verifier_owned.authority.no_disable_flag_final_logit_contribution")
        _require(failures, not authority_probe.get("disable_flag_final_logit_contribution_sites"), "verifier_owned.authority.no_disable_flag_contribution_sites")
        _require(failures, authority_probe.get("required_named_projection_sources_present") is True, "verifier_owned.authority.named_sources_present")
        _require(failures, not authority_probe.get("missing_required_group_sources"), "verifier_owned.authority.no_missing_group_sources")
        _require(failures, authority_probe.get("named_projection_final_logit_gradient_sources_present") is True, "verifier_owned.authority.named_projection_gradient_sources_present")
        _require(failures, authority_probe.get("named_projection_final_logit_gradient_nonzero") is True, "verifier_owned.authority.named_projection_gradient_nonzero")
        _require(failures, not authority_probe.get("missing_named_projection_gradient_sources"), "verifier_owned.authority.no_missing_named_projection_gradients")
        _require(failures, not authority_probe.get("zero_named_projection_gradient_sources"), "verifier_owned.authority.no_zero_named_projection_gradients")
        _require(failures, authority_probe.get("rejects_receipt_only_authority") is True, "verifier_owned.authority.rejects_receipt_only")
        step0_probe = by_name.get("step0_parity_report_regression", {})
        _require(failures, step0_probe.get("imported_step0_parity_report") is True, "verifier_owned.step0.imported")
        _require(failures, step0_probe.get("attribute_error_ignored") is False, "verifier_owned.step0.no_attribute_error_ignore")
        _require(failures, float(step0_probe.get("t2_present_stock_max_abs_err", 1.0)) <= 1e-6, "verifier_owned.step0.t2_present_parity")
        _require(failures, float(step0_probe.get("no_t2_stock_max_abs_err", 1.0)) <= 1e-6, "verifier_owned.step0.no_t2_parity")
        _require(failures, int(step0_probe.get("compatible_argmax_changed_voxels", 1)) == 0, "verifier_owned.step0.argmax")
        _require(failures, int(step0_probe.get("no_t2_edema_owned_module_call_count", 1)) == 0, "verifier_owned.step0.no_t2_edema_calls")
        _require(failures, step0_probe.get("no_t2_class4_in_competition") is False, "verifier_owned.step0.no_t2_class4_excluded")
        partial_probe = by_name.get("partial_hw_extent_zero_contribution", {})
        _require(failures, partial_probe.get("loss_matches_fully_valid_reference") is True, "verifier_owned.partial_hw.scalar_matches_reference")
        _require(failures, float(partial_probe.get("actual_scalar_loss", 0.0)) > 0.0, "verifier_owned.partial_hw.actual_scalar_nonzero")
        _require(failures, float(partial_probe.get("reference_fully_valid_only_loss", 0.0)) > 0.0, "verifier_owned.partial_hw.reference_nonzero")
        _require(failures, float(partial_probe.get("partial_hw_presence_denominator_contribution", 1.0)) == 0.0, "verifier_owned.partial_hw.presence_denominator_zero")
        _require(failures, float(partial_probe.get("partial_hw_area_denominator_contribution", 1.0)) == 0.0, "verifier_owned.partial_hw.area_denominator_zero")
        _require(failures, float(partial_probe.get("partial_hw_extent_head_grad_abs_sum", 1.0)) == 0.0, "verifier_owned.partial_hw.grad_zero")
        _require(failures, float(partial_probe.get("partial_hw_extent_bias_abs_sum", 1.0)) == 0.0, "verifier_owned.partial_hw.bias_zero")
        _require(failures, float(partial_probe.get("full_neighbor_extent_head_grad_abs_sum", 0.0)) > 0.0, "verifier_owned.partial_hw.full_neighbor_grad_active")
        _require(failures, float(partial_probe.get("full_neighbor_extent_bias_abs_sum", 0.0)) > 0.0, "verifier_owned.partial_hw.full_neighbor_bias_active")
        _require(failures, partial_probe.get("straight_through_zero_loss_detected") is False, "verifier_owned.partial_hw.no_straight_through_zero")
        reference_probe = by_name.get("partial_hw_extent_reference_objective", {})
        _require(failures, reference_probe.get("loss_matches_fully_valid_reference") is True, "verifier_owned.partial_hw.reference_probe_matches")
        _require(failures, float(reference_probe.get("full_neighbor_extent_head_grad_abs_sum", 0.0)) > 0.0, "verifier_owned.partial_hw.reference_probe_full_grad")
        cross_z_probe = by_name.get("partial_hw_slice_extent_head_cross_z_gradient", {})
        _require(failures, cross_z_probe.get("uses_real_slice_extent_head") is True, "verifier_owned.partial_hw.cross_z_real_slice_extent_head")
        _require(failures, cross_z_probe.get("loss_applied_only_to_fully_valid_neighbor") is True, "verifier_owned.partial_hw.cross_z_neighbor_only_objective")
        _require(failures, cross_z_probe.get("cross_z_partial_feature_gradient_zero") is True, "verifier_owned.partial_hw.cross_z_partial_feature_grad_zero")
        _require(failures, cross_z_probe.get("full_neighbor_gradient_nonzero") is True, "verifier_owned.partial_hw.cross_z_full_neighbor_grad_nonzero")
        _require(failures, float(cross_z_probe.get("partial_hw_input_feature_grad_abs_sum", 1.0)) == 0.0, "verifier_owned.partial_hw.cross_z_partial_feature_grad_abs_zero")
        _require(failures, float(cross_z_probe.get("full_neighbor_input_feature_grad_abs_sum", 0.0)) > 0.0, "verifier_owned.partial_hw.cross_z_full_neighbor_feature_grad_abs_nonzero")

        checkpoint_probe = by_name.get("schema_v4_checkpoint_resume", {})
        _require(failures, checkpoint_probe.get("current_request_nonce_bound") is True, "verifier_owned.checkpoint.current_request_nonce")
        _require(failures, checkpoint_probe.get("current_frozen_contract_sha256_bound") is True, "verifier_owned.checkpoint.current_frozen_contract_sha256")

    if transaction_receipt is not None:
        _require(failures, transaction_receipt.get("schema") == "CARE_ASE_FAITHFUL_TRANSACTION_GATE_RECEIPT_V1", "verifier_owned.transaction.schema")
        _require(failures, transaction_receipt.get("review_round") == REVIEW_ROUND, "verifier_owned.transaction.review_round")
        _require(failures, transaction_receipt.get("planner_review_commit") == PLANNER_REVIEW_COMMIT, "verifier_owned.transaction.planner_review_commit")
        _require(failures, transaction_receipt.get("integration_sha") == REVIEWED_INTEGRATION_COMMIT, "verifier_owned.transaction.integration_sha")
        _require(
            failures,
            transaction_receipt.get("implementation_fingerprint_sha256") == REVIEWED_IMPLEMENTATION_FINGERPRINT,
            "verifier_owned.transaction.implementation_fingerprint",
        )
        _require(
            failures,
            transaction_receipt.get("reviewed_verifier_fingerprint_sha256_at_repair_start") == REVIEWED_VERIFIER_FINGERPRINT,
            "verifier_owned.transaction.reviewed_verifier_fingerprint",
        )
        _require(failures, _is_sha256(transaction_receipt.get("verifier_source_fingerprint_sha256")), "verifier_owned.transaction.verifier_source_fingerprint")
        _require(failures, _is_sha256(transaction_receipt.get("executable_verifier_receipt_sha256")), "verifier_owned.transaction.executable_receipt_sha")
        _require(failures, transaction_receipt.get("status") == "PASS", "verifier_owned.transaction.status")
        _require(failures, not transaction_receipt.get("failures"), "verifier_owned.transaction.no_failures")
        _require(failures, transaction_receipt.get("hosted_ci_conclusion") == "success", "verifier_owned.transaction.hosted_ci_success")
        _require(failures, transaction_receipt.get("hosted_ci_head_sha") == transaction_receipt.get("ci_checked_commit_sha"), "verifier_owned.transaction.hosted_ci_head_matches_checked_commit")
        _require(
            failures,
            transaction_receipt.get("hosted_ci_head_sha") == REVIEWED_INTEGRATION_COMMIT
            and transaction_receipt.get("ci_checked_commit_sha") == REVIEWED_INTEGRATION_COMMIT,
            "verifier_owned.transaction.hosted_ci_exact_reviewed_integration",
        )
        _require(failures, transaction_receipt.get("planner_packet_sha") == REVIEWED_INTEGRATION_COMMIT, "verifier_owned.transaction.planner_packet_bound_to_reviewed_integration")
        _require(failures, _is_sha256(transaction_receipt.get("runtime_manifest_sha")), "verifier_owned.transaction.runtime_manifest_sha")
        _require(failures, transaction_receipt.get("stale_planner_reused_after_key_commit") is False, "verifier_owned.transaction.no_stale_planner_reuse")

    if mutation_manifest is not None:
        _require(failures, mutation_manifest.get("schema") == "CARE_ASE_FAITHFUL_RUNTIME_MUTATION_MANIFEST_V1", "verifier_owned.mutations.schema")
        _require(failures, mutation_manifest.get("task_id") == TASK_ID, "verifier_owned.mutations.task_id")
        _require(failures, mutation_manifest.get("request_nonce") == REQUEST_NONCE, "verifier_owned.mutations.request_nonce")
        _require(failures, mutation_manifest.get("review_round") == REVIEW_ROUND, "verifier_owned.mutations.review_round")
        invocations = mutation_manifest.get("mutation_invocations", [])
        ids = {str(item.get("mutation_id")) for item in invocations if isinstance(item, dict)}
        _require(failures, REQUIRED_EXECUTABLE_MUTATION_IDS.issubset(ids), "verifier_owned.mutations.required_ids")
        _require(failures, mutation_manifest.get("all_returned_nonzero") is True, "verifier_owned.mutations.all_nonzero")
        for item in invocations:
            mutation_id = item.get("mutation_id")
            _require(failures, item.get("exit_code") != 0, f"verifier_owned.mutations.nonzero:{mutation_id}")
            for field in ("command_sha256", "stdout_sha256", "stderr_sha256", "report_sha256"):
                _require(failures, _is_sha256(item.get(field)), f"verifier_owned.mutations.{field}:{mutation_id}")
            report_path = _resolve_artifact(item.get("report_path"))
            if report_path is None or not report_path.is_file():
                failures.append(f"verifier_owned.mutations.report_missing:{mutation_id}")
            elif _is_sha256(item.get("report_sha256")):
                _require(failures, item.get("report_sha256") == _sha256_file(report_path), f"verifier_owned.mutations.report_hash:{mutation_id}")
                report = load_json(report_path)
                _require(failures, report.get("fixture_mode") is False, f"verifier_owned.mutations.not_fixture:{mutation_id}")
                _require(failures, report.get("mutation_executed") is True, f"verifier_owned.mutations.executed:{mutation_id}")
                _require(failures, isinstance(report.get("mutation_applied"), str) and report.get("mutation_applied"), f"verifier_owned.mutations.applied:{mutation_id}")
                _require(failures, _is_sha256(report.get("mutated_fingerprint_sha256")), f"verifier_owned.mutations.mutated_fingerprint:{mutation_id}")
                _require(failures, int(report.get("failure_count", 0)) > 0, f"verifier_owned.mutations.failure_count:{mutation_id}")


def _check_artifact_bindings(
    failures: list[str],
    evidence: dict[str, Any],
    *,
    root: Path = ROOT,
    require_artifacts: bool = True,
) -> None:
    if not require_artifacts:
        return
    receipt_paths = evidence.get("receipt_paths")
    if not isinstance(receipt_paths, dict):
        failures.append("artifact_binding.receipt_paths.missing")
        return
    for name in sorted(REQUIRED_RECEIPT_PATHS):
        if name not in receipt_paths:
            failures.append(f"artifact_binding.receipt_paths.missing:{name}")

    source_manifest_path, source_manifest = _load_artifact(failures, receipt_paths, "source_manifest", root=root)
    if source_manifest_path is not None and source_manifest is not None:
        _check_source_manifest_and_topology(failures, source_manifest_path, source_manifest, evidence, root=root)

    receipt_payloads: dict[str, dict[str, Any]] = {}
    for name in sorted(REQUIRED_RECEIPT_PATHS - {"source_manifest", "static_architecture_checks", "architecture_signature", "parameter_owner_registry"}):
        path, payload = _load_artifact(failures, receipt_paths, name, root=root)
        if path is None or payload is None:
            continue
        receipt_payloads[name] = payload
        _require(failures, payload.get("task_id") == TASK_ID, f"artifact_binding.{name}.task_id")
        _require(failures, payload.get("request_nonce") == REQUEST_NONCE, f"artifact_binding.{name}.request_nonce")
        _require(failures, payload.get("executed") is True, f"artifact_binding.{name}.executed")
        _require(failures, payload.get("exit_code") == 0, f"artifact_binding.{name}.exit_code")
        _require(failures, payload.get("zero_credit") is True, f"artifact_binding.{name}.zero_credit")
        _require(failures, payload.get("formal_training_started") is False, f"artifact_binding.{name}.no_training")
        _require(failures, payload.get("outer_accessed") is False, f"artifact_binding.{name}.no_outer")
        if "command" in payload:
            _require(failures, payload.get("command_sha256") == _json_sha(payload["command"]), f"artifact_binding.{name}.command_sha")
        if "payload" in payload:
            expected_stdout = json.dumps(payload["payload"], indent=2, sort_keys=True, default=str).encode("utf-8")
            stdout_path = path.with_name(path.name.replace("_receipt.json", "_stdout.json"))
            if stdout_path.is_file():
                _require(
                    failures,
                    payload.get("stdout_sha256") in {_sha256_file(stdout_path), _sha256_bytes(expected_stdout)},
                    f"artifact_binding.{name}.stdout_file_sha",
                )
            else:
                _require(failures, payload.get("stdout_sha256") == _sha256_bytes(expected_stdout), f"artifact_binding.{name}.stdout_payload_sha")
        _require(failures, payload.get("stderr_sha256") == _sha256_bytes(b""), f"artifact_binding.{name}.stderr_empty_sha")

    for name in ("static_architecture_checks", "architecture_signature", "parameter_owner_registry"):
        path, payload = _load_artifact(failures, receipt_paths, name, root=root)
        if path is None or payload is None:
            continue
        field = f"{name}_sha256"
        if field in payload:
            _require(failures, payload[field] == _payload_sha_without_self(payload, field), f"artifact_binding.{name}.sha_recomputed")
            _require(failures, evidence.get(field) == payload[field], f"artifact_binding.{name}.evidence_sha")

    _check_runtime_receipt_payloads(failures, receipt_payloads, evidence)
    _check_verifier_owned_execution(failures, evidence)


def validate_evidence(
    evidence: dict[str, Any],
    verification_contract: dict[str, Any] | None = None,
    *,
    require_artifacts: bool = True,
) -> list[str]:
    failures: list[str] = []
    _require(failures, evidence.get("task_id") == TASK_ID, "binding.task_id")
    _require(failures, evidence.get("request_nonce") == REQUEST_NONCE, "binding.request_nonce")
    _require(
        failures,
        evidence.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256,
        "binding.frozen_contract_sha256",
    )
    if verification_contract is not None:
        _require(
            failures,
            verification_contract.get("frozen_contract_sha256") == FROZEN_CONTRACT_SHA256,
            "verification_contract.frozen_contract_sha256",
        )
        _require(failures, len(verification_contract.get("protected_known_bad_categories", [])) == 24, "verification_contract.known_bad_count")

    try:
        receipts = _get(evidence, "role_receipts")
        for field in ("thread_id", "codex_home", "worktree"):
            values = [receipts[role][field] for role in ("controller", "verifier", "executor")]
            _require(failures, len(set(values)) == 3, f"kb01.{field}_unique")
    except KeyError as exc:
        failures.append(f"kb01.missing:{exc}")

    trunk = _get(evidence, "architecture.stock_trunk")
    for field in (
        "encoder_byte_coverage",
        "bottleneck_byte_coverage",
        "decoder_byte_coverage",
        "deep_supervision_head_byte_coverage",
    ):
        _require(failures, float(trunk.get(field, 0.0)) >= 0.99, f"kb02.{field}")
    _require(failures, trunk.get("channels_from_plan_introspection") is True, "kb02.channels_from_plan_introspection")
    _require(failures, trunk.get("decoder_reset") is False, "kb02.decoder_reset")
    _require(failures, trunk.get("channels_shrunk") is False, "kb02.channels_shrunk")
    _require(failures, trunk.get("trunk_permanently_frozen") is False, "kb02.trunk_permanently_frozen")
    _require(failures, float(trunk.get("stock_compatible_logits_max_abs_err", 1.0)) <= 1e-6, "kb02.stock_compatible_logits")
    _require(failures, int(trunk.get("stock_compatible_argmax_changed_voxels", 1)) == 0, "kb02.stock_compatible_argmax")
    _require(
        failures,
        trunk.get("encoder_and_shared_low_mid_decoder_run_once") is True,
        "kb02.encoder_shared_decoder_single_run",
    )

    decoders = _get(evidence, "architecture.pathology_decoders")
    _require(failures, decoders.get("scar_highest_two_scale_independent_decoder") is True, "kb03.scar_decoder")
    _require(failures, decoders.get("edema_highest_two_scale_independent_decoder") is True, "kb03.edema_decoder")
    _require(failures, decoders.get("d0_shallow_head_substitute") is False, "kb03.d0_shallow_head_substitute")
    _require(failures, decoders.get("stock_class4_5_normal_forward_shortcut") is False, "kb04.stock_shortcut")
    _require(failures, decoders.get("scar_context_logits_enter_final_path") is True, "kb09.scar_context_final_path")
    _require(failures, decoders.get("edema_context_logits_enter_final_path") is True, "kb09.edema_context_final_path")

    authority = _get(evidence, "architecture.required_module_authority")
    for name, value in authority.items():
        _require(failures, value is True, f"kb05.{name}")

    mechanisms = _get(evidence, "architecture.forbidden_mechanisms")
    for name, value in mechanisms.items():
        _require(failures, value is False, f"kb10.{name}")

    truth = _get(evidence, "architecture.single_truth")
    _require(failures, truth.get("legacy_imports_are_thin_forwarders") is True, "kb22.legacy_imports_are_thin_forwarders")
    _require(failures, truth.get("monolith_runnable") is False, "kb23.monolith_runnable")
    _require(failures, truth.get("duplicate_runtime_truth") is False, "kb23.duplicate_runtime_truth")

    modalities = _get(evidence, "modalities_and_gradients")
    _require(failures, modalities.get("adapters_active_initialized") is True, "kb06.adapters_active_initialized")
    _require(failures, modalities.get("adapter_and_projection_double_zero") is False, "kb06.double_zero")
    _require(failures, modalities.get("scar_uses_lge_primary") is True, "kb07.scar_lge_primary")
    _require(failures, modalities.get("scar_uses_c0_auxiliary") is True, "kb07.scar_c0_auxiliary")
    _require(failures, modalities.get("scar_uses_t2") is False, "kb07.scar_uses_t2")
    _require(failures, modalities.get("edema_uses_t2_primary") is True, "kb07.edema_t2_primary")
    _require(failures, modalities.get("edema_uses_c0_auxiliary") is True, "kb07.edema_c0_auxiliary")
    _require(failures, modalities.get("edema_uses_lge_weak_context") is True, "kb07.edema_lge_weak_context")
    _require(failures, abs(float(modalities.get("scar_c0_gate_initial_output", -1.0)) - 0.2) < 1e-6, "kb07.scar_c0_gate")
    _require(failures, abs(float(modalities.get("edema_c0_gate_initial_output", -1.0)) - 0.2) < 1e-6, "kb07.edema_c0_gate")
    _require(failures, abs(float(modalities.get("edema_lge_gate_initial_output", -1.0)) - 0.05) < 1e-6, "kb07.edema_lge_gate")
    _require(failures, modalities.get("named_zero_residual_projections") is True, "kb06.named_zero_residual_projections")
    _require(
        failures,
        modalities.get("first_backward_required_projection_grad_nonzero_finite") is True,
        "kb06.first_backward_grad",
    )
    _require(
        failures,
        modalities.get("second_backward_adapter_gate_context_grad_nonzero_finite") is True,
        "kb06.second_backward_grad",
    )

    no_t2 = _get(evidence, "no_t2_semantics")
    _require(failures, int(no_t2.get("edema_owned_module_call_count", -1)) == 0, "kb08.edema_call_count")
    _require(failures, int(no_t2.get("edema_supervision_rows", -1)) == 0, "kb08.edema_supervision")
    _require(failures, int(no_t2.get("edema_negative_rows", -1)) == 0, "kb08.edema_negative")
    _require(failures, float(no_t2.get("edema_parameter_grad_abs_sum", 1.0)) == 0.0, "kb08.edema_gradient")
    _require(failures, no_t2.get("class4_in_softmax_dice_argmax_denominator") is False, "kb08.class4_competition")
    _require(failures, no_t2.get("class5_decode_remaps_to_official_label5") is True, "kb08.class5_remap")
    _require(failures, no_t2.get("mixed_batch_safe_scatter") is True, "kb08.mixed_batch_scatter")

    context = _get(evidence, "context_and_extent")
    for field in (
        "anatomy_context_detached_before_pathology",
        "context_soft_wall_extent_have_final_authority",
        "full_case_extent_targets",
        "invalid_padding_partial_hw_bias_zero",
        "presence_area_validity_separate",
        "training_inference_compute_slice_extent_statistics_shared",
        "tile_outputs_base_logits_only",
        "global_bias_applied_once_after_aggregation",
        "single_tile_multi_tile_same_path",
    ):
        code = "kb09" if "authority" in field else "kb11" if "extent" in field or "bias" in field or "validity" in field else "kb12"
        _require(failures, context.get(field) is True, f"{code}.{field}")
    _require(failures, context.get("ramp_formula") == "piecewise_0_500_2000_or_deploy", "kb17.ramp_formula")

    losses = _get(evidence, "losses")
    terms = losses.get("terms", {})
    for name, weight in REQUIRED_LOSSES.items():
        term = terms.get(name, {})
        _require(failures, abs(float(term.get("weight", -1.0)) - weight) < 1e-8, f"kb13.{name}.weight")
        _require(failures, term.get("included_in_total") is True, f"kb13.{name}.included")
    _require(failures, losses.get("zero_denominator_claims_coverage") is False, "kb13.zero_denominator_claims_coverage")
    _require(failures, losses.get("per_loss_denominators_reported") is True, "kb13.denominators_reported")
    _require(failures, losses.get("eligible_row_voxel_normalization") is True, "kb13.eligible_normalization")
    _require(failures, losses.get("fp32_sensitive_reductions") is True, "kb13.fp32_reductions")

    sampler = _get(evidence, "sampler_and_hard_negatives")
    _require(failures, sampler.get("scar_sampler_percentages") == [35, 20, 20, 15, 10], "kb14.scar_sampler")
    _require(failures, sampler.get("edema_sampler_percentages") == [35, 20, 20, 15, 10], "kb14.edema_sampler")
    _require(failures, int(sampler.get("no_t2_edema_event_count", -1)) == 0, "kb08.no_t2_edema_events")
    hard_negative = sampler.get("hard_negative_binding", {})
    for field in ("mask_sha256", "coordinate_sha256", "checkpoint_sha256", "grid_sha256"):
        _require(failures, _is_sha256(hard_negative.get(field)), f"kb14.{field}")
    _require(failures, bool(hard_negative.get("case_id")), "kb14.case_id")
    for item in sampler.get("requested_resolved_mismatches", []):
        _require(failures, item.get("recorded") is True, "kb15.unrecorded_mismatch")

    checkpoint = _get(evidence, "checkpoint_and_resume")
    _require(failures, int(checkpoint.get("schema_version", 0)) == 4, "kb16.schema_version")
    _require(failures, checkpoint.get("self_contained_deployment") is True, "kb16.self_contained_deployment")
    _require(failures, checkpoint.get("cross_fold_resume_rejected") is True, "kb16.cross_fold_resume")
    _require(failures, checkpoint.get("contract_manifest_environment_drift_rejected") is True, "kb16.drift_rejected")
    _require(failures, checkpoint.get("reload_next_step_matches_uninterrupted") is True, "kb16.reload_next_step")
    _require(failures, checkpoint.get("reload_validation_advances_training_rng") is False, "kb16.reload_rng_advanced")
    _require(failures, checkpoint.get("nonfinite_blocks_optimizer_commit") is True, "kb16.nonfinite_block")
    _require(failures, checkpoint.get("early_checkpoint_uses_saved_step_ramp") is True, "kb17.saved_step_ramp")
    _require(failures, checkpoint.get("early_checkpoint_uses_final_step_ramp") is False, "kb17.final_step_ramp")

    receipts = _get(evidence, "runtime_receipts")
    _require(failures, receipts.get("canned_without_execution") is False, "kb18.canned_receipt")
    for receipt_name in ("forward_backward_probe", "inference_probe"):
        receipt = receipts.get(receipt_name, {})
        _require(failures, receipt.get("executed") is True, f"kb18.{receipt_name}.executed")
        _require(failures, receipt.get("exit_code") == 0, f"kb18.{receipt_name}.exit_code")
        for field in ("command_sha256", "stdout_sha256", "stderr_sha256"):
            _require(failures, _is_sha256(receipt.get(field)), f"kb18.{receipt_name}.{field}")

    evaluation = _get(evidence, "evaluation_interface")
    _require(failures, evaluation.get("canonical_full_volume_only") is True, "kb19.full_volume_only")
    _require(failures, evaluation.get("patch_proxy_evaluator") is False, "kb19.patch_proxy")
    _require(failures, evaluation.get("fair_baseline_same_cases_tta_decode_population") is True, "kb19.fair_baseline")
    _require(failures, REQUIRED_METRICS.issubset(set(evaluation.get("metrics", []))), "kb24.required_metrics")

    training = _get(evidence, "formal_training_accounting")
    if training.get("claims_formal_training") is True:
        _require(failures, int(training.get("completed_optimizer_steps", 0)) >= 14000, "kb20.completed_optimizer_steps")
        _require(failures, set(training.get("visited_stages", [])) == {"A", "B", "C"}, "kb20.visited_stages")
        _require(failures, training.get("pending_or_preempted_counted") is False, "kb20.pending_preempted_counted")
        _require(failures, training.get("stage_b_or_c_skipped") is False, "kb20.stage_skipped")

    boundary = _get(evidence, "data_boundary")
    for field in (
        "outer_used_for_threshold",
        "outer_used_for_coefficients",
        "outer_used_for_checkpoint",
        "outer_used_for_source_selection",
    ):
        _require(failures, boundary.get(field) is False, f"kb21.{field}")
    _require(failures, boundary.get("hidden_host_asset_required") is False, "kb22.hidden_host_asset")
    _require(failures, boundary.get("old_wrapper_bypasses_new_implementation") is False, "kb22.old_wrapper_bypass")

    _check_artifact_bindings(failures, evidence, require_artifacts=require_artifacts)

    return failures


def _mutate(evidence: dict[str, Any], dotted: str, value: Any) -> None:
    current = evidence
    parts = dotted.split(".")
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = value


def known_bad_evidence(case_id: str) -> dict[str, Any]:
    evidence = copy.deepcopy(reference_evidence())
    mutations: dict[str, Callable[[dict[str, Any]], None]] = {
        "kb01_role_isolation_overlap": lambda e: _mutate(e, "role_receipts.executor.worktree", e["role_receipts"]["verifier"]["worktree"]),
        "kb02_trunk_inheritance_degraded": lambda e: (_mutate(e, "architecture.stock_trunk.decoder_byte_coverage", 0.5), _mutate(e, "architecture.stock_trunk.trunk_permanently_frozen", True)),
        "kb03_shallow_decoder_head": lambda e: (_mutate(e, "architecture.pathology_decoders.scar_highest_two_scale_independent_decoder", False), _mutate(e, "architecture.pathology_decoders.d0_shallow_head_substitute", True)),
        "kb04_stock_class_shortcut": lambda e: _mutate(e, "architecture.pathology_decoders.stock_class4_5_normal_forward_shortcut", True),
        "kb05_required_module_no_authority": lambda e: _mutate(e, "architecture.required_module_authority.edema_dilation_affects_final_logits", False),
        "kb06_dead_gradient_double_zero": lambda e: (_mutate(e, "modalities_and_gradients.adapter_and_projection_double_zero", True), _mutate(e, "modalities_and_gradients.second_backward_adapter_gate_context_grad_nonzero_finite", False)),
        "kb07_modality_role_violation": lambda e: (_mutate(e, "modalities_and_gradients.scar_uses_t2", True), _mutate(e, "modalities_and_gradients.edema_uses_t2_primary", False)),
        "kb08_no_t2_edema_leak": lambda e: (_mutate(e, "no_t2_semantics.edema_owned_module_call_count", 2), _mutate(e, "no_t2_semantics.class4_in_softmax_dice_argmax_denominator", True)),
        "kb09_auxiliary_only_context_extent": lambda e: (_mutate(e, "context_and_extent.context_soft_wall_extent_have_final_authority", False), _mutate(e, "architecture.pathology_decoders.scar_context_logits_enter_final_path", False)),
        "kb10_hard_or_forbidden_mechanism": lambda e: (_mutate(e, "architecture.forbidden_mechanisms.hard_roi", True), _mutate(e, "architecture.forbidden_mechanisms.prototype_dictionary_query", True)),
        "kb11_patch_local_extent_or_invalid_bias": lambda e: (_mutate(e, "context_and_extent.full_case_extent_targets", False), _mutate(e, "context_and_extent.invalid_padding_partial_hw_bias_zero", False)),
        "kb12_tile_bias_or_path_fork": lambda e: (_mutate(e, "context_and_extent.tile_outputs_base_logits_only", False), _mutate(e, "context_and_extent.single_tile_multi_tile_same_path", False)),
        "kb13_loss_excluded_or_fake_denominator": lambda e: (_mutate(e, "losses.terms.relation_loss.included_in_total", False), _mutate(e, "losses.zero_denominator_claims_coverage", True)),
        "kb14_hard_negative_unbound": lambda e: _mutate(e, "sampler_and_hard_negatives.hard_negative_binding.checkpoint_sha256", ""),
        "kb15_unrecorded_sampler_fallback": lambda e: _mutate(e, "sampler_and_hard_negatives.requested_resolved_mismatches", [{"requested": "canonical_oof_fn", "resolved": "random_wall", "recorded": False}]),
        "kb16_checkpoint_resume_drift": lambda e: (_mutate(e, "checkpoint_and_resume.schema_version", 3), _mutate(e, "checkpoint_and_resume.reload_next_step_matches_uninterrupted", False)),
        "kb17_early_checkpoint_final_ramp": lambda e: _mutate(e, "checkpoint_and_resume.early_checkpoint_uses_final_step_ramp", True),
        "kb18_canned_receipt_without_execution": lambda e: (_mutate(e, "runtime_receipts.canned_without_execution", True), _mutate(e, "runtime_receipts.forward_backward_probe.executed", False)),
        "kb19_patch_proxy_evaluator": lambda e: (_mutate(e, "evaluation_interface.patch_proxy_evaluator", True), _mutate(e, "evaluation_interface.fair_baseline_same_cases_tta_decode_population", False)),
        "kb20_incomplete_training_counted": lambda e: (_mutate(e, "formal_training_accounting.claims_formal_training", True), _mutate(e, "formal_training_accounting.completed_optimizer_steps", 6000), _mutate(e, "formal_training_accounting.visited_stages", ["A"]), _mutate(e, "formal_training_accounting.pending_or_preempted_counted", True)),
        "kb21_outer_selection_leak": lambda e: _mutate(e, "data_boundary.outer_used_for_checkpoint", True),
        "kb22_hidden_asset_or_old_wrapper": lambda e: (_mutate(e, "data_boundary.hidden_host_asset_required", True), _mutate(e, "data_boundary.old_wrapper_bypasses_new_implementation", True)),
        "kb23_dual_truth_implementation": lambda e: (_mutate(e, "architecture.single_truth.monolith_runnable", True), _mutate(e, "architecture.single_truth.duplicate_runtime_truth", True)),
        "kb24_metric_interface_missing": lambda e: _mutate(e, "evaluation_interface.metrics", ["dice", "hd95"]),
    }
    if case_id not in mutations:
        raise KeyError(f"unknown known-bad case: {case_id}")
    mutations[case_id](evidence)
    evidence["known_bad_case_id"] = case_id
    return evidence


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate CARE-ASE faithful implementation evidence.")
    parser.add_argument("--verification-contract", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--known-bad-id", choices=[item["id"] for item in KNOWN_BAD_CATEGORIES])
    parser.add_argument("--emit-reference", action="store_true")
    parser.add_argument("--list-known-bad", action="store_true")
    parser.add_argument(
        "--allow-public-reference-fixture",
        action="store_true",
        help="allow the emitted public schema fixture to bypass artifact binding checks; never use for Executor evidence",
    )
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args(argv)

    if args.list_known_bad:
        print(json.dumps(KNOWN_BAD_CATEGORIES, indent=2, sort_keys=True))
        return 0
    if args.emit_reference:
        print(json.dumps(reference_evidence(), indent=2, sort_keys=True))
        return 0

    if bool(args.evidence) == bool(args.known_bad_id):
        parser.error("provide exactly one of --evidence or --known-bad-id")

    evidence = load_json(args.evidence) if args.evidence else known_bad_evidence(args.known_bad_id)
    verification_contract = load_json(args.verification_contract) if args.verification_contract else None
    allow_fixture = args.allow_public_reference_fixture and evidence == reference_evidence()
    failures = validate_evidence(
        evidence,
        verification_contract,
        require_artifacts=not allow_fixture,
    )
    if args.allow_public_reference_fixture and not allow_fixture:
        failures.append("public_reference_fixture.forbidden_for_non_reference_evidence")
    result = {
        "schema": "CARE_ASE_FAITHFUL_VALIDATION_RESULT_V1",
        "task_id": TASK_ID,
        "known_bad_case_id": evidence.get("known_bad_case_id"),
        "passed": not failures,
        "failure_count": len(failures),
        "failures": failures,
    }
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
