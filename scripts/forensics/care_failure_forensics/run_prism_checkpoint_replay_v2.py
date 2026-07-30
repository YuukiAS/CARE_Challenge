#!/usr/bin/env python3
"""Replay all CARE-PRISM W3 checkpoints for the V2 forensic packet."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_care_prism import (  # noqa: E402
    binary_metrics,
    crop_outputs,
    move_batch,
    pad_to_multiple,
    spatial_multiple,
)
from src.care_myocardium.data.care_prism_dataset import CAREPRISMAugmenter, CAREPRISMFullPatientDataset  # noqa: E402
from src.care_myocardium.inference.care_prism_predictor import CAREPRISMDecodeConfig, decode_care_prism_outputs  # noqa: E402
from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_care_prism, build_source_nnunet  # noqa: E402
from src.care_myocardium.training.care_prism_trainer import file_sha256  # noqa: E402


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
SOURCE_RUNTIME = Path(
    "results/20260729_care_prism_v2_backbone_repair_and_resume/runtime/fold0_w3_fold0_6500_formal_v2"
)
NNUNET_CKPT = Path(
    "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception as exc:
        return f"UNAVAILABLE:{type(exc).__name__}:{exc}"


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows([{k: row.get(k, "") for k in fieldnames} for row in rows])


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True, default=str)
        f.write("\n")


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if value != value:
            return "nan"
        if value == float("inf"):
            return "inf"
        return f"{value:.9f}"
    return str(value)


def checkpoint_step(path: Path) -> int:
    stem = path.stem
    return int(stem.replace("checkpoint_step", ""))


def append_or_replace_status(path: Path, task_id: str, status_row: dict[str, Any]) -> None:
    fieldnames = ["task_id", "category", "required", "status", "terminal_status", "evidence_path", "notes"]
    rows: list[dict[str, Any]] = []
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as f:
            rows = [{k: row.get(k, "") for k in fieldnames} for row in csv.DictReader(f)]
    replaced = False
    for row in rows:
        if row.get("task_id") == task_id:
            row.update(status_row)
            replaced = True
    if not replaced:
        rows.append({"task_id": task_id, **status_row})
    write_csv(path, rows, fieldnames)


def save_probability(prob_dir: Path, checkpoint: Path, case_id: str, decoded: dict[str, Any]) -> Path:
    step = checkpoint.stem.replace("checkpoint_", "")
    path = prob_dir / step / f"{case_id}_probabilities.npz"
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        scar_probability=decoded["scar_probability"].astype(np.float16),
        edema_probability=decoded["edema_probability"].astype(np.float16),
    )
    return path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--max-cases", type=int, default=0)
    args = ap.parse_args()

    root = args.root.resolve()
    result_root = root / RESULT_REL
    output_root = result_root / "runtime/prism_checkpoint_replay_v2" / args.run_id
    probability_root = output_root / "raw_probabilities"
    source_runtime = root / SOURCE_RUNTIME
    checkpoint_dir = source_runtime / "checkpoints"
    checkpoints = sorted(checkpoint_dir.glob("checkpoint_step*.pt"), key=checkpoint_step)
    if len(checkpoints) != 13:
        raise SystemExit(f"expected 13 checkpoints, found {len(checkpoints)} in {checkpoint_dir}")
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")

    config = CAREPRISMConfig.from_nnunet_plans()
    pad_multiple = spatial_multiple(config)
    ds = CAREPRISMFullPatientDataset(fold=0, split="inner_select", augmenter=CAREPRISMAugmenter(training=False))
    case_limit = len(ds) if args.max_cases <= 0 else min(args.max_cases, len(ds))
    anchor = build_source_nnunet(config).to(device)
    anchor_payload = torch.load(root / NNUNET_CKPT, map_location="cpu", weights_only=False)
    anchor.load_state_dict(anchor_payload.get("network_weights", anchor_payload), strict=False)
    anchor.eval()

    case_rows: list[dict[str, Any]] = []
    prob_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    threshold_cfg = CAREPRISMDecodeConfig(scar_threshold=0.5, edema_threshold=0.5)
    for checkpoint in checkpoints:
        model = build_care_prism(config).to(device)
        payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
        model.load_state_dict(payload["model_state"])
        model.eval()
        checkpoint_case_rows: list[dict[str, Any]] = []
        with torch.no_grad():
            for idx in range(case_limit):
                batch = move_batch(ds[idx], device)
                images, original_spatial = pad_to_multiple(batch["images"].float(), pad_multiple)
                outputs = crop_outputs(model(images, batch["availability"]), original_spatial)
                decoded = decode_care_prism_outputs(outputs, batch["availability"], threshold_cfg)
                logits = anchor(images)
                if isinstance(logits, (list, tuple)):
                    logits = logits[0]
                labels = logits[..., : original_spatial[0], : original_spatial[1], : original_spatial[2]].argmax(dim=1, keepdim=True)
                case_id = batch["case_id"][0]
                scar_target = batch["scar_target"].detach().cpu().numpy()[0, 0] > 0.5
                edema_zone_target = batch["edema_zone_target"].detach().cpu().numpy()[0, 0] > 0.5
                pure_edema_target = edema_zone_target & ~scar_target
                union = batch["anatomy_target"][:, 0:1].detach().cpu().numpy()[0, 0] > 0.5
                predictions = {
                    "scar": decoded["scar_mask"].astype(bool),
                    "pure_edema": decoded["pure_edema_mask"].astype(bool),
                    "edema_zone": decoded["edema_zone_mask"].astype(bool),
                }
                targets = {
                    "scar": scar_target,
                    "pure_edema": pure_edema_target,
                    "edema_zone": edema_zone_target,
                }
                anchor_predictions = {
                    "scar": (labels == 5).detach().cpu().numpy()[0, 0],
                    "pure_edema": (labels == 4).detach().cpu().numpy()[0, 0],
                    "edema_zone": ((labels == 4) | (labels == 5)).detach().cpu().numpy()[0, 0],
                }
                prob_path = save_probability(probability_root, checkpoint, case_id, decoded)
                prob_rows.append(
                    {
                        "checkpoint": str(checkpoint.relative_to(root)),
                        "checkpoint_step": checkpoint_step(checkpoint),
                        "checkpoint_sha256": file_sha256(checkpoint),
                        "case_id": case_id,
                        "probability_file": str(prob_path.relative_to(root)),
                        "probability_sha256": sha256_file(prob_path),
                        "probability_size_bytes": prob_path.stat().st_size,
                        "scar_threshold": 0.5,
                        "edema_threshold": 0.5,
                        "no_t2_edema_exact_zero": decoded["no_t2_edema_exact_zero"],
                    }
                )
                for metric_name in ("scar", "pure_edema", "edema_zone"):
                    metrics = binary_metrics(predictions[metric_name], targets[metric_name], union)
                    anchor_metrics = binary_metrics(anchor_predictions[metric_name], targets[metric_name], union)
                    row = {
                        "checkpoint": str(checkpoint.relative_to(root)),
                        "checkpoint_step": checkpoint_step(checkpoint),
                        "checkpoint_sha256": file_sha256(checkpoint),
                        "case_id": case_id,
                        "split": "inner_select",
                        "metric_name": metric_name,
                        "t2_present": fmt(float(batch["t2_present"][0, 0])),
                        "dice": fmt(metrics["dice"]),
                        "hd95_voxels": fmt(metrics["hd95"]),
                        "exact_hd_voxels": fmt(metrics["exact_hd"]),
                        "infinite_hd": metrics["infinite_hd"],
                        "lesion_recall": fmt(metrics["lesion_recall"]),
                        "gt_component_count": metrics["gt_component_count"],
                        "pred_component_count": metrics["pred_component_count"],
                        "remote_fp_count_known_bug_old_definition": metrics["remote_fp_count"],
                        "volume_ratio": fmt(metrics["volume_ratio"]),
                        "empty_gt": metrics["empty_gt"],
                        "empty_pred": metrics["empty_pred"],
                        "nnunet_dice": fmt(anchor_metrics["dice"]),
                        "dice_delta_vs_nnunet": fmt(metrics["dice"] - anchor_metrics["dice"]),
                        "nnunet_hd95_voxels": fmt(anchor_metrics["hd95"]),
                        "help_vs_nnunet": metrics["dice"] > anchor_metrics["dice"],
                        "harm_vs_nnunet": metrics["dice"] < anchor_metrics["dice"],
                    }
                    case_rows.append(row)
                    checkpoint_case_rows.append(row)
        for metric_name in ("scar", "pure_edema", "edema_zone"):
            metric_subset = [r for r in checkpoint_case_rows if r["metric_name"] == metric_name]
            dices = [float(r["dice"]) for r in metric_subset]
            helped = sum(1 for r in metric_subset if str(r["help_vs_nnunet"]) == "True")
            harmed = sum(1 for r in metric_subset if str(r["harm_vs_nnunet"]) == "True")
            curve_rows.append(
                {
                    "checkpoint": str(checkpoint.relative_to(root)),
                    "checkpoint_step": checkpoint_step(checkpoint),
                    "checkpoint_sha256": file_sha256(checkpoint),
                    "metric_name": metric_name,
                    "case_count": len(metric_subset),
                    "mean_dice": fmt(float(np.mean(dices)) if dices else float("nan")),
                    "median_dice": fmt(float(np.median(dices)) if dices else float("nan")),
                    "help_case_count": helped,
                    "harm_case_count": harmed,
                    "raw_probability_rows": sum(1 for r in prob_rows if int(r["checkpoint_step"]) == checkpoint_step(checkpoint)),
                }
            )

    write_csv(
        result_root / "prism_corrected_casewise_metrics.csv",
        case_rows,
        [
            "checkpoint",
            "checkpoint_step",
            "checkpoint_sha256",
            "case_id",
            "split",
            "metric_name",
            "t2_present",
            "dice",
            "hd95_voxels",
            "exact_hd_voxels",
            "infinite_hd",
            "lesion_recall",
            "gt_component_count",
            "pred_component_count",
            "remote_fp_count_known_bug_old_definition",
            "volume_ratio",
            "empty_gt",
            "empty_pred",
            "nnunet_dice",
            "dice_delta_vs_nnunet",
            "nnunet_hd95_voxels",
            "help_vs_nnunet",
            "harm_vs_nnunet",
        ],
    )
    write_csv(
        result_root / "prism_raw_probability_manifest.csv",
        prob_rows,
        [
            "checkpoint",
            "checkpoint_step",
            "checkpoint_sha256",
            "case_id",
            "probability_file",
            "probability_sha256",
            "probability_size_bytes",
            "scar_threshold",
            "edema_threshold",
            "no_t2_edema_exact_zero",
        ],
    )
    write_csv(
        result_root / "prism_checkpoint_curve.csv",
        curve_rows,
        [
            "checkpoint",
            "checkpoint_step",
            "checkpoint_sha256",
            "metric_name",
            "case_count",
            "mean_dice",
            "median_dice",
            "help_case_count",
            "harm_case_count",
            "raw_probability_rows",
        ],
    )
    selected = max([r for r in curve_rows if r["metric_name"] == "edema_zone"], key=lambda r: float(r["mean_dice"]))
    receipt = {
        "created_at_utc": utc_now(),
        "status": "COMPLETED_WITH_VALID_EVIDENCE",
        "task": "G2_PRISM_13_CHECKPOINT_REPLAY",
        "run_id": args.run_id,
        "checkpoint_count": len(checkpoints),
        "case_count": case_limit,
        "row_count": len(case_rows),
        "probability_row_count": len(prob_rows),
        "split": "inner_select",
        "outer_accessed": False,
        "thresholds": {"scar": 0.5, "edema": 0.5},
        "selected_by_edema_zone_mean_dice": selected,
        "repo_head": git_head(root),
        "environment": {
            "python": sys.executable,
            "torch": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
            "hostname": socket.gethostname(),
            "platform": platform.platform(),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", ""),
            "slurm_step_id": os.environ.get("SLURM_STEP_ID", ""),
            "slurm_partition": os.environ.get("SLURM_JOB_PARTITION", ""),
        },
        "outputs": {
            "curve_csv": str((result_root / "prism_checkpoint_curve.csv").relative_to(root)),
            "casewise_csv": str((result_root / "prism_corrected_casewise_metrics.csv").relative_to(root)),
            "raw_probability_manifest": str((result_root / "prism_raw_probability_manifest.csv").relative_to(root)),
            "runtime_probability_root": str(probability_root.relative_to(root)),
        },
    }
    write_json(result_root / "prism_checkpoint_replay_receipt.json", receipt)
    report = (
        "# PRISM 13-checkpoint replay\n\n"
        "结论：G2 已在 fold0 inner_select 上重放 W3 formal v2 的 13 个 checkpoint，"
        "固定 scar/edema threshold 为 0.5，并为每个 checkpoint/case 保存 scar 与 edema raw probability。"
        "该证据用于后续 PRISM curve、step3000 选择、pure edema/scar 分离和 component on/off 分析；"
        "尚未等同于 P1-P11 全部完成。\n\n"
        f"- checkpoint_count: {len(checkpoints)}\n"
        f"- case_count: {case_limit}\n"
        f"- metric rows: {len(case_rows)}\n"
        f"- raw probability rows: {len(prob_rows)}\n"
        f"- selected checkpoint by edema_zone mean Dice: step {selected['checkpoint_step']}\n"
    )
    (result_root / "prism_forensics_report.md").write_text(report, encoding="utf-8")
    append_or_replace_status(
        result_root / "v2_task_status.csv",
        "G2_PRISM_13_CHECKPOINT_REPLAY",
        {
            "category": "gpu_diagnostic",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE",
            "terminal_status": "true",
            "evidence_path": str((result_root / "prism_checkpoint_replay_receipt.json").relative_to(root)),
            "notes": "13 W3 checkpoints replayed on inner_select with raw probability manifest; P1-P11 still need downstream aggregation.",
        },
    )
    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
