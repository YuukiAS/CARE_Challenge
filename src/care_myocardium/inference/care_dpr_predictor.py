"""Full-volume aggregation and component arbitration for CARE-DPR."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np
import torch
from scipy import ndimage as ndi

from src.care_myocardium.models.care_dg import EDEMA_CHANNEL, SCAR_CHANNEL

CANDIDATE_TYPES = ("ADD_FN", "REVISE_FP")
LEGAL_ACTIONS = ("KEEP_ANCHOR_LOCAL_MASK", "REPLACE_WITH_REFINED_LOCAL_MASK")
THRESHOLD_CANDIDATES = (0.30, 0.40, 0.50, 0.60, 0.70)


@dataclass(frozen=True)
class DPRCandidate:
    pathology: str
    candidate_type: str
    component_index: int
    voxel_count: int
    action_if_rejected: str = "KEEP_ANCHOR_LOCAL_MASK"
    action_if_accepted: str = "REPLACE_WITH_REFINED_LOCAL_MASK"


def gaussian_importance(shape: tuple[int, int, int]) -> np.ndarray:
    axes = []
    for size in shape:
        if size <= 1:
            axes.append(np.ones((size,), dtype=np.float32))
        else:
            center = (float(size) - 1.0) / 2.0
            sigma = max(float(size) / 8.0, 1.0)
            coord = np.arange(size, dtype=np.float32)
            arr = np.exp(-0.5 * ((coord - center) / sigma) ** 2).astype(np.float32)
            axes.append(np.maximum(arr / float(arr.max()), 1e-3))
    return (axes[0][:, None, None] * axes[1][None, :, None] * axes[2][None, None, :]).astype(np.float32)


def starts_for(dim: int, patch: int, overlap: float = 0.5) -> list[int]:
    if dim <= patch:
        return [0]
    stride = max(1, int(round(float(patch) * (1.0 - float(overlap)))))
    starts = list(range(0, dim - patch + 1, stride))
    if starts[-1] != dim - patch:
        starts.append(dim - patch)
    return starts


def extract(arr: np.ndarray, start: tuple[int, int, int], shape: tuple[int, int, int], fill: float) -> tuple[np.ndarray, tuple[slice, slice, slice]]:
    src = []
    dst = []
    for s0, size, dim in zip(start, shape, arr.shape[-3:]):
        s1 = min(dim, int(s0) + int(size))
        src.append(slice(int(s0), s1)); dst.append(slice(0, max(0, s1 - int(s0))))
    out = np.full(arr.shape[:-3] + tuple(shape), fill, dtype=arr.dtype)
    out[(..., *dst)] = arr[(..., *src)]
    return out, tuple(src)


def aggregate_patch_outputs(model: torch.nn.Module, batch_np: dict[str, np.ndarray], *, patch_shape: tuple[int, int, int] = (8, 128, 128), overlap: float = 0.5, device: torch.device | None = None) -> dict[str, np.ndarray]:
    """Aggregate probabilities/features before component construction.

    This function deliberately never averages patch final labels and never runs
    component arbitration inside a patch.
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    spatial = tuple(int(v) for v in batch_np["anchor_logits"].shape[-3:])
    accum_keys = ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "scar_p_refined", "scar_utility_accept_prob", "edema_p_coarse", "edema_q_fn", "edema_q_fp", "edema_p_refined", "edema_utility_accept_prob"]
    acc = {k: np.zeros(spatial, dtype=np.float32) for k in accum_keys}
    weight = np.zeros(spatial, dtype=np.float32)
    g = gaussian_importance(patch_shape)
    starts = [(z, y, x) for z in starts_for(spatial[0], patch_shape[0], overlap) for y in starts_for(spatial[1], patch_shape[1], overlap) for x in starts_for(spatial[2], patch_shape[2], overlap)]
    model.eval()
    with torch.no_grad():
        for start in starts:
            patch = {}
            for key, fill in [("images", 0.0), ("anchor_logits", -12.0), ("uncertainty", 1.0), ("myocardium_support", 0.0), ("edema_support", 0.0), ("distance_to_myocardium", 99.0)]:
                patch[key], src = extract(batch_np[key], start, patch_shape, fill)
            inp = {k: torch.from_numpy(v[None]).float().to(device) for k, v in patch.items()}
            out = model(inp["images"], torch.from_numpy(batch_np["availability"][None]).float().to(device), inp["anchor_logits"], uncertainty=inp["uncertainty"], myocardium_support=inp["myocardium_support"], edema_support=inp["edema_support"], distance_to_myocardium=inp["distance_to_myocardium"], t2_present=torch.tensor([float(batch_np["t2_present"])], device=device), strict_inputs=True, anchor_value_kind="log_probabilities")
            dst_slices = tuple(slice(0, s.stop - s.start) for s in src)
            for key in accum_keys:
                arr = out[key].detach().float().cpu().numpy()[0, 0][dst_slices]
                acc[key][src] += arr * g[dst_slices]
            weight[src] += g[dst_slices]
    weight = np.maximum(weight, 1e-6)
    return {k: v / weight for k, v in acc.items()} | {"aggregation_overlap": np.asarray(overlap), "gaussian_blending": np.asarray(True)}


