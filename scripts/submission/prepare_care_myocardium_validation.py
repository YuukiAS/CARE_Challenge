#!/usr/bin/env python3
"""Prepare CARE-Myocardium validation predictions and submission zip.

Official validation submission structure:
https://zmic.org.cn/care_2026/valid_submission/
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import numpy as np
import SimpleITK as sitk


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUN_NAME = "nnunet_5fold_best"
DEFAULT_NNUNET = REPO_ROOT / "env_CARE" / "bin" / "nnUNetv2_predict"

MYOPS_COMPACT_TO_RAW = {
    0: 0,
    1: 200,
    2: 500,
    3: 600,
    4: 1220,
    5: 2221,
}
CINE_COMPACT_TO_RAW = {
    0: 0,
    1: 200,
    2: 500,
    3: 2221,
}


def read_sitk(path: Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def resample_to_reference(moving: sitk.Image, reference: sitk.Image, *, is_label: bool) -> sitk.Image:
    resampler = sitk.ResampleImageFilter()
    resampler.SetReferenceImage(reference)
    resampler.SetInterpolator(sitk.sitkNearestNeighbor if is_label else sitk.sitkLinear)
    resampler.SetDefaultPixelValue(0)
    return resampler.Execute(moving)


def blank_like(reference: sitk.Image) -> sitk.Image:
    blank = sitk.Image(reference.GetSize(), reference.GetPixelID())
    blank.CopyInformation(reference)
    return blank


def extract_frame_3d(cine_path: Path, time_index: int | None) -> sitk.Image:
    img4d = read_sitk(cine_path)
    if img4d.GetDimension() != 4:
        raise ValueError(f"Expected 4D Cine, got dimension {img4d.GetDimension()} for {cine_path}")
    size4d = list(img4d.GetSize())
    nt = size4d[3]
    t = nt // 2 if time_index is None else int(time_index)
    t = max(0, min(nt - 1, t))

    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size4d[0], size4d[1], size4d[2], 0])
    extractor.SetIndex([0, 0, 0, t])
    return extractor.Execute(img4d)


def discover_myops_cases(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("**/Case*") if p.is_dir() and (p / f"{p.name}_LGE.nii.gz").is_file())


def discover_cine_cases(root: Path) -> list[Path]:
    return sorted(root.glob("**/Case*_Cine.nii.gz"))


def reset_dir(path: Path, overwrite: bool) -> None:
    if path.exists() and overwrite:
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def prepare_myops_inputs(input_root: Path, output_dir: Path, overwrite: bool) -> list[str]:
    reset_dir(output_dir, overwrite)
    case_ids: list[str] = []
    for case_dir in discover_myops_cases(input_root):
        cid = case_dir.name
        case_ids.append(cid)
        ref = read_sitk(case_dir / f"{cid}_LGE.nii.gz")
        t2_path = case_dir / f"{cid}_T2.nii.gz"
        c0_path = case_dir / f"{cid}_C0.nii.gz"

        channels = [
            ref,
            resample_to_reference(read_sitk(t2_path), ref, is_label=False) if t2_path.is_file() else blank_like(ref),
            resample_to_reference(read_sitk(c0_path), ref, is_label=False) if c0_path.is_file() else blank_like(ref),
        ]
        for channel_idx, image in enumerate(channels):
            sitk.WriteImage(image, str(output_dir / f"{cid}_{channel_idx:04d}.nii.gz"))
    return case_ids


def prepare_cine_inputs(input_root: Path, output_dir: Path, overwrite: bool, time_index: int | None) -> list[str]:
    reset_dir(output_dir, overwrite)
    case_ids: list[str] = []
    for cine_path in discover_cine_cases(input_root):
        cid = cine_path.name.replace("_Cine.nii.gz", "")
        case_ids.append(cid)
        image = extract_frame_3d(cine_path, time_index)
        sitk.WriteImage(image, str(output_dir / f"{cid}_0000.nii.gz"))
    return case_ids


def nnunet_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CARE_ROOT", str(REPO_ROOT))
    env.setdefault("nnUNet_raw", str(REPO_ROOT / "data" / "nnUNet" / "nnUNet_raw"))
    env.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data" / "nnUNet" / "nnUNet_preprocessed"))
    env.setdefault("nnUNet_results", str(REPO_ROOT / "data" / "nnUNet" / "nnUNet_results"))
    return env


def run_predict(
    nnunet_predict: Path,
    dataset_id: str,
    input_dir: Path,
    output_dir: Path,
    folds: list[str],
    checkpoint: str,
    device: str,
    continue_prediction: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(nnunet_predict),
        "-d",
        dataset_id,
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-c",
        "3d_fullres",
        "-tr",
        "nnUNetTrainer_500epochs",
        "-p",
        "nnUNetPlans",
        "-f",
        *folds,
        "-chk",
        checkpoint,
        "-device",
        device,
        "-npp",
        "1",
        "-nps",
        "1",
        "--disable_progress_bar",
    ]
    if continue_prediction:
        cmd.append("--continue_prediction")
    print("Running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=REPO_ROOT, env=nnunet_env())


def remap_prediction(pred_path: Path, out_path: Path, mapping: dict[int, int]) -> None:
    image = read_sitk(pred_path)
    arr = sitk.GetArrayFromImage(image).astype(np.int32, copy=False)
    out = np.zeros_like(arr, dtype=np.uint16)
    for compact, raw in mapping.items():
        out[arr == compact] = raw
    out_image = sitk.GetImageFromArray(out)
    out_image.CopyInformation(image)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out_image, str(out_path))


def build_submission(
    myops_pred_dir: Path,
    cine_pred_dir: Path,
    submission_dir: Path,
    myops_case_ids: list[str],
    cine_case_ids: list[str],
) -> None:
    if submission_dir.exists():
        shutil.rmtree(submission_dir)
    for cid in myops_case_ids:
        remap_prediction(
            myops_pred_dir / f"{cid}.nii.gz",
            submission_dir / "MyoPS" / "Anonymous Center" / cid / f"{cid}_pred.nii.gz",
            MYOPS_COMPACT_TO_RAW,
        )
    for cid in cine_case_ids:
        remap_prediction(
            cine_pred_dir / f"{cid}.nii.gz",
            submission_dir / "CineMyoPS" / "Anonymous Center" / cid / f"{cid}_pred.nii.gz",
            CINE_COMPACT_TO_RAW,
        )


def zip_submission(submission_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(submission_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(submission_dir))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--myops-val", type=Path, default=REPO_ROOT / "data" / "CARE_Challenge" / "MyoPS_val")
    parser.add_argument("--cine-val", type=Path, default=REPO_ROOT / "data" / "CARE_Challenge" / "CineMyoPS_val")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT / "results" / "submissions" / "care_myocardium_validation")
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME, help="Prediction workspace name under output-root.")
    parser.add_argument(
        "--timestamp",
        default=None,
        help="Timestamp for the submission package name (default: current local YYYYMMDD_HHMMSS).",
    )
    parser.add_argument(
        "--no-timestamp",
        action="store_true",
        help="Do not append a timestamp to submission package names.",
    )
    parser.add_argument("--team-name", default="OrganAgent")
    parser.add_argument("--folds", nargs="+", default=["0", "1", "2", "3", "4"])
    parser.add_argument("--checkpoint", default="checkpoint_best.pth")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu", "mps"])
    parser.add_argument("--time-index", type=int, default=-1, help="Cine frame index; -1 matches training default middle frame.")
    parser.add_argument("--nnunet-predict", type=Path, default=DEFAULT_NNUNET)
    parser.add_argument("--overwrite-inputs", action="store_true")
    parser.add_argument("--skip-predict", action="store_true", help="Reuse existing nnU-Net output folders and only rebuild submission zip.")
    parser.add_argument("--continue-prediction", action="store_true")
    parser.add_argument("--task", choices=["both", "myops", "cine"], default="both")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.nnunet_predict.is_file() and not args.skip_predict:
        raise FileNotFoundError(f"nnUNetv2_predict not found: {args.nnunet_predict}")

    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    package_name = f"CARE-Myocardium-{args.team_name}" if args.no_timestamp else f"CARE-Myocardium-{args.team_name}_{timestamp}"

    run_root = args.output_root / args.run_name
    input_root = run_root / "nnunet_inputs"
    pred_root = run_root / "nnunet_predictions"
    package_root = run_root / "packages"
    submission_dir = package_root / package_name
    zip_path = package_root / f"{package_name}.zip"

    ti = None if args.time_index < 0 else args.time_index
    myops_input = input_root / "MyoPS"
    cine_input = input_root / "CineMyoPS"
    myops_pred = pred_root / "Dataset501_CAREMyoPS"
    cine_pred = pred_root / "Dataset502_CARECineMyoPS"

    myops_case_ids: list[str] = []
    cine_case_ids: list[str] = []
    if args.task in {"both", "myops"}:
        myops_case_ids = prepare_myops_inputs(args.myops_val, myops_input, args.overwrite_inputs)
        print(f"Prepared {len(myops_case_ids)} MyoPS validation cases -> {myops_input}", flush=True)
    if args.task in {"both", "cine"}:
        cine_case_ids = prepare_cine_inputs(args.cine_val, cine_input, args.overwrite_inputs, ti)
        print(f"Prepared {len(cine_case_ids)} CineMyoPS validation cases -> {cine_input}", flush=True)

    if not args.skip_predict:
        if args.task in {"both", "myops"}:
            run_predict(args.nnunet_predict, "501", myops_input, myops_pred, args.folds, args.checkpoint, args.device, args.continue_prediction)
        if args.task in {"both", "cine"}:
            run_predict(args.nnunet_predict, "502", cine_input, cine_pred, args.folds, args.checkpoint, args.device, args.continue_prediction)

    if args.task != "both":
        raise SystemExit("Packaging requires --task both so both leaderboard folders are present.")
    build_submission(myops_pred, cine_pred, submission_dir, myops_case_ids, cine_case_ids)
    zip_submission(submission_dir, zip_path)

    manifest = {
        "created_at_local": datetime.now().isoformat(timespec="seconds"),
        "official_format": "https://zmic.org.cn/care_2026/valid_submission/",
        "team_name": args.team_name,
        "run_name": args.run_name,
        "package_name": package_name,
        "timestamp": timestamp,
        "folds": args.folds,
        "checkpoint": args.checkpoint,
        "device": args.device,
        "myops_cases": len(myops_case_ids),
        "cine_cases": len(cine_case_ids),
        "zip": str(zip_path),
    }
    manifest_path = package_root / f"{package_name}_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(__import__("json").dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Submission zip -> {zip_path}", flush=True)
    print(f"Manifest -> {manifest_path}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
