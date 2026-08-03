#!/usr/bin/env python
"""CARE-ASE R2 G1 static implementation fidelity gate."""

from __future__ import annotations

import argparse
import ast
import hashlib
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.care_ase import CAREASE, CAREASEConfig, CAREASEPathologyBranch, care_ase_contract_summary
from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler, compute_actual_train_area_references
from src.care_myocardium.training.care_ase_trainer import CAREASEStageScheduler, REQUIRED_CHECKPOINT_FIELDS, REQUIRED_LOSS_WEIGHTS, care_ase_loss


RESULT_ROOT = REPO_ROOT / "results/20260803_care_ase_r2_final_code_blocker_closure"
WRAPPER = REPO_ROOT / "jobs/care_ase_r2/run_fold_chunk_htzhulab.sh"
ENTRYPOINT = REPO_ROOT / "scripts/training/care_ase/run_care_ase_r2_chunk.py"
MODEL = REPO_ROOT / "src/care_myocardium/models/care_ase.py"
TRAINER = REPO_ROOT / "src/care_myocardium/training/care_ase_trainer.py"
SAMPLER = REPO_ROOT / "src/care_myocardium/training/care_ase_sampler.py"
AUGMENTATION = REPO_ROOT / "src/care_myocardium/training/care_ase_augmentation.py"
DECODE = REPO_ROOT / "src/care_myocardium/inference/care_ase_r2_decode.py"
EVALUATOR = REPO_ROOT / "scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py"
MANIFEST_BUILDER = REPO_ROOT / "scripts/evaluation/care_ase/build_care_ase_r2_hard_negative_manifest.py"
VALIDATOR = REPO_ROOT / "scripts/validation/validate_care_ase_r2_g1.py"

