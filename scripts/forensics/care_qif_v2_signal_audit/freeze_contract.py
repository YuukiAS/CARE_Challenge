#!/usr/bin/env python3
"""Freeze W0 data, OOF provenance, and scar component capacity evidence."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_qif_v2_signal_audit.common import (
    DATASET_JSON,
    FULLRES_ROOT,
    PLANS_JSON,
    REPO_ROOT,
    RESULT_ROOT,
    SPLITS_PATH,
    STOCK_ROOT,
    all_dataset_cases,
    case_membership_proof,
    checkpoint_path_for_fold,
    complete_bc_cases,
    component_rows,
    load_seg,
    oof_fold_for_case,
    rel,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
)


def capture(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else f"ERROR[{proc.returncode}]: {proc.stderr.strip()}"


def scar_stats(case_id: str) -> dict[str, Any]:
    seg = load_seg(case_id)
    rows = component_rows(case_id)
    count = max(int(r["component_count"]) for r in rows) if rows else 0
    return {
        "scar_voxels": int((seg == 5).sum()),
        "injury_voxels": int(((seg == 4) | (seg == 5)).sum()),
        "healthy_myo_voxels": int((seg == 1).sum()),
        "scar_component_count": count,
        "small_scar_component_count": sum(1 for r in rows if str(r.get("small_lesion")).lower() == "true"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, default=RESULT_ROOT)
    args = parser.parse_args()
    out = args.result_root
    out.mkdir(parents=True, exist_ok=True)

    bc = complete_bc_cases()
    by_center = {center: [r for r in bc if r["center"] == center] for center in ("CenterB", "CenterC")}
    case_stats = {row["case_id"]: scar_stats(row["case_id"]) for row in bc}

    data_status = (
        len(bc) == 80
        and len(by_center["CenterB"]) == 35
        and len(by_center["CenterC"]) == 45
        and all(row["modality_group"] == "C0+LGE+T2" for row in bc)
    )

    oof_rows: list[dict[str, Any]] = []
    oof_ok = True
    fold_checkpoint_sha = {
        fold: sha256_file(checkpoint_path_for_fold(fold))
        for fold in sorted({oof_fold_for_case(row["case_id"]) for row in bc})
        if checkpoint_path_for_fold(fold).exists()
    }
    plans_sha = sha256_file(PLANS_JSON)
    dataset_sha = sha256_file(DATASET_JSON)
    split_sha = sha256_file(SPLITS_PATH)
    for row in bc:
        fold = oof_fold_for_case(row["case_id"])
        ckpt = checkpoint_path_for_fold(fold)
        proof = case_membership_proof(row["case_id"], fold)
        ok = ckpt.exists() and proof["status"] == "PASS"
        oof_ok = oof_ok and ok
        oof_rows.append(
            {
                **row,
                **case_stats[row["case_id"]],
                "oof_fold": fold,
                "checkpoint_path": rel(ckpt),
                "checkpoint_sha256": fold_checkpoint_sha.get(fold, ""),
                "plans_path": rel(PLANS_JSON),
                "plans_sha256": plans_sha,
                "dataset_json_path": rel(DATASET_JSON),
                "dataset_json_sha256": dataset_sha,
                "split_path": rel(SPLITS_PATH),
                "split_sha256": split_sha,
                "case_membership_status": proof["status"],
                "case_membership_proof_sha256": proof["proof_sha256"],
                "oof_provenance_status": "PASS" if ok else "FAIL",
            }
        )

    all_cases = all_dataset_cases()
    comp_rows: list[dict[str, Any]] = []
    for case_id in all_cases:
        comp_rows.extend(component_rows(case_id))
    counts = {}
    for row in comp_rows:
        counts[row["case_id"]] = max(counts.get(row["case_id"], 0), int(row["component_count"]))
    covered = sum(1 for case_id in all_cases if counts.get(case_id, 0) <= 32) / max(len(all_cases), 1)
    capacity_ok = covered >= 0.99

    write_csv(out / "oof_backbone_manifest.csv", oof_rows)
    write_csv(out / "component_statistics.csv", comp_rows)
    write_json(
        out / "component_capacity_receipt.json",
        {
            "created_at": utc_now(),
            "case_count": len(all_cases),
            "query_count": 32,
            "component_count_le_32_fraction": float(covered),
            "overflow_case_count": int(sum(1 for case_id in all_cases if counts.get(case_id, 0) > 32)),
            "max_component_count": int(max(counts.values()) if counts else 0),
            "status": "PASS" if capacity_ok else "QUERY_CAPACITY_INVALID",
        },
    )
    write_json(
        out / "frozen_data_contract.json",
        {
            "created_at": utc_now(),
            "complete_triomodal_cases": len(bc),
            "CenterB": len(by_center["CenterB"]),
            "CenterC": len(by_center["CenterC"]),
            "expected_complete_triomodal_cases": 80,
            "expected_CenterB": 35,
            "expected_CenterC": 45,
            "all_cases_for_component_statistics": len(all_cases),
            "labels": {
                "healthy_myocardium": 1,
                "LV_cavity": 2,
                "pure_edema": 4,
                "scar": 5,
                "injury_zone": [4, 5],
                "myocardium_union": [1, 4, 5],
            },
            "data_contract_status": "PASS" if data_status else "DATA_CONTRACT_MISMATCH",
            "oof_feature_provenance_status": "PASS" if oof_ok else "OOF_FEATURE_PROVENANCE_FAIL",
            "query_capacity_status": "PASS" if capacity_ok else "QUERY_CAPACITY_INVALID",
        },
    )
    write_json(
        out / "controller_context.json",
        {
            "created_at": utc_now(),
            "task_key": "20260731_care_qif_v2_signal_audit",
            "phase": "W0",
            "repo_root": str(REPO_ROOT),
            "git_head": capture(["git", "rev-parse", "HEAD"]),
            "git_status_short_branch": capture(["git", "status", "--short", "--branch"]),
            "task_prompt_paths": [
                "prompts/blueprints/CARE_QIF_v2_signal_audit_20260731.md",
                "prompts/tasks/20260731_care_qif_v2_signal_audit_executor_plan.yaml",
                "prompts/tasks/20260731_care_qif_v2_signal_audit_controller.md",
            ],
            "task_prompt_sha256": {
                "blueprint": sha256_file(REPO_ROOT / "prompts/blueprints/CARE_QIF_v2_signal_audit_20260731.md"),
                "executor_plan": sha256_file(REPO_ROOT / "prompts/tasks/20260731_care_qif_v2_signal_audit_executor_plan.yaml"),
                "controller": sha256_file(REPO_ROOT / "prompts/tasks/20260731_care_qif_v2_signal_audit_controller.md"),
            },
            "agents_sha256": sha256_file(REPO_ROOT / "AGENTS.md"),
            "slurm_skill_sha256": sha256_file(REPO_ROOT / ".agents/skills/slurm-routing-partition/SKILL.md"),
            "mapper_skill_sha256": sha256_file(REPO_ROOT / ".agents/skills/care-mapper/SKILL.md"),
            "data_roots": {
                "fullres": rel(FULLRES_ROOT),
                "stock_nnunet": rel(STOCK_ROOT),
                "runtime_feature_cache": "/users/a/e/aereinh/.tmp/codex-CARE/20260731_care_qif_v2_signal_audit/features",
            },
            "stale_evidence": {
                "CURRENT_md_reflects_qif_contract": False,
                "wiki_readme_reflects_qif_contract": False,
                "action": "recorded only; CURRENT.md and wiki/README.md were not modified by this task",
            },
        },
    )
    write_csv(
        out / "controller_ledger.csv",
        [
            {
                "timestamp": utc_now(),
                "phase": "W0",
                "git_head": capture(["git", "rev-parse", "HEAD"]),
                "decision": "PASS" if data_status and oof_ok and capacity_ok else "BLOCKED",
                "next_action": "W1_W2" if data_status and oof_ok and capacity_ok else "write_blocked_packet",
            }
        ],
    )
    if not data_status:
        return 10
    if not oof_ok:
        return 11
    if not capacity_ok:
        return 12
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
