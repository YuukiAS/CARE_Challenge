#!/usr/bin/env python3
"""Figure 2: qualitative multi-sequence results for the two best-performing cases.

Rows: LGE / C0 / T2 (grayscale) then ground truth / MoSAIC (label overlay on LGE).
Columns: one per case. Each case is rendered with the model of the fold that held
it out, so nothing shown here was seen during that model's training.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from myops.config import load_config
from myops.data.labels import (
    TRACK_MYOPS, num_classes, modalities_for_track, default_thresholds,
)
from myops.data.preprocessing import cache_path
from myops.inference.predict import predict_case_coarse, predict_case_fine
from myops.inference.postprocess import (
    largest_component, enforce_pathology_inside_myo, clean_prediction_by_class,
)
from myops.inference.edema_predict import (
    load_edema_model, predict_edema_case_probs, merge_labels,
)
from myops.models import build_model
from myops.utils.io import torch_load

CACHE = ROOT / "cache"
GRID = ROOT / "grid_output" / "5fold"
OUT = ROOT / "paper" / "figures"
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}

# 0=bg 1=myo 2=LV 3=RV 4=edema 5=scar
LABEL_COLORS = ["#00000000", "#4C9F70", "#3C6E9F", "#8E6FB0", "#E8B54D", "#C6453D"]
LABEL_NAMES = ["", "Myocardium", "LV", "RV", "Edema", "Scar"]


def load_models(fold: int, device):
    fold_dir = GRID / f"fold{fold}"
    coarse_cfg = load_config(str(ROOT / "configs" / "myops_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))

    coarse = build_model(stage="coarse", track=TRACK_MYOPS, arch="2d_coarse",
                         in_channels=n_mod * 2, out_channels=num_classes(TRACK_MYOPS, "coarse"),
                         base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
                         deep_supervision=True)
    coarse.load_state_dict(torch.load(str(fold_dir / "coarse" / "best.pt"),
                                      map_location="cpu", weights_only=False)["model_state"])
    coarse = coarse.to(device).eval()

    scar_cfg = load_config(str(ROOT / "configs" / "myops_fine.yaml"))
    mcfg = scar_cfg["model"]
    scar = build_model(stage="fine", track=TRACK_MYOPS, arch=mcfg.get("arch", "2d_multi"),
                       in_channels=n_mod * 2 + 1, out_channels=num_classes(TRACK_MYOPS, "fine"),
                       base_channels=int(mcfg.get("base_channels", 24)),
                       deep_supervision=bool(mcfg.get("deep_supervision", True)),
                       grid_size=int(mcfg.get("grid_size", 4)),
                       span_range=float(mcfg.get("span_range", 0.98)),
                       image_size=192,
                       use_tps=bool(mcfg.get("use_tps", True)),
                       use_spg=bool(mcfg.get("use_spg", True)),
                       use_consistency=bool(mcfg.get("use_consistency", True)))
    for name in ("best_scar.pt", "best_pathology.pt", "best.pt", "last.pt"):
        if (fold_dir / "fine" / name).exists():
            break
    scar.load_state_dict(torch.load(str(fold_dir / "fine" / name), map_location="cpu",
                                    weights_only=False)["model_state"], strict=False)
    scar = scar.to(device).eval()

    ck = fold_dir / "edema" / "best.pt"
    if not ck.exists():
        ck = fold_dir / "edema" / "last.pt"
    edema = load_edema_model(str(ck), device)
    return coarse, scar, edema


def predict(case_id: str, fold: int, device):
    """Return (image[3,D,H,W], ground truth, prediction) in cached space."""
    payload = torch_load(cache_path(str(CACHE), TRACK_MYOPS, case_id))
    gt = np.asarray(payload["fine_label"], dtype=np.int16)
    image = np.asarray(payload["image"], dtype=np.float32)

    coarse_model, scar_model, edema_model = load_models(fold, device)
    thresholds = default_thresholds(TRACK_MYOPS, "fine")

    with torch.no_grad():
        coarse_prior = np.asarray(predict_case_coarse(
            coarse_model, payload, TRACK_MYOPS, device,
            image_size=[192, 192], tta_config=TTA)["label"], dtype=np.int16)
        ucf_probs = np.asarray(predict_case_fine(
            scar_model, payload, TRACK_MYOPS, device, coarse_prior=coarse_prior,
            image_size=[192, 192], tta_config=TTA)["probs"], dtype=np.float32)
        edema_prob = predict_edema_case_probs(
            edema_model, payload, coarse_prior, device, dim=192)

    ucf_label = np.zeros(ucf_probs.shape[1:], dtype=np.int16)
    for c in range(ucf_probs.shape[0]):
        ucf_label[ucf_probs[c] > thresholds[c]] = c + 1

    myo_mask = binary_dilation(coarse_prior > 0, iterations=1)
    ucf_label = enforce_pathology_inside_myo(ucf_label, 1, [4, 5], external_myo_mask=myo_mask)
    ucf_label = clean_prediction_by_class(ucf_label, {4: 5, 5: 3})

    edema_zone = edema_prob > 0.35
    if edema_zone.any():
        edema_zone = largest_component(edema_zone)
    edema_zone = edema_zone & myo_mask
    pred = merge_labels(ucf_label, coarse_prior, edema_zone)
    pred = clean_prediction_by_class(pred, {4: 5, 5: 3})
    scar_mask = pred == 5
    if scar_mask.any():
        pred[scar_mask & ~largest_component(scar_mask)] = 0

    return image, gt, pred


def best_slice(gt: np.ndarray) -> int:
    """Slice carrying the most lesion, which is what the figure is about."""
    lesion = ((gt == 4) | (gt == 5)).sum(axis=(1, 2))
    return int(np.argmax(lesion)) if lesion.max() > 0 else gt.shape[0] // 2


def crop_box(gt2d: np.ndarray, shape, margin: int = 28):
    """Tight box around the heart so the ventricle fills the panel."""
    ys, xs = np.where(gt2d > 0)
    if len(ys) == 0:
        h, w = shape
        return slice(0, h), slice(0, w)
    y0, y1 = max(0, ys.min() - margin), min(shape[0], ys.max() + margin)
    x0, x1 = max(0, xs.min() - margin), min(shape[1], xs.max() + margin)
    return slice(y0, y1), slice(x0, x1)


def show_gray(ax, img):
    lo, hi = np.percentile(img, [1, 99])
    ax.imshow(img, cmap="gray", vmin=lo, vmax=hi)
    ax.set_xticks([]); ax.set_yticks([])


def show_overlay(ax, base, label, cmap, norm):
    lo, hi = np.percentile(base, [1, 99])
    ax.imshow(base, cmap="gray", vmin=lo, vmax=hi)
    masked = np.ma.masked_where(label == 0, label)
    ax.imshow(masked, cmap=cmap, norm=norm, alpha=0.55, interpolation="nearest")
    ax.set_xticks([]); ax.set_yticks([])


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    OUT.mkdir(parents=True, exist_ok=True)

    cases = [("Case3037", 2, "(a) CenterC"), ("Case2023", 2, "(b) CenterB")]
    per_case = {c["case_id"]: c for c in
                json.loads((ROOT / "paper" / "results" / "myops_main.json").read_text())["per_case"]}

    cmap = ListedColormap(LABEL_COLORS)
    norm = BoundaryNorm(np.arange(-0.5, 6.5, 1.0), cmap.N)

    # One row per case, columns walking from raw sequences to prediction. This
    # stays wide and short, which is what the LNCS text width can afford.
    cols = ["LGE", "C0", "T2", "Ground truth", r"$\bf{MoSAIC}$"]
    fig, axes = plt.subplots(len(cases), 5, figsize=(4.8, 2.05))

    for row, (case_id, fold, tag) in enumerate(cases):
        print(f"  {case_id} (fold {fold})...")
        image, gt, pred = predict(case_id, fold, device)
        z = best_slice(gt)
        sy, sx = crop_box(gt[z], gt[z].shape)

        lge, c0, t2 = image[0, z][sy, sx], image[1, z][sy, sx], image[2, z][sy, sx]
        gt2d, pr2d = gt[z][sy, sx], pred[z][sy, sx]

        show_gray(axes[row, 0], lge)
        show_gray(axes[row, 1], c0)
        show_gray(axes[row, 2], t2)
        show_overlay(axes[row, 3], lge, gt2d, cmap, norm)
        show_overlay(axes[row, 4], lge, pr2d, cmap, norm)

        m = per_case[case_id]
        axes[row, 0].set_ylabel(f"{tag}\nscar {m['scar_dice']:.2f}\nedema {m['edema_dice']:.2f}",
                                fontsize=5.2, labelpad=2)

    for c, name in enumerate(cols):
        axes[0, c].set_title(name, fontsize=6.5, pad=2.5)

    handles = [Patch(facecolor=LABEL_COLORS[i], label=LABEL_NAMES[i]) for i in range(1, 6)]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=5.5,
               frameon=False, bbox_to_anchor=(0.5, -0.01), handlelength=1.1,
               columnspacing=1.1, handletextpad=0.4)

    fig.subplots_adjust(left=0.088, right=0.998, top=0.885, bottom=0.075,
                        wspace=0.03, hspace=0.03)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"fig2_qualitative.{ext}", dpi=300)
    print(f"  -> {OUT/'fig2_qualitative.pdf'}")


if __name__ == "__main__":
    main()
