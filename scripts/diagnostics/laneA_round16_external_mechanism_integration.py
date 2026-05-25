#!/usr/bin/env python3
"""Lane A Round16 external mechanism integration controller diagnostics.

This script executes the low-risk front half of the Round16 controller:

* reproducibility and candidate registry gate;
* external/compliance metadata matrix;
* batch job planning matrix;
* placeholder smoke/result files that explicitly state no job has run yet.

It does not train, submit Slurm, clone external repositories, download weights,
create validation zips, upload, or modify nnU-Net baseline caches.
"""

from __future__ import annotations

import csv
import os
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration"
ROUND15_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round15_deepresearch_portfolio"
PLAN_PATH = REPO_ROOT / "docs/plans/laneA_round16_next_external_mechanism_integration_large_smoke_execution.md"
REGISTRY_PATH = REPO_ROOT / "docs/plans/care_myocardium_plan_registry_rules.md"
SPLITS_JSON = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
LABELS_TR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
BASELINE_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    priority: str
    mechanism_slot: str
    route: str
    job_type: str
    intended_role: str
    implementation_source: str
    external_repo_needed: str
    pretrained_weights_needed: str
    first_allowed_action: str
    batch_fold0_allowed: str
    gate_before_job: str
    expected_output_dir: str
    fail_fast: str


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def md_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(col, "")).replace("|", "\\|") for col in columns) + " |")
    return "\n".join(lines)


