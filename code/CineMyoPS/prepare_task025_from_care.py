#!/usr/bin/env python3
"""
Export CARE CineMyoPS_train into nnU-Net v1 task folder Task025_Cine_Seg (file naming matches
third_party/CineMyoPS/code/nnunet/preprocessing/sanity_checks.py).

dataset.json "image" must be ./imagesTr/{case_id}.nii.gz (case_id without _0000); nnU-Net appends _%04d for modalities.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

# Reuse CARE label remap logic (copy compact mapping from code/nnUNet/convert_cine)
_SCRIPT = Path(__file__).resolve().parent.parent / "nnUNet"
if str(_SCRIPT) not in sys.path:
    sys.path.insert(0, str(_SCRIPT))
from nnunet_label_utils import remap_segmentation


def _extract_frame_3d(cine_path: Path, time_index: int | None) -> sitk.Image:
    img4d = sitk.ReadImage(str(cine_path))
    if img4d.GetDimension() != 4:
        raise ValueError(f"Expected 4D Cine, got dimension {img4d.GetDimension()} for {cine_path}")
    size4d = list(img4d.GetSize())
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
        gd = cine.parent / f"{cid}_gd.nii.gz"
        if gd.is_file():
            pairs.append((cine, gd))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description="CARE CineMyoPS_train -> Task025_Cine_Seg (nnUNet v1 raw)")
    ap.add_argument(
        "--input",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/CARE_Challenge/CineMyoPS_train"),
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/benchmarks/CineMyoPS/Task025_Cine_Seg"),
        help="Task folder (contains imagesTr, labelsTr, dataset.json)",
    )
    ap.add_argument("--max-cases", type=int, default=0)
    ap.add_argument("--time-index", type=int, default=-1, help="-1 = temporal midpoint")
    args = ap.parse_args()

    pairs = discover_pairs(args.input)
    if args.max_cases > 0:
        pairs = pairs[: args.max_cases]
    if not pairs:
        print("No cine/gd pairs found.", file=sys.stderr)
        sys.exit(1)

    out = args.output
    im_tr = out / "imagesTr"
    lb_tr = out / "labelsTr"
    im_tr.mkdir(parents=True, exist_ok=True)
    lb_tr.mkdir(parents=True, exist_ok=True)

    ti = None if args.time_index < 0 else args.time_index
    cine_compact_map = {0: 0, 1: 1, 2: 2, 5: 3}

    training = []
    names: list[str] = []

    for cine_p, gd_p in pairs:
        cid = cine_p.name.replace("_Cine.nii.gz", "")
        center = cine_p.parent.name
        # nnU-Net raw naming: case id without channel suffix; images use <case>_0000.nii.gz
        case_id = f"{center}_{cid}"
        names.append(case_id)

        cine_3d = _extract_frame_3d(cine_p, ti)
        sitk.WriteImage(cine_3d, str(im_tr / f"{case_id}_0000.nii.gz"))

        gd_img = sitk.ReadImage(str(gd_p))
        gd_img = _resample_to_reference(gd_img, cine_3d, is_label=True)
        gd_arr = sitk.GetArrayFromImage(gd_img)
        rem = remap_segmentation(gd_arr)
        rem_compact = np.zeros_like(rem, dtype=np.uint8)
        for src, dst in cine_compact_map.items():
            rem_compact[rem == src] = dst
        out_lab = sitk.GetImageFromArray(rem_compact.astype(np.uint8))
        out_lab.CopyInformation(gd_img)
        sitk.WriteImage(out_lab, str(lb_tr / f"{case_id}.nii.gz"))

        training.append(
            {
                "image": f"./imagesTr/{case_id}.nii.gz",
                "label": f"./labelsTr/{case_id}.nii.gz",
            }
        )

    ds = {
        "name": "Cine_Seg",
        "description": "CARE CineMyoPS_train (single frame)",
        "tensorImageSize": "3D",
        "reference": "CARE",
        "licence": "",
        "release": "0.0",
        "modality": {"0": "Cine"},
        "labels": {
            "0": "background",
            "1": "myocardium",
            "2": "LV_blood",
            "3": "scar",
        },
        "numTraining": len(training),
        "numTest": 0,
        "training": training,
        "test": [],
    }
    with (out / "dataset.json").open("w", encoding="utf-8") as f:
        json.dump(ds, f, indent=2)

    print(f"Wrote {len(pairs)} cases to {out}")
    print("Next: link or copy this folder under CineMyoPS outputs/nnunet/raw/nnUNet_raw_data/ (see run_train.sh).")


if __name__ == "__main__":
    main()
