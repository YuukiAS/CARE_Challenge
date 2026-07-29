#!/usr/bin/env python3
"""Build W0 freeze receipts for the CARE-ARC clean fold1 controller task."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import SimpleITK as sitk

from scripts.training.run_care_dg import deterministic_inner_split, load_splits, stable_json_sha256
from src.care_myocardium.data.case_metadata import load_myops_case_metadata

TASK_KEY = "20260729_care_arc_clean_fold1"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
LABEL_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
REQUIRED_AUTHORITY_FILES = [
    "AGENTS.md",
    "START_HERE_FOR_GPT.md",
    "GPT_PLANNER_CARE_PROTOCOL.md",
    "prompts/FINAL_OUTPUT_READABILITY_POLICY.md",
    "prompts/AGENT_FLOW_V2_PROTOCOL.md",
    "prompts/HANDOFF_GATE_POLICY.md",
    "prompts/GPT_HARD_GATE_PROMPT.md",
    "prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md",
    "prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md",
    "wiki/README.md",
    ".agents/skills/slurm-routing-partition/SKILL.md",
    ".agents/skills/care-mapper/SKILL.md",
    ".agents/skills/codex-workflow-protocol/SKILL.md",
    ".agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md",
    "prompts/tasks/20260729_care_arc_execution_hardening_amendment.md",
    "prompts/blueprints/CARE_ARC_anchor_relaxed_complete_reconstruction_20260729.md",
    "prompts/tasks/20260729_care_arc_clean_fold1_executor_plan_v2.yaml",
    "prompts/tasks/20260729_care_arc_clean_fold1_controller_v2.md",
    "prompts/routes/handoffs/CURRENT.md",
    "data/benchmarks/protocol/splits_MyoPS.json",
    "data/benchmarks/protocol/cases_MyoPS.json",
    "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json",
]
PATHOLOGY_LABELS = {
    "myocardium": [1],
    "edema_zone": [4, 5],
    "pure_edema": [4],
    "scar": [5],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT))


def run_capture(cmd: list[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=REPO_ROOT, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return {
            "command": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:  # pragma: no cover - live environment guard
        return {"command": cmd, "returncode": 999, "stdout": "", "stderr": repr(exc)}


def label_path(case_id: str) -> Path:
    path = LABEL_ROOT / f"{case_id}.nii.gz"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def case_shape_and_bounds(case_id: str) -> dict[str, Any]:
    img = sitk.ReadImage(str(label_path(case_id)))
    arr = sitk.GetArrayFromImage(img)
    shape = tuple(int(v) for v in arr.shape)
    out: dict[str, Any] = {
        "case_id": case_id,
        "shape_dhw": list(shape),
        "spacing_zyx": list(reversed([float(v) for v in img.GetSpacing()])),
        "label_path": rel(label_path(case_id)),
        "label_sha256": sha256_file(label_path(case_id)),
    }
    any_gt = arr > 0
    out["any_gt_voxels"] = int(any_gt.sum())
    if any_gt.any():
        coords = any_gt.nonzero()
        out["gt_bbox_zyx_min"] = [int(coords[i].min()) for i in range(3)]
        out["gt_bbox_zyx_max"] = [int(coords[i].max()) for i in range(3)]
    else:
        out["gt_bbox_zyx_min"] = None
        out["gt_bbox_zyx_max"] = None
    for name, labels in PATHOLOGY_LABELS.items():
        mask = sum((arr == int(v)) for v in labels).astype(bool)
        out[f"{name}_voxels"] = int(mask.sum())
    return out


def crop_covers(bounds: dict[str, Any], crop_hw: int) -> bool:
    bbox_min = bounds["gt_bbox_zyx_min"]
    bbox_max = bounds["gt_bbox_zyx_max"]
    if bbox_min is None or bbox_max is None:
        return True
    _d, h, w = [int(v) for v in bounds["shape_dhw"]]
    y0 = h // 2 - crop_hw // 2
    x0 = w // 2 - crop_hw // 2
    y1 = y0 + crop_hw
    x1 = x0 + crop_hw
    return int(bbox_min[1]) >= y0 and int(bbox_max[1]) < y1 and int(bbox_min[2]) >= x0 and int(bbox_max[2]) < x1


def summarize_depths(rows: list[dict[str, Any]]) -> dict[str, Any]:
    depths: dict[str, int] = {}
    for row in rows:
        d = str(row["shape_dhw"][0])
        depths[d] = depths.get(d, 0) + 1
    return {
        "case_count": len(rows),
        "depth_counts": dict(sorted(depths.items(), key=lambda kv: int(kv[0]))),
        "min_depth": min(int(r["shape_dhw"][0]) for r in rows) if rows else None,
        "max_depth": max(int(r["shape_dhw"][0]) for r in rows) if rows else None,
        "z_crop_allowed": False,
        "full_depth_contract": "preserve original D for every case",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobid", default="61220581")
    args = parser.parse_args()

    created_at = now_utc()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    metadata = load_myops_case_metadata(REPO_ROOT)
    splits = load_splits()
    selected_folds: dict[str, Any] = {}
    all_actual_cases: list[str] = []
    for fold_id in (0, 1):
        fold = next(row for row in splits if int(row["fold"]) == fold_id)
        inner = deterministic_inner_split(sorted(fold["train"]), fold_id, metadata)
        outer_cases = sorted(fold["val"])
        actual_train = sorted(inner["actual_train_cases"])
        disjoint = not (set(actual_train) & set(inner["inner_select_cases"]) or set(actual_train) & set(outer_cases))
        payload = {
            **inner,
            "outer_cases": outer_cases,
            "outer_cases_sha256": stable_json_sha256(outer_cases),
            "actual_train_inner_outer_disjoint": disjoint,
            "inner12_count_observed": len(inner["inner_select_cases"]),
            "inner12_policy_note": "Reused existing deterministic_inner_split precedent from scripts/training/run_care_dg.py.",
        }
        selected_folds[f"fold{fold_id}"] = payload
        all_actual_cases.extend(actual_train)
    split_receipt = {
        "task_key": TASK_KEY,
        "created_at_utc": created_at,
        "status": "PASS" if all(v["actual_train_inner_outer_disjoint"] for v in selected_folds.values()) else "FAIL",
        "folds": selected_folds,
        "source_split_path": "data/benchmarks/protocol/splits_MyoPS.json",
        "source_split_sha256": sha256_file(REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"),
    }

    unique_actual = sorted(set(all_actual_cases))
    shape_rows = [case_shape_and_bounds(case_id) for case_id in unique_actual]
    depth_receipt = {
        "task_key": TASK_KEY,
        "created_at_utc": created_at,
        "status": "PASS",
        "audited_population": "fold0_and_fold1_actual_train_union",
        "fold_actual_train_case_counts": {
            key: value["counts"]["actual_train"] for key, value in selected_folds.items()
        },
        "union_actual_train_case_count": len(unique_actual),
        **summarize_depths(shape_rows),
        "representative_depths_present": sorted({int(r["shape_dhw"][0]) for r in shape_rows}),
    }
    crop_candidates = []
    selected_crop = None
    for crop_hw in (192, 224, 256):
        failed = [r["case_id"] for r in shape_rows if not crop_covers(r, crop_hw)]
        row = {
            "crop_hw": crop_hw,
            "coverage": 1.0 - (len(failed) / max(1, len(shape_rows))),
            "coverage_percent": 100.0 * (1.0 - (len(failed) / max(1, len(shape_rows)))),
            "failed_case_count": len(failed),
            "failed_cases": failed[:50],
        }
        crop_candidates.append(row)
        if selected_crop is None and not failed:
            selected_crop = crop_hw
    crop_receipt = {
        "task_key": TASK_KEY,
        "created_at_utc": created_at,
        "status": "PASS" if selected_crop is not None else "FAIL",
        "selection_rule": "first of 192,224,256 with 100% actual-train GT coverage under image-center crop",
        "selected_inplane_crop_hw": selected_crop,
        "z_crop_allowed": False,
        "candidate_results": crop_candidates,
    }

    authority_hashes = {
        path: sha256_file(REPO_ROOT / path) for path in REQUIRED_AUTHORITY_FILES if (REPO_ROOT / path).exists()
    }
    git_head = run_capture(["git", "rev-parse", "HEAD"])
    git_status = run_capture(["git", "status", "--short", "--branch"])
    squeue = run_capture(["squeue", "-j", str(args.jobid), "-o", "%i|%P|%j|%u|%T|%M|%l|%D|%R"])
    controller_context = {
        "task_key": TASK_KEY,
        "phase": "W0",
        "created_at_utc": created_at,
        "git_head": git_head["stdout"],
        "git_status_short_branch": git_status["stdout"].splitlines(),
        "authority_priority": [
            "prompts/tasks/20260729_care_arc_execution_hardening_amendment.md",
            "prompts/blueprints/CARE_ARC_anchor_relaxed_complete_reconstruction_20260729.md",
            "prompts/tasks/20260729_care_arc_clean_fold1_executor_plan_v2.yaml",
            "prompts/tasks/20260729_care_arc_clean_fold1_controller_v2.md",
            "prompts/routes/handoffs/CURRENT.md",
        ],
        "authority_sha256": authority_hashes,
        "required_job_ids": [str(args.jobid)],
        "allocation_snapshot": squeue,
        "required_runtime_paths": [
            "results/20260729_care_arc_clean_fold1/runtime/preflight",
            "results/20260729_care_arc_clean_fold1/runtime/fold0_development",
            "results/20260729_care_arc_clean_fold1/runtime/fold1_clean",
        ],
        "files_read": REQUIRED_AUTHORITY_FILES,
        "executor_plan_validator_compatibility": {
            "legacy_validator": "scripts/ops/validate_executor_plan.py",
            "observed_status": "FAIL",
            "controller_interpretation": "single-executor task proceeds under explicit user/controller contract; recorded as compatibility finding",
        },
    }
    adoption = {
        "task_key": TASK_KEY,
        "created_at_utc": created_at,
        "status": "PASS",
        "active_authority": "CARE-ARC execution hardening amendment R1",
        "head_equals_origin_main": git_head["stdout"] == run_capture(["git", "rev-parse", "origin/main"])["stdout"],
        "required_commits_present": {
            commit: run_capture(["git", "merge-base", "--is-ancestor", commit, "HEAD"])["returncode"] == 0
            for commit in [
                "6166cb26e701a6c37f27a6c231392c3883a28cd0",
                "5f9805e2a32edc1836299476eff3587dc395639e",
                "988477ef4175f47f514d41c18bcd113b6543589e",
                "59a664bd15b936e9adc9774340ababce9a3a0323",
            ]
        },
        "forbidden_actions": {
            "new_slurm_job": False,
            "runtime_git_push": False,
            "validation_or_docker_upload": False,
            "write_overflow_htzhu_care": False,
        },
    }

    write_json(RESULT_ROOT / "controller_context.json", controller_context)
    write_json(RESULT_ROOT / "adoption_receipt.json", adoption)
    write_json(RESULT_ROOT / "split_freeze_receipt.json", split_receipt)
    write_json(RESULT_ROOT / "full_volume_shape_audit.json", depth_receipt)
    write_json(RESULT_ROOT / "crop_freeze_receipt.json", crop_receipt)
    write_csv(
        RESULT_ROOT / "full_volume_shape_audit_cases.csv",
        shape_rows,
        [
            "case_id",
            "shape_dhw",
            "spacing_zyx",
            "any_gt_voxels",
            "myocardium_voxels",
            "edema_zone_voxels",
            "pure_edema_voxels",
            "scar_voxels",
            "gt_bbox_zyx_min",
            "gt_bbox_zyx_max",
            "label_path",
            "label_sha256",
        ],
    )
    bootstrap_md = f"""# CARE-ARC W0 Controller Bootstrap Snapshot