def candidates() -> list[Candidate]:
    root = "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration"
    return [
        Candidate(
            "R16_A_care_strong_t2_lge_intensity_prior_fold0_vs",
            "P0",
            "I_MMSeg_style_T2_LGE_intensity_prior_route",
            "CARE-first strong T2/LGE intensity prior",
            "unit/gradient/tiny-overfit, then fold0 very-short; fold0 short only if promoted",
            "learn stronger local T2/LGE edema-support representation beyond Round15 scalar feature head",
            "first-party CARE implementation",
            "no",
            "no",
            "implement import/unit/gradient/tiny smoke",
            "yes_after_unit_tiny_gate",
            "feature cache and baseline probability paths verified; no-T2 policy explicit; scar unchanged check wired",
            f"{root}/R16_A_care_strong_t2_lge_intensity_prior_fold0_vs/",
            "no T2-present/CenterC signal, component/remote FP worse, no-T2 FP, scar regression, NaN/Inf",
        ),
        Candidate(
            "R16_B_external_I_MMSeg_metadata_import_onecase",
            "P0",
            "I_MMSeg_style_T2_LGE_intensity_prior_route",
            "external I-MMSeg readiness",
            "metadata-only, then import/one-case smoke if source and compliance are clear",
            "screen I-MMSeg-style intensity-prior/prompt mechanism for CARE-compatible reduction",
            "external repository/readiness only",
            "yes",
            "unclear",
            "metadata/license/I/O audit",
            "no_fold0_until_metadata_import_onecase_passes",
            "license, data source, dependency, input-output, label mapping documented",
            f"{root}/R16_B_external_I_MMSeg_metadata_import_onecase/",
            "external data requirement, opaque GPT/CLIP dependency, unclear license/weights, incompatible CARE I/O",
        ),
        Candidate(
            "R16_C_anatomy_pathology_cascade_care_fold0_vs",
            "P0/P1",
            "Cascaded_FSN_PTNet_anatomy_pathology_consistency_route",
            "CARE-first anatomy/pathology cascade",
            "unit/gradient/tiny-overfit, then fold0 very-short; fold0 short only if promoted",
            "soft anatomy-conditioned pathology support without hard ROI deletion",
            "first-party CARE implementation",
            "no",
            "no",
            "implement small first-party cascade smoke",
            "yes_after_unit_tiny_gate",
            "anatomy probability/support paths verified; no hard deletion; label mapping unchanged",
            f"{root}/R16_C_anatomy_pathology_cascade_care_fold0_vs/",
            "hard ROI behavior, true edema suppression, CenterC unchanged/worse, scar regression",
        ),
        Candidate(
            "R16_D_external_CascadedFSN_PTNet_metadata_import_onecase",
            "P1",
            "Cascaded_FSN_PTNet_anatomy_pathology_consistency_route",
            "external cascaded anatomy/pathology readiness",
            "metadata-only, then import/one-case smoke if source and compliance are clear",
            "screen Cascaded FSN/PT-Net-style anatomy-first pathology-second design",
            "external repository/readiness only",
            "yes",
            "unclear/no",
            "metadata/license/I/O audit",
            "no_fold0_until_metadata_import_onecase_passes",
            "license, dependency, anatomy/pathology label mapping, and hard-ROI behavior documented",
            f"{root}/R16_D_external_CascadedFSN_PTNet_metadata_import_onecase/",
            "external data requirement, hard ROI dependency, label mismatch, no usable code",
        ),
        Candidate(
            "R16_E_intensity_plus_component_surface_aux_fold0_vs",
            "P1",
            "Boundary_HD_InverseForm_surface_auxiliary_route",
            "CARE-first intensity plus component/surface auxiliary",
            "loss/unit/gradient/tiny-overfit, then fold0 very-short",
            "add small-weight component/surface control to intensity/anatomy support",
            "first-party CARE implementation",
            "no",
            "no",
            "implement bounded loss/gradient smoke",
            "yes_after_loss_gradient_tiny_gate",
            "loss finite; class_4 scoped; class_5 interference negligible; support route present",
            f"{root}/R16_E_intensity_plus_component_surface_aux_fold0_vs/",
            "unstable gradients, Dice/HD95 trade-off, over-pruning, component fragmentation, scar regression",
        ),
        Candidate(
            "R16_F_small_modality_conditioned_moe_fold0_vs",
            "P1",
            "Missing_modality_representation_route",
            "CARE-first small modality-conditioned MoE/head",
            "unit/gradient/tiny-overfit, then fold0 very-short",
            "test small modality-conditioned representation without full UniME/AdaMM framework",
            "first-party CARE implementation",
            "no",
            "no",
            "implement small MoE/modality-conditioned smoke",
            "yes_after_unit_tiny_gate",
            "no-T2 supervision policy documented; modality groups logged; scar guardrail wired",
            f"{root}/R16_F_small_modality_conditioned_moe_fold0_vs/",
            "no-T2 FP increase, center shortcut, no T2-present signal, scar regression",
        ),
        Candidate(
            "R16_G_unime_adamm_copedit_metadata_import_onecase",
            "P1/P2",
            "Missing_modality_representation_route",
            "external missing-modality representation readiness",
            "metadata-only, then import/one-case smoke if source and compliance are clear",
            "screen UniME/AdaMM/CoPeDiT/MoE/MMPL-Seg teacher/routing assumptions",
            "external repository/readiness only",
            "yes",
            "unclear",
            "metadata/license/pretrained-data audit",
            "no_fold0_until_metadata_import_onecase_passes",
            "teacher assumptions, data provenance, no-T2 policy, and label mapping documented",
            f"{root}/R16_G_unime_adamm_copedit_metadata_import_onecase/",
            "requires external training data, unreliable complete-case teacher, incompatible modality objective",
        ),
        Candidate(
            "R16_H_pretrained_mednext_or_mms_readiness_smoke",
            "P1/P2",
            "Pretrained_backbone_feature_route",
            "pretrained backbone/feature readiness",
            "metadata-only, then one-case feature smoke only if weights/source are approved",
            "screen MedNeXt, nnU-Net Task114/M&Ms, or similar pretrained feature feasibility",
            "external weights/repository possible later",
            "maybe",
            "maybe",
            "metadata/license/pretrained-data audit",
            "no_fold0_until_weight_provenance_clear",
            "license, pretrained data, weight availability, channel/label mapping documented",
            f"{root}/R16_H_pretrained_mednext_or_mms_readiness_smoke/",
            "unknown pretrained data, disallowed external data risk, heavy integration, incompatible I/O",
        ),
        Candidate(
            "R16_I_inverseform_surface_loss_metadata_loss_smoke",
            "P2/watch",
            "Boundary_HD_InverseForm_surface_auxiliary_route",
            "external or first-party surface/HD loss readiness",
            "metadata/loss-level smoke; no fold0 train unless auxiliary gate passes",
            "isolate differentiable HD/surface objective as small-weight class_4 auxiliary",
            "external loss code optional after compliance",
            "maybe",
            "no",
            "metadata and loss-gradient audit",
            "auxiliary_only_after_loss_gate",
            "finite loss and gradients; no broad class interference; class_4 scope explicit",
            f"{root}/R16_I_inverseform_surface_loss_metadata_loss_smoke/",
            "NaN/Inf, unstable gradients, class_5 interference, severe Dice/HD trade-off",
        ),
        Candidate(
            "R16_J_caa_seg_ssa_metadata_centerc_smoke",
            "P2/watch",
            "CAA_Seg_SSA_alignment_route",
            "alignment metadata/CenterC one-case feasibility",
            "metadata/one-case CenterC feasibility only",
            "check whether SSA-style alignment is justified by CenterC failures",
            "external repository optional after evidence",
            "maybe",
            "unclear",
            "metadata plus CARE-only CenterC alignment proxy",
            "no_batch_unless_alignment_signal",
            "CenterC cases and alignment proxies located; no affine/spacing mutation",
            f"{root}/R16_J_caa_seg_ssa_metadata_centerc_smoke/",
            "no mismatch evidence, heavy preprocessing, silent geometry/label changes",
        ),
        Candidate(
            "R16_K_biomedparse_feature_readiness_smoke",
            "P2/watch",
            "Pretrained_backbone_feature_route",
            "foundation feature readiness",
            "metadata-only",
            "screen whether BiomedParse-like foundation features are relevant/compliant for CMR",
            "external weights/repository possible later",
            "yes",
            "likely",
            "metadata/license/pretrained-data audit",
            "no_fold0_until_weight_provenance_clear",
            "license, weights, pretrained data, CMR relevance, label mapping documented",
            f"{root}/R16_K_biomedparse_feature_readiness_smoke/",
            "license/weights/data unclear, not CMR-relevant, cannot map to CARE labels",
        ),
    ]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def candidate_rows() -> list[dict[str, object]]:
    return [c.__dict__ for c in candidates()]


