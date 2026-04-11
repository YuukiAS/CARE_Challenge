#!/usr/bin/env python3
"""
Convert CARE MyoPS_train (multi-sequence NIfTI) to nnU-Net v2 Dataset folder.

- Reference grid: LGE. T2 and C0 are resampled to LGE with SimpleITK.
- Missing T2 or C0: zero-filled image on the LGE grid.
- Channels: 0=LGE, 1=T2, 2=C0 (bSSFP).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import SimpleITK as sitk
# Allow running as script from repo
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from nnunet_label_utils import labels_dict_for_dataset_json, remap_segmentation

try:
    from nnunetv2.dataset_conversion.generate_dataset_json import generate_dataset_json
except ImportError as e:
    raise SystemExit("nnunetv2 is required. Install: pip install nnunetv2") from e


def _read_sitk(path: str) -> sitk.Image:
    return sitk.ReadImage(path)


def _resample_to_reference(moving: sitk.Image, reference: sitk.Image, is_label: bool) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def _blank_like(reference: sitk.Image, pixel_id: int | None = None) -> sitk.Image:
    pid = pixel_id if pixel_id is not None else reference.GetPixelID()
    blank = sitk.Image(reference.GetSize(), pid)
    blank.CopyInformation(reference)
    return blank


def discover_cases(root: Path) -> list[Path]:
    cases: list[Path] = []
    for p in sorted(root.glob("**/Case*")):
        if not p.is_dir():
            continue
        cid = p.name
        if (p / f"{cid}_LGE.nii.gz").is_file():
            cases.append(p)
    return cases


def convert_case(case_dir: Path, out_images: Path, out_labels: Path, case_id: str) -> None:
    cid = case_dir.name
    lge_path = case_dir / f"{cid}_LGE.nii.gz"
    gd_path = case_dir / f"{cid}_gd.nii.gz"
    t2_path = case_dir / f"{cid}_T2.nii.gz"
    c0_path = case_dir / f"{cid}_C0.nii.gz"

    ref = _read_sitk(str(lge_path))

    def get_ch(path: Path | None) -> sitk.Image:
        if path is None or not path.is_file():
            return _blank_like(ref)
        mov = _read_sitk(str(path))
        return _resample_to_reference(mov, ref, is_label=False)

    lge_sitk = ref
    t2_sitk = get_ch(t2_path if t2_path.is_file() else None)
    c0_sitk = get_ch(c0_path if c0_path.is_file() else None)

    for i, vol in enumerate((lge_sitk, t2_sitk, c0_sitk)):
        out_p = out_images / f"{case_id}_{i:04d}.nii.gz"
        sitk.WriteImage(vol, str(out_p))

    gd_sitk = _read_sitk(str(gd_path))
    gd_sitk = _resample_to_reference(gd_sitk, ref, is_label=True)
    arr = sitk.GetArrayFromImage(gd_sitk)
    # SimpleITK uses z,y,x; nibabel uses different — GetArrayFromImage is z,y,x consistent with itk
    rem = remap_segmentation(arr)
    out_lab = sitk.GetImageFromArray(rem)
    out_lab.CopyInformation(gd_sitk)
    sitk.WriteImage(out_lab, str(out_labels / f"{case_id}.nii.gz"))


def main() -> None:
    ap = argparse.ArgumentParser(description="MyoPS_train -> nnU-Net v2 raw dataset")
    ap.add_argument(
        "--input",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/CARE_Challenge/MyoPS_train"),
        help="Path to MyoPS_train",
    )
    ap.add_argument(
        "--output",
        type=Path,
        required=True,
        help="e.g. .../nnUNet_raw/Dataset501_CAREMyoPS",
    )
    ap.add_argument("--max-cases", type=int, default=0, help="If >0, only convert this many cases (sorted order).")
    args = ap.parse_args()

    out_root = args.output
    images_tr = out_root / "imagesTr"
    labels_tr = out_root / "labelsTr"
    images_tr.mkdir(parents=True, exist_ok=True)
    labels_tr.mkdir(parents=True, exist_ok=True)

    cases = discover_cases(args.input)
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    for case_dir in cases:
        convert_case(case_dir, images_tr, labels_tr, case_dir.name)

    labels = labels_dict_for_dataset_json()
    generate_dataset_json(
        str(out_root),
        channel_names={0: "LGE", 1: "T2", 2: "C0"},
        labels=labels,
        num_training_cases=len(cases),
        file_ending=".nii.gz",
        dataset_name=args.output.name,
        description="data/CARE_Challenge/MyoPS_train (LGE ref, missing modalities zero)",
        reference="CARE challenge / MyoPS_train",
    )
    print(f"Wrote {len(cases)} cases to {out_root}")


if __name__ == "__main__":
    main()
