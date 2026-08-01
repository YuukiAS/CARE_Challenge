#!/usr/bin/env python3
"""Bootstrap receipts for the 20260801 target-domain pathology race."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import random
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


TASK_KEY = "20260801_care_target_domain_pathology_specialist_race"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"
STOCK_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
BLUEPRINT = REPO_ROOT / "prompts/blueprints/CARE_target_domain_pathology_specialist_race_20260801.md"
CONTROLLER = REPO_ROOT / "prompts/tasks/20260801_care_target_domain_pathology_race_controller.md"
EXECUTOR_PLAN = REPO_ROOT / "prompts/tasks/20260801_care_target_domain_pathology_race_executor_plan.yaml"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git_out(args: list[str]) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    return proc.stdout.strip() if proc.stdout else f"returncode={proc.returncode}"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({k for row in rows for k in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def label_counts(case_id: str) -> dict[str, int]:
    pkl_path = PREPROCESSED / f"{case_id}.pkl"
    with pkl_path.open("rb") as f:
        props = pickle.load(f)
    loc = props.get("class_locations", {})
    return {
        "scar_location_samples": int(len(loc.get(5, []))),
        "edema_location_samples": int(len(loc.get(4, []))),
        "injury_location_samples": int(len(loc.get(4, [])) + len(loc.get(5, []))),
    }


def quartile(values: list[int], value: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    n = len(ordered)
    q1 = ordered[int((n - 1) * 0.25)]
    q2 = ordered[int((n - 1) * 0.50)]
    q3 = ordered[int((n - 1) * 0.75)]
    if value <= q1:
        return 0
    if value <= q2:
        return 1
    if value <= q3:
        return 2
    return 3


def choose_inner(dev_rows: list[dict[str, Any]], seed: int) -> set[str]:
    scar_values = [int(r["scar_location_samples"]) for r in dev_rows]
    injury_values = [int(r["injury_location_samples"]) for r in dev_rows]
    strata: dict[tuple[str, int, int], list[str]] = {}
    for row in dev_rows:
        key = (
            str(row["center"]),
            quartile(scar_values, int(row["scar_location_samples"])),
            quartile(injury_values, int(row["injury_location_samples"])),
        )
        strata.setdefault(key, []).append(str(row["case_id"]))
    rng = random.Random(seed)
    selected: set[str] = set()
    target = max(1, round(len(dev_rows) * 0.20))
    for key in sorted(strata):
        cases = sorted(strata[key])
        rng.shuffle(cases)
        take = 1 if len(cases) >= 3 else 0
        selected.update(cases[:take])
    if len(selected) < target:
        remaining = [str(r["case_id"]) for r in sorted(dev_rows, key=lambda x: str(x["case_id"])) if str(r["case_id"]) not in selected]
        rng.shuffle(remaining)
        selected.update(remaining[: target - len(selected)])
    if len(selected) > target:
        selected = set(sorted(selected)[:target])
    return selected


def build(args: argparse.Namespace) -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    metadata = load_myops_case_metadata(REPO_ROOT)
    split_data = json.loads(SPLITS.read_text(encoding="utf-8"))
    complete_cases = sorted(
        cid for cid, meta in metadata.items() if meta.lge_present and meta.t2_present and meta.c0_present
    )
    center_counts = Counter(metadata[cid].center for cid in complete_cases)

    all_rows: list[dict[str, Any]] = []
    split_receipt: dict[str, Any] = {}
    required_outer = {
        2: {"Case3008", "Case2019", "Case2034"},
        3: {"Case3009", "Case2021"},
    }
    data_contract_errors: list[str] = []
    for fold in (2, 3):
        split = split_data[fold]
        train_complete = [cid for cid in split["train"] if cid in complete_cases]
        outer_complete = [cid for cid in split["val"] if cid in complete_cases]
        dev_rows = []
        for cid in train_complete:
            meta = metadata[cid]
            row = {"case_id": cid, "center": meta.center, **label_counts(cid)}
            dev_rows.append(row)
        inner = choose_inner(dev_rows, 20260801 + fold)
        fold_rows: list[dict[str, Any]] = []
        for cid in sorted(train_complete + outer_complete):
            meta = metadata[cid]
            counts = label_counts(cid)
            canonical_split = "val" if cid in outer_complete else "train"
            role = "outer" if canonical_split == "val" else ("inner_selection" if cid in inner else "actual_train")
            fold_rows.append(
                {
                    "fold": fold,
                    "case_id": cid,
                    "canonical_split": canonical_split,
                    "race_role": role,
                    "center": meta.center,
                    "modality_group": meta.modality_group,
                    "lge_present": int(meta.lge_present),
                    "t2_present": int(meta.t2_present),
                    "c0_present": int(meta.c0_present),
                    "scar_positive": int(counts["scar_location_samples"] > 0),
                    "edema_positive": int(counts["edema_location_samples"] > 0),
                    **counts,
                    "sentinel_case": int(cid in required_outer[fold]),
                }
            )
        missing = sorted(required_outer[fold] - set(outer_complete))
        if missing:
            data_contract_errors.append(f"fold{fold} missing required outer cases: {','.join(missing)}")
        write_csv(RESULT_ROOT / f"fold{fold}_case_manifest.csv", fold_rows)
        all_rows.extend(fold_rows)
        split_receipt[f"fold{fold}"] = {
            "outer_complete_count": len(outer_complete),
            "development_complete_count": len(train_complete),
            "inner_selection_count": len(inner),
            "actual_train_count": len(train_complete) - len(inner),
            "required_outer_cases": sorted(required_outer[fold]),
            "missing_required_outer_cases": missing,
            "outer_cases": sorted(outer_complete),
            "inner_selection_cases": sorted(inner),
            "actual_train_cases": sorted(set(train_complete) - inner),
        }

    write_csv(RESULT_ROOT / "fold2_fold3_case_manifest.csv", all_rows)
    data_contract_status = "PASS" if len(complete_cases) == 80 and center_counts.get("CenterB") == 35 and center_counts.get("CenterC") == 45 and not data_contract_errors else "FAIL"
    write_json(
        RESULT_ROOT / "frozen_data_contract.json",
        {
            "created_at": now_utc(),
            "dataset": "Dataset501_CAREMyoPS",
            "input_order": ["LGE", "T2", "C0"],
            "complete_triomodal_cases": len(complete_cases),
            "center_counts": dict(sorted(center_counts.items())),
            "formal_folds": [2, 3],
            "label_semantics": {"scar": 5, "pure_edema": 4, "injury": [4, 5], "myocardium_union": [1, 4, 5]},
            "data_contract_status": data_contract_status,
            "errors": data_contract_errors,
            "splits_final_sha256": sha256_file(SPLITS),
            "plans_sha256": sha256_file(PLANS),
        },
    )
    write_json(RESULT_ROOT / "split_receipt.json", {"created_at": now_utc(), "status": data_contract_status, **split_receipt})

    allocation = {
        "policy_override": {
            "created_at": now_utc(),
            "source": "user_message_after_initial_insufficient_allocation_findings",
            "summary": "User authorized controller to decide between submitting extra Slurm jobs or using the existing one-GPU allocation serially, and requested not to stop at the original resource block.",
            "new_slurm_job_authorized": True,
            "serial_fallback_authorized": True,
        },
        "observed_existing_allocation": {
            "job_id": "61220581",
            "state": "RUNNING",
            "partition": "htzhulab",
            "alloc_tres": "cpu=8,mem=64G,node=1,billing=8,gres/gpu=1,gres/gpu:nvidia_h100_nvl=1",
            "gpu_count": 1,
            "time_left_at_probe": args.existing_time_left,
            "contract_original_required_gpu_count": 4,
            "contract_original_required_walltime_hours": 10,
            "original_resource_gate_status": "FAIL_GPU_COUNT",
            "post_override_resource_strategy": "submit_lane_level_extra_gpu_jobs_and_keep_existing_h100_available",
        },
        "queue_snapshot_paths": {
            "htzhulab": "results/20260801_care_target_domain_pathology_specialist_race/queue_htzhulab.txt",
            "school_gpu": "results/20260801_care_target_domain_pathology_specialist_race/queue_school_gpu.txt",
        },
    }
    write_json(RESULT_ROOT / "resource_override_receipt.json", allocation["policy_override"])
    write_json(RESULT_ROOT / "existing_allocation_receipt.json", allocation)

    required_reads = [
        "START_HERE_FOR_GPT.md",
        "GPT_PLANNER_CARE_PROTOCOL.md",
        "AGENTS.md",
        "prompts/FINAL_OUTPUT_READABILITY_POLICY.md",
        "prompts/AGENT_FLOW_V2_PROTOCOL.md",
        "prompts/HANDOFF_GATE_POLICY.md",
        "prompts/GPT_HARD_GATE_PROMPT.md",
        "prompts/routes/ROUTE_ANTI_LAZINESS_PROTOCOL.md",
        "prompts/routes/ROUTE_HARD_REQUIREMENTS_MATRIX.md",
        "prompts/routes/handoffs/CURRENT.md",
        "routes/README.md",
        "wiki/README.md",
        ".agents/skills/slurm-routing-partition/SKILL.md",
        ".agents/skills/care-mapper/SKILL.md",
    ]
    context = {
        "created_at": now_utc(),
        "task_key": TASK_KEY,
        "phase": "W0_BOOTSTRAP_AND_FREEZE",
        "git_head": git_out(["rev-parse", "HEAD"]),
        "git_status_short": git_out(["status", "--short", "--branch"]),
        "origin_main": git_out(["rev-parse", "origin/main"]),
        "prompt_hashes": {
            str(BLUEPRINT.relative_to(REPO_ROOT)): sha256_file(BLUEPRINT),
            str(CONTROLLER.relative_to(REPO_ROOT)): sha256_file(CONTROLLER),
            str(EXECUTOR_PLAN.relative_to(REPO_ROOT)): sha256_file(EXECUTOR_PLAN),
        },
        "files_read": required_reads + [str(BLUEPRINT.relative_to(REPO_ROOT)), str(CONTROLLER.relative_to(REPO_ROOT)), str(EXECUTOR_PLAN.relative_to(REPO_ROOT))],
        "diagram_versions_read": ["SRR-v2", "SRR-v2.5", "SRR-v3"],
        "visual_read_status": "PLANNER_BLUEPRINT_CLAIM_ACCEPTED_UNDER_USER_CONTINUE_INSTRUCTION",
        "visual_read_boundary": "Current Codex thread has repository PNGs but no ChatGPT Project-background visual channel attachment; blueprint states planning already visually read these versions.",
        "recovered_route_objective": "modality-specific evidence; pathology-specific scar/edema authority; soft anatomy context; negative-space accounting; full-volume help/harm and HD95 gates",
        "data_contract_status": data_contract_status,
        "resource_strategy": allocation["observed_existing_allocation"]["post_override_resource_strategy"],
        "stale_state_note": "CURRENT.md/wiki still describe MyoWall/PRISM predecessor state and will need terminal update after race results.",
    }
    write_json(RESULT_ROOT / "controller_context.json", context)
    write_csv(
        RESULT_ROOT / "controller_ledger.csv",
        [
            {
                "timestamp": now_utc(),
                "phase": "W0_BOOTSTRAP_AND_FREEZE",
                "git_head": context["git_head"],
                "decision": "CONTINUE_AFTER_USER_RESOURCE_OVERRIDE",
                "next_action": "SUBMIT_LANE_LEVEL_GPU_WORKERS",
            }
        ],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing-time-left", default="2-02:20:27")
    args = parser.parse_args()
    build(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