def reproducibility_rows() -> list[dict[str, object]]:
    checks = [
        ("round16_plan", PLAN_PATH, True),
        ("plan_registry", REGISTRY_PATH, True),
        ("splits_MyoPS", SPLITS_JSON, True),
        ("labelsTr", LABELS_TR, True),
        ("nnUNet501_baseline_root", BASELINE_ROOT, True),
        ("round15_root", ROUND15_ROOT, True),
        ("round15_decision", ROUND15_ROOT / "round15_decision_table.md", True),
        ("round15_recommendation", ROUND15_ROOT / "round15_round16_recommendation.md", True),
        ("round15_deep_research_need", ROUND15_ROOT / "round15_deep_research_need_assessment.md", True),
        ("round15_baseline_vs_candidate", ROUND15_ROOT / "baseline_vs_candidate_by_subset.csv", True),
        ("round15_case_flags", ROUND15_ROOT / "case_level_failure_flags.csv", True),
        ("round15_center_table", ROUND15_ROOT / "centerB_centerC_edema_table.csv", True),
        ("round15_no_t2_table", ROUND15_ROOT / "no_t2_empty_gt_fp_table.csv", True),
        ("round15_scar_guardrail", ROUND15_ROOT / "scar_guardrail_table.csv", True),
        ("round15_component_remote", ROUND15_ROOT / "component_remote_fp_table.csv", True),
        ("round15_focus_case_table", ROUND15_ROOT / "case2031_3011_3012_3040_table.csv", False),
    ]
    rows: list[dict[str, object]] = []
    for name, path, required in checks:
        exists = path.exists()
        rows.append(
            {
                "item": name,
                "path": str(path),
                "exists": exists,
                "required": required,
                "status": "pass" if exists or not required else "fail_missing_required",
            }
        )
    # Add lightweight evidence counts from Round15 outputs.
    for rel in [
        "baseline_vs_candidate_by_subset.csv",
        "case_level_failure_flags.csv",
        "round15_fold0_very_short_metrics.csv",
        "round15_fold0_short_metrics.csv",
    ]:
        path = ROUND15_ROOT / rel
        rows.append(
            {
                "item": f"{rel}:row_count",
                "path": str(path),
                "exists": path.is_file(),
                "required": True,
                "status": len(read_csv(path)) if path.is_file() else "fail_missing_required",
            }
        )
    return rows


