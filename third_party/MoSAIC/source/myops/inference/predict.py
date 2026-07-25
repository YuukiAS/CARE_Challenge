from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import torch

from myops.data.labels import (
    STAGE_FINE,
    TRACK_CINE,
    TRACK_MYOPS,
    class_order_for_track,
    class_thresholds_for_track,
    default_thresholds,
    num_classes,
    train_to_official_labels,
)
from myops.data.preprocessing import cache_path, select_cine_frame_indices
from myops.utils.image import center_crop_or_pad, compute_bbox
from myops.utils.io import torch_load, torch_save
from myops.utils.metrics import dice_score, hd95
from scipy.ndimage import binary_dilation

from myops.inference.postprocess import (
    clean_prediction_by_class,
    enforce_pathology_inside_myo,
    largest_component,
)


def _image_volume_from_payload(payload: dict[str, Any], track: str) -> np.ndarray:
    if track == TRACK_MYOPS:
        return np.asarray(payload["image"], dtype=np.float32)
    if "cine_features" in payload:
        return np.asarray(payload["cine_features"], dtype=np.float32)
    return np.asarray(payload["ref_image"], dtype=np.float32)[None]


def _cine_sequence_from_payload(payload: dict[str, Any], frame_count: int = 20) -> np.ndarray:
    cine = np.asarray(payload["cine"], dtype=np.float32)
    if cine.ndim != 4:
        raise ValueError(f"Expected cached cine as [T,Z,H,W], got {cine.shape}")
    indices = payload.get("selected_frame_indices")
    if not indices:
        indices = select_cine_frame_indices(
            cine.shape[0],
            int(payload.get("reference_frame_index", 0)),
            float(payload.get("cine_frame_fraction", 2.0 / 3.0)),
            int(frame_count),
        )
    indices = [int(i) % cine.shape[0] for i in indices]
    if frame_count > 0:
        indices = indices[:frame_count]
        while len(indices) < frame_count:
            indices.append(indices[-1] if indices else 0)
    return cine[np.asarray(indices, dtype=np.int64)]


def _run_model_once(model: torch.nn.Module, image: torch.Tensor) -> torch.Tensor:
    with torch.no_grad():
        outputs = model(image)
    if isinstance(outputs, dict):
        return outputs["logits"]
    return outputs


def _tta_predict(model: torch.nn.Module, image: torch.Tensor, tta_config: dict | None) -> torch.Tensor:
    logits = _run_model_once(model, image)
    if not tta_config or not tta_config.get("enabled", False):
        return logits
    flips = tta_config.get("flips", ["horizontal", "vertical"])
    all_logits = [logits]
    if "horizontal" in flips:
        flipped = torch.flip(image, dims=[-1])
        out = _run_model_once(model, flipped)
        all_logits.append(torch.flip(out, dims=[-1]))
    if "vertical" in flips:
        flipped = torch.flip(image, dims=[-2])
        out = _run_model_once(model, flipped)
        all_logits.append(torch.flip(out, dims=[-2]))
    return torch.stack(all_logits, dim=0).mean(dim=0)


def predict_case_coarse(
    model: torch.nn.Module, payload: dict[str, Any], track: str,
    device: torch.device, thresholds: list[float] | None = None,
    image_size: list[int] | None = None, tta_config: dict | None = None,
) -> dict[str, Any]:
    model.eval()
    image_volume = _image_volume_from_payload(payload, track)
    presence_mask = list(payload["modality_presence_mask"])
    nc = num_classes(track, "coarse")
    thresholds = thresholds or default_thresholds(track, "coarse")
    image_size = image_size or [192, 192]

    pred_volume = np.zeros(image_volume.shape[1:], dtype=np.int16)
    prob_volume = np.zeros((nc,) + image_volume.shape[1:], dtype=np.float32)

    for z in range(image_volume.shape[1]):
        image_slice = image_volume[:, z]
        presence = np.stack([np.full(image_slice.shape[-2:], float(v), dtype=np.float32) for v in presence_mask], axis=0)
        x = np.concatenate([image_slice, presence], axis=0)
        x = np.stack([center_crop_or_pad(ch, image_size) for ch in x], axis=0)
        tensor = torch.from_numpy(x[None]).float().to(device)

        logits = _tta_predict(model, tensor, tta_config)
        probs = torch.sigmoid(logits).cpu().numpy()[0]

        for c in range(nc):
            p = center_crop_or_pad(probs[c], list(image_volume.shape[-2:]))
            prob_volume[c, z] = p

    for c in range(nc):
        binary = prob_volume[c] > thresholds[c]
        binary = largest_component(binary)
        pred_volume[binary & (pred_volume == 0)] = c + 1

    return {"case_id": payload["case_id"], "label": pred_volume, "probs": prob_volume}


