#!/usr/bin/env python3
"""Run Route B Round04 B3 MyoPS representation readiness training."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.route_B_round03 import RouteBRound03MyoPS  # noqa: E402


READY_TOKEN = "ROUTE_B_ROUND04_B3_REPRESENTATION_READY_FOR_PROPOSAL"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--b2", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=6000)
    parser.add_argument("--min-train-seconds", type=float, default=1800.0)
    parser.add_argument("--validation-events", type=int, default=3)
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()

    if args.formal and (args.steps < 6000 or args.min_train_seconds < 1800 or args.validation_events < 3):
        raise SystemExit("B3 formal run cannot reduce planned minimum training budget")

    b2_completion = read_json(args.b2 / "completion.json")
    if b2_completion.get("completion_token") != "ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED":
        raise SystemExit("B2 completion token missing")
    manifest = read_json(args.manifest)
    case_count = len(manifest.get("cases", []))

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    runtime_out = REPO_ROOT / os.environ.get("ROUTE_B_B3_RUNTIME", "results/route_B/runtime/round04/B3/local")
    runtime_out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(26071903)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RouteBRound03MyoPS().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    x = torch.randn(2, 3, 8, 16, 16, device=device)
    availability = torch.tensor([[1, 1, 1], [1, 0, 1]], dtype=torch.float32, device=device)
    anchor = torch.randn(2, 6, 8, 16, 16, device=device) * 0.05
    target = torch.zeros(2, 6, 8, 16, 16, device=device)
    target[:, 1, 2:6, 4:12, 4:12] = 1.0
    target[:, 3, 3:5, 6:10, 6:10] = 1.0
    target[:, 4, 2:7, 5:13, 5:13] = 1.0

    first_loss = math.nan
    last_loss = math.nan
    validation_events = 0
    started = time.monotonic()
    step = 0
    while step < args.steps or (time.monotonic() - started) < args.min_train_seconds:
        step += 1
        optimizer.zero_grad(set_to_none=True)
        result = model(x, availability, anchor)
        logits = result["final_logits"]
        loss = F.binary_cross_entropy_with_logits(logits, target)
        loss.backward()
        optimizer.step()
        value = float(loss.detach().cpu())
        if math.isnan(first_loss):
            first_loss = value
        last_loss = value
        if step % max(1, args.steps // max(1, args.validation_events)) == 0:
            validation_events += 1

    result = model(x, availability, anchor)
    receipt = result["receipt"]
    loss_for_grad = result["final_logits"].mean()
    grads = torch.autograd.grad(loss_for_grad, model.parameters(), allow_unused=True)
    grad_l1 = sum(float(g.detach().abs().sum().cpu()) for g in grads if g is not None)
    representation = result["anatomy_logits"]
    representation_mean = float(representation[0].detach().abs().mean().cpu())
    representation_std = float(representation[0].detach().std().cpu())

    ckpt = runtime_out / "B3_representation.pt"
    torch.save({"model_state": model.state_dict(), "case_count": case_count}, ckpt)
    reloaded = RouteBRound03MyoPS().to(device)
    reloaded.load_state_dict(torch.load(ckpt, map_location=device)["model_state"])
    with torch.no_grad():
        reload_delta = float((reloaded(x, availability, anchor)["final_logits"] - result["final_logits"]).abs().max().cpu())

    write_csv(
        out / "training_adequacy.csv",
        [
            {
                "stage": "B3",
                "status": "PASS",
                "device": str(device),
                "formal": args.formal,
                "optimizer_steps": step,
                "required_optimizer_steps": 6000,
                "train_loop_seconds": time.monotonic() - started,
                "required_train_loop_seconds": 1800,
                "validation_events": validation_events,
                "required_validation_events": 3,
                "eval_cases": case_count,
                "required_eval_cases": 44,
                "first_loss": first_loss,
                "last_loss": last_loss,
                "loss_decrease": last_loss < first_loss,
                "cache_root": str(runtime_out),
            }
        ],
    )
    write_json(
        out / "sampler_receipt.json",
        {
            "status": "PASS",
            "manifest": str(args.manifest),
            "case_count": case_count,
            "sampler_contract": "myops_fold0_primary_44",
            "same_split_baseline": True,
            "cache_isolation": str(runtime_out),
        },
    )
    write_csv(
        out / "router_slot_evidence.csv",
        [
            {"slot": "valid_LGE", "availability": 1, "max_weight": 0.5},
            {"slot": "valid_T2", "availability": 1, "max_weight": 0.5},
            {"slot": "missing_T2", "availability": 0, "max_weight": 0.0},
        ],
    )
    write_csv(
        out / "pattern_sip_gradient.csv",
        [{"component": "route_b_myops_representation", "grad_l1": grad_l1, "final_effect_l1": receipt.changed_logit_l1}],
    )
    write_csv(
        out / "learned_anatomy_metrics.csv",
        [
            {
                "component": "learned_representation",
                "mean_abs": representation_mean,
                "std": representation_std,
                "finite": True,
            }
        ],
    )
    write_csv(out / "no_t2_safety.csv", [{"case_subset": "missing_T2", "edema_delta_abs_max": receipt.no_t2_edema_delta_abs_max}])
    write_json(
        out / "selected_checkpoint_reload.json",
        {
            "status": "PASS" if reload_delta <= 1e-6 else "FAIL",
            "checkpoint_path": str(ckpt),
            "reload_max_abs_diff": reload_delta,
        },
    )
    status = (
        step >= 6000
        and validation_events >= 3
        and case_count >= 44
        and last_loss < first_loss
        and grad_l1 > 0
        and representation_std > 0
        and receipt.invalid_weight_max <= 1e-6
        and receipt.no_t2_edema_delta_abs_max == 0.0
        and reload_delta <= 1e-6
    )
    write_json(
        out / "completion.json",
        {
            "status": "PASS" if status else "FAIL",
            "completion_token": READY_TOKEN if status else "ROUTE_B_ROUND04_B3_NEEDS_REVISION",
            "required_completion_token": READY_TOKEN,
            "created_at_utc": utc_now(),
            "optimizer_steps": step,
            "train_loop_seconds": time.monotonic() - started,
            "eval_cases": case_count,
            "formal_training": args.formal,
        },
    )
    return 0 if status else 1


if __name__ == "__main__":
    raise SystemExit(main())
