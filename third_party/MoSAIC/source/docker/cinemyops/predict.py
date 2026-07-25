#!/usr/bin/env python3
"""CineMyoPS Docker inference: multi-scale coarse+fine with TTA."""
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import binary_dilation, zoom

sys.path.insert(0, "/app")

from myops_pkg.config import load_config
from myops_pkg.data.labels import (
    TRACK_CINE,
    num_classes,
    modalities_for_track,
    default_thresholds,
    train_to_official_labels,
)
from myops_pkg.data.preprocessing import preprocess_cine_case, cache_path
from myops_pkg.inference.predict import predict_case_coarse, predict_case_fine
from myops_pkg.inference.postprocess import (
    largest_component,
    enforce_pathology_inside_myo,
    clean_prediction_by_class,
)
from myops_pkg.models import build_model
from myops_pkg.utils.io import torch_load

WEIGHTS = Path("/app/weights")
CONFIGS = Path("/app/configs")
CACHE = Path("/tmp/cache")
INPUT_DIR = Path("/input/cinemyops")
OUTPUT_DIR = Path("/output/cinemyops")
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}
CINE_SPACINGS = [[1.25, 1.25, 4.0], [1.25, 1.25, 8.0], [1.25, 1.25, 16.0]]


def _get_zoom_factors(current_zhw, payload):
    original_shape = payload.get("original_shape")
    if original_shape is None:
        return None
    orig_hwz = list(original_shape)[:3]
    cur_hwz = [current_zhw[1], current_zhw[2], current_zhw[0]]
    if cur_hwz == orig_hwz:
        return None
    return orig_hwz, [o / c for o, c in zip(orig_hwz, cur_hwz)]


def probs_to_original_space(probs_zhw, payload):
    C = probs_zhw.shape[0]
    probs_hwz = np.transpose(probs_zhw, (0, 2, 3, 1))
    info = _get_zoom_factors(list(probs_zhw.shape[1:]), payload)
    if info is None:
        return probs_hwz
    orig_hwz, factors = info
    out = np.zeros([C] + orig_hwz, dtype=np.float32)
    for c in range(C):
        out[c] = zoom(probs_hwz[c], factors, order=1)
    return out


def label_to_original_space(label_zhw, payload):
    label_hwz = np.transpose(label_zhw, (1, 2, 0))
    info = _get_zoom_factors(list(label_zhw.shape), payload)
    if info is None:
        return label_hwz
    _, factors = info
    return zoom(label_hwz.astype(np.float32), factors, order=0).astype(np.int16)


def discover_cases():
    cine_files = sorted(INPUT_DIR.glob("*_Cine.nii.gz"))
    return [(f.name.replace("_Cine.nii.gz", ""), str(f)) for f in cine_files]


def _build_fine(device, ckpt_name, fine_cfg):
    base_ch = int(fine_cfg["model"].get("base_channels", 16))
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))
    fine_model = build_model(
        stage="fine", track=TRACK_CINE, arch="cine_hybrid",
        in_channels=num_frames + 1, out_channels=num_classes(TRACK_CINE, "fine"),
        base_channels=base_ch, deep_supervision=False,
        num_frames=num_frames,
        max_displacement=float(fine_cfg["model"].get("max_displacement", 0.25)),
    )
    ckpt = torch.load(str(WEIGHTS / ckpt_name), map_location="cpu", weights_only=False)
    fine_model.load_state_dict(ckpt["model_state"], strict=False)
    return fine_model.to(device).eval()


