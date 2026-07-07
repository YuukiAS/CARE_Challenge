#!/usr/bin/env python3
"""Replay completed M8 checkpoints on a broader fold0 validation subset.

This helper is evaluation-only. It does not train, package validation outputs,
upload, or make hosted metric claims. Its purpose is to close the M8 formal
evidence breadth gap by adding T2-present, multimodal, CenterB/CenterC fold0
validation cases to the same local metric tables used by the M8 aggregator.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import collect_case_metrics, load_split, write_csv  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_PROPOSAL_THRESHOLDS,
    SRRProposeRefineMyoPS,
    evaluate,
    full_case_anchor_tensors,
    load_myops_case_metadata,
    maybe_disable_context,
    model_kwargs_from_args,
    read_anchored_case,
)


TASK_KEY = "20260707_srr_v3_m8_editor_grade_leaderboard_sprint"
DEFAULT_PACKET = REPO_ROOT / "results" / TASK_KEY
VARIANTS = [
    "m8_full_srr_context_arbitration_longrun",
    "m8_scar_precision_edema_safe_longrun",
    "m8_t2_centerC_edema_repair_longrun",
]


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def as_bool(value: object) -> bool:
    return str(value).lower() in {"1", "true", "yes"}


def parse_thresholds(value: object) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    text = str(value or DEFAULT_PROPOSAL_THRESHOLDS)
    return [float(part) for part in text.replace(";", ",").split(",") if part.strip()]


def variant_dir(packet: Path, variant: str) -> Path:
    return packet / "runtime" / "variants" / variant


def broad_variant_dir(packet: Path, variant: str) -> Path:
    return packet / "runtime" / "broad_eval" / "variants" / variant


def select_broad_case_ids(packet: Path, fold: int, max_cases: int, explicit_case_ids: list[str]) -> list[str]:
    if explicit_case_ids:
        return explicit_case_ids[:max_cases]
    metadata = load_myops_case_metadata()
    _train_ids, val_ids = load_split(fold)
    existing_cases = {
        str(row.get("case_id", ""))
        for row in read_csv_rows(packet / "m8_formal_case_manifest.csv")
        if row.get("case_id")
    }
    priority: list[tuple[int, str]] = []
    for idx, case_id in enumerate(val_ids):
        meta = metadata[case_id]
        if case_id in existing_cases:
            continue
        center_priority = 0 if meta.center in {"CenterB", "CenterC"} else 2
        t2_priority = 0 if bool(meta.t2_present) else 3
        multimodal_priority = 0 if str(meta.modality_group).lower() != "lge-only" else 2
        priority.append((center_priority + t2_priority + multimodal_priority, f"{idx:04d}:{case_id}"))
    selected = [item.split(":", 1)[1] for _score, item in sorted(priority)]
    return selected[:max_cases]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    import csv

    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def source_args_from_checkpoint(state: dict[str, object], summary: dict[str, object]) -> Namespace:
    values = dict(state.get("args", {}) or {})
    values.setdefault("variant", summary.get("model_variant") or state.get("model_variant") or state.get("variant"))
    values.setdefault("run_label", values.get("variant"))
    values.setdefault("base_channels", summary.get("base_channels") or 32)
    values.setdefault("encoder_profile", summary.get("encoder_profile") or "balanced_4scale")
    values.setdefault("disable_local_refinement", False)
    values.setdefault("disable_anatomy_roi_prior", False)
    values.setdefault("disable_nnunet_anchor", summary.get("disable_nnunet_anchor", False))
    values.setdefault("nnunet_anchor_root", summary.get("nnunet_anchor_root"))
    values.setdefault("proposal_thresholds", summary.get("proposal_thresholds") or DEFAULT_PROPOSAL_THRESHOLDS)
    values.setdefault("scar_decode_threshold", summary.get("scar_decode_threshold", 0.5))
    values.setdefault("edema_decode_threshold", summary.get("edema_decode_threshold", 0.5))
    return Namespace(**values)


def metric_rows_by_name(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(row.get("metric_name", "")): row for row in rows}


def finite_float(value: object, default: float = 0.0) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return default
    return out if out == out else default


def sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values.astype(np.float32, copy=False)))


def proposal_recall_precision(proposal: np.ndarray, gt_mask: np.ndarray) -> tuple[object, object]:
    proposal = proposal.astype(bool, copy=False)
    gt_mask = gt_mask.astype(bool, copy=False)
    proposal_voxels = int(proposal.sum())
    gt_voxels = int(gt_mask.sum())
    inter = int(np.logical_and(proposal, gt_mask).sum())
    recall: object = "" if gt_voxels == 0 else inter / max(1, gt_voxels)
    precision: object = "" if proposal_voxels == 0 else inter / max(1, proposal_voxels)
    return recall, precision


def checkpoint_contribution_and_anchor_rows(
    model: SRRProposeRefineMyoPS,
    args: Namespace,
    cases: list[object],
    device: torch.device,
    *,
    variant: str,
    checkpoint: Path,
    out_dir: Path,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    contribution_rows: list[dict[str, object]] = []
    anchor_rows: list[dict[str, object]] = []
    model.eval()
    for case in cases:
        with torch.no_grad():
            x = torch.from_numpy(case.image[None]).float().to(device)
            av = torch.from_numpy(case.availability[None]).float().to(device)
            anchor_features, component_features = full_case_anchor_tensors(case, device)
            anchor_features, component_features = maybe_disable_context(args, anchor_features, component_features)
            outputs = model(x, av, anchor_features=anchor_features, component_features=component_features)
            final_logits = outputs["logits"]
            anchor_logits = outputs.get("nnunet_anchor_logits")
            if anchor_logits is None:
                continue
            final_pred = torch.argmax(final_logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
            anchor_pred = torch.argmax(anchor_logits, dim=1)[0].detach().cpu().numpy().astype(np.uint8)
            final_np = final_logits[0].detach().cpu().numpy()
            anchor_np = anchor_logits[0].detach().cpu().numpy()
            correction_mask = outputs.get("branch_correction_mask")
            srr_weight = outputs.get("srr_retrieval_weight")
            proposal_weight = outputs.get("proposal_weight")
            refiner_weight = outputs.get("refiner_weight")
            fallback_weight = outputs.get("branch_fallback_weight")
            final_metrics = metric_rows_by_name(collect_case_metrics(variant, case, final_pred))
            anchor_metrics = metric_rows_by_name(collect_case_metrics("A_nnunet_anchor_control", case, anchor_pred))
            for cls, class_name, prefix in [(5, "myops_scar", "scar"), (4, "myops_edema", "edema")]:
                anchor_row = anchor_metrics[class_name]
                final_row = final_metrics[class_name]
                final_cls = final_pred == cls
                anchor_cls = anchor_pred == cls
                proposal = sigmoid(outputs[f"{prefix}_proposal_logits"][0, 0].detach().cpu().numpy()) >= 0.10
                gt_mask = case.label_arr == cls
                recall, precision = proposal_recall_precision(proposal, gt_mask)
                residual = outputs[f"{prefix}_refinement_residual"][0, 0].detach().cpu().numpy()
                anchor_rows.append(
                    {
                        "candidate_id": "A_nnunet_anchor_control",
                        "candidate_type": "same_split_nnunet_anchor_control",
                        "metric_name": class_name,
                        "case_id": case.case_id,
                        "center": case.metadata.center,
                        "modality_group": case.metadata.modality_group,
                        "t2_present": case.metadata.t2_present,
                        "class_id": cls,
                        "dice": anchor_row.get("dice", ""),
                        "hd95": anchor_row.get("hd95", ""),
                        "component_count": anchor_row.get("component_count", ""),
                        "remote_fp_count": anchor_row.get("remote_fp_count", ""),
                        "no_t2_edema_voxels": int(np.count_nonzero(anchor_pred == 4)) if cls == 4 and not case.metadata.t2_present else 0,
                        "derived_from_variant_count": 1,
                        "source_evidence": "broad_eval direct nnU-Net anchor logits",
                    }
                )
                contribution_rows.append(
                    {
                        "variant": variant,
                        "checkpoint": str(checkpoint),
                        "decode_mode": "argmax",
                        "case_id": case.case_id,
                        "center": case.metadata.center,
                        "modality_group": case.metadata.modality_group,
                        "t2_present": case.metadata.t2_present,
                        "class_name": class_name,
                        "anchor_delta_rate": float(np.mean(final_cls != anchor_cls)),
                        "final_delta_rate": float(np.mean(final_pred != anchor_pred)),
                        "correction_gate_open_rate": float(correction_mask.detach().mean().cpu()) if correction_mask is not None else "EVIDENCE_NOT_FOUND",
                        "srr_weight_mean": float(srr_weight.detach().mean().cpu()) if srr_weight is not None else "EVIDENCE_NOT_FOUND",
                        "proposal_weight_mean": float(proposal_weight.detach().mean().cpu()) if proposal_weight is not None else "EVIDENCE_NOT_FOUND",
                        "refiner_weight_mean": float(refiner_weight.detach().mean().cpu()) if refiner_weight is not None else "EVIDENCE_NOT_FOUND",
                        "fallback_weight_mean": float(fallback_weight.detach().mean().cpu()) if fallback_weight is not None else "EVIDENCE_NOT_FOUND",
                        "final_logit_delta_abs_mean": float(np.mean(np.abs(final_np[cls] - anchor_np[cls]))),
                        "roi_delta_abs_mean": float(np.mean(np.abs(residual))),
                        "proposal_recall_proxy": recall,
                        "proposal_precision_proxy": precision,
                        "refiner_delta_magnitude": float(np.mean(np.abs(residual))),
                        "no_t2_edema_voxels": int(np.count_nonzero(final_pred == 4)) if not case.metadata.t2_present else 0,
                        "dice_delta": finite_float(final_row.get("dice")) - finite_float(anchor_row.get("dice")),
                        "hd95_delta": finite_float(final_row.get("hd95")) - finite_float(anchor_row.get("hd95")),
                        "remote_fp_delta": finite_float(final_row.get("remote_fp_count")) - finite_float(anchor_row.get("remote_fp_count")),
                        "component_count_delta": finite_float(final_row.get("component_count")) - finite_float(anchor_row.get("component_count")),
                        "source_prediction_path": str(out_dir / "predictions/fold_0/checkpoint_best/argmax" / f"{case.case_id}.nii.gz"),
                    }
                )
    return contribution_rows, anchor_rows


def normalize_csv_newlines(path: Path) -> None:
    for csv_path in path.rglob("*.csv"):
        data = csv_path.read_bytes()
        normalized = data.replace(b"\r\n", b"\n")
        if normalized != data:
            csv_path.write_bytes(normalized)


def run_variant(packet: Path, variant: str, case_ids: list[str], device: torch.device) -> dict[str, object]:
    source_dir = variant_dir(packet, variant)
    out_dir = broad_variant_dir(packet, variant)
    summary = read_json(source_dir / "summary.json")
    checkpoint = Path(str(summary.get("checkpoint_best") or source_dir / "checkpoints/fold_0/propref_config/checkpoint_best.pt"))
    started = time.time()
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    state = torch.load(checkpoint, map_location=device, weights_only=False)
    args = source_args_from_checkpoint(state, summary)
    metadata = load_myops_case_metadata()
    anchor_root = Path(str(getattr(args, "nnunet_anchor_root", "") or summary.get("nnunet_anchor_root", "")))
    cases = [read_anchored_case(case_id, metadata, anchor_root) for case_id in case_ids]
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    model.load_state_dict(state["model_state_dict"])
    model.eval()
    evaluate(
        model,
        cases,
        out_dir,
        variant,
        device,
        disable_nnunet_anchor=as_bool(getattr(args, "disable_nnunet_anchor", False)),
        checkpoint_name="checkpoint_best",
        proposal_thresholds=parse_thresholds(getattr(args, "proposal_thresholds", DEFAULT_PROPOSAL_THRESHOLDS)),
        scar_decode_threshold=float(getattr(args, "scar_decode_threshold", 0.5)),
        edema_decode_threshold=float(getattr(args, "edema_decode_threshold", 0.5)),
    )
    contribution_rows, anchor_rows = checkpoint_contribution_and_anchor_rows(
        model,
        args,
        cases,
        device,
        variant=variant,
        checkpoint=checkpoint,
        out_dir=out_dir,
    )
    write_csv(out_dir / "srr_contribution_by_case_checkpoint_best.csv", contribution_rows)
    write_csv(out_dir / "anchor_control_metrics_checkpoint_best.csv", anchor_rows)
    normalize_csv_newlines(out_dir)
    elapsed = time.time() - started
    case_summary = [
        {
            "case_id": case.case_id,
            "center": case.metadata.center,
            "modality_group": case.metadata.modality_group,
            "t2_present": bool(case.metadata.t2_present),
            "scar_gt_positive": bool(np.count_nonzero(case.label_arr == 5)),
            "edema_gt_positive": bool(np.count_nonzero(case.label_arr == 4)),
        }
        for case in cases
    ]
    summary_out = {
        "status": "BROAD_EVAL_COMPLETED",
        "variant": variant,
        "source_checkpoint": str(checkpoint),
        "source_summary": str(source_dir / "summary.json"),
        "output_dir": str(out_dir),
        "eval_only": True,
        "training_launched": False,
        "validation_package_created": False,
        "validation_upload_run": False,
        "case_ids": case_ids,
        "case_summary": case_summary,
        "case_count": len(case_summary),
        "t2_present_case_count": sum(1 for row in case_summary if row["t2_present"]),
        "centerB_or_centerC_case_count": sum(1 for row in case_summary if row["center"] in {"CenterB", "CenterC"}),
        "multimodal_case_count": sum(1 for row in case_summary if str(row["modality_group"]).lower() != "lge-only"),
        "edema_gt_positive_case_count": sum(1 for row in case_summary if row["edema_gt_positive"]),
        "scar_gt_positive_case_count": sum(1 for row in case_summary if row["scar_gt_positive"]),
        "runtime_seconds": elapsed,
        "updated_at_utc": datetime.now(UTC).isoformat(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(json.dumps(summary_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary_out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", default=str(DEFAULT_PACKET))
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--max-cases", type=int, default=12)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--variant", action="append", choices=VARIANTS, default=[])
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--list-cases-only", action="store_true")
    args = parser.parse_args()
    packet = Path(args.packet)
    if not packet.is_absolute():
        packet = REPO_ROOT / packet
    case_ids = select_broad_case_ids(packet, args.fold, args.max_cases, args.case_id)
    if args.list_cases_only:
        print(json.dumps({"packet": str(packet), "selected_case_ids": case_ids}, indent=2))
        return
    device = torch.device(args.device if args.device == "cpu" or torch.cuda.is_available() else "cpu")
    variants = args.variant or VARIANTS
    summaries = [run_variant(packet, variant, case_ids, device) for variant in variants]
    print(json.dumps({"packet": str(packet), "device": str(device), "case_ids": case_ids, "variant_summaries": summaries}, indent=2))


if __name__ == "__main__":
    main()
