from __future__ import annotations

from itertools import combinations

import torch
from torch import nn
from torch.nn import functional as F
import numpy as np

from myops.data.labels import (
    STAGE_FINE,
    TRACK_CINE,
    TRACK_MYOPS,
    class_order_for_track,
    default_class_weights,
)


def labels_to_one_hot(label: torch.Tensor, num_classes: int) -> torch.Tensor:
    return torch.stack([(label == i).float() for i in range(1, num_classes + 1)], dim=1)


def masked_sigmoid_dice_loss(
    logits: torch.Tensor, target: torch.Tensor, supervision_mask: torch.Tensor,
    class_weights: torch.Tensor | None = None, smooth: float = 1e-5,
) -> torch.Tensor:
    probs = torch.sigmoid(logits)
    dims = tuple(range(2, probs.ndim))
    intersection = (probs * target).sum(dim=dims)
    denominator = probs.sum(dim=dims) + target.sum(dim=dims)
    dice = (2.0 * intersection + smooth) / (denominator + smooth)
    loss = 1.0 - dice
    if class_weights is not None:
        loss = loss * class_weights.view(1, -1)
    loss = loss * supervision_mask
    return loss.sum() / supervision_mask.sum().clamp_min(1.0)


def masked_bce_loss(
    logits: torch.Tensor, target: torch.Tensor, supervision_mask: torch.Tensor,
    class_weights: torch.Tensor | None = None,
) -> torch.Tensor:
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    bce = bce.mean(dim=tuple(range(2, bce.ndim)))
    if class_weights is not None:
        bce = bce * class_weights.view(1, -1)
    bce = bce * supervision_mask
    return bce.sum() / supervision_mask.sum().clamp_min(1.0)


def _pathology_indices(track: str, stage: str, num_classes: int) -> list[int]:
    if stage != STAGE_FINE:
        return []
    if track == TRACK_MYOPS:
        return [i for i in (3, 4) if i < num_classes]
    if track == TRACK_CINE:
        return [2] if num_classes >= 3 else []
    return []


def _class_specific_pathology_indices(track: str, stage: str, num_classes: int) -> dict[str, int]:
    if stage != STAGE_FINE:
        return {}
    if track == TRACK_MYOPS:
        mapping = {"edema": 3, "scar": 4}
    elif track == TRACK_CINE:
        mapping = {"cine_scar": 2}
    else:
        mapping = {}
    return {name: idx for name, idx in mapping.items() if idx < num_classes}


def _enabled_class_mask(
    track: str,
    stage: str,
    num_classes: int,
    enabled_classes: list[str | int] | None,
    device: torch.device,
) -> torch.Tensor | None:
    if enabled_classes is None:
        return None
    class_names = class_order_for_track(track, stage)[:num_classes]
    mask = torch.zeros(num_classes, dtype=torch.float32, device=device)
    for raw_name in enabled_classes:
        if isinstance(raw_name, int):
            index = int(raw_name)
            if index >= 1:
                index -= 1
            if index < 0 or index >= num_classes:
                raise ValueError(f"enabled_classes index out of range: {raw_name}")
        else:
            name = str(raw_name)
            if name not in class_names:
                raise ValueError(f"enabled_classes contains unknown class for {track}/{stage}: {name}")
            index = class_names.index(name)
        mask[index] = 1.0
    return mask.view(1, -1)


def masked_pathology_tversky_loss(
    logits: torch.Tensor, target: torch.Tensor, supervision_mask: torch.Tensor,
    indices: list[int], alpha: float, beta: float, smooth: float = 1e-5,
) -> torch.Tensor:
    if not indices:
        return logits.sum() * 0.0
    probs = torch.sigmoid(logits[:, indices])
    target = target[:, indices]
    supervision = supervision_mask[:, indices]
    dims = tuple(range(2, probs.ndim))
    tp = (probs * target).sum(dim=dims)
    fp = (probs * (1.0 - target)).sum(dim=dims)
    fn = ((1.0 - probs) * target).sum(dim=dims)
    score = (tp + smooth) / (tp + alpha * fp + beta * fn + smooth)
    loss = (1.0 - score) * supervision
    return loss.sum() / supervision.sum().clamp_min(1.0)


