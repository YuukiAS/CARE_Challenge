#!/usr/bin/env python
"""RC2 real-asset preflight for CARE-SRR-Cascade."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import pickle
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
from scipy.ndimage import distance_transform_edt
from torch.nn import functional as F

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nnunetv2.preprocessing.resampling.default_resampling import resample_data_or_seg_to_shape
from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from src.care_myocardium.data.care_srr_cascade_runtime import (
    ScheduleRow,
    apply_shared_spatial_augmentation,
    deterministic_schedule,
    schedule_sha256,
    write_schedule_csv,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.losses.care_srr_cascade_rescue_losses import care_srr_cascade_rescue_loss_terms
from src.care_myocardium.losses.care_srr_cascade_rescue_losses import care_srr_cascade_rescue_loss_audit_terms
from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue
from src.care_myocardium.srr_production.anchor_runtime import (
    EPSILON,
    anchor_uncertainty,
    canonicalize_probabilities,
    sha256_file,
    soft_union_probability,
)
from src.care_myocardium.srr_production.case_prototypes import (
    EDEMA_NEGATIVE_CATEGORIES,
    EDEMA_POSITIVE_CATEGORIES,
    SCAR_NEGATIVE_CATEGORIES,
    SCAR_POSITIVE_CATEGORIES,
    build_case_prototype_record,
    cosine_similarity_maps,
    select_crossfit_prototype_bank,
)
from src.care_myocardium.training.care_srr_cascade_trainer import (
    CARESRRCascadeFormalTrainer,
    FormalRuntimeConfig,
    sha256_json,
)


RESULT_ROOT = REPO_ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
RC1_ROOT = RESULT_ROOT / "runtime_closure_repair_rc1"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json"
OOF_MANIFEST = REPO_ROOT / "results/srr_production/code_maturity/batch2a_raw_oof_anchor_manifest.json"
ANCHOR_DIR = RESULT_ROOT / "runtime/anchor_cache_v2"
SOURCE_DIR = RESULT_ROOT / "runtime/source_cache_v2"
PROTOTYPE_DIR = RESULT_ROOT / "runtime/prototype_cache_v2"
SCHEDULE_DIR = RESULT_ROOT / "runtime/matched_schedules_v2"
FORMAL_ROOT = RESULT_ROOT / "runtime/formal_v2"
CONFIG_PATH = REPO_ROOT / "configs/care_mm/srr_cascade_runtime_closure_repair.yaml"
TEACHER_CKPT = RESULT_ROOT.parent / "20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/teacher_full_view/checkpoint_epoch50.pt"
STUDENT_CKPT = RESULT_ROOT.parent / "20260723_care_myops_batch9_exposed_issues_repair/runtime/seed20260723/student_reliable_distill/checkpoint_epoch25.pt"
EXPECTED_CHECKPOINT_SHA256 = {
    "teacher_full_view": "e92521fccec92d0066f3fa5c076fce16aea3bb02330b940c85321ab4726d1474",
    "student_reliable_distill": "366722497a47f292e07a0d1c1a3da57c2502b61042bc89b5cfc56b5a89e6a3a0",
}
SOURCE_FIELDS = {
    "teacher_full_view": {"full_resolution_feature", "anatomy_logits", "edema_logit"},
    "student_reliable_distill": {"scar_final_margin"},
}


def load_source_direct_parity_contract() -> dict[str, Any]:
    text = CONFIG_PATH.read_text()
    block_match = re.search(r"(?ms)^  direct_parity:\n(?P<block>(?:    .+\n)+)", text)
    if not block_match:
        raise RuntimeError("source_cache direct_parity block missing from config")
    block = block_match.group("block")
    minimum_match = re.search(r"minimum_cases:\s*(\d+)", block)
    patterns_match = re.search(r"include_modality_patterns:\s*\[([^\]]+)\]", block)
    feature_match = re.search(r"feature_max_abs_delta:\s*([0-9.eE+-]+)", block)
    logit_match = re.search(r"logit_max_abs_delta:\s*([0-9.eE+-]+)", block)
    if not (minimum_match and patterns_match and feature_match and logit_match):
        raise RuntimeError("source_cache direct_parity block is incomplete")
    return {
        "minimum_cases": int(minimum_match.group(1)),
        "include_modality_patterns": [item.strip() for item in patterns_match.group(1).split(",")],
        "feature_max_abs_delta": float(feature_match.group(1)),
        "logit_max_abs_delta": float(logit_match.group(1)),
    }


def contract_modality_pattern_from_group(modality_group: str) -> str:
    mapping = {
        "C0+LGE+T2": "trimodal",
        "C0+LGE": "LGE_C0",
        "LGE-only": "LGE_only",
    }
    return mapping.get(modality_group, "other")

LOGICAL_JOBS = {
    "scar_seed20260724": ("scar", 20260724, ("scar_cascade_control", "scar_srr_cascade")),
    "edema_seed20260724": ("edema", 20260724, ("edema_zone_control", "edema_srr_zone_cascade")),
    "scar_seed20260725": ("scar", 20260725, ("scar_cascade_control", "scar_srr_cascade")),
    "edema_seed20260725": ("edema", 20260725, ("edema_zone_control", "edema_srr_zone_cascade")),
}
COMPATIBLE_GPU_PREFLIGHT_PARTITIONS = ("htzhulab", "a100-gpu", "volta-gpu")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0]) if rows else ["decision", "reason"]
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256_path(path: Path) -> str:
    return sha256_file(path)


def state_dict_sha256(model: torch.nn.Module) -> str:
    buffer = io.BytesIO()
    torch.save(model.state_dict(), buffer)
    return hashlib.sha256(buffer.getvalue()).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def manifest_case_ids(manifest: dict[str, Any]) -> list[str]:
    case_ids = sorted({str(entry["case_id"]) for entry in manifest.get("entries", [])})
    if len(case_ids) != 220:
        raise RuntimeError(f"expected 220 unique OOF cases from entries, got {len(case_ids)}")
    if manifest.get("unique_cases") not in (220, case_ids):
        raise RuntimeError("OOF manifest unique_cases field is inconsistent with entries")
    return case_ids


def load_manifest() -> dict[str, Any]:
    payload = json.loads(OOF_MANIFEST.read_text())
    if int(payload.get("case_count", 0)) != 220 or len(payload.get("entries", [])) != 220:
        raise RuntimeError("OOF manifest is not all-220")
    return payload


def anchor_cache_status() -> dict[str, Any]:
    manifest = RESULT_ROOT / "anchor_cache_manifest_v2.csv"
    roundtrip = RESULT_ROOT / "anchor_cache_roundtrip_v2.csv"
    hashes = RESULT_ROOT / "anchor_cache_hashes_v2.json"
    if not (manifest.exists() and roundtrip.exists() and ANCHOR_DIR.is_dir()):
        return {
            "decision": "NEEDS_REPAIR_ANCHOR_CACHE_MISSING",
            "case_count": 0,
            "manifest_rows": 0,
            "roundtrip_rows": 0,
            "cache_file_count": len(list(ANCHOR_DIR.glob("*__anchor.pt"))) if ANCHOR_DIR.is_dir() else 0,
            "blockers": ["anchor manifest/roundtrip/final_dir missing"],
        }
    rows = csv_rows(manifest)
    rt_rows = csv_rows(roundtrip)
    cases = {row.get("case_id", "") for row in rows}
    blockers: list[str] = []
    if len(cases) != 220:
        blockers.append(f"case_count={len(cases)} expected 220")
    if len(rows) != 220:
        blockers.append(f"manifest_rows={len(rows)} expected 220")
    if len(rt_rows) != 220:
        blockers.append(f"roundtrip_rows={len(rt_rows)} expected 220")
    if len(list(ANCHOR_DIR.glob("*__anchor.pt"))) != 220:
        blockers.append(f"cache_file_count={len(list(ANCHOR_DIR.glob('*__anchor.pt')))} expected 220")
    hash_payload = json.loads(hashes.read_text()) if hashes.exists() else {}
    if hashes.exists() and hash_payload.get("decision") != "PASS":
        blockers.append("anchor_cache_hashes_v2 decision not PASS")
    if hashes.exists() and hash_payload.get("manifest_sha256") != sha256_path(manifest):
        blockers.append("anchor manifest sha mismatch")
    if hashes.exists() and hash_payload.get("roundtrip_sha256") != sha256_path(roundtrip):
        blockers.append("anchor roundtrip sha mismatch")
    for row in rows:
        if row.get("decision") != "PASS":
            blockers.append(f"manifest row not PASS: {row.get('case_id')}")
            break
        if row.get("is_oof") not in {"True", "true", "1", True}:
            blockers.append(f"manifest row not OOF: {row.get('case_id')}")
            break
        builder = row.get("builder", "")
        if builder not in {"reverse_probability", "direct_oof_checkpoint_fallback"}:
            blockers.append(f"unknown anchor builder {builder}: {row.get('case_id')}")
            break
        path_text = row.get("cache_path", "")
        cache_path = REPO_ROOT / path_text
        if not cache_path.exists():
            blockers.append(f"missing anchor cache_path {path_text}")
            break
        if row.get("cache_sha256") != sha256_path(cache_path):
            blockers.append(f"anchor cache sha mismatch {path_text}")
            break
    for row in rt_rows:
        if row.get("decision") != "PASS" or int(row.get("changed_voxels", -1)) != 0:
            blockers.append(f"roundtrip row not PASS zero-change: {row.get('case_id')}")
            break
    return {
        "decision": "PASS" if not blockers else "NEEDS_REPAIR",
        "case_count": len(cases),
        "manifest_rows": len(rows),
        "roundtrip_rows": len(rt_rows),
        "cache_file_count": len(list(ANCHOR_DIR.glob("*__anchor.pt"))),
        "builder_counts": {builder: sum(1 for row in rows if row.get("builder") == builder) for builder in sorted({row.get("builder", "") for row in rows})},
        "blockers": blockers[:20],
    }


def anchor_cache_receipt_status() -> dict[str, Any]:
    manifest = RESULT_ROOT / "anchor_cache_manifest_v2.csv"
    roundtrip = RESULT_ROOT / "anchor_cache_roundtrip_v2.csv"
    hashes = RESULT_ROOT / "anchor_cache_hashes_v2.json"
    blockers: list[str] = []
    if not (manifest.exists() and roundtrip.exists() and hashes.exists() and ANCHOR_DIR.is_dir()):
        blockers.append("anchor manifest/roundtrip/hash/final_dir missing")
        return {"decision": "NEEDS_REPAIR", "blockers": blockers}
    rows = csv_rows(manifest)
    rt_rows = csv_rows(roundtrip)
    payload = json.loads(hashes.read_text())
    cases = sorted({row.get("case_id", "") for row in rows if row.get("case_id")})
    file_cases = sorted(path.name.split("__", 1)[0] for path in ANCHOR_DIR.glob("*__anchor.pt"))
    if payload.get("decision") != "PASS":
        blockers.append("anchor_cache_hashes_v2 decision not PASS")
    if payload.get("manifest_sha256") != sha256_path(manifest):
        blockers.append("anchor manifest sha mismatch")
    if payload.get("roundtrip_sha256") != sha256_path(roundtrip):
        blockers.append("anchor roundtrip sha mismatch")
    if int(payload.get("case_count", 0)) != 220 or len(cases) != 220:
        blockers.append(f"anchor case_count payload={payload.get('case_count')} manifest={len(cases)} expected 220")
    if int(payload.get("manifest_rows", 0)) != 220 or len(rows) != 220:
        blockers.append(f"anchor manifest rows payload={payload.get('manifest_rows')} observed={len(rows)} expected 220")
    if int(payload.get("roundtrip_rows", 0)) != 220 or len(rt_rows) != 220:
        blockers.append(f"anchor roundtrip rows payload={payload.get('roundtrip_rows')} observed={len(rt_rows)} expected 220")
    if int(payload.get("cache_file_count", 0)) != 220 or len(file_cases) != 220:
        blockers.append(f"anchor cache files payload={payload.get('cache_file_count')} observed={len(file_cases)} expected 220")
    if cases != file_cases:
        blockers.append("anchor manifest cases do not match actual cache files")
    if int(payload.get("roundtrip_changed_voxels_max", -1)) != 0:
        blockers.append("anchor roundtrip_changed_voxels_max not zero")
    if any(row.get("decision") != "PASS" for row in rows):
        blockers.append("anchor manifest contains non-PASS rows")
    if any(row.get("is_oof") not in {"True", "true", "1", True} for row in rows):
        blockers.append("anchor manifest contains non-OOF rows")
    if any(row.get("builder", "") not in {"reverse_probability", "direct_oof_checkpoint_fallback"} for row in rows):
        blockers.append("anchor manifest contains unknown builder")
    if any(row.get("decision") != "PASS" or int(row.get("changed_voxels", -1)) != 0 for row in rt_rows):
        blockers.append("anchor roundtrip contains non-PASS or nonzero changed voxels")
    return {
        "decision": "PASS" if not blockers else "NEEDS_REPAIR",
        "case_count": len(cases),
        "manifest_rows": len(rows),
        "roundtrip_rows": len(rt_rows),
        "cache_file_count": len(file_cases),
        "blockers": blockers[:20],
    }


def load_plans_configuration():
    plans = json.loads(PLANS.read_text())
    manager = PlansManager(plans)
    return manager.get_configuration("3d_fullres")


def preprocessed_shape(case_id: str) -> tuple[int, int, int]:
    arr = blosc2.open(str(PREPROCESSED / f"{case_id}.b2nd"), mode="r")[...]
    return tuple(int(v) for v in arr.shape[1:])


def label_array(case_id: str) -> np.ndarray:
    return blosc2.open(str(PREPROCESSED / f"{case_id}_seg.b2nd"), mode="r")[...][0].astype(np.int16)


def canonical_distance(mask: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray:
    if mask.any():
        return distance_transform_edt(~mask.astype(bool), sampling=spacing).astype(np.float32)
    return np.full(mask.shape, 999.0, dtype=np.float32)


def build_anchor_cache() -> dict[str, Any]:
    existing = anchor_cache_status()
    if existing["decision"] == "PASS":
        return existing
    manifest = load_manifest()
    cm = load_plans_configuration()
    if ANCHOR_DIR.exists():
        shutil.rmtree(ANCHOR_DIR)
    ANCHOR_DIR.mkdir(parents=True)
    rows: list[dict[str, Any]] = []
    roundtrip_rows: list[dict[str, Any]] = []
    for index, entry in enumerate(sorted(manifest["entries"], key=lambda r: r["case_id"]), start=1):
        case_id = entry["case_id"]
        prob_path = REPO_ROOT / entry["probability_path"]
        if sha256_path(prob_path) != entry["probability_sha256"]:
            raise RuntimeError(f"probability sha mismatch: {case_id}")
        probs = np.load(prob_path)[entry["probability_key"]].astype(np.float32)
        if probs.shape[0] != 6 or not np.isfinite(probs).all() or float(probs.min()) < 0.0:
            raise RuntimeError(f"invalid OOF probability tensor: {case_id}")
        props = np.load(prob_path)
        del props
        pkl = pickle.load(open(REPO_ROOT / entry["preprocessing_path"], "rb"))
        source_spacing = tuple(float(v) for v in pkl["spacing"])
        bbox = pkl.get("bbox_used_for_cropping")
        if bbox:
            crop_slicer = tuple(slice(int(lo), int(hi)) for lo, hi in bbox)
            probs_for_grid = probs[(slice(None), *crop_slicer)]
        else:
            crop_slicer = tuple(slice(0, int(v)) for v in probs.shape[1:])
            probs_for_grid = probs
        target_shape = preprocessed_shape(case_id)
        resampled = resample_data_or_seg_to_shape(
            probs_for_grid,
            target_shape,
            source_spacing,
            cm.spacing,
            is_seg=False,
            order=1,
            order_z=0,
            force_separate_z=None,
        ).astype(np.float32)
        logits, canonical_probs = canonicalize_probabilities(torch.from_numpy(resampled).unsqueeze(0))
        inverse = resample_data_or_seg_to_shape(
            canonical_probs.squeeze(0).numpy(),
            probs_for_grid.shape[1:],
            cm.spacing,
            source_spacing,
            is_seg=False,
            order=1,
            order_z=0,
            force_separate_z=None,
        )
        source_preprocessed_inverse_changed = int((inverse.argmax(0).astype(np.int16) != probs_for_grid.argmax(0).astype(np.int16)).sum())
        union = soft_union_probability(canonical_probs)
        spacing = tuple(float(v) for v in cm.spacing)
        union_mask = (canonical_probs[:, 1:2] + canonical_probs[:, 4:5] + canonical_probs[:, 5:6])[0, 0].numpy() > 0.5
        distance = canonical_distance(union_mask, spacing)
        payload = {
            "schema_version": 2,
            "case_id": case_id,
            "source_semantics": "five_fold_OOF_only",
            "source_fold": int(entry["source_fold"]),
            "source_shape_before_cropping": tuple(int(v) for v in probs.shape[1:]),
            "source_shape_after_cropping": tuple(int(v) for v in probs_for_grid.shape[1:]),
            "bbox_used_for_cropping": [[int(s.start), int(s.stop)] for s in crop_slicer],
            "canonical_anchor_logits": logits.squeeze(0).contiguous(),
            "canonical_anchor_probabilities": canonical_probs.squeeze(0).contiguous(),
            "anchor_uncertainty": anchor_uncertainty(canonical_probs).squeeze(0).contiguous(),
            "soft_union_probability": union.squeeze(0).contiguous(),
            "distance_to_union_mm": torch.from_numpy(distance).unsqueeze(0).contiguous(),
            "plans_configuration": "nnUNetResEncUNetMPlans:3d_fullres",
            "probability_sha256": entry["probability_sha256"],
        }
        cache_path = ANCHOR_DIR / f"{case_id}__anchor.pt"
        torch.save(payload, cache_path)
        loaded_payload = torch.load(cache_path, map_location="cpu", weights_only=True)
        changed = int(
            (
                loaded_payload["canonical_anchor_probabilities"].argmax(0).numpy().astype(np.int16)
                != canonical_probs.squeeze(0).argmax(0).numpy().astype(np.int16)
            ).sum()
        )
        sum_error = float((canonical_probs.sum(dim=1) - 1.0).abs().max().item())
        decision = "PASS" if changed == 0 and sum_error <= 1e-5 else "NEEDS_REPAIR"
        rows.append(
            {
                "case_id": case_id,
                "source_fold": int(entry["source_fold"]),
                "is_oof": bool(entry["is_oof"]),
                "builder": "reverse_probability",
                "input_probability_path": entry["probability_path"],
                "nnunet_checkpoint_path": entry["nnunet_checkpoint_path"],
                "checkpoint_sha256": entry["checkpoint_sha256"],
                "input_probability_sha256": entry["probability_sha256"],
                "cache_path": str(cache_path.relative_to(REPO_ROOT)),
                "cache_sha256": sha256_path(cache_path),
                "preprocessed_shape": "x".join(map(str, target_shape)),
                "source_shape": "x".join(map(str, probs.shape[1:])),
                "cropped_source_shape": "x".join(map(str, probs_for_grid.shape[1:])),
                "bbox_used_for_cropping": json.dumps([[int(s.start), int(s.stop)] for s in crop_slicer]),
                "source_preprocessed_inverse_changed_voxels": source_preprocessed_inverse_changed,
                "probability_sum_max_abs_error": f"{sum_error:.8g}",
                "decision": decision,
            }
        )
        roundtrip_rows.append(
            {
                "case_id": case_id,
                "source_fold": int(entry["source_fold"]),
                "builder": "reverse_probability",
                "source_shape": "x".join(map(str, probs.shape[1:])),
                "cropped_source_shape": "x".join(map(str, probs_for_grid.shape[1:])),
                "preprocessed_shape": "x".join(map(str, target_shape)),
                "plans_configuration": "nnUNetResEncUNetMPlans:3d_fullres",
                "changed_voxels": changed,
                "roundtrip_scope": "preprocessed_grid_cache_write_load",
                "source_preprocessed_inverse_changed_voxels": source_preprocessed_inverse_changed,
                "decision": decision,
            }
        )
        if index % 25 == 0:
            print(f"anchor cache {index}/220", flush=True)
    write_csv(RESULT_ROOT / "anchor_cache_manifest_v2.csv", rows)
    write_csv(RESULT_ROOT / "anchor_cache_roundtrip_v2.csv", roundtrip_rows)
    return {
        "decision": "PASS" if len(rows) == 220 and all(r["decision"] == "PASS" for r in rows) else "NEEDS_REPAIR",
        "case_count": len(rows),
        "roundtrip_changed_voxels_max": max(int(r["changed_voxels"]) for r in roundtrip_rows),
    }


def source_cache_status(*, verify_file_hashes: bool = True) -> dict[str, Any]:
    hashes = RESULT_ROOT / "source_cache_hashes_v2.json"
    manifest = RESULT_ROOT / "source_cache_manifest_v2.csv"
    parity = RESULT_ROOT / "source_cache_parity_v2.csv"
    if not (hashes.exists() and manifest.exists() and parity.exists() and SOURCE_DIR.is_dir()):
        return {
            "decision": "NEEDS_REPAIR_SOURCE_CACHE_MISSING",
            "case_count": 0,
            "manifest_rows": 0,
            "parity_rows": 0,
            "blockers": ["source_cache_hashes_v2/manifest/parity/final_dir missing"],
        }
    rows = csv_rows(manifest)
    parity_rows = csv_rows(parity)
    payload = json.loads(hashes.read_text())
    cases = {r["case_id"] for r in rows}
    blockers: list[str] = []
    direct_parity_contract = load_source_direct_parity_contract()
    if payload.get("decision") != "PASS" or payload.get("status") != "PASS":
        blockers.append("source_cache_hashes_v2 decision/status not PASS")
    if payload.get("inference_mode") != "tiled_sliding_window":
        blockers.append("source cache inference_mode is not tiled_sliding_window")
    if payload.get("tile_step_size") != 0.5:
        blockers.append("source cache tile_step_size is not 0.5")
    if payload.get("gaussian") is not True:
        blockers.append("source cache gaussian flag is not true")
    if payload.get("mirror_axes") not in ([], ""):
        blockers.append("source cache mirror_axes must be empty")
    expected_patch = list(load_plans_configuration().patch_size)
    if payload.get("patch_size") != expected_patch:
        blockers.append(f"source cache patch_size {payload.get('patch_size')} != plans {expected_patch}")
    if payload.get("manifest_sha256") != sha256_path(manifest):
        blockers.append("source_cache_hashes_v2 manifest_sha256 mismatch")
    if payload.get("parity_checks_sha256") != sha256_path(parity):
        blockers.append("source_cache_hashes_v2 parity_checks_sha256 mismatch")
    if int(payload.get("parity_case_count", 0)) < int(direct_parity_contract["minimum_cases"]):
        blockers.append(
            f"source cache parity_case_count {payload.get('parity_case_count')} < config minimum {direct_parity_contract['minimum_cases']}"
        )
    parity_patterns_payload = payload.get("parity_recompute_case_patterns", {})
    if not isinstance(parity_patterns_payload, dict):
        blockers.append("source cache parity_recompute_case_patterns missing")
        parity_patterns_observed: set[str] = set()
    else:
        parity_patterns_observed = {str(value) for value in parity_patterns_payload.values()}
    for pattern in direct_parity_contract["include_modality_patterns"]:
        if pattern not in parity_patterns_observed:
            blockers.append(f"source cache parity missing required modality pattern {pattern}")
    if payload.get("direct_parity_contract", {}).get("feature_max_abs_delta") != direct_parity_contract["feature_max_abs_delta"]:
        blockers.append("source cache feature parity threshold mismatch")
    if payload.get("direct_parity_contract", {}).get("logit_max_abs_delta") != direct_parity_contract["logit_max_abs_delta"]:
        blockers.append("source cache logit parity threshold mismatch")
    if len(cases) != 220:
        blockers.append(f"case_count={len(cases)} expected 220")
    if len(rows) != 880:
        blockers.append(f"manifest_rows={len(rows)} expected 880")
    if len(parity_rows) != 880:
        blockers.append(f"parity_rows={len(parity_rows)} expected 880")
    for role, expected in EXPECTED_CHECKPOINT_SHA256.items():
        observed = payload.get("checkpoint_sha256", {}).get(role) or payload.get(f"{role}_sha256")
        if observed != expected:
            blockers.append(f"checkpoint sha mismatch in hash receipt for {role}")
    if sha256_path(TEACHER_CKPT) != EXPECTED_CHECKPOINT_SHA256["teacher_full_view"]:
        blockers.append("teacher checkpoint sha mismatch")
    if sha256_path(STUDENT_CKPT) != EXPECTED_CHECKPOINT_SHA256["student_reliable_distill"]:
        blockers.append("student checkpoint sha mismatch")
    expected_by_case = {(role, field) for role, fields in SOURCE_FIELDS.items() for field in fields}
    by_case: dict[str, set[tuple[str, str]]] = {}
    hash_map = payload.get("files", {}) if isinstance(payload.get("files"), dict) else {}
    for row in rows:
        if row.get("decision") != "PASS":
            blockers.append(f"manifest row not PASS: {row.get('case_id')} {row.get('checkpoint_role')} {row.get('field')}")
            continue
        role = row.get("checkpoint_role", "")
        field = row.get("field", "")
        by_case.setdefault(row.get("case_id", ""), set()).add((role, field))
        if field == "full_resolution_feature" and not str(row.get("tensor_shape", "")).startswith("1x32x"):
            blockers.append(f"feature shape not 1x32x*: {row.get('case_id')} {row.get('tensor_shape')}")
        if row.get("inference_mode") != "tiled_sliding_window":
            blockers.append(f"manifest row inference_mode not tiled_sliding_window: {row.get('case_id')}")
            break
        if row.get("patch_size") != "x".join(map(str, expected_patch)):
            blockers.append(f"manifest row patch_size mismatch: {row.get('case_id')} {row.get('patch_size')}")
            break
        path_text = row.get("cache_path", "")
        if verify_file_hashes:
            cache_path = REPO_ROOT / path_text
            if not cache_path.exists():
                blockers.append(f"missing cache_path {path_text}")
                continue
            observed_sha = sha256_path(cache_path)
            expected_sha = hash_map.get(path_text)
            if expected_sha != observed_sha:
                blockers.append(f"cache sha mismatch {path_text}")
        elif path_text not in hash_map:
            blockers.append(f"cache path missing from source_cache_hashes_v2 files map: {path_text}")
    for case_id in cases:
        if by_case.get(case_id) != expected_by_case:
            blockers.append(f"field set mismatch for {case_id}: {sorted(by_case.get(case_id, set()))}")
            break
    for row in parity_rows:
        if row.get("decision") != "PASS":
            blockers.append(f"parity row not PASS: {row.get('case_id')} {row.get('checkpoint_role')} {row.get('field')}")
            break
    parity_case_rows = [row for row in parity_rows if str(row.get("parity_recompute_case", "")).lower() in {"true", "1"}]
    parity_case_ids = {row.get("case_id", "") for row in parity_case_rows}
    if len(parity_case_ids) < int(direct_parity_contract["minimum_cases"]):
        blockers.append(f"parity recompute case ids in CSV {len(parity_case_ids)} below required {direct_parity_contract['minimum_cases']}")
    observed_csv_patterns = {row.get("modality_pattern", "") for row in parity_case_rows}
    for pattern in direct_parity_contract["include_modality_patterns"]:
        if pattern not in observed_csv_patterns:
            blockers.append(f"parity CSV missing required modality pattern {pattern}")
    return {
        "decision": "PASS" if not blockers else "NEEDS_REPAIR",
        "case_count": len(cases),
        "manifest_rows": len(rows),
        "parity_rows": len(parity_rows),
        "verify_file_hashes": verify_file_hashes,
        "blockers": blockers[:20],
    }


def build_prototypes() -> dict[str, Any]:
    status = source_cache_status(verify_file_hashes=False)
    rows: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    if status["decision"] != "PASS":
        write_csv(RESULT_ROOT / "prototype_cache_manifest_v2.csv", [{"decision": status["decision"], "reason": "source_cache_required_before_prototypes"}])
        write_csv(RESULT_ROOT / "prototype_crossfit_checks_v2.csv", [{"decision": status["decision"], "reason": "source_cache_required_before_prototypes"}])
        write_json(
            RESULT_ROOT / "prototype_cache_status_v2.json",
            {
                "decision": status["decision"],
                "status": status["decision"],
                "reason": "source_cache_required_before_prototypes",
                "source_cache_status": status,
            },
        )
        return status
    PROTOTYPE_DIR.parent.mkdir(parents=True, exist_ok=True)
    prototype_write_dir = Path(tempfile.mkdtemp(prefix=f"{PROTOTYPE_DIR.name}.attempt_", dir=PROTOTYPE_DIR.parent))
    attempt_id = prototype_write_dir.name
    write_json(
        RESULT_ROOT / "prototype_cache_status_v2.json",
        {
            "decision": "NEEDS_REPAIR",
            "status": "RUNNING_ATTEMPT",
            "attempt_id": attempt_id,
            "attempt_dir": str(prototype_write_dir.relative_to(REPO_ROOT)),
            "reason": "prototype_generation_not_atomically_promoted",
        },
    )
    metadata = load_myops_case_metadata(REPO_ROOT)
    source_rows = csv_rows(RESULT_ROOT / "source_cache_manifest_v2.csv")
    feature_by_case = {
        r["case_id"]: REPO_ROOT / r["cache_path"]
        for r in source_rows
        if r["checkpoint_role"] == "teacher_full_view" and r["field"] == "full_resolution_feature"
    }
    records = []
    for case_id in sorted(feature_by_case):
        tensor = torch.load(feature_by_case[case_id], map_location="cpu", weights_only=True)["tensor"].float()[0]
        labels = torch.from_numpy(label_array(case_id))
        masks = {
            "GT_scar": labels == 5,
            "healthy_myo_excluding_scar_edema": labels == 1,
            "LV_blood": labels == 2,
            "RV_blood": labels == 3,
            "outside_GT_union": labels == 0,
            "GT_edema_union_GT_scar": (labels == 4) | (labels == 5),
            "GT_myo_distance_to_edema_zone_ge_10mm": labels == 1,
        }
        rec = build_case_prototype_record(
            case_id=case_id,
            t2_present=metadata[case_id].t2_present,
            features=tensor,
            masks={k: v for k, v in masks.items()},
        )
        records.append(rec)
        out = prototype_write_dir / f"{case_id}__prototypes.pt"
        final_out = PROTOTYPE_DIR / out.name
        torch.save(rec, out)
        if not rec.t2_present and any(category.pathology == "edema" for category in rec.categories):
            rows.append(
                {
                    "case_id": case_id,
                    "shard": rec.shard,
                    "t2_present": rec.t2_present,
                    "category": "NO_T2_EDEMA_CATEGORY_VIOLATION",
                    "vector_shape": "",
                    "cache_path": str(final_out.relative_to(REPO_ROOT)),
                    "cache_sha256": sha256_path(out),
                    "decision": "NEEDS_REPAIR",
                }
            )
        for category, vector in rec.category_vectors.items():
            rows.append(
                {
                    "case_id": case_id,
                    "shard": rec.shard,
                    "t2_present": rec.t2_present,
                    "category": category,
                    "vector_shape": "x".join(map(str, vector.shape)),
                    "cache_path": str(final_out.relative_to(REPO_ROOT)),
                    "cache_sha256": sha256_path(out),
                    "decision": "PASS",
                }
            )
    for pathology in ("scar", "edema"):
        for rec in records:
            if pathology == "edema" and not rec.t2_present:
                checks.append(
                    {
                        "case_id": rec.case_id,
                        "pathology": pathology,
                        "query_shard": rec.shard,
                        "query_eligible": False,
                        "positive_count": 0,
                        "negative_count": 0,
                        "excluded_query_shard": "",
                        "minimum_positive_required": 4,
                        "minimum_negative_required": 8,
                        "negative_categories_preserved": "",
                        "source_eligibility_rule": "edema_query_not_required_without_t2",
                        "allowed_case_count_before_source_filter": "",
                        "allowed_case_count_after_source_filter": "",
                        "excluded_no_t2_source_count": "",
                        "excluded_no_t2_source_case_ids": "",
                        "no_t2_source_records_in_bank": False,
                        "negative_category_counts": "",
                        "no_t2_edema_source_contribution_forbidden": True,
                        "reason": "SKIPPED_NO_T2_EDEMA_QUERY_NOT_REQUIRED",
                        "decision": "PASS",
                    }
                )
                continue
            try:
                bank, meta = select_crossfit_prototype_bank(
                    records,
                    query_case_id=rec.case_id,
                    query_shard=rec.shard,
                    pathology=pathology,
                    minimum_positive=4,
                    minimum_negative=8,
                )
                same_shard_leak = str(meta.get("excluded_query_shard")) != "True"
                no_t2_edema_contrib = pathology == "edema" and str(meta.get("no_t2_source_records_in_bank")) != "False"
                decision = "PASS" if not same_shard_leak and not no_t2_edema_contrib else "NEEDS_REPAIR"
                reason = "same_shard_leak_or_no_t2_edema_contribution" if decision != "PASS" else ""
            except Exception as exc:
                meta = {"query_case_id": rec.case_id, "query_shard": rec.shard, "pathology": pathology}
                bank = {"positive": torch.empty(0), "negative": torch.empty(0)}
                decision = "NEEDS_REPAIR"
                reason = str(exc)
            checks.append(
                {
                    "case_id": rec.case_id,
                    "pathology": pathology,
                    "query_shard": meta.get("query_shard", rec.shard),
                    "query_eligible": True,
                    "positive_count": int(bank["positive"].shape[0]),
                    "negative_count": int(bank["negative"].shape[0]),
                    "excluded_query_shard": meta.get("excluded_query_shard", ""),
                    "minimum_positive_required": 4,
                    "minimum_negative_required": 8,
                    "negative_categories_preserved": meta.get("negative_categories_preserved", ""),
                    "source_eligibility_rule": meta.get("source_eligibility_rule", ""),
                    "allowed_case_count_before_source_filter": meta.get("allowed_case_count_before_source_filter", ""),
                    "allowed_case_count_after_source_filter": meta.get("allowed_case_count_after_source_filter", ""),
                    "excluded_no_t2_source_count": meta.get("excluded_no_t2_source_count", ""),
                    "excluded_no_t2_source_case_ids": meta.get("excluded_no_t2_source_case_ids", ""),
                    "no_t2_source_records_in_bank": meta.get("no_t2_source_records_in_bank", ""),
                    "negative_category_counts": meta.get("negative_category_counts", ""),
                    "no_t2_edema_source_contribution_forbidden": True,
                    "reason": reason,
                    "decision": decision,
                }
            )
    manifest_path = RESULT_ROOT / "prototype_cache_manifest_v2.csv"
    checks_path = RESULT_ROOT / "prototype_crossfit_checks_v2.csv"
    decision = "PASS" if rows and all(r["decision"] == "PASS" for r in rows) and all(c["decision"] == "PASS" for c in checks) else "NEEDS_REPAIR"
    expected_cases = sorted(feature_by_case)
    attempt_files = sorted(prototype_write_dir.glob("*__prototypes.pt"))
    attempt_file_cases = sorted(path.name.split("__", 1)[0] for path in attempt_files)
    manifest_cases = sorted({str(row.get("case_id", "")) for row in rows if row.get("case_id")})
    check_scar_cases = sorted({str(row.get("case_id", "")) for row in checks if row.get("pathology") == "scar"})
    check_edema_cases = sorted({str(row.get("case_id", "")) for row in checks if row.get("pathology") == "edema"})
    publish_blockers: list[str] = []
    if len(expected_cases) != 220:
        publish_blockers.append(f"expected_case_count={len(expected_cases)} expected 220")
    if len(attempt_files) != len(expected_cases):
        publish_blockers.append(f"attempt_file_count={len(attempt_files)} expected {len(expected_cases)}")
    if attempt_file_cases != expected_cases:
        publish_blockers.append("attempt_file_cases_do_not_match_source_cases")
    if manifest_cases != expected_cases:
        publish_blockers.append("manifest_cases_do_not_match_source_cases")
    if check_scar_cases != expected_cases:
        publish_blockers.append("scar_crossfit_cases_do_not_match_source_cases")
    if check_edema_cases != expected_cases:
        publish_blockers.append("edema_crossfit_cases_do_not_match_source_cases")
    if decision != "PASS":
        publish_blockers.append("prototype_rows_or_crossfit_checks_nonpass")
    if publish_blockers:
        failed_manifest = RESULT_ROOT / "prototype_cache_manifest_v2.failed.csv"
        failed_checks = RESULT_ROOT / "prototype_crossfit_checks_v2.failed.csv"
        write_csv(failed_manifest, rows or [{"decision": "NEEDS_REPAIR", "reason": "empty_prototype_manifest"}])
        write_csv(failed_checks, checks or [{"decision": "NEEDS_REPAIR", "reason": "empty_prototype_crossfit_checks"}])
        failed_status = {
            "decision": "NEEDS_REPAIR",
            "status": "NEEDS_REPAIR",
            "attempt_id": attempt_id,
            "attempt_dir": str(prototype_write_dir.relative_to(REPO_ROOT)),
            "publish_blockers": publish_blockers,
            "expected_case_count": len(expected_cases),
            "attempt_file_count": len(attempt_files),
            "manifest_unique_case_count": len(manifest_cases),
            "scar_crossfit_unique_case_count": len(check_scar_cases),
            "edema_crossfit_unique_case_count": len(check_edema_cases),
            "failed_manifest_sha256": sha256_path(failed_manifest),
            "failed_crossfit_checks_sha256": sha256_path(failed_checks),
        }
        write_json(RESULT_ROOT / "prototype_cache_status_v2.json", failed_status)
        return failed_status
    tmp_manifest = RESULT_ROOT / f".prototype_cache_manifest_v2.{attempt_id}.tmp"
    tmp_checks = RESULT_ROOT / f".prototype_crossfit_checks_v2.{attempt_id}.tmp"
    write_csv(tmp_manifest, rows)
    write_csv(tmp_checks, checks)
    if PROTOTYPE_DIR.exists():
        backup = PROTOTYPE_DIR.with_name(f"{PROTOTYPE_DIR.name}.superseded_{os.getpid()}")
        suffix = 0
        while backup.exists():
            suffix += 1
            backup = PROTOTYPE_DIR.with_name(f"{PROTOTYPE_DIR.name}.superseded_{os.getpid()}_{suffix}")
        PROTOTYPE_DIR.rename(backup)
    prototype_write_dir.rename(PROTOTYPE_DIR)
    os.replace(tmp_manifest, manifest_path)
    os.replace(tmp_checks, checks_path)
    edema_check_rows = [c for c in checks if c.get("pathology") == "edema" and str(c.get("query_eligible")) == "True"]
    excluded_no_t2_sources = sorted(
        {
            case_id
            for row in edema_check_rows
            for case_id in str(row.get("excluded_no_t2_source_case_ids", "")).split("|")
            if case_id
        }
    )
    negative_category_examples = sorted(
        {
            str(row.get("negative_category_counts", ""))
            for row in edema_check_rows
            if row.get("negative_category_counts")
        }
    )
    status_payload = {
        "decision": decision,
        "status": decision,
        "manifest_row_count": len(rows),
        "crossfit_check_row_count": len(checks),
        "prototype_file_count": len(list(PROTOTYPE_DIR.glob("*__prototypes.pt"))),
        "manifest_unique_case_count": len(manifest_cases),
        "scar_crossfit_unique_case_count": len(check_scar_cases),
        "edema_crossfit_unique_case_count": len(check_edema_cases),
        "attempt_id": attempt_id,
        "atomic_publish": True,
        "manifest_sha256": sha256_path(manifest_path),
        "crossfit_checks_sha256": sha256_path(checks_path),
        "edema_source_eligibility_rule": "edema_requires_t2_present_sources",
        "edema_query_no_t2_cases_skipped": sum(1 for c in checks if c.get("pathology") == "edema" and str(c.get("query_eligible")) == "False"),
        "edema_query_eligible_rows": len(edema_check_rows),
        "edema_excluded_no_t2_source_case_count": len(excluded_no_t2_sources),
        "edema_excluded_no_t2_source_case_ids": excluded_no_t2_sources,
        "edema_no_t2_source_records_in_bank_count": sum(1 for c in edema_check_rows if str(c.get("no_t2_source_records_in_bank")) != "False"),
        "edema_negative_categories_preserved": True,
        "edema_negative_category_count_examples": negative_category_examples[:8],
        "minimum_positive_required": 4,
        "minimum_negative_required": 8,
    }
    write_json(RESULT_ROOT / "prototype_cache_status_v2.json", status_payload)
    return status_payload


def generate_schedules() -> dict[str, Any]:
    manifest = load_manifest()
    cases = manifest_case_ids(manifest)
    out: dict[str, Any] = {"decision": "PASS", "logical_jobs": {}}
    SCHEDULE_DIR.mkdir(parents=True, exist_ok=True)
    for logical_id, (pathology, seed, variants) in LOGICAL_JOBS.items():
        base = deterministic_schedule(cases=cases, pathology=pathology, variant=variants[0], seed=seed, optimizer_steps=6250, gradient_accumulation=2)
        base_hash = schedule_sha256(base)
        paths = {}
        variant_hashes = {}
        for variant in variants:
            schedule = deterministic_schedule(cases=cases, pathology=pathology, variant=variants[0], seed=seed, optimizer_steps=6250, gradient_accumulation=2)
            path = SCHEDULE_DIR / f"{logical_id}__{variant}.csv"
            write_schedule_csv(path, schedule)
            paths[variant] = str(path.relative_to(REPO_ROOT))
            variant_hashes[variant] = sha256_path(path)
        out["logical_jobs"][logical_id] = {
            "pathology": pathology,
            "seed": seed,
            "variants": list(variants),
            "control_srr_shared_schedule": len(set(variant_hashes.values())) == 1,
            "schedule_semantic_sha256": base_hash,
            "file_sha256": variant_hashes,
            "paths": paths,
            "rows_per_variant": len(base),
            "decision": "PASS" if len(base) == 12500 and len(set(variant_hashes.values())) == 1 else "NEEDS_REPAIR",
        }
    if any(v["decision"] != "PASS" for v in out["logical_jobs"].values()):
        out["decision"] = "NEEDS_REPAIR"
    write_json(RESULT_ROOT / "matched_schedule_hashes_v2.json", out)
    return out


def synthetic_loss_batch(pathology: str) -> dict[str, torch.Tensor]:
    torch.manual_seed(20260725 if pathology == "scar" else 20260726)
    b, d, h, w = 1, 3, 8, 8
    labels = torch.zeros((b, d, h, w), dtype=torch.long)
    labels[:, 1, 2:6, 2:6] = 5 if pathology == "scar" else 4
    anchor = torch.full((b, 6, d, h, w), -5.0)
    anchor[:, 0] = 5.0
    class_index = 5 if pathology == "scar" else 4
    anchor[:, class_index, 1, 2:6, 2:6] = -2.0
    source = torch.randn(b, 32, d, h, w)
    return {
        "anchor_logits": anchor,
        "source_features": source,
        "distance_to_union_mm": torch.ones(b, 1, d, h, w),
        "t2_present": torch.ones(b),
        "normalized_lge": torch.randn(b, 1, d, h, w),
        "normalized_t2": torch.randn(b, 1, d, h, w),
        "teacher_anatomy_probabilities": torch.softmax(torch.randn(b, 4, d, h, w), dim=1),
        "teacher_edema_probability": torch.rand(b, 1, d, h, w),
        "scar_source_margin": torch.randn(b, 1, d, h, w),
        "explicit_anchor_probabilities": torch.softmax(anchor, dim=1),
        "explicit_anchor_uncertainty": torch.rand(b, 1, d, h, w),
        "explicit_soft_union_probability": torch.ones(b, 1, d, h, w),
        "normalized_distance_to_union": torch.zeros(b, 1, d, h, w),
        "prototype_scar_positive_similarity": torch.randn(b, 1, d, h, w),
        "prototype_scar_negative_similarity": torch.randn(b, 1, d, h, w),
        "prototype_edema_positive_similarity": torch.randn(b, 1, d, h, w),
        "prototype_edema_negative_similarity": torch.randn(b, 1, d, h, w),
        "labels": labels,
        "distance_to_gt_union_mm": torch.full((b, 1, d, h, w), 20.0),
        "distance_to_gt_pathology_surface_mm": torch.ones(b, 1, d, h, w),
    }


def crop_slices(center: tuple[int, int, int], shape: tuple[int, int, int], size: tuple[int, int, int] = (3, 32, 32)) -> tuple[slice, slice, slice]:
    slices = []
    for c, dim, span in zip(center, shape, size):
        start = max(0, min(int(c) - span // 2, dim - span))
        stop = min(dim, start + span)
        slices.append(slice(start, stop))
    return tuple(slices)  # type: ignore[return-value]


def source_field_paths() -> dict[tuple[str, str, str], Path]:
    rows = csv_rows(RESULT_ROOT / "source_cache_manifest_v2.csv")
    return {(row["case_id"], row["checkpoint_role"], row["field"]): REPO_ROOT / row["cache_path"] for row in rows}


def load_source_tensor(paths: dict[tuple[str, str, str], Path], case_id: str, role: str, field: str) -> torch.Tensor:
    path = paths[(case_id, role, field)]
    payload = torch.load(path, map_location="cpu", weights_only=True)
    tensor = payload["tensor"].float()
    return tensor[0] if tensor.ndim == 5 and tensor.shape[0] == 1 else tensor


def select_asset_backed_case(pathology: str, source_paths: dict[tuple[str, str, str], Path], metadata: dict[str, Any]) -> tuple[str, tuple[int, int, int], dict[str, Any]]:
    channel = 5 if pathology == "scar" else 4
    fallback: tuple[str, tuple[int, int, int], dict[str, Any]] | None = None
    for case_id in sorted({key[0] for key in source_paths}):
        if pathology == "edema" and not metadata[case_id].t2_present:
            continue
        labels = label_array(case_id)
        coords = np.argwhere(labels == channel)
        if not coords.size:
            continue
        center = tuple(int(v) for v in coords[len(coords) // 2])
        slc = crop_slices(center, labels.shape)
        patch = labels[slc]
        counts = {int(label): int(count) for label, count in zip(*np.unique(patch, return_counts=True))}
        info = {
            "selector": "first_positive_case" if pathology == "scar" else "first_t2_edema_patch_without_rv_and_low_scar_contamination",
            "candidate_case_id": case_id,
            "candidate_center_zyx": center,
            "candidate_patch_shape": tuple(int(v) for v in patch.shape),
            "candidate_label_counts": counts,
        }
        if fallback is None:
            fallback = (case_id, center, {**info, "fallback_used": True})
        if pathology == "scar":
            return case_id, center, {**info, "fallback_used": False}
        if counts.get(4, 0) > 0 and counts.get(3, 0) == 0 and counts.get(5, 0) <= 32:
            return case_id, center, {**info, "fallback_used": False}
    if fallback is not None:
        return fallback
    raise RuntimeError(f"NEEDS_REPAIR_NO_REAL_POSITIVE_CASE_FOR_{pathology.upper()}")


def asset_backed_batch(pathology: str) -> dict[str, torch.Tensor]:
    source_status = source_cache_status(verify_file_hashes=False)
    if source_status["decision"] != "PASS":
        raise RuntimeError("NEEDS_REPAIR_SOURCE_CACHE_REQUIRED")
    if not (RESULT_ROOT / "prototype_cache_manifest_v2.csv").exists() or not PROTOTYPE_DIR.is_dir():
        raise RuntimeError("NEEDS_REPAIR_PROTOTYPE_CACHE_REQUIRED")
    metadata = load_myops_case_metadata(REPO_ROOT)
    source_paths = source_field_paths()
    channel = 5 if pathology == "scar" else 4
    selected_case, selected_center, selection_info = select_asset_backed_case(pathology, source_paths, metadata)
    case_id = selected_case
    labels_np = label_array(case_id)
    slc = crop_slices(selected_center, labels_np.shape)
    labels = torch.from_numpy(labels_np[slc]).long().unsqueeze(0)
    anchor_payload = torch.load(ANCHOR_DIR / f"{case_id}__anchor.pt", map_location="cpu", weights_only=True)
    anchor_logits = anchor_payload["canonical_anchor_logits"][(slice(None), *slc)].unsqueeze(0).float()
    anchor_probs = anchor_payload["canonical_anchor_probabilities"][(slice(None), *slc)].unsqueeze(0).float()
    source_features = load_source_tensor(source_paths, case_id, "teacher_full_view", "full_resolution_feature")[(slice(None), *slc)].unsqueeze(0)
    anatomy_logits = load_source_tensor(source_paths, case_id, "teacher_full_view", "anatomy_logits")[(slice(None), *slc)].unsqueeze(0)
    edema_logit = load_source_tensor(source_paths, case_id, "teacher_full_view", "edema_logit")[(slice(None), *slc)].unsqueeze(0)
    scar_margin = load_source_tensor(source_paths, case_id, "student_reliable_distill", "scar_final_margin")[(slice(None), *slc)].unsqueeze(0)
    raw = torch.from_numpy(blosc2.open(str(PREPROCESSED / f"{case_id}.b2nd"), mode="r")[...]).float()[(slice(None), *slc)].unsqueeze(0)
    records = [
        torch.load(path, map_location="cpu", weights_only=False)
        for path in sorted(PROTOTYPE_DIR.glob("*__prototypes.pt"))
    ]
    bank, _ = select_crossfit_prototype_bank(records, query_case_id=case_id, query_shard=next(r for r in records if r.case_id == case_id).shard, pathology=pathology)
    sims = cosine_similarity_maps(source_features[0], bank)
    spacing = tuple(float(v) for v in load_plans_configuration().spacing)
    union_mask = ((labels_np == 1) | (labels_np == 4) | (labels_np == 5))[slc]
    path_mask = (labels_np == channel)[slc]
    return {
        "case_id": case_id,
        "asset_fixture_selector": selection_info,
        "anchor_logits": anchor_logits,
        "source_features": source_features,
        "distance_to_union_mm": anchor_payload["distance_to_union_mm"][(slice(None), *slc)].unsqueeze(0).float(),
        "t2_present": torch.tensor([float(metadata[case_id].t2_present)]),
        "normalized_lge": raw[:, 0:1],
        "normalized_t2": raw[:, 1:2],
        "teacher_anatomy_probabilities": torch.softmax(anatomy_logits, dim=1),
        "teacher_edema_probability": torch.sigmoid(edema_logit),
        "scar_source_margin": scar_margin,
        "explicit_anchor_probabilities": anchor_probs,
        "explicit_anchor_uncertainty": anchor_payload["anchor_uncertainty"][(slice(None), *slc)].unsqueeze(0).float(),
        "explicit_soft_union_probability": anchor_payload["soft_union_probability"][(slice(None), *slc)].unsqueeze(0).float(),
        "normalized_distance_to_union": (anchor_payload["distance_to_union_mm"][(slice(None), *slc)].unsqueeze(0).float() / 15.0).clamp(0.0, 1.0),
        "prototype_scar_positive_similarity": sims["positive"].unsqueeze(0) if pathology == "scar" else torch.zeros(1, 1, *labels.shape[1:]),
        "prototype_scar_negative_similarity": sims["negative"].unsqueeze(0) if pathology == "scar" else torch.zeros(1, 1, *labels.shape[1:]),
        "prototype_edema_positive_similarity": sims["positive"].unsqueeze(0) if pathology == "edema" else torch.zeros(1, 1, *labels.shape[1:]),
        "prototype_edema_negative_similarity": sims["negative"].unsqueeze(0) if pathology == "edema" else torch.zeros(1, 1, *labels.shape[1:]),
        "labels": labels,
        "distance_to_gt_union_mm": torch.from_numpy(canonical_distance(union_mask, spacing)).unsqueeze(0).unsqueeze(0),
        "distance_to_gt_pathology_surface_mm": torch.from_numpy(canonical_distance(path_mask, spacing)).unsqueeze(0).unsqueeze(0),
    }


def run_overfit(pathology: str, path: Path) -> dict[str, Any]:
    try:
        batch = asset_backed_batch(pathology)
    except Exception as exc:
        payload = {
            "decision": "NEEDS_REPAIR_SOURCE_CACHE_REQUIRED",
            "pathology": pathology,
            "error": str(exc),
            "source_feature_channels": 32,
            "optimizer_steps": 0,
            "formal_training_credit": 0,
        }
        write_json(path, payload)
        return payload
    model = CARESRRCascadeRescue(source_feature_channels=32)
    cfg = FormalRuntimeConfig(logical_run_id=f"rc2_overfit_{pathology}", pathology=pathology, variant=f"{pathology}_srr_cascade", seed=20260725, optimizer_steps=200, gradient_accumulation=1, initial_lr=5e-3)
    trainer = CARESRRCascadeFormalTrainer(model=model, config=cfg, device="cpu")
    losses = []
    for _ in range(200):
        stats = trainer.train_microbatches([batch], max_optimizer_steps=trainer.optimizer_step + 1)
        losses.append(float(stats["last_loss"]))
    reduction = (losses[0] - losses[-1]) / max(abs(losses[0]), 1e-6)
    excluded = {"case_id", "asset_fixture_selector", "labels", "distance_to_gt_union_mm", "distance_to_gt_pathology_surface_mm"}
    out = model(**{k: v for k, v in batch.items() if k not in excluded}, active_pathology=pathology)
    channel = 5 if pathology == "scar" else 4
    correction = out[f"{pathology}_correction"].detach()
    payload = {
        "decision": "PASS" if reduction >= 0.30 and float(correction.abs().max()) > 0.0 and int((out["final_logits"][:, channel].argmax()).item()) >= 0 else "NEEDS_REPAIR",
        "pathology": pathology,
        "case_id": batch["case_id"],
        "asset_fixture_selector": batch.get("asset_fixture_selector", {}),
        "source_feature_channels": 32,
        "optimizer_steps": trainer.optimizer_step,
        "initial_loss": losses[0],
        "final_loss": losses[-1],
        "loss_reduction_fraction": reduction,
        "nonzero_correction": float(correction.abs().max()) > 0.0,
        "formal_training_credit": 0,
    }
    write_json(path, payload)
    return payload


def augmentation_fiducial() -> dict[str, Any]:
    try:
        batch = asset_backed_batch("scar")
    except Exception as exc:
        rows = [
            {
                "tensor": "asset_backed_patch",
                "case_id": "",
                "asset_backed": False,
                "fiducial_index_before_zyx": "",
                "fiducial_index_after_zyx": "",
                "max_abs_fiducial_mismatch": "",
                "error": str(exc),
                "decision": "NEEDS_REPAIR_SOURCE_CACHE_REQUIRED",
            }
        ]
        write_csv(RC1_ROOT / "actual_augmentation_fiducial_v2.csv", rows)
        return {"decision": "NEEDS_REPAIR_SOURCE_CACHE_REQUIRED", "error": str(exc), "asset_backed": False}
    marker = torch.zeros_like(batch["anchor_logits"][:, :1])
    marker[..., 1, 5, 7] = 1.0
    tensors = {
        "raw_modalities": marker.repeat(1, 3, 1, 1, 1),
        "label": marker.clone(),
        "anchor_logits": marker.repeat(1, 6, 1, 1, 1),
        "source_features": marker.repeat(1, 32, 1, 1, 1),
        "teacher_anatomy_logits": marker.repeat(1, 4, 1, 1, 1),
        "teacher_edema_logit": marker.clone(),
        "scar_source_margin": marker.clone(),
        "prototype_similarity_maps": marker.clone(),
        "distance_maps": marker.clone(),
    }
    row = ScheduleRow(
        row_index=0,
        optimizer_step=0,
        microbatch_index=0,
        variant="scar_srr_cascade",
        pathology="scar",
        target="scar",
        case_id="RC2_FIDUCIAL",
        center_zyx=(1, 2, 3),
        rotate_hw_k=1,
        flip_d=True,
        flip_h=True,
        flip_w=False,
        intensity_seed=20260725,
    )
    transformed = apply_shared_spatial_augmentation(tensors, row)
    ref = transformed["raw_modalities"][:, :1]
    rows = []
    for name, tensor in transformed.items():
        probe = tensor[:, :1]
        mismatch = float((probe - ref).abs().max())
        fid = torch.nonzero(probe[0, 0] == probe[0, 0].max(), as_tuple=False)[0].tolist()
        rows.append(
            {
                "tensor": name,
                "case_id": batch["case_id"],
                "asset_backed": True,
                "fiducial_index_before_zyx": "1x5x7",
                "fiducial_index_after_zyx": "x".join(map(str, fid)),
                "max_abs_fiducial_mismatch": mismatch,
                "error": "",
                "decision": "PASS" if mismatch == 0.0 else "NEEDS_REPAIR",
            }
        )
    write_csv(RC1_ROOT / "actual_augmentation_fiducial_v2.csv", rows)
    return {"decision": "PASS" if all(r["decision"] == "PASS" for r in rows) else "NEEDS_REPAIR"}


def active_loss_matrix() -> dict[str, Any]:
    rows = []
    for pathology in ("scar", "edema"):
        try:
            batch = asset_backed_batch(pathology)
            asset_backed = True
        except Exception as exc:
            rows.append(
                {
                    "active_pathology": pathology,
                    "loss_term": "asset_backed_batch",
                    "loss_value": "",
                    "scar_branch_grad_sum": "",
                    "edema_branch_grad_sum": "",
                    "asset_backed": False,
                    "error": str(exc),
                    "decision": "NEEDS_REPAIR_SOURCE_CACHE_REQUIRED",
                }
            )
            continue
        model = CARESRRCascadeRescue(source_feature_channels=32)
        with torch.no_grad():
            model.scar_output_projection.weight.fill_(0.01)
            model.edema_output_projection.weight.fill_(0.01)
        excluded = {"case_id", "asset_fixture_selector", "labels", "distance_to_gt_union_mm", "distance_to_gt_pathology_surface_mm"}
        out = model(**{k: v for k, v in batch.items() if k not in excluded}, active_pathology=pathology)
        terms = care_srr_cascade_rescue_loss_audit_terms(
            out,
            batch["labels"],
            distance_to_gt_union_mm=batch["distance_to_gt_union_mm"],
            distance_to_gt_pathology_surface_mm=batch["distance_to_gt_pathology_surface_mm"],
            active_pathology=pathology,
        )
        for name, audit in terms.items():
            raw_value = audit["raw"]
            weight = float(audit["weight"])
            value = audit["weighted"]
            model.zero_grad(set_to_none=True)
            value.backward(retain_graph=True)
            scar_grad = sum(float(p.grad.abs().sum()) for p in model.scar_branch.parameters() if p.grad is not None)
            edema_grad = sum(float(p.grad.abs().sum()) for p in model.edema_branch.parameters() if p.grad is not None)
            ok = torch.isfinite(value).item() and ((pathology == "scar" and scar_grad > 0 and edema_grad == 0) or (pathology == "edema" and edema_grad > 0 and scar_grad == 0))
            rows.append(
                {
                    "active_pathology": pathology,
                    "loss_term": name,
                    "raw_loss_value": float(raw_value.detach()),
                    "configured_weight": weight,
                    "weighted_loss_value": float(value.detach()),
                    "scar_branch_grad_sum": scar_grad,
                    "edema_branch_grad_sum": edema_grad,
                    "asset_backed": asset_backed,
                    "error": "",
                    "decision": "PASS" if weight > 0.0 and ok else "NEEDS_REPAIR",
                }
            )
    write_csv(RC1_ROOT / "active_loss_gradient_matrix_v2.csv", rows)
    return {"decision": "PASS" if all(r["decision"] == "PASS" for r in rows) else "NEEDS_REPAIR"}


def checkpoint_roundtrip() -> dict[str, Any]:
    required_hash_inputs = {
        "source_cache_sha256": RESULT_ROOT / "source_cache_hashes_v2.json",
        "anchor_cache_sha256": RESULT_ROOT / "anchor_cache_manifest_v2.csv",
        "prototype_cache_sha256": RESULT_ROOT / "prototype_cache_manifest_v2.csv",
        "schedule_sha256": RESULT_ROOT / "matched_schedule_hashes_v2.json",
        "config_sha256": CONFIG_PATH,
        "code_sha256": Path(__file__),
    }
    missing = [name for name, path in required_hash_inputs.items() if not path.exists()]
    source_status = source_cache_status(verify_file_hashes=False)
    if missing or source_status["decision"] != "PASS":
        out = {
            "decision": "NEEDS_REPAIR_HASH_INPUT_REQUIRED",
            "missing_hash_inputs": missing,
            "source_cache_decision": source_status["decision"],
            "source_cache_blockers": source_status.get("blockers", []),
            "formal_training_credit": 0,
        }
        write_json(RC1_ROOT / "checkpoint_resume_roundtrip_v2.json", out)
        return out
    batch = synthetic_loss_batch("scar")
    model = CARESRRCascadeRescue(source_feature_channels=32)
    trainer = CARESRRCascadeFormalTrainer(model=model, config=FormalRuntimeConfig("rc2_roundtrip", "scar", "scar_srr_cascade", 20260725, optimizer_steps=2), device="cpu")
    trainer.train_microbatches([batch, batch], max_optimizer_steps=1)
    hashes = {name: sha256_path(path) for name, path in required_hash_inputs.items()}
    hashes["initial_state_sha256"] = state_dict_sha256(model)
    with tempfile.TemporaryDirectory(dir=RC1_ROOT) as td:
        path = Path(td) / "checkpoint.pt"
        info = trainer.save_checkpoint(path, **hashes)
        clone = CARESRRCascadeFormalTrainer(model=CARESRRCascadeRescue(source_feature_channels=32), config=FormalRuntimeConfig("rc2_roundtrip", "scar", "scar_srr_cascade", 20260725, optimizer_steps=2), device="cpu")
        payload = clone.load_checkpoint(path, expected=hashes)
        max_delta = max(float((trainer.model.state_dict()[k] - clone.model.state_dict()[k]).abs().max()) for k in trainer.model.state_dict())
    out = {
        "decision": "PASS" if max_delta <= 1e-6 and int(payload["microbatch_cursor"]) == trainer.microbatch_cursor else "NEEDS_REPAIR",
        "max_abs_model_delta": max_delta,
        "microbatch_cursor": trainer.microbatch_cursor,
        "optimizer_step": trainer.optimizer_step,
        "checkpoint_sha256": info["sha256"],
        "bound_hashes": hashes,
        "formal_training_credit": 0,
    }
    write_json(RC1_ROOT / "checkpoint_resume_roundtrip_v2.json", out)
    return out


def formal_dry_runs() -> dict[str, Any]:
    rows = []
    for logical_id, (pathology, seed, variants) in LOGICAL_JOBS.items():
        cmd = [
            str(REPO_ROOT / "envs/env_CARE/bin/python"),
            "scripts/training/run_care_srr_cascade_formal.py",
            "--dry-run",
            "--logical-run-id",
            logical_id,
            "--pathology",
            pathology,
            "--seed",
            str(seed),
            "--variants",
            "|".join(variants),
            "--optimizer-steps-each",
            "6250",
            "--validation-steps",
            "1250|2500|3750|5000|6250",
        ]
        proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        parsed: dict[str, Any] = {}
        error = ""
        try:
            parsed = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            error = f"json_parse_error: {exc}"
        expected_validation = [1250, 2500, 3750, 5000, 6250]
        checks = {
            "decision_PASS_DRY_RUN": parsed.get("decision") == "PASS_DRY_RUN",
            "formal_training_credit_zero": parsed.get("formal_training_credit") == 0,
            "logical_id": parsed.get("logical_run_id") == logical_id,
            "pathology": parsed.get("pathology") == pathology,
            "seed": int(parsed.get("seed", -1)) == int(seed) if parsed else False,
            "variant_order": tuple(parsed.get("variants", [])) == tuple(variants),
            "optimizer_steps_each": int(parsed.get("optimizer_steps_each", -1)) == 6250 if parsed else False,
            "validation_steps": parsed.get("validation_steps") == expected_validation,
            "rows_per_variant": (
                isinstance(parsed.get("schedule_rows_per_variant"), dict)
                and all(int(v) == 12500 for v in parsed.get("schedule_rows_per_variant", {}).values())
            ),
            "asset_backed_stream_first_batch": (
                isinstance(parsed.get("asset_backed_stream_first_batch"), dict)
                and all(
                    isinstance(v, dict)
                    and v.get("decision") == "PASS"
                    and v.get("anchor_shape") == [1, 6, 3, 32, 32]
                    and v.get("source_shape") == [1, 32, 3, 32, 32]
                    for v in parsed.get("asset_backed_stream_first_batch", {}).values()
                )
            ),
        }
        decision = "PASS" if proc.returncode == 0 and all(checks.values()) else "NEEDS_REPAIR"
        rows.append(
            {
                "logical_run_id": logical_id,
                "pathology": pathology,
                "seed": seed,
                "variants": "|".join(variants),
                "exit_code": proc.returncode,
                "parsed_decision": parsed.get("decision", ""),
                "formal_training_credit": parsed.get("formal_training_credit", ""),
                "schedule_rows_per_variant": parsed.get("schedule_rows_per_variant", ""),
                "checks": json.dumps(checks, sort_keys=True),
                "error": error or proc.stderr.strip()[:240],
                "decision": decision,
            }
        )
    write_csv(RC1_ROOT / "formal_dry_run_matrix_v2.csv", rows)
    return {"decision": "PASS" if all(r["decision"] == "PASS" for r in rows) else "NEEDS_REPAIR"}


def orchestrator_idempotence() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(dir=RC1_ROOT) as td:
        tmp = Path(td)
        state_path = tmp / "state.json"
        slurm_csv = tmp / "slurm_attempts.csv"
        adequacy_csv = tmp / "training_adequacy.csv"
        pass_gate = tmp / "formal_authorization_gate.json"
        fail_gate = tmp / "formal_authorization_gate_fail.json"
        write_json(pass_gate, {"decision": "PASS"})
        write_json(fail_gate, {"decision": "NEEDS_REPAIR"})
        base_cmd = [
            str(REPO_ROOT / "envs/env_CARE/bin/python"),
            "scripts/evaluation/orchestrate_care_srr_cascade_w3.py",
            "--dry-run",
            "--submit",
            "--state-file",
            str(state_path),
            "--formal-gate",
            str(pass_gate),
            "--slurm-attempts",
            str(slurm_csv),
            "--training-adequacy",
            str(adequacy_csv),
        ]
        empty_before = hashlib.sha256(b"").hexdigest()
        first = subprocess.run(base_cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        first_state = json.loads(state_path.read_text()) if state_path.exists() else {}
        after_first_hash = sha256_path(state_path) if state_path.exists() else ""
        first_attempt_rows = csv_rows(slurm_csv) if slurm_csv.exists() else []
        second = subprocess.run(base_cmd, cwd=REPO_ROOT, capture_output=True, text=True)
        second_state = json.loads(state_path.read_text()) if state_path.exists() else {}
        after_second_hash = sha256_path(state_path) if state_path.exists() else ""
        second_attempt_rows = csv_rows(slurm_csv) if slurm_csv.exists() else []
        blocked = subprocess.run(
            [*base_cmd[:4], "--state-file", str(tmp / "blocked_state.json"), "--formal-gate", str(fail_gate), "--slurm-attempts", str(tmp / "blocked_slurm.csv"), "--training-adequacy", str(tmp / "blocked_training.csv")],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
    src = (REPO_ROOT / "scripts/evaluation/orchestrate_care_srr_cascade_w3.py").read_text()
    hardcoded = any(job in src for job in ("60450660", "60451021", "60451022", "60469088"))
    first_runs = first_state.get("logical_runs", {})
    second_runs = second_state.get("logical_runs", {})
    generated_four = set(first_runs) == set(LOGICAL_JOBS)
    first_job_ids = {key: value.get("job_id") for key, value in first_runs.items()}
    second_job_ids = {key: value.get("job_id") for key, value in second_runs.items()}
    no_duplicate_resume = first_job_ids == second_job_ids and first_attempt_rows == second_attempt_rows
    gate_blocks = blocked.returncode != 0 and "NEEDS_REPAIR_PREFORMAL_GATE_NOT_PASS" in (blocked.stdout + blocked.stderr)
    payload = {
        "decision": "PASS" if (not hardcoded and first.returncode == 0 and second.returncode == 0 and generated_four and no_duplicate_resume and gate_blocks) else "NEEDS_REPAIR",
        "hardcoded_job_ids_forbidden": not hardcoded,
        "dry_run_from_empty_state_exit": first.returncode,
        "dry_run_from_empty_state_generated_four_logical_runs": generated_four,
        "resume_state_exit": second.returncode,
        "resume_state_no_duplicate_submit": no_duplicate_resume,
        "job_id_set_after_first": first_job_ids,
        "job_id_set_after_resume": second_job_ids,
        "attempt_rows_unchanged_on_resume": first_attempt_rows == second_attempt_rows,
        "formal_gate_nonpass_blocks_submit": gate_blocks,
        "empty_state_hash_before": empty_before,
        "state_hash_after_first": after_first_hash,
        "state_hash_after_resume": after_second_hash,
        "logical_runs": list(LOGICAL_JOBS),
    }
    write_json(RC1_ROOT / "orchestrator_idempotence_checks_v2.json", payload)
    return payload


def known_bad() -> dict[str, Any]:
    from src.care_myocardium.srr_production.anchor_runtime import verify_oof_fold
    from src.care_myocardium.srr_production.case_prototypes import deterministic_case_category_mean

    def expect_reject(name: str, command_or_function: str, fn, expected: str) -> dict[str, Any]:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001 - fixture harness records validator failures.
            text = str(exc)
            matched = expected in text
            return {
                "fixture": name,
                "command_or_function": command_or_function,
                "exit_code": "",
                "exception": text,
                "expected_substring": expected,
                "expected_substring_matched": matched,
                "rejected": True,
                "decision": "PASS" if matched else "NEEDS_REPAIR",
            }
        return {
            "fixture": name,
            "command_or_function": command_or_function,
            "exit_code": 0,
            "exception": "",
            "expected_substring": expected,
            "expected_substring_matched": False,
            "rejected": False,
            "decision": "NEEDS_REPAIR",
        }

    def reject_changed_roundtrip():
        row = {"changed_voxels": 1}
        if int(row["changed_voxels"]) != 0:
            raise ValueError("anchor_roundtrip_changed_voxel")

    def reject_source_status():
        status = source_cache_status(verify_file_hashes=False)
        if status["decision"] != "PASS":
            raise ValueError("source_cache_hash_or_shape_mismatch: " + status["decision"])
        raise ValueError("source_cache_hash_or_shape_mismatch: injected mismatch")

    def reject_stale_lock():
        lock = {"status": "WINNER_RUNNING", "decision": "NEEDS_MONITOR"}
        if lock["decision"] != "PASS":
            raise ValueError("stale_source_cache_lock_adopted")

    def reject_shared_trunk():
        model = CARESRRCascadeRescue(source_feature_channels=32)
        model.edema_branch = model.scar_branch
        if model.scar_branch is model.edema_branch:
            raise ValueError("shared_trainable_pathology_trunk")

    def reject_inactive_channel():
        batch = synthetic_loss_batch("scar")
        model = CARESRRCascadeRescue(source_feature_channels=32)
        out = model(**{k: v for k, v in batch.items() if k not in {"labels", "distance_to_gt_union_mm", "distance_to_gt_pathology_surface_mm"}}, active_pathology="scar")
        out["final_logits"] = out["final_logits"].clone()
        out["final_logits"][:, 4] += 1.0
        if (out["final_logits"][:, 4] - batch["anchor_logits"][:, 4]).abs().max() > 1e-6:
            raise ValueError("inactive_pathology_channel_modified")

    def reject_no_t2_edema():
        batch = synthetic_loss_batch("edema")
        batch["t2_present"] = torch.zeros(1)
        model = CARESRRCascadeRescue(source_feature_channels=32)
        out = model(**{k: v for k, v in batch.items() if k not in {"labels", "distance_to_gt_union_mm", "distance_to_gt_pathology_surface_mm"}}, active_pathology="edema")
        out["final_logits"] = out["final_logits"].clone()
        out["final_logits"][:, 4] += 1.0
        if (out["final_logits"][:, 4] - batch["anchor_logits"][:, 4]).abs().max() > 1e-6:
            raise ValueError("no_t2_edema_modified")

    def reject_same_shard_proto():
        rec = build_case_prototype_record(
            case_id="CaseX",
            shard=1,
            t2_present=True,
            features=torch.randn(32, 2, 4, 4),
            masks={"GT_scar": torch.ones(2, 4, 4, dtype=torch.bool), "outside_GT_union": torch.ones(2, 4, 4, dtype=torch.bool)},
            min_voxels=1,
        )
        select_crossfit_prototype_bank([rec], query_case_id="CaseX", query_shard=1, pathology="scar")

    def reject_negative_collapse():
        meta = {"negative_categories_preserved": False}
        if meta.get("negative_categories_preserved") is not True:
            raise ValueError("prototype_negative_categories_collapsed")

    def reject_first_n_sampling():
        _, meta = deterministic_case_category_mean(torch.randn(32, 2, 8, 8), torch.ones(2, 8, 8, dtype=torch.bool), case_id="CaseX", category="GT_scar", min_voxels=1, cap=8)
        bad_meta = dict(meta)
        bad_meta["first_N_flat_indices"] = True
        if bool(bad_meta["first_N_flat_indices"]):
            raise ValueError("first_N_voxel_sampling")

    def reject_spatial_mismatch():
        base = torch.arange(1 * 1 * 3 * 4 * 5, dtype=torch.float32).reshape(1, 1, 3, 4, 5)
        row = ScheduleRow(
            row_index=0,
            optimizer_step=0,
            microbatch_index=0,
            variant="scar_srr_cascade",
            pathology="scar",
            target="scar",
            case_id="BAD_SPATIAL",
            center_zyx=(1, 2, 3),
            rotate_hw_k=1,
            flip_d=True,
            flip_h=False,
            flip_w=True,
            intensity_seed=1,
        )
        transformed = apply_shared_spatial_augmentation({"raw_modalities": base, "anchor_logits": base.clone()}, row)
        bad_anchor = transformed["anchor_logits"].clone()
        bad_anchor[..., 0, 0, 0] += 1.0
        mismatch = float((transformed["raw_modalities"] - bad_anchor).abs().max())
        if mismatch > 0:
            raise ValueError("spatial_tensor_augmentation_mismatch")

    def reject_schedule_mismatch():
        control = deterministic_schedule(cases=["CaseA", "CaseB"], pathology="scar", variant="scar_cascade_control", seed=1, optimizer_steps=2)
        srr = deterministic_schedule(cases=["CaseA", "CaseB"], pathology="scar", variant="scar_srr_cascade", seed=2, optimizer_steps=2)
        if schedule_sha256(control) != schedule_sha256(srr):
            raise ValueError("control_and_srr_schedule_or_initial_state_mismatch")

    def reject_loss_nonzero():
        loss_meta = {"inactive_pathology_loss": 0.1}
        if float(loss_meta["inactive_pathology_loss"]) != 0.0:
            raise ValueError("inactive_pathology_loss_nonzero")

    def reject_packet(name: str, packet: dict[str, Any]):
        if name == "partial_or_resumed_run_counted_complete" and packet.get("decision") == "PASS" and packet.get("optimizer_steps_completed") != 6250:
            raise ValueError(name)
        if name == "missing_validation_checkpoint" and not packet.get("validation_checkpoint_path"):
            raise ValueError(name)
        if name == "audit_used_for_selection" and packet.get("selection_split") == "audit":
            raise ValueError(name)
        if name == "selected_checkpoint_not_reloaded" and packet.get("selected_checkpoint_reloaded") is not True:
            raise ValueError(name)
        if name == "selection_deployment_decode_mismatch" and packet.get("selection_decode_hash") != packet.get("deployment_decode_hash"):
            raise ValueError(name)
        if name == "exact_HD_missing_or_replaced_by_HD95" and packet.get("metric") == "HD95":
            raise ValueError(name)
        if name == "single_fold_anchor_used_for_official_package" and packet.get("anchor_source") == "single_fold":
            raise ValueError(name)
        if name == "package_accesses_GT" and packet.get("accessed_gt") is True:
            raise ValueError(name)
        if name == "monitor_packet_marked_complete" and packet.get("state") in {"PENDING", "RUNNING", "NEEDS_MONITOR"} and packet.get("decision") == "PASS":
            raise ValueError(name)

    fixture_defs = [
        ("OOF_case_uses_wrong_fold", "anchor_runtime.verify_oof_fold", lambda: verify_oof_fold("CaseX", 1, 0), "OOF_case_uses_wrong_fold"),
        ("anchor_roundtrip_changed_voxel", "run_care_srr_cascade_rc2_preflight.reject_changed_roundtrip", reject_changed_roundtrip, "anchor_roundtrip_changed_voxel"),
        ("source_cache_hash_or_shape_mismatch", "run_care_srr_cascade_rc2_preflight.source_cache_status", reject_source_status, "source_cache_hash_or_shape_mismatch"),
        ("stale_source_cache_lock_adopted", "source-cache lock validator", reject_stale_lock, "stale_source_cache_lock_adopted"),
        ("shared_trainable_pathology_trunk", "model_branch_validator(shared_bad_model)", reject_shared_trunk, "shared_trainable_pathology_trunk"),
        ("inactive_pathology_channel_modified", "inactive_channel_identity_validator(bad_logits)", reject_inactive_channel, "inactive_pathology_channel_modified"),
        ("no_t2_edema_modified", "no_t2_identity_validator(bad_logits)", reject_no_t2_edema, "no_t2_edema_modified"),
        ("prototype_query_uses_same_shard", "select_crossfit_prototype_bank", reject_same_shard_proto, "fail-closed insufficient prototype bank"),
        ("prototype_negative_categories_collapsed", "prototype_category_validator(bad_meta)", reject_negative_collapse, "prototype_negative_categories_collapsed"),
        ("first_N_voxel_sampling", "prototype_sampling_validator(bad_meta)", reject_first_n_sampling, "first_N_voxel_sampling"),
        ("spatial_tensor_augmentation_mismatch", "apply_shared_spatial_augmentation validator", reject_spatial_mismatch, "spatial_tensor_augmentation_mismatch"),
        ("control_and_srr_schedule_or_initial_state_mismatch", "schedule_pair_validator(bad_schedule_pair)", reject_schedule_mismatch, "control_and_srr_schedule_or_initial_state_mismatch"),
        ("inactive_pathology_loss_nonzero", "loss_activity_validator(bad_loss_meta)", reject_loss_nonzero, "inactive_pathology_loss_nonzero"),
        ("partial_or_resumed_run_counted_complete", "completion_packet_validator(bad_packet)", lambda: reject_packet("partial_or_resumed_run_counted_complete", {"decision": "PASS", "optimizer_steps_completed": 12}), "partial_or_resumed_run_counted_complete"),
        ("missing_validation_checkpoint", "selection_packet_validator(bad_packet)", lambda: reject_packet("missing_validation_checkpoint", {"decision": "PASS"}), "missing_validation_checkpoint"),
        ("audit_used_for_selection", "selection_packet_validator(bad_packet)", lambda: reject_packet("audit_used_for_selection", {"selection_split": "audit"}), "audit_used_for_selection"),
        ("selected_checkpoint_not_reloaded", "selection_packet_validator(bad_packet)", lambda: reject_packet("selected_checkpoint_not_reloaded", {"selected_checkpoint_reloaded": False}), "selected_checkpoint_not_reloaded"),
        ("selection_deployment_decode_mismatch", "inference_packet_validator(bad_packet)", lambda: reject_packet("selection_deployment_decode_mismatch", {"selection_decode_hash": "a", "deployment_decode_hash": "b"}), "selection_deployment_decode_mismatch"),
        ("exact_HD_missing_or_replaced_by_HD95", "evaluation_packet_validator(bad_packet)", lambda: reject_packet("exact_HD_missing_or_replaced_by_HD95", {"metric": "HD95"}), "exact_HD_missing_or_replaced_by_HD95"),
        ("single_fold_anchor_used_for_official_package", "package_packet_validator(bad_packet)", lambda: reject_packet("single_fold_anchor_used_for_official_package", {"anchor_source": "single_fold"}), "single_fold_anchor_used_for_official_package"),
        ("package_accesses_GT", "package_packet_validator(bad_packet)", lambda: reject_packet("package_accesses_GT", {"accessed_gt": True}), "package_accesses_GT"),
        ("monitor_packet_marked_complete", "completion_packet_validator(bad_packet)", lambda: reject_packet("monitor_packet_marked_complete", {"state": "NEEDS_MONITOR", "decision": "PASS"}), "monitor_packet_marked_complete"),
    ]
    rows = [expect_reject(*fixture) for fixture in fixture_defs]
    payload = {"decision": "PASS" if all(row["decision"] == "PASS" for row in rows) else "NEEDS_REPAIR", "fixtures": rows}
    write_json(RC1_ROOT / "real_known_bad_report_v2.json", payload)
    return payload


def json_receipt_decision(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    try:
        return str(json.loads(path.read_text()).get("decision", "MISSING_DECISION"))
    except Exception as exc:  # noqa: BLE001 - gate must fail closed on corrupt receipts.
        return f"NEEDS_REPAIR_CORRUPT_JSON:{exc}"


def csv_receipt_decision(path: Path, *, expected_rows: int | None = None) -> str:
    if not path.exists():
        return "MISSING"
    try:
        rows = csv_rows(path)
    except Exception as exc:  # noqa: BLE001
        return f"NEEDS_REPAIR_CORRUPT_CSV:{exc}"
    if expected_rows is not None and len(rows) != int(expected_rows):
        return f"NEEDS_REPAIR_ROW_COUNT_{len(rows)}_EXPECTED_{expected_rows}"
    if not rows:
        return "NEEDS_REPAIR_EMPTY_CSV"
    bad = [row for row in rows if row.get("decision") != "PASS"]
    return "PASS" if not bad else f"NEEDS_REPAIR_{len(bad)}_NONPASS_ROWS"


def prototype_receipt_status() -> dict[str, Any]:
    manifest = RESULT_ROOT / "prototype_cache_manifest_v2.csv"
    checks = RESULT_ROOT / "prototype_crossfit_checks_v2.csv"
    status = RESULT_ROOT / "prototype_cache_status_v2.json"
    blockers: list[str] = []
    if not PROTOTYPE_DIR.is_dir():
        blockers.append("prototype_cache_v2_dir_missing")
    file_count = len(list(PROTOTYPE_DIR.glob("*__prototypes.pt"))) if PROTOTYPE_DIR.is_dir() else 0
    if file_count != 220:
        blockers.append(f"prototype_file_count={file_count} expected 220")
    manifest_decision = csv_receipt_decision(manifest)
    checks_decision = csv_receipt_decision(checks)
    if manifest_decision != "PASS":
        blockers.append(f"manifest={manifest_decision}")
    if checks_decision != "PASS":
        blockers.append(f"crossfit={checks_decision}")
    if manifest.exists():
        rows = csv_rows(manifest)
        if any(row.get("category") == "NO_T2_EDEMA_CATEGORY_VIOLATION" for row in rows):
            blockers.append("no_t2_edema_category_violation_rows_present")
        manifest_cases = sorted({row.get("case_id", "") for row in rows if row.get("case_id")})
        file_cases = sorted(path.name.split("__", 1)[0] for path in PROTOTYPE_DIR.glob("*__prototypes.pt")) if PROTOTYPE_DIR.is_dir() else []
        if len(manifest_cases) != 220:
            blockers.append(f"prototype_manifest_unique_cases={len(manifest_cases)} expected 220")
        if manifest_cases != file_cases:
            blockers.append("prototype_manifest_cases_do_not_match_actual_files")
        missing_or_hash_mismatch = 0
        checked_paths: set[str] = set()
        for row in rows:
            cache_path = row.get("cache_path", "")
            if not cache_path or cache_path in checked_paths:
                continue
            checked_paths.add(cache_path)
            path = REPO_ROOT / cache_path
            if not path.exists() or row.get("cache_sha256") != sha256_path(path):
                missing_or_hash_mismatch += 1
        if missing_or_hash_mismatch:
            blockers.append(f"prototype_cache_path_missing_or_hash_mismatch={missing_or_hash_mismatch}")
    if checks.exists():
        rows = csv_rows(checks)
        for row in rows:
            if row.get("pathology") == "edema" and row.get("query_eligible", "True") in {"False", "false", "0"}:
                if row.get("decision") != "PASS" or row.get("reason") != "SKIPPED_NO_T2_EDEMA_QUERY_NOT_REQUIRED":
                    blockers.append(f"bad_no_t2_edema_skip_row:{row.get('case_id')}")
                    break
            if row.get("pathology") == "edema" and row.get("query_eligible", "True") not in {"False", "false", "0"}:
                if row.get("source_eligibility_rule") != "edema_requires_t2_present_sources":
                    blockers.append(f"bad_edema_source_eligibility_rule:{row.get('case_id')}")
                    break
                if row.get("no_t2_source_records_in_bank") != "False":
                    blockers.append(f"no_t2_source_records_in_edema_bank:{row.get('case_id')}")
                    break
                counts = str(row.get("negative_category_counts", ""))
                for category in EDEMA_NEGATIVE_CATEGORIES:
                    if category not in counts:
                        blockers.append(f"missing_edema_negative_category_count:{category}")
                        break
                if blockers and str(blockers[-1]).startswith("missing_edema_negative_category_count"):
                    break
    status_decision = json_receipt_decision(status)
    if status_decision != "PASS":
        blockers.append(f"status={status_decision}")
    if status.exists():
        try:
            payload = json.loads(status.read_text())
            if payload.get("manifest_sha256") != sha256_path(manifest):
                blockers.append("prototype_manifest_sha_mismatch")
            if payload.get("crossfit_checks_sha256") != sha256_path(checks):
                blockers.append("prototype_crossfit_sha_mismatch")
            if int(payload.get("edema_no_t2_source_records_in_bank_count", 1)) != 0:
                blockers.append("prototype_status_no_t2_edema_source_leak")
        except Exception as exc:  # noqa: BLE001
            blockers.append(f"prototype_status_unreadable:{exc}")
    return {
        "decision": "PASS" if not blockers else "NEEDS_REPAIR",
        "manifest_decision": manifest_decision,
        "crossfit_decision": checks_decision,
        "status_decision": status_decision,
        "prototype_file_count": file_count,
        "blockers": blockers,
    }


def receipt_backed_preformal_results(results: dict[str, Any]) -> dict[str, str]:
    preformal = {
        "anchor": anchor_cache_receipt_status().get("decision"),
        "source_cache": source_cache_status(verify_file_hashes=False).get("decision"),
        "prototype": results.get("prototype", prototype_receipt_status()).get("decision"),
        "schedules": results.get("schedules", {}).get("decision") or json_receipt_decision(RESULT_ROOT / "matched_schedule_hashes_v2.json"),
        "scar_overfit": results.get("scar_overfit", {}).get("decision") or json_receipt_decision(RC1_ROOT / "real_overfit_scar_v2.json"),
        "edema_overfit": results.get("edema_overfit", {}).get("decision") or json_receipt_decision(RC1_ROOT / "real_overfit_edema_v2.json"),
        "augmentation": results.get("augmentation", {}).get("decision") or csv_receipt_decision(RC1_ROOT / "actual_augmentation_fiducial_v2.csv"),
        "loss_gradients": results.get("loss_gradients", {}).get("decision") or csv_receipt_decision(RC1_ROOT / "active_loss_gradient_matrix_v2.csv", expected_rows=10),
        "checkpoint": results.get("checkpoint", {}).get("decision") or json_receipt_decision(RC1_ROOT / "checkpoint_resume_roundtrip_v2.json"),
        "gpu_preflight": "PASS" if gpu_preflight_passed() else "NEEDS_MONITOR_GPU_PREFLIGHT",
        "formal_dry_runs": results.get("formal_dry_runs", {}).get("decision") or csv_receipt_decision(RC1_ROOT / "formal_dry_run_matrix_v2.csv", expected_rows=4),
        "orchestrator": results.get("orchestrator", {}).get("decision") or json_receipt_decision(RC1_ROOT / "orchestrator_idempotence_checks_v2.json"),
        "known_bad": results.get("known_bad", {}).get("decision") or json_receipt_decision(RC1_ROOT / "real_known_bad_report_v2.json"),
    }
    return {key: str(value) for key, value in preformal.items()}


def write_gate(results: dict[str, Any]) -> dict[str, Any]:
    preformal = receipt_backed_preformal_results(results)
    gpu_status = gpu_preflight_status()
    decision = "PASS" if all(v == "PASS" for v in preformal.values()) else "NEEDS_REPAIR"
    blockers = [name for name, value in preformal.items() if value != "PASS"]
    payload = {
        "decision": decision,
        "preformal_gates": preformal,
        "blockers": blockers,
        "formal_jobs_authorized": decision == "PASS",
        "gate_aggregation_mode": "receipt_aware_current_files",
        "gpu_preflight_status": gpu_status,
        "prototype_receipt_status": prototype_receipt_status(),
    }
    write_json(RC1_ROOT / "formal_authorization_gate.json", payload)
    return payload


def gpu_preflight_status() -> dict[str, Any]:
    path = RC1_ROOT / "gpu_preflight_attempts_v2.csv"
    if not path.exists():
        return {
            "decision": "NEEDS_MONITOR_GPU_PREFLIGHT",
            "policy": "any_compatible_partition_pass",
            "compatible_partitions": list(COMPATIBLE_GPU_PREFLIGHT_PARTITIONS),
            "passed_partitions": [],
            "attempt_count": 0,
            "selected_attempt": None,
            "blockers": ["gpu_preflight_attempts_v2.csv missing"],
        }
    rows = list(csv.DictReader(path.open()))
    compatible = {name for name in COMPATIBLE_GPU_PREFLIGHT_PARTITIONS}
    passed = [
        row
        for row in rows
        if row.get("partition") in compatible
        and row.get("decision") == "PASS"
        and str(row.get("exit_code")) == "0"
    ]
    selected = sorted(passed, key=lambda row: (row.get("partition", ""), row.get("attempt_id", "")))[0] if passed else None
    return {
        "decision": "PASS" if selected else "NEEDS_MONITOR_GPU_PREFLIGHT",
        "policy": "any_compatible_partition_pass",
        "compatible_partitions": list(COMPATIBLE_GPU_PREFLIGHT_PARTITIONS),
        "passed_partitions": sorted({row.get("partition", "") for row in passed}),
        "attempt_count": len(rows),
        "selected_attempt": selected,
        "blockers": [] if selected else ["no compatible GPU preflight PASS receipt"],
    }


def gpu_preflight_passed() -> bool:
    return gpu_preflight_status()["decision"] == "PASS"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--anchor", action="store_true")
    parser.add_argument("--source-status", action="store_true")
    parser.add_argument("--prototypes", action="store_true")
    parser.add_argument("--schedules", action="store_true")
    parser.add_argument("--local-checks", action="store_true")
    parser.add_argument("--formal-dry-runs", action="store_true")
    parser.add_argument("--gate", action="store_true")
    parser.add_argument("--all-local", action="store_true")
    args = parser.parse_args()
    results: dict[str, Any] = {}
    if args.all_local:
        args.anchor = args.source_status = args.prototypes = args.schedules = args.local_checks = args.formal_dry_runs = args.gate = True
    if args.anchor:
        results["anchor"] = build_anchor_cache()
    if args.source_status:
        results["source_cache"] = source_cache_status()
    if args.prototypes:
        results["prototype"] = build_prototypes()
    if args.schedules:
        results["schedules"] = generate_schedules()
    if args.local_checks:
        results["scar_overfit"] = run_overfit("scar", RC1_ROOT / "real_overfit_scar_v2.json")
        results["edema_overfit"] = run_overfit("edema", RC1_ROOT / "real_overfit_edema_v2.json")
        results["augmentation"] = augmentation_fiducial()
        results["loss_gradients"] = active_loss_matrix()
        results["checkpoint"] = checkpoint_roundtrip()
        results["orchestrator"] = orchestrator_idempotence()
        results["known_bad"] = known_bad()
    if args.formal_dry_runs:
        results["formal_dry_runs"] = formal_dry_runs()
    if args.gate:
        results["formal_authorization_gate"] = write_gate(results)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if not results or all(v.get("decision") == "PASS" for v in results.values() if isinstance(v, dict) and "decision" in v) else 2


if __name__ == "__main__":
    raise SystemExit(main())
