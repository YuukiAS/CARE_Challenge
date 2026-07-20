#!/usr/bin/env python3
"""Strict Route B Round04 B5 refiner validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B5_REFINER_STAGE_COMPLETE"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    required = [
        "training_adequacy.csv",
        "scar_refiner_metrics.csv",
        "edema_refiner_metrics.csv",
        "proposal_to_final_retention.csv",
        "remote_fp_and_component_matrix.csv",
        "no_t2_safety.csv",
        "refiner_final_effect.csv",
        "selected_checkpoint_reload.json",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    training = read_csv_rows(result_dir / "training_adequacy.csv")[0]
    scar = read_csv_rows(result_dir / "scar_refiner_metrics.csv")
    edema = read_csv_rows(result_dir / "edema_refiner_metrics.csv")
    retention = read_csv_rows(result_dir / "proposal_to_final_retention.csv")
    remote = read_csv_rows(result_dir / "remote_fp_and_component_matrix.csv")
    no_t2 = read_csv_rows(result_dir / "no_t2_safety.csv")
    effects = read_csv_rows(result_dir / "refiner_final_effect.csv")
    reload = load_json(result_dir / "selected_checkpoint_reload.json")
    completion = load_json(result_dir / "completion.json")

    if not scar or not edema or scar[0].get("separate_refiner") != "True" or edema[0].get("separate_refiner") != "True":
        add(errors, "SHARED_UNDIFFERENTIATED_REFINER", "scar/edema refiners are not separated")
    if any(float(row.get("final_effect_l1", 0.0) or 0.0) <= 0 for row in effects):
        add(errors, "REFINER_FINAL_EFFECT_ZERO", "refiner final effect is zero")
    if any(float(row.get("retention", 0.0) or 0.0) <= 0 for row in retention):
        add(errors, "PROPOSAL_TO_FINAL_RETENTION_FAILED", "proposal-to-final retention failed")
    if any(row.get("target") == "scar" and row.get("remote_fp_regression") == "True" for row in remote):
        add(errors, "SCAR_REMOTE_FP_REGRESSION", "scar remote FP regression detected")
    if any(float(row.get("edema_delta_abs_max", 1.0) or 1.0) != 0.0 for row in no_t2):
        add(errors, "NO_T2_EDEMA_NONZERO", "no-T2 edema delta nonzero")
    if any(row.get("hard_roi_deleted") == "True" for row in retention):
        add(errors, "HARD_ROI_DELETION", "hard ROI deletion detected")
    if not (result_dir.parent / "B4" / "completion.json").is_file():
        add(errors, "WEAK_B4_CONTROL_MISSING", "B4 control evidence missing")
    if float(training.get("optimizer_steps", 0) or 0) < 10000:
        add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", "optimizer steps below B5 minimum")
    if float(training.get("train_loop_seconds", 0) or 0) < 3000:
        add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", "train seconds below B5 minimum")
    if int(float(training.get("validation_events", 0) or 0)) < 5:
        add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", "validation events below B5 minimum")
    if int(float(training.get("eval_cases", 0) or 0)) < 44:
        add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", "eval cases below B5 minimum")
    if str(training.get("loss_decrease")) != "True":
        add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", "loss did not decrease")
    if reload.get("status") != "PASS":
        add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", "checkpoint reload failed")
    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "WEAK_FAITHFUL_REFINER_PREMATURE_STOP", "completion token/status mismatch")

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
