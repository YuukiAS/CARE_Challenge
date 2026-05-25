"""Lane A Round17 MedNeXt / stronger-backbone nnU-Net trainer."""

from __future__ import annotations

import os

import torch
from torch import nn

from nnunetv2.paths import nnUNet_results
from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import nnUNetTrainer_500epochs

from src.care_myocardium.mednext import MedNeXtConfig, create_care_mednext


class nnUNetTrainerLaneAMedNeXtShort(nnUNetTrainer_500epochs):
    """Bounded fold0 MedNeXt trainer preserving Dataset501 semantics.

    The trainer keeps nnU-Net's Dataset501 dataloading, standard multiclass
    loss, validation export, label mapping, and evaluator compatibility. Only
    the network architecture is replaced with the locally audited MedNeXt v1
    source code. No pretrained weights are loaded here.
    """

    @staticmethod
    def build_network_architecture(
        plans_manager,
        configuration_manager,
        num_input_channels: int,
        num_output_channels: int,
        enable_deep_supervision: bool = True,
    ) -> nn.Module:
        model_id = os.environ.get("LANEA_ROUND17_MEDNEXT_MODEL_ID", "S")
        kernel_size = int(os.environ.get("LANEA_ROUND17_MEDNEXT_KERNEL_SIZE", "3"))
        deep_supervision = os.environ.get("LANEA_ROUND17_DEEP_SUPERVISION", "0").lower() in {"1", "true", "yes"}
        return create_care_mednext(
            MedNeXtConfig(
                model_id=model_id,
                num_input_channels=num_input_channels,
                num_classes=num_output_channels,
                kernel_size=kernel_size,
                deep_supervision=deep_supervision and enable_deep_supervision,
            )
        )

    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict, device: torch.device = torch.device("cuda")):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("LANEA_ROUND17_EPOCHS", "3"))
        self.num_iterations_per_epoch = int(os.environ.get("LANEA_ROUND17_ITERS_PER_EPOCH", "5"))
        self.num_val_iterations_per_epoch = int(os.environ.get("LANEA_ROUND17_VAL_ITERS_PER_EPOCH", "2"))
        self.initial_lr = float(os.environ.get("LANEA_ROUND17_INITIAL_LR", "0.0001"))
        self.save_every = max(1, min(self.save_every, self.num_epochs))
        if nnUNet_results is not None:
            experiment = os.environ.get(
                "LANEA_ROUND17_EXPERIMENT_NAME",
                "laneA_r17_mednext_s_kernel3_fold0_very_short",
            )
            self.output_folder_base = os.path.join(
                nnUNet_results,
                self.plans_manager.dataset_name,
                experiment + "__" + self.plans_manager.plans_name + "__" + configuration,
            )
            self.output_folder = os.path.join(self.output_folder_base, f"fold_{fold}")
