"""Lane A Round4 nnU-Net trainer for bounded fold0 edema smoke.

The trainer keeps the nnU-Net Dataset501 label semantics and base loss intact,
then adds a class_4 edema-only focal Tversky auxiliary term. The auxiliary
weight is downweighted for no-T2 cases by case key; class_5 scar remains covered
only by the normal multiclass nnU-Net loss.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Sequence

import numpy as np
import torch
from torch import nn

from nnunetv2.paths import nnUNet_results
from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import nnUNetTrainer_500epochs


EDEMA_CLASS = 4


def _care_root() -> Path:
    return Path(os.environ.get("CARE_ROOT", Path.cwd())).resolve()


def _case_t2_map() -> dict[str, bool]:
    root = _care_root()
    cases_json = root / "data/benchmarks/protocol/cases_MyoPS.json"
    raw_root = root / "data/CARE_Challenge/MyoPS_train"
    data = json.loads(cases_json.read_text(encoding="utf-8"))["cases"]
    out: dict[str, bool] = {}
    for item in data:
        cid = item["case_id"]
        center = item["center"]
        out[cid] = (raw_root / center / cid / f"{cid}_T2.nii.gz").is_file()
    return out


class EdemaFocalTverskyAuxLoss(nn.Module):
    def __init__(
        self,
        base_loss: nn.Module,
        aux_weight: float = 0.25,
        no_t2_weight: float = 0.25,
        alpha_fn: float = 0.7,
        beta_fp: float = 0.3,
        gamma: float = 0.75,
    ) -> None:
        super().__init__()
        self.base_loss = base_loss
        self.aux_weight = float(aux_weight)
        self.no_t2_weight = float(no_t2_weight)
        self.alpha_fn = float(alpha_fn)
        self.beta_fp = float(beta_fp)
        self.gamma = float(gamma)
        self._current_keys: list[str] | None = None
        self._case_has_t2 = _case_t2_map()

    def set_current_keys(self, keys: Sequence[str] | None) -> None:
        self._current_keys = [str(k) for k in keys] if keys is not None else None

    def forward(self, output, target):  # type: ignore[override]
        base = self.base_loss(output, target)
        primary_output = output[0] if isinstance(output, (list, tuple)) else output
        primary_target = target[0] if isinstance(target, (list, tuple)) else target
        aux = self._edema_focal_tversky(primary_output, primary_target)
        return base + self.aux_weight * aux

    def _sample_weights(self, batch_size: int, device: torch.device) -> torch.Tensor:
        if self._current_keys is None:
            return torch.ones(batch_size, device=device, dtype=torch.float32)
        weights = []
        for key in self._current_keys[:batch_size]:
            weights.append(1.0 if self._case_has_t2.get(str(key), False) else self.no_t2_weight)
        while len(weights) < batch_size:
            weights.append(1.0)
        return torch.tensor(weights, device=device, dtype=torch.float32)

    def _edema_focal_tversky(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if target.ndim == logits.ndim:
            target = target[:, 0]
        target = target.long()
        prob = torch.softmax(logits, dim=1)[:, EDEMA_CLASS]
        gt = (target == EDEMA_CLASS).float()
        axes = tuple(range(1, prob.ndim))
        tp = (prob * gt).sum(dim=axes)
        fp = (prob * (1.0 - gt)).sum(dim=axes)
        fn = ((1.0 - prob) * gt).sum(dim=axes)
        tversky = (tp + 1e-6) / (tp + self.alpha_fn * fn + self.beta_fp * fp + 1e-6)
        loss = torch.pow(1.0 - tversky, self.gamma)
        weights = self._sample_weights(logits.shape[0], logits.device)
        return (loss * weights).sum() / torch.clamp(weights.sum(), min=1e-6)


class nnUNetTrainerLaneAEdemaFocalTverskyT2DownShort(nnUNetTrainer_500epochs):
    """Bounded fold0 short-train trainer for Lane A Round4."""

    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict, device: torch.device = torch.device("cuda")):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("LANEA_ROUND4_EPOCHS", "20"))
        self.num_iterations_per_epoch = int(os.environ.get("LANEA_ROUND4_ITERS_PER_EPOCH", "25"))
        self.num_val_iterations_per_epoch = int(os.environ.get("LANEA_ROUND4_VAL_ITERS_PER_EPOCH", "10"))
        self.initial_lr = float(os.environ.get("LANEA_ROUND4_INITIAL_LR", "0.0001"))
        self.save_every = max(1, min(self.save_every, self.num_epochs))
        if nnUNet_results is not None:
            self.output_folder_base = os.path.join(
                nnUNet_results,
                self.plans_manager.dataset_name,
                "laneA_edema_focal_tversky_t2down_fold0_short__"
                + self.plans_manager.plans_name
                + "__"
                + configuration,
            )
            self.output_folder = os.path.join(self.output_folder_base, f"fold_{fold}")

    def _build_loss(self):
        base_loss = super()._build_loss()
        return EdemaFocalTverskyAuxLoss(
            base_loss=base_loss,
            aux_weight=float(os.environ.get("LANEA_ROUND4_AUX_WEIGHT", "0.25")),
            no_t2_weight=float(os.environ.get("LANEA_ROUND4_NO_T2_WEIGHT", "0.25")),
        )

    def train_step(self, batch: dict) -> dict:
        if hasattr(self.loss, "set_current_keys"):
            self.loss.set_current_keys(batch.get("keys"))
        return super().train_step(batch)

    def validation_step(self, batch: dict) -> dict:
        if hasattr(self.loss, "set_current_keys"):
            self.loss.set_current_keys(batch.get("keys"))
        return super().validation_step(batch)
