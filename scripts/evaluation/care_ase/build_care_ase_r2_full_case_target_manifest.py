#!/usr/bin/env python
"""Build lightweight full-case target-cache manifest for CARE-ASE R2 v9."""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_ase_splits import PREPROCESSED_REL, build_care_ase_case_roles, sha256_file
from src.care_myocardium.training.care_ase_trainer import build_full_case_target_cache


TASK_KEY = "20260803_care_ase_r2_last_hotfix_v9"


def sha256_array(array: np.ndarray) -> str:
    arr = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode("utf-8"))
    h.update(json.dumps(list(arr.shape)).encode("utf-8"))
    h.update(arr.tobytes())
    return h.hexdigest()


def json_sha(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def spacing_for_case(preprocessed: Path, case_id: str) -> tuple[float, float, float]:
    plans_path = preprocessed.parent / "nnUNetPlans.json"
    if plans_path.is_file():
        plans = json.loads(plans_path.read_text(encoding="utf-8"))
        return tuple(float(v) for v in plans["configurations"]["3d_fullres"]["spacing"])
    props_path = preprocessed / f"{case_id}.pkl"
    if props_path.is_file():
        with props_path.open("rb") as f:
            props = pickle.load(f)
        if "spacing" in props:
            return tuple(float(v) for v in props["spacing"])
    return (1.0, 1.0, 1.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    preprocessed = REPO_ROOT / PREPROCESSED_REL
    plans_path = preprocessed.parent / "nnUNetPlans.json"
    rows = [row for row in build_care_ase_case_roles(REPO_ROOT, int(args.fold)) if row.role == "actual-train"]
    cases: dict[str, Any] = {}
    for row in rows:
        seg_path = preprocessed / f"{row.case_id}_seg.b2nd"
        image_path = preprocessed / f"{row.case_id}.b2nd"
        properties_path = preprocessed / f"{row.case_id}.pkl"
        seg = np.asarray(blosc2.open(str(seg_path), mode="r")[:])[0].astype(np.int16, copy=False)
        spacing = spacing_for_case(preprocessed, row.case_id)
        cache = build_full_case_target_cache(seg, spacing)
        field_sha = {key: sha256_array(value) for key, value in sorted(cache.items()) if isinstance(value, np.ndarray)}
        cases[row.case_id] = {
            "case_id": row.case_id,
            "segmentation_path": str(seg_path.relative_to(REPO_ROOT)),
            "segmentation_sha256": sha256_file(seg_path),
            "image_path": str(image_path.relative_to(REPO_ROOT)),
            "image_sha256": sha256_file(image_path),
            "properties_path": str(properties_path.relative_to(REPO_ROOT)),
            "properties_sha256": sha256_file(properties_path) if properties_path.is_file() else "MISSING",
            "plans_path": str(plans_path.relative_to(REPO_ROOT)),
            "plans_sha256": sha256_file(plans_path),
            "shape_zyx": list(seg.shape),
            "spacing_zyx": list(spacing),
            "cache_schema": "care_ase_r2_v9_full_case_physical_target_cache",
            **{f"{key}_sha256": value for key, value in field_sha.items()},
            "valid_label_mask_sha256": field_sha["valid_label_mask"],
            "scar_component_id_sha256": field_sha["scar_component_id"],
            "scar_component_metadata_sha256": json_sha(
                {
                    "volume": field_sha["scar_component_volume_mm3"],
                    "center_z": field_sha["scar_component_center_z"],
                    "center_y": field_sha["scar_component_center_y"],
                    "center_x": field_sha["scar_component_center_x"],
                }
            ),
            "scar_center_fullres_sha256": field_sha["scar_center_fullres"],
            "scar_context_sha256": field_sha["scar_context_target"],
            "edema_context_sha256": field_sha["edema_context_target"],
            "signed_endo_distance_sha256": field_sha["signed_endo_distance"],
            "signed_epi_distance_sha256": field_sha["signed_epi_distance"],
            "wall_depth_rho_sha256": field_sha["wall_depth_rho"],
            "geometry_valid_sha256": field_sha["geometry_valid"],
            "edema_boundary_sha256": field_sha["edema_boundary"],
            "edema_boundary_raw_mm_sha256": field_sha["edema_boundary_raw_mm"],
            "edema_boundary_valid_sha256": field_sha["edema_boundary_valid"],
            "scar_extent_profile_sha256": json_sha(
                {
                    "presence": field_sha["scar_slice_presence"],
                    "pathology_voxels": field_sha["scar_slice_pathology_voxels"],
                    "wall_voxels": field_sha["scar_slice_wall_voxels"],
                    "area": field_sha["scar_slice_area"],
                    "area_valid": field_sha["scar_slice_area_valid"],
                }
            ),
            "edema_extent_profile_sha256": json_sha(
                {
                    "presence": field_sha["edema_slice_presence"],
                    "pathology_voxels": field_sha["edema_slice_pathology_voxels"],
                    "wall_voxels": field_sha["edema_slice_wall_voxels"],
                    "area": field_sha["edema_slice_area"],
                    "area_valid": field_sha["edema_slice_area_valid"],
                }
            ),
            "full_cache_payload_sha256": json_sha(field_sha),
        }
    payload = {
        "status": "PASS",
        "task_key": TASK_KEY,
        "schema_version": 1,
        "fold": int(args.fold),
        "case_count": len(cases),
        "cases": cases,
    }
    payload["payload_sha256"] = json_sha(payload)
    output = args.output or REPO_ROOT / "results" / TASK_KEY / f"full_case_target_cache_manifest_fold{args.fold}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output), "case_count": len(cases)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
