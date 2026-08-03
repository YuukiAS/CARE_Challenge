"""Canonical CARE-ASE R2 full-volume inference.

All CARE-ASE full-volume consumers must use this module so single-tile and
tiled inference share the same extent semantics.
"""

from __future__ import annotations

from typing import Any

import torch
import torch.nn.functional as F

from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.models.care_ase import compute_slice_extent_statistics


def starts_for(dim: int, patch: int, overlap: float = 0.5) -> list[int]:
    if dim <= patch:
        return [0]
    stride = max(1, int(patch * (1.0 - overlap)))
    values = list(range(0, max(dim - patch, 0) + 1, stride))
    if not values or values[-1] != dim - patch:
        values.append(dim - patch)
    return values


def _pad_patch_to_size(patch: torch.Tensor, patch_size: tuple[int, int, int]) -> tuple[torch.Tensor, tuple[int, int, int]]:
    actual = tuple(int(v) for v in patch.shape[-3:])
    pads: list[int] = []
    for have, want in reversed(list(zip(actual, patch_size))):
        pads.extend([0, max(int(want) - int(have), 0)])
    if any(pads):
        patch = F.pad(patch, pads)
    return patch, actual


def _aggregate_patch_tensor(accum: torch.Tensor, count: torch.Tensor, value: torch.Tensor, z: int, y: int, x: int, actual: tuple[int, int, int]) -> None:
    value = value[..., : actual[0], : actual[1], : actual[2]]
    accum[..., z : z + actual[0], y : y + actual[1], x : x + actual[2]] += value
    count[..., z : z + actual[0], y : y + actual[1], x : x + actual[2]] += 1.0


def global_extent_bias(
    model: torch.nn.Module,
    components: dict[str, torch.Tensor],
    p_wall: torch.Tensor,
    *,
    pathology: str,
    global_step: int = 14000,
    valid_spatial_mask: torch.Tensor | None = None,
) -> torch.Tensor:
    if valid_spatial_mask is None:
        valid_down = torch.ones_like(p_wall[:, :1])
    else:
        valid_down = F.interpolate(valid_spatial_mask.detach().float(), size=p_wall.shape[-3:], mode="nearest").clamp(0.0, 1.0)
    if pathology == "scar":
        presence, area, _wall_slice, _fallback = compute_slice_extent_statistics(
            components["scar_extent_presence"],
            components["scar_extent_area"],
            p_wall,
            valid_down,
        )
        area_reference = model.scar_area_reference
        presence_coef, area_coef, wall_coef = 0.30, 0.20, 0.15
    elif pathology == "edema":
        presence, area, _wall_slice, _fallback = compute_slice_extent_statistics(
            components["edema_extent_presence"],
            components["edema_extent_area"],
            p_wall,
            valid_down,
        )
        area_reference = model.edema_area_reference
        presence_coef, area_coef, wall_coef = 0.35, 0.30, 0.10
    else:
        raise ValueError(f"unknown pathology: {pathology}")
    valid_slice = (valid_down.sum(dim=(-2, -1), keepdim=True) > 0).to(dtype=p_wall.dtype)
    presence_bias = presence_coef * model._sigmoid_logit_center(presence, 0.50) * valid_slice
    area_bias = area_coef * model._sigmoid_logit_center(area, area_reference) * valid_slice
    slice_valid = F.interpolate(valid_slice, size=p_wall.shape[-3:], mode="nearest")
    slice_bias = F.interpolate(presence_bias + area_bias, size=p_wall.shape[-3:], mode="trilinear", align_corners=False) * slice_valid
    wall_bias = wall_coef * model._sigmoid_logit_center(p_wall.detach(), 0.50) * slice_valid
    return float(model.extent_wall_ramp(global_step)) * (slice_bias + wall_bias)


