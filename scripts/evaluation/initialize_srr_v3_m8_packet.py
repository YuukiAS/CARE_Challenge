#!/usr/bin/env python3
"""Initialize the SRR-v3 M8 leaderboard sprint packet without claiming readiness."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260707_srr_v3_m8_editor_grade_leaderboard_sprint"
OUT_DIR = REPO_ROOT / "results" / TASK_KEY

REQUIRED_FILES = [
    "result.md",
    "completion_check.md",
    "review_request.md",
    "MANIFEST.md",
    "commands_run.md",
    "m8_route_objective.md",
    "m8_training_budget_ledger.csv",
    "m8_variant_config_contract.json",
    "m8_variant_matrix.csv",
    "m8_architecture_gap_closure_table.csv",
    "m8_hardcase_sampling_report.md",
    "m8_batch_composition.csv",
    "m8_prototype_bank_summary.json",
    "m8_hard_negative_memory_summary.csv",
    "m8_prototype_margin_by_case.csv",
    "m8_proposal_refiner_recall_precision.csv",
    "m8_loss_schedule.md",
    "m8_training_curves.csv",
    "m8_validation_events.csv",
    "m8_loss_component_by_step.csv",
    "m8_loss_component_gradient_sanity.csv",
    "m8_srr_contribution_by_case.csv",
    "m8_arbitration_opening_diagnostics.csv",
    "m8_formal_case_manifest.csv",
    "m8_same_split_help_harm.csv",
    "m8_hard_subgroup_metrics.csv",
    "m8_component_remote_fp_hd95_report.csv",
    "m8_local_inference_recipe.md",
    "m8_candidate_assembly_matrix.csv",
    "m8_export_dry_run_qc.md",
    "m8_best_variant_decision_table.csv",
    "m8_route_promotion_decision.md",
    "m8_cine_case_manifest.csv",
    "m8_registration_same_subset_matrix.csv",
    "m8_registration_method_selection.md",
    "m8_temporal_dictionary_evidence.csv",
    "m8_temporal_dictionary_index.json",
    "m8_temporal_dictionary_case_summary.csv",
    "m8_temporal_aggregation_metrics.csv",
    "m8_frame0_vs_temporal_help_harm.csv",
    "m8_cine_metrics_summary.csv",
    "m8_myops_decision.md",
    "m8_cine_decision.md",
    "m8_combined_decision.md",
    "m8_label_export_dry_run_qc.md",
    "m8_official_label_mapping_qc.csv",
    "m8_strict_validator_report.md",
    "m8_strict_validator_report.csv",
    "m8_validator_unit_test_report.md",
    "m8_leaderboard_readiness_report.md",
    "m8_next_action.md",
]

CSV_HEADERS = {
    "m8_training_budget_ledger.csv": [
        "run_id",
        "variant",
        "job_id",
        "is_training_run",
        "is_eval_only",
        "start_time",
        "end_time",
        "train_loop_seconds",
        "optimizer_steps",
        "validation_event_count",
        "checkpoint_in",
        "checkpoint_out",
        "included_in_8h_budget",
        "exclusion_reason",
    ],
    "m8_variant_matrix.csv": [
        "variant",
        "config_path",
        "code_path",
        "encoder_profile",
        "dictionary_slot_counts",
        "router_gate_strategy",
        "prototype_bank_source",
        "hard_negative_source",
        "proposal_thresholds",
        "roi_policy",
        "loss_weights",
        "sampler_quotas",
        "training_stages",
        "optimizer_lr_scheduler",
        "checkpoint_selection_rule",
        "inference_arbitration_rule",
        "no_t2_edema_safety_rule",
    ],
    "m8_architecture_gap_closure_table.csv": [
        "route_component",
        "m7_status",
        "required_m8_closure",
        "closure_status",
        "code_path",
        "config_path",
        "runtime_evidence_path",
        "unit_test_or_validator_path",
        "reviewer_repro_command",
        "blocker_if_not_closed",
    ],
    "m8_batch_composition.csv": [
        "step",
        "variant",
        "case_id",
        "center",
        "modality_group",
        "t2_present",
        "c0_present",
        "scar_gt_positive",
        "edema_gt_positive",
        "no_t2_safety_case",
        "remote_fp_positive",
        "small_lesion",
        "large_lesion",
        "selected_reason",
        "loss_terms_active",
    ],
    "m8_srr_contribution_by_case.csv": [
        "variant",
        "checkpoint",
        "decode_mode",
        "case_id",
        "center",
        "modality_group",
        "t2_present",
        "class_name",
        "anchor_delta_rate",
        "final_delta_rate",
        "correction_gate_open_rate",
        "srr_weight_mean",
        "proposal_weight_mean",
        "refiner_weight_mean",
        "fallback_weight_mean",
        "final_logit_delta_abs_mean",
        "roi_delta_abs_mean",
        "proposal_recall_proxy",
        "proposal_precision_proxy",
        "refiner_delta_magnitude",
        "no_t2_edema_voxels",
        "dice_delta",
        "hd95_delta",
        "remote_fp_delta",
        "component_count_delta",
        "source_prediction_path",
    ],
}

DEFAULT_CSV_HEADER = ["status", "reason", "source_path"]


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row}) or DEFAULT_CSV_HEADER
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "EVIDENCE_NOT_FOUND"


def config_contract() -> dict[str, object]:
    common_stages = ["evidence_warmup", "proposal_dictionary", "soft_roi_refinement", "low_lr_calibration"]
    return {
        "task_key": TASK_KEY,
        "config_status": "M8_MONITOR_CONFIG_CONTRACT_WRITTEN",
        "code_path": "scripts/training/run_srr_propref_myops_fold0.py --variant-config-contract",
        "variants": {
            "m8_full_srr_context_arbitration_longrun": {
                "encoder_profile": "full_4scale",
                "dictionary_slot_counts": {"shared": 12, "private_lge": 8, "private_t2": 8, "interaction": 6},
                "router_bias_gate_opening_strategy": "correction-opportunity curriculum with closed fallback outside uncertain/error regions",
                "prototype_bank_source": "same-split train/OOF labeled features with T2 edema repair",
                "hard_negative_mining_source": "results/20260629_proposal_memory_hardneg/mined_components.csv",
                "proposal_thresholds": {"sweep": [0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90], "scar_decode": 0.50, "edema_decode": 0.50},
                "roi_dilation_crop_policy": "task soft-gate ROI with anatomy probability, LV/RV distance, uncertainty and crop refiner channels",
                "loss_weights": {"scar": 1.35, "edema": 1.35, "proposal": 0.45, "prototype_margin": 0.20, "component_proposal": 0.20, "semantic_retrieval": 0.04, "baseline_preservation": 0.10, "roi": 0.25, "roi_remote": 0.05},
                "sampler_quotas": {"complete": 0.55, "foreground": 0.82, "hard_negative": 0.30, "t2_edema_centerC": 0.12},
                "training_stages": common_stages,
                "optimizer": {"lr": 0.0008, "weight_decay": 0.0001, "scheduler": "validation early-stop with low-lr calibration floor"},
                "checkpoint_selection_rule": "eligible best validation loss after min-best-step-fraction, plus final checkpoint",
                "inference_arbitration_rule": "anchor-preserving SRR residual plus proposal/refiner bounded final-logit effect",
                "no_t2_edema_safety_rule": "no-T2 samples block edema loss/proposal/refiner/export voxels instead of acting as edema negatives",
            },
            "m8_scar_precision_edema_safe_longrun": {
                "encoder_profile": "safe_4scale",
                "dictionary_slot_counts": {"shared": 8, "private_lge": 10, "private_t2": 6, "interaction": 4},
                "router_bias_gate_opening_strategy": "conservative scar precision and remote-FP suppression with stronger baseline preservation",
                "prototype_bank_source": "same-split train/OOF labeled features; scar-positive priority",
                "hard_negative_mining_source": "remote-FP mined nnU-Net components",
                "proposal_thresholds": {"sweep": [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90], "scar_decode": 0.55, "edema_decode": 0.55},
                "roi_dilation_crop_policy": "smaller scar ROI, conservative edema ROI, HD95 guard",
                "loss_weights": {"scar": 1.65, "edema": 1.10, "proposal": 0.50, "prototype_margin": 0.25, "component_proposal": 0.30, "semantic_retrieval": 0.04, "baseline_preservation": 0.14, "roi": 0.22, "roi_remote": 0.08},
                "sampler_quotas": {"complete": 0.50, "foreground": 0.86, "hard_negative": 0.45, "remote_fp": 0.20},
                "training_stages": common_stages,
                "optimizer": {"lr": 0.0007, "weight_decay": 0.00012, "scheduler": "validation early-stop with scar HD95 guard"},
                "checkpoint_selection_rule": "best same-split scar Dice/HD95 guard among eligible checkpoints",
                "inference_arbitration_rule": "conservative fallback when SRR increases remote FP or scar HD95 risk",
                "no_t2_edema_safety_rule": "strict no-T2 edema suppression through loss, decode and dry-run export",
            },
            "m8_t2_centerC_edema_repair_longrun": {
                "encoder_profile": "balanced_4scale",
                "dictionary_slot_counts": {"shared": 10, "private_lge": 6, "private_t2": 12, "interaction": 8},
                "router_bias_gate_opening_strategy": "T2-present CenterB/CenterC edema recall with LGE-T2 interaction mass floor",
                "prototype_bank_source": "T2-present edema-positive/negative same-split cases with CenterC oversampling",
                "hard_negative_mining_source": "edema false-positive and false-negative cases from same split",
                "proposal_thresholds": {"sweep": [0.03, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70], "scar_decode": 0.50, "edema_decode": 0.45},
                "roi_dilation_crop_policy": "larger edema ROI with no-T2 block and CenterC edema recall guard",
                "loss_weights": {"scar": 1.20, "edema": 1.65, "proposal": 0.55, "prototype_margin": 0.20, "component_proposal": 0.25, "semantic_retrieval": 0.05, "baseline_preservation": 0.10, "roi": 0.32, "roi_remote": 0.04},
                "sampler_quotas": {"complete": 0.65, "foreground": 0.88, "hard_negative": 0.30, "t2_edema_centerC": 0.25},
                "training_stages": common_stages,
                "optimizer": {"lr": 0.0008, "weight_decay": 0.0001, "scheduler": "validation early-stop with edema recall/HD95 guard"},
                "checkpoint_selection_rule": "best T2-present edema subgroup subject to no-T2 safety",
                "inference_arbitration_rule": "edema candidate allowed only with T2-present evidence and safety export guard",
                "no_t2_edema_safety_rule": "no-T2 myocardium is never used as edema-negative supervision and export blocks edema voxels",
            },
        },
    }


def variant_matrix_rows(config_path: Path, contract: dict[str, object]) -> list[dict[str, object]]:
    rows = []
    for variant, cfg in contract["variants"].items():
        rows.append(
            {
                "variant": variant,
                "config_path": str(config_path),
                "code_path": "scripts/training/run_srr_propref_myops_fold0.py: apply_variant_config_contract",
                "encoder_profile": cfg["encoder_profile"],
                "dictionary_slot_counts": json.dumps(cfg["dictionary_slot_counts"], sort_keys=True),
                "router_gate_strategy": cfg["router_bias_gate_opening_strategy"],
                "prototype_bank_source": cfg["prototype_bank_source"],
                "hard_negative_source": cfg["hard_negative_mining_source"],
                "proposal_thresholds": json.dumps(cfg["proposal_thresholds"], sort_keys=True),
                "roi_policy": cfg["roi_dilation_crop_policy"],
                "loss_weights": json.dumps(cfg["loss_weights"], sort_keys=True),
                "sampler_quotas": json.dumps(cfg["sampler_quotas"], sort_keys=True),
                "training_stages": ",".join(cfg["training_stages"]),
                "optimizer_lr_scheduler": json.dumps(cfg["optimizer"], sort_keys=True),
                "checkpoint_selection_rule": cfg["checkpoint_selection_rule"],
                "inference_arbitration_rule": cfg["inference_arbitration_rule"],
                "no_t2_edema_safety_rule": cfg["no_t2_edema_safety_rule"],
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--myops-job-id", default="")
    parser.add_argument("--myops-htzhulab-job-id", default="")
    parser.add_argument("--myops-a100-job-id", default="")
    parser.add_argument("--myops-cancelled-job-id", default="")
    parser.add_argument("--myops-race-watcher-job-id", default="")
    parser.add_argument("--myops-race-log-path", default="")
    parser.add_argument("--cine-job-id", default="")
    parser.add_argument("--cine-job-script", default="jobs/src/run_srr_v3_m8_cine_registration_mature.sh")
    parser.add_argument("--partition-note", default="")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    head = git_head()
    contract = config_contract()
    config_path = OUT_DIR / "m8_variant_config_contract.json"
    config_path.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")

    write_text(
        OUT_DIR / "m8_route_objective.md",
        "\n".join(
            [
                "# M8 Route Objective",
                "",
                "status: `M8_NEEDS_MONITOR_NO_REVIEW`",
                "",
                "SRR-MyoPS is availability-aware selective retrieval with a semantic representation retrieval bank, anatomy-guided lesion proposal, pathology-specific soft-ROI refinement, explicit proposal/refinement/retrieval/safety losses, and nnU-Net anchor/context/evidence/safety. nnU-Net is the protected anchor and same-split comparator, not the whole route. Cine is registration-aware temporal retrieval with warped non-reference evidence.",
                "",
                "This file records the M8 route objective before scientific work. Current packet state is monitor-only because M8 long training and mature Cine registration have been submitted/started but not re-aggregated into final evidence.",
            ]
        )
        + "\n",
    )
    write_csv(OUT_DIR / "m8_variant_matrix.csv", variant_matrix_rows(config_path, contract), CSV_HEADERS["m8_variant_matrix.csv"])

    variants = list(contract["variants"])
    routed_job_id = ";".join(
        item
        for item in [
            f"htzhulab:{args.myops_htzhulab_job_id}" if args.myops_htzhulab_job_id else "",
            f"a100-gpu:{args.myops_a100_job_id or args.myops_job_id}" if (args.myops_a100_job_id or args.myops_job_id) else "",
        ]
        if item
    ) or "JOB_NOT_SUBMITTED"
    ledger_rows = []
    for idx, variant in enumerate(variants):
        ledger_rows.append(
            {
                "run_id": f"myops_array_{idx}",
                "variant": variant,
                "job_id": routed_job_id,
                "is_training_run": "true",
                "is_eval_only": "false",
                "start_time": "AWAITING_SACCT",
                "end_time": "AWAITING_SACCT",
                "train_loop_seconds": "AWAITING_RUNTIME_AGGREGATION",
                "optimizer_steps": "AWAITING_RUNTIME_AGGREGATION",
                "validation_event_count": "AWAITING_RUNTIME_AGGREGATION",
                "checkpoint_in": "none",
                "checkpoint_out": f"results/{TASK_KEY}/runtime/variants/{variant}/checkpoints/fold_0/propref_config",
                "included_in_8h_budget": "false_until_completed_and_aggregated",
                "exclusion_reason": "M8_NEEDS_MONITOR_NO_REVIEW: job pending/running/not aggregated",
            }
        )
    write_csv(OUT_DIR / "m8_training_budget_ledger.csv", ledger_rows, CSV_HEADERS["m8_training_budget_ledger.csv"])

    closure_rows = []
    for component in [
        "availability-aware modality handling",
        "semantic retrieval dictionary and prototypes",
        "hard-negative memory",
        "scar/edema proposal",
        "anatomy distance/uncertainty gates",
        "soft-ROI refinement",
        "branch arbitration final-logit effect",
        "baseline-preserving fallback",
        "expanded loss objectives",
        "per-case contribution export",
        "no-T2 edema safety",
        "same-split help/harm evaluator",
        "Cine registration-aware temporal dictionary",
    ]:
        closure_rows.append(
            {
                "route_component": component,
                "m7_status": "diagnostic evidence only",
                "required_m8_closure": "runtime evidence from M8 long training or mature Cine attempt",
                "closure_status": "NEEDS_EVIDENCE",
                "code_path": "scripts/training/run_srr_propref_myops_fold0.py; scripts/evaluation/run_srr_v3_m7_cine_registration_repair.py",
                "config_path": str(config_path),
                "runtime_evidence_path": f"results/{TASK_KEY}/runtime/",
                "unit_test_or_validator_path": "scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py",
                "reviewer_repro_command": f"python scripts/evaluation/validate_srr_v3_m8_leaderboard_sprint_packet.py --packet results/{TASK_KEY}",
                "blocker_if_not_closed": "M8_NEEDS_MONITOR_NO_REVIEW",
            }
        )
    write_csv(OUT_DIR / "m8_architecture_gap_closure_table.csv", closure_rows, CSV_HEADERS["m8_architecture_gap_closure_table.csv"])

    monitor_csv_files = [
        name
        for name in REQUIRED_FILES
        if name.endswith(".csv")
        and name
        not in {
            "m8_training_budget_ledger.csv",
            "m8_variant_matrix.csv",
            "m8_architecture_gap_closure_table.csv",
            "m8_strict_validator_report.csv",
        }
    ]
    for name in monitor_csv_files:
        write_csv(
            OUT_DIR / name,
            [{"status": "M8_NEEDS_MONITOR_NO_REVIEW", "reason": "Awaiting completed M8 runtime aggregation.", "source_path": f"results/{TASK_KEY}/runtime/"}],
            CSV_HEADERS.get(name, DEFAULT_CSV_HEADER),
        )

    write_text(OUT_DIR / "m8_prototype_bank_summary.json", json.dumps({"status": "M8_NEEDS_MONITOR_NO_REVIEW", "reason": "Awaiting M8 training runtime prototype summaries."}, indent=2) + "\n")
    write_text(OUT_DIR / "m8_temporal_dictionary_index.json", json.dumps({"status": "M8_NEEDS_MONITOR_NO_REVIEW", "reason": "Awaiting mature Cine registration and temporal dictionary aggregation."}, indent=2) + "\n")

    for name in REQUIRED_FILES:
        path = OUT_DIR / name
        if path.exists() or name.endswith(".csv") or name.endswith(".json"):
            continue
        title = name.replace("_", " ").replace(".md", "").title()
        write_text(
            path,
            f"# {title}\n\nstatus: `M8_NEEDS_MONITOR_NO_REVIEW`\n\nThis M8 artifact is not ready for review because M8 MyoPS long training and Cine mature registration have not completed and been re-aggregated into lightweight evidence files.\n\n",
        )

    write_text(
        OUT_DIR / "result.md",
        f"# M8 Executor Result\n\nstatus: `M8_NEEDS_MONITOR_NO_REVIEW`\n\nM8 start gates passed, config contract was written, and Slurm jobs were submitted or prepared for MyoPS long training and Cine mature registration. This packet is monitor-only until completed jobs are re-aggregated. It is not ready for review and does not claim route promotion, validation packaging/upload, hosted metrics, challenge readiness, scientific stop, fold expansion, or M9.\n\n- git_head: `{head}`\n- generated_at_utc: `{now}`\n- myops_cancelled_pre_race_job_id: `{args.myops_cancelled_job_id or 'NONE'}`\n- myops_htzhulab_job_id: `{args.myops_htzhulab_job_id or 'JOB_NOT_SUBMITTED'}`\n- myops_a100_job_id: `{args.myops_a100_job_id or args.myops_job_id or 'JOB_NOT_SUBMITTED'}`\n- myops_race_watcher_job_id: `{args.myops_race_watcher_job_id or 'JOB_NOT_SUBMITTED'}`\n- myops_race_log_path: `{args.myops_race_log_path or 'EVIDENCE_NOT_FOUND'}`\n- cine_job_id: `{args.cine_job_id or 'JOB_NOT_SUBMITTED'}`\n- partition_note: `{args.partition_note}`\n\n",
    )
    write_text(
        OUT_DIR / "completion_check.md",
        "# M8 Completion Check\n\nstatus: `M8_NEEDS_MONITOR_NO_REVIEW`\n\nreason: M8 training budget is not proven. `m8_training_budget_ledger.csv` contains awaiting-runtime rows, so total included real MyoPS train loop seconds is below the required 28800 until completed jobs are re-aggregated.\n\n",
    )
    write_text(
        OUT_DIR / "review_request.md",
        "# M8 Review Request\n\nstatus: `NO_REVIEW_REQUESTED_MONITOR_ONLY`\n\nDo not review this as a normal ready packet. A separate executor continuation must re-aggregate completed MyoPS and Cine runtime outputs before review can be requested.\n",
    )
    write_text(
        OUT_DIR / "commands_run.md",
        "\n".join(
            [
                "# Commands Run",
                "",
                "| command | status | purpose |",
                "| --- | --- | --- |",
                f"| `scancel {args.myops_cancelled_job_id}` | {'exit 0' if args.myops_cancelled_job_id else 'not run'} | Cancel pre-race single-partition M8 MyoPS job before resubmitting lock-safe mirror jobs. |",
                f"| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint_htzhulab.sh` | {'submitted `' + args.myops_htzhulab_job_id + '`' if args.myops_htzhulab_job_id else 'not submitted'} | Start M8 MyoPS htzhulab race mirror. |",
                f"| `sbatch jobs/src/run_srr_v3_m8_myops_leaderboard_sprint.sh` | {'submitted `' + (args.myops_a100_job_id or args.myops_job_id) + '`' if (args.myops_a100_job_id or args.myops_job_id) else 'not submitted'} | Start M8 MyoPS a100-gpu race mirror. |",
                f"| `sbatch --wrap python scripts/evaluation/watch_srr_v3_m8_myops_race.py ...` | {'submitted `' + args.myops_race_watcher_job_id + '`' if args.myops_race_watcher_job_id else 'not submitted'} | Watch htzhulab/a100 race and cancel the pending mirror when one starts. |",
                f"| `sbatch {args.cine_job_script}` | {'submitted `' + args.cine_job_id + '`' if args.cine_job_id else 'not submitted'} | Start M8 mature Cine registration attempt. |",
                f"| `python scripts/evaluation/initialize_srr_v3_m8_packet.py ...` | exit 0 | Initialize monitor-only M8 packet. |",
            ]
        )
        + "\n",
    )
    manifest = ["# M8 Manifest", "", f"task_key: `{TASK_KEY}`", f"generated_at_utc: `{now}`", "", "## Files"]
    for name in REQUIRED_FILES:
        manifest.append(f"- `{name}`")
    write_text(OUT_DIR / "MANIFEST.md", "\n".join(manifest) + "\n")

    print(
        json.dumps(
            {
                "status": "M8_NEEDS_MONITOR_NO_REVIEW",
                "out_dir": str(OUT_DIR),
                "myops_htzhulab_job_id": args.myops_htzhulab_job_id,
                "myops_a100_job_id": args.myops_a100_job_id or args.myops_job_id,
                "myops_race_watcher_job_id": args.myops_race_watcher_job_id,
                "cine_job_id": args.cine_job_id,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
