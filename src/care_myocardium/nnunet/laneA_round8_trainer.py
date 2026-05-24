"""Lane A Round8 nnU-Net trainer components.

Round8 reuses Round7 modality-presence channels and tests a T2-present edema
expert supervision route. The minimum Candidate A keeps the normal nnU-Net
segmentation head but separates class_4 edema supervision by modality group.
"""

from __future__ import annotations

import os
from typing import Sequence

import torch
from torch import nn
from torch.amp import autocast

from batchgenerators.utilities.file_and_folder_operations import maybe_mkdir_p
from nnunetv2.inference.export_prediction import export_prediction_from_logits
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor
from nnunetv2.paths import nnUNet_results
from nnunetv2.training.loss.dice import get_tp_fp_fn_tn
from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import nnUNetTrainer_500epochs
from nnunetv2.utilities.helpers import dummy_context

from src.care_myocardium.nnunet.laneA_round7_trainer import (
    EDEMA_CLASS,
    MODALITY_PRESENCE_ORDER,
    append_modality_presence_channels,
    append_modality_presence_to_case,
    load_case_modality_map,
    nnUNetTrainerLaneAModPresenceUncertaintyShort,
)


SCAR_CLASS = 5
NON_EDEMA_CLASSES = (0, 1, 2, 3, 5)


def t2_present_mask_from_keys(keys: Sequence[str] | None, batch_size: int, device: torch.device) -> torch.Tensor:
    case_meta = load_case_modality_map()
    if keys is None:
        return torch.ones((batch_size,), dtype=torch.bool, device=device)
    values: list[bool] = []
    for key in [str(k) for k in keys][:batch_size]:
        values.append(bool(case_meta.get(key, {}).get("T2_present", False)))
    while len(values) < batch_size:
        values.append(True)
    return torch.tensor(values, dtype=torch.bool, device=device)


def apply_t2_absent_edema_logit_bias(logits: torch.Tensor, t2_mask: torch.Tensor, bias: float) -> torch.Tensor:
    """Apply modality-conditioned edema abstention for no-T2 samples."""

    if bias <= 0 or bool(t2_mask.all()):
        return logits
    adjusted = logits.clone()
    adjusted[~t2_mask, EDEMA_CLASS] = adjusted[~t2_mask, EDEMA_CLASS] - float(bias)
    return adjusted


