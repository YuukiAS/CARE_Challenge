#!/usr/bin/env python3
"""Round16 first-party external-mechanism-inspired fold0 very-short runner.

This runner is for R16_A/R16_C/R16_E/R16_F only. It trains a tiny edema-only
feature model on fold0 train samples and exports fold0 validation predictions
for local gate evaluation. It preserves class_5 scar from the nnU-Net501
baseline, falls back to baseline for no-T2 cases, and writes outputs only under
the Round16 diagnostics root.

It does not modify nnU-Net caches, train external repositories, download
weights, create validation zips, upload, or expand to fold1-4.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
import torch
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round16_external_mechanism_integration"
os.environ.setdefault("MPLCONFIGDIR", str(OUT_ROOT / "mpl_cache"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagnostics import laneA_round4_fold0_short_train_eval as eval4
from scripts.diagnostics.laneA_round16_first_party_smoke import SmallModalityConditionedHead, feature_maps
from src.care_myocardium.calibrator.laneA_round14_model import VoxelFeatureCalibrator
from src.care_myocardium.refiner.laneA_round10_dataset import RefinerCase, build_cases, load_case_features, write_csv


EDEMA = 4
SCAR = 5
SEED = 16016
SUBSETS = [
    "all_case",
    "t2_present",
    "t2_present_gt_positive",
    "complete_modality",
    "CenterB",
    "CenterC",
    "no_t2_empty_gt",
    "modality:C0+LGE+T2",
    "modality:C0+LGE",
    "modality:LGE-only",
]

FEATURE_SETS = {
    "R16_A_care_strong_t2_lge_intensity_prior_fold0_vs": {
        "model_kind": "VoxelFeatureCalibrator",
        "auxiliary": "none",
        "features": [
            "baseline_edema_prob",
            "baseline_scar_prob",
            "t2_support",
            "t2_local_mean",
            "lge_support",
            "lge_local_mean",
            "t2_lge_contrast",
            "local_t2_lge_contrast",
            "entropy",
            "edema_margin",
            "t2_present",
        ],
    },
    "R16_C_anatomy_pathology_cascade_care_fold0_vs": {
        "model_kind": "VoxelFeatureCalibrator",
        "auxiliary": "soft_anatomy_feature_only",
        "features": [
            "baseline_edema_prob",
            "baseline_scar_prob",
            "t2_support",
            "t2_local_mean",
            "lge_support",
            "t2_lge_contrast",
            "anatomy_support",
            "support_score",
            "entropy",
            "edema_margin",
            "t2_present",
        ],
    },
    "R16_E_intensity_plus_component_surface_aux_fold0_vs": {
        "model_kind": "VoxelFeatureCalibrator",
        "auxiliary": "logit_l2_boundary_proxy_weight_1e-4",
        "features": [
            "baseline_edema_prob",
            "baseline_scar_prob",
            "t2_support",
            "t2_local_mean",
            "lge_support",
            "t2_lge_contrast",
            "anatomy_support",
            "support_score",
            "entropy",
            "edema_margin",
            "t2_present",
        ],
    },
    "R16_F_small_modality_conditioned_moe_fold0_vs": {
        "model_kind": "SmallModalityConditionedHead",
        "auxiliary": "modality_conditioned_gate",
        "features": [
            "baseline_edema_prob",
            "baseline_scar_prob",
            "t2_support",
            "lge_support",
            "anatomy_support",
            "entropy",
            "edema_margin",
            "c0_present",
            "lge_present",
            "t2_present",
        ],
    },
}


def finite(values: list[object]) -> list[float]:
    out = []
    for value in values:
        try:
            v = float(value)
        except (TypeError, ValueError):
            continue
        if not math.isnan(v) and not math.isinf(v):
            out.append(v)
    return out


def avg(values: list[object]) -> float | None:
    vals = finite(values)
    return float(mean(vals)) if vals else None


def delta(candidate: object, baseline: object, *, lower_is_better: bool = False) -> float | None:
    try:
        c = float(candidate)
        b = float(baseline)
    except (TypeError, ValueError):
        return None
    if math.isnan(c) or math.isnan(b) or math.isinf(c) or math.isinf(b):
        return None
    return b - c if lower_is_better else c - b


def subset_filter(name: str):
    if name == "all_case":
        return lambda r: True
    if name == "t2_present":
        return lambda r: r.get("t2_present") is True
    if name == "t2_present_gt_positive":
        return lambda r: r.get("t2_present") is True and r.get("edema_gt_positive") is True
    if name == "complete_modality":
        return lambda r: r.get("modality_group") == "C0+LGE+T2"
    if name == "CenterB":
        return lambda r: r.get("center") == "CenterB"
    if name == "CenterC":
        return lambda r: r.get("center") == "CenterC"
    if name == "no_t2_empty_gt":
        return lambda r: r.get("t2_present") is False and r.get("edema_gt_positive") is False
    if name.startswith("modality:"):
        group = name.split(":", 1)[1]
        return lambda r: r.get("modality_group") == group
    raise ValueError(name)


def aggregate_subset(rows: list[dict[str, object]], subset: str, model: str) -> dict[str, object]:
    filt = subset_filter(subset)
    items = [r for r in rows if r["model"] == model and not r.get("missing_prediction") and filt(r)]
    return {
        "model": model,
        "subset": subset,
        "n": len(items),
        "myops_edema_dice": avg([r.get("myops_edema_dice") for r in items]),
        "myops_edema_hd": avg([r.get("myops_edema_hd") for r in items]),
        "myops_edema_hd95": avg([r.get("myops_edema_hd95") for r in items]),
        "myops_edema_component_count": avg([r.get("myops_edema_component_count") for r in items]),
        "myops_edema_small_fp": avg([r.get("myops_edema_small_fp") for r in items]),
        "myops_edema_remote_fp": avg([r.get("myops_edema_remote_fp") for r in items]),
        "myops_edema_pred_gt_volume_ratio": avg([r.get("myops_edema_pred_gt_volume_ratio") for r in items]),
        "myops_scar_dice": avg([r.get("myops_scar_dice") for r in items]),
        "myops_scar_hd": avg([r.get("myops_scar_hd") for r in items]),
        "myops_scar_hd95": avg([r.get("myops_scar_hd95") for r in items]),
    }


def stack_feature_array(features: np.ndarray, names: list[str]) -> np.ndarray:
    maps = feature_maps(features)
    return np.stack([maps[name].astype(np.float32, copy=False) for name in names], axis=0)


def sample_case(
    case: RefinerCase,
    names: list[str],
    *,
    max_pos: int,
    max_neg: int,
    rng: np.random.Generator,
    no_t2_weight: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    features, target, _baseline, _gt_img = load_case_features(case)
    x_full = stack_feature_array(features, names)
    target_bool = target.astype(bool)
    pos = np.flatnonzero(target_bool.ravel())
    neg = np.flatnonzero(~target_bool.ravel())
    if pos.size:
        pos = rng.choice(pos, size=min(max_pos, pos.size), replace=False)
    if neg.size:
        neg = rng.choice(neg, size=min(max_neg, neg.size), replace=False)
    idx = np.concatenate([pos, neg])
    if idx.size == 0:
        return (
            np.empty((0, len(names)), np.float32),
            np.empty((0,), np.float32),
            np.empty((0,), np.float32),
            np.empty((0, 3), np.float32),
        )
    rng.shuffle(idx)
    x = x_full.reshape((len(names), -1)).T[idx]
    y = target_bool.ravel()[idx].astype(np.float32)
    weight_value = no_t2_weight if (not case.t2_present and not case.edema_gt_positive) else 1.0
    weights = np.full(y.shape, weight_value, dtype=np.float32)
    modality = np.stack([features[9].ravel()[idx], features[10].ravel()[idx], features[11].ravel()[idx]], axis=1).astype(np.float32)
    return x.astype(np.float32, copy=False), y, weights, modality


def build_train_samples(
    cases: list[RefinerCase],
    names: list[str],
    max_cases: int | None,
    no_t2_weight: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(SEED)
    train_cases = [c for c in cases if c.fold0_split == "train"]
    if max_cases is not None:
        train_cases = train_cases[:max_cases]
    xs, ys, ws, ms, used = [], [], [], [], []
    for case in train_cases:
        if case.t2_present:
            max_pos, max_neg = 1024, 1024
        else:
            max_pos, max_neg = 0, 256
        x, y, w, m = sample_case(case, names, max_pos=max_pos, max_neg=max_neg, rng=rng, no_t2_weight=no_t2_weight)
        if x.size == 0:
            continue
        xs.append(x)
        ys.append(y)
        ws.append(w)
        ms.append(m)
        used.append(case.case_id)
    if not xs:
        raise RuntimeError("no training samples built")
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(ws), np.concatenate(ms), used


def make_model(model_kind: str, in_features: int) -> nn.Module:
    if model_kind == "SmallModalityConditionedHead":
        return SmallModalityConditionedHead(in_features, hidden_features=24)
    return VoxelFeatureCalibrator(in_features, hidden_features=24)


def model_logits(model: nn.Module, model_kind: str, x: torch.Tensor, modality: torch.Tensor) -> torch.Tensor:
    if model_kind == "SmallModalityConditionedHead":
        return model(x, modality)  # type: ignore[misc]
    return model(x)


def compute_loss(
    logits: torch.Tensor,
    y: torch.Tensor,
    w: torch.Tensor,
    auxiliary: str,
) -> tuple[torch.Tensor, torch.Tensor]:
    loss_raw = nn.functional.binary_cross_entropy_with_logits(logits, y, reduction="none")
    loss = torch.sum(loss_raw * w) / torch.clamp(w.sum(), min=1.0)
    aux_loss = torch.tensor(0.0, device=logits.device)
    if auxiliary == "logit_l2_boundary_proxy_weight_1e-4":
        aux_loss = 1e-4 * torch.mean(logits.square())
        loss = loss + aux_loss
    return loss, aux_loss


def train_model(
    x_np: np.ndarray,
    y_np: np.ndarray,
    w_np: np.ndarray,
    modality_np: np.ndarray,
    *,
    model_kind: str,
    auxiliary: str,
    epochs: int,
    device: str,
) -> tuple[nn.Module, list[dict[str, object]]]:
    torch.manual_seed(SEED)
    model = make_model(model_kind, x_np.shape[1]).to(device)
    x = torch.from_numpy(x_np).to(device)
    y = torch.from_numpy(y_np).to(device)
    w = torch.from_numpy(w_np).to(device)
    modality = torch.from_numpy(modality_np).to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-3, weight_decay=1e-4)
    rows = []
    for epoch in range(epochs):
        opt.zero_grad(set_to_none=True)
        logits = model_logits(model, model_kind, x, modality)
        loss, aux_loss = compute_loss(logits, y, w, auxiliary)
        loss.backward()
        grad_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                grad_norm += float(p.grad.detach().norm().cpu())
        opt.step()
        rows.append(
            {
                "epoch": epoch,
                "loss": float(loss.detach().cpu()),
                "auxiliary_loss": float(aux_loss.detach().cpu()),
                "grad_norm": grad_norm,
                "nan_or_inf": (not math.isfinite(float(loss.detach().cpu()))) or (not math.isfinite(grad_norm)),
            }
        )
    return model, rows


def resolve_device(requested: str) -> str:
    if requested != "cuda":
        return requested
    if not torch.cuda.is_available():
        print("Requested cuda but CUDA is unavailable; falling back to cpu", flush=True)
        return "cpu"
    major, minor = torch.cuda.get_device_capability(0)
    if (major, minor) < (7, 5):
        print(f"Requested cuda but device capability {major}.{minor} is unsupported by this PyTorch build; falling back to cpu", flush=True)
        return "cpu"
    return requested


def infer_case(
    model: nn.Module,
    case: RefinerCase,
    names: list[str],
    *,
    model_kind: str,
    device: str,
    threshold: float,
) -> tuple[sitk.Image, np.ndarray, dict[str, object]]:
    features, _target, baseline_seg, gt_img = load_case_features(case)
    x_full = stack_feature_array(features, names)
    flat_np = x_full.reshape((len(names), -1)).T.astype(np.float32, copy=False)
    modality_np = np.stack([features[9].ravel(), features[10].ravel(), features[11].ravel()], axis=1).astype(np.float32)
    flat = torch.from_numpy(flat_np).to(device)
    modality = torch.from_numpy(modality_np).to(device)
    probs = []
    model.eval()
    with torch.no_grad():
        start = 0
        for chunk in torch.split(flat, 262144):
            mod_chunk = modality[start : start + chunk.shape[0]]
            probs.append(torch.sigmoid(model_logits(model, model_kind, chunk, mod_chunk)).detach().cpu())
            start += chunk.shape[0]
    score = torch.cat(probs).numpy().reshape(baseline_seg.shape)
    refined = baseline_seg.copy()
    if not case.t2_present:
        changed = 0
    else:
        accept = (score >= threshold) & (baseline_seg != SCAR)
        refined[(baseline_seg == EDEMA) & (score < 0.25)] = 0
        refined[accept] = EDEMA
        refined[baseline_seg == SCAR] = SCAR
        changed = int(np.sum(refined != baseline_seg))
    scar_changed = int(np.sum((refined == SCAR) != (baseline_seg == SCAR)))
    info = {
        "case_id": case.case_id,
        "fold0_split": case.fold0_split,
        "center": case.center,
        "modality_group": case.modality_group,
        "T2_present": case.t2_present,
        "edema_gt_positive": case.edema_gt_positive,
        "changed_voxels": changed,
        "scar_changed_voxels": scar_changed,
        "score_mean": float(np.mean(score)),
        "score_p95": float(np.percentile(score, 95)),
        "threshold": threshold,
    }
    return gt_img, refined.astype(np.uint8, copy=False), info


def write_prediction(path: Path, reference: sitk.Image, arr: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = sitk.GetImageFromArray(arr)
    img.CopyInformation(reference)
    sitk.WriteImage(img, str(path))


def compare_rows(all_rows: list[dict[str, object]], candidate_model: str) -> list[dict[str, object]]:
    metrics = []
    for model in ["baseline_nnunet501_fold0", candidate_model]:
        for subset in SUBSETS:
            metrics.append(aggregate_subset(all_rows, subset, model))
    by_key = {(r["model"], r["subset"]): r for r in metrics}
    out = []
    for subset in SUBSETS:
        b = by_key[("baseline_nnunet501_fold0", subset)]
        c = by_key[(candidate_model, subset)]
        out.append(
            {
                "candidate_id": candidate_model,
                "subset": subset,
                "n": c["n"],
                "baseline_edema_dice": b["myops_edema_dice"],
                "candidate_edema_dice": c["myops_edema_dice"],
                "delta_edema_dice": delta(c["myops_edema_dice"], b["myops_edema_dice"]),
                "baseline_edema_hd95": b["myops_edema_hd95"],
                "candidate_edema_hd95": c["myops_edema_hd95"],
                "delta_edema_hd95_improvement": delta(c["myops_edema_hd95"], b["myops_edema_hd95"], lower_is_better=True),
                "baseline_edema_component_count": b["myops_edema_component_count"],
                "candidate_edema_component_count": c["myops_edema_component_count"],
                "delta_edema_component_count_improvement": delta(c["myops_edema_component_count"], b["myops_edema_component_count"], lower_is_better=True),
                "baseline_edema_remote_fp": b["myops_edema_remote_fp"],
                "candidate_edema_remote_fp": c["myops_edema_remote_fp"],
                "delta_edema_remote_fp_improvement": delta(c["myops_edema_remote_fp"], b["myops_edema_remote_fp"], lower_is_better=True),
                "baseline_scar_dice": b["myops_scar_dice"],
                "candidate_scar_dice": c["myops_scar_dice"],
                "delta_scar_dice": delta(c["myops_scar_dice"], b["myops_scar_dice"]),
                "baseline_scar_hd95": b["myops_scar_hd95"],
                "candidate_scar_hd95": c["myops_scar_hd95"],
                "delta_scar_hd95_improvement": delta(c["myops_scar_hd95"], b["myops_scar_hd95"], lower_is_better=True),
            }
        )
    return out


def delta_float(value: object) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0.0
    return 0.0 if math.isnan(v) or math.isinf(v) else v


def failure_flags(all_rows: list[dict[str, object]], candidate_model: str) -> list[dict[str, object]]:
    by_case: dict[str, dict[str, dict[str, object]]] = {}
    for row in all_rows:
        by_case.setdefault(str(row["case_id"]), {})[str(row["model"])] = row
    out = []
    for cid, pair in sorted(by_case.items()):
        b = pair.get("baseline_nnunet501_fold0")
        c = pair.get(candidate_model)
        if not b or not c:
            out.append({"candidate_id": candidate_model, "case_id": cid, "flags": "missing_baseline_or_candidate"})
            continue
        flags = []
        ed_dice_delta = delta(c.get("myops_edema_dice"), b.get("myops_edema_dice"))
        ed_hd95_delta = delta(c.get("myops_edema_hd95"), b.get("myops_edema_hd95"), lower_is_better=True)
        comp_delta = delta(c.get("myops_edema_component_count"), b.get("myops_edema_component_count"), lower_is_better=True)
        remote_delta = delta(c.get("myops_edema_remote_fp"), b.get("myops_edema_remote_fp"), lower_is_better=True)
        scar_dice_delta = delta(c.get("myops_scar_dice"), b.get("myops_scar_dice"))
        scar_hd95_delta = delta(c.get("myops_scar_hd95"), b.get("myops_scar_hd95"), lower_is_better=True)
        if ed_dice_delta is not None and ed_dice_delta > 0.005 and ed_hd95_delta is not None and ed_hd95_delta < -0.5:
            flags.append("edema_dice_up_hd95_worse")
        if comp_delta is not None and comp_delta < -0.5:
            flags.append("edema_component_worse")
        if remote_delta is not None and remote_delta < 0:
            flags.append("edema_remote_fp_worse")
        if scar_dice_delta is not None and scar_dice_delta < -0.02:
            flags.append("scar_dice_guardrail_drop")
        if scar_hd95_delta is not None and scar_hd95_delta < -1.0:
            flags.append("scar_hd95_guardrail_worse")
        if c.get("t2_present") is False and c.get("edema_gt_positive") is False:
            if float(c.get("myops_edema_component_count") or 0) > float(b.get("myops_edema_component_count") or 0):
                flags.append("no_t2_empty_gt_new_edema_fp")
        out.append(
            {
                "candidate_id": candidate_model,
                "case_id": cid,
                "center": c.get("center"),
                "modality_group": c.get("modality_group"),
                "t2_present": c.get("t2_present"),
                "edema_gt_positive": c.get("edema_gt_positive"),
                "delta_edema_dice": ed_dice_delta,
                "delta_edema_hd95_improvement": ed_hd95_delta,
                "delta_edema_component_count_improvement": comp_delta,
                "delta_edema_remote_fp_improvement": remote_delta,
                "delta_scar_dice": scar_dice_delta,
                "delta_scar_hd95_improvement": scar_hd95_delta,
                "flags": ";".join(flags),
            }
        )
    return out


def decide(comparison: list[dict[str, object]], flags: list[dict[str, object]]) -> tuple[str, str]:
    hard = [r for r in flags if r.get("flags")]
    by_subset = {r["subset"]: r for r in comparison}
    t2 = by_subset["t2_present_gt_positive"]
    center = by_subset["CenterC"]
    if hard:
        return "fail_stop_no_longer_train", f"{len(hard)} case-level flags"
    t2_dice = delta_float(t2.get("delta_edema_dice"))
    t2_hd95 = delta_float(t2.get("delta_edema_hd95_improvement"))
    c_dice = delta_float(center.get("delta_edema_dice"))
    c_hd95 = delta_float(center.get("delta_edema_hd95_improvement"))
    clean_signal = (
        (t2_dice > 0.005 and t2_hd95 >= -0.1)
        or (t2_hd95 > 0.5 and t2_dice >= -0.001)
        or (c_dice > 0.005 and c_hd95 >= -0.1)
        or (c_hd95 > 0.5 and c_dice >= -0.001)
    )
    return ("pass_watch_consider_short", "clean target subset signal") if clean_signal else ("watch_stop_no_clear_positive_signal", "no clean T2-present/CenterC signal")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-id", choices=sorted(FEATURE_SETS), required=True)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--threshold", type=float, default=0.55)
    parser.add_argument("--max-train-cases", type=int, default=None)
    parser.add_argument("--no-t2-weight", type=float, default=0.05)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()

    spec = FEATURE_SETS[args.candidate_id]
    names = list(spec["features"])
    model_kind = str(spec["model_kind"])
    auxiliary = str(spec["auxiliary"])
    out_dir = OUT_ROOT / args.candidate_id
    pred_dir = out_dir / "validation_predictions"
    out_dir.mkdir(parents=True, exist_ok=True)
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    device = resolve_device(args.device)

    cases = build_cases()
    x_np, y_np, w_np, modality_np, used_cases = build_train_samples(cases, names, args.max_train_cases, args.no_t2_weight)
    model, train_rows = train_model(
        x_np,
        y_np,
        w_np,
        modality_np,
        model_kind=model_kind,
        auxiliary=auxiliary,
        epochs=max(1, args.epochs),
        device=device,
    )

    train_summary = {
        "candidate_id": args.candidate_id,
        "feature_columns": ",".join(names),
        "model_kind": model_kind,
        "auxiliary": auxiliary,
        "requested_device": args.device,
        "device": device,
        "epochs": args.epochs,
        "max_train_cases": args.max_train_cases if args.max_train_cases is not None else "all",
        "n_train_cases_used": len(used_cases),
        "n_samples": int(x_np.shape[0]),
        "n_positive": int(y_np.sum()),
        "n_negative": int((1 - y_np).sum()),
        "initial_loss": train_rows[0]["loss"],
        "final_loss": train_rows[-1]["loss"],
        "loss_delta": train_rows[0]["loss"] - train_rows[-1]["loss"],
        "nan_or_inf": any(bool(r["nan_or_inf"]) for r in train_rows),
        "threshold": args.threshold,
        "no_t2_policy": f"weak {args.no_t2_weight} training weight and validation fallback-to-baseline",
        "scar_policy": "class_5 scar voxels copied from baseline exactly",
        "fold_policy": "fold0 only; fold1-4 forbidden",
    }
    write_csv(out_dir / "train_loss.csv", train_rows)
    write_csv(out_dir / "train_summary.csv", [train_summary])
    write_text(out_dir / "train_config.yaml", "\n".join(f"{k}: {v}" for k, v in train_summary.items()) + "\n")
    write_text(out_dir / "train_command.txt", " ".join(sys.argv) + "\n")

    if args.smoke_only:
        print(f"Smoke-only completed for {args.candidate_id}; outputs in {out_dir}")
        return

    change_rows = []
    for case in [c for c in cases if c.fold0_split == "val"]:
        reference, refined, info = infer_case(model, case, names, model_kind=model_kind, device=device, threshold=args.threshold)
        write_prediction(pred_dir / f"{case.case_id}.nii.gz", reference, refined)
        change_rows.append(info)
    write_csv(out_dir / "validation_change_summary.csv", change_rows)

    baseline_rows = eval4.build_case_rows(eval4.BASELINE_PRED_DIR, "baseline_nnunet501_fold0")
    candidate_rows = eval4.build_case_rows(pred_dir, args.candidate_id)
    all_rows = baseline_rows + candidate_rows
    comparison = compare_rows(all_rows, args.candidate_id)
    flags = failure_flags(all_rows, args.candidate_id)
    status, reason = decide(comparison, flags)
    write_csv(out_dir / "fold0_very_short_case_metrics.csv", all_rows)
    write_csv(out_dir / "baseline_vs_candidate_by_subset.csv", comparison)
    write_csv(out_dir / "case_level_failure_flags.csv", flags)
    write_text(
        out_dir / "fold0_very_short_summary.md",
        f"# {args.candidate_id} Fold0 Very-Short Summary\n\n"
        f"Gate: `{status}`\n\nReason: {reason}\n\n"
        "No validation zip/upload was created. Fold1-4 remain forbidden.\n",
    )
    print(f"{args.candidate_id} gate: {status} ({reason})")


if __name__ == "__main__":
    main()
