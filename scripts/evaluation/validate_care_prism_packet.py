#!/usr/bin/env python
"""Fail-closed validator for CARE-PRISM W1/W2 result packets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_W1 = [
    "adoption_receipt.json",
    "backbone_asset_resolution.json",
    "controller_context.json",
    "init_transplant_report_fold0.json",
    "init_transplant_report_fold1.json",
    "multiscale_usage_report.json",
    "data_pipeline_report.json",
    "loss_and_negative_space_report.json",
    "implementation_intervention_report.json",
    "known_bad_report.json",
    "checkpoint_resume_report.json",
    "implementation_validator_report.json",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, required=True)
    parser.add_argument("--stage", choices=["W1"], default="W1")
    args = parser.parse_args()
    errors: list[str] = []
    reports: dict[str, dict[str, Any]] = {}
    for name in REQUIRED_W1:
        path = args.result_root / name
        if not path.exists():
            errors.append(f"missing required W1 file: {name}")
            continue
        try:
            reports[name] = read_json(path)
        except Exception as exc:
            errors.append(f"invalid JSON {name}: {exc}")
    for name, payload in reports.items():
        if name.endswith("_report.json") or name in {"backbone_asset_resolution.json", "implementation_validator_report.json"}:
            status = payload.get("status")
            if status not in {"PASS", "PASS_PLAN_DRIVEN_STOCK_NNUNET", None}:
                errors.append(f"{name} status is {status!r}")
    for name in ("init_transplant_report_fold0.json", "init_transplant_report_fold1.json"):
        payload = reports.get(name, {})
        if float(payload.get("transplant", {}).get("byte_coverage", 0.0)) < 0.99:
            errors.append(f"{name} byte coverage below 0.99")
        if float(payload.get("fp32_encoder_parity", {}).get("max_abs_error", 1.0)) > 1.0e-6:
            errors.append(f"{name} FP32 parity above 1e-6")
    loss = reports.get("loss_and_negative_space_report.json", {})
    data = reports.get("data_pipeline_report.json", {})
    if float(loss.get("no_t2_edema_probability_max", 1.0)) != 0.0:
        errors.append("no-T2 edema probability is not exact zero")
    if float(loss.get("no_t2_edema_refiner_grad_abs", 1.0)) != 0.0:
        errors.append("no-T2 edema gradient is not exact zero")
    if float(loss.get("scar_negative_target_sum", 0.0)) <= 0.0 or float(loss.get("edema_negative_target_sum", 0.0)) <= 0.0:
        errors.append("negative-space targets are empty")
    if float(data.get("edema_negative_target_sum_t2_case", 0.0)) <= 0.0:
        errors.append("real Dataset501 T2-present edema negative target is empty")
    decision = "PASS" if not errors else "FAIL"
    out = {"status": decision, "errors": errors, "validated_files": REQUIRED_W1}
    (args.result_root / "strict_validator_report.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(out, sort_keys=True))
    raise SystemExit(0 if decision == "PASS" else 1)


if __name__ == "__main__":
    main()
