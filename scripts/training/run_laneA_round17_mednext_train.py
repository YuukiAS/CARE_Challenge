#!/usr/bin/env python3
"""Lane A Round17 MedNeXt fold0 very-short training runner.

This is a bounded code-only MedNeXt Stage5 entrypoint. It trains from CARE
Dataset501 preprocessed fold0 data, writes only under the Round17 diagnostics
root, and never downloads weights, modifies nnU-Net baseline caches, creates a
validation zip, uploads, or expands beyond fold0.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import pickle
import sys
from dataclasses import dataclass
from pathlib import Path

import blosc2
import numpy as np
import torch
from torch import nn


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))

from batchgenerators.utilities.file_and_folder_operations import load_json
from nnunetv2.inference.export_prediction import export_prediction_from_logits
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from scripts.diagnostics import laneA_round4_fold0_short_train_eval as eval4
from src.care_myocardium.mednext import MedNeXtConfig, create_care_mednext, mednext_repo_path


OUT_ROOT = REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round17_mednext_backbone"
PREPROC_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
PREPROC_FULLRES = PREPROC_ROOT / "nnUNetPlans_3d_fullres"
RAW_LABEL_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
SPLITS_JSON = PREPROC_ROOT / "splits_final.json"
PLANS_JSON = PREPROC_ROOT / "nnUNetPlans.json"
DATASET_JSON = PREPROC_ROOT / "dataset.json"
SEED = 17017
IGNORE_LABEL = -1


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    model_size: str
    kernel_size: int
    input_channels: int
    deep_supervision: bool = False


CANDIDATES = {
    "R17_A_mednext_s_kernel3_standard_dicece_fold0_vs": CandidateSpec(
        "R17_A_mednext_s_kernel3_standard_dicece_fold0_vs",
        model_size="S",
        kernel_size=3,
        input_channels=3,
    ),
    "R17_B_mednext_b_kernel3_standard_dicece_fold0_vs": CandidateSpec(
        "R17_B_mednext_b_kernel3_standard_dicece_fold0_vs",
        model_size="B",
        kernel_size=3,
        input_channels=3,
    ),
    "R17_D_mednext_s_modality_channels_fold0_vs": CandidateSpec(
        "R17_D_mednext_s_modality_channels_fold0_vs",
        model_size="S",
        kernel_size=3,
        input_channels=6,
    ),
    "R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_vs": CandidateSpec(
        "R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_vs",
        model_size="S",
        kernel_size=5,
        input_channels=3,
    ),
    "R17_A_mednext_s_kernel3_standard_dicece_fold0_fairshort": CandidateSpec(
        "R17_A_mednext_s_kernel3_standard_dicece_fold0_fairshort",
        model_size="S",
        kernel_size=3,
        input_channels=3,
    ),
    "R17_B_mednext_b_kernel3_standard_dicece_fold0_fairshort": CandidateSpec(
        "R17_B_mednext_b_kernel3_standard_dicece_fold0_fairshort",
        model_size="B",
        kernel_size=3,
        input_channels=3,
    ),
    "R17_D_mednext_s_modality_channels_fold0_fairshort": CandidateSpec(
        "R17_D_mednext_s_modality_channels_fold0_fairshort",
        model_size="S",
        kernel_size=3,
        input_channels=6,
    ),
    "R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_fairshort": CandidateSpec(
        "R17_C_mednext_s_kernel5_upkern_or_largekernel_fold0_fairshort",
        model_size="S",
        kernel_size=5,
        input_channels=3,
    ),
}


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_splits() -> tuple[list[str], list[str]]:
    data = json.loads(SPLITS_JSON.read_text(encoding="utf-8"))
    split = data[0]
    return list(split["train"]), list(split["val"])


def parse_shape(text: str) -> tuple[int, int, int]:
    parts = [int(v) for v in text.lower().replace(",", "x").split("x") if v]
    if len(parts) != 3:
        raise ValueError(f"patch shape must have 3 spatial dims, got {text!r}")
    return tuple(parts)  # type: ignore[return-value]


def load_preprocessed_case(case_id: str) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    data = blosc2.open(urlpath=str(PREPROC_FULLRES / f"{case_id}.b2nd"), mode="r")[...].astype(np.float32, copy=False)
    seg = blosc2.open(urlpath=str(PREPROC_FULLRES / f"{case_id}_seg.b2nd"), mode="r")[...].astype(np.int64, copy=False)[0]
    with (PREPROC_FULLRES / f"{case_id}.pkl").open("rb") as f:
        props = pickle.load(f)
    return data, seg, props


def with_presence_channels(data: np.ndarray, input_channels: int) -> np.ndarray:
    if input_channels == 3:
        return data
    if input_channels != 6:
        raise ValueError(f"unsupported input channel count: {input_channels}")
    # Dataset501 image channel order is LGE, T2, C0. The appended modality
    # presence order follows the Round7 convention: C0, LGE, T2.
    presence = [
        float(np.any(np.abs(data[2]) > 0.0)),
        float(np.any(np.abs(data[0]) > 0.0)),
        float(np.any(np.abs(data[1]) > 0.0)),
    ]
    maps = [np.full(data.shape[1:], value, dtype=np.float32) for value in presence]
    return np.concatenate([data, np.stack(maps, axis=0)], axis=0).astype(np.float32, copy=False)


def crop_or_pad(array: np.ndarray, starts: tuple[int, int, int], patch_shape: tuple[int, int, int], pad_value: float | int) -> np.ndarray:
    spatial = array.shape[-3:]
    slices = []
    pads = []
    for start, size, dim in zip(starts, patch_shape, spatial):
        lo = max(start, 0)
        hi = min(start + size, dim)
        slices.append(slice(lo, hi))
        pads.append((max(0, -start), max(0, start + size - dim)))
    cropped = array[(..., *slices)]
    return np.pad(cropped, [(0, 0)] * (array.ndim - 3) + pads, mode="constant", constant_values=pad_value)


def random_patch(
    data: np.ndarray,
    seg: np.ndarray,
    patch_shape: tuple[int, int, int],
    rng: np.random.Generator,
    oversample_foreground: float,
) -> tuple[np.ndarray, np.ndarray]:
    valid = seg >= 0
    foreground = np.argwhere(valid & np.isin(seg, [4, 5]))
    if foreground.size and rng.random() < oversample_foreground:
        center = foreground[int(rng.integers(0, len(foreground)))]
    else:
        valid_coords = np.argwhere(valid)
        center = valid_coords[int(rng.integers(0, len(valid_coords)))] if len(valid_coords) else np.asarray(seg.shape) // 2
    starts = tuple(int(c - p // 2) for c, p in zip(center, patch_shape))
    x = crop_or_pad(data, starts, patch_shape, 0.0).astype(np.float32, copy=False)
    y = crop_or_pad(seg[None], starts, patch_shape, IGNORE_LABEL).astype(np.int64, copy=False)[0]
    return x, y


def dice_ce_loss(logits: torch.Tensor, target: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    ce = nn.functional.cross_entropy(logits, target, ignore_index=IGNORE_LABEL)
    valid = target != IGNORE_LABEL
    if not bool(valid.any()):
        return ce, ce.detach() * 0, ce
    probs = torch.softmax(logits, dim=1)
    safe_target = torch.where(valid, target, torch.zeros_like(target))
    one_hot = nn.functional.one_hot(safe_target, num_classes=logits.shape[1]).permute(0, 4, 1, 2, 3).float()
    valid_f = valid[:, None].float()
    probs = probs * valid_f
    one_hot = one_hot * valid_f
    dims = (0, 2, 3, 4)
    intersect = torch.sum(probs * one_hot, dims)
    denom = torch.sum(probs + one_hot, dims)
    dice_loss = torch.mean(1.0 - (2.0 * intersect + 1.0) / (denom + 1.0))
    return ce + dice_loss, ce.detach(), dice_loss.detach()


def resolve_device(requested: str) -> torch.device:
    if requested == "cuda" and not torch.cuda.is_available():
        print("Requested cuda but CUDA is unavailable; falling back to cpu", flush=True)
        return torch.device("cpu")
    return torch.device(requested)


def train(
    model: nn.Module,
    spec: CandidateSpec,
    train_cases: list[str],
    args: argparse.Namespace,
    device: torch.device,
) -> list[dict[str, object]]:
    rng = np.random.default_rng(args.seed)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    rows: list[dict[str, object]] = []
    model.train()
    global_step = 0
    for epoch in range(args.epochs):
        for step in range(args.steps_per_epoch):
            case_id = train_cases[int(rng.integers(0, len(train_cases)))]
            data, seg, _props = load_preprocessed_case(case_id)
            data = with_presence_channels(data, spec.input_channels)
            xs, ys = [], []
            for _ in range(args.batch_size):
                x, y = random_patch(data, seg, args.patch_shape, rng, args.oversample_foreground)
                xs.append(x)
                ys.append(y)
            x_t = torch.from_numpy(np.stack(xs)).to(device=device, dtype=torch.float32)
            y_t = torch.from_numpy(np.stack(ys)).to(device=device, dtype=torch.long)
            opt.zero_grad(set_to_none=True)
            out = model(x_t)
            logits = out[0] if isinstance(out, (tuple, list)) else out
            loss, ce, dice = dice_ce_loss(logits, y_t)
            loss.backward()
            grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
            opt.step()
            loss_value = float(loss.detach().cpu())
            rows.append(
                {
                    "epoch": epoch,
                    "step": step,
                    "global_step": global_step,
                    "case_id": case_id,
                    "loss": loss_value,
                    "ce_loss": float(ce.cpu()),
                    "dice_loss": float(dice.cpu()),
                    "grad_norm": float(grad_norm.detach().cpu() if isinstance(grad_norm, torch.Tensor) else grad_norm),
                    "nan_or_inf": not math.isfinite(loss_value),
                }
            )
            global_step += 1
    return rows


def starts_for_dim(dim: int, patch: int, stride: int) -> list[int]:
    if dim <= patch:
        return [0]
    starts = list(range(0, max(dim - patch, 0) + 1, stride))
    if starts[-1] != dim - patch:
        starts.append(dim - patch)
    return starts


def pad_to_patch(data: np.ndarray, patch_shape: tuple[int, int, int]) -> tuple[np.ndarray, tuple[int, int, int]]:
    pads = []
    for dim, patch in zip(data.shape[-3:], patch_shape):
        pads.append((0, max(0, patch - dim)))
    padded = np.pad(data, [(0, 0)] * (data.ndim - 3) + pads, mode="constant", constant_values=0)
    return padded, data.shape[-3:]  # type: ignore[return-value]


def sliding_window_logits(
    model: nn.Module,
    data: np.ndarray,
    patch_shape: tuple[int, int, int],
    stride_shape: tuple[int, int, int],
    device: torch.device,
) -> np.ndarray:
    data_padded, original_shape = pad_to_patch(data, patch_shape)
    sums = np.zeros((6, *data_padded.shape[-3:]), dtype=np.float32)
    counts = np.zeros(data_padded.shape[-3:], dtype=np.float32)
    z_starts = starts_for_dim(data_padded.shape[-3], patch_shape[0], stride_shape[0])
    y_starts = starts_for_dim(data_padded.shape[-2], patch_shape[1], stride_shape[1])
    x_starts = starts_for_dim(data_padded.shape[-1], patch_shape[2], stride_shape[2])
    model.eval()
    with torch.no_grad():
        for z in z_starts:
            for y in y_starts:
                for x in x_starts:
                    patch = data_padded[:, z : z + patch_shape[0], y : y + patch_shape[1], x : x + patch_shape[2]]
                    x_t = torch.from_numpy(patch[None]).to(device=device, dtype=torch.float32)
                    out = model(x_t)
                    logits = out[0] if isinstance(out, (tuple, list)) else out
                    logits_np = logits.detach().cpu().numpy()[0]
                    sums[:, z : z + patch_shape[0], y : y + patch_shape[1], x : x + patch_shape[2]] += logits_np
                    counts[z : z + patch_shape[0], y : y + patch_shape[1], x : x + patch_shape[2]] += 1.0
    logits = sums / np.maximum(counts[None], 1.0)
    return logits[:, : original_shape[0], : original_shape[1], : original_shape[2]]


def export_predictions(
    model: nn.Module,
    spec: CandidateSpec,
    val_cases: list[str],
    args: argparse.Namespace,
    device: torch.device,
    pred_dir: Path,
) -> list[dict[str, object]]:
    rows = []
    selected = val_cases[: args.max_val_cases] if args.max_val_cases is not None else val_cases
    plans = load_json(str(PLANS_JSON))
    dataset_json = load_json(str(DATASET_JSON))
    plans_manager = PlansManager(plans)
    configuration_manager = plans_manager.get_configuration("3d_fullres")
    for case_id in selected:
        data, _seg, props = load_preprocessed_case(case_id)
        data = with_presence_channels(data, spec.input_channels)
        logits_preproc = sliding_window_logits(model, data, args.patch_shape, args.stride_shape, device)
        pred_dir.mkdir(parents=True, exist_ok=True)
        output_file_truncated = pred_dir / case_id
        export_prediction_from_logits(
            logits_preproc,
            props,
            configuration_manager,
            plans_manager,
            dataset_json,
            str(output_file_truncated),
            save_probabilities=False,
        )
        rows.append(
            {
                "case_id": case_id,
                "preprocessed_logits_shape": "x".join(str(v) for v in logits_preproc.shape),
                "export_method": "nnunetv2.export_prediction_from_logits",
                "prediction_path": str((pred_dir / f"{case_id}.nii.gz").relative_to(REPO_ROOT)),
            }
        )
    return rows


def aggregate_results(out_dir: Path, candidate_id: str, status: str, train_rows: list[dict[str, object]], n_predictions: int) -> None:
    row = {
        "candidate_id": candidate_id,
        "status": status,
        "output_dir": str(out_dir.relative_to(REPO_ROOT)),
        "epochs": len({r["epoch"] for r in train_rows}),
        "steps": len(train_rows),
        "initial_loss": train_rows[0]["loss"] if train_rows else "",
        "final_loss": train_rows[-1]["loss"] if train_rows else "",
        "nan_or_inf": any(bool(r.get("nan_or_inf")) for r in train_rows),
        "validation_predictions": n_predictions,
    }
    path = OUT_ROOT / "round17_fold0_very_short_results.csv"
    rows: list[dict[str, object]] = []
    if path.is_file():
        with path.open(newline="", encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("candidate_id") != candidate_id]
    rows.append(row)
    write_csv(path, rows, list(row.keys()))


def config_lines(args: argparse.Namespace, spec: CandidateSpec, device: torch.device, train_cases: list[str], val_cases: list[str]) -> list[str]:
    return [
        f"candidate_id: {spec.candidate_id}",
        "round: 17",
        "lane: laneA_myops",
        "stage: mednext_fold0_very_short_training_batch",
        "dataset: Dataset501_CAREMyoPS",
        "fold: 0",
        f"train_cases: {len(train_cases)}",
        f"validation_cases: {len(val_cases)}",
        f"output_root: {OUT_ROOT.relative_to(REPO_ROOT)}",
        "model:",
        "  architecture: MedNeXtV1",
        f"  model_size: {spec.model_size}",
        f"  kernel_size: {spec.kernel_size}",
        f"  input_channels: {spec.input_channels}",
        "  output_classes: 6",
        f"  deep_supervision: {str(spec.deep_supervision).lower()}",
        "objective:",
        "  loss: standard_cross_entropy_plus_soft_dice",
        "  primary_gate: myops_edema class_4 T2-present GT-positive / CenterC",
        "  co_primary_metric: myops_scar class_5 non-regression/improvement",
        "training:",
        f"  epochs: {args.epochs}",
        f"  steps_per_epoch: {args.steps_per_epoch}",
        f"  batch_size: {args.batch_size}",
        f"  patch_shape: {'x'.join(str(v) for v in args.patch_shape)}",
        f"  lr: {args.lr}",
        f"  weight_decay: {args.weight_decay}",
        f"  device: {device}",
        f"  seed: {args.seed}",
        "constraints:",
        "  pretrained_weights: not_used",
        "  external_training_data: forbidden",
        "  production_baseline_cache_writes: forbidden",
        "  validation_zip: forbidden",
        "  fold1_4: forbidden_without_user_authorization",
        f"mednext_repo: {mednext_repo_path()}",
        "",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Lane A Round17 MedNeXt fold0 very-short runner")
    parser.add_argument("--candidate-id", choices=sorted(CANDIDATES), default="R17_A_mednext_s_kernel3_standard_dicece_fold0_vs")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--steps-per-epoch", type=int, default=24)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--patch-shape", type=parse_shape, default=parse_shape("32x128x128"))
    parser.add_argument("--stride-shape", type=parse_shape, default=parse_shape("32x96x96"))
    parser.add_argument("--oversample-foreground", type=float, default=0.75)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-5)
    parser.add_argument("--grad-clip", type=float, default=12.0)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--max-train-cases", type=int, default=None)
    parser.add_argument("--max-val-cases", type=int, default=None)
    parser.add_argument("--smoke-only", action="store_true")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    spec = CANDIDATES[args.candidate_id]
    train_cases, val_cases = load_splits()
    if args.max_train_cases is not None:
        train_cases = train_cases[: args.max_train_cases]
    if not train_cases:
        raise RuntimeError("no fold0 train cases available")

    out_dir = OUT_ROOT / spec.candidate_id
    pred_dir = out_dir / "validation_predictions"
    out_dir.mkdir(parents=True, exist_ok=True)
    device = resolve_device(args.device)
    model = create_care_mednext(
        MedNeXtConfig(
            model_id=spec.model_size,
            num_input_channels=spec.input_channels,
            num_classes=6,
            kernel_size=spec.kernel_size,
            deep_supervision=spec.deep_supervision,
        )
    ).to(device)

    write_text(out_dir / "train_config.yaml", "\n".join(config_lines(args, spec, device, train_cases, val_cases)))
    write_text(out_dir / "train_command.txt", " ".join([sys.executable, *sys.argv]) + "\n")

    train_rows = train(model, spec, train_cases, args, device)
    write_csv(out_dir / "train_loss.csv", train_rows)
    torch.save(
        {
            "candidate_id": spec.candidate_id,
            "model_state_dict": model.state_dict(),
            "config": spec.__dict__,
            "args": {k: str(v) for k, v in vars(args).items()},
        },
        out_dir / "checkpoint_very_short.pt",
    )

    if args.smoke_only:
        aggregate_results(out_dir, spec.candidate_id, "smoke_only_completed", train_rows, 0)
        print(f"Smoke-only completed for {spec.candidate_id}; outputs in {out_dir}")
        return

    prediction_rows = export_predictions(model, spec, val_cases, args, device, pred_dir)
    write_csv(out_dir / "validation_prediction_manifest.csv", prediction_rows)
    baseline_rows = eval4.build_case_rows(eval4.BASELINE_PRED_DIR, "baseline_nnunet501_fold0")
    candidate_rows = eval4.build_case_rows(pred_dir, spec.candidate_id)
    write_csv(out_dir / "fold0_very_short_case_metrics.csv", baseline_rows + candidate_rows)
    status = "completed_with_44_predictions" if len(prediction_rows) == 44 else "completed_partial_predictions"
    aggregate_results(out_dir, spec.candidate_id, status, train_rows, len(prediction_rows))
    write_text(
        out_dir / "fold0_very_short_summary.md",
        "\n".join(
            [
                f"# {spec.candidate_id} Fold0 Very-Short Summary",
                "",
                f"- Status: `{status}`",
                f"- Validation predictions: `{len(prediction_rows)}`",
                f"- Initial loss: `{train_rows[0]['loss'] if train_rows else 'NA'}`",
                f"- Final loss: `{train_rows[-1]['loss'] if train_rows else 'NA'}`",
                "- No pretrained weights, external data, validation zip, upload, or fold1-4 expansion were used.",
                "",
            ]
        ),
    )
    print(f"{spec.candidate_id}: {status}; outputs in {out_dir}")


if __name__ == "__main__":
    main()
