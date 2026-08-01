"""nnU-Net trainer variants for the 20260801 target-domain gap closure."""

from __future__ import annotations

import json
from pathlib import Path

import torch
from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import nnUNetTrainer_500epochs


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = REPO_ROOT / "results/20260801_care_target_domain_race_gap_closure"


class nnUNetTrainerGapClosureM0R4000(nnUNetTrainer_500epochs):
    """Faithful target-domain control for M0R.

    This intentionally breaks from the old M0 negative run: no SGD, no PolyLR,
    and checkpoints remain aligned to every 500 optimizer steps.
    """

    def __init__(
        self,
        plans: dict,
        configuration: str,
        fold: int,
        dataset_json: dict,
        device: torch.device = torch.device("cuda"),
    ) -> None:
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_iterations_per_epoch = 250
        self.num_val_iterations_per_epoch = 50
        self.num_epochs = 16
        self.save_every = 2
        self.initial_lr = 1.0e-4
        self.weight_decay = 1.0e-4

    def configure_optimizers(self):
        backbone_params = []
        head_params = []
        for name, param in self.network.named_parameters():
            if not param.requires_grad:
                continue
            if "seg_layers" in name or name.endswith(".seg_output.weight") or name.endswith(".seg_output.bias"):
                head_params.append(param)
            else:
                backbone_params.append(param)

        groups = []
        if backbone_params:
            groups.append({"params": backbone_params, "lr": 1.0e-4, "name": "backbone_decoder"})
        if head_params:
            groups.append({"params": head_params, "lr": 5.0e-4, "name": "segmentation_heads"})
        if not groups:
            groups.append({"params": self.network.parameters(), "lr": 1.0e-4, "name": "all_trainable"})
        optimizer = torch.optim.AdamW(groups, weight_decay=self.weight_decay)
        scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, lr_lambda=lambda _epoch: 1.0)
        return optimizer, scheduler

    def do_split(self):
        split = json.loads((RESULT_ROOT / "split_receipt_copy.json").read_text(encoding="utf-8"))
        key = f"fold{int(self.fold)}"
        if key not in split:
            raise RuntimeError(f"gap closure split receipt does not contain {key}")
        tr_keys = list(split[key]["actual_train_cases"])
        val_keys = list(split[key]["inner_selection_cases"])
        self.print_to_log_file(
            f"Using gap-closure complete-trimodal split for {key}: "
            f"{len(tr_keys)} actual-train, {len(val_keys)} inner-selection"
        )
        return tr_keys, val_keys
