#!/usr/bin/env python3
"""Fail-closed validator for M9 SRR dictionary fidelity packets."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import sys
import tempfile
from pathlib import Path


READY_STATE = "M9_READY_FOR_REVIEW"
ALLOWED_STATES = {
    READY_STATE,
    "M9_NEEDS_EVIDENCE",
    "M9_NEEDS_REVISION",
    "M9_SCIENTIFIC_UNDERTRAINED",
    "M9_NEEDS_MONITOR",
    "M9_RESOURCE_BLOCKED",
    "M9_BLOCKED_PROJECT_ROUTE_DIAGRAMS_UNAVAILABLE",
}
MONITOR_TOKENS = {"NEEDS_MONITOR", "PENDING_MONITOR", "JOB_SUBMITTED", "PENDING_PRIORITY", "RUNNING", "AWAITING_SACCT"}
FORBIDDEN_READY_PHRASES = {"validation upload", "hosted metric claim", "leaderboard-ready", "fold expansion", "M10"}
REQUIRED_FILES = [
    "result.md",
    "completion_check.md",
    "review_request.md",
    "MANIFEST.md",
    "commands_run.md",
    "m9_route_objective.md",
    "m9_rrl_brr2_adaptation_contract.md",
    "m9_dictionary_fidelity_matrix.csv",
    "m9_code_patch_summary.md",
    "m9_loss_weight_wiring_test_report.md",
    "m9_metric_aligned_checkpoint_selection.csv",
    "m9_nnunet_role_audit.md",
    "m9_pattern_sip_usage_by_group.csv",
    "m9_integrativeness_gamma_soft.csv",
    "m9_dictionary_slot_group_stability.csv",
    "m9_dictionary_invalid_slot_mask_report.csv",
    "m9_prototype_memory_summary.json",
    "m9_prototype_update_ledger.csv",
    "m9_hard_negative_replay_ledger.csv",
    "m9_no_t2_edema_negative_violation_report.csv",
    "m9_pathology_specific_refiner_contract.md",
    "m9_scar_refiner_roi_stats.csv",
    "m9_edema_refiner_roi_stats.csv",
    "m9_refiner_asymmetry_ablation.csv",
    "m9_training_budget_ledger.csv",
    "m9_training_curves.csv",
    "m9_validation_events.csv",
    "m9_loss_component_gradient_sanity.csv",
    "m9_candidate_assembly_matrix.csv",
    "m9_same_split_help_harm.csv",
    "m9_hard_subgroup_metrics.csv",
    "m9_component_remote_fp_hd95_report.csv",
    "m9_proposal_refiner_recall_precision.csv",
    "m9_refiner_causal_effect.csv",
    "m9_ablation_matrix.csv",
    "m9_cine_architecture_contract.md",
    "m9_cine_weight_provenance.md",
    "m9_cine_reference_frame_contract.md",
    "m9_cine_final_output_manifest.csv",
    "m9_cine_final_output_qc.md",
    "m9_cine_registration_quality.csv",
    "m9_cine_temporal_dictionary_usage.csv",
    "m9_cine_temporal_case_metrics.csv",
    "m9_cine_frame0_vs_temporal_help_harm.csv",
    "m9_cine_failure_matrix.csv",
    "m9_cine_next_required_action.md",
    "m9_route_promotion_decision.md",
    "m9_next_required_action.md",
    "m9_strict_validator_report.csv",
    "m9_strict_validator_report.md",
    "m9_validator_selftest_report.csv",
    "m9_validator_selftest_report.md",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def completion_state(packet: Path) -> str:
    text = read_text(packet / "completion_check.md")
    match = re.search(r"status:\s*`?([A-Z0-9_]+)`?", text)
    return match.group(1) if match else "EVIDENCE_NOT_FOUND"


def validate(packet: Path) -> list[str]:
    errors: list[str] = []
    state = completion_state(packet)
    if state not in ALLOWED_STATES:
        errors.append(f"invalid completion state: {state}")
    for file_name in REQUIRED_FILES:
        if not (packet / file_name).is_file():
            errors.append(f"missing required file: {file_name}")
    all_md = "\n".join(read_text(path) for path in packet.glob("*.md"))
    if "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED" not in all_md:
        errors.append("missing M8 follow-up review token")
    if "SRR_MAIN_NOT_ANCHOR_RESIDUAL" not in all_md:
        errors.append("missing SRR-main final-output evidence token")
    if "CONTEXT_TEACHER_SAFETY_CONTROL_ONLY" not in all_md:
        errors.append("missing nnU-Net role audit token")
    if (packet / "review.md").exists():
        errors.append("executor packet must not contain review.md")
    if state == READY_STATE:
        upper_md = all_md.upper()
        for token in MONITOR_TOKENS:
            if token in upper_md:
                errors.append(f"ready packet contains monitor token: {token}")
        lower_md = all_md.lower()
        for phrase in FORBIDDEN_READY_PHRASES:
            if phrase.lower() in lower_md and f"not {phrase.lower()}" not in lower_md and f"no {phrase.lower()}" not in lower_md:
                errors.append(f"ready packet contains forbidden phrase: {phrase}")
        loss_report = read_text(packet / "m9_loss_weight_wiring_test_report.md")
        if "total_loss_changed: `true`" not in loss_report or "gradient_norm_changed: `true`" not in loss_report:
            errors.append("loss-weight wiring report does not prove total loss and gradient change")
        selection = read_csv(packet / "m9_metric_aligned_checkpoint_selection.csv")
        if not selection or any("patch_loss_only" in " ".join(row.values()).lower() for row in selection):
            errors.append("checkpoint selection is missing or patch-loss-only")
        nnunet_audit = read_text(packet / "m9_nnunet_role_audit.md")
        if "final_logits = nnunet_anchor_logits + bounded_srr_delta" in nnunet_audit:
            errors.append("formal M9 candidate uses forbidden anchor-residual final logits")
        ready_text = "\n".join(read_text(path) for path in packet.glob("*"))
        ready_upper = ready_text.upper()
        if "SRR_DIAGRAM_BOOTSTRAP_EVIDENCE" not in ready_upper:
            errors.append("missing diagram bootstrap fields")
        if "ANCHOR_ONLY_CONTROL_PROMOTED" in ready_upper or "M8_ANCHOR_RESIDUAL_CONTROL_PROMOTED" in ready_upper:
            errors.append("anchor-only or M8 anchor-residual control marked as candidate promotion")
        if "[FUSED,FUSED,FUSED]" in ready_upper or "FUSED_FUSED_FUSED" in ready_upper:
            errors.append("formal BR2 candidate uses pseudo-modality fused/fused/fused")
        if "INVALID_SLOT_ACTIVE_WHEN_MODALITY_MISSING" in ready_upper:
            errors.append("invalid modality interaction slot active when modality missing")
        if "UNIFORM_COVERAGE_SUBSTITUTE" in ready_upper:
            errors.append("pattern-SIP report substitutes uniform coverage for integrativeness")
        if "DETERMINISTIC_AXIS_PROTOTYPES_ONLY_FORMAL" in ready_upper:
            errors.append("deterministic axis prototypes are the only formal prototype source")
        if "NO_T2_MYOCARDIUM_USED_AS_EDEMA_NEGATIVE" in ready_upper:
            errors.append("no-T2 myocardium used as edema negative")
        if "NO_T2_FORMAL_CANDIDATE_EMITS_EDEMA_VOXELS" in ready_upper:
            errors.append("no-T2 formal candidate emits edema voxels")
        if "IDENTICAL_SCAR_EDEMA_REFINER_BEHAVIOR" in ready_upper:
            errors.append("scar/edema refiners use identical formal behavior")
        if "SCAR_REFINER_EVIDENCE_MISSING" in ready_upper:
            errors.append("scar refiner required evidence missing")
        if "EDEMA_REFINER_EVIDENCE_MISSING" in ready_upper:
            errors.append("edema refiner required evidence missing")
        if "REFINER_CLAIMED_WITH_NO_FINAL_LABEL_EFFECT" in ready_upper:
            errors.append("refiner has no final-label effect but is claimed implemented")
        if "HARD_SUBGROUP_ROWS_MISSING" in ready_upper:
            errors.append("hard subgroup metrics missing required rows")
        if "CINE_OPTIONAL_OMITTED_READY" in ready_upper:
            errors.append("Cine omitted as optional while M9 marked ready")
        if "CINE_WEIGHT_DOWNLOAD_ONLY_READY" in ready_upper:
            errors.append("Cine completion is only weight download/provenance")
        if "CINE_FRAME0_ONLY_READY" in ready_upper or "CINE_DESCRIPTOR_ONLY_READY" in ready_upper:
            errors.append("Cine completion is frame0-only or descriptor-only")
        if "CINE_SINGLE_SYN_SMOKE_READY" in ready_upper or "CINE_SINGLE_DEMONS_SMOKE_READY" in ready_upper:
            errors.append("Cine completion is single registration smoke without final labels")
        if "UNTRAINED_VOXELMORPH_READY" in ready_upper:
            errors.append("untrained/unverified VoxelMorph claimed ready")
        if "TEMPORAL_DICTIONARY_WITHOUT_FINAL_OUTPUT_LABELS" in ready_upper:
            errors.append("Cine temporal dictionary lacks final output labels or metrics")
        if "SMOKE_ONLY_FORMAL_TRAINING" in ready_upper or "SYNTHETIC_ONLY_FORMAL_EVIDENCE" in ready_upper:
            errors.append("smoke-only or synthetic-only evidence marked formal training")
        if "VALIDATION PACKAGE CREATED" in ready_upper or "VALIDATION UPLOAD COMPLETED" in ready_upper or "HOSTED METRIC CLAIM PRESENT" in ready_upper:
            errors.append("validation package/upload/hosted metric claim present")
        if "M10_STARTED_AUTOMATICALLY" in ready_upper or "FOLD_EXPANSION_STARTED_AUTOMATICALLY" in ready_upper:
            errors.append("M10 or fold expansion started automatically")
        required_ready_files = [
            "m9_pattern_sip_usage_by_group.csv",
            "m9_integrativeness_gamma_soft.csv",
            "m9_dictionary_slot_group_stability.csv",
            "m9_dictionary_invalid_slot_mask_report.csv",
            "m9_scar_refiner_roi_stats.csv",
            "m9_edema_refiner_roi_stats.csv",
            "m9_refiner_asymmetry_ablation.csv",
            "m9_training_budget_ledger.csv",
            "m9_same_split_help_harm.csv",
            "m9_hard_subgroup_metrics.csv",
            "m9_refiner_causal_effect.csv",
            "m9_cine_registration_quality.csv",
            "m9_cine_temporal_dictionary_usage.csv",
            "m9_cine_temporal_case_metrics.csv",
        ]
        for file_name in required_ready_files:
            rows = read_csv(packet / file_name)
            if not rows or any("EVIDENCE_NOT_FOUND" in " ".join(row.values()) for row in rows):
                errors.append(f"ready packet lacks runtime evidence rows: {file_name}")
        cine_manifest = read_csv(packet / "m9_cine_final_output_manifest.csv")
        if not cine_manifest or not any(row.get("case_count") not in {"", "0"} for row in cine_manifest):
            errors.append("ready packet lacks Cine final-output rows")
    return errors


def write_good_fixture(good: Path) -> None:
    good.mkdir()
    common_md = (
        "status: `M9_READY_FOR_REVIEW`\n"
        "SRR_DIAGRAM_BOOTSTRAP_EVIDENCE\n"
        "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\n"
        "SRR_MAIN_NOT_ANCHOR_RESIDUAL\n"
        "CONTEXT_TEACHER_SAFETY_CONTROL_ONLY\n"
        "No validation upload, no hosted metric claim, no fold expansion, no M10.\n"
    )
    for file_name in REQUIRED_FILES:
        path = good / file_name
        if file_name.endswith(".csv"):
            path.write_text("status,case_count\nRUNTIME_EVIDENCE,1\n", encoding="utf-8")
        elif file_name.endswith(".json"):
            path.write_text('{"status": "RUNTIME_EVIDENCE"}\n', encoding="utf-8")
        else:
            path.write_text(common_md, encoding="utf-8")
    (good / "m9_loss_weight_wiring_test_report.md").write_text(
        common_md + "total_loss_changed: `true`\ngradient_norm_changed: `true`\n",
        encoding="utf-8",
    )
    (good / "m9_metric_aligned_checkpoint_selection.csv").write_text(
        "candidate_id,selection_metric,selected_checkpoint,status\n"
        "m9,metric_aligned_composite,checkpoint_best.pt,RUNTIME_EVIDENCE\n",
        encoding="utf-8",
    )
    (good / "m9_cine_final_output_manifest.csv").write_text(
        "status,case_count\nFOUND_LOCAL_FINAL_OUTPUTS,12\n",
        encoding="utf-8",
    )


def run_selftest() -> tuple[int, list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        good = root / "good"
        write_good_fixture(good)
        good_errors = validate(good)
        rows.append({"fixture": "good", "expected": "pass", "actual_error_count": str(len(good_errors)), "status": "PASS" if not good_errors else "FAIL"})
        mutations = {
            "01_missing_followup_token": lambda p: [
                md_path.write_text(
                    md_path.read_text(encoding="utf-8").replace(
                        "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED",
                        "M8_FOLLOWUP_TOKEN_REMOVED",
                    ),
                    encoding="utf-8",
                )
                for md_path in p.glob("*.md")
            ],
            "02_missing_diagram_bootstrap_fields": lambda p: [
                md_path.write_text(md_path.read_text(encoding="utf-8").replace("SRR_DIAGRAM_BOOTSTRAP_EVIDENCE", ""), encoding="utf-8")
                for md_path in p.glob("*.md")
            ],
            "03_missing_required_file": lambda p: (p / "m9_nnunet_role_audit.md").unlink(),
            "04_loss_weight_wiring_absent": lambda p: (p / "m9_loss_weight_wiring_test_report.md").write_text(
                "status: `M9_READY_FOR_REVIEW`\nSRR_DIAGRAM_BOOTSTRAP_EVIDENCE\n"
                "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\n"
                "SRR_MAIN_NOT_ANCHOR_RESIDUAL\nCONTEXT_TEACHER_SAFETY_CONTROL_ONLY\n",
                encoding="utf-8",
            ),
            "05_patch_loss_only": lambda p: (p / "m9_metric_aligned_checkpoint_selection.csv").write_text(
                "candidate_id,selection_metric,selected_checkpoint\nm9,patch_loss_only,checkpoint_best.pt\n",
                encoding="utf-8",
            ),
            "06_anchor_residual_final_logits": lambda p: (p / "m9_nnunet_role_audit.md").write_text(
                "status: `M9_READY_FOR_REVIEW`\nSRR_DIAGRAM_BOOTSTRAP_EVIDENCE\n"
                "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\n"
                "SRR_MAIN_NOT_ANCHOR_RESIDUAL\nCONTEXT_TEACHER_SAFETY_CONTROL_ONLY\n"
                "final_logits = nnunet_anchor_logits + bounded_srr_delta\n",
                encoding="utf-8",
            ),
            "07_anchor_control_promoted": lambda p: (p / "m9_candidate_assembly_matrix.csv").write_text("status,case_count\nANCHOR_ONLY_CONTROL_PROMOTED,1\n", encoding="utf-8"),
            "08_fused_pseudo_modality_formal": lambda p: (p / "m9_dictionary_fidelity_matrix.csv").write_text("status,case_count\n[fused,fused,fused],1\n", encoding="utf-8"),
            "09_invalid_slot_active": lambda p: (p / "m9_dictionary_invalid_slot_mask_report.csv").write_text("status,case_count\nINVALID_SLOT_ACTIVE_WHEN_MODALITY_MISSING,1\n", encoding="utf-8"),
            "10_uniform_coverage_pattern_sip": lambda p: (p / "m9_pattern_sip_usage_by_group.csv").write_text("status,case_count\nUNIFORM_COVERAGE_SUBSTITUTE,1\n", encoding="utf-8"),
            "11_deterministic_axis_prototypes_only": lambda p: (p / "m9_prototype_memory_summary.json").write_text('{"status": "DETERMINISTIC_AXIS_PROTOTYPES_ONLY_FORMAL"}\n', encoding="utf-8"),
            "12_no_t2_used_as_edema_negative": lambda p: (p / "m9_no_t2_edema_negative_violation_report.csv").write_text("status,case_count\nNO_T2_MYOCARDIUM_USED_AS_EDEMA_NEGATIVE,1\n", encoding="utf-8"),
            "13_no_t2_emits_edema": lambda p: (p / "m9_no_t2_edema_negative_violation_report.csv").write_text("status,case_count\nNO_T2_FORMAL_CANDIDATE_EMITS_EDEMA_VOXELS,1\n", encoding="utf-8"),
            "14_identical_refiners": lambda p: (p / "m9_refiner_asymmetry_ablation.csv").write_text("status,case_count\nIDENTICAL_SCAR_EDEMA_REFINER_BEHAVIOR,1\n", encoding="utf-8"),
            "15_scar_refiner_missing_evidence": lambda p: (p / "m9_scar_refiner_roi_stats.csv").write_text("status,case_count\nSCAR_REFINER_EVIDENCE_MISSING,1\n", encoding="utf-8"),
            "16_edema_refiner_missing_evidence": lambda p: (p / "m9_edema_refiner_roi_stats.csv").write_text("status,case_count\nEDEMA_REFINER_EVIDENCE_MISSING,1\n", encoding="utf-8"),
            "17_refiner_no_final_label_effect": lambda p: (p / "m9_refiner_causal_effect.csv").write_text("status,case_count\nREFINER_CLAIMED_WITH_NO_FINAL_LABEL_EFFECT,1\n", encoding="utf-8"),
            "18_hard_subgroups_missing": lambda p: (p / "m9_hard_subgroup_metrics.csv").write_text("status,case_count\nHARD_SUBGROUP_ROWS_MISSING,1\n", encoding="utf-8"),
            "19_cine_omitted_optional_ready": lambda p: (p / "m9_cine_architecture_contract.md").write_text("status: `M9_READY_FOR_REVIEW`\nSRR_DIAGRAM_BOOTSTRAP_EVIDENCE\nM8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\nSRR_MAIN_NOT_ANCHOR_RESIDUAL\nCONTEXT_TEACHER_SAFETY_CONTROL_ONLY\nCINE_OPTIONAL_OMITTED_READY\n", encoding="utf-8"),
            "20_cine_weight_download_only": lambda p: (p / "m9_cine_weight_provenance.md").write_text("status: `M9_READY_FOR_REVIEW`\nSRR_DIAGRAM_BOOTSTRAP_EVIDENCE\nM8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\nSRR_MAIN_NOT_ANCHOR_RESIDUAL\nCONTEXT_TEACHER_SAFETY_CONTROL_ONLY\nCINE_WEIGHT_DOWNLOAD_ONLY_READY\n", encoding="utf-8"),
            "21_cine_frame0_or_descriptor_only": lambda p: (p / "m9_cine_final_output_manifest.csv").write_text("status,case_count\nCINE_FRAME0_ONLY_READY,12\n", encoding="utf-8"),
            "22_cine_single_registration_smoke": lambda p: (p / "m9_cine_registration_quality.csv").write_text("status,case_count\nCINE_SINGLE_SYN_SMOKE_READY,1\n", encoding="utf-8"),
            "23_untrained_voxelmorph_ready": lambda p: (p / "m9_cine_registration_quality.csv").write_text("status,case_count\nUNTRAINED_VOXELMORPH_READY,1\n", encoding="utf-8"),
            "24_temporal_dict_without_final_labels": lambda p: (p / "m9_cine_temporal_dictionary_usage.csv").write_text("status,case_count\nTEMPORAL_DICTIONARY_WITHOUT_FINAL_OUTPUT_LABELS,12\n", encoding="utf-8"),
            "25_monitor_packet_marked_ready": lambda p: (p / "result.md").write_text(
                "status: `M9_READY_FOR_REVIEW`\nSRR_DIAGRAM_BOOTSTRAP_EVIDENCE\n"
                "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\n"
                "SRR_MAIN_NOT_ANCHOR_RESIDUAL\nCONTEXT_TEACHER_SAFETY_CONTROL_ONLY\nRUNNING\n",
                encoding="utf-8",
            ),
            "26_smoke_only_formal_training": lambda p: (p / "m9_training_budget_ledger.csv").write_text("status,case_count\nSMOKE_ONLY_FORMAL_TRAINING,1\n", encoding="utf-8"),
            "27_validation_upload_hosted_claim": lambda p: (p / "m9_route_promotion_decision.md").write_text(
                "status: `M9_READY_FOR_REVIEW`\nSRR_DIAGRAM_BOOTSTRAP_EVIDENCE\n"
                "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\n"
                "SRR_MAIN_NOT_ANCHOR_RESIDUAL\nCONTEXT_TEACHER_SAFETY_CONTROL_ONLY\nVALIDATION PACKAGE CREATED\n",
                encoding="utf-8",
            ),
            "28_m10_or_fold_expansion_started": lambda p: (p / "m9_next_required_action.md").write_text(
                "status: `M9_READY_FOR_REVIEW`\nSRR_DIAGRAM_BOOTSTRAP_EVIDENCE\n"
                "M8_FOLLOWUP_AUDITED_NO_DEPLOYABLE_REPAIR_SCIENTIFIC_UNRESOLVED\n"
                "SRR_MAIN_NOT_ANCHOR_RESIDUAL\nCONTEXT_TEACHER_SAFETY_CONTROL_ONLY\nM10_STARTED_AUTOMATICALLY\n",
                encoding="utf-8",
            ),
            "29_review_written": lambda p: (p / "review.md").write_text("bad\n", encoding="utf-8"),
        }
        for name, mutate in mutations.items():
            bad = root / name
            shutil.copytree(good, bad)
            mutate(bad)
            errors = validate(bad)
            rows.append({"fixture": name, "expected": "fail", "actual_error_count": str(len(errors)), "status": "PASS" if errors else "FAIL"})
    failures = sum(1 for row in rows if row["status"] != "PASS")
    return failures, rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", nargs="?", default="results/20260708_srr_v3_m9_dictionary_fidelity_repair_training")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        failures, rows = run_selftest()
        writer = csv.DictWriter(sys.stdout, fieldnames=["fixture", "expected", "actual_error_count", "status"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        raise SystemExit(1 if failures else 0)
    errors = validate(Path(args.packet))
    for error in errors:
        print(f"ERROR: {error}")
    print(f"error_count={len(errors)}")
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()
