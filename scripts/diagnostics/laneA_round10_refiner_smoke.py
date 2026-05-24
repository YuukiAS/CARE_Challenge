#!/usr/bin/env python3
"""Lane A Round10 refiner unit/gradient and tiny-overfit safety smoke."""

from __future__ import annotations

import csv
import math
import os
import random
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
import torch

from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, write_csv
from src.care_myocardium.refiner.laneA_round10_model import (
    ConservativeEdemaResidualRefiner,
    assert_scar_unchanged,
    fuse_edema_only_from_prob,
    refined_edema_logit,
)


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round10_edema_refiner"
PATCH_SHAPE = (8, 128, 128)
SEED = 42


def crop_slices(shape: tuple[int, int, int], center: tuple[int, int, int], patch_shape: tuple[int, int, int]) -> tuple[slice, slice, slice]:
    slices = []
    for size, c, patch in zip(shape, center, patch_shape):
        if size <= patch:
            start = 0
        else:
            start = max(0, min(int(c) - patch // 2, size - patch))
        slices.append(slice(start, min(start + patch, size)))
    return tuple(slices)  # type: ignore[return-value]


def crop_or_pad(arr: np.ndarray, slices: tuple[slice, slice, slice], patch_shape: tuple[int, int, int]) -> np.ndarray:
    spatial = arr[slices] if arr.ndim == 3 else arr[(slice(None), *slices)]
    out_shape = patch_shape if arr.ndim == 3 else (arr.shape[0], *patch_shape)
    out = np.zeros(out_shape, dtype=arr.dtype)
    insert = tuple(slice(0, s) for s in spatial.shape[-3:])
    if arr.ndim == 3:
        out[insert] = spatial
    else:
        out[(slice(None), *insert)] = spatial
    return out


def select_cases(cases: list[RefinerCase]) -> list[RefinerCase]:
    def first(pred):
        for case in cases:
            if case.fold0_split == "train" and pred(case):
                return case
        raise RuntimeError("required tiny smoke case not found")

    selected = [
        first(lambda c: c.center == "CenterB" and c.t2_present and c.edema_gt_positive),
        first(lambda c: c.center == "CenterC" and c.t2_present and c.edema_gt_positive),
        first(lambda c: c.modality_group == "LGE-only" and (not c.t2_present) and (not c.edema_gt_positive)),
        first(lambda c: c.modality_group == "C0+LGE" and (not c.t2_present) and (not c.edema_gt_positive)),
    ]
    dedup: dict[str, RefinerCase] = {}
    for case in selected:
        dedup[case.case_id] = case
    return list(dedup.values())


def patch_from_case(case: RefinerCase, *, rng: random.Random) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, dict[str, object]]:
    features, target, baseline, _ = load_case_features(case)
    if target.any():
        coords = np.argwhere(target > 0)
        center = tuple(int(x) for x in coords[rng.randrange(len(coords))])
    else:
        baseline_edema = np.argwhere(baseline == 4)
        if len(baseline_edema):
            center = tuple(int(x) for x in baseline_edema[rng.randrange(len(baseline_edema))])
        else:
            center = tuple(int(rng.randrange(s)) for s in target.shape)
    slices = crop_slices(target.shape, center, PATCH_SHAPE)
    feat = crop_or_pad(features, slices, PATCH_SHAPE)
    tgt = crop_or_pad(target, slices, PATCH_SHAPE)
    base = crop_or_pad(baseline, slices, PATCH_SHAPE)
    base_prob = feat[4]
    meta = {
        "case_id": case.case_id,
        "center": case.center,
        "modality_group": case.modality_group,
        "t2_present": case.t2_present,
        "edema_gt_positive": case.edema_gt_positive,
        "patch_gt_edema_voxels": int(tgt.sum()),
        "patch_baseline_edema_voxels": int((base == 4).sum()),
    }
    return (
        torch.from_numpy(feat[None]).float(),
        torch.from_numpy(tgt[None, None]).float(),
        torch.from_numpy(base[None]).long(),
        torch.from_numpy(base_prob[None, None]).float(),
        meta,
    )


def dice_from_masks(pred: torch.Tensor, target: torch.Tensor) -> float:
    pred_f = pred.float()
    target_f = target.float()
    denom = float(pred_f.sum().item() + target_f.sum().item())
    if denom == 0:
        return 1.0
    return float((2.0 * (pred_f * target_f).sum().item()) / denom)


def loss_fn(new_logit: torch.Tensor, delta: torch.Tensor, target: torch.Tensor, *, t2_present: bool) -> torch.Tensor:
    if t2_present:
        bce = torch.nn.functional.binary_cross_entropy_with_logits(new_logit, target)
        prob = torch.sigmoid(new_logit)
        inter = (prob * target).sum()
        dice = 1.0 - (2.0 * inter + 1e-6) / (prob.sum() + target.sum() + 1e-6)
        primary = 0.5 * bce + 0.5 * dice
    else:
        # Weak no-T2 calibration only; this is intentionally not a strong dense
        # negative objective.
        primary = 0.02 * torch.sigmoid(new_logit).mean()
    return primary + 0.01 * delta.abs().mean()


def write_config() -> None:
    (OUT_ROOT / "round10_refiner_config.yaml").write_text(
        "\n".join(
            [
                "candidate: conservative_edema_residual_refiner_A",
                "input_channels: 13",
                "feature_channel_order:",
                "  - baseline_prob_0",
                "  - baseline_prob_1",
                "  - baseline_prob_2",
                "  - baseline_prob_3",
                "  - baseline_prob_4_edema",
                "  - baseline_prob_5_scar",
                "  - C0_or_zero",
                "  - LGE_or_zero",
                "  - T2_or_zero",
                "  - C0_present",
                "  - LGE_present",
                "  - T2_present",
                "  - baseline_anatomy_support_prob_1_2_3",
                "delta_max: 1.0",
                "fusion_rule: class_4 edema only; class_5 scar unchanged by construction",
                "t2_present_loss: 0.5 * BCE(new_edema_logit, gt_edema) + 0.5 * soft_dice + 0.01 * L1(delta)",
                "no_t2_loss: 0.02 * mean(sigmoid(new_edema_logit)) + 0.01 * L1(delta)",
                "threshold: 0.5",
                "baseline_source: existing nnU-Net501 OOF probabilities for train rows, fold0 probabilities for val rows",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    write_config()
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    rng = random.Random(SEED)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.set_num_threads(2)
    cases = select_cases(build_cases())
    model = ConservativeEdemaResidualRefiner(in_channels=13, hidden_channels=12, delta_max=1.0).to(device)
    optim = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)

    smoke_rows: list[dict[str, object]] = []
    for case in cases:
        x, y, baseline, baseline_edema_prob, meta = patch_from_case(case, rng=rng)
        x = x.to(device)
        y = y.to(device)
        baseline = baseline.to(device)
        baseline_edema_prob = baseline_edema_prob.to(device)
        optim.zero_grad(set_to_none=True)
        delta = model(x)
        new_logit = refined_edema_logit(baseline_edema_prob, delta)
        loss = loss_fn(new_logit, delta, y, t2_present=case.t2_present)
        loss.backward()
        grad_norm = 0.0
        for param in model.parameters():
            if param.grad is not None:
                grad_norm += float(param.grad.detach().norm().cpu())
        optim.step()
        refined = fuse_edema_only_from_prob(baseline, baseline_edema_prob, delta.detach())
        scar_changed = assert_scar_unchanged(baseline, refined)
        smoke_rows.append(
            {
                **meta,
                "stage": "one_batch_gradient",
                "loss": float(loss.detach().cpu()),
                "loss_is_finite": bool(torch.isfinite(loss).detach().cpu()),
                "grad_norm": grad_norm,
                "delta_abs_mean": float(delta.detach().abs().mean().cpu()),
                "delta_abs_max": float(delta.detach().abs().max().cpu()),
                "scar_changed_voxels": scar_changed,
                "baseline_edema_voxels": int((baseline == 4).sum().detach().cpu()),
                "refined_edema_voxels": int((refined == 4).sum().detach().cpu()),
            }
        )

    write_csv(OUT_ROOT / "round10_unit_gradient_smoke.csv", smoke_rows)

    # Tiny-overfit safety screen on the same required case mix.
    tiny_rows: list[dict[str, object]] = []
    for step in range(30):
        case = cases[step % len(cases)]
        x, y, baseline, baseline_edema_prob, meta = patch_from_case(case, rng=rng)
        x = x.to(device)
        y = y.to(device)
        baseline = baseline.to(device)
        baseline_edema_prob = baseline_edema_prob.to(device)
        optim.zero_grad(set_to_none=True)
        delta = model(x)
        new_logit = refined_edema_logit(baseline_edema_prob, delta)
        loss = loss_fn(new_logit, delta, y, t2_present=case.t2_present)
        loss.backward()
        optim.step()
        refined = fuse_edema_only_from_prob(baseline, baseline_edema_prob, delta.detach())
        baseline_edema = baseline == 4
        refined_edema = refined == 4
        gt_edema = y[:, 0] > 0.5
        tiny_rows.append(
            {
                **meta,
                "step": step + 1,
                "loss": float(loss.detach().cpu()),
                "loss_is_finite": bool(torch.isfinite(loss).detach().cpu()),
                "baseline_patch_edema_dice": dice_from_masks(baseline_edema, gt_edema),
                "refined_patch_edema_dice": dice_from_masks(refined_edema, gt_edema),
                "delta_patch_edema_dice": dice_from_masks(refined_edema, gt_edema) - dice_from_masks(baseline_edema, gt_edema),
                "baseline_edema_voxels": int(baseline_edema.sum().detach().cpu()),
                "refined_edema_voxels": int(refined_edema.sum().detach().cpu()),
                "new_edema_voxels": int((refined_edema & (~baseline_edema)).sum().detach().cpu()),
                "scar_changed_voxels": assert_scar_unchanged(baseline, refined),
                "delta_abs_mean": float(delta.detach().abs().mean().cpu()),
                "delta_abs_max": float(delta.detach().abs().max().cpu()),
            }
        )
    write_csv(OUT_ROOT / "round10_tiny_overfit_metrics.csv", tiny_rows)

    residual_rows = [
        {
            "stage": "tiny_overfit",
            "n_rows": len(tiny_rows),
            "delta_abs_mean_avg": float(np.mean([float(r["delta_abs_mean"]) for r in tiny_rows])),
            "delta_abs_max_max": float(np.max([float(r["delta_abs_max"]) for r in tiny_rows])),
            "scar_changed_total": int(sum(int(r["scar_changed_voxels"]) for r in tiny_rows)),
            "no_t2_new_edema_voxels_total": int(
                sum(int(r["new_edema_voxels"]) for r in tiny_rows if str(r["t2_present"]).lower() == "false")
            ),
        }
    ]
    write_csv(OUT_ROOT / "residual_magnitude_summary.csv", residual_rows)
    any_fail = (
        any(not bool(r["loss_is_finite"]) for r in smoke_rows + tiny_rows)
        or any(int(r["scar_changed_voxels"]) != 0 for r in smoke_rows + tiny_rows)
        or residual_rows[0]["no_t2_new_edema_voxels_total"] > 0
        or not math.isfinite(float(residual_rows[0]["delta_abs_max_max"]))
    )
    decision = "pass_tiny_refiner_safety_gate" if not any_fail else "fail_tiny_refiner_safety_gate"
    with (OUT_ROOT / "round10_decision_table.md").open("w", encoding="utf-8") as f:
        f.write("# Lane A Round10 Decision Table\n\n")
        f.write(f"- Current gate: `{decision}`\n")
        f.write("- Completed: cache manifest, one-batch gradient smoke, tiny-overfit safety screen.\n")
        f.write("- Not completed yet: fold0 very-short refiner training, fold0 short/longer training.\n")
        f.write("- Prohibited still: validation zip, upload, fold1-4, whole-network fine-tune, external repo training.\n")
    print(f"Decision: {decision}")


if __name__ == "__main__":
    main()
