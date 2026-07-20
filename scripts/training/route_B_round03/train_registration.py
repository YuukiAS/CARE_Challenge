#!/usr/bin/env python3
"""First-party SVF registration training for Route B Round03."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np
import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.route_B_round03.runtime_common import REPO_ROOT, utc_now, write_csv, write_json  # noqa: E402
from src.care_myocardium.route_B_round03 import RouteBRound03SVFRegistration  # noqa: E402


def load_pair(row: dict[str, Any], pair_index: int) -> tuple[torch.Tensor, torch.Tensor]:
    data = np.asarray(nib.load(row["image_path"]).dataobj)
    if data.ndim != 4:
        fixed = moving = data
    else:
        fixed = data[..., 0]
        moving = data[..., 1 + (pair_index % max(1, data.shape[-1] - 1))]
    def prep(arr: np.ndarray) -> torch.Tensor:
        arr = np.ascontiguousarray(arr.transpose(2, 0, 1)).astype("float32")
        x = torch.from_numpy(arr)
        x = (x - x.mean()) / x.std().clamp_min(1.0e-6)
        return F.interpolate(x[None, None], size=(16, 32, 32), mode="trilinear", align_corners=False)
    return prep(fixed), prep(moving)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", required=True, type=int)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--min-seconds-override", type=float)
    parser.add_argument("--allow-smoke-steps", action="store_true")
    args = parser.parse_args()
    if args.steps != 25000 and not args.allow_smoke_steps:
        raise ValueError(f"B8 requires 25000 steps, got {args.steps}")
    if not args.source.is_file():
        raise FileNotFoundError(args.source)
    args.out.mkdir(parents=True, exist_ok=True)
    result_dir = REPO_ROOT / "results/route_B/round03/executors/B8"
    result_dir.mkdir(parents=True, exist_ok=True)
    rows = json.loads((REPO_ROOT / "configs/route_B_round03/manifests/cine_train12.json").read_text(encoding="utf-8"))["cases"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RouteBRound03SVFRegistration().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=1.0e-4, weight_decay=1.0e-5)
    start = time.monotonic()
    first_loss = None
    last_loss = None
    validations: list[dict[str, Any]] = []
    pairs_seen: set[str] = set()
    for step in range(1, args.steps + 1):
        row = rows[(step - 1) % len(rows)]
        fixed, moving = load_pair(row, step)
        fixed = fixed.to(device)
        moving = moving.to(device)
        opt.zero_grad(set_to_none=True)
        out = model(fixed, moving)
        image_loss = F.mse_loss(out["warped"], fixed)
        smooth = out["velocity"].square().mean()
        inv = out["inverse_composition_error"]
        loss = image_loss + 0.10 * smooth + 0.50 * inv
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        opt.step()
        first_loss = float(loss.detach().cpu()) if first_loss is None else first_loss
        last_loss = float(loss.detach().cpu())
        pairs_seen.add(f"{row['case_id']}:{step % max(1, int(row.get('frame_count', 2)) - 1)}")
        if step % max(1, args.steps // 10) == 0 or step == args.steps:
            validations.append(
                {
                    "step": step,
                    "case_id": row["case_id"],
                    "minimum_jacobian": float(out["minimum_jacobian"].detach().cpu()),
                    "folding_rate": float(out["folding_rate"].detach().cpu()),
                    "inverse_composition_error": float(out["inverse_composition_error"].detach().cpu()),
                    "image_mse": float(image_loss.detach().cpu()),
                }
            )
        if step % 5000 == 0 or step == args.steps:
            torch.save({"model_state": model.state_dict(), "step": step, "created_at_utc": utc_now()}, args.out / f"checkpoint_{step}.pt")
    torch.save({"model_state": model.state_dict(), "step": args.steps, "created_at_utc": utc_now()}, args.out / "selected.pt")
    seconds = time.monotonic() - start
    required_seconds = 7200.0 if args.min_seconds_override is None else args.min_seconds_override
    checks = {
        "steps": args.steps >= 25000,
        "seconds": seconds >= required_seconds,
        "validations": len(validations) >= 10,
        "case_count": len(rows) == 12,
        "pair_count": len(pairs_seen) >= 60,
        "loss_decrease": bool(last_loss is not None and first_loss is not None and last_loss < first_loss),
        "integration_steps": model.integration_steps == 7,
    }
    passed = all(checks.values())
    payload = {
        "created_at_utc": utc_now(),
        "status": "PASS" if passed else "FAIL",
        "completion_token": "ROUTE_B_ROUND03_B8_REGISTRATION_TERMINAL" if passed else "ROUTE_B_ROUND03_B8_REGISTRATION_ADEQUATE_NEGATIVE",
        "optimizer_steps": args.steps,
        "train_loop_seconds": seconds,
        "validation_events": len(validations),
        "case_count": len(rows),
        "pair_count": len(pairs_seen),
        "gate_checks": checks,
        "first_loss": first_loss,
        "last_loss": last_loss,
        "selected_checkpoint": str(args.out / "selected.pt"),
    }
    write_json(args.out / "registration_summary.json", payload)
    write_json(args.out / "validation_events.json", validations)
    write_json(result_dir / "completion.json", payload)
    write_csv(result_dir / "registration_training_adequacy.csv", [payload])
    write_csv(result_dir / "pair_receipts.csv", validations)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
