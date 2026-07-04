"""Prototype-bank utilities for MyoPS pathology proposals."""

from __future__ import annotations

from dataclasses import dataclass, field

import torch
import torch.nn.functional as F


SCAR_CLASS = 5
EDEMA_CLASS = 4
MYOCARDIUM_CLASS = 1
BLOOD_CLASSES = (2, 3)
ANATOMY_CLASSES = (1, 2, 3, 4, 5)


SCAR_NEGATIVE_CATEGORIES = (
    "normal_myocardium",
    "blood_pool",
    "outside_myocardium",
    "hard_fp",
    "artifact",
)
EDEMA_NEGATIVE_CATEGORIES = (
    "t2_present_normal_myocardium_far_from_edema",
    "t2_present_blood_pool",
    "t2_present_outside_myocardium",
    "t2_present_hard_fp",
    "t2_present_artifact",
)


@dataclass
class PrototypeBank:
    """Fixed-size prototype tensors plus extraction provenance."""

    scar_positive: torch.Tensor
    scar_negative: torch.Tensor
    edema_positive: torch.Tensor
    edema_negative: torch.Tensor
    counts: dict[str, int]
    source: str
    hard_negative_counts: dict[str, int] = field(default_factory=dict)
    category_counts: dict[str, int] = field(default_factory=dict)


def deterministic_axis_prototypes(count: int, channels: int, *, offset: int = 0) -> torch.Tensor:
    """Return deterministic, non-random fallback vectors for unfit modules."""

    out = torch.zeros(int(count), int(channels), dtype=torch.float32)
    if count <= 0 or channels <= 0:
        return out
    for idx in range(int(count)):
        out[idx, (idx + int(offset)) % int(channels)] = 1.0
    return F.normalize(out, dim=1)


def _ensure_batched_labels(labels: torch.Tensor) -> torch.Tensor:
    if labels.ndim == 5 and labels.shape[1] == 1:
        return labels[:, 0]
    if labels.ndim == 4:
        return labels
    raise ValueError(f"expected labels shape (B,D,H,W) or (B,1,D,H,W), got {tuple(labels.shape)}")


def _resize_mask(mask: torch.Tensor, spatial: tuple[int, int, int]) -> torch.Tensor:
    mask_f = mask.to(dtype=torch.float32)
    if mask_f.shape[-3:] == spatial:
        return mask_f > 0.5
    resized = F.interpolate(mask_f[:, None], size=spatial, mode="nearest")[:, 0]
    return resized > 0.5


def _category_means(features: torch.Tensor, masks: list[tuple[str, torch.Tensor]]) -> tuple[list[torch.Tensor], dict[str, int]]:
    vectors: list[torch.Tensor] = []
    counts: dict[str, int] = {}
    for category, mask in masks:
        mask = _resize_mask(mask, features.shape[-3:]).to(device=features.device)
        count = int(mask.sum().item())
        counts[category] = counts.get(category, 0) + count
        if count <= 0:
            continue
        for batch_idx in range(features.shape[0]):
            sample_mask = mask[batch_idx]
            if bool(sample_mask.any().item()):
                sample_vectors = features[batch_idx, :, sample_mask]
                vectors.append(sample_vectors.mean(dim=1))
    return vectors, counts


def _fit_tensor(vectors: list[torch.Tensor], count: int, channels: int, *, offset: int) -> torch.Tensor:
    if not vectors:
        return deterministic_axis_prototypes(count, channels, offset=offset)
    stacked = torch.stack([v.detach().to(dtype=torch.float32).cpu() for v in vectors], dim=0)
    if stacked.shape[0] >= count:
        fitted = stacked[:count]
    else:
        pad = stacked[-1:].repeat(count - stacked.shape[0], 1)
        fitted = torch.cat([stacked, pad], dim=0)
    return F.normalize(fitted, dim=1)


def _dilated(mask: torch.Tensor, radius: int = 2) -> torch.Tensor:
    if not bool(mask.any().item()):
        return mask
    kernel = 2 * int(radius) + 1
    pooled = F.max_pool3d(mask[:, None].float(), kernel_size=kernel, stride=1, padding=radius)
    return pooled[:, 0] > 0.5


def _anchor_prob(anchor: torch.Tensor | None, channel: int, spatial: tuple[int, int, int]) -> torch.Tensor | None:
    if anchor is None or anchor.ndim != 5 or anchor.shape[1] <= channel:
        return None
    value = anchor[:, channel : channel + 1].float()
    if value.shape[-3:] != spatial:
        value = F.interpolate(value, size=spatial, mode="trilinear", align_corners=False)
    return value[:, 0]