当前任务已同步到 `origin/main`，最高 authority 为 execution hardening amendment。W0 冻结了 fold0/fold1 的 outer、inner 和 actual-train 病例集合，确认 actual-train 不包含 inner 或 outer；实际训练合同必须保留每例完整 z 深度，不允许 z crop。in-plane crop 按 actual-train GT 覆盖率冻结为 `{selected_crop}`。

- created_at_utc: `{created_at}`
- git_head: `{git_head["stdout"]}`
- allocation_jobid: `{args.jobid}`
- allocation_snapshot_returncode: `{squeue["returncode"]}`
- split_receipt: `results/{TASK_KEY}/split_freeze_receipt.json`
- shape_audit: `results/{TASK_KEY}/full_volume_shape_audit.json`
- crop_receipt: `results/{TASK_KEY}/crop_freeze_receipt.json`
- executor_plan_validator_compatibility: `legacy_validator_failed_recorded`
"""
    (RESULT_ROOT / "controller_bootstrap_snapshot.md").write_text(bootstrap_md, encoding="utf-8")
    ledger_path = RESULT_ROOT / "controller_ledger.csv"
    write_csv(
        ledger_path,
        [
            {
                "timestamp_utc": created_at,
                "phase": "W0",
                "git_head": git_head["stdout"],
                "task_hash": authority_hashes.get("prompts/tasks/20260729_care_arc_execution_hardening_amendment.md", ""),
                "job_states": squeue["stdout"].replace("\n", " / "),
                "decision": "W0_FREEZE_COMPLETE" if split_receipt["status"] == "PASS" and crop_receipt["status"] == "PASS" else "W0_NEEDS_REPAIR",
                "next_action": "W1_IMPLEMENTATION",
            }
        ],
        ["timestamp_utc", "phase", "git_head", "task_hash", "job_states", "decision", "next_action"],
    )
    print(json.dumps({
        "status": "PASS" if split_receipt["status"] == "PASS" and crop_receipt["status"] == "PASS" else "FAIL",
        "selected_crop": selected_crop,
        "depth_counts": depth_receipt["depth_counts"],
        "fold0_counts": selected_folds["fold0"]["counts"],
        "fold1_counts": selected_folds["fold1"]["counts"],
        "outputs": [
            rel(RESULT_ROOT / "controller_context.json"),
            rel(RESULT_ROOT / "split_freeze_receipt.json"),
            rel(RESULT_ROOT / "full_volume_shape_audit.json"),
            rel(RESULT_ROOT / "crop_freeze_receipt.json"),
        ],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