class SeparatedEdemaLoss(nn.Module):
    """Functional class_4 separation for Round8 Candidate A.

    T2-present samples receive full six-class supervision plus a class_4 expert
    auxiliary loss. no-T2 samples receive dense supervision only over
    non-edema classes [0, 1, 2, 3, 5], so class_4 is not treated as a hard
    voxelwise negative. A weak confidence penalty can optionally discourage
    no-T2 edema logit drift without becoming full dense negative BCE.
    """

    def __init__(
        self,
        full_ce_weight: float = 1.0,
        dice_weight: float = 1.0,
        edema_expert_weight: float = 1.0,
        edema_positive_weight_cap: float = 50.0,
        no_t2_confidence_weight: float = 0.01,
        no_t2_confidence_threshold: float = 0.25,
        t2_absent_logit_bias: float = 0.0,
        eps: float = 1e-6,
    ) -> None:
        super().__init__()
        self.full_ce_weight = float(full_ce_weight)
        self.dice_weight = float(dice_weight)
        self.edema_expert_weight = float(edema_expert_weight)
        self.edema_positive_weight_cap = float(edema_positive_weight_cap)
        self.no_t2_confidence_weight = float(no_t2_confidence_weight)
        self.no_t2_confidence_threshold = float(no_t2_confidence_threshold)
        self.t2_absent_logit_bias = float(t2_absent_logit_bias)
        self.eps = float(eps)
        self._current_keys: list[str] | None = None
        self._case_meta = load_case_modality_map()

    def set_current_keys(self, keys: Sequence[str] | None) -> None:
        self._current_keys = [str(k) for k in keys] if keys is not None else None

    def t2_present_mask(self, batch_size: int, device: torch.device) -> torch.Tensor:
        if self._current_keys is None:
            return torch.ones((batch_size,), dtype=torch.bool, device=device)
        values: list[bool] = []
        for key in self._current_keys[:batch_size]:
            values.append(bool(self._case_meta.get(str(key), {}).get("T2_present", False)))
        while len(values) < batch_size:
            values.append(True)
        return torch.tensor(values, dtype=torch.bool, device=device)

    def forward(self, output, target):  # type: ignore[override]
        logits = output[0] if isinstance(output, (list, tuple)) else output
        labels = target[0] if isinstance(target, (list, tuple)) else target
        if labels.ndim == logits.ndim:
            labels = labels[:, 0]
        labels = labels.long()
        t2_mask = self.t2_present_mask(logits.shape[0], logits.device)
        logits = apply_t2_absent_edema_logit_bias(logits, t2_mask, self.t2_absent_logit_bias)
        losses: list[torch.Tensor] = []
        if bool(t2_mask.any()):
            losses.append(self._t2_present_loss(logits[t2_mask], labels[t2_mask]))
        if bool((~t2_mask).any()):
            losses.append(self._no_t2_loss(logits[~t2_mask], labels[~t2_mask]))
        if not losses:
            return logits.sum() * 0
        return torch.stack(losses).mean()

    def _t2_present_loss(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        ce = torch.nn.functional.cross_entropy(logits, labels)
        dice = self._multiclass_dice_loss(logits, labels, classes=(1, 2, 3, 4, 5))
        edema = self._edema_expert_loss(logits, labels)
        return self.full_ce_weight * ce + self.dice_weight * dice + self.edema_expert_weight * edema

    def _no_t2_loss(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        class_index = torch.tensor(NON_EDEMA_CLASSES, device=logits.device, dtype=torch.long)
        reduced_logits = torch.index_select(logits, 1, class_index)
        reduced_labels = labels.clone()
        reduced_labels[reduced_labels == SCAR_CLASS] = 4
        # no-T2 edema labels should be empty in CARE. If a future split violates
        # this, map class_4 to background for the non-edema loss and let the gate
        # fail through the metadata audit rather than crashing mid-training.
        reduced_labels[reduced_labels == EDEMA_CLASS] = 0
        ce = torch.nn.functional.cross_entropy(reduced_logits, reduced_labels)
        dice = self._multiclass_dice_loss(reduced_logits, reduced_labels, classes=(1, 2, 3, 4))
        prob = torch.softmax(logits, dim=1)[:, EDEMA_CLASS]
        confidence = torch.relu(prob - self.no_t2_confidence_threshold).square().mean()
        return self.full_ce_weight * ce + self.dice_weight * dice + self.no_t2_confidence_weight * confidence

    def _edema_expert_loss(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        gt = (labels == EDEMA_CLASS).float()
        edema_logits = logits[:, EDEMA_CLASS]
        axes = tuple(range(1, gt.ndim))
        pos = gt.sum(dim=axes)
        total = torch.tensor(float(gt[0].numel()), device=gt.device, dtype=gt.dtype)
        raw_pos_weight = torch.clamp((total - pos) / torch.clamp(pos, min=self.eps), min=1.0, max=self.edema_positive_weight_cap)
        view_shape = (gt.shape[0],) + (1,) * (gt.ndim - 1)
        voxel_weight = 1.0 + (raw_pos_weight.view(view_shape) - 1.0) * gt
        bce = torch.nn.functional.binary_cross_entropy_with_logits(edema_logits, gt, reduction="none")
        bce = (bce * voxel_weight).mean()
        prob = torch.softmax(logits, dim=1)[:, EDEMA_CLASS]
        intersection = (prob * gt).sum(dim=axes)
        denominator = prob.sum(dim=axes) + gt.sum(dim=axes)
        dice = 1.0 - (2.0 * intersection + self.eps) / (denominator + self.eps)
        return 0.5 * bce + 0.5 * dice.mean()

    def _multiclass_dice_loss(self, logits: torch.Tensor, labels: torch.Tensor, classes: Sequence[int]) -> torch.Tensor:
        probs = torch.softmax(logits, dim=1)
        losses: list[torch.Tensor] = []
        axes = tuple(range(1, labels.ndim))
        for cls in classes:
            gt = (labels == int(cls)).float()
            prob = probs[:, int(cls)]
            denom = prob.sum(dim=axes) + gt.sum(dim=axes)
            present = gt.sum(dim=axes) > 0
            dice = 1.0 - (2.0 * (prob * gt).sum(dim=axes) + self.eps) / (denom + self.eps)
            if bool(present.any()):
                losses.append(dice[present].mean())
        if not losses:
            return logits.sum() * 0
        return torch.stack(losses).mean()


class nnUNetTrainerLaneAT2EdemaExpertShort(nnUNetTrainerLaneAModPresenceUncertaintyShort):
    """Bounded trainer for Round8 Candidate A."""

    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict, device: torch.device = torch.device("cuda")):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("LANEA_ROUND8_EPOCHS", "5"))
        self.num_iterations_per_epoch = int(os.environ.get("LANEA_ROUND8_ITERS_PER_EPOCH", "10"))
        self.num_val_iterations_per_epoch = int(os.environ.get("LANEA_ROUND8_VAL_ITERS_PER_EPOCH", "5"))
        self.initial_lr = float(os.environ.get("LANEA_ROUND8_INITIAL_LR", "0.0001"))
        self.save_every = max(1, min(self.save_every, self.num_epochs))
        if nnUNet_results is not None:
            self.output_folder_base = os.path.join(
                nnUNet_results,
                self.plans_manager.dataset_name,
                "laneA_t2_edema_expert_sephead_fold0_short__"
                + self.plans_manager.plans_name
                + "__"
                + configuration,
            )
            self.output_folder = os.path.join(self.output_folder_base, f"fold_{fold}")

    def _build_loss(self):
        return SeparatedEdemaLoss(
            full_ce_weight=float(os.environ.get("LANEA_ROUND8_FULL_CE_WEIGHT", "1.0")),
            dice_weight=float(os.environ.get("LANEA_ROUND8_DICE_WEIGHT", "1.0")),
            edema_expert_weight=float(os.environ.get("LANEA_ROUND8_EDEMA_EXPERT_WEIGHT", "3.0")),
            edema_positive_weight_cap=float(os.environ.get("LANEA_ROUND8_EDEMA_POSITIVE_WEIGHT_CAP", "50.0")),
            no_t2_confidence_weight=float(os.environ.get("LANEA_ROUND8_NO_T2_CONFIDENCE_WEIGHT", "0.01")),
            no_t2_confidence_threshold=float(os.environ.get("LANEA_ROUND8_NO_T2_CONFIDENCE_THRESHOLD", "0.25")),
            t2_absent_logit_bias=float(os.environ.get("LANEA_ROUND8_T2_ABSENT_LOGIT_BIAS", "6.0")),
        )

    def _prepare_round8_batch(self, batch: dict) -> tuple[torch.Tensor, object]:
        return self._prepare_round7_batch(batch)

    def train_step(self, batch: dict) -> dict:
        data, target = self._prepare_round8_batch(batch)
        self.optimizer.zero_grad(set_to_none=True)
        with autocast(self.device.type, enabled=True) if self.device.type == "cuda" else dummy_context():
            output = self.network(data)
            loss = self.loss(output, target)
        if self.grad_scaler is not None:
            self.grad_scaler.scale(loss).backward()
            self.grad_scaler.unscale_(self.optimizer)
            torch.nn.utils.clip_grad_norm_(self.network.parameters(), 12)
            self.grad_scaler.step(self.optimizer)
            self.grad_scaler.update()
        else:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.network.parameters(), 12)
            self.optimizer.step()
        return {"loss": loss.detach().cpu().numpy()}

    def validation_step(self, batch: dict) -> dict:
        data, target = self._prepare_round8_batch(batch)
        with autocast(self.device.type, enabled=True) if self.device.type == "cuda" else dummy_context():
            output = self.network(data)
            loss = self.loss(output, target)
        if self.enable_deep_supervision:
            output = output[0]
            target = target[0]
            t2_mask = t2_present_mask_from_keys(batch.get("keys"), data.shape[0], data.device)
            output = apply_t2_absent_edema_logit_bias(
                output,
                t2_mask,
                float(os.environ.get("LANEA_ROUND8_T2_ABSENT_LOGIT_BIAS", "6.0")),
            )

        axes = [0] + list(range(2, output.ndim))
        if self.label_manager.has_regions:
            predicted_segmentation_onehot = (torch.sigmoid(output) > 0.5).long()
        else:
            output_seg = output.argmax(1)[:, None]
            predicted_segmentation_onehot = torch.zeros(output.shape, device=output.device, dtype=torch.float16)
            predicted_segmentation_onehot.scatter_(1, output_seg, 1)
            del output_seg

        if self.label_manager.has_ignore_label:
            if not self.label_manager.has_regions:
                mask = (target != self.label_manager.ignore_label).float()
                target[target == self.label_manager.ignore_label] = 0
            else:
                if target.dtype == torch.bool:
                    mask = ~target[:, -1:]
                else:
                    mask = 1 - target[:, -1:]
                target = target[:, :-1]
        else:
            mask = None

        tp, fp, fn, _ = get_tp_fp_fn_tn(predicted_segmentation_onehot, target, axes=axes, mask=mask)
        tp_hard = tp.detach().cpu().numpy()
        fp_hard = fp.detach().cpu().numpy()
        fn_hard = fn.detach().cpu().numpy()
        if not self.label_manager.has_regions:
            tp_hard = tp_hard[1:]
            fp_hard = fp_hard[1:]
            fn_hard = fn_hard[1:]
        return {"loss": loss.detach().cpu().numpy(), "tp_hard": tp_hard, "fp_hard": fp_hard, "fn_hard": fn_hard}

    def perform_actual_validation(self, save_probabilities: bool = False):
        self.set_deep_supervision_enabled(False)
        self.network.eval()
        predictor = nnUNetPredictor(
            tile_step_size=0.5,
            use_gaussian=True,
            use_mirroring=True,
            perform_everything_on_device=True,
            device=self.device,
            verbose=False,
            verbose_preprocessing=False,
            allow_tqdm=False,
        )
        predictor.manual_initialization(
            self.network,
            self.plans_manager,
            self.configuration_manager,
            None,
            self.dataset_json,
            self.__class__.__name__,
            self.inference_allowed_mirroring_axes,
        )

        validation_output_folder = os.path.join(self.output_folder, "validation")
        maybe_mkdir_p(validation_output_folder)
        _, val_keys = self.do_split()
        dataset_val = self.dataset_class(
            self.preprocessed_dataset_folder,
            val_keys,
            folder_with_segs_from_previous_stage=self.folder_with_segs_from_previous_stage,
        )
        case_meta = load_case_modality_map()
        bias = float(os.environ.get("LANEA_ROUND8_T2_ABSENT_LOGIT_BIAS", "6.0"))
        for key in dataset_val.identifiers:
            self.print_to_log_file(f"predicting {key} with Round8 modality-presence channels")
            data, _, _, properties = dataset_val.load_case(key)
            data = append_modality_presence_to_case(data[:], key, self._case_meta)
            self.print_to_log_file(f"{key}, shape {tuple(data.shape)}")
            prediction = predictor.predict_sliding_window_return_logits(data).cpu()
            if not bool(case_meta.get(str(key), {}).get("T2_present", False)):
                prediction[EDEMA_CLASS] = prediction[EDEMA_CLASS] - bias
            output_filename_truncated = os.path.join(validation_output_folder, key)
            export_prediction_from_logits(
                prediction,
                properties,
                self.configuration_manager,
                self.plans_manager,
                self.dataset_json,
                output_filename_truncated,
                save_probabilities,
            )
