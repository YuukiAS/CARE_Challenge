#!/usr/bin/env python3
"""
Convert CARE CineMyoPS_train to nnU-Net v2 Dataset folder.

- Cine volumes are 4D (x, y, z, time). We export a single 3D frame (default: middle time index)
  to match the 3D label mask. ED frame selection is preferred when metadata exists.
- Single input channel: Cine (frame).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from nnunet_label_utils import remap_segmentation

try:
    from nnunetv2.dataset_conversion.generate_dataset_json import generate_dataset_json
except ImportError as e:
    raise SystemExit("nnunetv2 is required. Install: pip install nnunetv2") from e


def _extract_frame_3d(cine_path: Path, time_index: int | None) -> sitk.Image:
    img4d = sitk.ReadImage(str(cine_path))
    if img4d.GetDimension() != 4:
        raise ValueError(f"Expected 4D Cine, got dimension {img4d.GetDimension()} for {cine_path}")
    size4d = list(img4d.GetSize())  # x, y, z, t
    nt = size4d[3]
    t = (nt // 2) if time_index is None else int(time_index)
    t = max(0, min(nt - 1, t))

    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size4d[0], size4d[1], size4d[2], 0])
    extractor.SetIndex([0, 0, 0, t])
    return extractor.Execute(img4d)


def _resample_to_reference(moving: sitk.Image, reference: sitk.Image, is_label: bool) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def discover_pairs(root: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    for cine in sorted(root.glob("**/*_Cine.nii.gz")):
        cid = cine.name.replace("_Cine.nii.gz", "")
        parent = cine.parent
        gd = parent / f"{cid}_gd.nii.gz"
        if gd.is_file():
            pairs.append((cine, gd))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description="CineMyoPS_train -> nnU-Net v2 raw dataset")
    ap.add_argument(
        "--input",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/CARE_Challenge/CineMyoPS_train"),
        help="Path to CineMyoPS_train",
    )
    ap.add_argument(
        "--output",
        type=Path,
        required=True,
        help="e.g. .../nnUNet_raw/Dataset502_CARECineMyoPS",
    )
    ap.add_argument("--max-cases", type=int, default=0, help="If >0, only convert this many pairs.")
    ap.add_argument(
        "--time-index",
        type=int,
        default=-1,
        help="Time frame index for 4D Cine (-1 = middle frame).",
    )
    args = ap.parse_args()

    out_root = args.output
    images_tr = out_root / "imagesTr"
    labels_tr = out_root / "labelsTr"
    images_tr.mkdir(parents=True, exist_ok=True)
    labels_tr.mkdir(parents=True, exist_ok=True)

    pairs = discover_pairs(args.input)
    if args.max_cases > 0:
        pairs = pairs[: args.max_cases]

    ti = None if args.time_index < 0 else args.time_index

    # Dataset-specific compact relabel for nnU-Net (labels must be consecutive):
    # global nnU-Net ids from remap_segmentation: 0,1,2,3,4,5
    # Cine task effectively uses 0,1,2,5 -> map to 0,1,2,3.
    cine_compact_map = {
        0: 0,
        1: 1,  # myocardium
        2: 2,  # LV blood
        5: 3,  # scar
    }
    labels_compact = {
        "background": 0,
        "myocardium": 1,
        "LV_blood": 2,
        "scar": 3,
    }
    present_label_ids: set[int] = set()

    for cine_p, gd_p in pairs:
        cid = cine_p.name.replace("_Cine.nii.gz", "")
        cine_3d = _extract_frame_3d(cine_p, ti)
        sitk.WriteImage(cine_3d, str(images_tr / f"{cid}_0000.nii.gz"))

        gd_img = sitk.ReadImage(str(gd_p))
        gd_img = _resample_to_reference(gd_img, cine_3d, is_label=True)
        gd_arr = sitk.GetArrayFromImage(gd_img)
        rem = remap_segmentation(gd_arr)
        rem_compact = np.zeros_like(rem, dtype=np.uint8)
        for src, dst in cine_compact_map.items():
            rem_compact[rem == src] = dst
        present_label_ids.update(np.unique(rem_compact).astype(int).tolist())
        out_lab = sitk.GetImageFromArray(rem_compact.astype(np.uint8))
        out_lab.CopyInformation(gd_img)
        sitk.WriteImage(out_lab, str(labels_tr / f"{cid}.nii.gz"))

    generate_dataset_json(
        str(out_root),
        channel_names={0: "Cine"},
        labels=labels_compact,
        num_training_cases=len(pairs),
        file_ending=".nii.gz",
        dataset_name=args.output.name,
        description="CARE CineMyoPS_train (single Cine frame, middle time by default)",
        reference="CARE challenge / CineMyoPS_train",
    )
    print(f"Wrote {len(pairs)} cases to {out_root}")
    print(f"Present compact labels in Cine dataset: {sorted(present_label_ids)}")


if __name__ == "__main__":
    main()
