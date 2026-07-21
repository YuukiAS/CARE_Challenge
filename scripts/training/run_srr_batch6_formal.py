#!/usr/bin/env python3
"""Thin Batch6 formal training wrapper around run_srr_propref_myops_fold0.py."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "envs/env_CARE/bin/python"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def selected_batch4_checkpoint(cfg: dict[str, Any]) -> Path:
    adequacy = load_json(repo_path(cfg["source_batch4"]["result_root"]) / "training_adequacy.json")
    path = repo_path(str(adequacy["selected_checkpoint_path"]))
    if str(adequacy.get("selected_checkpoint_sha256")) != str(cfg["source_batch4"]["selected_checkpoint_sha256"]):
        raise SystemExit("Batch4 selected checkpoint SHA in adequacy does not match Batch6 config")
    return path


def selected_stage300_checkpoint(result_root: Path) -> Path:
    adequacy = load_json(result_root / "training_adequacy.json")
    if adequacy.get("continuation_gate_decision") != "PASS":
        raise SystemExit("Stage 900 requested but stage-300 continuation gate is not PASS")
    path = adequacy.get("selected_checkpoint_path")
    if not path:
        raise SystemExit("Stage 300 selected checkpoint path missing")
    return repo_path(str(path))


def fixed_overfit_receipt(result_root: Path) -> Path:
    path = result_root / "fixed_batch_overfit.json"
    payload = load_json(path)
    if payload.get("status") != "PASS" or int(payload.get("optimizer_steps", -1)) != 60:
        raise SystemExit("Batch6 formal training is blocked: fixed-overfit receipt is not PASS")
    if int(payload.get("formal_training_credit", -1)) != 0:
        raise SystemExit("Batch6 fixed-overfit receipt must have zero formal training credit")
    return path


def build_command(cfg: dict[str, Any], stage: str, attempt_label: str) -> list[str]:
    result_root = repo_path(cfg["paths"]["result_root"])
    fixed_receipt = fixed_overfit_receipt(result_root)
    formal = cfg["formal_training"]
    source_ckpt = selected_batch4_checkpoint(cfg) if stage == "300" else selected_stage300_checkpoint(result_root)
    source_sha = str(cfg["source_batch4"]["selected_checkpoint_sha256"]) if stage == "300" else ""
    if stage == "300":
        max_steps = int(formal["stage_300"]["optimizer_steps"])
        eval_steps = ",".join(str(x) for x in formal["stage_300"]["full_volume_eval_steps"])
        trainable = ",".join(formal["stage_300"]["trainable_groups"])
        extra: list[str] = []
    else:
        max_steps = int(formal["stage_900"]["total_optimizer_steps"]) - int(formal["stage_300"]["optimizer_steps"])
        eval_steps = "150,300,600"
        trainable = ",".join(formal["stage_300"]["trainable_groups"])
        extra = [
            "--batch6-unfreeze-at-step", "1",
            "--batch6-additional-trainable-groups", ",".join(formal["stage_900"]["additionally_unfreeze_at_step_301"]),
        ]
    attempt_root = result_root / "runtime/attempts" / attempt_label
    return [
        str(PYTHON), "scripts/training/run_srr_propref_myops_fold0.py",
        "--variant", cfg["model"]["variant"],
        "--run-label", attempt_label,
        "--fold", str(cfg["training_data"]["fold"]),
        "--seed", "20260721",
        "--device", "cuda",
        "--base-channels", str(cfg["model"]["base_channels"]),
        "--encoder-profile", cfg["model"]["encoder_profile"],
        "--final-output-mode", cfg["model"]["final_output_mode"],
        "--patch-shape", ",".join(str(x) for x in formal["patch_shape"]),
        "--batch-size", str(formal["batch_size"]),
        "--max-steps", str(max_steps),
        "--max-runtime-seconds", str(cfg["slurm"]["maximum_runtime_seconds_per_stage"]),
        "--lr", str(formal["learning_rate"]),
        "--weight-decay", str(formal["weight_decay"]),
        "--grad-clip", str(formal["grad_clip"]),
        "--val-every", "100" if stage == "300" else "150",
        "--early-stop-patience", "0",
        "--min-optimizer-steps-for-plateau", str(max_steps),
        "--min-train-loop-seconds-for-plateau", "0",
        "--skip-overfit-sanity",
        "--external-fixed-overfit-receipt", str(fixed_receipt.relative_to(REPO_ROOT)),
        "--warm-start-checkpoint", str(source_ckpt.relative_to(REPO_ROOT)),
        "--warm-start-checkpoint-sha256", source_sha,
        "--batch6-trainable-groups", trainable,
        "--prototype-bank-cases", str(cfg["source_batch4"]["train_cases"]),
        "--full-volume-eval-steps", eval_steps,
        "--out-root", str(attempt_root.relative_to(REPO_ROOT)),
        "--hardneg-components-csv", "results/20260629_proposal_memory_hardneg/mined_components.csv",
        "--loss-weight-json", json.dumps(cfg["canonical_loss_weights"], sort_keys=True),
        *extra,
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch6.yaml")
    parser.add_argument("--stage", choices=("300", "900"), required=True)
    parser.add_argument("--attempt-label", default="")
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    partition = os.environ.get("PARTITION_LABEL", "local")
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    attempt_label = args.attempt_label or f"batch6_formal{args.stage}_{partition}_{job_id}"
    cmd = build_command(cfg, args.stage, attempt_label)
    payload = {
        "status": "BATCH6_FORMAL_CONTRACT_READY",
        "stage": args.stage,
        "attempt_label": attempt_label,
        "command": cmd,
    }
    if args.print_contract:
        print(json.dumps(payload, indent=2, sort_keys=True))
        contract_cmd = [*cmd, "--print-contract"]
        return subprocess.run(contract_cmd, cwd=REPO_ROOT).returncode
    print(json.dumps(payload, indent=2, sort_keys=True))
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
