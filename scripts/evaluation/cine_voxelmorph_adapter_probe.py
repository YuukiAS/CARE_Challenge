#!/usr/bin/env python3
"""Bounded CARE CineMyoPS VoxelMorph adapter probe.

This is a diagnostic adapter check only. It runs the local PyTorch
VoxelMorph API on one CARE cine frame pair without training or validation
packaging.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from scipy import ndimage


def compact_pred_from_cinema(raw: np.ndarray) -> np.ndarray:
    compact = np.zeros(raw.shape, dtype=np.uint8)
    compact[raw == 2] = 1
    compact[raw == 3] = 2
    return compact


def normalize_image(arr: np.ndarray) -> np.ndarray:
    arr = arr.astype(np.float32)
    lo, hi = np.percentile(arr, [1, 99])
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    arr = np.clip(arr, lo, hi)
    return ((arr - lo) / (hi - lo)).astype(np.float32)


def resample_tensor(
    arr: np.ndarray,
    out_shape: tuple[int, int, int],
    *,
    mode: str,
) -> torch.Tensor:
    tensor = torch.from_numpy(arr[None, None].astype(np.float32))
    if mode == "nearest":
        return F.interpolate(tensor, size=out_shape, mode="nearest")
    return F.interpolate(tensor, size=out_shape, mode="trilinear", align_corners=True)


def dice(a: np.ndarray, b: np.ndarray, label: int) -> float:
    ma = a == label
    mb = b == label
    denom = int(ma.sum() + mb.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(ma, mb).sum() / denom)


def component_count(mask: np.ndarray) -> int:
    _labeled, count = ndimage.label(mask)
    return int(count)


def ncc(a: np.ndarray, b: np.ndarray) -> float:
    av = a.astype(np.float64).ravel()
    bv = b.astype(np.float64).ravel()
    av -= av.mean()
    bv -= bv.mean()
    denom = np.sqrt(np.square(av).sum() * np.square(bv).sum())
    if denom <= 0:
        return 0.0
    return float(np.dot(av, bv) / denom)


def jacobian_det_3d(displacement: np.ndarray) -> np.ndarray:
    # displacement is channel-first: (3, D, H, W), matching voxel axes.
    grads = [np.gradient(displacement[c]) for c in range(3)]
    jac = np.zeros((3, 3) + displacement.shape[1:], dtype=np.float32)
    for c in range(3):
        for ax in range(3):
            jac[c, ax] = grads[c][ax]
    for i in range(3):
        jac[i, i] += 1.0
    return (
        jac[0, 0] * (jac[1, 1] * jac[2, 2] - jac[1, 2] * jac[2, 1])
        - jac[0, 1] * (jac[1, 0] * jac[2, 2] - jac[1, 2] * jac[2, 0])
        + jac[0, 2] * (jac[1, 0] * jac[2, 1] - jac[1, 1] * jac[2, 0])
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cine-path", type=Path, default=Path("data/CARE_Challenge/CineMyoPS_train/center_alpha/Case1001_Cine.nii.gz"))
    ap.add_argument("--fixed-pred", type=Path, default=Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/predictions/train/center_alpha/Case1001_t00_cinema_acdc_s0.nii.gz"))
    ap.add_argument("--moving-pred", type=Path, default=Path("results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/predictions/train/center_alpha/Case1001_t09_cinema_acdc_s0.nii.gz"))
    ap.add_argument("--case-id", default="Case1001")
    ap.add_argument("--center", default="center_alpha")
    ap.add_argument("--fixed-frame", type=int, default=0)
    ap.add_argument("--moving-frame", type=int, default=9)
    ap.add_argument("--out-dir", type=Path, default=Path("results/20260704_cine_full_cinema_registration"))
    ap.add_argument("--probe-shape", default="16,64,64")
    ap.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    args = ap.parse_args()

    import voxelmorph as vxm

    out_shape = tuple(int(item) for item in args.probe_shape.split(","))
    if len(out_shape) != 3:
        raise ValueError("--probe-shape must be D,H,W")

    cine = sitk.GetArrayFromImage(sitk.ReadImage(str(args.cine_path)))
    fixed_img = normalize_image(cine[int(args.fixed_frame)])
    moving_img = normalize_image(cine[int(args.moving_frame)])
    fixed_pred = compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(str(args.fixed_pred))))
    moving_pred = compact_pred_from_cinema(sitk.GetArrayFromImage(sitk.ReadImage(str(args.moving_pred))))

    fixed_t = resample_tensor(fixed_img, out_shape, mode="linear")
    moving_t = resample_tensor(moving_img, out_shape, mode="linear")
    fixed_label_t = resample_tensor(fixed_pred, out_shape, mode="nearest")
    moving_label_t = resample_tensor(moving_pred, out_shape, mode="nearest")

    fixed_label = fixed_label_t[0, 0].numpy().astype(np.uint8)
    moving_label = moving_label_t[0, 0].numpy().astype(np.uint8)
    fixed_np = fixed_t[0, 0].numpy()
    moving_np = moving_t[0, 0].numpy()

    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    model = vxm.nn.models.VxmPairwise(
        ndim=3,
        source_channels=1,
        target_channels=1,
        nb_features=(4, 4, 4, 4),
        integration_steps=1,
        device=str(device),
    ).to(device)
    model.eval()

    start = time.time()
    with torch.no_grad():
        field, warped_moving = model(
            moving_t.to(device),
            fixed_t.to(device),
            return_warped_source=True,
            return_field_type="displacement",
        )
        label_transformer = vxm.nn.modules.SpatialTransformer(interpolation_mode="nearest")
        warped_label_t = label_transformer(moving_label_t.to(device), field).cpu()
    runtime = time.time() - start

    field_np = field.cpu().numpy()[0].astype(np.float32)
    warped_np = warped_moving.cpu().numpy()[0, 0].astype(np.float32)
    warped_label = np.rint(warped_label_t.numpy()[0, 0]).astype(np.uint8)
    jac_det = jacobian_det_3d(field_np)
    disp_mag = np.sqrt(np.square(field_np).sum(axis=0))

    rows: list[dict[str, Any]] = []
    for label, name in [(1, "class_1_myocardium"), (2, "class_2_lv")]:
        rows.append(
            {
                "method": "voxelmorph_pytorch_untrained_adapter_probe",
                "transform_family": "learned_deformable_untrained",
                "case_id": args.case_id,
                "center": args.center,
                "fixed_frame": int(args.fixed_frame),
                "moving_frame": int(args.moving_frame),
                "class_id": label,
                "class_name": name,
                "dice_before": dice(moving_label, fixed_label, label),
                "dice_after": dice(warped_label, fixed_label, label),
                "component_count_before": component_count(moving_label == label),
                "component_count_after": component_count(warped_label == label),
                "runtime_seconds": runtime,
                "image_ncc_before": ncc(moving_np, fixed_np),
                "image_ncc_after": ncc(warped_np, fixed_np),
                "mean_abs_displacement": float(np.mean(np.abs(field_np))),
                "max_abs_displacement": float(np.max(np.abs(field_np))),
                "mean_displacement_magnitude": float(np.mean(disp_mag)),
                "max_displacement_magnitude": float(np.max(disp_mag)),
                "jacobian_min": float(np.min(jac_det)),
                "jacobian_max": float(np.max(jac_det)),
                "folding_proxy_voxels": int((jac_det <= 0).sum()),
                "model_status": "untrained_pytorch_voxelmorph_api_no_cardiac_weights",
            }
        )

    out_dir = args.out_dir
    write_csv(out_dir / "voxelmorph_adapter_probe.csv", rows)
    summary = {
        "status": "VOXELMORPH_ADAPTER_PROBE_COMPLETE_NOT_TRAINED_NOT_FULL_REGISTRATION",
        "case_id": args.case_id,
        "fixed_frame": int(args.fixed_frame),
        "moving_frame": int(args.moving_frame),
        "probe_shape_dhw": list(out_shape),
        "device": str(device),
        "runtime_seconds": runtime,
        "voxelmorph_file": str(Path(vxm.__file__).resolve()),
        "model_status": "untrained PyTorch VxmPairwise; no cardiac pretrained weights loaded",
        "image_ncc_before": ncc(moving_np, fixed_np),
        "image_ncc_after": ncc(warped_np, fixed_np),
        "mean_abs_displacement": float(np.mean(np.abs(field_np))),
        "max_abs_displacement": float(np.max(np.abs(field_np))),
        "folding_proxy_voxels": int((jac_det <= 0).sum()),
        "csv": str(out_dir / "voxelmorph_adapter_probe.csv"),
    }
    (out_dir / "voxelmorph_adapter_probe_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
