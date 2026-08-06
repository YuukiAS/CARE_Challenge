#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable


TASK_ID = "care-ase-faithful"
REQUEST_NONCE = "care-ase-20260806T090955Z"
FROZEN_CONTRACT_SHA256 = "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d"


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


def validate_evidence(evidence: dict[str, Any], verification_contract: dict[str, Any] | None = None) -> list[str]:
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
    failures = validate_evidence(evidence, verification_contract)
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