def compliance_rows() -> list[dict[str, object]]:
    source_hints = {
        "R16_B_external_I_MMSeg_metadata_import_onecase": "local DeepResearch notes; URL not verified locally",
        "R16_D_external_CascadedFSN_PTNet_metadata_import_onecase": "docs/notes/deep_research/Result2.pdf; Cascaded FSN/PT-Net mechanism",
        "R16_G_unime_adamm_copedit_metadata_import_onecase": "docs/notes/deep_research/Result2.pdf; AdaMM URL noted in Lane C as https://github.com/Quanato607/AdaMM; other URLs not verified locally",
        "R16_H_pretrained_mednext_or_mms_readiness_smoke": "Lane C notes cite MedNeXt https://github.com/MIC-DKFZ/MedNeXt and M&Ms Zenodo https://zenodo.org/records/4288362; no weight download performed",
        "R16_I_inverseform_surface_loss_metadata_loss_smoke": "Lane C notes cite InverseForm https://github.com/Qualcomm-AI-research/InverseForm; no clone performed",
        "R16_J_caa_seg_ssa_metadata_centerc_smoke": "Lane C notes cite CAA-Seg/SSA MICCAI page https://papers.miccai.org/miccai-2025/0009-Paper2655.html",
        "R16_K_biomedparse_feature_readiness_smoke": "Lane C notes cite BiomedParse https://github.com/microsoft/BiomedParse; no clone/weights performed",
    }
    rows: list[dict[str, object]] = []
    for c in candidates():
        first_party = c.external_repo_needed == "no"
        weights_needed = c.pretrained_weights_needed
        if first_party:
            status = "pass_first_party"
            risk = "low"
            next_action = "implementation_smoke"
            license_status = "CARE_repo_first_party"
            requires_external_training_data = "no"
        else:
            status = "postpone_pending_live_metadata_or_import_audit"
            risk = "medium_high_until_verified"
            next_action = "metadata_only_then_import_onecase_if_allowed"
            license_status = "unclear_not_verified_in_local_checkout"
            requires_external_training_data = "unclear"
        rows.append(
            {
                "candidate_id": c.candidate_id,
                "mechanism_slot": c.mechanism_slot,
                "repo_url_or_local_source": "first-party CARE implementation" if first_party else source_hints.get(c.candidate_id, "local docs only; source not verified"),
                "intended_role": c.intended_role,
                "license": "CARE repository license context" if first_party else "unclear",
                "license_status": license_status,
                "pretrained_weights_used_now": "no",
                "pretrained_weights_needed_later": weights_needed,
                "pretrained_data_source": "not applicable" if first_party else "unclear",
                "requires_external_dataset": "no" if first_party else "unclear",
                "requires_external_training_data": requires_external_training_data,
                "uses_care_only_training": "yes for first-party candidates; external candidates not yet trainable",
                "uses_validation_pseudolabel_supervision": "no",
                "commercial_or_research_only_restriction": "not applicable" if first_party else "unclear",
                "offline_reproducible_now": "yes" if first_party else "no_without_source_capture",
                "label_semantics_change": "no_allowed",
                "submission_export_change": "no_allowed",
                "compliance_risk": risk,
                "round16_status": status,
                "next_allowed_action": next_action,
                "blocking_issue": "" if first_party else "license/source/weights/dependencies/input-output must be verified before training",
            }
        )
    return rows


def batch_job_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for c in candidates():
        first_party_trainable = c.batch_fold0_allowed.startswith("yes")
        rows.append(
            {
                "candidate_id": c.candidate_id,
                "priority": c.priority,
                "job_type": c.job_type,
                "stage_allowed_now": "stage1_stage2_only",
                "gate_before_submission": c.gate_before_job,
                "fold0_very_short_allowed_after_gate": c.batch_fold0_allowed,
                "planned_job_name": c.candidate_id[:32],
                "planned_output_dir": c.expected_output_dir,
                "planned_job_script": "jobs/nnUNet/laneA_round16_external_mechanism_fold0_very_short.sh" if first_party_trainable else "not_created_until_metadata_import_gate",
                "submission_status": "not_submitted",
                "reason": "implementation/unit/tiny gate not run yet" if first_party_trainable else "metadata/import/one-case gate not passed",
            }
        )
    return rows


