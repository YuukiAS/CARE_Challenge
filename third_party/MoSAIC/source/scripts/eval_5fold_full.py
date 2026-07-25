#!/usr/bin/env python3
"""5-fold evaluation of the full MoSAIC pipeline with Dice AND HD95.

Extends scripts/eval_5fold.py (which reported Dice only) with the second official
CARE ranking metric, per-case records, and a --variant switch that toggles one
inference-time component at a time. The `main` variant must reproduce the Dice in
grid_output/5fold/v4_eval_results.json exactly.

    python scripts/eval_5fold_full.py --track myops --variant main
    python scripts/eval_5fold_full.py --track cine  --variant no_tta
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.ndimage import binary_dilation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from myops.config import load_config
from myops.data.labels import (
    EDEMA_CENTERS, TRACK_CINE, TRACK_MYOPS,
    default_thresholds, modalities_for_track, num_classes, train_label_map_for_track,
)
from myops.data.preprocessing import cache_path
from myops.data.splits import filter_records, split_records_by_fold
from myops.inference.edema_predict import load_edema_model, merge_labels, predict_edema_case_probs
from myops.inference.postprocess import (
    clean_prediction_by_class, enforce_pathology_inside_myo, largest_component,
)
from myops.inference.predict import predict_case_coarse, predict_case_fine
from myops.models import build_model
from myops.utils.io import read_jsonl, torch_load
from myops.utils.metrics import dice_score, hd95

ROOT = Path(__file__).resolve().parent.parent
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}

# Each variant disables exactly one inference-time component of the main pipeline.
VARIANTS = {
    "main":              {},
    "no_tta":            {"tta": False},
    "no_constraint":     {"constraint": False},
    "no_cc":             {"cc_cleanup": False},
    "no_edema_expert":   {"edema_expert": False},   # myops only
    "modality_lge_only": {"presence": [1.0, 0.0, 0.0]},
    "modality_lge_c0":   {"presence": [1.0, 1.0, 0.0]},
}


def spacing_zhw(payload) -> list[float]:
    """Physical spacing of the cached ZHW volume (target_spacing is stored XYZ)."""
    ts = payload["target_spacing"]
    return [float(ts[2]), float(ts[0]), float(ts[1])]


def score(pred: np.ndarray, gt: np.ndarray, spacing) -> tuple[float, float]:
    return dice_score(pred, gt), hd95(pred, gt, spacing)


def apply_presence_override(payload: dict, presence: list[float] | None) -> dict:
    """Simulate a centre that only acquired a subset of sequences.

    Missing sequences are zero-filled by preprocess_myops_case, so we reproduce
    that exactly: zero the image channel AND clear the presence flag.
    """
    if presence is None:
        return payload
    payload = copy.copy(payload)
    image = np.array(payload["image"], dtype=np.float32, copy=True)
    for idx, flag in enumerate(presence):
        if flag < 0.5:
            image[idx] = 0.0
    payload["image"] = image
    payload["modality_presence_mask"] = list(presence)
    return payload


# ---------------------------------------------------------------------------
# MyoPS
# ---------------------------------------------------------------------------
def _fine_source(fold_dir: Path, fine_root: Path | None, fold: int,
                 default_sub: str, default_cfg: Path) -> tuple[Path, dict]:
    """Locate the Stage-2 checkpoint dir and the config the model was built with.

    With --fine-root pointing at an ablation variant we must rebuild the network
    from *that run's* saved config, since variants change the architecture.
    """
    if fine_root is None:
        return fold_dir / default_sub, load_config(str(default_cfg))
    run_dir = fine_root / f"fold{fold}"
    cfg_path = run_dir / "config.yaml"
    if not cfg_path.exists():
        raise SystemExit(f"Missing {cfg_path}; cannot rebuild the ablation model.")
    return run_dir, load_config(str(cfg_path))


def load_myops_models(fold_dir: Path, device, fine_root=None, fold=0):
    coarse_cfg = load_config(str(ROOT / "configs" / "myops_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))

    coarse = build_model(stage="coarse", track=TRACK_MYOPS, arch="2d_coarse",
                         in_channels=n_mod * 2, out_channels=num_classes(TRACK_MYOPS, "coarse"),
                         base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
                         deep_supervision=True)
    coarse.load_state_dict(torch.load(str(fold_dir / "coarse" / "best.pt"),
                                      map_location="cpu", weights_only=False)["model_state"])
    coarse = coarse.to(device).eval()

    scar_dir, scar_cfg = _fine_source(fold_dir, fine_root, fold, "fine",
                                      ROOT / "configs" / "myops_fine.yaml")
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
        ckpt = scar_dir / name
        if ckpt.exists():
            break
    else:
        raise SystemExit(f"No Stage-2a checkpoint under {scar_dir}")
    scar.load_state_dict(torch.load(str(ckpt), map_location="cpu", weights_only=False)["model_state"],
                         strict=False)
    scar = scar.to(device).eval()
    scar.disable_coarse_prior = bool(scar_cfg.get("data", {}).get("disable_coarse_prior", False))

    edema_ckpt = fold_dir / "edema" / "best.pt"
    if not edema_ckpt.exists():
        edema_ckpt = fold_dir / "edema" / "last.pt"
    edema = load_edema_model(str(edema_ckpt), device)
    return coarse, scar, edema


def eval_myops_fold(fold_dir: Path, records, cache_root, device, opts,
                    fine_root=None, fold=0) -> list[dict]:
    coarse_model, scar_model, edema_model = load_myops_models(fold_dir, device, fine_root, fold)
    no_prior = bool(getattr(scar_model, "disable_coarse_prior", False))
    label_map = train_label_map_for_track(TRACK_MYOPS, "fine")
    thresholds = default_thresholds(TRACK_MYOPS, "fine")
    tta = TTA if opts.get("tta", True) else None

    per_case = []
    for rec in records:
        payload = torch_load(cache_path(cache_root, TRACK_MYOPS, rec["case_id"]))
        gt = np.asarray(payload["fine_label"], dtype=np.int16)
        sp = spacing_zhw(payload)
        payload_in = apply_presence_override(payload, opts.get("presence"))

        with torch.no_grad():
            coarse_prior = np.asarray(predict_case_coarse(
                coarse_model, payload_in, TRACK_MYOPS, device,
                image_size=[192, 192], tta_config=tta)["label"], dtype=np.int16)
            ucf_probs = np.asarray(predict_case_fine(
                scar_model, payload_in, TRACK_MYOPS, device, coarse_prior=coarse_prior,
                image_size=[192, 192], tta_config=tta,
                disable_coarse_prior=no_prior)["probs"], dtype=np.float32)
            edema_prob = predict_edema_case_probs(
                edema_model, payload_in, coarse_prior, device, dim=192)

        ucf_label = np.zeros(ucf_probs.shape[1:], dtype=np.int16)
        for c in range(ucf_probs.shape[0]):
            ucf_label[ucf_probs[c] > thresholds[c]] = c + 1

        myo_mask = binary_dilation(coarse_prior > 0, iterations=1)
        if opts.get("constraint", True):
            ucf_label = enforce_pathology_inside_myo(ucf_label, 1, [4, 5], external_myo_mask=myo_mask)
        if opts.get("cc_cleanup", True):
            ucf_label = clean_prediction_by_class(ucf_label, {4: 5, 5: 3})

        if opts.get("edema_expert", True):
            edema_zone = edema_prob > 0.35
            if edema_zone.any():
                edema_zone = largest_component(edema_zone)
            if opts.get("constraint", True):
                edema_zone = edema_zone & myo_mask
            final = merge_labels(ucf_label, coarse_prior, edema_zone)
        else:
            # Ablation: no dedicated expert -- keep FinePathNet's own edema channel.
            final = np.zeros_like(ucf_label)
            for src, dst in ((1, 1), (2, 2), (3, 3)):
                final[coarse_prior == src] = dst
            anat = (ucf_label >= 1) & (ucf_label <= 3)
            final[anat] = ucf_label[anat]
            final[ucf_label == 4] = 4
            final[ucf_label == 5] = 5

        if opts.get("cc_cleanup", True):
            final = clean_prediction_by_class(final, {4: 5, 5: 3})
            scar_mask = final == 5
            if scar_mask.any():
                final[scar_mask & ~largest_component(scar_mask)] = 0

        m = {"case_id": rec["case_id"], "center": rec["center"]}
        for name, tid in label_map.items():
            d, h = score(final == tid, gt == tid, sp)
            m[f"{name}_dice"], m[f"{name}_hd95"] = d, h
        d, h = score(np.isin(final, [4, 5]), np.isin(gt, [4, 5]), sp)
        m["lesion_union_dice"], m["lesion_union_hd95"] = d, h
        m["mean_dice"] = float(np.mean([m[f"{n}_dice"] for n in label_map]))
        per_case.append(m)

    del coarse_model, scar_model, edema_model
    torch.cuda.empty_cache()
    return per_case


# ---------------------------------------------------------------------------
# CineMyoPS
# ---------------------------------------------------------------------------
def load_cine_models(fold_dir: Path, device, fine_root=None, fold=0):
    coarse_cfg = load_config(str(ROOT / "configs" / "cine_coarse.yaml"))
    fine_dir, fine_cfg = _fine_source(fold_dir, fine_root, fold, "fine_v2",
                                      ROOT / "configs" / "cine_fine.yaml")
    n_mod = len(modalities_for_track(TRACK_CINE))

    coarse = build_model(stage="coarse", track=TRACK_CINE, arch="2d_coarse",
                         in_channels=n_mod * 2, out_channels=num_classes(TRACK_CINE, "coarse"),
                         base_channels=int(coarse_cfg["model"].get("base_channels", 24)),
                         deep_supervision=True)
    coarse.load_state_dict(torch.load(str(fold_dir / "coarse" / "best.pt"),
                                      map_location="cpu", weights_only=False)["model_state"])
    coarse = coarse.to(device).eval()

    num_frames = int(fine_cfg["model"].get("num_frames", 20))
    fine = build_model(stage="fine", track=TRACK_CINE, arch="cine_hybrid",
                       in_channels=num_frames + 1, out_channels=num_classes(TRACK_CINE, "fine"),
                       base_channels=int(fine_cfg["model"].get("base_channels", 16)),
                       deep_supervision=False, num_frames=num_frames,
                       max_displacement=float(fine_cfg["model"].get("max_displacement", 0.25)),
                       pathology_input=str(fine_cfg["model"].get("pathology_input", "flow")))
    for name in ("best_cine_scar.pt", "best_pathology.pt", "best.pt", "last.pt"):
        ckpt = fine_dir / name
        if ckpt.exists():
            break
    else:
        raise SystemExit(f"No Stage-2c checkpoint under {fine_dir}")
    fine.load_state_dict(torch.load(str(ckpt), map_location="cpu", weights_only=False)["model_state"],
                         strict=False)
    return coarse, fine.to(device).eval(), num_frames


def eval_cine_fold(fold_dir: Path, records, cache_root, device, opts,
                   fine_root=None, fold=0) -> list[dict]:
    coarse_model, fine_model, num_frames = load_cine_models(fold_dir, device, fine_root, fold)
    tta = TTA if opts.get("tta", True) else None

    per_case = []
    for rec in records:
        payload = torch_load(cache_path(cache_root, TRACK_CINE, rec["case_id"]))
        gt = np.asarray(payload["fine_label"], dtype=np.int16)
        sp = spacing_zhw(payload)

        with torch.no_grad():
            coarse_prior = np.asarray(predict_case_coarse(
                coarse_model, payload, TRACK_CINE, device,
                image_size=[192, 192], tta_config=tta)["label"], dtype=np.int16)
            pred = np.asarray(predict_case_fine(
                fine_model, payload, TRACK_CINE, device, coarse_prior=coarse_prior,
                image_size=[192, 192], crop_margin=[1, 18, 18],
                use_cine_sequence=True, cine_frame_count=num_frames,
                tta_config=tta)["label"], dtype=np.int16)

        if opts.get("constraint", True):
            myo_mask = binary_dilation(coarse_prior > 0, iterations=1)
            pred = enforce_pathology_inside_myo(pred, 1, [3], external_myo_mask=myo_mask)
        if opts.get("cc_cleanup", True):
            scar_mask = pred == 3
            if scar_mask.any():
                pred[scar_mask & ~largest_component(scar_mask)] = 0
            pred = clean_prediction_by_class(pred, {3: 5})

        m = {"case_id": rec["case_id"], "center": rec["center"]}
        for name, tid in (("myo", 1), ("lv", 2), ("scar", 3)):
            d, h = score(pred == tid, gt == tid, sp)
            m[f"{name}_dice"], m[f"{name}_hd95"] = d, h
        m["mean_dice"] = float(np.mean([m["myo_dice"], m["lv_dice"], m["scar_dice"]]))
        per_case.append(m)

    del coarse_model, fine_model
    torch.cuda.empty_cache()
    return per_case


def summarize(per_case: list[dict]) -> dict[str, float]:
    keys = [k for k in per_case[0] if k.endswith(("_dice", "_hd95"))]
    out = {}
    for k in keys:
        vals = [c[k] for c in per_case]
        if k.endswith("_hd95"):
            vals = [v for v in vals if np.isfinite(v)]
        out[k] = float(np.mean(vals)) if vals else float("nan")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", required=True, choices=["myops", "cine"])
    ap.add_argument("--variant", default="main", choices=sorted(VARIANTS))
    ap.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    ap.add_argument("--out-dir", type=str, default=str(ROOT / "paper" / "results"))
    ap.add_argument("--fine-root", type=str, default=None,
                    help="Evaluate an ablation variant's Stage-2 model inside the full "
                         "pipeline, e.g. ablations/myops/no_tps (expects fold{N}/config.yaml)")
    ap.add_argument("--tag", type=str, default=None, help="output filename tag")
    args = ap.parse_args()

    if args.track == "cine" and args.variant in ("no_edema_expert", "modality_lge_only", "modality_lge_c0"):
        raise SystemExit(f"variant {args.variant} does not apply to the cine track")

    opts = VARIANTS[args.variant]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cache_root = str(ROOT / "cache")

    if args.track == "myops":
        records = filter_records(read_jsonl(str(ROOT / "cache" / "manifest.jsonl")), TRACK_MYOPS)
        records = [r for r in records if r.get("center") in EDEMA_CENTERS]
        base = ROOT / "grid_output" / "5fold"
        runner = eval_myops_fold
    else:
        records = filter_records(read_jsonl(str(ROOT / "cache" / "cine_manifest.jsonl")), TRACK_CINE)
        base = ROOT / "grid_output_cine" / "5fold"
        runner = eval_cine_fold

    fine_root = Path(args.fine_root) if args.fine_root else None
    tag = args.tag or (fine_root.name if fine_root else args.variant)

    fold_summaries, all_cases = {}, []
    for fold in args.folds:
        _, val_recs = split_records_by_fold(records, fold)
        print(f"\n--- {args.track}/{tag} fold {fold} ({len(val_recs)} cases) ---")
        cases = runner(base / f"fold{fold}", val_recs, cache_root, device, opts,
                       fine_root=fine_root, fold=fold)
        for c in cases:
            c["fold"] = fold
        all_cases.extend(cases)
        fold_summaries[str(fold)] = summarize(cases)
        s = fold_summaries[str(fold)]
        print(f"    scar_dice={s['scar_dice']:.4f}  myo_dice={s['myo_dice']:.4f}")

    keys = sorted(next(iter(fold_summaries.values())))
    average = {k: float(np.mean([fold_summaries[f][k] for f in fold_summaries
                                 if np.isfinite(fold_summaries[f][k])])) for k in keys}
    std = {k: float(np.std([fold_summaries[f][k] for f in fold_summaries
                            if np.isfinite(fold_summaries[f][k])])) for k in keys}

    result = {"track": args.track, "variant": args.variant, "tag": tag,
              "fine_root": str(fine_root) if fine_root else None, "folds": args.folds,
              "fold_summaries": fold_summaries, "average": average, "std": std,
              "per_case": all_cases}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.track}_{tag}.json"
    out_path.write_text(json.dumps(result, indent=2))

    print(f"\n=== {args.track}/{tag} average over {len(args.folds)} folds ===")
    for k in keys:
        if k.endswith("_dice"):
            print(f"  {k:24s} {average[k]:.4f} +- {std[k]:.4f}")
    for k in keys:
        if k.endswith("_hd95"):
            print(f"  {k:24s} {average[k]:.2f} +- {std[k]:.2f} mm")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