def build_candidates(anchor_mask: np.ndarray, maps: dict[str, np.ndarray], *, pathology: str, threshold: float = 0.5, t2_present: bool = True) -> list[tuple[DPRCandidate, np.ndarray, np.ndarray]]:
    if pathology not in {"scar", "edema_zone"}:
        raise ValueError(pathology)
    if pathology == "edema_zone" and not t2_present:
        return []
    if pathology == "scar":
        anchor = anchor_mask == SCAR_CHANNEL
        coarse = maps["scar_p_coarse"] >= threshold
        q_fn = maps["scar_q_fn"] >= threshold
        q_fp = maps["scar_q_fp"] >= threshold
        refined = maps["scar_p_refined"] >= threshold
    else:
        anchor = (anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)
        coarse = maps["edema_p_coarse"] >= threshold
        q_fn = maps["edema_q_fn"] >= threshold
        q_fp = maps["edema_q_fp"] >= threshold
        refined = maps["edema_p_refined"] >= threshold
    out = []
    structure = ndi.generate_binary_structure(3, 1)
    add_mask = (refined | coarse | q_fn) & ~anchor
    add_labeled, add_count = ndi.label(add_mask, structure=structure)
    for idx in range(1, int(add_count) + 1):
        comp = add_labeled == idx
        out.append((DPRCandidate(pathology, "ADD_FN", idx, int(comp.sum())), np.zeros_like(comp, dtype=bool), refined & comp))
    revise_mask = anchor & q_fp
    revise_labeled, revise_count = ndi.label(revise_mask, structure=structure)
    for idx in range(1, int(revise_count) + 1):
        comp = revise_labeled == idx
        out.append((DPRCandidate(pathology, "REVISE_FP", idx, int(comp.sum())), anchor & comp, refined & comp))
    return out


def arbitrate_pathology(anchor_local: np.ndarray, candidates: list[tuple[DPRCandidate, np.ndarray, np.ndarray]], utility_map: np.ndarray, threshold: float) -> tuple[np.ndarray, list[dict[str, Any]]]:
    result = anchor_local.copy().astype(bool)
    audit = []
    for cand, anchor_mask, refined_mask in candidates:
        if cand.candidate_type not in CANDIDATE_TYPES:
            raise ValueError(f"unknown candidate type {cand.candidate_type}")
        score_region = refined_mask | anchor_mask
        score = float(utility_map[score_region].mean()) if np.any(score_region) else 0.0
        accepted = score >= float(threshold)
        if accepted:
            result[score_region] = refined_mask[score_region]
            action = cand.action_if_accepted
        else:
            result[score_region] = anchor_mask[score_region]
            action = cand.action_if_rejected
        if action not in LEGAL_ACTIONS:
            raise ValueError(action)
        audit.append({"pathology": cand.pathology, "candidate_type": cand.candidate_type, "component_index": cand.component_index, "voxel_count": cand.voxel_count, "utility_score": score, "accepted": bool(accepted), "action": action})
    return result, audit


def compose_dual_pathology(anchor_mask: np.ndarray, maps: dict[str, np.ndarray], *, scar_threshold: float = 0.5, edema_threshold: float = 0.5, utility_threshold: float = 0.5, t2_present: bool = True) -> tuple[np.ndarray, list[dict[str, Any]]]:
    edema_anchor = (anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)
    scar_anchor = anchor_mask == SCAR_CHANNEL
    edema_candidates = build_candidates(anchor_mask, maps, pathology="edema_zone", threshold=edema_threshold, t2_present=t2_present)
    scar_candidates = build_candidates(anchor_mask, maps, pathology="scar", threshold=scar_threshold, t2_present=True)
    edema_zone, edema_audit = arbitrate_pathology(edema_anchor, edema_candidates, maps.get("edema_utility_accept_prob", np.zeros_like(anchor_mask, dtype=np.float32)), utility_threshold)
    scar, scar_audit = arbitrate_pathology(scar_anchor, scar_candidates, maps.get("scar_utility_accept_prob", np.zeros_like(anchor_mask, dtype=np.float32)), utility_threshold)
    final = anchor_mask.copy()
    final[(anchor_mask == EDEMA_CHANNEL) | (anchor_mask == SCAR_CHANNEL)] = 0
    pure_edema = edema_zone & ~scar
    final[pure_edema] = EDEMA_CHANNEL
    final[scar] = SCAR_CHANNEL
    return final, edema_audit + scar_audit


def exact_anchor_when_zero_accepted(anchor_mask: np.ndarray) -> np.ndarray:
    return anchor_mask.copy()
