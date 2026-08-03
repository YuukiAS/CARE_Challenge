"""Canonical CARE-ASE R2 full-volume inference.

All CARE-ASE full-volume consumers must use this module so single-tile and
tiled inference share the same extent semantics.
"""

from __future__ import annotations

from itertools import combinations
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


def _aggregate_patch_tensor(accum: torch.Tensor, value: torch.Tensor, z: int, y: int, x: int, actual: tuple[int, int, int]) -> None:
    value = value[..., : actual[0], : actual[1], : actual[2]]
    accum[..., z : z + actual[0], y : y + actual[1], x : x + actual[2]] += value


def gaussian_importance_map(
    patch_size: tuple[int, int, int],
    *,
    sigma_scale: float = 1.0 / 8.0,
    device: torch.device | None = None,
    dtype: torch.dtype = torch.float32,
) -> torch.Tensor:
    axes = []
    for size in patch_size:
        coord = torch.arange(int(size), device=device, dtype=dtype)
        center = (float(size) - 1.0) / 2.0
        sigma = max(float(size) * float(sigma_scale), 1.0e-6)
        axes.append(torch.exp(-0.5 * ((coord - center) / sigma) ** 2))
    weight = axes[0][:, None, None] * axes[1][None, :, None] * axes[2][None, None, :]
    return weight.clamp_min(torch.finfo(dtype).eps)[None, None]


def mirror_axis_combinations(axes: tuple[int, ...]) -> list[tuple[int, ...]]:
    clean = tuple(sorted(set(int(axis) for axis in axes)))
    out: list[tuple[int, ...]] = [()]
    for length in range(1, len(clean) + 1):
        out.extend(tuple(item) for item in combinations(clean, length))
    return out


def _flip_spatial(tensor: torch.Tensor, axes: tuple[int, ...]) -> torch.Tensor:
    if not axes:
        return tensor
    dims = tuple(int(axis) - 3 for axis in axes)
    return torch.flip(tensor, dims=dims)


def _forward_with_mirror_average(
    model: torch.nn.Module,
    patch: torch.Tensor,
    availability: torch.Tensor,
    *,
    global_step: int,
    mirror_axes: tuple[int, ...],
) -> dict[str, Any]:
    combos = mirror_axis_combinations(mirror_axes)
    final_logits = None
    p_wall = None
    components: dict[str, torch.Tensor] = {}
    for axes in combos:
        mirrored_patch = _flip_spatial(patch, axes)
        outputs = model(mirrored_patch, availability, global_step=global_step, disable_extent_wall=True)
        logits = _flip_spatial(outputs["final_logits"].float(), axes)
        wall = _flip_spatial(outputs["p_wall_union"].float(), axes)
        final_logits = logits if final_logits is None else final_logits + logits
        p_wall = wall if p_wall is None else p_wall + wall
        for key in ("scar_extent_presence", "scar_extent_area", "edema_extent_presence", "edema_extent_area"):
            value = _flip_spatial(outputs["components"][key].float(), axes)
            components[key] = value if key not in components else components[key] + value
    denom = float(len(combos))
    return {
        "final_logits": final_logits / denom,
        "p_wall_union": p_wall / denom,
        "components": {key: value / denom for key, value in components.items()},
        "mirror_count": len(combos),
    }


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
    use_gaussian: bool = True,
    gaussian_sigma_scale: float = 1.0 / 8.0,
    use_mirroring: bool = False,
    allowed_mirror_axes: tuple[int, ...] = (),
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
    denominator = image.new_zeros((image.shape[0], 1, *spatial))
    valid_support = image.new_zeros((image.shape[0], 1, *spatial))
    with torch.no_grad():
        with torch.autocast(device_type=image.device.type, enabled=False):
            fp32_image = image.float()
            for z in starts[0]:
                for y in starts[1]:
                    for x in starts[2]:
                        patch = fp32_image[..., z : z + patch_size[0], y : y + patch_size[1], x : x + patch_size[2]]
                        patch_padded, actual = _pad_patch_to_size(patch, patch_size)
                        mirror_axes = tuple(int(axis) for axis in allowed_mirror_axes) if use_mirroring else ()
                        outputs = _forward_with_mirror_average(
                            model,
                            patch_padded,
                            availability,
                            global_step=global_step,
                            mirror_axes=mirror_axes,
                        )
                        weight = (
                            gaussian_importance_map(
                                patch_size,
                                sigma_scale=gaussian_sigma_scale,
                                device=image.device,
                                dtype=torch.float32,
                            )
                            if use_gaussian
                            else image.new_ones((1, 1, *patch_size), dtype=torch.float32)
                        )
                        _aggregate_patch_tensor(base, outputs["final_logits"].float() * weight, z, y, x, actual)
                        _aggregate_patch_tensor(p_wall, outputs["p_wall_union"].float() * weight, z, y, x, actual)
                        valid_patch = denominator.new_ones((image.shape[0], 1, *patch_size))
                        _aggregate_patch_tensor(valid_support, valid_patch, z, y, x, actual)
                        components = outputs["components"]
                        for key, target in component_accums.items():
                            up = F.interpolate(components[key].float(), size=patch_size, mode="trilinear", align_corners=False)
                            _aggregate_patch_tensor(target, up * weight, z, y, x, actual)
                        _aggregate_patch_tensor(denominator, weight, z, y, x, actual)
            averaged_base = base / denominator.clamp_min(torch.finfo(base.dtype).eps)
            averaged_p_wall = p_wall / denominator.clamp_min(torch.finfo(p_wall.dtype).eps)
            averaged_components = {key: value / denominator.clamp_min(torch.finfo(value.dtype).eps) for key, value in component_accums.items()}
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
    use_gaussian: bool = True,
    gaussian_sigma_scale: float = 1.0 / 8.0,
    use_mirroring: bool = False,
    allowed_mirror_axes: tuple[int, ...] = (),
) -> torch.Tensor:
    logits = predict_care_ase_r2_full_volume_logits(
        model,
        image,
        availability,
        patch_size=patch_size,
        overlap=overlap,
        global_step=global_step,
        use_gaussian=use_gaussian,
        gaussian_sigma_scale=gaussian_sigma_scale,
        use_mirroring=use_mirroring,
        allowed_mirror_axes=allowed_mirror_axes,
    )
    return decode_care_ase_r2_logits(logits, availability)
