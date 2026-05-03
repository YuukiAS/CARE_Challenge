#!/usr/bin/env python3
"""Export per-case MyoPS-Net validation predictions as compact CARE labels."""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import torch


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


REPO = _repo_root() / "third_party" / "MyoPS-Net"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from network.model import MyoPSNet  # noqa: E402
from process import LargestConnectedComponents  # noqa: E402
from utils.tools import Normalization, ResultTransform  # noqa: E402


def select_checkpoint(checkpoint_dir: Path) -> Path:
    ckpts = sorted(checkpoint_dir.glob("*.pth"))
    if not ckpts:
        raise FileNotFoundError(f"No checkpoints found under {checkpoint_dir}")

    def score(path: Path) -> tuple[float, float]:
        m = re.match(r"([0-9]+(?:\.[0-9]+)?)\[(\d+)\]\.pth$", path.name)
        if m:
            return (float(m.group(1)), float(m.group(2)))
        return (-1.0, path.stat().st_mtime)

    return max(ckpts, key=score)


def discover_val_cases(data_root: Path) -> list[tuple[str, Path]]:
    val_root = data_root / "val_set" / "val_image"
    cases: list[tuple[str, Path]] = []
    for case_dir in sorted(val_root.glob("*/*")):
        if not case_dir.is_dir():
            continue
        case_id = case_dir.name
        lge = case_dir / f"{case_id}_LGE.nii.gz"
        if lge.is_file():
            cases.append((case_id, case_dir))
    return cases


def center_crop_or_pad(arr: np.ndarray, dim: int) -> tuple[np.ndarray, tuple[int, int, int, int, int, int, int, int]]:
    h, w = arr.shape
    src_y0 = max(0, (h - dim) // 2)
    src_x0 = max(0, (w - dim) // 2)
    src_y1 = min(h, src_y0 + dim)
    src_x1 = min(w, src_x0 + dim)

    dst_y0 = max(0, (dim - h) // 2)
    dst_x0 = max(0, (dim - w) // 2)
    dst_y1 = dst_y0 + (src_y1 - src_y0)
    dst_x1 = dst_x0 + (src_x1 - src_x0)

    out = np.zeros((dim, dim), dtype=arr.dtype)
    out[dst_y0:dst_y1, dst_x0:dst_x1] = arr[src_y0:src_y1, src_x0:src_x1]
    return out, (src_y0, src_y1, src_x0, src_x1, dst_y0, dst_y1, dst_x0, dst_x1)


def paste_back(crop_pred: np.ndarray, shape_hw: tuple[int, int], meta: tuple[int, int, int, int, int, int, int, int]) -> np.ndarray:
    full = np.zeros(shape_hw, dtype=np.uint8)
    src_y0, src_y1, src_x0, src_x1, dst_y0, dst_y1, dst_x0, dst_x1 = meta
    full[src_y0:src_y1, src_x0:src_x1] = crop_pred[dst_y0:dst_y1, dst_x0:dst_x1]
    return full


def load_modalities(case_dir: Path, case_id: str) -> tuple[dict[str, np.ndarray], nib.Nifti1Image]:
    ref_img = nib.load(str(case_dir / f"{case_id}_LGE.nii.gz"))
    modalities = {}
    for name in ("C0", "LGE", "T2", "T1m", "T2starm"):
        modalities[name] = nib.load(str(case_dir / f"{case_id}_{name}.nii.gz")).get_fdata().astype(np.float32)
    return modalities, ref_img


def run_case(
    model: MyoPSNet,
    case_dir: Path,
    case_id: str,
    dim: int,
    device: torch.device,
    normalize: Normalization,
    keep_lcc: LargestConnectedComponents,
    result_transform: ResultTransform,
) -> nib.Nifti1Image:
    modalities, ref_img = load_modalities(case_dir, case_id)
    for key in modalities:
        if np.any(modalities[key]):
            modalities[key] = normalize(modalities[key], "Truncate").astype(np.float32, copy=False)

    h, w, z = modalities["LGE"].shape
    pred_vol = np.zeros((h, w, z), dtype=np.uint8)

    for zi in range(z):
        crops = []
        crop_meta = None
        for key in ("C0", "LGE", "T2", "T1m", "T2starm"):
            crop, crop_meta = center_crop_or_pad(modalities[key][:, :, zi], dim)
            crop = normalize(crop.astype(np.float32, copy=False), "Zero_Mean_Unit_Std")
            crops.append(torch.from_numpy(crop).float().unsqueeze(0).unsqueeze(0).to(device))

        with torch.no_grad():
            _, res_lge, res_t2, res_mapping = model(*crops)

        seg_lge = torch.argmax(res_lge, dim=1).squeeze(0).cpu()
        seg_t2 = torch.argmax(res_t2, dim=1).squeeze(0).cpu()
        if res_mapping is not None:
            seg_mapping = torch.argmax(res_mapping, dim=1).squeeze(0).cpu()
        else:
            seg_mapping = None

        seg_lge = keep_lcc(seg_lge, "scar")
        seg_t2 = keep_lcc(seg_t2, "edema")
        if seg_mapping is not None:
            seg_mapping = keep_lcc(seg_mapping, "scar")

        pathology = result_transform(seg_lge, seg_mapping, seg_t2).numpy().astype(np.uint8, copy=False)
        compact = np.zeros_like(pathology, dtype=np.uint8)
        compact[pathology == 1] = 4
        compact[pathology == 2] = 5
        pred_vol[:, :, zi] = paste_back(compact, (h, w), crop_meta)

    return nib.Nifti1Image(pred_vol, ref_img.affine, ref_img.header)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export MyoPS-Net validation predictions to compact CARE labels")
    ap.add_argument("--data-root", type=Path, required=True, help="Per-fold staged data root, e.g. data/benchmarks/MyoPS-Net/fold_0")
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, default=None)
    ap.add_argument("--checkpoint-dir", type=Path, default=None, help="Folder containing *.pth; best score file is selected")
    ap.add_argument("--dim", type=int, default=192)
    ap.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument(
        "--variant",
        type=str,
        default=os.environ.get("MYOPS_NET_VARIANT", "challenge3"),
        choices=["full", "challenge3"],
    )
    args = ap.parse_args()

    ckpt = args.checkpoint
    if ckpt is None:
        ckpt_dir = args.checkpoint_dir
        if ckpt_dir is None:
            ckpt_dir = _repo_root() / "results" / "checkpoints" / "MyoPS-Net" / args.data_root.name / "checkpoints"
        ckpt = select_checkpoint(ckpt_dir)

    device = torch.device(args.device)
    model = MyoPSNet(in_chs=(5, 2, 2, 3), out_chs=(3, 3, 3, 3), variant=args.variant).to(device)
    state = torch.load(ckpt, map_location=device)
    model.load_state_dict(state)
    model.eval()

    normalize = Normalization()
    keep_lcc = LargestConnectedComponents()
    result_transform = ResultTransform(ToOriginal=False)

    cases = discover_val_cases(args.data_root)
    if not cases:
        raise FileNotFoundError(f"No validation cases found under {args.data_root / 'val_set' / 'val_image'}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for case_id, case_dir in cases:
        pred_img = run_case(model, case_dir, case_id, args.dim, device, normalize, keep_lcc, result_transform)
        nib.save(pred_img, str(args.output_dir / f"{case_id}.nii.gz"))
        print(f"Wrote {args.output_dir / f'{case_id}.nii.gz'}")


if __name__ == "__main__":
    main()
