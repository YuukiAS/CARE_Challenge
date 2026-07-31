#!/usr/bin/env python3
"""Prepare CARE-MyoWall-IF P0 metric, stock asset, and pilot split receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.myowall_if.stock_adapter import DEFAULT_PLANS, DEFAULT_STOCK_ROOT, sha256_file  # noqa: E402

TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
METRIC_RECEIPT = REPO_ROOT / "results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json"
EXTERNAL_METRIC_RECEIPT = Path("/users/a/e/aereinh/CARE_worktrees/task_metric_truth_20260731/results/20260731_care_metric_truth_reconciliation/metric_truth_receipt.json")
SPLITS = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
DATASET_JSON = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/dataset.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)


def burden_bin(seg_path: Path, label: int | tuple[int, ...]) -> str:
    try:
        import blosc2
        import numpy as np
    except Exception:
        return "burden_unknown"
    seg = np.asarray(blosc2.open(str(seg_path), mode="r")[:]).squeeze()
    labels = label if isinstance(label, tuple) else (label,)
    pos = np.isin(seg, labels).sum()
    wall = np.isin(seg, (1, 4, 5)).sum()
    ratio = float(pos) / max(float(wall), 1.0)
    if pos <= 0:
        return "burden0"
    if ratio < 0.01:
        return "burden1"
    if ratio < 0.05:
        return "burden2"
    return "burden3"


def deterministic_pick(cases: list[str], n: int) -> list[str]:
    keyed = sorted((hashlib.sha256(f"CARE_MyoWall_IF_20260731:{cid}".encode("utf-8")).hexdigest(), cid) for cid in cases)
    return [cid for _key, cid in keyed[:n]]


def stratified_pick(cases: list[str], n: int, rows_by_case: dict[str, dict[str, Any]]) -> list[str]:
    strata: dict[str, list[str]] = defaultdict(list)
    for cid in cases:
        row = rows_by_case[cid]
        key = "|".join([str(row["center"]), str(row["scar_burden_bin"]), str(row["edema_burden_bin"]), str(row["scar_component_bin"])])
        strata[key].append(cid)
    selected: list[str] = []
    for _stratum, members in sorted(strata.items()):
        if len(selected) >= n:
            break
        selected.extend(deterministic_pick(members, 1))
    if len(selected) < n:
        remaining = [cid for cid in cases if cid not in set(selected)]
        selected.extend(deterministic_pick(remaining, n - len(selected)))
    return sorted(selected[:n])


def build_split() -> tuple[list[str], list[str], list[dict[str, Any]]]:
    fold1_train = sorted(read_json(SPLITS)["folds"][1]["train"])
    meta = load_myops_case_metadata(REPO_ROOT)
    fullres = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
    rows = []
    for cid in fold1_train:
        md = meta[cid]
        seg_path = fullres / f"{cid}_seg.b2nd"
        rows.append(
            {
                "case_id": cid,
                "center": md.center,
                "modality_group": md.modality_group,
                "t2_present": md.t2_present,
                "c0_present": md.c0_present,
                "scar_burden_bin": burden_bin(seg_path, 5),
                "edema_burden_bin": burden_bin(seg_path, 4) if md.t2_present else "no_t2",
                "scar_component_bin": "component_uncomputed",
            }
        )
    by_case = {row["case_id"]: row for row in rows}
    t2_cases = [r["case_id"] for r in rows if r["t2_present"] and r["c0_present"]]
    lge_only = [r["case_id"] for r in rows if not r["t2_present"] and not r["c0_present"]]
    lge_c0 = [r["case_id"] for r in rows if not r["t2_present"] and r["c0_present"]]
    if len(t2_cases) < 16 or len(lge_only) < 8 or len(lge_c0) < 8:
        raise RuntimeError(f"pilot split quota impossible: t2={len(t2_cases)} lge_only={len(lge_only)} lge_c0={len(lge_c0)}")
    inner = sorted(stratified_pick(t2_cases, 16, by_case) + stratified_pick(lge_only, 8, by_case) + stratified_pick(lge_c0, 8, by_case))
    train = sorted(set(fold1_train) - set(inner))
    if len(inner) != 32 or len(train) + len(inner) != len(fold1_train):
        raise RuntimeError("pilot split cardinality failed")
    for row in rows:
        row["pilot_split"] = "pilot_inner" if row["case_id"] in set(inner) else "pilot_train"
    return train, inner, rows


def run() -> int:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    metric_payload = {"metric_dependency_status": "WAITING_FOR_RECEIPT", "metric_receipt_path": str(METRIC_RECEIPT.relative_to(REPO_ROOT)), "formal_training_allowed": False}
    source_receipt = METRIC_RECEIPT if METRIC_RECEIPT.is_file() else (EXTERNAL_METRIC_RECEIPT if EXTERNAL_METRIC_RECEIPT.is_file() else None)
    if source_receipt is not None:
        receipt = read_json(source_receipt)
        metric_payload.update(
            {
                "metric_dependency_status": "PASS"
                if receipt.get("metric_contract_status") == "PASS" and int(receipt.get("canonical_t2_present_count", -1)) == 80
                else "FAIL",
                "metric_receipt_source": "current_main" if source_receipt == METRIC_RECEIPT else "external_isolated_metric_truth_worktree",
                "metric_receipt_absolute_path": str(source_receipt),
                "metric_contract_status": receipt.get("metric_contract_status"),
                "canonical_t2_present_count": receipt.get("canonical_t2_present_count"),
                "formal_training_allowed": receipt.get("metric_contract_status") == "PASS" and int(receipt.get("canonical_t2_present_count", -1)) == 80,
                "metric_receipt_sha256": sha256_file(source_receipt),
            }
        )
    write_json(RESULT_ROOT / "metric_dependency_receipt.json", metric_payload)
    train, inner, rows = build_split()
    (RESULT_ROOT / "pilot_train_cases.txt").write_text("\n".join(train) + "\n", encoding="utf-8")
    (RESULT_ROOT / "pilot_inner_cases.txt").write_text("\n".join(inner) + "\n", encoding="utf-8")
    write_rows(RESULT_ROOT / "pilot_subgroup_matrix.csv", rows)
    write_json(
        RESULT_ROOT / "pilot_split_receipt.json",
        {
            "status": "PASS",
            "split_source": str(SPLITS.relative_to(REPO_ROOT)),
            "fold": 1,
            "fold1_train_total": len(train) + len(inner),
            "pilot_train_count": len(train),
            "pilot_inner_count": len(inner),
            "pilot_inner_t2_present": sum(1 for r in rows if r["pilot_split"] == "pilot_inner" and r["t2_present"]),
            "pilot_inner_lge_only": sum(1 for r in rows if r["pilot_split"] == "pilot_inner" and r["modality_group"] == "LGE-only"),
            "pilot_inner_lge_c0": sum(1 for r in rows if r["pilot_split"] == "pilot_inner" and r["modality_group"] == "C0+LGE"),
            "fold1_outer_read": False,
            "hash_seed": "CARE_MyoWall_IF_20260731",
            "pilot_train_sha256": hashlib.sha256("\n".join(train).encode("utf-8")).hexdigest(),
            "pilot_inner_sha256": hashlib.sha256("\n".join(inner).encode("utf-8")).hexdigest(),
        },
    )
    ckpt = DEFAULT_STOCK_ROOT / "fold_1/checkpoint_final.pth"
    plans = read_json(DEFAULT_PLANS)
    conf = plans["configurations"]["3d_fullres"]
    write_json(
        RESULT_ROOT / "asset_freeze_receipt.json",
        {
            "status": "PASS" if ckpt.is_file() and DEFAULT_PLANS.is_file() and DATASET_JSON.is_file() and SPLITS.is_file() else "FAIL",
            "fold": 1,
            "checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
            "checkpoint_size_bytes": ckpt.stat().st_size if ckpt.is_file() else None,
            "checkpoint_sha256": sha256_file(ckpt) if ckpt.is_file() else None,
            "plans_path": str(DEFAULT_PLANS.relative_to(REPO_ROOT)),
            "plans_sha256": sha256_file(DEFAULT_PLANS),
            "dataset_json_path": str(DATASET_JSON.relative_to(REPO_ROOT)),
            "dataset_json_sha256": sha256_file(DATASET_JSON),
            "splits_path": str(SPLITS.relative_to(REPO_ROOT)),
            "splits_sha256": sha256_file(SPLITS),
            "trainer": "nnUNetTrainer_500epochs",
            "network_class": conf["architecture"]["network_class_name"],
            "patch_size": conf["patch_size"],
            "input_order": ["LGE", "T2", "C0"],
        },
    )
    print(json.dumps(metric_payload, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
