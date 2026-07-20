#!/usr/bin/env python3
"""Strict Route B Round04 B2 implementation freeze validator."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


READY_TOKEN = "ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def add(errors: list[dict[str, str]], key: str, detail: str) -> None:
    errors.append({"key": key, "detail": detail})


def validate(result_dir: Path, require_token: str) -> dict[str, Any]:
    required = [
        "implementation_snapshot.md",
        "tensor_contract.json",
        "forward_gradient_intervention.csv",
        "save_reload_export_report.json",
        "cinema_source_fidelity.json",
        "registration_temporal_smoke.json",
        "route_local_mapper_draft.md",
        "completion.json",
    ]
    errors: list[dict[str, str]] = []
    for name in required:
        if not (result_dir / name).is_file():
            add(errors, "DISCONNECTED_RETRIEVAL_PROPOSAL_REFINER", f"missing {name}")
    if errors:
        return {"status": "FAIL", "errors": errors, "failure_keys": sorted({e["key"] for e in errors})}

    tensor = load_json(result_dir / "tensor_contract.json")
    forward = read_csv_rows(result_dir / "forward_gradient_intervention.csv")
    reload = load_json(result_dir / "save_reload_export_report.json")
    cinema = load_json(result_dir / "cinema_source_fidelity.json")
    reg = load_json(result_dir / "registration_temporal_smoke.json")
    completion = load_json(result_dir / "completion.json")

    if tensor.get("modality_order") != ["LGE", "T2", "C0"] or tensor.get("scale_channels") != [32, 64, 128, 256]:
        add(errors, "NNUNET_ONLY_BYPASS", "SRR-v3 tensor contract not present")
    if tensor.get("experts_per_scale") != 16 or tensor.get("expert_families_per_scale") != 16:
        add(errors, "DISCONNECTED_RETRIEVAL_PROPOSAL_REFINER", "expert structure mismatch")
    if float(tensor.get("invalid_weight_max", 1.0)) > 1e-6:
        add(errors, "INVALID_SLOT_WEIGHT_NONZERO", "invalid slot weight nonzero")
    if float(tensor.get("route_b_owned_changed_logit_l1", 0.0)) <= 0:
        add(errors, "DISCONNECTED_RETRIEVAL_PROPOSAL_REFINER", "final logits unchanged")
    rows = {row["component"]: row for row in forward}
    if float(rows.get("myops_final_logits", {}).get("grad_l1", 0.0) or 0.0) <= 0:
        add(errors, "PATTERN_SIP_ALIAS_OR_NO_GRADIENT", "MyoPS gradient missing")
    if float(rows.get("no_t2_edema_guard", {}).get("delta_abs_max", 1.0) or 1.0) != 0.0:
        add(errors, "OFFICIAL_LABEL_ROUNDTRIP_FAILED", "no-T2 edema guard violated")
    if cinema.get("status") != "PASS" or cinema.get("weight_sha256_observed") != cinema.get("weight_sha256_required"):
        add(errors, "FAKE_CINEMA_SOURCE_OR_WRONG_SHA", "official CineMA source/weight failed")
    if cinema.get("route_local_decoder_feature_shape", [None, None])[1] != 32:
        add(errors, "FAKE_CINEMA_SOURCE_OR_WRONG_SHA", "Cine decoder feature shape mismatch")
    if int(reg.get("registration_integration_steps", 0)) != 7:
        add(errors, "DIRECT_VELOCITY_AS_DISPLACEMENT", "registration integration steps mismatch")
    if "minimum_jacobian" not in reg or "folding_rate" not in reg:
        add(errors, "DIRECT_VELOCITY_AS_DISPLACEMENT", "Jacobian evidence missing")
    if len(reg.get("temporal_required_fields", [])) != 14:
        add(errors, "TEMPORAL_REQUIRED_INPUT_UNCONSUMED", "temporal input fields missing")
    if reload.get("status") != "PASS":
        add(errors, "LEGACY_ROUND03_WRAPPER_BYPASS", "save/reload/export report failed")
    if completion.get("completion_token") != require_token or require_token != READY_TOKEN or completion.get("status") != "PASS":
        add(errors, "LEGACY_ROUND03_WRAPPER_BYPASS", "completion token/status mismatch")

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
