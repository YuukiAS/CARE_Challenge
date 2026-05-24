#!/usr/bin/env python3
"""Run Lane A Round4 bounded fold0 nnU-Net short train.

This script instantiates the local first-party trainer directly so we do not
need to copy custom trainer files into the nnU-Net package. It trains only the
requested fold/configuration and then runs nnU-Net validation for that fold.
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
    parser = argparse.ArgumentParser(description="Lane A Round4 bounded fold0 short train")
    parser.add_argument("--dataset", default="501")
    parser.add_argument("--configuration", default="3d_fullres")
    parser.add_argument("--fold", default="0")
    parser.add_argument("--pretrained-weights", type=Path, required=True)
    parser.add_argument("--export-validation-probabilities", action="store_true")
    args = parser.parse_args()

    os.environ.setdefault("CARE_ROOT", str(REPO_ROOT))
    os.environ.setdefault("nnUNet_raw", str(REPO_ROOT / "data/nnUNet/nnUNet_raw"))
    os.environ.setdefault("nnUNet_preprocessed", str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed"))
    os.environ.setdefault("nnUNet_results", str(REPO_ROOT / "data/nnUNet/nnUNet_results"))
    os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / "results/diagnostics/phase0_phase1/laneA_myops/round4_fold0_short_train/mpl_cache"))

    from batchgenerators.utilities.file_and_folder_operations import load_json
    from nnunetv2.utilities.dataset_name_id_conversion import maybe_convert_to_dataset_name
    from nnunetv2.run.run_training import maybe_load_checkpoint
    from src.care_myocardium.nnunet.laneA_round4_trainer import nnUNetTrainerLaneAEdemaFocalTverskyT2DownShort

    dataset_name = maybe_convert_to_dataset_name(int(args.dataset) if args.dataset.isdigit() else args.dataset)
    preprocessed_base = Path(os.environ["nnUNet_preprocessed"]) / dataset_name
    plans = load_json(str(preprocessed_base / "nnUNetPlans.json"))
    plans["continue_training"] = False
    dataset_json = load_json(str(preprocessed_base / "dataset.json"))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    trainer = nnUNetTrainerLaneAEdemaFocalTverskyT2DownShort(
        plans=plans,
        configuration=args.configuration,
        fold=int(args.fold),
        dataset_json=dataset_json,
        device=device,
    )
    maybe_load_checkpoint(trainer, continue_training=False, validation_only=False, pretrained_weights_file=str(args.pretrained_weights))
    trainer.run_training()
    trainer.perform_actual_validation(args.export_validation_probabilities)


if __name__ == "__main__":
    main()
