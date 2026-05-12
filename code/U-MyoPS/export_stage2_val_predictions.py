#!/usr/bin/env python3
"""Export U-MyoPS Stage2 validation predictions to CARE compact labels for unified evaluation.

CARE2026 / unified offline alignment (MyoPS pathology only):
  - nnU-Net Task901 foreground label 1 (\"edema\") -> CARE voxel id 4 -> leaderboard **myops_edema**
  - nnU-Net Task901 foreground label 2 (\"scar\")  -> CARE voxel id 5 -> leaderboard **myops_scar**

These must match ``build_stage2_task_from_stage1.write_dataset_json`` and ``compact_pathology_label``.
Inference must use the same ``--whichsubnet`` as training (default ``scar``; override via
``UMYOPS_STAGE2_WHICH_SUBNET`` or CLI ``--which-subnet``).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import SimpleITK as sitk
import numpy as np


def _configure_logging() -> None:
    """Match U-MyoPS Stage1 style: `YYYY-mm-dd HH:MM:SS INFO: message`."""
    root = logging.getLogger()
    if root.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s INFO: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_stage2_task_name(base_task: str, fold: int, per_fold: bool) -> str:
    return f"{base_task}_fold{fold}" if per_fold else base_task


def val_case_ids(protocol_json: Path, fold: int) -> list[str]:
    with protocol_json.open(encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data["folds"][fold]["val"])


def find_prediction(src_dir: Path, case_id: str) -> Path:
    exact = src_dir / f"{case_id}.nii.gz"
    if exact.is_file():
        return exact
    matches = sorted(src_dir.glob(f"*{case_id}*.nii.gz"))
    if len(matches) == 1:
        return matches[0]
    raise FileNotFoundError(f"Could not uniquely resolve prediction for {case_id} in {src_dir}")


def remap_to_care(pred_img: sitk.Image) -> sitk.Image:
    """Map nnU-Net argmax labels {0,1,2} to CARE Dataset501 compact {0,4,5}."""
    arr = sitk.GetArrayFromImage(pred_img)
    u = np.unique(arr)
    bad = u[(u != 0) & (u != 1) & (u != 2)]
    if bad.size:
        logging.warning(
            "[U-MyoPS export] unexpected nnUNet label ids in prediction (expected 0,1,2): %s",
            bad.tolist(),
        )
    out = np.zeros(arr.shape, dtype=np.uint8)
    out[arr == 1] = 4
    out[arr == 2] = 5
    img = sitk.GetImageFromArray(out)
    img.CopyInformation(pred_img)
    return img


def resolve_stage2_python() -> Path:
    repo = repo_root()
    env_path = (
        os.environ.get("UMYOPS_STAGE2_PYTHON")
        or os.environ.get("LEGACY_PYTHON")
        or (
            str(Path(os.environ["CARE_CineMyoPS_ENV"]) / "bin" / "python")
            if os.environ.get("CARE_CineMyoPS_ENV")
            else None
        )
        or (
            str(Path(os.environ["CARE_CINEMYOPS_ENV"]) / "bin" / "python")
            if os.environ.get("CARE_CINEMYOPS_ENV")
            else None
        )
        or str(repo / "env_CARE_nnUNet_v1" / "bin" / "python")
    )
    py = Path(env_path)
    if not py.is_file():
        raise FileNotFoundError(
            f"Could not resolve Stage2 inference python. Checked: {py}. "
            "Set UMYOPS_STAGE2_PYTHON or LEGACY_PYTHON if needed."
        )
    return py


def fallback_tmp_validation_raw_dir(fold: int) -> Path:
    """Where ``build_fallback_predictions`` writes nnU-Net argmax outputs before CARE remap."""
    return repo_root() / "results" / "predictions" / "_tmp" / "U-MyoPS" / f"fold_{fold}" / "validation_raw"


def tmp_validation_raw_complete(tmp_raw: Path, case_ids: list[str]) -> bool:
    if not tmp_raw.is_dir():
        return False
    return all((tmp_raw / f"{cid}.nii.gz").is_file() for cid in case_ids)


def build_fallback_predictions(
    src_dir: Path,
    task_name: str,
    case_ids: list[str],
    trainer: str,
    dim: str,
    fold: int,
    which_subnet: str = "scar",
) -> Path:
    repo = repo_root()
    umyo_repo = repo / "third_party" / "U-MyoPS_myops"
    raw_task_dir = repo / "third_party" / "U-MyoPS_myops" / "outputs" / "nnunet" / "raw" / "nnUNet_raw_data" / task_name
    images_dir = raw_task_dir / "imagesTr"
    if not images_dir.is_dir():
        raise FileNotFoundError(f"Missing Stage2 raw images directory: {images_dir}")

    pred_dir = fallback_tmp_validation_raw_dir(fold)
    tmp_root = pred_dir.parent
    input_dir = tmp_root / "input"
    shutil.rmtree(input_dir, ignore_errors=True)
    input_dir.mkdir(parents=True, exist_ok=True)
    pred_dir.mkdir(parents=True, exist_ok=True)

    for case_id in case_ids:
        for mod_idx in range(4):
            src_file = images_dir / f"{case_id}_{mod_idx:04d}.nii.gz"
            if not src_file.exists():
                raise FileNotFoundError(f"Missing Stage2 modality file for {case_id}: {src_file}")
            dst_file = input_dir / src_file.name
            dst_file.symlink_to(src_file.resolve())

    py = resolve_stage2_python()
    env = os.environ.copy()
    env["nnUNet_raw_data_base"] = env.get("nnUNet_raw_data_base", str(umyo_repo / "outputs" / "nnunet" / "raw"))
    env["nnUNet_preprocessed"] = env.get("nnUNet_preprocessed", str(umyo_repo / "outputs" / "nnunet" / "prepro"))
    env["RESULTS_FOLDER"] = env.get("RESULTS_FOLDER", str(umyo_repo / "outputs" / "nnunet" / "output"))
    env["PYTHONPATH"] = f"{umyo_repo / 'jrs'}:{umyo_repo}:{env.get('PYTHONPATH', '')}".rstrip(":")
    env["PYTHONUNBUFFERED"] = "1"

    cmd = [
        str(py),
        str(umyo_repo / "jrs" / "pathology_segmentation_test.py"),
        "-i",
        str(input_dir),
        "-o",
        str(pred_dir),
        "-t",
        task_name,
        "-m",
        dim,
        "-tr",
        trainer,
        "-f",
        str(fold),
        "--chk",
        "model_final_checkpoint",
        "--disable_tta",
        "--overwrite_existing",
        "--num_threads_preprocessing",
        "2",
        "--num_threads_nifti_save",
        "2",
        "--whichsubnet",
        which_subnet,
    ]
    verbose = os.environ.get("UMYOPS_EXPORT_VERBOSE_INFERENCE", "").strip() in (
        "1",
        "true",
        "True",
        "yes",
    )
    logging.info(
        "[U-MyoPS export] fallback nnUNet inference: task=%s fold=%d val_cases=%d whichsubnet=%s -> %s",
        task_name,
        fold,
        len(case_ids),
        which_subnet,
        pred_dir,
    )
    if verbose:
        logging.info("[U-MyoPS export] UMYOPS_EXPORT_VERBOSE_INFERENCE=1: streaming nnUNet stdout/stderr")
        subprocess.run(cmd, check=True, env=env, cwd=umyo_repo / "jrs")
    else:
        proc = subprocess.run(
            cmd,
            check=False,
            env=env,
            cwd=umyo_repo / "jrs",
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            tail_out = (proc.stdout or "")[-12000:]
            tail_err = (proc.stderr or "")[-12000:]
            logging.error("[U-MyoPS export] pathology_segmentation_test failed (exit %s)", proc.returncode)
            if tail_err.strip():
                logging.error("[U-MyoPS export] stderr (tail):\n%s", tail_err)
            if tail_out.strip():
                logging.error("[U-MyoPS export] stdout (tail):\n%s", tail_out)
            raise subprocess.CalledProcessError(proc.returncode, cmd, proc.stdout, proc.stderr)
        logging.info("[U-MyoPS export] nnUNet inference finished ok")
    return pred_dir


def main() -> None:
    _configure_logging()
    ap = argparse.ArgumentParser(description="Export U-MyoPS Stage2 validation predictions for unified evaluation")
    ap.add_argument("--fold", type=int, required=True)
    ap.add_argument("--base-task-name", type=str, default="Task901_CARE_UmyopsPathology")
    ap.add_argument("--per-fold-task", action="store_true", default=False)
    ap.add_argument("--trainer", type=str, default="nnUNetTrainerPSNV8")
    ap.add_argument("--dim", type=str, default="2d")
    ap.add_argument("--protocol-json", type=Path, default=repo_root() / "data" / "benchmarks" / "protocol" / "splits_MyoPS.json")
    ap.add_argument("--results-root", type=Path, default=repo_root() / "third_party" / "U-MyoPS_myops" / "outputs" / "nnunet" / "output" / "nnUNet")
    ap.add_argument("--output-dir", type=Path, default=None)
    ap.add_argument(
        "--which-subnet",
        type=str,
        default=None,
        help="PSNV8 subnet tag for pathology inference (default: env UMYOPS_STAGE2_WHICH_SUBNET or 'scar'). "
        "Must match training.",
    )
    args = ap.parse_args()

    task_name = resolve_stage2_task_name(args.base_task_name, args.fold, args.per_fold_task)
    case_ids = val_case_ids(args.protocol_json, args.fold)
    which_subnet = (args.which_subnet or os.environ.get("UMYOPS_STAGE2_WHICH_SUBNET") or "scar").strip()
    logging.info("[U-MyoPS export] whichsubnet=%s (must match Stage2 training)", which_subnet)
    src_dir = args.results_root / args.dim / task_name / f"{args.trainer}__nnUNetPlansv2.1" / f"fold_{args.fold}" / "validation_raw"
    if not src_dir.is_dir():
        tmp_raw = fallback_tmp_validation_raw_dir(args.fold)
        if tmp_validation_raw_complete(tmp_raw, case_ids):
            logging.warning(
                "validation_raw missing under results tree for fold %s; reusing complete cached raw preds -> %s "
                "(delete this dir to force re-inference)",
                args.fold,
                tmp_raw,
            )
            src_dir = tmp_raw
        else:
            logging.warning(
                "validation_raw missing for fold %s; running fallback nnUNet inference -> %s",
                args.fold,
                src_dir.parent,
            )
            src_dir = build_fallback_predictions(
                src_dir=src_dir,
                task_name=task_name,
                case_ids=case_ids,
                trainer=args.trainer,
                dim=args.dim,
                fold=args.fold,
                which_subnet=which_subnet,
            )

    out_dir = args.output_dir or repo_root() / "results" / "predictions" / "U-MyoPS" / f"fold_{args.fold}"
    out_dir.mkdir(parents=True, exist_ok=True)

    logging.info(
        "===== U-MyoPS Stage2 export: remap %d val predictions -> %s =====",
        len(case_ids),
        out_dir,
    )
    n = len(case_ids)
    for i, case_id in enumerate(case_ids):
        pred_path = find_prediction(src_dir, case_id)
        pred_img = sitk.ReadImage(str(pred_path))
        sitk.WriteImage(remap_to_care(pred_img), str(out_dir / f"{case_id}.nii.gz"))
        if (i + 1) % 10 == 0 or (i + 1) == n:
            logging.info("[U-MyoPS export] wrote %d/%d cases", i + 1, n)
    logging.info("[U-MyoPS export] done | %d NIfTI -> %s", n, out_dir)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI wrapper
        logging.error("export_stage2_val_predictions: %s", exc)
        sys.exit(1)
