#!/usr/bin/env python3
"""Batch10 paired student/natural/teacher spatial fiducial audit."""

from __future__ import annotations

import csv
import json
import pickle
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_mm_batch9 import Batch9PatchSampler, PREPROCESSED, build_case_records, write_csv


TASK_KEY = "20260724_care_myops_batch10_deadline_rescue"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
PATCH_SIZE = (20, 128, 128)
MATCHED_SEED = 20260724
STEP = 3
VARIANTS = [
    "student_direct_reliable",
    "student_moddrop_control",
    "student_reliable_distill",
]


def read_props(case_id: str) -> dict[str, Any]:
    with (PREPROCESSED / f"{case_id}.pkl").open("rb") as f:
        return pickle.load(f)


def parse_bounds(text: str) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    parts = []
    for item in text.split(";"):
        lo, hi = item.split(":")
        parts.append((int(lo), int(hi)))
    if len(parts) != 3:
        raise ValueError(f"expected z/y/x patch bounds, got {text!r}")
    return parts[0], parts[1], parts[2]


def physical_xyz_mm(props: dict[str, Any], voxel_zyx: tuple[int, int, int]) -> tuple[float, float, float]:
    sitk = props.get("sitk_stuff") or {}
    spacing = np.asarray(sitk.get("spacing") or props.get("spacing")[::-1], dtype=np.float64)
    origin = np.asarray(sitk.get("origin") or (0.0, 0.0, 0.0), dtype=np.float64)
    direction = np.asarray(sitk.get("direction") or np.eye(3).reshape(-1), dtype=np.float64).reshape(3, 3)
    voxel_xyz = np.asarray([voxel_zyx[2], voxel_zyx[1], voxel_zyx[0]], dtype=np.float64)
    physical = origin + direction.dot(voxel_xyz * spacing)
    return tuple(float(v) for v in physical)


def sample_one(case_id: str, variant: str) -> tuple[Any, Any, Any, dict[str, Any]]:
    sampler = Batch9PatchSampler(build_case_records(0), patch_size=PATCH_SIZE, seed=MATCHED_SEED)
    student_x, natural_x, y, _availability, _records, sample_rows = sampler.sample_batch(
        1,
        variant=variant,
        step=STEP,
        matched_seed=MATCHED_SEED,
        force_case_ids=[case_id],
    )
    return student_x[0].numpy(), natural_x[0].numpy(), y[0].numpy(), sample_rows[0]


def main() -> int:
    records = [r for r in build_case_records(0) if r.split == "train"]
    complete = [r for r in records if r.t2_present and r.c0_present]
    selected_records = (complete[:2] + records[:2])[:4]
    rows: list[dict[str, Any]] = []
    failures = []
    for record in selected_records:
        case_id = record.case_id
        props = read_props(case_id)
        shape_zyx = tuple(int(v) for v in props["shape_after_cropping_and_before_resampling"])
        teacher_x, teacher_natural, teacher_y, teacher_meta = sample_one(case_id, "teacher_full_view")
        del teacher_natural
        teacher_bounds = parse_bounds(teacher_meta["patch_bounds"])
        for variant in VARIANTS:
            student_x, natural_x, y, meta = sample_one(case_id, variant)
            bounds = parse_bounds(meta["patch_bounds"])
            valid_hi = tuple(min(bounds[i][1], shape_zyx[i]) for i in range(3))
            valid_lo = tuple(bounds[i][0] for i in range(3))
            valid_size = tuple(max(1, valid_hi[i] - valid_lo[i]) for i in range(3))
            fiducials = {
                "corner0": (0, 0, 0),
                "center": tuple((s - 1) // 2 for s in valid_size),
                "corner1": tuple(s - 1 for s in valid_size),
            }
            status = "PASS"
            reasons = []
            if bounds != teacher_bounds:
                status = "FAIL"
                reasons.append("teacher_patch_bounds_mismatch")
            if student_x.shape[-3:] != natural_x.shape[-3:] or student_x.shape[-3:] != teacher_x.shape[-3:] or y.shape != teacher_y.shape:
                status = "FAIL"
                reasons.append("spatial_shape_mismatch")
            for fiducial_name, local_zyx in fiducials.items():
                original_zyx = tuple(min(shape_zyx[i] - 1, valid_lo[i] + local_zyx[i]) for i in range(3))
                physical = physical_xyz_mm(props, original_zyx)
                max_index_delta_student_natural = 0
                max_index_delta_teacher_natural = max(abs(bounds[i][0] - teacher_bounds[i][0]) for i in range(3))
                if max_index_delta_student_natural != 0 or max_index_delta_teacher_natural != 0:
                    status = "FAIL"
                row = {
                    "case_id": case_id,
                    "variant": variant,
                    "matched_seed": MATCHED_SEED,
                    "step": STEP,
                    "fiducial": fiducial_name,
                    "student_patch_bounds_zyx": meta["patch_bounds"],
                    "natural_patch_bounds_zyx": meta["patch_bounds"],
                    "teacher_patch_bounds_zyx": teacher_meta["patch_bounds"],
                    "local_fiducial_zyx": ";".join(str(v) for v in local_zyx),
                    "original_preprocessed_voxel_zyx": ";".join(str(v) for v in original_zyx),
                    "physical_xyz_mm": ";".join(f"{v:.6f}" for v in physical),
                    "student_shape_zyx": ";".join(str(v) for v in student_x.shape[-3:]),
                    "natural_shape_zyx": ";".join(str(v) for v in natural_x.shape[-3:]),
                    "teacher_shape_zyx": ";".join(str(v) for v in teacher_x.shape[-3:]),
                    "label_shape_zyx": ";".join(str(v) for v in y.shape),
                    "student_availability": meta["student_availability"],
                    "natural_availability": meta["natural_availability"],
                    "teacher_availability": teacher_meta["student_availability"],
                    "max_abs_index_delta_student_natural": max_index_delta_student_natural,
                    "max_abs_index_delta_teacher_natural": max_index_delta_teacher_natural,
                    "spatial_transform_kind": "shared_patch_crop_then_channel_mask_only",
                    "status": status,
                    "failure_reasons": ";".join(reasons),
                }
                rows.append(row)
            if status != "PASS":
                failures.append({"case_id": case_id, "variant": variant, "reasons": reasons})
    write_csv(RESULT_ROOT / "paired_spatial_fiducial_checks.csv", rows)
    payload = {
        "schema_version": 1,
        "status": "FAIL" if failures else "PASS",
        "checked_unix": int(time.time()),
        "case_count": len(selected_records),
        "variant_count": len(VARIANTS),
        "row_count": len(rows),
        "matched_seed": MATCHED_SEED,
        "step": STEP,
        "spatial_transform_kind": "shared_patch_crop_then_channel_mask_only",
        "wave4_authorization_context": "near_baseline_gate_failed_training_not_authorized",
        "failures": failures,
    }
    (RESULT_ROOT / "paired_spatial_fiducial_receipt.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
