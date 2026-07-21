#!/usr/bin/env python3
"""Fail-closed validator for the Batch7 upstream candidate-quality packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results/20260721_srr_batch7_upstream_candidate_quality"


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7.yaml")
    parser.add_argument("--result-root", default=str(RESULT_ROOT))
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(args.result_root)
    errors: list[str] = []
    required = [
        "prototype_memory_manifest.json",
        "prototype_feature_drift.csv",
        "semantic_negative_counts.csv",
        "fixed_batch_overfit.json",
        "fixed_batch_overfit_trace.csv",
        "gradient_authority.csv",
        "training_adequacy.json",
        "checkpoint_selection.csv",
        "casewise_metrics.csv",
        "subgroup_metrics.csv",
        "help_harm.csv",
        "proposal_refiner_metrics.csv",
        "source_arbiter_metrics.csv",
        "final_mechanism_interventions.csv",
    ]
    for name in required:
        path = result_root / name
        if not path.is_file() or path.stat().st_size == 0:
            fail(errors, f"missing_or_empty_required_output:{name}")
    manifest_path = result_root / "prototype_memory_manifest.json"
    if manifest_path.is_file():
        manifest = load_json(manifest_path)
        if manifest.get("source_checkpoint_sha256") != cfg["source_batch6"]["selected_checkpoint_sha256"]:
            fail(errors, "asset built from wrong checkpoint sha")
        if int(manifest.get("source_case_count", -1)) != int(cfg["training_data"]["train_case_count"]):
            fail(errors, "asset source case count is not exactly 176")
        if manifest.get("validation_intersection"):
            fail(errors, "asset validation leakage detected")
        if not manifest.get("full_tensor_sha256"):
            fail(errors, "asset missing full tensor sha256 declaration")
        if int(manifest.get("deterministic_axis_random_repeat_formal_contribution", 1)) != 0:
            fail(errors, "deterministic/random/repeat semantic negatives have formal contribution")
        if not bool(manifest.get("no_t2_edema_memory_count_zero", False)):
            fail(errors, "no-T2 edema memory vector accepted")
    fixed_path = result_root / "fixed_batch_overfit.json"
    if fixed_path.is_file():
        fixed = load_json(fixed_path)
        if fixed.get("status") != "PASS":
            fail(errors, "fixed overfit did not PASS")
        if int(fixed.get("optimizer_steps", -1)) != 100:
            fail(errors, "fixed overfit steps not exactly 100")
        if int(fixed.get("formal_training_credit", -1)) != 0:
            fail(errors, "fixed overfit has nonzero formal training credit")
    adequacy_path = result_root / "training_adequacy.json"
    if adequacy_path.is_file():
        adequacy = load_json(adequacy_path)
        if adequacy.get("formal_training_submitted") is not True:
            fail(errors, "formal training was not submitted")
        if int(adequacy.get("actual_optimizer_steps", -1)) != 300 and adequacy.get("stage") == "formal_300":
            fail(errors, "formal300 does not report exactly 300 optimizer steps")
        gate = adequacy.get("continuation_gate", {})
        if adequacy.get("continuation_gate_decision") == "FAIL" and adequacy.get("formal_1200_step_status") != "SKIPPED_STEP300_GATE_FAILED":
            fail(errors, "1200 was not skipped after failed 300 gate")
        if gate.get("decision") == "PASS" and gate.get("checks", {}).get("scar_refiner_only_dice_delta") is False:
            fail(errors, "scar refiner harmful but continuation passed")
        text = json.dumps(adequacy)
        for token in ("NEEDS_MONITOR", "PENDING_MONITOR", "JOB_SUBMITTED", "PENDING_PRIORITY", "RUNNING", "AWAITING_SACCT"):
            if token in text:
                fail(errors, f"monitor token in completion evidence:{token}")
    model_src = (REPO_ROOT / "src/care_myocardium/models/srr_propref.py").read_text(encoding="utf-8")
    if "class DifferentiableSoftROIRefinementHead" not in model_src:
        fail(errors, "missing DifferentiableSoftROIRefinementHead")
    if "class PathologySourceArbiter" not in model_src:
        fail(errors, "missing PathologySourceArbiter")
    if "prototype_maps=prototype_maps" not in model_src:
        fail(errors, "M10 spatial dictionary does not receive prototype_maps")
    if "0.5 * (scar_logits + scar_dict" in model_src or "0.5 * (edema_logits + edema_dict" in model_src:
        fail(errors, "fixed 0.5 proposal/refiner average remains in formal path")
    if "discovery_fusion" not in model_src or "confirmation_fusion" not in model_src:
        fail(errors, "dual-source proposal branches missing")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Batch7 packet validator passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
