#!/usr/bin/env python3
"""Run the CARE MoSAIC fold0 fair reproduction stages.

This wrapper is intentionally MyoPS-only. It builds a manifest from the CARE
canonical fold0 split and trains MoSAIC fold0 models from random initialization;
it never loads /users/a/e/aereinh/MoSAIC full-data submission checkpoints for
fold0 training or fold0 performance comparison.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
MOSAIC_SOURCE = REPO_ROOT / "third_party/MoSAIC/source"
if str(MOSAIC_CODE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_CODE))
if str(MOSAIC_SOURCE) not in sys.path:
    sys.path.insert(0, str(MOSAIC_SOURCE))

from mosaic_fair_protocol import (  # noqa: E402
    DEFAULT_CONFIG,
    DEFAULT_RESULT_ROOT,
    OFFICIAL_TO_COMPACT,
    geometry_matches,
    geometry_signature,
    load_fold_case_sets,
    load_fold_train_cases,
    load_fold_val_cases,
    load_yaml,
    remap_labels,
    sha256_file,
    write_csv,
    write_json,
)
from myops.data.labels import TRACK_MYOPS, modalities_for_track, num_classes, train_to_official_labels  # noqa: E402
from myops.data.manifest import build_myops_manifest  # noqa: E402
from myops.data.preprocessing import cache_path  # noqa: E402
from myops.inference.edema_predict import load_edema_model, merge_labels, predict_edema_case_probs  # noqa: E402
from myops.inference.postprocess import clean_prediction_by_class, enforce_pathology_inside_myo, largest_component  # noqa: E402
from myops.inference.predict import predict_case_coarse, predict_case_fine  # noqa: E402
from myops.models import build_model  # noqa: E402
from myops.utils.io import read_jsonl, torch_load, write_jsonl  # noqa: E402
from scipy.ndimage import binary_dilation  # noqa: E402


def import_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


UPSTREAM_5FOLD = import_script(MOSAIC_SOURCE / "scripts/5fold_train_all.py", "mosaic_5fold_train_all")
UPSTREAM_INFER = import_script(MOSAIC_SOURCE / "scripts/infer_and_submit.py", "mosaic_infer_and_submit")


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_split_manifest(config: dict[str, Any], result_root: Path, manifest_path: Path) -> list[dict[str, Any]]:
    split_path = REPO_ROOT / config["dataset"]["split_path"]
    fold = int(config["dataset"]["fold"])
    train_cases, val_cases = load_fold_case_sets(split_path, fold)
    records = build_myops_manifest(REPO_ROOT / "data/CARE_Challenge")
    seen = {str(r["case_id"]) for r in records}
    missing = sorted((train_cases | val_cases) - seen)
    if missing:
        raise FileNotFoundError(f"split cases missing from MoSAIC manifest: {missing[:10]}")
    for rec in records:
        cid = str(rec["case_id"])
        if cid in val_cases:
            rec["fold"] = 0
            rec["care_split_role"] = "val"
        elif cid in train_cases:
            rec["fold"] = 1
            rec["care_split_role"] = "train"
        else:
            raise ValueError(f"case {cid} is not in CARE fold0 train or val")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(records, manifest_path)
    audit_rows = []
    for rec in sorted(records, key=lambda r: str(r["case_id"])):
        audit_rows.append(
            {
                "case_id": rec["case_id"],
                "center": rec["center"],
                "split_role": rec["care_split_role"],
                "mosaic_fold_field": rec["fold"],
                "available_modalities": "+".join(rec.get("available_modalities", [])),
                "has_scar": int(bool(rec.get("has_scar"))),
                "has_edema": int(bool(rec.get("has_edema"))),
                "status": "PASS_EXACT_FOLD0",
            }
        )
    write_csv(result_root / "fold0_split_audit.csv", audit_rows)
    write_json(
        result_root / "benchmark_contract.json",
        {
            "task_key": config["task_key"],
            "fold": fold,
            "split_path": config["dataset"]["split_path"],
            "train_count": len(train_cases),
            "val_count": len(val_cases),
            "expected_train_count": int(config["dataset"]["expected_train_count"]),
            "expected_val_count": int(config["dataset"]["expected_val_count"]),
            "train_count_status": "PASS" if len(train_cases) == int(config["dataset"]["expected_train_count"]) else "FAIL",
            "val_count_status": "PASS" if len(val_cases) == int(config["dataset"]["expected_val_count"]) else "FAIL",
            "primary_comparison": ["nnunet_fold0", "mosaic_fold0_random_init"],
            "secondary_comparison_policy": "canonical_if_existing_predictions_else_historical_noncanonical",
            "forbidden_actions": ["validation_upload", "docker_build", "git_push", "new_hybrid_training"],
            "full_data_mosaic_weights_policy": "forbidden_for_fold0_training_or_fold0_performance_comparison",
        },
    )
    return records


def write_weight_provenance(config: dict[str, Any], result_root: Path, manifest_path: Path) -> None:
    source_files = [
        DEFAULT_CONFIG,
        REPO_ROOT / config["dataset"]["split_path"],
        MOSAIC_SOURCE / "configs/myops_coarse.yaml",
        MOSAIC_SOURCE / "configs/myops_fine.yaml",
        MOSAIC_SOURCE / "configs/myops_edema.yaml",
        MOSAIC_SOURCE / "configs/myops_edema_fine.yaml",
        manifest_path,
    ]
    rows = []
    for path in source_files:
        rows.append({"path": rel(path), "exists": path.is_file(), "sha256": sha256_file(path) if path.is_file() else None})
    write_json(
        result_root / "weight_provenance.json",
        {
            "status": "PASS_RANDOM_INIT_FOLD0_ONLY",
            "mosaic_submission_weight_root": str(Path(config["external_assets"]["mosaic_root_default"])),
            "submission_weights_used_for_fold0_training": False,
            "submission_weights_used_for_fold0_initialization": False,
            "submission_weights_used_for_fold0_comparison": False,
            "submission_weights_allowed_scope": "model-load or official-validation deployment smoke only",
            "fold0_checkpoint_root": rel(result_root / "runtime/fold0"),
            "source_files": rows,
        },
    )


def runtime_root(result_root: Path) -> Path:
    return result_root / "runtime/fold0"


def manifest_path(result_root: Path) -> Path:
    return runtime_root(result_root) / "manifest_fold0_exact.jsonl"


def cache_dir(result_root: Path) -> Path:
    return runtime_root(result_root) / "cache"


def ensure_exact_manifest(config: dict[str, Any], result_root: Path) -> list[dict[str, Any]]:
    path = manifest_path(result_root)
    records = write_split_manifest(config, result_root, path)
    write_weight_provenance(config, result_root, path)
    return records


def stage_coarse(config: dict[str, Any], result_root: Path, gpu: int) -> None:
    records = ensure_exact_manifest(config, result_root)
    rroot = runtime_root(result_root)
    coarse_dir = rroot / "coarse"
    coarse_cfg = UPSTREAM_5FOLD.build_myops_coarse_config(rroot)
    myops_cached = (cache_dir(result_root) / "myops").exists()
    if not (coarse_dir / "experiment_result.json").is_file():
        UPSTREAM_5FOLD.run_worker(
            coarse_cfg,
            "coarse",
            0,
            str(REPO_ROOT / "data/CARE_Challenge"),
            str(coarse_dir),
            str(cache_dir(result_root)),
            "myops",
            str(manifest_path(result_root)),
            gpu_id=gpu,
            skip_preprocess=myops_cached,
        )
    ckpt = coarse_dir / "best.pt"
    if not ckpt.is_file():
        ckpt = coarse_dir / "last.pt"
    if not ckpt.is_file():
        raise FileNotFoundError(f"coarse checkpoint missing: {coarse_dir}")
    UPSTREAM_5FOLD.generate_coarse_predictions(
        str(ckpt),
        records,
        str(cache_dir(result_root)),
        str(rroot / "coarse_predictions"),
        "myops",
        gpu,
    )


def stage_scar(config: dict[str, Any], result_root: Path, gpu: int) -> None:
    ensure_exact_manifest(config, result_root)
    coarse_pred_dir = runtime_root(result_root) / "coarse_predictions"
    if not coarse_pred_dir.is_dir():
        raise FileNotFoundError(f"coarse predictions missing: {coarse_pred_dir}")
    out = runtime_root(result_root) / "fine_scar"
    if not (out / "experiment_result.json").is_file():
        UPSTREAM_5FOLD.run_worker(
            str(MOSAIC_SOURCE / "configs/myops_fine.yaml"),
            "fine",
            0,
            str(REPO_ROOT / "data/CARE_Challenge"),
            str(out),
            str(cache_dir(result_root)),
            "myops",
            str(manifest_path(result_root)),
            str(coarse_pred_dir),
            gpu,
            skip_preprocess=True,
        )


def stage_edema(config: dict[str, Any], result_root: Path, gpu: int) -> None:
    records = ensure_exact_manifest(config, result_root)
    coarse_pred_dir = runtime_root(result_root) / "coarse_predictions"
    if not coarse_pred_dir.is_dir():
        raise FileNotFoundError(f"coarse predictions missing: {coarse_pred_dir}")
    from myops.data.splits import split_records_by_fold

    train_records, val_records = split_records_by_fold(records, 0)
    out = runtime_root(result_root) / "edema"
    if not (out / "last.pt").is_file():
        UPSTREAM_5FOLD.train_edema_net(train_records, val_records, str(cache_dir(result_root)), str(coarse_pred_dir), out, gpu)


def build_coarse_model(device: torch.device, ckpt_path: Path):
    cfg = UPSTREAM_INFER.load_config(str(MOSAIC_SOURCE / "configs/myops_coarse.yaml"))
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
    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"])
    return model.to(device).eval()


def build_scar_model(device: torch.device, ckpt_path: Path):
    cfg = UPSTREAM_INFER.load_config(str(MOSAIC_SOURCE / "configs/myops_fine.yaml"))
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
    ckpt = torch.load(str(ckpt_path), map_location="cpu", weights_only=False)
    model.load_state_dict(ckpt["model_state"], strict=False)
    return model.to(device).eval()


def checkpoint(path: Path, fallbacks: list[str]) -> Path:
    for name in fallbacks:
        candidate = path / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"no checkpoint in {path}: {fallbacks}")


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


def sitk_write_like(array_zyx: np.ndarray, reference_path: Path, dest: Path) -> None:
    ref = sitk.ReadImage(str(reference_path))
    oriented = orient_array_to_reference_zyx(array_zyx, ref)
    img = sitk.GetImageFromArray(oriented.astype(np.int16, copy=False))
    img.CopyInformation(ref)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(img, str(dest))


def normalize_prediction(raw_path: Path, gt_path: Path, flat_path: Path, case_id: str) -> dict[str, Any]:
    gt_img = sitk.ReadImage(str(gt_path))
    raw_img = sitk.ReadImage(str(raw_path))
    raw_arr = sitk.GetArrayFromImage(raw_img).astype(np.int32, copy=False)
    raw_sig = geometry_signature(raw_img)
    gt_sig = geometry_signature(gt_img)
    raw_status = "PASS" if geometry_matches(raw_sig, gt_sig) else "FAIL_STANDARDIZED_AFTER_AUDIT"
    if raw_status == "PASS":
        std_img = raw_img
    else:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(gt_img)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        std_img = resampler.Execute(raw_img)
    flat_path.parent.mkdir(parents=True, exist_ok=True)
    sitk.WriteImage(std_img, str(flat_path))
    std_sig = geometry_signature(std_img)
    std_match = geometry_matches(std_sig, gt_sig)
    return {
        "case_id": case_id,
        "raw_prediction_path": rel(raw_path),
        "normalized_prediction_path": rel(flat_path),
        "nested_output_normalized": int(flat_path.is_file()),
        "label_space": "official",
        "canonical_eval_prediction_path": rel(flat_path),
        "raw_geometry_status": raw_status,
        "raw_size_xyz": raw_sig["size_xyz"],
        "gt_size_xyz": gt_sig["size_xyz"],
        "raw_spacing_xyz": raw_sig["spacing_xyz"],
        "gt_spacing_xyz": gt_sig["spacing_xyz"],
        "standardized_geometry_status": "PASS" if std_match else "FAIL",
        "raw_unique_labels": sorted(int(x) for x in np.unique(raw_arr)),
    }


def stage_infer(config: dict[str, Any], result_root: Path, gpu: int) -> None:
    ensure_exact_manifest(config, result_root)
    os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rroot = runtime_root(result_root)
    coarse = build_coarse_model(device, checkpoint(rroot / "coarse", ["best.pt", "last.pt"]))
    scar = build_scar_model(device, checkpoint(rroot / "fine_scar", ["best.pt", "last.pt"]))
    edema = load_edema_model(str(checkpoint(rroot / "edema", ["best.pt", "last.pt"])), device)
    tta = {"enabled": True, "flips": ["horizontal", "vertical"]}
    thresholds = UPSTREAM_INFER.default_thresholds(TRACK_MYOPS, "fine")
    raw_root = result_root / "native_mosaic_raw_nested/MyoPS/Anonymous Center"
    flat_root = result_root / "native_mosaic_predictions"
    compact_root = result_root / "native_mosaic_predictions_compact"
    rows = []
    for case_id in load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"])):
        payload = torch_load(cache_path(str(cache_dir(result_root)), TRACK_MYOPS, case_id))
        with torch.no_grad():
            coarse_result = predict_case_coarse(coarse, payload, TRACK_MYOPS, device, image_size=[192, 192], tta_config=tta)
            coarse_prior = np.asarray(coarse_result["label"], dtype=np.int16)
            scar_result = predict_case_fine(scar, payload, TRACK_MYOPS, device, coarse_prior=coarse_prior, image_size=[192, 192], tta_config=tta)
            ucf_probs = np.asarray(scar_result["probs"], dtype=np.float32)
            edema_prob = predict_edema_case_probs(edema, payload, coarse_prior, device, dim=192)
        ucf_probs_orig = UPSTREAM_INFER.probs_to_original_space(ucf_probs, payload)
        edema_prob_orig = UPSTREAM_INFER.probs_to_original_space(edema_prob[None], payload)[0]
        ucf_label_orig = UPSTREAM_INFER.probs_to_label(ucf_probs_orig, thresholds)
        coarse_orig = UPSTREAM_INFER.label_to_original_space(coarse_prior, payload)
        myo_mask = binary_dilation(coarse_orig > 0, iterations=1)
        ucf_label_orig = enforce_pathology_inside_myo(ucf_label_orig, 1, [4, 5], external_myo_mask=myo_mask)
        ucf_label_orig = clean_prediction_by_class(ucf_label_orig, {4: 5, 5: 3})
        edema_zone = edema_prob_orig > 0.35
        if edema_zone.any():
            edema_zone = largest_component(edema_zone)
        edema_zone = edema_zone & myo_mask
        final_label_hwz = merge_labels(ucf_label_orig, coarse_orig, edema_zone)
        final_label_hwz = clean_prediction_by_class(final_label_hwz, {4: 5, 5: 3})
        scar_mask = final_label_hwz == 5
        if scar_mask.any():
            final_label_hwz[scar_mask & ~largest_component(scar_mask)] = 0
        official_hwz = train_to_official_labels(final_label_hwz, TRACK_MYOPS, stage="fine")
        official_zyx = np.transpose(official_hwz, (2, 0, 1))
        compact_zyx = remap_labels(official_zyx, OFFICIAL_TO_COMPACT)
        raw_path = raw_root / case_id / f"{case_id}_pred.nii.gz"
        gt_path = REPO_ROOT / config["dataset"]["raw_label_dir"] / f"{case_id}.nii.gz"
        sitk_write_like(official_zyx, gt_path, raw_path)
        rows.append(normalize_prediction(raw_path, gt_path, flat_root / f"{case_id}.nii.gz", case_id))
        sitk_write_like(compact_zyx, gt_path, compact_root / f"{case_id}.nii.gz")
    expected_count = len(load_fold_val_cases(REPO_ROOT / config["dataset"]["split_path"], int(config["dataset"]["fold"])))
    adapter_pass = (
        len(rows) == expected_count
        and all(row.get("standardized_geometry_status") == "PASS" for row in rows)
        and all(int(row.get("nested_output_normalized", 0)) == 1 for row in rows)
    )
    write_json(
        result_root / "runtime_adapter_audit.json",
        {
            "status": "PASS" if adapter_pass else "FAIL",
            "myops_only": True,
            "cine_called": False,
            "expected_case_count": expected_count,
            "normalized_case_count": len(rows),
            "flat_prediction_dir": rel(flat_root),
            "compact_prediction_dir": rel(compact_root),
            "raw_nested_prediction_dir": rel(raw_root),
            "rows": rows,
        },
    )
    write_csv(result_root / "runtime_adapter_audit.csv", rows)


def preflight(config: dict[str, Any], result_root: Path) -> None:
    records = ensure_exact_manifest(config, result_root)
    payload = {
        "status": "PASS",
        "python_executable": sys.executable,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "mosaic_source": rel(MOSAIC_SOURCE),
        "manifest": rel(manifest_path(result_root)),
        "record_count": len(records),
        "train_count": sum(1 for r in records if r["care_split_role"] == "train"),
        "val_count": sum(1 for r in records if r["care_split_role"] == "val"),
    }
    write_json(result_root / "mosaic_fold0_preflight.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    ap.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    ap.add_argument("--stage", choices=["preflight", "coarse", "scar", "edema", "infer"], required=True)
    ap.add_argument("--gpu", type=int, default=0)
    args = ap.parse_args()
    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    result_root.mkdir(parents=True, exist_ok=True)
    config = load_yaml(args.config if args.config.is_absolute() else REPO_ROOT / args.config)
    if args.stage == "preflight":
        preflight(config, result_root)
    elif args.stage == "coarse":
        stage_coarse(config, result_root, args.gpu)
    elif args.stage == "scar":
        stage_scar(config, result_root, args.gpu)
    elif args.stage == "edema":
        stage_edema(config, result_root, args.gpu)
    elif args.stage == "infer":
        stage_infer(config, result_root, args.gpu)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
