#!/usr/bin/env python3
"""
Export CARE MyoPS_train into U-MyoPS / jrs dataloader layout (see jrs/dataloader/jrsdataset.py).

Each subject directory must contain files matching:
  *img_c0*, *img_t2*, *img_de* (DE = LGE) and *ana_c0*, *ana_patho_t2*, *ana_patho_de* label stacks.

We use CARE filenames: copy/resample NIfTI; unified gd for all three label paths (clinical approximation).
Output default: data/benchmarks/U-MyoPS/gen_ZS_unaligned/data/<center>_<case>/
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk


def discover_cases(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in sorted(root.glob("**/Case*")):
        if not p.is_dir():
            continue
        cid = p.name
        if (p / f"{cid}_LGE.nii.gz").is_file() and (p / f"{cid}_gd.nii.gz").is_file():
            out.append(p)
    return out


def resample(moving: sitk.Image, reference: sitk.Image, is_label: bool) -> sitk.Image:
    r = sitk.ResampleImageFilter()
    r.SetReferenceImage(reference)
    r.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    r.SetDefaultPixelValue(0)
    return r.Execute(moving)


def compute_square_bbox(mask_2d: np.ndarray, padding: int = 16) -> dict[str, int]:
    ys, xs = np.where(mask_2d > 0)
    h, w = mask_2d.shape
    if len(xs) == 0 or len(ys) == 0:
        return {"x0": 0, "y0": 0, "x1": w, "y1": h}

    x0 = int(xs.min())
    x1 = int(xs.max()) + 1
    y0 = int(ys.min())
    y1 = int(ys.max()) + 1

    side = max(x1 - x0, y1 - y0) + padding * 2
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0

    half = side / 2.0
    x0 = int(round(cx - half))
    x1 = int(round(cx + half))
    y0 = int(round(cy - half))
    y1 = int(round(cy + half))

    if x0 < 0:
        x1 -= x0
        x0 = 0
    if y0 < 0:
        y1 -= y0
        y0 = 0
    if x1 > w:
        x0 -= x1 - w
        x1 = w
    if y1 > h:
        y0 -= y1 - h
        y1 = h

    x0 = max(0, x0)
    y0 = max(0, y0)
    x1 = min(w, x1)
    y1 = min(h, y1)
    return {"x0": int(x0), "y0": int(y0), "x1": int(x1), "y1": int(y1)}


def write_subject_manifest(
    out_subj: Path,
    *,
    center: str,
    cid: str,
    subj_name: str,
    ref: sitk.Image,
    label_img: sitk.Image,
    has_c0: bool,
    has_t2: bool,
) -> None:
    label_arr = sitk.GetArrayFromImage(label_img)
    valid_slices: list[dict[str, object]] = []
    for z in range(label_arr.shape[0]):
        mask = label_arr[z] > 0
        if not np.any(mask):
            continue
        valid_slices.append({"z": z, "bbox": compute_square_bbox(mask)})

    if not valid_slices:
        z = int(label_arr.shape[0] // 2)
        valid_slices.append({"z": z, "bbox": compute_square_bbox(label_arr[z] > 0)})

    manifest = {
        "subject_id": subj_name,
        "case_id": cid,
        "center": center,
        "reference_size_xyz": list(ref.GetSize()),
        "reference_spacing_xyz": list(ref.GetSpacing()),
        "modalities_present": {"c0": has_c0, "t2": has_t2, "de": True},
        "valid_slices": valid_slices,
    }
    (out_subj / "subject_meta.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def export_subject(case_dir: Path, out_subj: Path) -> None:
    cid = case_dir.name
    center = case_dir.parent.name
    subj_name = f"{center}_{cid}"
    out_subj.mkdir(parents=True, exist_ok=True)

    lge = case_dir / f"{cid}_LGE.nii.gz"
    gd = case_dir / f"{cid}_gd.nii.gz"
    t2 = case_dir / f"{cid}_T2.nii.gz"
    c0 = case_dir / f"{cid}_C0.nii.gz"
    has_c0 = c0.is_file()
    has_t2 = t2.is_file()

    ref = sitk.ReadImage(str(lge))

    def maybe_resample(p: Path) -> sitk.Image:
        if not p.is_file():
            blank = sitk.Image(ref.GetSize(), ref.GetPixelID())
            blank.CopyInformation(ref)
            return blank
        im = sitk.ReadImage(str(p))
        return resample(im, ref, is_label=False)

    im_c0 = maybe_resample(c0)
    im_t2 = maybe_resample(t2)
    im_de = ref
    lb = resample(sitk.ReadImage(str(gd)), ref, is_label=True)

    # Filenames must match sort_glob patterns in jrsdataset._getsample
    sitk.WriteImage(im_c0, str(out_subj / f"{subj_name}_img_c0_{cid}.nii.gz"))
    sitk.WriteImage(im_t2, str(out_subj / f"{subj_name}_img_t2_{cid}.nii.gz"))
    sitk.WriteImage(im_de, str(out_subj / f"{subj_name}_img_de_{cid}.nii.gz"))
    sitk.WriteImage(lb, str(out_subj / f"{subj_name}_ana_c0_{cid}.nii.gz"))
    sitk.WriteImage(lb, str(out_subj / f"{subj_name}_ana_patho_t2_{cid}.nii.gz"))
    sitk.WriteImage(lb, str(out_subj / f"{subj_name}_ana_patho_de_{cid}.nii.gz"))
    write_subject_manifest(
        out_subj,
        center=center,
        cid=cid,
        subj_name=subj_name,
        ref=ref,
        label_img=lb,
        has_c0=has_c0,
        has_t2=has_t2,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="CARE MyoPS_train -> U-MyoPS jrs folder layout")
    ap.add_argument(
        "--input",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/CARE_Challenge/MyoPS_train"),
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/benchmarks/U-MyoPS/gen_ZS_unaligned/data"),
        help="Directory of per-subject folders (mirrors ../data/gen_ZS_unaligned/data from jrs).",
    )
    ap.add_argument("--max-cases", type=int, default=0)
    args = ap.parse_args()

    cases = discover_cases(args.input)
    if args.max_cases > 0:
        cases = cases[: args.max_cases]
    if not cases:
        print("No cases found.", file=sys.stderr)
        sys.exit(1)

    args.output.mkdir(parents=True, exist_ok=True)
    for case_dir in cases:
        center = case_dir.parent.name
        cid = case_dir.name
        out_subj = args.output / f"{center}_{cid}"
        if out_subj.exists():
            shutil.rmtree(out_subj)
        export_subject(case_dir, out_subj)

    print(f"Exported {len(cases)} subjects to {args.output}")


if __name__ == "__main__":
    main()