def build_prototype_bank_from_labeled_features(
    *,
    scar_features: torch.Tensor,
    edema_features: torch.Tensor,
    labels: torch.Tensor,
    availability: torch.Tensor,
    anchor_probabilities: torch.Tensor | None = None,
    scar_positive_count: int = 6,
    scar_negative_count: int = 8,
    edema_positive_count: int = 6,
    edema_negative_count: int = 8,
    source: str = "labeled_train_or_oof_feature_tensors",
) -> PrototypeBank:
    """Extract leakage-safe pathology prototypes from labeled train/OOF tensors.

    Edema positive and safe-negative masks are restricted to T2-present samples.
    No-T2 myocardium is deliberately excluded from every edema negative mask.
    """

    if scar_features.shape != edema_features.shape:
        raise ValueError("scar_features and edema_features must have the same shape")
    if scar_features.ndim != 5:
        raise ValueError(f"expected feature shape (B,C,D,H,W), got {tuple(scar_features.shape)}")
    labels_4d = _ensure_batched_labels(labels).to(device=scar_features.device)
    availability = availability.to(device=scar_features.device, dtype=torch.float32).clamp(0, 1)
    if availability.shape != (scar_features.shape[0], 3):
        raise ValueError(f"expected availability shape (B,3), got {tuple(availability.shape)}")

    labels_for_features = _resize_mask(torch.ones_like(labels_4d, dtype=torch.bool), scar_features.shape[-3:])
    labels_resized = F.interpolate(labels_4d[:, None].float(), size=scar_features.shape[-3:], mode="nearest")[:, 0].long()
    labels_resized = torch.where(labels_for_features, labels_resized, torch.zeros_like(labels_resized))

    anatomy = torch.zeros_like(labels_resized, dtype=torch.bool)
    for cls in ANATOMY_CLASSES:
        anatomy |= labels_resized == int(cls)
    scar_gt = labels_resized == SCAR_CLASS
    edema_gt = labels_resized == EDEMA_CLASS
    normal_myo = labels_resized == MYOCARDIUM_CLASS
    blood = torch.zeros_like(labels_resized, dtype=torch.bool)
    for cls in BLOOD_CLASSES:
        blood |= labels_resized == int(cls)
    outside = ~anatomy

    t2_present = availability[:, 1].view(-1, 1, 1, 1) > 0.5
    edema_far = normal_myo & ~_dilated(edema_gt, radius=2)

    scar_anchor = _anchor_prob(anchor_probabilities, SCAR_CLASS, scar_features.shape[-3:])
    edema_anchor = _anchor_prob(anchor_probabilities, EDEMA_CLASS, scar_features.shape[-3:])
    scar_hard_fp = (scar_anchor > 0.35) & ~scar_gt if scar_anchor is not None else torch.zeros_like(scar_gt)
    edema_hard_fp = (edema_anchor > 0.35) & ~edema_gt if edema_anchor is not None else torch.zeros_like(edema_gt)

    scar_pos_vecs, scar_pos_counts = _category_means(scar_features, [("scar_positive", scar_gt)])
    scar_neg_vecs, scar_neg_counts = _category_means(
        scar_features,
        [
            ("normal_myocardium", normal_myo & ~scar_gt),
            ("blood_pool", blood),
            ("outside_myocardium", outside),
            ("hard_fp", scar_hard_fp),
            ("artifact", scar_hard_fp & outside),
        ],
    )
    edema_pos_vecs, edema_pos_counts = _category_means(edema_features, [("t2_present_edema_positive", edema_gt & t2_present)])
    edema_neg_vecs, edema_neg_counts = _category_means(
        edema_features,
        [
            ("t2_present_normal_myocardium_far_from_edema", edema_far & t2_present),
            ("t2_present_blood_pool", blood & t2_present),
            ("t2_present_outside_myocardium", outside & t2_present),
            ("t2_present_hard_fp", edema_hard_fp & t2_present),
            ("t2_present_artifact", edema_hard_fp & outside & t2_present),
        ],
    )

    channels = int(scar_features.shape[1])
    counts = {
        "scar_positive": len(scar_pos_vecs),
        "scar_negative": len(scar_neg_vecs),
        "edema_positive": len(edema_pos_vecs),
        "edema_negative": len(edema_neg_vecs),
    }
    category_counts = {**scar_pos_counts, **scar_neg_counts, **edema_pos_counts, **edema_neg_counts}
    hard_negative_counts = {
        "scar_hard_fp": int(scar_hard_fp.sum().item()),
        "scar_artifact": int((scar_hard_fp & outside).sum().item()),
        "edema_t2_present_hard_fp": int((edema_hard_fp & t2_present).sum().item()),
        "edema_t2_present_artifact": int((edema_hard_fp & outside & t2_present).sum().item()),
        "edema_no_t2_myocardium_negative_voxels": 0,
    }
    return PrototypeBank(
        scar_positive=_fit_tensor(scar_pos_vecs, scar_positive_count, channels, offset=0),
        scar_negative=_fit_tensor(scar_neg_vecs, scar_negative_count, channels, offset=1),
        edema_positive=_fit_tensor(edema_pos_vecs, edema_positive_count, channels, offset=2),
        edema_negative=_fit_tensor(edema_neg_vecs, edema_negative_count, channels, offset=3),
        counts=counts,
        source=source,
        hard_negative_counts=hard_negative_counts,
        category_counts=category_counts,
    )
