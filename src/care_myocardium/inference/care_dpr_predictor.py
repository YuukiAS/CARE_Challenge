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
    bbox_zyx: tuple[tuple[int, int], tuple[int, int], tuple[int, int]] = ((0, 0), (0, 0), (0, 0))
    truncation_flag: bool = False
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
    accum_keys = ["scar_p_coarse", "scar_q_fn", "scar_q_fp", "edema_p_coarse", "edema_q_fn", "edema_q_fp"]
    acc = {k: np.zeros(spatial, dtype=np.float32) for k in accum_keys}
    shared_acc: np.ndarray | None = None
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
            shared = out["shared_feature"].detach().float().cpu().numpy()[0]
            if shared_acc is None:
                shared_acc = np.zeros((shared.shape[0], *spatial), dtype=np.float32)
            shared_acc[(slice(None), *src)] += shared[(slice(None), *dst_slices)] * g[dst_slices]
            weight[src] += g[dst_slices]
    weight = np.maximum(weight, 1e-6)
    result = {k: v / weight for k, v in acc.items()}
    result["shared_full_resolution_feature"] = shared_acc / weight[None] if shared_acc is not None else np.zeros((0, *spatial), dtype=np.float32)
    result["aggregate_before_components"] = np.asarray(True)
    return result | {"aggregation_overlap": np.asarray(overlap), "gaussian_blending": np.asarray(True)}


def _bbox(mask: np.ndarray) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return ((0, 0), (0, 0), (0, 0))
    lo = coords.min(axis=0); hi = coords.max(axis=0) + 1
    return tuple((int(a), int(b)) for a, b in zip(lo, hi))  # type: ignore[return-value]


def _expand(mask: np.ndarray, margin: int = 3) -> np.ndarray:
    if margin <= 0 or not np.any(mask):
        return mask.astype(bool)
    structure = ndi.generate_binary_structure(3, 1)
    return ndi.binary_dilation(mask.astype(bool), structure=structure, iterations=int(margin))



def build_candidate_rois(anchor_mask: np.ndarray, maps: dict[str, np.ndarray], *, pathology: str, threshold: float = 0.5, t2_present: bool = True, margin: int = 3) -> list[tuple[DPRCandidate, np.ndarray, np.ndarray, np.ndarray]]:
    """Build full-volume candidates before any local refinement decision."""
    if pathology not in {"scar", "edema_zone"}:
        raise ValueError(pathology)
    if pathology == "edema_zone" and not t2_present:
        return []
    if pathology == "scar":
        anchor = anchor_mask == SCAR_CHANNEL
        coarse = maps["scar_p_coarse"] >= threshold
        q_fn = maps["scar_q_fn"] >= threshold
        q_fp = maps["scar_q_fp"] >= threshold
    else:
        anchor = (anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)
        coarse = maps["edema_p_coarse"] >= threshold
        q_fn = maps["edema_q_fn"] >= threshold
        q_fp = maps["edema_q_fp"] >= threshold
    out: list[tuple[DPRCandidate, np.ndarray, np.ndarray, np.ndarray]] = []
    structure = ndi.generate_binary_structure(3, 1)
    add_mask = (coarse | q_fn) & ~anchor
    add_labeled, add_count = ndi.label(add_mask, structure=structure)
    for idx in range(1, int(add_count) + 1):
        comp = add_labeled == idx
        roi = _expand(comp, margin=margin)
        trunc = bool(np.any(roi[[0, -1], :, :]) or np.any(roi[:, [0, -1], :]) or np.any(roi[:, :, [0, -1]]))
        out.append((DPRCandidate(pathology, "ADD_FN", idx, int(comp.sum()), _bbox(roi), trunc), np.zeros_like(comp, dtype=bool), comp, roi))
    anchor_labeled, anchor_count = ndi.label(anchor, structure=structure)
    revise_idx = 0
    for idx in range(1, int(anchor_count) + 1):
        anchor_comp = anchor_labeled == idx
        if not np.any(anchor_comp & q_fp):
            continue
        revise_idx += 1
        roi = _expand(anchor_comp, margin=margin)
        trunc = bool(np.any(roi[[0, -1], :, :]) or np.any(roi[:, [0, -1], :]) or np.any(roi[:, :, [0, -1]]))
        out.append((DPRCandidate(pathology, "REVISE_FP", revise_idx, int(anchor_comp.sum()), _bbox(roi), trunc), anchor_comp, anchor_comp, roi))
    out.sort(key=lambda item: (item[0].candidate_type, item[0].bbox_zyx, item[0].component_index))
    return out

