"""nnU-Net trainer variants for the 20260801 target-domain gap closure."""

from __future__ import annotations

import json
import math
from pathlib import Path

import torch
from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import nnUNetTrainer_500epochs


REPO_ROOT = Path(__file__).resolve().parents[3]
RESULT_ROOT = REPO_ROOT / "results/20260801_care_target_domain_race_gap_closure"


class _NoOpStepScheduler:
    """nnU-Net expects a scheduler object; M0R applies LR manually per optimizer step."""

    def __init__(self, optimizer: torch.optim.Optimizer) -> None:
        self.optimizer = optimizer
        self._last_lr = [float(group["lr"]) for group in optimizer.param_groups]

    def step(self, *_args, **_kwargs) -> None:
        self._last_lr = [float(group["lr"]) for group in self.optimizer.param_groups]

    def get_last_lr(self) -> list[float]:
        return list(self._last_lr)


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
        self.target_optimizer_steps = 4000
        self.warmup_optimizer_steps = 250
        self.min_lr = 1.0e-6
        self.checkpoint_every_optimizer_steps = 500
        self._m0r_optimizer_step = 0

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
        for group in groups:
            group["base_lr"] = float(group["lr"])
        optimizer = torch.optim.AdamW(groups, weight_decay=self.weight_decay)
        scheduler = _NoOpStepScheduler(optimizer)
        return optimizer, scheduler

    def _lr_factor_for_step(self, step: int) -> float:
        if step <= self.warmup_optimizer_steps:
            return max(step / float(self.warmup_optimizer_steps), self.min_lr / 5.0e-4)
        progress = (step - self.warmup_optimizer_steps) / float(self.target_optimizer_steps - self.warmup_optimizer_steps)
        progress = min(max(progress, 0.0), 1.0)
        return 0.5 * (1.0 + math.cos(math.pi * progress))

    def _apply_m0r_lrs(self, step: int) -> None:
        factor = self._lr_factor_for_step(step)
        for group in self.optimizer.param_groups:
            base_lr = float(group.get("base_lr", group["lr"]))
            lr = self.min_lr + (base_lr - self.min_lr) * factor
            group["lr"] = lr

    def train_step(self, batch: dict) -> dict:
        step = self._m0r_optimizer_step + 1
        self._apply_m0r_lrs(step)
        output = super().train_step(batch)
        self._m0r_optimizer_step = step
        if step % self.checkpoint_every_optimizer_steps == 0 and step <= self.target_optimizer_steps:
            self.save_checkpoint(str(Path(self.output_folder) / f"checkpoint_step{step:05d}.pth"))
        return output

    def on_train_start(self):
        self._m0r_optimizer_step = int(self.current_epoch) * int(self.num_iterations_per_epoch)
        super().on_train_start()

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
