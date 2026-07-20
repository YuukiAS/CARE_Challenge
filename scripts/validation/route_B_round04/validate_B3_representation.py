#!/usr/bin/env python3
"""Strict Route B Round04 B3 representation validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B3_REPRESENTATION_READY_FOR_PROPOSAL"


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
        "sampler_receipt.json",
        "router_slot_evidence.csv",
        "pattern_sip_gradient.csv",
        "learned_anatomy_metrics.csv",
        "no_t2_safety.csv",
        "selected_checkpoint_reload.json",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "FORMAL_TRAINING_INADEQUATE", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    training = read_csv_rows(result_dir / "training_adequacy.csv")[0]
    sampler = load_json(result_dir / "sampler_receipt.json")
    slots = read_csv_rows(result_dir / "router_slot_evidence.csv")
    gradients = read_csv_rows(result_dir / "pattern_sip_gradient.csv")
    anatomy = read_csv_rows(result_dir / "learned_anatomy_metrics.csv")
    no_t2 = read_csv_rows(result_dir / "no_t2_safety.csv")
    reload = load_json(result_dir / "selected_checkpoint_reload.json")
    completion = load_json(result_dir / "completion.json")

    if completion.get("completion_token") == "ROUTE_B_ROUND03_B3_GLOBAL_STOP":
        add(errors, "ROUND03_B3_GLOBAL_STOP_REUSED", "Round03 terminal token reused")
    if sampler.get("sampler_contract") != "myops_fold0_primary_44" or int(sampler.get("case_count", 0)) < 44:
        add(errors, "SAMPLER_CONTRACT_MISMATCH", "sampler contract/case count mismatch")
    if float(training.get("optimizer_steps", 0) or 0) < 6000:
        add(errors, "FORMAL_TRAINING_INADEQUATE", "optimizer steps below B3 minimum")
    if float(training.get("train_loop_seconds", 0) or 0) < 1800:
        add(errors, "FORMAL_TRAINING_INADEQUATE", "train seconds below B3 minimum")
    if int(float(training.get("validation_events", 0) or 0)) < 3:
        add(errors, "FORMAL_TRAINING_INADEQUATE", "validation events below B3 minimum")
    if int(float(training.get("eval_cases", 0) or 0)) < 44:
        add(errors, "FORMAL_TRAINING_INADEQUATE", "eval cases below B3 minimum")
    if str(training.get("loss_decrease")) != "True":
        add(errors, "FORMAL_TRAINING_INADEQUATE", "loss did not decrease")
    if any(row.get("availability") == "0" and float(row.get("max_weight", 1.0) or 1.0) > 1e-6 for row in slots):
        add(errors, "INVALID_SLOT_WEIGHT_NONZERO", "invalid modality slot has nonzero weight")
    if any(float(row.get("edema_delta_abs_max", 1.0) or 1.0) != 0.0 for row in no_t2):
        add(errors, "NO_T2_EDEMA_NONZERO", "no-T2 edema delta is nonzero")
    if not gradients or any(float(row.get("grad_l1", 0.0) or 0.0) <= 0 for row in gradients):
        add(errors, "ROUTER_FAMILY_GRADIENT_MISSING", "representation gradient missing")
    if not anatomy or any(row.get("finite") != "True" or float(row.get("std", 0.0) or 0.0) <= 0 for row in anatomy):
        add(errors, "LEARNED_ANATOMY_NONFINITE_OR_CONSTANT", "learned anatomy representation invalid")
    if completion.get("completion_token") in {"ROUTE_B_READY_FOR_REVIEW", "ROUTE_B_NEGATIVE"}:
        add(errors, "B3_FULL_ROUTE_NEGATIVE_TOKEN_FORBIDDEN", "B3 emitted full-route terminal token")
    if reload.get("status") != "PASS":
        add(errors, "FORMAL_TRAINING_INADEQUATE", "checkpoint reload failed")
    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "FORMAL_TRAINING_INADEQUATE", "completion token/status mismatch")

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
