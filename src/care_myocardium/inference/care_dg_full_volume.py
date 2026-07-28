"""GT-free CARE-DG full-volume inference helpers."""

from __future__ import annotations

import numpy as np
import torch
from torch.amp import autocast

from scripts.training.run_care_dg import PATCH_SHAPE
from src.care_myocardium.models.care_dg import ANATOMY_CHANNELS, EDEMA_CHANNEL, SCAR_CHANNEL


def starts_for(dim: int, patch: int, overlap: float = 0.5) -> list[int]:
    if dim <= patch:
        return [0]
    stride = max(1, int(round(float(patch) * (1.0 - float(overlap)))))
    starts = list(range(0, max(1, dim - patch + 1), stride))
    last = dim - patch
    if starts[-1] != last:
        starts.append(last)
    return starts


def extract_start(
    arr: np.ndarray,
    start: tuple[int, int, int],
    shape: tuple[int, int, int],
    fill: float,
) -> tuple[np.ndarray, tuple[slice, slice, slice], tuple[slice, slice, slice]]:
    spatial = arr.shape[-3:]
    src: list[slice] = []
    dst: list[slice] = []
    for start_i, size_i, dim_i in zip(start, shape, spatial):
        end_i = min(dim_i, int(start_i) + int(size_i))
        src.append(slice(int(start_i), end_i))
        dst.append(slice(0, max(0, end_i - int(start_i))))
    out = np.full(arr.shape[:-3] + tuple(shape), fill, dtype=arr.dtype)
    out[(..., *dst)] = arr[(..., *src)]
    return out, tuple(src), tuple(dst)


def gaussian_importance(shape: tuple[int, int, int]) -> np.ndarray:
    axes = []
    for size in shape:
        if size <= 1:
            axes.append(np.ones((size,), dtype=np.float32))
            continue
        coord = np.arange(size, dtype=np.float32)
        center = (float(size) - 1.0) / 2.0
        sigma = max(float(size) / 8.0, 1.0)
        vals = np.exp(-0.5 * ((coord - center) / sigma) ** 2).astype(np.float32)
        axes.append(np.maximum(vals / float(vals.max()), 1e-3))
    return (axes[0][:, None, None] * axes[1][None, :, None] * axes[2][None, None, :]).astype(np.float32)


def _scatter_subtract(logits: np.ndarray, competitor: np.ndarray, correction: np.ndarray) -> None:
    for channel in range(logits.shape[0]):
        mask = competitor == channel
        if np.any(mask):
            logits[channel][mask] -= correction[mask]


