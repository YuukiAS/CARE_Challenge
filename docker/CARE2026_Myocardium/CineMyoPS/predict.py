#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import binary_dilation, zoom

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP / "vendor"))

from myops.config import load_config
from myops.data.labels import TRACK_CINE, default_thresholds, modalities_for_track, num_classes, train_to_official_labels
from myops.data.preprocessing import cache_path, preprocess_cine_case
from myops.inference.postprocess import clean_prediction_by_class, enforce_pathology_inside_myo, largest_component
from myops.inference.predict import predict_case_coarse, predict_case_fine
from myops.models import build_model
from myops.utils.io import torch_load

CONFIGS = Path(os.environ.get("CARE_CONFIGS", APP / "configs"))
WEIGHTS = Path(os.environ.get("CARE_MOSAIC_WEIGHTS", APP / "models/mosaic/cinemyops"))
CACHE = Path(os.environ.get("CARE_CACHE_DIR", "/tmp/care_cinemyops_cache"))
INPUT_DIR = Path(os.environ.get("CARE_INPUT_DIR", "/input/cinemyops"))
OUTPUT_DIR = Path(os.environ.get("CARE_OUTPUT_DIR", "/output/cinemyops"))
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}
CINE_SPACINGS = [[1.25, 1.25, 4.0], [1.25, 1.25, 8.0], [1.25, 1.25, 16.0]]


def _device() -> torch.device:
    requested = os.environ.get("CARE_DEVICE", "cpu")
    if requested.startswith("cuda") and torch.cuda.is_available():
        return torch.device(requested)
    return torch.device("cpu")


def _get_zoom_factors(current_zhw: list[int], payload: dict):
    original_shape = payload.get("original_shape")
    if original_shape is None:
        return None
    orig_hwz = list(original_shape)[:3]
    cur_hwz = [current_zhw[1], current_zhw[2], current_zhw[0]]
    if cur_hwz == orig_hwz:
        return None
    return orig_hwz, [o / c for o, c in zip(orig_hwz, cur_hwz)]


def probs_to_original_space(probs_zhw: np.ndarray, payload: dict) -> np.ndarray:
    probs_hwz = np.transpose(probs_zhw, (0, 2, 3, 1))
    info = _get_zoom_factors(list(probs_zhw.shape[1:]), payload)
    if info is None:
        return probs_hwz
    orig_hwz, factors = info
    out = np.zeros([probs_zhw.shape[0]] + orig_hwz, dtype=np.float32)
    for c in range(probs_zhw.shape[0]):
        out[c] = zoom(probs_hwz[c], factors, order=1)
    return out


def label_to_original_space(label_zhw: np.ndarray, payload: dict) -> np.ndarray:
    label_hwz = np.transpose(label_zhw, (1, 2, 0))
    info = _get_zoom_factors(list(label_zhw.shape), payload)
    if info is None:
        return label_hwz
    _, factors = info
    return zoom(label_hwz.astype(np.float32), factors, order=0).astype(np.int16)


def discover_cases() -> list[tuple[str, str]]:
    base = INPUT_DIR if INPUT_DIR.exists() else Path("/input")
    cine_files = sorted(base.glob("**/*_Cine.nii.gz"))
    return [(f.name.replace("_Cine.nii.gz", ""), str(f)) for f in cine_files]


