#!/usr/bin/env python3
"""MyoPS Docker inference: coarse + scar fine + EdemaNet + V4 merge."""
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import binary_dilation, zoom

sys.path.insert(0, "/app")

from myops_pkg.config import load_config
from myops_pkg.data.labels import (
    TRACK_MYOPS,
    num_classes,
    modalities_for_track,
    default_thresholds,
    train_to_official_labels,
)
from myops_pkg.data.preprocessing import preprocess_myops_case, cache_path
from myops_pkg.inference.predict import predict_case_coarse, predict_case_fine
from myops_pkg.inference.postprocess import (
    largest_component,
    enforce_pathology_inside_myo,
    clean_prediction_by_class,
)
from myops_pkg.inference.edema_predict import (
    load_edema_model,
    predict_edema_case_probs,
    merge_labels,
)
from myops_pkg.models import build_model
from myops_pkg.utils.io import torch_load

WEIGHTS = Path("/app/weights")
CONFIGS = Path("/app/configs")
CACHE = Path("/tmp/cache")
INPUT_DIR = Path("/input/myops")
OUTPUT_DIR = Path("/output/myops")
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}


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
    lge_files = sorted(INPUT_DIR.glob("*_LGE.nii.gz"))
    cases = []
    for lge_path in lge_files:
        case_id = lge_path.name.replace("_LGE.nii.gz", "")
        image_paths = {"LGE": str(lge_path)}
        modalities = ["LGE"]
        for mod in ["C0", "T2"]:
            p = INPUT_DIR / f"{case_id}_{mod}.nii.gz"
            if p.exists():
                image_paths[mod] = str(p)
                modalities.append(mod)
        cases.append((case_id, image_paths, modalities))
    return cases


def _build_coarse(device, ckpt_name, coarse_cfg, n_mod):
    coarse_model = build_model(
        stage="coarse", track=TRACK_MYOPS, arch="2d_coarse",
        in_channels=n_mod * 2, out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    ckpt = torch.load(str(WEIGHTS / ckpt_name), map_location="cpu", weights_only=False)
    coarse_model.load_state_dict(ckpt["model_state"])
    return coarse_model.to(device).eval()


def load_models(device):
    coarse_cfg = load_config(str(CONFIGS / "myops_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))

    # NEW coarse drives scar branch + myo_mask; OLD coarse feeds the edema branch
    coarse_model = _build_coarse(device, "coarse.pt", coarse_cfg, n_mod)
    coarse_edema = _build_coarse(device, "coarse_edema.pt", coarse_cfg, n_mod)

    scar_cfg = load_config(str(CONFIGS / "myops_fine.yaml"))
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
    ckpt = torch.load(str(WEIGHTS / "fine_scar.pt"), map_location="cpu", weights_only=False)
    scar_model.load_state_dict(ckpt["model_state"], strict=False)
    scar_model = scar_model.to(device).eval()

    edema_model = load_edema_model(str(WEIGHTS / "edema.pt"), device)

    return coarse_model, coarse_edema, scar_model, edema_model


def main():
    device = torch.device("cpu")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    cases = discover_cases()
    if not cases:
        print("No MyoPS cases found in /input/myops/")
        return

    print(f"Found {len(cases)} MyoPS cases")
    print("Loading models...")
    coarse_model, coarse_edema, scar_model, edema_model = load_models(device)

    coarse_cfg = load_config(str(CONFIGS / "myops_coarse.yaml"))
    target_spacing = coarse_cfg["data"].get("myops_target_spacing", [1.25, 1.25, 10.0])
    reg_config = coarse_cfg["data"].get("registration")
    ucf_thresholds = default_thresholds(TRACK_MYOPS, "fine")

    for case_id, image_paths, modalities in cases:
        print(f"\n  {case_id} (modalities: {modalities})...")

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
            # NEW coarse: scar branch + myo_mask
            coarse_result = predict_case_coarse(
                coarse_model, payload, TRACK_MYOPS, device,
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
                coarse_edema, payload, TRACK_MYOPS, device,
                image_size=[192, 192], tta_config=TTA,
            )
            coarse_prior_old = np.asarray(coarse_old_result["label"], dtype=np.int16)

            edema_prob = predict_edema_case_probs(
                edema_model, payload, coarse_prior_old, device, dim=192,
            )

        ucf_probs_orig = probs_to_original_space(ucf_probs, payload)
        edema_prob_orig = probs_to_original_space(edema_prob[None], payload)[0]

        ucf_label_orig = np.zeros(ucf_probs_orig.shape[1:], dtype=np.int16)
        for c in range(ucf_probs_orig.shape[0]):
            ucf_label_orig[ucf_probs_orig[c] > ucf_thresholds[c]] = c + 1

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
        out_path = OUTPUT_DIR / f"{case_id}_pred.nii.gz"
        nib.save(nib.Nifti1Image(official_label.astype(np.int16), affine, header), str(out_path))
        print(f"    -> {out_path.name} labels: {np.unique(official_label)}")

    print(f"\nDone. {len(cases)} predictions saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
