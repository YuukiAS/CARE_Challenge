#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


CARE_ROOT = repo_root()
CARE_CINE_CODE = CARE_ROOT / "third_party" / "CineMyoPS" / "code"
if str(CARE_CINE_CODE) not in sys.path:
    sys.path.insert(0, str(CARE_CINE_CODE))

from nnunet.training.model_restore import restore_model  # noqa: E402


@contextmanager
def temporary_env(name: str, value: str):
    old = os.environ.get(name)
    os.environ[name] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = old


def counts(arr: np.ndarray | torch.Tensor) -> dict[str, int]:
    if isinstance(arr, torch.Tensor):
        arr = arr.detach().cpu().numpy()
    vals, cnts = np.unique(arr.astype(np.int64), return_counts=True)
    return {str(int(v)): int(c) for v, c in zip(vals, cnts)}


def channel_stats(t: torch.Tensor) -> dict[str, dict[str, float]]:
    t = t.detach().float().cpu()
    out: dict[str, dict[str, float]] = {}
    for c in range(t.shape[1]):
        x = t[:, c]
        out[str(c)] = {
            "mean": float(x.mean()),
            "min": float(x.min()),
            "max": float(x.max()),
        }
    return out


def softmax_argmax_counts(t: torch.Tensor, dim: int = 1) -> dict[str, int]:
    return counts(torch.softmax(t, dim=dim).argmax(dim=dim))


def load_case_map(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["case_id"]: f"{item['center']}_{item['case_id']}" for item in payload["cases"]}


def load_split_cases(path: Path, fold: int, n_val: int) -> tuple[list[str], list[str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    fold_payload = payload["folds"][fold]
    return sorted(fold_payload["val"])[:n_val], sorted(fold_payload["train"])[:1]


def load_preprocessed_case(preprocessed_stage: Path, prefixed_case: str) -> np.ndarray:
    npy = preprocessed_stage / f"{prefixed_case}.npy"
    if npy.is_file():
        return np.load(npy, mmap_mode="r")
    npz = preprocessed_stage / f"{prefixed_case}.npz"
    if npz.is_file():
        return np.load(npz)["data"]
    raise FileNotFoundError(f"Missing preprocessed case {prefixed_case} under {preprocessed_stage}")


def read_nifti_counts(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "exists": False}
    arr = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))
    return {"path": str(path), "exists": True, "shape": list(arr.shape), "unique_counts": counts(arr)}


