#!/usr/bin/env python3
"""5-fold eval with V4 pipeline.

MyoPS: coarse + scar FinePathNet + dedicated EdemaNet
CineMyoPS: coarse + CineHybridNet V2
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import torch
from scipy.ndimage import binary_dilation

from myops.config import load_config
from myops.data.labels import (
    TRACK_MYOPS, TRACK_CINE, EDEMA_CENTERS,
    num_classes, modalities_for_track, train_label_map_for_track,
    default_thresholds,
)
from myops.data.preprocessing import cache_path
from myops.data.splits import split_records_by_fold, filter_records
from myops.inference.predict import predict_case_coarse, predict_case_fine
from myops.inference.postprocess import (
    largest_component, enforce_pathology_inside_myo, clean_prediction_by_class,
)
from myops.inference.edema_predict import (
    load_edema_model, predict_edema_case_probs, merge_labels,
)
from myops.models import build_model
from myops.utils.io import read_jsonl, torch_load

ROOT = Path(__file__).resolve().parent.parent
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}


def dice(pred: np.ndarray, gt: np.ndarray) -> float:
    i = int((pred & gt).sum())
    t = int(pred.sum()) + int(gt.sum())
    return float(2 * i / (t + 1e-8)) if t > 0 else (1.0 if i == 0 else 0.0)


def load_myops_fold_models(fold_dir: Path, device: torch.device):
    coarse_cfg = load_config(str(ROOT / "configs" / "myops_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))

    coarse_model = build_model(
        stage="coarse", track=TRACK_MYOPS, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    ckpt = torch.load(str(fold_dir / "coarse" / "best.pt"), map_location="cpu", weights_only=False)
    coarse_model.load_state_dict(ckpt["model_state"])
    coarse_model = coarse_model.to(device).eval()

    scar_cfg = load_config(str(ROOT / "configs" / "myops_fine.yaml"))
    scar_model = build_model(
        stage="fine", track=TRACK_MYOPS, arch="2d_multi",
        in_channels=n_mod * 2 + 1, out_channels=num_classes(TRACK_MYOPS, "fine"),
        base_channels=int(scar_cfg["model"].get("base_channels", 24)),
        deep_supervision=bool(scar_cfg["model"].get("deep_supervision", True)),
        grid_size=int(scar_cfg["model"].get("grid_size", 4)),
        span_range=float(scar_cfg["model"].get("span_range", 0.98)),
        image_size=192,
        use_tps=bool(scar_cfg["model"].get("use_tps", True)),
        use_spg=bool(scar_cfg["model"].get("use_spg", True)),
        use_consistency=bool(scar_cfg["model"].get("use_consistency", True)),
    )
    scar_ckpt = fold_dir / "fine" / "best_scar.pt"
    if not scar_ckpt.exists():
        scar_ckpt = fold_dir / "fine" / "best.pt"
    ckpt = torch.load(str(scar_ckpt), map_location="cpu", weights_only=False)
    scar_model.load_state_dict(ckpt["model_state"], strict=False)
    scar_model = scar_model.to(device).eval()

    # Dedicated EdemaNet (NOT channel-swapped FinePathNet)
    edema_ckpt = fold_dir / "edema" / "best.pt"
    if not edema_ckpt.exists():
        edema_ckpt = fold_dir / "edema" / "last.pt"
    edema_model = load_edema_model(str(edema_ckpt), device)

    return coarse_model, scar_model, edema_model


def eval_myops_fold_v4(fold: int, fold_dir: Path, val_records: list,
                       cache_root: str, device: torch.device):
    coarse_model, scar_model, edema_model = load_myops_fold_models(fold_dir, device)
    label_map = train_label_map_for_track(TRACK_MYOPS, "fine")
    ucf_thresholds = default_thresholds(TRACK_MYOPS, "fine")

    all_metrics = []
    for i, rec in enumerate(val_records):
        case_id = rec["case_id"]
        payload = torch_load(cache_path(cache_root, TRACK_MYOPS, case_id))

        with torch.no_grad():
            coarse_result = predict_case_coarse(
                coarse_model, payload, TRACK_MYOPS, device,
                image_size=[192, 192], tta_config=TTA,
            )
            coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)

            ucf_result = predict_case_fine(
                scar_model, payload, TRACK_MYOPS, device,
                coarse_prior=coarse_prior, image_size=[192, 192],
                tta_config=TTA,
            )
            ucf_probs = np.asarray(ucf_result["probs"], dtype=np.float32)

            # EdemaNet: get edema probability map
            edema_prob = predict_edema_case_probs(
                edema_model, payload, coarse_prior, device, dim=192,
            )

        # Scar from UCF
        ucf_label = np.zeros(ucf_probs.shape[1:], dtype=np.int16)
        for c in range(ucf_probs.shape[0]):
            ucf_label[ucf_probs[c] > ucf_thresholds[c]] = c + 1

        myo_mask = binary_dilation(coarse_prior > 0, iterations=1)
        ucf_label = enforce_pathology_inside_myo(
            ucf_label, 1, [4, 5], external_myo_mask=myo_mask,
        )
        ucf_label = clean_prediction_by_class(ucf_label, {4: 5, 5: 3})

        # Edema from EdemaNet
        edema_zone = edema_prob > 0.35
        if edema_zone.any():
            edema_zone = largest_component(edema_zone)
        edema_zone = edema_zone & myo_mask

        # Merge using edema_predict.merge_labels
        final_label = merge_labels(ucf_label, coarse_prior, edema_zone)

        # Final cleanup
        final_label = clean_prediction_by_class(final_label, {4: 5, 5: 3})
        scar_mask = (final_label == 5)
        if scar_mask.any():
            final_label[scar_mask & ~largest_component(scar_mask)] = 0

        gt = np.asarray(payload["fine_label"], dtype=np.int16)
        m = {}
        for name, tid in label_map.items():
            m[f"{name}_dice"] = dice(final_label == tid, gt == tid)
        lu_p = (final_label == 4) | (final_label == 5)
        lu_g = (gt == 4) | (gt == 5)
        m["lesion_union_dice"] = dice(lu_p, lu_g)
        m["mean_dice"] = float(np.mean([m[f"{n}_dice"] for n in label_map]))
        all_metrics.append(m)
        print(f"    {case_id}: scar={m['scar_dice']:.4f} edema={m['edema_dice']:.4f}")

    del coarse_model, scar_model, edema_model
    torch.cuda.empty_cache()

    avg = {k: float(np.mean([m[k] for m in all_metrics])) for k in all_metrics[0]}
    return avg


def load_cine_fold_models(fold_dir: Path, device: torch.device):
    coarse_cfg = load_config(str(ROOT / "configs" / "cine_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_CINE))

    coarse_model = build_model(
        stage="coarse", track=TRACK_CINE, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_CINE, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    ckpt = torch.load(str(fold_dir / "coarse" / "best.pt"), map_location="cpu", weights_only=False)
    coarse_model.load_state_dict(ckpt["model_state"])
    coarse_model = coarse_model.to(device).eval()

    fine_cfg = load_config(str(ROOT / "configs" / "cine_fine.yaml"))
    base_ch = int(fine_cfg["model"].get("base_channels", 16))
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))
    out_ch = num_classes(TRACK_CINE, "fine")

    fine_model = build_model(
        stage="fine", track=TRACK_CINE, arch="cine_hybrid",
        in_channels=num_frames + 1, out_channels=out_ch,
        base_channels=base_ch, deep_supervision=False,
        num_frames=num_frames,
        max_displacement=float(fine_cfg["model"].get("max_displacement", 0.25)),
    )
    # fine_v2 (z-spacing augmentation)
    fine_dir = fold_dir / "fine_v2"
    for ckpt_name in ["best_cine_scar.pt", "best.pt", "last.pt"]:
        fine_ckpt = fine_dir / ckpt_name
        if fine_ckpt.exists():
            break
    ckpt = torch.load(str(fine_ckpt), map_location="cpu", weights_only=False)
    fine_model.load_state_dict(ckpt["model_state"], strict=False)
    fine_model = fine_model.to(device).eval()

    return coarse_model, fine_model, fine_cfg


def eval_cine_fold_v4(fold: int, fold_dir: Path, val_records: list,
                      cache_root: str, device: torch.device):
    coarse_model, fine_model, fine_cfg = load_cine_fold_models(fold_dir, device)
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))

    scar_dices, myo_dices, lv_dices = [], [], []
    for i, rec in enumerate(val_records):
        case_id = rec["case_id"]
        payload = torch_load(cache_path(cache_root, TRACK_CINE, case_id))

        with torch.no_grad():
            coarse_result = predict_case_coarse(
                coarse_model, payload, TRACK_CINE, device,
                image_size=[192, 192], tta_config=TTA,
            )
            coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)

            fine_result = predict_case_fine(
                fine_model, payload, TRACK_CINE, device,
                coarse_prior=coarse_prior, image_size=[192, 192],
                crop_margin=[1, 18, 18],
                use_cine_sequence=True, cine_frame_count=num_frames,
                tta_config=TTA,
            )
            pred = np.asarray(fine_result["label"], dtype=np.int16)

        myo_mask = binary_dilation(coarse_prior > 0, iterations=1)
        pred = enforce_pathology_inside_myo(pred, 1, [3], external_myo_mask=myo_mask)
        scar_mask = (pred == 3)
        if scar_mask.any():
            pred[scar_mask & ~largest_component(scar_mask)] = 0
        pred = clean_prediction_by_class(pred, {3: 5})

        gt = np.asarray(payload["fine_label"], dtype=np.int16)
        sd = dice(pred == 3, gt == 3)
        md = dice(pred == 1, gt == 1)
        ld = dice(pred == 2, gt == 2)
        scar_dices.append(sd)
        myo_dices.append(md)
        lv_dices.append(ld)
        print(f"    {case_id}: scar={sd:.4f} myo={md:.4f} lv={ld:.4f}")

    del coarse_model, fine_model
    torch.cuda.empty_cache()

    return {
        "scar_dice": float(np.mean(scar_dices)),
        "myo_dice": float(np.mean(myo_dices)),
        "lv_dice": float(np.mean(lv_dices)),
        "mean_dice": float(np.mean([np.mean(myo_dices), np.mean(lv_dices), np.mean(scar_dices)])),
    }


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cache_root = str(ROOT / "cache")
    myops_manifest = str(ROOT / "cache" / "manifest.jsonl")
    cine_manifest = str(ROOT / "cache" / "cine_manifest.jsonl")

    print("=" * 70)
    print("  MyoPS 5-Fold V4 (B+C only, dedicated EdemaNet)")
    print("=" * 70)

    myops_records = filter_records(read_jsonl(myops_manifest), TRACK_MYOPS)
    edema_records = [r for r in myops_records if r.get("center") in EDEMA_CENTERS]

    myops_fold_results = {}
    for fold in range(5):
        fold_dir = ROOT / "grid_output" / "5fold" / f"fold{fold}"
        _, val_recs = split_records_by_fold(edema_records, fold)
        print(f"\n--- Fold {fold} ({len(val_recs)} B+C val cases) ---")
        avg = eval_myops_fold_v4(fold, fold_dir, val_recs, cache_root, device)
        myops_fold_results[fold] = avg
        print(f"  -> scar={avg['scar_dice']:.4f} edema={avg['edema_dice']:.4f}")

    print("\n" + "=" * 70)
    print("  CineMyoPS 5-Fold V4 (V2 only)")
    print("=" * 70)

    cine_records = filter_records(read_jsonl(cine_manifest), TRACK_CINE)

    cine_fold_results = {}
    for fold in range(5):
        fold_dir = ROOT / "grid_output_cine" / "5fold" / f"fold{fold}"
        _, val_recs = split_records_by_fold(cine_records, fold)
        print(f"\n--- Fold {fold} ({len(val_recs)} val cases) ---")
        avg = eval_cine_fold_v4(fold, fold_dir, val_recs, cache_root, device)
        cine_fold_results[fold] = avg
        print(f"  -> scar={avg['scar_dice']:.4f} myo={avg['myo_dice']:.4f}")

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY: MyoPS (B+C)")
    print("=" * 70)
    for fold in range(5):
        m = myops_fold_results[fold]
        print(f"  Fold {fold}: scar={m['scar_dice']:.4f} edema={m['edema_dice']:.4f} mean={m['mean_dice']:.4f}")
    myops_avg = {k: float(np.mean([myops_fold_results[f][k] for f in range(5)])) for k in myops_fold_results[0]}
    print(f"  AVG:    scar={myops_avg['scar_dice']:.4f} edema={myops_avg['edema_dice']:.4f} mean={myops_avg['mean_dice']:.4f}")

    print(f"\n  SUMMARY: CineMyoPS")
    for fold in range(5):
        m = cine_fold_results[fold]
        print(f"  Fold {fold}: scar={m['scar_dice']:.4f} myo={m['myo_dice']:.4f} lv={m['lv_dice']:.4f}")
    cine_avg = {k: float(np.mean([cine_fold_results[f][k] for f in range(5)])) for k in cine_fold_results[0]}
    print(f"  AVG:    scar={cine_avg['scar_dice']:.4f} myo={cine_avg['myo_dice']:.4f} lv={cine_avg['lv_dice']:.4f}")

    results = {
        "myops_fold_results": {str(k): v for k, v in myops_fold_results.items()},
        "myops_average": myops_avg,
        "cine_fold_results": {str(k): v for k, v in cine_fold_results.items()},
        "cine_average": cine_avg,
    }
    out_path = ROOT / "grid_output" / "5fold" / "v4_eval_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
