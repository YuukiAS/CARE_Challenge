#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import binary_dilation, zoom

APP = Path(__file__).resolve().parent
sys.path.insert(0, str(APP / "vendor"))

from myops.config import load_config
from myops.data.labels import TRACK_MYOPS, default_thresholds, modalities_for_track, num_classes
from myops.data.preprocessing import cache_path, preprocess_myops_case
from myops.inference.postprocess import clean_prediction_by_class, enforce_pathology_inside_myo, largest_component
from myops.inference.predict import predict_case_coarse, predict_case_fine
from myops.models import build_model
from myops.utils.io import torch_load

CONFIGS = Path(os.environ.get("CARE_CONFIGS", APP / "configs"))
MOSAIC_WEIGHTS = Path(os.environ.get("CARE_MOSAIC_WEIGHTS", APP / "models/mosaic/myops"))
INPUT_DIR = Path(os.environ.get("CARE_INPUT_DIR", "/input/myops"))
OUTPUT_DIR = Path(os.environ.get("CARE_OUTPUT_DIR", "/output/myops"))
CACHE = Path(os.environ.get("CARE_CACHE_DIR", "/tmp/care_myops_cache"))
NNUNET_RESULTS = Path(os.environ.get("nnUNet_results", APP / "models/nnunet/nnUNet_results"))
NNUNET_RAW = Path(os.environ.get("nnUNet_raw", APP / "models/nnunet/nnUNet_raw"))
NNUNET_PREPROCESSED = Path(os.environ.get("nnUNet_preprocessed", APP / "models/nnunet/nnUNet_preprocessed"))
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}
OFFICIAL = {1: 200, 2: 500, 3: 600, 4: 1220, 5: 2221}


def _device() -> torch.device:
    requested = os.environ.get("CARE_DEVICE", "cpu")
    if requested.startswith("cuda") and torch.cuda.is_available():
        return torch.device(requested)
    return torch.device("cpu")


def _guard_forbidden_mosaic_edema() -> None:
    forbidden = [MOSAIC_WEIGHTS / "coarse_edema.pt", MOSAIC_WEIGHTS / "edema.pt"]
    present = [str(p) for p in forbidden if p.exists()]
    if present:
        raise RuntimeError("Forbidden MoSAIC edema asset present in MyoPS bundle: " + ", ".join(present))


def _get_zoom_factors(current_zhw: list[int], payload: dict):
    original_shape = payload.get("original_shape")
    if original_shape is None:
        return None
    orig_hwz = list(original_shape)[:3]
    cur_hwz = [current_zhw[1], current_zhw[2], current_zhw[0]]
    if cur_hwz == orig_hwz:
        return None
    return orig_hwz, [o / c for o, c in zip(orig_hwz, cur_hwz)]


def _probs_to_original_space(probs_zhw: np.ndarray, payload: dict) -> np.ndarray:
    probs_hwz = np.transpose(probs_zhw, (0, 2, 3, 1))
    info = _get_zoom_factors(list(probs_zhw.shape[1:]), payload)
    if info is None:
        return probs_hwz
    orig_hwz, factors = info
    out = np.zeros([probs_zhw.shape[0]] + orig_hwz, dtype=np.float32)
    for c in range(probs_zhw.shape[0]):
        out[c] = zoom(probs_hwz[c], factors, order=1)
    return out


def _label_to_original_space(label_zhw: np.ndarray, payload: dict) -> np.ndarray:
    label_hwz = np.transpose(label_zhw, (1, 2, 0))
    info = _get_zoom_factors(list(label_zhw.shape), payload)
    if info is None:
        return label_hwz
    _, factors = info
    return zoom(label_hwz.astype(np.float32), factors, order=0).astype(np.int16)