def predict_case_fine(
    model: torch.nn.Module, payload: dict[str, Any], track: str,
    device: torch.device, coarse_prior: np.ndarray,
    thresholds: list[float] | None = None,
    image_size: list[int] | None = None, crop_margin: list[int] | None = None,
    min_component_sizes: dict[int, int] | None = None,
    pathology_dilation_iterations: int = 1,
    tta_config: dict | None = None,
    use_cine_sequence: bool = False,
    cine_frame_count: int = 20,
    channel_order: list[int] | None = None,
    disable_coarse_prior: bool = False,
) -> dict[str, Any]:
    model.eval()
    image_volume = (
        _cine_sequence_from_payload(payload, cine_frame_count)
        if track == TRACK_CINE and use_cine_sequence
        else _image_volume_from_payload(payload, track)
    )
    presence_mask = list(payload["modality_presence_mask"])
    if channel_order is not None:
        image_volume = image_volume[channel_order]
        presence_mask = [presence_mask[i] for i in channel_order]
    nc = num_classes(track, "fine")
    thresholds = thresholds or default_thresholds(track, "fine")
    image_size = image_size or [192, 192]
    crop_margin = crop_margin or [1, 16, 16]
    min_component_sizes = min_component_sizes or ({4: 3, 5: 2} if track == TRACK_MYOPS else {3: 2})

    if disable_coarse_prior:
        # Ablation: no Stage-1 cascade -- neither ROI cropping, nor the prior
        # channel, nor the anatomical post-hoc constraint may use it.
        coarse_prior = np.zeros_like(coarse_prior)
        prior_bbox = [[0, int(s)] for s in coarse_prior.shape]
    else:
        prior_bbox = compute_bbox(coarse_prior > 0, margin=crop_margin)
    _, y_range, x_range = prior_bbox
    y0, y1 = y_range
    x0, x1 = x_range

    resampled_shape = image_volume.shape[1:]
    pred_volume = np.zeros(resampled_shape, dtype=np.int16)
    prob_volume = np.zeros((nc,) + resampled_shape, dtype=np.float32)

    z0, z1 = prior_bbox[0]
    for z in range(z0, z1):
        image_slice = image_volume[:, z, y0:y1, x0:x1]
        coarse_slice = coarse_prior[z, y0:y1, x0:x1][None].astype(np.float32)
        if track == TRACK_CINE and use_cine_sequence:
            x = np.concatenate([image_slice, coarse_slice], axis=0)
        else:
            presence = np.stack([np.full(image_slice.shape[-2:], float(v), dtype=np.float32) for v in presence_mask], axis=0)
            x = np.concatenate([image_slice, presence, coarse_slice], axis=0)
        x = np.stack([center_crop_or_pad(ch, image_size) for ch in x], axis=0)
        tensor = torch.from_numpy(x[None]).float().to(device)

        logits = _tta_predict(model, tensor, tta_config)
        probs = torch.sigmoid(logits).cpu().numpy()[0]

        for c in range(nc):
            p = center_crop_or_pad(probs[c], [y1 - y0, x1 - x0])
            prob_volume[c, z, y0:y1, x0:x1] = p

    for c in range(nc):
        pred_volume[prob_volume[c] > thresholds[c]] = c + 1

    myo_constraint = coarse_prior > 0
    if pathology_dilation_iterations > 0:
        myo_constraint = binary_dilation(myo_constraint, iterations=pathology_dilation_iterations)
    if track == TRACK_MYOPS:
        pred_volume = enforce_pathology_inside_myo(pred_volume, 1, [4, 5], external_myo_mask=myo_constraint)
    else:
        pred_volume = enforce_pathology_inside_myo(pred_volume, 1, [3], external_myo_mask=myo_constraint)

    pred_volume = clean_prediction_by_class(pred_volume, min_component_sizes)

    if track == TRACK_MYOPS:
        edema_mask = pred_volume == 4
        if edema_mask.any():
            lcc = largest_component(edema_mask)
            pred_volume[edema_mask & (~lcc)] = 0

    return {"case_id": payload["case_id"], "label": pred_volume, "probs": prob_volume}


def predict_records_coarse(
    model: torch.nn.Module, records: list[dict[str, Any]], cache_root: str | Path,
    device: torch.device, output_dir: str | Path | None = None,
    thresholds: list[float] | None = None, tta_config: dict | None = None,
) -> list[dict[str, Any]]:
    results = []
    for record in records:
        payload = torch_load(cache_path(cache_root, record["track"], record["case_id"]))
        result = predict_case_coarse(
            model, payload, record["track"], device,
            thresholds=thresholds, tta_config=tta_config,
        )
        results.append(result)
        if output_dir is not None:
            dest = Path(output_dir) / record["track"] / f'{record["case_id"]}.pt'
            torch_save(result, dest)
    return results