def masked_pathology_focal_loss(
    logits: torch.Tensor, target: torch.Tensor, supervision_mask: torch.Tensor,
    indices: list[int], gamma: float,
) -> torch.Tensor:
    if not indices:
        return logits.sum() * 0.0
    logits = logits[:, indices]
    target = target[:, indices]
    supervision = supervision_mask[:, indices]
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    focal = ((1.0 - torch.exp(-bce)) ** gamma) * bce
    focal = focal.mean(dim=tuple(range(2, focal.ndim)))
    focal = focal * supervision
    return focal.sum() / supervision.sum().clamp_min(1.0)


def pathology_inclusiveness_loss(
    logits: torch.Tensor, target: torch.Tensor, supervision_mask: torch.Tensor,
    edema_idx: int = 3, scar_idx: int = 4, eps: float = 1e-7,
) -> torch.Tensor:
    both_supervised = supervision_mask[:, edema_idx] * supervision_mask[:, scar_idx]
    if both_supervised.sum() < 0.5:
        return logits.sum() * 0.0

    scar_prob = torch.sigmoid(logits[:, scar_idx])
    edema_prob = torch.sigmoid(logits[:, edema_idx])
    scar_target = target[:, scar_idx]
    edema_target = target[:, edema_idx]

    non_edema = 1.0 - edema_target
    omega_edema = non_edema.sum(dim=(-2, -1)).clamp_min(1.0)
    l_inc_s = -(non_edema * torch.log(1.0 - scar_prob + eps)).sum(dim=(-2, -1)) / omega_edema

    omega_scar = scar_target.sum(dim=(-2, -1)).clamp_min(1.0)
    l_inc_e = -(scar_target * torch.log(edema_prob + eps)).sum(dim=(-2, -1)) / omega_scar

    loss = (l_inc_s + l_inc_e) * both_supervised
    return loss.sum() / both_supervised.sum().clamp_min(1.0)


def flow_smoothness_loss(flow: torch.Tensor) -> torch.Tensor:
    if flow.shape[-1] < 2 or flow.shape[-2] < 2:
        return flow.sum() * 0.0
    dx = torch.abs(flow[..., :, :, 1:] - flow[..., :, :, :-1]).mean()
    dy = torch.abs(flow[..., :, 1:, :] - flow[..., :, :-1, :]).mean()
    return dx + dy


class MyocardiumConsistencyLoss(nn.Module):
    """Enforce cross-modality agreement on myocardium segmentation."""

    def __init__(self) -> None:
        super().__init__()

    def forward(
        self, myo_preds: dict[str, torch.Tensor], myo_target: torch.Tensor,
        presence_mask: torch.Tensor, smooth: float = 1e-5,
    ) -> torch.Tensor:
        modality_names = ["lge", "c0", "t2"]
        modality_indices = {"lge": 0, "c0": 1, "t2": 2}
        loss = torch.tensor(0.0, device=myo_target.device)
        count = 0

        for name in modality_names:
            if name not in myo_preds:
                continue
            idx = modality_indices[name]
            p = presence_mask[:, idx].mean()
            if p < 0.5:
                continue
            pred = torch.sigmoid(myo_preds[name])
            dims = tuple(range(2, pred.ndim))
            inter = (pred * myo_target).sum(dim=dims)
            denom = pred.sum(dim=dims) + myo_target.sum(dim=dims)
            dice = (2.0 * inter + smooth) / (denom + smooth)
            loss = loss + (1.0 - dice).mean()
            count += 1

        for (name_a, pred_a), (name_b, pred_b) in combinations(myo_preds.items(), 2):
            idx_a = modality_indices.get(name_a, -1)
            idx_b = modality_indices.get(name_b, -1)
            if idx_a < 0 or idx_b < 0:
                continue
            pa = presence_mask[:, idx_a].mean()
            pb = presence_mask[:, idx_b].mean()
            if pa < 0.5 or pb < 0.5:
                continue
            sa = torch.sigmoid(pred_a)
            sb = torch.sigmoid(pred_b)
            dims = tuple(range(2, sa.ndim))
            inter = (sa * sb).sum(dim=dims)
            denom = sa.sum(dim=dims) + sb.sum(dim=dims)
            dice = (2.0 * inter + smooth) / (denom + smooth)
            loss = loss + (1.0 - dice).mean()
            count += 1

        return loss / max(count, 1)


