"""Lane A Round9 baseline-initialized nnU-Net trainer components."""

from __future__ import annotations

import os

import torch
from nnunetv2.paths import nnUNet_results

from src.care_myocardium.nnunet.laneA_round8_trainer import SeparatedEdemaLoss, nnUNetTrainerLaneAT2EdemaExpertShort
from src.care_myocardium.nnunet.laneA_round9_checkpoint_loader import load_adapted_checkpoint


class PaddingSafeSeparatedEdemaLoss(SeparatedEdemaLoss):
    """Round9 separated edema loss with diagnostic/training padding safety."""

    def forward(self, output, target):  # type: ignore[override]
        logits = output[0] if isinstance(output, (list, tuple)) else output
        labels = target[0] if isinstance(target, (list, tuple)) else target
        if labels.ndim == logits.ndim:
            labels = labels[:, 0]
        labels = labels.long()
        if bool((labels < 0).any()):
            labels = labels.clone()
            labels[labels < 0] = 0
        return super().forward(logits, labels)


class nnUNetTrainerLaneABaselineInitializedEdemaAdapt(nnUNetTrainerLaneAT2EdemaExpertShort):
    """Round9 checkpoint-initialized 6-channel edema adaptation trainer."""

    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict, device: torch.device = torch.device("cuda")):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("LANEA_ROUND9_EPOCHS", "3"))
        self.num_iterations_per_epoch = int(os.environ.get("LANEA_ROUND9_ITERS_PER_EPOCH", "5"))
        self.num_val_iterations_per_epoch = int(os.environ.get("LANEA_ROUND9_VAL_ITERS_PER_EPOCH", "2"))
        self.initial_lr = float(os.environ.get("LANEA_ROUND9_INITIAL_LR", "0.00001"))
        self.save_every = max(1, min(self.save_every, self.num_epochs))
        if nnUNet_results is not None:
            experiment = os.environ.get(
                "LANEA_ROUND9_EXPERIMENT_NAME",
                "laneA_r9_ckptinit_6ch_edema_adapt_fold0_very_short",
            )
            self.output_folder_base = os.path.join(
                nnUNet_results,
                self.plans_manager.dataset_name,
                experiment + "__" + self.plans_manager.plans_name + "__" + configuration,
            )
            self.output_folder = os.path.join(self.output_folder_base, f"fold_{fold}")

    def _build_loss(self):
        return PaddingSafeSeparatedEdemaLoss(
            full_ce_weight=float(os.environ.get("LANEA_ROUND9_FULL_CE_WEIGHT", "1.0")),
            dice_weight=float(os.environ.get("LANEA_ROUND9_DICE_WEIGHT", "1.0")),
            edema_expert_weight=float(os.environ.get("LANEA_ROUND9_EDEMA_EXPERT_WEIGHT", "1.0")),
            edema_positive_weight_cap=float(os.environ.get("LANEA_ROUND9_EDEMA_POSITIVE_WEIGHT_CAP", "50.0")),
            no_t2_confidence_weight=float(os.environ.get("LANEA_ROUND9_NO_T2_CONFIDENCE_WEIGHT", "0.0")),
            no_t2_confidence_threshold=float(os.environ.get("LANEA_ROUND9_NO_T2_CONFIDENCE_THRESHOLD", "0.5")),
            t2_absent_logit_bias=float(os.environ.get("LANEA_ROUND9_T2_ABSENT_LOGIT_BIAS", "0.0")),
        )

    def initialize(self):
        super().initialize()
        checkpoint = os.environ.get("LANEA_ROUND9_INIT_CHECKPOINT")
        if checkpoint:
            target_network = getattr(self.network, "_orig_mod", self.network)
            report = load_adapted_checkpoint(
                target_network,
                checkpoint,
                modality_init=float(os.environ.get("LANEA_ROUND9_MODALITY_CHANNEL_INIT", "0.0")),
            )
            loaded = sum(1 for row in report if row["status"] in {"loaded", "expanded_first_conv"})
            expanded = [row for row in report if row["status"] == "expanded_first_conv"]
            self.print_to_log_file(
                f"LaneA Round9 loaded checkpoint {checkpoint}; loaded_or_expanded={loaded}; "
                f"expanded_input_keys={[row['key'] for row in expanded]}"
            )
        return self