def evaluate_predictions(
    track: str, stage: str, results: list[dict[str, Any]], cache_root: str | Path,
) -> dict[str, float]:
    class_names = class_order_for_track(track, stage)
    dice_bucket: dict[str, list[float]] = defaultdict(list)
    hd_bucket: dict[str, list[float]] = defaultdict(list)

    for result in results:
        payload = torch_load(cache_path(cache_root, track, result["case_id"]))
        target = np.asarray(payload[f"{stage}_label"], dtype=np.int16)
        prediction = np.asarray(result["label"], dtype=np.int16)
        supervision = np.asarray(
            payload.get(f"{stage}_supervision_mask", [1.0] * len(class_names)),
            dtype=np.float32,
        )
        spacing = [
            float(payload["target_spacing"][2]),
            float(payload["target_spacing"][0]),
            float(payload["target_spacing"][1]),
        ]

        for class_idx, class_name in enumerate(class_names, start=1):
            if class_idx - 1 >= len(supervision) or supervision[class_idx - 1] <= 0.5:
                continue
            pred_mask = prediction == class_idx
            target_mask = target == class_idx
            dice_bucket[f"{class_name}_dice"].append(dice_score(pred_mask, target_mask))
            hd_bucket[f"{class_name}_hd95"].append(hd95(pred_mask, target_mask, spacing))

        if track == TRACK_MYOPS and stage == STAGE_FINE and float(supervision[3:].sum()) > 0.0:
            pred_union = np.isin(prediction, [4, 5])
            target_union = np.isin(target, [4, 5])
            dice_bucket["lesion_union_dice"].append(dice_score(pred_union, target_union))
            hd_bucket["lesion_union_hd95"].append(hd95(pred_union, target_union, spacing))

    summary: dict[str, float] = {}
    all_dice: list[float] = []
    all_hd: list[float] = []
    for key, values in sorted(dice_bucket.items()):
        mean_val = float(np.mean(values)) if values else 0.0
        summary[key] = mean_val
        all_dice.append(mean_val)
    for key, values in sorted(hd_bucket.items()):
        finite = [v for v in values if np.isfinite(v)]
        mean_val = float(np.mean(finite)) if finite else float("inf")
        summary[key] = mean_val
        if np.isfinite(mean_val):
            all_hd.append(mean_val)
    summary["mean_dice"] = float(np.mean(all_dice)) if all_dice else 0.0
    summary["mean_hd95"] = float(np.mean(all_hd)) if all_hd else float("inf")

    if stage == STAGE_FINE:
        if track == TRACK_MYOPS:
            path_dice = [
                summary[k] for k in ("edema_dice", "scar_dice")
                if k in summary and np.isfinite(summary[k])
            ]
            path_hd = [
                summary[k] for k in ("edema_hd95", "scar_hd95")
                if k in summary and np.isfinite(summary[k])
            ]
            summary["pathology_mean_dice"] = float(np.mean(path_dice)) if path_dice else 0.0
            summary["pathology_mean_hd95"] = float(np.mean(path_hd)) if path_hd else float("inf")
        elif track == TRACK_CINE:
            summary["cine_scar_dice"] = float(summary.get("scar_dice", 0.0))
            summary["cine_scar_hd95"] = float(summary.get("scar_hd95", float("inf")))
    return summary


def _rethreshold_result(
    result: dict[str, Any], thresholds: list[float], track: str,
    coarse_priors: dict[str, np.ndarray],
    dilation_iterations: int = 2,
    min_component_sizes: dict[int, int] | None = None,
) -> dict[str, Any]:
    prob_volume = np.asarray(result["probs"], dtype=np.float32)
    nc = prob_volume.shape[0]
    pred_volume = np.zeros(prob_volume.shape[1:], dtype=np.int16)
    for c in range(nc):
        pred_volume[prob_volume[c] > thresholds[c]] = c + 1

    coarse_prior = coarse_priors.get(result["case_id"])
    if coarse_prior is not None:
        myo_constraint = coarse_prior > 0
        if dilation_iterations > 0:
            myo_constraint = binary_dilation(myo_constraint, iterations=dilation_iterations)
        if track == TRACK_MYOPS:
            pred_volume = enforce_pathology_inside_myo(pred_volume, 1, [4, 5], external_myo_mask=myo_constraint)
        else:
            pred_volume = enforce_pathology_inside_myo(pred_volume, 1, [3], external_myo_mask=myo_constraint)

    if min_component_sizes:
        pred_volume = clean_prediction_by_class(pred_volume, min_component_sizes)

    return {"case_id": result["case_id"], "label": pred_volume, "probs": prob_volume}


