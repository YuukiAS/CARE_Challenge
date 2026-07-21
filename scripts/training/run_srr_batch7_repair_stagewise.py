#!/usr/bin/env python3
"""Batch7 repair stagewise training wrapper."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "envs/env_CARE/bin/python"


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def stage_cfg(cfg: dict[str, Any], stage: str) -> dict[str, Any]:
    mapping = {
        "proposal": "proposal_stage",
        "scar_refiner": "scar_refiner_stage",
        "edema_refiner": "edema_refiner_stage",
        "source_arbiter": "source_arbiter_stage",
        "production_gate": "production_gate_stage",
    }
    return dict(cfg["stagewise_training"][mapping[stage]])


def source_checkpoint(cfg: dict[str, Any], stage: str) -> Path:
    result_root = repo_path(cfg["paths"]["result_root"])
    if stage == "proposal":
        return repo_path(cfg["source_checkpoints"]["batch7"]["path"])
    proposal = load_json(result_root / "proposal_stage_adequacy.json")
    if proposal.get("continuation_gate_decision") != "PASS":
        raise SystemExit("downstream stage blocked: proposal continuation gate did not PASS")
    return repo_path(proposal["selected_checkpoint_path"])


def production_mode(stage: str) -> str:
    return {
        "proposal": "proposal_only_gate_one",
        "scar_refiner": "refiner_only_gate_one",
        "edema_refiner": "refiner_only_gate_one",
        "source_arbiter": "learned_source_gate_one",
        "production_gate": "production_gate_one",
    }[stage]


def trainable_groups(cfg: dict[str, Any], stage: str) -> list[str]:
    raw = stage_cfg(cfg, stage).get("trainable_groups", [])
    groups = [str(item) for item in raw]
    if stage == "scar_refiner":
        groups = ["scar_refine"]
    elif stage == "edema_refiner":
        groups = ["edema_refine"]
    elif stage == "source_arbiter":
        groups = ["accepted_pathology_source_arbiters_only"]
    elif stage == "production_gate":
        groups = ["production_correction_gate"]
    return groups


def eval_steps(cfg: dict[str, Any], stage: str) -> str:
    return ",".join(str(item) for item in stage_cfg(cfg, stage)["full_volume_eval_steps"])


def build_command(cfg: dict[str, Any], stage: str, attempt_label: str) -> list[str]:
    common = cfg["stagewise_training"]["common"]
    scfg = stage_cfg(cfg, stage)
    ckpt = source_checkpoint(cfg, stage)
    result_root = repo_path(cfg["paths"]["result_root"])
    attempt_root = result_root / "runtime/stages" / stage / "attempts" / attempt_label
    return [
        str(PYTHON),
        "scripts/training/run_srr_propref_myops_fold0.py",
        "--variant",
        cfg["model"]["variant"],
        "--run-label",
        attempt_label,
        "--fold",
        str(cfg["training_data"]["fold"]),
        "--seed",
        "20260721",
        "--device",
        "cuda",
        "--base-channels",
        str(cfg["model"]["base_channels"]),
        "--encoder-profile",
        cfg["model"]["encoder_profile"],
        "--final-output-mode",
        cfg["model"]["final_output_mode"],
        "--patch-shape",
        ",".join(str(x) for x in common["patch_shape"]),
        "--batch-size",
        str(common["batch_size"]),
        "--max-steps",
        str(scfg["optimizer_steps"]),
        "--max-runtime-seconds",
        str(cfg["slurm"]["maximum_runtime_seconds_per_job"]),
        "--lr",
        str(common["learning_rate"]),
        "--weight-decay",
        str(common["weight_decay"]),
        "--grad-clip",
        str(common["grad_clip"]),
        "--val-every",
        str(scfg["full_volume_eval_steps"][0]),
        "--early-stop-patience",
        "0",
        "--min-optimizer-steps-for-plateau",
        str(scfg["optimizer_steps"]),
        "--min-train-loop-seconds-for-plateau",
        "0",
        "--warm-start-checkpoint",
        str(ckpt.relative_to(REPO_ROOT)),
        "--warm-start-checkpoint-sha256",
        cfg["source_checkpoints"]["batch7"]["sha256"] if stage == "proposal" else "",
        "--warm-start-allow-architecture-extension",
        "--prototype-memory-asset",
        cfg["paths"]["semantic_memory_asset"],
        "--prototype-memory-manifest",
        str((result_root / "semantic_memory_manifest.json").relative_to(REPO_ROOT)),
        "--batch6-trainable-groups",
        ",".join(trainable_groups(cfg, stage)),
        "--full-volume-eval-steps",
        eval_steps(cfg, stage),
        "--out-root",
        str(attempt_root.relative_to(REPO_ROOT)),
        "--production-intervention-mode",
        production_mode(stage),
        "--loss-weight-json",
        json.dumps({}, sort_keys=True),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_repair.yaml")
    parser.add_argument("--stage", choices=("proposal", "scar_refiner", "edema_refiner", "source_arbiter", "production_gate"), required=True)
    parser.add_argument("--attempt-label", default="")
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    partition = os.environ.get("PARTITION_LABEL", "local")
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    attempt_label = args.attempt_label or f"batch7_repair_{args.stage}_{partition}_{job_id}"
    cmd = build_command(cfg, args.stage, attempt_label)
    payload = {"status": "BATCH7_REPAIR_STAGE_CONTRACT_READY", "stage": args.stage, "attempt_label": attempt_label, "command": cmd}
    print(json.dumps(payload, indent=2, sort_keys=True))
    if args.print_contract:
        return subprocess.run([*cmd, "--print-contract"], cwd=REPO_ROOT).returncode
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
