#!/usr/bin/env python3
"""Run Lane A Round7 bounded nnU-Net train.

This entrypoint intentionally isolates Round7 outputs from the Dataset501
baseline cache. Validation export is disabled by default because Round7 first
needs wiring/tiny/fold0 gates before a submission-style inference path.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Lane A Round7 bounded fold0 train")
    parser.add_argument("--dataset", default="501")
    parser.add_argument("--configuration", default="3d_fullres")
    parser.add_argument("--fold", default="0")
    parser.add_argument("--run-validation-export", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
    os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
    os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
    os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
    os.environ.setdefault(
        "MPLCONFIGDIR",
        str(REPO_ROOT / "results/diagnostics/care_myocardium/laneA_myops/round07_modality_uncertainty/mpl_cache"),
    )

    from batchgenerators.utilities.file_and_folder_operations import load_json
    from nnunetv2.utilities.dataset_name_id_conversion import maybe_convert_to_dataset_name
    from src.care_myocardium.nnunet.laneA_round7_trainer import nnUNetTrainerLaneAModPresenceUncertaintyShort

    dataset_name = maybe_convert_to_dataset_name(int(args.dataset) if args.dataset.isdigit() else args.dataset)
    preprocessed_base = Path(os.environ["nnUNet_preprocessed"]) / dataset_name
    plans = load_json(str(preprocessed_base / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(preprocessed_base / "dataset.json"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    trainer = nnUNetTrainerLaneAModPresenceUncertaintyShort(
        plans=plans,
        configuration=args.configuration,
        fold=int(args.fold),
        dataset_json=dataset_json,
        device=device,
    )
    trainer.run_training()
    if args.run_validation_export:
        trainer.perform_actual_validation(save_probabilities=False)


if __name__ == "__main__":
    main()
