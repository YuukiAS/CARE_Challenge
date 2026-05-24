#!/usr/bin/env python3
"""Train Lane A Round10 edema-only residual refiner."""

from __future__ import annotations

import argparse
import csv
import os
import random
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault(
    "MPLCONFIGDIR",
    str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner/mpl_cache"),
)
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import SimpleITK as sitk
import torch

from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, write_csv
from src.care_myocardium.refiner.laneA_round10_model import (
    ConservativeEdemaResidualRefiner,
    assert_scar_unchanged,
    fuse_edema_only_from_prob,
    refined_edema_logit,
)


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner"


def crop_slices(shape: tuple[int, int, int], center: tuple[int, int, int], patch_shape: tuple[int, int, int]) -> tuple[slice, slice, slice]:
    out = []
    for size, c, patch in zip(shape, center, patch_shape):
        start = 0 if size <= patch else max(0, min(int(c) - patch // 2, size - patch))
        out.append(slice(start, min(start + patch, size)))
    return tuple(out)  # type: ignore[return-value]


def crop_or_pad(arr: np.ndarray, slices: tuple[slice, slice, slice], patch_shape: tuple[int, int, int]) -> np.ndarray:
    cropped = arr[slices] if arr.ndim == 3 else arr[(slice(None), *slices)]
    out_shape = patch_shape if arr.ndim == 3 else (arr.shape[0], *patch_shape)
    out = np.zeros(out_shape, dtype=arr.dtype)
    insert = tuple(slice(0, s) for s in cropped.shape[-3:])
    if arr.ndim == 3:
        out[insert] = cropped
    else:
        out[(slice(None), *insert)] = cropped
    return out


class LazyCaseCache:
    def __init__(self) -> None:
        self._cache: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, sitk.Image]] = {}

    def get(self, case: RefinerCase) -> tuple[np.ndarray, np.ndarray, np.ndarray, sitk.Image]:
        if case.case_id not in self._cache:
            self._cache[case.case_id] = load_case_features(case)
        return self._cache[case.case_id]


