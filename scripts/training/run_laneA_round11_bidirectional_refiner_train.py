#!/usr/bin/env python3
"""Run Lane A Round11 bidirectional edema refiner smokes/training.

The model is refiner-only: it reads existing nnU-Net501 probabilities and raw
modalities, changes only class_4 edema, and keeps class_5 scar immutable.
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import subprocess
import sys
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner/mpl_cache"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round10_refiner_eval as r10_eval
from scripts.diagnostics import laneA_round4_fold0_short_train_eval as base_eval
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, write_csv
from src.care_myocardium.refiner.laneA_round11_model import (
    BidirectionalEdemaResidualRefiner,
    assert_scar_unchanged,
    bidirectional_edema_logit,
    fuse_component_safe_bidirectional,
    split_add_remove_delta,
)


OUT_ROOT = REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round11_component_safe_refiner"
EDEMA = 4
SCAR = 5


def component_count(mask: np.ndarray) -> int:
    _, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


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
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    features, target, baseline, _ = cache.get(case)
    coords = np.argwhere(target > 0)
    if len(coords) and rng.random() < 0.80:
        center = tuple(int(x) for x in coords[rng.randrange(len(coords))])
    else:
        baseline_edema = np.argwhere(baseline == EDEMA)
        if len(baseline_edema):
            center = tuple(int(x) for x in baseline_edema[rng.randrange(len(baseline_edema))])
        else:
            center = tuple(int(rng.randrange(s)) for s in target.shape)
    slices = crop_slices(target.shape, center, patch_shape)
    feat = crop_or_pad(features, slices, patch_shape)
    tgt = crop_or_pad(target, slices, patch_shape)
    base = crop_or_pad(baseline, slices, patch_shape)
    base_prob = feat[4]
    anatomy = feat[-1]
    return (
        torch.from_numpy(feat[None]).float(),
        torch.from_numpy(tgt[None, None]).float(),
        torch.from_numpy(base[None]).long(),
        torch.from_numpy(base_prob[None, None]).float(),
        torch.from_numpy(anatomy[None, None]).float(),
    )


def dice_loss_from_logits(logit: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    prob = torch.sigmoid(logit)
    return 1.0 - (2.0 * (prob * target).sum() + 1e-6) / (prob.sum() + target.sum() + 1e-6)


def loss_fn(
    new_logit: torch.Tensor,
    delta: torch.Tensor,
    target: torch.Tensor,
    baseline: torch.Tensor,
    *,
    t2_present: bool,
) -> torch.Tensor:
    add_delta, remove_delta = split_add_remove_delta(delta)
    if t2_present:
        bce = torch.nn.functional.binary_cross_entropy_with_logits(new_logit, target)
        primary = 0.5 * bce + 0.5 * dice_loss_from_logits(new_logit, target)
        # Penalize removing known true edema more than adding near-boundary edema.
        true_baseline_edema = (baseline[:, None] == EDEMA) & (target > 0.5)
        remove_true = (torch.relu(remove_delta) * true_baseline_edema.float()).mean()
        primary = primary + 0.05 * remove_true
    else:
        # no-T2 empty-GT is weak calibration only, not dense hard negative.
        primary = 0.005 * torch.sigmoid(new_logit).mean()
    residual_reg = 0.01 * delta.abs().mean()
    add_reg = 0.005 * torch.relu(add_delta).mean()
    remove_reg = 0.005 * torch.relu(remove_delta).mean()
    return primary + residual_reg + add_reg + remove_reg


def choose_train_case(t2_cases: list[RefinerCase], no_t2_cases: list[RefinerCase], rng: random.Random) -> RefinerCase:
    if rng.random() < 0.78:
        return t2_cases[rng.randrange(len(t2_cases))]
    return no_t2_cases[rng.randrange(len(no_t2_cases))]


def export_validation_predictions(
    model: BidirectionalEdemaResidualRefiner,
    val_cases: list[RefinerCase],
    cache: LazyCaseCache,
    pred_dir: Path,
    device: torch.device,
    threshold: float,
    add_threshold: float,
    remove_threshold: float,
    fallback_if_component_worse: bool,
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
            anatomy = torch.from_numpy(features[-1][None, None]).float().to(device)
            delta = model(x)
            refined = fuse_component_safe_bidirectional(
                base,
                base_prob,
                delta,
                anatomy,
                t2_present=case.t2_present,
                threshold=threshold,
                add_prob_threshold=add_threshold,
                remove_prob_threshold=remove_threshold,
            )[0].detach().cpu().numpy().astype(np.uint8)
            fallback_applied = False
            if fallback_if_component_worse and component_count(refined == EDEMA) > component_count(baseline == EDEMA):
                refined = baseline.copy()
                fallback_applied = True
            scar_changed = assert_scar_unchanged(base, torch.from_numpy(refined[None]).to(device))
            out = sitk.GetImageFromArray(refined)
            out.CopyInformation(gt_img)
            sitk.WriteImage(out, str(pred_dir / f"{case.case_id}.nii.gz"))
            added = (refined == EDEMA) & (baseline != EDEMA)
            removed = (baseline == EDEMA) & (refined != EDEMA)
            rows.append(
                {
                    "case_id": case.case_id,
                    "center": case.center,
                    "modality_group": case.modality_group,
                    "t2_present": case.t2_present,
                    "edema_gt_positive": case.edema_gt_positive,
                    "delta_abs_mean": float(delta.detach().abs().mean().cpu()),
                    "delta_abs_max": float(delta.detach().abs().max().cpu()),
                    "changed_voxels": int((refined != baseline).sum()),
                    "added_voxels": int(added.sum()),
                    "removed_voxels": int(removed.sum()),
                    "component_fallback_applied": fallback_applied,
                    "scar_changed_voxels": scar_changed,
                    "baseline_edema_voxels": int((baseline == EDEMA).sum()),
                    "refined_edema_voxels": int((refined == EDEMA).sum()),
                }
            )
    return rows


def append_train_commands(command: str) -> None:
    path = OUT_ROOT / "round11_train_commands.txt"
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    path.write_text(existing + command + "\n", encoding="utf-8")


def evaluate_predictions(candidate_pred_dir: Path, metrics_name: str) -> None:
    # Reuse the Round10 evaluator with a temporary output swap would be fragile;
    # keep Round11 evaluation local while preserving the same metric functions.
    from scripts.diagnostics.laneA_round11_component_safe_refiner import (
        BASELINE_MODEL,
        SUBSETS,
        aggregate,
        compare_to_baseline,
        failure_flags,
        md_table,
        scar_guardrail_rows,
    )
    from src.care_myocardium.refiner.laneA_round10_dataset import load_label

    cases = [c for c in build_cases() if c.fold0_split == "val"]
    baseline_rows = base_eval.build_case_rows(base_eval.BASELINE_PRED_DIR, BASELINE_MODEL)
    candidate_rows = []
    scar_rows = []
    for case in cases:
        gt_img, gt = load_label(case.gt_path)
        baseline = base_eval.read_pred(case.prediction_path, gt_img)
        pred = base_eval.read_pred(candidate_pred_dir / f"{case.case_id}.nii.gz", gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        row: dict[str, object] = {
            "model": "candidate_laneA_round11_bidirectional_refiner",
            "case_id": case.case_id,
            "missing_prediction": False,
            "center": case.center,
            "modality_group": case.modality_group,
            "t2_present": case.t2_present,
            "edema_gt_positive": case.edema_gt_positive,
            "scar_gt_positive": case.scar_gt_positive,
        }
        row.update(base_eval.class_metrics(pred, gt, spacing, EDEMA, "myops_edema"))
        row.update(base_eval.class_metrics(pred, gt, spacing, SCAR, "myops_scar"))
        candidate_rows.append(row)
        scar_rows.append(
            {
                "case_id": case.case_id,
                "scar_changed_voxels": int(np.logical_xor(baseline == SCAR, pred == SCAR).sum()),
                "non_edema_changed_voxels": int(((baseline != pred) & (baseline != EDEMA) & (pred != EDEMA)).sum()),
                "changed_voxels_total": int((baseline != pred).sum()),
            }
        )
    write_csv(OUT_ROOT / metrics_name, baseline_rows + candidate_rows)
    subset_rows = []
    for model, rows in [(BASELINE_MODEL, baseline_rows), ("candidate_laneA_round11_bidirectional_refiner", candidate_rows)]:
        for subset in SUBSETS:
            subset_rows.append(aggregate(rows, subset, model))
    comparison = compare_to_baseline(subset_rows, "candidate_laneA_round11_bidirectional_refiner")
    write_csv(OUT_ROOT / "baseline_vs_refiner_by_subset.csv", comparison)
    flags = failure_flags(baseline_rows, candidate_rows, scar_rows)
    write_csv(OUT_ROOT / "case_level_failure_flags.csv", flags)
    write_csv(OUT_ROOT / "scar_unchanged_guardrail_table.csv", scar_rows)
    write_csv(OUT_ROOT / "no_t2_empty_gt_fp_table.csv", [r for r in candidate_rows if r.get("t2_present") is False and r.get("edema_gt_positive") is False])
    write_csv(OUT_ROOT / "centerB_centerC_edema_table.csv", [r for r in candidate_rows if r.get("center") in {"CenterB", "CenterC"}])
    lines = [
        "# Lane A Round11 Bidirectional Refiner Evaluation",
        "",
        *md_table(
            comparison,
            [
                "subset",
                "n",
                "delta_edema_dice",
                "delta_edema_hd95_improvement",
                "delta_edema_component_count_improvement",
                "delta_edema_remote_fp_improvement",
                "delta_scar_dice",
                "delta_scar_hd95_improvement",
            ],
        ),
        "",
        "Failure flags:",
        *[f"- {r['case_id']}: {r['flags']}" for r in flags if r.get("flags")],
    ]
    (OUT_ROOT / "round11_bidirectional_refiner_eval.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_tiny_predictions(cases: list[RefinerCase], candidate_pred_dir: Path) -> None:
    rows: list[dict[str, object]] = []
    for case in cases:
        gt_img, gt = base_eval.read_label(case.gt_path)
        baseline = base_eval.read_pred(case.prediction_path, gt_img)
        pred = base_eval.read_pred(candidate_pred_dir / f"{case.case_id}.nii.gz", gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        base_edema = base_eval.class_metrics(baseline, gt, spacing, EDEMA, "baseline_edema")
        cand_edema = base_eval.class_metrics(pred, gt, spacing, EDEMA, "candidate_edema")
        base_scar = base_eval.class_metrics(baseline, gt, spacing, SCAR, "baseline_scar")
        cand_scar = base_eval.class_metrics(pred, gt, spacing, SCAR, "candidate_scar")
        rows.append(
            {
                "case_id": case.case_id,
                "center": case.center,
                "modality_group": case.modality_group,
                "t2_present": case.t2_present,
                "edema_gt_positive": case.edema_gt_positive,
                "baseline_edema_dice": base_edema["baseline_edema_dice"],
                "candidate_edema_dice": cand_edema["candidate_edema_dice"],
                "delta_edema_dice": r10_eval.delta(cand_edema["candidate_edema_dice"], base_edema["baseline_edema_dice"]),
                "baseline_edema_hd95": base_edema["baseline_edema_hd95"],
                "candidate_edema_hd95": cand_edema["candidate_edema_hd95"],
                "delta_edema_hd95_improvement": r10_eval.delta(
                    cand_edema["candidate_edema_hd95"], base_edema["baseline_edema_hd95"], lower_is_better=True
                ),
                "baseline_edema_component_count": base_edema["baseline_edema_component_count"],
                "candidate_edema_component_count": cand_edema["candidate_edema_component_count"],
                "delta_edema_component_count_improvement": r10_eval.delta(
                    cand_edema["candidate_edema_component_count"], base_edema["baseline_edema_component_count"], lower_is_better=True
                ),
                "baseline_edema_remote_fp": base_edema["baseline_edema_remote_fp"],
                "candidate_edema_remote_fp": cand_edema["candidate_edema_remote_fp"],
                "delta_edema_remote_fp_improvement": r10_eval.delta(
                    cand_edema["candidate_edema_remote_fp"], base_edema["baseline_edema_remote_fp"], lower_is_better=True
                ),
                "delta_scar_dice": r10_eval.delta(cand_scar["candidate_scar_dice"], base_scar["baseline_scar_dice"]),
                "delta_scar_hd95_improvement": r10_eval.delta(
                    cand_scar["candidate_scar_hd95"], base_scar["baseline_scar_hd95"], lower_is_better=True
                ),
                "scar_changed_voxels": int(np.logical_xor(baseline == SCAR, pred == SCAR).sum()),
                "no_t2_new_edema_voxels": int(((pred == EDEMA) & (baseline != EDEMA)).sum())
                if not case.t2_present and not case.edema_gt_positive
                else 0,
            }
        )
    write_csv(OUT_ROOT / "round11_tiny_overfit_metrics.csv", rows)


def selected_tiny_cases(cases: list[RefinerCase]) -> list[RefinerCase]:
    preferred = {"Case2031", "Case3012"}
    selected = [c for c in cases if c.case_id in preferred]
    selected.extend([c for c in cases if c.fold0_split == "val" and c.center == "CenterB" and c.t2_present and c.case_id not in preferred][:1])
    selected.extend([c for c in cases if c.fold0_split == "val" and c.center == "CenterC" and c.t2_present and c.case_id not in preferred][:1])
    selected.extend([c for c in cases if c.fold0_split == "val" and (not c.t2_present) and (not c.edema_gt_positive)][:2])
    return selected


def run_unit_gradient(args: argparse.Namespace) -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    rng = random.Random(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cases = build_cases()
    t2_case = next(c for c in cases if c.case_id == "Case2031")
    no_t2_case = next(c for c in cases if (not c.t2_present) and (not c.edema_gt_positive))
    cache = LazyCaseCache()
    model = BidirectionalEdemaResidualRefiner(in_channels=13, hidden_channels=args.hidden_channels, delta_max=args.delta_max).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr)
    rows = []
    for case in [t2_case, no_t2_case]:
        x, y, baseline, base_prob, anatomy = sample_patch(case, cache, rng, args.patch_shape)
        x = x.to(device)
        y = y.to(device)
        baseline = baseline.to(device)
        base_prob = base_prob.to(device)
        anatomy = anatomy.to(device)
        optim.zero_grad(set_to_none=True)
        delta = model(x)
        new_logit = bidirectional_edema_logit(base_prob, delta)
        loss = loss_fn(new_logit, delta, y, baseline, t2_present=case.t2_present)
        loss.backward()
        grad_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                grad_norm += float(p.grad.detach().norm().cpu())
        refined = fuse_component_safe_bidirectional(
            baseline,
            base_prob,
            delta.detach(),
            anatomy,
            t2_present=case.t2_present,
            add_prob_threshold=args.add_threshold,
            remove_prob_threshold=args.remove_threshold,
        )
        rows.append(
            {
                "case_id": case.case_id,
                "t2_present": case.t2_present,
                "loss": float(loss.detach().cpu()),
                "loss_is_finite": bool(torch.isfinite(loss).detach().cpu()),
                "grad_norm": grad_norm,
                "grad_is_finite": bool(np.isfinite(grad_norm)),
                "scar_changed_voxels": assert_scar_unchanged(baseline, refined),
                "new_no_t2_edema_voxels": int(((refined == EDEMA) & (baseline != EDEMA)).sum().detach().cpu())
                if not case.t2_present
                else 0,
                "add_delta_abs_mean": float(delta[:, 0].detach().abs().mean().cpu()),
                "remove_delta_abs_mean": float(delta[:, 1].detach().abs().mean().cpu()),
            }
        )
    write_csv(OUT_ROOT / "round11_unit_gradient_smoke.csv", rows)
    print(f"Wrote {OUT_ROOT / 'round11_unit_gradient_smoke.csv'}")


def train(args: argparse.Namespace) -> Path:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    append_train_commands(" ".join(sys.argv))
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    rng = random.Random(args.seed)
    torch.set_num_threads(2)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    cases = build_cases()
    if args.mode == "tiny":
        train_cases = selected_tiny_cases(cases)
        val_cases = train_cases
        metrics_path = OUT_ROOT / "round11_tiny_overfit_train_log.csv"
    else:
        train_cases = [c for c in cases if c.fold0_split == "train"]
        val_cases = [c for c in cases if c.fold0_split == "val"]
        metrics_path = OUT_ROOT / "round11_fold0_very_short_train_log.csv"
    t2_cases = [c for c in train_cases if c.t2_present and c.edema_gt_positive]
    no_t2_cases = [c for c in train_cases if (not c.t2_present) and (not c.edema_gt_positive)]
    if not t2_cases or not no_t2_cases:
        raise RuntimeError("Round11 needs both T2-positive and no-T2 empty-GT cases")
    model = BidirectionalEdemaResidualRefiner(in_channels=13, hidden_channels=args.hidden_channels, delta_max=args.delta_max).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    cache = LazyCaseCache()
    config_lines = [
        "candidate: component_safe_bidirectional_edema_refiner_A",
        f"mode: {args.mode}",
        f"run_name: {args.run_name}",
        f"epochs: {args.epochs}",
        f"steps_per_epoch: {args.steps_per_epoch}",
        f"lr: {args.lr}",
        f"hidden_channels: {args.hidden_channels}",
        f"delta_max: {args.delta_max}",
        f"add_threshold: {args.add_threshold}",
        f"remove_threshold: {args.remove_threshold}",
        f"seed: {args.seed}",
        f"patch_shape: {','.join(str(x) for x in args.patch_shape)}",
        "fusion_rule: class_4 edema only; class_5 scar unchanged; no-T2 additions disabled",
        "no_t2_policy: weak calibration only, not dense hard negative",
    ]
    (OUT_ROOT / "round11_train_config.yaml").write_text("\n".join(config_lines) + "\n", encoding="utf-8")
    rows = []
    model.train()
    for epoch in range(args.epochs):
        losses = []
        scar_changed_total = 0
        no_t2_new_total = 0
        added_total = 0
        removed_total = 0
        for _ in range(args.steps_per_epoch):
            case = choose_train_case(t2_cases, no_t2_cases, rng)
            x, y, baseline, base_prob, anatomy = sample_patch(case, cache, rng, args.patch_shape)
            x = x.to(device)
            y = y.to(device)
            baseline = baseline.to(device)
            base_prob = base_prob.to(device)
            anatomy = anatomy.to(device)
            optim.zero_grad(set_to_none=True)
            delta = model(x)
            new_logit = bidirectional_edema_logit(base_prob, delta)
            loss = loss_fn(new_logit, delta, y, baseline, t2_present=case.t2_present)
            loss.backward()
            optim.step()
            refined = fuse_component_safe_bidirectional(
                baseline,
                base_prob,
                delta.detach(),
                anatomy,
                t2_present=case.t2_present,
                add_prob_threshold=args.add_threshold,
                remove_prob_threshold=args.remove_threshold,
            )
            scar_changed_total += assert_scar_unchanged(baseline, refined)
            added = (refined == EDEMA) & (baseline != EDEMA)
            removed = (baseline == EDEMA) & (refined != EDEMA)
            added_total += int(added.sum().detach().cpu())
            removed_total += int(removed.sum().detach().cpu())
            if not case.t2_present and not case.edema_gt_positive:
                no_t2_new_total += int(added.sum().detach().cpu())
            losses.append(float(loss.detach().cpu()))
        rows.append(
            {
                "epoch": epoch + 1,
                "mean_loss": float(mean(losses)),
                "max_loss": float(max(losses)),
                "loss_is_finite": bool(np.isfinite(losses).all()),
                "scar_changed_voxels_train_patches": scar_changed_total,
                "no_t2_new_edema_voxels_train_patches": no_t2_new_total,
                "added_voxels_train_patches": added_total,
                "removed_voxels_train_patches": removed_total,
            }
        )
    write_csv(metrics_path, rows)
    ckpt_dir = OUT_ROOT / "checkpoints"
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    torch.save({"model_state_dict": model.state_dict(), "args": vars(args)}, ckpt_dir / f"{args.run_name}.pt")
    pred_dir = OUT_ROOT / "predictions" / args.run_name / ("tiny" if args.mode == "tiny" else "validation")
    residual_rows = export_validation_predictions(
        model,
        val_cases,
        cache,
        pred_dir,
        device,
        threshold=args.threshold,
        add_threshold=args.add_threshold,
        remove_threshold=args.remove_threshold,
        fallback_if_component_worse=not args.disable_component_fallback,
    )
    write_csv(OUT_ROOT / "round11_bidirectional_residual_summary.csv", residual_rows)
    if args.mode == "train" and not args.skip_eval:
        evaluate_predictions(pred_dir, "round11_fold0_very_short_metrics.csv")
    if args.mode == "tiny":
        evaluate_tiny_predictions(val_cases, pred_dir)
    return pred_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["unit", "tiny", "train"], default="unit")
    parser.add_argument("--run-name", default="laneA_r11_bidirectional_edema_refiner_fold0_very_short")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--steps-per-epoch", type=int, default=40)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--hidden-channels", type=int, default=16)
    parser.add_argument("--delta-max", type=float, default=1.0)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument("--add-threshold", type=float, default=0.5)
    parser.add_argument("--remove-threshold", type=float, default=0.45)
    parser.add_argument("--disable-component-fallback", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--patch-shape", default="8,128,128")
    parser.add_argument("--skip-eval", action="store_true")
    args = parser.parse_args()
    args.patch_shape = tuple(int(x) for x in str(args.patch_shape).split(","))
    if len(args.patch_shape) != 3:
        raise ValueError("--patch-shape must have three comma-separated integers")
    if args.mode == "unit":
        run_unit_gradient(args)
    else:
        pred_dir = train(args)
        print(f"Wrote predictions to {pred_dir}")


if __name__ == "__main__":
    main()
