#!/usr/bin/env python3
"""Run M0 TD-NNUNET outer prediction/evaluation for fold2 and fold3."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TASK_KEY = "20260801_care_target_domain_pathology_specialist_race"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
M0_RESULT_ROOT = RESULT_ROOT / "m0_td_nnunet"
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY / "m0_td_nnunet"
MODEL_FOLDER = (
    RUNTIME_ROOT
    / "nnUNet_results"
    / "Dataset501_CAREMyoPS"
    / "nnUNetTrainerTargetDomainRace4000__nnUNetPlans__3d_fullres"
)
RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_outer_cases(fold: int) -> list[str]:
    path = RESULT_ROOT / f"fold{fold}_case_manifest.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return sorted(r["case_id"] for r in rows if r.get("race_role") == "outer")


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def predict_fold(fold: int, checkpoint_name: str, overwrite: bool) -> Path:
    checkpoint = MODEL_FOLDER / f"fold_{fold}" / checkpoint_name
    if not checkpoint.exists():
        raise FileNotFoundError(f"checkpoint missing: {checkpoint}")
    cases = read_outer_cases(fold)
    inputs = []
    for case_id in cases:
        paths = [RAW_ROOT / "imagesTr" / f"{case_id}_{channel:04d}.nii.gz" for channel in range(3)]
        missing = [str(p) for p in paths if not p.exists()]
        if missing:
            raise FileNotFoundError(f"raw images missing for {case_id}: {missing}")
        inputs.append([str(p) for p in paths])

    os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
    os.environ["nnUNet_raw"] = str(REPO_ROOT / "data/nnUNet/nnUNet_raw")
    os.environ["nnUNet_preprocessed"] = str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed")
    os.environ["nnUNet_results"] = str(RUNTIME_ROOT / "nnUNet_results")
    os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_ROOT / "mpl_cache"))

    import nnunetv2.inference.predict_from_raw_data as predict_from_raw_data
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
    from src.care_myocardium.nnunet.target_domain_race_trainer import nnUNetTrainerTargetDomainRace4000

    original_class_finder = predict_from_raw_data.recursive_find_python_class

    def class_finder(folder, trainer_name, current_module):
        if trainer_name == "nnUNetTrainerTargetDomainRace4000":
            return nnUNetTrainerTargetDomainRace4000
        return original_class_finder(folder, trainer_name, current_module)

    predict_from_raw_data.recursive_find_python_class = class_finder

    out_dir = RUNTIME_ROOT / "outer_predictions" / f"fold_{fold}" / checkpoint_name.replace(".pth", "")
    out_dir.mkdir(parents=True, exist_ok=True)
    output_files = [str(out_dir / case_id) for case_id in cases]
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=False,
        perform_everything_on_device=True,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=True,
    )
    predictor.initialize_from_trained_model_folder(str(MODEL_FOLDER), use_folds=(fold,), checkpoint_name=checkpoint_name)
    predictor.predict_from_files(
        inputs,
        output_files,
        save_probabilities=False,
        overwrite=overwrite,
        num_processes_preprocessing=4,
        num_processes_segmentation_export=4,
    )
    manifest = {
        "created_at": now_utc(),
        "lane_id": "M0_TD_NNUNET",
        "fold": fold,
        "checkpoint_name": checkpoint_name,
        "checkpoint_path": str(checkpoint),
        "case_count": len(cases),
        "cases": cases,
        "prediction_dir": str(out_dir),
        "prediction_files_present": sum((out_dir / f"{case_id}.nii.gz").exists() for case_id in cases),
    }
    write_json(M0_RESULT_ROOT / f"fold{fold}_outer_prediction_manifest.json", manifest)
    return out_dir


def evaluate_fold(fold: int, pred_dir: Path, checkpoint_name: str) -> Path:
    cases = ",".join(read_outer_cases(fold))
    out_dir = M0_RESULT_ROOT / f"fold{fold}_outer_eval_{checkpoint_name.replace('.pth', '')}"
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts/evaluation/evaluate_predictions.py"),
        "--pred-dir",
        str(pred_dir),
        "--gt-dir",
        str(RAW_ROOT / "labelsTr"),
        "--cases",
        cases,
        "--foreground-classes",
        "1,2,3,4,5",
        "--skip-dice-if-gt-empty",
        "--hd95",
        "--output-dir",
        str(out_dir),
    ]
    subprocess.run(cmd, check=True, cwd=str(REPO_ROOT))
    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, action="append", choices=[2, 3], required=True)
    parser.add_argument("--checkpoint-name", default="checkpoint_best.pth")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    rows = []
    for fold in args.fold:
        pred_dir = predict_fold(fold, args.checkpoint_name, overwrite=args.overwrite)
        eval_dir = evaluate_fold(fold, pred_dir, args.checkpoint_name)
        summary_path = eval_dir / "evaluation_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "fold": fold,
                "checkpoint_name": args.checkpoint_name,
                "prediction_dir": str(pred_dir),
                "eval_dir": str(eval_dir),
                "summary_path": str(summary_path),
                "mean_dice": summary.get("mean_dice"),
                "class4_edema_dice": (summary.get("mean_per_class") or {}).get("4"),
                "class5_scar_dice": (summary.get("mean_per_class") or {}).get("5"),
            }
        )
    write_json(
        M0_RESULT_ROOT / f"outer_eval_summary_{args.checkpoint_name.replace('.pth', '')}.json",
        {"created_at": now_utc(), "lane_id": "M0_TD_NNUNET", "rows": rows},
    )
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