def build_candidates(anchor_mask: np.ndarray, maps: dict[str, np.ndarray], *, pathology: str, threshold: float = 0.5, t2_present: bool = True, margin: int = 3) -> list[tuple[DPRCandidate, np.ndarray, np.ndarray]]:
    refined_key = "scar_p_refined" if pathology == "scar" else "edema_p_refined"
    refined = maps.get(refined_key, np.zeros_like(anchor_mask, dtype=np.float32)) >= threshold
    out: list[tuple[DPRCandidate, np.ndarray, np.ndarray]] = []
    for cand, anchor_local, seed, roi in build_candidate_rois(anchor_mask, maps, pathology=pathology, threshold=threshold, t2_present=t2_present, margin=margin):
        if np.any(refined):
            replacement = refined & roi
        elif cand.candidate_type == "ADD_FN":
            replacement = seed.astype(bool)
        else:
            replacement = np.zeros_like(anchor_local, dtype=bool)
        out.append((cand, anchor_local, replacement))
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
        audit.append({"pathology": cand.pathology, "candidate_type": cand.candidate_type, "component_index": cand.component_index, "voxel_count": cand.voxel_count, "bbox_zyx": cand.bbox_zyx, "component_truncation_flag": cand.truncation_flag, "utility_score": score, "accepted": bool(accepted), "action": action})
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



