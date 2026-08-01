#!/usr/bin/env python3
"""Full-volume inner-set evaluation for target-domain gap-closure lanes."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import blosc2
import numpy as np
import torch
import torch.nn.functional as F
from scipy.ndimage import binary_dilation, distance_transform_edt, generate_binary_structure, label as cc_label


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TASK_KEY = "20260801_care_target_domain_race_gap_closure"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
DATA_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
RUNTIME_ROOT = Path("/users/a/e/aereinh/.tmp/codex-CARE") / TASK_KEY

PINNED_M1_ROOT = REPO_ROOT / "third_party/MyoPS-Net_PINNED"
PINNED_M2_ROOT = REPO_ROOT / "third_party/I_MMSeg_PINNED"
if str(PINNED_M1_ROOT) not in sys.path:
    sys.path.insert(0, str(PINNED_M1_ROOT))
if str(PINNED_M2_ROOT) not in sys.path:
    sys.path.insert(0, str(PINNED_M2_ROOT))

from scripts.training.target_domain_gap_closure.run_m1_myopsnet_l_care import CARETriModalMyoPSNet  # noqa: E402
from scripts.training.target_domain_gap_closure.run_m2_i_mmseg_care import build_model as build_m2_model  # noqa: E402
from src.care_myocardium.nnunet.gap_closure_trainer import nnUNetTrainerGapClosureM0R4000  # noqa: E402
from src.care_myocardium.models.target_domain_gap_closure import CARETargetDomainSpecialist  # noqa: E402


PATHOLOGIES = {
    "scar": 5,
    "pure_edema": 4,
}
REMOTE_FP_DISTANCE_MM = 10.0
SMALL_LESION_VOXELS = 100
_M0R_PREDICTOR_CACHE: dict[tuple[int, str], Any] = {}


@dataclass(frozen=True)
class CheckpointSpec:
    lane: str
    fold: int
    step: int
    path: Path


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def load_case(case_id: str) -> tuple[np.ndarray, np.ndarray]:
    image = read_b2nd(DATA_ROOT / f"{case_id}.b2nd").astype(np.float32)
    label = read_b2nd(DATA_ROOT / f"{case_id}_seg.b2nd")[0].astype(np.uint8)
    return image, label


def center_crop_or_pad(arr: np.ndarray, dim: int) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    h, w = arr.shape[-2:]
    pad_h = max(0, dim - h)
    pad_w = max(0, dim - w)
    if pad_h or pad_w:
        pad_spec = [(0, 0)] * arr.ndim
        pad_spec[-2] = (pad_h // 2, pad_h - pad_h // 2)
        pad_spec[-1] = (pad_w // 2, pad_w - pad_w // 2)
        arr = np.pad(arr, pad_spec, mode="constant")
        h, w = arr.shape[-2:]
    y0 = max(0, (h - dim) // 2)
    x0 = max(0, (w - dim) // 2)
    return arr[..., y0 : y0 + dim, x0 : x0 + dim], (y0, y0 + dim, x0, x0 + dim)


def paste_crop(pred: np.ndarray, decoded: np.ndarray, bounds: tuple[int, int, int, int]) -> None:
    y0, y1, x0, x1 = bounds
    h, w = pred.shape[-2:]
    yy0, yy1 = max(0, y0), min(h, y1)
    xx0, xx1 = max(0, x0), min(w, x1)
    pred[..., yy0:yy1, xx0:xx1] = decoded[..., (yy0 - y0) : (yy1 - y0), (xx0 - x0) : (xx1 - x0)]


def binary_dice(pred: np.ndarray, gt: np.ndarray) -> float:
    p = pred.astype(bool)
    g = gt.astype(bool)
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(p, g).sum() / denom)


def surface(mask: np.ndarray) -> np.ndarray:
    if not mask.any():
        return mask.astype(bool)
    structure = generate_binary_structure(mask.ndim, 1)
    return np.logical_xor(mask.astype(bool), binary_dilation(mask.astype(bool), structure=structure))


def hausdorff(pred: np.ndarray, gt: np.ndarray, percentile: float = 95.0) -> float | None:
    p = pred.astype(bool)
    g = gt.astype(bool)
    if not p.any() and not g.any():
        return 0.0
    if not p.any() or not g.any():
        return None
    sp = surface(p)
    sg = surface(g)
    dt_g = distance_transform_edt(~sg)
    dt_p = distance_transform_edt(~sp)
    d = np.concatenate([dt_g[sp], dt_p[sg]])
    return float(np.percentile(d, percentile)) if d.size else 0.0


def lesion_recall(pred: np.ndarray, gt: np.ndarray) -> tuple[float | None, float | None, int, int]:
    cc, n = cc_label(gt.astype(bool))
    if n == 0:
        return None, None, 0, 0
    hit = 0
    small = 0
    small_hit = 0
    p = pred.astype(bool)
    for idx in range(1, n + 1):
        comp = cc == idx
        is_hit = bool(np.logical_and(comp, p).any())
        hit += int(is_hit)
        if int(comp.sum()) < SMALL_LESION_VOXELS:
            small += 1
            small_hit += int(is_hit)
    return float(hit / n), (float(small_hit / small) if small else None), int(n), int(small)


def component_count(mask: np.ndarray) -> int:
    _cc, n = cc_label(mask.astype(bool))
    return int(n)


def fp_metrics(pred: np.ndarray, gt: np.ndarray, blood: np.ndarray) -> dict[str, Any]:
    fp = pred.astype(bool) & ~gt.astype(bool)
    cc, n = cc_label(fp)
    if n == 0:
        return {"remote_fp_count": 0, "remote_fp_voxels": 0, "blood_pool_adjacent_fp_count": 0, "blood_pool_adjacent_fp_voxels": 0}
    if gt.any():
        dt_gt = distance_transform_edt(~gt.astype(bool))
    else:
        dt_gt = np.full(fp.shape, REMOTE_FP_DISTANCE_MM + 1.0)
    dt_blood = distance_transform_edt(~blood.astype(bool)) if blood.any() else np.full(fp.shape, REMOTE_FP_DISTANCE_MM + 1.0)
    remote_count = remote_vox = blood_count = blood_vox = 0
    for idx in range(1, n + 1):
        comp = cc == idx
        vox = int(comp.sum())
        if float(dt_gt[comp].min()) > REMOTE_FP_DISTANCE_MM:
            remote_count += 1
            remote_vox += vox
        if float(dt_blood[comp].min()) <= 2.0:
            blood_count += 1
            blood_vox += vox
    return {
        "remote_fp_count": remote_count,
        "remote_fp_voxels": remote_vox,
        "blood_pool_adjacent_fp_count": blood_count,
        "blood_pool_adjacent_fp_voxels": blood_vox,
    }


def metric_rows(
    lane: str,
    fold: int,
    step: int,
    case_id: str,
    pred: np.ndarray,
    gt_label: np.ndarray,
    population: str = "inner_selection",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    blood = (gt_label == 2) | (gt_label == 3)
    for pathology, label_value in PATHOLOGIES.items():
        pm = pred == label_value
        gt = gt_label == label_value
        tp = int(np.logical_and(pm, gt).sum())
        pred_voxels = int(pm.sum())
        gt_voxels = int(gt.sum())
        rec, small_rec, lesion_count, small_count = lesion_recall(pm, gt)
        fp = fp_metrics(pm, gt, blood)
        rows.append(
            {
                "lane": lane,
                "fold": fold,
                "checkpoint_step": step,
                "case_id": case_id,
                "population": population,
                "pathology": pathology,
                "dice": binary_dice(pm, gt),
                "hd95_vox": hausdorff(pm, gt, 95.0),
                "exact_hd_vox": hausdorff(pm, gt, 100.0),
                "precision": float(tp / pred_voxels) if pred_voxels else (1.0 if gt_voxels == 0 else 0.0),
                "sensitivity": float(tp / gt_voxels) if gt_voxels else (1.0 if pred_voxels == 0 else 0.0),
                "pred_component_count": component_count(pm),
                "gt_component_count": lesion_count,
                "pred_voxels": pred_voxels,
                "gt_voxels": gt_voxels,
                "volume_ratio": float(pred_voxels / gt_voxels) if gt_voxels else None,
                "lesion_recall": rec,
                "small_lesion_recall": small_rec,
                "gt_lesion_count": lesion_count,
                "small_lesion_count": small_count,
                **fp,
            }
        )
    return rows


def checkpoint_step(path: Path) -> int:
    match = re.search(r"step(\d+)", path.name)
    return int(match.group(1)) if match else -1


def discover_checkpoints(lane: str, fold: int, policy: str) -> list[CheckpointSpec]:
    receipt_path = RESULT_ROOT / lane / f"fold{fold}_training_receipt.json"
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    if lane == "m0r_faithful_control":
        paths = [Path(p) for p in data["step_checkpoints"] if checkpoint_step(Path(p)) > 0 and checkpoint_step(Path(p)) % 500 == 0]
        paths = sorted(paths, key=checkpoint_step)
        if policy == "final":
            paths = paths[-1:]
        return [CheckpointSpec(lane=lane, fold=fold, step=checkpoint_step(path), path=path) for path in paths]
    ckpt_dir = Path(str(data["checkpoint_dir"]))
    paths = sorted(
        [path for path in ckpt_dir.glob("checkpoint_step*.pt") if checkpoint_step(path) > 0 and checkpoint_step(path) % 500 == 0],
        key=checkpoint_step,
    )
    if policy == "final":
        paths = paths[-1:]
    return [CheckpointSpec(lane=lane, fold=fold, step=checkpoint_step(path), path=path) for path in paths]


def cases_for_fold(fold: int, max_cases: int | None) -> list[str]:
    split = json.loads((RESULT_ROOT / "split_receipt_copy.json").read_text(encoding="utf-8"))
    cases = list(split[f"fold{fold}"]["inner_selection_cases"])
    return cases[:max_cases] if max_cases else cases


def predict_m1(spec: CheckpointSpec, image: np.ndarray, device: torch.device, dim: int) -> np.ndarray:
    model = CARETriModalMyoPSNet().to(device)
    model.load_state_dict(torch.load(spec.path, map_location=device)["model"])
    model.eval()
    pred = np.zeros(tuple(image.shape[1:]), dtype=np.uint8)
    with torch.no_grad():
        for z in range(image.shape[1]):
            crop, bounds = center_crop_or_pad(image[:, z], dim)
            c0 = torch.from_numpy(crop[2:3]).unsqueeze(0).to(device=device, dtype=torch.float32)
            lge = torch.from_numpy(crop[0:1]).unsqueeze(0).to(device=device, dtype=torch.float32)
            t2 = torch.from_numpy(crop[1:2]).unsqueeze(0).to(device=device, dtype=torch.float32)
            _seg_c0, seg_lge, seg_t2 = model(c0, lge, t2)
            scar = torch.argmax(seg_lge, dim=1)[0].detach().cpu().numpy() == 1
            edema = torch.argmax(seg_t2, dim=1)[0].detach().cpu().numpy() == 1
            decoded = np.zeros_like(scar, dtype=np.uint8)
            decoded[edema] = 4
            decoded[scar] = 5
            paste_crop(pred[z], decoded, bounds)
    return pred


def get_m0r_predictor(spec: CheckpointSpec, device: torch.device) -> Any:
    key = (spec.fold, spec.path.name)
    if key in _M0R_PREDICTOR_CACHE:
        return _M0R_PREDICTOR_CACHE[key]

    os_environ = __import__("os").environ
    os_environ["CARE_ROOT"] = str(REPO_ROOT)
    os_environ["nnUNet_raw"] = str(REPO_ROOT / "data/nnUNet/nnUNet_raw")
    os_environ["nnUNet_preprocessed"] = str(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed")
    os_environ["nnUNet_results"] = str(RUNTIME_ROOT / "m0r_faithful_control" / "nnUNet_results")
    os_environ.setdefault("MPLCONFIGDIR", str(RUNTIME_ROOT / "m0r_faithful_control" / "mpl_cache"))

    import nnunetv2.inference.predict_from_raw_data as predict_from_raw_data
    from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

    original_class_finder = predict_from_raw_data.recursive_find_python_class

    def class_finder(folder: str, trainer_name: str, current_module: str) -> Any:
        if trainer_name == "nnUNetTrainerGapClosureM0R4000":
            return nnUNetTrainerGapClosureM0R4000
        return original_class_finder(folder, trainer_name, current_module)

    predict_from_raw_data.recursive_find_python_class = class_finder
    model_folder = spec.path.parent.parent
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=False,
        perform_everything_on_device=True,
        device=device,
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(str(model_folder), use_folds=(spec.fold,), checkpoint_name=spec.path.name)
    _M0R_PREDICTOR_CACHE[key] = predictor
    return predictor


def predict_m0r(spec: CheckpointSpec, image: np.ndarray, device: torch.device) -> np.ndarray:
    predictor = get_m0r_predictor(spec, device)
    with torch.no_grad():
        data = torch.from_numpy(image).to(device=device, dtype=torch.float32)
        logits = predictor.predict_logits_from_preprocessed_data(data).detach().cpu().numpy()
    return np.argmax(logits, axis=0).astype(np.uint8)


def predict_m2(spec: CheckpointSpec, image: np.ndarray, device: torch.device, dim: int) -> np.ndarray:
    model = build_m2_model(device, load_released=False)
    model.load_state_dict(torch.load(spec.path, map_location=device)["model"])
    model.eval()
    pred = np.zeros(tuple(image.shape[1:]), dtype=np.uint8)
    with torch.no_grad():
        for z in range(image.shape[1]):
            crop, bounds = center_crop_or_pad(image[:, z], dim)
            c0 = torch.from_numpy(crop[2:3]).unsqueeze(0).to(device=device, dtype=torch.float32)
            lge = torch.from_numpy(crop[0:1]).unsqueeze(0).to(device=device, dtype=torch.float32)
            t2 = torch.from_numpy(crop[1:2]).unsqueeze(0).to(device=device, dtype=torch.float32)
            compact = torch.argmax(model(c0, lge, t2, False), dim=1)[0].detach().cpu().numpy().astype(np.uint8)
            decoded = np.zeros_like(compact, dtype=np.uint8)
            decoded[compact == 1] = 1
            decoded[compact == 2] = 5
            decoded[compact == 3] = 4
            paste_crop(pred[z], decoded, bounds)
    return pred


def starts(size: int, patch: int, stride: int) -> list[int]:
    if size <= patch:
        return [0]
    out = list(range(0, size - patch + 1, stride))
    if out[-1] != size - patch:
        out.append(size - patch)
    return out


def predict_m3(spec: CheckpointSpec, image: np.ndarray, device: torch.device, patch: tuple[int, int, int]) -> np.ndarray:
    model = CARETargetDomainSpecialist(fold=spec.fold, map_location=device).to(device)
    model.load_state_dict(torch.load(spec.path, map_location=device)["model"])
    model.eval()
    spatial = tuple(int(v) for v in image.shape[1:])
    padded = np.pad(
        image,
        [(0, 0), (0, max(0, patch[0] - spatial[0])), (0, max(0, patch[1] - spatial[1])), (0, max(0, patch[2] - spatial[2]))],
        mode="constant",
    )
    logits_sum = np.zeros((2, *padded.shape[1:]), dtype=np.float32)
    counts = np.zeros(tuple(padded.shape[1:]), dtype=np.float32)
    z_starts = starts(padded.shape[1], patch[0], max(1, patch[0] // 2))
    y_starts = starts(padded.shape[2], patch[1], max(1, patch[1] // 2))
    x_starts = starts(padded.shape[3], patch[2], max(1, patch[2] // 2))
    with torch.no_grad():
        for z in z_starts:
            for y in y_starts:
                for x in x_starts:
                    block = torch.from_numpy(padded[:, z : z + patch[0], y : y + patch[1], x : x + patch[2]]).unsqueeze(0).to(device=device, dtype=torch.float32)
                    out = model(block)
                    scar = F.interpolate(out["scar_logit"], size=patch, mode="trilinear", align_corners=False)[0, 0].detach().cpu().numpy()
                    edema = F.interpolate(out["pure_edema_logit"], size=patch, mode="trilinear", align_corners=False)[0, 0].detach().cpu().numpy()
                    logits_sum[0, z : z + patch[0], y : y + patch[1], x : x + patch[2]] += scar
                    logits_sum[1, z : z + patch[0], y : y + patch[1], x : x + patch[2]] += edema
                    counts[z : z + patch[0], y : y + patch[1], x : x + patch[2]] += 1.0
    logits = logits_sum / np.maximum(counts[None], 1.0)
    logits = logits[:, : spatial[0], : spatial[1], : spatial[2]]
    pred = np.zeros(spatial, dtype=np.uint8)
    edema = logits[1] > 0.0
    scar = logits[0] > 0.0
    pred[edema] = 4
    pred[scar] = 5
    return pred


def mean_optional(rows: Iterable[dict[str, Any]], field: str) -> float | None:
    values = [float(row[field]) for row in rows if row.get(field) is not None]
    return float(np.mean(values)) if values else None


def summarize_subset(lane: str, fold: int | str, step: int, pathology: str, subset: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "lane": lane,
        "fold": fold,
        "checkpoint_step": step,
        "pathology": pathology,
        "case_count": len(subset),
        "dice_mean": mean_optional(subset, "dice"),
        "hd95_vox_mean": mean_optional(subset, "hd95_vox"),
        "exact_hd_vox_mean": mean_optional(subset, "exact_hd_vox"),
        "precision_mean": mean_optional(subset, "precision"),
        "sensitivity_mean": mean_optional(subset, "sensitivity"),
        "lesion_recall_mean": mean_optional(subset, "lesion_recall"),
        "small_lesion_recall_mean": mean_optional(subset, "small_lesion_recall"),
        "remote_fp_count_sum": int(sum(int(r["remote_fp_count"]) for r in subset)),
        "remote_fp_voxels_sum": int(sum(int(r["remote_fp_voxels"]) for r in subset)),
        "blood_pool_adjacent_fp_count_sum": int(sum(int(r["blood_pool_adjacent_fp_count"]) for r in subset)),
        "blood_pool_adjacent_fp_voxels_sum": int(sum(int(r["blood_pool_adjacent_fp_voxels"]) for r in subset)),
        "pred_component_count_sum": int(sum(int(r["pred_component_count"]) for r in subset)),
        "gt_component_count_sum": int(sum(int(r["gt_component_count"]) for r in subset)),
        "volume_ratio_mean": mean_optional(subset, "volume_ratio"),
    }


def metric_for_compare(row: dict[str, Any], field: str, default: float) -> float:
    value = row.get(field)
    return float(value) if value is not None else default


def is_better_global_selection(candidate: dict[str, Any], current: dict[str, Any] | None, pathology: str) -> bool:
    if current is None:
        return True
    cand_dice = metric_for_compare(candidate, "dice_mean", -1.0)
    curr_dice = metric_for_compare(current, "dice_mean", -1.0)
    if abs(cand_dice - curr_dice) > 0.01:
        return cand_dice > curr_dice

    cand_hd95 = metric_for_compare(candidate, "hd95_vox_mean", float("inf"))
    curr_hd95 = metric_for_compare(current, "hd95_vox_mean", float("inf"))
    cand_sens = metric_for_compare(candidate, "sensitivity_mean", -1.0)
    curr_sens = metric_for_compare(current, "sensitivity_mean", -1.0)
    if pathology == "scar":
        if abs(cand_hd95 - curr_hd95) > 1.0:
            return cand_hd95 < curr_hd95
        cand_remote = int(candidate["remote_fp_count_sum"])
        curr_remote = int(current["remote_fp_count_sum"])
        if cand_remote != curr_remote:
            return cand_remote < curr_remote
        cand_remote_vox = int(candidate["remote_fp_voxels_sum"])
        curr_remote_vox = int(current["remote_fp_voxels_sum"])
        if cand_remote_vox != curr_remote_vox:
            return cand_remote_vox < curr_remote_vox
        if cand_sens != curr_sens:
            return cand_sens > curr_sens
    else:
        if abs(cand_sens - curr_sens) > 0.02:
            return cand_sens > curr_sens
        if cand_hd95 != curr_hd95:
            return cand_hd95 < curr_hd95
        cand_volume = abs(metric_for_compare(candidate, "volume_ratio_mean", float("inf")) - 1.0)
        curr_volume = abs(metric_for_compare(current, "volume_ratio_mean", float("inf")) - 1.0)
        if cand_volume != curr_volume:
            return cand_volume < curr_volume
    return int(candidate["checkpoint_step"]) < int(current["checkpoint_step"])


def evaluate(args: argparse.Namespace) -> dict[str, Any]:
    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    lanes = [lane.strip() for lane in args.lanes.split(",") if lane.strip()]
    case_rows: list[dict[str, Any]] = []
    inference_rows: list[dict[str, Any]] = []
    for lane in lanes:
        for fold in (2, 3):
            cases = cases_for_fold(fold, args.max_cases)
            for spec in discover_checkpoints(lane, fold, args.checkpoint_policy):
                for idx, case_id in enumerate(cases, start=1):
                    t0 = time.time()
                    image, label = load_case(case_id)
                    if lane == "m0r_faithful_control":
                        pred = predict_m0r(spec, image, device)
                    elif lane == "m1_myopsnet_l_care":
                        pred = predict_m1(spec, image, device, args.dim)
                    elif lane == "m2_i_mmseg_care":
                        pred = predict_m2(spec, image, device, args.dim)
                    elif lane == "m3_care_tds":
                        pred = predict_m3(spec, image, device, tuple(int(v) for v in args.m3_patch.split(",")))
                    else:
                        raise ValueError(f"unsupported lane for this evaluator: {lane}")
                    case_rows.extend(metric_rows(lane, fold, spec.step, case_id, pred, label))
                    inference_rows.append(
                        {
                            "lane": lane,
                            "fold": fold,
                            "checkpoint_step": spec.step,
                            "case_id": case_id,
                            "status": "COMPLETED",
                            "device": str(device),
                            "elapsed_seconds": round(time.time() - t0, 3),
                            "outer_cases_accessed": False,
                        }
                    )
                    print(json.dumps({"lane": lane, "fold": fold, "checkpoint_step": spec.step, "case": case_id, "index": idx, "total": len(cases)}), flush=True)
    summary_rows: list[dict[str, Any]] = []
    for lane in lanes:
        for fold in (2, 3):
            for step in sorted({int(r["checkpoint_step"]) for r in case_rows if r["lane"] == lane and int(r["fold"]) == fold}):
                for pathology in PATHOLOGIES:
                    subset = [r for r in case_rows if r["lane"] == lane and int(r["fold"]) == fold and int(r["checkpoint_step"]) == step and r["pathology"] == pathology]
                    if not subset:
                        continue
                    summary_rows.append(summarize_subset(lane, fold, step, pathology, subset))
    global_rows: list[dict[str, Any]] = []
    for lane in lanes:
        for step in sorted({int(r["checkpoint_step"]) for r in case_rows if r["lane"] == lane}):
            for pathology in PATHOLOGIES:
                subset = [r for r in case_rows if r["lane"] == lane and int(r["checkpoint_step"]) == step and r["pathology"] == pathology]
                if subset:
                    global_rows.append(summarize_subset(lane, "2+3", step, pathology, subset))
    selection_rows: list[dict[str, Any]] = []
    for lane in lanes:
        for pathology in PATHOLOGIES:
            candidates = [r for r in global_rows if r["lane"] == lane and r["pathology"] == pathology]
            selected: dict[str, Any] | None = None
            for candidate in candidates:
                if is_better_global_selection(candidate, selected, pathology):
                    selected = candidate
            if selected is None:
                continue
            selection_rows.append(
                {
                    **selected,
                    "selection_scope": "global_inner_fold2_fold3",
                    "selection_rule": (
                        "scar:max_dice_tol_0.01_then_lower_hd95_tol_1_then_lower_remote_fp_then_higher_sensitivity_then_earlier_checkpoint"
                        if pathology == "scar"
                        else "edema:max_dice_tol_0.01_then_higher_sensitivity_tol_0.02_then_lower_hd95_then_volume_ratio_closer_1_then_earlier_checkpoint"
                    ),
                    "outer_cases_accessed": False,
                }
            )
    out_dir = RESULT_ROOT / args.output_dir
    write_csv(out_dir / "casewise_metrics.csv", case_rows)
    write_csv(out_dir / "summary_metrics.csv", summary_rows)
    write_csv(out_dir / "global_summary_metrics.csv", global_rows)
    write_csv(out_dir / "selection_candidates.csv", selection_rows)
    write_csv(out_dir / "inference_accounting.csv", inference_rows)
    receipt = {
        "created_at": now_utc(),
        "status": "PASS",
        "lanes": lanes,
        "checkpoint_policy": args.checkpoint_policy,
        "folds": [2, 3],
        "population": "inner_selection_cases_only",
        "outer_cases_accessed": False,
        "casewise_rows": len(case_rows),
        "summary_rows": len(summary_rows),
        "global_summary_rows": len(global_rows),
        "selection_rows": len(selection_rows),
        "m0r_predictor_note": "M0R uses nnUNetPredictor on preprocessed b2nd tensors when lane m0r_faithful_control is requested.",
    }
    write_json(out_dir / "evaluation_receipt.json", receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lanes", default="m2_i_mmseg_care")
    parser.add_argument("--checkpoint-policy", choices=["final", "all"], default="final")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--dim", type=int, default=128)
    parser.add_argument("--m3-patch", default="16,64,64")
    parser.add_argument("--output-dir", default="inner_evaluation")
    parser.add_argument("--cpu", action="store_true")
    args = parser.parse_args()
    payload = evaluate(args)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
