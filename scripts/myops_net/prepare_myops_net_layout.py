#!/usr/bin/env python3
"""
Stage CARE MyoPS_train into MyoPS-Net expected layout under data/benchmarks/MyoPS-Net/.

Upstream expects (see third_party/MyoPS-Net): train_set/train_image, train_set/train_gd,
train.txt / validation.txt with lines: image_prefix gd_prefix z_index (paths relative to --path).

File naming per slice stack: prefix_C0.nii.gz, _LGE, _T2, _T1m, _T2starm, and gd: prefix_gd.nii.gz.
CARE provides C0, LGE, T2, gd; T1m and T2starm are zero-filled on the LGE grid.
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import SimpleITK as sitk


def discover_cases(root: Path) -> list[Path]:
    cases: list[Path] = []
    for p in sorted(root.glob("**/Case*")):
        if not p.is_dir():
            continue
        cid = p.name
        if (p / f"{cid}_LGE.nii.gz").is_file() and (p / f"{cid}_gd.nii.gz").is_file():
            cases.append(p)
    return cases


def _read_sitk(path: str) -> sitk.Image:
    return sitk.ReadImage(path)


def _resample_to_reference(moving: sitk.Image, reference: sitk.Image, is_label: bool) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def _blank_sitk(reference: sitk.Image, pixel_id: int | None = None) -> sitk.Image:
    pid = pixel_id if pixel_id is not None else reference.GetPixelID()
    blank = sitk.Image(reference.GetSize(), pid)
    blank.CopyInformation(reference)
    return blank


def write_zeros_like_lge(case_lge: Path, out_path: Path) -> None:
    ref = nib.load(str(case_lge))
    data = np.zeros(ref.shape, dtype=np.float32)
    img = nib.Nifti1Image(data, ref.affine, ref.header)
    nib.save(img, str(out_path))


def export_case(case_dir: Path, img_root: Path, gd_root: Path, rel_prefix: Path) -> int:
    """Write modalities into train_image / train_gd trees; return z-depth (slice count)."""
    cid = case_dir.name
    lge_src = case_dir / f"{cid}_LGE.nii.gz"
    gd_path = case_dir / f"{cid}_gd.nii.gz"
    t2_path = case_dir / f"{cid}_T2.nii.gz"
    c0_path = case_dir / f"{cid}_C0.nii.gz"

    ref = _read_sitk(str(lge_src))
    sub_img = img_root / rel_prefix
    sub_gd = gd_root / rel_prefix
    sub_img.mkdir(parents=True, exist_ok=True)
    sub_gd.mkdir(parents=True, exist_ok=True)

    def get_ch(p: Path | None) -> sitk.Image:
        if p is None or not p.is_file():
            return _blank_sitk(ref)
        mov = _read_sitk(str(p))
        return _resample_to_reference(mov, ref, is_label=False)

    lge_sitk = ref
    t2_sitk = get_ch(t2_path if t2_path.is_file() else None)
    c0_sitk = get_ch(c0_path if c0_path.is_file() else None)

    out_lge = sub_img / f"{cid}_LGE.nii.gz"
    sitk.WriteImage(lge_sitk, str(out_lge))
    sitk.WriteImage(t2_sitk, str(sub_img / f"{cid}_T2.nii.gz"))
    sitk.WriteImage(c0_sitk, str(sub_img / f"{cid}_C0.nii.gz"))

    # T1m / T2* placeholders (MyoPS-Net naming); match LGE geometry using source header
    write_zeros_like_lge(lge_src, sub_img / f"{cid}_T1m.nii.gz")
    write_zeros_like_lge(lge_src, sub_img / f"{cid}_T2starm.nii.gz")

    gd_sitk = _read_sitk(str(gd_path))
    gd_sitk = _resample_to_reference(gd_sitk, ref, is_label=True)
    sitk.WriteImage(gd_sitk, str(sub_gd / f"{cid}_gd.nii.gz"))

    return int(ref.GetSize()[2])


def write_list_file(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="CARE MyoPS_train -> MyoPS-Net folder layout")
    ap.add_argument(
        "--input",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/CARE_Challenge/MyoPS_train"),
        help="Path to MyoPS_train",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net"),
        help="Benchmark root (train_set/, train.txt created here)",
    )
    ap.add_argument("--val-ratio", type=float, default=0.2, help="Fraction of cases for validation (by count).")
    ap.add_argument("--max-cases", type=int, default=0, help="If >0, only use this many cases.")
    ap.add_argument("--seed", type=int, default=42, help="Shuffle seed for train/val split.")
    args = ap.parse_args()

    cases = discover_cases(args.input)
    if args.max_cases > 0:
        cases = cases[: args.max_cases]
    if not cases:
        print("No cases found.", file=sys.stderr)
        sys.exit(1)

    rng = random.Random(args.seed)
    rng.shuffle(cases)
    n_val = max(1, int(round(len(cases) * args.val_ratio))) if len(cases) > 1 else 0
    if len(cases) == 1:
        train_cases, val_cases = cases, []
    else:
        val_cases = cases[:n_val]
        train_cases = cases[n_val:]

    out = args.output
    tr_img = out / "train_set" / "train_image"
    tr_gd = out / "train_set" / "train_gd"
    va_img = out / "val_set" / "val_image"
    va_gd = out / "val_set" / "val_gd"

    def rel_prefix(center: str, cid: str) -> Path:
        return Path(center) / cid

    train_lines: list[str] = []
    val_lines: list[str] = []

    for case_dir in train_cases:
        center = case_dir.parent.name
        cid = case_dir.name
        rp = rel_prefix(center, cid)
        nz = export_case(case_dir, tr_img, tr_gd, rp)
        p_img = f"train_set/train_image/{rp}/{cid}"
        p_gd = f"train_set/train_gd/{rp}/{cid}"
        for z in range(nz):
            train_lines.append(f"{p_img} {p_gd} {z}")

    for case_dir in val_cases:
        center = case_dir.parent.name
        cid = case_dir.name
        rp = rel_prefix(center, cid)
        nz = export_case(case_dir, va_img, va_gd, rp)
        p_img = f"val_set/val_image/{rp}/{cid}"
        p_gd = f"val_set/val_gd/{rp}/{cid}"
        for z in range(nz):
            val_lines.append(f"{p_img} {p_gd} {z}")

    write_list_file(out / "train.txt", train_lines)
    write_list_file(out / "validation.txt", val_lines if val_lines else train_lines[: max(1, len(train_lines) // 10)])

    if not val_cases:
        print("Warning: single-case or empty val split; validation.txt duplicates a subset of train.", file=sys.stderr)

    print(f"Wrote MyoPS-Net staging to {out}")
    print(f"  train cases: {len(train_cases)}, val cases: {len(val_cases)}")
    print(f"  train lines: {len(train_lines)}, val lines: {len(val_lines)}")


if __name__ == "__main__":
    main()