def choose_slice(label_3d: np.ndarray) -> int:
    foreground = label_3d > 0
    if foreground.ndim != 3:
        raise ValueError(f"Expected 3D label, got {label_3d.shape}")
    per_slice = foreground.reshape(foreground.shape[0], -1).sum(axis=1)
    if per_slice.max() > 0:
        return int(per_slice.argmax())
    return int(label_3d.shape[0] // 2)


def extract_2d_network_patch(data: np.ndarray, label: np.ndarray, patch_size: tuple[int, int]) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Return a (T,H,W) cine patch and 2D label.

    nnU-Net v1 2D preprocessed arrays are usually (C,Z,H,W), but some cases with
    anisotropic resampling may be stored with the slice axis in another position.
    The network expects (B,T,H,W), so infer the in-plane axes from trainer.patch_size
    and slice along the remaining axis instead of assuming axis 0 is always Z.
    """
    if data.ndim != 4 or label.ndim != 3:
        raise ValueError(f"Expected data (C,*,*,*) and label (*,*,*), got {data.shape=} {label.shape=}")
    spatial = data.shape[1:]
    if tuple(spatial) != tuple(label.shape):
        raise ValueError(f"Data/label spatial shapes differ: {spatial=} label={label.shape}")
    target = tuple(int(x) for x in patch_size)
    axes = list(range(3))
    # Prefer exact patch-size matches; otherwise use the two largest dimensions as in-plane axes.
    exact = [i for i, dim in enumerate(spatial) if dim in target]
    if len(exact) >= 2:
        inplane = exact[:2]
    else:
        inplane = sorted(axes, key=lambda i: spatial[i], reverse=True)[:2]
    slice_axes = [i for i in axes if i not in inplane]
    if len(slice_axes) != 1:
        raise RuntimeError(f"Could not infer unique slice axis from spatial={spatial} patch_size={target}")
    slice_axis = slice_axes[0]
    label_for_choice = np.moveaxis(label, slice_axis, 0)
    z = choose_slice(label_for_choice)
    patch = np.take(data, z, axis=1 + slice_axis)
    label_2d = np.take(label, z, axis=slice_axis)
    if patch.ndim != 3:
        raise ValueError(f"Expected extracted patch (T,H,W), got {patch.shape}")
    if tuple(patch.shape[1:]) != tuple(label_2d.shape):
        raise ValueError(f"Patch/label 2D shape mismatch: patch={patch.shape} label={label_2d.shape}")
    return np.ascontiguousarray(patch, dtype=np.float32), np.asarray(label_2d), int(z), int(slice_axis)


def forward_once(trainer, patch: np.ndarray, train_mode: bool) -> dict[str, Any]:
    previous = trainer.network.training
    trainer.network.train(train_mode)
    tensor = torch.from_numpy(patch[None]).float()
    if torch.cuda.is_available():
        tensor = tensor.cuda(non_blocking=True)
    with torch.no_grad():
        _, cardiac_seg, pathology_seg, _ = trainer.network(tensor)
        cardiac_ed = cardiac_seg[:, :, 0]
        pathology = pathology_seg
        with temporary_env("CINE_COMBINE_MODE", "current"):
            combined = trainer._combine_compact_softmax(cardiac_ed, pathology)
        by_mode = {}
        for mode in ("current", "cardiac_only", "myocardium_gated_scar", "pathology_direct"):
            with temporary_env("CINE_COMBINE_MODE", mode):
                compact = trainer._combine_compact_softmax(cardiac_ed, pathology)
            by_mode[mode] = counts(compact.argmax(dim=1))
    trainer.network.train(previous)
    return {
        "mode": "train" if train_mode else "eval",
        "cardiac_seg_logits": channel_stats(cardiac_ed),
        "pathology_seg_logits": channel_stats(pathology),
        "cardiac_softmax_argmax_counts": softmax_argmax_counts(cardiac_ed),
        "pathology_softmax_argmax_counts": softmax_argmax_counts(pathology),
        "current_combine_argmax_counts": counts(combined.argmax(dim=1)),
        "combine_mode_argmax_counts": by_mode,
    }


def predict_once(trainer, data: np.ndarray) -> dict[str, Any]:
    previous = os.environ.get("CINE_COMBINE_MODE")
    os.environ["CINE_COMBINE_MODE"] = "current"
    seg, softmax = trainer.predict_preprocessed_data_return_seg_and_softmax(
        data=data,
        do_mirroring=False,
        mirror_axes=(),
        use_sliding_window=True,
        step_size=0.5,
        use_gaussian=False,
        pad_border_mode="constant",
        pad_kwargs={"constant_values": 0},
        all_in_gpu=False,
        verbose=False,
        mixed_precision=False,
    )
    if previous is None:
        os.environ.pop("CINE_COMBINE_MODE", None)
    else:
        os.environ["CINE_COMBINE_MODE"] = previous
    return {
        "softmax_channel_stats": {
            str(c): {
                "mean": float(softmax[c].mean()),
                "min": float(softmax[c].min()),
                "max": float(softmax[c].max()),
            }
            for c in range(softmax.shape[0])
        },
        "argmax_counts": counts(seg),
    }


def parse_args() -> argparse.Namespace:
    root = repo_root()
    ap = argparse.ArgumentParser(description="Debug CineMyoPS inference/softmax semantics for round4.")
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--task", default="Task026_Cine_4D")
    ap.add_argument("--trainer", default="CARECineMyoPSTrainerBNCalib")
    ap.add_argument("--checkpoint", default="model_final_checkpoint")
    ap.add_argument("--n-val", type=int, default=3)
    ap.add_argument("--split-json", type=Path, default=root / "data/benchmarks/protocol/splits_CineMyoPS.json")
    ap.add_argument("--cases-json", type=Path, default=root / "data/benchmarks/protocol/cases_CineMyoPS.json")
    ap.add_argument(
        "--preprocessed-stage",
        type=Path,
        default=root
        / "data/nnUNet/nnUNet_preprocessed/Task026_Cine_4D/nnUNetData_plans_v2.1_2D_stage0",
    )
    ap.add_argument(
        "--model-root",
        type=Path,
        default=root
        / "data/nnUNet/nnUNet_results/nnUNet/2d/Task026_Cine_4D/"
        "CARECineMyoPSTrainerBNCalib__nnUNetPlansv2.1",
    )
    ap.add_argument(
        "--raw-task-root",
        type=Path,
        default=root / "data/nnUNet/nnUNet_raw/Task026_Cine_4D",
    )
    ap.add_argument(
        "--protocol-gt-root",
        type=Path,
        default=root / "data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/labelsTr",
    )
    ap.add_argument(
        "--exported-pred-dir",
        type=Path,
        default=root / "results/predictions/CineMyoPS_BNCalib/fold_0",
    )
    ap.add_argument(
        "--output-json",
        type=Path,
        default=root / "results/diagnostics/CineMyoPS_round4/inference_semantics.json",
    )
    ap.add_argument("--bn-recalibrate", action="store_true", default=True)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    os.environ.setdefault("CINE_BN_RECALIBRATE", "1" if args.bn_recalibrate else "0")
    os.environ.setdefault("CINE_BN_RECALIB_BATCHES", "32")

    val_cases, train_cases = load_split_cases(args.split_json, args.fold, args.n_val)
    selected_cases = [("val", c) for c in val_cases] + [("train", c) for c in train_cases]
    case_map = load_case_map(args.cases_json)

    fold_dir = args.model_root / f"fold_{args.fold}"
    checkpoint_path = fold_dir / f"{args.checkpoint}.model"
    trainer = restore_model(
        str(checkpoint_path) + ".pkl",
        checkpoint=str(checkpoint_path),
        train=False,
        fp16=False,
    )
    if args.bn_recalibrate and hasattr(trainer, "_maybe_recalibrate_batchnorm"):
        trainer._maybe_recalibrate_batchnorm(verbose=True, mixed_precision=False)

    result: dict[str, Any] = {
        "model_root": str(args.model_root),
        "checkpoint": args.checkpoint,
        "fold": args.fold,
        "bn_recalibration": getattr(trainer, "_care_bn_recalib_stats", {}),
        "patch_size": [int(v) for v in trainer.patch_size],
        "cases": {},
    }

    for split, case_id in selected_cases:
        prefixed = case_map[case_id]
        arr = load_preprocessed_case(args.preprocessed_stage, prefixed)
        data = np.asarray(arr[:-1], dtype=np.float32)
        label = np.asarray(arr[-1]).astype(np.int16)
        patch, label_2d, z, slice_axis = extract_2d_network_patch(
            data,
            label,
            tuple(int(v) for v in trainer.patch_size),
        )

        raw_input_shapes = {}
        for p in sorted((args.raw_task_root / "imagesTr").glob(f"{prefixed}_*.nii.gz")):
            raw_input_shapes[p.name] = list(sitk.GetArrayFromImage(sitk.ReadImage(str(p))).shape)

        case_result = {
            "split": split,
            "prefixed_case": prefixed,
            "preprocessed_shape": list(arr.shape),
            "network_patch_shape": list(patch.shape),
            "selected_slice": z,
            "selected_slice_axis": slice_axis,
            "selected_slice_label_counts": counts(label_2d),
            "preprocessed_label_counts": counts(label),
            "raw_input_shapes": raw_input_shapes,
            "raw_task_label": read_nifti_counts(args.raw_task_root / "labelsTr" / f"{prefixed}.nii.gz"),
            "protocol_gt": read_nifti_counts(args.protocol_gt_root / f"{case_id}.nii.gz"),
            "direct_eval_forward": forward_once(trainer, patch, train_mode=False),
            "direct_train_forward": forward_once(trainer, patch, train_mode=True),
            "predict_no_tta_no_gaussian": predict_once(trainer, data),
            "exported_nifti": read_nifti_counts(args.exported_pred_dir / f"{case_id}.nii.gz"),
        }
        result["cases"][case_id] = case_result

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(f"wrote {args.output_json}")


if __name__ == "__main__":
    main()
