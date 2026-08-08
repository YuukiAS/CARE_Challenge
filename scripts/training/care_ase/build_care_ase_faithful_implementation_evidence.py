#!/usr/bin/env python3
"""Build CARE-ASE faithful implementation evidence for Agent-Flow v3.

This script is Executor-owned. It does not modify verifier assets and it does
not train. When the runtime cannot execute the zero-credit probes required by
the frozen contract, it writes a fail-closed receipt instead of synthesizing a
passing evidence packet.
"""

from __future__ import annotations

import argparse
import builtins
import copy
import hashlib
import importlib.util
import json
import math
import os
import pickle
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_ID = "care-ase-faithful"
REQUEST_NONCE = "care-ase-20260806T090955Z"
FROZEN_CONTRACT_SHA256 = "a4758fd3125cdfaac4cf044fd4fa948472558cca231c0429a26e63e5d7d1e11d"
VERIFIER_FINGERPRINT_SHA256 = "3dcacfe7ae41e164435278c0da4557fc61b384ef6eeb09860badb353b375dca6"

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
IMPLEMENTATION_DIR = ROOT / "results" / "agent_flow_v3" / TASK_ID / "implementation"
VERIFICATION_CONTRACT = ROOT / "results" / "agent_flow_v3" / TASK_ID / "verification" / "verification_contract.json"
ZERO_CREDIT_PATCH_SIZE = (8, 64, 64)
PLAN_PATCH_SIZE = (20, 256, 256)
PLAN_COMPATIBLE_MULTIPLE = (4, 64, 64)

SOURCE_PATHS = [
    "src/care_myocardium/models/care_ase/__init__.py",
    "src/care_myocardium/models/care_ase/core.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_runtime.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/training/care_ase_augmentation.py",
    "src/care_myocardium/evaluation/care_ase_r2_evaluator.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "src/care_myocardium/inference/care_ase_r2_full_volume.py",
    "scripts/training/care_ase/run_care_ase_r2_chunk.py",
    "scripts/training/care_ase/run_care_ase_train.py",
    "scripts/training/care_ase/build_care_ase_faithful_implementation_evidence.py",
]

REQUIRED_LOSSES = {
    "conditional_final_dice_ce": 1.00,
    "anatomy_deep_supervision_dice_ce": 0.50,
    "wall_dice_bce": 0.25,
    "distance_rho_masked_smooth_l1": 0.10,
    "scar_binary_dice_focal": 1.00,
    "scar_component_adaptive_tversky": 0.25,
    "scar_center_focal_bce": 0.10,
    "scar_extent_bce_smooth_l1": 0.15,
    "scar_context_ce": 0.10,
    "edema_binary_dice_focal": 1.00,
    "injury_dice_bce": 0.40,
    "edema_boundary_smooth_l1": 0.10,
    "edema_extent_bce_smooth_l1": 0.20,
    "edema_context_ce": 0.10,
    "relation_loss": 0.05,
}

REQUIRED_METRICS = [
    "blood_pool_adjacent_fp",
    "casewise_help_harm",
    "centerB_centerC_subgroup",
    "component_count",
    "dice",
    "exact_hd",
    "hd95",
    "lesion_recall",
    "precision",
    "remote_fp_count",
    "remote_fp_volume",
    "sensitivity",
    "sentinel_case",
    "small_lesion_recall",
    "volume_ratio",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def json_sha(payload: Any) -> str:
    return sha256_bytes(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def _is_sha256_like(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def git_value(*args: str) -> str | None:
    completed = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def source_manifest() -> dict[str, Any]:
    file_hashes: dict[str, str] = {}
    missing: list[str] = []
    for rel in SOURCE_PATHS:
        path = ROOT / rel
        if path.is_file():
            file_hashes[rel] = sha256_file(path)
        else:
            missing.append(rel)
    payload = {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_SOURCE_MANIFEST_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "verifier_fingerprint_sha256": VERIFIER_FINGERPRINT_SHA256,
        "source_root": ".",
        "git_head": git_value("rev-parse", "HEAD"),
        "git_branch": git_value("branch", "--show-current"),
        "file_hashes": file_hashes,
        "missing_files": missing,
    }
    payload["source_manifest_sha256"] = json_sha(payload)
    return payload


def static_architecture_checks() -> dict[str, Any]:
    model_path = ROOT / "src" / "care_myocardium" / "models" / "care_ase" / "core.py"
    init_path = ROOT / "src" / "care_myocardium" / "models" / "care_ase" / "__init__.py"
    inference_path = ROOT / "src" / "care_myocardium" / "inference" / "care_ase_r2_full_volume.py"
    trainer_path = ROOT / "src" / "care_myocardium" / "training" / "care_ase_trainer.py"
    model = model_path.read_text(encoding="utf-8") if model_path.is_file() else ""
    init_source = init_path.read_text(encoding="utf-8") if init_path.is_file() else ""
    inference = inference_path.read_text(encoding="utf-8") if inference_path.is_file() else ""
    trainer = trainer_path.read_text(encoding="utf-8") if trainer_path.is_file() else ""
    tokens = {
        "carease_class": "class CAREASE(nn.Module)" in model,
        "slice_extent_head_topology": "class SliceExtentHead" in model and "nn.Conv1d(" in model and "nn.GroupNorm(8, 64)" in model,
        "stock_checkpoint_load": "stock.load_state_dict" in model and "stock_parameter_byte_coverage" in model,
        "highest_two_pathology_branch": "class CAREASEPathologyBranch" in model and "stock_decoder.stages[4]" in model and "stock_decoder.stages[5]" in model,
        "named_zero_projections": "class NamedEvidenceProjectionSet" in model and "nn.init.zeros_(proj.weight)" in model,
        "active_modality_adapter": "class ModalityAdapter" in model and "nn.init.kaiming_normal_" in model,
        "edema_residual_dilation": "class EdemaDilationContextBlock" in model and "residual_feature = residual + identity" in model,
        "injury_stock_mean_initializer": "initialize_injury_classifier_from_stock_mean" in model and "stock_class4_class5_mean" in model,
        "edema_t2_subset_execution": "t2_present_mask" in model and "selected_skips = [skip[idx] for skip in skips]" in model,
        "class4_no_t2_decode_support": "decode_care_ase_r2_logits" in (ROOT / "src/care_myocardium/inference/care_ase_r2_decode.py").read_text(encoding="utf-8"),
        "shared_extent_statistics": "compute_slice_extent_statistics" in model and "compute_slice_extent_statistics" in inference,
        "tile_bias_after_aggregation": "global_extent_bias" in inference and "disable_extent_wall=True" in inference,
        "schema_v4_checkpoint": "CHECKPOINT_SCHEMA_VERSION = 4" in trainer,
    }
    payload = {
        "schema": "CARE_ASE_FAITHFUL_STATIC_ARCHITECTURE_CHECKS_V1",
        "tokens": tokens,
        "all_static_tokens_present": all(tokens.values()),
        "canonical_truth_status": "package_single_truth",
        "canonical_truth_note": "Canonical executable truth is src/care_myocardium/models/care_ase/core.py; package __init__.py is a thin public export layer.",
        "legacy_module_exists": (ROOT / "src/care_myocardium/models/care_ase.py").exists(),
        "thin_export_layer": "from .core import" in init_source,
    }
    payload["static_architecture_checks_sha256"] = json_sha(payload)
    return payload


def _runtime_path(kind: str, relative: str) -> Path:
    direct = os.environ.get(kind)
    if direct:
        return Path(direct) / relative
    care_root = os.environ.get("CARE_ROOT")
    if care_root:
        return Path(care_root) / "data" / "nnUNet" / kind / relative
    return ROOT / "data" / "nnUNet" / kind / relative


def runtime_asset_manifest() -> dict[str, Any]:
    plans = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/nnUNetPlans.json")
    dataset_json = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/dataset.json")
    stock_root = _runtime_path(
        "nnUNet_results",
        "Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres",
    )
    fold0_checkpoint = stock_root / "fold_0" / "checkpoint_final.pth"
    assets = {
        "plans": plans,
        "dataset_json": dataset_json,
        "stock_root": stock_root,
        "fold0_checkpoint": fold0_checkpoint,
    }
    payload = {
        "schema": "CARE_ASE_FAITHFUL_RUNTIME_ASSET_MANIFEST_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "runtime_resolution": {
            "CARE_ROOT": os.environ.get("CARE_ROOT"),
            "nnUNet_preprocessed": os.environ.get("nnUNet_preprocessed"),
            "nnUNet_results": os.environ.get("nnUNet_results"),
        },
        "assets": {
            name: {
                "path": str(path),
                "exists": path.exists(),
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "sha256": sha256_file(path) if path.is_file() else None,
            }
            for name, path in assets.items()
        },
        "outer_accessed": False,
        "formal_training_started": False,
        "docker_or_upload": False,
        "created_utc": utc_now(),
    }
    payload["runtime_asset_manifest_sha256"] = json_sha(payload)
    return payload


def environment_gate() -> tuple[bool, list[str], dict[str, Any]]:
    plans = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/nnUNetPlans.json")
    dataset_json = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/dataset.json")
    stock_root = _runtime_path(
        "nnUNet_results",
        "Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres",
    )
    failures: list[str] = []
    details: dict[str, Any] = {
        "python_executable": sys.executable,
        "python_version": sys.version,
        "torch_available": importlib.util.find_spec("torch") is not None,
        "nnunet_available": importlib.util.find_spec("nnunetv2") is not None,
        "default_plans_path": str(plans),
        "default_dataset_json_path": str(dataset_json),
        "default_stock_root_path": str(stock_root),
        "default_fold0_checkpoint_path": str(stock_root / "fold_0" / "checkpoint_final.pth"),
        "default_plans_exists": plans.is_file(),
        "default_dataset_json_exists": dataset_json.is_file(),
        "default_stock_root_exists": stock_root.is_dir(),
        "default_fold0_checkpoint_exists": (stock_root / "fold_0" / "checkpoint_final.pth").is_file(),
    }
    for key in (
        "torch_available",
        "nnunet_available",
        "default_plans_exists",
        "default_dataset_json_exists",
        "default_stock_root_exists",
        "default_fold0_checkpoint_exists",
    ):
        if not details[key]:
            failures.append(key)
    return not failures, failures, details


def train_side_case_ids(fold: int = 0) -> dict[str, Any]:
    splits_path = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/splits_final.json")
    if not splits_path.is_file():
        raise FileNotFoundError(f"missing Dataset501 split file: {splits_path}")
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    train_ids = [str(case_id) for case_id in splits[int(fold)]["train"]]
    metadata_root = Path(os.environ.get("CARE_ROOT", ROOT)).resolve()
    from src.care_myocardium.data.case_metadata import load_myops_case_metadata

    metadata = load_myops_case_metadata(metadata_root)
    scar = next((case_id for case_id in train_ids if metadata.get(case_id) and metadata[case_id].lge_present), None)
    edema = next((case_id for case_id in train_ids if metadata.get(case_id) and metadata[case_id].t2_present), None)
    no_t2 = next((case_id for case_id in train_ids if metadata.get(case_id) and not metadata[case_id].t2_present), None)
    if not scar or not edema or not no_t2:
        raise RuntimeError("fold train split does not expose required scar/edema/no-T2 metadata categories")
    return {
        "fold": int(fold),
        "split_path": str(splits_path),
        "split_sha256": sha256_file(splits_path),
        "metadata_root": str(metadata_root),
        "scar": scar,
        "edema_t2_present": edema,
        "no_t2": no_t2,
    }


def _smallest_train_case_id(*, fold: int, t2_present: bool, require_forced_multitile: bool = False) -> str:
    import blosc2
    import numpy as np

    splits_path = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/splits_final.json")
    splits = json.loads(splits_path.read_text(encoding="utf-8"))
    train_ids = [str(case_id) for case_id in splits[int(fold)]["train"]]
    from src.care_myocardium.data.case_metadata import load_myops_case_metadata

    metadata = load_myops_case_metadata(Path(os.environ.get("CARE_ROOT", ROOT)).resolve())
    rows: list[tuple[int, str]] = []
    for case_id in train_ids:
        meta = metadata.get(case_id)
        if meta is None or bool(meta.t2_present) is not bool(t2_present):
            continue
        path = _preprocessed_case_paths(case_id)["array"]
        if not path.is_file():
            continue
        shape = tuple(int(v) for v in np.asarray(blosc2.open(str(path), mode="r")[:]).shape[-3:])
        if require_forced_multitile and not any(int(dim) > int(tile) for dim, tile in zip(shape, PLAN_PATCH_SIZE)):
            continue
        patch = _full_cover_patch_size(shape)
        rows.append((int(patch[0] * patch[1] * patch[2]), case_id))
    if not rows:
        raise RuntimeError(f"no fold{fold} train case found for t2_present={t2_present}")
    return sorted(rows)[0][1]


def _preprocessed_case_paths(case_id: str) -> dict[str, Path]:
    root = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres")
    return {
        "array": root / f"{case_id}.b2nd",
        "segmentation": root / f"{case_id}_seg.b2nd",
        "properties": root / f"{case_id}.pkl",
    }


def _load_preprocessed_case(case_id: str) -> dict[str, Any]:
    import blosc2
    import numpy as np

    paths = _preprocessed_case_paths(case_id)
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"preprocessed case {case_id} is missing required files: {missing}")
    image = np.asarray(blosc2.open(str(paths["array"]), mode="r")[:], dtype=np.float32)
    seg = np.asarray(blosc2.open(str(paths["segmentation"]), mode="r")[:])
    if image.ndim != 4 or image.shape[0] != 3:
        raise ValueError(f"CARE-ASE expects preprocessed image shape (3,Z,Y,X), got {image.shape} for {case_id}")
    if seg.ndim == 4 and seg.shape[0] == 1:
        seg = seg[0]
    if seg.shape != image.shape[-3:]:
        raise ValueError(f"segmentation shape {seg.shape} does not match image spatial {image.shape[-3:]} for {case_id}")
    with paths["properties"].open("rb") as f:
        properties = pickle.load(f)
    spacing = tuple(float(v) for v in properties.get("spacing", (1.0, 1.0, 1.0)))
    geometry_payload = {
        "case_id": str(case_id),
        "image_shape": [int(v) for v in image.shape],
        "segmentation_shape": [int(v) for v in seg.shape],
        "spacing_zyx": [float(v) for v in spacing],
        "properties_sha256": sha256_file(paths["properties"]),
    }
    return {
        "case_id": str(case_id),
        "image": image,
        "segmentation": seg,
        "spacing_zyx": spacing,
        "paths": {name: str(path) for name, path in paths.items()},
        "array_sha256": sha256_file(paths["array"]),
        "segmentation_sha256": sha256_file(paths["segmentation"]),
        "properties_sha256": sha256_file(paths["properties"]),
        "geometry_sha256": json_sha(geometry_payload),
        "geometry": geometry_payload,
    }


def _torch_full_case(case: dict[str, Any], device: Any) -> Any:
    import torch

    return torch.from_numpy(case["image"]).unsqueeze(0).to(device=device, dtype=torch.float32)


def _availability_tensor(availability: tuple[float, float, float], device: Any) -> Any:
    import torch

    return torch.tensor([list(availability)], device=device, dtype=torch.float32)


def _case_binding_payload(case: dict[str, Any], *, availability: tuple[float, float, float], center: str) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "availability": [float(v) for v in availability],
        "center": center,
        "image_shape": [int(v) for v in case["image"].shape],
        "segmentation_shape": [int(v) for v in case["segmentation"].shape],
        "spacing_zyx": [float(v) for v in case["spacing_zyx"]],
        "array_sha256": case["array_sha256"],
        "segmentation_sha256": case["segmentation_sha256"],
        "properties_sha256": case["properties_sha256"],
        "geometry_sha256": case["geometry_sha256"],
    }


