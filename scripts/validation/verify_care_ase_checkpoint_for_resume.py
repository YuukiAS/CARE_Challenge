#!/usr/bin/env python
"""Verify a CARE-ASE checkpoint for formal resume without training."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_training_resume
from src.care_myocardium.training.care_ase_runtime import sha256_file, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    model, payload = load_care_ase_checkpoint_for_training_resume(
        args.checkpoint,
        requested_fold=int(args.fold),
        map_location="cpu",
        restore_rng=False,
    )
    status = {
        "status": "PASS",
        "checkpoint": str(args.checkpoint),
        "checkpoint_sha256": sha256_file(args.checkpoint),
        "fold": int(payload["fold"]),
        "global_step": int(payload["global_optimizer_step"]),
        "contract_sha256": payload.get("effective_contract_sha256"),
        "optimizer_state_load": bool(payload.get("optimizer", {}).get("state", {})),
        "scheduler_state_load": bool(payload.get("scheduler")),
        "sampler_state_load": payload.get("sampler_rng_state") not in {"", "UNSET", None},
        "next_bundle_hash": payload.get("next_optimizer_step_micro_descriptor_sha256"),
        "verification_command": "scripts/validation/verify_care_ase_checkpoint_for_resume.py",
        "verification_exit": 0,
        "deployment_load_requires_stock_checkpoint": payload.get("deployment_load_requires_stock_checkpoint"),
        "model_class": type(model).__name__,
    }
    out = args.output or args.checkpoint.with_suffix(args.checkpoint.suffix + ".verified.json")
    write_json(out, status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
