#!/usr/bin/env python3
"""Run one pathology arm of the Batch7 minimal/BR2/SIP decomposition."""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = REPO_ROOT / "envs/env_CARE/bin/python"
DEFAULT_FIXED_OVERFIT = REPO_ROOT / "results/20260721_srr_batch7_upstream_candidate_quality/fixed_batch_overfit.json"


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_fixed_overfit(path: Path) -> Path:
    payload = load_json(path)
    if payload.get("status") != "PASS" or int(payload.get("optimizer_steps", -1)) != 100:
        raise SystemExit(f"Batch7 decomposition blocked: fixed overfit receipt is not PASS/100 steps: {path}")
    if int(payload.get("formal_training_credit", -1)) != 0:
        raise SystemExit(f"Batch7 fixed overfit receipt must have zero formal training credit: {path}")
    return path


def csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def calibrated_sip_weight(result_root: Path, pathology: str, *, placeholder: float | None = None) -> float:
    path = result_root / "sip_weight_calibration.csv"
    rows = csv_rows(path)
    candidates: list[tuple[float, dict[str, str]]] = []
    for row in rows:
        if row.get("pathology") != pathology:
            continue
        if row.get("status") != "PASS":
            continue
        try:
            candidates.append((float(row["selected_lambda"]), row))
        except (KeyError, TypeError, ValueError):
            continue
    if not candidates:
        if placeholder is not None:
            return float(placeholder)
        raise SystemExit(
            f"Batch7 SIP run blocked: missing PASS train-only calibration row for {pathology} in {path}"
        )
    return candidates[0][0]


