#!/usr/bin/env python3
"""Strict Route B Round04 B1 anatomy repair validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B1_ANATOMY_REPAIR_IMPLEMENTED"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    required = [
        "anatomy_target_roundtrip.json",
        "anatomy_microset_metrics.csv",
        "anatomy_gradient_receipt.csv",
        "anatomy_intervention_receipt.csv",
        "save_reload_report.json",
        "training_adequacy.csv",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "ANATOMY_MICRO_OVERFIT_INADEQUATE", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    target = load_json(result_dir / "anatomy_target_roundtrip.json")
    metrics = read_csv_rows(result_dir / "anatomy_microset_metrics.csv")
    grads = read_csv_rows(result_dir / "anatomy_gradient_receipt.csv")
    interventions = read_csv_rows(result_dir / "anatomy_intervention_receipt.csv")
    reload = load_json(result_dir / "save_reload_report.json")
    training = read_csv_rows(result_dir / "training_adequacy.csv")[0]
    completion = load_json(result_dir / "completion.json")

    if target.get("compact_union_labels") != [1, 4, 5] or int(target.get("union_positive_voxels", 0)) <= 0:
        add(errors, "PURE_MYOCARDIUM_UNION_TARGET", "union target excludes scar/edema or is empty")
    metric_map = {row["target"]: float(row["dice"]) for row in metrics}
    if metric_map.get("union", 0.0) < 0.20:
        add(errors, "ANATOMY_MICRO_OVERFIT_INADEQUATE", "union dice below minimum")
    if float(training.get("optimizer_steps", 0) or 0) < float(training.get("required_optimizer_steps", 10**12) or 10**12):
        add(errors, "ANATOMY_MICRO_OVERFIT_INADEQUATE", "steps below required")
    if float(training.get("train_loop_seconds", 0) or 0) < float(training.get("required_train_loop_seconds", 10**12) or 10**12):
        add(errors, "ANATOMY_MICRO_OVERFIT_INADEQUATE", "train seconds below required")
    if int(float(training.get("validation_events", 0) or 0)) < int(float(training.get("required_validation_events", 10**12) or 10**12)):
        add(errors, "ANATOMY_MICRO_OVERFIT_INADEQUATE", "validation events below required")
    if str(training.get("loss_decrease")) != "True":
        add(errors, "ANATOMY_MICRO_OVERFIT_INADEQUATE", "loss did not decrease")
    grad_map = {row["branch"]: float(row["grad_l1"]) for row in grads}
    if grad_map.get("routed", 0.0) <= 0:
        add(errors, "ROUTED_ANATOMY_GRADIENT_MISSING", "routed grad is zero")
    if grad_map.get("lateral", 0.0) <= 0:
        add(errors, "LATERAL_ANATOMY_GRADIENT_MISSING", "lateral grad is zero")
    if any(str(row.get("became_final_base")) == "True" for row in interventions):
        add(errors, "ANCHOR_SUPPORT_FLOOR_BECAME_FINAL_BASE", "anchor floor became final base")
    if reload.get("status") != "PASS" or float(reload.get("reload_max_abs_diff", 1.0)) > 1e-6:
        add(errors, "SAVE_RELOAD_MISMATCH", "save reload mismatch")
    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "ANATOMY_MICRO_OVERFIT_INADEQUATE", "completion token/status mismatch")

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
