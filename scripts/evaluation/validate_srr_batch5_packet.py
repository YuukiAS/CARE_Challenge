#!/usr/bin/env python3
"""Strict validator for CARE SRR Batch5 diagnostic repair packets."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260721_srr_batch5_post_batch4_diagnostic_repair"
EXPECTED_CHECKPOINT_SHA = "bc325754202d5cf0aa59aa8fab0306b38c2665640339afa3f8d06a13c70009f6"
MODES = {
    "anchor_identity_control",
    "anchor_bounded_full",
    "srr_no_anchor_control",
    "anchor_bounded_proposal_only",
    "anchor_bounded_refiner_only",
    "production_gate_closed",
    "production_gate_open_bounded_control",
}
DECISIONS = {
    "B5_FINAL_OBJECTIVE_ALIGNMENT_BOTTLENECK",
    "B5_OUTPUT_AUTHORITY_BOTTLENECK",
    "B5_PROPOSAL_PRECISION_BOTTLENECK",
    "B5_REFINER_EFFECTIVENESS_BOTTLENECK",
    "B5_EVALUATION_SEMANTICS_ONLY_ISSUE",
    "B5_INSUFFICIENT_MECHANISM_EVIDENCE",
}
REQUIRED = (
    "implementation_snapshot.md",
    "evaluation_semantics_audit.md",
    "loss_authority_audit.md",
    "loss_parameter_gradient_matrix.csv",
    "loss_directionality_audit.csv",
    "checkpoint_reranking.csv",
    "mode_intervention_metrics.csv",
    "casewise_mechanism_attribution.csv",
    "oracle_headroom.csv",
    "prototype_manifest_audit.json",
    "batch6_unique_repair_decision.md",
    "mapper_report_final.md",
    "controller_report.md",
    "completion_check.md",
    "MANIFEST.md",
)


class ValidationError(RuntimeError):
    pass


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise ValidationError(f"missing required JSON: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValidationError(f"missing required CSV: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def validate_packet(result_root: Path) -> dict[str, Any]:
    for name in REQUIRED:
        expect((result_root / name).is_file(), f"missing required output: {name}")

    rerank = read_csv(result_root / "checkpoint_reranking.csv")
    expect({row["step"] for row in rerank} == {"600", "1200", "1800"}, "checkpoint reranking does not cover 600/1200/1800")
    expect(all(row.get("decode_rule") == "outputs_logits_argmax" for row in rerank), "reranking decode rule drifted")

    mode_rows = read_csv(result_root / "mode_intervention_metrics.csv")
    expect({row["mode"] for row in mode_rows} == MODES, "mode intervention metrics missing modes")
    expect(
        all(row.get("population") in {"positive_gt_cases", "all_case_empty_safe"} for row in mode_rows),
        "metric population field invalid",
    )

    case_rows = read_csv(result_root / "casewise_mechanism_attribution.csv")
    expect(len(case_rows) >= 44 * 2 * len(MODES), "casewise mechanism attribution does not cover 44 cases x 2 pathologies x modes")
    for key in ("production_gate_mean", "raw_correction_abs_mean", "bounded_correction_abs_mean", "dice_delta_vs_anchor"):
        expect(key in case_rows[0], f"casewise mechanism field missing: {key}")

    oracle_rows = read_csv(result_root / "oracle_headroom.csv")
    expect(len(oracle_rows) >= 44 * 2, "oracle headroom does not cover 44 cases x 2 pathologies")
    expect(all(row.get("diagnostic_only") == "True" for row in oracle_rows), "oracle rows are not diagnostic_only")
    expect(all(row.get("deployable_candidate") == "False" for row in oracle_rows), "oracle rows incorrectly marked deployable")

    gradient_rows = read_csv(result_root / "loss_parameter_gradient_matrix.csv")
    expect(gradient_rows, "loss gradient matrix is empty")
    expect(all(row.get("optimizer_steps") == "0" for row in gradient_rows), "gradient matrix records optimizer steps")
    groups = {row["parameter_group"] for row in gradient_rows}
    for group in ("production_correction_gate", "scar_refiner", "edema_refiner", "scar_dictionary", "edema_dictionary", "retrieval_router"):
        expect(group in groups, f"loss gradient matrix missing parameter group {group}")

    prototype = load_json(result_root / "prototype_manifest_audit.json")
    for key in ("asset_sha256", "feature_hash", "config_sha256", "source_commit", "split_hash", "anchor_manifest_hash"):
        expect(bool(prototype.get(key)), f"prototype audit hash missing: {key}")
    expect(prototype.get("asset_sha256") == "8b262f8bb87e0733a48e169c77b028a3833b70cbcd33d2ac2fb4857ba1cbde83", "prototype asset hash drifted")

    text = (result_root / "batch6_unique_repair_decision.md").read_text(encoding="utf-8")
    present = [decision for decision in DECISIONS if decision in text]
    expect(len(set(present)) == 1, f"expected exactly one Batch6 decision, found {present}")

    completion = (result_root / "completion_check.md").read_text(encoding="utf-8")
    expect("optimizer_steps: 0" in completion, "completion_check missing optimizer_steps: 0")
    expect("training_allowed: false" in completion, "completion_check missing training forbidden assertion")
    expect("validation_upload_allowed: false" in completion, "completion_check missing upload forbidden assertion")

    return {
        "status": "BATCH5_STRICT_VALIDATION_PASS",
        "result_root": str(result_root.relative_to(REPO_ROOT)),
        "mode_count": len(MODES),
        "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA,
        "batch6_decision": present[0],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", default=f"results/{TASK_KEY}")
    args = parser.parse_args()
    try:
        payload = validate_packet(REPO_ROOT / args.result_root)
    except ValidationError as exc:
        print(json.dumps({"status": "BATCH5_STRICT_VALIDATION_FAIL", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