def sample_patch(
    case: RefinerCase,
    cache: LazyCaseCache,
    rng: random.Random,
    patch_shape: tuple[int, int, int],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    features, target, baseline, _ = cache.get(case)
    coords = np.argwhere(target > 0)
    if len(coords) and rng.random() < 0.85:
        center = tuple(int(x) for x in coords[rng.randrange(len(coords))])
    else:
        baseline_edema = np.argwhere(baseline == 4)
        if len(baseline_edema):
            center = tuple(int(x) for x in baseline_edema[rng.randrange(len(baseline_edema))])
        else:
            center = tuple(int(rng.randrange(s)) for s in target.shape)
    slices = crop_slices(target.shape, center, patch_shape)
    feat = crop_or_pad(features, slices, patch_shape)
    tgt = crop_or_pad(target, slices, patch_shape)
    base = crop_or_pad(baseline, slices, patch_shape)
    base_prob = feat[4]
    return (
        torch.from_numpy(feat[None]).float(),
        torch.from_numpy(tgt[None, None]).float(),
        torch.from_numpy(base[None]).long(),
        torch.from_numpy(base_prob[None, None]).float(),
    )


def loss_fn(new_logit: torch.Tensor, delta: torch.Tensor, target: torch.Tensor, *, t2_present: bool) -> torch.Tensor:
    if t2_present:
        bce = torch.nn.functional.binary_cross_entropy_with_logits(new_logit, target)
        prob = torch.sigmoid(new_logit)
        dice = 1.0 - (2.0 * (prob * target).sum() + 1e-6) / (prob.sum() + target.sum() + 1e-6)
        primary = 0.5 * bce + 0.5 * dice
    else:
        primary = 0.02 * torch.sigmoid(new_logit).mean()
    return primary + 0.01 * delta.abs().mean()


def choose_train_case(t2_cases: list[RefinerCase], no_t2_cases: list[RefinerCase], rng: random.Random) -> RefinerCase:
    if rng.random() < 0.75:
        return t2_cases[rng.randrange(len(t2_cases))]
    return no_t2_cases[rng.randrange(len(no_t2_cases))]


def export_validation_predictions(
    model: ConservativeEdemaResidualRefiner,
    val_cases: list[RefinerCase],
    cache: LazyCaseCache,
    pred_dir: Path,
    device: torch.device,
    threshold: float,
) -> list[dict[str, object]]:
    pred_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    model.eval()
    with torch.no_grad():
        for case in val_cases:
            features, _, baseline, gt_img = cache.get(case)
            x = torch.from_numpy(features[None]).float().to(device)
            base = torch.from_numpy(baseline[None]).long().to(device)
            base_prob = torch.from_numpy(features[4][None, None]).float().to(device)
            delta = model(x)
            refined = fuse_edema_only_from_prob(base, base_prob, delta, threshold=threshold)[0].detach().cpu().numpy().astype(np.uint8)
            scar_changed = assert_scar_unchanged(base, torch.from_numpy(refined[None]).to(device))
            out = sitk.GetImageFromArray(refined)
            out.CopyInformation(gt_img)
            sitk.WriteImage(out, str(pred_dir / f"{case.case_id}.nii.gz"))
            rows.append(
                {
                    "case_id": case.case_id,
                    "center": case.center,
                    "modality_group": case.modality_group,
                    "t2_present": case.t2_present,
                    "edema_gt_positive": case.edema_gt_positive,
                    "delta_abs_mean": float(delta.detach().abs().mean().cpu()),
                    "delta_abs_max": float(delta.detach().abs().max().cpu()),
                    "delta_clip_fraction": float((delta.detach().abs() >= model.delta_max - 1e-6).float().mean().cpu()),
                    "changed_voxels": int((refined != baseline).sum()),
                    "scar_changed_voxels": scar_changed,
                    "baseline_edema_voxels": int((baseline == 4).sum()),
                    "refined_edema_voxels": int((refined == 4).sum()),
                }
            )
    return rows


def append_train_commands(command: str) -> None:
    path = OUT_ROOT / "round10_train_commands.txt"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    path.write_text(existing + command + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-name", default="laneA_r10_edema_residual_refiner_fold0_very_short")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--steps-per-epoch", type=int, default=40)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden-channels", type=int, default=16)
    parser.add_argument("--delta-max", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patch-shape", default="8,128,128")
    parser.add_argument("--skip-eval", action="store_true")
    args = parser.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    command = " ".join(sys.argv)
    append_train_commands(command)
    patch_shape = tuple(int(x) for x in args.patch_shape.split(","))
    if len(patch_shape) != 3:
        raise ValueError("--patch-shape must have three comma-separated integers")
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    rng = random.Random(args.seed)
    torch.set_num_threads(2)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cases = build_cases()
    train_cases = [c for c in cases if c.fold0_split == "train"]
    val_cases = [c for c in cases if c.fold0_split == "val"]
    t2_cases = [c for c in train_cases if c.t2_present and c.edema_gt_positive]
    no_t2_cases = [c for c in train_cases if (not c.t2_present) and (not c.edema_gt_positive)]
    if not t2_cases or not no_t2_cases:
        raise RuntimeError("Round10 refiner train needs both T2-positive and no-T2 empty-GT train cases")

    model = ConservativeEdemaResidualRefiner(in_channels=13, hidden_channels=args.hidden_channels, delta_max=args.delta_max).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    cache = LazyCaseCache()
    train_rows: list[dict[str, object]] = []

    config_lines = [
        "candidate: conservative_edema_residual_refiner_A",
        f"run_name: {args.run_name}",
        f"epochs: {args.epochs}",
        f"steps_per_epoch: {args.steps_per_epoch}",
        f"lr: {args.lr}",
        f"hidden_channels: {args.hidden_channels}",
        f"delta_max: {args.delta_max}",
        f"threshold: {args.threshold}",
        f"seed: {args.seed}",
        f"patch_shape: {args.patch_shape}",
        "train_cases: fold0 train, using existing nnU-Net501 out-of-fold baseline probabilities",
        "validation_cases: fold0 validation, using existing nnU-Net501 fold0 probabilities",
        "fusion_rule: class_4 edema only; class_5 scar unchanged",
    ]
    (OUT_ROOT / "round10_train_config.yaml").write_text("\n".join(config_lines) + "\n", encoding="utf-8")

    model.train()
    for epoch in range(args.epochs):
        losses = []
        scar_changed_total = 0
        no_t2_new_total = 0
        for _ in range(args.steps_per_epoch):
            case = choose_train_case(t2_cases, no_t2_cases, rng)
            x, y, baseline, baseline_prob = sample_patch(case, cache, rng, patch_shape)
            x = x.to(device)
            y = y.to(device)
            baseline = baseline.to(device)
            baseline_prob = baseline_prob.to(device)
            optim.zero_grad(set_to_none=True)
            delta = model(x)
            new_logit = refined_edema_logit(baseline_prob, delta)
            loss = loss_fn(new_logit, delta, y, t2_present=case.t2_present)
            loss.backward()
            optim.step()
            refined = fuse_edema_only_from_prob(baseline, baseline_prob, delta.detach(), threshold=args.threshold)
            scar_changed_total += assert_scar_unchanged(baseline, refined)
            if not case.t2_present and not case.edema_gt_positive:
                no_t2_new_total += int(((refined == 4) & (baseline != 4)).sum().detach().cpu())
            losses.append(float(loss.detach().cpu()))
        train_rows.append(
            {
                "epoch": epoch + 1,
                "mean_loss": float(np.mean(losses)),
                "max_loss": float(np.max(losses)),
                "loss_is_finite": bool(np.isfinite(losses).all()),
                "scar_changed_voxels_train_patches": scar_changed_total,
                "no_t2_new_edema_voxels_train_patches": no_t2_new_total,
            }
        )
    write_csv(OUT_ROOT / "round10_refiner_train_log.csv", train_rows)
    ckpt_dir = OUT_ROOT / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "args": vars(args)}, ckpt_dir / f"{args.run_name}.pt")

    pred_dir = OUT_ROOT / "predictions" / args.run_name / "validation"
    residual_rows = export_validation_predictions(model, val_cases, cache, pred_dir, device, args.threshold)
    write_csv(OUT_ROOT / "residual_magnitude_summary.csv", residual_rows)

    if not args.skip_eval:
        subprocess.run(
            [
                str(REPO_ROOT / "envs/env_CARE/bin/python"),
                str(REPO_ROOT / "scripts/diagnostics/laneA_round10_refiner_eval.py"),
                "--candidate-pred-dir",
                str(pred_dir),
                "--metrics-name",
                "round10_fold0_very_short_metrics.csv",
            ],
            cwd=str(REPO_ROOT),
            check=True,
        )
    print(f"Wrote predictions to {pred_dir}")


if __name__ == "__main__":
    main()
