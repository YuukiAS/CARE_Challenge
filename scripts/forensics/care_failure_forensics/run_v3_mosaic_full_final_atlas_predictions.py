#!/usr/bin/env python3
"""Generate bound MoSAIC full/final voxel predictions for V3 atlas cases."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import binary_dilation, zoom


CARE_ROOT = Path("/users/a/e/aereinh/CARE")
MOSAIC_SOURCE = Path("/users/a/e/aereinh/MoSAIC/code/source")
MOSAIC_WEIGHTS = Path("/users/a/e/aereinh/MoSAIC/code/weights/myops")
RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")

if str(MOSAIC_SOURCE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_SOURCE))

from myops.config import load_config  # noqa: E402
from myops.data.labels import TRACK_MYOPS, default_thresholds, modalities_for_track, num_classes, train_to_official_labels  # noqa: E402
from myops.data.preprocessing import cache_path, preprocess_myops_case  # noqa: E402
from myops.inference.edema_predict import load_edema_model, merge_labels, predict_edema_case_probs  # noqa: E402
from myops.inference.postprocess import clean_prediction_by_class, enforce_pathology_inside_myo, largest_component  # noqa: E402
from myops.inference.predict import predict_case_coarse, predict_case_fine  # noqa: E402
from myops.models import build_model  # noqa: E402
from myops.utils.io import torch_load  # noqa: E402


TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def zoom_factors(current_zhw: tuple[int, int, int], payload: dict[str, Any]) -> tuple[list[int], list[float]] | None:
    original_shape = payload.get("original_shape")
    if original_shape is None:
        return None
    orig_hwz = list(original_shape)[:3]
    cur_hwz = [current_zhw[1], current_zhw[2], current_zhw[0]]
    if cur_hwz == orig_hwz:
        return None
    return orig_hwz, [o / c for o, c in zip(orig_hwz, cur_hwz)]


def probs_to_original_space(probs_zhw: np.ndarray, payload: dict[str, Any]) -> np.ndarray:
    channels = probs_zhw.shape[0]
    probs_hwz = np.transpose(probs_zhw, (0, 2, 3, 1))
    info = zoom_factors(tuple(probs_zhw.shape[1:]), payload)
    if info is None:
        return probs_hwz
    orig_hwz, factors = info
    out = np.zeros([channels] + orig_hwz, dtype=np.float32)
    for channel in range(channels):
        out[channel] = zoom(probs_hwz[channel], factors, order=1)
    return out


def label_to_original_space(label_zhw: np.ndarray, payload: dict[str, Any]) -> np.ndarray:
    label_hwz = np.transpose(label_zhw, (1, 2, 0))
    info = zoom_factors(tuple(label_zhw.shape), payload)
    if info is None:
        return label_hwz
    _orig_hwz, factors = info
    return zoom(label_hwz.astype(np.float32), factors, order=0).astype(np.int16)


def record_for_case(root: Path, row: dict[str, str]) -> dict[str, Any]:
    case_id = row["case_id"]
    center = row["center"]
    case_dir = root / "data/CARE_Challenge/MyoPS_train" / center / case_id
    image_paths: dict[str, str] = {}
    modalities: list[str] = []
    for modality in ["LGE", "C0", "T2"]:
        path = case_dir / f"{case_id}_{modality}.nii.gz"
        if path.exists():
            image_paths[modality] = str(path)
            modalities.append(modality)
    label_path = case_dir / f"{case_id}_gd.nii.gz"
    center_index = max(ord(center[-1]) - ord("A"), 0) if center.startswith("Center") and center[-1:].isalpha() else -1
    return {
        "track": "myops",
        "case_id": case_id,
        "center": center,
        "image_paths": image_paths,
        "label_path": str(label_path) if label_path.exists() else None,
        "available_modalities": modalities,
        "modality_presence_mask": [1.0 if m in modalities else 0.0 for m in ["LGE", "C0", "T2"]],
        "coarse_supervision_mask": [1.0, 1.0, 1.0],
        "fine_supervision_mask": [1.0, 1.0, 1.0, 1.0 if "T2" in modalities else 0.0, 1.0],
        "center_domain_id": center_index,
    }


def build_coarse(device: torch.device, checkpoint_name: str, coarse_cfg: dict[str, Any], n_mod: int) -> torch.nn.Module:
    model = build_model(
        stage="coarse",
        track=TRACK_MYOPS,
        arch="2d_coarse",
        in_channels=n_mod * 2,
        out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    ckpt = torch.load(str(MOSAIC_WEIGHTS / checkpoint_name), map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    return model.to(device).eval()


def load_models(device: torch.device) -> tuple[torch.nn.Module, torch.nn.Module, torch.nn.Module, torch.nn.Module]:
    coarse_cfg = load_config(str(MOSAIC_SOURCE / "configs/myops_coarse.yaml"))
    fine_cfg = load_config(str(MOSAIC_SOURCE / "configs/myops_fine.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))
    coarse = build_coarse(device, "coarse.pt", coarse_cfg, n_mod)
    coarse_edema = build_coarse(device, "coarse_edema.pt", coarse_cfg, n_mod)
    scar = build_model(
        stage="fine",
        track=TRACK_MYOPS,
        arch="2d_multi",
        in_channels=n_mod * 2 + 1,
        out_channels=num_classes(TRACK_MYOPS, "fine"),
        base_channels=int(fine_cfg["model"].get("base_channels", 24)),
        deep_supervision=bool(fine_cfg["model"].get("deep_supervision", True)),
        grid_size=int(fine_cfg["model"].get("grid_size", 4)),
        span_range=float(fine_cfg["model"].get("span_range", 0.98)),
        image_size=192,
        use_tps=bool(fine_cfg["model"].get("use_tps", True)),
        use_spg=bool(fine_cfg["model"].get("use_spg", True)),
        use_consistency=bool(fine_cfg["model"].get("use_consistency", True)),
    )
    scar_ckpt = torch.load(str(MOSAIC_WEIGHTS / "fine_scar.pt"), map_location="cpu", weights_only=False)
    scar.load_state_dict(scar_ckpt["model_state"], strict=False)
    edema = load_edema_model(str(MOSAIC_WEIGHTS / "edema.pt"), device)
    return coarse, coarse_edema, scar.to(device).eval(), edema.eval()


def predict_case(
    payload: dict[str, Any],
    coarse: torch.nn.Module,
    coarse_edema: torch.nn.Module,
    scar: torch.nn.Module,
    edema: torch.nn.Module,
    device: torch.device,
) -> np.ndarray:
    with torch.no_grad():
        coarse_result = predict_case_coarse(coarse, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=TTA)
        coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)
        scar_result = predict_case_fine(scar, payload, TRACK_MYOPS, device, coarse_prior=coarse_prior, image_size=[192, 192], tta_config=TTA)
        scar_probs = np.asarray(scar_result["probs"], dtype=np.float32)
        coarse_old_result = predict_case_coarse(coarse_edema, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=TTA)
        coarse_prior_old = np.asarray(coarse_old_result["label"], dtype=np.int16)
        edema_prob = predict_edema_case_probs(edema, payload, coarse_prior_old, device, dim=192)

    scar_probs_orig = probs_to_original_space(scar_probs, payload)
    edema_prob_orig = probs_to_original_space(edema_prob[None], payload)[0]
    scar_label_orig = np.zeros(scar_probs_orig.shape[1:], dtype=np.int16)
    for channel in range(scar_probs_orig.shape[0]):
        scar_label_orig[scar_probs_orig[channel] > default_thresholds(TRACK_MYOPS, "fine")[channel]] = channel + 1
    coarse_orig = label_to_original_space(coarse_prior, payload)
    coarse_old_orig = label_to_original_space(coarse_prior_old, payload)
    myo_mask = binary_dilation(coarse_orig > 0, iterations=1)
    myo_mask_edema = binary_dilation(coarse_old_orig > 0, iterations=1)
    scar_label_orig = enforce_pathology_inside_myo(scar_label_orig, 1, [4, 5], external_myo_mask=myo_mask)
    scar_label_orig = clean_prediction_by_class(scar_label_orig, {4: 5, 5: 3})
    edema_zone = edema_prob_orig > 0.35
    if edema_zone.any():
        edema_zone = largest_component(edema_zone)
    edema_zone = edema_zone & myo_mask_edema
    final_label = merge_labels(scar_label_orig, coarse_orig, edema_zone)
    final_label = clean_prediction_by_class(final_label, {4: 5, 5: 3})
    scar_mask = final_label == 5
    if scar_mask.any():
        final_label[scar_mask & ~largest_component(scar_mask)] = 0
    return train_to_official_labels(final_label, TRACK_MYOPS, stage="fine").astype(np.int16)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=CARE_ROOT)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    root = args.root.resolve()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    out = root / RESULT_REL
    pred_dir = out / "runtime/v3_mosaic_full_final_atlas_predictions/preds"
    cache_dir = out / "runtime/v3_mosaic_full_final_atlas_predictions/cache"
    pred_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    atlas = read_csv(out / "v3_case_atlas_manifest.csv")
    if args.limit > 0:
        atlas = atlas[: args.limit]
    if not atlas:
        raise SystemExit("v3_case_atlas_manifest.csv has no rows")
    canonical = {row["case_id"]: row for row in read_csv(out / "v3_canonical_modality_manifest.csv")}
    coarse_cfg = load_config(str(MOSAIC_SOURCE / "configs/myops_coarse.yaml"))
    target_spacing = coarse_cfg["data"].get("myops_target_spacing", [1.25, 1.25, 10.0])
    reg_config = coarse_cfg["data"].get("registration")
    coarse, coarse_edema, scar, edema = load_models(device)
    rows: list[dict[str, Any]] = []
    for row in atlas:
        case_id = row["case_id"]
        record = record_for_case(root, canonical[case_id])
        cached = cache_path(cache_dir, TRACK_MYOPS, case_id)
        if not cached.exists():
            preprocess_myops_case(record, cache_dir, target_spacing, registration_config=reg_config)
        payload = torch_load(cached)
        output_path = pred_dir / f"{case_id}_mosaic_full_final_pred.nii.gz"
        if not output_path.exists():
            label = predict_case(payload, coarse, coarse_edema, scar, edema, device)
            affine = np.asarray(payload.get("affine", np.eye(4)))
            header = payload.get("header", None)
            nib.save(nib.Nifti1Image(label, affine, header), str(output_path))
        rows.append(
            {
                "case_id": case_id,
                "prediction_path": str(output_path.relative_to(root)),
                "prediction_sha256": sha256(output_path),
                "source_tree": str(MOSAIC_SOURCE),
                "weights_dir": str(MOSAIC_WEIGHTS),
                "recipe": "M10_local_full_final_coarse_fine_scar_coarse_edema_edemanet_tta_threshold_postprocess",
                "tta": json.dumps(TTA, sort_keys=True),
                "status": "BOUND",
            }
        )
    write_csv(out / "v3_mosaic_full_final_prediction_manifest.csv", rows)
    (out / "v3_mosaic_full_final_prediction_receipt.json").write_text(
        json.dumps(
            {
                "created_at": utc_now(),
                "status": "PASS",
                "device": str(device),
                "case_count": len(rows),
                "prediction_dir": str(pred_dir),
                "manifest": "v3_mosaic_full_final_prediction_manifest.csv",
                "validation_upload": False,
                "docker_upload": False,
                "new_architecture_training": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(out / "v3_mosaic_full_final_prediction_manifest.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
