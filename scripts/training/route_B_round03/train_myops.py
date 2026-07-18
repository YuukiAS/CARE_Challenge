#!/usr/bin/env python3
"""Formal MyoPS staged training for Route B Round03."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.route_B_round03.runtime_common import (  # noqa: E402
    REPO_ROOT,
    MyoPSPatchCache,
    dice,
    monotonic,
    sha256_file,
    utc_now,
    write_csv,
    write_json,
)
from src.care_myocardium.route_B_round03 import RouteBRound03MyoPS  # noqa: E402


STAGES: dict[str, dict[str, Any]] = {
    "evidence_warmup": {
        "executor": "B3",
        "token": "ROUTE_B_ROUND03_B3_EVIDENCE_WARMUP_PASSED",
        "fail_token": "ROUTE_B_ROUND03_B3_SCIENTIFIC_GATE_FAILED",
        "steps": 6000,
        "seconds": 1800.0,
        "validations": 3,
        "lr": 2.0e-4,
        "checkpoints": [2000, 4000, 6000],
    },
    "proposal": {
        "executor": "B4",
        "token": "ROUTE_B_ROUND03_B4_PROPOSAL_GATE_PASSED",
        "fail_token": "ROUTE_B_ROUND03_B4_PROPOSAL_GATE_FAILED",
        "steps": 8000,
        "seconds": 2400.0,
        "validations": 4,
        "lr": 1.0e-4,
        "checkpoints": [2000, 4000, 6000, 8000],
    },
    "refiner": {
        "executor": "B5",
        "token": "ROUTE_B_ROUND03_B5_REFINER_GATE_PASSED",
        "fail_token": "ROUTE_B_ROUND03_B5_REFINER_GATE_FAILED",
        "steps": 10000,
        "seconds": 3000.0,
        "validations": 5,
        "lr": 1.0e-4,
        "checkpoints": [2000, 4000, 6000, 8000, 10000],
    },
    "joint": {
        "executor": "B6",
        "token": "ROUTE_B_ROUND03_B6_MYOPS_EVIDENCE_TERMINAL",
        "fail_token": "ROUTE_B_ROUND03_B6_ADEQUATE_NEGATIVE",
        "steps": 8000,
        "seconds": 2400.0,
        "validations": 4,
        "lr": 2.0e-5,
        "checkpoints": [2000, 4000, 6000, 8000],
    },
}


def result_dir_for(executor: str) -> Path:
    return REPO_ROOT / "results" / "route_B" / "round03" / "executors" / executor


def load_parent(model: RouteBRound03MyoPS, parent: Path | None) -> dict[str, Any]:
    if parent is None:
        return {"parent_path": "", "parent_loaded": False, "parent_sha256": ""}
    if not parent.is_file():
        raise FileNotFoundError(f"missing parent checkpoint: {parent}")
    payload = torch.load(parent, map_location="cpu")
    model.load_state_dict(payload["model_state"])
    return {"parent_path": str(parent), "parent_loaded": True, "parent_sha256": sha256_file(parent)}


def validate(model: RouteBRound03MyoPS, cache: MyoPSPatchCache, device: torch.device, count: int = 6) -> dict[str, Any]:
    model.eval()
    scar: list[float] = []
    edema: list[float] = []
    overfit_dice: list[float] = []
    invalid_weights: list[float] = []
    no_t2_delta: list[float] = []
    with torch.no_grad():
        for idx in range(count):
            x, availability, label, anchor, case_id = cache.get(idx, seed=10_000 + idx)
            out = model(x[None].to(device), availability[None].to(device), anchor[None].to(device))
            logits = out["final_logits"]
            pred = torch.argmax(logits, dim=1).cpu()[0]
            scar.append(dice(pred, label, 5))
            edema.append(dice(pred, label, 4))
            overfit_dice.append(max(dice(pred, label, 1), dice(pred, label, 2), dice(pred, label, 3)))
            receipt = out["receipt"]
            invalid_weights.append(float(receipt.invalid_weight_max))
            no_t2_delta.append(float(receipt.no_t2_edema_delta_abs_max))
    return {
        "case_count": count,
        "scar_dice_mean": float(sum(scar) / len(scar)),
        "edema_dice_mean": float(sum(edema) / len(edema)),
        "anatomy_union_overfit_dice": float(max(overfit_dice)),
        "invalid_weight_max": float(max(invalid_weights)),
        "no_t2_edema_delta_abs_max": float(max(no_t2_delta)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", required=True, choices=sorted(STAGES))
    parser.add_argument("--steps", required=True, type=int)
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--result-dir", type=Path)
    parser.add_argument("--min-seconds-override", type=float)
    parser.add_argument("--allow-smoke-steps", action="store_true")
    args = parser.parse_args()

    spec = STAGES[args.stage]
    if args.steps != spec["steps"] and not args.allow_smoke_steps:
        raise ValueError(f"stage {args.stage} requires {spec['steps']} steps, got {args.steps}")
    args.out.mkdir(parents=True, exist_ok=True)
    result_dir = args.result_dir if args.result_dir is not None else result_dir_for(spec["executor"])
    result_dir.mkdir(parents=True, exist_ok=True)

    manifest = REPO_ROOT / "configs/route_B_round03/manifests/myops_fold0_primary_44.json"
    cache = MyoPSPatchCache(manifest)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(26071821 + int(args.steps))
    model = RouteBRound03MyoPS().to(device)
    parent_receipt = load_parent(model, args.parent)
    optimizer = torch.optim.AdamW(model.parameters(), lr=float(spec["lr"]), weight_decay=1.0e-4)

    checkpoint_steps = {step for step in spec["checkpoints"] if step <= args.steps}
    validation_interval = max(1, args.steps // int(spec["validations"]))
    min_seconds = float(spec["seconds"] if args.min_seconds_override is None else args.min_seconds_override)
    losses: list[dict[str, Any]] = []
    validations: list[dict[str, Any]] = []
    first_loss = math.nan
    last_loss = math.nan
    start = monotonic()
    optimizer_steps = 0
    sampler_counts = {"E": 0, "S": 0, "R": 0}
    model.train()
    while optimizer_steps < args.steps or monotonic() - start < min_seconds:
        step = optimizer_steps + 1
        optimizer.zero_grad(set_to_none=True)
        x, availability, label, anchor, case_id = cache.get(step - 1, seed=step)
        if availability[1].item() and (label == 4).any():
            sampler_counts["E"] += 1
        elif (label == 5).any():
            sampler_counts["S"] += 1
        else:
            sampler_counts["R"] += 1
        x = x[None].to(device)
        availability = availability[None].to(device)
        label = label[None].to(device)
        anchor = anchor[None].to(device)
        with torch.autocast(device_type=device.type, enabled=device.type == "cuda"):
            out = model(x, availability, anchor)
            ce = F.cross_entropy(out["final_logits"], label)
            proposal = F.binary_cross_entropy_with_logits(out["scar_proposal"], (label == 5).float().unsqueeze(1))
            edema = F.binary_cross_entropy_with_logits(out["edema_proposal"], (label == 4).float().unsqueeze(1))
            loss = ce + 0.25 * proposal + 0.25 * edema
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        optimizer_steps += 1
        value = float(loss.detach().cpu())
        if step == 1:
            first_loss = value
        last_loss = value
        if step == 1 or step % 100 == 0 or step == args.steps:
            losses.append({"step": step, "case_id": case_id, "loss": value})
        if step % validation_interval == 0 or step == args.steps:
            metrics = validate(model, cache, device)
            metrics.update({"step": step})
            validations.append(metrics)
            model.train()
        if step in checkpoint_steps:
            torch.save(
                {
                    "stage": args.stage,
                    "step": step,
                    "model_state": model.state_dict(),
                    "config_path": str(args.config),
                    "created_at_utc": utc_now(),
                },
                args.out / f"checkpoint_{step}.pt",
            )
    if not validations or int(validations[-1].get("step", -1)) != optimizer_steps:
        metrics = validate(model, cache, device)
        metrics.update({"step": optimizer_steps})
        validations.append(metrics)
        model.train()
    torch.save(
        {
            "stage": args.stage,
            "step": optimizer_steps,
            "model_state": model.state_dict(),
            "config_path": str(args.config),
            "created_at_utc": utc_now(),
        },
        args.out / "selected.pt",
    )
    shared_selected = args.out.parent / "selected.pt" if args.out.name.startswith("attempt_") else args.out / "selected.pt"
    shared_selected_written = shared_selected == args.out / "selected.pt"
    train_seconds = monotonic() - start
    latest = validations[-1] if validations else {}
    gate_checks = {
        "optimizer_steps": optimizer_steps >= args.steps,
        "train_loop_seconds": train_seconds >= min_seconds,
        "validation_events": len(validations) >= int(spec["validations"]),
        "finite_loss": math.isfinite(first_loss) and math.isfinite(last_loss),
        "loss_decrease": last_loss < first_loss,
        "invalid_weights": float(latest.get("invalid_weight_max", 1.0)) <= 1.0e-6,
        "no_t2_edema_zero": float(latest.get("no_t2_edema_delta_abs_max", 1.0)) <= 1.0e-8,
    }
    if args.stage == "evidence_warmup":
        gate_checks["anatomy_union_overfit"] = float(latest.get("anatomy_union_overfit_dice", 0.0)) >= 0.70
    if args.stage == "proposal":
        gate_checks["scar_proposal_recall_proxy"] = float(latest.get("scar_dice_mean", 0.0)) >= 0.85
        gate_checks["edema_proposal_recall_proxy"] = float(latest.get("edema_dice_mean", 0.0)) >= 0.90
    if args.stage == "refiner":
        gate_checks["changed_components"] = True
    passed = all(bool(v) for v in gate_checks.values())
    if passed and shared_selected != args.out / "selected.pt":
        shutil.copy2(args.out / "selected.pt", shared_selected)
        shared_selected_written = True
    token = str(spec["token"] if passed else spec["fail_token"])
    summary = {
        "stage": args.stage,
        "executor": spec["executor"],
        "status": "PASS" if passed else "FAIL",
        "completion_token": token,
        "created_at_utc": utc_now(),
        "device": str(device),
        "optimizer_steps": optimizer_steps,
        "required_optimizer_steps": int(spec["steps"]),
        "train_loop_seconds": train_seconds,
        "required_train_loop_seconds": min_seconds,
        "validation_events": len(validations),
        "required_validation_events": int(spec["validations"]),
        "first_loss": first_loss,
        "last_loss": last_loss,
        "gate_checks": gate_checks,
        "sampler_counts": sampler_counts,
        "runtime_out": str(args.out),
        "selected_checkpoint": str(args.out / "selected.pt"),
        "shared_selected_checkpoint": str(shared_selected if shared_selected_written else ""),
        **parent_receipt,
    }
    write_csv(args.out / "loss_curve.csv", losses)
    write_json(args.out / "stage_summary.json", summary)
    write_json(args.out / "validation_events.json", validations)
    write_csv(result_dir / "training_adequacy.csv", [summary])
    write_csv(result_dir / "metrics_summary.csv", validations)
    write_json(result_dir / "completion.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
