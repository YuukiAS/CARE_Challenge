"""Lane A Round7 nnU-Net trainer components.

Round7 tests explicit modality-presence conditioning plus uncertainty-weighted
class_4 edema supervision. The implementation keeps Dataset501 label semantics,
fold splits, and the standard multiclass nnU-Net base loss intact.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
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


EDEMA_CLASS = 4
MODALITY_PRESENCE_ORDER = ("C0", "LGE", "T2")


def _care_root() -> Path:
    return Path(os.environ.get("CARE_ROOT", Path.cwd())).resolve()


def load_case_modality_map(root: Path | None = None) -> dict[str, dict[str, object]]:
    """Return case metadata used for conditioning and loss weights."""

    care_root = root or _care_root()
    cases_json = care_root / "data/benchmarks/protocol/cases_MyoPS.json"
    raw_root = care_root / "data/CARE_Challenge/MyoPS_train"
    data = json.loads(cases_json.read_text(encoding="utf-8"))["cases"]
    out: dict[str, dict[str, object]] = {}
    for item in data:
        cid = item["case_id"]
        center = item["center"]
        case_dir = raw_root / center / cid
        has_c0 = (case_dir / f"{cid}_C0.nii.gz").is_file()
        has_lge = (case_dir / f"{cid}_LGE.nii.gz").is_file()
        has_t2 = (case_dir / f"{cid}_T2.nii.gz").is_file()
        if has_c0 and has_lge and has_t2:
            group = "C0+LGE+T2"
        elif has_c0 and has_lge:
            group = "C0+LGE"
        elif has_lge:
            group = "LGE-only"
        else:
            group = "other"
        out[cid] = {
            "center": center,
            "modality_group": group,
            "C0_present": has_c0,
            "LGE_present": has_lge,
            "T2_present": has_t2,
        }
    return out


def modality_presence_tensor(
    keys: Sequence[str] | None,
    spatial_shape: Sequence[int],
    case_meta: Mapping[str, Mapping[str, object]],
    device: torch.device,
    dtype: torch.dtype,
    batch_size: int,
) -> torch.Tensor:
    """Create constant C0/LGE/T2 presence channels for a batch."""

    values: list[list[float]] = []
    safe_keys = [str(k) for k in keys] if keys is not None else []
    for idx in range(batch_size):
        key = safe_keys[idx] if idx < len(safe_keys) else ""
        meta = case_meta.get(key, {})
        values.append([1.0 if meta.get(f"{name}_present", False) else 0.0 for name in MODALITY_PRESENCE_ORDER])
    base = torch.tensor(values, device=device, dtype=dtype)
    view_shape = (batch_size, len(MODALITY_PRESENCE_ORDER), *([1] * len(spatial_shape)))
    return base.view(view_shape).expand(batch_size, len(MODALITY_PRESENCE_ORDER), *spatial_shape)


def append_modality_presence_channels(
    data: torch.Tensor,
    keys: Sequence[str] | None,
    case_meta: Mapping[str, Mapping[str, object]],
) -> torch.Tensor:
    """Append C0/LGE/T2 constant presence channels to image data."""

    presence = modality_presence_tensor(
        keys=keys,
        spatial_shape=data.shape[2:],
        case_meta=case_meta,
        device=data.device,
        dtype=data.dtype,
        batch_size=data.shape[0],
    )
    return torch.cat([data, presence], dim=1)


def append_modality_presence_to_case(
    data: np.ndarray | torch.Tensor,
    key: str,
    case_meta: Mapping[str, Mapping[str, object]],
) -> torch.Tensor:
    """Append modality-presence channels to one preprocessed case."""

    tensor = data if isinstance(data, torch.Tensor) else torch.from_numpy(np.asarray(data))
    if tensor.ndim != 4:
        raise ValueError(f"Expected one preprocessed case with shape (c, z, y, x), got {tuple(tensor.shape)}")
    batched = tensor[None].float()
    return append_modality_presence_channels(batched, [key], case_meta)[0]


class EdemaUncertaintyWeightedAuxLoss(nn.Module):
    """Class_4 auxiliary loss with low-weight no-T2 negative supervision."""

    def __init__(
        self,
        base_loss: nn.Module,
        aux_weight: float = 0.20,
        no_t2_negative_weight: float = 0.05,
        t2_present_weight: float = 1.0,
        eps: float = 1e-6,
    ) -> None:
        super().__init__()
        self.base_loss = base_loss
        self.aux_weight = float(aux_weight)
        self.no_t2_negative_weight = float(no_t2_negative_weight)
        self.t2_present_weight = float(t2_present_weight)
        self.eps = float(eps)
        self._current_keys: list[str] | None = None
        self._case_meta = load_case_modality_map()

    def set_current_keys(self, keys: Sequence[str] | None) -> None:
        self._current_keys = [str(k) for k in keys] if keys is not None else None

    def sample_weights(self, batch_size: int, device: torch.device) -> torch.Tensor:
        if self._current_keys is None:
            return torch.full((batch_size,), self.t2_present_weight, device=device, dtype=torch.float32)
        weights: list[float] = []
        for key in self._current_keys[:batch_size]:
            has_t2 = bool(self._case_meta.get(str(key), {}).get("T2_present", False))
            weights.append(self.t2_present_weight if has_t2 else self.no_t2_negative_weight)
        while len(weights) < batch_size:
            weights.append(self.t2_present_weight)
        return torch.tensor(weights, device=device, dtype=torch.float32)

    def forward(self, output, target):  # type: ignore[override]
        base = self.base_loss(output, target)
        primary_output = output[0] if isinstance(output, (list, tuple)) else output
        primary_target = target[0] if isinstance(target, (list, tuple)) else target
        aux = self._edema_auxiliary_loss(primary_output, primary_target)
        return base + self.aux_weight * aux

    def _edema_auxiliary_loss(self, logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        if target.ndim == logits.ndim:
            target = target[:, 0]
        target = target.long()
        edema_logits = logits[:, EDEMA_CLASS]
        prob = torch.softmax(logits, dim=1)[:, EDEMA_CLASS]
        gt = (target == EDEMA_CLASS).float()
        axes = tuple(range(1, prob.ndim))

        gt_voxels = gt.sum(dim=axes)
        bce = torch.nn.functional.binary_cross_entropy_with_logits(
            edema_logits,
            gt,
            reduction="none",
        ).mean(dim=axes)

        intersection = (prob * gt).sum(dim=axes)
        denominator = prob.sum(dim=axes) + gt_voxels
        dice_loss = 1.0 - (2.0 * intersection + self.eps) / (denominator + self.eps)
        positive_loss = 0.5 * bce + 0.5 * dice_loss

        # Empty-GT cases only receive low-weight BCE. This avoids converting
        # no-T2 empty-GT cases into strong class_4 negative supervision.
        per_sample = torch.where(gt_voxels > 0, positive_loss, bce)
        weights = self.sample_weights(logits.shape[0], logits.device)
        return (per_sample * weights).sum() / torch.clamp(weights.sum(), min=self.eps)


class nnUNetTrainerLaneAModPresenceUncertaintyShort(nnUNetTrainer_500epochs):
    """Bounded fold0 trainer for Round7 modality-aware edema supervision."""

    @staticmethod
    def build_network_architecture(
        plans_manager,
        configuration_manager,
        num_input_channels: int,
        num_output_channels: int,
        enable_deep_supervision: bool = True,
    ) -> nn.Module:
        return nnUNetTrainer_500epochs.build_network_architecture(
            plans_manager,
            configuration_manager,
            num_input_channels + len(MODALITY_PRESENCE_ORDER),
            num_output_channels,
            enable_deep_supervision,
        )

    def __init__(self, plans: dict, configuration: str, fold: int, dataset_json: dict, device: torch.device = torch.device("cuda")):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = int(os.environ.get("LANEA_ROUND7_EPOCHS", "5"))
        self.num_iterations_per_epoch = int(os.environ.get("LANEA_ROUND7_ITERS_PER_EPOCH", "10"))
        self.num_val_iterations_per_epoch = int(os.environ.get("LANEA_ROUND7_VAL_ITERS_PER_EPOCH", "5"))
        self.initial_lr = float(os.environ.get("LANEA_ROUND7_INITIAL_LR", "0.0001"))
        self.save_every = max(1, min(self.save_every, self.num_epochs))
        self._case_meta = load_case_modality_map()
        if nnUNet_results is not None:
            self.output_folder_base = os.path.join(
                nnUNet_results,
                self.plans_manager.dataset_name,
                "laneA_modpresence_uncertainty_fold0_short__"
                + self.plans_manager.plans_name
                + "__"
                + configuration,
            )
            self.output_folder = os.path.join(self.output_folder_base, f"fold_{fold}")

    def _build_loss(self):
        base_loss = super()._build_loss()
        return EdemaUncertaintyWeightedAuxLoss(
            base_loss=base_loss,
            aux_weight=float(os.environ.get("LANEA_ROUND7_AUX_WEIGHT", "0.20")),
            no_t2_negative_weight=float(os.environ.get("LANEA_ROUND7_NO_T2_NEGATIVE_WEIGHT", "0.05")),
            t2_present_weight=float(os.environ.get("LANEA_ROUND7_T2_PRESENT_WEIGHT", "1.0")),
        )

    def _prepare_round7_batch(self, batch: dict) -> tuple[torch.Tensor, object]:
        keys = batch.get("keys")
        if hasattr(self.loss, "set_current_keys"):
            self.loss.set_current_keys(keys)
        data = batch["data"].to(self.device, non_blocking=True)
        data = append_modality_presence_channels(data, keys, self._case_meta)
        target = batch["target"]
        if isinstance(target, list):
            target = [i.to(self.device, non_blocking=True) for i in target]
        else:
            target = target.to(self.device, non_blocking=True)
        return data, target

    def train_step(self, batch: dict) -> dict:
        data, target = self._prepare_round7_batch(batch)
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
        data, target = self._prepare_round7_batch(batch)
        with autocast(self.device.type, enabled=True) if self.device.type == "cuda" else dummy_context():
            output = self.network(data)
            loss = self.loss(output, target)
        if self.enable_deep_supervision:
            output = output[0]
            target = target[0]

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
        """Export fold validation predictions with Round7 channel injection.

        The default nnU-Net implementation loads 3-channel preprocessed cases
        and feeds them directly to the predictor. Round7 networks expect the 3
        original image channels plus 3 modality-presence channels, so validation
        export must inject those channels case-by-case.
        """

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
        for key in dataset_val.identifiers:
            self.print_to_log_file(f"predicting {key} with Round7 modality-presence channels")
            data, _, _, properties = dataset_val.load_case(key)
            data = append_modality_presence_to_case(data[:], key, self._case_meta)
            self.print_to_log_file(f"{key}, shape {tuple(data.shape)}")
            prediction = predictor.predict_sliding_window_return_logits(data).cpu()
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