def discover_cases() -> list[tuple[str, dict[str, str], list[str]]]:
    base = INPUT_DIR if INPUT_DIR.exists() else Path("/input")
    lge_files = sorted(base.glob("**/*_LGE.nii.gz"))
    cases = []
    for lge_path in lge_files:
        case_id = lge_path.name.replace("_LGE.nii.gz", "")
        case_dir = lge_path.parent
        image_paths = {"LGE": str(lge_path)}
        modalities = ["LGE"]
        for mod in ["C0", "T2"]:
            p = case_dir / f"{case_id}_{mod}.nii.gz"
            if p.exists():
                image_paths[mod] = str(p)
                modalities.append(mod)
        cases.append((case_id, image_paths, modalities))
    return cases


def _build_coarse(device: torch.device, cfg: dict):
    n_mod = len(modalities_for_track(TRACK_MYOPS))
    model = build_model(
        stage="coarse", track=TRACK_MYOPS, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(cfg["model"].get("base_channels", 24)), deep_supervision=True,
    )
    ckpt = torch.load(str(MOSAIC_WEIGHTS / "coarse.pt"), map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    return model.to(device).eval()


def _build_scar(device: torch.device, cfg: dict):
    n_mod = len(modalities_for_track(TRACK_MYOPS))
    model = build_model(
        stage="fine", track=TRACK_MYOPS, arch="2d_multi",
        in_channels=n_mod * 2 + 1, out_channels=num_classes(TRACK_MYOPS, "fine"),
        base_channels=int(cfg["model"].get("base_channels", 24)),
        deep_supervision=bool(cfg["model"].get("deep_supervision", True)),
        grid_size=int(cfg["model"].get("grid_size", 4)),
        span_range=float(cfg["model"].get("span_range", 0.98)),
        image_size=192,
        use_tps=bool(cfg["model"].get("use_tps", True)),
        use_spg=bool(cfg["model"].get("use_spg", True)),
        use_consistency=bool(cfg["model"].get("use_consistency", True)),
    )
    ckpt = torch.load(str(MOSAIC_WEIGHTS / "fine_scar.pt"), map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"], strict=False)
    return model.to(device).eval()


def run_mosaic_scar(cases: list[tuple[str, dict[str, str], list[str]]], device: torch.device) -> dict[str, np.ndarray]:
    _guard_forbidden_mosaic_edema()
    coarse_cfg = load_config(str(CONFIGS / "myops_coarse.yaml"))
    fine_cfg = load_config(str(CONFIGS / "myops_fine.yaml"))
    coarse_model = _build_coarse(device, coarse_cfg)
    scar_model = _build_scar(device, fine_cfg)
    target_spacing = coarse_cfg["data"].get("myops_target_spacing", [1.25, 1.25, 10.0])
    reg_config = coarse_cfg["data"].get("registration")
    thresholds = default_thresholds(TRACK_MYOPS, "fine")
    scars: dict[str, np.ndarray] = {}

    for case_id, image_paths, modalities in cases:
        cached = cache_path(str(CACHE), TRACK_MYOPS, case_id)
        if not cached.exists():
            record = {
                "track": "myops", "case_id": case_id, "center": "inference",
                "image_paths": image_paths, "label_path": None,
                "available_modalities": modalities,
                "modality_presence_mask": [1.0 if m in modalities else 0.0 for m in ["LGE", "C0", "T2"]],
                "coarse_supervision_mask": [0.0] * 3,
                "fine_supervision_mask": [0.0] * 5,
                "center_domain_id": -1,
            }
            preprocess_myops_case(record, str(CACHE), target_spacing, registration_config=reg_config)
        payload = torch_load(cached)
        with torch.no_grad():
            coarse = predict_case_coarse(coarse_model, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=TTA)
            coarse_prior = np.asarray(coarse["label"], dtype=np.int16)
            fine = predict_case_fine(scar_model, payload, TRACK_MYOPS, device, coarse_prior=coarse_prior, image_size=[192, 192], tta_config=TTA)
        probs_orig = _probs_to_original_space(np.asarray(fine["probs"], dtype=np.float32), payload)
        label = np.zeros(probs_orig.shape[1:], dtype=np.int16)
        for c in range(probs_orig.shape[0]):
            label[probs_orig[c] > thresholds[c]] = c + 1
        coarse_orig = _label_to_original_space(coarse_prior, payload)
        myo_mask = binary_dilation(coarse_orig > 0, iterations=1)
        label = enforce_pathology_inside_myo(label, 1, [4, 5], external_myo_mask=myo_mask)
        label = clean_prediction_by_class(label, {4: 5, 5: 3})
        scar = label == 5
        if scar.any():
            scar = scar & largest_component(scar)
        scars[case_id] = scar
    return scars


def run_nnunet(cases: list[tuple[str, dict[str, str], list[str]]], device: torch.device, tmp: Path) -> Path:
    in_dir = tmp / "nnunet_in"
    out_dir = tmp / "nnunet_out"
    in_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    for case_id, image_paths, _ in cases:
        for idx, mod in enumerate(["LGE", "T2", "C0"]):
            src = Path(image_paths.get(mod, ""))
            if not src.exists():
                continue
            shutil.copy2(src, in_dir / f"{case_id}_{idx:04d}.nii.gz")
    cmd = [
        "nnUNetv2_predict", "-d", "501", "-tr", "nnUNetTrainer_500epochs",
        "-c", "3d_fullres", "-f", "0", "1", "2", "3", "4",
        "-chk", "checkpoint_best.pth", "-i", str(in_dir), "-o", str(out_dir),
        "-npp", "1", "-nps", "1", "-device", device.type, "--disable_progress_bar",
    ]
    env = os.environ.copy()
    env["nnUNet_results"] = str(NNUNET_RESULTS)
    env["nnUNet_raw"] = str(NNUNET_RAW)
    env["nnUNet_preprocessed"] = str(NNUNET_PREPROCESSED)
    subprocess.run(cmd, check=True, env=env)
    return out_dir


def compose(nnunet_arr: np.ndarray, scar_mask: np.ndarray, disable_scar: bool = False, disable_edema: bool = False) -> np.ndarray:
    final = np.zeros(nnunet_arr.shape, dtype=np.int16)
    for raw, official in OFFICIAL.items():
        if raw == 4 and disable_edema:
            continue
        if raw <= 4:
            final[nnunet_arr == raw] = official
    if not disable_scar:
        final[scar_mask] = OFFICIAL[5]
    return final


def main() -> None:
    torch.set_num_threads(int(os.environ.get("CARE_TORCH_THREADS", "1")))
    device = _device()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    cases = discover_cases()
    if not cases:
        raise SystemExit("No MyoPS cases found.")
    print(f"Found {len(cases)} MyoPS cases; device={device}")
    scars = run_mosaic_scar(cases, device)
    with tempfile.TemporaryDirectory(prefix="care_myops_") as tmpdir:
        nnunet_out = run_nnunet(cases, device, Path(tmpdir))
        for case_id, _, _ in cases:
            nn_img = sitk.ReadImage(str(nnunet_out / f"{case_id}.nii.gz"))
            nn_arr = sitk.GetArrayFromImage(nn_img)
            scar = np.asarray(scars[case_id])
            if scar.shape != nn_arr.shape:
                raise RuntimeError(f"{case_id}: scar shape {scar.shape} != nnU-Net shape {nn_arr.shape}")
            final = compose(
                nn_arr, scar,
                disable_scar=os.environ.get("CARE_DISABLE_MOSAIC_SCAR") == "1",
                disable_edema=os.environ.get("CARE_DISABLE_NNUNET_EDEMA") == "1",
            )
            out_img = sitk.GetImageFromArray(final.astype(np.int16))
            out_img.CopyInformation(nn_img)
            tmp_out = OUTPUT_DIR / f".{case_id}_pred.tmp.nii.gz"
            out_path = OUTPUT_DIR / f"{case_id}_pred.nii.gz"
            sitk.WriteImage(out_img, str(tmp_out))
            os.replace(tmp_out, out_path)
            print(f"{case_id}: labels={np.unique(final).tolist()} -> {out_path}")


if __name__ == "__main__":
    main()
