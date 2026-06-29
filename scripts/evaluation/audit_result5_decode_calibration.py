#!/usr/bin/env python3
"""Audit Result5 checkpoint selection and pathology decode calibration."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training import run_srr_myops_fold0 as runner


DEFAULT_PROPOSAL_ROOT = REPO_ROOT / "results/20260628_myops_proposal"
DEFAULT_DECODE_DIR = REPO_ROOT / "results/20260629_loss_decode_calibration"
DEFAULT_CHECKPOINT_DIR = REPO_ROOT / "results/20260629_pathology_checkpoint_selection"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def finite_mean(values: list[Any]) -> float | None:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return float(np.mean(vals)) if vals else None


def load_completed_variant_dirs(root: Path, requested: list[str]) -> list[Path]:
    variant_root = root / "variants"
    out = []
    for name in requested:
        path = variant_root / name
        if (path / "summary.json").is_file():
            out.append(path)
    return out


def namespace_from_checkpoint_args(raw: dict[str, Any]) -> argparse.Namespace:
    defaults = runner.argparse.Namespace(
        variant="proposal_pos_neg_basic",
        base_channels=16,
        router_temperature=1.0,
        anatomy_router_temperature=None,
        scar_router_temperature=None,
        edema_router_temperature=None,
        expert_dropout=0.0,
        retrieval_entropy_floor=0.7,
        retrieval_entropy_weight=0.08,
        retrieval_coverage_weight=0.08,
        retrieval_max_weight_penalty=0.04,
        anatomy_weight=1.0,
        scar_weight=1.2,
        edema_weight=1.3,
        prior_weight=0.1,
        retrieval_weight=1.0,
        containment_weight=0.0,
        compactness_weight=0.0,
        proposal_bce_weight=0.45,
        proposal_margin_weight=0.20,
        proposal_uncertainty_weight=0.05,
        proposal_margin=0.25,
    )
    data = vars(defaults)
    data.update(raw)
    return argparse.Namespace(**data)


def load_model(checkpoint_path: Path, device: torch.device) -> torch.nn.Module:
    state = torch.load(checkpoint_path, map_location=device, weights_only=False)
    args = namespace_from_checkpoint_args(dict(state.get("args", {})))
    model = runner.make_model(args, device)
    model.load_state_dict(state["model_state_dict"])
    model.eval()
    return model


def sigmoid_np(logits: torch.Tensor) -> np.ndarray:
    return torch.sigmoid(logits)[0, 0].detach().cpu().numpy()


def raw_argmax(outputs: dict[str, torch.Tensor]) -> np.ndarray:
    return torch.argmax(outputs["logits"], dim=1)[0].detach().cpu().numpy().astype(np.uint8)


def priority_decode(
    outputs: dict[str, torch.Tensor],
    scar_key: str,
    edema_key: str,
    scar_threshold: float,
    edema_threshold: float,
) -> np.ndarray:
    pred = torch.argmax(outputs["anatomy_logits"], dim=1)[0].detach().cpu().numpy().astype(np.uint8)
    scar_logits = outputs.get(scar_key, outputs["scar_logits"])
    edema_logits = outputs.get(edema_key, outputs["edema_logits"])
    scar_prob = sigmoid_np(scar_logits)
    edema_prob = sigmoid_np(edema_logits)
    pred[edema_prob >= edema_threshold] = 4
    pred[scar_prob >= scar_threshold] = 5
    return pred


def decode_predictions(outputs: dict[str, torch.Tensor]) -> dict[str, np.ndarray]:
    preds = {
        "raw_argmax_current": raw_argmax(outputs),
        "mixed_priority_t0.50": priority_decode(outputs, "scar_logits", "edema_logits", 0.50, 0.50),
        "original_evidence_priority_t0.50": priority_decode(outputs, "scar_evidence_logits", "edema_evidence_logits", 0.50, 0.50),
    }
    if "scar_proposal_logits" in outputs:
        preds["proposal_priority_t0.50"] = priority_decode(outputs, "scar_proposal_logits", "edema_proposal_logits", 0.50, 0.50)
    return preds


def threshold_predictions(outputs: dict[str, torch.Tensor], thresholds: list[float]) -> dict[str, np.ndarray]:
    preds = {}
    for source, scar_key, edema_key in [
        ("mixed", "scar_logits", "edema_logits"),
        ("original_evidence", "scar_evidence_logits", "edema_evidence_logits"),
        ("proposal", "scar_proposal_logits", "edema_proposal_logits"),
    ]:
        if scar_key not in outputs or edema_key not in outputs:
            continue
        for threshold in thresholds:
            name = f"threshold_sweep_{source}_t{threshold:.2f}"
            preds[name] = priority_decode(outputs, scar_key, edema_key, threshold, threshold)
    return preds


def collect_fast_case_metrics(variant: str, case: runner.CaseData, pred: np.ndarray) -> list[dict[str, Any]]:
    gt = case.label_arr.astype(np.uint8, copy=False)
    invalid = sorted(set(np.unique(pred).tolist()) - {0, 1, 2, 3, 4, 5})
    rows = []
    for cls, name in [(4, "myops_edema"), (5, "myops_scar")]:
        pred_mask = pred == cls
        gt_mask = gt == cls
        small_fp, remote_fp = runner.fp_counts(pred_mask, gt_mask)
        rows.append(
            {
                "variant": variant,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "class_id": cls,
                "metric_name": name,
                "dice": runner.dice_per_class(pred, gt, cls, skip_if_gt_empty=False),
                "hd": None,
                "hd95": None,
                "component_count": runner.component_count(pred_mask),
                "small_fp_count": small_fp,
                "remote_fp_count": remote_fp,
                "pred_gt_volume_ratio": runner.volume_ratio(pred_mask, gt_mask),
                "pred_empty": not bool(pred_mask.any()),
                "gt_empty": not bool(gt_mask.any()),
                "invalid_label_values": ",".join(str(v) for v in invalid),
            }
        )
    return rows


def evaluate_checkpoint(
    variant: str,
    checkpoint_name: str,
    checkpoint_path: Path,
    val_cases: list[runner.CaseData],
    device: torch.device,
    thresholds: list[float],
) -> list[dict[str, Any]]:
    model = load_model(checkpoint_path, device)
    rows: list[dict[str, Any]] = []
    for case in val_cases:
        with torch.no_grad():
            x = torch.from_numpy(case.image[None]).float().to(device)
            av = torch.from_numpy(case.availability[None]).float().to(device)
            outputs = model(x, av)
        preds = decode_predictions(outputs)
        preds.update(threshold_predictions(outputs, thresholds))
        for mode, pred in preds.items():
            metric_fn = collect_fast_case_metrics if mode.startswith("threshold_sweep_") else runner.collect_case_metrics
            for row in metric_fn(f"{variant}__{checkpoint_name}__{mode}", case, pred):
                row["variant"] = variant
                row["checkpoint"] = checkpoint_name
                row["decode_mode"] = mode
                row["checkpoint_path"] = str(checkpoint_path)
                rows.append(row)
    return rows


def summarize_decode_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    groups: list[tuple[str, Any]] = [
        ("all_cases", lambda r: True),
        ("gt_positive_only", lambda r: not bool(r["gt_empty"])),
        ("t2_present", lambda r: bool(r["t2_present"])),
        ("complete_modality", lambda r: r["modality_group"] == "C0+LGE+T2"),
        ("CenterB", lambda r: r["center"] == "CenterB"),
        ("CenterC", lambda r: r["center"] == "CenterC"),
        ("LGE-only", lambda r: r["modality_group"] == "LGE-only"),
        ("no_T2_empty_GT", lambda r: (not bool(r["t2_present"])) and bool(r["gt_empty"])),
    ]
    keys = sorted({(r["variant"], r["checkpoint"], r["decode_mode"], int(r["class_id"]), r["metric_name"]) for r in rows})
    for variant, checkpoint, mode, cls, metric_name in keys:
        cls_rows = [
            r
            for r in rows
            if r["variant"] == variant
            and r["checkpoint"] == checkpoint
            and r["decode_mode"] == mode
            and int(r["class_id"]) == cls
        ]
        for group, predicate in groups:
            subset = [r for r in cls_rows if predicate(r)]
            if not subset:
                continue
            out.append(
                {
                    "variant": variant,
                    "checkpoint": checkpoint,
                    "decode_mode": mode,
                    "class_id": cls,
                    "metric_name": metric_name,
                    "group": group,
                    "n": len(subset),
                    "dice_mean": finite_mean([r["dice"] for r in subset]),
                    "hd_mean": finite_mean([r["hd"] for r in subset]),
                    "hd95_mean": finite_mean([r["hd95"] for r in subset]),
                    "component_count_mean": finite_mean([r["component_count"] for r in subset]),
                    "remote_fp_mean": finite_mean([r["remote_fp_count"] for r in subset]),
                    "empty_prediction_rate": finite_mean([1.0 if r["pred_empty"] else 0.0 for r in subset]),
                    "pred_gt_volume_ratio_mean": finite_mean([r["pred_gt_volume_ratio"] for r in subset]),
                }
            )
    return out


def get_metric(rows: list[dict[str, Any]], variant: str, checkpoint: str, mode: str, cls: int, group: str, key: str) -> float | None:
    for row in rows:
        if (
            row["variant"] == variant
            and row["checkpoint"] == checkpoint
            and row["decode_mode"] == mode
            and int(row["class_id"]) == cls
            and row["group"] == group
        ):
            val = row.get(key)
            return None if val is None else float(val)
    return None


def checkpoint_metric_rows(summary_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    keys = sorted({(r["variant"], r["checkpoint"], r["decode_mode"]) for r in summary_rows})
    for variant, checkpoint, mode in keys:
        scar_dice = get_metric(summary_rows, variant, checkpoint, mode, 5, "all_cases", "dice_mean")
        edema_dice = get_metric(summary_rows, variant, checkpoint, mode, 4, "gt_positive_only", "dice_mean")
        scar_hd95 = get_metric(summary_rows, variant, checkpoint, mode, 5, "all_cases", "hd95_mean")
        edema_hd95 = get_metric(summary_rows, variant, checkpoint, mode, 4, "gt_positive_only", "hd95_mean")
        scar_remote = get_metric(summary_rows, variant, checkpoint, mode, 5, "all_cases", "remote_fp_mean")
        edema_remote = get_metric(summary_rows, variant, checkpoint, mode, 4, "gt_positive_only", "remote_fp_mean")
        scar_comp = get_metric(summary_rows, variant, checkpoint, mode, 5, "all_cases", "component_count_mean")
        edema_comp = get_metric(summary_rows, variant, checkpoint, mode, 4, "gt_positive_only", "component_count_mean")
        score = None
        if scar_dice is not None and edema_dice is not None:
            score = (
                scar_dice
                + edema_dice
                - 0.001 * (scar_hd95 or 0.0)
                - 0.001 * (edema_hd95 or 0.0)
                - 0.02 * ((scar_remote or 0.0) + (edema_remote or 0.0)) / 2.0
                - 0.01 * ((scar_comp or 0.0) + (edema_comp or 0.0)) / 2.0
            )
        out.append(
            {
                "variant": variant,
                "checkpoint": checkpoint,
                "decode_mode": mode,
                "scar_all_dice": scar_dice,
                "edema_gt_positive_dice": edema_dice,
                "scar_all_hd95": scar_hd95,
                "edema_gt_positive_hd95": edema_hd95,
                "scar_remote_fp_mean": scar_remote,
                "edema_remote_fp_mean": edema_remote,
                "scar_component_count_mean": scar_comp,
                "edema_component_count_mean": edema_comp,
                "pathology_selection_score": score,
            }
        )
    return out


def choose_decode_selection(summary_rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    keys = sorted({(r["variant"], r["checkpoint"]) for r in summary_rows})
    any_signal = False
    any_rows = bool(summary_rows)
    for variant, checkpoint in keys:
        raw_scar = get_metric(summary_rows, variant, checkpoint, "raw_argmax_current", 5, "all_cases", "dice_mean")
        raw_edema = get_metric(summary_rows, variant, checkpoint, "raw_argmax_current", 4, "gt_positive_only", "dice_mean")
        best_combo = -1.0
        best_mode = ""
        for row in summary_rows:
            if row["variant"] != variant or row["checkpoint"] != checkpoint or row["group"] not in {"all_cases", "gt_positive_only"}:
                continue
            mode = row["decode_mode"]
            scar = get_metric(summary_rows, variant, checkpoint, mode, 5, "all_cases", "dice_mean")
            edema = get_metric(summary_rows, variant, checkpoint, mode, 4, "gt_positive_only", "dice_mean")
            if scar is None or edema is None:
                continue
            combo = scar + edema
            if combo > best_combo:
                best_combo = combo
                best_mode = mode
        raw_combo = (raw_scar or 0.0) + (raw_edema or 0.0)
        if best_mode:
            reasons.append(
                f"{variant}/{checkpoint}: raw_combo={raw_combo:.4f}, "
                f"best_combo={best_combo:.4f}, best_mode={best_mode}"
            )
        else:
            reasons.append(
                f"{variant}/{checkpoint}: no complete scar+edema target group pair; "
                f"raw_scar={raw_scar}, raw_edema={raw_edema}"
            )
            continue
        if best_combo - raw_combo >= 0.05:
            any_signal = True
    if not any_rows:
        return "INSUFFICIENT_ARTIFACTS", ["No completed checkpoints were available."]
    return ("DECODE_CALIBRATION_SIGNAL" if any_signal else "NO_HIDDEN_EVIDENCE", reasons)


def choose_checkpoint_selection(checkpoint_rows: list[dict[str, Any]]) -> tuple[str, list[str]]:
    reasons = []
    variants = sorted({r["variant"] for r in checkpoint_rows})
    if not checkpoint_rows:
        return "INSUFFICIENT_CHECKPOINTS", ["No checkpoint metrics were produced."]
    final_better = False
    for variant in variants:
        modes = sorted({r["decode_mode"] for r in checkpoint_rows if r["variant"] == variant})
        for mode in modes:
            best = next((r for r in checkpoint_rows if r["variant"] == variant and r["checkpoint"] == "best" and r["decode_mode"] == mode), None)
            final = next((r for r in checkpoint_rows if r["variant"] == variant and r["checkpoint"] == "final" and r["decode_mode"] == mode), None)
            if best is None or final is None:
                continue
            best_score = best.get("pathology_selection_score")
            final_score = final.get("pathology_selection_score")
            if best_score is None or final_score is None:
                continue
            delta = float(final_score) - float(best_score)
            reasons.append(f"{variant}/{mode}: final_minus_best_score={delta:.4f}")
            if delta >= 0.02:
                final_better = True
    if final_better:
        return "FINAL_BETTER_THAN_PATCH_BEST", reasons
    if reasons:
        return "PATCH_BEST_CONFIRMED_OK", reasons
    return "INSUFFICIENT_CHECKPOINTS", ["Best/final checkpoint pairs lacked complete scar+edema target groups."]


def write_task_docs(
    decode_dir: Path,
    checkpoint_dir: Path,
    decode_selection: str,
    decode_reasons: list[str],
    checkpoint_selection: str,
    checkpoint_reasons: list[str],
    variants: list[str],
) -> None:
    decode_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    (decode_dir / "selection.md").write_text(
        "\n".join(["# Loss/Decode Calibration Selection", "", f"status: `{decode_selection}`", "", "## Reasons", *[f"- {r}" for r in decode_reasons]]) + "\n",
        encoding="utf-8",
    )
    (checkpoint_dir / "selection.md").write_text(
        "\n".join(["# Pathology Checkpoint Selection", "", f"status: `{checkpoint_selection}`", "", "## Reasons", *[f"- {r}" for r in checkpoint_reasons]]) + "\n",
        encoding="utf-8",
    )
    (decode_dir / "result.md").write_text(
        "\n".join(
            [
                "# Result 20260629 Loss/Decode Calibration",
                "",
                f"- variants evaluated: `{', '.join(variants)}`",
                f"- selection: `{decode_selection}`",
                "- outputs: `decode_metrics.csv`, `checkpoint_comparison.csv`, `selection.md`.",
                "- This task reads completed local fold0 checkpoints only and does not modify running Slurm jobs.",
                "- Core SRR losses were audited; ignored `-1` padding was confirmed as a bug in prior code and repaired for future runs.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (checkpoint_dir / "result.md").write_text(
        "\n".join(
            [
                "# Result 20260629 Pathology Checkpoint Selection",
                "",
                f"- variants evaluated: `{', '.join(variants)}`",
                f"- selection: `{checkpoint_selection}`",
                "- outputs: `checkpoint_metrics.csv`, `selection.md`.",
                "- Pathology-aware score uses scar all-case Dice plus edema GT-positive Dice, penalized by HD95, remote FP, and component burden.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (decode_dir / "MANIFEST.md").write_text(
        "\n".join(
            [
                "# MANIFEST",
                "",
                "- Task: `prompts/tasks/20260629_loss_decode_calibration.md`",
                "- Result: `results/20260629_loss_decode_calibration/result.md`",
                "- Selection: `results/20260629_loss_decode_calibration/selection.md`",
                "- Decode metrics: `results/20260629_loss_decode_calibration/decode_metrics.csv`",
                "- Checkpoint comparison copy: `results/20260629_loss_decode_calibration/checkpoint_comparison.csv`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (checkpoint_dir / "MANIFEST.md").write_text(
        "\n".join(
            [
                "# MANIFEST",
                "",
                "- Task: `prompts/tasks/20260629_pathology_checkpoint_selection.md`",
                "- Result: `results/20260629_pathology_checkpoint_selection/result.md`",
                "- Selection: `results/20260629_pathology_checkpoint_selection/selection.md`",
                "- Checkpoint metrics: `results/20260629_pathology_checkpoint_selection/checkpoint_metrics.csv`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal-root", type=Path, default=DEFAULT_PROPOSAL_ROOT)
    parser.add_argument("--decode-dir", type=Path, default=DEFAULT_DECODE_DIR)
    parser.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    parser.add_argument("--variants", default="proposal_pos_neg_basic")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--thresholds", default="0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90")
    parser.add_argument("--limit-cases", type=int, default=0, help="Debug only: evaluate the first N fold0 validation cases.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    requested = [v.strip() for v in args.variants.split(",") if v.strip()]
    thresholds = [float(x) for x in args.thresholds.split(",") if x.strip()]
    device = torch.device(args.device)
    _, val_ids = runner.load_split(0)
    if args.limit_cases > 0:
        val_ids = val_ids[: args.limit_cases]
    metadata = runner.load_myops_case_metadata()
    val_cases = [runner.read_case(cid, metadata) for cid in val_ids]
    variant_dirs = load_completed_variant_dirs(args.proposal_root, requested)
    case_rows: list[dict[str, Any]] = []
    evaluated_variants: list[str] = []
    for variant_dir in variant_dirs:
        variant = variant_dir.name
        ckpt_dir = variant_dir / "checkpoints/fold_0/srr_fold0_config"
        checkpoints = {
            "best": ckpt_dir / "checkpoint_best.pt",
            "final": ckpt_dir / "checkpoint_final.pt",
        }
        variant_done = False
        for checkpoint_name, path in checkpoints.items():
            if not path.is_file() or path.stat().st_size == 0:
                continue
            case_rows.extend(evaluate_checkpoint(variant, checkpoint_name, path, val_cases, device, thresholds))
            variant_done = True
        if variant_done:
            evaluated_variants.append(variant)
    summary_rows = summarize_decode_rows(case_rows)
    checkpoint_rows = checkpoint_metric_rows(summary_rows)
    args.decode_dir.mkdir(parents=True, exist_ok=True)
    args.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.decode_dir / "decode_case_metrics.csv", case_rows)
    write_csv(args.decode_dir / "decode_metrics.csv", summary_rows)
    write_csv(args.decode_dir / "checkpoint_comparison.csv", checkpoint_rows)
    write_csv(args.checkpoint_dir / "checkpoint_metrics.csv", checkpoint_rows)
    decode_selection, decode_reasons = choose_decode_selection(summary_rows)
    checkpoint_selection, checkpoint_reasons = choose_checkpoint_selection(checkpoint_rows)
    write_task_docs(
        args.decode_dir,
        args.checkpoint_dir,
        decode_selection,
        decode_reasons,
        checkpoint_selection,
        checkpoint_reasons,
        evaluated_variants,
    )
    print(json.dumps({"variants": evaluated_variants, "decode_selection": decode_selection, "checkpoint_selection": checkpoint_selection}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
