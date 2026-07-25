#!/usr/bin/env python
"""Calibration-only selector for CARE-SRR-Cascade candidates."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


SIX_CANDIDATES = (
    "control_seed20260724",
    "control_seed20260725",
    "srr_seed20260724",
    "srr_seed20260725",
    "control_two_seed_probability_mean_derived_bounded_channel_correction",
    "srr_two_seed_probability_mean_derived_bounded_channel_correction",
)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _float(row: dict[str, str], key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key, default) or default)
    except ValueError:
        return default


def select_candidate(rows: list[dict[str, str]]) -> dict[str, Any]:
    if any(str(row.get("split", "calibration")) == "audit" for row in rows):
        raise ValueError("audit_used_for_selection")
    in_contract = [row for row in rows if row.get("candidate") in SIX_CANDIDATES]
    eligible = [row for row in in_contract if row.get("candidate_eligible", "true").lower() != "false"]
    selection_pool = eligible or in_contract
    if not selection_pool:
        return {"decision": "FALLBACK_TO_NNUNET_no_contract_candidate", "selected_candidate": ""}
    selection_pool.sort(
        key=lambda row: (
            -_float(row, "positive_GT_Dice_delta"),
            _float(row, "exact_HD_delta"),
            _float(row, "HD95_relative_worsening"),
            _float(row, "remote_FP_ratio", 1.0),
            -_float(row, "help_minus_harm"),
            _float(row, "optimizer_step", 999999),
            SIX_CANDIDATES.index(row["candidate"]),
        )
    )
    selected = selection_pool[0]
    if eligible:
        return {"decision": "PASS", "selected_candidate": selected["candidate"], "row": selected}
    return {
        "decision": "PASS_AUDIT_EVIDENCE_ONLY_CALIBRATION_INELIGIBLE",
        "selected_candidate": selected["candidate"],
        "row": selected,
        "deployable_after_calibration": False,
        "notes": "All six calibration candidates were ineligible; selected best calibration-only candidate for audit evidence before fallback.",
    }


def contract() -> dict[str, Any]:
    return {
        "entrypoint": "scripts/evaluation/select_care_srr_cascade.py",
        "calibration_only": True,
        "audit_used_for_selection": False,
        "six_candidates": SIX_CANDIDATES,
        "lexicographic_order": [
            "maximize_positive_GT_Dice_delta",
            "minimize_exact_HD_delta",
            "minimize_HD95_relative_worsening",
            "minimize_remote_FP_ratio",
            "maximize_help_minus_harm",
            "prefer_earlier_optimizer_step",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--metrics-csv", type=Path)
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    if not (args.metrics_csv and args.output_json):
        raise SystemExit("--metrics-csv and --output-json are required unless --print-contract")
    payload = select_candidate(read_rows(args.metrics_csv))
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["selected_candidate"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