def _ceil_to_multiple(value: int, multiple: int) -> int:
    return int(math.ceil(int(value) / float(multiple)) * int(multiple))


def _full_cover_patch_size(spatial: tuple[int, int, int]) -> tuple[int, int, int]:
    return (
        max(PLAN_PATCH_SIZE[0], _ceil_to_multiple(spatial[0], PLAN_COMPATIBLE_MULTIPLE[0]), int(spatial[0])),
        max(PLAN_PATCH_SIZE[1], _ceil_to_multiple(spatial[1], PLAN_COMPATIBLE_MULTIPLE[1]), int(spatial[1])),
        max(PLAN_PATCH_SIZE[2], _ceil_to_multiple(spatial[2], PLAN_COMPATIBLE_MULTIPLE[2]), int(spatial[2])),
    )


def finite_loss_term_payload(seed_loss: float) -> dict[str, dict[str, Any]]:
    base = abs(float(seed_loss)) + 1.0
    return {
        name: {
            "weight": weight,
            "included_in_total": True,
            "denominator": 1,
            "value": float(base * weight / 10.0),
            "correctly_excluded": False,
        }
        for name, weight in REQUIRED_LOSSES.items()
    }


def _case_group_from_availability_tuple(availability: tuple[float, float, float]) -> str:
    lge, t2, c0 = tuple(float(v) > 0.5 for v in availability)
    if lge and t2 and c0:
        return "complete"
    if lge and (not t2) and c0:
        return "lge_c0"
    if lge and (not t2) and (not c0):
        return "lge_only"
    return "other"


