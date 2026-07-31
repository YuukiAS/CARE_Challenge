#!/usr/bin/env python3
"""Loss and set matching for CARE-QIF v2 scar component queries."""

from __future__ import annotations

from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from scipy.optimize import linear_sum_assignment

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import connected_components_26


def dice_loss_from_logits(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    prob = torch.sigmoid(logits)
    target = target.float()
    inter = (prob * target).sum(dim=(-3, -2, -1))
    den = prob.sum(dim=(-3, -2, -1)) + target.sum(dim=(-3, -2, -1))
    return (1.0 - (2.0 * inter + 1.0) / (den + 1.0)).mean()


def focal_loss_from_logits(logits: torch.Tensor, target: torch.Tensor, alpha: float = 0.25, gamma: float = 2.0) -> torch.Tensor:
    target = target.float()
    bce = F.binary_cross_entropy_with_logits(logits, target, reduction="none")
    prob = torch.sigmoid(logits)
    p_t = prob * target + (1.0 - prob) * (1.0 - target)
    alpha_t = alpha * target + (1.0 - alpha) * (1.0 - target)
    return (alpha_t * (1.0 - p_t).pow(gamma) * bce).mean()


def dense_loss(logits: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    return dice_loss_from_logits(logits, target) + focal_loss_from_logits(logits, target)


@dataclass
class ComponentTargets:
    masks: torch.Tensor
    centers: torch.Tensor
    count: int


def component_targets(target: torch.Tensor) -> ComponentTargets:
    arr = target.detach().cpu().numpy().astype(bool)
    if arr.ndim == 5:
        arr = arr[0, 0]
    elif arr.ndim == 4:
        arr = arr[0]
    lab, count = connected_components_26(arr)
    masks = []
    centers = []
    shape = np.asarray(arr.shape, dtype=np.float32)
    for idx in range(1, count + 1):
        mask = lab == idx
        coords = np.argwhere(mask)
        masks.append(torch.from_numpy(mask.astype(np.float32)))
        centers.append(torch.from_numpy((coords.mean(axis=0) / np.maximum(shape - 1.0, 1.0)).astype(np.float32)))
    if not masks:
        return ComponentTargets(torch.zeros((0, *arr.shape), dtype=torch.float32), torch.zeros((0, 3), dtype=torch.float32), 0)
    return ComponentTargets(torch.stack(masks, dim=0), torch.stack(centers, dim=0), count)


class ScarSetMatcher:
    def __init__(self, cost_dice: float = 2.0, cost_focal: float = 2.0, cost_center: float = 1.0, cost_class: float = 1.0) -> None:
        self.cost_dice = float(cost_dice)
        self.cost_focal = float(cost_focal)
        self.cost_center = float(cost_center)
        self.cost_class = float(cost_class)

    def match(self, outputs: dict[str, torch.Tensor], target: torch.Tensor) -> tuple[np.ndarray, np.ndarray, ComponentTargets]:
        comps = component_targets(target)
        q = int(outputs["query_mask_logits"].shape[1])
        if comps.count == 0:
            return np.asarray([], dtype=np.int64), np.asarray([], dtype=np.int64), comps
        pred_masks = outputs["query_mask_logits"][0]
        pred_centers = outputs["query_centers"][0]
        class_logits = outputs["class_logits"][0]
        target_masks = comps.masks.to(pred_masks.device)
        target_centers = comps.centers.to(pred_centers.device)
        logits_flat = pred_masks.flatten(1)
        target_flat = target_masks.flatten(1)
        prob_flat = torch.sigmoid(logits_flat)
        inter = prob_flat @ target_flat.t()
        den = prob_flat.sum(dim=1, keepdim=True) + target_flat.sum(dim=1).view(1, -1)
        dice_t = 1.0 - (2.0 * inter + 1.0) / (den + 1.0)
        pos_term = 0.25 * (1.0 - prob_flat).pow(2.0) * F.softplus(-logits_flat)
        neg_term = 0.75 * prob_flat.pow(2.0) * F.softplus(logits_flat)
        pos_sum = pos_term @ target_flat.t()
        neg_sum = neg_term.sum(dim=1, keepdim=True) - (neg_term @ target_flat.t())
        focal_t = (pos_sum + neg_sum) / float(target_flat.shape[1])
        center_t = torch.cdist(pred_centers, target_centers, p=1)
        class_t = -F.log_softmax(class_logits, dim=-1)[:, 1].view(-1, 1)
        costs = self.cost_dice * dice_t + self.cost_focal * focal_t + self.cost_center * center_t + self.cost_class * class_t
        qi, cj = linear_sum_assignment(costs.detach().cpu().numpy())
        return qi.astype(np.int64), cj.astype(np.int64), comps


class ScarComponentQueryLoss:
    def __init__(self) -> None:
        self.matcher = ScarSetMatcher()

    def __call__(self, outputs: dict[str, torch.Tensor], batch: dict[str, torch.Tensor]) -> tuple[torch.Tensor, dict[str, Any]]:
        target = batch["scar_target"].float()
        loss_dense = dense_loss(outputs["dense_logit"], target)
        qi, cj, comps = self.matcher.match(outputs, target)
        class_target = torch.zeros((outputs["class_logits"].shape[1],), dtype=torch.long, device=outputs["class_logits"].device)
        loss_mask = torch.zeros((), dtype=loss_dense.dtype, device=loss_dense.device)
        loss_center = torch.zeros((), dtype=loss_dense.dtype, device=loss_dense.device)
        if len(qi):
            class_target[torch.as_tensor(qi, device=class_target.device)] = 1
            tgt_masks = comps.masks.to(outputs["query_mask_logits"].device)[torch.as_tensor(cj, device=class_target.device)]
            pred_masks = outputs["query_mask_logits"][0, torch.as_tensor(qi, device=class_target.device)]
            loss_mask = dice_loss_from_logits(pred_masks, tgt_masks) + focal_loss_from_logits(pred_masks, tgt_masks)
            tgt_centers = comps.centers.to(outputs["query_centers"].device)[torch.as_tensor(cj, device=class_target.device)]
            loss_center = F.l1_loss(outputs["query_centers"][0, torch.as_tensor(qi, device=class_target.device)], tgt_centers)
        weights = torch.tensor([0.2, 1.0], device=outputs["class_logits"].device, dtype=outputs["class_logits"].dtype)
        loss_class = F.cross_entropy(outputs["class_logits"][0], class_target, weight=weights)
        total = loss_dense + loss_mask + 0.5 * loss_center + loss_class
        return total, {
            "loss_dense": float(loss_dense.detach().cpu()),
            "loss_query_mask": float(loss_mask.detach().cpu()),
            "loss_center": float(loss_center.detach().cpu()),
            "loss_class": float(loss_class.detach().cpu()),
            "matched_queries": int(len(qi)),
            "unmatched_queries": int(outputs["class_logits"].shape[1] - len(qi)),
            "no_object_loss_nonzero": bool(float(loss_class.detach().cpu()) > 0),
        }