class BinaryGaussianDiceLoss(nn.Module):
    """Registration loss: Gaussian-smoothed Dice on warped masks."""

    def __init__(self, sigma: float = 1.0) -> None:
        super().__init__()
        self.sigma = sigma

    def _smooth(self, mask: torch.Tensor) -> torch.Tensor:
        if self.sigma <= 0:
            return mask
        k = int(3 * self.sigma) * 2 + 1
        padding = k // 2
        x = torch.arange(k, dtype=mask.dtype, device=mask.device) - k // 2
        kernel_1d = torch.exp(-0.5 * (x / self.sigma) ** 2)
        kernel_1d = kernel_1d / kernel_1d.sum()
        kernel_2d = kernel_1d[:, None] * kernel_1d[None, :]
        kernel_2d = kernel_2d.view(1, 1, k, k)
        b, c = mask.shape[:2]
        mask = mask.view(b * c, 1, *mask.shape[2:])
        mask = F.pad(mask, [padding] * 4, mode="replicate")
        mask = F.conv2d(mask, kernel_2d)
        return mask.view(b, c, *mask.shape[2:])

    def forward(self, pred_mask: torch.Tensor, target_mask: torch.Tensor, smooth: float = 1e-5) -> torch.Tensor:
        pred_s = self._smooth(pred_mask)
        target_s = self._smooth(target_mask)
        dims = tuple(range(2, pred_s.ndim))
        inter = (pred_s * target_s).sum(dim=dims)
        denom = pred_s.sum(dim=dims) + target_s.sum(dim=dims)
        dice = (2.0 * inter + smooth) / (denom + smooth)
        return (1.0 - dice).mean()