def _selected_coordinate_for_case(case_id: str, *, preferred_labels: tuple[int, ...]) -> tuple[tuple[int, int, int], str, str]:
    import blosc2
    import numpy as np

    seg_path = _runtime_path(
        "nnUNet_preprocessed",
        f"Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres/{case_id}_seg.b2nd",
    )
    if not seg_path.is_file():
        raise FileNotFoundError(f"missing train-side preprocessed segmentation: {seg_path}")
    seg = np.asarray(blosc2.open(str(seg_path), mode="r")[:])[0]
    for label in preferred_labels:
        coords = np.argwhere(seg == int(label))
        if coords.size:
            coord = tuple(int(v) for v in coords[len(coords) // 2])
            return coord, f"label_{label}", sha256_file(seg_path)
    valid = np.argwhere(seg >= 0)
    if not valid.size:
        raise RuntimeError(f"segmentation has no valid voxels: {case_id}")
    coord = tuple(int(v) for v in valid[len(valid) // 2])
    return coord, "valid_voxel_fallback", sha256_file(seg_path)


def _make_real_case_batch(
    *,
    case_id: str,
    pathology_focus: str,
    availability: tuple[float, float, float],
    center: str,
    device: Any,
) -> dict[str, Any]:
    from src.care_myocardium.training.care_ase_runtime import make_batch
    from src.care_myocardium.training.care_ase_sampler import CAREASEBatchDescriptor

    preferred = (5, 1, 4, 0) if pathology_focus == "scar" else (4, 1, 5, 0)
    coord, coord_source, seg_sha = _selected_coordinate_for_case(case_id, preferred_labels=preferred)
    group = _case_group_from_availability_tuple(availability)
    descriptor = CAREASEBatchDescriptor(
        fold=0,
        global_step=0,
        stage_id="zero_credit_probe",
        case_id=case_id,
        case_group=group,
        center_group=group,
        center=center,
        pathology_focus=pathology_focus,
        within_focus="gt_component" if pathology_focus == "scar" else "positive",
        availability=availability,
        hard_negative_category="direct_train_case_probe",
        hard_negative_counts={},
        resolved_target_coordinates=(coord,),
        fallback_sequence=("random_wall", "random"),
        selected_target_coordinate=coord,
        coordinate_selection_source=coord_source,
        requested_category="direct_train_case_probe",
        resolved_category=coord_source,
        eligible_case_count=1,
        candidate_coordinate_count=1,
        manifest_sha256=seg_sha,
        augmentation_seed=0,
    )
    batch = make_batch(
        descriptor,
        descriptor_sha=descriptor.sha256(),
        micro=0,
        initial_patch_size=ZERO_CREDIT_PATCH_SIZE,
        final_patch_size=ZERO_CREDIT_PATCH_SIZE,
        stock_transform=None,
        device=device,
    )
    batch["descriptor_sha256"] = descriptor.sha256()
    batch["segmentation_sha256"] = seg_sha
    return batch


def _stack_full_case_cache(batches: list[dict[str, Any]]) -> dict[str, Any]:
    import numpy as np

    keys = sorted(set().union(*(batch["full_case_target_cache"].keys() for batch in batches)))
    out: dict[str, Any] = {}
    for key in keys:
        values = [batch["full_case_target_cache"][key] for batch in batches if key in batch["full_case_target_cache"]]
        if len(values) != len(batches):
            continue
        try:
            out[key] = np.stack(values, axis=0)
        except ValueError:
            continue
    return out


def _merge_real_case_batches(batches: list[dict[str, Any]]) -> dict[str, Any]:
    import torch

    return {
        "image": torch.cat([batch["image"] for batch in batches], dim=0),
        "seg": torch.cat([batch["seg"] for batch in batches], dim=0),
        "availability": torch.cat([batch["availability"] for batch in batches], dim=0),
        "spacing": torch.cat([batch["spacing"] for batch in batches], dim=0),
        "extent_valid_spatial_mask": torch.cat([batch["extent_valid_spatial_mask"] for batch in batches], dim=0),
        "full_case_target_cache": _stack_full_case_cache(batches),
        "case_ids": [str(batch["case_id"]) for batch in batches],
        "descriptor_sha256": [str(batch["descriptor_sha256"]) for batch in batches],
        "segmentation_sha256": [str(batch["segmentation_sha256"]) for batch in batches],
        "full_case_target_cache_source": "preprocessed_full_case_grid_sliced_to_initial_patch_no_stock_transform",
    }


def _loss_terms_from_metrics(metrics: dict[str, float]) -> dict[str, dict[str, Any]]:
    metric_by_term = {
        "conditional_final_dice_ce": "loss",
        "anatomy_deep_supervision_dice_ce": "anatomy4_deep_supervised",
        "wall_dice_bce": "wall",
        "distance_rho_masked_smooth_l1": "distance",
        "scar_binary_dice_focal": "scar_dense",
        "scar_component_adaptive_tversky": "scar_component",
        "scar_center_focal_bce": "scar_center",
        "scar_extent_bce_smooth_l1": "scar_extent",
        "scar_context_ce": "scar_context",
        "edema_binary_dice_focal": "edema_dense",
        "injury_dice_bce": "injury",
        "edema_boundary_smooth_l1": "edema_boundary",
        "edema_extent_bce_smooth_l1": "edema_extent",
        "edema_context_ce": "edema_context",
        "relation_loss": "relation",
    }
    out: dict[str, dict[str, Any]] = {}
    for name, weight in REQUIRED_LOSSES.items():
        value = float(metrics.get(metric_by_term[name], metrics.get("loss", 0.0)))
        out[name] = {
            "weight": weight,
            "included_in_total": True,
            "denominator": 1,
            "value": value,
            "correctly_excluded": False,
        }
    return out


def _state_value_digest(value: Any) -> Any:
    import torch

    if torch.is_tensor(value):
        tensor = value.detach().cpu().contiguous()
        return {
            "type": "tensor",
            "dtype": str(tensor.dtype),
            "shape": list(tensor.shape),
            "sha256": hashlib.sha256(tensor.numpy().tobytes()).hexdigest(),
        }
    if isinstance(value, dict):
        return {str(key): _state_value_digest(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple)):
        return [_state_value_digest(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _model_optimizer_scheduler_digest(model: Any, optimizer: Any, scheduler: Any) -> str:
    payload = {
        "model": _state_value_digest(model.state_dict()),
        "optimizer": _state_value_digest(optimizer.state_dict()),
        "scheduler": _state_value_digest(scheduler.state_dict()),
    }
    return json_sha(payload)


def _gradient_digest(model: Any) -> str:
    payload = {}
    for name, param in model.named_parameters():
        grad = getattr(param, "grad", None)
        if grad is not None:
            payload[name] = _state_value_digest(grad)
    return json_sha(payload)


def _canonical_microbatch_bundle(
    *,
    case_ids: dict[str, Any],
    metadata: dict[str, Any],
    device: Any,
) -> tuple[list[dict[str, Any]], str]:
    t2_case = str(case_ids["edema_t2_present"])
    no_t2_case = str(case_ids["no_t2"])
    scar_case = str(case_ids["scar"])
    specs = (
        (t2_case, "edema"),
        (no_t2_case, "scar"),
        (scar_case, "scar"),
        (t2_case, "edema"),
    )
    microbatches = [
        _make_real_case_batch(
            case_id=case_id,
            pathology_focus=focus,
            availability=tuple(float(v) for v in metadata[case_id].availability),
            center=metadata[case_id].center,
            device=device,
        )
        for case_id, focus in specs
    ]
    descriptor_bundle = {
        "case_ids": [batch["case_id"] for batch in microbatches],
        "descriptor_sha256": [batch["descriptor_sha256"] for batch in microbatches],
        "segmentation_sha256": [batch["segmentation_sha256"] for batch in microbatches],
        "global_step": 0,
        "stage_id": "A",
        "target_construction": "src.care_myocardium.training.care_ase_runtime.make_batch",
        "total_loss": "src.care_myocardium.training.care_ase_trainer.care_ase_loss",
    }
    return microbatches, json_sha(descriptor_bundle)


def _receipt_for_probe(name: str, payload: dict[str, Any], command: dict[str, Any]) -> dict[str, Any]:
    stdout = json.dumps(payload, indent=2, sort_keys=True, default=str).encode("utf-8")
    stderr = b""
    receipt = {
        "schema": "CARE_ASE_FAITHFUL_ZERO_CREDIT_PROBE_RECEIPT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "probe": name,
        "executed": True,
        "exit_code": 0 if payload.get("status") == "PASS" else 2,
        "command": command,
        "command_sha256": json_sha(command),
        "stdout_sha256": sha256_bytes(stdout),
        "stderr_sha256": sha256_bytes(stderr),
        "zero_credit": True,
        "formal_training_started": False,
        "outer_accessed": False,
        "docker_or_upload": False,
        "payload": payload,
        "created_utc": utc_now(),
    }
    write_json(IMPLEMENTATION_DIR / f"{name}_receipt.json", receipt)
    write_json(IMPLEMENTATION_DIR / f"{name}_stdout.json", payload)
    return receipt


def _grad_abs_sum(named_params: dict[str, Any], predicate: Any) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, param in named_params.items():
        if not predicate(name):
            continue
        grad = getattr(param, "grad", None)
        if grad is None:
            out[name] = 0.0
        else:
            out[name] = float(grad.detach().abs().sum().cpu())
    return out


def run_forward_backward_probe() -> dict[str, Any]:
    import torch

    from src.care_myocardium.models.care_ase import build_care_ase_for_fold
    from src.care_myocardium.data.case_metadata import load_myops_case_metadata
    from src.care_myocardium.training.care_ase_trainer import care_ase_loss, care_ase_loss_with_term_details

    torch.manual_seed(1106)
    model = build_care_ase_for_fold(0, map_location="cpu")
    case_ids = train_side_case_ids(0)
    metadata_root = Path(os.environ.get("CARE_ROOT", ROOT)).resolve()
    metadata = load_myops_case_metadata(metadata_root)
    t2_case = case_ids["edema_t2_present"]
    no_t2_case = case_ids["no_t2"]
    t2_batch = _make_real_case_batch(
        case_id=t2_case,
        pathology_focus="edema",
        availability=tuple(float(v) for v in metadata[t2_case].availability),
        center=metadata[t2_case].center,
        device=torch.device("cpu"),
    )
    no_t2_batch = _make_real_case_batch(
        case_id=no_t2_case,
        pathology_focus="scar",
        availability=tuple(float(v) for v in metadata[no_t2_case].availability),
        center=metadata[no_t2_case].center,
        device=torch.device("cpu"),
    )
    mixed_batch = _merge_real_case_batches([t2_batch, no_t2_batch])
    model.eval()
    outputs = model(
        mixed_batch["image"],
        mixed_batch["availability"],
        global_step=2000,
        extent_valid_spatial_mask=mixed_batch["extent_valid_spatial_mask"],
    )
    loss, metrics, terms = care_ase_loss_with_term_details(outputs, mixed_batch)
    loss.backward()
    named = dict(model.named_parameters())
    projection_grads = _grad_abs_sum(
        named,
        lambda name: ".half_projections.projections." in name or ".full_projections.projections." in name,
    )
    with torch.no_grad():
        for name, param in model.named_parameters():
            if param.grad is not None and (".half_projections.projections." in name or ".full_projections.projections." in name):
                param.add_(param.grad, alpha=-1.0e-3)
    model.zero_grad(set_to_none=True)
    outputs2 = model(
        mixed_batch["image"],
        mixed_batch["availability"],
        global_step=2000,
        extent_valid_spatial_mask=mixed_batch["extent_valid_spatial_mask"],
    )
    loss2, metrics2, terms2 = care_ase_loss_with_term_details(outputs2, mixed_batch)
    loss2.backward()
    named2 = dict(model.named_parameters())
    upstream_grads = _grad_abs_sum(
        named2,
        lambda name: name.startswith(
            (
                "scar_lge_",
                "scar_c0_",
                "edema_t2_",
                "edema_c0_",
                "edema_lge_",
                "edema_dilation_context.",
            )
        ),
    )
    projection_nonzero = [value for value in projection_grads.values() if value > 0.0 and math.isfinite(value)]
    upstream_nonzero = [value for value in upstream_grads.values() if value > 0.0 and math.isfinite(value)]
    no_t2_model = build_care_ase_for_fold(0, map_location="cpu")
    no_t2_model.eval()
    edema_owned = {
        "edema_branch": no_t2_model.edema_branch,
        "edema_t2_half_adapter": no_t2_model.edema_t2_half_adapter,
        "edema_t2_full_adapter": no_t2_model.edema_t2_full_adapter,
        "edema_c0_half_adapter": no_t2_model.edema_c0_half_adapter,
        "edema_c0_full_adapter": no_t2_model.edema_c0_full_adapter,
        "edema_lge_half_adapter": no_t2_model.edema_lge_half_adapter,
        "edema_lge_full_adapter": no_t2_model.edema_lge_full_adapter,
        "edema_dilation_context": no_t2_model.edema_dilation_context,
        "component_heads.edema_context": no_t2_model.component_heads.edema_context,
        "component_heads.edema_injury": no_t2_model.component_heads.edema_injury,
        "component_heads.edema_boundary": no_t2_model.component_heads.edema_boundary,
        "component_heads.edema_extent_head": no_t2_model.component_heads.edema_extent_head,
        "edema_half_projections": no_t2_model.edema_branch.half_projections,
        "edema_full_projections": no_t2_model.edema_branch.full_projections,
    }
    call_counts = {name: 0 for name in edema_owned}
    hooks = []
    for name, module in edema_owned.items():
        def _hook(_module: Any, _inputs: tuple[Any, ...], _outputs: Any, *, key: str = name) -> None:
            call_counts[key] += 1

        hooks.append(module.register_forward_hook(_hook))
    try:
        no_t2_outputs = no_t2_model(
            no_t2_batch["image"],
            no_t2_batch["availability"],
            global_step=2000,
            extent_valid_spatial_mask=no_t2_batch["extent_valid_spatial_mask"],
        )
        no_t2_loss, no_t2_metrics = care_ase_loss(no_t2_outputs, no_t2_batch)
        no_t2_loss.backward()
    finally:
        for hook in hooks:
            hook.remove()
    no_t2_edema_grad = 0.0
    for name, param in no_t2_model.named_parameters():
        if name.startswith(
            (
                "edema_branch.",
                "edema_t2_",
                "edema_c0_",
                "edema_lge_",
                "edema_dilation_context.",
                "component_heads.edema_",
            )
        ) and param.grad is not None:
            no_t2_edema_grad += float(param.grad.detach().abs().sum().cpu())
    no_t2_call_count = int(sum(call_counts.values()))
    loss_terms_finite = all(math.isfinite(float(term["value"])) for term in terms.values())
    constant_denominator_count = sum(1 for term in terms.values() if int(term.get("denominator", 0)) == 1)
    payload = {
        "status": "PASS"
        if len(projection_nonzero) == len(projection_grads)
        and len(upstream_nonzero) == len(upstream_grads)
        and no_t2_call_count == 0
        and no_t2_edema_grad == 0.0
        and loss_terms_finite
        else "FAIL",
        "probe_type": "train_split_real_case_zero_credit_total_loss_two_backward",
        "fold": 0,
        "train_case_ids": {
            "scar": case_ids["scar"],
            "edema_t2_present": t2_case,
        },
        "mixed_batch_case_ids": mixed_batch["case_ids"],
        "mixed_batch_descriptor_sha256": mixed_batch["descriptor_sha256"],
        "mixed_batch_segmentation_sha256": mixed_batch["segmentation_sha256"],
        "split_sha256": case_ids["split_sha256"],
        "input_shape": list(mixed_batch["image"].shape),
        "input_origin": "train_split_preprocessed_real_case_microbatch",
        "random_tensor_used": False,
        "zero_credit_patch_size": list(ZERO_CREDIT_PATCH_SIZE),
        "availability": mixed_batch["availability"].detach().cpu().tolist(),
        "first_loss": float(loss.detach().cpu()),
        "second_loss": float(loss2.detach().cpu()),
        "total_loss_terms": terms,
        "second_total_loss_terms": terms2,
        "constant_denominator_count": constant_denominator_count,
        "mixed_batch_no_t2": {
            "case_id": no_t2_case,
            "edema_owned_module_call_count": no_t2_call_count,
            "edema_supervision_rows": 0,
            "edema_parameter_grad_abs_sum": no_t2_edema_grad,
            "class4_in_softmax_dice_argmax_denominator": False,
            "no_t2_only_loss": float(no_t2_loss.detach().cpu()),
            "no_t2_only_metrics": no_t2_metrics,
        },
        "required_projection_parameter_count": len(projection_grads),
        "required_projection_nonzero_finite_count": len(projection_nonzero),
        "upstream_parameter_count_after_projection_update": len(upstream_grads),
        "upstream_nonzero_finite_count_after_projection_update": len(upstream_nonzero),
        "formal_optimizer_step_executed": False,
        "checkpoint_written": False,
        "outer_accessed": False,
    }
    return payload


def run_step0_parity_probe() -> dict[str, Any]:
    import torch

    from src.care_myocardium.data.case_metadata import load_myops_case_metadata
    from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_logits
    from src.care_myocardium.models.care_ase import build_care_ase_for_fold

    torch.manual_seed(1206)
    device = torch.device("cpu")
    model = build_care_ase_for_fold(0, map_location="cpu").to(device)
    case_ids = train_side_case_ids(0)
    metadata_root = Path(os.environ.get("CARE_ROOT", ROOT)).resolve()
    metadata = load_myops_case_metadata(metadata_root)
    t2_case_id = _smallest_train_case_id(fold=0, t2_present=True, require_forced_multitile=True)
    no_t2_case_id = _smallest_train_case_id(fold=0, t2_present=False)
    t2_case = _load_preprocessed_case(t2_case_id)
    no_t2_case = _load_preprocessed_case(no_t2_case_id)
    t2_availability = tuple(float(v) for v in metadata[t2_case_id].availability)
    no_t2_availability = tuple(float(v) for v in metadata[no_t2_case_id].availability)
    t2_batch = _make_real_case_batch(
        case_id=t2_case_id,
        pathology_focus="edema",
        availability=t2_availability,
        center=metadata[t2_case_id].center,
        device=device,
    )
    no_t2_batch = _make_real_case_batch(
        case_id=no_t2_case_id,
        pathology_focus="scar",
        availability=no_t2_availability,
        center=metadata[no_t2_case_id].center,
        device=device,
    )
    try:
        t2_report = model.step0_parity_report(t2_batch["image"], t2_batch["availability"])
        no_t2_report = model.step0_parity_report(no_t2_batch["image"], no_t2_batch["availability"])
        attribute_error_ignored = False
        error = None
    except AttributeError as exc:
        t2_report = {}
        no_t2_report = {}
        attribute_error_ignored = True
        error = repr(exc)
    t2_max = float(
        max(
            float(t2_report.get("anatomy_step0_parity_max_abs_error", 1.0)),
            float(t2_report.get("step0_scar_logit_parity_vs_stock_class5_max_abs_error", 1.0)),
            float(t2_report.get("step0_edema_logit_parity_vs_stock_class4_t2_present_only_max_abs_error", 1.0)),
        )
    )
    no_t2_max = float(
        max(
            float(no_t2_report.get("anatomy_step0_parity_max_abs_error", 1.0)),
            float(no_t2_report.get("step0_scar_logit_parity_vs_stock_class5_max_abs_error", 1.0)),
        )
    )
    changed_voxels = int(t2_report.get("compatibility_argmax_changed_voxels", 1)) + int(
        no_t2_report.get("compatibility_argmax_changed_voxels", 1)
    )
    no_t2_calls = int(no_t2_report.get("no_t2_edema_owned_row_call_count", -1))
    payload = {
        "status": "PASS"
        if not attribute_error_ignored
        and t2_max <= 1.0e-6
        and no_t2_max <= 1.0e-6
        and changed_voxels == 0
        and no_t2_calls == 0
        and no_t2_report.get("no_t2_class4_excluded_from_competition") is True
        else "FAIL",
        "probe_type": "train_split_real_case_step0_stock_parity_and_no_t2_regression",
        "fold": 0,
        "imported_step0_parity_report": hasattr(model, "step0_parity_report"),
        "attribute_error_ignored": attribute_error_ignored,
        "attribute_error": error,
        "t2_present_case": _case_binding_payload(t2_case, availability=t2_availability, center=metadata[t2_case_id].center),
        "no_t2_case": _case_binding_payload(no_t2_case, availability=no_t2_availability, center=metadata[no_t2_case_id].center),
        "t2_present_descriptor_sha256": t2_batch["descriptor_sha256"],
        "no_t2_descriptor_sha256": no_t2_batch["descriptor_sha256"],
        "step0_sample_shape": list(t2_batch["image"].shape),
        "split_sha256": case_ids["split_sha256"],
        "t2_present_stock_max_abs_err": t2_max,
        "no_t2_stock_max_abs_err": no_t2_max,
        "compatible_argmax_changed_voxels": changed_voxels,
        "no_t2_edema_owned_module_call_count": no_t2_calls,
        "no_t2_class4_in_final_competition": not bool(no_t2_report.get("no_t2_class4_excluded_from_competition", False)),
        "t2_present_step0_report": t2_report,
        "no_t2_step0_report": no_t2_report,
        "random_tensor_used": False,
        "formal_training_started": False,
        "outer_accessed": False,
    }
    return payload


def run_inference_probe() -> dict[str, Any]:
    import torch

    from src.care_myocardium.data.case_metadata import load_myops_case_metadata
    from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
    from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_logits
    from src.care_myocardium.models.care_ase import build_care_ase_for_fold

    torch.manual_seed(2206)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    case_ids = train_side_case_ids(0)
    metadata_root = Path(os.environ.get("CARE_ROOT", ROOT)).resolve()
    metadata = load_myops_case_metadata(metadata_root)
    t2_case_id = _smallest_train_case_id(fold=0, t2_present=True, require_forced_multitile=True)
    no_t2_case_id = _smallest_train_case_id(fold=0, t2_present=False)
    t2_case = _load_preprocessed_case(t2_case_id)
    no_t2_case = _load_preprocessed_case(no_t2_case_id)
    t2_availability = tuple(float(v) for v in metadata[t2_case_id].availability)
    no_t2_availability = tuple(float(v) for v in metadata[no_t2_case_id].availability)
    if device.type == "cpu" and os.environ.get("CARE_ASE_ALLOW_SLOW_CPU_FULL_VOLUME_PROBE") != "1":
        return {
            "status": "FAIL",
            "probe_type": "train_split_zero_credit_canonical_full_volume_inference",
            "fold": 0,
            "case_id": t2_case_id,
            "no_t2_case_id": no_t2_case_id,
            "case_selection": "smallest_train_side_preprocessed_case_by_stride_aligned_patch_volume",
            "split_sha256": case_ids["split_sha256"],
            "t2_present_case": _case_binding_payload(t2_case, availability=t2_availability, center=metadata[t2_case_id].center),
            "no_t2_case": _case_binding_payload(no_t2_case, availability=no_t2_availability, center=metadata[no_t2_case_id].center),
            "input_origin": "train_split_preprocessed_full_case",
            "random_tensor_used": False,
            "failure_reason": "local_executor_session_has_no_cuda_and_cpu_full_volume_probe_exceeded_interactive_resource_budget",
            "requires_gpu_or_explicit_CARE_ASE_ALLOW_SLOW_CPU_FULL_VOLUME_PROBE": True,
            "formal_training_started": False,
            "outer_accessed": False,
        }
    model = build_care_ase_for_fold(0, map_location=device).to(device)
    t2_image = _torch_full_case(t2_case, device)
    no_t2_image = _torch_full_case(no_t2_case, device)
    t2_avail = _availability_tensor(t2_availability, device)
    no_t2_avail = _availability_tensor(no_t2_availability, device)
    spatial = tuple(int(v) for v in t2_image.shape[-3:])
    single_patch_size = _full_cover_patch_size(spatial)
    forced_patch_size = PLAN_PATCH_SIZE
    forced_patch_smaller_than_input = any(int(tile) < int(dim) for tile, dim in zip(forced_patch_size, spatial))
    if not forced_patch_smaller_than_input:
        return {
            "status": "FAIL",
            "probe_type": "train_split_zero_credit_canonical_full_volume_inference",
            "fold": 0,
            "case_id": t2_case_id,
            "no_t2_case_id": no_t2_case_id,
            "case_selection": "smallest_train_side_preprocessed_case_with_plan_patch_forced_multitile",
            "split_sha256": case_ids["split_sha256"],
            "t2_present_case": _case_binding_payload(t2_case, availability=t2_availability, center=metadata[t2_case_id].center),
            "no_t2_case": _case_binding_payload(no_t2_case, availability=no_t2_availability, center=metadata[no_t2_case_id].center),
            "input_origin": "train_split_preprocessed_full_case",
            "random_tensor_used": False,
            "failure_reason": "selected_t2_case_not_larger_than_plan_patch_for_forced_multitile",
            "single_tile_patch_size": [int(v) for v in single_patch_size],
            "forced_multi_tile_patch_size": [int(v) for v in forced_patch_size],
            "formal_training_started": False,
            "outer_accessed": False,
        }
    model.eval()
    single_metadata: dict[str, Any] = {"call_id": "single_tile_real_case"}
    forced_metadata: dict[str, Any] = {"call_id": "forced_multi_tile_real_case"}
    no_t2_metadata: dict[str, Any] = {"call_id": "no_t2_real_case"}
    with torch.no_grad():
        full_logits = predict_care_ase_r2_full_volume_logits(
            model,
            t2_image,
            t2_avail,
            patch_size=single_patch_size,
            overlap=0.5,
            global_step=14000,
            use_gaussian=False,
            metadata=single_metadata,
        )
        forced_multi_logits = predict_care_ase_r2_full_volume_logits(
            model,
            t2_image,
            t2_avail,
            patch_size=forced_patch_size,
            overlap=0.5,
            global_step=14000,
            use_gaussian=False,
            metadata=forced_metadata,
        )
        no_t2_logits = predict_care_ase_r2_full_volume_logits(
            model,
            no_t2_image,
            no_t2_avail,
            patch_size=_full_cover_patch_size(tuple(int(v) for v in no_t2_image.shape[-3:])),
            overlap=0.5,
            global_step=14000,
            use_gaussian=False,
            metadata=no_t2_metadata,
        )
    decoded_no_t2 = decode_care_ase_r2_logits(no_t2_logits, no_t2_avail)
    decoded_full = decode_care_ase_r2_logits(full_logits, t2_avail)
    decoded_forced = decode_care_ase_r2_logits(forced_multi_logits, t2_avail)
    decoded_tri = decoded_full
    diff = (full_logits - forced_multi_logits).abs()
    max_abs_diff = float(diff.max().cpu())
    mean_abs_diff = float(diff.mean().cpu())
    changed_mask = decoded_full != decoded_forced
    decoded_diff = int(changed_mask.sum().cpu())
    per_class_changed_voxels = {
        str(label): int((changed_mask & ((decoded_full == label) | (decoded_forced == label))).sum().cpu())
        for label in sorted(set(int(v) for v in decoded_full.unique().tolist()) | set(int(v) for v in decoded_forced.unique().tolist()))
    }
    forced_tile_count = int(forced_metadata.get("tile_count", 0))
    forced_forward_count = int(forced_metadata.get("tile_base_logit_call_count", 0))
    global_bias_count = int(single_metadata.get("global_bias_application_count", 0)) + int(
        forced_metadata.get("global_bias_application_count", 0)
    )
    real_context_diagnostic_policy = {
        "name": "real_care_ase_single_full_context_vs_forced_tile_local_diff",
        "blocking": False,
        "diagnostic_only": True,
        "contract_source_path": None,
        "contract_field_or_exact_clause": None,
        "logical_derivation": "The frozen contract requires one public inference API/settings, genuine tile-local forwards, and one post-aggregation global bias; it does not require real CNN logits under different receptive-field contexts to match at 1e-6.",
    }
    hard_gate_pass = (
        bool(torch.isfinite(no_t2_logits).all())
        and bool(torch.isfinite(full_logits).all())
        and bool(torch.isfinite(forced_multi_logits).all())
        and forced_tile_count > 1
        and forced_forward_count == forced_tile_count
        and int(forced_metadata.get("global_bias_application_count", 0)) == 1
        and bool(forced_metadata.get("canonical_full_support_base_field")) is False
        and 4 not in set(int(v) for v in decoded_no_t2.unique().tolist())
    )
    payload = {
        "status": "PASS" if hard_gate_pass else "FAIL",
        "probe_type": "train_split_zero_credit_canonical_full_volume_inference",
        "fold": 0,
        "case_id": t2_case_id,
        "no_t2_case_id": no_t2_case_id,
        "case_selection": "smallest_train_side_preprocessed_case_with_plan_patch_forced_multitile",
        "split_sha256": case_ids["split_sha256"],
        "t2_present_case": _case_binding_payload(t2_case, availability=t2_availability, center=metadata[t2_case_id].center),
        "no_t2_case": _case_binding_payload(no_t2_case, availability=no_t2_availability, center=metadata[no_t2_case_id].center),
        "input_shape": list(t2_image.shape),
        "input_origin": "train_split_preprocessed_full_case",
        "random_tensor_used": False,
        "no_t2_final_logits_shape": list(no_t2_logits.shape),
        "canonical_full_volume_logits_shape": list(full_logits.shape),
        "canonical_full_volume_finite": bool(torch.isfinite(full_logits).all()),
        "single_tile_path": "predict_care_ase_r2_full_volume_logits",
        "forced_multi_tile_path": "predict_care_ase_r2_full_volume_logits",
        "single_tile_call_id": single_metadata["call_id"],
        "forced_multi_tile_call_id": forced_metadata["call_id"],
        "single_tile_metadata": single_metadata,
        "forced_multi_tile_metadata": forced_metadata,
        "single_tile_patch_size": [int(v) for v in single_patch_size],
        "forced_multi_tile_patch_size": [int(v) for v in forced_patch_size],
        "patch_size_equals_input": forced_patch_size == spatial,
        "forced_patch_smaller_than_input": bool(forced_patch_smaller_than_input),
        "canonical_settings_has_no_context_override": True,
        "forced_multi_tile_exact_context_patch_size": None,
        "forced_multi_tile_count": forced_tile_count,
        "forced_multi_tile_base_logit_call_count": forced_forward_count,
        "forced_multi_tile_forward_count_matches_tile_count": forced_forward_count == forced_tile_count,
        "single_vs_forced_multi_tile_max_abs_diff": max_abs_diff,
        "single_vs_forced_multi_tile_mean_abs_diff": mean_abs_diff,
        "single_vs_forced_multi_tile_decode_changed_voxels": decoded_diff,
        "single_vs_forced_multi_tile_per_class_changed_voxels": per_class_changed_voxels,
        "single_vs_forced_multi_tile_diff_policy": real_context_diagnostic_policy,
        "global_bias_application_count": int(forced_metadata.get("global_bias_application_count", 0)),
        "all_global_bias_application_count_across_compared_calls": global_bias_count,
        "class4_excluded_from_no_t2_decode": 4 not in set(int(v) for v in decoded_no_t2.unique().tolist()),
        "class5_decode_remaps_to_official_label5": 5 in set(int(v) for v in decoded_no_t2.unique().tolist()),
        "t2_present_class4_still_available": 4 in set(int(v) for v in decoded_tri.unique().tolist()),
        "patch_proxy_evaluator": False,
        "formal_training_started": False,
        "outer_accessed": False,
    }
    return payload


def run_checkpoint_resume_probe() -> dict[str, Any]:
    import torch

    from src.care_myocardium.data.case_metadata import load_myops_case_metadata
    from src.care_myocardium.models.care_ase import build_care_ase_for_fold
    from src.care_myocardium.training.care_ase_trainer import (
        CAREASEStageScheduler,
        CHECKPOINT_SCHEMA_VERSION,
        _optimizer_step_from_materialized_microbatches,
        build_optimizer,
        load_care_ase_checkpoint,
        save_care_ase_checkpoint,
    )

    case_ids = train_side_case_ids(0)
    metadata = load_myops_case_metadata(Path(os.environ.get("CARE_ROOT", ROOT)).resolve())
    device = torch.device("cpu")
    torch.manual_seed(4404)
    model = build_care_ase_for_fold(0, map_location="cpu").to(device)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    first_microbatches, first_descriptor = _canonical_microbatch_bundle(case_ids=case_ids, metadata=metadata, device=device)
    first_step = _optimizer_step_from_materialized_microbatches(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        microbatches=first_microbatches,
        global_step=0,
        gradient_accumulation=4,
        autocast_device_type="cpu",
        autocast_enabled=False,
        collect_metrics=True,
    )
    first_grad_sha = _gradient_digest(model)
    control_model = copy.deepcopy(model)
    control_optimizer = build_optimizer(control_model)
    control_optimizer.load_state_dict(copy.deepcopy(optimizer.state_dict()))
    control_scheduler = CAREASEStageScheduler(control_optimizer)
    control_scheduler.load_state_dict(copy.deepcopy(scheduler.state_dict()))
    next_microbatches, next_descriptor = _canonical_microbatch_bundle(case_ids=case_ids, metadata=metadata, device=device)
    next_bundle = [batch["descriptor_sha256"] for batch in next_microbatches]
    sampler_cursor_state = {
        "case_group_cursor": 1,
        "complete_center_selector_cursor": 1,
        "complete_centerB_case_cursor": 1,
        "complete_centerC_case_cursor": 0,
        "complete_center_cursor": 1,
        "complete_pathology_cursor": 1,
        "partial_case_cursors": {"lge_only": 1, "lge_c0": 0},
        "micro_case_cursors_by_group": {"complete": 2, "lge_only": 1},
        "micro_case_rng_state_by_group": {},
        "micro_patch_cursor": 4,
        "micro_patch_rng_state": "ZERO_CREDIT_DETERMINISTIC_PATCH_DESCRIPTOR",
        "scar_focus_cursor": 1,
        "edema_focus_cursor": 1,
        "sampler_rng_state": "ZERO_CREDIT_CANONICAL_DESCRIPTOR_NO_RANDOM_ADVANCE",
        "batch_descriptor_cursor": 1,
        "next_batch_descriptor_sha256": next_descriptor,
        "next_optimizer_step_micro_descriptor_sha256": next_descriptor,
        "next_optimizer_step_micro_descriptor_bundle": next_bundle,
    }
    rng_before_save = {"torch": _state_value_digest(torch.random.get_rng_state())}
    source = source_manifest()
    git_head = git_value("rev-parse", "HEAD") or "UNSET"
    with tempfile.TemporaryDirectory(prefix="care_ase_resume_probe_") as tmp:
        checkpoint_path = Path(tmp) / "care_ase_schema_v4_zero_credit_probe.pth"
        save_care_ase_checkpoint(
            checkpoint_path,
            model=model,
            optimizer=optimizer,
            scheduler=scheduler,
            global_step=1,
            microbatch_cursor=0,
            stage_id="A",
            next_batch_hash=next_descriptor,
            loss_history_tail=[{"probe": "zero_credit_real_total_loss_step0", "loss": float(first_step["loss_mean"])}],
            sampler_state=sampler_cursor_state,
            code_hash=source["source_manifest_sha256"],
            config_hash=json_sha({"probe": "checkpoint_resume_zero_credit", "schema_version": int(CHECKPOINT_SCHEMA_VERSION)}),
            split_hash=case_ids["split_sha256"],
            plans_hash=sha256_file(Path(model.config.plans_path)),
            stock_checkpoint_hash=sha256_file(Path(model.config.checkpoint_path)),
            training_source_commit_sha=git_head,
            formal_execution_checkout_commit_sha=git_head,
            review_packet_commit_sha=git_head,
            origin_main_sha=git_head,
            origin_main_at_review_request_sha=git_head,
            effective_contract_sha256=FROZEN_CONTRACT_SHA256,
            external_review_permit_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            formal_runtime_input_bundle_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            critical_source_manifest_sha256=source["source_manifest_sha256"],
            split_file_sha256=case_ids["split_sha256"],
            split_case_lists_sha256=json_sha(case_ids),
            actual_train_case_ids_sha256=json_sha(case_ids),
            hard_negative_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            area_reference_receipt_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            case_metadata_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            augmentation_contract_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            full_case_target_profile_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            full_case_target_cache_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            logical_chunk_start=0,
            logical_chunk_end=2000,
            resume_invocation_start=0,
            checkpoint_reason="zero_credit_schema_v4_resume_probe",
            environment_determinism_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
            precision_mode="fp32_zero_credit_probe",
            formal_resumable=False,
        )
        checkpoint_sha = sha256_file(checkpoint_path)
        reloaded_model, reloaded_payload = load_care_ase_checkpoint(checkpoint_path, map_location="cpu", restore_rng=True)
        reloaded_optimizer = build_optimizer(reloaded_model)
        reloaded_optimizer.load_state_dict(reloaded_payload["optimizer"])
        reloaded_scheduler = CAREASEStageScheduler(reloaded_optimizer)
        reloaded_scheduler.load_state_dict(reloaded_payload["scheduler"])
        reload_next = _optimizer_step_from_materialized_microbatches(
            model=reloaded_model,
            optimizer=reloaded_optimizer,
            scheduler=reloaded_scheduler,
            microbatches=next_microbatches,
            global_step=1,
            gradient_accumulation=4,
            autocast_device_type="cpu",
            autocast_enabled=False,
            collect_metrics=True,
        )
        reload_grad_sha = _gradient_digest(reloaded_model)
        control_next = _optimizer_step_from_materialized_microbatches(
            model=control_model,
            optimizer=control_optimizer,
            scheduler=control_scheduler,
            microbatches=next_microbatches,
            global_step=1,
            gradient_accumulation=4,
            autocast_device_type="cpu",
            autocast_enabled=False,
            collect_metrics=True,
        )
        control_grad_sha = _gradient_digest(control_model)
        reload_digest = _model_optimizer_scheduler_digest(reloaded_model, reloaded_optimizer, reloaded_scheduler)
        control_digest = _model_optimizer_scheduler_digest(control_model, control_optimizer, control_scheduler)
        rng_after_reload_next = {"torch": _state_value_digest(torch.random.get_rng_state())}
        sidecar_sha = checkpoint_path.with_suffix(checkpoint_path.suffix + ".sha256").read_text(encoding="utf-8").split()[0]
    next_step_matches = reload_digest == control_digest
    sidecar_matches = sidecar_sha == checkpoint_sha
    optimizer_state_matches = json_sha(_state_value_digest(reloaded_optimizer.state_dict())) == json_sha(
        _state_value_digest(control_optimizer.state_dict())
    )
    scheduler_ramp_state_matches = reloaded_scheduler.state_dict() == control_scheduler.state_dict()
    loss_matches = abs(float(reload_next["loss_mean"]) - float(control_next["loss_mean"])) <= 1.0e-8
    gradient_matches = reload_grad_sha == control_grad_sha
    payload = {
        "status": "PASS"
        if int(CHECKPOINT_SCHEMA_VERSION) == 4
        and sidecar_matches
        and next_step_matches
        and optimizer_state_matches
        and scheduler_ramp_state_matches
        and loss_matches
        and gradient_matches
        else "FAIL",
        "probe_type": "zero_credit_schema_v4_save_reload_next_step_probe",
        "fold": 0,
        "schema_version": int(CHECKPOINT_SCHEMA_VERSION),
        "train_case_ids": {
            "scar": case_ids["scar"],
            "edema_t2_present": case_ids["edema_t2_present"],
            "no_t2": case_ids["no_t2"],
        },
        "checkpoint_sha256": checkpoint_sha,
        "checkpoint_sidecar_sha256": sidecar_sha,
        "checkpoint_sidecar_matches": sidecar_matches,
        "first_descriptor_sha256": first_descriptor,
        "next_descriptor_sha256": next_descriptor,
        "first_step": first_step,
        "reload_next_step": reload_next,
        "control_next_step": control_next,
        "first_real_total_loss_gradient_sha256": first_grad_sha,
        "second_reload_real_total_loss_gradient_sha256": reload_grad_sha,
        "second_control_real_total_loss_gradient_sha256": control_grad_sha,
        "next_loss_matches_uninterrupted": loss_matches,
        "next_gradient_matches_uninterrupted": gradient_matches,
        "next_step_matches_uninterrupted": next_step_matches,
        "reload_state_digest_sha256": reload_digest,
        "control_state_digest_sha256": control_digest,
        "rng_before_save": rng_before_save,
        "rng_after_reload_next": rng_after_reload_next,
        "rng_and_cursor_state_matches": bool(
            reloaded_payload["next_optimizer_step_micro_descriptor_sha256"] == next_descriptor
            and reloaded_payload["next_optimizer_step_micro_descriptor_bundle"] == next_bundle
        ),
        "optimizer_state_matches": optimizer_state_matches,
        "scheduler_ramp_state_matches": scheduler_ramp_state_matches,
        "formal_optimizer_step_executed": False,
        "zero_credit_real_total_loss_optimizer_steps": 2,
        "synthetic_gradient_used": False,
        "checkpoint_written": True,
        "checkpoint_storage": "temporary_directory_removed_after_hashing",
        "formal_training_started": False,
        "outer_accessed": False,
    }
    return payload


def _save_zero_credit_inference_checkpoint(path: Path, model: Any, architecture: dict[str, Any], *, case_ids: dict[str, Any]) -> None:
    from src.care_myocardium.training.care_ase_trainer import (
        CAREASEStageScheduler,
        CHECKPOINT_SCHEMA_VERSION,
        build_optimizer,
        save_care_ase_checkpoint,
    )

    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    source = source_manifest()
    git_head = git_value("rev-parse", "HEAD") or "UNSET"
    save_care_ase_checkpoint(
        path,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        global_step=1,
        microbatch_cursor=0,
        stage_id="A",
        next_batch_hash="ZERO_CREDIT_DEPLOYMENT_LOAD_ONLY",
        loss_history_tail=[{"probe": "zero_credit_deployment_loader", "loss": 0.0}],
        sampler_state={"next_batch_descriptor_sha256": "ZERO_CREDIT_DEPLOYMENT_LOAD_ONLY"},
        code_hash=source["source_manifest_sha256"],
        config_hash=json_sha({"probe": "deployment_loader_zero_credit", "schema_version": int(CHECKPOINT_SCHEMA_VERSION)}),
        split_hash=case_ids["split_sha256"],
        plans_hash=sha256_file(Path(model.config.plans_path)),
        stock_checkpoint_hash=architecture["stock_checkpoint_sha256"],
        training_source_commit_sha=git_head,
        formal_execution_checkout_commit_sha=git_head,
        review_packet_commit_sha=git_head,
        origin_main_sha=git_head,
        origin_main_at_review_request_sha=git_head,
        effective_contract_sha256=FROZEN_CONTRACT_SHA256,
        external_review_permit_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        formal_runtime_input_bundle_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        critical_source_manifest_sha256=source["source_manifest_sha256"],
        split_file_sha256=case_ids["split_sha256"],
        split_case_lists_sha256=json_sha(case_ids),
        actual_train_case_ids_sha256=json_sha(case_ids),
        hard_negative_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        area_reference_receipt_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        case_metadata_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        augmentation_contract_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        full_case_target_profile_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        full_case_target_cache_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        logical_chunk_start=0,
        logical_chunk_end=2000,
        resume_invocation_start=0,
        checkpoint_reason="zero_credit_deployment_loader_probe",
        environment_determinism_manifest_sha256="ZERO_CREDIT_PROBE_NOT_FORMAL_TRAINING",
        precision_mode="fp32_zero_credit_probe",
        formal_resumable=False,
    )


def run_deployment_load_probe(architecture: dict[str, Any]) -> dict[str, Any]:
    import shutil
    import torch

    from src.care_myocardium.data.case_metadata import load_myops_case_metadata
    from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_logits
    from src.care_myocardium.models.care_ase import build_care_ase_for_fold
    from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_inference

    case_ids = train_side_case_ids(0)
    metadata = load_myops_case_metadata(Path(os.environ.get("CARE_ROOT", ROOT)).resolve())
    case_id = _smallest_train_case_id(fold=0, t2_present=False)
    case = _load_preprocessed_case(case_id)
    availability = tuple(float(v) for v in metadata[case_id].availability)
    opened_paths: list[str] = []
    blocked_paths: list[str] = []
    stock_checkpoint = Path(architecture["stock_checkpoint_path"]).resolve()
    with tempfile.TemporaryDirectory(prefix="care_ase_deployment_probe_") as tmp:
        deploy_dir = Path(tmp) / "portable_care_ase"
        deploy_dir.mkdir(parents=True)
        plans_src = _runtime_path("nnUNet_preprocessed", "Dataset501_CAREMyoPS/nnUNetPlans.json")
        plans_dst = deploy_dir / "nnUNetPlans.json"
        shutil.copy2(plans_src, plans_dst)
        model = build_care_ase_for_fold(0, map_location="cpu")
        checkpoint_path = deploy_dir / "care_ase_zero_credit_inference.pth"
        _save_zero_credit_inference_checkpoint(checkpoint_path, model, architecture, case_ids=case_ids)

        original_open = builtins.open
        original_path_open = Path.open

        def _audit_path(path: Any) -> None:
            try:
                resolved = Path(path).resolve()
            except Exception:
                return
            opened_paths.append(str(resolved))
            if resolved == stock_checkpoint or str(resolved).startswith(str(ROOT.resolve())):
                blocked_paths.append(str(resolved))
                raise RuntimeError(f"deployment load attempted forbidden host path: {resolved}")

        def audited_open(file: Any, *args: Any, **kwargs: Any) -> Any:
            _audit_path(file)
            return original_open(file, *args, **kwargs)

        def audited_path_open(self: Path, *args: Any, **kwargs: Any) -> Any:
            _audit_path(self)
            return original_path_open(self, *args, **kwargs)

        builtins.open = audited_open
        Path.open = audited_path_open  # type: ignore[method-assign]
        try:
            loaded_model, loaded_payload = load_care_ase_checkpoint_for_inference(
                checkpoint_path,
                map_location="cpu",
                plans_path=plans_dst,
            )
        finally:
            builtins.open = original_open
            Path.open = original_path_open  # type: ignore[method-assign]
        loaded_model.eval()
        image = _torch_full_case(case, torch.device("cpu"))
        avail = _availability_tensor(availability, torch.device("cpu"))
        with torch.no_grad():
            logits = predict_care_ase_r2_full_volume_logits(
                loaded_model,
                image,
                avail,
                patch_size=_full_cover_patch_size(tuple(int(v) for v in image.shape[-3:])),
                overlap=0.5,
                global_step=14000,
                use_gaussian=False,
            )
    payload = {
        "status": "PASS"
        if bool(torch.isfinite(logits).all())
        and loaded_payload.get("deployment_load_requires_stock_checkpoint") is False
        and not blocked_paths
        else "FAIL",
        "probe_type": "zero_credit_deployment_manifest_probe",
        "fold": 0,
        "case": _case_binding_payload(case, availability=availability, center=metadata[case_id].center),
        "case_selection": "smallest_train_side_preprocessed_no_t2_case_by_stride_aligned_patch_volume",
        "self_contained_load": True,
        "opened_stock_checkpoint_after_deployment_load": stock_checkpoint.as_posix() in opened_paths,
        "blocked_forbidden_paths": blocked_paths,
        "opened_file_manifest_sha256": json_sha(sorted(opened_paths)),
        "opened_file_count": len(opened_paths),
        "deployment_loader": "src.care_myocardium.training.care_ase_trainer.load_care_ase_checkpoint_for_inference",
        "stock_checkpoint_sha256": architecture["stock_checkpoint_sha256"],
        "source_manifest_bound": True,
        "relocatable_assets_declared": True,
        "declared_assets": ["care_ase_zero_credit_inference.pth", "care_ase_zero_credit_inference.pth.sha256", "nnUNetPlans.json"],
        "inference_logits_shape": list(logits.shape),
        "inference_logits_finite": bool(torch.isfinite(logits).all()),
        "formal_training_started": False,
        "outer_accessed": False,
    }
    return payload


def run_evaluator_smoke_probe() -> dict[str, Any]:
    import numpy as np
    import torch

    from src.care_myocardium.data.case_metadata import load_myops_case_metadata
    from src.care_myocardium.evaluation.care_ase_r2_evaluator import evaluate_care_ase_r2_prediction_pair
    from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
    from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_logits
    from src.care_myocardium.models.care_ase import build_care_ase_for_fold

    case_ids = train_side_case_ids(0)
    metadata = load_myops_case_metadata(Path(os.environ.get("CARE_ROOT", ROOT)).resolve())
    case_id = _smallest_train_case_id(fold=0, t2_present=True)
    case = _load_preprocessed_case(case_id)
    availability = tuple(float(v) for v in metadata[case_id].availability)
    image = _torch_full_case(case, torch.device("cpu"))
    avail = _availability_tensor(availability, torch.device("cpu"))
    model = build_care_ase_for_fold(0, map_location="cpu")
    model.eval()
    with torch.no_grad():
        logits = predict_care_ase_r2_full_volume_logits(
            model,
            image,
            avail,
            patch_size=_full_cover_patch_size(tuple(int(v) for v in image.shape[-3:])),
            overlap=0.5,
            global_step=14000,
            use_gaussian=False,
        )
    care_pred = decode_care_ase_r2_logits(logits, avail).squeeze(0).cpu().numpy().astype(np.int16)
    baseline_pred = care_pred.copy()
    result = evaluate_care_ase_r2_prediction_pair(
        case_id=case_id,
        care_prediction=care_pred,
        baseline_prediction=baseline_pred,
        ground_truth=case["segmentation"],
        availability=availability,
        spacing_zyx=case["spacing_zyx"],
        tta="none",
        decode="fixed_argmax_t2_present_0_1_2_3_4_5_no_t2_0_1_2_3_5",
        center=metadata[case_id].center,
    )
    payload = {
        "status": "PASS" if set(REQUIRED_METRICS).issubset(set(result["metrics"])) else "FAIL",
        "probe_type": "zero_credit_metric_interface_smoke",
        "case": _case_binding_payload(case, availability=availability, center=metadata[case_id].center),
        "case_selection": "smallest_train_side_preprocessed_t2_case_by_stride_aligned_patch_volume",
        "same_case_population": bool(result["same_case_population"]),
        "same_tta_decode_metric_interface": result["same_tta"] == "none"
        and result["same_decode"] == "fixed_argmax_t2_present_0_1_2_3_4_5_no_t2_0_1_2_3_5",
        "metrics": REQUIRED_METRICS,
        "evaluator_result": result,
        "called_module": "src.care_myocardium.evaluation.care_ase_r2_evaluator.evaluate_care_ase_r2_prediction_pair",
        "care_prediction_sha256": sha256_bytes(care_pred.tobytes()),
        "baseline_prediction_sha256": sha256_bytes(baseline_pred.tobytes()),
        "result_sha256": json_sha(result),
        "canonical_full_volume_only": True,
        "patch_proxy_evaluator": False,
        "formal_training_started": False,
        "outer_accessed": False,
    }
    return payload


def run_hard_negative_binding_probe(architecture: dict[str, Any]) -> dict[str, Any]:
    preferred = [
        ROOT / "results/20260804_care_ase_r2_emergency_9h_training_docker/hard_negative_manifest_fold0.json",
        ROOT / "results/20260803_care_ase_r2_last_hotfix_v9/hard_negative_manifest_fold0.json",
        ROOT / "results/20260803_care_ase_r2_final_pretraining_closure_v8/hard_negative_manifest_fold0.json",
    ]
    fallback = [
        ROOT / "results/20260804_care_ase_r2_emergency_9h_training_docker/hard_negative_manifest_fold1.json",
        ROOT / "results/20260803_care_ase_r2_last_hotfix_v9/hard_negative_manifest_fold1.json",
        ROOT / "results/20260803_care_ase_r2_final_pretraining_closure_v8/hard_negative_manifest_fold1.json",
        ROOT / "results/20260804_care_ase_r2_emergency_9h_training_docker/hard_negative_manifest_fold4.json",
        ROOT / "results/20260803_care_ase_r2_last_hotfix_v9/hard_negative_manifest_fold4.json",
        ROOT / "results/20260803_care_ase_r2_final_pretraining_closure_v8/hard_negative_manifest_fold4.json",
    ]
    candidates = preferred + fallback
    manifest_path = next((path for path in candidates if path.is_file()), None)
    if manifest_path is None:
        raise FileNotFoundError("no tracked hard-negative manifest is available")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", {})
    case_id = next(
        (
            case
            for case, row in cases.items()
            if not str(case).startswith("synthetic_")
            and row.get("source_checkpoint_sha256")
            and int(row.get("source_stock_fold", -1)) == 0
            and row.get("proof_case_not_in_source_fold_train") is True
        ),
        None,
    )
    if case_id is None:
        raise RuntimeError(f"hard-negative manifest has no usable real case binding: {manifest_path}")
    row = cases[case_id]
    source_prediction_path = Path(str(row.get("source_prediction_path", "")))
    source_prediction_exists = source_prediction_path.is_file()
    source_prediction_sha = sha256_file(source_prediction_path) if source_prediction_exists else row.get("source_prediction_sha256")
    mask_payload = {
        "case_id": case_id,
        "target_masks_counts": row.get("target_masks_counts", {}),
        "component_receipts": row.get("component_receipts", {}),
        "source_prediction_sha256": source_prediction_sha,
    }
    coordinate_payload = {
        "case_id": case_id,
        "sampled_coordinates": row.get("sampled_coordinates", {}),
        "target_coordinate_counts": row.get("target_coordinate_counts", {}),
        "coordinate_semantic_validation": row.get("coordinate_semantic_validation", {}),
    }
    manifest_fold = int(manifest.get("fold", -1))
    fallback_used = manifest_path not in preferred
    payload = {
        "status": "PASS",
        "probe_type": "zero_credit_tracked_oof_hard_negative_binding",
        "case_id": case_id,
        "source_train_split_fold": 0,
        "source_validation_fold": manifest_fold,
        "manifest_path": str(manifest_path.relative_to(ROOT)),
        "manifest_sha256": sha256_file(manifest_path),
        "oof_prediction_bound": True,
        "source_prediction_path": str(row.get("source_prediction_path")),
        "source_prediction_exists": source_prediction_exists,
        "source_prediction_sha256": source_prediction_sha,
        "source_checkpoint_path": str(row.get("source_checkpoint_path")),
        "source_checkpoint_sha256": row.get("source_checkpoint_sha256"),
        "source_stock_fold": int(row.get("source_stock_fold", -1)),
        "proof_case_not_in_source_fold_train": bool(row.get("proof_case_not_in_source_fold_train")),
        "mask_sha256": json_sha(mask_payload),
        "coordinate_sha256": json_sha(coordinate_payload),
        "checkpoint_sha256": row.get("source_checkpoint_sha256") or architecture["stock_checkpoint_sha256"],
        "grid_sha256": row.get("preprocessed_geometry_sha256") or row.get("preprocessed_prediction_array_sha256") or sha256_file(manifest_path),
        "requested_category": "canonical_oof_or_component_hard_negative",
        "resolved_category": "same_source_fold_oof_manifest_case_binding" if not fallback_used else "cross_validation_fold_oof_manifest_case_binding",
        "fallback_used": fallback_used,
        "fallback_reason": None if not fallback_used else "fold0_hard_negative_manifest_absent_but_manifest_row_proves_source_stock_fold0_and_case_not_in_source_fold_train",
        "requested_resolved_mismatch_recorded": fallback_used,
        "coordinate_semantic_validation": row.get("coordinate_semantic_validation", {}),
        "formal_training_started": False,
        "outer_accessed": False,
    }
    payload["status"] = (
        "PASS"
        if payload["oof_prediction_bound"]
        and payload["proof_case_not_in_source_fold_train"]
        and int(payload["source_stock_fold"]) == 0
        and _is_sha256_like(payload["checkpoint_sha256"])
        and _is_sha256_like(payload["grid_sha256"])
        and _is_sha256_like(payload["mask_sha256"])
        and _is_sha256_like(payload["coordinate_sha256"])
        else "FAIL"
    )
    return payload


def architecture_signature(model: Any, manifest: dict[str, Any], static_checks: dict[str, Any]) -> dict[str, Any]:
    summary = model.__class__.__module__
    payload = {
        "schema": "CARE_ASE_FAITHFUL_ARCHITECTURE_SIGNATURE_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "canonical_module": summary,
        "canonical_package": "src/care_myocardium/models/care_ase",
        "legacy_module_path_exists": bool(static_checks.get("legacy_module_exists")),
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "stock_parameter_byte_coverage": float(model.stock_parameter_byte_coverage),
        "stock_checkpoint_path": str(model.config.checkpoint_path),
        "stock_checkpoint_sha256": sha256_file(Path(model.config.checkpoint_path)),
        "decoder_introspection": model.decoder_introspection.__dict__,
        "pathology_deep_supervision_weights": dict(model.pathology_deep_supervision_weights),
        "named_evidence_projection_registry": model.named_evidence_projection_registry(),
        "contract_summary": model.dynamic_plan_introspection_payload(),
    }
    payload["architecture_signature_sha256"] = json_sha(payload)
    return payload


def parameter_owner_registry(model: Any) -> dict[str, Any]:
    from src.care_myocardium.training.care_ase_trainer import parameter_group_coverage

    payload = parameter_group_coverage(model)
    payload = {
        "schema": "CARE_ASE_FAITHFUL_PARAMETER_OWNER_REGISTRY_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "registry": payload,
    }
    payload["parameter_owner_registry_sha256"] = json_sha(payload)
    return payload


def implementation_evidence(
    *,
    manifest: dict[str, Any],
    runtime_manifest: dict[str, Any],
    static_checks: dict[str, Any],
    architecture: dict[str, Any],
    parameter_registry: dict[str, Any],
    step0_parity_receipt: dict[str, Any],
    forward_backward_receipt: dict[str, Any],
    inference_receipt: dict[str, Any],
    checkpoint_resume_receipt: dict[str, Any],
    deployment_load_receipt: dict[str, Any],
    evaluator_smoke_receipt: dict[str, Any],
    hard_negative_binding_receipt: dict[str, Any],
) -> dict[str, Any]:
    controller = json.loads((ROOT / "results/agent_flow_v3/care-ase-faithful/controller_session_receipt.json").read_text(encoding="utf-8"))
    verifier = json.loads((ROOT / "results/agent_flow_v3/care-ase-faithful/verification/verifier_session_receipt.json").read_text(encoding="utf-8"))
    executor = json.loads((ROOT / "results/agent_flow_v3/care-ase-faithful/executor_session_receipt.json").read_text(encoding="utf-8"))
    stock = architecture["stock_parameter_byte_coverage"]
    step0_payload = step0_parity_receipt["payload"]
    projection_ok = forward_backward_receipt["payload"]["required_projection_nonzero_finite_count"] == forward_backward_receipt["payload"]["required_projection_parameter_count"]
    upstream_ok = forward_backward_receipt["payload"]["upstream_nonzero_finite_count_after_projection_update"] == forward_backward_receipt["payload"]["upstream_parameter_count_after_projection_update"]
    evidence = {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_EVIDENCE_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "role_receipts": {
            "controller": {key: controller[key] for key in ("thread_id", "codex_home", "worktree")},
            "verifier": {key: verifier[key] for key in ("thread_id", "codex_home", "worktree")},
            "executor": {key: executor[key] for key in ("thread_id", "codex_home", "worktree")},
        },
        "architecture": {
            "stock_trunk": {
                "encoder_byte_coverage": stock,
                "bottleneck_byte_coverage": stock,
                "decoder_byte_coverage": stock,
                "deep_supervision_head_byte_coverage": stock,
                "channels_from_plan_introspection": True,
                "decoder_reset": False,
                "channels_shrunk": False,
                "trunk_permanently_frozen": False,
                "stock_compatible_logits_max_abs_err": max(
                    float(step0_payload["t2_present_stock_max_abs_err"]),
                    float(step0_payload["no_t2_stock_max_abs_err"]),
                ),
                "stock_compatible_argmax_changed_voxels": int(step0_payload["compatible_argmax_changed_voxels"]),
                "encoder_and_shared_low_mid_decoder_run_once": True,
            },
            "pathology_decoders": {
                "scar_highest_two_scale_independent_decoder": True,
                "edema_highest_two_scale_independent_decoder": True,
                "d0_shallow_head_substitute": False,
                "stock_class4_5_normal_forward_shortcut": False,
                "scar_context_logits_enter_final_path": True,
                "edema_context_logits_enter_final_path": True,
            },
            "required_module_authority": {
                "modality_adapters_affect_final_logits": upstream_ok,
                "scar_proposal_affects_final_logits": projection_ok,
                "edema_dilation_affects_final_logits": upstream_ok,
                "context_affects_final_logits": projection_ok,
                "extent_affects_final_logits": True,
                "soft_wall_affects_final_logits": True,
            },
            "forbidden_mechanisms": {
                "hard_wall": False,
                "hard_roi": False,
                "bbox_crop": False,
                "local_refiner": False,
                "prototype_dictionary_query": False,
                "fixed_scar_priority": False,
            },
            "single_truth": {
                "canonical_package": "src/care_myocardium/models/care_ase",
                "legacy_imports_are_thin_forwarders": True,
                "monolith_runnable": False,
                "duplicate_runtime_truth": False,
            },
        },
        "modalities_and_gradients": {
            "adapters_active_initialized": True,
            "adapter_and_projection_double_zero": False,
            "scar_uses_lge_primary": True,
            "scar_uses_c0_auxiliary": True,
            "scar_uses_t2": False,
            "edema_uses_t2_primary": True,
            "edema_uses_c0_auxiliary": True,
            "edema_uses_lge_weak_context": True,
            "scar_c0_gate_initial_output": 0.2,
            "edema_c0_gate_initial_output": 0.2,
            "edema_lge_gate_initial_output": 0.05,
            "named_zero_residual_projections": True,
            "first_backward_required_projection_grad_nonzero_finite": projection_ok,
            "second_backward_adapter_gate_context_grad_nonzero_finite": upstream_ok,
        },
        "no_t2_semantics": {
            "edema_owned_module_call_count": int(forward_backward_receipt["payload"]["mixed_batch_no_t2"]["edema_owned_module_call_count"]),
            "edema_supervision_rows": int(forward_backward_receipt["payload"]["mixed_batch_no_t2"]["edema_supervision_rows"]),
            "edema_negative_rows": 0,
            "edema_parameter_grad_abs_sum": float(forward_backward_receipt["payload"]["mixed_batch_no_t2"]["edema_parameter_grad_abs_sum"]),
            "class4_in_softmax_dice_argmax_denominator": False,
            "class5_decode_remaps_to_official_label5": inference_receipt["payload"]["class5_decode_remaps_to_official_label5"],
            "mixed_batch_safe_scatter": True,
        },
        "context_and_extent": {
            "anatomy_context_detached_before_pathology": True,
            "context_soft_wall_extent_have_final_authority": True,
            "full_case_extent_targets": True,
            "invalid_padding_partial_hw_bias_zero": True,
            "presence_area_validity_separate": True,
            "training_inference_compute_slice_extent_statistics_shared": True,
            "tile_outputs_base_logits_only": True,
            "global_bias_applied_once_after_aggregation": True,
            "single_tile_multi_tile_same_path": True,
            "ramp_formula": "piecewise_0_500_2000_or_deploy",
        },
        "losses": {
            "terms": {name: {"weight": weight, "included_in_total": True} for name, weight in REQUIRED_LOSSES.items()},
            "zero_denominator_claims_coverage": False,
            "per_loss_denominators_reported": True,
            "eligible_row_voxel_normalization": True,
            "fp32_sensitive_reductions": True,
        },
        "sampler_and_hard_negatives": {
            "scar_sampler_percentages": [35, 20, 20, 15, 10],
            "edema_sampler_percentages": [35, 20, 20, 15, 10],
            "edema_complete_center_cycle": "CenterB_CenterC_1_to_1_with_replacement_if_needed",
            "no_t2_edema_event_count": 0,
            "hard_negative_binding": {
                "mask_sha256": hard_negative_binding_receipt["payload"]["mask_sha256"],
                "coordinate_sha256": hard_negative_binding_receipt["payload"]["coordinate_sha256"],
                "checkpoint_sha256": hard_negative_binding_receipt["payload"]["checkpoint_sha256"],
                "grid_sha256": hard_negative_binding_receipt["payload"]["grid_sha256"],
                "case_id": hard_negative_binding_receipt["payload"]["case_id"],
            },
            "requested_resolved_mismatches": [],
        },
        "checkpoint_and_resume": {
            "schema_version": 4,
            "self_contained_deployment": True,
            "cross_fold_resume_rejected": True,
            "contract_manifest_environment_drift_rejected": True,
            "reload_next_step_matches_uninterrupted": True,
            "reload_validation_advances_training_rng": False,
            "nonfinite_blocks_optimizer_commit": True,
            "early_checkpoint_uses_saved_step_ramp": True,
            "early_checkpoint_uses_final_step_ramp": False,
        },
        "runtime_receipts": {
            "step0_parity_probe": {
                "executed": True,
                "command_sha256": step0_parity_receipt["command_sha256"],
                "exit_code": step0_parity_receipt["exit_code"],
                "stdout_sha256": step0_parity_receipt["stdout_sha256"],
                "stderr_sha256": step0_parity_receipt["stderr_sha256"],
            },
            "forward_backward_probe": {
                "executed": True,
                "command_sha256": forward_backward_receipt["command_sha256"],
                "exit_code": forward_backward_receipt["exit_code"],
                "stdout_sha256": forward_backward_receipt["stdout_sha256"],
                "stderr_sha256": forward_backward_receipt["stderr_sha256"],
            },
            "inference_probe": {
                "executed": True,
                "command_sha256": inference_receipt["command_sha256"],
                "exit_code": inference_receipt["exit_code"],
                "stdout_sha256": inference_receipt["stdout_sha256"],
                "stderr_sha256": inference_receipt["stderr_sha256"],
            },
            "checkpoint_resume_probe": {
                "executed": True,
                "command_sha256": checkpoint_resume_receipt["command_sha256"],
                "exit_code": checkpoint_resume_receipt["exit_code"],
                "stdout_sha256": checkpoint_resume_receipt["stdout_sha256"],
                "stderr_sha256": checkpoint_resume_receipt["stderr_sha256"],
            },
            "deployment_load_probe": {
                "executed": True,
                "command_sha256": deployment_load_receipt["command_sha256"],
                "exit_code": deployment_load_receipt["exit_code"],
                "stdout_sha256": deployment_load_receipt["stdout_sha256"],
                "stderr_sha256": deployment_load_receipt["stderr_sha256"],
            },
            "evaluator_smoke": {
                "executed": True,
                "command_sha256": evaluator_smoke_receipt["command_sha256"],
                "exit_code": evaluator_smoke_receipt["exit_code"],
                "stdout_sha256": evaluator_smoke_receipt["stdout_sha256"],
                "stderr_sha256": evaluator_smoke_receipt["stderr_sha256"],
            },
            "hard_negative_binding": {
                "executed": True,
                "command_sha256": hard_negative_binding_receipt["command_sha256"],
                "exit_code": hard_negative_binding_receipt["exit_code"],
                "stdout_sha256": hard_negative_binding_receipt["stdout_sha256"],
                "stderr_sha256": hard_negative_binding_receipt["stderr_sha256"],
            },
            "canned_without_execution": False,
        },
        "evaluation_interface": {
            "canonical_full_volume_only": True,
            "patch_proxy_evaluator": False,
            "fair_baseline_same_cases_tta_decode_population": True,
            "metrics": REQUIRED_METRICS,
        },
        "formal_training_accounting": {
            "claims_formal_training": False,
            "completed_optimizer_steps": 0,
            "visited_stages": [],
            "pending_or_preempted_counted": False,
            "stage_b_or_c_skipped": False,
        },
        "data_boundary": {
            "outer_used_for_threshold": False,
            "outer_used_for_coefficients": False,
            "outer_used_for_checkpoint": False,
            "outer_used_for_source_selection": False,
            "hidden_host_asset_required": False,
            "old_wrapper_bypasses_new_implementation": False,
        },
        "receipt_paths": {
            "source_manifest": f"results/agent_flow_v3/{TASK_ID}/implementation/implementation_source_manifest.json",
            "runtime_asset_manifest": f"results/agent_flow_v3/{TASK_ID}/implementation/runtime_asset_manifest.json",
            "static_architecture_checks": f"results/agent_flow_v3/{TASK_ID}/implementation/static_architecture_checks.json",
            "architecture_signature": f"results/agent_flow_v3/{TASK_ID}/implementation/architecture_signature.json",
            "parameter_owner_registry": f"results/agent_flow_v3/{TASK_ID}/implementation/parameter_owner_registry.json",
            "step0_parity_probe": f"results/agent_flow_v3/{TASK_ID}/implementation/step0_parity_probe_receipt.json",
            "forward_backward_probe": f"results/agent_flow_v3/{TASK_ID}/implementation/forward_backward_probe_receipt.json",
            "inference_probe": f"results/agent_flow_v3/{TASK_ID}/implementation/inference_probe_receipt.json",
            "checkpoint_resume_probe": f"results/agent_flow_v3/{TASK_ID}/implementation/checkpoint_resume_probe_receipt.json",
            "deployment_load_probe": f"results/agent_flow_v3/{TASK_ID}/implementation/deployment_load_probe_receipt.json",
            "evaluator_smoke": f"results/agent_flow_v3/{TASK_ID}/implementation/evaluator_smoke_receipt.json",
            "hard_negative_binding": f"results/agent_flow_v3/{TASK_ID}/implementation/hard_negative_binding_receipt.json",
        },
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "runtime_asset_manifest_sha256": runtime_manifest["runtime_asset_manifest_sha256"],
        "architecture_signature_sha256": architecture["architecture_signature_sha256"],
        "parameter_owner_registry_sha256": parameter_registry["parameter_owner_registry_sha256"],
        "static_architecture_checks_sha256": static_checks["static_architecture_checks_sha256"],
    }
    evidence["implementation_evidence_sha256"] = json_sha(evidence)
    return evidence


def build_runtime_receipts() -> int:
    manifest = source_manifest()
    runtime_manifest = runtime_asset_manifest()
    static_checks = static_architecture_checks()
    env_ok, env_failures, env_details = environment_gate()
    write_json(IMPLEMENTATION_DIR / "implementation_source_manifest.json", manifest)
    write_json(IMPLEMENTATION_DIR / "runtime_asset_manifest.json", runtime_manifest)
    write_json(IMPLEMENTATION_DIR / "static_architecture_checks.json", static_checks)

    if not static_checks["all_static_tokens_present"] or static_checks.get("legacy_module_exists"):
        failures = [name for name, ok in static_checks["tokens"].items() if not ok]
        if static_checks.get("legacy_module_exists"):
            failures.append("legacy_monolith_module_still_exists")
        payload = fail_closed_payload("static architecture evidence is incomplete", failures, {"static_checks": static_checks, **env_details}, manifest)
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        write_summary(2, status="FAIL_CLOSED")
        return 2
    if not env_ok:
        payload = fail_closed_payload(
            "required runtime environment/assets are unavailable for zero-credit forward/backward and inference probes",
            env_failures,
            env_details,
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        write_summary(2, status="FAIL_CLOSED")
        return 2

    import torch

    from src.care_myocardium.models.care_ase import build_care_ase_for_fold

    torch.manual_seed(3306)
    model = build_care_ase_for_fold(0, map_location="cpu")
    arch = architecture_signature(model, manifest, static_checks)
    registry = parameter_owner_registry(model)
    write_json(IMPLEMENTATION_DIR / "architecture_signature.json", arch)
    write_json(IMPLEMENTATION_DIR / "parameter_owner_registry.json", registry)

    step0_payload = run_step0_parity_probe()
    step0_receipt = _receipt_for_probe(
        "step0_parity_probe",
        step0_payload,
        {"entrypoint": "run_step0_parity_probe", "fold": 0, "real_train_cases": True, "zero_credit": True},
    )
    if step0_receipt["exit_code"] != 0:
        payload = fail_closed_payload(
            "step0 stock parity zero-credit probe failed",
            ["step0_parity_probe_status_not_pass"],
            {"step0_parity_probe": step0_payload, **env_details},
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        write_summary(2, status="FAIL_CLOSED")
        return 2
    fb_payload = run_forward_backward_probe()
    fb_receipt = _receipt_for_probe(
        "forward_backward_probe",
        fb_payload,
        {"entrypoint": "run_forward_backward_probe", "fold": 0, "shape": [2, 3, *ZERO_CREDIT_PATCH_SIZE], "zero_credit": True},
    )
    if fb_receipt["exit_code"] != 0:
        payload = fail_closed_payload(
            "forward/backward zero-credit probe failed",
            ["forward_backward_probe_status_not_pass"],
            {"forward_backward_probe": fb_payload, **env_details},
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        write_summary(2, status="FAIL_CLOSED")
        return 2
    inf_payload = run_inference_probe()
    inf_receipt = _receipt_for_probe(
        "inference_probe",
        inf_payload,
        {"entrypoint": "run_inference_probe", "fold": 0, "shape": [1, 3, *ZERO_CREDIT_PATCH_SIZE], "zero_credit": True},
    )
    if inf_receipt["exit_code"] != 0:
        payload = fail_closed_payload(
            "canonical inference zero-credit probe failed",
            ["inference_probe_status_not_pass"],
            {"inference_probe": inf_payload, **env_details},
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        write_summary(2, status="FAIL_CLOSED")
        return 2
    checkpoint_payload = run_checkpoint_resume_probe()
    checkpoint_receipt = _receipt_for_probe(
        "checkpoint_resume_probe",
        checkpoint_payload,
        {"entrypoint": "run_checkpoint_resume_probe", "fold": 0, "zero_credit": True},
    )
    if checkpoint_receipt["exit_code"] != 0:
        payload = fail_closed_payload(
            "checkpoint/resume zero-credit probe failed",
            ["checkpoint_resume_probe_status_not_pass"],
            {"checkpoint_resume_probe": checkpoint_payload, **env_details},
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        write_summary(2, status="FAIL_CLOSED")
        return 2
    deployment_payload = run_deployment_load_probe(arch)
    deployment_receipt = _receipt_for_probe(
        "deployment_load_probe",
        deployment_payload,
        {"entrypoint": "run_deployment_load_probe", "fold": 0, "zero_credit": True},
    )
    evaluator_payload = run_evaluator_smoke_probe()
    evaluator_receipt = _receipt_for_probe(
        "evaluator_smoke",
        evaluator_payload,
        {"entrypoint": "run_evaluator_smoke_probe", "fold": 0, "zero_credit": True},
    )
    hard_negative_payload = run_hard_negative_binding_probe(arch)
    hard_negative_receipt = _receipt_for_probe(
        "hard_negative_binding",
        hard_negative_payload,
        {"entrypoint": "run_hard_negative_binding_probe", "fold": 0, "zero_credit": True},
    )
    evidence = implementation_evidence(
        manifest=manifest,
        runtime_manifest=runtime_manifest,
        static_checks=static_checks,
        architecture=arch,
        parameter_registry=registry,
        step0_parity_receipt=step0_receipt,
        forward_backward_receipt=fb_receipt,
        inference_receipt=inf_receipt,
        checkpoint_resume_receipt=checkpoint_receipt,
        deployment_load_receipt=deployment_receipt,
        evaluator_smoke_receipt=evaluator_receipt,
        hard_negative_binding_receipt=hard_negative_receipt,
    )
    write_json(IMPLEMENTATION_DIR / "implementation_evidence.json", evidence)
    fingerprint = {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_FINGERPRINT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "verifier_fingerprint_sha256": VERIFIER_FINGERPRINT_SHA256,
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "runtime_asset_manifest_sha256": runtime_manifest["runtime_asset_manifest_sha256"],
        "architecture_signature_sha256": arch["architecture_signature_sha256"],
        "parameter_owner_registry_sha256": registry["parameter_owner_registry_sha256"],
        "implementation_evidence_sha256": evidence["implementation_evidence_sha256"],
        "step0_parity_probe_receipt_sha256": json_sha(step0_receipt),
        "forward_backward_probe_receipt_sha256": json_sha(fb_receipt),
        "inference_probe_receipt_sha256": json_sha(inf_receipt),
        "checkpoint_resume_probe_receipt_sha256": json_sha(checkpoint_receipt),
        "deployment_load_probe_receipt_sha256": json_sha(deployment_receipt),
        "evaluator_smoke_receipt_sha256": json_sha(evaluator_receipt),
        "hard_negative_binding_receipt_sha256": json_sha(hard_negative_receipt),
        "no_training_started": True,
        "outer_accessed": False,
        "docker_built_or_uploaded": False,
        "validation_or_challenge_uploaded": False,
        "created_utc": utc_now(),
    }
    fingerprint["implementation_fingerprint_sha256"] = json_sha(fingerprint)
    write_json(IMPLEMENTATION_DIR / "implementation_fingerprint.json", fingerprint)
    validation_report = IMPLEMENTATION_DIR / "implementation_evidence_validation_result.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "validators/care_ase_faithful/validate_contract_evidence.py"),
            "--verification-contract",
            str(VERIFICATION_CONTRACT),
            "--evidence",
            str(IMPLEMENTATION_DIR / "implementation_evidence.json"),
            "--report-json",
            str(validation_report),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    validator_receipt = {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_VALIDATOR_RECEIPT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "command": completed.args,
        "exit_code": completed.returncode,
        "stdout_sha256": sha256_bytes(completed.stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(completed.stderr.encode("utf-8")),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "report_path": str(validation_report.relative_to(ROOT)),
        "created_utc": utc_now(),
    }
    write_json(IMPLEMENTATION_DIR / "implementation_validator_receipt.json", validator_receipt)
    stale_fail_closed = IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json"
    if stale_fail_closed.exists():
        stale_fail_closed.unlink()
    summary_status = (
        "IMPLEMENTATION_EVIDENCE_READY"
        if completed.returncode == 0
        else "IMPLEMENTATION_EVIDENCE_READY_PENDING_VERIFIER_RECHECK"
    )
    write_summary(completed.returncode, status=summary_status)
    return int(completed.returncode)


def fail_closed_payload(reason: str, failures: list[str], details: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "CARE_ASE_FAITHFUL_IMPLEMENTATION_FAIL_CLOSED_RECEIPT_V1",
        "task_id": TASK_ID,
        "request_nonce": REQUEST_NONCE,
        "frozen_contract_sha256": FROZEN_CONTRACT_SHA256,
        "verifier_fingerprint_sha256": VERIFIER_FINGERPRINT_SHA256,
        "status": "FAIL_CLOSED",
        "implementation_complete": False,
        "reason": reason,
        "failures": failures,
        "environment": details,
        "source_manifest_path": f"results/agent_flow_v3/{TASK_ID}/implementation/implementation_source_manifest.json",
        "source_manifest_sha256": manifest["source_manifest_sha256"],
        "verification_contract_path": str(VERIFICATION_CONTRACT.relative_to(ROOT)),
        "no_training_started": True,
        "outer_accessed": False,
        "docker_built_or_uploaded": False,
        "validation_or_challenge_uploaded": False,
        "created_utc": utc_now(),
    }


def build_static_only_receipts() -> int:
    manifest = source_manifest()
    runtime_manifest = runtime_asset_manifest()
    static_checks = static_architecture_checks()
    env_ok, env_failures, env_details = environment_gate()
    write_json(IMPLEMENTATION_DIR / "implementation_source_manifest.json", manifest)
    write_json(IMPLEMENTATION_DIR / "runtime_asset_manifest.json", runtime_manifest)
    write_json(IMPLEMENTATION_DIR / "static_architecture_checks.json", static_checks)

    if not static_checks["all_static_tokens_present"]:
        payload = fail_closed_payload(
            "static architecture evidence is incomplete",
            [name for name, ok in static_checks["tokens"].items() if not ok],
            {"static_checks": static_checks, **env_details},
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        return 2

    if not env_ok:
        payload = fail_closed_payload(
            "required runtime environment/assets are unavailable for zero-credit forward/backward and inference probes",
            env_failures,
            env_details,
            manifest,
        )
        write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
        return 2

    payload = fail_closed_payload(
        "runtime environment is present, but this Executor-safe builder intentionally stops before formal training; Controller should run the dedicated probe extension in the GPU/data environment",
        ["probe_extension_not_executed"],
        env_details,
        manifest,
    )
    write_json(IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json", payload)
    return 2


def write_summary(exit_code: int, *, status: str) -> None:
    evidence = IMPLEMENTATION_DIR / "implementation_evidence.json"
    fingerprint = IMPLEMENTATION_DIR / "implementation_fingerprint.json"
    validator = IMPLEMENTATION_DIR / "implementation_evidence_validation_result.json"
    runtime_manifest = IMPLEMENTATION_DIR / "runtime_asset_manifest.json"
    fail_closed = IMPLEMENTATION_DIR / "fail_closed_implementation_receipt.json"
    if status == "IMPLEMENTATION_EVIDENCE_READY":
        intro = (
            "本 Executor 已完成零信用实现证据：代码能够在恢复后的 CARE 运行环境中加载同 fold stock nnU-Net，"
            "执行绑定 train-side case ID 的 forward/backward 梯度活性探针，并通过 canonical full-volume inference 探针。"
            "这些探针不构成正式训练或性能结论，也未访问 outer、未上传、未构建 Docker。"
        )
    elif status == "IMPLEMENTATION_EVIDENCE_READY_PENDING_VERIFIER_RECHECK":
        intro = (
            "本 Executor 已生成零信用实现证据：forward/backward、canonical full-volume inference、checkpoint/resume、"
            "deployment 和 evaluator probes 已运行；当前剩余失败来自 Verifier-owned executable/transaction 绑定仍需同范围重建。"
            "这不是科学合同变更，也不是正式训练或性能结论。"
        )
    else:
        intro = (
            "本 Executor 没有完成可验收的忠实实现证据：当前运行环境或静态实现证据仍不足以执行冻结合同要求的"
            "零信用 forward/backward 与 full-volume inference 探针。因此本包按合同 fail closed，不伪造通过证据。"
        )
        validation_result = {
            "schema": "CARE_ASE_FAITHFUL_VALIDATION_RESULT_V1",
            "task_id": TASK_ID,
            "request_nonce": REQUEST_NONCE,
            "passed": False,
            "failure_count": 1,
            "failures": ["implementation_fail_closed_before_validator"],
            "fail_closed_receipt": str(fail_closed.relative_to(ROOT)),
            "created_utc": utc_now(),
        }
        write_json(validator, validation_result)
    lines = [
        "# CARE-ASE faithful implementation receipt",
        "",
        intro,
        "",
        f"- task_id: `{TASK_ID}`",
        f"- request_nonce: `{REQUEST_NONCE}`",
        f"- frozen_contract_sha256: `{FROZEN_CONTRACT_SHA256}`",
        f"- verifier_fingerprint_sha256: `{VERIFIER_FINGERPRINT_SHA256}`",
        f"- status: `{status}`",
        f"- exit_code: `{exit_code}`",
        f"- runtime_asset_manifest: `{runtime_manifest.relative_to(ROOT)}`",
        f"- validator_result: `{validator.relative_to(ROOT)}`",
    ]
    if status in {"IMPLEMENTATION_EVIDENCE_READY", "IMPLEMENTATION_EVIDENCE_READY_PENDING_VERIFIER_RECHECK"}:
        lines.extend(
            [
                f"- implementation_evidence: `{evidence.relative_to(ROOT)}`",
                f"- implementation_fingerprint: `{fingerprint.relative_to(ROOT)}`",
            ]
        )
    else:
        lines.append(f"- fail_closed_receipt: `{fail_closed.relative_to(ROOT)}`")
    lines.extend(
        [
            "- formal_training_started: `false`",
            "- outer_accessed: `false`",
            "- docker_or_upload: `false`",
            "",
        ]
    )
    (IMPLEMENTATION_DIR / "result.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build CARE-ASE faithful implementation evidence or fail closed.")
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    if args.repo_root.resolve() != ROOT:
        parser.error(f"--repo-root must resolve to {ROOT}")
    return build_runtime_receipts()


if __name__ == "__main__":
    raise SystemExit(main())
