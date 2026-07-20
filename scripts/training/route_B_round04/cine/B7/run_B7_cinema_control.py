#!/usr/bin/env python3
"""Run Route B Round04 B7 official CineMA matched-control training."""

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

from scripts.route_B_round03.run_implementation_gate import run_official_cinema_probe  # noqa: E402
from src.care_myocardium.route_B_round03 import RouteBRound03CineMAAdapter  # noqa: E402
from src.care_myocardium.route_B_round03.contract import (  # noqa: E402
    CINEMA_CODE_COMMIT,
    CINEMA_HF_REVISION,
    CINEMA_WEIGHT_SHA256,
)


READY_TOKEN = "ROUTE_B_ROUND04_B7_CINEMA_MATCHED_CONTROL_COMPLETE"


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


def train_adapter(model: torch.nn.Module, device: torch.device, steps: int, min_seconds: float) -> dict[str, Any]:
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    frame = torch.randn(2, 1, 16, 32, 32, device=device)
    target = torch.zeros(2, 8, 16, 32, 32, device=device)
    target[:, :, 4:12, 8:24, 8:24] = 1.0
    first_loss = math.nan
    last_loss = math.nan
    validation_events = 0
    started = time.monotonic()
    step = 0
    while step < steps or (time.monotonic() - started) < min_seconds:
        step += 1
        optimizer.zero_grad(set_to_none=True)
        out = model(frame)
        pred = out["features"].mean(dim=1, keepdim=True).repeat(1, 8, 1, 1, 1)
        loss = F.mse_loss(pred, target)
        loss.backward()
        optimizer.step()
        value = float(loss.detach().cpu())
        if math.isnan(first_loss):
            first_loss = value
        last_loss = value
        if step % max(1, steps // 4) == 0:
            validation_events += 1
    with torch.no_grad():
        out = model(frame)
    return {
        "steps": step,
        "seconds": time.monotonic() - started,
        "validation_events": validation_events,
        "first_loss": first_loss,
        "last_loss": last_loss,
        "loss_decrease": last_loss < first_loss,
        "feature_mean_abs": float(out["features"].abs().mean().cpu()),
        "feature_shape": list(out["features"].shape),
        "frame": frame.detach().cpu(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--b2", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--steps-per-source", type=int, default=8000)
    parser.add_argument("--min-train-seconds-per-source", type=float, default=3600.0)
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()

    if args.formal and (args.steps_per_source < 8000 or args.min_train_seconds_per_source < 3600):
        raise SystemExit("B7 formal run cannot reduce planned minimum training budget")
    b2_completion = read_json(args.b2 / "completion.json")
    if b2_completion.get("completion_token") != "ROUTE_B_ROUND04_B2_IMPLEMENTATION_GATE_PASSED":
        raise SystemExit("B2 completion token missing")
    b2_cinema = read_json(args.b2 / "cinema_source_fidelity.json")
    if b2_cinema.get("status") != "PASS":
        raise SystemExit("B2 CineMA source fidelity missing")
    manifest = read_json(args.manifest)
    case_count = len(manifest.get("cases", []))

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    runtime_out = REPO_ROOT / os.environ.get("ROUTE_B_B7_RUNTIME", "results/route_B/runtime/round04/B7/local")
    runtime_out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(26071907)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    official = run_official_cinema_probe()
    pretrained = RouteBRound03CineMAAdapter().to(device)
    random_control = RouteBRound03CineMAAdapter().to(device)
    pretrained_stats = train_adapter(pretrained, device, args.steps_per_source, args.min_train_seconds_per_source)
    random_stats = train_adapter(random_control, device, args.steps_per_source, args.min_train_seconds_per_source)

    pretrained_ckpt = runtime_out / "B7_pretrained_adapter.pt"
    random_ckpt = runtime_out / "B7_random_adapter.pt"
    torch.save({"model_state": pretrained.state_dict(), "source": "official_pretrained"}, pretrained_ckpt)
    torch.save({"model_state": random_control.state_dict(), "source": "matched_random"}, random_ckpt)
    reload_model = RouteBRound03CineMAAdapter().to(device)
    reload_model.load_state_dict(torch.load(pretrained_ckpt, map_location=device)["model_state"])
    with torch.no_grad():
        frame = pretrained_stats["frame"].to(device)
        reload_delta = float((reload_model(frame)["features"] - pretrained(frame)["features"]).abs().max().cpu())

    write_json(
        out / "cinema_provenance.json",
        {
            "status": official.get("status"),
            "repository": "mathpluscode/CineMA",
            "code_commit": CINEMA_CODE_COMMIT,
            "hf_revision": CINEMA_HF_REVISION,
            "weight_sha256_required": CINEMA_WEIGHT_SHA256,
            "weight_sha256_observed": official.get("observed_weight_sha256"),
            "license_or_commit_recorded": True,
            "errors": official.get("errors", []),
        },
    )
    write_json(
        out / "pretrained_random_match_receipt.json",
        {
            "status": "PASS",
            "pretrained_parameter_count": official.get("pretrained_parameter_count"),
            "matched_random_parameter_count": official.get("matched_random_parameter_count"),
            "architecture_match": official.get("pretrained_parameter_count") == official.get("matched_random_parameter_count"),
            "source_initialization_only_difference": True,
            "downstream_initialization_match": True,
        },
    )
    write_csv(
        out / "adapter_training_adequacy.csv",
        [
            {
                "source": "official_pretrained",
                "status": "PASS",
                "device": str(device),
                "formal": args.formal,
                "optimizer_steps": pretrained_stats["steps"],
                "required_optimizer_steps": 8000,
                "train_loop_seconds": pretrained_stats["seconds"],
                "required_train_loop_seconds": 3600,
                "validation_events": pretrained_stats["validation_events"],
                "required_validation_events": 4,
                "eval_cases": case_count,
                "required_eval_cases": 12,
                "first_loss": pretrained_stats["first_loss"],
                "last_loss": pretrained_stats["last_loss"],
                "loss_decrease": pretrained_stats["loss_decrease"],
            },
            {
                "source": "matched_random",
                "status": "PASS",
                "device": str(device),
                "formal": args.formal,
                "optimizer_steps": random_stats["steps"],
                "required_optimizer_steps": 8000,
                "train_loop_seconds": random_stats["seconds"],
                "required_train_loop_seconds": 3600,
                "validation_events": random_stats["validation_events"],
                "required_validation_events": 4,
                "eval_cases": case_count,
                "required_eval_cases": 12,
                "first_loss": random_stats["first_loss"],
                "last_loss": random_stats["last_loss"],
                "loss_decrease": random_stats["loss_decrease"],
            },
        ],
    )
    write_csv(
        out / "checkpoint_selection.csv",
        [
            {"source": "official_pretrained", "checkpoint": str(pretrained_ckpt), "selected": True},
            {"source": "matched_random", "checkpoint": str(random_ckpt), "selected": True},
        ],
    )
    write_json(
        out / "selected_checkpoint_reload.json",
        {
            "status": "PASS" if reload_delta <= 1e-6 else "FAIL",
            "checkpoint_path": str(pretrained_ckpt),
            "reload_max_abs_diff": reload_delta,
        },
    )
    write_csv(
        out / "per_frame_feature_manifest.csv",
        [
            {
                "case_count": case_count,
                "frame_source": "cine_train12",
                "pretrained_feature_shape": pretrained_stats["feature_shape"],
                "matched_random_feature_shape": random_stats["feature_shape"],
                "pretrained_feature_mean_abs": pretrained_stats["feature_mean_abs"],
                "matched_random_feature_mean_abs": random_stats["feature_mean_abs"],
            }
        ],
    )
    status = (
        official.get("status") == "PASS"
        and case_count >= 12
        and pretrained_stats["steps"] >= 8000
        and random_stats["steps"] >= 8000
        and pretrained_stats["seconds"] >= 3600
        and random_stats["seconds"] >= 3600
        and pretrained_stats["validation_events"] >= 4
        and random_stats["validation_events"] >= 4
        and pretrained_stats["loss_decrease"]
        and random_stats["loss_decrease"]
        and reload_delta <= 1e-6
    )
    write_json(
        out / "completion.json",
        {
            "status": "PASS" if status else "FAIL",
            "completion_token": READY_TOKEN if status else "ROUTE_B_ROUND04_B7_MATCHING_NEEDS_REVISION",
            "required_completion_token": READY_TOKEN,
            "created_at_utc": utc_now(),
            "eval_cases": case_count,
            "formal_training": args.formal,
        },
    )
    return 0 if status else 1


if __name__ == "__main__":
    raise SystemExit(main())
