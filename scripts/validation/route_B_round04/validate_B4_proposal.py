#!/usr/bin/env python3
"""Strict Route B Round04 B4 proposal validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B4_PROPOSAL_STAGE_COMPLETE"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    required = [
        "oof_shard_manifest.json",
        "prototype_bank_inventory.csv",
        "prototype_leakage_audit.json",
        "hard_negative_queue_receipt.json",
        "proposal_metrics.csv",
        "soft_roi_coverage.csv",
        "proposal_final_effect.csv",
        "selected_checkpoint_reload.json",
        "training_adequacy.csv",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    oof = load_json(result_dir / "oof_shard_manifest.json")
    inventory = read_csv_rows(result_dir / "prototype_bank_inventory.csv")
    leakage = load_json(result_dir / "prototype_leakage_audit.json")
    negatives = load_json(result_dir / "hard_negative_queue_receipt.json")
    metrics = read_csv_rows(result_dir / "proposal_metrics.csv")
    coverage = read_csv_rows(result_dir / "soft_roi_coverage.csv")
    effects = read_csv_rows(result_dir / "proposal_final_effect.csv")
    reload = load_json(result_dir / "selected_checkpoint_reload.json")
    training = read_csv_rows(result_dir / "training_adequacy.csv")[0]
    completion = load_json(result_dir / "completion.json")

    if leakage.get("current_case_leakage") or not oof.get("current_case_excluded"):
        add(errors, "OOF_CURRENT_CASE_LEAKAGE", "current case leakage detected")
    if leakage.get("validation_or_test_leakage") or not oof.get("validation_or_test_excluded"):
        add(errors, "OOF_VALIDATION_OR_TEST_LEAKAGE", "validation/test leakage detected")
    if any(row.get("bootstrap") == "True" or row.get("ema") == "True" for row in inventory):
        add(errors, "BOOTSTRAP_OR_EMA_FORMAL_BANK", "bootstrap/EMA formal prototype bank used")
    if not negatives.get("edema_safe_negative_t2_present_only"):
        add(errors, "NO_T2_EDEMA_NEGATIVE", "edema negatives are not T2-present safe negatives")
    if any(row.get("similarity_connected") != "True" for row in metrics):
        add(errors, "PROTOTYPE_SIMILARITY_DISCONNECTED", "proposal similarity disconnected")
    if any(row.get("constant") == "True" for row in metrics):
        add(errors, "CONSTANT_PROPOSAL", "constant proposal detected")
    if negatives.get("hard_roi_deletion") or any(row.get("hard_roi_deleted") == "True" for row in coverage):
        add(errors, "HARD_ROI_DELETION", "hard ROI deletion detected")
    if any(float(row.get("coverage", 0.0) or 0.0) <= 0 for row in coverage):
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "soft ROI coverage missing")
    if any(float(row.get("final_effect_l1", 0.0) or 0.0) <= 0 for row in effects):
        add(errors, "PROTOTYPE_SIMILARITY_DISCONNECTED", "proposal has no final effect")
    if float(training.get("optimizer_steps", 0) or 0) < 8000:
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "optimizer steps below B4 minimum")
    if float(training.get("train_loop_seconds", 0) or 0) < 2400:
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "train seconds below B4 minimum")
    if int(float(training.get("validation_events", 0) or 0)) < 4:
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "validation events below B4 minimum")
    if int(float(training.get("eval_cases", 0) or 0)) < 44:
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "eval cases below B4 minimum")
    if str(training.get("loss_decrease")) != "True":
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "loss did not decrease")
    if reload.get("status") != "PASS":
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "checkpoint reload failed")
    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "WEAK_VALID_PROPOSAL_PREMATURE_STOP", "completion token/status mismatch")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "failure_keys": sorted({e["key"] for e in errors}),
        "completion_token": completion.get("completion_token"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--require-token", default=READY_TOKEN)
    args = parser.parse_args()
    report = validate(args.input, args.require_token)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if args.strict and report["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