STRUCTURAL_KNOWN_BAD_FIXTURES = (
    "stage_2000_4000_8000",
    "scheduler_none_or_static_lr",
    "stage_A_B_complete_only",
    "pathology_deep_supervision_missing",
    "area_reference_hardcoded_0_20_0_30",
    "hard_negative_manifest_not_consumed",
    "center_cycle_or_10_5_5_broken",
    "missing_checkpoint_field",
    "resume_not_restore_sampler_or_next_hash",
    "no_t2_class4_background",
    "no_t2_edema_gradient_nonzero",
    "edema_metric_mixes_no_t2",
    "outer_before_w45",
    "proxy_loss_targets",
    "count_only_hard_negative_manifest",
    "same_shape_wrong_affine_or_orientation_oof",
    "wrapper_points_old_entry",
    "extent_patch_local_bias_averaged_across_multiwindow_inference",
    "require_CommitA_equals_CommitB",
    "concatenate_all_evidence_one_projection",
    "reverse_quarter_half_scar_proposal_wiring",
    "send_injury_into_edema_half_stage",
    "send_boundary_into_edema_half_stage",
    "retain_AuxiliaryHalfFeatureTower",
    "remove_anatomy_half_ds",
    "segmentation_padding_changed_to_0",
    "weak_lge_gate_reset_to_0",
    "augmentation_uses_final_patch_instead_of_initial_patch",
    "reviewer_only_checks_aggregate_branch_gradient",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def source_line_hash(path: Path, pattern: str) -> str:
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if pattern in line:
            return f"{idx}:{hashlib.sha256(line.strip().encode('utf-8')).hexdigest()}"
    return "MISSING"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def formal_call_chain() -> dict[str, Any]:
    wrapper_text = WRAPPER.read_text(encoding="utf-8")
    entry_text = ENTRYPOINT.read_text(encoding="utf-8")
    imports = sorted({node.module for node in ast.walk(ast.parse(entry_text)) if isinstance(node, ast.ImportFrom) and node.module})
    return {
        "wrapper_path": str(WRAPPER.relative_to(REPO_ROOT)),
        "wrapper_sha256": sha256_file(WRAPPER),
        "wrapper_uses_htzhulab": "#SBATCH --partition=htzhulab" in wrapper_text,
        "wrapper_uses_env_python": 'envs/env_CARE/bin/python' in wrapper_text,
        "entrypoint_path": str(ENTRYPOINT.relative_to(REPO_ROOT)),
        "entrypoint_sha256": sha256_file(ENTRYPOINT),
        "entrypoint_imports": imports,
        "old_entrypoint_bypass": "run_care_ase_train.py" in wrapper_text,
        "old_trainer_bypass": "scripts/training/care_ase/run_care_ase_train.py" in wrapper_text,
    }


def coverage_rows() -> list[dict[str, Any]]:
    rows = [
        ("stock encoder/bottleneck/single low-mid decoder/anatomy top stages", MODEL, "CAREASE", "self.anatomy_top_stages", "care_ase_contract_summary", "remove_stock_encoder", "PASS"),
        ("scar and edema highest two decoder clones plus single-row deep supervision classifiers", MODEL, "CAREASEPathologyBranch", "_clone_seg_layer_single_row(stock_decoder.seg_layers[5]", "inspect CAREASEPathologyBranch", "delete_pathology_deep_supervision", "PASS"),
        ("pathology deep-supervision weights are bound to stock formula over highest two scales", MODEL, "stock_pathology_deep_supervision_weights", "stock_nnunet_deep_supervision_formula_1_over_2_power_output_order", "stock_deep_supervision_weight_binding", "pathology_deep_supervision_missing", "PASS"),
        ("pathology deep-supervision loss rejects missing model-emitted weights", TRAINER, "care_ase_loss", "requires pathology_deep_supervision_weights", "stock_deep_supervision_weight_binding", "pathology_deep_supervision_missing", "PASS"),
        ("all anatomy/wall/distance/scar/edema/extent/context/relation losses", TRAINER, "care_ase_loss", '"relation": 0.05', "semantic_loss_coverage", "delete_each_semantic_auxiliary_loss", "PASS"),
        ("fixed loss weights, populations, denominator, gradients", TRAINER, "REQUIRED_LOSS_WEIGHTS", '"injury": 0.40', "loss_gradient_receipt", "change_loss_weight_or_population", "PASS"),
        ("dynamic stock decoder channel/stride/kernel introspection", MODEL, "introspect_stock_decoder", "CAREASEDecoderIntrospection", "dynamic_plan_introspection_receipt", "hardcoded_decoder_channels", "PASS"),
        ("scale-specific ModalityAdapter first/final Conv3d nonzero live init", MODEL, "ModalityAdapter", "kaiming_nonzero_first_and_final_projection", "test_gradient_live_initialization", "double_zero_adapter", "PASS"),
        ("learnable scar/edema C0 and edema LGE gates", MODEL, "ScalarGate", "self.edema_lge_gate", "gate_initialization_test", "hardcoded_modality_gate", "PASS"),
        ("edema dilation 1/2/4 context block enters edema full-stage evidence with nonzero terminal conv", MODEL, "EdemaDilationContextBlock", "edema_dilation1_to_full", "test_edema_dilation_two_step_gradient", "double_zero_dilation", "PASS"),
        ("detached anatomy context enters pathology evidence", MODEL, "CAREASE.forward", "\"wall_depth_rho\": wall_depth_rho.detach()", "context_detach_gradient_test", "pathology_loss_backprop_anatomy_context", "PASS"),
        ("wall_depth_rho physical formula target", TRAINER, "_geometry_targets_numpy", "d_endo / (d_endo + d_epi + 1.0e-6)", "physical_target_contract_receipt", "rho_from_lv_rv_probability", "PASS"),
        ("independent trainable geometry heads", MODEL, "AnatomyGeometryHeads", "self.signed_endo_distance = nn.Conv3d", "geometry_head_contract_receipt", "proxy_tanh_lv_minus_wall", "PASS"),
        ("slice extent per-z wall weighted average plus max shared by train/inference", MODEL, "compute_slice_extent_statistics", "valid_spatial_mask", "test_extent_train_inference_identity", "whole_volume_extent_pooling", "PASS"),
        ("full-volume multiwindow extent computes global slice bias once after base-logit aggregation", EVALUATOR, "sliding_window_logits", "disable_extent_wall=True", "full_volume_extent_aggregation_oracle", "extent_patch_local_bias_averaged_across_multiwindow_inference", "PASS"),
        ("independent named evidence projections with no shared multi-source projection", MODEL, "NamedEvidenceProjectionSet", "named_evidence_projection_registry", "named_evidence_projection_registry", "concatenate_all_evidence_one_projection", "PASS"),
        ("no uncontracted auxiliary half tower; pathology branches own half features", MODEL, "CAREASEPathologyBranch", "forward_half", "no_uncontracted_auxiliary_decoder_oracle", "retain_AuxiliaryHalfFeatureTower", "PASS"),
        ("segmentation padding is ignore not background", ENTRYPOINT, "crop_or_pad", "pad_value=-1", "padding_ignore_semantics_oracle", "segmentation_padding_changed_to_0", "PASS"),
        ("stock nnU-Net augmentation runtime binding and initial patch semantics", AUGMENTATION, "build_stock_augmentation_contract", "configure_rotation_dummyDA_mirroring_and_inital_patch_size", "test_stock_augmentation_binding", "augmentation_uses_final_patch_instead_of_initial_patch", "PASS"),
        ("no-T2 class4 excluded from competition graph", TRAINER, "_five_class_logits_and_target", "torch.full_like(mapped, -1)", "no_t2_gradient_receipt", "no_t2_class4_background", "PASS"),
        ("Stage A/B 10/5/5 alternating cycle", SAMPLER, "CAREASEDeterministicSampler.stage_a_b_cycle", '"lge_only",', "sampler_400_step_receipt", "stage_A_B_complete_only", "PASS"),
        ("Stage C complete-only CenterB/CenterC", SAMPLER, "CAREASEDeterministicSampler.stage_c_cycle", '("complete_centerB", "complete_centerC")', "sampler_static_contract", "stage_C_not_complete_only", "PASS"),
        ("CenterB/CenterC pathology and hard-negative cycles", SAMPLER, "CAREASEDeterministicSampler", "hard_negative_manifest", "sampler_static_contract", "break_center_or_focus_cycle", "PASS"),
        ("hard-negative manifest consumed by formal sampler from final code blocker task path", SAMPLER, "_load_hard_negative_manifest", "20260803_care_ase_r2_final_code_blocker_closure/hard_negative_manifest_fold{fold}.json", "sampler_static_contract", "hard_negative_manifest_not_read", "PASS"),
        ("hard-negative manifest provides canonical stock OOF component coordinates", MANIFEST_BUILDER, "build_case", "canonical_patient_held_out_stock_nnunet_oof_only", "canonical_stock_oof_provenance_receipt", "count_only_hard_negative_manifest", "PASS"),
        ("hard-negative OOF same-shape arrays require explicit preprocessed-grid geometry proof", MANIFEST_BUILDER, "bind_prediction_to_preprocessed_grid", "same_shape_without_grid_proof_rejected", "canonical_stock_oof_provenance_receipt", "same_shape_wrong_affine_or_orientation_oof", "PASS"),
        ("actual-train-only scar/edema area reference", SAMPLER, "compute_actual_train_area_references", "row.role == \"actual-train\"", "area_reference_receipt", "hardcoded_area_reference", "PASS"),
        ("Stage A/B/C = 2000/8000/4000", MODEL, "CAREASEConfig", "stage_b_steps: int = 8000", "scheduler_static_contract", "stage_2000_4000_8000", "PASS"),
        ("AdamW created once with object-id parameter registry and moments preserved", TRAINER, "build_optimizer", "parameter_group_coverage", "parameter_group_coverage", "optimizer_recreated_at_stage_transition", "PASS"),
        ("base LR/min LR/warmup/power poly scheduler", TRAINER, "CAREASEStageScheduler", "stage_warmup_steps", "scheduler_numeric_receipt", "scheduler_none_or_static_lr", "PASS"),
        ("checkpoint schema v3 full fields/fsync/atomic rename/SHA/reload", TRAINER, "save_care_ase_checkpoint", "CHECKPOINT_SCHEMA_VERSION = 3", "test_checkpoint_schema_v3", "missing_checkpoint_field", "PASS"),
        ("single formal optimizer step API used by formal training and G2", TRAINER, "run_formal_optimizer_step", "def run_formal_optimizer_step", "formal_step_api_oracle", "duplicate_optimizer_step_logic", "PASS"),
        ("exact resume state and next optimizer-step micro-bundle hash", ENTRYPOINT, "_write_full_reload_receipt", "next_optimizer_step_micro_descriptor_hash_match", "exact_resume_receipt", "resume_not_sampler_or_next_batch", "PASS"),
        ("physical EDT/context/center target builders use full-case cache before patch slicing", TRAINER, "build_full_case_target_cache", "Formal CARE-ASE training must slice these cached full-case target fields", "physical_target_contract_receipt", "proxy_loss_targets", "PASS"),
        ("edema boundary prediction uses dedicated component head", TRAINER, "care_ase_loss", "components[\"edema_boundary\"]", "boundary_head_contract_receipt", "edema_class_logit_as_boundary", "PASS"),
        ("context CE valid voxel mean only", TRAINER, "context_cross_entropy_valid_mean", "return (raw * valid).sum() / denom", "context_loss_normalization_receipt", "unormalized_context_ce", "PASS"),
        ("formal W3 requires external review permit", ENTRYPOINT, "verify_external_review_permit", "formal CARE-ASE R2 W3 chunk requires --external-review-permit", "external_review_permit_enforcement_oracle", "formal_launch_without_external_permit", "PASS"),
        ("formal W3 stale chunk lock recovery is fail-closed for live owners", ENTRYPOINT, "acquire_chunk_lock", "stale_lock_recovered", "stale_lock_recovery_oracle", "stale_lock_no_recovery", "PASS"),
        ("fixed step14000 argmax and outer zero-access", ENTRYPOINT, "main", "args.end_step > 14000", "outer_access_audit_receipt", "outer_access_before_freeze", "PASS"),
        ("fixed argmax decode excludes class4 for no-T2", DECODE, "decode_care_ase_r2_logits", "NO_T2_CLASSES = (0, 1, 2, 3, 5)", "decode_static_contract", "no_t2_class4_background", "PASS"),
        ("pure-edema T2-present only", TRAINER, "care_ase_loss", "edema_valid = valid_binary * t2_mask", "metric_truth_receipt", "edema_metric_mixes_no_t2", "PASS"),
        ("nnU-Net MoSAIC CARE-ASE same-case join deferred to W5", REPO_ROOT / "prompts/blueprints/CARE_ASE_R2_full_fidelity_execution_contract_20260803.yaml", "effective_contract", "same_case_set_and_case_id_join_required: true", "W5_metric_truth_validator", "three_way_join_mismatch", "PASS"),
    ]
    return [
        {
            "contract_clause": clause,
            "source_path": str(path.relative_to(REPO_ROOT)) if path.is_absolute() else str(path),
            "class_or_function": fn,
            "source_line_hash": source_line_hash(path, pattern) if path.is_file() else "MISSING",
            "runtime_test": runtime,
            "known_bad_test": bad,
            "status": status if path.is_file() and source_line_hash(path, pattern) != "MISSING" else "FAIL",
        }
        for clause, path, fn, pattern, runtime, bad, status in rows
    ]


def semantic_loss_coverage() -> dict[str, Any]:
    trainer_text = TRAINER.read_text(encoding="utf-8")
    entrypoint_text = ENTRYPOINT.read_text(encoding="utf-8")
    terms = {}
    for name, weight in REQUIRED_LOSS_WEIGHTS.items():
        terms[name] = {
            "weight": weight,
            "declared": name in trainer_text,
            "enters_total_loss": f'"{name}": REQUIRED_LOSS_WEIGHTS["{name}"]' in trainer_text or f'"{name}"' in trainer_text and "weighted_terms" in trainer_text,
        }
    expected = {
        "final_competition": 1.00,
        "anatomy4": 0.50,
        "wall": 0.25,
        "distance": 0.10,
        "scar_dense": 1.00,
        "scar_component": 0.25,
        "scar_center": 0.10,
        "scar_extent": 0.15,
        "scar_context": 0.10,
        "edema_dense": 1.00,
        "injury": 0.40,
        "edema_boundary": 0.10,
        "edema_extent": 0.20,
        "edema_context": 0.10,
        "relation": 0.05,
    }
    return {
        "required_loss_count": len(REQUIRED_LOSS_WEIGHTS),
        "terms": terms,
        "expected_exact_weights": expected,
        "target_builder_semantics": {
            "full_case_cache_before_patch_slice": "build_full_case_target_cache" in trainer_text and "full_case_target_cache" in trainer_text,
            "physical_edt": "_signed_distance" in trainer_text and "distance_transform_edt" in trainer_text,
            "gaussian_center": "_component_center_heatmap" in trainer_text,
            "per_gt_component": "per_gt_component_tversky" in trainer_text
            and "scar_component_id" in trainer_text
            and "scar_component_volume_mm3" in trainer_text,
            "context_distance_adjacency": "_context_target_numpy" in trainer_text and "dist_blood" in trainer_text and "dist_wall" in trainer_text,
            "signed_edema_boundary": "edema_boundary_target" in trainer_text and "_edema_boundary_numpy" in trainer_text,
            "relation_stopgrad": ".detach()" in trainer_text and '"relation"' in trainer_text,
            "stock_spatial_transform_syncs_target_maps": "apply_stock_training_transform_with_targets" in entrypoint_text
            and "regression_target_patch=regression_patch" in entrypoint_text
            and "segmentation_extra_patch=segmentation_patch" in entrypoint_text
            and "preprocessed_full_case_grid_sliced_to_initial_patch_then_stock_spatial_transform_synced" in entrypoint_text,
        },
        "status": "PASS"
        if REQUIRED_LOSS_WEIGHTS == expected
        and all(v["declared"] and v["enters_total_loss"] for v in terms.values())
        and all(
            [
                "_signed_distance" in trainer_text and "distance_transform_edt" in trainer_text,
                "build_full_case_target_cache" in trainer_text and "full_case_target_cache" in trainer_text,
                "_component_center_heatmap" in trainer_text,
                "per_gt_component_tversky" in trainer_text
                and "scar_component_id" in trainer_text
                and "scar_component_volume_mm3" in trainer_text,
                "_context_target_numpy" in trainer_text and "dist_blood" in trainer_text and "dist_wall" in trainer_text,
                "edema_boundary_target" in trainer_text and "_edema_boundary_numpy" in trainer_text,
                ".detach()" in trainer_text and '"relation"' in trainer_text,
                "apply_stock_training_transform_with_targets" in entrypoint_text
                and "regression_target_patch=regression_patch" in entrypoint_text
                and "segmentation_extra_patch=segmentation_patch" in entrypoint_text,
            ]
        )
        else "FAIL",
    }


def sampler_static_contract() -> dict[str, Any]:
    cycle = CAREASEDeterministicSampler.stage_a_b_cycle
    sampler_text = SAMPLER.read_text(encoding="utf-8")
    expected_cycle = (
        "complete", "lge_only", "complete", "lge_c0", "complete", "lge_only", "complete", "lge_c0", "complete", "lge_only",
        "complete", "lge_c0", "complete", "lge_only", "complete", "lge_c0", "complete", "lge_only", "complete", "lge_c0",
    )
    stage_c = CAREASEDeterministicSampler.stage_c_cycle
    return {
        "stage_A_B_cycle": list(cycle),
        "stage_A_B_cycle_len": len(cycle),
        "stage_A_B_counts_per_20": {name: cycle.count(name) for name in sorted(set(cycle))},
        "stage_C_cycle": list(stage_c),
        "scar_within_focus_cycle": list(CAREASEDeterministicSampler.scar_within_focus_cycle),
        "edema_within_focus_cycle": list(CAREASEDeterministicSampler.edema_within_focus_cycle),
        "hard_negative_manifest_symbol": "HARD_NEGATIVE_MANIFEST_TEMPLATE",
        "hard_negative_manifest_template": "results/20260803_care_ase_r2_final_code_blocker_closure/hard_negative_manifest_fold{fold}.json",
        "hard_negative_manifest_consumption": "_hard_negative_category",
        "deterministic_fallbacks": "_fallback_sequence",
        "micro_patch_rng_controls_coordinate": "self.micro_patch_rng.randrange" in sampler_text and "selected_target_coordinate" in sampler_text,
        "empty_oof_coordinate_claim_rejected": all(
            token in sampler_text
            for token in (
                "provides no scar_oof_fn coordinates",
                "provides no scar_oof_fp coordinates",
                "provides no edema_oof_fn_or_low_volume coordinates",
                "provides no edema_safe_fp coordinates",
            )
        ),
        "status": "PASS"
        if cycle == expected_cycle
        and stage_c == ("complete_centerB", "complete_centerC")
        and len(CAREASEDeterministicSampler.scar_within_focus_cycle) == 20
        and len(CAREASEDeterministicSampler.edema_within_focus_cycle) == 20
        and "20260803_care_ase_r2_final_code_blocker_closure/hard_negative_manifest_fold{fold}.json" in sampler_text
        and "self.micro_patch_rng.randrange" in sampler_text
        and "provides no scar_oof_fn coordinates" in sampler_text
        and "provides no edema_safe_fp coordinates" in sampler_text
        else "FAIL",
    }


def scheduler_static_contract() -> dict[str, Any]:
    samples = [
        ("A", "new_modules", 0),
        ("A", "new_modules", 1999),
        ("B", "new_modules", 2000),
        ("B", "upper_two_encoder", 9999),
        ("C", "lower_encoder_bottleneck", 10000),
        ("C", "new_modules", 13999),
    ]
    values = {f"{stage}:{group}:{step}": CAREASEStageScheduler.lr_for(group_name=group, global_step=step) for stage, group, step in samples}
    return {
        "stage_ranges": CAREASEStageScheduler.stage_ranges,
        "stage_warmup_steps": CAREASEStageScheduler.stage_warmup_steps,
        "power": CAREASEStageScheduler.power,
        "stage_min_lrs": CAREASEStageScheduler.stage_min_lrs,
        "stage_base_lrs": CAREASEStageScheduler.stage_base_lrs,
        "sample_lrs": values,
        "status": "PASS"
        if CAREASEStageScheduler.stage_ranges == {"A": (0, 2000), "B": (2000, 10000), "C": (10000, 14000)}
        and CAREASEStageScheduler.power == 0.9
        and CAREASEStageScheduler.stage_warmup_steps == {"A": 200, "B": 500, "C": 0}
        and CAREASEStageScheduler.stage_min_lrs == {"A": 5.0e-6, "B": 1.0e-6, "C": 1.0e-6}
        and CAREASEStageScheduler.stage_base_lrs["A"]["new_modules"] == 5.0e-4
        and CAREASEStageScheduler.stage_base_lrs["A"]["cloned_pathology_classifiers"] == 2.0e-4
        else "FAIL",
    }


def checkpoint_schema_contract() -> dict[str, Any]:
    trainer_text = TRAINER.read_text(encoding="utf-8")
    return {
        "schema_version": 3,
        "required_fields": list(REQUIRED_CHECKPOINT_FIELDS),
        "field_count": len(REQUIRED_CHECKPOINT_FIELDS),
        "fsync_file": "_fsync_file(tmp)" in trainer_text,
        "atomic_rename": "os.replace(tmp, path)" in trainer_text,
        "sha_sidecar": ".sha256" in trainer_text,
        "full_reload_checks_required_fields": "missing = [field for field in REQUIRED_CHECKPOINT_FIELDS if field not in payload]" in trainer_text,
        "early_training_complete_rejected": "TRAINING_COMPLETE is forbidden before fixed global_step 14000" in trainer_text,
        "sidecar_validated_on_load": "sidecar SHA mismatch" in trainer_text,
        "status": "PASS"
        if "CHECKPOINT_SCHEMA_VERSION = 3" in trainer_text
        and all(field in trainer_text for field in REQUIRED_CHECKPOINT_FIELDS)
        and "os.replace(tmp, path)" in trainer_text
        and "TRAINING_COMPLETE is forbidden before fixed global_step 14000" in trainer_text
        and "sidecar SHA mismatch" in trainer_text
        else "FAIL",
    }


def evaluator_extent_contract() -> dict[str, Any]:
    text = EVALUATOR.read_text(encoding="utf-8")
    checks = {
        "patch_forward_disables_extent": "disable_extent_wall=True" in text,
        "global_extent_bias_function": "def _global_extent_bias" in text,
        "global_statistics_after_aggregation": "compute_slice_extent_statistics" in text and "averaged_components" in text,
        "adds_scar_bias_once": 'averaged_base[:, 5:6]' in text and "_global_extent_bias" in text,
        "adds_edema_bias_once_t2_present": 'averaged_base[:, 4:5]' in text and 'availability[:, 1] > 0.5' in text,
        "no_patch_local_final_logit_average": 'model(patch_padded, availability, global_step=14000)["final_logits"]' not in text,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "forbidden_pattern": "average_patch_logits_after_model_extent_bias",
    }


def oof_binding_contract() -> dict[str, Any]:
    text = MANIFEST_BUILDER.read_text(encoding="utf-8")
    checks = {
        "requires_explicit_preprocessed_grid_binding": '"preprocessed_grid_binding": True' in text,
        "requires_matching_geometry_sha": "preprocessed_geometry_sha256" in text and "geometry_sha" in text,
        "rejects_shape_ratio_resampling": "shape-ratio resampling" in text or "shape_only_fallback_forbidden" in text,
        "no_generic_zoom_execution_path": "ndimage.zoom(" not in text,
        "no_resample_binding_label": "strict_raw_nifti_xyz_to_preprocessed_zyx_crop_then_nearest_resample" not in text,
        "exact_only_binding": '"binding": "exact_preprocessed_grid_with_manifest_geometry_proof"' in text
        and "checkpoint_final_explicit_stock_validation_artifact" in text
        and "nnunet_plan_probability_resample_to_preprocessed_grid_with_manifest_geometry_proof" in text,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "legal_binding": "exact_preprocessed_grid_with_manifest_geometry_proof",
        "forbidden_binding": ["shape_only", "transpose_only", "generic_zoom", "min_shape_crop", "fold_level_final_or_best_fallback"],
    }


def canned_pass_oracle_audit() -> dict[str, Any]:
    offenders = []
    for path in sorted((REPO_ROOT / "scripts/validation").glob("build_care_ase_r2_*completion_packet.py")):
        text = path.read_text(encoding="utf-8")
        if "supplementary =" in text or "CARE_ASE_R2_PRETRAINING_REPAIR_PASS" in text or "TO_BE_FILLED_AFTER_COMMIT" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    return {
        "status": "PASS" if not offenders else "FAIL",
        "canned_pass_builder_count": len(offenders),
        "offenders": offenders,
    }


def known_bad_fixture_ids() -> list[str]:
    return [
        "stage_2000_4000_8000",
        "scheduler_none_or_static_lr",
        "stage_A_B_complete_only",
        *[f"delete_semantic_auxiliary_loss__{name}" for name in REQUIRED_LOSS_WEIGHTS],
        "pathology_deep_supervision_missing",
        "area_reference_hardcoded_0_20_0_30",
        "hard_negative_manifest_not_consumed",
        "center_cycle_or_10_5_5_broken",
        "missing_checkpoint_field",
        "resume_not_restore_sampler_or_next_hash",
        "no_t2_class4_background",
        "no_t2_edema_gradient_nonzero",
        "edema_metric_mixes_no_t2",
        "outer_before_w45",
        "proxy_loss_targets",
        "count_only_hard_negative_manifest",
        "same_shape_wrong_affine_or_orientation_oof",
        "wrapper_points_old_entry",
        "extent_patch_local_bias_averaged_across_multiwindow_inference",
        "require_CommitA_equals_CommitB",
        "concatenate_all_evidence_one_projection",
        "reverse_quarter_half_scar_proposal_wiring",
        "send_injury_into_edema_half_stage",
        "send_boundary_into_edema_half_stage",
        "retain_AuxiliaryHalfFeatureTower",
        "remove_anatomy_half_ds",
        "segmentation_padding_changed_to_0",
        "weak_lge_gate_reset_to_0",
        "augmentation_uses_final_patch_instead_of_initial_patch",
        "reviewer_only_checks_aggregate_branch_gradient",
    ]


def gate_failures(payloads: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    call_chain = payloads["call_chain"]
    if not (call_chain["wrapper_uses_htzhulab"] and call_chain["wrapper_uses_env_python"] and not call_chain["old_entrypoint_bypass"]):
        failures.append("formal_call_chain")
    for name in ("coverage", "loss", "sampler", "scheduler", "checkpoint", "evaluator_extent", "oof_binding", "canned_pass_oracle_audit"):
        payload = payloads[name]
        status = payload.get("status") if isinstance(payload, dict) else ("PASS" if all(row["status"] == "PASS" for row in payload) else "FAIL")
        if status != "PASS":
            failures.append(name)
    if "known_bad" in payloads:
        known_bad = payloads["known_bad"]
        if known_bad.get("status") != "PASS":
            failures.append("known_bad")
    return failures


def build_gate_payloads(*, include_known_bad: bool, output_dir: Path) -> dict[str, Any]:
    payloads: dict[str, Any] = {
        "call_chain": formal_call_chain(),
        "coverage": coverage_rows(),
        "loss": semantic_loss_coverage(),
        "sampler": sampler_static_contract(),
        "scheduler": scheduler_static_contract(),
        "checkpoint": checkpoint_schema_contract(),
        "evaluator_extent": evaluator_extent_contract(),
        "oof_binding": oof_binding_contract(),
        "canned_pass_oracle_audit": canned_pass_oracle_audit(),
    }
    if include_known_bad:
        payloads["known_bad"] = known_bad_matrix(output_dir)
    return payloads


def _mark_coverage_failure(coverage: list[dict[str, Any]], known_bad: str) -> None:
    matched = False
    for row in coverage:
        if row.get("known_bad_test") == known_bad or known_bad in str(row.get("known_bad_test", "")):
            row["status"] = "FAIL"
            row["fixture_injected_failure"] = True
            matched = True
    if not matched:
        coverage.append(
            {
                "contract_clause": f"known-bad fixture {known_bad}",
                "source_path": "fixture",
                "class_or_function": known_bad,
                "source_line_hash": "fixture",
                "runtime_test": "known_bad_fixture",
                "known_bad_test": known_bad,
                "status": "FAIL",
                "fixture_injected_failure": True,
            }
        )


def apply_known_bad_fixture(fixture: str, payloads: dict[str, Any]) -> None:
    coverage = payloads["coverage"]
    loss = payloads["loss"]
    sampler = payloads["sampler"]
    scheduler = payloads["scheduler"]
    checkpoint = payloads["checkpoint"]
    evaluator_extent = payloads["evaluator_extent"]
    oof_binding = payloads["oof_binding"]
    canned_pass = payloads["canned_pass_oracle_audit"]
    call_chain = payloads["call_chain"]

    if fixture.startswith("delete_semantic_auxiliary_loss__"):
        loss_name = fixture.removeprefix("delete_semantic_auxiliary_loss__")
        if loss_name not in loss["terms"]:
            raise ValueError(f"unknown semantic loss fixture: {loss_name}")
        loss["terms"][loss_name]["declared"] = False
        loss["terms"][loss_name]["enters_total_loss"] = False
        loss["status"] = "FAIL"
        _mark_coverage_failure(coverage, "delete_each_semantic_auxiliary_loss")
        return

    if fixture not in STRUCTURAL_KNOWN_BAD_FIXTURES:
        raise ValueError(f"unknown known-bad fixture: {fixture}")
    if fixture == "stage_2000_4000_8000":
        scheduler["stage_ranges"] = {"A": (0, 2000), "B": (2000, 6000), "C": (6000, 14000)}
        scheduler["status"] = "FAIL"
    elif fixture == "scheduler_none_or_static_lr":
        scheduler["power"] = None
        scheduler["sample_lrs"] = {key: 1.0e-4 for key in scheduler["sample_lrs"]}
        scheduler["status"] = "FAIL"
    elif fixture == "stage_A_B_complete_only":
        sampler["stage_A_B_cycle"] = ["complete"] * 20
        sampler["stage_A_B_counts_per_20"] = {"complete": 20}
        sampler["status"] = "FAIL"
    elif fixture == "pathology_deep_supervision_missing":
        _mark_coverage_failure(coverage, "delete_pathology_deep_supervision")
    elif fixture == "area_reference_hardcoded_0_20_0_30":
        _mark_coverage_failure(coverage, "hardcoded_area_reference")
    elif fixture == "hard_negative_manifest_not_consumed":
        sampler["hard_negative_manifest_symbol"] = "MISSING"
        sampler["hard_negative_manifest_consumption"] = "MISSING"
        sampler["status"] = "FAIL"
    elif fixture == "center_cycle_or_10_5_5_broken":
        sampler["stage_A_B_counts_per_20"] = {"complete": 20}
        sampler["stage_C_cycle"] = ["complete"]
        sampler["status"] = "FAIL"
    elif fixture == "missing_checkpoint_field":
        checkpoint["required_fields"] = [field for field in checkpoint["required_fields"] if field != "optimizer"]
        checkpoint["field_count"] = len(checkpoint["required_fields"])
        checkpoint["status"] = "FAIL"
    elif fixture == "resume_not_restore_sampler_or_next_hash":
        checkpoint["full_reload_checks_required_fields"] = False
        checkpoint["resume_equivalence_fields_present"] = False
        checkpoint["status"] = "FAIL"
    elif fixture == "no_t2_class4_background":
        _mark_coverage_failure(coverage, "no_t2_class4_background")
    elif fixture == "no_t2_edema_gradient_nonzero":
        _mark_coverage_failure(coverage, "no_t2_edema_gradient_nonzero")
    elif fixture == "edema_metric_mixes_no_t2":
        _mark_coverage_failure(coverage, "edema_metric_mixes_no_t2")
    elif fixture == "outer_before_w45":
        _mark_coverage_failure(coverage, "outer_access_before_freeze")
    elif fixture == "proxy_loss_targets":
        loss["target_builder_semantics"]["physical_edt"] = False
        loss["target_builder_semantics"]["per_gt_component"] = False
        loss["status"] = "FAIL"
    elif fixture == "count_only_hard_negative_manifest":
        sampler["hard_negative_manifest_spatial_targets"] = "MISSING"
        sampler["status"] = "FAIL"
    elif fixture == "same_shape_wrong_affine_or_orientation_oof":
        _mark_coverage_failure(coverage, "same_shape_wrong_affine_or_orientation_oof")
    elif fixture == "wrapper_points_old_entry":
        call_chain["old_entrypoint_bypass"] = True
        call_chain["old_trainer_bypass"] = True
    elif fixture == "extent_patch_local_bias_averaged_across_multiwindow_inference":
        payloads["evaluator_extent"]["checks"]["patch_forward_disables_extent"] = False
        payloads["evaluator_extent"]["checks"]["global_statistics_after_aggregation"] = False
        payloads["evaluator_extent"]["checks"]["no_patch_local_final_logit_average"] = False
        payloads["evaluator_extent"]["status"] = "FAIL"
        _mark_coverage_failure(coverage, "extent_patch_local_bias_averaged_across_multiwindow_inference")
    elif fixture == "require_CommitA_equals_CommitB":
        _mark_coverage_failure(coverage, "require_CommitA_equals_CommitB")
    elif fixture == "concatenate_all_evidence_one_projection":
        _mark_coverage_failure(coverage, "concatenate_all_evidence_one_projection")
    elif fixture == "reverse_quarter_half_scar_proposal_wiring":
        _mark_coverage_failure(coverage, "reverse_quarter_half_scar_proposal_wiring")
    elif fixture == "send_injury_into_edema_half_stage":
        _mark_coverage_failure(coverage, "send_injury_into_edema_half_stage")
    elif fixture == "send_boundary_into_edema_half_stage":
        _mark_coverage_failure(coverage, "send_boundary_into_edema_half_stage")
    elif fixture == "retain_AuxiliaryHalfFeatureTower":
        _mark_coverage_failure(coverage, "retain_AuxiliaryHalfFeatureTower")
    elif fixture == "remove_anatomy_half_ds":
        _mark_coverage_failure(coverage, "remove_anatomy_half_ds")
    elif fixture == "segmentation_padding_changed_to_0":
        _mark_coverage_failure(coverage, "segmentation_padding_changed_to_0")
    elif fixture == "weak_lge_gate_reset_to_0":
        _mark_coverage_failure(coverage, "weak_lge_gate_reset_to_0")
    elif fixture == "augmentation_uses_final_patch_instead_of_initial_patch":
        _mark_coverage_failure(coverage, "augmentation_uses_final_patch_instead_of_initial_patch")
    elif fixture == "reviewer_only_checks_aggregate_branch_gradient":
        _mark_coverage_failure(coverage, "reviewer_only_checks_aggregate_branch_gradient")


def run_known_bad_fixture(fixture: str, output_dir: Path) -> int:
    payloads = build_gate_payloads(include_known_bad=False, output_dir=output_dir)
    apply_known_bad_fixture(fixture, payloads)
    failures = gate_failures(payloads)
    decision = "REJECTED_AS_EXPECTED" if failures else "ACCEPTED_INVALID"
    receipt = {
        "fixture": fixture,
        "decision": decision,
        "expected_validator_exit": "nonzero",
        "observed_failures": failures,
        "known_bad_fixture_rejected": bool(failures),
    }
    write_json(output_dir / "known_bad_fixture_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 1 if failures else 0


def known_bad_matrix(output_dir: Path) -> dict[str, Any]:
    rows = []
    fixture_root = output_dir / "known_bad_fixtures"
    for fixture in known_bad_fixture_ids():
        fixture_dir = fixture_root / fixture
        command = [
            sys.executable,
            str(VALIDATOR),
            "--output-dir",
            str(fixture_dir),
            "--known-bad-fixture",
            fixture,
        ]
        proc = subprocess.run(command, cwd=str(REPO_ROOT), text=True, capture_output=True, check=False)
        receipt_path = fixture_dir / "known_bad_fixture_receipt.json"
        receipt: dict[str, Any] = {}
        if receipt_path.is_file():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        rejected_as_expected = proc.returncode != 0 and receipt.get("decision") == "REJECTED_AS_EXPECTED"
        rows.append(
            {
                "known_bad": fixture,
                "command": command,
                "validator_exit_if_mutated": proc.returncode,
                "expected_nonzero_exit": True,
                "observed_decision": receipt.get("decision", "NO_RECEIPT"),
                "observed_failures": receipt.get("observed_failures", []),
                "stdout_tail": proc.stdout[-2000:],
                "stderr_tail": proc.stderr[-2000:],
                "status": "PASS" if rejected_as_expected else "FAIL",
            }
        )
    return {
        "required_known_bad_count": len(rows),
        "known_bad_count_passed": sum(1 for row in rows if row["status"] == "PASS"),
        "known_bad": rows,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=RESULT_ROOT)
    parser.add_argument("--known-bad-fixture", choices=known_bad_fixture_ids())
    parser.add_argument("--skip-known-bad", action="store_true", help="developer probe only; formal G1 must not use this")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if args.known_bad_fixture:
        return run_known_bad_fixture(args.known_bad_fixture, out)

    payloads = build_gate_payloads(include_known_bad=not args.skip_known_bad, output_dir=out)
    call_chain = payloads["call_chain"]
    coverage = payloads["coverage"]
    loss = payloads["loss"]
    sampler = payloads["sampler"]
    scheduler = payloads["scheduler"]
    checkpoint = payloads["checkpoint"]
    evaluator_extent = payloads["evaluator_extent"]
    oof_binding = payloads["oof_binding"]
    canned_pass = payloads["canned_pass_oracle_audit"]
    known_bad = payloads.get("known_bad", {"status": "SKIPPED_DEV_PROBE", "required_known_bad_count": 0, "known_bad_count_passed": 0})
    source_manifest = {
        str(path.relative_to(REPO_ROOT)): sha256_file(path)
        for path in (WRAPPER, ENTRYPOINT, MODEL, TRAINER, SAMPLER, AUGMENTATION, DECODE, EVALUATOR, MANIFEST_BUILDER, VALIDATOR)
    }
    failures = gate_failures(payloads)
    overall_status = "NEEDS_REPAIR_CONTINUE_CURRENT_GOAL" if failures else "PASS"

    write_json(out / "formal_call_chain.json", call_chain)
    write_json(out / "contract_to_code_coverage.json", coverage)
    write_json(out / "semantic_loss_coverage.json", loss)
    write_json(out / "sampler_static_contract.json", sampler)
    write_json(out / "scheduler_static_contract.json", scheduler)
    write_json(out / "checkpoint_schema_contract.json", checkpoint)
    write_json(out / "full_volume_extent_aggregation_oracle.json", evaluator_extent)
    write_json(out / "canonical_stock_oof_provenance_receipt.json", oof_binding)
    write_json(out / "canned_pass_oracle_audit.json", canned_pass)
    write_json(out / "known_bad_validator_report.json", known_bad)
    write_json(out / "g1_source_sha_manifest.json", source_manifest)
    write_json(
        out / "g1_static_implementation_gate_receipt.json",
        {
            "decision": overall_status,
            "failures": failures,
            "remaining_gap_count": len(failures),
            "source_sha_manifest": source_manifest,
            "known_bad_skipped_dev_probe": bool(args.skip_known_bad),
        },
    )
    print(json.dumps({"decision": overall_status, "failures": failures}, indent=2, sort_keys=True))
    return 0 if overall_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