def loss_weights(
    cfg: dict[str, Any],
    pathology: str,
    *,
    br2: bool,
    sip: bool,
    result_root: Path,
    placeholder_sip_weight: float | None = None,
) -> dict[str, float]:
    source = cfg["loss_weights"]
    merged: dict[str, float] = {}
    for section in ("common_zero", f"{pathology}_common"):
        for key, value in source.get(section, {}).items():
            try:
                merged[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    if br2:
        br2_section = "br2_sip" if sip else "br2_no_sip"
        for key, value in source.get(br2_section, {}).items():
            if str(value) == "calibrated_from_candidates":
                merged[str(key)] = calibrated_sip_weight(result_root, pathology, placeholder=placeholder_sip_weight)
            else:
                merged[str(key)] = float(value)
    return merged


def trainable_groups(pathology: str, *, br2: bool) -> str:
    if pathology == "scar":
        groups = ["scar_evidence_head", "scar_proposal_dictionary"]
        if br2:
            groups.extend(["scar_lightweight_br2", "scar_br2_coefficients"])
    elif pathology == "edema":
        groups = ["edema_evidence_head", "edema_proposal_dictionary"]
        if br2:
            groups.extend(["edema_lightweight_br2", "edema_br2_coefficients"])
    else:
        raise ValueError(f"unknown pathology: {pathology}")
    return ",".join(groups)


def base_command(
    cfg: dict[str, Any],
    *,
    pathology: str,
    run_label: str,
    attempt_root: Path,
    max_steps: int,
    eval_steps: str,
    br2: bool,
    sip: bool,
    loss_json: dict[str, float],
) -> list[str]:
    common = cfg["common_training"]
    model = cfg["model"]
    cmd = [
        str(PYTHON),
        "scripts/training/run_srr_propref_myops_fold0.py",
        "--variant",
        model["source_variant"],
        "--run-label",
        run_label,
        "--fold",
        str(cfg["training_data"]["fold"]),
        "--seed",
        "20260722",
        "--device",
        "cuda",
        "--base-channels",
        str(model["base_channels"]),
        "--encoder-profile",
        model["encoder_profile"],
        "--final-output-mode",
        model["final_output_mode"],
        "--patch-shape",
        ",".join(str(x) for x in common["patch_shape"]),
        "--batch-size",
        str(common["batch_size"]),
        "--max-steps",
        str(max_steps),
        "--max-runtime-seconds",
        str(cfg["slurm"]["maximum_runtime_seconds_per_job"]),
        "--lr",
        str(common["learning_rate"]),
        "--weight-decay",
        str(common["weight_decay"]),
        "--grad-clip",
        str(common["grad_clip"]),
        "--val-every",
        "200" if max_steps >= 200 else str(max_steps),
        "--early-stop-patience",
        "0",
        "--min-optimizer-steps-for-plateau",
        str(max_steps),
        "--min-train-loop-seconds-for-plateau",
        "0",
        "--skip-overfit-sanity",
        "--external-fixed-overfit-receipt",
        str(DEFAULT_FIXED_OVERFIT.relative_to(REPO_ROOT)),
        "--warm-start-allow-architecture-extension",
        "--batch6-trainable-groups",
        trainable_groups(pathology, br2=br2),
        "--batch7-source-balanced-pathology",
        pathology,
        "--batch7-decomposition-schedule",
        "center_hierarchical_br2_400",
        "--batch7-minimal-decomposition-mode",
        "--full-volume-eval-steps",
        eval_steps,
        "--out-root",
        str(attempt_root.relative_to(REPO_ROOT)),
        "--disable-local-refinement",
        "--loss-weight-json",
        json.dumps(loss_json, sort_keys=True, separators=(",", ":")),
    ]
    if br2:
        cmd.append("--enable-batch7-decomposition-br2")
    if sip:
        cmd.append("--batch7-decomposition-use-sip")
    return cmd


def run(cmd: list[str], *, print_only: bool) -> None:
    print(json.dumps({"command": cmd}, indent=2, sort_keys=True), flush=True)
    if print_only:
        proc = subprocess.run([*cmd, "--print-contract"], cwd=REPO_ROOT)
    else:
        proc = subprocess.run(cmd, cwd=REPO_ROOT)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def warmup_checkpoint(attempt_root: Path, pathology: str, attempt_label: str) -> Path:
    return (
        attempt_root
        / "variants"
        / f"{pathology}_br2_warmup50__{attempt_label}"
        / "checkpoints/fold_0/propref_config/checkpoint_final.pt"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_minimal_decomposition.yaml")
    parser.add_argument("--pathology", choices=("scar", "edema"), required=True)
    parser.add_argument("--attempt-label", default="")
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(cfg["paths"]["result_root"])
    fixed = require_fixed_overfit(DEFAULT_FIXED_OVERFIT)
    source = repo_path(cfg["source_checkpoint"]["path"])
    source_sha = str(cfg["source_checkpoint"]["sha256"])
    if not source.is_file():
        raise SystemExit(f"source checkpoint not found: {source}")
    partition = os.environ.get("PARTITION_LABEL", "local")
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    attempt_label = args.attempt_label or f"batch7_minimal_decomposition_{args.pathology}_{partition}_{job_id}"
    attempt_root = result_root / "runtime/attempts" / attempt_label
    attempt_root.mkdir(parents=True, exist_ok=True)

    print(
        json.dumps(
            {
                "status": "BATCH7_MINIMAL_DECOMPOSITION_CONTRACT_READY",
                "pathology": args.pathology,
                "attempt_label": attempt_label,
                "attempt_root": str(attempt_root),
                "source_checkpoint": str(source),
                "source_checkpoint_sha256": source_sha,
                "fixed_overfit_receipt": str(fixed),
            },
            indent=2,
            sort_keys=True,
        ),
        flush=True,
    )

    minimal = base_command(
        cfg,
        pathology=args.pathology,
        run_label=f"{args.pathology}_minimal__{attempt_label}",
        attempt_root=attempt_root,
        max_steps=400,
        eval_steps="200,400",
        br2=False,
        sip=False,
        loss_json=loss_weights(cfg, args.pathology, br2=False, sip=False, result_root=result_root),
    )
    minimal.extend(["--warm-start-checkpoint", str(source.relative_to(REPO_ROOT)), "--warm-start-checkpoint-sha256", source_sha])
    run(minimal, print_only=args.print_contract)

    warmup = base_command(
        cfg,
        pathology=args.pathology,
        run_label=f"{args.pathology}_br2_warmup50__{attempt_label}",
        attempt_root=attempt_root,
        max_steps=50,
        eval_steps="",
        br2=True,
        sip=False,
        loss_json=loss_weights(cfg, args.pathology, br2=True, sip=False, result_root=result_root),
    )
    warmup.extend(["--warm-start-checkpoint", str(source.relative_to(REPO_ROOT)), "--warm-start-checkpoint-sha256", source_sha, "--skip-export"])
    run(warmup, print_only=args.print_contract)

    ckpt = warmup_checkpoint(attempt_root, args.pathology, attempt_label)
    ckpt_sha = "PRINT_CONTRACT_PLACEHOLDER_SHA256" if args.print_contract else None
    if not args.print_contract:
        if not ckpt.is_file():
            raise SystemExit(f"warmup checkpoint missing after step50 run: {ckpt}")
        from src.care_myocardium.srr_production.anchor_manifest import sha256_file

        ckpt_sha = sha256_file(ckpt)
    calibration_cmd = [
        str(PYTHON),
        "scripts/evaluation/calibrate_srr_batch7_sip_weight.py",
        "--pathology",
        args.pathology,
        "--checkpoint",
        str(ckpt.relative_to(REPO_ROOT)),
        "--checkpoint-sha256",
        str(ckpt_sha),
        "--device",
        "cuda",
    ]
    print(json.dumps({"calibration_command": calibration_cmd}, indent=2, sort_keys=True), flush=True)
    if not args.print_contract:
        proc = subprocess.run(calibration_cmd, cwd=REPO_ROOT)
        if proc.returncode != 0:
            raise SystemExit(proc.returncode)

    for suffix, sip in (("br2_no_sip", False), ("br2_sip", True)):
        cmd = base_command(
            cfg,
            pathology=args.pathology,
            run_label=f"{args.pathology}_{suffix}__{attempt_label}",
            attempt_root=attempt_root,
            max_steps=400,
            eval_steps="200,400",
            br2=True,
            sip=sip,
            loss_json=loss_weights(
                cfg,
                args.pathology,
                br2=True,
                sip=sip,
                result_root=result_root,
                placeholder_sip_weight=0.01 if args.print_contract else None,
            ),
        )
        cmd.extend(
            [
                "--resume-training-checkpoint",
                str(ckpt.relative_to(REPO_ROOT)),
                "--resume-training-checkpoint-sha256",
                str(ckpt_sha),
            ]
        )
        run(cmd, print_only=args.print_contract)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
