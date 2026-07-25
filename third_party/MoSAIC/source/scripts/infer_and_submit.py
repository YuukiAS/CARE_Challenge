#!/usr/bin/env python3
"""Inference on validation/test set and package submission ZIP.

Usage:
    python scripts/infer_and_submit.py --val-dir /path/to/Myo_val --gpu 0
"""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import binary_dilation, zoom

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from myops.config import load_config
from myops.data.labels import (
    TRACK_MYOPS, TRACK_CINE,
    num_classes, modalities_for_track, train_to_official_labels,
    default_thresholds,
)
from myops.data.preprocessing import preprocess_myops_case, preprocess_cine_case, cache_path
from myops.inference.predict import predict_case_coarse, predict_case_fine
from myops.inference.postprocess import (
    clean_prediction_by_class, enforce_pathology_inside_myo, largest_component,
)
from myops.inference.edema_predict import (
    load_edema_model, predict_edema_case_probs, merge_labels,
)
from myops.models import build_model
from myops.utils.io import torch_load

ROOT = Path(__file__).resolve().parent.parent
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}
CINE_SPACINGS = [[1.25, 1.25, 4.0], [1.25, 1.25, 8.0], [1.25, 1.25, 16.0]]


def save_nifti(data, path, affine, header=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(data.astype(np.int16), affine, header), str(path))


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


def probs_to_label(probs, thresholds):
    label = np.zeros(probs.shape[1:], dtype=np.int16)
    for c in range(probs.shape[0]):
        label[probs[c] > thresholds[c]] = c + 1
    return label


def preprocess_myops_val(val_dir, cache_dir):
    print("\nPreprocessing MyoPS validation data...")
    myops_val = Path(val_dir) / "MyoPS_val" / "AnonymousCenter"
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cases = sorted([d.name for d in myops_val.iterdir() if d.is_dir()])
    config = load_config(str(ROOT / "configs" / "myops_coarse.yaml"))
    target_spacing = config["data"].get("myops_target_spacing", [1.25, 1.25, 10.0])
    reg_config = config["data"].get("registration")

    for case_id in cases:
        case_dir = myops_val / case_id
        out_path = cache_path(str(cache_dir), TRACK_MYOPS, case_id)
        if out_path.exists():
            continue

        image_paths = {"LGE": str(case_dir / f"{case_id}_LGE.nii.gz")}
        modalities = ["LGE"]
        for mod in ["C0", "T2"]:
            p = case_dir / f"{case_id}_{mod}.nii.gz"
            if p.exists():
                image_paths[mod] = str(p)
                modalities.append(mod)

        record = {
            "track": "myops", "case_id": case_id, "center": "inference",
            "image_paths": image_paths, "label_path": None,
            "available_modalities": modalities,
            "modality_presence_mask": [1.0 if m in modalities else 0.0 for m in ["LGE", "C0", "T2"]],
            "coarse_supervision_mask": [0.0] * 3,
            "fine_supervision_mask": [0.0] * 5,
            "center_domain_id": -1,
        }
        preprocess_myops_case(record, str(cache_dir), target_spacing, registration_config=reg_config)
        print(f"  {case_id}: preprocessed")

    return cases


def preprocess_cine_val(val_dir, cache_dir, target_spacing=None):
    cine_val = Path(val_dir) / "CineMyoPS_val" / "AnonymousCenter"
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(str(ROOT / "configs" / "cine_coarse.yaml"))
    spacing = target_spacing or config["data"].get("cine_target_spacing", [1.25, 1.25, 8.0])

    cine_files = sorted(cine_val.glob("*_Cine.nii.gz"))
    cases = [f.name.replace("_Cine.nii.gz", "") for f in cine_files]

    for case_id, cine_path in zip(cases, cine_files):
        out_path = cache_path(str(cache_dir), TRACK_CINE, case_id)
        if out_path.exists():
            continue
        record = {
            "track": "cinemyops", "case_id": case_id, "center": "inference",
            "image_paths": {"Cine": str(cine_path)}, "label_path": None,
            "available_modalities": ["Cine"], "modality_presence_mask": [1.0],
            "coarse_supervision_mask": [0.0, 0.0],
            "fine_supervision_mask": [0.0, 0.0, 0.0],
            "center_domain_id": -1,
        }
        preprocess_cine_case(record, str(cache_dir), spacing, temporal_config=config.get("data"))
        print(f"  {case_id}: preprocessed (Z={spacing[2]}mm)")

    return cases


