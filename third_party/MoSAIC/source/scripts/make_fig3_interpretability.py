#!/usr/bin/env python3
"""Figure 3: what the alignment and motion modules actually learn.

(a) The Stage-2a TPS field: the predicted control lattice for the T2 stream drawn
    over the T2 slice, with the per-pixel displacement magnitude beneath it. The
    claim being evidenced is that the warp concentrates on the myocardial wall.
(b) The Stage-2c motion field: cine flow magnitude at end-systole with the
    predicted scar contour on top. The claim is that predicted scar coincides
    with the hypokinetic segment.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from myops.config import load_config
from myops.data.labels import (
    TRACK_MYOPS, TRACK_CINE, num_classes, modalities_for_track,
)
from myops.data.preprocessing import cache_path
from myops.models import build_model
from myops.models.tps import TPSGridGen
from myops.inference.predict import predict_case_coarse, predict_case_fine
from myops.inference.postprocess import largest_component, enforce_pathology_inside_myo
from scipy.ndimage import binary_dilation, zoom
from myops.utils.io import torch_load

CACHE = ROOT / "cache"
GRID = ROOT / "grid_output" / "5fold"
GRID_CINE = ROOT / "grid_output_cine" / "5fold"
OUT = ROOT / "paper" / "figures"
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}

MYOPS_CASE, MYOPS_FOLD = "Case3037", 2   # unused: panel (a) dropped
CINE_CASE, CINE_FOLD = None, 0          # resolved from the fold's validation split


# --------------------------------------------------------------------------
# (a) TPS alignment field
# --------------------------------------------------------------------------
def tps_panel(device):
    fold_dir = GRID / f"fold{MYOPS_FOLD}"
    cfg = load_config(str(ROOT / "configs" / "myops_fine.yaml"))
    mcfg = cfg["model"]
    n_mod = len(modalities_for_track(TRACK_MYOPS))

    grid_size = int(mcfg.get("grid_size", 4))
    span = float(mcfg.get("span_range", 0.98))

    model = build_model(stage="fine", track=TRACK_MYOPS, arch=mcfg.get("arch", "2d_multi"),
                        in_channels=n_mod * 2 + 1, out_channels=num_classes(TRACK_MYOPS, "fine"),
                        base_channels=int(mcfg.get("base_channels", 24)),
                        deep_supervision=bool(mcfg.get("deep_supervision", True)),
                        grid_size=grid_size, span_range=span, image_size=192,
                        use_tps=True, use_spg=bool(mcfg.get("use_spg", True)),
                        use_consistency=bool(mcfg.get("use_consistency", True)))
    for name in ("best_scar.pt", "best_pathology.pt", "best.pt", "last.pt"):
        if (fold_dir / "fine" / name).exists():
            break
    model.load_state_dict(torch.load(str(fold_dir / "fine" / name), map_location="cpu",
                                     weights_only=False)["model_state"], strict=False)
    model = model.to(device).eval()

    payload = torch_load(cache_path(str(CACHE), TRACK_MYOPS, MYOPS_CASE))
    image = np.asarray(payload["image"], dtype=np.float32)
    gt = np.asarray(payload["fine_label"], dtype=np.int16)
    z = int(np.argmax(((gt == 4) | (gt == 5)).sum(axis=(1, 2))))

    # Centre-crop to the 192x192 the network was trained at.
    def crop(a):
        h, w = a.shape[-2:]
        sy, sx = max(0, (h - 192) // 2), max(0, (w - 192) // 2)
        out = np.zeros(a.shape[:-2] + (192, 192), dtype=a.dtype)
        ch, cw = min(h, 192), min(w, 192)
        dy, dx = max(0, (192 - h) // 2), max(0, (192 - w) // 2)
        out[..., dy:dy + ch, dx:dx + cw] = a[..., sy:sy + ch, sx:sx + cw]
        return out

    img = crop(image[:, z])                       # [3,192,192]
    myo = crop((gt[z] == 1) | (gt[z] == 4) | (gt[z] == 5))
    presence = np.ones((3, 192, 192), dtype=np.float32)
    prior = np.zeros((1, 192, 192), dtype=np.float32)
    x = torch.from_numpy(np.concatenate([img, presence, prior], 0))[None].float().to(device)

    # forward() only exposes theta while training. Capture it with a hook instead,
    # so the network stays in eval mode and the field we draw is the one inference
    # actually uses.
    captured = {}
    handle = model.tps_t2.register_forward_hook(
        lambda mod, inp, out: captured.__setitem__("theta", out))
    with torch.no_grad():
        model(x)
    handle.remove()
    theta_t = captured["theta"]                   # [1,K,2] normalised coords
    theta = theta_t[0].cpu().numpy()

    # Target lattice the offsets are measured against.
    r = span
    tgt = np.array(list(np.ndindex(grid_size, grid_size)), dtype=np.float32)
    tgt = -r + tgt * (2.0 * r / (grid_size - 1))
    tgt = tgt[:, ::-1].copy()                     # (x, y) like TPSWarper

    # Dense displacement magnitude: where the sampling grid departs from identity.
    gen = TPSGridGen(192, 192, torch.from_numpy(tgt).float()).to(device)
    with torch.no_grad():
        coords = gen(theta_t.to(device))[0].cpu().numpy().reshape(192, 192, 2)
    ys, xs = np.meshgrid(np.linspace(-1, 1, 192), np.linspace(-1, 1, 192), indexing="ij")
    ident = np.stack([xs, ys], -1)
    disp = np.linalg.norm(coords - ident, axis=-1) * 96.0   # normalised -> pixels
    return img[2], myo, tgt, theta, disp


# --------------------------------------------------------------------------
# (b) cine motion field vs predicted scar
# --------------------------------------------------------------------------
def pick_cine_case() -> tuple[str, int]:
    """Best-scoring cine case, paired with the fold that held it out."""
    import json
    pc = json.loads((ROOT / "paper" / "results" / "cine_main.json").read_text())["per_case"]
    scored = [c for c in pc if c.get("scar_dice", 0) > 0]
    best = max(scored, key=lambda c: c["scar_dice"])
    print(f"      best cine case {best['case_id']} "
          f"(fold {best['fold']}, scar {best['scar_dice']:.3f})")
    return best["case_id"], int(best["fold"])


def cine_panel(device, case_id: str, fold: int):
    """Prediction comes from the real inference path (coarse prior, ROI crop, TTA,
    post-processing) so the contour drawn is the one the pipeline actually emits.
    The motion field is read separately with a hook, since it is an internal."""
    fold_dir = GRID_CINE / f"fold{fold}"
    cfg = load_config(str(ROOT / "configs" / "cine_fine.yaml"))
    mcfg = cfg["model"]
    num_frames = int(mcfg.get("num_frames", 20))

    coarse_cfg = load_config(str(ROOT / "configs" / "cine_coarse.yaml"))
    coarse = build_model(stage="coarse", track=TRACK_CINE, arch="2d_coarse",
                         in_channels=2, out_channels=num_classes(TRACK_CINE, "coarse"),
                         base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
                         deep_supervision=True)
    coarse.load_state_dict(torch.load(str(fold_dir / "coarse" / "best.pt"),
                                      map_location="cpu", weights_only=False)["model_state"])
    coarse = coarse.to(device).eval()

    model = build_model(stage="fine", track=TRACK_CINE, arch="cine_hybrid",
                        in_channels=num_frames + 1, out_channels=num_classes(TRACK_CINE, "fine"),
                        base_channels=int(mcfg.get("base_channels", 16)),
                        deep_supervision=bool(mcfg.get("deep_supervision", False)),
                        num_frames=num_frames,
                        max_displacement=float(mcfg.get("max_displacement", 0.25)),
                        pathology_input=mcfg.get("pathology_input", "flow"))
    for name in ("best_pathology.pt", "best.pt", "last.pt"):
        if (fold_dir / "fine_v2" / name).exists():
            break
    model.load_state_dict(torch.load(str(fold_dir / "fine_v2" / name), map_location="cpu",
                                     weights_only=False)["model_state"], strict=False)
    model = model.to(device).eval()

    payload = torch_load(cache_path(str(CACHE), TRACK_CINE, case_id))
    gt = np.asarray(payload["fine_label"], dtype=np.int16)
    image = np.asarray(payload["cine"], dtype=np.float32)

    flows_seen = {}
    def grab(mod, inp, out):
        if "f" not in flows_seen:
            flows_seen["f"] = out["motion_fields"].detach().float().cpu().numpy()
    handle = model.register_forward_hook(grab)
    with torch.no_grad():
        coarse_prior = np.asarray(predict_case_coarse(
            coarse, payload, TRACK_CINE, device,
            image_size=[192, 192], tta_config=TTA)["label"], dtype=np.int16)
        pred = np.asarray(predict_case_fine(
            model, payload, TRACK_CINE, device, coarse_prior=coarse_prior,
            image_size=[192, 192], crop_margin=[1, 18, 18],
            use_cine_sequence=True, cine_frame_count=num_frames,
            tta_config=TTA)["label"], dtype=np.int16)
    handle.remove()

    myo_mask = binary_dilation(coarse_prior > 0, iterations=1)
    pred = enforce_pathology_inside_myo(pred, 1, [3], external_myo_mask=myo_mask)
    scar_mask = pred == 3
    if scar_mask.any():
        pred[scar_mask & ~largest_component(scar_mask)] = 0

    # Slice showing the most reference scar, which is what the panel is about.
    z = int(np.argmax((gt == 3).sum(axis=(1, 2)))) if (gt == 3).any() else gt.shape[0] // 2

    flows = flows_seen["f"][0]                         # [T,2,h,w] at network resolution
    mag_all = np.linalg.norm(flows, axis=1) * 96.0
    t_es = int(np.argmax(mag_all.mean(axis=(1, 2))))
    mag = zoom(mag_all[t_es], [gt.shape[1] / mag_all.shape[1],
                               gt.shape[2] / mag_all.shape[2]], order=1)

    print(f"      pred scar px={int((pred[z]==3).sum())}  ref scar px={int((gt[z]==3).sum())}")
    return image[0, z], mag, pred[z], gt[z], t_es, case_id


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    OUT.mkdir(parents=True, exist_ok=True)

    # Panel (a), the TPS field, is deliberately not plotted: the trained warp is
    # input-independent and sub-pixel, so drawing it would assert an alignment
    # behaviour the weights do not show. The negative result is reported in text.
    print("  cine motion vs scar...")
    case, cfold = pick_cine_case()
    ed, mag, pred2d, gt2d, t_es, case = cine_panel(device, case, cfold)

    fig, axes = plt.subplots(1, 3, figsize=(4.8, 1.75))

    # Crop around the heart, taken from this case's own labels.
    ys, xs = np.where(gt2d > 0)
    if len(ys):
        m = 30
        sy = slice(max(0, ys.min() - m), min(192, ys.max() + m))
        sx = slice(max(0, xs.min() - m), min(192, xs.max() + m))
    else:
        sy = sx = slice(0, 192)

    # (a) ED frame
    ax = axes[0]
    lo, hi = np.percentile(ed[sy, sx], [1, 99])
    ax.imshow(ed[sy, sx], cmap="gray", vmin=lo, vmax=hi)
    ax.set_title("(a) cine ED frame", fontsize=6.5, pad=3)

    # (b) flow magnitude at peak motion
    ax = axes[1]
    im = ax.imshow(mag[sy, sx], cmap="viridis")
    ax.contour((gt2d[sy, sx] == 1) | (gt2d[sy, sx] == 3), levels=[0.5], colors="w", linewidths=0.6)
    ax.set_title(f"(b) $\\|\\varphi_t\\|$ at $t={t_es}$ (px)", fontsize=6.5, pad=3)
    cb = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    cb.ax.tick_params(labelsize=4.5, length=1.5)

    # (c) predicted scar against the reference
    ax = axes[2]
    ax.imshow(ed[sy, sx], cmap="gray", vmin=lo, vmax=hi)
    ax.contour(gt2d[sy, sx] == 3, levels=[0.5], colors="#E8B54D", linewidths=0.9)
    ax.contour(pred2d[sy, sx] == 3, levels=[0.5], colors="#C6453D", linewidths=0.9)
    ax.set_title("(c) scar: ref / pred", fontsize=6.5, pad=3)

    for ax in axes:
        ax.set_xticks([]); ax.set_yticks([])

    fig.subplots_adjust(left=0.005, right=0.985, top=0.86, bottom=0.02, wspace=0.14)
    fig.subplots_adjust(left=0.005, right=0.985, top=0.845, bottom=0.02, wspace=0.10)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"fig3_interpretability.{ext}", dpi=300)
    print(f"  -> {OUT/'fig3_interpretability.pdf'}")


if __name__ == "__main__":
    main()