class StageLoss(nn.Module):
    def __init__(
        self, track: str, stage: str,
        class_weights: list[float] | None = None,
        deep_supervision_weights: list[float] | None = None,
        pathology_tversky_weight: float = 0.0,
        pathology_focal_weight: float = 0.0,
        pathology_tversky_alpha: float = 0.7,
        pathology_tversky_beta: float = 0.3,
        pathology_focal_gamma: float = 2.0,
        class_specific_pathology: dict | None = None,
        enabled_classes: list[str | int] | None = None,
        consistency_weight: float = 0.0,
        registration_weight: float = 0.0,
        inclusiveness_weight: float = 0.0,
        t2_aux_weight: float = 0.0,
        edema_gaussian_dice_weight: float = 0.0,
        edema_gaussian_dice_sigma: float = 1.5,
        cine_aux_weights: dict | None = None,
    ) -> None:
        super().__init__()
        self.track = track
        self.stage = stage
        class_weights = class_weights or default_class_weights(track, stage)
        self.class_weights = torch.tensor(class_weights, dtype=torch.float32)
        self.deep_supervision_weights = deep_supervision_weights or [0.3, 0.15]
        self.pathology_tversky_weight = float(pathology_tversky_weight)
        self.pathology_focal_weight = float(pathology_focal_weight)
        self.pathology_tversky_alpha = float(pathology_tversky_alpha)
        self.pathology_tversky_beta = float(pathology_tversky_beta)
        self.pathology_focal_gamma = float(pathology_focal_gamma)
        self.class_specific_pathology = class_specific_pathology or {}
        self.enabled_classes = enabled_classes
        self.consistency_weight = float(consistency_weight)
        self.registration_weight = float(registration_weight)
        self.inclusiveness_weight = float(inclusiveness_weight)
        self.t2_aux_weight = float(t2_aux_weight)
        self.edema_gaussian_dice_weight = float(edema_gaussian_dice_weight)
        if self.edema_gaussian_dice_weight > 0:
            self.edema_gaussian_dice = BinaryGaussianDiceLoss(sigma=float(edema_gaussian_dice_sigma))
        self.cine_aux_weights = cine_aux_weights or {}
        if self.consistency_weight > 0:
            self.consistency_loss = MyocardiumConsistencyLoss()
        if self.registration_weight > 0:
            self.registration_loss = BinaryGaussianDiceLoss(sigma=1.0)

    def forward(self, outputs: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        logits = outputs["logits"]
        num_classes = logits.shape[1]
        target = labels_to_one_hot(batch["label"], num_classes=num_classes)
        supervision = batch["supervision_mask"][:, :num_classes].to(logits.device)
        enabled_mask = _enabled_class_mask(self.track, self.stage, num_classes, self.enabled_classes, logits.device)
        if enabled_mask is not None:
            supervision = supervision * enabled_mask
        cw = self.class_weights[:num_classes].to(logits.device)

        dice = masked_sigmoid_dice_loss(logits, target, supervision, class_weights=cw)
        bce = masked_bce_loss(logits, target, supervision, class_weights=cw)
        total = dice + bce

        pathology_tversky = logits.sum() * 0.0
        pathology_focal = logits.sum() * 0.0
        class_specific_indices = _class_specific_pathology_indices(self.track, self.stage, num_classes)

        if self.class_specific_pathology:
            for class_name, class_cfg in self.class_specific_pathology.items():
                if class_name not in class_specific_indices:
                    continue
                index = class_specific_indices[class_name]
                tw = float(class_cfg.get("tversky_weight", 0.0))
                fw = float(class_cfg.get("focal_weight", 0.0))
                if tw > 0:
                    pathology_tversky = pathology_tversky + tw * masked_pathology_tversky_loss(
                        logits, target, supervision, [index],
                        alpha=float(class_cfg.get("alpha", self.pathology_tversky_alpha)),
                        beta=float(class_cfg.get("beta", self.pathology_tversky_beta)),
                    )
                if fw > 0:
                    pathology_focal = pathology_focal + fw * masked_pathology_focal_loss(
                        logits, target, supervision, [index],
                        gamma=float(class_cfg.get("gamma", self.pathology_focal_gamma)),
                    )
            total = total + pathology_tversky + pathology_focal
        else:
            pathology_indices = _pathology_indices(self.track, self.stage, num_classes)
            pathology_tversky = masked_pathology_tversky_loss(
                logits, target, supervision, pathology_indices,
                alpha=self.pathology_tversky_alpha, beta=self.pathology_tversky_beta,
            )
            pathology_focal = masked_pathology_focal_loss(
                logits, target, supervision, pathology_indices,
                gamma=self.pathology_focal_gamma,
            )
            total = total + self.pathology_tversky_weight * pathology_tversky
            total = total + self.pathology_focal_weight * pathology_focal

        if "deep_supervision" in outputs:
            for weight, aux_logits in zip(self.deep_supervision_weights, outputs["deep_supervision"]):
                total = total + weight * (
                    masked_sigmoid_dice_loss(aux_logits, target, supervision, class_weights=cw)
                    + masked_bce_loss(aux_logits, target, supervision, class_weights=cw)
                )

        consistency = logits.sum() * 0.0
        if self.consistency_weight > 0 and "myo_preds" in outputs:
            myo_target = (batch["label"] == 1).float().unsqueeze(1)
            presence = batch["image"][:, 3:6, :1, :1].squeeze(-1).squeeze(-1)
            consistency = self.consistency_loss(outputs["myo_preds"], myo_target, presence)
            total = total + self.consistency_weight * consistency

        registration = logits.sum() * 0.0
        if self.registration_weight > 0 and "theta_c0" in outputs:
            myo_target = (batch["label"] == 1).float().unsqueeze(1)
            registration = self.registration_loss(myo_target, myo_target)
            total = total + self.registration_weight * registration

        cine_anatomy = logits.sum() * 0.0
        cine_consistency = logits.sum() * 0.0
        cine_motion = logits.sum() * 0.0
        cine_smooth = logits.sum() * 0.0
        if self.cine_aux_weights and self.track == TRACK_CINE and self.stage == STAGE_FINE:
            pathology_weight = float(self.cine_aux_weights.get("pathology", 1.0))
            total = total * pathology_weight

            if "anatomy_logits" in outputs:
                anatomy_logits = outputs["anatomy_logits"]
                ref_anatomy = anatomy_logits[:, 0]
                anatomy_target = target[:, :2]
                anatomy_supervision = supervision[:, :2]
                cine_anatomy = (
                    masked_sigmoid_dice_loss(ref_anatomy, anatomy_target, anatomy_supervision)
                    + masked_bce_loss(ref_anatomy, anatomy_target, anatomy_supervision)
                )
                total = total + float(self.cine_aux_weights.get("anatomy", 0.0)) * cine_anatomy

            if "warped_anatomy" in outputs and "anatomy_logits" in outputs and outputs["warped_anatomy"].shape[1] > 1:
                ref_prob = torch.sigmoid(outputs["anatomy_logits"][:, 0]).unsqueeze(1)
                cine_consistency = F.mse_loss(outputs["warped_anatomy"][:, 1:], ref_prob.expand_as(outputs["warped_anatomy"][:, 1:]))
                total = total + float(self.cine_aux_weights.get("consistency", 0.0)) * cine_consistency

            if "warped_images" in outputs and "ref_image" in outputs and outputs["warped_images"].shape[1] > 1:
                ref_image = outputs["ref_image"].unsqueeze(1)
                cine_motion = F.mse_loss(outputs["warped_images"][:, 1:], ref_image.expand_as(outputs["warped_images"][:, 1:]))
                total = total + float(self.cine_aux_weights.get("motion", 0.0)) * cine_motion

            if "motion_fields" in outputs and outputs["motion_fields"].shape[1] > 1:
                cine_smooth = flow_smoothness_loss(outputs["motion_fields"][:, 1:])
                total = total + float(self.cine_aux_weights.get("smooth", 0.0)) * cine_smooth

        inclusiveness = logits.sum() * 0.0
        if self.inclusiveness_weight > 0 and self.track == TRACK_MYOPS and self.stage == STAGE_FINE and num_classes >= 5:
            inclusiveness = pathology_inclusiveness_loss(logits, target, supervision)
            total = total + self.inclusiveness_weight * inclusiveness

        t2_edema = logits.sum() * 0.0
        if self.t2_aux_weight > 0 and "t2_edema_logits" in outputs and num_classes >= 4:
            t2_logits = outputs["t2_edema_logits"]
            edema_target = target[:, 3:4]
            edema_sup = supervision[:, 3:4]
            t2_edema = (
                masked_sigmoid_dice_loss(t2_logits, edema_target, edema_sup)
                + masked_bce_loss(t2_logits, edema_target, edema_sup)
            )
            total = total + self.t2_aux_weight * t2_edema

        edema_gdice = logits.sum() * 0.0
        if self.edema_gaussian_dice_weight > 0 and num_classes >= 4:
            edema_sup_flags = supervision[:, 3]
            supervised_idx = edema_sup_flags > 0.5
            if supervised_idx.any():
                edema_prob = torch.sigmoid(logits[supervised_idx, 3:4])
                edema_tgt = target[supervised_idx, 3:4]
                edema_gdice = self.edema_gaussian_dice(edema_prob, edema_tgt)
                total = total + self.edema_gaussian_dice_weight * edema_gdice

        return {
            "loss": total,
            "dice_loss": dice.detach(),
            "bce_loss": bce.detach(),
            "pathology_tversky_loss": pathology_tversky.detach(),
            "pathology_focal_loss": pathology_focal.detach(),
            "consistency_loss": consistency.detach(),
            "registration_loss": registration.detach(),
            "inclusiveness_loss": inclusiveness.detach(),
            "t2_edema_loss": t2_edema.detach(),
            "edema_gdice_loss": edema_gdice.detach(),
            "cine_anatomy_loss": cine_anatomy.detach(),
            "cine_consistency_loss": cine_consistency.detach(),
            "cine_motion_loss": cine_motion.detach(),
            "cine_smooth_loss": cine_smooth.detach(),
        }


# ---------------------------------------------------------------------------
# Edema loss classes (from MyoPS-edema)
# ---------------------------------------------------------------------------

class EdemaBinaryDiceLoss(nn.Module):
    def forward(self, predict, target):
        predict = predict.contiguous().view(predict.shape[0], -1)
        target = target.contiguous().view(target.shape[0], -1)
        num = (predict * target).sum(1)
        den = predict.sum(1) + target.sum(1)
        loss = 1 - (2 * num + 1e-10) / (den + 1e-10)
        return loss.mean()


class EdemaDiceLoss(nn.Module):
    def forward(self, predict, target):
        dice = EdemaBinaryDiceLoss()
        total_loss = 0
        for i in range(target.shape[1]):
            total_loss += dice(predict[:, i], target[:, i])
        return total_loss / target.shape[1]


class EdemaWCELoss(nn.Module):
    def weight_function(self, target):
        mask = torch.argmax(target, dim=1)
        voxels_sum = mask.shape[0] * mask.shape[1] * mask.shape[2]
        weights = []
        for i in range(int(mask.max()) + 1):
            voxels_i = (mask == i).sum().float().clamp_min(1)
            w_i = torch.log(voxels_sum / voxels_i)
            weights.append(w_i)
        return torch.stack(weights).to(target.device)

    def forward(self, predict, target):
        ce_loss = torch.mean(-target * torch.log(predict + 1e-10), dim=(0, 2, 3))
        weights = self.weight_function(target)
        n = min(len(weights), len(ce_loss))
        loss = weights[:n] * ce_loss[:n]
        return loss.sum()


class EdemaLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.dice_loss = EdemaDiceLoss()
        self.wce_loss = EdemaWCELoss()

    def forward(self, predict, target):
        return self.dice_loss(predict, target) + self.wce_loss(predict, target)
