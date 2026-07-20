#!/usr/bin/env python3
"""Strict Route B Round04 B7 CineMA matched-control validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B7_CINEMA_MATCHED_CONTROL_COMPLETE"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    required = [
        "cinema_provenance.json",
        "pretrained_random_match_receipt.json",
        "adapter_training_adequacy.csv",
        "checkpoint_selection.csv",
        "selected_checkpoint_reload.json",
        "per_frame_feature_manifest.csv",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    provenance = load_json(result_dir / "cinema_provenance.json")
    match = load_json(result_dir / "pretrained_random_match_receipt.json")
    training = read_csv_rows(result_dir / "adapter_training_adequacy.csv")
    selection = read_csv_rows(result_dir / "checkpoint_selection.csv")
    reload = load_json(result_dir / "selected_checkpoint_reload.json")
    features = read_csv_rows(result_dir / "per_frame_feature_manifest.csv")[0]
    completion = load_json(result_dir / "completion.json")

    if provenance.get("status") != "PASS" or provenance.get("weight_sha256_observed") != provenance.get("weight_sha256_required"):
        add(errors, "FAKE_CINEMA_SOURCE_OR_WRONG_SHA", "CineMA source or weight SHA mismatch")
    if not provenance.get("license_or_commit_recorded") or not provenance.get("code_commit"):
        add(errors, "CINEMA_LICENSE_OR_COMMIT_MISSING", "license/commit provenance missing")
    if not match.get("architecture_match"):
        add(errors, "PRETRAINED_RANDOM_ARCHITECTURE_MISMATCH", "parameter-count architecture match failed")
    if not match.get("downstream_initialization_match"):
        add(errors, "DOWNSTREAM_INITIALIZATION_MISMATCH", "downstream initialization mismatch")
    if not match.get("source_initialization_only_difference"):
        add(errors, "SOURCE_INITIALIZATION_NOT_ONLY_DIFFERENCE", "source init not only difference")
    if len(training) != 2 or {row.get("source") for row in training} != {"official_pretrained", "matched_random"}:
        add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", "training rows missing both sources")
    for row in training:
        if float(row.get("optimizer_steps", 0) or 0) < 8000:
            add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", f"{row.get('source')} steps below B7 minimum")
        if float(row.get("train_loop_seconds", 0) or 0) < 3600:
            add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", f"{row.get('source')} train seconds below B7 minimum")
        if int(float(row.get("validation_events", 0) or 0)) < 4:
            add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", f"{row.get('source')} validation events below B7 minimum")
        if int(float(row.get("eval_cases", 0) or 0)) < 12:
            add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", f"{row.get('source')} eval cases below B7 minimum")
        if str(row.get("loss_decrease")) != "True":
            add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", f"{row.get('source')} loss did not decrease")
    if reload.get("status") != "PASS":
        add(errors, "SELECTED_CHECKPOINT_NOT_RELOADED", "selected checkpoint reload failed")
    if not any(row.get("selected") == "True" and row.get("source") == "official_pretrained" for row in selection):
        add(errors, "SELECTED_CHECKPOINT_NOT_RELOADED", "official checkpoint not selected")
    if int(float(features.get("case_count", 0) or 0)) < 12:
        add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", "per-frame manifest case count below B7 minimum")
    if "internal_small_wrapper" in json.dumps(provenance).lower():
        add(errors, "INTERNAL_SMALL_WRAPPER_USED_AS_OFFICIAL", "internal wrapper presented as official")
    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "CASES_FRAMES_OPTIMIZER_BUDGET_MISMATCH", "completion token/status mismatch")

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
