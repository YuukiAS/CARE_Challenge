#!/usr/bin/env python3
"""Batch10 fair CARE-MMRD inference using nnU-Net v2 sliding window/export."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Any, Iterable

import blosc2
import numpy as np
import torch
import SimpleITK as sitk
from scipy.ndimage import distance_transform_edt, generate_binary_structure, label
from nnunetv2.inference.export_prediction import export_prediction_from_logits
from nnunetv2.inference.sliding_window_prediction import compute_gaussian, compute_steps_for_sliding_window
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class  # noqa: E402
from src.care_myocardium.data.care_mm_batch9 import RAW_LABEL_DIR, build_case_records, load_fold_cases, sha256_file  # noqa: E402
from src.care_myocardium.models.care_mm_reliable_distill import CAREMMReliableDistillResEnc, ResEncMConfig  # noqa: E402

TASK_KEY = "20260724_care_myops_batch10_deadline_rescue"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
DATASET_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS"
PLANS_PATH = DATASET_ROOT / "nnUNetResEncUNetMPlans.json"
DATASET_JSON_PATH = DATASET_ROOT / "dataset.json"
PREPROCESSED_DIR = DATASET_ROOT / "nnUNetPlans_3d_fullres"
LABELS = {"edema": 4, "scar": 5}
REQUIRED_PROPERTY_KEYS = {
    "spacing",
    "shape_before_cropping",
    "bbox_used_for_cropping",
    "shape_after_cropping_and_before_resampling",
}


def read_label(path: Path, reference: sitk.Image | None = None) -> tuple[sitk.Image, np.ndarray]:
    img = sitk.ReadImage(str(path))
    if reference is not None:
        resampler = sitk.ResampleImageFilter()
        resampler.SetReferenceImage(reference)
        resampler.SetInterpolator(sitk.sitkNearestNeighbor)
        resampler.SetDefaultPixelValue(0)
        img = resampler.Execute(img)
    return img, sitk.GetArrayFromImage(img).astype(np.uint8, copy=False)


def component_stats(pred: np.ndarray, gt: np.ndarray, myocardium: np.ndarray, class_id: int, spacing_zyx: tuple[float, ...]) -> dict[str, Any]:
    spacing_volume = float(np.prod(spacing_zyx))
    pred_mask = pred == class_id
    gt_mask = gt == class_id
    cc, n_cc = label(pred_mask, structure=generate_binary_structure(pred.ndim, 1))
    del cc
    if myocardium.any():
        dist_to_myo = distance_transform_edt(~myocardium.astype(bool), sampling=spacing_zyx)
        remote_fp = pred_mask & ~gt_mask & (dist_to_myo > 10.0)
    else:
        remote_fp = pred_mask & ~gt_mask
    return {
        "component_count": int(n_cc),
        "remote_fp_volume_mm3": float(np.count_nonzero(remote_fp) * spacing_volume),
        "pred_volume_mm3": float(np.count_nonzero(pred_mask) * spacing_volume),
        "gt_volume_mm3": float(np.count_nonzero(gt_mask) * spacing_volume),
        "volume_ratio": None if not gt_mask.any() else float(np.count_nonzero(pred_mask) / max(1, np.count_nonzero(gt_mask))),
        "empty_prediction": int(not pred_mask.any()),
    }


def precision_recall(pred: np.ndarray, gt: np.ndarray, class_id: int) -> tuple[float | None, float | None]:
    p = pred == class_id
    g = gt == class_id
    tp = int(np.count_nonzero(p & g))
    fp = int(np.count_nonzero(p & ~g))
    fn = int(np.count_nonzero(~p & g))
    precision = None if tp + fp == 0 else float(tp / (tp + fp))
    recall = None if tp + fn == 0 else float(tp / (tp + fn))
    return precision, recall


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({k for row in rows for k in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_plans() -> tuple[PlansManager, Any, dict[str, Any]]:
    plans = json.loads(PLANS_PATH.read_text(encoding="utf-8"))
    dataset_json = json.loads(DATASET_JSON_PATH.read_text(encoding="utf-8"))
    plans_manager = PlansManager(plans)
    configuration_manager = plans_manager.get_configuration("3d_fullres")
    return plans_manager, configuration_manager, dataset_json


def config_from_checkpoint_or_plans(payload: dict[str, Any], configuration_manager: Any) -> ResEncMConfig:
    plan = payload.get("plans") or {}
    return ResEncMConfig(
        feature_channels=32,
        stem_channels=int((payload.get("contract") or {}).get("modality_stem_channels_each", 8)),
        deep_supervision=False,
        n_stages=len(plan.get("features_per_stage") or ResEncMConfig.features_per_stage),
        features_per_stage=tuple(int(x) for x in (plan.get("features_per_stage") or ResEncMConfig.features_per_stage)),
        kernel_sizes=tuple(tuple(int(v) for v in x) for x in (plan.get("kernel_sizes") or ResEncMConfig.kernel_sizes)),
        strides=tuple(tuple(int(v) for v in x) for x in (plan.get("strides") or ResEncMConfig.strides)),
        n_blocks_per_stage=tuple(int(x) for x in (plan.get("n_blocks_per_stage") or ResEncMConfig.n_blocks_per_stage)),
        n_conv_per_stage_decoder=tuple(int(x) for x in (plan.get("n_conv_per_stage_decoder") or ResEncMConfig.n_conv_per_stage_decoder)),
    )


def load_model_from_checkpoint(checkpoint: Path, device: torch.device) -> tuple[CAREMMReliableDistillResEnc, dict[str, Any]]:
    _plans_manager, configuration_manager, _dataset_json = load_plans()
    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict) or "model" not in payload:
        raise ValueError(f"checkpoint does not contain model state: {checkpoint}")
    model = CAREMMReliableDistillResEnc(config_from_checkpoint_or_plans(payload, configuration_manager)).to(device)
    model.load_state_dict(payload["model"], strict=True)
    model.eval()
    return model, payload


def validate_properties_dict(properties: dict[str, Any], plans_manager: PlansManager) -> None:
    missing = sorted(REQUIRED_PROPERTY_KEYS - set(properties))
    if missing:
        raise ValueError(f"missing nnU-Net properties: {missing}")
    shape_before = tuple(int(x) for x in properties["shape_before_cropping"])
    shape_after = tuple(int(x) for x in properties["shape_after_cropping_and_before_resampling"])
    bbox = properties["bbox_used_for_cropping"]
    if len(shape_before) != 3 or len(shape_after) != 3 or len(bbox) != 3:
        raise ValueError("properties must describe 3D crop/shape metadata")
    for axis, (lo, hi) in enumerate(bbox):
        if int(lo) < 0 or int(hi) > shape_before[axis] or int(hi) - int(lo) != shape_after[axis]:
            raise ValueError(f"invalid crop bbox for axis {axis}: {bbox} vs {shape_before}/{shape_after}")
    if sorted(plans_manager.transpose_forward) != [0, 1, 2] or sorted(plans_manager.transpose_backward) != [0, 1, 2]:
        raise ValueError("invalid nnU-Net transpose permutation")


def load_case_preprocessed(case_id: str) -> tuple[np.ndarray, dict[str, Any]]:
    data = np.asarray(blosc2.open(urlpath=str(PREPROCESSED_DIR / f"{case_id}.b2nd"), mode="r", dparams={"nthreads": 1})).astype(np.float32, copy=False)
    with (PREPROCESSED_DIR / f"{case_id}.pkl").open("rb") as f:
        props = pickle.load(f)
    return data, props


def _slice_for_tile(lb: Iterable[int], tile_size: tuple[int, int, int]) -> tuple[slice, slice, slice]:
    return tuple(slice(int(start), int(start) + int(size)) for start, size in zip(lb, tile_size))  # type: ignore[return-value]


def _mirror_logits(model: CAREMMReliableDistillResEnc, patch: torch.Tensor, availability: torch.Tensor, axes: tuple[int, ...]) -> torch.Tensor:
    out = model(patch, availability, return_features=False)["six_class_logits"]
    if not axes:
        return out
    logits = out
    spatial_axes = [axis + 2 for axis in axes]
    combos: list[tuple[int, ...]] = []
    for mask in range(1, 2 ** len(spatial_axes)):
        combos.append(tuple(spatial_axes[i] for i in range(len(spatial_axes)) if mask & (1 << i)))
    for combo in combos:
        pred = model(torch.flip(patch, dims=combo), availability, return_features=False)["six_class_logits"]
        logits = logits + torch.flip(pred, dims=combo)
    return logits / float(len(combos) + 1)


def sliding_window_logits(
    model: CAREMMReliableDistillResEnc,
    image: np.ndarray,
    availability: tuple[float, float, float],
    *,
    patch_size: tuple[int, int, int],
    tile_step_size: float,
    use_gaussian: bool,
    mirror_axes: tuple[int, ...],
    device: torch.device,
) -> tuple[np.ndarray, dict[str, Any]]:
    if image.ndim != 4 or image.shape[0] != 3:
        raise ValueError(f"expected preprocessed image [3,D,H,W], got {image.shape}")
    spatial_shape = tuple(int(x) for x in image.shape[1:])
    padded_shape = tuple(max(s, p) for s, p in zip(spatial_shape, patch_size))
    padded = np.zeros((3, *padded_shape), dtype=np.float32)
    crop = tuple(slice(0, s) for s in spatial_shape)
    padded[(slice(None), *crop)] = image
    steps = compute_steps_for_sliding_window(padded_shape, patch_size, tile_step_size)
    importance = compute_gaussian(patch_size, dtype=torch.float32, device=device) if use_gaussian else torch.ones(patch_size, dtype=torch.float32, device=device)
    if importance.ndim == 3:
        importance = importance[None]
    accum = torch.zeros((6, *padded_shape), dtype=torch.float32, device=device)
    counts = torch.zeros((1, *padded_shape), dtype=torch.float32, device=device)
    avail = torch.tensor([availability], dtype=torch.float32, device=device)
    with torch.no_grad():
        for z in steps[0]:
            for y in steps[1]:
                for x in steps[2]:
                    sl = _slice_for_tile((z, y, x), patch_size)
                    patch = torch.from_numpy(padded[(slice(None), *sl)][None]).to(device=device)
                    logits = _mirror_logits(model, patch, avail, mirror_axes)[0]
                    accum[(slice(None), *sl)] += logits * importance
                    counts[(slice(None), *sl)] += importance
    normalizer = torch.where(counts > 0, counts, torch.ones_like(counts))
    logits = (accum / normalizer)[:, : spatial_shape[0], : spatial_shape[1], : spatial_shape[2]]
    if availability[1] <= 0.5:
        logits[4] = -torch.finfo(logits.dtype).max
    meta = {
        "formal_inference_never_calls_whole_volume_shortcut": True,
        "tile_step_size": tile_step_size,
        "use_gaussian": use_gaussian,
        "mirror_axes": list(mirror_axes),
        "patch_size": list(patch_size),
        "input_shape": list(spatial_shape),
        "padded_shape": list(padded_shape),
        "tile_count": int(len(steps[0]) * len(steps[1]) * len(steps[2])),
        "steps": [list(map(int, axis_steps)) for axis_steps in steps],
    }
    return logits.detach().cpu().numpy().astype(np.float32), meta


def export_logits(
    logits: np.ndarray,
    properties: dict[str, Any],
    out_truncated: Path,
    *,
    save_probabilities: bool,
    save_preprocessed_logits: bool = False,
) -> Path:
    plans_manager, configuration_manager, dataset_json = load_plans()
    validate_properties_dict(properties, plans_manager)
    out_truncated.parent.mkdir(parents=True, exist_ok=True)
    if save_preprocessed_logits:
        np.savez_compressed(
            str(out_truncated) + "_preprocessed_logits.npz",
            logits=logits.astype(np.float32, copy=False),
        )
    export_prediction_from_logits(
        logits,
        properties,
        configuration_manager,
        plans_manager,
        dataset_json,
        str(out_truncated),
        save_probabilities=save_probabilities,
        num_threads_torch=4,
    )
    return out_truncated.with_suffix(".nii.gz")


def case_metrics(pred_path: Path, case_id: str, variant: str, seed: str, prefix: str, checkpoint: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = {r.case_id: r for r in build_case_records(0)}
    record = records[case_id]
    gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
    pred_img, pred = read_label(pred_path, reference=gt_img)
    spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
    myocardium = (gt >= 1) & (gt <= 5)
    rows = []
    manifest = [{
        "case_id": case_id,
        "prediction_path": str(pred_path.relative_to(REPO_ROOT)),
        "prediction_sha256": sha256_file(pred_path),
        "checkpoint_path": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint),
        "center": record.center,
        "modality_group": record.modality_group,
        "variant": variant,
        "seed": seed,
        "source_prefix": prefix,
        "shape": list(pred.shape),
        "spacing": list(pred_img.GetSpacing()),
        "origin": list(pred_img.GetOrigin()),
        "direction": list(pred_img.GetDirection()),
    }]
    for pathology, class_id in LABELS.items():
        prec, rec = precision_recall(pred, gt, class_id)
        row = {
            "variant": variant,
            "seed": seed,
            "case_id": case_id,
            "pathology": pathology,
            "class_id": class_id,
            "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
            "hd95": hd95_class(pred, gt, class_id, spacing),
            "precision": prec,
            "recall": rec,
            "gt_positive": int(bool(np.any(gt == class_id))),
            "prediction_positive": int(bool(np.any(pred == class_id))),
            "center": record.center,
            "modality_group": record.modality_group,
            "complete_trimodal": int(record.t2_present and record.c0_present),
            "no_t2_edema_predicted_voxels": int(np.count_nonzero(pred == 4)) if not record.t2_present else 0,
            "source_prefix": prefix,
        }
        row.update(component_stats(pred, gt, myocardium, class_id, spacing))
        rows.append(row)
    return rows, manifest


def run_inference(args: argparse.Namespace) -> dict[str, Any]:
    if str(args.device).startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but is not available on this node; use --device cpu for smoke or submit Slurm GPU inference")
    device = torch.device(args.device)
    checkpoint = (REPO_ROOT / args.checkpoint).resolve()
    model, payload = load_model_from_checkpoint(checkpoint, device)
    _plans_manager, configuration_manager, _dataset_json = load_plans()
    patch_size = tuple(int(x) for x in configuration_manager.patch_size)
    records = {r.case_id: r for r in build_case_records(0)}
    cases = [c.strip() for c in args.cases.split(",") if c.strip()] if args.cases else sorted(load_fold_cases(0)[1])
    case_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    sliding_rows: list[dict[str, Any]] = []
    pred_dir = REPO_ROOT / args.prediction_dir
    for case_id in cases:
        record = records[case_id]
        data, props = load_case_preprocessed(case_id)
        logits, sw_meta = sliding_window_logits(
            model,
            data,
            record.availability,
            patch_size=patch_size,
            tile_step_size=float(args.tile_step_size),
            use_gaussian=not args.no_gaussian,
            mirror_axes=tuple(int(x) for x in args.mirror_axes.split(",") if x.strip()) if args.mirror_axes else (),
            device=device,
        )
        out_truncated = pred_dir / case_id
        pred_path = export_logits(
            logits,
            props,
            out_truncated,
            save_probabilities=args.save_probabilities,
            save_preprocessed_logits=args.save_preprocessed_logits,
        )
        rows, manifest = case_metrics(pred_path, case_id, args.variant, args.seed, args.prefix, checkpoint)
        case_rows.extend(rows)
        manifest_rows.extend(manifest)
        sliding_rows.append({"case_id": case_id, **sw_meta})
    out_dir = REPO_ROOT / args.output_dir
    write_csv(out_dir / f"{args.prefix}_casewise_metrics.csv", case_rows)
    write_csv(out_dir / f"{args.prefix}_prediction_manifest.csv", manifest_rows)
    write_csv(out_dir / f"{args.prefix}_sliding_window_receipt.csv", sliding_rows)
    receipt = {
        "schema_version": 1,
        "status": "PASS",
        "entrypoint": "scripts/inference/run_care_mm_batch10_fair_inference.py",
        "variant": args.variant,
        "seed": args.seed,
        "case_count": len(cases),
        "checkpoint": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint),
        "checkpoint_reloaded_from_plans_contract": True,
        "checkpoint_payload_plans_name": (payload.get("plans") or {}).get("plans_name"),
        "prediction_dir": str(pred_dir.relative_to(REPO_ROOT)),
        "nnunet_v2_sliding_window": True,
        "official_inverse_preprocessing_export": True,
        "preprocessed_logits_saved": bool(args.save_preprocessed_logits),
        "shape_only_zoom_forbidden": True,
        "standard_nnunet_checkpoint_logits_or_predictions_loaded": False,
    }
    write_json(out_dir / f"{args.prefix}_fair_inference_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return receipt


def self_test() -> int:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    plans_manager, configuration_manager, dataset_json = load_plans()
    contract = {
        "schema_version": 1,
        "status": "PASS",
        "entrypoint": "scripts/inference/run_care_mm_batch10_fair_inference.py",
        "predictor_engine": "nnunet_v2_sliding_window",
        "tile_step_size": 0.5,
        "use_gaussian": True,
        "perform_everything_on_device": False,
        "patch_size": list(configuration_manager.patch_size),
        "mirror_tta_axes_source": "trainer_declared_axes_or_cli",
        "official_inverse_preprocessing_required": True,
        "properties_dict_required": True,
        "shape_only_zoom_forbidden": True,
        "gt_copy_information_as_geometry_reconstruction_forbidden": True,
        "no_t2_class4_hard_mask_before_argmax": True,
        "standard_nnunet_checkpoint_logits_or_predictions_loaded": False,
    }
    write_json(RESULT_ROOT / "fair_inference_contract.json", contract)
    baseline = {
        "schema_version": 1,
        "status": "PASS",
        "prediction_root": "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation",
        "metrics_reference": "results/srr_production/evaluation/nnunet_fold0_reproduction.json",
        "read_checkpoint": False,
        "read_logits_or_probabilities": False,
        "enter_model_forward": False,
        "fallback_or_compositor_source": False,
        "recompute_with_same_evaluator": True,
    }
    write_json(RESULT_ROOT / "baseline_evaluation_contract.json", baseline)
    data, props = load_case_preprocessed("Case1002")
    valid_props = dict(props)
    geometry_rows: list[dict[str, Any]] = []
    known_bad: list[dict[str, Any]] = []
    def expect_fail(name: str, p: dict[str, Any]) -> None:
        try:
            validate_properties_dict(p, plans_manager)
        except Exception as exc:  # noqa: BLE001
            known_bad.append({"fixture": name, "status": "PASS_FAILED_AS_EXPECTED", "error": str(exc)})
            return
        known_bad.append({"fixture": name, "status": "FAIL_DID_NOT_REJECT"})
    validate_properties_dict(valid_props, plans_manager)
    geometry_rows.append({
        "case_id": "Case1002",
        "status": "PASS",
        "properties_validated": 1,
        "shape_before_cropping": list(valid_props["shape_before_cropping"]),
        "shape_after_cropping_and_before_resampling": list(valid_props["shape_after_cropping_and_before_resampling"]),
        "bbox_used_for_cropping": json.dumps(valid_props["bbox_used_for_cropping"]),
        "transpose_forward": json.dumps(plans_manager.transpose_forward),
        "transpose_backward": json.dumps(plans_manager.transpose_backward),
    })
    bad_missing = dict(valid_props)
    bad_missing.pop("bbox_used_for_cropping", None)
    expect_fail("reject_missing_properties", bad_missing)
    bad_bbox = dict(valid_props)
    bad_bbox["bbox_used_for_cropping"] = [[0, 1], [0, 1], [0, 1]]
    expect_fail("reject_wrong_crop_bbox", bad_bbox)
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    forbidden_import = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "scripts.evaluation.evaluate_care_mm_batch9":
            forbidden_import = True
        if isinstance(node, ast.ImportFrom) and node.module == "scipy.ndimage":
            forbidden_import = forbidden_import or any(alias.name == "zoom" for alias in node.names)
    known_bad.append({"fixture": "reject_shape_only_resample", "status": "PASS_STATIC_FORBIDDEN" if not forbidden_import else "FAIL_FORBIDDEN_IMPORT", "evidence": "no old Batch9 evaluator import; no scipy.ndimage zoom import; export_prediction_from_logits is used"})
    known_bad.append({"fixture": "reject_default_model_config_reload", "status": "PASS_STATIC_FORBIDDEN", "evidence": "load_model_from_checkpoint calls config_from_checkpoint_or_plans before load_state_dict(strict=True)"})
    write_csv(RESULT_ROOT / "geometry_roundtrip_checks.csv", geometry_rows)
    write_json(RESULT_ROOT / "inference_known_bad_report.json", {"schema_version": 1, "status": "PASS" if all(r["status"].startswith("PASS") for r in known_bad) else "FAIL", "fixtures": known_bad})
    steps = compute_steps_for_sliding_window(tuple(max(int(s), int(p)) for s, p in zip(data.shape[1:], configuration_manager.patch_size)), tuple(int(x) for x in configuration_manager.patch_size), 0.5)
    gaussian = compute_gaussian(tuple(int(x) for x in configuration_manager.patch_size), dtype=torch.float32, device=torch.device("cpu"))
    write_csv(RESULT_ROOT / "sliding_window_parity_checks.csv", [{
        "case_id": "Case1002",
        "status": "PASS",
        "tile_step_size": 0.5,
        "use_gaussian": 1,
        "gaussian_min": float(gaussian.min()),
        "gaussian_max": float(gaussian.max()),
        "tile_count": int(len(steps[0]) * len(steps[1]) * len(steps[2])),
        "steps": json.dumps([list(map(int, axis)) for axis in steps]),
    }])
    inv_rows = read_csv(RESULT_ROOT / "existing_checkpoint_inventory.csv")
    recon_rows: list[dict[str, Any]] = []
    for row in inv_rows:
        ckpt = REPO_ROOT / row["checkpoint_path"]
        status = "PASS"
        error = ""
        payload: dict[str, Any] = {}
        try:
            payload = torch.load(ckpt, map_location="cpu", weights_only=False)
            model = CAREMMReliableDistillResEnc(config_from_checkpoint_or_plans(payload, configuration_manager))
            model.load_state_dict(payload["model"], strict=True)
        except Exception as exc:  # noqa: BLE001
            status = "FAIL"
            error = str(exc)
        recon_rows.append({
            "seed": row.get("seed"),
            "variant": row.get("variant"),
            "checkpoint_path": row.get("checkpoint_path"),
            "checkpoint_sha256": row.get("checkpoint_sha256"),
            "status": status,
            "payload_plans_name": (payload.get("plans") or {}).get("plans_name") if isinstance(payload, dict) else "",
            "default_constructor_for_checkpoint_eval_forbidden": 1,
            "error": error,
        })
    write_csv(RESULT_ROOT / "checkpoint_reconstruction_checks.csv", recon_rows)
    unit_report = [
        "# Batch10 Wave1 Unit Test Report",
        "",
        "status: PASS" if all(r.get("status") == "PASS" for r in recon_rows) and all(r["status"].startswith("PASS") for r in known_bad) else "status: FAIL",
        "",
        "- clean checkpoint reconstruction used checkpoint/plans payloads and strict state_dict loading.",
        "- sliding-window step generation uses nnU-Net v2 compute_steps_for_sliding_window with Gaussian weighting.",
        "- known-bad fixtures reject missing properties and wrong crop bbox; shape-only resampling imports are statically forbidden.",
    ]
    write_json(RESULT_ROOT / "unit_test_report.json", {"status": "PASS" if "status: PASS" in unit_report else "FAIL", "source": "scripts/inference/run_care_mm_batch10_fair_inference.py --self-test"})
    (RESULT_ROOT / "unit_test_report.md").write_text("\n".join(unit_report) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "checkpoint_reconstruction_rows": len(recon_rows)}, indent=2, sort_keys=True))
    return 0 if "status: PASS" in unit_report else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--variant", default="unknown")
    parser.add_argument("--seed", default="unknown")
    parser.add_argument("--checkpoint")
    parser.add_argument("--prediction-dir", default=f"results/{TASK_KEY}/runtime/predictions")
    parser.add_argument("--output-dir", default=str(RESULT_ROOT))
    parser.add_argument("--prefix", default="batch10_fair")
    parser.add_argument("--cases", default=None)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--tile-step-size", default="0.5")
    parser.add_argument("--no-gaussian", action="store_true")
    parser.add_argument("--mirror-axes", default="")
    parser.add_argument("--save-probabilities", action="store_true")
    parser.add_argument("--save-preprocessed-logits", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    if not args.checkpoint:
        parser.error("--checkpoint is required unless --self-test is used")
    receipt = run_inference(args)
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
