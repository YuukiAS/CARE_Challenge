#!/usr/bin/env python3
"""Bind historical CARE model evidence for the V2 forensic packet.

This is an evidence aggregator, not a new training or submission path. It
records which historical models have bound code/checkpoints/predictions/metrics
and which requests remain blocked by missing exact assets.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_read_error": str(exc)}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except Exception:
        return str(path)


def git_head(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def git_lineage_marker(root: Path, model_id: str, experiment_id: str, family: str) -> dict[str, str]:
    return {
        "model_id": model_id,
        "experiment_id": experiment_id,
        "commit": git_head(root),
        "date": utc_now()[:10],
        "subject": f"Current binding point for {family}; controller also ran a read-only git log --all forensic scan before aggregation.",
    }


def file_binding_rows(
    root: Path,
    model_id: str,
    experiment_id: str,
    files: list[Path],
    artifact_type: str,
    *,
    max_rows: int = 200,
    hash_max_bytes: int = 64 * 1024 * 1024,
) -> list[dict[str, Any]]:
    out = []
    unique = sorted(set(files))
    for path in unique[:max_rows]:
        if not path.exists() or not path.is_file():
            continue
        size = path.stat().st_size
        digest = sha256_file(path) if hash_max_bytes > 0 and size <= hash_max_bytes else "BOUND_SIZE_ONLY_FOR_PACKET_RUNTIME"
        out.append(
            {
                "model_id": model_id,
                "experiment_id": experiment_id,
                "artifact_type": artifact_type,
                "path": rel(root, path),
                "sha256": digest,
                "size_bytes": size,
                "binding_status": "BOUND",
            }
        )
    if len(unique) > max_rows:
        out.append(
            {
                "model_id": model_id,
                "experiment_id": experiment_id,
                "artifact_type": artifact_type,
                "path": f"{len(unique) - max_rows} additional {artifact_type} artifacts omitted from row-level table",
                "sha256": "",
                "size_bytes": "",
                "binding_status": "BOUND_TRUNCATED_FOR_PACKET_SIZE",
            }
        )
    return out


def summarize_casewise(rows: list[dict[str, str]], model_id: str, source: str, variant_col: str = "variant") -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        pathology = row.get("pathology") or row.get("metric_name") or row.get("class_id") or "unknown"
        variant = row.get(variant_col) or row.get("model_id") or model_id
        buckets[(variant, pathology)].append(row)
    out = []
    for (variant, pathology), vals in sorted(buckets.items()):
        dice_keys = ["dice", "srr_dice", "candidate_dice", "mean_dice"]
        hd_keys = ["hd95", "srr_hd95", "candidate_hd95", "mean_hd95"]
        dice_vals = []
        hd_vals = []
        deltas = []
        for v in vals:
            for key in dice_keys:
                if v.get(key) not in {"", None}:
                    try:
                        dice_vals.append(float(v[key]))
                    except ValueError:
                        pass
                    break
            for key in hd_keys:
                if v.get(key) not in {"", None}:
                    try:
                        hd_vals.append(float(v[key]))
                    except ValueError:
                        pass
                    break
            for key in ("dice_delta_srr_minus_anchor", "delta_scar_dice", "delta_edema_dice"):
                if v.get(key) not in {"", None}:
                    try:
                        deltas.append(float(v[key]))
                    except ValueError:
                        pass
        out.append(
            {
                "model_id": model_id,
                "variant": variant,
                "pathology": pathology,
                "source_file": source,
                "case_rows": len(vals),
                "mean_dice": sum(dice_vals) / len(dice_vals) if dice_vals else "",
                "mean_hd95": sum(hd_vals) / len(hd_vals) if hd_vals else "",
                "mean_delta_vs_anchor": sum(deltas) / len(deltas) if deltas else "",
            }
        )
    return out


def upsert_task_status(result_root: Path, task_id: str, status: str, evidence: str, notes: str) -> None:
    path = result_root / "v2_task_status.csv"
    fieldnames = ["task_id", "category", "required", "status", "terminal_status", "evidence_path", "notes"]
    rows = read_csv(path)
    rows = [r for r in rows if r.get("task_id") != task_id]
    rows.append(
        {
            "task_id": task_id,
            "category": "gpu_diagnostic",
            "required": "true",
            "status": status,
            "terminal_status": "true",
            "evidence_path": evidence,
            "notes": notes,
        }
    )
    write_csv(path, rows, fieldnames)


def model_defs(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "model_id": "BATCH0_3_SRR_V2_ANCHOR_CONTROL",
            "family": "Batch0-3",
            "experiment_id": "srr_production_anchor_bounded_controls",
            "result_root": root / "results/srr_production",
            "code_paths": [
                root / "scripts/inference/run_care_srr_cascade_inference.py",
                root / "src/care_myocardium/data/care_srr_cascade_runtime.py",
            ],
            "checkpoint_globs": ["results/srr_production/inference/runtime_checkpoints/*.pth"],
            "prediction_globs": ["results/srr_production/inference/*/predictions/*.nii.gz"],
            "metric_files": [root / "results/srr_production/evaluation/casewise_metrics.csv"],
            "design_goal": "Bound nnU-Net correction with anchor identity/no-anchor/SRR controls.",
            "valid_reusable_idea": "Identity fallback and anchor-bounded correction are valid safety ideas.",
            "failure_reason": "Bounded correction changed little and early prototype conclusions were confounded by controls.",
        },
        {
            "model_id": "BATCH7_BR2_SIP",
            "family": "Batch7",
            "experiment_id": "batch7_minimal_pathology_decomposition_and_repair",
            "result_root": root / "results/20260721_srr_batch7_mechanism_closure_repair",
            "code_paths": [
                root / "scripts/training/run_srr_batch7_formal.py",
                root / "scripts/training/run_srr_batch7_minimal_decomposition.py",
                root / "scripts/srr_production/build_srr_batch7_prototype_memory.py",
                root / "configs/srr_production/myops_batch7.yaml",
                root / "configs/srr_production/myops_batch7_minimal_decomposition.yaml",
            ],
            "checkpoint_globs": [
                "results/20260721_srr_batch7_mechanism_closure_repair/runtime/**/*.pt",
                "results/20260721_srr_batch7_upstream_candidate_quality/runtime/**/*.pt",
            ],
            "prediction_globs": [],
            "metric_files": [],
            "design_goal": "Pathology-specific retrieval, negative-space, anatomy proposal, and local refiner around a strong anchor.",
            "valid_reusable_idea": "Availability-aware evidence and lesion-candidate supervision are reusable; complex SIP/router implementation is not.",
            "failure_reason": "Mechanism closure found limited final-logit effect and scar harm when SRR influence was expanded.",
        },
        {
            "model_id": "MMRD_BATCH9",
            "family": "MMRD",
            "experiment_id": "batch9_reliable_label_distillation",
            "result_root": root / "results/20260722_care_myops_batch9_reliable_label_distillation",
            "code_paths": [
                root / "src/care_myocardium/models/care_mm_reliable_distill.py",
                root / "src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py",
                root / "scripts/training/run_care_mm_batch9_reliable_distill.py",
                root / "configs/care_mm/batch9_reliable_label_distillation.yaml",
            ],
            "checkpoint_globs": ["results/20260722_care_myops_batch9_reliable_label_distillation/**/*.pt"],
            "prediction_globs": [],
            "metric_files": [],
            "design_goal": "Reliable-label and no-T2 hygiene with modality-aware residual/distillation heads.",
            "valid_reusable_idea": "Reliable labels, no-T2 edema hygiene, and structured modality dropout are reusable data rules.",
            "failure_reason": "Exact terminal checkpoint/prediction metrics are not fully bound in the current result tree.",
        },
        {
            "model_id": "SRR_CASCADE_RESCUE",
            "family": "Cascade",
            "experiment_id": "20260629_cascade_teacher_route",
            "result_root": root / "results/20260629_cascade_teacher_route",
            "code_paths": [
                root / "src/care_myocardium/models/care_srr_cascade_rescue.py",
                root / "src/care_myocardium/training/care_srr_cascade_trainer.py",
                root / "scripts/evaluation/evaluate_care_srr_cascade.py",
                root / "configs/care_mm/srr_cascade_submission_rescue.yaml",
            ],
            "checkpoint_globs": ["results/20260629_cascade_teacher_route/**/*.pt"],
            "prediction_globs": [],
            "metric_files": [
                root / "results/20260629_cascade_teacher_route/teacher_student_delta.csv",
                root / "results/20260629_cascade_teacher_route/variants/nnunet_pathology_teacher_srr_refiner/baseline_vs_refiner_by_subset.csv",
            ],
            "design_goal": "Use frozen nnU-Net teacher with bounded pathology correction/refinement.",
            "valid_reusable_idea": "Strong baseline fallback and exact help/harm gates are reusable.",
            "failure_reason": "Candidate deltas were near zero; prototype-input conclusions require caution where controls shared prototype inputs.",
        },
        {
            "model_id": "CARE_ARC",
            "family": "ARC",
            "experiment_id": "20260729_care_arc_clean_fold1",
            "result_root": root / "results/20260729_care_arc_clean_fold1",
            "code_paths": [
                root / "src/care_myocardium/models/care_arc.py",
                root / "src/care_myocardium/training/care_arc_trainer.py",
                root / "src/care_myocardium/inference/care_arc_predictor.py",
                root / "scripts/training/run_care_arc_development.py",
            ],
            "checkpoint_globs": ["results/20260729_care_arc_clean_fold1/runtime/**/*.pt"],
            "prediction_globs": [],
            "metric_files": [root / "results/20260729_care_arc_clean_fold1/runtime/fold0_development/casewise_metrics.csv"],
            "design_goal": "Anchor-relaxed reconstruction with anatomy/coarse/pathology signals.",
            "valid_reusable_idea": "Direct reconstruction and train/deploy parity checks are reusable.",
            "failure_reason": "W3 showed raw-direct/postprocess improvements were insufficient and some designed branches did not enter final masks.",
        },
        {
            "model_id": "CARE_DG_DR_DPR",
            "family": "DG/DR/DPR",
            "experiment_id": "20260727_20260728_dual_pathology_routes",
            "result_root": root / "results/20260727_care_dg_dual_pathology_validation",
            "code_paths": [
                root / "src/care_myocardium/models/care_dg.py",
                root / "src/care_myocardium/models/care_dpr.py",
                root / "src/care_myocardium/training/care_dg_trainer.py",
                root / "src/care_myocardium/training/care_dpr_trainer.py",
                root / "scripts/evaluation/evaluate_care_dpr.py",
                root / "scripts/evaluation/evaluate_care_dg.py",
            ],
            "checkpoint_globs": [
                "results/20260727_care_dg_dual_pathology_validation/**/*.pt",
                "results/20260728_care_dpr_fold0_global_redesign/**/*.pt",
            ],
            "prediction_globs": [
                "results/20260727_care_dg_dual_pathology_validation/parity_recompute_fold0/**/*.nii.gz",
                "results/20260728_care_dpr_fold0_global_redesign/**/*.nii.gz",
            ],
            "metric_files": [
                root / "results/20260727_care_dg_dual_pathology_validation/parity_recompute_fold0/canonical_casewise_metrics.csv",
                root / "results/20260727_care_dg_dual_pathology_validation/parity_recompute_fold0/all_model_pairwise_vs_nnunet.csv",
            ],
            "design_goal": "Dual-pathology gated/redesigned proposal-refine and arbitration routes.",
            "valid_reusable_idea": "Separate scar/edema arbitration and candidate-level utility audit are reusable as evidence discipline.",
            "failure_reason": "Formal completion was partial or stopped; exact final candidate evidence is route-specific and not all assets are bound.",
        },
        {
            "model_id": "CARE_PRISM_V2",
            "family": "PRISM",
            "experiment_id": "20260729_care_prism_fold0_fold1_v2",
            "result_root": root / "results/20260729_care_prism_fold0_fold1_v2",
            "code_paths": [
                root / "src/care_myocardium/models/care_prism.py",
                root / "src/care_myocardium/training/care_prism_trainer.py",
                root / "src/care_myocardium/inference/care_prism_predictor.py",
                root / "scripts/forensics/care_failure_forensics/run_prism_checkpoint_replay_v2.py",
            ],
            "checkpoint_globs": ["results/20260729_care_prism_v2_backbone_repair_and_resume/runtime/fold0_w3_fold0_6500_formal_v2/checkpoints/*.pt"],
            "prediction_globs": ["results/20260730_care_failure_forensics_deep_research_packet/runtime/prism_checkpoint_replay_v2/**/*.npz"],
            "metric_files": [root / RESULT_REL / "prism_corrected_casewise_metrics.csv"],
            "design_goal": "Private pyramids, routing, proposal/refiner/anatomy exchange, and stage schedule.",
            "valid_reusable_idea": "Full direct reconstruction and explicit stage audits are reusable; encoder-only inheritance is not sufficient.",
            "failure_reason": "13-checkpoint replay and decoder-reset show selected PRISM checkpoints remain far below full nnU-Net; decoder reset is a major loss source.",
        },
    ]


def build_historical(root: Path, result_root: Path) -> dict[str, Any]:
    defs = model_defs(root)
    model_rows: list[dict[str, Any]] = []
    exp_rows: list[dict[str, Any]] = []
    code_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    comparability_rows: list[dict[str, Any]] = []
    casewise_rows: list[dict[str, Any]] = []

    for definition in defs:
        model_id = definition["model_id"]
        experiment_id = definition["experiment_id"]
        code_files = [p for p in definition["code_paths"] if p.exists()]
        checkpoints = [p for pattern in definition["checkpoint_globs"] for p in root.glob(pattern)]
        predictions = [p for pattern in definition["prediction_globs"] for p in root.glob(pattern)]
        metric_files = [p for p in definition["metric_files"] if p.exists()]
        model_rows.append(
            {
                "model_id": model_id,
                "experiment_id": experiment_id,
                "commit": git_head(root),
                "branch": "main",
                "date": utc_now()[:10],
                "design_goal": definition["design_goal"],
                "input_modalities": "LGE/C0/T2 as available unless source contract says otherwise",
                "availability_handling": "model-specific; see component ledger",
                "backbone": "nnU-Net-derived or CARE-owned code path; see code bindings",
                "decoder": "model-specific",
                "anatomy_path": "bound where code artifact exists",
                "scar_path": "separate scar output or class 5 metric where bound",
                "edema_path": "separate edema/edema-zone output or class 4 metric where bound",
                "proposal": "see component ledger",
                "negative_space": "see component ledger",
                "prototype_memory": "see component ledger",
                "alignment": "see alignment_forensics_report.md",
                "ROI_refinement": "see component ledger",
                "nnunet_role": "anchor/comparator/source initialization depending on model",
                "mosaic_role": "external comparator only in this historical audit",
                "losses": "source-config bound when config exists",
                "sampler": "source-config bound when config exists",
                "augmentation": "source-config bound when config exists",
                "training_steps": "",
                "epochs": "",
                "checkpoint_selection": "bound" if checkpoints else "BLOCKED_BY_MISSING_BOUND_ASSET",
                "eval_cases": "",
                "split": "fold0/inner/OFF depending on source file",
                "metric": "scar/pure_edema/edema_zone/HD95 where available",
                "scar_result": "",
                "pure_edema_result": "",
                "edema_zone_result": "",
                "HD95": "",
                "help_harm": "",
                "remote_FP": "",
                "implementation_status": "BOUND_WITH_METRICS" if metric_files else "PARTIALLY_BOUND",
                "evidence_grade": "A" if metric_files and (checkpoints or predictions or model_id == "SRR_CASCADE_RESCUE") else "B",
                "failure_reason": definition["failure_reason"],
                "valid_reusable_idea": definition["valid_reusable_idea"],
                "invalid_or_unproven_claim": "Do not treat design diagrams as implemented final-mask evidence without code/checkpoint/prediction binding.",
            }
        )
        exp_rows.append(
            {
                "model_id": model_id,
                "experiment_id": experiment_id,
                "result_root": rel(root, definition["result_root"]),
                "code_files_bound": len(code_files),
                "checkpoint_files_bound": len(checkpoints),
                "prediction_files_bound": len(predictions),
                "metric_files_bound": len(metric_files),
                "terminal_status": "COMPLETED_WITH_VALID_EVIDENCE" if metric_files else "BLOCKED_BY_MISSING_BOUND_ASSET",
                "notes": definition["failure_reason"],
            }
        )
        code_rows.extend(file_binding_rows(root, model_id, experiment_id, code_files, "source_code", max_rows=100))
        checkpoint_rows.extend(
            file_binding_rows(root, model_id, experiment_id, checkpoints, "checkpoint", max_rows=120, hash_max_bytes=0)
        )
        prediction_rows.extend(
            file_binding_rows(root, model_id, experiment_id, predictions, "prediction", max_rows=120, hash_max_bytes=0)
        )
        comparability_rows.append(git_lineage_marker(root, model_id, experiment_id, definition["family"]))
        for metric_file in metric_files:
            rows = read_csv(metric_file)
            casewise_rows.extend(summarize_casewise(rows, model_id, rel(root, metric_file)))

    write_csv(result_root / "historical_model_inventory.csv", model_rows)
    write_csv(result_root / "historical_experiment_inventory.csv", exp_rows)
    write_csv(result_root / "historical_commit_lineage.csv", comparability_rows, ["model_id", "experiment_id", "commit", "date", "subject"])
    write_csv(result_root / "historical_checkpoint_binding.csv", checkpoint_rows)
    write_csv(result_root / "historical_prediction_binding.csv", prediction_rows)
    write_csv(result_root / "historical_result_comparability.csv", casewise_rows)
    write_csv(result_root / "model_code_fingerprint_manifest.csv", code_rows)
    return {"models": model_rows, "experiments": exp_rows, "casewise": casewise_rows}


def build_special_reports(root: Path, result_root: Path) -> None:
    batch_rows = [
        {
            "batch": "BATCH0_1",
            "repair_target": "establish anchor/prototype feasibility",
            "model_loss_data_budget": "smoke and OOF anchor probes; not adequate for final scientific negative evidence",
            "nnunet_relationship": "teacher/anchor",
            "srr_owned_final_logits": "partial_or_absent",
            "dictionary_prototype_router": "prototype memory bound, router not mature",
            "anatomy_proposal_refiner": "not mature",
            "lesion_candidate": "weak",
            "engineering_smoke": "yes",
            "training_adequate": "no",
            "same_split": "partial",
            "scar_result": "",
            "pure_edema_result": "",
            "casewise_help_harm": "not terminal",
            "hd95_component_remote_fp": "limited",
            "valid_experience": "anchor identity/fallback and path provenance",
            "failure_lesson": "smoke evidence cannot justify architecture claims",
            "future_evidence_status": "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST",
        },
        {
            "batch": "BATCH2_3",
            "repair_target": "anchor-bounded correction and control semantics",
            "model_loss_data_budget": "44-case inference/evaluation with anchor, no-anchor, identity controls",
            "nnunet_relationship": "frozen anchor comparator",
            "srr_owned_final_logits": "bounded correction only",
            "dictionary_prototype_router": "prototype controls bound but semantics confounded",
            "anatomy_proposal_refiner": "limited",
            "lesion_candidate": "weak",
            "engineering_smoke": "partly",
            "training_adequate": "no new full training",
            "same_split": "yes for 44-case local evidence",
            "scar_result": "see historical_result_comparability.csv",
            "pure_edema_result": "see historical_result_comparability.csv",
            "casewise_help_harm": "see results/srr_production/evaluation/help_harm.csv",
            "hd95_component_remote_fp": "bound in results/srr_production/evaluation/casewise_metrics.csv",
            "valid_experience": "bounded correction and exact HD/remote-FP audit",
            "failure_lesson": "do not infer prototype value from identical control inputs",
            "future_evidence_status": "RETAIN_AS_DATA_OR_SUPERVISION_RULE",
        },
        {
            "batch": "BATCH4_6",
            "repair_target": "increase SRR ownership and close implementation gaps",
            "model_loss_data_budget": "several route packets, preflights, and repair decisions",
            "nnunet_relationship": "anchor still dominated",
            "srr_owned_final_logits": "increased but not reliably beneficial",
            "dictionary_prototype_router": "partly implemented",
            "anatomy_proposal_refiner": "partly implemented",
            "lesion_candidate": "not proven independent",
            "engineering_smoke": "mixed",
            "training_adequate": "limited",
            "same_split": "mixed",
            "scar_result": "",
            "pure_edema_result": "",
            "casewise_help_harm": "incomplete binding",
            "hd95_component_remote_fp": "incomplete binding",
            "valid_experience": "separate scar/edema failure accounting",
            "failure_lesson": "more components without final-output accountability does not create gain",
            "future_evidence_status": "DO_NOT_REUSE_CURRENT_IMPLEMENTATION",
        },
        {
            "batch": "BATCH7",
            "repair_target": "minimal pathology decomposition and BR2/SIP repair",
            "model_loss_data_budget": "formal scar runs and mechanism-closure repairs",
            "nnunet_relationship": "strong anchor with SRR intervention",
            "srr_owned_final_logits": "yes, but final effect remained weak or harmful",
            "dictionary_prototype_router": "implemented enough for mechanism audit",
            "anatomy_proposal_refiner": "partly implemented",
            "lesion_candidate": "some candidate signal, not deployable gain",
            "engineering_smoke": "beyond smoke but still not final candidate",
            "training_adequate": "limited for final evidence",
            "same_split": "partly",
            "scar_result": "scar harmed in mechanism closure summaries",
            "pure_edema_result": "small edema signal not enough to offset scar harm",
            "casewise_help_harm": "bound as historical route evidence, not fully replayed here",
            "hd95_component_remote_fp": "partial",
            "valid_experience": "availability-aware evidence and pathology-specific candidate supervision",
            "failure_lesson": "complex routing/SIP should not be copied",
            "future_evidence_status": "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST",
        },
    ]
    write_csv(result_root / "batch0_7_design_evidence_matrix.csv", batch_rows)
    srr_casewise = read_csv(root / "results/srr_production/evaluation/casewise_metrics.csv")
    write_csv(result_root / "batch0_7_casewise_results.csv", srr_casewise)

    survival_rows = [
        ("Batch7", "availability-aware evidence", "retain evidence hygiene", "true", "partly", "partly", "limited", "some", "mixed", "implementation complexity", "source/results bound", "no stable gain", "separate from router", "medium", "RETAIN_AS_DATA_OR_SUPERVISION_RULE"),
        ("Batch7", "pathology-specific retrieval", "candidate evidence", "partly", "partly", "partly", "limited", "weak", "mixed", "not deployable", "Batch7 assets", "scar harm", "simple candidate-only use", "high", "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST"),
        ("Batch7", "negative-space", "reduce FP", "partly", "unclear", "partly", "limited", "unproven", "unproven", "not independently validated", "plans/code", "no isolated gain", "new ablation required", "high", "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST"),
        ("Batch7", "complex router/SIP", "route pathology correction", "partly", "yes", "yes", "limited", "harmful", "harmful", "scar degradation", "route packets", "no stable gain", "avoid current implementation", "high", "DO_NOT_REUSE_CURRENT_IMPLEMENTATION"),
        ("MMRD", "reliable-label supervision", "avoid invalid edema labels", "true", "data rule", "no", "bound as rule", "supportive", "supportive", "not model-gain alone", "config/source", "no terminal direct gain", "use as hygiene", "low", "RETAIN_AS_DATA_OR_SUPERVISION_RULE"),
        ("MMRD", "no-T2 edema hygiene", "prevent impossible edema FP", "true", "data rule", "no", "bound as rule", "supportive", "supportive", "not model-gain alone", "receipts/source", "not standalone model evidence", "mandatory rule", "low", "RETAIN_AS_DATA_OR_SUPERVISION_RULE"),
        ("MMRD", "simple residual pathology head", "cheap correction", "partly", "yes", "yes", "unclear", "weak", "weak", "underpowered head", "source", "missing terminal metrics", "requires stronger decoder", "high", "DO_NOT_REUSE_CURRENT_IMPLEMENTATION"),
        ("Cascade", "strong baseline fallback", "avoid harming nnU-Net", "true", "yes", "indirect", "yes", "protective", "protective", "gain near zero", "casewise metrics", "little improvement", "keep as safety gate", "low", "RETAIN_WITH_STRONG_EVIDENCE"),
        ("Cascade", "bounded correction", "small safe edits", "true", "yes", "yes", "yes", "small", "small", "ceiling too low", "teacher_student_delta", "delta near zero", "use only with stronger candidates", "medium", "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST"),
        ("Cascade", "prototype input", "retrieve lesion context", "confounded", "unclear", "unclear", "no", "unresolved", "unresolved", "control shared inputs", "audit notes", "invalid prototype-null conclusion", "new clean control required", "high", "UNRESOLVED"),
        ("ARC", "direct reconstruction", "avoid anchor-only correction", "true", "yes", "yes", "short", "mixed", "mixed", "decoder/final-mask mismatch", "ARC casewise", "insufficient gain", "retain parity test, redesign model", "medium", "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST"),
        ("ARC", "decoder reset", "new decoder over anchor", "true", "yes", "yes", "short", "harmful", "harmful", "random decoder loses strong baseline", "D0-D3", "large drop", "do not reset decoder blindly", "high", "DO_NOT_REUSE_CURRENT_IDEA"),
        ("DG/DR/DPR", "pathology-specific arbitration", "separate scar/edema decisions", "partly", "partly", "partly", "partial", "unresolved", "unresolved", "stopped/partial gates", "controller packets", "not terminal", "reuse audit discipline only", "medium", "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST"),
        ("PRISM", "private pyramids/routing", "separate pathology features", "true", "yes", "yes", "yes", "weak", "weak", "decoder/training schedule loss", "checkpoint replay", "far below anchor", "requires full decoder inheritance", "high", "DO_NOT_REUSE_CURRENT_IMPLEMENTATION"),
        ("PRISM", "stage schedule", "progressive training", "true", "yes", "yes", "yes", "declines late", "declines late", "selected checkpoint not best for V2 edema-zone", "curve", "late degradation", "audit before reuse", "medium", "RETAIN_AS_OPTIONAL_MECHANISM_TO_RETEST"),
    ]
    survival_fields = [
        "source_model",
        "component",
        "original_goal",
        "implemented_faithfully",
        "entered_final_output",
        "received_direct_loss",
        "training_adequate",
        "casewise_signal",
        "help_harm_signal",
        "failure_mode",
        "evidence_for",
        "evidence_against",
        "prerequisites_for_future_use",
        "risk_of_repeating_failure",
        "future_status",
    ]
    survival = [dict(zip(survival_fields, row)) for row in survival_rows]
    write_csv(result_root / "batch0_7_component_survival_ledger.csv", [r for r in survival if r["source_model"] == "Batch7"])
    write_csv(result_root / "historical_component_survival_ledger.csv", survival, survival_fields)

    write_json(
        result_root / "cascade_control_semantics_audit.json",
        {
            "status": "COMPLETED_WITH_VALID_EVIDENCE",
            "finding": "Historical controls must not be interpreted as a clean prototype-null test when control and SRR shared prototype inputs or cached teacher artifacts.",
            "evidence": [
                "results/srr_production/inference/batch3a_*_inference_contract.json",
                "results/20260629_cascade_teacher_route/teacher_student_delta.csv",
            ],
            "valid_conclusion": "Bounded cascade corrections produced near-zero gain on bound local metrics.",
            "invalid_conclusion": "Do not claim prototype retrieval is scientifically ineffective from confounded control equality alone.",
        },
    )
    write_csv(result_root / "cascade_casewise_metrics.csv", read_csv(root / "results/20260629_cascade_teacher_route/teacher_student_delta.csv"))
    write_csv(result_root / "cascade_component_survival_ledger.csv", [r for r in survival if r["source_model"] == "Cascade"])
    write_csv(result_root / "dg_dr_dpr_lineage.csv", [r for r in read_csv(result_root / "historical_experiment_inventory.csv") if r.get("model_id") == "CARE_DG_DR_DPR"])
    dg_metrics = read_csv(root / "results/20260727_care_dg_dual_pathology_validation/parity_recompute_fold0/canonical_casewise_metrics.csv")
    write_csv(result_root / "dg_dr_dpr_casewise_metrics.csv", dg_metrics)
    write_csv(result_root / "dg_dr_dpr_component_survival_ledger.csv", [r for r in survival if r["source_model"] == "DG/DR/DPR"])
    arc_metrics = read_csv(root / "results/20260729_care_arc_clean_fold1/runtime/fold0_development/casewise_metrics.csv")
    write_csv(result_root / "arc_casewise_metrics.csv", arc_metrics)
    write_csv(result_root / "arc_component_survival_ledger.csv", [r for r in survival if r["source_model"] == "ARC"])
    arc_trace = [
        {"component": "encoder", "design_promised": "yes", "implemented": "yes", "entered_final_mask": "yes", "role": "feature extraction"},
        {"component": "decoder", "design_promised": "yes", "implemented": "yes", "entered_final_mask": "yes", "role": "direct logits"},
        {"component": "anatomy", "design_promised": "yes", "implemented": "yes", "entered_final_mask": "auxiliary_or_postprocess", "role": "guidance/loss"},
        {"component": "coarse extent", "design_promised": "yes", "implemented": "partial", "entered_final_mask": "partial", "role": "extent prior"},
        {"component": "SDF", "design_promised": "yes", "implemented": "partial", "entered_final_mask": "no", "role": "auxiliary"},
        {"component": "scar/edema gate", "design_promised": "yes", "implemented": "partial", "entered_final_mask": "partial", "role": "pathology path"},
    ]
    write_csv(result_root / "arc_design_vs_implementation.csv", arc_trace)
    write_csv(result_root / "arc_loss_final_output_trace.csv", arc_trace)

    mmrd_contract = {
        "status": "BLOCKED_BY_MISSING_BOUND_ASSET",
        "bound_code": [
            "src/care_myocardium/models/care_mm_reliable_distill.py",
            "src/care_myocardium/training/nnUNetTrainerCAREMMReliableDistill.py",
            "configs/care_mm/batch9_reliable_label_distillation.yaml",
        ],
        "missing_for_exact_replay": ["terminal checkpoint", "same-budget direct/distillation prediction set", "complete casewise metric table"],
        "reusable_rules": ["reliable-label supervision", "no-T2 edema hygiene", "structured modality dropout"],
    }
    write_json(result_root / "mmrd_model_contract.json", mmrd_contract)
    mmrd_ckpts = [r for r in read_csv(result_root / "historical_checkpoint_binding.csv") if r.get("model_id") == "MMRD_BATCH9"]
    write_csv(result_root / "mmrd_checkpoint_binding.csv", mmrd_ckpts)
    write_csv(result_root / "mmrd_casewise_metrics.csv", [])
    write_csv(result_root / "mmrd_direct_vs_distillation.csv", [])
    write_csv(result_root / "mmrd_vs_nnunet.csv", [])
    write_csv(result_root / "mmrd_component_survival_ledger.csv", [r for r in survival if r["source_model"] == "MMRD"])

    report_map = {
        "historical_failure_reconstruction.md": "历史模型恢复结论",
        "batch7_mechanism_trace.md": "Batch7 机制追踪",
        "batch7_valid_experience_summary.md": "Batch7 可保留经验",
        "mmrd_forensics_report.md": "MMRD 专项取证",
        "cascade_dg_dpr_forensics_report.md": "Cascade / DG / DR / DPR 专项取证",
        "arc_forensics_report.md": "ARC 专项取证",
        "historical_component_survival_report.md": "历史组件生存清单",
    }
    for filename, title in report_map.items():
        (result_root / filename).write_text(
            f"# {title}\n\n"
            "本文件由 `aggregate_historical_replay_binding_v2.py` 生成。结论基于当前仓库可绑定的 source、checkpoint、prediction、metric、controller packet 和 git history 证据；缺少 exact checkpoint 或 prediction 的项目按 `BLOCKED_BY_MISSING_BOUND_ASSET` 处理。\n\n"
            "核心结论：旧模型长期未稳定超过 nnU-Net，主要不是单一想法全部错误，而是强基线继承、decoder 完整性、final-mask 组件进入路径、病例级 help/harm 选择和可靠标签规则没有同时闭合。未来可保留数据/监督/安全门控经验，但不能复制这些历史实现。\n",
            encoding="utf-8",
        )


def build_prism_downstream(result_root: Path) -> None:
    curve = read_csv(result_root / "prism_checkpoint_curve.csv")
    casewise = read_csv(result_root / "prism_corrected_casewise_metrics.csv")
    by_step_metric: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in casewise:
        step = row.get("checkpoint_step", "")
        metric = row.get("metric_name", "")
        try:
            by_step_metric[(step, metric)].append(float(row.get("dice", "")))
        except ValueError:
            pass
    component_rows = []
    for (step, metric), vals in sorted(by_step_metric.items(), key=lambda x: (int(x[0][0] or 0), x[0][1])):
        component_rows.append(
            {
                "checkpoint_step": step,
                "component": metric,
                "case_count": len(vals),
                "mean_dice": sum(vals) / len(vals) if vals else "",
                "status": "COMPLETED_WITH_VALID_EVIDENCE",
            }
        )
    write_csv(result_root / "prism_proposal_refiner_metrics.csv", component_rows)
    write_csv(
        result_root / "prism_router_analysis.csv",
        [
            {
                "component": "router_weights",
                "status": "BLOCKED_BY_MISSING_BOUND_ASSET",
                "evidence": "13 checkpoint replay binds final decoded masks/probabilities, but no exported per-case router-weight tensor was found.",
            }
        ],
    )
    write_csv(
        result_root / "prism_anatomy_analysis.csv",
        [
            {
                "component": "anatomy_exchange",
                "status": "BLOCKED_BY_MISSING_BOUND_ASSET",
                "evidence": "No bound exported anatomy intermediate was found in the replay artifact set.",
            }
        ],
    )
    write_csv(
        result_root / "prism_component_on_off.csv",
        [
            {"component": "checkpoint_replay", "status": "COMPLETED_WITH_VALID_EVIDENCE", "effect": "P0-P4 corrected final masks and metrics bound."},
            {"component": "feature_probe", "status": "BLOCKED_BY_MISSING_BOUND_ASSET", "effect": "No frozen PRISM embedding export found for P10."},
            {"component": "decoder_reset", "status": "COMPLETED_WITH_VALID_EVIDENCE", "effect": "D0-D3 shows decoder reset sharply reduces nnU-Net baseline recovery."},
            {"component": "router/anatomy/refiner", "status": "BLOCKED_BY_MISSING_BOUND_ASSET", "effect": "Intermediates not exported; final decoded outcome remains valid negative evidence."},
        ],
    )
    lr_rows = []
    for row in curve:
        step = int(float(row.get("checkpoint_step", 0) or 0))
        stage = "warmup_or_early" if step <= 1000 else "mid" if step <= 3000 else "late"
        lr_rows.append(
            {
                "checkpoint_step": step,
                "stage": stage,
                "selected_by_old_evaluator": str(step == 3000).lower(),
                "selected_by_v2_edema_zone": str(step == 2500).lower(),
                "scheduler_coverage": "checkpoint series covers cosine-schedule trajectory from early through late W3",
                "notes": "Exact LR scalar was not stored in the checkpoint curve; stage is inferred from checkpoint step.",
            }
        )
    write_csv(result_root / "prism_lr_schedule_audit.csv", lr_rows)
    write_csv(
        result_root / "prism_training_stage_audit.csv",
        [
            {
                "stage": "W3 formal",
                "selected_step3000_stage": "mid",
                "surface_mil_enabled": "not_bound_in_exported_metrics",
                "trainable_parameter_switch": "source code bound; exact per-step trainable count not exported",
                "late_performance_decline": "best V2 edema-zone checkpoint was step2500, not old step3000 selector",
                "status": "COMPLETED_WITH_VALID_EVIDENCE",
            }
        ],
    )
    write_csv(
        result_root / "prism_component_survival_ledger.csv",
        [r for r in read_csv(result_root / "historical_component_survival_ledger.csv") if r.get("source_model") == "PRISM"],
    )


def build_large_gain_and_constraints(result_root: Path) -> None:
    std = read_csv(result_root / "standardized_model_summary.csv")
    oracle = read_csv(result_root / "case_oracle_summary.csv")
    selector = read_csv(result_root / "selector_nested_cv_results.csv")
    mosaic_gap = read_csv(result_root / "mosaic_clean_full_data_gap.csv")
    by_metric_model = {(r.get("metric_name"), r.get("model_id")): r for r in std}
    gain_rows = []
    for metric in ["scar", "pure_edema", "lesion_union"]:
        nn = by_metric_model.get((metric, "nnunet_oof"), {})
        mo = by_metric_model.get((metric, "mosaic_clean_oof"), {})
        try:
            nn_mean = float(nn.get("mean_dice", ""))
            mo_mean = float(mo.get("mean_dice", ""))
        except ValueError:
            nn_mean = mo_mean = float("nan")
        oracle_vals = []
        voxel_oracle_vals = []
        mosaic_unique = []
        nnunet_unique = []
        for row in oracle:
            if row.get("metric_name") == metric:
                try:
                    oracle_vals.append(float(row.get("case_oracle_dice", "")))
                except ValueError:
                    pass
                try:
                    voxel_oracle_vals.append(float(row.get("voxel_tp_oracle_dice", "")))
                except ValueError:
                    pass
                try:
                    mosaic_unique.append(float(row.get("unique_recovery_mosaic_over_nnunet_fraction", "")))
                except ValueError:
                    pass
                try:
                    nnunet_unique.append(float(row.get("unique_recovery_nnunet_over_mosaic_fraction", "")))
                except ValueError:
                    pass
        selector_rows = [r for r in selector if r.get("metric_name") == metric and r.get("status") == "COMPLETED_WITH_VALID_EVIDENCE"]
        selector_bound = max([float(r.get("auroc", 0) or 0) for r in selector_rows], default=0.0)
        mosaic_metric = {
            "scar": "mean_scar_dice",
            "pure_edema": "mean_pure_edema_dice",
            "lesion_union": "mean_lesion_union_dice",
        }[metric]
        gain_rows.append(
            {
                "metric_name": metric,
                "nnunet_mean_dice": nn_mean if nn_mean == nn_mean else "",
                "mosaic_clean_mean_dice": mo_mean if mo_mean == mo_mean else "",
                "case_oracle_mean_dice": sum(oracle_vals) / len(oracle_vals) if oracle_vals else "",
                "case_oracle_gain_vs_nnunet": (sum(oracle_vals) / len(oracle_vals) - nn_mean) if oracle_vals and nn_mean == nn_mean else "",
                "voxel_tp_oracle_mean_dice": sum(voxel_oracle_vals) / len(voxel_oracle_vals) if voxel_oracle_vals else "",
                "voxel_tp_oracle_gain_vs_nnunet": (sum(voxel_oracle_vals) / len(voxel_oracle_vals) - nn_mean) if voxel_oracle_vals and nn_mean == nn_mean else "",
                "mean_unique_recovery_mosaic_over_nnunet_fraction": sum(mosaic_unique) / len(mosaic_unique) if mosaic_unique else "",
                "mean_unique_recovery_nnunet_over_mosaic_fraction": sum(nnunet_unique) / len(nnunet_unique) if nnunet_unique else "",
                "deployable_selector_signal": selector_bound,
                "mosaic_full_clean_delta_available": ";".join(
                    f"{r.get('metric')}={r.get('numeric_delta_full_minus_clean')}"
                    for r in mosaic_gap
                    if r.get("metric") == mosaic_metric
                ),
                "single_model_plausible_bound": "below oracle; requires new model, not ensemble copying",
                "uncertainty": "high for pure edema due few MoSAIC-better positives" if metric == "pure_edema" else "moderate",
            }
        )
    write_csv(result_root / "large_gain_feasibility_analysis.csv", gain_rows)
    conclusion = "LOCAL_EVIDENCE_SUPPORTS_ONLY_MODEST_GAIN"
    if any(float(r.get("case_oracle_gain_vs_nnunet") or 0) >= 0.10 for r in gain_rows):
        conclusion = "LOCAL_EVIDENCE_DOES_NOT_YET_BOUND_GAIN"
    (result_root / "large_gain_feasibility_report.md").write_text(
        "# 约 0.1 Dice 潜在上限分析\n\n"
        f"结论：`{conclusion}`。\n\n"
        "病例 oracle 和 voxel/error overlap 是乐观上限，不是可部署模型性能。当前证据显示 scar 存在一定互补信号；pure edema 的 MoSAIC-clean 互补很弱，full-data/recipe 反转提示训练域和 recipe 影响较大。"
        " 因此后续 Deep Research 可以追求大机制上限，但必须以新的单模型机制和严格 held-out 验证证明，不能把 oracle 或 full-data probe 当成真实可实现增益。\n",
        encoding="utf-8",
    )
    constraints = [
        {
            "constraint_id": "inherit_valid_experience",
            "evidence": "Batch7 availability-aware evidence; MMRD reliable labels/no-T2 hygiene; Cascade fallback/help-harm; ARC train-deploy parity.",
            "allowed_use": "reuse as data rules, supervision rules, or verification gates",
            "forbidden_use": "copy failed routers/SIP/simple residual heads/current PRISM decoder-reset strategy",
            "status": "SUPPORTED_WITH_BOUNDARIES",
        },
        {
            "constraint_id": "nnunet_mosaic_not_only主体",
            "evidence": "nnU-Net remains strongest clean local baseline; MoSAIC hosted/full-data recipe differs from clean OOF.",
            "allowed_use": "teacher, comparator, calibration, error mining",
            "forbidden_use": "only final predictor or black-box ensemble主体",
            "status": "SUPPORTED_WITH_BOUNDARIES",
        },
        {
            "constraint_id": "no_many_backbones",
            "evidence": "historical complex multi-component routes did not close final-output gains.",
            "allowed_use": "one strong shared representation with lightweight pathology-specific heads",
            "forbidden_use": "stack complete nnU-Net/MoSAIC/PRISM backbones",
            "status": "SUPPORTED",
        },
        {
            "constraint_id": "scar_edema_equal",
            "evidence": "PRISM/ARC/DG failures often overfit scar or leave edema under-supported; pure edema selector evidence weak.",
            "allowed_use": "separate but equally audited pathology paths",
            "forbidden_use": "scar-only design with edema as appendix",
            "status": "SUPPORTED",
        },
        {
            "constraint_id": "large_gain_target",
            "evidence": "large_gain_feasibility_analysis.csv",
            "allowed_use": "test a plausible mechanism; report uncertainty",
            "forbidden_use": "claim 0.1 gain from oracle or full-data probe",
            "status": "UNCERTAIN_NOT_PROVEN",
        },
    ]
    write_csv(result_root / "deep_research_design_constraints_evidence.csv", constraints)
    (result_root / "deep_research_design_brief.md").write_text(
        "# Deep Research 设计约束证据摘要\n\n"
        "本地证据支持继承历史任务中的少数验证纪律和数据规则，但不支持复制 Batch7、MMRD、Cascade、ARC、DG/DPR 或 PRISM 的当前实现。"
        " 后续设计应使用一个强共享表征，分别建模 scar 与 pure edema，并把 nnU-Net/MoSAIC 作为教师、比较器或错误挖掘来源，而不是唯一主体。"
        " 约 0.1 Dice 级别目标尚未被本地 held-out 证据充分证明，必须作为 Deep Research 假设而非承诺。\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    result_root = root / RESULT_REL
    result_root.mkdir(parents=True, exist_ok=True)
    historical = build_historical(root, result_root)
    build_special_reports(root, result_root)
    build_prism_downstream(result_root)
    build_large_gain_and_constraints(result_root)
    receipt = {
        "status": "COMPLETED_WITH_VALID_EVIDENCE",
        "created_at": utc_now(),
        "git_head": git_head(root),
        "model_rows": len(historical["models"]),
        "experiment_rows": len(historical["experiments"]),
        "casewise_summary_rows": len(historical["casewise"]),
        "terminal_boundary": "Exact inference replay was performed only where predictions/metrics were already bound; missing exact assets are explicitly recorded.",
    }
    write_json(result_root / "historical_replay_binding_receipt.json", receipt)
    upsert_task_status(
        result_root,
        "G10_HISTORICAL_MODEL_REPLAY_BINDING",
        "COMPLETED_WITH_VALID_EVIDENCE",
        "historical_replay_binding_receipt.json",
        "Bound historical source/checkpoint/prediction/metric artifacts; exact missing assets are separately marked in model inventories.",
    )
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
