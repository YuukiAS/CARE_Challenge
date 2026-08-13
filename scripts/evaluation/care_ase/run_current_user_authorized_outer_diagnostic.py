#!/usr/bin/env python
"""Run user-authorized CARE-ASE outer diagnostic comparisons for current training.

This intentionally mirrors the old ASE R2 diagnostic comparison path that was
used after explicit user override, but parameterizes the current formal
training result root and folds 2/3.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import statistics
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
from scipy import ndimage

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.inference.care_ase_r2_full_volume import (
    CAREASEFullVolumeInferenceSettings,
    predict_care_ase_r2_full_volume_logits,
)
from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_inference


TASK_KEY = "care-ase-faithful-formal-training-20260812"
RESULT_ROOT = REPO_ROOT / "results/agent_flow_v3" / TASK_KEY
DATA_REPO_ROOT = Path(os.environ.get("CARE_DATA_REPO_ROOT", REPO_ROOT)).resolve()
PREPROCESSED = DATA_REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
STOCK_ROOT = DATA_REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
SPLITS = DATA_REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def dice_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float:
    p = pred == cls
    g = gt == cls
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum() / denom)


def sensitivity_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    g = gt == cls
    total = int(g.sum())
    if total == 0:
        return None
    return float(np.logical_and(pred == cls, g).sum() / total)


def precision_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    p = pred == cls
    total = int(p.sum())
    if total == 0:
        return None
    return float(np.logical_and(p, gt == cls).sum() / total)


def volume_ratio_for_class(pred: np.ndarray, gt: np.ndarray, cls: int) -> float | None:
    gt_count = int((gt == cls).sum())
    if gt_count == 0:
        return None
    return float(int((pred == cls).sum()) / gt_count)


def hd95_for_class(pred: np.ndarray, gt: np.ndarray, cls: int, spacing: tuple[float, float, float]) -> float:
    p = pred == cls
    g = gt == cls
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return 1.0e6
    p_border = p ^ ndimage.binary_erosion(p)
    g_border = g ^ ndimage.binary_erosion(g)
    values = np.concatenate(
        [
            ndimage.distance_transform_edt(~g_border, sampling=spacing)[p_border],
            ndimage.distance_transform_edt(~p_border, sampling=spacing)[g_border],
        ]
    )
    return float(np.percentile(values, 95)) if values.size else 0.0


def mean(values: list[Any]) -> float | None:
    clean = [float(v) for v in values if v not in ("", None)]
    return statistics.fmean(clean) if clean else None


def restricted_argmax(logits: torch.Tensor, allowed_classes: tuple[int, ...]) -> np.ndarray:
    allowed = torch.as_tensor(allowed_classes, device=logits.device, dtype=torch.long)
    local = torch.argmax(logits.index_select(0, allowed).float(), dim=0)
    return allowed[local].detach().cpu().numpy().astype(np.uint8)


def runtime_dir_for_fold(fold: int) -> Path:
    if fold == 2:
        return RESULT_ROOT / "runtime/fold_2"
    if fold == 3:
        return RESULT_ROOT / "runtime/fold_3_parallel"
    raise ValueError(f"unsupported current formal-training fold: {fold}")


def latest_verified_step(fold: int) -> int:
    steps: list[int] = []
    for path in runtime_dir_for_fold(fold).glob("checkpoint_step*.pt.verified.json"):
        stem = path.name.split(".pt.verified.json")[0]
        steps.append(int(stem.replace("checkpoint_step", "")))
    if not steps:
        raise FileNotFoundError(f"no verified checkpoints for fold{fold}: {runtime_dir_for_fold(fold)}")
    return max(steps)


def checkpoint_for(fold: int, step: int) -> Path:
    ckpt = runtime_dir_for_fold(fold) / f"checkpoint_step{step:05d}.pt"
    verified = ckpt.with_suffix(ckpt.suffix + ".verified.json")
    if not ckpt.is_file():
        raise FileNotFoundError(f"missing checkpoint: {ckpt}")
    if not verified.is_file():
        raise FileNotFoundError(f"missing verified checkpoint receipt: {verified}")
    return ckpt


def run_fold(fold: int, step: int, *, force: bool, decision: str, output_suffix: str) -> dict[str, Any]:
    ckpt = checkpoint_for(fold, step)
    step_dir = f"step{step:05d}{output_suffix}"
    out_dir = RESULT_ROOT / "outer_diagnostic_user_authorized" / f"fold_{fold}" / step_dir
    summary_path = out_dir / "outer_diagnostic_summary.json"
    if summary_path.is_file() and not force:
        return json.loads(summary_path.read_text(encoding="utf-8"))

    out_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, payload = load_care_ase_checkpoint_for_inference(ckpt, map_location=device)
    model.to(device).eval()
    if int(payload.get("global_optimizer_step", -1)) != int(step):
        raise RuntimeError(f"checkpoint step mismatch: payload={payload.get('global_optimizer_step')} cli={step}")

    settings = CAREASEFullVolumeInferenceSettings(
        patch_size=(20, 256, 256),
        tile_step_size=0.5,
        use_gaussian=True,
        gaussian_sigma_scale=1.0 / 8.0,
        use_mirroring=True,
        allowed_mirror_axes=(0, 1, 2),
        precision="fp32",
    )
    stock = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=True,
        perform_everything_on_device=device.type == "cuda",
        device=device,
        verbose=False,
        allow_tqdm=False,
    )
    stock.initialize_from_trained_model_folder(
        str(STOCK_ROOT),
        use_folds=(int(fold),),
        checkpoint_name="checkpoint_final.pth",
    )
    cases = [str(case_id) for case_id in json.loads(SPLITS.read_text(encoding="utf-8"))[int(fold)]["val"]]
    metadata = load_myops_case_metadata(DATA_REPO_ROOT)
    rows: list[dict[str, Any]] = []
    for case_id in cases:
        image_np = read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False)
        seg = read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
        spacing = (1.0, 1.0, 1.0)
        pkl = PREPROCESSED / f"{case_id}.pkl"
        if pkl.is_file():
            with pkl.open("rb") as f:
                spacing = tuple(float(v) for v in pickle.load(f).get("spacing", spacing))
        image = torch.from_numpy(image_np[None]).to(device=device, dtype=torch.float32)
        availability = torch.tensor([metadata[case_id].availability], device=device, dtype=torch.float32)
        with torch.no_grad():
            care_logits = predict_care_ase_r2_full_volume_logits(
                model,
                image,
                availability,
                settings=settings,
                global_step=int(step),
            )
            care_pred = decode_care_ase_r2_logits(care_logits, availability).cpu().numpy().astype(np.uint8)[0]
            stock_logits = stock.predict_logits_from_preprocessed_data(
                torch.from_numpy(image_np).to(device=device, dtype=torch.float32)
            )
            stock_pred = torch.argmax(stock_logits.float(), dim=0).cpu().numpy().astype(np.uint8)
            stock_pred_no_t2_matched = restricted_argmax(stock_logits, (0, 1, 2, 3, 5))
        t2_present = bool(metadata[case_id].t2_present)
        row: dict[str, Any] = {
            "case_id": case_id,
            "fold": int(fold),
            "role": "outer",
            "t2_present": t2_present,
            "center": metadata[case_id].center,
            "modality_group": metadata[case_id].modality_group,
            "availability": "".join("1" if flag else "0" for flag in metadata[case_id].availability),
            "care_scar_dice": dice_for_class(care_pred, seg, 5),
            "nnunet_scar_dice": dice_for_class(stock_pred, seg, 5),
            "nnunet_no_t2_matched_scar_dice": "" if t2_present else dice_for_class(stock_pred_no_t2_matched, seg, 5),
            "care_scar_hd95": hd95_for_class(care_pred, seg, 5, spacing),
            "nnunet_scar_hd95": hd95_for_class(stock_pred, seg, 5, spacing),
            "nnunet_no_t2_matched_scar_hd95": "" if t2_present else hd95_for_class(stock_pred_no_t2_matched, seg, 5, spacing),
            "care_scar_sensitivity": sensitivity_for_class(care_pred, seg, 5),
            "nnunet_scar_sensitivity": sensitivity_for_class(stock_pred, seg, 5),
            "nnunet_no_t2_matched_scar_sensitivity": ""
            if t2_present
            else sensitivity_for_class(stock_pred_no_t2_matched, seg, 5),
            "care_scar_precision": precision_for_class(care_pred, seg, 5),
            "nnunet_scar_precision": precision_for_class(stock_pred, seg, 5),
            "nnunet_no_t2_matched_scar_precision": "" if t2_present else precision_for_class(stock_pred_no_t2_matched, seg, 5),
            "care_scar_volume_ratio": volume_ratio_for_class(care_pred, seg, 5),
            "nnunet_scar_volume_ratio": volume_ratio_for_class(stock_pred, seg, 5),
            "nnunet_no_t2_matched_scar_volume_ratio": ""
            if t2_present
            else volume_ratio_for_class(stock_pred_no_t2_matched, seg, 5),
        }
        if t2_present:
            row.update(
                {
                    "care_pure_edema_dice": dice_for_class(care_pred, seg, 4),
                    "nnunet_pure_edema_dice": dice_for_class(stock_pred, seg, 4),
                    "care_pure_edema_hd95": hd95_for_class(care_pred, seg, 4, spacing),
                    "nnunet_pure_edema_hd95": hd95_for_class(stock_pred, seg, 4, spacing),
                    "care_pure_edema_sensitivity": sensitivity_for_class(care_pred, seg, 4),
                    "nnunet_pure_edema_sensitivity": sensitivity_for_class(stock_pred, seg, 4),
                    "care_pure_edema_precision": precision_for_class(care_pred, seg, 4),
                    "nnunet_pure_edema_precision": precision_for_class(stock_pred, seg, 4),
                    "care_pure_edema_volume_ratio": volume_ratio_for_class(care_pred, seg, 4),
                    "nnunet_pure_edema_volume_ratio": volume_ratio_for_class(stock_pred, seg, 4),
                }
            )
        else:
            row.update(
                {
                    "care_pure_edema_dice": "",
                    "nnunet_pure_edema_dice": "",
                    "care_pure_edema_hd95": "",
                    "nnunet_pure_edema_hd95": "",
                    "care_pure_edema_sensitivity": "",
                    "nnunet_pure_edema_sensitivity": "",
                    "care_pure_edema_precision": "",
                    "nnunet_pure_edema_precision": "",
                    "care_pure_edema_volume_ratio": "",
                    "nnunet_pure_edema_volume_ratio": "",
                }
            )
        rows.append(row)

    casewise_path = out_dir / "outer_casewise_metrics.csv"
    with casewise_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "care_scar_mean": mean([row["care_scar_dice"] for row in rows]),
        "nnunet_scar_mean": mean([row["nnunet_scar_dice"] for row in rows]),
        "care_pure_edema_mean": mean([row["care_pure_edema_dice"] for row in rows]),
        "nnunet_pure_edema_mean": mean([row["nnunet_pure_edema_dice"] for row in rows]),
    }
    summary["care_minus_nnunet_scar_mean"] = summary["care_scar_mean"] - summary["nnunet_scar_mean"]
    summary["care_minus_nnunet_pure_edema_mean"] = summary["care_pure_edema_mean"] - summary["nnunet_pure_edema_mean"]
    stock_checkpoint = STOCK_ROOT / f"fold_{int(fold)}" / "checkpoint_final.pth"
    packet = {
        "status": "PASS",
        "decision": decision,
        "comparison_contract": "USER_AUTHORIZED_OUTER_DIAGNOSTIC_OLD_ASE_LOGIC",
        "fold": int(fold),
        "checkpoint_step": int(step),
        "case_count": len(rows),
        "edema_t2_case_count": sum(1 for row in rows if row["t2_present"]),
        "data_repo_root": str(DATA_REPO_ROOT),
        "checkpoint": str(ckpt.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(ckpt),
        "stock_checkpoint": str(stock_checkpoint),
        "stock_checkpoint_sha256": sha256_file(stock_checkpoint),
        "inference_settings": settings.to_json_dict(),
        "decode_asymmetry_audit": {
            "care_no_t2_decode_classes": [0, 1, 2, 3, 5],
            "original_nnunet_baseline_decode": "direct_six_class_argmax",
            "diagnostic_nnunet_no_t2_matched_columns": "nnunet_no_t2_matched_scar_* for no-T2 rows only; diagnostic-only, not checkpoint selection",
        },
        "casewise_csv": str(casewise_path.relative_to(REPO_ROOT)),
        "casewise_csv_sha256": sha256_file(casewise_path),
        "summary": summary,
    }
    summary_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return packet


def combine(packets: list[dict[str, Any]], *, decision: str) -> dict[str, Any]:
    case_total = sum(int(packet["case_count"]) for packet in packets)
    edema_total = sum(int(packet["edema_t2_case_count"]) for packet in packets)

    def weighted_mean(key: str, *, edema: bool = False) -> float:
        total = edema_total if edema else case_total
        if total <= 0:
            return float("nan")
        numerator = 0.0
        for packet in packets:
            n = int(packet["edema_t2_case_count"] if edema else packet["case_count"])
            numerator += float(packet["summary"][key]) * n
        return numerator / total

    care_scar = weighted_mean("care_scar_mean")
    nnunet_scar = weighted_mean("nnunet_scar_mean")
    care_edema = weighted_mean("care_pure_edema_mean", edema=True)
    nnunet_edema = weighted_mean("nnunet_pure_edema_mean", edema=True)
    return {
        "status": "PASS",
        "decision": decision,
        "comparison_contract": "USER_AUTHORIZED_OUTER_DIAGNOSTIC_OLD_ASE_LOGIC",
        "outer_access_authorization": "explicit_user_authorized_in_chat_2026-08-13",
        "fold_steps": {f"fold_{packet['fold']}": int(packet["checkpoint_step"]) for packet in packets},
        "case_count_total": case_total,
        "edema_t2_case_count_total": edema_total,
        "folds": packets,
        "scar": {
            "care_mean": care_scar,
            "nnunet_mean": nnunet_scar,
            "delta_care_minus_nnunet": care_scar - nnunet_scar,
        },
        "pure_edema": {
            "care_mean": care_edema,
            "nnunet_mean": nnunet_edema,
            "delta_care_minus_nnunet": care_edema - nnunet_edema,
        },
        "invalidated_prior_reporting": {
            "same_exposure_or_inner_in_sample_0_9_tables": "diagnostic_only_not_primary_fair_comparison",
            "reason": "old ASE thread established that inner/same-exposure panels inherited stock in-sample exposure and overstate held-out performance",
        },
        "decode_asymmetry_audit": {
            "care_no_t2_decode_classes": [0, 1, 2, 3, 5],
            "original_nnunet_baseline_decode": "direct_six_class_argmax",
            "diagnostic_nnunet_no_t2_matched_baseline": "available only when the casewise CSV was generated after this audit patch; diagnostic-only and must not replace the original outer headline",
        },
    }


def parse_fold_steps(values: list[str]) -> dict[int, int]:
    fold_steps: dict[int, int] = {}
    for value in values:
        fold_s, step_s = value.split(":", 1)
        fold_steps[int(fold_s)] = int(step_s)
    return fold_steps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold-step", action="append", default=[], help="fold:step, for example 2:5000")
    parser.add_argument("--latest", action="store_true", help="evaluate latest verified checkpoint for folds 2 and 3")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--output-name", default="outer_diagnostic_latest_combined_summary.json")
    parser.add_argument("--diagnostic-output-suffix", default="", help="append to per-fold step directory, for non-overwriting diagnostic reruns")
    args = parser.parse_args()
    output_suffix = str(args.diagnostic_output_suffix)
    if output_suffix and not output_suffix.startswith("_"):
        output_suffix = "_" + output_suffix
    if args.latest:
        fold_steps = {2: latest_verified_step(2), 3: latest_verified_step(3)}
    else:
        fold_steps = parse_fold_steps(args.fold_step)
    if sorted(fold_steps) != [2, 3]:
        raise RuntimeError(f"current outer diagnostic requires fold2 and fold3, got {sorted(fold_steps)}")
    decision = "USER_AUTHORIZED_CURRENT_OUTER_DIAGNOSTIC"
    packets = [run_fold(fold, step, force=args.force, decision=decision, output_suffix=output_suffix) for fold, step in sorted(fold_steps.items())]
    packet = combine(packets, decision=decision)
    out = RESULT_ROOT / "outer_diagnostic_user_authorized" / args.output_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