def compose_scar_priority_numpy(
    anchor_logits: np.ndarray,
    scar_delta: np.ndarray,
    edema_delta: np.ndarray,
    *,
    scar_margin_cap: float,
    edema_margin_cap: float,
    direct_residual: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    anchor = anchor_logits.astype(np.float32, copy=False)
    scar = np.clip(np.asarray(scar_delta, dtype=np.float32).reshape(anchor.shape[-3:]), -float(scar_margin_cap), float(scar_margin_cap))
    edema = np.clip(np.asarray(edema_delta, dtype=np.float32).reshape(anchor.shape[-3:]), -float(edema_margin_cap), float(edema_margin_cap))
    if direct_residual:
        final = anchor.copy()
        final[EDEMA_CHANNEL] += edema
        final[SCAR_CHANNEL] += scar
        return final.copy(), final

    after_edema = anchor.copy()
    anatomy = anchor[list(ANATOMY_CHANNELS)]
    edema_competitor = np.asarray(ANATOMY_CHANNELS, dtype=np.int16)[np.argmax(anatomy, axis=0)]
    after_edema[EDEMA_CHANNEL] += edema
    _scatter_subtract(after_edema, edema_competitor, edema)

    final = after_edema.copy()
    non_scar_channels = [c for c in range(anchor.shape[0]) if c != SCAR_CHANNEL]
    scar_competitor = np.asarray(non_scar_channels, dtype=np.int16)[np.argmax(after_edema[non_scar_channels], axis=0)]
    final[SCAR_CHANNEL] += scar
    _scatter_subtract(final, scar_competitor, scar)
    return after_edema, final


def full_volume_predict(
    model: torch.nn.Module,
    record: dict[str, np.ndarray],
    availability: tuple[float, float, float],
    t2_present: bool,
    device: torch.device,
    batch_size: int,
    *,
    overlap: float = 0.5,
    gaussian: bool = True,
    direct_residual: bool = False,
) -> dict[str, np.ndarray]:
    del batch_size
    spatial = tuple(int(v) for v in record["anchor_logits"].shape[-3:])
    scar_delta = np.zeros((1, *spatial), dtype=np.float32)
    edema_delta = np.zeros((1, *spatial), dtype=np.float32)
    weight = np.zeros(spatial, dtype=np.float32)
    importance = gaussian_importance(PATCH_SHAPE) if gaussian else np.ones(PATCH_SHAPE, dtype=np.float32)
    patch_specs = [
        (z, y, x)
        for z in starts_for(spatial[0], PATCH_SHAPE[0], overlap)
        for y in starts_for(spatial[1], PATCH_SHAPE[1], overlap)
        for x in starts_for(spatial[2], PATCH_SHAPE[2], overlap)
    ]
    model.eval()
    with torch.inference_mode():
        for start in patch_specs:
            patches: dict[str, np.ndarray] = {}
            src: tuple[slice, slice, slice] | None = None
            dst: tuple[slice, slice, slice] | None = None
            for key, fill in (
                ("images", 0.0),
                ("anchor_logits", -12.0),
                ("uncertainty", 1.0),
                ("myocardium_support", 0.0),
                ("edema_support", 0.0),
                ("distance_to_myocardium", 99.0),
            ):
                patches[key], src, dst = extract_start(record[key], start, PATCH_SHAPE, fill)
            assert src is not None and dst is not None
            batch = {
                "images": torch.from_numpy(patches["images"][None]).float().to(device),
                "anchor_logits": torch.from_numpy(patches["anchor_logits"][None]).float().to(device),
                "availability": torch.tensor([availability], dtype=torch.float32, device=device),
                "uncertainty": torch.from_numpy(patches["uncertainty"][None]).float().to(device),
                "myocardium_support": torch.from_numpy(patches["myocardium_support"][None]).float().to(device),
                "edema_support": torch.from_numpy(patches["edema_support"][None]).float().to(device),
                "distance_to_myocardium": torch.from_numpy(patches["distance_to_myocardium"][None]).float().to(device),
                "t2_present": torch.tensor([1.0 if t2_present else 0.0], dtype=torch.float32, device=device),
            }
            with autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                out = model(
                    batch["images"],
                    batch["availability"],
                    batch["anchor_logits"],
                    uncertainty=batch["uncertainty"],
                    myocardium_support=batch["myocardium_support"],
                    edema_support=batch["edema_support"],
                    distance_to_myocardium=batch["distance_to_myocardium"],
                    t2_present=batch["t2_present"],
                    strict_inputs=True,
                    anchor_value_kind="log_probabilities",
                )
            patch_weight = importance[dst].astype(np.float32, copy=False)
            scar_arr = out["scar_delta"][0].detach().float().cpu().numpy()
            edema_arr = out["edema_delta"][0].detach().float().cpu().numpy()
            scar_delta[(..., *src)] += scar_arr[(..., *dst)] * patch_weight[None]
            edema_delta[(..., *src)] += edema_arr[(..., *dst)] * patch_weight[None]
            weight[src] += patch_weight

    safe_weight = np.maximum(weight, 1.0)[None]
    scar_delta = scar_delta / safe_weight
    edema_delta = edema_delta / safe_weight
    after_edema_logits, final_logits = compose_scar_priority_numpy(
        record["anchor_logits"],
        scar_delta,
        edema_delta,
        scar_margin_cap=float(getattr(model.config, "scar_margin_cap", 8.0)),
        edema_margin_cap=float(getattr(model.config, "edema_margin_cap", 8.0)),
        direct_residual=direct_residual,
    )
    return {
        "final_logits": final_logits,
        "after_edema_logits": after_edema_logits,
        "final_mask": final_logits.argmax(axis=0).astype(np.uint8),
        "after_edema_mask": after_edema_logits.argmax(axis=0).astype(np.uint8),
        "scar_delta": scar_delta,
        "edema_delta": edema_delta,
        "patch_count": len(patch_specs),
        "patch_starts": patch_specs,
        "overlap": float(overlap),
        "gaussian_blending": bool(gaussian),
        "composition": "full_anchor_once_after_delta_aggregation",
    }
