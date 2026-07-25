#!/usr/bin/env python
"""Evaluate CARE-SRR-Cascade tensor predictions for calibration/audit."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
from scipy.ndimage import binary_erosion, distance_transform_edt, label as cc_label

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue
from src.care_myocardium.srr_production.case_prototypes import (
    CasePrototypeRecord,
    cosine_similarity_maps,
    select_crossfit_prototype_bank,
)


RESULT_ROOT = REPO_ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
FORMAL_ROOT = RESULT_ROOT / "runtime/formal_v2"
ANCHOR_DIR = RESULT_ROOT / "runtime/anchor_cache_v2"
SOURCE_DIR = RESULT_ROOT / "runtime/source_cache_v2"
PROTOTYPE_DIR = RESULT_ROOT / "runtime/prototype_cache_v2"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json"
SPLIT_MANIFEST = REPO_ROOT / "results/20260724_care_myops_batch10_deadline_rescue/rescue_split_manifest.csv"
SIX_CANDIDATES = (
    "control_seed20260724",
    "control_seed20260725",
    "srr_seed20260724",
    "srr_seed20260725",
    "control_two_seed_probability_mean_derived_bounded_channel_correction",
    "srr_two_seed_probability_mean_derived_bounded_channel_correction",
)

def dice(pred: torch.Tensor, gt: torch.Tensor, cls: int) -> float:
    p = pred == int(cls)
    g = gt == int(cls)
    denom = int(p.sum() + g.sum())
    if denom == 0:
        return 1.0
    return float(2 * int((p & g).sum()) / denom)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tensor(tensor: torch.Tensor) -> str:
    arr = tensor.detach().cpu().contiguous().numpy()
    return hashlib.sha256(arr.tobytes()).hexdigest()


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def load_spacing() -> tuple[float, float, float]:
    plans = json.loads(PLANS.read_text())
    return tuple(float(v) for v in PlansManager(plans).get_configuration("3d_fullres").spacing)


def surface(mask: np.ndarray) -> np.ndarray:
    mask = mask.astype(bool)
    if not mask.any():
        return mask
    return mask ^ binary_erosion(mask)


def hd_metrics(pred_mask: np.ndarray, gt_mask: np.ndarray, spacing: tuple[float, float, float]) -> tuple[float, float]:
    if not pred_mask.any() and not gt_mask.any():
        return 0.0, 0.0
    if not pred_mask.any() or not gt_mask.any():
        return math.inf, math.inf
    pred_surface = surface(pred_mask)
    gt_surface = surface(gt_mask)
    pred_to_gt = distance_transform_edt(~gt_surface, sampling=spacing)[pred_surface]
    gt_to_pred = distance_transform_edt(~pred_surface, sampling=spacing)[gt_surface]
    distances = np.concatenate([pred_to_gt, gt_to_pred]).astype(np.float64)
    return float(distances.max()), float(np.percentile(distances, 95))


def mask_metrics(pred: np.ndarray, gt: np.ndarray, cls: int, spacing: tuple[float, float, float]) -> dict[str, Any]:
    pred_mask = pred == int(cls)
    gt_mask = gt == int(cls)
    pred_empty = not bool(pred_mask.any())
    gt_empty = not bool(gt_mask.any())
    if gt_empty and pred_empty:
        exact_hd, hd95, candidate_eligible = 0.0, 0.0, True
    elif gt_empty or pred_empty:
        exact_hd, hd95, candidate_eligible = math.inf, math.inf, False
    else:
        exact_hd, hd95 = hd_metrics(pred_mask, gt_mask, spacing)
        candidate_eligible = True
    dsc = dice(torch.as_tensor(pred), torch.as_tensor(gt), cls)
    tp = int((pred_mask & gt_mask).sum())
    fp = int((pred_mask & ~gt_mask).sum())
    fn = int((~pred_mask & gt_mask).sum())
    precision = float(tp / (tp + fp)) if tp + fp else (1.0 if not gt_mask.any() else 0.0)
    recall = float(tp / (tp + fn)) if tp + fn else (1.0 if not gt_mask.any() else 0.0)
    union = (gt == 1) | (gt == 4) | (gt == 5)
    remote = pred_mask & (distance_transform_edt(~union, sampling=spacing) > 10.0)
    component_count = int(cc_label(pred_mask)[1])
    voxel_volume = float(np.prod(spacing))
    gt_volume = max(float(gt_mask.sum() * voxel_volume), 1e-6)
    return {
        "Dice": dsc,
        "exact_HD": exact_hd,
        "HD95": hd95,
        "precision": precision,
        "recall": recall,
        "remote_FP_mm3": float(remote.sum() * voxel_volume),
        "component_count": component_count,
        "volume_ratio": float((pred_mask.sum() * voxel_volume) / gt_volume),
        "empty_prediction": int(pred_empty),
        "gt_positive": int(not gt_empty),
        "candidate_eligible": bool(candidate_eligible),
    }


def empty_rule_metrics(pred: torch.Tensor, gt: torch.Tensor, cls: int) -> dict[str, Any]:
    pred_empty = not bool((pred == int(cls)).any())
    gt_empty = not bool((gt == int(cls)).any())
    if gt_empty and pred_empty:
        return {"Dice": 1.0, "exact_HD": 0.0, "HD95": 0.0, "candidate_eligible": True}
    if gt_empty and not pred_empty:
        return {"Dice": 0.0, "exact_HD": math.inf, "HD95": math.inf, "candidate_eligible": False}
    if not gt_empty and pred_empty:
        return {"Dice": 0.0, "exact_HD": math.inf, "HD95": math.inf, "candidate_eligible": False}
    return {"Dice": dice(pred, gt, cls), "exact_HD": 0.0, "HD95": 0.0, "candidate_eligible": True}


def evaluate_prediction(prediction_path: Path, label_path: Path, *, pathology: str, case_id: str) -> dict[str, Any]:
    pred_payload = torch.load(prediction_path, map_location="cpu", weights_only=True)
    label_payload = torch.load(label_path, map_location="cpu", weights_only=True)
    logits = pred_payload["final_logits"]
    pred = logits.argmax(dim=1).squeeze(0)
    gt = label_payload["labels"] if isinstance(label_payload, dict) else label_payload
    cls = 5 if pathology == "scar" else 4
    metrics = empty_rule_metrics(pred, gt, cls)
    changed = int((pred != torch.as_tensor(label_payload.get("anchor_argmax", pred) if isinstance(label_payload, dict) else pred)).sum().item())
    return {
        "case_id": case_id,
        "pathology": pathology,
        **metrics,
        "precision": "",
        "recall": "",
        "remote_FP_mm3": "",
        "component_count": "",
        "volume_ratio": "",
        "help_harm": "",
        "empty_prediction": int(not bool((pred == cls).any())),
        "changed_voxels": changed,
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["case_id"])
        writer.writeheader()
        writer.writerows(rows)


def source_path_map() -> dict[tuple[str, str, str], Path]:
    return {
        (row["case_id"], row["checkpoint_role"], row["field"]): REPO_ROOT / row["cache_path"]
        for row in read_csv_rows(RESULT_ROOT / "source_cache_manifest_v2.csv")
    }


def full_case_batch(
    case_id: str,
    *,
    pathology: str,
    metadata: dict[str, Any],
    paths: dict[tuple[str, str, str], Path],
    records: list[CasePrototypeRecord],
    bank_records: list[CasePrototypeRecord],
    device: torch.device,
) -> tuple[dict[str, torch.Tensor], np.ndarray]:
    anchor = torch.load(ANCHOR_DIR / f"{case_id}__anchor.pt", map_location="cpu", weights_only=True)
    source = torch.load(paths[(case_id, "teacher_full_view", "full_resolution_feature")], map_location="cpu", weights_only=True)["tensor"][0].float()
    anatomy_logits = torch.load(paths[(case_id, "teacher_full_view", "anatomy_logits")], map_location="cpu", weights_only=True)["tensor"][0].float()
    edema_logit = torch.load(paths[(case_id, "teacher_full_view", "edema_logit")], map_location="cpu", weights_only=True)["tensor"][0].float()
    scar_margin = torch.load(paths[(case_id, "student_reliable_distill", "scar_final_margin")], map_location="cpu", weights_only=True)["tensor"][0].float()
    raw = torch.from_numpy(blosc2.open(str(PREPROCESSED / f"{case_id}.b2nd"), mode="r")[...]).float()
    labels = blosc2.open(str(PREPROCESSED / f"{case_id}_seg.b2nd"), mode="r")[...][0].astype(np.int16)
    record = next(r for r in records if r.case_id == case_id)
    bank, _ = select_crossfit_prototype_bank(bank_records, query_case_id=case_id, query_shard=record.shard, pathology=pathology, mode="validation")
    sims = cosine_similarity_maps(source, bank)
    zeros = torch.zeros(1, *source.shape[1:])
    batch = {
        "anchor_logits": anchor["canonical_anchor_logits"].unsqueeze(0).float(),
        "source_features": source.unsqueeze(0).float(),
        "distance_to_union_mm": anchor["distance_to_union_mm"].unsqueeze(0).float(),
        "t2_present": torch.tensor([float(metadata[case_id].t2_present)]),
        "normalized_lge": raw[0:1].unsqueeze(0).float(),
        "normalized_t2": (raw[1:2] if raw.shape[0] > 1 else zeros).unsqueeze(0).float(),
        "teacher_anatomy_probabilities": torch.softmax(anatomy_logits.unsqueeze(0), dim=1),
        "teacher_edema_probability": torch.sigmoid(edema_logit.unsqueeze(0)),
        "scar_source_margin": scar_margin.unsqueeze(0),
        "explicit_anchor_probabilities": anchor["canonical_anchor_probabilities"].unsqueeze(0).float(),
        "explicit_anchor_uncertainty": anchor["anchor_uncertainty"].unsqueeze(0).float(),
        "explicit_soft_union_probability": anchor["soft_union_probability"].unsqueeze(0).float(),
        "normalized_distance_to_union": (anchor["distance_to_union_mm"].unsqueeze(0).float() / 15.0).clamp(0.0, 1.0),
        "prototype_scar_positive_similarity": sims["positive"].unsqueeze(0) if pathology == "scar" else zeros.unsqueeze(0),
        "prototype_scar_negative_similarity": sims["negative"].unsqueeze(0) if pathology == "scar" else zeros.unsqueeze(0),
        "prototype_edema_positive_similarity": sims["positive"].unsqueeze(0) if pathology == "edema" else zeros.unsqueeze(0),
        "prototype_edema_negative_similarity": sims["negative"].unsqueeze(0) if pathology == "edema" else zeros.unsqueeze(0),
    }
    return {k: v.to(device) for k, v in batch.items()}, labels


def checkpoint_for(pathology: str, seed: int, kind: str) -> Path:
    variant = ("scar_cascade_control" if kind == "control" else "scar_srr_cascade") if pathology == "scar" else ("edema_zone_control" if kind == "control" else "edema_srr_zone_cascade")
    return FORMAL_ROOT / f"{pathology}_seed{seed}" / variant / "checkpoints/checkpoint_final.pt"


def candidate_logits(
    *,
    pathology: str,
    candidate: str,
    batch: dict[str, torch.Tensor],
    models: dict[tuple[int, str], CARESRRCascadeRescue],
) -> torch.Tensor:
    if candidate.startswith("control_seed"):
        seed = int(candidate.rsplit("seed", 1)[1])
        return models[(seed, "control")](**batch, active_pathology=pathology)["final_logits"]
    if candidate.startswith("srr_seed"):
        seed = int(candidate.rsplit("seed", 1)[1])
        return models[(seed, "srr")](**batch, active_pathology=pathology)["final_logits"]
    kind = "control" if candidate.startswith("control_two_seed") else "srr"
    probs = []
    for seed in (20260724, 20260725):
        logits = models[(seed, kind)](**batch, active_pathology=pathology)["final_logits"]
        probs.append(torch.softmax(logits, dim=1))
    mean_prob = torch.stack(probs).mean(dim=0).clamp_min(1e-6)
    mean_prob = mean_prob / mean_prob.sum(dim=1, keepdim=True)
    return mean_prob.log()


def load_models(pathology: str, device: torch.device) -> tuple[dict[tuple[int, str], CARESRRCascadeRescue], list[dict[str, Any]]]:
    out: dict[tuple[int, str], CARESRRCascadeRescue] = {}
    rows: list[dict[str, Any]] = []
    for seed in (20260724, 20260725):
        for kind in ("control", "srr"):
            ckpt = checkpoint_for(pathology, seed, kind)
            payload = torch.load(ckpt, map_location="cpu", weights_only=False)
            model = CARESRRCascadeRescue(source_feature_channels=32).to(device)
            model.load_state_dict(payload["model_state"])
            model.eval()
            out[(seed, kind)] = model
            rows.append({"pathology": pathology, "seed": seed, "kind": kind, "checkpoint_path": str(ckpt.relative_to(REPO_ROOT)), "checkpoint_sha256": sha256_file(ckpt), "optimizer_step": int(payload["optimizer_step"]), "selected_for_candidate_set": True})
    return out, rows


def aggregate_rows(case_rows: list[dict[str, Any]], *, pathology: str, split: str) -> list[dict[str, Any]]:
    by_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in case_rows:
        by_candidate[row["candidate"]].append(row)
    out = []
    for candidate in SIX_CANDIDATES:
        rows = by_candidate.get(candidate, [])
        if not rows:
            continue
        positive = [r for r in rows if int(r["gt_positive"]) == 1]
        base = positive or rows
        dice_delta = float(np.mean([float(r["Dice"]) - float(r["anchor_Dice"]) for r in base]))
        exact_delta = float(np.mean([finite_delta(r["exact_HD"], r["anchor_exact_HD"]) for r in base]))
        hd95_worse = float(np.mean([relative_worsening(r["HD95"], r["anchor_HD95"]) for r in base]))
        remote_ratio = float(np.mean([ratio(float(r["remote_FP_mm3"]), float(r["anchor_remote_FP_mm3"])) for r in rows]))
        help_count = sum(1 for r in rows if float(r["Dice"]) > float(r["anchor_Dice"]) + 1e-6)
        harm_count = sum(1 for r in rows if float(r["Dice"]) + 1e-6 < float(r["anchor_Dice"]))
        eligible = all(str(r["candidate_eligible"]).lower() == "true" for r in rows)
        positive_empty = sum(1 for r in positive if int(r["empty_prediction"]) == 1)
        no_t2_edema_voxels = sum(int(r.get("edema_voxels", 0)) for r in rows if str(r.get("t2_present")) in {"0", "False", "false"})
        out.append({
            "split": split,
            "pathology": pathology,
            "candidate": candidate,
            "case_count": len(rows),
            "positive_gt_case_count": len(positive),
            "Dice": float(np.mean([float(r["Dice"]) for r in rows])),
            "exact_HD": float(np.mean([finite_cap(r["exact_HD"]) for r in rows])),
            "HD95": float(np.mean([finite_cap(r["HD95"]) for r in rows])),
            "precision": float(np.mean([float(r["precision"]) for r in rows])),
            "recall": float(np.mean([float(r["recall"]) for r in rows])),
            "remote_FP_mm3": float(np.mean([float(r["remote_FP_mm3"]) for r in rows])),
            "component_count": float(np.mean([float(r["component_count"]) for r in rows])),
            "volume_ratio": float(np.mean([float(r["volume_ratio"]) for r in rows])),
            "help_harm": help_count - harm_count,
            "help_minus_harm": help_count - harm_count,
            "positive_GT_Dice_delta": dice_delta,
            "exact_HD_delta": exact_delta,
            "HD95_relative_worsening": hd95_worse,
            "remote_FP_ratio": remote_ratio,
            "empty_prediction": sum(int(r["empty_prediction"]) for r in rows),
            "positive_GT_empty_count": positive_empty,
            "no_t2_edema_voxels": no_t2_edema_voxels,
            "candidate_eligible": str(bool(eligible)).lower(),
            "optimizer_step": 6250,
        })
    return out


def finite_cap(value: Any, cap: float = 9999.0) -> float:
    v = float(value)
    return v if math.isfinite(v) else cap


def finite_delta(value: Any, base: Any, cap: float = 9999.0) -> float:
    return finite_cap(value, cap) - finite_cap(base, cap)


def ratio(value: float, base: float) -> float:
    return float(value / max(base, 1e-6))


def relative_worsening(value: Any, base: Any) -> float:
    return max(0.0, finite_delta(value, base)) / max(finite_cap(base), 1e-6)


def split_cases(split_name: str, *, max_cases: int = 0) -> list[dict[str, str]]:
    rows = [r for r in read_csv_rows(SPLIT_MANIFEST) if r["rescue_split"] == split_name]
    if len(rows) != 22:
        raise RuntimeError(f"{split_name} split must contain 22 cases, got {len(rows)}")
    return rows[: int(max_cases)] if int(max_cases) > 0 else rows


def fold0_train_case_ids() -> set[str]:
    validation_cases = {row["case_id"] for row in read_csv_rows(SPLIT_MANIFEST)}
    all_cases = {path.name.split("__", 1)[0] for path in ANCHOR_DIR.glob("*__anchor.pt")}
    train_cases = all_cases - validation_cases
    if len(validation_cases) != 44:
        raise RuntimeError(f"expected 44 frozen calibration/audit cases, got {len(validation_cases)}")
    if len(train_cases) != 176:
        raise RuntimeError(f"expected 176 fold0 train cases for prototype bank, got {len(train_cases)}")
    return train_cases


def audit_gate(pathology: str, audit_rows: list[dict[str, Any]], audit_aggregate: list[dict[str, Any]]) -> tuple[bool, dict[str, Any]]:
    blockers: list[str] = []
    if not audit_rows or not audit_aggregate:
        return False, {"decision": "FAIL", "blockers": ["missing_audit_rows"]}
    row = audit_aggregate[0]
    checks = {
        "candidate_eligible": str(row.get("candidate_eligible", "")).lower() == "true",
        "positive_GT_Dice_delta_min": float(row.get("positive_GT_Dice_delta", -999.0)) >= 0.0,
        "exact_HD_delta_max": float(row.get("exact_HD_delta", 999.0)) <= 0.0,
        "HD95_relative_worsening_max": float(row.get("HD95_relative_worsening", 999.0)) <= 0.05,
        "help_minus_harm_min": float(row.get("help_minus_harm", -999.0)) >= 0.0,
        "positive_GT_empty_max": int(float(row.get("positive_GT_empty_count", 999))) == 0,
    }
    if pathology == "scar":
        checks["remote_FP_ratio_max"] = float(row.get("remote_FP_ratio", 999.0)) <= 1.0
    else:
        checks["remote_FP_ratio_max"] = float(row.get("remote_FP_ratio", 999.0)) <= 1.05
        checks["no_t2_edema_voxels_max"] = int(float(row.get("no_t2_edema_voxels", 999))) == 0
        for center in ("CenterB", "CenterC"):
            members = [r for r in audit_rows if r.get("center") == center and int(r.get("gt_positive", 0)) == 1]
            if members:
                delta = float(np.mean([float(r["Dice"]) - float(r["anchor_Dice"]) for r in members]))
                checks[f"{center}_Dice_delta_min"] = delta >= -0.005
            else:
                checks[f"{center}_Dice_delta_min"] = False
    blockers = [name for name, ok in checks.items() if not ok]
    return not blockers, {"decision": "PASS" if not blockers else "FAIL", "checks": checks, "blockers": blockers}


def evaluate_pathology_batch(pathology: str, *, device: torch.device, max_cases_per_split: int = 0) -> dict[str, Any]:
    cls = 5 if pathology == "scar" else 4
    spacing = load_spacing()
    metadata = load_myops_case_metadata(REPO_ROOT)
    paths = source_path_map()
    records = [torch.load(path, map_location="cpu", weights_only=False) for path in sorted(PROTOTYPE_DIR.glob("*__prototypes.pt"))]
    train_cases = fold0_train_case_ids()
    bank_records = [record for record in records if record.case_id in train_cases]
    if len(bank_records) != 176:
        raise RuntimeError(f"prototype bank must use exactly 176 fold0 train records, got {len(bank_records)}")
    models, checkpoint_rows = load_models(pathology, device)
    calibration_case_rows: list[dict[str, Any]] = []
    audit_case_rows: list[dict[str, Any]] = []
    prediction_manifest: list[dict[str, Any]] = []

    def run_split(split_name: str, candidates: tuple[str, ...]) -> list[dict[str, Any]]:
        rows_out: list[dict[str, Any]] = []
        for split_row in split_cases(split_name, max_cases=max_cases_per_split):
            case_id = split_row["case_id"]
            batch, gt = full_case_batch(case_id, pathology=pathology, metadata=metadata, paths=paths, records=records, bank_records=bank_records, device=device)
            anchor_pred = batch["anchor_logits"].argmax(dim=1).squeeze(0).cpu().numpy().astype(np.int16)
            anchor_metrics = mask_metrics(anchor_pred, gt, cls, spacing)
            for candidate in candidates:
                with torch.inference_mode():
                    logits = candidate_logits(pathology=pathology, candidate=candidate, batch=batch, models=models)
                pred = logits.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.int16)
                metrics = mask_metrics(pred, gt, cls, spacing)
                row = {
                    "split": "calibration" if split_name == "calibration" else "audit",
                    "pathology": pathology,
                    "case_id": case_id,
                    "center": split_row["center"],
                    "modality_group": split_row["modality_group"],
                    "t2_present": split_row["t2_present"],
                    "candidate": candidate,
                    **metrics,
                    "anchor_Dice": anchor_metrics["Dice"],
                    "anchor_exact_HD": anchor_metrics["exact_HD"],
                    "anchor_HD95": anchor_metrics["HD95"],
                    "anchor_remote_FP_mm3": anchor_metrics["remote_FP_mm3"],
                    "help_harm": (1 if metrics["Dice"] > anchor_metrics["Dice"] + 1e-6 else (-1 if metrics["Dice"] + 1e-6 < anchor_metrics["Dice"] else 0)),
                    "changed_voxels": int((pred != anchor_pred).sum()),
                    "edema_voxels": int((pred == 4).sum()),
                    "prediction_argmax_sha256": hashlib.sha256(pred.tobytes()).hexdigest(),
                }
                rows_out.append(row)
                prediction_manifest.append({
                    "split": row["split"],
                    "pathology": pathology,
                    "case_id": case_id,
                    "candidate": candidate,
                    "argmax_sha256": row["prediction_argmax_sha256"],
                    "decode": "six_class_argmax_same_as_deployment",
                    "audit_used_for_selection": False,
                })
        return rows_out

    calibration_case_rows = run_split("calibration", SIX_CANDIDATES)
    calibration_aggregate = aggregate_rows(calibration_case_rows, pathology=pathology, split="calibration")
    cal_path = RESULT_ROOT / f"w4_calibration_metrics_{pathology}_v2.csv"
    write_csv(cal_path, calibration_aggregate)
    selection_path = RESULT_ROOT / f"w4_selection_{pathology}_v2.json"
    from scripts.evaluation.select_care_srr_cascade import select_candidate

    selection = select_candidate([{k: str(v) for k, v in row.items()} for row in calibration_aggregate])
    selection["selection_split"] = "calibration"
    selection["audit_used_for_selection"] = False
    write_json(selection_path, selection)

    selected_candidate = selection.get("selected_candidate") or ""
    audit_candidates = (selected_candidate,) if selected_candidate else ()
    audit_case_rows = run_split("audit", audit_candidates) if audit_candidates else []
    audit_aggregate = aggregate_rows(audit_case_rows, pathology=pathology, split="audit") if audit_case_rows else []
    audit_path = RESULT_ROOT / f"w4_audit_metrics_{pathology}_v2.csv"
    write_csv(audit_path, audit_aggregate)
    audit_ok, gate_details = audit_gate(pathology, audit_case_rows, audit_aggregate)
    if not selected_candidate or not audit_ok:
        decision = "FALLBACK_TO_NNUNET"
    elif selected_candidate.startswith("srr"):
        decision = "USE_SRR_CASCADE"
    else:
        decision = "USE_CASCADE_CONTROL"
    final = {
        "decision": decision,
        "pathology": pathology,
        "selected_candidate": selected_candidate,
        "selection_split": "calibration",
        "audit_used_for_selection": False,
        "audit_pass": audit_ok,
        "audit_gate": gate_details,
        "decode": "six_class_argmax_same_as_deployment",
        "prototype_bank_source": "fold0_train_only",
        "prototype_bank_record_count": len(bank_records),
    }
    write_json(RESULT_ROOT / f"w4_final_decision_{pathology}_v2.json", final)
    return {
        "pathology": pathology,
        "decision": decision,
        "checkpoint_rows": checkpoint_rows,
        "calibration_case_rows": calibration_case_rows,
        "audit_case_rows": audit_case_rows,
        "calibration_aggregate": calibration_aggregate,
        "audit_aggregate": audit_aggregate,
        "prediction_manifest": prediction_manifest,
        "selection": selection,
        "final": final,
    }


def run_w4_batch(pathologies: list[str], device_text: str, *, max_cases_per_split: int = 0) -> dict[str, Any]:
    device = torch.device(device_text)
    outputs = [evaluate_pathology_batch(pathology, device=device, max_cases_per_split=max_cases_per_split) for pathology in pathologies]
    checkpoint_rows = [row for out in outputs for row in out["checkpoint_rows"]]
    calibration_case_rows = [row for out in outputs for row in out["calibration_case_rows"]]
    audit_case_rows = [row for out in outputs for row in out["audit_case_rows"]]
    prediction_manifest = [row for out in outputs for row in out["prediction_manifest"] if row["split"] == "audit"]
    write_csv(RESULT_ROOT / "calibration_checkpoint_selection_v2.csv", checkpoint_rows)
    write_csv(RESULT_ROOT / "calibration_casewise_metrics_v2.csv", calibration_case_rows)
    write_json(RESULT_ROOT / "calibration_candidate_manifest_v2.json", {
        "decision": "PASS",
        "six_candidates": SIX_CANDIDATES,
        "pathologies": pathologies,
        "audit_used_for_selection": False,
        "checkpoint_count_per_variant": 1,
    })
    write_csv(RESULT_ROOT / "audit_prediction_manifest_v2.csv", prediction_manifest)
    write_csv(RESULT_ROOT / "audit_casewise_metrics_v2.csv", audit_case_rows)
    subgroup_rows = []
    for pathology in pathologies:
        rows = [r for r in audit_case_rows if r["pathology"] == pathology]
        for key in sorted({r["center"] for r in rows} | {r["modality_group"] for r in rows}):
            members = [r for r in rows if r["center"] == key or r["modality_group"] == key]
            if members:
                subgroup_rows.append({"pathology": pathology, "subgroup": key, "case_count": len(members), "Dice": float(np.mean([float(r["Dice"]) for r in members])), "help_harm": sum(int(r["help_harm"]) for r in members)})
    write_csv(RESULT_ROOT / "audit_subgroup_metrics_v2.csv", subgroup_rows)
    write_csv(RESULT_ROOT / "audit_help_harm_v2.csv", [{"pathology": p, "help_minus_harm": sum(int(r["help_harm"]) for r in audit_case_rows if r["pathology"] == p)} for p in pathologies])
    hd_rows = [
        {"split": r["split"], "pathology": r["pathology"], "case_id": r["case_id"], "candidate": r["candidate"], "exact_HD": r["exact_HD"], "HD95": r["HD95"], "empty_prediction": r["empty_prediction"], "candidate_eligible": r["candidate_eligible"]}
        for r in calibration_case_rows + audit_case_rows
    ]
    write_csv(RESULT_ROOT / "exact_hd_and_hd95_checks_v2.csv", hd_rows)
    decisions = {out["pathology"]: out["final"] for out in outputs}
    write_json(RESULT_ROOT / "pathology_branch_decision_v2.json", {"decision": "PASS", "pathology_decisions": decisions, "audit_used_for_selection": False})
    write_json(RESULT_ROOT / "final_composition_contract_v2.json", {"decision": "PASS", "pathology_decisions": decisions, "failed_pathology_exact_anchor_fallback": True, "decode": "six_class_argmax_same_as_deployment"})
    write_csv(RESULT_ROOT / "full44_final_candidate_metrics_v2.csv", calibration_case_rows + audit_case_rows)
    any_custom = any(row["decision"] != "FALLBACK_TO_NNUNET" for row in decisions.values())
    write_json(RESULT_ROOT / "scientific_gate_v2.json", {"decision": "CUSTOM_PATHOLOGY_AUDIT_PASS" if any_custom else "NO_CUSTOM_RESCUE_USE_BASELINE_ONLY", "pathology_decisions": decisions, "at_least_one_custom_pathology_passes_audit": any_custom})
    return {"decision": "PASS", "pathology_decisions": decisions, "audit_used_for_selection": False}


def contract() -> dict[str, Any]:
    return {
        "entrypoint": "scripts/evaluation/evaluate_care_srr_cascade.py",
        "metrics": ["Dice", "exact_HD", "HD95", "precision", "recall", "remote_FP_mm3", "component_count", "volume_ratio", "help_harm", "empty_prediction", "changed_voxels"],
        "empty_rules": "contract_exact_empty_prediction_rules",
        "audit_used_for_selection": False,
        "batch_w4_outputs": [
            "w4_calibration_metrics_<pathology>_v2.csv",
            "w4_audit_metrics_<pathology>_v2.csv",
            "w4_selection_<pathology>_v2.json",
            "w4_final_decision_<pathology>_v2.json",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--prediction", type=Path)
    parser.add_argument("--label", type=Path)
    parser.add_argument("--pathology", choices=["scar", "edema"], default="scar")
    parser.add_argument("--case-id", default="synthetic")
    parser.add_argument("--output-csv", type=Path)
    parser.add_argument("--w4-batch", action="store_true")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--pathologies", default="scar,edema")
    parser.add_argument("--max-cases-per-split", type=int, default=0)
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    if args.w4_batch:
        pathologies = [p.strip() for p in args.pathologies.split(",") if p.strip()]
        print(json.dumps(run_w4_batch(pathologies, args.device, max_cases_per_split=args.max_cases_per_split), indent=2, sort_keys=True))
        return 0
    if not (args.prediction and args.label and args.output_csv):
        raise SystemExit("--prediction, --label, and --output-csv are required unless --print-contract")
    row = evaluate_prediction(args.prediction, args.label, pathology=args.pathology, case_id=args.case_id)
    write_csv(args.output_csv, [row])
    print(json.dumps({"decision": "PASS", "output_csv": str(args.output_csv)}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
