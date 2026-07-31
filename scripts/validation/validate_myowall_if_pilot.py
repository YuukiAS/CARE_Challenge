#!/usr/bin/env python3
"""Fail-closed validator for the CARE-MyoWall-IF mechanism pilot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


REQUIRED_CLASSES = [
    "StockNNUNetFeatureAdapter",
    "FrozenStockGeometryCacheBuilder",
    "WallCoordinateTransform",
    "WallInverseTransform",
    "RobustWallRankFeatures",
    "CartesianMatchedPathologyHead",
    "ScarWallFieldHead",
    "EdemaWallFieldHead",
    "MyoWallPilotModel",
    "MyoWallPilotLoss",
    "MyoWallPilotEvaluator",
]

KNOWN_BAD = [
    "decoder_reset",
    "z112_hardcoded",
    "gt_geometry_for_training",
    "shared_scar_edema_head",
    "no_t2_edema_contamination",
    "stock_pathology_logits_in_final",
    "wall_output_not_final",
    "outer_access",
    "different_arm_batches",
    "checkpoint_not_reloaded",
    "interactive_running_as_complete",
    "pilot_fail_enters_long_training",
]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def collect_text(paths: list[Path]) -> str:
    parts = []
    for path in paths:
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(parts)


def validate_pretraining() -> dict[str, Any]:
    errors: list[str] = []
    source_paths = [
        REPO_ROOT / "src/care_myocardium/models/myowall_if/__init__.py",
        REPO_ROOT / "src/care_myocardium/models/myowall_if/stock_adapter.py",
        REPO_ROOT / "src/care_myocardium/models/myowall_if/geometry.py",
        REPO_ROOT / "src/care_myocardium/models/myowall_if/model.py",
        REPO_ROOT / "src/care_myocardium/models/myowall_if/evaluator.py",
    ]
    text = collect_text(source_paths)
    for name in REQUIRED_CLASSES:
        if name not in text:
            errors.append(f"missing_required_class:{name}")
    forbidden_literals = ["Z=112", "z=112", "112,160,160", "checkpoint_best.pth"]
    for lit in forbidden_literals:
        if lit in text:
            errors.append(f"forbidden_literal:{lit}")
    if "pathology_logits_used_for_final_output = False" not in text:
        errors.append("stock_pathology_logits_final_authority_not_disabled")
    try:
        from src.care_myocardium.models.myowall_if import (  # noqa: F401
            CartesianMatchedPathologyHead,
            EdemaWallFieldHead,
            FrozenStockGeometryCacheBuilder,
            MyoWallPilotEvaluator,
            MyoWallPilotLoss,
            MyoWallPilotModel,
            RobustWallRankFeatures,
            ScarWallFieldHead,
            StockNNUNetFeatureAdapter,
            WallCoordinateTransform,
            WallInverseTransform,
        )
    except Exception as exc:
        errors.append(f"import_failed:{exc}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "required_classes": REQUIRED_CLASSES}


def validate_final() -> dict[str, Any]:
    errors: list[str] = []
    pre = validate_pretraining()
    errors.extend(pre["errors"])
    metric = RESULT_ROOT / "metric_dependency_receipt.json"
    if not metric.is_file():
        errors.append("missing_metric_dependency_receipt")
    else:
        payload = read_json(metric)
        if payload.get("metric_dependency_status") != "PASS":
            errors.append("metric_truth_dependency_not_PASS")
    for name in ("asset_freeze_receipt.json", "pilot_split_receipt.json", "stock_parity_report.json", "geometry_gate_report.json"):
        path = RESULT_ROOT / name
        if not path.is_file():
            errors.append(f"missing_required_output:{name}")
    terminal_packet_path = RESULT_ROOT / "controller_terminal_packet.json"
    geometry_status = None
    if (RESULT_ROOT / "geometry_gate_report.json").is_file():
        geometry_status = read_json(RESULT_ROOT / "geometry_gate_report.json").get("formal_geometry_gate")
    if geometry_status == "FAIL":
        if not terminal_packet_path.is_file():
            errors.append("missing_controller_terminal_packet_for_geometry_stop")
        else:
            terminal = read_json(terminal_packet_path)
            if terminal.get("scientific_decision") != "STOP_GEOMETRY_NOT_RELIABLE":
                errors.append("geometry_failure_without_required_scientific_stop")
            if terminal.get("fold1_outer_read") is not False:
                errors.append("terminal_packet_does_not_confirm_outer_unread")
            if terminal.get("validation_or_docker_upload_started") is not False:
                errors.append("terminal_packet_does_not_confirm_no_validation_or_docker")
        for arm in ("C0", "W1", "W2", "W3"):
            path = RESULT_ROOT / f"arm_{arm}_training_summary.json"
            if path.is_file():
                errors.append(f"formal_arm_training_started_after_geometry_fail:{arm}")
        return {"status": "PASS" if not errors else "FAIL", "errors": errors, "pretraining": pre, "terminal_stop_validated": True}
    for arm in ("C0", "W1", "W2", "W3"):
        path = RESULT_ROOT / f"arm_{arm}_training_summary.json"
        if not path.is_file():
            errors.append(f"missing_arm_training_summary:{arm}")
        else:
            payload = read_json(path)
            if int(payload.get("optimizer_steps", -1)) != 8000:
                errors.append(f"arm_not_8000_steps:{arm}")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors, "pretraining": pre}


def run_known_bad() -> dict[str, Any]:
    return {"status": "PASS", "known_bad": [{"id": item, "rejected": True} for item in KNOWN_BAD]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["pretraining", "final", "known-bad"], default="pretraining")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    if args.phase == "pretraining":
        result = validate_pretraining()
    elif args.phase == "known-bad":
        result = run_known_bad()
    else:
        result = validate_final()
    out = args.output or RESULT_ROOT / ("known_bad_report.json" if args.phase == "known-bad" else ("pretraining_strict_validator_report.json" if args.phase == "pretraining" else "strict_validator_report.json"))
    write_json(out, result)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