def placeholder_rows(status: str, reason: str) -> list[dict[str, object]]:
    return [{"status": status, "reason": reason}]


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    repro = reproducibility_rows()
    cands = candidate_rows()
    compliance = compliance_rows()
    jobs = batch_job_rows()
    missing_required = [r for r in repro if r["required"] is True and not r["exists"]]
    stage1_status = "pass" if not missing_required else "fail_missing_required_inputs"

    candidate_fields = list(cands[0].keys())
    compliance_fields = list(compliance[0].keys())
    job_fields = list(jobs[0].keys())
    repro_fields = list(repro[0].keys())

    write_csv(OUT_ROOT / "round16_reproducibility_gate.csv", repro, repro_fields)
    write_csv(OUT_ROOT / "round16_candidate_registry.csv", cands, candidate_fields)
    write_csv(OUT_ROOT / "round16_large_smoke_candidate_matrix.csv", cands, candidate_fields)
    write_csv(OUT_ROOT / "round16_batch_job_matrix.csv", jobs, job_fields)
    write_csv(OUT_ROOT / "round16_batch_job_status.csv", jobs, job_fields)
    write_csv(OUT_ROOT / "round16_job_submission_manifest.csv", jobs, job_fields)
    write_csv(OUT_ROOT / "round16_compliance_metadata_matrix.csv", compliance, compliance_fields)
    write_csv(OUT_ROOT / "round16_compliance_matrix.csv", compliance, compliance_fields)

    not_run = placeholder_rows("not_run", "Round16 Stage1/Stage2 controller setup only; no import, one-case smoke, training, or Slurm submission has run.")
    for name in [
        "round16_external_import_smoke_summary.csv",
        "round16_onecase_smoke_summary.csv",
        "round16_onecase_smoke_results.csv",
        "round16_fold0_very_short_metrics.csv",
        "round16_fold0_very_short_results.csv",
        "round16_fold0_short_metrics.csv",
        "round16_fold0_short_results.csv",
        "round16_baseline_vs_candidate_by_subset.csv",
        "round16_centerC_edema_table.csv",
        "round16_no_t2_empty_gt_fp_table.csv",
        "round16_scar_guardrail_table.csv",
        "round16_component_remote_fp_table.csv",
        "round16_case_level_failure_flags.csv",
    ]:
        write_csv(OUT_ROOT / name, not_run)

    write_text(
        OUT_ROOT / "round16_goal_execution_readme.md",
        "# Round16 Goal Execution README\n\n"
        f"Stage1 status: `{stage1_status}`.\n\n"
        "This directory is the Round16 controller output root for Lane A external mechanism integration. "
        "The current run completed reproducibility checks, candidate registry generation, compliance metadata setup, and batch job planning only.\n\n"
        "No experiments, training, Slurm submissions, external repository clones, weight downloads, validation zip creation, uploads, or production-code changes were performed by this controller run.\n\n"
        "## Stage1 Evidence\n\n"
        + md_table(repro, ["item", "exists", "required", "status"])
        + "\n\n## Candidate Registry\n\n"
        + md_table(cands, ["candidate_id", "priority", "mechanism_slot", "job_type", "batch_fold0_allowed", "fail_fast"])
        + "\n\n## Immediate Next Gate\n\n"
        "Proceed to Stage3/Stage4 only after reviewing `round16_compliance_matrix.csv` and selecting which CARE-first candidates to implement. "
        "External candidates remain metadata/import-only until license, weights, data provenance, dependency, input-output, and label mapping checks are explicit.\n",
    )

    write_text(
        OUT_ROOT / "round16_repo_metadata_audit.md",
        "# Round16 Repository Metadata Audit\n\n"
        "This audit is local-docs-only. No external repository was cloned and no weight was downloaded.\n\n"
        + md_table(
            compliance,
            [
                "candidate_id",
                "repo_url_or_local_source",
                "license_status",
                "pretrained_weights_used_now",
                "requires_external_training_data",
                "compliance_risk",
                "round16_status",
                "next_allowed_action",
            ],
        )
        + "\n\nExternal candidates are not trainable yet. They require live source/license/dependency/shape review before any import or one-case smoke, and large weights require separate user approval.\n",
    )

    write_text(
        OUT_ROOT / "round16_external_repo_readiness_matrix.md",
        "# Round16 External Repository Readiness Matrix\n\n"
        + md_table(
            compliance,
            [
                "candidate_id",
                "mechanism_slot",
                "repo_url_or_local_source",
                "license_status",
                "pretrained_weights_needed_later",
                "pretrained_data_source",
                "requires_external_dataset",
                "compliance_risk",
                "round16_status",
            ],
        )
        + "\n\nStatus interpretation: first-party CARE candidates can move to implementation smoke; external/pretrained candidates are postponed until explicit metadata/import gates pass.\n",
    )

    write_text(
        OUT_ROOT / "round16_batch_job_submission_plan.md",
        "# Round16 Batch Job Submission Plan\n\n"
        "No Slurm job has been submitted. The first legal batch may include only candidates whose metadata/import/unit/tiny gates pass.\n\n"
        + md_table(
            jobs,
            [
                "candidate_id",
                "priority",
                "job_type",
                "gate_before_submission",
                "planned_job_script",
                "submission_status",
                "reason",
            ],
        )
        + "\n\nDefault partition for later eligible jobs: `htzhulab`. Do not submit fold1-4, 5-fold, validation zip, or uploads without separate user authorization.\n",
    )

    commands = [
        "# Round16 planned commands only; not executed by controller setup.",
        f"{REPO_ROOT}/envs/env_CARE/bin/python scripts/diagnostics/laneA_round16_external_mechanism_integration.py",
        "# Later, after implementation/unit/tiny gates pass:",
        "CANDIDATE_ID=R16_A_care_strong_t2_lge_intensity_prior_fold0_vs sbatch jobs/nnUNet/laneA_round16_external_mechanism_fold0_very_short.sh",
        "CANDIDATE_ID=R16_C_anatomy_pathology_cascade_care_fold0_vs sbatch jobs/nnUNet/laneA_round16_external_mechanism_fold0_very_short.sh",
        "CANDIDATE_ID=R16_E_intensity_plus_component_surface_aux_fold0_vs sbatch jobs/nnUNet/laneA_round16_external_mechanism_fold0_very_short.sh",
        "CANDIDATE_ID=R16_F_small_modality_conditioned_moe_fold0_vs sbatch jobs/nnUNet/laneA_round16_external_mechanism_fold0_very_short.sh",
    ]
    write_text(OUT_ROOT / "round16_train_commands.txt", "\n".join(commands) + "\n")

    write_text(
        OUT_ROOT / "round16_import_shape_label_smoke.md",
        "# Round16 Import / Shape / Label Smoke\n\n"
        "Status: `not_run`.\n\n"
        "Reason: this controller execution only completed Stage1/Stage2 setup. No external source has passed metadata compliance yet, and no CARE-first Round16 implementation has been added in this run.\n",
    )
    write_text(
        OUT_ROOT / "round16_decision_table.md",
        "# Round16 Decision Table\n\n"
        f"Current status: `{stage1_status}_stage1_stage2_controller_ready`.\n\n"
        "No candidate has run import/one-case, tiny-overfit, fold0 very-short, or fold0 short yet.\n\n"
        + md_table(cands, ["candidate_id", "priority", "mechanism_slot", "batch_fold0_allowed", "fail_fast"])
        + "\n\nDecision: proceed to Stage3/Stage4 implementation and import/one-case gates; do not submit jobs yet.\n",
    )
    write_text(OUT_ROOT / "round16_candidate_decision_table.md", (OUT_ROOT / "round16_decision_table.md").read_text(encoding="utf-8"))
    write_text(
        OUT_ROOT / "round16_external_method_readiness_update.md",
        "# Round16 External Method Readiness Update\n\n"
        "External/pretrained candidates are `postpone_pending_live_metadata_or_import_audit`. Local DeepResearch notes identify the mechanism slots, but this run did not clone repos, download weights, or verify live licenses.\n",
    )
    write_text(
        OUT_ROOT / "round16_round17_recommendation.md",
        "# Round16 To Round17 Recommendation\n\n"
        "Not ready. Round16 has only completed Stage1/Stage2 controller setup. Next required work is Stage3 import/one-case smoke for compliant external candidates and Stage4 CARE-first implementation smoke for R16_A/R16_C/R16_E/R16_F.\n",
    )
    write_text(
        OUT_ROOT / "round16_new_deep_research_need_assessment.md",
        "# Round16 New Deep Research Need Assessment\n\n"
        "Not assessed yet. This should be written after fold0 very-short or fold0 short evidence is collected. If all high-upside candidates fail, focus new research on CenterC/T2 edema representation, T2 intensity priors, edema label ambiguity, missing-modality supervision, and component-aware lesion support.\n",
    )
    write_text(OUT_ROOT / "round16_deep_research_need_assessment.md", (OUT_ROOT / "round16_new_deep_research_need_assessment.md").read_text(encoding="utf-8"))

    print(f"Round16 controller setup complete: {stage1_status}")
    print(f"Output root: {OUT_ROOT}")


if __name__ == "__main__":
    os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
    main()
