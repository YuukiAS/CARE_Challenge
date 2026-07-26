#!/usr/bin/env python3
"""Export leakage-safe MoSAIC OOF predictions, probabilities, and feature evidence.

This script is intentionally fold-specific. It only predicts the held-out cases
from data/benchmarks/protocol/splits_MyoPS.json with that fold's isolated MoSAIC
checkpoints under care_scf_v1/mosaic_oof/foldX/.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import binary_dilation, generate_binary_structure
from scipy.ndimage import label as cc_label

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
MOSAIC_SOURCE = REPO_ROOT / "third_party/MoSAIC/source"
for _p in (REPO_ROOT, MOSAIC_CODE, MOSAIC_SOURCE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from mosaic_fair_protocol import (  # noqa: E402
    MOSAIC_SOURCE_COMMIT,
    geometry_matches,
    geometry_signature,
    load_fold_case_sets,
    load_fold_val_cases,
    remap_labels,
    sha256_file,
    write_csv,
    write_json,
)
from myops.data.labels import TRACK_MYOPS, modalities_for_track, num_classes, train_to_official_labels  # noqa: E402
from myops.data.preprocessing import cache_path  # noqa: E402
from myops.inference.edema_predict import merge_labels  # noqa: E402
from myops.inference.postprocess import clean_prediction_by_class, enforce_pathology_inside_myo, largest_component  # noqa: E402
from myops.inference.predict import predict_case_coarse, predict_case_fine  # noqa: E402
from myops.models import build_model  # noqa: E402
from myops.utils.io import read_jsonl, torch_load  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402

DEFAULT_RESULT_ROOT = REPO_ROOT / "results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1"
SPLIT_PATH = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
GT_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
NNUNET_OOF_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
FOLD0_REAUDIT_ROOT = REPO_ROOT / "results/20260726_mosaic_fold0_fairness_reaudit"
FOLD0_OLD_ROOT = REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction"
FOLD0_MODEL_ID = "clean_pathology_checkpoint"
OFFICIAL_TO_COMPACT = {1220: 4, 2221: 5}
TTA = {"enabled": True, "flips": ["horizontal", "vertical"]}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = sorted({k for row in rows for k in row}) if rows else ["empty"]
    write_csv(path, rows, fieldnames=fieldnames)


def import_upstream_infer():
    spec = importlib.util.spec_from_file_location("mosaic_oof_infer_submit", MOSAIC_SOURCE / "scripts/infer_and_submit.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import infer_and_submit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fold_root(result_root: Path, fold: int) -> Path:
    return result_root / "mosaic_oof" / f"fold{fold}"


def manifest_path(result_root: Path, fold: int) -> Path:
    return fold_root(result_root, fold) / "receipts" / f"manifest_fold{fold}_exact.jsonl"


def cache_dir(result_root: Path, fold: int) -> Path:
    return fold_root(result_root, fold) / "cache"


def stage_dir(result_root: Path, fold: int, stage: str) -> Path:
    return fold_root(result_root, fold) / ("fine_scar" if stage == "scar" else stage)


def selected_checkpoint(result_root: Path, fold: int, stage: str) -> Path:
    out = stage_dir(result_root, fold, stage)
    if stage == "coarse":
        path = out / "best.pt"
        return path if path.exists() else out / "last.pt"
    if stage == "scar":
        primary = out / "best_scar.pt"
        fallback = out / "best_pathology.pt"
        if primary.exists():
            return primary
        if fallback.exists():
            return fallback
        raise FileNotFoundError(f"scar pathology checkpoint missing: {out}")
    raise ValueError(stage)


def assert_training_complete(result_root: Path, fold: int, stage: str) -> dict[str, Any]:
    path = fold_root(result_root, fold) / "receipts" / f"{stage}_training_budget_receipt.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing training receipt: {path}")
    payload = read_json(path)
    if payload.get("terminal_status") != "COMPLETE_FULL_BUDGET" or payload.get("undertrained"):
        raise RuntimeError(f"stage is not complete full budget: {path}")
    if int(payload.get("completed_epochs", -1)) != int(payload.get("max_epochs", -2)):
        raise RuntimeError(f"epoch budget mismatch: {path}")
    if int(payload.get("actual_optimizer_steps", -1)) != int(payload.get("expected_optimizer_steps", -2)):
        raise RuntimeError(f"optimizer-step budget mismatch: {path}")
    return payload


def load_checkpoint_state(path: Path) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    ckpt = torch.load(str(path), map_location="cpu", weights_only=False)
    if not isinstance(ckpt, dict):
        raise TypeError(f"unsupported checkpoint object in {path}: {type(ckpt)!r}")
    state = ckpt.get("model_state", ckpt)
    meta = {k: v for k, v in ckpt.items() if k != "model_state" and isinstance(v, (str, int, float, bool))}
    return state, meta


def build_coarse_model(device: torch.device, ckpt_path: Path):
    upstream = import_upstream_infer()
    cfg = upstream.load_config(str(MOSAIC_SOURCE / "configs/myops_coarse.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))
    model = build_model(
        stage="coarse",
        track=TRACK_MYOPS,
        arch="2d_coarse",
        in_channels=n_mod * 2,
        out_channels=num_classes(TRACK_MYOPS, "coarse"),
        base_channels=int(cfg["model"].get("base_channels", 24)),
        deep_supervision=True,
    )
    state, _meta = load_checkpoint_state(ckpt_path)
    model.load_state_dict(state)
    return model.to(device).eval()


def build_scar_model(device: torch.device, ckpt_path: Path):
    upstream = import_upstream_infer()
    cfg = upstream.load_config(str(MOSAIC_SOURCE / "configs/myops_fine.yaml"))
    n_mod = len(modalities_for_track(TRACK_MYOPS))
    model = build_model(
        stage="fine",
        track=TRACK_MYOPS,
        arch="2d_multi",
        in_channels=n_mod * 2 + 1,
        out_channels=num_classes(TRACK_MYOPS, "fine"),
        base_channels=int(cfg["model"].get("base_channels", 24)),
        deep_supervision=bool(cfg["model"].get("deep_supervision", True)),
        grid_size=int(cfg["model"].get("grid_size", 4)),
        span_range=float(cfg["model"].get("span_range", 0.98)),
        image_size=192,
        use_tps=bool(cfg["model"].get("use_tps", True)),
        use_spg=bool(cfg["model"].get("use_spg", True)),
        use_consistency=bool(cfg["model"].get("use_consistency", True)),
    )
    state, _meta = load_checkpoint_state(ckpt_path)
    model.load_state_dict(state, strict=False)
    return model.to(device).eval()


def orient_array_to_reference_zyx(array: np.ndarray, ref: sitk.Image) -> np.ndarray:
    arr = np.asarray(array)
    ref_x, ref_y, ref_z = (int(v) for v in ref.GetSize())
    ref_zyx = (ref_z, ref_y, ref_x)
    if tuple(arr.shape) == ref_zyx:
        return arr
    candidates = {
        (ref_z, ref_x, ref_y): (0, 2, 1),
        (ref_x, ref_y, ref_z): (2, 1, 0),
        (ref_y, ref_x, ref_z): (2, 0, 1),
    }
    axes = candidates.get(tuple(arr.shape))
    if axes is None:
        raise ValueError(f"cannot orient prediction array shape {tuple(arr.shape)} to reference zyx {ref_zyx}")
    return np.transpose(arr, axes)


def sitk_write_like(array_zyx: np.ndarray, reference_path: Path, dest: Path) -> dict[str, Any]:
    ref = sitk.ReadImage(str(reference_path))
    oriented = orient_array_to_reference_zyx(array_zyx, ref)
    img = sitk.GetImageFromArray(oriented.astype(np.int16, copy=False))
    img.CopyInformation(ref)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(dest))
    written = sitk.ReadImage(str(dest))
    return {
        "prediction_path": rel(dest),
        "geometry_status": "PASS" if geometry_matches(geometry_signature(written), geometry_signature(ref)) else "FAIL",
        "size_xyz": list(written.GetSize()),
        "spacing_xyz": list(written.GetSpacing()),
        "reference_path": rel(reference_path),
    }


def embedding_collector(model: torch.nn.Module):
    vectors: list[np.ndarray] = []

    def hook(_module, inputs, _outputs):
        if not inputs:
            return
        tensor = inputs[0]
        if isinstance(tensor, torch.Tensor) and tensor.ndim == 4:
            vec = tensor.detach().float().mean(dim=(0, 2, 3)).cpu().numpy()
            vectors.append(vec)

    handle = model.msf_decoder.register_forward_hook(hook) if hasattr(model, "msf_decoder") else None

    def finalize() -> dict[str, np.ndarray]:
        if handle is not None:
            handle.remove()
        if not vectors:
            return {"embedding_mean": np.zeros((0,), dtype=np.float32), "embedding_std": np.zeros((0,), dtype=np.float32)}
        arr = np.stack(vectors).astype(np.float32, copy=False)
        return {"embedding_mean": arr.mean(axis=0), "embedding_std": arr.std(axis=0)}

    return finalize


def component_rows(case_id: str, fold: int, final_label_hwz: np.ndarray, scar_probs_hwz: np.ndarray, coarse_hwz: np.ndarray) -> list[dict[str, Any]]:
    scar_mask = final_label_hwz == 5
    cc, n_cc = cc_label(scar_mask.astype(bool), structure=generate_binary_structure(3, 1))
    support = coarse_hwz > 0
    rows: list[dict[str, Any]] = []
    for idx in range(1, n_cc + 1):
        comp = cc == idx
        coords = np.argwhere(comp)
        if not len(coords):
            continue
        zyx_center = [float(v) for v in coords[:, [2, 0, 1]].mean(axis=0)]
        bbox_min = [int(v) for v in coords.min(axis=0)]
        bbox_max = [int(v) for v in coords.max(axis=0)]
        rows.append({
            "fold": int(fold),
            "case_id": case_id,
            "pathology": "scar",
            "component_id": f"fold{fold}:{case_id}:scar:{idx}",
            "component_voxels": int(comp.sum()),
            "center_zyx": json.dumps(zyx_center),
            "bbox_min_hwz": json.dumps(bbox_min),
            "bbox_max_hwz": json.dumps(bbox_max),
            "mosaic_scar_probability_mean": float(np.mean(scar_probs_hwz[4][comp])) if comp.any() else 0.0,
            "mosaic_scar_probability_max": float(np.max(scar_probs_hwz[4][comp])) if comp.any() else 0.0,
            "anatomy_overlap_fraction": float(np.count_nonzero(comp & support) / max(1, int(comp.sum()))),
        })
    return rows



def integrate_existing_fold0(result_root: Path) -> dict[str, Any]:
    """Register the already audited clean fold0 MoSAIC OOF artifacts.

    This does not rewrite the historical fold0 reproduction. It records fold0 as
    held-out OOF evidence under the current CARE-SCF result tree and references
    the clean pathology-checkpoint artifacts from the fold0 fairness reaudit.
    """

    fold = 0
    train_cases, val_cases = load_fold_case_sets(SPLIT_PATH, fold)
    if len(train_cases) != 176 or len(val_cases) != 44 or train_cases & val_cases:
        raise RuntimeError("bad split fold0")
    metadata = load_myops_case_metadata(REPO_ROOT)
    out_root = fold_root(result_root, fold)
    out_root.mkdir(parents=True, exist_ok=True)
    source_manifest = FOLD0_REAUDIT_ROOT / "prediction_manifest.csv"
    if not source_manifest.is_file():
        raise FileNotFoundError(source_manifest)
    rows: list[dict[str, str]] = []
    with source_manifest.open(newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("model_id") == FOLD0_MODEL_ID]
    by_case = {r["case_id"]: r for r in rows}
    manifest_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    component_feature_rows: list[dict[str, Any]] = []
    for case_id in sorted(val_cases):
        row = by_case.get(case_id)
        if row is None:
            raise FileNotFoundError(f"fold0 clean pathology prediction missing for {case_id}")
        prob_path = REPO_ROOT / row["stage_cache_path"]
        compact_path = REPO_ROOT / row["compact_prediction_path"]
        official_path = REPO_ROOT / row["official_prediction_path"]
        if not prob_path.is_file() or not compact_path.is_file() or not official_path.is_file():
            raise FileNotFoundError(f"fold0 artifact missing for {case_id}")
        payload = np.load(prob_path)
        final_label_hwz = np.asarray(payload["final_label"], dtype=np.int16)
        scar_probs_hwz = np.asarray(payload["scar_probs"], dtype=np.float32)
        coarse_hwz = np.asarray(payload["coarse_scar"], dtype=np.int16)
        components = component_rows(case_id, fold, final_label_hwz, scar_probs_hwz, coarse_hwz)
        component_feature_rows.extend(components)
        meta = metadata[case_id]
        nnunet_dir = NNUNET_OOF_ROOT / "fold_0/validation"
        manifest_rows.append({
            "fold": 0,
            "case_id": case_id,
            "source_commit": MOSAIC_SOURCE_COMMIT,
            "oof_model_fold": 0,
            "case_role": "held_out_val",
            "trained_on_case": False,
            "train_case_count": 176,
            "val_case_count": 44,
            "nnunet_prediction": rel(nnunet_dir / f"{case_id}.nii.gz"),
            "nnunet_probability": rel(nnunet_dir / f"{case_id}.npz"),
            "mosaic_prediction_official": row["official_prediction_path"],
            "mosaic_prediction_compact": row["compact_prediction_path"],
            "mosaic_probability": row["stage_cache_path"],
            "mosaic_embedding": "PENDING_FOLD0_REEXPORT_WITH_HOOK",
            "gt": rel(GT_DIR / f"{case_id}.nii.gz"),
            "pathology_component": "scar",
            "modality_availability": meta.modality_group,
            "t2_present": int(meta.t2_present),
            "center": meta.center,
            "coarse_checkpoint_sha256": row.get("loaded_coarse_scar_sha256"),
            "scar_checkpoint_sha256": row.get("loaded_scar_sha256"),
            "component_count_scar": len(components),
            "fold0_source": rel(FOLD0_REAUDIT_ROOT),
        })
        for space, pred_path in [("official", official_path), ("compact", compact_path)]:
            ref = sitk.ReadImage(str(GT_DIR / f"{case_id}.nii.gz"))
            pred = sitk.ReadImage(str(pred_path))
            geometry_rows.append({
                "fold": 0,
                "case_id": case_id,
                "space": space,
                "prediction_path": rel(pred_path),
                "geometry_status": "PASS" if geometry_matches(geometry_signature(pred), geometry_signature(ref)) else "FAIL",
                "reference_path": rel(GT_DIR / f"{case_id}.nii.gz"),
            })
    checkpoint_rows = [
        {"fold": 0, "stage": "coarse", "checkpoint_path": rel(FOLD0_OLD_ROOT / "runtime/fold0/coarse/best.pt"), "sha256": rows[0].get("loaded_coarse_scar_sha256") if rows else None, "receipt_status": "PREEXISTING_FOLD0_FAIR_REPRODUCTION"},
        {"fold": 0, "stage": "scar", "checkpoint_path": rel(FOLD0_OLD_ROOT / "runtime/fold0/fine_scar/best_scar.pt"), "sha256": rows[0].get("loaded_scar_sha256") if rows else None, "receipt_status": "PREEXISTING_FOLD0_FAIR_REPRODUCTION"},
    ]
    write_manifest_csv(out_root / "oof_prediction_manifest.csv", manifest_rows)
    write_manifest_csv(out_root / "oof_geometry_audit.csv", geometry_rows)
    write_manifest_csv(out_root / "oof_checkpoint_manifest.csv", checkpoint_rows)
    write_manifest_csv(out_root / "features/scar_component_features.csv", component_feature_rows)
    return {"fold": 0, "status": "PASS_PREEXISTING_CLEAN_FOLD0", "case_count": len(manifest_rows), "component_count": len(component_feature_rows)}

def export_fold(result_root: Path, fold: int, gpu: int) -> dict[str, Any]:
    if int(fold) == 0:
        return integrate_existing_fold0(result_root)
    coarse_receipt = assert_training_complete(result_root, fold, "coarse")
    scar_receipt = assert_training_complete(result_root, fold, "scar")
    train_cases, val_cases = load_fold_case_sets(SPLIT_PATH, fold)
    if len(train_cases) != 176 or len(val_cases) != 44 or train_cases & val_cases:
        raise RuntimeError(f"bad split fold{fold}")
    records = read_jsonl(str(manifest_path(result_root, fold)))
    rec_by_case = {str(r["case_id"]): r for r in records}
    metadata = load_myops_case_metadata(REPO_ROOT)
    upstream = import_upstream_infer()
    thresholds = upstream.default_thresholds(TRACK_MYOPS, "fine")
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    coarse_ckpt = selected_checkpoint(result_root, fold, "coarse")
    scar_ckpt = selected_checkpoint(result_root, fold, "scar")
    coarse = build_coarse_model(device, coarse_ckpt)
    scar = build_scar_model(device, scar_ckpt)
    out_root = fold_root(result_root, fold)
    official_dir = out_root / "oof_predictions/official"
    compact_dir = out_root / "oof_predictions/compact"
    prob_dir = out_root / "probabilities"
    feature_dir = out_root / "features"
    manifest_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    component_feature_rows: list[dict[str, Any]] = []
    checkpoint_rows = [
        {"fold": fold, "stage": "coarse", "checkpoint_path": rel(coarse_ckpt), "sha256": sha256_file(coarse_ckpt), "receipt_status": coarse_receipt["terminal_status"]},
        {"fold": fold, "stage": "scar", "checkpoint_path": rel(scar_ckpt), "sha256": sha256_file(scar_ckpt), "receipt_status": scar_receipt["terminal_status"]},
    ]
    for case_id in sorted(val_cases):
        record = rec_by_case[case_id]
        if case_id in train_cases:
            raise RuntimeError(f"leakage: val case is in train cases: {case_id}")
        payload = torch_load(cache_path(str(cache_dir(result_root, fold)), TRACK_MYOPS, case_id))
        finalize_embedding = embedding_collector(scar)
        with torch.no_grad():
            coarse_result = predict_case_coarse(coarse, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=TTA)
            coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)
            scar_result = predict_case_fine(scar, payload, TRACK_MYOPS, device, coarse_prior=coarse_prior, image_size=[192, 192], tta_config=TTA)
        embedding = finalize_embedding()
        scar_probs_compact = np.asarray(scar_result["probs"], dtype=np.float32)
        scar_probs_hwz = upstream.probs_to_original_space(scar_probs_compact, payload)
        raw_scar_label = upstream.probs_to_label(scar_probs_hwz, thresholds)
        coarse_hwz = upstream.label_to_original_space(coarse_prior, payload)
        myo_mask = binary_dilation(coarse_hwz > 0, iterations=1)
        scar_contained = enforce_pathology_inside_myo(raw_scar_label.copy(), 1, [4, 5], external_myo_mask=myo_mask)
        scar_clean = clean_prediction_by_class(scar_contained.copy(), {4: 5, 5: 3})
        final_label_hwz = merge_labels(scar_clean, coarse_hwz, np.zeros_like(coarse_hwz, dtype=bool))
        final_label_hwz = clean_prediction_by_class(final_label_hwz, {4: 5, 5: 3})
        scar_mask = final_label_hwz == 5
        if scar_mask.any():
            final_label_hwz[scar_mask & ~largest_component(scar_mask)] = 0
        official_hwz = train_to_official_labels(final_label_hwz, TRACK_MYOPS, stage="fine")
        official_zyx = np.transpose(official_hwz, (2, 0, 1))
        compact_zyx = remap_labels(official_zyx, OFFICIAL_TO_COMPACT)
        gt_path = GT_DIR / f"{case_id}.nii.gz"
        official_path = official_dir / f"{case_id}.nii.gz"
        compact_path = compact_dir / f"{case_id}.nii.gz"
        official_geom = sitk_write_like(official_zyx, gt_path, official_path)
        compact_geom = sitk_write_like(compact_zyx, gt_path, compact_path)
        prob_path = prob_dir / f"{case_id}.npz"
        prob_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            prob_path,
            scar_probs=scar_probs_hwz.astype(np.float16),
            coarse_scar=coarse_hwz.astype(np.int16),
            raw_scar_label=raw_scar_label.astype(np.int16),
            scar_clean=scar_clean.astype(np.int16),
            final_label=final_label_hwz.astype(np.int16),
        )
        emb_path = feature_dir / "embeddings" / f"{case_id}.npz"
        emb_path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(emb_path, **embedding)
        components = component_rows(case_id, fold, final_label_hwz, scar_probs_hwz, coarse_hwz)
        component_feature_rows.extend(components)
        meta = metadata[case_id]
        nnunet_dir = NNUNET_OOF_ROOT / f"fold_{fold}/validation"
        manifest_rows.append({
            "fold": int(fold),
            "case_id": case_id,
            "source_commit": MOSAIC_SOURCE_COMMIT,
            "oof_model_fold": int(fold),
            "case_role": "held_out_val",
            "trained_on_case": False,
            "train_case_count": 176,
            "val_case_count": 44,
            "nnunet_prediction": rel(nnunet_dir / f"{case_id}.nii.gz"),
            "nnunet_probability": rel(nnunet_dir / f"{case_id}.npz"),
            "mosaic_prediction_official": rel(official_path),
            "mosaic_prediction_compact": rel(compact_path),
            "mosaic_probability": rel(prob_path),
            "mosaic_embedding": rel(emb_path),
            "gt": rel(gt_path),
            "pathology_component": "scar",
            "modality_availability": meta.modality_group,
            "t2_present": int(meta.t2_present),
            "center": meta.center,
            "coarse_checkpoint_sha256": sha256_file(coarse_ckpt),
            "scar_checkpoint_sha256": sha256_file(scar_ckpt),
            "component_count_scar": len(components),
        })
        geometry_rows.append({"fold": fold, "case_id": case_id, "space": "official", **official_geom})
        geometry_rows.append({"fold": fold, "case_id": case_id, "space": "compact", **compact_geom})
    write_manifest_csv(out_root / "oof_prediction_manifest.csv", manifest_rows)
    write_manifest_csv(out_root / "oof_geometry_audit.csv", geometry_rows)
    write_manifest_csv(out_root / "oof_checkpoint_manifest.csv", checkpoint_rows)
    write_manifest_csv(feature_dir / "scar_component_features.csv", component_feature_rows)
    del coarse, scar
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return {"fold": fold, "status": "PASS", "case_count": len(manifest_rows), "component_count": len(component_feature_rows)}


def summarize(result_root: Path, folds: list[int]) -> dict[str, Any]:
    coverage_rows: list[dict[str, Any]] = []
    prediction_rows: list[dict[str, Any]] = []
    checkpoint_rows: list[dict[str, Any]] = []
    geometry_rows: list[dict[str, Any]] = []
    all_val_seen: list[str] = []
    leakage_errors: list[str] = []
    for fold in folds:
        train_cases, val_cases = load_fold_case_sets(SPLIT_PATH, fold)
        manifest_file = fold_root(result_root, fold) / "oof_prediction_manifest.csv"
        rows = []
        if manifest_file.is_file():
            with manifest_file.open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
        predicted_cases = {r["case_id"] for r in rows}
        all_val_seen.extend(sorted(predicted_cases))
        for case_id in sorted(val_cases):
            in_pred = case_id in predicted_cases
            if case_id in train_cases and in_pred:
                leakage_errors.append(f"fold{fold}:{case_id}")
            coverage_rows.append({
                "fold": fold,
                "case_id": case_id,
                "expected_val": True,
                "mosaic_oof_present": in_pred,
                "nnunet_oof_present": (NNUNET_OOF_ROOT / f"fold_{fold}/validation/{case_id}.nii.gz").is_file(),
                "nnunet_probability_present": (NNUNET_OOF_ROOT / f"fold_{fold}/validation/{case_id}.npz").is_file(),
                "trained_on_case": case_id in train_cases,
            })
        prediction_rows.extend(rows)
        for name, bucket in [("oof_checkpoint_manifest.csv", checkpoint_rows), ("oof_geometry_audit.csv", geometry_rows)]:
            p = fold_root(result_root, fold) / name
            if p.is_file():
                with p.open(newline="", encoding="utf-8") as f:
                    bucket.extend(csv.DictReader(f))
    duplicate_cases = sorted({c for c in all_val_seen if all_val_seen.count(c) > 1})
    expected_union = set().union(*[load_fold_case_sets(SPLIT_PATH, f)[1] for f in folds]) if folds else set()
    covered_once = len(all_val_seen) == len(set(all_val_seen)) == len(expected_union) and set(all_val_seen) == expected_union
    geometry_pass = bool(geometry_rows) and all(str(r.get("geometry_status")) == "PASS" for r in geometry_rows)
    write_manifest_csv(result_root / "mosaic_oof_coverage.csv", coverage_rows)
    write_manifest_csv(result_root / "mosaic_oof_prediction_manifest.csv", prediction_rows)
    write_manifest_csv(result_root / "mosaic_oof_checkpoint_manifest.csv", checkpoint_rows)
    write_manifest_csv(result_root / "mosaic_oof_geometry_audit.csv", geometry_rows)
    audit = {
        "status": "PASS" if covered_once and not leakage_errors and geometry_pass else "FAIL",
        "folds": folds,
        "expected_case_count": len(expected_union),
        "covered_prediction_rows": len(prediction_rows),
        "covered_unique_cases": len(set(all_val_seen)),
        "covered_once": covered_once,
        "duplicate_cases": duplicate_cases,
        "leakage_errors": leakage_errors,
        "geometry_pass": geometry_pass,
        "full_data_checkpoint_used": False,
        "source_commit": MOSAIC_SOURCE_COMMIT,
    }
    write_json(result_root / "mosaic_oof_no_leakage_audit.json", audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--gpu", type=int, default=0)
    parser.add_argument("--summarize-only", action="store_true")
    args = parser.parse_args()
    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    result_root.mkdir(parents=True, exist_ok=True)
    outputs = []
    if not args.summarize_only:
        for fold in args.folds:
            outputs.append(export_fold(result_root, int(fold), int(args.gpu)))
    audit = summarize(result_root, [int(f) for f in args.folds])
    write_json(result_root / "mosaic_oof_export_receipt.json", {
        "time_utc": now_iso(),
        "source_commit": MOSAIC_SOURCE_COMMIT,
        "fold_outputs": outputs,
        "no_leakage_audit_status": audit["status"],
        "validation_upload_performed": False,
        "new_slurm_allocations_submitted": False,
    })
    print(json.dumps({"fold_outputs": outputs, "audit": audit}, indent=2, sort_keys=True))
    return 0 if audit["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