def predict_care_ase_r2_full_volume_logits(
    model: torch.nn.Module,
    image: torch.Tensor,
    availability: torch.Tensor,
    *,
    patch_size: tuple[int, int, int] = (20, 256, 256),
    overlap: float = 0.5,
    global_step: int = 14000,
) -> torch.Tensor:
    was_training = model.training
    model.eval()
    spatial = tuple(int(v) for v in image.shape[-3:])
    starts = [starts_for(dim, size, overlap) for dim, size in zip(spatial, patch_size)]
    base = image.new_zeros((image.shape[0], 6, *spatial))
    p_wall = image.new_zeros((image.shape[0], 1, *spatial))
    component_accums = {
        "scar_extent_presence": image.new_zeros((image.shape[0], 1, *spatial)),
        "scar_extent_area": image.new_zeros((image.shape[0], 1, *spatial)),
        "edema_extent_presence": image.new_zeros((image.shape[0], 1, *spatial)),
        "edema_extent_area": image.new_zeros((image.shape[0], 1, *spatial)),
    }
    count = image.new_zeros((image.shape[0], 1, *spatial))
    valid_support = image.new_zeros((image.shape[0], 1, *spatial))
    with torch.no_grad():
        with torch.autocast(device_type=image.device.type, enabled=False):
            fp32_image = image.float()
            for z in starts[0]:
                for y in starts[1]:
                    for x in starts[2]:
                        patch = fp32_image[..., z : z + patch_size[0], y : y + patch_size[1], x : x + patch_size[2]]
                        patch_padded, actual = _pad_patch_to_size(patch, patch_size)
                        outputs = model(patch_padded, availability, global_step=global_step, disable_extent_wall=True)
                        _aggregate_patch_tensor(base, count, outputs["final_logits"].float(), z, y, x, actual)
                        _aggregate_patch_tensor(p_wall, count.new_zeros(count.shape), outputs["p_wall_union"].float(), z, y, x, actual)
                        valid_patch = count.new_ones((image.shape[0], 1, *patch_size))
                        _aggregate_patch_tensor(valid_support, count.new_zeros(count.shape), valid_patch, z, y, x, actual)
                        components = outputs["components"]
                        for key, target in component_accums.items():
                            up = F.interpolate(components[key].float(), size=patch_size, mode="trilinear", align_corners=False)
                            _aggregate_patch_tensor(target, count.new_zeros(count.shape), up, z, y, x, actual)
                        count[..., z : z + actual[0], y : y + actual[1], x : x + actual[2]] += 1.0
            averaged_base = base / count.clamp_min(1.0)
            averaged_p_wall = p_wall / count.clamp_min(1.0)
            averaged_components = {key: value / count.clamp_min(1.0) for key, value in component_accums.items()}
            valid_support = valid_support.clamp(0.0, 1.0)
            averaged_base[:, 5:6] = averaged_base[:, 5:6] + global_extent_bias(
                model,
                averaged_components,
                averaged_p_wall,
                pathology="scar",
                global_step=global_step,
                valid_spatial_mask=valid_support,
            )
            if bool((availability[:, 1] > 0.5).any()):
                averaged_base[:, 4:5] = averaged_base[:, 4:5] + global_extent_bias(
                    model,
                    averaged_components,
                    averaged_p_wall,
                    pathology="edema",
                    global_step=global_step,
                    valid_spatial_mask=valid_support,
                )
    if was_training:
        model.train()
    return averaged_base


def predict_care_ase_r2_full_volume_labels(
    model: torch.nn.Module,
    image: torch.Tensor,
    availability: torch.Tensor,
    *,
    patch_size: tuple[int, int, int] = (20, 256, 256),
    overlap: float = 0.5,
    global_step: int = 14000,
) -> torch.Tensor:
    logits = predict_care_ase_r2_full_volume_logits(
        model,
        image,
        availability,
        patch_size=patch_size,
        overlap=overlap,
        global_step=global_step,
    )
    return decode_care_ase_r2_logits(logits, availability)
