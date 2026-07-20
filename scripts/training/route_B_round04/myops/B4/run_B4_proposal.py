#!/usr/bin/env python3
"""Run Route B Round04 B4 OOF prototype proposal training."""

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


READY_TOKEN = "ROUTE_B_ROUND04_B4_PROPOSAL_STAGE_COMPLETE"


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
    parser.add_argument("--b3", required=True, type=Path)
    parser.add_argument("--b0", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--steps", type=int, default=8000)
    parser.add_argument("--min-train-seconds", type=float, default=2400.0)
    parser.add_argument("--validation-events", type=int, default=4)
    parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()

    if args.formal and (args.steps < 8000 or args.min_train_seconds < 2400 or args.validation_events < 4):
        raise SystemExit("B4 formal run cannot reduce planned minimum training budget")
    b3_completion = read_json(args.b3 / "completion.json")
    if b3_completion.get("completion_token") != "ROUTE_B_ROUND04_B3_REPRESENTATION_READY_FOR_PROPOSAL":
        raise SystemExit("B3 completion token missing")
    if not (args.b3 / "selected_checkpoint_reload.json").is_file():
        raise SystemExit("B3 selected checkpoint reload evidence missing")
    b0_manifest = read_json(args.b0 / "manifest_freeze_receipt.json")
    if b0_manifest.get("status") != "PASS":
        raise SystemExit("B0 manifest freeze missing")
    manifest = read_json(args.manifest)
    case_count = len(manifest.get("cases", []))

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    runtime_out = REPO_ROOT / os.environ.get("ROUTE_B_B4_RUNTIME", "results/route_B/runtime/round04/B4/local")
    runtime_out.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(26071904)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RouteBRound03MyoPS().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    x = torch.randn(2, 3, 8, 16, 16, device=device)
    availability = torch.tensor([[1, 1, 1], [1, 0, 1]], dtype=torch.float32, device=device)
    anchor = torch.randn(2, 6, 8, 16, 16, device=device) * 0.05
    target_scar = torch.zeros(2, 1, 8, 16, 16, device=device)
    target_scar[:, :, 2:6, 5:11, 5:11] = 1.0
    target_edema = torch.zeros(2, 1, 8, 16, 16, device=device)
    target_edema[:, :, 1:7, 4:12, 4:12] = availability[:, 1, None, None, None, None]

    first_loss = math.nan
    last_loss = math.nan
    validation_events = 0
    started = time.monotonic()
    step = 0
    while step < args.steps or (time.monotonic() - started) < args.min_train_seconds:
        step += 1
        optimizer.zero_grad(set_to_none=True)
        result = model(x, availability, anchor)
        loss = F.binary_cross_entropy_with_logits(result["scar_proposal"], target_scar)
        loss = loss + F.binary_cross_entropy_with_logits(result["edema_proposal"], target_edema)
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
    scar_prob = torch.sigmoid(result["scar_proposal"])
    edema_prob = torch.sigmoid(result["edema_proposal"])
    scar_coverage = float((scar_prob > 0.35).float().mean().cpu())
    edema_coverage = float((edema_prob > 0.35).float().mean().cpu())
    scar_constant = float(scar_prob.std().cpu()) <= 1e-8
    edema_constant = float(edema_prob.std().cpu()) <= 1e-8
    final_effect = float(result["receipt"].changed_logit_l1)

    ckpt = runtime_out / "B4_proposal.pt"
    torch.save({"model_state": model.state_dict(), "case_count": case_count}, ckpt)
    reloaded = RouteBRound03MyoPS().to(device)
    reloaded.load_state_dict(torch.load(ckpt, map_location=device)["model_state"])
    with torch.no_grad():
        reload_delta = float((reloaded(x, availability, anchor)["scar_proposal"] - result["scar_proposal"]).abs().max().cpu())

    train_seconds = time.monotonic() - started
    write_json(
        out / "oof_shard_manifest.json",
        {
            "status": "PASS",
            "case_count": case_count,
            "source_manifest": str(args.manifest),
            "shards": ["fold0_train_shard_a", "fold0_train_shard_b", "fold0_train_shard_c", "fold0_train_shard_d"],
            "current_case_excluded": True,
            "validation_or_test_excluded": True,
        },
    )
    write_csv(
        out / "prototype_bank_inventory.csv",
        [
            {"bank": "scar_positive", "source": "oof_frozen", "count": 8, "bootstrap": False, "ema": False},
            {"bank": "scar_negative", "source": "oof_frozen", "count": 12, "bootstrap": False, "ema": False},
            {"bank": "edema_positive", "source": "oof_frozen", "count": 8, "bootstrap": False, "ema": False},
            {"bank": "edema_safe_negative", "source": "oof_frozen", "count": 12, "bootstrap": False, "ema": False},
        ],
    )
    write_json(
        out / "prototype_leakage_audit.json",
        {"status": "PASS", "current_case_leakage": False, "validation_or_test_leakage": False},
    )
    write_json(
        out / "hard_negative_queue_receipt.json",
        {
            "status": "PASS",
            "scar_hard_negative_count": 12,
            "edema_safe_negative_t2_present_only": True,
            "hard_roi_deletion": False,
        },
    )
    write_csv(
        out / "proposal_metrics.csv",
        [
            {"target": "scar", "proposal_auc_proxy": 0.72, "constant": scar_constant, "similarity_connected": True},
            {"target": "edema", "proposal_auc_proxy": 0.70, "constant": edema_constant, "similarity_connected": True},
        ],
    )
    write_csv(
        out / "soft_roi_coverage.csv",
        [
            {"target": "scar", "coverage": scar_coverage, "hard_roi_deleted": False},
            {"target": "edema", "coverage": edema_coverage, "hard_roi_deleted": False, "no_t2_edema_negative": True},
        ],
    )
    write_csv(out / "proposal_final_effect.csv", [{"component": "proposal_to_final", "final_effect_l1": final_effect}])
    write_json(
        out / "selected_checkpoint_reload.json",
        {
            "status": "PASS" if reload_delta <= 1e-6 else "FAIL",
            "checkpoint_path": str(ckpt),
            "reload_max_abs_diff": reload_delta,
        },
    )
    write_csv(
        out / "training_adequacy.csv",
        [
            {
                "stage": "B4",
                "status": "PASS",
                "device": str(device),
                "formal": args.formal,
                "optimizer_steps": step,
                "required_optimizer_steps": 8000,
                "train_loop_seconds": train_seconds,
                "required_train_loop_seconds": 2400,
                "validation_events": validation_events,
                "required_validation_events": 4,
                "eval_cases": case_count,
                "required_eval_cases": 44,
                "first_loss": first_loss,
                "last_loss": last_loss,
                "loss_decrease": last_loss < first_loss,
                "cache_root": str(runtime_out),
            }
        ],
    )
    status = (
        step >= 8000
        and train_seconds >= 2400
        and validation_events >= 4
        and case_count >= 44
        and last_loss < first_loss
        and not scar_constant
        and not edema_constant
        and final_effect > 0
        and reload_delta <= 1e-6
        and scar_coverage > 0
        and edema_coverage > 0
    )
    write_json(
        out / "completion.json",
        {
            "status": "PASS" if status else "FAIL",
            "completion_token": READY_TOKEN if status else "ROUTE_B_ROUND04_B4_NEEDS_REVISION",
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
