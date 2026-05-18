#!/usr/bin/env python3
"""Prepare CARE-Myocardium validation predictions and upload zip.

Official validation layout:
  CARE-Myocardium-TeamName.zip
  ├── MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz
  └── CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz

The website expects the zip name without a timestamp. This script stores each
submission under a timestamped folder, then writes the upload zip with the
official fixed filename inside that folder.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath

import numpy as np
import SimpleITK as sitk


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NNUNET = REPO_ROOT / "env_CARE" / "bin" / "nnUNetv2_predict"
SUBMISSION_ROOT = REPO_ROOT / "results" / "submissions" / "care_myocardium_validation"

MYOPS_MODELS = {"nnUNet", "MyoPS-Net", "U-MyoPS"}
CINE_MODELS = {"nnUNet", "CineMyoPS"}
MODEL_ALIASES = {
    "nnunet": "nnUNet",
    "nnUNet": "nnUNet",
    "myops": "MyoPS-Net",
    "MyoPS": "MyoPS-Net",
    "myops-net": "MyoPS-Net",
    "MyoPS-Net": "MyoPS-Net",
    "umyops": "U-MyoPS",
    "U-MyoPS": "U-MyoPS",
    "cinemyops": "CineMyoPS",
    "CineMyoPS": "CineMyoPS",
}

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
PATHOLOGY_RAW_LABEL = 2221
SUBMISSION_ALLOWED_LABELS = {
    "MyoPS": {0, 200, 500, 600, 1220, 2221},
    "CineMyoPS": {0, 200, 500, 2221},
}
SUBMISSION_REQUIRED_PATHOLOGY = {
    "MyoPS": {1220, 2221},
    "CineMyoPS": {2221},
}


def read_sitk(path: Path) -> sitk.Image:
    return sitk.ReadImage(str(path))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sanitize_name(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z_.+-]+", "-", text).strip("-") or "submission"


def canonical_model(name: str) -> str:
    if name not in MODEL_ALIASES:
        raise ValueError(f"Unknown model alias '{name}'. Known: {sorted(MODEL_ALIASES)}")
    return MODEL_ALIASES[name]


def reset_dir(path: Path, overwrite: bool = True) -> None:
    if path.exists() and overwrite:
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


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


def sample_frame_indices(num_total_frames: int, num_sampled_frames: int) -> list[int]:
    if not 1 <= num_sampled_frames <= num_total_frames:
        raise ValueError(f"Cannot sample {num_sampled_frames} frames from {num_total_frames}")
    targets = np.linspace(0.0, float(num_total_frames - 1), num=num_sampled_frames)
    indices: list[int] = []
    used: set[int] = set()
    for target in targets:
        candidates = sorted(range(num_total_frames), key=lambda idx: (abs(idx - target), idx))
        chosen = next(idx for idx in candidates if idx not in used)
        indices.append(chosen)
        used.add(chosen)
    indices[0] = 0
    return indices


def discover_myops_cases(root: Path) -> list[Path]:
    return sorted(p for p in root.glob("**/Case*") if p.is_dir() and (p / f"{p.name}_LGE.nii.gz").is_file())


def discover_cine_cases(root: Path) -> list[Path]:
    return sorted(root.glob("**/Case*_Cine.nii.gz"))


def nnunet_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("CARE_ROOT", str(REPO_ROOT))
    env.setdefault("nnUNet_raw", str(REPO_ROOT / "data" / "nnUNet" / "nnUNet_raw"))
    env.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data" / "nnUNet" / "nnUNet_preprocessed"))
    env.setdefault("nnUNet_results", str(REPO_ROOT / "data" / "nnUNet" / "nnUNet_results"))
    env.setdefault("nnUNet_raw_data_base", str(REPO_ROOT / "data" / "nnUNet"))
    env.setdefault("RESULTS_FOLDER", str(REPO_ROOT / "data" / "nnUNet" / "nnUNet_results"))
    return env


def prepare_nnunet_myops_inputs(input_root: Path, output_dir: Path, overwrite: bool) -> list[str]:
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


def prepare_nnunet_cine_inputs(input_root: Path, output_dir: Path, overwrite: bool, time_index: int | None) -> list[str]:
    reset_dir(output_dir, overwrite)
    case_ids: list[str] = []
    for cine_path in discover_cine_cases(input_root):
        cid = cine_path.name.replace("_Cine.nii.gz", "")
        case_ids.append(cid)
        image = extract_frame_3d(cine_path, time_index)
        sitk.WriteImage(image, str(output_dir / f"{cid}_0000.nii.gz"))
    return case_ids


def prepare_myops_net_inputs(input_root: Path, output_root: Path, overwrite: bool) -> list[str]:
    val_image = output_root / "val_set" / "val_image"
    reset_dir(val_image, overwrite)
    case_ids: list[str] = []
    for case_dir in discover_myops_cases(input_root):
        center = case_dir.parent.name
        cid = case_dir.name
        case_ids.append(cid)
        out_case = val_image / center / cid
        out_case.mkdir(parents=True, exist_ok=True)
        ref = read_sitk(case_dir / f"{cid}_LGE.nii.gz")
        channels = {
            "LGE": ref,
            "T2": resample_to_reference(read_sitk(case_dir / f"{cid}_T2.nii.gz"), ref, is_label=False)
            if (case_dir / f"{cid}_T2.nii.gz").is_file()
            else blank_like(ref),
            "C0": resample_to_reference(read_sitk(case_dir / f"{cid}_C0.nii.gz"), ref, is_label=False)
            if (case_dir / f"{cid}_C0.nii.gz").is_file()
            else blank_like(ref),
            "T1m": blank_like(ref),
            "T2starm": blank_like(ref),
        }
        for name, image in channels.items():
            sitk.WriteImage(image, str(out_case / f"{cid}_{name}.nii.gz"))
    return case_ids


def prepare_cinemyops_inputs(input_root: Path, output_dir: Path, overwrite: bool, num_frames: int) -> list[str]:
    reset_dir(output_dir, overwrite)
    case_ids: list[str] = []
    for cine_path in discover_cine_cases(input_root):
        cid = cine_path.name.replace("_Cine.nii.gz", "")
        image4d = read_sitk(cine_path)
        if image4d.GetDimension() != 4:
            raise ValueError(f"Expected 4D Cine, got dimension {image4d.GetDimension()} for {cine_path}")
        frame_indices = sample_frame_indices(image4d.GetSize()[3], num_frames)
        case_ids.append(cid)
        for channel_idx, time_index in enumerate(frame_indices):
            frame = extract_frame_3d(cine_path, time_index)
            sitk.WriteImage(frame, str(output_dir / f"{cid}_{channel_idx:04d}.nii.gz"))
    return case_ids


def run_nnunet_predict(
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


def available_myops_net_folds(requested: list[str]) -> list[str]:
    out: list[str] = []
    for fold in requested:
        if (REPO_ROOT / "results" / "checkpoints" / "MyoPS-Net" / f"fold_{fold}" / "checkpoints").is_dir():
            out.append(fold)
    return out


def available_cinemyops_folds(requested: list[str], task: str, trainer: str, dim: str) -> list[str]:
    base = (
        REPO_ROOT
        / "data"
        / "nnUNet"
        / "nnUNet_results"
        / "nnUNet"
        / dim
        / task
        / f"{trainer}__nnUNetPlansv2.1"
    )
    return [fold for fold in requested if (base / f"fold_{fold}").is_dir()]


def run_myops_net_predict(data_root: Path, output_dir: Path, fold: str, device: str, variant: str) -> None:
    ckpt_dir = REPO_ROOT / "results" / "checkpoints" / "MyoPS-Net" / f"fold_{fold}" / "checkpoints"
    cmd = [
        str(REPO_ROOT / "env_CARE" / "bin" / "python"),
        str(REPO_ROOT / "code" / "MyoPS-Net" / "export_val_predictions.py"),
        "--data-root",
        str(data_root),
        "--output-dir",
        str(output_dir),
        "--checkpoint-dir",
        str(ckpt_dir),
        "--device",
        device,
        "--variant",
        variant,
    ]
    print("Running:", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=REPO_ROOT, env=nnunet_env())


def run_cinemyops_predict(
    input_dir: Path,
    output_dir: Path,
    fold: str,
    task: str,
    trainer: str,
    dim: str,
    checkpoint: str,
    combine_mode: str,
    num_frames: int,
) -> None:
    reset_dir(output_dir, True)
    cmd = [
        "bash",
        str(REPO_ROOT / "code" / "CineMyoPS" / "run_test.sh"),
        "-i",
        str(input_dir),
        "-o",
        str(output_dir),
        "-t",
        task,
        "-tr",
        trainer,
        "-m",
        dim,
        "-f",
        fold,
        "--chk",
        checkpoint,
        "--overwrite_existing",
        "--disable_tta",
    ]
    print("Running:", " ".join(cmd), flush=True)
    print(f"CineMyoPS env: CINE_COMBINE_MODE={combine_mode} CINE_NUM_FRAMES={num_frames}", flush=True)
    env = nnunet_env()
    env["CINE_COMBINE_MODE"] = combine_mode
    env["CINE_NUM_FRAMES"] = str(num_frames)
    subprocess.run(cmd, check=True, cwd=REPO_ROOT, env=env)


def find_prediction(src_dir: Path, case_id: str) -> Path:
    exact = src_dir / f"{case_id}.nii.gz"
    if exact.is_file():
        return exact
    matches = sorted(src_dir.glob(f"*_{case_id}.nii.gz"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"Could not resolve prediction for {case_id} in {src_dir}")


def copy_exact_predictions(src_dir: Path, dest_dir: Path, case_ids: list[str]) -> None:
    reset_dir(dest_dir, True)
    for cid in case_ids:
        shutil.copy2(find_prediction(src_dir, cid), dest_dir / f"{cid}.nii.gz")


def majority_vote_case(paths: list[Path], out_path: Path) -> None:
    images = [read_sitk(path) for path in paths]
    arrays = [sitk.GetArrayFromImage(image).astype(np.int16, copy=False) for image in images]
    if any(arr.shape != arrays[0].shape for arr in arrays):
        raise ValueError(f"Cannot vote predictions with different shapes for {out_path.name}")
    if len(arrays) == 1:
        voted = arrays[0].astype(np.uint8, copy=False)
    else:
        stack = np.stack(arrays, axis=0)
        flat = stack.reshape((stack.shape[0], -1))
        out = np.zeros(flat.shape[1], dtype=np.uint8)
        for idx in range(flat.shape[1]):
            out[idx] = Counter(int(v) for v in flat[:, idx]).most_common(1)[0][0]
        voted = out.reshape(arrays[0].shape)
    out_img = sitk.GetImageFromArray(voted)
    out_img.CopyInformation(images[0])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out_img, str(out_path))


def majority_vote_predictions(fold_dirs: list[Path], output_dir: Path, case_ids: list[str]) -> None:
    reset_dir(output_dir, True)
    for cid in case_ids:
        majority_vote_case([find_prediction(folder, cid) for folder in fold_dirs], output_dir / f"{cid}.nii.gz")


def _centered_voxel(mask: np.ndarray, fallback_shape: tuple[int, ...]) -> tuple[int, ...]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return tuple(int(s // 2) for s in fallback_shape)
    center = (np.asarray(fallback_shape, dtype=np.float64) - 1.0) / 2.0
    best = int(np.argmin(np.sum((coords - center) ** 2, axis=1)))
    return tuple(int(v) for v in coords[best])


def ensure_pathology_label(arr: np.ndarray) -> bool:
    if np.any(arr == PATHOLOGY_RAW_LABEL):
        return False
    for candidate_mask in (arr == 200, arr == 500, arr != 0):
        if np.any(candidate_mask):
            arr[_centered_voxel(candidate_mask, arr.shape)] = PATHOLOGY_RAW_LABEL
            return True
    arr[_centered_voxel(np.zeros(arr.shape, dtype=bool), arr.shape)] = PATHOLOGY_RAW_LABEL
    return True


def remap_prediction(pred_path: Path, out_path: Path, mapping: dict[int, int], *, enforce_pathology: bool) -> bool:
    image = read_sitk(pred_path)
    arr = sitk.GetArrayFromImage(image).astype(np.int32, copy=False)
    out = np.zeros_like(arr, dtype=np.uint16)
    for compact, raw in mapping.items():
        out[arr == compact] = raw
    patched = ensure_pathology_label(out) if enforce_pathology else False
    out_image = sitk.GetImageFromArray(out)
    out_image.CopyInformation(image)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(out_image, str(out_path))
    return patched


def build_submission_tree(
    myops_pred_dir: Path,
    cine_pred_dir: Path,
    submission_dir: Path,
    myops_case_ids: list[str],
    cine_case_ids: list[str],
) -> list[str]:
    reset_dir(submission_dir, True)
    patched_cases: list[str] = []
    for cid in myops_case_ids:
        patched = remap_prediction(
            find_prediction(myops_pred_dir, cid),
            submission_dir / "MyoPS" / "Anonymous Center" / cid / f"{cid}_pred.nii.gz",
            MYOPS_COMPACT_TO_RAW,
            enforce_pathology=True,
        )
        if patched:
            patched_cases.append(f"MyoPS/{cid}")
    for cid in cine_case_ids:
        patched = remap_prediction(
            find_prediction(cine_pred_dir, cid),
            submission_dir / "CineMyoPS" / "Anonymous Center" / cid / f"{cid}_pred.nii.gz",
            CINE_COMPACT_TO_RAW,
            enforce_pathology=True,
        )
        if patched:
            patched_cases.append(f"CineMyoPS/{cid}")
    return patched_cases


def zip_submission(submission_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(submission_dir.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(submission_dir))


def _read_zipped_nifti_labels(zf: zipfile.ZipFile, member: str) -> tuple[set[int], Counter]:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / PurePosixPath(member).name
        out_path.write_bytes(zf.read(member))
        arr = sitk.GetArrayFromImage(sitk.ReadImage(str(out_path)))
    values, counts = np.unique(arr, return_counts=True)
    labels = {int(v) for v in values}
    return labels, Counter({int(v): int(c) for v, c in zip(values, counts)})


def validate_submission_zip(zip_path: Path, myops_case_ids: list[str], cine_case_ids: list[str]) -> dict:
    expected_cases = {
        "MyoPS": set(myops_case_ids),
        "CineMyoPS": set(cine_case_ids),
    }
    branch_files: dict[str, dict[str, str]] = {"MyoPS": {}, "CineMyoPS": {}}
    branch_counts: dict[str, Counter] = {"MyoPS": Counter(), "CineMyoPS": Counter()}

    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for name in names:
            parts = PurePosixPath(name).parts
            if PurePosixPath(name).is_absolute() or ".." in parts:
                raise ValueError(f"Unsafe path in submission zip: {name}")
            if not name.endswith("_pred.nii.gz"):
                raise ValueError(f"Unexpected non-prediction file in submission zip: {name}")
            if len(parts) != 4 or parts[0] not in branch_files or parts[1] != "Anonymous Center":
                raise ValueError(f"Unexpected CARE-Myocardium zip layout: {name}")
            branch, _, case_id, filename = parts
            expected_name = f"{case_id}_pred.nii.gz"
            if filename != expected_name:
                raise ValueError(f"Prediction filename does not match case folder for {name}; expected {expected_name}")
            if case_id in branch_files[branch]:
                raise ValueError(f"Duplicate prediction for {branch}/{case_id}")
            labels, counts = _read_zipped_nifti_labels(zf, name)
            extra_labels = labels - SUBMISSION_ALLOWED_LABELS[branch]
            if extra_labels:
                raise ValueError(f"Unexpected labels in {branch}/{case_id}: {sorted(extra_labels)}. Present labels: {sorted(labels)}")
            if not (labels & SUBMISSION_REQUIRED_PATHOLOGY[branch]):
                raise ValueError(
                    f"Missing pathology label in {branch}/{case_id}. "
                    f"Expected at least one of {sorted(SUBMISSION_REQUIRED_PATHOLOGY[branch])}. "
                    f"Present labels: {sorted(labels)}"
                )
            branch_files[branch][case_id] = name
            branch_counts[branch].update(counts)

    required_roots = {"MyoPS/", "CineMyoPS/"}
    roots_present = {name.split("/", 1)[0] + "/" for name in names if "/" in name}
    if not required_roots.issubset(roots_present):
        raise ValueError(f"Submission zip missing roots: {sorted(required_roots - roots_present)}")
    branch_summary = {}
    for branch, expected in expected_cases.items():
        present = set(branch_files[branch])
        missing = sorted(expected - present)
        extra = sorted(present - expected)
        if missing or extra:
            raise ValueError(f"{branch} case mismatch. Missing: {missing}; extra: {extra}")
        branch_summary[branch] = {
            "files": len(branch_files[branch]),
            "cases": len(present),
            "aggregate_labels": {str(k): int(v) for k, v in sorted(branch_counts[branch].items())},
            "missing_pathology_cases": [],
        }
    return {"files": len(names), "roots": sorted(roots_present), "branches": branch_summary}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--myops-val", type=Path, default=REPO_ROOT / "data" / "CARE_Challenge" / "MyoPS_val")
    parser.add_argument("--cine-val", type=Path, default=REPO_ROOT / "data" / "CARE_Challenge" / "CineMyoPS_val")
    parser.add_argument("--output-root", type=Path, default=SUBMISSION_ROOT, help="Root for submission workspaces.")
    parser.add_argument("--upload-root", type=Path, default=None, help="Root for upload-ready timestamped folders.")
    parser.add_argument("--workspace-root", type=Path, default=None, help="Root for intermediate model inputs/preds.")
    parser.add_argument("--run-name", default=None, help="Optional human label added to the timestamped folder name.")
    parser.add_argument("--submission-model", default=None, help="Convenience alias: nnUNet, MyoPS-Net/MyoPS, U-MyoPS, CineMyoPS.")
    parser.add_argument("--myops-model", default=None, help="MyoPS side model: nnUNet, MyoPS-Net, U-MyoPS.")
    parser.add_argument("--cine-model", default=None, help="Cine side model: nnUNet, CineMyoPS.")
    parser.add_argument("--timestamp", default=None, help="Timestamp folder suffix (default: local YYYYMMDD_HHMMSS).")
    parser.add_argument("--team-name", default="OrganAgent")
    parser.add_argument("--folds", nargs="+", default=["0", "1", "2", "3", "4"])
    parser.add_argument("--checkpoint", default="checkpoint_best.pth", help="nnU-Net v2 checkpoint.")
    parser.add_argument("--cine-checkpoint", default="model_best", help="CineMyoPS nnU-Net v1 checkpoint stem.")
    parser.add_argument("--umyops-checkpoint", default="model_final_checkpoint", help="Recorded in manifest for U-MyoPS external preds.")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu", "mps"])
    parser.add_argument("--time-index", type=int, default=-1, help="nnUNet Cine frame index; -1 uses middle frame.")
    parser.add_argument("--cine-num-frames", type=int, default=int(os.environ.get("CINE_NUM_FRAMES", "4")))
    parser.add_argument("--nnunet-predict", type=Path, default=DEFAULT_NNUNET)
    parser.add_argument("--overwrite-inputs", action="store_true")
    parser.add_argument("--skip-predict", action="store_true", help="Reuse existing workspace predictions and rebuild zip.")
    parser.add_argument("--continue-prediction", action="store_true")
    parser.add_argument("--myops-pred-dir", type=Path, default=None, help="Explicit compact-label MyoPS validation predictions.")
    parser.add_argument("--cine-pred-dir", type=Path, default=None, help="Explicit compact-label Cine validation predictions.")
    parser.add_argument("--myops-net-variant", default=os.environ.get("MYOPS_NET_VARIANT", "challenge3"), choices=["full", "challenge3"])
    parser.add_argument("--cine-task", default=os.environ.get("CINE_NNUNET_TASK", "Task026_Cine_4D"))
    parser.add_argument("--cine-trainer", default=os.environ.get("CINE_NNUNET_TRAINER", "CARECineMyoPSTrainer"))
    parser.add_argument("--cine-dim", default=os.environ.get("CINE_NNUNET_DIM", "2d"))
    parser.add_argument("--cine-combine-mode", default=os.environ.get("CINE_COMBINE_MODE", "current"))
    return parser.parse_args()


def resolve_model_combo(args: argparse.Namespace) -> tuple[str, str]:
    myops = canonical_model(args.myops_model) if args.myops_model else None
    cine = canonical_model(args.cine_model) if args.cine_model else None
    if args.submission_model:
        chosen = canonical_model(args.submission_model)
        if chosen in MYOPS_MODELS:
            myops = myops or chosen
            cine = cine or "nnUNet"
        elif chosen in CINE_MODELS:
            cine = cine or chosen
            myops = myops or "nnUNet"
    myops = myops or "nnUNet"
    cine = cine or "nnUNet"
    if myops not in MYOPS_MODELS:
        raise ValueError(f"Unsupported MyoPS model: {myops}")
    if cine not in CINE_MODELS:
        raise ValueError(f"Unsupported Cine model: {cine}")
    return myops, cine


def prepare_myops_predictions(args: argparse.Namespace, model: str, workspace: Path, case_ids: list[str]) -> tuple[Path, dict]:
    pred_final = workspace / "predictions" / "MyoPS" / model / "ensemble"
    if args.myops_pred_dir is not None:
        copy_exact_predictions(args.myops_pred_dir, pred_final, case_ids)
        return pred_final, {"source": "explicit", "pred_dir": str(args.myops_pred_dir)}
    if args.skip_predict and pred_final.is_dir():
        return pred_final, {"source": "workspace-cache", "pred_dir": str(pred_final)}
    if args.skip_predict:
        raise FileNotFoundError(
            f"--skip-predict was set but no cached MyoPS predictions exist at {pred_final}. "
            "Provide --myops-pred-dir or rerun without --skip-predict."
        )
    if model == "nnUNet":
        if not args.nnunet_predict.is_file():
            raise FileNotFoundError(f"nnUNetv2_predict not found: {args.nnunet_predict}")
        input_dir = workspace / "inputs" / "MyoPS" / "nnUNet"
        pred_dir = workspace / "predictions" / "MyoPS" / "nnUNet" / "raw"
        run_nnunet_predict(args.nnunet_predict, "501", input_dir, pred_dir, args.folds, args.checkpoint, args.device, args.continue_prediction)
        copy_exact_predictions(pred_dir, pred_final, case_ids)
        return pred_final, {"source": "nnUNetv2_predict", "folds": args.folds, "checkpoint": args.checkpoint}
    if model == "MyoPS-Net":
        staged = workspace / "inputs" / "MyoPS" / "MyoPS-Net"
        folds = available_myops_net_folds(args.folds)
        if not folds:
            raise FileNotFoundError("No MyoPS-Net checkpoints found under results/checkpoints/MyoPS-Net/fold_*/checkpoints")
        fold_dirs: list[Path] = []
        for fold in folds:
            fold_dir = workspace / "predictions" / "MyoPS" / "MyoPS-Net" / f"fold_{fold}"
            run_myops_net_predict(staged, fold_dir, fold, args.device, args.myops_net_variant)
            fold_dirs.append(fold_dir)
        majority_vote_predictions(fold_dirs, pred_final, case_ids)
        return pred_final, {
            "source": "MyoPS-Net",
            "requested_folds": args.folds,
            "used_folds": folds,
            "policy": "hard-label majority vote; single fold if only one checkpoint exists",
            "variant": args.myops_net_variant,
        }
    if model == "U-MyoPS":
        raise RuntimeError(
            "U-MyoPS submission requires compact-label validation predictions. "
            "Current repo exports U-MyoPS protocol fold predictions only; provide --myops-pred-dir "
            "after running a validation Stage1->Stage2 inference pipeline."
        )
    raise AssertionError(model)


def prepare_cine_predictions(args: argparse.Namespace, model: str, workspace: Path, case_ids: list[str]) -> tuple[Path, dict]:
    pred_final = workspace / "predictions" / "CineMyoPS" / model / "ensemble"
    if args.cine_pred_dir is not None:
        copy_exact_predictions(args.cine_pred_dir, pred_final, case_ids)
        return pred_final, {"source": "explicit", "pred_dir": str(args.cine_pred_dir)}
    if args.skip_predict and pred_final.is_dir():
        return pred_final, {"source": "workspace-cache", "pred_dir": str(pred_final)}
    if args.skip_predict:
        raise FileNotFoundError(
            f"--skip-predict was set but no cached CineMyoPS predictions exist at {pred_final}. "
            "Provide --cine-pred-dir or rerun without --skip-predict."
        )
    if model == "nnUNet":
        if not args.nnunet_predict.is_file():
            raise FileNotFoundError(f"nnUNetv2_predict not found: {args.nnunet_predict}")
        input_dir = workspace / "inputs" / "CineMyoPS" / "nnUNet"
        pred_dir = workspace / "predictions" / "CineMyoPS" / "nnUNet" / "raw"
        run_nnunet_predict(args.nnunet_predict, "502", input_dir, pred_dir, args.folds, args.checkpoint, args.device, args.continue_prediction)
        copy_exact_predictions(pred_dir, pred_final, case_ids)
        return pred_final, {"source": "nnUNetv2_predict", "folds": args.folds, "checkpoint": args.checkpoint}
    if model == "CineMyoPS":
        input_dir = workspace / "inputs" / "CineMyoPS" / "CineMyoPS"
        folds = available_cinemyops_folds(args.folds, args.cine_task, args.cine_trainer, args.cine_dim)
        if not folds:
            raise FileNotFoundError(
                "No CineMyoPS fold folders found under "
                f"data/nnUNet/nnUNet_results/nnUNet/{args.cine_dim}/{args.cine_task}/"
                f"{args.cine_trainer}__nnUNetPlansv2.1"
            )
        fold_dirs: list[Path] = []
        for fold in folds:
            fold_dir = workspace / "predictions" / "CineMyoPS" / "CineMyoPS" / f"fold_{fold}"
            run_cinemyops_predict(
                input_dir,
                fold_dir,
                fold,
                args.cine_task,
                args.cine_trainer,
                args.cine_dim,
                args.cine_checkpoint,
                args.cine_combine_mode,
                args.cine_num_frames,
            )
            fold_dirs.append(fold_dir)
        majority_vote_predictions(fold_dirs, pred_final, case_ids)
        return pred_final, {
            "source": "CineMyoPS",
            "requested_folds": args.folds,
            "used_folds": folds,
            "policy": "hard-label majority vote; single fold if only one checkpoint exists",
            "task": args.cine_task,
            "trainer": args.cine_trainer,
            "dim": args.cine_dim,
            "checkpoint": args.cine_checkpoint,
            "num_frames": args.cine_num_frames,
            "combine_mode": args.cine_combine_mode,
        }
    raise AssertionError(model)


def main() -> None:
    args = parse_args()
    myops_model, cine_model = resolve_model_combo(args)
    timestamp = args.timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    combo_name = f"{myops_model}_MyoPS+{cine_model}_CineMyoPS"
    label = sanitize_name(args.run_name or combo_name)
    submission_id = sanitize_name(f"{label}_{timestamp}")

    output_root = args.output_root
    upload_root = args.upload_root or (output_root / "upload_ready")
    workspace_root = args.workspace_root or (output_root / "workspaces")
    workspace = workspace_root / submission_id
    upload_dir = upload_root / submission_id
    submission_tree = upload_dir / "submission_tree"
    zip_path = upload_dir / f"CARE-Myocardium-{args.team_name}.zip"

    ti = None if args.time_index < 0 else args.time_index
    overwrite_inputs = args.overwrite_inputs or not args.skip_predict

    myops_case_ids = prepare_nnunet_myops_inputs(args.myops_val, workspace / "inputs" / "MyoPS" / "nnUNet", overwrite_inputs)
    cine_case_ids = prepare_nnunet_cine_inputs(args.cine_val, workspace / "inputs" / "CineMyoPS" / "nnUNet", overwrite_inputs, ti)
    if myops_model == "MyoPS-Net":
        staged_ids = prepare_myops_net_inputs(args.myops_val, workspace / "inputs" / "MyoPS" / "MyoPS-Net", overwrite_inputs)
        if staged_ids != myops_case_ids:
            raise RuntimeError("MyoPS-Net staged case ids differ from nnUNet staged case ids")
    if cine_model == "CineMyoPS":
        staged_ids = prepare_cinemyops_inputs(args.cine_val, workspace / "inputs" / "CineMyoPS" / "CineMyoPS", overwrite_inputs, args.cine_num_frames)
        if staged_ids != cine_case_ids:
            raise RuntimeError("CineMyoPS staged case ids differ from nnUNet staged case ids")

    print(f"Submission id: {submission_id}", flush=True)
    print(f"MyoPS model: {myops_model}; CineMyoPS model: {cine_model}", flush=True)
    print(f"Workspace: {workspace}", flush=True)
    print(f"Upload dir: {upload_dir}", flush=True)

    myops_pred, myops_info = prepare_myops_predictions(args, myops_model, workspace, myops_case_ids)
    cine_pred, cine_info = prepare_cine_predictions(args, cine_model, workspace, cine_case_ids)
    patched_cases = build_submission_tree(myops_pred, cine_pred, submission_tree, myops_case_ids, cine_case_ids)
    zip_submission(submission_tree, zip_path)
    zip_check = validate_submission_zip(zip_path, myops_case_ids, cine_case_ids)

    manifest = {
        "created_at_local": datetime.now().isoformat(timespec="seconds"),
        "official_format": "https://zmic.org.cn/care_2026/valid_submission/",
        "team_name": args.team_name,
        "submission_id": submission_id,
        "combo": {"myops_model": myops_model, "cine_model": cine_model},
        "timestamp": timestamp,
        "workspace": str(workspace),
        "upload_dir": str(upload_dir),
        "zip": str(zip_path),
        "zip_name_policy": "official upload zip name intentionally has no timestamp; timestamp is on parent folder",
        "myops_cases": len(myops_case_ids),
        "cine_cases": len(cine_case_ids),
        "myops": myops_info,
        "cine": cine_info,
        "pathology_label_fallback": {
            "raw_label": PATHOLOGY_RAW_LABEL,
            "cases": patched_cases,
        },
        "zip_check": zip_check,
    }
    write_json(upload_dir / "manifest.json", manifest)
    print(f"Submission zip -> {zip_path}", flush=True)
    print(f"Manifest -> {upload_dir / 'manifest.json'}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