def _center_of(mask: np.ndarray) -> tuple[int, int, int]:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return tuple(int(v // 2) for v in mask.shape)
    return tuple(int(v) for v in np.round(coords.mean(axis=0)).astype(int))


def _torch_map(arr: np.ndarray, device: torch.device) -> torch.Tensor:
    return torch.from_numpy(arr[None, None].astype(np.float32)).to(device)


def _anchor_margin_np(anchor_logits: np.ndarray, *, pathology: str) -> np.ndarray:
    if pathology == "scar":
        comp = np.max(np.concatenate([anchor_logits[:SCAR_CHANNEL], anchor_logits[SCAR_CHANNEL + 1 :]], axis=0), axis=0)
        return (anchor_logits[SCAR_CHANNEL] - comp).astype(np.float32)
    zone = np.maximum(anchor_logits[SCAR_CHANNEL], anchor_logits[EDEMA_CHANNEL])
    anatomy = np.max(anchor_logits[list(c for c in range(anchor_logits.shape[0]) if c not in (SCAR_CHANNEL, EDEMA_CHANNEL))], axis=0)
    return (zone - anatomy).astype(np.float32)


def _refine_and_score_candidate(model: torch.nn.Module, maps: dict[str, np.ndarray], batch_np: dict[str, np.ndarray], cand: DPRCandidate, anchor_local: np.ndarray, seed_mask: np.ndarray, roi: np.ndarray, *, device: torch.device, threshold: float) -> tuple[np.ndarray, float, float, dict[str, Any]]:
    pathology = cand.pathology
    feature = torch.from_numpy(maps["shared_full_resolution_feature"][None].astype(np.float32)).to(device)
    if pathology == "scar":
        branch = model.scar_branch
        extras = [batch_np["images"][0], _anchor_margin_np(batch_np["anchor_logits"], pathology="scar"), maps["scar_p_coarse"], maps["scar_q_fn"], maps["scar_q_fp"], batch_np["uncertainty"][0], batch_np["myocardium_support"][0], batch_np["distance_to_myocardium"][0]]
        pfx = "scar"
        support_np = batch_np["myocardium_support"][0]
    else:
        branch = model.edema_branch
        extras = [batch_np["images"][1], batch_np["images"][0], _anchor_margin_np(batch_np["anchor_logits"], pathology="edema_zone"), maps["edema_p_coarse"], maps["edema_q_fn"], maps["edema_q_fp"], batch_np["uncertainty"][0], batch_np["edema_support"][0], batch_np["distance_to_myocardium"][0]]
        pfx = "edema"
        support_np = batch_np["edema_support"][0]
    full_input = torch.cat([feature, torch.from_numpy(np.stack(extras, axis=0)[None].astype(np.float32)).to(device)], dim=1)
    center = _center_of(seed_mask | anchor_local)
    with torch.no_grad():
        refined_logit, _ = branch.local_refiner.forward_at_center(full_input, center)
        refined_prob = torch.sigmoid(refined_logit)[0, 0].detach().float().cpu().numpy()
    refined_prob = refined_prob * roi.astype(np.float32)
    refined_mask = refined_prob >= float(threshold)
    component_mask_np = (seed_mask | anchor_local | refined_mask).astype(np.float32)
    if not np.any(component_mask_np):
        component_mask_np = roi.astype(np.float32)
    scored = branch.component_utility.score_candidate(
        feature,
        p_coarse=_torch_map(maps[f"{pfx}_p_coarse"], device),
        q_fn=_torch_map(maps[f"{pfx}_q_fn"], device),
        q_fp=_torch_map(maps[f"{pfx}_q_fp"], device),
        p_refined=_torch_map(refined_prob, device),
        anchor_margin=_torch_map(_anchor_margin_np(batch_np["anchor_logits"], pathology=pathology), device),
        uncertainty=_torch_map(batch_np["uncertainty"][0], device),
        distance_to_support=_torch_map(batch_np["distance_to_myocardium"][0], device),
        support=_torch_map(support_np, device),
        component_mask=_torch_map(component_mask_np, device),
        candidate_type=cand.candidate_type,
        truncation_flag=torch.tensor([[float(cand.truncation_flag)]], device=device),
    )
    accept_logit = float(scored["utility_accept_logit"][0, 0].detach().cpu())
    utility_reg = float(scored["utility_regression"][0, 0].detach().cpu())
    audit = {
        "pathology": cand.pathology,
        "candidate_type": cand.candidate_type,
        "component_index": cand.component_index,
        "voxel_count": cand.voxel_count,
        "bbox_zyx": cand.bbox_zyx,
        "component_truncation_flag": cand.truncation_flag,
        "pass2_candidate_center_zyx": center,
        "pass2_roi_context_zyx": list(branch.local_refiner.roi_context_zyx),
        "component_descriptor_uses_aggregated_shared_feature": True,
        "utility_accept_logit": accept_logit,
        "utility_regression": utility_reg,
        "utility_score": float(1.0 / (1.0 + np.exp(-accept_logit))),
    }
    return refined_mask, accept_logit, utility_reg, audit


def run_two_pass_full_volume_dpr(model: torch.nn.Module, batch_np: dict[str, np.ndarray], *, patch_shape: tuple[int, int, int] = (8, 128, 128), overlap: float = 0.5, proposal_threshold: float = 0.5, refined_threshold: float = 0.5, utility_threshold: float = 0.5, scar_utility_threshold: float | None = None, edema_utility_threshold: float | None = None, utility_regression_min: float | None = None, scar_utility_regression_min: float | None = None, edema_utility_regression_min: float | None = None, device: torch.device | None = None) -> dict[str, Any]:
    """Formal R2 two-pass full-volume DPR inference.

    Pass 1 aggregates full-resolution shared features and proposal maps. Pass 2
    builds candidates in the complete volume, then refines and scores each
    candidate independently with the pathology-specific local refiner and
    ComponentUtilityMLP weights.
    """
    device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
    pass1 = aggregate_patch_outputs(model, batch_np, patch_shape=patch_shape, overlap=overlap, device=device)
    if "anchor_mask" in batch_np:
        anchor_mask = np.asarray(batch_np["anchor_mask"]).astype(np.uint8, copy=False)
    else:
        anchor_mask = np.asarray(batch_np["anchor_logits"]).argmax(axis=0).astype(np.uint8)
    pass1["scar_p_refined"] = np.zeros_like(anchor_mask, dtype=np.float32)
    pass1["edema_p_refined"] = np.zeros_like(anchor_mask, dtype=np.float32)
    candidate_records = []
    candidate_evidence: list[dict[str, Any]] = []
    final_by_pathology: dict[str, np.ndarray] = {}
    all_audit: list[dict[str, Any]] = []
    for pathology, pfx in (("edema_zone", "edema"), ("scar", "scar")):
        anchor_local = ((anchor_mask == SCAR_CHANNEL) | (anchor_mask == EDEMA_CHANNEL)) if pathology == "edema_zone" else (anchor_mask == SCAR_CHANNEL)
        result = anchor_local.copy().astype(bool)
        candidates = build_candidate_rois(anchor_mask, pass1, pathology=pathology, threshold=proposal_threshold, t2_present=bool(batch_np.get("t2_present", True)))
        p_refined_full = np.zeros_like(anchor_mask, dtype=np.float32)
        for cand, cand_anchor, seed, roi in candidates:
            refined_mask, accept_logit, utility_reg, audit = _refine_and_score_candidate(model, pass1, batch_np, cand, cand_anchor, seed, roi, device=device, threshold=refined_threshold)
            p_refined_full[roi] = np.maximum(p_refined_full[roi], refined_mask[roi].astype(np.float32))
            score_region = (cand_anchor | refined_mask | seed)
            threshold_for_pathology = float(edema_utility_threshold if pathology == "edema_zone" and edema_utility_threshold is not None else scar_utility_threshold if pathology == "scar" and scar_utility_threshold is not None else utility_threshold)
            score_accept = float(audit["utility_score"]) >= threshold_for_pathology
            regression_floor = edema_utility_regression_min if pathology == "edema_zone" and edema_utility_regression_min is not None else scar_utility_regression_min if pathology == "scar" and scar_utility_regression_min is not None else utility_regression_min
            regression_accept = True if regression_floor is None else float(utility_reg) >= float(regression_floor)
            accepted = bool(score_accept and regression_accept)
            if cand.candidate_type == "ADD_FN":
                if accepted:
                    result[refined_mask] = True
                    action = cand.action_if_accepted
                else:
                    action = cand.action_if_rejected
            elif accepted:
                result[score_region] = refined_mask[score_region]
                action = cand.action_if_accepted
            else:
                result[cand_anchor] = True
                action = cand.action_if_rejected
            audit.update({
                "accepted": bool(accepted),
                "action": action,
                "legal_action": action in LEGAL_ACTIONS,
                "utility_threshold": threshold_for_pathology,
                "utility_regression_min": regression_floor,
                "score_accepts_candidate": bool(score_accept),
                "regression_accepts_candidate": bool(regression_accept),
            })
            all_audit.append(audit)
            candidate_records.append({"pathology": pathology, "candidate_type": cand.candidate_type, "accepted": bool(accepted), "utility_score": audit["utility_score"], "utility_regression": utility_reg})
            candidate_evidence.append({
                "candidate": cand,
                "pathology": pathology,
                "candidate_type": cand.candidate_type,
                "anchor_local_mask": cand_anchor.copy(),
                "seed_mask": seed.copy(),
                "roi_mask": roi.copy(),
                "refined_local_mask": refined_mask.copy(),
                "utility_score": float(audit["utility_score"]),
                "utility_regression": float(utility_reg),
                "utility_regression_min": regression_floor,
                "score_accepts_candidate": bool(score_accept),
                "regression_accepts_candidate": bool(regression_accept),
                "accepted": bool(accepted),
                "action": action,
            })
        pass1[f"{pfx}_p_refined"] = p_refined_full
        final_by_pathology[pathology] = result
    final = anchor_mask.copy()
    final[(anchor_mask == EDEMA_CHANNEL) | (anchor_mask == SCAR_CHANNEL)] = 0
    edema_zone = final_by_pathology.get("edema_zone", (anchor_mask == EDEMA_CHANNEL) | (anchor_mask == SCAR_CHANNEL))
    scar = final_by_pathology.get("scar", anchor_mask == SCAR_CHANNEL)
    final[edema_zone & ~scar] = EDEMA_CHANNEL
    final[scar] = SCAR_CHANNEL
    return {
        "status": "PASS",
        "pass1": pass1,
        "final_mask": final,
        "candidate_audit": all_audit,
        "candidate_records": candidate_records,
        "candidate_evidence": candidate_evidence,
        "component_utility_calls": len(candidate_evidence),
        "two_pass_full_volume_candidate_pipeline": True,
        "pass1_aggregates_patch_final_labels": False,
        "pass1_runs_component_decision": False,
        "pass2_refines_each_candidate": True,
    }


def exact_anchor_when_zero_accepted(anchor_mask: np.ndarray) -> np.ndarray:
    return anchor_mask.copy()
