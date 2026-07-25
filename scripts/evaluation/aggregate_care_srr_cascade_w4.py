#!/usr/bin/env python
"""W4 aggregation gate for CARE-SRR-Cascade after formal training."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
RC1_ROOT = RESULT / "runtime_closure_repair_rc1"

PATHOLOGIES = ("scar", "edema")
FINAL_DECISIONS = ("USE_SRR_CASCADE", "USE_CASCADE_CONTROL", "FALLBACK_TO_NNUNET")
SIX_CANDIDATES = (
    "control_seed20260724",
    "control_seed20260725",
    "srr_seed20260724",
    "srr_seed20260725",
    "control_two_seed_probability_mean_derived_bounded_channel_correction",
    "srr_two_seed_probability_mean_derived_bounded_channel_correction",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text()) if path.exists() else {}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def required_paths(result_root: Path, pathology: str) -> dict[str, Path]:
    return {
        "calibration_metrics": result_root / f"w4_calibration_metrics_{pathology}_v2.csv",
        "audit_metrics": result_root / f"w4_audit_metrics_{pathology}_v2.csv",
        "selection": result_root / f"w4_selection_{pathology}_v2.json",
        "final_decision": result_root / f"w4_final_decision_{pathology}_v2.json",
    }


def metric_rows_valid(path: Path, *, expected_split: str) -> tuple[bool, list[str]]:
    blockers: list[str] = []
    rows = read_csv(path)
    if not rows:
        return False, [f"{path.name}:missing_or_empty"]
    for row in rows:
        split = row.get("split", expected_split)
        if split != expected_split:
            blockers.append(f"{path.name}:bad_split:{split}")
        if expected_split == "calibration":
            candidate = row.get("candidate", "")
            if candidate not in SIX_CANDIDATES:
                blockers.append(f"{path.name}:candidate_not_in_six:{candidate}")
        for key in ("Dice", "exact_HD", "remote_FP_mm3", "help_harm"):
            if key not in row:
                blockers.append(f"{path.name}:missing_metric:{key}")
    return not blockers, blockers


def validate_pathology_outputs(result_root: Path, pathology: str) -> dict[str, Any]:
    paths = required_paths(result_root, pathology)
    blockers: list[str] = []
    exists = {key: path.exists() for key, path in paths.items()}
    for key, present in exists.items():
        if not present:
            blockers.append(f"missing_{pathology}_{key}:{display_path(paths[key])}")
    cal_ok, cal_blockers = metric_rows_valid(paths["calibration_metrics"], expected_split="calibration")
    audit_ok, audit_blockers = metric_rows_valid(paths["audit_metrics"], expected_split="audit")
    blockers.extend(cal_blockers)
    blockers.extend(audit_blockers)
    selection = read_json(paths["selection"])
    if selection:
        selected = selection.get("selected_candidate", "")
        if selected and selected not in SIX_CANDIDATES:
            blockers.append(f"{pathology}:selected_candidate_not_in_six:{selected}")
        if selection.get("selection_split") == "audit":
            blockers.append(f"{pathology}:audit_used_for_selection")
    final_decision = read_json(paths["final_decision"])
    if final_decision:
        if final_decision.get("decision") not in FINAL_DECISIONS:
            blockers.append(f"{pathology}:bad_final_decision:{final_decision.get('decision')}")
        if final_decision.get("audit_used_for_selection") is True:
            blockers.append(f"{pathology}:final_decision_audit_used_for_selection")
    return {
        "pathology": pathology,
        "decision": "PASS" if not blockers and cal_ok and audit_ok else "NEEDS_REPAIR",
        "paths": {key: display_path(path) for key, path in paths.items()},
        "exists": exists,
        "blockers": blockers,
    }


def aggregate(result_root: Path = RESULT) -> dict[str, Any]:
    terminal = read_json(result_root / "runtime_closure_repair_rc1/formal_terminal_accounting_v2.json")
    terminal_decision = terminal.get("decision", "MISSING")
    if terminal_decision != "PASS_TERMINAL_TRAINING_READY_FOR_AGGREGATION":
        payload = {
            "schema_version": 1,
            "timestamp_utc": utc_now(),
            "decision": "NEEDS_MONITOR_W3_NOT_TERMINAL" if terminal_decision in {"NEEDS_MONITOR", "MISSING"} else "NEEDS_REPAIR_W3_ACCOUNTING",
            "formal_terminal_accounting_decision": terminal_decision,
            "completion_claim": False,
            "pathology_results": [],
            "blockers": [f"formal_terminal_accounting={terminal_decision}"],
        }
        write_json(result_root / "runtime_closure_repair_rc1/w4_aggregation_status_v2.json", payload)
        return payload
    pathology_results = [validate_pathology_outputs(result_root, pathology) for pathology in PATHOLOGIES]
    blockers = [blocker for row in pathology_results for blocker in row["blockers"]]
    payload = {
        "schema_version": 1,
        "timestamp_utc": utc_now(),
        "decision": "PASS_READY_FOR_STRICT_VALIDATOR" if not blockers else "NEEDS_REPAIR_W4_OUTPUTS",
        "formal_terminal_accounting_decision": terminal_decision,
        "completion_claim": False,
        "pathology_results": pathology_results,
        "blockers": blockers,
    }
    write_json(result_root / "runtime_closure_repair_rc1/w4_aggregation_status_v2.json", payload)
    return payload


def contract() -> dict[str, Any]:
    return {
        "entrypoint": "scripts/evaluation/aggregate_care_srr_cascade_w4.py",
        "requires_w3_terminal_accounting_pass": True,
        "calibration_candidates": SIX_CANDIDATES,
        "audit_used_for_selection": False,
        "final_decisions": FINAL_DECISIONS,
        "monitor_packet_marked_complete_forbidden": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--result-root", type=Path, default=RESULT)
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(contract(), indent=2, sort_keys=True))
        return 0
    payload = aggregate(args.result_root)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["decision"] in {"PASS_READY_FOR_STRICT_VALIDATOR", "NEEDS_MONITOR_W3_NOT_TERMINAL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