def search_thresholds(
    track: str, stage: str, results: list[dict[str, Any]], cache_root: str | Path,
    coarse_priors: dict[str, np.ndarray] | None = None,
    dilation_iterations: int = 2,
    min_component_sizes: dict[int, int] | None = None,
    search_values: list[float] | None = None,
    target_class_names: list[str] | set[str] | None = None,
) -> dict[str, Any]:
    search_values = search_values or [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5]
    coarse_priors = coarse_priors or {}
    class_names = class_order_for_track(track, stage)
    nc = len(class_names)
    base_thresholds = default_thresholds(track, stage)

    pathology_names = {"edema", "scar", "cine_scar"}
    target_names = {str(name) for name in target_class_names} if target_class_names else None
    pathology_indices = [
        i for i, name in enumerate(class_names)
        if name in pathology_names and (target_names is None or name in target_names)
    ]

    best_thresholds = list(base_thresholds)
    best_score = -1.0

    for pi in pathology_indices:
        best_t = best_thresholds[pi]
        best_class_score = -1.0
        for t in search_values:
            trial = list(best_thresholds)
            trial[pi] = t
            rethresholded = [
                _rethreshold_result(r, trial, track, coarse_priors, dilation_iterations, min_component_sizes)
                for r in results
            ]
            metrics = evaluate_predictions(track, stage, rethresholded, cache_root)
            score = float(metrics.get(f"{class_names[pi]}_dice", 0.0))
            if score > best_class_score:
                best_class_score = score
                best_t = t
        best_thresholds[pi] = best_t
        print(f"  {class_names[pi]}: best threshold={best_t:.2f}, dice={best_class_score:.4f}")

    final = [
        _rethreshold_result(r, best_thresholds, track, coarse_priors, dilation_iterations, min_component_sizes)
        for r in results
    ]
    final_metrics = evaluate_predictions(track, stage, final, cache_root)
    return {"thresholds": best_thresholds, "metrics": final_metrics, "results": final}


def search_postprocessing(
    track: str, stage: str, results: list[dict[str, Any]], cache_root: str | Path,
    coarse_priors: dict[str, np.ndarray] | None = None,
    thresholds: list[float] | None = None,
    score_key: str | None = None,
) -> dict[str, Any]:
    coarse_priors = coarse_priors or {}
    thresholds = thresholds or default_thresholds(track, stage)

    dilation_values = [0, 1, 2, 3]
    if track == TRACK_MYOPS:
        min_size_options = [
            {4: 0, 5: 0}, {4: 2, 5: 1}, {4: 3, 5: 2}, {4: 5, 5: 3},
        ]
    else:
        min_size_options = [{3: 0}, {3: 1}, {3: 2}, {3: 3}]
    score_key = score_key or ("pathology_mean_dice" if track == TRACK_MYOPS else "cine_scar_dice")

    best_score = -1.0
    best_dilation = 2
    best_min_sizes: dict[int, int] = min_size_options[0]
    best_metrics: dict[str, float] = {}

    for dil in dilation_values:
        for min_sizes in min_size_options:
            rethresholded = [
                _rethreshold_result(r, thresholds, track, coarse_priors, dil, min_sizes)
                for r in results
            ]
            metrics = evaluate_predictions(track, stage, rethresholded, cache_root)
            score = metrics.get(score_key, 0.0)
            if score > best_score:
                best_score = score
                best_dilation = dil
                best_min_sizes = min_sizes
                best_metrics = metrics

    print(f"  Best postprocess: dilation={best_dilation}, min_sizes={best_min_sizes}")
    print(f"  {score_key}={best_score:.4f}")
    return {
        "dilation_iterations": best_dilation,
        "min_component_sizes": best_min_sizes,
        "metrics": best_metrics,
    }


def merge_edema_scar_predictions(
    scar_result: dict[str, Any],
    edema_result: dict[str, Any],
    thresholds: list[float] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or [0.5, 0.5, 0.5, 0.35, 0.3]
    scar_probs = np.asarray(scar_result["probs"], dtype=np.float32)
    edema_probs = np.asarray(edema_result["probs"], dtype=np.float32)

    merged_probs = scar_probs.copy()
    merged_probs[3] = edema_probs[3]

    pred = np.zeros(merged_probs.shape[1:], dtype=np.int16)
    anatomy_channels = min(3, merged_probs.shape[0])
    for c in range(anatomy_channels):
        mask = merged_probs[c] > thresholds[c]
        pred[mask & (pred == 0)] = c + 1
    if merged_probs.shape[0] > 3:
        edema_mask = merged_probs[3] > thresholds[3]
        pred[edema_mask] = 4
    if merged_probs.shape[0] > 4:
        scar_mask = merged_probs[4] > thresholds[4]
        pred[scar_mask] = 5

    return {
        "case_id": scar_result["case_id"],
        "label": pred,
        "probs": merged_probs,
    }
