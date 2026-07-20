#!/usr/bin/env python3
"""Strict Route B Round04 B8 Cine registration validator."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B8_REGISTRATION_STAGE_COMPLETE"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def finite(value: Any) -> bool:
    return math.isfinite(as_float(value, float("nan")))


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    required = [
        "registration_training_adequacy.json",
        "selected_checkpoint_reload.json",
        "registration_pair_receipts.csv",
        "registration_case_full_gate.csv",
        "jacobian_histograms.json",
        "inverse_consistency.csv",
        "real_syn_control.csv",
        "registration_method_decision.json",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    training = load_json(result_dir / "registration_training_adequacy.json")
    reload = load_json(result_dir / "selected_checkpoint_reload.json")
    pairs = read_csv_rows(result_dir / "registration_pair_receipts.csv")
    cases = read_csv_rows(result_dir / "registration_case_full_gate.csv")
    jacobian = load_json(result_dir / "jacobian_histograms.json")
    inverse = read_csv_rows(result_dir / "inverse_consistency.csv")
    syn = read_csv_rows(result_dir / "real_syn_control.csv")
    decision = load_json(result_dir / "registration_method_decision.json")
    completion = load_json(result_dir / "completion.json")

    if int(training.get("integration_steps", 0)) == 0 or training.get("uses_direct_velocity_as_displacement"):
        add(errors, "DIRECT_VELOCITY_AS_DISPLACEMENT", "velocity used directly or integration skipped")
    if int(training.get("integration_steps", 0)) != 7:
        add(errors, "SCALING_SQUARING_STEPS_NOT_SEVEN", "B8 requires exactly seven scaling-and-squaring steps")
    if as_float(training.get("optimizer_steps")) < 25000:
        add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", "optimizer steps below B8 minimum")
    if as_float(training.get("train_loop_seconds")) < 7200:
        add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", "train seconds below B8 minimum")
    if int(as_float(training.get("validation_events"))) < 10:
        add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", "validation events below B8 minimum")
    if int(as_float(training.get("eval_cases"))) < 12:
        add(errors, "FULL_DENOMINATOR_MISSING", "eval case count below B8 minimum")
    if int(as_float(training.get("pair_receipts"))) < 60 or len(pairs) < 60:
        add(errors, "PAIR_AS_CASE_AGGREGATION", "pair receipts below B8 minimum")
    if training.get("loss_decrease") is not True:
        add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", "loss did not decrease")

    if reload.get("status") != "PASS":
        add(errors, "SELECTED_REGISTRATION_NOT_RELOADED", "selected registration checkpoint reload failed")

    case_ids = {row.get("case_id") for row in cases if row.get("case_id")}
    pair_case_ids = {row.get("case_id") for row in pairs if row.get("case_id")}
    if len(case_ids) < 12 or len(pair_case_ids) < 12:
        add(errors, "FULL_DENOMINATOR_MISSING", "case denominator misses eligible cases")
    if any(row.get("full_denominator_present") != "True" for row in cases):
        add(errors, "FULL_DENOMINATOR_MISSING", "full denominator flag missing")
    if any(row.get("pair_as_case_aggregation") == "True" for row in cases + pairs):
        add(errors, "PAIR_AS_CASE_AGGREGATION", "pair rows were aggregated as cases")
    if sum(row.get("full_case_event") == "True" for row in cases) < 4:
        add(errors, "FULL_DENOMINATOR_MISSING", "full-case event coverage below B8 minimum")

    for row in pairs:
        if row.get("direct_velocity_as_displacement") == "True":
            add(errors, "DIRECT_VELOCITY_AS_DISPLACEMENT", "pair row marks direct velocity displacement")
        if int(as_float(row.get("integration_steps"))) != 7:
            add(errors, "SCALING_SQUARING_STEPS_NOT_SEVEN", "pair row integration step mismatch")
        if row.get("true_jacobian") != "True" or row.get("physical_displacement_mm") != "True":
            add(errors, "PROXY_JACOBIAN", "pair row lacks true physical Jacobian evidence")
        if not finite(row.get("minimum_jacobian")):
            add(errors, "PROXY_JACOBIAN", "nonfinite Jacobian value")
    if jacobian.get("proxy_jacobian") is True or jacobian.get("source") != "finite_difference_displacement_gradient":
        add(errors, "PROXY_JACOBIAN", "Jacobian source is proxy or mislabeled")
    if not finite(jacobian.get("minimum_jacobian")):
        add(errors, "PROXY_JACOBIAN", "Jacobian histogram minimum is nonfinite")

    if len(inverse) < 60 or any(row.get("composition_checked") != "True" for row in inverse):
        add(errors, "INVERSE_CONSISTENCY_MISSING", "inverse consistency rows missing composition checks")
    if any(not finite(row.get("inverse_consistency_l1")) for row in inverse):
        add(errors, "INVERSE_CONSISTENCY_MISSING", "inverse consistency value nonfinite")

    if len(syn) < 12:
        add(errors, "SYN_OUTPUT_COPIED_OR_PROXY", "SyN control denominator below 12 cases")
    if any(row.get("copied_or_proxy") == "True" or row.get("uses_proxy_after_metric") == "True" for row in syn):
        add(errors, "SYN_OUTPUT_COPIED_OR_PROXY", "SyN row copied/proxy flag set")
    selected = decision.get("decision") in {"LEARNED_REGISTRATION_SELECTED", "SYN_REGISTRATION_SELECTED"}
    if selected:
        if not all(row.get("syn_executed") == "True" for row in syn):
            add(errors, "SYN_OUTPUT_COPIED_OR_PROXY", "selected method lacks executed SyN control")
        if not all("antsRegistration" in row.get("command", "") for row in syn):
            add(errors, "SYN_OUTPUT_COPIED_OR_PROXY", "selected method lacks ANTs command evidence")
    elif decision.get("decision") == "CINE_REGISTRATION_BLOCKER":
        if decision.get("learned_runtime_faithful") is not True:
            add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", "blocker claimed without faithful learned runtime")
        if not all(row.get("attempted") == "True" and row.get("failure_rows_recorded") == "True" for row in syn):
            add(errors, "SYN_OUTPUT_COPIED_OR_PROXY", "blocker lacks recorded SyN attempt denominator")
    else:
        add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", "unknown registration method decision")

    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "REGISTRATION_BLOCKER_WITHOUT_FAITHFUL_RUNTIME", "completion token/status mismatch")

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "failure_keys": sorted({e["key"] for e in errors}),
        "completion_token": completion.get("completion_token"),
        "method_decision": decision.get("decision"),
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
