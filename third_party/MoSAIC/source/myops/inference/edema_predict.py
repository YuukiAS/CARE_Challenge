"""EdemaNet inference: independent argmax prediction + label-level merge."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
from scipy.ndimage import binary_dilation

from myops.models.edema_net import EdemaNet


def load_edema_model(checkpoint_path: str, device: torch.device) -> EdemaNet:
    model = EdemaNet(use_c0=True, deep_supervision=True)
    ckpt = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    model = model.to(device)
    model.eval()
    return model


def _center_crop_or_pad(arr: np.ndarray, target_size: list[int]) -> np.ndarray:
    h, w = arr.shape[-2:]
    th, tw = target_size
    out = np.zeros(arr.shape[:-2] + (th, tw), dtype=arr.dtype)
    sh = max(0, (h - th) // 2)
    sw = max(0, (w - tw) // 2)
    dh = max(0, (th - h) // 2)
    dw = max(0, (tw - w) // 2)
    copy_h = min(h, th)
    copy_w = min(w, tw)
    out[..., dh:dh + copy_h, dw:dw + copy_w] = arr[..., sh:sh + copy_h, sw:sw + copy_w]
    return out


def _uncrop(arr: np.ndarray, original_hw: tuple[int, int], target_size: list[int]) -> np.ndarray:
    h, w = original_hw
    th, tw = target_size
    out = np.zeros(arr.shape[:-2] + (h, w), dtype=arr.dtype)
    sh = max(0, (th - h) // 2)
    sw = max(0, (tw - w) // 2)
    dh = max(0, (h - th) // 2)
    dw = max(0, (w - tw) // 2)
    copy_h = min(h, th)
    copy_w = min(w, tw)
    out[..., dh:dh + copy_h, dw:dw + copy_w] = arr[..., sh:sh + copy_h, sw:sw + copy_w]
    return out


def _predict_slice(model, lge, c0, t2, mask, device, dim):
    """Run model on a single slice, return 3-class softmax probs [3, H, W] in original space."""
    H, W = lge.shape
    lge_c = _center_crop_or_pad(lge, [dim, dim])
    c0_c = _center_crop_or_pad(c0, [dim, dim])
    t2_c = _center_crop_or_pad(t2, [dim, dim])
    mask_c = _center_crop_or_pad(mask, [dim, dim])

    lge_t = torch.from_numpy(lge_c[None, None]).float().to(device)
    c0_t = torch.from_numpy(c0_c[None, None]).float().to(device)
    t2_t = torch.from_numpy(t2_c[None, None]).float().to(device)
    mask_t = torch.from_numpy(mask_c[None, None]).float().to(device)

    output = model(lge_t, c0_t, t2_t, mask_t)
    if isinstance(output, tuple):
        output = output[0]
    probs = output.cpu().numpy()[0]  # [3, dim, dim] — already softmax'd by model

    probs_full = np.zeros((3, H, W), dtype=np.float32)
    for c in range(3):
        probs_full[c] = _uncrop(probs[c], (H, W), [dim, dim])
    return probs_full


def predict_edema_case_argmax(
    model: EdemaNet, payload: dict, coarse_prior: np.ndarray,
    device: torch.device, dim: int = 192,
) -> np.ndarray:
    """Run EdemaNet with TTA and return binary edema zone mask (argmax == 2)."""
    image = np.asarray(payload["image"], dtype=np.float32)  # [3, D, H, W]
    num_slices = image.shape[1]
    H, W = image.shape[2], image.shape[3]

    cardiac_mask_raw = (coarse_prior > 0)
    cardiac_mask = binary_dilation(cardiac_mask_raw, iterations=3).astype(np.float32)

    # Accumulate 3-class probs with TTA (original + h-flip + v-flip)
    probs_sum = np.zeros((3, num_slices, H, W), dtype=np.float32)

    with torch.no_grad():
        for z in range(num_slices):
            lge = image[0, z]
            c0 = image[1, z]
            t2 = image[2, z]
            mask = cardiac_mask[z]

            # Original
            p = _predict_slice(model, lge, c0, t2, mask, device, dim)
            probs_sum[:, z] += p

            # H-flip
            p_h = _predict_slice(
                model,
                np.flip(lge, axis=-1).copy(),
                np.flip(c0, axis=-1).copy(),
                np.flip(t2, axis=-1).copy(),
                np.flip(mask, axis=-1).copy(),
                device, dim,
            )
            probs_sum[:, z] += np.flip(p_h, axis=-1)

            # V-flip
            p_v = _predict_slice(
                model,
                np.flip(lge, axis=-2).copy(),
                np.flip(c0, axis=-2).copy(),
                np.flip(t2, axis=-2).copy(),
                np.flip(mask, axis=-2).copy(),
                device, dim,
            )
            probs_sum[:, z] += np.flip(p_v, axis=-2)

    probs_avg = probs_sum / 3.0  # [3, D, H, W]

    # Argmax: class 2 = edema zone (includes scar region)
    pred_class = np.argmax(probs_avg, axis=0)  # [D, H, W]
    edema_zone = (pred_class == 2)

    return edema_zone


def predict_edema_case_probs(
    model: EdemaNet, payload: dict, coarse_prior: np.ndarray,
    device: torch.device, dim: int = 192,
) -> np.ndarray:
    """Run EdemaNet with TTA and return edema zone probability map [D, H, W]."""
    image = np.asarray(payload["image"], dtype=np.float32)
    num_slices = image.shape[1]
    H, W = image.shape[2], image.shape[3]

    cardiac_mask_raw = (coarse_prior > 0)
    cardiac_mask = binary_dilation(cardiac_mask_raw, iterations=3).astype(np.float32)

    probs_sum = np.zeros((3, num_slices, H, W), dtype=np.float32)

    with torch.no_grad():
        for z in range(num_slices):
            lge = image[0, z]
            c0 = image[1, z]
            t2 = image[2, z]
            mask = cardiac_mask[z]

            p = _predict_slice(model, lge, c0, t2, mask, device, dim)
            probs_sum[:, z] += p

            p_h = _predict_slice(
                model,
                np.flip(lge, axis=-1).copy(),
                np.flip(c0, axis=-1).copy(),
                np.flip(t2, axis=-1).copy(),
                np.flip(mask, axis=-1).copy(),
                device, dim,
            )
            probs_sum[:, z] += np.flip(p_h, axis=-1)

            p_v = _predict_slice(
                model,
                np.flip(lge, axis=-2).copy(),
                np.flip(c0, axis=-2).copy(),
                np.flip(t2, axis=-2).copy(),
                np.flip(mask, axis=-2).copy(),
                device, dim,
            )
            probs_sum[:, z] += np.flip(p_v, axis=-2)

    probs_avg = probs_sum / 3.0
    return probs_avg[2]  # edema zone probability [D, H, W]


def merge_labels(
    ucf_fine_label: np.ndarray,
    coarse_label: np.ndarray,
    edema_zone: np.ndarray,
) -> np.ndarray:
    """Merge coarse anatomy + UCF scar + EdemaNet edema zone.

    coarse_label: 0=bg, 1=ring_myo, 2=lv, 3=rv (from coarse model)
    ucf_fine_label: 0=bg, 1=myo, 2=lv, 3=rv, 4=edema(unreliable), 5=scar
    edema_zone: binary mask from EdemaNet (class 2 = full edema zone incl. scar)

    Output: 0=bg, 1=myo, 2=lv, 3=rv, 4=edema(from EdemaNet), 5=scar(from UCF)
    """
    final = np.zeros_like(ucf_fine_label)

    # Anatomy from coarse
    final[coarse_label == 1] = 1  # myo
    final[coarse_label == 2] = 2  # lv
    final[coarse_label == 3] = 3  # rv

    # Override with UCF fine anatomy
    fine_anatomy = (ucf_fine_label >= 1) & (ucf_fine_label <= 3)
    final[fine_anatomy] = ucf_fine_label[fine_anatomy]

    # Edema from EdemaNet (zone minus scar)
    ucf_scar = (ucf_fine_label == 5)
    pure_edema = edema_zone & ~ucf_scar
    final[pure_edema] = 4  # edema

    # Scar from UCF (highest priority)
    final[ucf_scar] = 5  # scar

    return final