def _build_myops_coarse(device, ckpt_path, coarse_cfg, n_mod):
    coarse_model = build_model(
        stage="coarse", track=TRACK_MYOPS, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    coarse_model.load_state_dict(ckpt["model_state"])
    return coarse_model.to(device).eval()


def load_myops_models(device):
    """Regression fix (Part B): keep NEW coarse+scar, restore OLD edema.

    The edema branch is fed the OLD coarse prior to faithfully reproduce the
    previous-best edema-zone score (0.6255); the scar branch uses the NEW coarse.
    """
    full_dir = ROOT / "full_train" / "myops" / "fold-1"
    myopsf = ROOT / "checkpoints" / "myopsf"
    coarse_cfg = load_config(str(ROOT / "configs" / "myops_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))

    # NEW coarse (scar branch + myo_mask)
    new_coarse_path = full_dir / "coarse" / "best.pt"
    if not new_coarse_path.exists():
        new_coarse_path = full_dir / "coarse" / "last.pt"
    coarse_new = _build_myops_coarse(device, new_coarse_path, coarse_cfg, n_mod)

    # OLD coarse (edema branch, to reproduce 0.6255)
    old_coarse_path = myopsf / "myops_coarse_full" / "best.pt"
    if not old_coarse_path.exists():
        old_coarse_path = myopsf / "myops_coarse_full" / "last.pt"
    coarse_old = _build_myops_coarse(device, old_coarse_path, coarse_cfg, n_mod)

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
    scar_ckpt = full_dir / "fine" / "best_scar.pt"
    if not scar_ckpt.exists():
        scar_ckpt = full_dir / "fine" / "best.pt"
    ckpt = torch.load(str(scar_ckpt), map_location="cpu", weights_only=False)
    scar_model.load_state_dict(ckpt["model_state"], strict=False)
    scar_model = scar_model.to(device).eval()

    # OLD edema (previous-best, scores 0.6255 on validation zone)
    edema_ckpt = myopsf / "myops_edema_full" / "last.pt"
    if not edema_ckpt.exists():
        edema_ckpt = myopsf / "myops_edema_full" / "best.pt"
    edema_model = load_edema_model(str(edema_ckpt), device)

    return coarse_new, coarse_old, scar_model, edema_model


def _build_cine_fine(device, ckpt_path, fine_cfg):
    base_ch = int(fine_cfg["model"].get("base_channels", 16))
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))
    fine_model = build_model(
        stage="fine", track=TRACK_CINE, arch="cine_hybrid",
        in_channels=num_frames + 1, out_channels=num_classes(TRACK_CINE, "fine"),
        base_channels=base_ch, deep_supervision=False,
        num_frames=num_frames,
        max_displacement=float(fine_cfg["model"].get("max_displacement", 0.25)),
    )
    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    fine_model.load_state_dict(ckpt["model_state"], strict=False)
    return fine_model.to(device).eval()


def load_cine_models(device):
    """Regression fix (Part B): full revert to previous-best CineMyoPS ensemble.

    Old coarse (cine_coarse_full_v2) + V1/V2 fine ensemble from MyoPS-F, which
    scored cine scar=0.2069 on validation (vs 0.1878 for the new single model).
    """
    myopsf = ROOT / "checkpoints" / "myopsf"
    coarse_cfg = load_config(str(ROOT / "configs" / "cine_coarse.yaml"))
    fine_cfg = load_config(str(ROOT / "configs" / "cine_fine.yaml"))
    n_mod = len(modalities_for_track(TRACK_CINE))

    coarse_model = build_model(
        stage="coarse", track=TRACK_CINE, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_CINE, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    coarse_path = myopsf / "cine_coarse_full_v2" / "best.pt"
    if not coarse_path.exists():
        coarse_path = myopsf / "cine_coarse_full" / "best.pt"
    ckpt = torch.load(str(coarse_path), map_location="cpu", weights_only=False)
    coarse_model.load_state_dict(ckpt["model_state"])
    coarse_model = coarse_model.to(device).eval()

    v1_path = myopsf / "cine_scar_full" / "best_pathology.pt"
    if not v1_path.exists():
        v1_path = myopsf / "cine_scar_full" / "best.pt"
    fine_v1 = _build_cine_fine(device, v1_path, fine_cfg)

    v2_path = myopsf / "cine_scar_full_v2" / "best_pathology.pt"
    if not v2_path.exists():
        v2_path = myopsf / "cine_scar_full_v2" / "best.pt"
    fine_v2 = _build_cine_fine(device, v2_path, fine_cfg)

    return coarse_model, [fine_v1, fine_v2]


def infer_myops(val_dir, cache_dir, output_dir, device):
    print("\n" + "=" * 60)
    print("Inference: MyoPS (coarse + scar + EdemaNet + V4 merge)")
    print("=" * 60)

    cases = preprocess_myops_val(val_dir, cache_dir)
    coarse_new, coarse_old, scar_model, edema_model = load_myops_models(device)

    myops_out = Path(output_dir) / "MyoPS" / "Anonymous Center"
    myops_out.mkdir(parents=True, exist_ok=True)

    ucf_thresholds = default_thresholds(TRACK_MYOPS, "fine")

    for case_id in cases:
        print(f"\n  {case_id}...")
        payload = torch_load(cache_path(str(cache_dir), TRACK_MYOPS, case_id))

        with torch.no_grad():
            # NEW coarse drives scar branch + myo_mask
            coarse_result = predict_case_coarse(
                coarse_new, payload, TRACK_MYOPS, device,
                image_size=[192, 192], tta_config=TTA,
            )
            coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)

            ucf_result = predict_case_fine(
                scar_model, payload, TRACK_MYOPS, device,
                coarse_prior=coarse_prior, image_size=[192, 192], tta_config=TTA,
            )
            ucf_probs = np.asarray(ucf_result["probs"], dtype=np.float32)

            # OLD coarse prior feeds the OLD edema branch (reproduce 0.6255)
            coarse_old_result = predict_case_coarse(
                coarse_old, payload, TRACK_MYOPS, device,
                image_size=[192, 192], tta_config=TTA,
            )
            coarse_prior_old = np.asarray(coarse_old_result["label"], dtype=np.int16)

            edema_prob = predict_edema_case_probs(
                edema_model, payload, coarse_prior_old, device, dim=192,
            )

        ucf_probs_orig = probs_to_original_space(ucf_probs, payload)
        edema_prob_orig = probs_to_original_space(edema_prob[None], payload)[0]
        ucf_label_orig = probs_to_label(ucf_probs_orig, ucf_thresholds)
        coarse_orig = label_to_original_space(coarse_prior, payload)

        # NEW-coarse myo_mask constrains scar; OLD-coarse myo_mask constrains edema
        # (faithful reproduction of previous-best 0.6255 edema zone)
        myo_mask = binary_dilation(coarse_orig > 0, iterations=1)
        coarse_old_orig = label_to_original_space(coarse_prior_old, payload)
        myo_mask_edema = binary_dilation(coarse_old_orig > 0, iterations=1)

        ucf_label_orig = enforce_pathology_inside_myo(ucf_label_orig, 1, [4, 5], external_myo_mask=myo_mask)
        ucf_label_orig = clean_prediction_by_class(ucf_label_orig, {4: 5, 5: 3})

        edema_zone = edema_prob_orig > 0.35
        if edema_zone.any():
            edema_zone = largest_component(edema_zone)
        edema_zone = edema_zone & myo_mask_edema

        final_label = merge_labels(ucf_label_orig, coarse_orig, edema_zone)
        final_label = clean_prediction_by_class(final_label, {4: 5, 5: 3})
        scar_mask = (final_label == 5)
        if scar_mask.any():
            final_label[scar_mask & ~largest_component(scar_mask)] = 0

        official_label = train_to_official_labels(final_label, TRACK_MYOPS, stage="fine")

        affine = np.asarray(payload.get("affine", np.eye(4)))
        header = payload.get("header", None)
        case_out = myops_out / case_id
        save_nifti(official_label, case_out / f"{case_id}_pred.nii.gz", affine, header)
        print(f"    labels: {np.unique(official_label)}")

    del coarse_new, coarse_old, scar_model, edema_model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def infer_cine(val_dir, cache_base, output_dir, device):
    print("\n" + "=" * 60)
    print("Inference: CineMyoPS (multi-scale + V1/V2 ensemble + TTA)")
    print("=" * 60)

    coarse_model, fine_models = load_cine_models(device)
    fine_cfg = load_config(str(ROOT / "configs" / "cine_fine.yaml"))
    num_frames = int(fine_cfg["model"].get("num_frames", fine_cfg["data"].get("max_cine_frames", 20)))
    thresholds = default_thresholds(TRACK_CINE, "fine")

    cine_out = Path(output_dir) / "CineMyoPS" / "Anonymous Center"
    cine_out.mkdir(parents=True, exist_ok=True)

    cine_val = Path(val_dir) / "CineMyoPS_val" / "AnonymousCenter"
    cine_files = sorted(cine_val.glob("*_Cine.nii.gz"))
    cases = [f.name.replace("_Cine.nii.gz", "") for f in cine_files]

    for case_id in cases:
        print(f"\n  {case_id}...")

        all_probs_orig = []
        for spacing in CINE_SPACINGS:
            tag = f"cine_z{spacing[2]:.0f}"
            cache_dir = Path(cache_base) / tag
            preprocess_cine_val(val_dir, str(cache_dir), spacing)

            payload = torch_load(cache_path(str(cache_dir), TRACK_CINE, case_id))

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

        pred_label = probs_to_label(avg_probs, thresholds)

        default_cache = Path(cache_base) / "cine_z8"
        payload_default = torch_load(cache_path(str(default_cache), TRACK_CINE, case_id))
        coarse_result = predict_case_coarse(
            coarse_model, payload_default, TRACK_CINE, device,
            image_size=[192, 192], tta_config=TTA,
        )
        coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)
        coarse_orig = label_to_original_space(coarse_prior, payload_default)

        myo_mask = binary_dilation(coarse_orig > 0, iterations=1)
        pred_label = enforce_pathology_inside_myo(pred_label, 1, [3], external_myo_mask=myo_mask)
        scar_mask = (pred_label == 3)
        if scar_mask.any():
            pred_label[scar_mask & ~largest_component(scar_mask)] = 0
        pred_label = clean_prediction_by_class(pred_label, {3: 5})

        official_label = train_to_official_labels(pred_label, TRACK_CINE, stage="fine")

        affine = np.asarray(payload_default.get("affine", np.eye(4)))
        header = payload_default.get("header", None)
        case_out = cine_out / case_id
        save_nifti(official_label, case_out / f"{case_id}_pred.nii.gz", affine, header)
        print(f"    labels: {np.unique(official_label)}")

    del coarse_model, fine_models
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def package_submission(output_dir):
    print("\n" + "=" * 60)
    print("Packaging Submission")
    print("=" * 60)

    zip_path = ROOT / "outputs" / "CARE-Myocardium-UNC.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    output_dir = Path(output_dir)

    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for nifti_file in sorted(output_dir.rglob("*_pred.nii.gz")):
            arcname = str(nifti_file.relative_to(output_dir))
            zf.write(str(nifti_file), arcname)
            print(f"  Added: {arcname}")

    print(f"\nSubmission ZIP: {zip_path}")
    print(f"Size: {zip_path.stat().st_size / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-dir", type=str, required=True, help="Path to Myo_val data directory")
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args()

    import os
    os.environ["CUDA_VISIBLE_DEVICES"] = str(args.gpu)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    cache_dir = str(ROOT / "cache_val")
    output_dir = str(ROOT / "outputs" / "validation")

    infer_myops(args.val_dir, cache_dir, output_dir, device)
    infer_cine(args.val_dir, cache_dir, output_dir, device)
    package_submission(output_dir)


if __name__ == "__main__":
    main()
