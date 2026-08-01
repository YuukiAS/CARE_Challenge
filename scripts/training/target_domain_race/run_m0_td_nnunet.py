#!/usr/bin/env python3
"""Run M0 TD-NNUNET formal training for one fold."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


TASK_KEY = "20260801_care_target_domain_pathology_specialist_race"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY / "m0_td_nnunet"
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY / "m0_td_nnunet"
STOCK_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_csv(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()), lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=[2, 3])
    parser.add_argument("--configuration", default="3d_fullres")
    args = parser.parse_args()

    os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
    os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
    os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
    os.environ["nnUNet_results"] = str(RUNTIME_ROOT / "nnUNet_results")
    os.environ.setdefault("MPLCONFIGDIR", str(RUNTIME_ROOT / "mpl_cache"))
    Path(os.environ["nnUNet_results"]).mkdir(parents=True, exist_ok=True)
    Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

    from batchgenerators.utilities.file_and_folder_operations import load_json
    from nnunetv2.run.run_training import maybe_load_checkpoint
    from nnunetv2.utilities.dataset_name_id_conversion import maybe_convert_to_dataset_name
    from src.care_myocardium.nnunet.target_domain_race_trainer import nnUNetTrainerTargetDomainRace4000

    dataset_name = maybe_convert_to_dataset_name(501)
    preprocessed_base = Path(os.environ["nnUNet_preprocessed"]) / dataset_name
    plans = load_json(str(preprocessed_base / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(preprocessed_base / "dataset.json"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    trainer = nnUNetTrainerTargetDomainRace4000(plans, args.configuration, args.fold, dataset_json, device)
    pretrained = STOCK_ROOT / f"fold_{args.fold}" / "checkpoint_final.pth"
    start = now_utc()
    append_csv(
        RESULT_ROOT / "training_accounting.csv",
        {
            "fold": args.fold,
            "event": "start",
            "timestamp": start,
            "target_optimizer_steps": 4000,
            "num_epochs": 16,
            "num_iterations_per_epoch": 250,
            "pretrained_checkpoint": str(pretrained),
            "device": str(device),
            "formal_credit": "pending",
        },
    )
    maybe_load_checkpoint(trainer, continue_training=False, validation_only=False, pretrained_weights_file=str(pretrained))
    trainer.run_training()
    checkpoint_final = Path(trainer.output_folder) / "checkpoint_final.pth"
    checkpoint_best = Path(trainer.output_folder) / "checkpoint_best.pth"
    receipt = {
        "created_at": now_utc(),
        "lane_id": "M0_TD_NNUNET",
        "fold": args.fold,
        "status": "TRAINING_COMPLETE",
        "formal_training_credit": True,
        "optimizer_steps": 4000,
        "num_epochs": 16,
        "num_iterations_per_epoch": 250,
        "output_folder": str(trainer.output_folder),
        "checkpoint_final": str(checkpoint_final),
        "checkpoint_final_exists": checkpoint_final.exists(),
        "checkpoint_best": str(checkpoint_best),
        "checkpoint_best_exists": checkpoint_best.exists(),
        "pretrained_checkpoint": str(pretrained),
    }
    write_json(RESULT_ROOT / f"fold{args.fold}_training_receipt.json", receipt)
    append_csv(
        RESULT_ROOT / "training_accounting.csv",
        {
            "fold": args.fold,
            "event": "complete",
            "timestamp": receipt["created_at"],
            "target_optimizer_steps": 4000,
            "num_epochs": 16,
            "num_iterations_per_epoch": 250,
            "pretrained_checkpoint": str(pretrained),
            "device": str(device),
            "formal_credit": "true",
        },
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