def _build_fine(device: torch.device, ckpt_name: str, fine_cfg: dict):
    base_ch = int(fine_cfg["model"].get("base_channels", 16))
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))
    model = build_model(
        stage="fine", track=TRACK_CINE, arch="cine_hybrid",
        in_channels=num_frames + 1, out_channels=num_classes(TRACK_CINE, "fine"),
        base_channels=base_ch, deep_supervision=False, num_frames=num_frames,
        max_displacement=float(fine_cfg["model"].get("max_displacement", 0.25)),
    )
    ckpt = torch.load(str(WEIGHTS / ckpt_name), map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"], strict=False)
    return model.to(device).eval()


def load_models(device: torch.device):
    coarse_cfg = load_config(str(CONFIGS / "cine_coarse.yaml"))
    fine_cfg = load_config(str(CONFIGS / "cine_fine.yaml"))
    n_mod = len(modalities_for_track(TRACK_CINE))
    coarse = build_model(
        stage="coarse", track=TRACK_CINE, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_CINE, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    ckpt = torch.load(str(WEIGHTS / "coarse.pt"), map_location="cpu", weights_only=False)
    coarse.load_state_dict(ckpt["model_state"])
    return coarse.to(device).eval(), [_build_fine(device, "fine_v1.pt", fine_cfg), _build_fine(device, "fine_v2.pt", fine_cfg)]


def preprocess_at_spacing(case_id: str, cine_path: str, spacing: list[float], coarse_cfg: dict):
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


def main() -> None:
    torch.set_num_threads(int(os.environ.get("CARE_TORCH_THREADS", "1")))
    device = _device()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    cases = discover_cases()
    if not cases:
        raise SystemExit("No CineMyoPS cases found.")
    print(f"Found {len(cases)} CineMyoPS cases; device={device}")
    coarse_model, fine_models = load_models(device)
    coarse_cfg = load_config(str(CONFIGS / "cine_coarse.yaml"))
    fine_cfg = load_config(str(CONFIGS / "cine_fine.yaml"))
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))
    thresholds = default_thresholds(TRACK_CINE, "fine")
    for case_id, cine_path in cases:
        all_probs_orig = []
        default_payload = None
        for spacing in CINE_SPACINGS:
            payload = preprocess_at_spacing(case_id, cine_path, spacing, coarse_cfg)
            if spacing[2] == 8.0:
                default_payload = payload
            with torch.no_grad():
                coarse_result = predict_case_coarse(coarse_model, payload, TRACK_CINE, device, image_size=[192, 192], tta_config=TTA)
                coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)
                probs_sum = None
                for fine_model in fine_models:
                    fine_result = predict_case_fine(
                        fine_model, payload, TRACK_CINE, device,
                        coarse_prior=coarse_prior, image_size=[192, 192],
                        crop_margin=[1, 18, 18], use_cine_sequence=True,
                        cine_frame_count=num_frames, tta_config=TTA,
                    )
                    probs = np.asarray(fine_result["probs"], dtype=np.float32)
                    probs_sum = probs if probs_sum is None else probs_sum + probs
            probs_orig = probs_to_original_space(probs_sum / len(fine_models), payload)
            all_probs_orig.append(probs_orig)
        target_shape = all_probs_orig[0].shape
        avg_probs = np.zeros(target_shape, dtype=np.float32)
        n_valid = 0
        for probs in all_probs_orig:
            if probs.shape == target_shape:
                avg_probs += probs
                n_valid += 1
        avg_probs /= max(n_valid, 1)
        pred = np.zeros(avg_probs.shape[1:], dtype=np.int16)
        for c in range(avg_probs.shape[0]):
            pred[avg_probs[c] > thresholds[c]] = c + 1
        if default_payload is None:
            default_payload = preprocess_at_spacing(case_id, cine_path, [1.25, 1.25, 8.0], coarse_cfg)
        with torch.no_grad():
            coarse_result = predict_case_coarse(coarse_model, default_payload, TRACK_CINE, device, image_size=[192, 192], tta_config=TTA)
        coarse_orig = label_to_original_space(np.asarray(coarse_result["label"], dtype=np.int16), default_payload)
        myo_mask = binary_dilation(coarse_orig > 0, iterations=1)
        pred = enforce_pathology_inside_myo(pred, 1, [3], external_myo_mask=myo_mask)
        scar = pred == 3
        if scar.any():
            pred[scar & ~largest_component(scar)] = 0
        pred = clean_prediction_by_class(pred, {3: 5})
        official = train_to_official_labels(pred, TRACK_CINE, stage="fine")
        out_path = OUTPUT_DIR / f"{case_id}_pred.nii.gz"
        tmp_out = OUTPUT_DIR / f".{case_id}_pred.tmp.nii.gz"
        nib.save(nib.Nifti1Image(official.astype(np.int16), np.asarray(default_payload.get("affine", np.eye(4))), default_payload.get("header", None)), str(tmp_out))
        os.replace(tmp_out, out_path)
        print(f"{case_id}: labels={np.unique(official).tolist()} -> {out_path}")


if __name__ == "__main__":
    main()
