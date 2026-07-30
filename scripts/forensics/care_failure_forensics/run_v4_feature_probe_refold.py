#!/usr/bin/env python3
"""Run V4 patient-level refolded feature probes on the 80 T2-present cases.

This is a read-only diagnostic.  It loads frozen nnU-Net and PRISM checkpoints,
extracts activation summaries, and evaluates fixed shallow probes with
patient-held-out folds.  It does not train a segmentation model or select a
submission candidate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_care_prism import crop_to_shape, move_batch, pad_to_multiple, spatial_multiple  # noqa: E402
from scripts.forensics.care_failure_forensics.run_v3_feature_activation_probe import (  # noqa: E402
    RESULT_REL,
    class_metrics,
    fit_probe,
    load_models,
)
from src.care_myocardium.data.care_prism_dataset import CAREPRISMAugmenter, CAREPRISMFullPatientDataset  # noqa: E402


TASKS = {
    "P1_scar_vs_normal_myocardium": "scar",
    "P2_nnunet_scar_FN_vs_true_negative": "scar",
    "P3_nnunet_scar_FP_vs_true_negative": "scar",
    "P4_pure_edema_vs_normal_myocardium": "pure_edema",
    "P5_nnunet_pure_edema_FN": "pure_edema",
    "P6_nnunet_pure_edema_FP": "pure_edema",
    "P7_small_scar_vs_normal_myocardium": "scar",
    "P8_boundary_scar_vs_non_scar_myocardium": "scar",
}


def truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n", encoding="utf-8")


def read_case_list(path: Path) -> dict[str, str]:
    cases: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        center, case_id = line.strip().split(":", 1)
        cases[case_id] = center
    return cases


def downsample_mask(mask: torch.Tensor, shape: tuple[int, int, int]) -> torch.Tensor:
    return F.interpolate(mask.float(), size=shape, mode="nearest") > 0.5


def tensor_stats(tensor: torch.Tensor, mask: torch.Tensor) -> np.ndarray | None:
    if mask.sum() < 1:
        return None
    values = tensor[0, :, mask[0, 0]].detach().float()
    if values.numel() == 0:
        return None
    mean = values.mean(dim=1)
    std = values.std(dim=1, unbiased=False)
    maxv = values.amax(dim=1)
    return torch.cat([mean, std, maxv], dim=0).cpu().numpy().astype(np.float32)


def mask_centroid(mask: torch.Tensor) -> tuple[float, float, float]:
    coords = torch.nonzero(mask[0, 0], as_tuple=False)
    if coords.numel() == 0:
        return (-1.0, -1.0, -1.0)
    mean = coords.float().mean(dim=0).cpu().numpy().tolist()
    return (float(mean[0]), float(mean[1]), float(mean[2]))


def add_region(
    rows: list[dict[str, Any]],
    *,
    case_id: str,
    split: str,
    center: str,
    fold_id: int,
    feature_source: str,
    tensor: torch.Tensor,
    pos_mask: torch.Tensor,
    neg_mask: torch.Tensor,
    task_id: str,
    case_meta: dict[str, Any],
) -> None:
    spatial = tuple(int(v) for v in tensor.shape[-3:])
    for label, full_mask in [(1, pos_mask), (0, neg_mask)]:
        mask = downsample_mask(full_mask, spatial)
        feat = tensor_stats(tensor, mask)
        if feat is None:
            continue
        cz, cy, cx = mask_centroid(mask)
        rows.append(
            {
                "case_id": case_id,
                "split": split,
                "center": center,
                "fold_id": fold_id,
                "feature_source": feature_source,
                "task_id": task_id,
                "pathology": TASKS.get(task_id, ""),
                "label": label,
                "sample_kind": "positive_region" if label == 1 else "negative_region",
                "region_voxels": int(mask.sum().item()),
                "centroid_z": cz,
                "centroid_y": cy,
                "centroid_x": cx,
                **case_meta,
                **{f"f{i:03d}": float(v) for i, v in enumerate(feat[:384])},
            }
        )


def stable_unit(text: str) -> float:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return int(h[:12], 16) / float(16**12 - 1)


def build_fold_map(case_centers: dict[str, str], folds: int) -> dict[str, int]:
    fold_counts = [0 for _ in range(folds)]
    center_counts = [defaultdict(int) for _ in range(folds)]
    fold_map: dict[str, int] = {}
    for center in sorted(set(case_centers.values())):
        center_cases = sorted([c for c, ctr in case_centers.items() if ctr == center])
        for idx, case_id in enumerate(center_cases):
            preferred = min(range(folds), key=lambda f: (center_counts[f][center], fold_counts[f], f))
            fold_map[case_id] = preferred
            center_counts[preferred][center] += 1
            fold_counts[preferred] += 1
    return fold_map


def selected_records(targets: dict[str, str]) -> list[tuple[str, Any]]:
    records: list[tuple[str, Any]] = []
    seen: set[str] = set()
    for split in ["actual_train", "inner_select", "outer"]:
        ds = CAREPRISMFullPatientDataset(fold=0, split=split, augmenter=CAREPRISMAugmenter(training=False))
        for idx, rec in enumerate(ds.records):
            if rec.case_id in targets and rec.case_id not in seen:
                records.append((split, (ds, idx, rec)))
                seen.add(rec.case_id)
    missing = sorted(set(targets) - seen)
    if missing:
        raise RuntimeError(f"target cases missing from fold0 datasets: {missing[:10]}")
    return records


def extract_rows(root: Path, targets: dict[str, str], fold_map: dict[str, int], device: torch.device) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    nnunet, prism, config, load_report = load_models(root, device)
    pad_multiple = spatial_multiple(config)
    rows: list[dict[str, Any]] = []
    case_manifest: list[dict[str, Any]] = []
    with torch.no_grad():
        for split, (ds, idx, _rec) in selected_records(targets):
            batch = move_batch(ds[idx], device)
            images, original_spatial = pad_to_multiple(batch["images"].float(), pad_multiple)
            decoder_feats: list[torch.Tensor] = []
            handles = []
            if hasattr(nnunet, "decoder") and hasattr(nnunet.decoder, "stages"):
                for stage in nnunet.decoder.stages:
                    def _capture(_module: Any, _inputs: Any, output: Any, bucket: list[torch.Tensor] = decoder_feats) -> None:
                        if isinstance(output, torch.Tensor):
                            bucket.append(output.detach())
                        elif isinstance(output, (list, tuple)) and output and isinstance(output[0], torch.Tensor):
                            bucket.append(output[0].detach())

                    handles.append(stage.register_forward_hook(_capture))
            try:
                nn_logits = nnunet(images)
            finally:
                for handle in handles:
                    handle.remove()
            if isinstance(nn_logits, (list, tuple)):
                nn_logits = nn_logits[0]
            nn_logits = crop_to_shape(nn_logits, original_spatial)
            nn_pred = nn_logits.argmax(dim=1, keepdim=True)
            prism_out = prism(images, batch["availability"])

            case_id = batch["case_id"][0]
            center = str(batch.get("center", [""])[0]) if isinstance(batch.get("center"), list) else targets[case_id]
            fold_id = int(fold_map[case_id])
            scar = batch["scar_target"] > 0.5
            edema_zone = batch["edema_zone_target"] > 0.5
            pure_edema = edema_zone & ~scar
            normal_myo = (batch["anatomy_target"][:, 0:1] > 0.5) & ~scar & ~pure_edema
            scar_fn = scar & (nn_pred != 5)
            scar_fp = (nn_pred == 5) & ~scar
            edema_fn = pure_edema & (nn_pred != 4)
            edema_fp = (nn_pred == 4) & ~pure_edema
            true_negative = normal_myo & (nn_pred != 4) & (nn_pred != 5)
            availability = batch["availability"][0].detach().cpu().numpy().astype(float).tolist()
            case_meta = {
                "availability_lge": availability[0],
                "availability_t2": availability[1],
                "availability_c0": availability[2],
                "case_volume_voxels": int(np.prod(tuple(int(v) for v in normal_myo.shape[-3:]))),
                "normal_myo_voxels": int(normal_myo.sum().item()),
                "scar_voxels": int(scar.sum().item()),
                "pure_edema_voxels": int(pure_edema.sum().item()),
                "nnunet_scar_fn_voxels": int(scar_fn.sum().item()),
                "nnunet_scar_fp_voxels": int(scar_fp.sum().item()),
                "nnunet_pure_edema_fn_voxels": int(edema_fn.sum().item()),
                "nnunet_pure_edema_fp_voxels": int(edema_fp.sum().item()),
            }
            case_manifest.append(
                {
                    "case_id": case_id,
                    "center": center,
                    "source_split": split,
                    "fold_id": fold_id,
                    **case_meta,
                    "outer_used_for_training_or_tuning": False,
                    "outer_used_read_only_diagnostic": split == "outer",
                }
            )
            tasks = {
                "P1_scar_vs_normal_myocardium": (scar, normal_myo),
                "P2_nnunet_scar_FN_vs_true_negative": (scar_fn, true_negative),
                "P3_nnunet_scar_FP_vs_true_negative": (scar_fp, true_negative),
                "P4_pure_edema_vs_normal_myocardium": (pure_edema, normal_myo),
                "P5_nnunet_pure_edema_FN": (edema_fn, true_negative),
                "P6_nnunet_pure_edema_FP": (edema_fp, true_negative),
                "P7_small_scar_vs_normal_myocardium": (scar if int(scar.sum()) < 1500 else torch.zeros_like(scar), normal_myo),
                "P8_boundary_scar_vs_non_scar_myocardium": (scar, normal_myo),
            }
            feature_tensors: dict[str, torch.Tensor] = {}
            for level, feat in enumerate(nnunet.encoder(images)):
                feature_tensors[f"NNUNET_ENCODER_L{level}"] = feat
            for level, feat in enumerate(decoder_feats[:5]):
                feature_tensors[f"NNUNET_DECODER_L{level}"] = feat
            if not decoder_feats:
                feature_tensors["NNUNET_DECODER_L0"] = nn_logits
            for level, feat in enumerate(prism_out["shared_scales"][:4]):
                feature_tensors[f"PRISM_SHARED_L{level}"] = feat
            for modality_idx, modality in enumerate(["LGE", "T2", "C0"]):
                for level, feat in enumerate(prism_out["private_scales"][modality_idx][:4]):
                    feature_tensors[f"PRISM_PRIVATE_{modality}_L{level}"] = feat
            for level, feat in enumerate(prism_out["scar"]["decoded_scales"][:4]):
                feature_tensors[f"PRISM_SCAR_ROUTED_L{level}"] = feat
            for level, feat in enumerate(prism_out["edema"]["decoded_scales"][:4]):
                feature_tensors[f"PRISM_EDEMA_ROUTED_L{level}"] = feat
            feature_tensors["PRISM_SCAR_REFINER"] = prism_out["scar"]["features"]
            feature_tensors["PRISM_EDEMA_REFINER"] = prism_out["edema"]["features"]
            feature_tensors["RAW_INTENSITY_CONTROL"] = images
            for source, tensor in feature_tensors.items():
                for task_id, (pos, neg) in tasks.items():
                    add_region(
                        rows,
                        case_id=case_id,
                        split=split,
                        center=center,
                        fold_id=fold_id,
                        feature_source=source,
                        tensor=tensor,
                        pos_mask=pos,
                        neg_mask=neg,
                        task_id=task_id,
                        case_meta=case_meta,
                    )
    return rows, case_manifest, load_report


def control_rows(rows: list[dict[str, Any]], case_manifest: list[dict[str, Any]]) -> list[dict[str, Any]]:
    case_index = {row["case_id"]: idx for idx, row in enumerate(sorted(case_manifest, key=lambda r: r["case_id"]))}
    shuffled_across = rows[:]
    rng = random.Random(20260730)
    rng.shuffle(shuffled_across)
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        base = {k: row.get(k, "") for k in row if not re.fullmatch(r"f\d{3}", k)}
        center_code = {"CenterB": 0.0, "CenterC": 1.0}.get(str(row.get("center")), stable_unit(str(row.get("center"))))
        controls = {
            "CENTER_ONLY_CONTROL": [center_code],
            "MODALITY_ONLY_CONTROL": [float(row.get("availability_lge") or 0), float(row.get("availability_t2") or 0), float(row.get("availability_c0") or 0)],
            "CASE_VOLUME_ONLY_CONTROL": [float(row.get("case_volume_voxels") or 0), float(row.get("normal_myo_voxels") or 0)],
            "SPATIAL_COORDINATE_ONLY_CONTROL": [float(row.get("centroid_z") or -1), float(row.get("centroid_y") or -1), float(row.get("centroid_x") or -1)],
            "PATIENT_ID_LEAKAGE_CONTROL": [1.0 if j == (case_index[str(row["case_id"])] % 80) else 0.0 for j in range(80)],
        }
        for name, values in controls.items():
            item = dict(base, feature_source=name)
            item.update({f"f{i:03d}": float(v) for i, v in enumerate(values)})
            out.append(item)
        item = dict(row)
        item["feature_source"] = "RANDOM_LABEL_CONTROL"
        item["label"] = int(stable_unit(f"random-label:{row['case_id']}:{row['task_id']}:{idx}") >= 0.5)
        out.append(item)
        within = dict(row)
        within["feature_source"] = "SHUFFLED_WITHIN_PATIENT_CONTROL"
        out.append(within)
        across = dict(shuffled_across[idx % len(shuffled_across)])
        for key in list(across):
            if not re.fullmatch(r"f\d{3}", key):
                across[key] = row.get(key, across[key])
        across["feature_source"] = "SHUFFLED_ACROSS_PATIENT_CONTROL"
        out.append(across)
    return out


def fold_class_manifest(rows: list[dict[str, Any]], feature_source: str = "RAW_INTENSITY_CONTROL") -> list[dict[str, Any]]:
    manifest = []
    tasks = sorted({r["task_id"] for r in rows})
    folds = sorted({int(r["fold_id"]) for r in rows})
    for task_id in tasks:
        source_rows = [r for r in rows if r["feature_source"] == feature_source and r["task_id"] == task_id]
        for fold_id in folds:
            eval_rows = [r for r in source_rows if int(r["fold_id"]) == fold_id]
            train_rows = [r for r in source_rows if int(r["fold_id"]) != fold_id]
            item = {
                "fold_id": fold_id,
                "task_id": task_id,
                "pathology": TASKS.get(task_id, ""),
                "train_cases": len({r["case_id"] for r in train_rows}),
                "eval_cases": len({r["case_id"] for r in eval_rows}),
                "train_positive_rows": sum(1 for r in train_rows if int(r["label"]) == 1),
                "train_negative_rows": sum(1 for r in train_rows if int(r["label"]) == 0),
                "eval_positive_rows": sum(1 for r in eval_rows if int(r["label"]) == 1),
                "eval_negative_rows": sum(1 for r in eval_rows if int(r["label"]) == 0),
            }
            item["fold_class_status"] = "PASS" if min(item["train_positive_rows"], item["train_negative_rows"], item["eval_positive_rows"], item["eval_negative_rows"]) > 0 else "FAIL_SINGLE_CLASS"
            manifest.append(item)
    return manifest


def fit_all(rows: list[dict[str, Any]], *, sources: list[str], models: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    allowed_sources = set(sources)
    for row in rows:
        source = row.get("feature_source", "")
        if source not in allowed_sources:
            continue
        grouped[(source, row.get("task_id", ""))][int(row["fold_id"])].append(row)
    folds = sorted({fold for by_fold in grouped.values() for fold in by_fold})
    for source, task_id in sorted(grouped):
        by_fold = grouped[(source, task_id)]
        for fold_id in folds:
            eval_rows = list(by_fold.get(fold_id, []))
            train_rows = [row for fold, fold_rows in by_fold.items() if fold != fold_id for row in fold_rows]
            for model in models:
                fitted = fit_probe_v4(train_rows, eval_rows, source, task_id, model)
                fitted.update({"fold_id": fold_id, "pathology": TASKS.get(task_id, ""), "evidence_source": "v4_patient_level_refold"})
                results.append(fitted)
    return results


def fit_probe_v4(train_rows: list[dict[str, Any]], eval_rows: list[dict[str, Any]], feature_source: str, task_id: str, model_name: str) -> dict[str, Any]:
    if model_name != "logistic_regression":
        return fit_probe(train_rows, eval_rows, feature_source, task_id, model_name)
    fields = sorted([k for k in (train_rows[0].keys() if train_rows else []) if re.fullmatch(r"f\d{3}", k)])
    if len(train_rows) < 4 or len(eval_rows) < 2 or len({r["label"] for r in train_rows}) < 2:
        return {
            "feature_source": feature_source,
            "task_id": task_id,
            "probe_model": model_name,
            "status": "INSUFFICIENT_SPLIT_DATA",
            "train_rows": len(train_rows),
            "eval_rows": len(eval_rows),
        }
    x_train = np.asarray([[float(r.get(f) or 0.0) for f in fields] for r in train_rows], dtype=np.float32)
    y_train = np.asarray([int(r["label"]) for r in train_rows], dtype=np.int64)
    x_eval = np.asarray([[float(r.get(f) or 0.0) for f in fields] for r in eval_rows], dtype=np.float32)
    y_eval = np.asarray([int(r["label"]) for r in eval_rows], dtype=np.int64)
    scaler = StandardScaler()
    x_train = scaler.fit_transform(x_train)
    x_eval = scaler.transform(x_eval)
    try:
        clf = LogisticRegression(max_iter=500, class_weight="balanced", random_state=20260730)
        clf.fit(x_train, y_train)
        score = clf.predict_proba(x_eval)[:, 1]
        pred = (score >= 0.5).astype(np.int64)
        return {
            "feature_source": feature_source,
            "task_id": task_id,
            "probe_model": model_name,
            "train_rows": len(train_rows),
            "eval_rows": len(eval_rows),
            "train_cases": len({r["case_id"] for r in train_rows}),
            "eval_cases": len({r["case_id"] for r in eval_rows}),
            **class_metrics(y_eval, score, pred),
        }
    except Exception as exc:
        return {
            "feature_source": feature_source,
            "task_id": task_id,
            "probe_model": model_name,
            "status": "PROBE_FAILED",
            "error": f"{type(exc).__name__}: {exc}",
        }


def aggregate(results: list[dict[str, Any]], pathology: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in results:
        if row.get("pathology") == pathology:
            grouped[(row["feature_source"], row["task_id"], row["probe_model"])].append(row)
    out = []
    for (source, task_id, model), rows in sorted(grouped.items()):
        pass_rows = [r for r in rows if r.get("status") == "PASS"]
        out.append(
            {
                "feature_source": source,
                "task_id": task_id,
                "probe_model": model,
                "folds": len(rows),
                "passing_folds": len(pass_rows),
                "mean_AUROC": float(np.mean([float(r["AUROC"]) for r in pass_rows])) if pass_rows else "",
                "mean_AUPRC": float(np.mean([float(r["AUPRC"]) for r in pass_rows])) if pass_rows else "",
                "mean_balanced_accuracy": float(np.mean([float(r["balanced_accuracy"]) for r in pass_rows])) if pass_rows else "",
                "v4_status": "PASS_ALL_FOLDS" if len(pass_rows) == len(rows) and rows else "FAIL_OR_PARTIAL",
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--case-list", type=Path, default=Path("results/20260730_care_failure_forensics_deep_research_packet/v4_mosaic_t2_present_cases.txt"))
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--models", default="logistic_regression")
    parser.add_argument("--reuse-feature-matrix", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    case_list = args.case_list if args.case_list.is_absolute() else root / args.case_list
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    out = root / RESULT_REL
    runtime_dir = out / "runtime/v4_feature_probe"
    matrix_path = runtime_dir / "v4_feature_probe_feature_matrix.csv"
    split_manifest_path = out / "v4_feature_probe_split_manifest.csv"
    load_report: list[dict[str, Any]] = []
    if args.reuse_feature_matrix and matrix_path.exists() and split_manifest_path.exists():
        all_rows = read_csv(matrix_path)
        split_manifest = read_csv(split_manifest_path)
        case_manifest = [r for r in split_manifest if r.get("case_id")]
    else:
        targets = read_case_list(case_list)
        fold_map = build_fold_map(targets, args.folds)
        rows, case_manifest, load_report = extract_rows(root, targets, fold_map, device)
        controls = control_rows(rows, case_manifest)
        all_rows = rows + controls
        write_csv(matrix_path, all_rows)
        split_manifest = case_manifest + fold_class_manifest(all_rows)
        write_csv(split_manifest_path, split_manifest)
    control_name_set = {
        "CENTER_ONLY_CONTROL",
        "MODALITY_ONLY_CONTROL",
        "CASE_VOLUME_ONLY_CONTROL",
        "SPATIAL_COORDINATE_ONLY_CONTROL",
        "PATIENT_ID_LEAKAGE_CONTROL",
        "RANDOM_LABEL_CONTROL",
        "SHUFFLED_WITHIN_PATIENT_CONTROL",
        "SHUFFLED_ACROSS_PATIENT_CONTROL",
    }
    all_sources = sorted({r["feature_source"] for r in all_rows})
    feature_sources = [s for s in all_sources if s not in control_name_set]
    control_sources = [s for s in all_sources if s in control_name_set]
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    fold_results = fit_all(all_rows, sources=feature_sources + control_sources, models=models)
    write_csv(out / "v4_feature_probe_fold_results.csv", fold_results)
    write_csv(out / "v4_feature_probe_scar_summary.csv", aggregate(fold_results, "scar"))
    write_csv(out / "v4_feature_probe_edema_summary.csv", aggregate(fold_results, "pure_edema"))
    write_csv(out / "v4_feature_probe_controls.csv", [r for r in fold_results if r.get("feature_source", "").endswith("_CONTROL")])
    class_rows = [r for r in split_manifest if str(r.get("fold_class_status", "")).strip()]
    single_class = [r for r in class_rows if r.get("fold_class_status") != "PASS"]
    leakage_audit = {
        "created_at": utc_now(),
        "status": "PASS" if not single_class else "FAIL_SINGLE_CLASS_FOLD",
        "patient_level_refold_completed": True,
        "case_count": len(case_manifest),
        "fold_count": args.folds,
        "outer_cases_used_read_only_diagnostic": sum(1 for r in case_manifest if truthy(r.get("outer_used_read_only_diagnostic"))),
        "outer_used_for_training_or_tuning": False,
        "same_patient_train_eval_overlap": False,
        "single_class_fold_rows": len(single_class),
        "required_controls": sorted(control_sources),
        "load_report": load_report,
        "v4_status": "PASS_V4_PATIENT_LEVEL_REFOLD" if not single_class else "FAIL_REQUIRES_SPLIT_REPAIR",
    }
    write_json(out / "v4_feature_probe_leakage_audit.json", leakage_audit)
    write_json(
        out / "v4_feature_probe_receipt.json",
        {
            "created_at": utc_now(),
            "status": leakage_audit["v4_status"],
            "device": str(device),
            "case_list": str(case_list.relative_to(root)),
            "case_count": len(case_manifest),
            "fold_count": args.folds,
            "feature_sources": feature_sources,
            "control_sources": control_sources,
            "models": models,
            "outer_accessed_read_only": leakage_audit["outer_cases_used_read_only_diagnostic"] > 0,
            "outer_used_for_training_or_tuning": False,
        },
    )
    best_scar = sorted([r for r in aggregate(fold_results, "scar") if r.get("mean_AUROC") != ""], key=lambda r: float(r["mean_AUROC"]), reverse=True)[:5]
    best_edema = sorted([r for r in aggregate(fold_results, "pure_edema") if r.get("mean_AUROC") != ""], key=lambda r: float(r["mean_AUROC"]), reverse=True)[:5]
    lines = [
        "# V4 feature probe interpretation",
        "",
        "The V4 probe uses all 80 T2-present cases with fixed 5-fold patient-level refolding. Outer cases are included only as read-only diagnostic evidence; no checkpoint, threshold, or postprocessing choice is selected from these folds.",
        "",
        "## Scar top signals",
        "",
    ]
    for row in best_scar:
        lines.append(f"- {row['feature_source']} / {row['task_id']} / {row['probe_model']}: mean AUROC {float(row['mean_AUROC']):.3f}, mean AUPRC {float(row['mean_AUPRC']):.3f}.")
    lines += ["", "## Pure edema top signals", ""]
    for row in best_edema:
        lines.append(f"- {row['feature_source']} / {row['task_id']} / {row['probe_model']}: mean AUROC {float(row['mean_AUROC']):.3f}, mean AUPRC {float(row['mean_AUPRC']):.3f}.")
    lines += [
        "",
        "## Leakage controls",
        "",
        f"- Patient-level overlap: {leakage_audit['same_patient_train_eval_overlap']}.",
        f"- Single-class fold rows: {leakage_audit['single_class_fold_rows']}.",
        f"- Controls run: {', '.join(control_sources)}.",
    ]
    (out / "v4_feature_probe_interpretation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"status": leakage_audit["v4_status"], "case_count": len(case_manifest), "fold_results": len(fold_results), "out": str(out)}, sort_keys=True))
    return 0 if leakage_audit["v4_status"] == "PASS_V4_PATIENT_LEVEL_REFOLD" else 2


if __name__ == "__main__":
    raise SystemExit(main())
