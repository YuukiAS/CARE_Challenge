#!/usr/bin/env python3
"""Run bounded Lane A Round9 checkpoint-initialized nnU-Net training."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from batchgenerators.utilities.file_and_folder_operations import load_json
from nnunetv2.utilities.dataset_name_id_conversion import maybe_convert_to_dataset_name

from src.care_myocardium.nnunet.laneA_round9_trainer import nnUNetTrainerLaneABaselineInitializedEdemaAdapt


DEFAULT_CKPT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    / "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Lane A Round9 bounded nnU-Net trainer")
    parser.add_argument("--dataset", type=int, default=501)
    parser.add_argument("--configuration", default="3d_fullres")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--run-validation-export", action="store_true")
    parser.add_argument("--init-checkpoint", default=str(DEFAULT_CKPT))
    args = parser.parse_args()

    os.environ.setdefault("LANEA_ROUND9_INIT_CHECKPOINT", args.init_checkpoint)
    dataset_name = maybe_convert_to_dataset_name(args.dataset)
    preprocessed = Path(os.environ["nnUNet_preprocessed"]) / dataset_name
    plans = load_json(str(preprocessed / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(preprocessed / "dataset.json"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    trainer = nnUNetTrainerLaneABaselineInitializedEdemaAdapt(plans, args.configuration, args.fold, dataset_json, device)
    trainer.initialize()
    trainer.run_training()
    if args.run_validation_export:
        trainer.perform_actual_validation(save_probabilities=False)


if __name__ == "__main__":
    main()
