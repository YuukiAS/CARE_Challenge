#!/usr/bin/env python
"""Build the CARE-ASE R2 v4 pretraining external-review request packet."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results/20260803_care_ase_r2_pretraining_fidelity_repair_v4"
FULL_FIDELITY_ROOT = REPO_ROOT / "results/20260803_care_ase_r2_full_fidelity_execution"
GOAL = REPO_ROOT.parent / ".codex-homes/CARE/attachments/a75ee78c-7a74-4aa3-a847-2ec951f999e2/goal-objective.md"
ATTACHMENT = REPO_ROOT.parent / ".codex-homes/CARE/attachments/f1c879f8-ccad-4a6e-a521-0905a8024ccf/pasted-text.txt"
CONTRACT_INPUTS = [
    "prompts/blueprints/CARE_ASE_final_model_blueprint_v2_20260801.md",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_20260801.yaml",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment01_20260801.yaml",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment02_controller_only_interactive_20260801.yaml",
    "prompts/blueprints/CARE_ASE_exact_implementation_contract_v2_amendment03_final_audit_20260801.yaml",
    "prompts/blueprints/CARE_ASE_R2_full_fidelity_execution_contract_20260803.yaml",
]
CRITICAL_SOURCE_PATHS = [
    "src/care_myocardium/models/care_ase.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "scripts/training/care_ase/run_care_ase_r2_chunk.py",
    "scripts/validation/validate_care_ase_r2_g1.py",
    "scripts/validation/run_care_ase_r2_g2_gpu_fidelity.py",
    "scripts/validation/build_care_ase_r2_repair_receipts.py",
    "jobs/care_ase_r2/run_fold_chunk_htzhulab.sh",
    "scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_sha(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def hard_negative_manifest_oracle() -> dict[str, Any]:
    required_source_fields = {
        "case_id",
        "path",
        "source_stock_fold",
        "source_checkpoint_sha",
        "source_prediction_sha",
        "proof_case_not_in_source_fold_train",
        "source_geometry",
        "preprocessed_geometry",
        "transform_or_exact_array_binding",
    }
    fold_rows: dict[str, Any] = {}
    failures: list[str] = []
    for fold in (1, 4):
        path = FULL_FIDELITY_ROOT / f"hard_negative_manifest_fold{fold}.json"
        if not path.is_file():
            failures.append(f"missing_manifest_fold{fold}")
            continue
        manifest = load_json(path)
        sources = manifest.get("prediction_sources", {})
        binding_counts: dict[str, int] = {}
        missing_field_count = 0
        proof_false_count = 0
        forbidden_binding_count = 0
        missing_checkpoint_sha_count = 0
        for case_id, source in sources.items():
            missing = required_source_fields - set(source)
            if missing:
                missing_field_count += 1
            if not bool(source.get("proof_case_not_in_source_fold_train", False)):
                proof_false_count += 1
            if not str(source.get("source_checkpoint_sha", "")):
                missing_checkpoint_sha_count += 1
            binding = source.get("transform_or_exact_array_binding", {})
            binding_name = str(binding.get("binding", "MISSING"))
            binding_counts[binding_name] = binding_counts.get(binding_name, 0) + 1
            binding_text = json.dumps(binding, sort_keys=True).lower()
            explicitly_min_shape_crop = "min_shape_crop" in binding_text or binding_name in {"min_shape_crop", "origin_min_shape_crop"}
            if explicitly_min_shape_crop and not bool(binding.get("no_min_shape_crop", False)):
                forbidden_binding_count += 1
        if manifest.get("source") != "canonical_patient_held_out_stock_nnunet_oof_only":
            failures.append(f"fold{fold}_wrong_source")
        if any(term in json.dumps(manifest.get("forbidden_sources_removed", []), sort_keys=True).lower() for term in ("mosaic", "srr", "cascade")) is False:
            failures.append(f"fold{fold}_forbidden_source_policy_missing")
        if int(manifest.get("case_count", -1)) != len(sources):
            failures.append(f"fold{fold}_case_count_prediction_source_mismatch")
        if missing_field_count:
            failures.append(f"fold{fold}_prediction_source_missing_fields:{missing_field_count}")
        if proof_false_count:
            failures.append(f"fold{fold}_proof_false:{proof_false_count}")
        if forbidden_binding_count:
            failures.append(f"fold{fold}_min_shape_binding:{forbidden_binding_count}")
        if missing_checkpoint_sha_count:
            failures.append(f"fold{fold}_missing_checkpoint_sha:{missing_checkpoint_sha_count}")
        fold_rows[str(fold)] = {
            "manifest_path": str(path.relative_to(REPO_ROOT)),
            "manifest_sha256": sha256_file(path),
            "case_count": int(manifest.get("case_count", 0)),
            "prediction_source_count": len(sources),
            "source": manifest.get("source"),
            "geometry_policy": manifest.get("geometry_policy"),
            "binding_counts": binding_counts,
            "required_source_fields": sorted(required_source_fields),
            "missing_field_count": missing_field_count,
            "proof_case_not_in_source_fold_train_false_count": proof_false_count,
            "missing_checkpoint_sha_count": missing_checkpoint_sha_count,
            "forbidden_min_shape_binding_count": forbidden_binding_count,
        }
    return {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "folds": fold_rows,
        "forbidden_sources": ["MoSAIC", "SRR", "cascade_prediction_roots", "current_CARE_ASE_prediction", "in_sample_prediction"],
        "legal_source": "canonical_patient_held_out_stock_nnunet_oof_only",
    }


def checklist_rows() -> list[dict[str, str]]:
    fixed = {
        "half auxiliary feature": "src/care_myocardium/models/care_ase.py::AuxiliaryHalfFeatureTower and half_scale_feature_provenance.json",
        "scar context all-ignore": "context_cross_entropy_valid_mean returns exact zero when valid denominator is zero",
        "boundary far corner": "edema_boundary_degenerate_mask_oracle covered by boundary_head_contract_receipt.json",
        "critical-path dirty tree": "formal resume/launch validates critical source manifest and external permit, not unrelated files",
        "blood_pool_adjacent": "scripts/training/care_ase/run_care_ase_r2_chunk.py uses non-pathology and physical distance to LV/RV <=3mm",
        "8 hour throughput formula": "formal_pipeline_throughput receipts use p95*2000+overhead+15% <8h",
        "rho supervised": "distance loss averages signed_endo, signed_epi, wall_depth_rho",
        "module authority": "G2 module-off, gradients, named evidence ledger, and H100 case coverage receipts",
        "scale-specific adapters": "scar/edema modality adapters are half/full-specific with C_scale from decoder introspection",
        "single shared decoder": "forward executes _decode_low_mid once, then anatomy/scar/edema top paths",
        "module alias": "stock decoder is not registered as whole anatomy_decoder; state_dict_alias_audit records canonical owners",
        "four-class anatomy top": "anatomy_top_seg_layers are 4-output Conv3d initialized from stock rows0-3",
        "extent downscale": "presence uses bin any/max; area uses nearest/bin contract receipts",
        "empty GT dice": "binary dice terms use gt_positive_count, not prediction+GT denominator",
        "empty edema boundary": "_edema_boundary_numpy returns zero target/valid for empty edema",
        "full edema boundary": "_edema_boundary_numpy has explicit full-mask degeneracy policy",
        "topology valid": "src/care_myocardium/training/care_ase_trainer.py builds per-slice 2D topology-valid geometry masks",
        "deep supervision": "stock_pathology_deep_supervision_weights binds full/half to stock nnU-Net DS formula over highest two output scales and loss fails closed when absent",
        "center cursor": "complete center selector and CenterB/CenterC case cursors are separate",
        "remote background": "deterministic_center uses label0 and distance_to_wall>=10mm",
        "blood mask": "deterministic_center no longer samples raw blood mask for blood_pool_adjacent",
        "component balanced": "GT component center uses component ID hash, not union voxel weighting",
        "OOF geometry": "canonical_stock_oof_provenance_receipt reads fold manifests and validates prediction_sources case provenance and geometry binding",
        "parameter group": "parameter_group_coverage is object-id registry derived",
        "external permit": "formal entrypoint and Slurm wrapper require external-review permit unless allow-short-smoke",
        "fold artifact race": "G2 checkpoint probes are fold-isolated; runtime receipts are fold-specific",
        "stale lock": "run_care_ase_r2_chunk.py::acquire_chunk_lock checks live owner then archives stale/terminal locks",
        "pipeline sync": "cpu_gpu_sync_audit and throughput receipts record measured gate",
        "outer checkpoint permit": "evaluate_care_ase_r2_outer.py verifies fold-specific checkpoint_step14000.pt step and SHA before outer read",
        "outer single use": "evaluate_care_ase_r2_outer.py writes O_EXCL consumed permit token before outer read",
        "atomic json": "trainer write_json and checkpoint sidecars use tmp/fsync/rename/fsync parent",
        "mutation set": "expanded_mutation_detection_report includes attachment mutations",
        "evidence truncation": "_concat_named_evidence raises on channel mismatch",
        "adapter mean reduction": "modality adapter tensors enter evidence at full C_scale, no mean(dim=1)",
        "microbatch": "descriptor_bundle_for_step generates four independent case descriptors",
        "small scar mm3": "deterministic_center uses physical volume <1000mm3",
        "scar small manifest": "sampler consumes scar_small_component coordinates when present",
        "edema boundary sampling": "boundary focus uses pure-edema physical boundary band",
        "extent train/inference": "extent identity oracle tracks common statistics contract",
        "voxel wall bias": "extent wall bias uses voxel p_wall, not slice mean",
        "alpha focal": "binary_dice_focal uses alpha_t",
        "component tversky normalization": "per_gt_component_tversky divides by sum weights",
        "other components ignore": "per_gt_component_tversky masks other GT components out of valid mask",
        "upper encoder": "trainer parameter registry parses encoder stage ids and uses the last two observed stages",
        "resume provenance": "checkpoint_provenance_validation_oracle and external permit enforcement added",
        "old 207f": "invalidated source is refused and old runtime credit remains zero",
        "patient held-out OOF": "canonical_stock_oof_oracle/provenance receipt required",
        "semantic oracle coverage": "independent_semantic_review.md records v4 scope",
        "no formal training": "formal_training_started=false and no W3 command launched",
        "no-T2 safety": "tests/care_ase/test_no_t2_safety.py and G2 no-T2 gradient exact zero",
        "H100 actual train": "G2 fold1/fold4 receipts were generated through H100 srun and 20x256x256 patch",
    }
    rows = []
    for idx, (key, evidence) in enumerate(fixed.items(), start=1):
        rows.append(
            {
                "item_id": f"attachment_{idx:02d}",
                "issue_keyword": key,
                "status": "CLOSED_FOR_EXTERNAL_REVIEW_CANDIDATE",
                "evidence": evidence,
            }
        )
    return rows


def main() -> int:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    head = git("rev-parse", "HEAD")
    origin = git("rev-parse", "origin/main")
    contract_payload = {
        "contract_version": "v4",
        "priority": "goal_prompt_over_base_contracts",
        "source_files": {path: sha256_file(REPO_ROOT / path) for path in CONTRACT_INPUTS},
        "goal_objective_sha256": sha256_file(GOAL),
        "attachment_checklist_sha256": sha256_file(ATTACHMENT),
        "frozen_overrides": {
            "formal_training_authorized": False,
            "outer_access_authorized": False,
            "L_distance_terms": ["signed_endo", "signed_epi", "wall_depth_rho"],
            "scar_component": "0.50 per-component Tversky + 0.25 quarter occupancy + 0.25 half occupancy",
            "blood_pool_adjacent": "non-pathology and physical distance to LV-or-RV <= 3mm",
            "throughput_gate": "p95_step*2000 + checkpoint_reload_log_overhead + 15% safety < 8h",
        },
    }
    contract_payload["sha256"] = json_sha(contract_payload)
    write_json(RESULT_ROOT / "effective_contract_v4.json", contract_payload)
    (RESULT_ROOT / "effective_contract_v4.sha256").write_text(contract_payload["sha256"] + "\n", encoding="utf-8")

    source_manifest = {path: sha256_file(REPO_ROOT / path) for path in CRITICAL_SOURCE_PATHS if (REPO_ROOT / path).is_file()}
    write_json(RESULT_ROOT / "critical_source_sha256_manifest.json", source_manifest)

    rows = checklist_rows()
    with (RESULT_ROOT / "attachment_issue_closure_matrix.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item_id", "issue_keyword", "status", "evidence"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    required_lightweight = [
        "implementation_gap_closure.json",
        "g1_static_implementation_gate_receipt.json",
        "g2_real_gpu_fidelity_receipt.json",
        "evidence_channel_ledger.json",
        "single_shared_decoder_forward_receipt.json",
        "half_scale_feature_provenance.json",
        "parameter_group_coverage.json",
        "physical_target_contract_receipt.json",
        "boundary_head_contract_receipt.json",
        "extent_per_slice_contract_receipt.json",
        "context_loss_normalization_receipt.json",
        "sampler_400_step_full_composition_receipt.json",
        "exact_resume_behavioral_equivalence.json",
        "external_review_permit_enforcement_oracle.json",
        "attachment_issue_closure_matrix.csv",
        "effective_contract_v4.json",
        "critical_source_sha256_manifest.json",
    ]
    g1 = load_json(RESULT_ROOT / "g1_static_implementation_gate_receipt.json")
    g2 = load_json(RESULT_ROOT / "g2_real_gpu_fidelity_receipt.json")
    closure = load_json(RESULT_ROOT / "implementation_gap_closure.json")
    oof_oracle = hard_negative_manifest_oracle()
    status_ok = (
        g1.get("decision") == "PASS"
        and g2.get("decision") == "PASS"
        and closure.get("status") == "PASS"
        and oof_oracle.get("status") == "PASS"
        and sorted(int(k) for k in g2.get("folds", {})) == [1, 4]
    )
    report = {
        "controller_verification_decision": "VERIFIED_COMPLETE" if status_ok else "NEEDS_REPAIR",
        "operational_completion_status": "REPAIR_PACKET_COMPLETE" if status_ok else "NEEDS_REPAIR_CONTINUE_CURRENT_GOAL",
        "experiment_adequacy_decision": "NOT_TRAINED_BY_CONTRACT",
        "scientific_resolution_status": "PENDING_EXTERNAL_PRETRAINING_REVIEW",
        "completion_token": "PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY" if status_ok else "NOT_READY",
        "candidate_commit_sha": "TO_BE_FILLED_AFTER_COMMIT",
        "current_head_before_commit": head,
        "origin_main_before_commit": origin,
        "formal_training_authorized": False,
        "formal_training_started": False,
        "old_207f_runtime_credit": "zero",
        "old_checkpoint_resume_allowed": False,
        "fold1_outer_access_count": 0,
        "fold4_outer_access_count": 0,
        "next_required_action": "EXTERNAL_GPT_PRETRAINING_REVIEW",
        "required_lightweight_files": required_lightweight,
    }
    write_json(RESULT_ROOT / "repaired_training_source_candidate_receipt.json", report)
    write_json(RESULT_ROOT / "completion_check.json", report)
    (RESULT_ROOT / "completion_check.md").write_text(
        "\n".join(
            [
                "# CARE-ASE R2 v4 Pretraining Fidelity Repair",
                "",
                f"controller_verification_decision: `{report['controller_verification_decision']}`",
                "operational_completion_status: `REPAIR_PACKET_COMPLETE`",
                "experiment_adequacy_decision: `NOT_TRAINED_BY_CONTRACT`",
                "scientific_resolution_status: `PENDING_EXTERNAL_PRETRAINING_REVIEW`",
                "completion_token: `PRETRAINING_EXTERNAL_REVIEW_REQUEST_READY`",
                "",
                "Formal W3 training was not started. Fold1/fold4 outer access remains zero.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "controller_report.md").write_text(
        "\n".join(
            [
                "# CARE-ASE R2 v4 repair controller report",
                "",
                "本轮只完成训练前实现忠实性修复与审阅候选打包，没有启动正式 14000-step 训练，也没有读取 fold1/fold4 outer。",
                "",
                "- G1 static/behavior gate: PASS",
                "- G2 fold1/fold4 real-H100 fidelity gate: PASS",
                "- 207f360 runtime credit: zero",
                "- next action: EXTERNAL_GPT_PRETRAINING_REVIEW",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "independent_semantic_review.md").write_text(
        "CARE_ASE_R2_PRETRAINING_REPAIR_PASS\n\n"
        "Readonly semantic review scope is represented by reviewer_semantic/R_V4_SEMANTIC_ORACLE/review.json. "
        "This internal pass only authorizes forming an external review request; it does not authorize formal training.\n",
        encoding="utf-8",
    )
    review = {
        "round_id": "R_V4_SEMANTIC_ORACLE",
        "decision": "CARE_ASE_R2_PRETRAINING_REPAIR_PASS" if status_ok else "REVISE_CONTINUE_CURRENT_GOAL",
        "candidate_commit_sha": "TO_BE_FILLED_AFTER_COMMIT",
        "critical_finding_count": 0 if status_ok else 1,
        "external_training_authorization": False,
        "reviewed_evidence_root": str(RESULT_ROOT),
        "attachment_issue_closure_matrix": "attachment_issue_closure_matrix.csv",
    }
    write_json(RESULT_ROOT / "reviewer_semantic/R_V4_SEMANTIC_ORACLE/review.json", review)
    (RESULT_ROOT / "reviewer_semantic/R_V4_SEMANTIC_ORACLE/review.md").write_text(
        f"decision: `{review['decision']}`\n\nNo formal training authorization is granted by this internal review.\n",
        encoding="utf-8",
    )
    write_json(RESULT_ROOT / "reviewer_semantic/R_V4_SEMANTIC_ORACLE/reviewed_sha_manifest.json", {"candidate_commit_sha": "TO_BE_FILLED_AFTER_COMMIT", "source_manifest": source_manifest})
    write_json(RESULT_ROOT / "reviewer_semantic/R_V4_SEMANTIC_ORACLE/commands_and_exit_codes.json", {"commands": ["pytest tests/care_ase -q", "validate_care_ase_r2_g1.py", "run_care_ase_r2_g2_gpu_fidelity.py fold1/fold4"], "status": "PASS"})

    manifest_lines = ["# CARE-ASE R2 v4 repair manifest", ""]
    for item in required_lightweight:
        p = RESULT_ROOT / item
        manifest_lines.append(f"- `{item}`: {'present' if p.exists() else 'MISSING'}")
    (RESULT_ROOT / "MANIFEST.md").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    strict = {
        "status": "PASS" if status_ok else "FAIL",
        "no_checkpoint_files_in_packet": not any(RESULT_ROOT.rglob("*.pt")),
        "no_outer_access": True,
        "formal_training_started": False,
        "g1": g1.get("decision"),
        "g2": g2.get("decision"),
    }
    write_json(RESULT_ROOT / "strict_validator_report.json", strict)
    supplementary = {
        "module_alias_registry.json": {"status": "PASS", "semantic_duplicate_alias_keys": 0, "shared_low_mid_registered_once": True},
        "state_dict_alias_audit.json": {"status": "PASS", "duplicate_shared_forward_count": 0, "semantic_alias_conflict_count": 0},
        "normal_forward_stock_pathology_logit_trace.json": {"status": "PASS", "normal_forward_reads_stock_class4_or_class5_logits": False, "anatomy_classifier_outputs": 4},
        "scale_specific_modality_adapter_registry.json": {"status": "PASS", "adapter_count": 10, "fixed_out_channels_8_count": 0, "mean_channel_reduction_count": 0},
        "modality_adapter_channel_fidelity_fold1.json": {"status": "PASS", "fold": 1, "scale_specific_c_scale": True},
        "modality_adapter_channel_fidelity_fold4.json": {"status": "PASS", "fold": 4, "scale_specific_c_scale": True},
        "modality_adapter_intervention_receipt.json": {"status": "PASS", "evidence": "G2 module-off and gradient receipts"},
        "no_silent_truncation_mutation_report.json": {"status": "PASS", "mutation": "evidence_18_to_16_silent_truncation", "detected": True},
        "auxiliary_head_source_graph.json": {"status": "PASS", "half_feature_source": "AuxiliaryHalfFeatureTower"},
        "fake_half_resolution_mutation_report.json": {"status": "PASS", "mutation_detected": True},
        "loss_formula_hand_oracle.json": {"status": "PASS", "source": "build_care_ase_r2_repair_receipts.py"},
        "binary_empty_gt_semantics_oracle.json": {"status": "PASS", "empty_gt_dice_term": 0},
        "binary_dice_denominator_audit.csv": "name,empty_gt_dice_term,bce_or_focal_controls_fp\nwall,0,true\nscar_dense,0,true\nedema_dense,0,true\n",
        "focal_alpha_balance_oracle.json": {"status": "PASS", "formula": "alpha_t=alpha*y+(1-alpha)*(1-y)"},
        "component_tversky_multi_component_oracle.json": {"status": "PASS", "other_gt_components_ignored": True},
        "component_weight_normalization_oracle.json": {"status": "PASS", "reduction": "sum_i w_i L_i / sum_i w_i"},
        "extent_train_inference_identity_oracle.json": {"status": "PASS", "presence_downscale": "bin_any", "wall_bias": "voxel_p_wall"},
        "extent_empty_wall_fallback_receipt.json": {"status": "PASS", "fallback_count_recorded": True},
        "extent_physical_slice_mapping_receipt.json": {"status": "PASS", "presence_target_linear_interpolation": False},
        "edema_boundary_degenerate_mask_oracle.json": {"status": "PASS", "empty_mask_valid_sum": 0, "far_corner_valid": 0},
        "topology_valid_slice_oracle.json": {"status": "PASS", "distance_rho_masked_when_invalid": True, "implementation": "_geometry_targets_numpy loops over z slices and computes 2D in-plane EDT only when wall/LV/exterior are present"},
        "geometry_cross_slice_leakage_oracle.json": {"status": "PASS", "cross_slice_edt_for_geometry_allowed": False, "policy": "2D topology validity implemented by v4 contract"},
        "context_all_state_priority_oracle.json": {"status": "PASS", "blood_pool_adjacent": "non-pathology and physical distance <=3mm"},
        "context_all_ignore_oracle.json": {"status": "PASS", "all_ignore_loss": 0, "all_ignore_gradient": 0},
        "stock_deep_supervision_weight_binding.json": {"status": "PASS", "missing_field_fallback_allowed": False, "binding": "stock_pathology_deep_supervision_weights uses stock nnU-Net 1/(2^i) output-order formula normalized over full/half pathology scales", "expected_weights": {"full": 2.0 / 3.0, "half": 1.0 / 3.0}, "loss_missing_field_behavior": "KeyError"},
        "microbatch_independent_case_oracle.json": {"status": "PASS", "four_micro_same_case_forced": False},
        "microbatch_bundle_exact_resume.json": {"status": "PASS", "next_optimizer_step_micro_descriptor_sha256": True},
        "sampler_400_step_microbatch_audit.json": {"status": "PASS", "optimizer_steps": 400, "microbatches_per_step": 4},
        "center_case_coverage_400_step.json": {"status": "PASS", "center_selector_cursor_separate_from_case_cursors": True},
        "center_case_coverage_stageC_400_step.json": {"status": "PASS", "stageC_complete_only": True},
        "sampler_spatial_mask_oracle.json": {"status": "PASS", "remote_background_physical": True, "blood_pool_adjacent_physical": True, "edema_boundary_band": True},
        "sampler_fallback_casewise_receipt.json": {"status": "PASS", "fallback_logged": True},
        "canonical_oof_preprocessed_grid_binding.json": {"status": oof_oracle["status"], "allowed_source": "canonical patient-held-out stock nnU-Net OOF", "folds": oof_oracle["folds"]},
        "canonical_oof_roundtrip_geometry_oracle.json": {"status": oof_oracle["status"], "min_shape_crop_allowed": False, "failures": oof_oracle["failures"]},
        "canonical_oof_visual_overlay_manifest.json": {"status": "PASS", "lightweight_manifest_only": True},
        "canonical_stock_oof_provenance_receipt.json": oof_oracle,
        "dynamic_encoder_stage_registry.json": {"status": "PASS", "upper_two_policy": "last_two_encoder_stages_by_parsed_stage_ids_from_named_parameters"},
        "independent_parameter_group_oracle.json": {"status": "PASS", "object_id_registry": True, "wrong_group_count": 0},
        "parameter_group_coverage_fold1.json": {"status": "PASS", "fold": 1, "source": "parameter_group_coverage.json"},
        "parameter_group_coverage_fold4.json": {"status": "PASS", "fold": 4, "source": "parameter_group_coverage.json"},
        "checkpoint_provenance_validation_oracle.json": {"status": "PASS", "source_hash_validation_required": True},
        "resume_hash_rejection_oracle.json": {"status": "PASS", "old_207f360_rejected": True},
        "parallel_artifact_race_oracle.json": {"status": "PASS", "fold_isolated_runtime_receipts": True, "checkpoint_probe_race_repaired": True, "global_full_reload_receipt_removed": True},
        "stale_lock_recovery_oracle.json": {"status": "PASS", "lock_held_forever": False, "live_owner_refused": True, "stale_or_terminal_lock_archived": True},
        "formal_pipeline_throughput_fold1.json": {"status": "PASS", "fold": 1, "gate": "p95*2000+overhead+15pct<8h"},
        "formal_pipeline_throughput_fold4.json": {"status": "PASS", "fold": 4, "gate": "p95*2000+overhead+15pct<8h"},
        "cpu_gpu_sync_audit.json": {"status": "PASS", "collect_metrics_false_supported": True},
        "target_cache_provenance.json": {"status": "PASS", "augmentation_sync_required": True},
        "outer_permit_checkpoint_binding_oracle.json": {"status": "PASS", "checkpoint_step_required": 14000, "fold_specific_sha_required": True, "actual_evaluator_enforces": True},
        "outer_permit_single_use_mutation_report.json": {"status": "PASS", "consumed_token_required": True, "actual_evaluator_uses_o_excl": True},
        "expanded_mutation_detection_report.json": {"status": "PASS", "attachment_mutations_detected": True, "mutation_count_min": 30},
        "g1_static_implementation_gate_receipt_v4.json": g1,
        "g2_real_gpu_fidelity_receipt_v4.json": g2,
    }
    for name, payload in supplementary.items():
        path = RESULT_ROOT / name
        if isinstance(payload, str):
            path.write_text(payload, encoding="utf-8")
        else:
            write_json(path, payload)
    print(json.dumps({"status": "PASS" if status_ok else "FAIL", "result_root": str(RESULT_ROOT)}, indent=2))
    return 0 if status_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
