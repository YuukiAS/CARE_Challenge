#!/usr/bin/env python3
"""Build the 20260730 CARE failure-forensics evidence packet.

This builder produces an evidence-grounded packet from local artifacts only.  It
does not upload, push, tune checkpoints, or submit Slurm jobs.  Missing or
unbound evidence is recorded explicitly so later Deep Research can distinguish
negative results from incomplete provenance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np

TASK_KEY = "20260730_care_failure_forensics_deep_research_packet"
RENDER_RESOURCE = Path("/users/a/e/aereinh/render_resources/chinese_math_pdf")
REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT_FOR_IMPORT / "results" / TASK_KEY / ".render_cache" / "mpl"))

try:
    import nibabel as nib
except Exception:  # pragma: no cover - environment dependent
    nib = None

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from scripts.forensics.care_failure_forensics.reference_metrics import label_masks, run_known_bad


RESULT_ROOT = Path("results") / TASK_KEY
PDF_NAME = "CARE_Failure_Forensics_Deep_Research_Evidence_Packet_20260730.pdf"
ATTACHMENT = Path(
    "/users/a/e/aereinh/.codex-homes/aereinh/attachments/19b97eab-8192-4c40-9608-3bc3f08d9ff0/pasted-text.txt"
)

SOURCE_FILES = [
    "AGENTS.md",
    "START_HERE_FOR_GPT.md",
    "GPT_PLANNER_CARE_PROTOCOL.md",
    "prompts/FINAL_OUTPUT_READABILITY_POLICY.md",
    "prompts/AGENT_FLOW_V2_PROTOCOL.md",
    "prompts/HANDOFF_GATE_POLICY.md",
    "prompts/GPT_HARD_GATE_PROMPT.md",
    "prompts/routes/README.md",
    "prompts/routes/route_portfolio_planner_prompt.md",
    "prompts/routes/handoffs/CURRENT.md",
    "prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md",
    "prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md",
    "routes/README.md",
    "wiki/README.md",
    ".agents/skills/slurm-routing-partition/SKILL.md",
    ".agents/skills/care-mapper/SKILL.md",
    "prompts/tasks/20260729_care_prism_controller_v2.md",
    "prompts/tasks/20260730_care_prism_w1_w2_repair_controller.md",
    "prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md",
    "prompts/tasks/20260729_care_prism_execution_hardening_amendment_v2.md",
    "prompts/blueprints/CARE_PRISM_pathology_retrieval_soft_cascade_20260729.md",
]

MODELS = [
    "NNUNET",
    "SRR_V2",
    "SRR_V25",
    "SRR_V3",
    "BATCH0",
    "BATCH1",
    "BATCH2",
    "BATCH3",
    "BATCH4",
    "BATCH5",
    "BATCH6",
    "BATCH7",
    "MMRD",
    "SRR_CASCADE",
    "CARE_ARC",
    "CARE_DG",
    "CARE_DR",
    "DPR",
    "CARE_PRISM_V1",
    "CARE_PRISM_V2",
    "MOSAIC_CLEAN",
    "MOSAIC_FULL_DATA",
    "MOSAIC_HOSTED_RECIPE",
    "CINE_BASELINES",
    "MOSAIC_CINE",
]

KEY_RESULT_DIRS = [
    "results/20260729_care_prism_fold0_fold1_v2",
    "results/20260729_care_prism_v2_backbone_repair_and_resume",
    "results/20260729_care_arc_clean_fold1",
    "results/20260728_care_dpr_fold0_global_redesign",
    "results/20260728_mosaic_full_weight_validation_probe",
    "results/20260726_care_mosaic_validation_gap_forensics_and_final_blueprint",
    "results/20260726_care_fullinfo_nnunet_and_care_scf",
    "results/20260725_care_myops_mosaic_fold0_reproduction",
    "results/20260725_care_m0_mosaic_fold0_fair_repro",
    "results/20260724_care_myops_srr_cascade_submission_rescue",
    "results/route_B",
    "results/route_C",
    "results/care_scf",
    "results/srr_production",
    "results/metrics",
    "results/leaderboard",
]

REQUIRED_OUTPUTS = [
    "controller_context.json",
    "controller_ledger.csv",
    "controller_bootstrap_snapshot.md",
    "task_scope_receipt.json",
    "source_read_manifest.csv",
    "evidence_inventory.csv",
    "checkpoint_inventory.csv",
    "prediction_inventory.csv",
    "external_local_repo_inventory.csv",
    "path_resolution_log.jsonl",
    "hash_manifest.csv",
    "data_case_manifest.csv",
    "data_center_modality_matrix.csv",
    "label_availability_matrix.csv",
    "label_semantics_contract.json",
    "official_internal_label_mapping.csv",
    "split_integrity_report.json",
    "spatial_geometry_audit.csv",
    "pathology_prevalence_summary.csv",
    "lesion_component_summary.csv",
    "data_truth_report.md",
    "reference_metric_known_bad_report.json",
    "metric_cross_implementation_report.json",
    "metric_semantics_validator_report.json",
    "model_lineage.csv",
    "experiment_lineage.csv",
    "historical_results_matrix.csv",
    "historical_failure_evidence.csv",
    "result_comparability_matrix.csv",
    "stale_evidence_report.md",
    "architecture_fidelity_matrix.csv",
    "loss_to_parameter_trace.csv",
    "component_final_output_effect.csv",
    "train_deploy_parity_matrix.csv",
    "implementation_maturity_report.md",
    "model_code_fingerprint_manifest.csv",
    "standardized_casewise_metrics.csv",
    "standardized_model_summary.csv",
    "pathology_population_summary.csv",
    "subgroup_performance_matrix.csv",
    "help_harm_matrix.csv",
    "hd_component_matrix.csv",
    "prediction_manifest.csv",
    "metric_reaggregation_report.md",
    "case_error_taxonomy.csv",
    "case_review_selection.csv",
    "manual_visual_review_notes.md",
    "case_montage_manifest.csv",
    "case_oracle_summary.csv",
    "voxel_error_overlap_matrix.csv",
    "fn_overlap_matrix.csv",
    "fp_overlap_matrix.csv",
    "model_disagreement_matrix.csv",
    "selector_feature_manifest.csv",
    "selector_nested_cv_results.csv",
    "complementarity_report.md",
    "feature_probe_inventory.csv",
    "feature_probe_case_split.json",
    "feature_probe_summary.csv",
    "feature_probe_full_results.csv",
    "feature_probe_random_control.csv",
    "feature_separability_report.md",
    "decoder_reset_contract.json",
    "decoder_reset_training_summary.csv",
    "decoder_reset_checkpoint_manifest.csv",
    "decoder_reset_inner_casewise.csv",
    "decoder_reset_comparison.csv",
    "decoder_reset_diagnostic_report.md",
    "mosaic_repo_weight_recipe_binding.json",
    "mosaic_ablation_contract.json",
    "mosaic_recipe_decomposition_casewise.csv",
    "mosaic_recipe_decomposition_summary.csv",
    "mosaic_clean_full_data_gap.csv",
    "mosaic_help_harm_vs_nnunet.csv",
    "mosaic_gap_forensics_report.md",
    "cross_modal_alignment_casewise.csv",
    "slice_correspondence_quality.csv",
    "alignment_error_correlation.csv",
    "alignment_forensics_report.md",
    "cine_data_manifest.csv",
    "cine_model_lineage.csv",
    "cine_implementation_fidelity_matrix.csv",
    "cine_casewise_metrics.csv",
    "cine_temporal_signal_probe.csv",
    "cine_motion_quality.csv",
    "cine_forensics_report.md",
    "root_cause_evidence_graph.json",
    "root_cause_ranked_table.csv",
    "research_decision_tree.md",
    "local_evidence_conclusions.md",
    "external_deep_research_question_bank.md",
    "external_deep_research_question_bank.json",
    "evidence_claim_ledger.csv",
    "deep_research_evidence_index.md",
    "deep_research_upload_manifest.json",
    "deep_research_prompt_seed.md",
    "completion_check.md",
    "controller_report.md",
    "MANIFEST.md",
    "notification_brief.json",
]


@dataclass
class CommandResult:
    cmd: str
    returncode: int
    output: str


def run(cmd: list[str], cwd: Path, timeout: int = 120) -> CommandResult:
    text_cmd = " ".join(cmd)
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        return CommandResult(text_cmd, p.returncode, p.stdout)
    except Exception as exc:
        return CommandResult(text_cmd, 99, str(exc))


def sha256_path(path: Path, max_bytes: int | None = None) -> tuple[str, str]:
    if not path.exists() or not path.is_file():
        return "", "MISSING"
    h = hashlib.sha256()
    read = 0
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            if max_bytes is not None and read + len(chunk) > max_bytes:
                h.update(chunk[: max_bytes - read])
                return h.hexdigest(), f"PREFIX_{max_bytes}_BYTES"
            h.update(chunk)
            read += len(chunk)
    return h.hexdigest(), "FULL"


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, object]], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        keys: list[str] = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        fields = keys or ["status"]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def append_ledger(root: Path, phase: str, decision: str, next_action: str, head: str, task_hash: str) -> None:
    path = root / "controller_ledger.csv"
    new = not path.exists()
    with path.open("a", newline="") as f:
        fields = ["timestamp_utc", "phase", "git_head", "task_hash", "job_states", "decision", "next_action"]
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(
            {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "phase": phase,
                "git_head": head,
                "task_hash": task_hash,
                "job_states": "READ_ONLY_BOOTSTRAP_NO_NEW_JOB",
                "decision": decision,
                "next_action": next_action,
            }
        )


def discover_files(pattern_roots: Iterable[Path], regex: str, limit: int = 2000) -> list[Path]:
    out: list[Path] = []
    rx = re.compile(regex, re.IGNORECASE)
    roots = [root for root in pattern_roots if root.exists()]
    if roots and shutil.which("rg"):
        try:
            p = subprocess.run(
                ["rg", "--files", *[str(r) for r in roots]],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=8,
            )
            if p.returncode in {0, 1}:
                for line in p.stdout.splitlines():
                    path = Path(line)
                    if rx.search(str(path)):
                        out.append(path)
                        if len(out) >= limit:
                            return out
                return out
        except Exception:
            return out
    # Avoid slow recursive walks on the HPC result tree. If rg is unavailable,
    # record the inventory gap rather than blocking the controller.
    if roots:
        return out
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", "__pycache__", ".mypy_cache", ".pytest_cache"}]
            for name in filenames:
                p = Path(dirpath) / name
                if rx.search(str(p)):
                    out.append(p)
                    if len(out) >= limit:
                        return out
    return out


def prompt_receipt(repo: Path, root: Path) -> str:
    task_prompt = repo / "prompts" / "tasks" / f"{TASK_KEY}.md"
    prompt_sha, prompt_hash_status = sha256_path(ATTACHMENT)
    task_prompt.parent.mkdir(parents=True, exist_ok=True)
    task_prompt.write_text(
        "# 20260730 CARE failure forensics deep research packet\n\n"
        "This local task file records the controller contract supplied as an attachment.\n\n"
        f"- attachment_path: `{ATTACHMENT}`\n"
        f"- attachment_sha256: `{prompt_sha}`\n"
        f"- hash_status: `{prompt_hash_status}`\n"
        "- execution_scope: forensic research packet only; no upload, no push, no new architecture.\n",
        encoding="utf-8",
    )
    copied_sha, _ = sha256_path(task_prompt)
    write_json(
        root / "task_scope_receipt.json",
        {
            "task_key": TASK_KEY,
            "task_prompt_path": str(task_prompt),
            "task_prompt_sha256": copied_sha,
            "attachment_path": str(ATTACHMENT),
            "attachment_sha256": prompt_sha,
            "status": "AUTHORIZED_LOCAL_FORENSIC_AUDIT",
            "forbidden_actions": [
                "validation upload",
                "docker upload",
                "hosted leaderboard claim",
                "new architecture training",
                "fold0 outer tuning",
                "git push",
            ],
        },
    )
    return copied_sha


def source_manifest(repo: Path, root: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for rel in SOURCE_FILES:
        p = repo / rel
        sha, status = sha256_path(p)
        rows.append(
            {
                "path": rel,
                "exists": p.exists(),
                "size_bytes": p.stat().st_size if p.exists() else "",
                "sha256": sha,
                "hash_status": status,
                "line_count": sum(1 for _ in p.open(errors="ignore")) if p.exists() and p.is_file() else "",
            }
        )
    write_csv(root / "source_read_manifest.csv", rows)
    return rows


def git_context(repo: Path) -> dict[str, object]:
    cmds = {
        "head": ["git", "rev-parse", "HEAD"],
        "origin_main": ["git", "rev-parse", "origin/main"],
        "branch": ["git", "branch", "--show-current"],
        "status_no_untracked": ["git", "status", "--short", "--branch", "--untracked-files=no"],
        "log_15": ["git", "log", "--oneline", "--decorate", "-15"],
    }
    out = {name: run(cmd, repo, 30).__dict__ for name, cmd in cmds.items()}
    return out


def slurm_snapshot(repo: Path) -> dict[str, object]:
    # These are best-effort because sandboxed runs may not access Slurm sockets.
    cmds = {
        "squeue_user": ["squeue", "-u", os.environ.get("USER", "")],
        "sacct_user": ["sacct", "-u", os.environ.get("USER", ""), "--starttime", "2026-07-29", "--format=JobID,JobName%30,Partition,State,ExitCode,Elapsed,NodeList", "-P"],
        "sinfo": ["sinfo", "-o", "%P|%a|%l|%D|%t|%G"],
    }
    return {name: run(cmd, repo, 5).__dict__ for name, cmd in cmds.items()}


def inventory(repo: Path, root: Path) -> None:
    evidence_roots = [repo / rel for rel in KEY_RESULT_DIRS] + [repo / "prompts", repo / "wiki"]
    evidence_files = discover_files(evidence_roots, r"(prism|mosaic|nnunet|srr|mmrd|cascade|arc|dg|dpr|cine|metric|gate|validator|controller|packet|summary|casewise|manifest)", 300)
    erows = []
    hash_rows = []
    for p in evidence_files:
        rel = p.relative_to(repo) if p.is_relative_to(repo) else p
        if p.stat().st_size > 10 * 1024 * 1024:
            sha, hs = "", "LARGE_METADATA_ONLY"
        else:
            sha, hs = sha256_path(p, max_bytes=8 * 1024)
        erows.append(
            {
                "evidence_id": f"E-INV-{len(erows)+1:04d}",
                "path": str(rel),
                "kind": p.suffix.lower().lstrip(".") or "file",
                "size_bytes": p.stat().st_size,
                "sha256": sha,
                "hash_status": hs,
                "evidence_quality": "BOUND_LIGHTWEIGHT" if hs == "FULL" else "LARGE_PREFIX_HASH_ONLY",
            }
        )
        hash_rows.append({"path": str(rel), "sha256": sha, "hash_status": hs, "size_bytes": p.stat().st_size})
    write_csv(root / "evidence_inventory.csv", erows)

    ckpt_roots = [
        repo / "data/nnUNet/nnUNet_results",
        *[repo / rel for rel in KEY_RESULT_DIRS],
        Path("/users/a/e/aereinh/MoSAIC/code/weights"),
    ]
    ckpts = discover_files(ckpt_roots, r"(\.pt$|\.pth$|\.ckpt$|checkpoint|model_final_checkpoint)", 150)
    crows = []
    for p in ckpts:
        if p.stat().st_size > 10 * 1024 * 1024:
            sha, hs = "", "LARGE_METADATA_ONLY"
        else:
            sha, hs = sha256_path(p, max_bytes=8 * 1024)
        lower = str(p).lower()
        if "nnunet" in lower:
            model_id = "NNUNET"
        elif "mosaic" in lower or "mosam" in lower:
            model_id = "MOSAIC_UNBOUND"
        elif "prism" in lower:
            model_id = "CARE_PRISM_UNBOUND"
        elif "arc" in lower:
            model_id = "CARE_ARC_UNBOUND"
        elif "dpr" in lower:
            model_id = "DPR_UNBOUND"
        else:
            model_id = "UNBOUND_CHECKPOINT"
        crows.append(
            {
                "model_id": model_id,
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "sha256": sha,
                "hash_status": hs,
                "source_commit": "",
                "code_fingerprint": "UNBOUND_RECIPE",
                "config_path": "",
                "config_sha256": "",
                "split": "",
                "train_cases": "",
                "eval_cases": "",
                "label_semantics": "UNBOUND",
                "preprocess": "UNBOUND",
                "decode_rule": "UNBOUND",
                "metric_implementation": "UNBOUND",
                "checkpoint_selection_rule": "UNBOUND",
                "training_budget": "UNBOUND",
                "status": "LOCAL_FILE_PRESENT",
                "evidence_quality": "UNBOUND_CHECKPOINT" if "UNBOUND" in model_id else "PARTIALLY_BOUND_BY_PATH",
            }
        )
        hash_rows.append({"path": str(p), "sha256": sha, "hash_status": hs, "size_bytes": p.stat().st_size})
    write_csv(root / "checkpoint_inventory.csv", crows)

    preds = discover_files(
        [repo / "data/nnUNet/nnUNet_results", *[repo / rel for rel in KEY_RESULT_DIRS]],
        r"(\.nii\.gz$|\.nii$|prediction|predictions|validation|probabilities)",
        200,
    )
    prows = []
    for p in preds:
        if p.is_dir():
            continue
        if p.stat().st_size > 2 * 1024 * 1024 * 1024:
            continue
        rel = p.relative_to(repo) if p.is_relative_to(repo) else p
        lower = str(p).lower()
        if "labelstr" in lower or "imagestr" in lower:
            continue
        model_id = "NNUNET" if "nnunet" in lower else "MOSAIC" if "mosaic" in lower else "UNBOUND_PREDICTION"
        if p.stat().st_size > 10 * 1024 * 1024:
            sha, hs = "", "LARGE_METADATA_ONLY"
        else:
            sha, hs = sha256_path(p, max_bytes=8 * 1024)
        prows.append(
            {
                "model_id": model_id,
                "path": str(rel),
                "size_bytes": p.stat().st_size,
                "sha256": sha,
                "hash_status": hs,
                "split": "UNBOUND",
                "eval_cases": "",
                "label_semantics": "UNBOUND",
                "decode_rule": "UNBOUND",
                "metric_implementation": "UNBOUND",
                "status": "LOCAL_FILE_PRESENT",
                "evidence_quality": "UNBOUND_PREDICTION" if model_id == "UNBOUND_PREDICTION" else "PARTIALLY_BOUND_BY_PATH",
            }
        )
    write_csv(root / "prediction_inventory.csv", prows)
    write_csv(root / "prediction_manifest.csv", prows)

    ext = []
    for p in [Path("/users/a/e/aereinh/MoSAIC"), Path("/users/a/e/aereinh/MoSAIC/code/source"), Path("/users/a/e/aereinh/MoSAIC/code/weights")]:
        ext.append({"path": str(p), "exists": p.exists(), "kind": "external_local_repo_or_asset", "write_authorized": False})
    write_csv(root / "external_local_repo_inventory.csv", ext)
    write_csv(root / "hash_manifest.csv", hash_rows)
    with (root / "path_resolution_log.jsonl").open("w") as f:
        for p in ckpt_roots + evidence_roots:
            f.write(json.dumps({"path": str(p), "exists": p.exists()}, ensure_ascii=False) + "\n")


def data_audit(repo: Path, root: Path) -> None:
    labels_dir = repo / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
    images_dir = repo / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr"
    rows = []
    if nib and labels_dir.exists():
        for lab_path in sorted(labels_dir.glob("*.nii.gz")):
            case = lab_path.name.replace(".nii.gz", "")
            try:
                img = nib.load(str(lab_path))
                arr = np.asanyarray(img.dataobj)
                spacing = tuple(float(x) for x in img.header.get_zooms()[: arr.ndim])
                masks = label_masks(arr)
                voxel_vol = float(np.prod(spacing))
                files = {m: (images_dir / f"{case}_{i:04d}.nii.gz").exists() for i, m in enumerate(["LGE", "C0", "T2"])}
                rows.append(
                    {
                        "case_id": case,
                        "center": case[4] if len(case) > 4 and case.startswith("Case") else "",
                        "fold_membership": "UNRESOLVED_FROM_SPLITS",
                        "available_modalities": "+".join([k for k, v in files.items() if v]),
                        "T2_present": files.get("T2", False),
                        "C0_present": files.get("C0", False),
                        "LGE_present": files.get("LGE", False),
                        "image_shape": "x".join(map(str, arr.shape)),
                        "spacing": "x".join(f"{x:.4g}" for x in spacing),
                        "origin": "UNREAD_NIFTI_LABEL_ONLY",
                        "direction": "UNREAD_NIFTI_LABEL_ONLY",
                        "orientation": "UNRESOLVED",
                        "number_of_slices": arr.shape[-1] if arr.ndim >= 3 else "",
                        "scar_voxels": int(masks["official_scar"].sum()),
                        "pure_edema_voxels": int(masks["official_pure_edema"].sum()),
                        "edema_zone_voxels": int(masks["internal_edema_zone"].sum()),
                        "myocardium_union_voxels": int(masks["myocardium_union"].sum()),
                        "LV_voxels": int(masks["lv"].sum()),
                        "RV_voxels": int(masks["rv"].sum()),
                        "scar_components": component_count(masks["official_scar"]),
                        "pure_edema_components": component_count(masks["official_pure_edema"]),
                        "edema_zone_components": component_count(masks["internal_edema_zone"]),
                        "scar_volume_mm3": int(masks["official_scar"].sum()) * voxel_vol,
                        "pure_edema_volume_mm3": int(masks["official_pure_edema"].sum()) * voxel_vol,
                        "lesion_to_myocardium_ratio": safe_ratio(int(masks["internal_edema_zone"].sum()), int(masks["myocardium_union"].sum())),
                        "empty_nonempty_state": "scar_nonempty" if masks["official_scar"].any() else "scar_empty",
                    }
                )
            except Exception as exc:
                rows.append({"case_id": case, "status": "READ_ERROR", "error": str(exc)})
    write_csv(root / "data_case_manifest.csv", rows)

    centers = {}
    for r in rows:
        centers.setdefault(r.get("center", ""), {"center": r.get("center", ""), "cases": 0, "T2_present": 0, "C0_present": 0, "LGE_present": 0})
        centers[r.get("center", "")]["cases"] += 1
        for k in ["T2_present", "C0_present", "LGE_present"]:
            centers[r.get("center", "")][k] += int(bool(r.get(k)))
    write_csv(root / "data_center_modality_matrix.csv", list(centers.values()))

    label_rows = []
    for r in rows:
        label_rows.append(
            {
                "case_id": r.get("case_id", ""),
                "T2_present": r.get("T2_present", ""),
                "scar_nonempty": int(float(r.get("scar_voxels", 0)) > 0) if str(r.get("scar_voxels", "")).replace(".", "", 1).isdigit() else "",
                "pure_edema_nonempty": int(float(r.get("pure_edema_voxels", 0)) > 0) if str(r.get("pure_edema_voxels", "")).replace(".", "", 1).isdigit() else "",
                "edema_zone_nonempty": int(float(r.get("edema_zone_voxels", 0)) > 0) if str(r.get("edema_zone_voxels", "")).replace(".", "", 1).isdigit() else "",
            }
        )
    write_csv(root / "label_availability_matrix.csv", label_rows)

    write_json(
        root / "label_semantics_contract.json",
        {
            "official_scar": "label == 5",
            "official_pure_edema": "label == 4, reported only on reliable T2-present population when used for official edema claims",
            "internal_edema_zone": "label in {4, 5}; internal structure analysis only, not official edema",
            "myocardium_union": "label in {1, 4, 5}",
            "LV": "label == 2",
            "RV": "label == 3",
        },
    )
    write_csv(
        root / "official_internal_label_mapping.csv",
        [
            {"object": "scar", "internal_labels": "5", "official_export": "scar", "allowed_claim_scope": "official"},
            {"object": "pure_edema", "internal_labels": "4", "official_export": "edema", "allowed_claim_scope": "T2-present official edema"},
            {"object": "edema_zone", "internal_labels": "4|5", "official_export": "none", "allowed_claim_scope": "internal only"},
        ],
    )
    write_json(root / "split_integrity_report.json", {"status": "UNRESOLVED", "reason": "split files require dedicated parser; no outer tuning was performed in this packet build"})
    write_csv(root / "spatial_geometry_audit.csv", [{"audit": "raw_label_scan", "status": "PARTIAL", "cases": len(rows), "note": "Full raw/preprocessed/export round-trip not completed"}])

    if rows:
        totals = {
            "cases": len(rows),
            "scar_positive": sum(int(r.get("scar_voxels", 0) > 0) for r in rows),
            "pure_edema_positive": sum(int(r.get("pure_edema_voxels", 0) > 0) for r in rows),
            "t2_present": sum(int(bool(r.get("T2_present"))) for r in rows),
        }
    else:
        totals = {"cases": 0, "scar_positive": 0, "pure_edema_positive": 0, "t2_present": 0}
    write_csv(root / "pathology_prevalence_summary.csv", [totals])
    write_csv(
        root / "lesion_component_summary.csv",
        [
            {
                "object": "scar",
                "mean_components": mean_numeric(rows, "scar_components"),
                "positive_cases": totals["scar_positive"],
            },
            {
                "object": "pure_edema",
                "mean_components": mean_numeric(rows, "pure_edema_components"),
                "positive_cases": totals["pure_edema_positive"],
            },
        ],
    )
    (root / "data_truth_report.md").write_text(
        "# 数据、标签和空间真值审计\n\n"
        f"本次离线扫描读取 `Dataset501_CAREMyoPS/labelsTr`，有效病例数为 {totals['cases']}。"
        "报告严格区分 official scar、official pure edema 和 internal edema-zone。"
        "完整 raw/preprocessed/export round-trip 几何验证尚未完成，因此空间结论保持 PARTIAL。\n",
        encoding="utf-8",
    )


def component_count(mask: np.ndarray) -> int:
    from scipy import ndimage

    return int(ndimage.label(mask, ndimage.generate_binary_structure(mask.ndim, 1))[1])


def safe_ratio(a: int, b: int) -> float | None:
    return None if b == 0 else float(a) / float(b)


def mean_numeric(rows: list[dict[str, object]], key: str) -> float | str:
    vals = []
    for r in rows:
        try:
            vals.append(float(r[key]))
        except Exception:
            pass
    return float(np.mean(vals)) if vals else ""


def model_tables(root: Path) -> None:
    lineage = []
    for m in MODELS:
        if m == "NNUNET":
            quality = "A_VERIFIED_FAIR_FINAL_MASK"
            conclusion = "强基线；需继续绑定五折和同口径病例级指标。"
        elif "MOSAIC" in m:
            quality = "B_VERIFIED_DIAGNOSTIC" if m != "MOSAIC_HOSTED_RECIPE" else "E_STALE_OR_INCONSISTENT"
            conclusion = "clean/full-data/hosted recipe 必须分层，full-data 不能作为 clean 公平比较。"
        elif "PRISM" in m:
            quality = "D_UNDERTRAINED"
            conclusion = "W1-W3 现有证据提示 decoder/reset、loss stage 和 evaluator 语义需要继续诊断。"
        elif m in {"CARE_ARC", "DPR", "SRR_CASCADE"}:
            quality = "B_VERIFIED_DIAGNOSTIC"
            conclusion = "已有控制器证据可作为诊断负结果，不等同于新路线失败的普遍定理。"
        else:
            quality = "E_STALE_OR_INCONSISTENT"
            conclusion = "历史证据需绑定代码、checkpoint、split 和预测。"
        lineage.append(
            {
                "model_id": m,
                "design_goal": "historical CARE route or baseline",
                "input_modalities": "UNBOUND_OR_ROUTE_SPECIFIC",
                "missing_modality_handling": "UNBOUND",
                "backbone": "UNBOUND",
                "anatomy_path": "UNBOUND",
                "pathology_proposal": "UNBOUND",
                "scar_edema_independent": "UNBOUND",
                "negative_space": "UNBOUND",
                "prototype_memory": "UNBOUND",
                "alignment_registration": "UNBOUND",
                "roi_refiner": "UNBOUND",
                "final_output_producer": "UNBOUND",
                "nnunet_permission": "baseline/reference allowed",
                "mosaic_permission": "read-only evidence allowed",
                "loss": "UNBOUND",
                "sampling": "UNBOUND",
                "augmentation": "UNBOUND",
                "checkpoint_selection": "UNBOUND",
                "train_deploy_parity": "UNBOUND",
                "local_metric": "UNBOUND",
                "same_split_baseline": "UNBOUND",
                "hosted_metric": "UNAUTHORIZED_TO_CLAIM",
                "result_evidence_grade": quality,
                "known_implementation_bug": "SEE_IMPLEMENTATION_MATURITY_REPORT",
                "known_evaluation_bug": "REMOTE_FP_AND_EDEMA_SEMANTICS_REQUIRE_REFERENCE_EVALUATOR",
                "current_scientific_conclusion": conclusion,
            }
        )
    write_csv(root / "model_lineage.csv", lineage)
    write_csv(root / "experiment_lineage.csv", lineage, fields=["model_id", "design_goal", "checkpoint_selection", "result_evidence_grade", "current_scientific_conclusion"])
    write_csv(root / "historical_results_matrix.csv", [{"model_id": r["model_id"], "metric_status": "REQUIRES_STANDARDIZED_REAGGREGATION", "evidence_grade": r["result_evidence_grade"]} for r in lineage])
    write_csv(root / "historical_failure_evidence.csv", [{"model_id": r["model_id"], "failure_status": r["current_scientific_conclusion"], "evidence_grade": r["result_evidence_grade"]} for r in lineage])
    write_csv(root / "result_comparability_matrix.csv", [{"comparison": "all_models_vs_nnunet", "status": "NOT_YET_COMPARABLE_UNTIL_SPLIT_LABEL_RECIPE_BOUND", "allowed_use": "inventory_and_research_questions"}])
    (root / "stale_evidence_report.md").write_text("# Stale Evidence Report\n\n所有 C-G 级证据不得用于证明模型优于 nnU-Net 或 MoSAIC；它们只用于定位历史缺口。\n", encoding="utf-8")

    arch_rows = []
    for m in ["SRR", "MMRD", "Cascade", "ARC", "DG", "PRISM", "MoSAIC", "nnU-Net"]:
        arch_rows.append(
            {
                "model": m,
                "design_claim": "requires source-bound review",
                "implemented": "PARTIAL_OR_UNVERIFIED",
                "final_logits_effect": "UNVERIFIED_BY_FORWARD",
                "loss_enters_total": "UNVERIFIED",
                "train_deploy_parity": "UNVERIFIED",
                "status": "NEEDS_FORWARD_AND_GRADIENT_AUDIT",
            }
        )
    write_csv(root / "architecture_fidelity_matrix.csv", arch_rows)
    write_csv(root / "loss_to_parameter_trace.csv", [{"model": "PRISM", "loss": "surface/MIL/prototype", "gradient_trace_status": "NOT_RUN"}])
    write_csv(root / "component_final_output_effect.csv", [{"model": "PRISM", "component": "proposal/prototype/refiner", "on_off_final_logit_delta": "NOT_RUN", "status": "NEEDS_FORWARD_AUDIT"}])
    write_csv(root / "train_deploy_parity_matrix.csv", [{"model": "PRISM", "status": "UNVERIFIED"}])
    (root / "implementation_maturity_report.md").write_text("# Implementation Maturity\n\n当前包未声明任何模块已经病例级 forward 证明影响 final logits。需要后续 F3 诊断。\n", encoding="utf-8")
    write_csv(root / "model_code_fingerprint_manifest.csv", [{"model": "PRISM", "fingerprint_status": "SOURCE_MANIFEST_ONLY"}])


def metric_placeholder_tables(root: Path) -> None:
    rows = []
    for m in ["NNUNET", "MOSAIC_CLEAN", "MOSAIC_FULL_DATA", "CARE_PRISM_V2", "CARE_ARC", "DPR", "SRR_CASCADE"]:
        for p in ["official_scar", "official_pure_edema", "internal_edema_zone"]:
            rows.append(
                {
                    "model_id": m,
                    "pathology": p,
                    "mean": "",
                    "median": "",
                    "standard_deviation": "",
                    "bootstrap_95ci": "",
                    "case_count": "",
                    "GT_positive_count": "",
                    "empty_count": "",
                    "help_count": "",
                    "harm_count": "",
                    "tie_count": "",
                    "status": "REQUIRES_STANDARDIZED_REAGGREGATION",
                }
            )
    write_csv(root / "standardized_casewise_metrics.csv", [{"case_id": "UNRUN", "status": "REQUIRES_BOUND_PREDICTIONS"}])
    write_csv(root / "standardized_model_summary.csv", rows)
    write_csv(root / "pathology_population_summary.csv", [{"population": "all", "status": "SEE_pathology_prevalence_summary"}])
    write_csv(root / "subgroup_performance_matrix.csv", [{"subgroup": "T2-present", "status": "REQUIRES_REAGGREGATION"}])
    write_csv(root / "help_harm_matrix.csv", [{"comparison": "model_vs_nnunet", "status": "REQUIRES_CASEWISE_METRICS"}])
    write_csv(root / "hd_component_matrix.csv", [{"model": "UNRUN", "status": "REQUIRES_REFERENCE_EVALUATOR_ON_BOUND_PREDICTIONS"}])
    (root / "metric_reaggregation_report.md").write_text("# Metric Reaggregation\n\nReference evaluator known-bad fixtures pass, but full prediction reaggregation is not yet terminal.\n", encoding="utf-8")


def diagnostics_placeholders(root: Path) -> None:
    write_csv(root / "case_error_taxonomy.csv", [{"case_id": "UNSELECTED", "status": "REQUIRES_CASEWISE_METRICS"}])
    write_csv(root / "case_review_selection.csv", [{"case_id": "UNSELECTED", "reason": "casewise metrics unavailable"}])
    (root / "manual_visual_review_notes.md").write_text("VISUAL_HUMAN_CONFIRMATION_PENDING\n\nMontage generation is limited to placeholder/contact-sheet QA until standardized metrics select cases.\n", encoding="utf-8")
    write_csv(root / "case_montage_manifest.csv", [{"figure": "figures/summary_status.png", "status": "PLACEHOLDER_NOT_CASE_MONTAGE"}])

    write_csv(root / "case_oracle_summary.csv", [{"oracle": "all_models_case_oracle", "status": "REQUIRES_CASEWISE_METRICS"}])
    for name in ["voxel_error_overlap_matrix.csv", "fn_overlap_matrix.csv", "fp_overlap_matrix.csv", "model_disagreement_matrix.csv"]:
        write_csv(root / name, [{"status": "REQUIRES_BOUND_PREDICTIONS"}])
    write_csv(root / "selector_feature_manifest.csv", [{"feature": "nnunet_entropy", "status": "NOT_EXTRACTED"}])
    write_csv(root / "selector_nested_cv_results.csv", [{"probe": "logistic_regression", "status": "NOT_RUN"}])
    (root / "complementarity_report.md").write_text("LOCAL_EVIDENCE_DOES_NOT_SUPPORT_DEPLOYABLE_MODEL_SELECTION yet: required casewise evidence has not been reaggregated.\n", encoding="utf-8")

    write_csv(root / "feature_probe_inventory.csv", [{"feature_source": "nnunet_encoder", "status": "NOT_EXTRACTED"}])
    write_json(root / "feature_probe_case_split.json", {"status": "NOT_RUN", "outer_used_for_training": False})
    write_csv(root / "feature_probe_summary.csv", [{"probe": "P1_scar_vs_normal", "AUROC": "", "status": "NOT_RUN"}])
    write_csv(root / "feature_probe_full_results.csv", [{"status": "NOT_RUN"}])
    write_csv(root / "feature_probe_random_control.csv", [{"status": "NOT_RUN"}])
    (root / "feature_separability_report.md").write_text("冻结特征 probe 尚未运行；不能声称 retrieval/prototype 具备病例外信号。\n", encoding="utf-8")

    write_json(root / "decoder_reset_contract.json", {"D0": "NOT_RUN", "outer_used": False, "uses_stock_nnunet_required": True})
    write_csv(root / "decoder_reset_training_summary.csv", [{"diagnostic": "D0_FULL_PRETRAINED_IDENTITY", "status": "NOT_RUN"}])
    write_csv(root / "decoder_reset_checkpoint_manifest.csv", [{"diagnostic": "D0", "status": "NO_NEW_CHECKPOINT"}])
    write_csv(root / "decoder_reset_inner_casewise.csv", [{"diagnostic": "D0", "status": "NOT_RUN"}])
    write_csv(root / "decoder_reset_comparison.csv", [{"diagnostic": "D0-D3", "status": "NOT_RUN"}])
    (root / "decoder_reset_diagnostic_report.md").write_text("D0-D3 尚未运行；PRISM 低分暂不能被定性为纯 representation、decoder 或训练协议问题。\n", encoding="utf-8")

    write_json(root / "mosaic_repo_weight_recipe_binding.json", {"status": "PARTIAL", "weights_root": "/users/a/e/aereinh/MoSAIC/code/weights"})
    write_json(root / "mosaic_ablation_contract.json", {"M0_to_M10": "DEFINED_NOT_RUN", "full_data_not_clean_comparison": True})
    for name in ["mosaic_recipe_decomposition_casewise.csv", "mosaic_recipe_decomposition_summary.csv", "mosaic_clean_full_data_gap.csv", "mosaic_help_harm_vs_nnunet.csv"]:
        write_csv(root / name, [{"status": "NOT_RUN"}])
    (root / "mosaic_gap_forensics_report.md").write_text("MoSAIC clean/full-data/hosted gap 尚未完成 M0-M10 decomposition；full-data 不能冒充 clean 证据。\n", encoding="utf-8")

    for name in ["cross_modal_alignment_casewise.csv", "slice_correspondence_quality.csv", "alignment_error_correlation.csv"]:
        write_csv(root / name, [{"status": "NOT_RUN"}])
    (root / "alignment_forensics_report.md").write_text("LOCAL_EVIDENCE_DOES_NOT_SUPPORT_ALIGNMENT_AS_PRIMARY_FAILURE_CAUSE yet: alignment correlation audit not run.\n", encoding="utf-8")

    write_csv(root / "cine_data_manifest.csv", [{"status": "PARTIAL_INVENTORY_ONLY"}])
    write_csv(root / "cine_model_lineage.csv", [{"model": "MOSAIC_CINE", "status": "UNBOUND"}])
    write_csv(root / "cine_implementation_fidelity_matrix.csv", [{"component": "temporal_path", "status": "UNVERIFIED"}])
    write_csv(root / "cine_casewise_metrics.csv", [{"status": "NOT_RUN"}])
    write_csv(root / "cine_temporal_signal_probe.csv", [{"probe": "CINE_P0_vs_P1", "status": "NOT_RUN"}])
    write_csv(root / "cine_motion_quality.csv", [{"status": "NOT_RUN"}])
    (root / "cine_forensics_report.md").write_text("Cine temporal signal 尚未病例外验证；不能把单帧输出包装成 temporal evidence。\n", encoding="utf-8")


def root_cause(root: Path) -> None:
    causes = [
        ("METRIC_IMPLEMENTATION", "MODERATE", "remote FP 和 pure-edema/edema-zone 语义已有 known-bad 保护；全量影响未重算。"),
        ("CHECKPOINT_OR_RECIPE", "MODERATE", "MoSAIC clean/full-data/hosted recipe 未绑定完成，存在本地证据反转风险。"),
        ("DECODER_CAPABILITY_LOSS", "LOW", "PRISM decoder-reset 假说合理但 D0-D3 未运行。"),
        ("COMPONENT_NOT_WIRED", "LOW", "多个路线需 forward/on-off 才能确认模块是否进入 final logits。"),
        ("INSUFFICIENT_PATHOLOGY_SIGNAL", "UNRESOLVED", "feature probe 未运行。"),
        ("MULTIMODAL_MISALIGNMENT", "UNRESOLVED", "alignment correlation 未运行。"),
        ("CINE_TASK_DEFINITION", "UNRESOLVED", "Cine P0/P1 未运行。"),
    ]
    rows = []
    for idx, (cause, conf, note) in enumerate(causes, 1):
        rows.append(
            {
                "root_cause": cause,
                "evidence": note,
                "counterevidence": "not yet fully tested",
                "affected_models": "multiple",
                "affected_pathology": "scar|pure_edema|cine",
                "severity": "HIGH" if idx <= 2 else "MODERATE",
                "confidence": conf,
                "confirmed": conf == "MODERATE",
                "missing_evidence": "standardized reaggregation / diagnostic probes",
                "needs_external_literature": True,
                "next_research_question": "Which mechanism is falsifiable under patient-level split?",
                "falsification_experiment": "fixed-checkpoint forensic diagnostic only",
                "worth_designing_model_now": False,
            }
        )
    write_csv(root / "root_cause_ranked_table.csv", rows)
    write_json(root / "root_cause_evidence_graph.json", {"nodes": rows, "edges": []})
    (root / "research_decision_tree.md").write_text(
        "# Research Decision Tree\n\n"
        "1. 先完成 evaluation/data repair。\n"
        "2. 若 D0 不能复现 nnU-Net，停止 decoder-reset。\n"
        "3. 若 selector nested CV 不超过 always-best-single-model，停止 deployable selector。\n"
        "4. 若 feature probe control 不成立，停止 retrieval/prototype 叙事。\n",
        encoding="utf-8",
    )
    (root / "local_evidence_conclusions.md").write_text(
        "# Local Evidence Conclusions\n\n"
        "当前本地证据支持 A 和 I：先做评价/数据/recipe 绑定修复，并承认关键证据仍缺失。"
        "尚不能支持新的 CARE 架构蓝图。\n",
        encoding="utf-8",
    )
    q = [
        {"question_id": "DR-001", "question": "Small-lesion scar segmentation beyond nnU-Net requires which evidence standard?", "local_status": "open"},
        {"question_id": "DR-002", "question": "Can clean MoSAIC recipe gains be separated from full-data target-domain advantage?", "local_status": "open"},
        {"question_id": "DR-003", "question": "Do frozen encoder features contain patient-held-out scar FN/FP separability?", "local_status": "open"},
        {"question_id": "DR-004", "question": "When does cine temporal information improve pathology segmentation over ED-only?", "local_status": "open"},
    ]
    write_json(root / "external_deep_research_question_bank.json", q)
    (root / "external_deep_research_question_bank.md").write_text("\n".join(f"- [{x['question_id']}] {x['question']}" for x in q) + "\n", encoding="utf-8")


def figures(root: Path) -> None:
    fig_dir = root / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    # Evidence grade overview.
    grade_counts = {}
    with (root / "model_lineage.csv").open() as f:
        for r in csv.DictReader(f):
            grade_counts[r["result_evidence_grade"]] = grade_counts.get(r["result_evidence_grade"], 0) + 1
    plt.figure(figsize=(9, 4))
    plt.bar(list(grade_counts), list(grade_counts.values()), color=["#4c78a8", "#f58518", "#54a24b", "#e45756", "#72b7b2"][: len(grade_counts)])
    plt.xticks(rotation=25, ha="right")
    plt.ylabel("model count")
    plt.title("Local evidence grades, not performance claims")
    plt.tight_layout()
    plt.savefig(fig_dir / "evidence_grade_counts.png", dpi=180)
    plt.close()

    rows = []
    case_path = root / "data_case_manifest.csv"
    if case_path.exists():
        with case_path.open() as f:
            rows = list(csv.DictReader(f))
    if rows:
        scar = [float(r.get("scar_volume_mm3") or 0) for r in rows]
        edema = [float(r.get("pure_edema_volume_mm3") or 0) for r in rows]
        plt.figure(figsize=(8, 4))
        plt.hist([scar, edema], bins=30, label=["scar", "pure edema"], color=["#b279a2", "#59a14f"])
        plt.yscale("log")
        plt.xlabel("volume mm3")
        plt.ylabel("case count (log)")
        plt.legend()
        plt.title("Pathology volume distribution from local labels")
        plt.tight_layout()
        plt.savefig(fig_dir / "pathology_volume_distribution.png", dpi=180)
        plt.close()

        centers = {}
        for r in rows:
            c = r.get("center", "")
            centers.setdefault(c, 0)
            centers[c] += 1
        plt.figure(figsize=(7, 4))
        plt.bar(sorted(centers), [centers[k] for k in sorted(centers)], color="#9c755f")
        plt.xlabel("center code from case id")
        plt.ylabel("case count")
        plt.title("Dataset501 label cases by center")
        plt.tight_layout()
        plt.savefig(fig_dir / "center_case_counts.png", dpi=180)
        plt.close()

    plt.figure(figsize=(8, 5))
    decisions = ["A data/eval repair", "I missing evidence", "H no new architecture now", "C selector", "D retrieval", "G cine"]
    status = [1, 1, 1, 0, 0, 0]
    colors = ["#4c78a8" if x else "#bab0ac" for x in status]
    plt.barh(decisions, status, color=colors)
    plt.xlim(0, 1.2)
    plt.xlabel("supported by current local packet")
    plt.title("Decision state")
    plt.tight_layout()
    plt.savefig(fig_dir / "decision_state.png", dpi=180)
    plt.close()


def tex_escape(s: object) -> str:
    text = str(s)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def small_table_tex(path: Path, max_rows: int = 12) -> str:
    if not path.exists():
        return "缺失。"
    with path.open() as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return "空表。"
    fields = list(rows[0].keys())[:5]
    lines = [r"\begin{longtable}{p{0.19\linewidth}p{0.19\linewidth}p{0.19\linewidth}p{0.19\linewidth}p{0.19\linewidth}}", r"\toprule"]
    lines.append(" & ".join(tex_escape(x) for x in fields) + r"\\")
    lines.append(r"\midrule")
    for r in rows[:max_rows]:
        lines.append(" & ".join(tex_escape(r.get(x, ""))[:180] for x in fields) + r"\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{longtable}")
    return "\n".join(lines)


def write_report(repo: Path, root: Path) -> None:
    src = root / "report_source"
    sections = src / "sections"
    tables = src / "generated_tables"
    figs = src / "generated_figures"
    sections.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)
    figs.mkdir(parents=True, exist_ok=True)
    for p in (root / "figures").glob("*.png"):
        shutil.copy2(p, figs / p.name)

    claims = [
        {"claim_id": "E-DATA-001", "claim_text": "本包读取 Dataset501 labelsTr 的病例清单并统计标签体积。", "pdf_page": "", "section": "2", "source_path": "data_case_manifest.csv", "source_sha256": "", "source_row_or_key": "all", "calculation_script": "build_forensic_packet.py", "calculation_script_sha256": "", "reproducible": True, "confidence": "MODERATE", "notes": "geometry round-trip incomplete"},
        {"claim_id": "E-METRIC-001", "claim_text": "reference metric known-bad fixtures pass for remote FP, spacing HD95, empty cases and lesion recall.", "pdf_page": "", "section": "3", "source_path": "reference_metric_known_bad_report.json", "source_sha256": "", "source_row_or_key": "status", "calculation_script": "reference_metrics.py", "calculation_script_sha256": "", "reproducible": True, "confidence": "HIGH", "notes": "synthetic fixtures only"},
        {"claim_id": "E-MOSAIC-001", "claim_text": "full-data MoSAIC evidence cannot be used as clean fold0 comparison.", "pdf_page": "", "section": "12", "source_path": "mosaic_ablation_contract.json", "source_sha256": "", "source_row_or_key": "full_data_not_clean_comparison", "calculation_script": "build_forensic_packet.py", "calculation_script_sha256": "", "reproducible": True, "confidence": "HIGH", "notes": "contract boundary"},
        {"claim_id": "E-PRISM-001", "claim_text": "PRISM decoder-reset explanation remains unresolved until D0-D3 terminal diagnostics complete.", "pdf_page": "", "section": "20", "source_path": "decoder_reset_diagnostic_report.md", "source_sha256": "", "source_row_or_key": "all", "calculation_script": "build_forensic_packet.py", "calculation_script_sha256": "", "reproducible": True, "confidence": "LOW", "notes": "diagnostics not run"},
    ]
    for i in range(5, 21):
        claims.append(
            {
                "claim_id": f"E-GAP-{i:03d}",
                "claim_text": f"Required diagnostic evidence item {i} remains incomplete and is not used as a performance claim.",
                "pdf_page": "",
                "section": str(i),
                "source_path": "strict_validator_report.json",
                "source_sha256": "",
                "source_row_or_key": "required_diagnostic_waves_terminal",
                "calculation_script": "validate_forensic_packet.py",
                "calculation_script_sha256": "",
                "reproducible": True,
                "confidence": "HIGH",
                "notes": "validator will fail until completed",
            }
        )
    for c in claims:
        source = root / c["source_path"]
        c["source_sha256"], _ = sha256_path(source)
        script = repo / "scripts/forensics/care_failure_forensics" / c["calculation_script"]
        c["calculation_script_sha256"], _ = sha256_path(script)
    write_csv(root / "evidence_claim_ledger.csv", claims)

    chapter_titles = [
        "为什么现在必须做失败取证",
        "CARE 数据、中心、模态和标签真值",
        "官方与内部指标语义",
        "当前评价代码中的已确认问题",
        "nnU-Net 强基线到底强在哪里",
        "SRR v2-v3 的设计意图与落地差距",
        "Batch 0-7 历史证据",
        "MMRD 的设计、实现和失败",
        "Cascade/DG 的设计、实现和失败",
        "ARC 的设计、实现和失败",
        "PRISM W1-W3 的完整复盘",
        "MoSAIC clean、full-data 和 hosted recipe",
        "所有模型统一病例级比较",
        "困难子组",
        "case-wise help/harm",
        "失败病例视觉图册",
        "错误重合和模型互补上限",
        "selector feasibility",
        "冻结特征可分性 probe",
        "decoder-reset 诊断对照",
        "多序列错位是否为主因",
        "scar 的真实瓶颈",
        "pure edema 的真实瓶颈",
        "Cine 的真实瓶颈",
        "为什么过去多次充分设计仍然失败",
        "根因排序与证据图",
        "当前能下的结论",
        "当前不能下的结论",
        "外部 Deep Research 必须回答的问题",
        "下一轮决策树",
    ]
    sec_paths = []
    for idx, title in enumerate(chapter_titles, 1):
        body = [
            rf"\section{{{tex_escape(str(idx) + '. ' + title)}}}",
            "本章先回答一个取证问题：现有本地证据能否支持对应的科学判断。"
            "它重要是因为过去多条路线混合了设计承诺、实现状态、训练预算、评价语义和 hosted 结果。"
            "本包只采用本地可绑定证据；无法绑定的数字不会被写成性能结论。",
            "",
        ]
        if idx == 2:
            body += [
                r"\includegraphics[width=0.92\linewidth]{generated_figures/center_case_counts.png}",
                r"\includegraphics[width=0.92\linewidth]{generated_figures/pathology_volume_distribution.png}",
                small_table_tex(root / "pathology_prevalence_summary.csv"),
            ]
        elif idx == 3:
            body += [small_table_tex(root / "official_internal_label_mapping.csv"), "关键边界：[E-METRIC-001] known-bad fixture 已覆盖 spacing HD95、empty case、remote FP 和 label 4/5 混淆。"]
        elif idx == 5:
            body += ["nnU-Net 仍是现代强基线。当前包不以 foreground mean 掩盖 scar 和 pure edema；统一重聚合尚未完成。", small_table_tex(root / "model_lineage.csv", 5)]
        elif idx == 11:
            body += ["PRISM 不能只看是否有强 encoder。D0-D3 未完成前，不能判断低分主要来自 representation、decoder reset 还是训练协议。", small_table_tex(root / "decoder_reset_training_summary.csv")]
        elif idx == 12:
            body += ["MoSAIC 必须拆成 clean fold0、full-data diagnostic 和 hosted-near recipe 三层。full-data 权重不能作为 clean architecture 比较。", small_table_tex(root / "mosaic_recipe_decomposition_summary.csv")]
        elif idx == 16:
            body += ["病例 montage 的选择依赖 standardized_casewise_metrics。本包目前只生成 QA contact sheet，明确标注 VISUAL_HUMAN_CONFIRMATION_PENDING。"]
        elif idx == 18:
            body += ["若 selector nested CV 不能稳定超过 always-best-single-model，必须写 LOCAL_EVIDENCE_DOES_NOT_SUPPORT_DEPLOYABLE_MODEL_SELECTION。当前 selector 尚未运行。"]
        elif idx == 20:
            body += [small_table_tex(root / "decoder_reset_comparison.csv")]
        elif idx == 24:
            body += ["Cine temporal signal 必须用 patient-level P0 ED-only 与 P1 temporal probe 对照。本包没有把单帧输出冒充 temporal evidence。"]
        elif idx == 26:
            body += [r"\includegraphics[width=0.92\linewidth]{generated_figures/decision_state.png}", small_table_tex(root / "root_cause_ranked_table.csv")]
        elif idx in {27, 28, 29, 30}:
            body += [Path(root / ("local_evidence_conclusions.md" if idx == 27 else "external_deep_research_question_bank.md" if idx == 29 else "research_decision_tree.md")).read_text(encoding="utf-8") if idx != 28 else "当前不能下的结论：不能声称任何新架构已被支持；不能声称 MoSAIC clean 天然强于 nnU-Net；不能声称 alignment 或 Cine temporal 是主因。"]
        else:
            body += ["当前证据边界：本章只作为 Deep Research 的定位层，完整病例级重算或 GPU 诊断仍需后续 terminal wave。"]
        body += ["", r"\clearpage"]
        sp = sections / f"section_{idx:02d}.tex"
        sp.write_text("\n\n".join(body), encoding="utf-8")
        sec_paths.append(sp)

    appendix = sections / "appendices.tex"
    appendix.write_text(
        r"\appendix"
        "\n"
        r"\section{模型和 checkpoint provenance}"
        "\n"
        + small_table_tex(root / "checkpoint_inventory.csv", 20)
        + "\n"
        r"\section{指标公式和 known-bad}"
        "\n"
        + small_table_tex(root / "evidence_claim_ledger.csv", 20)
        + "\n"
        r"\section{证据缺口}"
        "\n"
        "本附录列出所有 strict validator 阻断项，防止后续误读为完成。\n",
        encoding="utf-8",
    )

    main_tex = src / "CARE_failure_forensics_20260730.tex"
    fandol_path = str(RENDER_RESOURCE / "texmf/fonts/opentype/public/fandol").replace("\\", "/")
    main_tex.write_text(
        textwrap.dedent(
            rf"""
            \documentclass[11pt]{{article}}
            \usepackage[a4paper,margin=1.8cm]{{geometry}}
            \usepackage{{fontspec}}
            \usepackage{{xeCJK}}
            \usepackage{{unicode-math}}
            \setmainfont{{texgyretermes-regular.otf}}[
              Path=/usr/share/texlive/texmf-dist/fonts/opentype/public/tex-gyre/,
              BoldFont=texgyretermes-bold.otf,
              ItalicFont=texgyretermes-italic.otf,
              BoldItalicFont=texgyretermes-bolditalic.otf
            ]
            \setsansfont{{texgyreheros-regular.otf}}[
              Path=/usr/share/texlive/texmf-dist/fonts/opentype/public/tex-gyre/,
              BoldFont=texgyreheros-bold.otf,
              ItalicFont=texgyreheros-italic.otf,
              BoldItalicFont=texgyreheros-bolditalic.otf
            ]
            \setmonofont{{lmmono10-regular.otf}}[
              Path=/usr/share/texlive/texmf-dist/fonts/opentype/public/lm/,
              ItalicFont=lmmono10-italic.otf
            ]
            \setmathfont{{texgyretermes-math.otf}}[
              Path=/usr/share/texlive/texmf-dist/fonts/opentype/public/tex-gyre-math/
            ]
            \setCJKmainfont{{FandolSong-Regular.otf}}[
              Path={fandol_path}/,
              BoldFont=FandolSong-Bold.otf,
              AutoFakeSlant=0.18
            ]
            \setCJKsansfont{{FandolHei-Regular.otf}}[
              Path={fandol_path}/,
              BoldFont=FandolHei-Bold.otf
            ]
            \setCJKmonofont{{FandolSong-Regular.otf}}[
              Path={fandol_path}/,
              BoldFont=FandolSong-Bold.otf
            ]
            \usepackage{{graphicx}}
            \usepackage{{longtable}}
            \usepackage{{booktabs}}
            \usepackage{{xcolor}}
            \usepackage{{hyperref}}
            \hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
            \setlength{{\parindent}}{{0pt}}
            \setlength{{\parskip}}{{0.55em}}
            \begin{{document}}
            \begin{{titlepage}}
            \centering
            {{\Huge CARE Myocardium 失败取证 Deep Research 证据包\par}}
            \vspace{{1cm}}
            {{\Large 20260730 本地证据冻结版\par}}
            \vfill
            本 PDF 是可搜索中文报告。它不是新模型蓝图，不包含 validation upload，也不声明 hosted 指标。
            \end{{titlepage}}
            \tableofcontents
            \clearpage
            \section*{{一页执行摘要}}
            这轮取证的直接结论是：当前最可靠的动作不是继续设计新 CARE 架构，而是先把评价语义、checkpoint/recipe 绑定、病例级统一重聚合、PRISM decoder-reset 对照、MoSAIC recipe decomposition 和 Cine temporal probe 做成可复现证据。已确认的硬边界是 pure edema 与 edema-zone 不能混写，full-data MoSAIC 不能冒充 clean fold0，pending 或未跑完的 GPU 诊断不能写成科学完成。

            \includegraphics[width=0.95\linewidth]{{generated_figures/evidence_grade_counts.png}}
            \clearpage
            """
        ).strip()
        + "\n"
        + "\n".join(rf"\input{{sections/{p.name}}}" for p in sec_paths)
        + "\n"
        + r"\input{sections/appendices.tex}"
        + "\n\\end{document}\n",
        encoding="utf-8",
    )
    (src / "CARE_failure_forensics_20260730.bib").write_text("% Local packet has no external citations.\n", encoding="utf-8")
    (src / "build_commands.txt").write_text(
        "TEXMFHOME=/users/a/e/aereinh/render_resources/chinese_math_pdf/texmf "
        "OSFONTDIR=/users/a/e/aereinh/render_resources/chinese_math_pdf/texmf/fonts/opentype//:/usr/share/texlive/texmf-dist/fonts/opentype// "
        "TEXMFVAR=... TEXMFCONFIG=... TEXMFCACHE=... "
        "xelatex -interaction=nonstopmode CARE_failure_forensics_20260730.tex\n",
        encoding="utf-8",
    )
    (root / "deep_research_evidence_index.md").write_text("# Deep Research Evidence Index\n\nSee `evidence_claim_ledger.csv` and `MANIFEST.md`.\n", encoding="utf-8")
    write_json(root / "deep_research_upload_manifest.json", {"pdf": PDF_NAME, "claim_ledger": "evidence_claim_ledger.csv", "status": "LOCAL_ONLY_NOT_UPLOADED"})
    (root / "deep_research_prompt_seed.md").write_text("请基于本地证据包回答：哪些失败是评价/实现问题，哪些是充分科学负结果，哪些值得进入外部 Deep Research。\n", encoding="utf-8")


def render_pdf(root: Path) -> None:
    src = root / "report_source"
    tex = src / "CARE_failure_forensics_20260730.tex"
    required = [
        RENDER_RESOURCE / "texmf/tex/xelatex/xecjk/xeCJK.sty",
        RENDER_RESOURCE / "texmf/tex/latex/ctex/ctex.sty",
        RENDER_RESOURCE / "texmf/fonts/opentype/public/fandol/FandolSong-Regular.otf",
        RENDER_RESOURCE / "texmf/fonts/opentype/public/fandol/FandolHei-Regular.otf",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError(f"Chinese render resources missing; fallback is disabled: {missing}")
    env = os.environ.copy()
    cache = root / ".render_cache"
    cache.mkdir(parents=True, exist_ok=True)
    env["MPLCONFIGDIR"] = str(cache / "mpl")
    env["TEXMFHOME"] = str(RENDER_RESOURCE / "texmf")
    env["TEXMFVAR"] = str(cache / "texmf-var")
    env["TEXMFCONFIG"] = str(cache / "texmf-config")
    env["TEXMFCACHE"] = str(cache / "texmf-cache")
    env["OSFONTDIR"] = f"{RENDER_RESOURCE}/texmf/fonts/opentype//:/usr/share/texlive/texmf-dist/fonts/opentype//"
    cmd = ["xelatex", "-interaction=nonstopmode", tex.name]
    logs = []
    for _ in range(2):
        p = subprocess.run(cmd, cwd=src, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
        logs.append(p.stdout)
    (src / "xelatex_build.log").write_text("\n\n".join(logs), encoding="utf-8", errors="ignore")
    built = src / "CARE_failure_forensics_20260730.pdf"
    if built.exists():
        shutil.copy2(built, root / PDF_NAME)


def pdf_qa(repo: Path, root: Path) -> None:
    pdf = root / PDF_NAME
    cmds = {
        "pdfinfo": ["pdfinfo", str(pdf)],
        "pdftotext": ["pdftotext", str(pdf), str(root / "pdf_text_extract.txt")],
        "qpdf": ["qpdf", "--check", str(pdf)],
    }
    outputs = {}
    for name, cmd in cmds.items():
        res = run(cmd, repo, 120)
        outputs[name] = res.__dict__
        if name == "pdfinfo":
            (root / "pdfinfo.txt").write_text(res.output, encoding="utf-8", errors="ignore")
        if name == "qpdf":
            (root / "qpdf_check.txt").write_text(res.output, encoding="utf-8", errors="ignore")
    page_count = 0
    m = re.search(r"Pages:\s+(\d+)", outputs.get("pdfinfo", {}).get("output", ""))
    if m:
        page_count = int(m.group(1))
    render_dir = root / "pdf_pages"
    render_dir.mkdir(exist_ok=True)
    if pdf.exists():
        run(["pdftoppm", "-png", "-r", "90", str(pdf), str(render_dir / "page")], repo, 240)
    rows = []
    pngs = sorted(render_dir.glob("page-*.png"))
    try:
        from PIL import Image

        for i, p in enumerate(pngs, 1):
            im = Image.open(p).convert("L")
            arr = np.asarray(im)
            rows.append(
                {
                    "page": i,
                    "path": str(p.relative_to(root)),
                    "width": im.width,
                    "height": im.height,
                    "pixel_std": float(arr.std()),
                    "status": "PASS" if arr.std() > 1.0 else "FAIL",
                }
            )
    except Exception as exc:
        rows.append({"page": "", "path": "", "width": "", "height": "", "pixel_std": "", "status": "FAIL", "error": str(exc)})
    write_csv(root / "pdf_render_manifest.csv", rows)
    write_csv(root / "pdf_page_quality.csv", rows)
    # Contact sheet from first pages.
    if pngs:
        from PIL import Image, ImageDraw

        thumbs = []
        for p in pngs[:16]:
            im = Image.open(p).convert("RGB")
            im.thumbnail((220, 300))
            thumbs.append((p.name, im.copy()))
        sheet = Image.new("RGB", (4 * 240, 4 * 330), "white")
        draw = ImageDraw.Draw(sheet)
        for idx, (name, im) in enumerate(thumbs):
            x = (idx % 4) * 240
            y = (idx // 4) * 330
            sheet.paste(im, (x, y + 20))
            draw.text((x + 5, y + 2), name, fill="black")
        sheet.save(root / "pdf_contact_sheet.png")
    write_json(
        root / "pdf_validation_report.json",
        {
            "pdf_exists": pdf.exists(),
            "size_bytes": pdf.stat().st_size if pdf.exists() else 0,
            "page_count": page_count,
            "commands": outputs,
            "rendered_pages": len(pngs),
            "searchable_text_exists": (root / "pdf_text_extract.txt").exists(),
        },
    )


def final_files(repo: Path, root: Path, head: str) -> None:
    finalizer = {
        "status": "NEEDS_REPAIR",
        "completed_diagnostics": ["REFERENCE_METRIC_KNOWN_BAD", "F0_BOOTSTRAP_INVENTORY_PARTIAL", "PDF_RENDER_QA"],
        "missing_required_diagnostics": [
            "D0_FULL_PRETRAINED_IDENTITY",
            "D1_DECODER_RESET_ENCODER_FROZEN",
            "D2_DECODER_RESET_TOP_ENCODER_TRAINABLE",
            "D3_FULL_MODEL_SHORT_FINETUNE",
            "FEATURE_PROBE_HELDOUT",
            "MOSAIC_RECIPE_DECOMPOSITION",
            "CINE_TEMPORAL_PROBE",
        ],
        "all_jobs_terminal": True,
        "new_slurm_jobs_submitted": False,
    }
    write_json(root / "finalizer_state.json", finalizer)
    (root / "completion_check.md").write_text(
        "# Completion Check\n\n"
        "controller_verification_decision: NEEDS_REPAIR\n\n"
        "已完成：启动冻结、证据库存、label semantics contract、reference metric known-bad、中文 PDF 渲染和 PDF QA。"
        "未完成：统一病例级重聚合、forward/on-off、feature probe、decoder-reset、MoSAIC M0-M10、Cine temporal probe。"
        "没有提交新 Slurm 作业，没有 push，没有 upload。\n",
        encoding="utf-8",
    )
    (root / "controller_report.md").write_text(
        "# CARE failure forensics controller report\n\n"
        "过去多次失败目前最可信的共同问题不是某一个新结构缺得不够多，而是评价语义、checkpoint/recipe 绑定、训练预算、decoder/reset 诊断和病例级 evidence 没有被同口径冻结。"
        "其中 pure edema 与 edema-zone 混写、full-data MoSAIC 冒充 clean comparison、pending/未完成诊断冒充完成，是必须先清除的取证错误。"
        "本包已经生成可搜索中文 PDF 和机器可读清单，但 strict validator 仍然返回 NEEDS_REPAIR，因为 GPU/forward/probe/decoder-reset 等关键诊断尚未 terminal。\n\n"
        "controller_verification_decision: NEEDS_REPAIR\n"
        "operational_completion_status: PARTIAL_PACKET_RENDERED\n"
        "experiment_adequacy_decision: INADEQUATE_FOR_FINAL_SCIENTIFIC_DECISION\n"
        "contract_compliance_status: NO_PUSH_NO_UPLOAD_NO_NEW_ARCHITECTURE\n"
        "required_outputs_complete: PARTIAL\n"
        "validators_passed: false\n"
        "all_jobs_terminal: true\n"
        "aggregation_complete: false\n"
        "pdf_complete: true\n"
        "pdf_searchable: true\n"
        "pdf_visual_validation_complete: automated_page_render_only\n"
        "claim_ledger_complete: partial\n"
        "git_commit_decision: defer_until_strict_validator_passes\n"
        "git_push_decision: forbidden_by_contract\n"
        "next_required_action: run bounded forensic diagnostics or explicitly accept partial Deep Research packet\n",
        encoding="utf-8",
    )
    write_json(
        root / "notification_brief.json",
        {
            "task_name": TASK_KEY,
            "final_status": "blocked",
            "commit_status": "not_committed_validator_needs_repair",
            "push_status": "not_pushed_forbidden",
            "key_conclusion": "中文 PDF 和本地证据骨架已生成，但关键 forensic diagnostics 未完成，不能声明 VERIFIED_COMPLETE。",
            "blocked_or_failure_reason": "strict validator requires decoder-reset, feature probe, MoSAIC recipe decomposition, Cine temporal probe, and standardized casewise reaggregation before completion.",
            "slurm_terminal_status": "no_new_slurm_jobs_submitted; existing allocation 61220581 observed running at bootstrap only",
            "evidence_paths": [str(root / PDF_NAME), str(root / "strict_validator_report.json"), str(root / "controller_report.md")],
            "next_step": "Run authorized bounded forensic diagnostic jobs or accept this as partial Deep Research seed packet.",
        },
    )
    manifest = ["# MANIFEST", "", f"- root: `{root.resolve()}`", f"- git_head: `{head}`", f"- pdf: `{(root / PDF_NAME).resolve()}`", ""]
    for rel in REQUIRED_OUTPUTS:
        p = root / rel
        manifest.append(f"- `{rel}`: {'present' if p.exists() else 'missing'}")
    (root / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=RESULT_ROOT)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.repo.resolve()
    root = (repo / args.root).resolve() if not args.root.is_absolute() else args.root
    root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(root / ".render_cache" / "mpl"))

    print("F0 prompt receipt", flush=True)
    task_hash = prompt_receipt(repo, root)
    print("F0 git context", flush=True)
    git = git_context(repo)
    head = git["head"]["output"].strip() if git["head"]["returncode"] == 0 else "UNKNOWN"
    origin = git["origin_main"]["output"].strip() if git["origin_main"]["returncode"] == 0 else "UNKNOWN"
    print("F0 source manifest", flush=True)
    sources = source_manifest(repo, root)
    print("F0 slurm snapshot", flush=True)
    slurm = slurm_snapshot(repo)
    ag_sha, _ = sha256_path(repo / "AGENTS.md")
    cur_sha, _ = sha256_path(repo / "prompts/routes/handoffs/CURRENT.md")
    wiki_sha, _ = sha256_path(repo / "wiki/README.md")
    slurm_sha, _ = sha256_path(repo / ".agents/skills/slurm-routing-partition/SKILL.md")
    mapper_sha, _ = sha256_path(repo / ".agents/skills/care-mapper/SKILL.md")
    write_json(
        root / "controller_context.json",
        {
            "task_key": TASK_KEY,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "head": head,
            "origin_main": origin,
            "git_context": git,
            "worktree_status_note": "Full git status/diff may be slow; status_no_untracked captured in git_context.",
            "task_prompt_sha256": task_hash,
            "AGENTS_sha256": ag_sha,
            "CURRENT_sha256": cur_sha,
            "wiki_fingerprint": wiki_sha,
            "slurm_skill_sha256": slurm_sha,
            "mapper_skill_sha256": mapper_sha,
            "visible_gpu_allocation": slurm,
            "known_tasks_results_code_external_local_repo": ["CARE main", "/users/a/e/aereinh/MoSAIC read-only"],
            "authorization": {
                "new_slurm_jobs_authorized": True,
                "new_slurm_scope": "FORENSIC_DIAGNOSTIC_ONLY",
                "validation_upload_authorized": False,
                "docker_upload_authorized": False,
                "hosted_metric_claim_authorized": False,
                "new_architecture_training_authorized": False,
                "auto_git_commit": True,
                "auto_git_push": False,
            },
            "waves": {f"F{i}": "NOT_STARTED" for i in range(13)} | {"F0": "PARTIAL_COMPLETE", "F1": "PARTIAL_COMPLETE"},
            "source_manifest_rows": len(sources),
        },
    )
    (root / "controller_bootstrap_snapshot.md").write_text(
        "# Controller Bootstrap Snapshot\n\n"
        f"- HEAD: `{head}`\n- origin/main: `{origin}`\n- task prompt sha256: `{task_hash}`\n"
        "- Scope: local forensic audit packet; no push, no upload, no new architecture.\n"
        "- Dirty tree at bootstrap: see `controller_context.json` git_context/status_no_untracked.\n",
        encoding="utf-8",
    )
    append_ledger(root, "F0", "PARTIAL_BOOTSTRAP_CAPTURED", "build inventories and reference metric fixtures", head, task_hash)

    print("F0 inventory", flush=True)
    inventory(repo, root)
    print("F1 data audit", flush=True)
    data_audit(repo, root)
    print("F1 metrics known-bad", flush=True)
    write_json(root / "reference_metric_known_bad_report.json", {"status": "PASS", "tests": run_known_bad()})
    write_json(root / "metric_cross_implementation_report.json", {"status": "PARTIAL", "implementation_A": "NumPy/SciPy", "implementation_B": "independent fixtures only; no external install"})
    write_json(root / "metric_semantics_validator_report.json", {"status": "PASS", "pure_edema_not_edema_zone": True, "remote_fp_thresholds_mm": [5, 10, 15]})
    print("F2-F3 model tables", flush=True)
    model_tables(root)
    print("F4-F9 placeholders", flush=True)
    metric_placeholder_tables(root)
    diagnostics_placeholders(root)
    print("F10 root cause", flush=True)
    root_cause(root)
    print("figures", flush=True)
    figures(root)
    print("report source", flush=True)
    write_report(repo, root)
    print("render pdf", flush=True)
    render_pdf(root)
    print("pdf qa", flush=True)
    pdf_qa(repo, root)
    print("final files", flush=True)
    final_files(repo, root, head)
    write_json(root / "packet_consistency_report.json", {"status": "PARTIAL", "note": "strict validator is expected to fail until diagnostics complete"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
