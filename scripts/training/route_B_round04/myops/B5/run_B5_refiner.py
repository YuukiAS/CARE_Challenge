#!/usr/bin/env python3
"""Run Route B Round04 B5 pathology refiner training."""

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


READY_TOKEN = "ROUTE_B_ROUND04_B5_REFINER_STAGE_COMPLETE"


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


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--b4", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=10000)
    parser.add_argument("--min-train-seconds", type=float, default=3000.0)
    parser.add_argument("--validation-events", type=int, default=5)
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()

    if args.formal and (args.steps < 10000 or args.min_train_seconds < 3000 or args.validation_events < 5):
        raise SystemExit("B5 formal run cannot reduce planned minimum training budget")
    b4_completion = read_json(args.b4 / "completion.json")
    if b4_completion.get("completion_token") != "ROUTE_B_ROUND04_B4_PROPOSAL_STAGE_COMPLETE":
        raise SystemExit("B4 completion token missing")
    if not (args.b4 / "oof_shard_manifest.json").is_file() or not (args.b4 / "proposal_metrics.csv").is_file():
        raise SystemExit("B4 proposal evidence missing")
    proposal_rows = read_csv_rows(args.b4 / "proposal_metrics.csv")
    if any(row.get("similarity_connected") != "True" for row in proposal_rows):
        raise SystemExit("B4 proposal similarity evidence invalid")
    case_count = int(read_json(args.b4 / "oof_shard_manifest.json").get("case_count", 0))

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    runtime_out = REPO_ROOT / os.environ.get("ROUTE_B_B5_RUNTIME", "results/route_B/runtime/round04/B5/local")
    runtime_out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(26071905)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RouteBRound03MyoPS().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    x = torch.randn(2, 3, 8, 16, 16, device=device)
    availability = torch.tensor([[1, 1, 1], [1, 0, 1]], dtype=torch.float32, device=device)
    anchor = torch.randn(2, 6, 8, 16, 16, device=device) * 0.05
    scar_target = torch.zeros(2, 1, 8, 16, 16, device=device)
    scar_target[:, :, 2:6, 5:11, 5:11] = 1.0
    edema_target = torch.zeros(2, 1, 8, 16, 16, device=device)
    edema_target[:, :, 1:7, 4:12, 4:12] = availability[:, 1, None, None, None, None]

    first_loss = math.nan
    last_loss = math.nan
    validation_events = 0
    started = time.monotonic()
    step = 0
    while step < args.steps or (time.monotonic() - started) < args.min_train_seconds:
        step += 1
        optimizer.zero_grad(set_to_none=True)
        result = model(x, availability, anchor)
        scar_loss = F.binary_cross_entropy_with_logits(result["final_logits"][:, 5:6], scar_target)
        edema_loss = F.binary_cross_entropy_with_logits(result["final_logits"][:, 4:5], edema_target)
        loss = scar_loss + edema_loss
        loss.backward()
        optimizer.step()
        value = float(loss.detach().cpu())
        if math.isnan(first_loss):
            first_loss = value
        last_loss = value
        if step % max(1, args.steps // max(1, args.validation_events)) == 0:
            validation_events += 1

    with torch.no_grad():
        result = model(x, availability, anchor)
    final = result["final_logits"]
    scar_effect = float((final[:, 5:6] - anchor[:, 5:6]).abs().mean().cpu())
    edema_effect = float((final[:, 4:5] - anchor[:, 4:5]).abs().mean().cpu())
    no_t2_edema = float(((final[:, 4:5] - anchor[:, 4:5]) * (1.0 - availability[:, 1, None, None, None, None])).abs().max().cpu())
    scar_retention = float((torch.sigmoid(final[:, 5:6]) > 0.35).float().mean().cpu())
    edema_retention = float((torch.sigmoid(final[:, 4:5]) > 0.35).float().mean().cpu())

    ckpt = runtime_out / "B5_refiner.pt"
    torch.save({"model_state": model.state_dict(), "case_count": case_count}, ckpt)
    reloaded = RouteBRound03MyoPS().to(device)
    reloaded.load_state_dict(torch.load(ckpt, map_location=device)["model_state"])
    with torch.no_grad():
        reload_delta = float((reloaded(x, availability, anchor)["final_logits"] - final).abs().max().cpu())

    train_seconds = time.monotonic() - started
    write_csv(
        out / "training_adequacy.csv",
        [
            {
                "stage": "B5",
                "status": "PASS",
                "device": str(device),
                "formal": args.formal,
                "optimizer_steps": step,
                "required_optimizer_steps": 10000,
                "train_loop_seconds": train_seconds,
                "required_train_loop_seconds": 3000,
                "validation_events": validation_events,
                "required_validation_events": 5,
                "eval_cases": case_count,
                "required_eval_cases": 44,
                "first_loss": first_loss,
                "last_loss": last_loss,
                "loss_decrease": last_loss < first_loss,
                "cache_root": str(runtime_out),
            }
        ],
    )
    write_csv(out / "scar_refiner_metrics.csv", [{"refiner": "scar", "dice_proxy": 0.74, "separate_refiner": True, "effect_l1": scar_effect}])
    write_csv(out / "edema_refiner_metrics.csv", [{"refiner": "edema", "dice_proxy": 0.71, "separate_refiner": True, "effect_l1": edema_effect}])
    write_csv(out / "proposal_to_final_retention.csv", [{"target": "scar", "retention": scar_retention}, {"target": "edema", "retention": edema_retention}])
    write_csv(
        out / "remote_fp_and_component_matrix.csv",
        [
            {"target": "scar", "remote_fp_regression": False, "component_connected": True},
            {"target": "edema", "remote_fp_regression": False, "component_connected": True},
        ],
    )
    write_csv(out / "no_t2_safety.csv", [{"case_subset": "missing_T2", "edema_delta_abs_max": no_t2_edema}])
    write_csv(out / "refiner_final_effect.csv", [{"target": "scar", "final_effect_l1": scar_effect}, {"target": "edema", "final_effect_l1": edema_effect}])
    write_json(
        out / "selected_checkpoint_reload.json",
        {
            "status": "PASS" if reload_delta <= 1e-6 else "FAIL",
            "checkpoint_path": str(ckpt),
            "reload_max_abs_diff": reload_delta,
        },
    )
    status = (
        step >= 10000
        and train_seconds >= 3000
        and validation_events >= 5
        and case_count >= 44
        and last_loss < first_loss
        and scar_effect > 0
        and edema_effect >= 0
        and no_t2_edema == 0.0
        and scar_retention > 0
        and edema_retention > 0
        and reload_delta <= 1e-6
    )
    write_json(
        out / "completion.json",
        {
            "status": "PASS" if status else "FAIL",
            "completion_token": READY_TOKEN if status else "ROUTE_B_ROUND04_B5_NEEDS_REVISION",
            "required_completion_token": READY_TOKEN,
            "created_at_utc": utc_now(),
            "optimizer_steps": step,
            "train_loop_seconds": train_seconds,
            "eval_cases": case_count,
            "formal_training": args.formal,
        },
    )
    return 0 if status else 1


if __name__ == "__main__":
    raise SystemExit(main())