def load_models(device):
    """V1/V2 ensemble (previous-best CineMyoPS recipe)."""
    coarse_cfg = load_config(str(CONFIGS / "cine_coarse.yaml"))
    fine_cfg = load_config(str(CONFIGS / "cine_fine.yaml"))
    n_mod = len(modalities_for_track(TRACK_CINE))

    coarse_model = build_model(
        stage="coarse", track=TRACK_CINE, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_CINE, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    ckpt = torch.load(str(WEIGHTS / "coarse.pt"), map_location="cpu", weights_only=False)
    coarse_model.load_state_dict(ckpt["model_state"])
    coarse_model = coarse_model.to(device).eval()

    fine_v1 = _build_fine(device, "fine_v1.pt", fine_cfg)
    fine_v2 = _build_fine(device, "fine_v2.pt", fine_cfg)

    return coarse_model, [fine_v1, fine_v2]


def preprocess_at_spacing(case_id, cine_path, spacing, coarse_cfg):
    tag = f"cine_z{spacing[2]:.0f}"
    cache_dir = CACHE / tag
    cache_dir.mkdir(parents=True, exist_ok=True)

    out_path = cache_path(str(cache_dir), TRACK_CINE, case_id)
    if not out_path.exists():
        record = {
            "track": "cinemyops", "case_id": case_id, "center": "inference",
            "image_paths": {"Cine": cine_path}, "label_path": None,
            "available_modalities": ["Cine"], "modality_presence_mask": [1.0],
            "coarse_supervision_mask": [0.0, 0.0],
            "fine_supervision_mask": [0.0, 0.0, 0.0],
            "center_domain_id": -1,
        }
        preprocess_cine_case(record, str(cache_dir), spacing, temporal_config=coarse_cfg.get("data"))

    return torch_load(out_path)


def main():
    device = torch.device("cpu")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    cases = discover_cases()
    if not cases:
        print("No CineMyoPS cases found in /input/cinemyops/")
        return

    print(f"Found {len(cases)} CineMyoPS cases")
    print("Loading models...")
    coarse_model, fine_models = load_models(device)

    coarse_cfg = load_config(str(CONFIGS / "cine_coarse.yaml"))
    fine_cfg = load_config(str(CONFIGS / "cine_fine.yaml"))
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))
    thresholds = default_thresholds(TRACK_CINE, "fine")

    for case_id, cine_path in cases:
        print(f"\n  {case_id}...")

        all_probs_orig = []
        default_payload = None

        for spacing in CINE_SPACINGS:
            payload = preprocess_at_spacing(case_id, cine_path, spacing, coarse_cfg)
            if spacing[2] == 8.0:
                default_payload = payload

            with torch.no_grad():
                coarse_result = predict_case_coarse(
                    coarse_model, payload, TRACK_CINE, device,
                    image_size=[192, 192], tta_config=TTA,
                )
                coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)

                # V1/V2 ensemble: average probs across the two fine models
                probs_sum = None
                for fine_model in fine_models:
                    fine_result = predict_case_fine(
                        fine_model, payload, TRACK_CINE, device,
                        coarse_prior=coarse_prior, image_size=[192, 192],
                        crop_margin=[1, 18, 18],
                        use_cine_sequence=True, cine_frame_count=num_frames,
                        tta_config=TTA,
                    )
                    p = np.asarray(fine_result["probs"], dtype=np.float32)
                    probs_sum = p if probs_sum is None else probs_sum + p
                probs = probs_sum / len(fine_models)

            probs_orig = probs_to_original_space(probs, payload)
            all_probs_orig.append(probs_orig)
            print(f"    Z={spacing[2]}mm shape={probs_orig.shape}")

        target_shape = all_probs_orig[0].shape
        avg_probs = np.zeros(target_shape, dtype=np.float32)
        n_valid = 0
        for p in all_probs_orig:
            if p.shape == target_shape:
                avg_probs += p
                n_valid += 1
        avg_probs /= max(n_valid, 1)

        pred_label = np.zeros(avg_probs.shape[1:], dtype=np.int16)
        for c in range(avg_probs.shape[0]):
            pred_label[avg_probs[c] > thresholds[c]] = c + 1

        if default_payload is None:
            default_payload = preprocess_at_spacing(case_id, cine_path, [1.25, 1.25, 8.0], coarse_cfg)

        with torch.no_grad():
            coarse_result = predict_case_coarse(
                coarse_model, default_payload, TRACK_CINE, device,
                image_size=[192, 192], tta_config=TTA,
            )
            coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)

        coarse_orig = label_to_original_space(coarse_prior, default_payload)

        myo_mask = binary_dilation(coarse_orig > 0, iterations=1)
        pred_label = enforce_pathology_inside_myo(pred_label, 1, [3], external_myo_mask=myo_mask)
        scar_mask = (pred_label == 3)
        if scar_mask.any():
            pred_label[scar_mask & ~largest_component(scar_mask)] = 0
        pred_label = clean_prediction_by_class(pred_label, {3: 5})

        official_label = train_to_official_labels(pred_label, TRACK_CINE, stage="fine")

        affine = np.asarray(default_payload.get("affine", np.eye(4)))
        header = default_payload.get("header", None)
        out_path = OUTPUT_DIR / f"{case_id}_pred.nii.gz"
        nib.save(nib.Nifti1Image(official_label.astype(np.int16), affine, header), str(out_path))
        print(f"    -> {out_path.name} labels: {np.unique(official_label)}")

    print(f"\nDone. {len(cases)} predictions saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
