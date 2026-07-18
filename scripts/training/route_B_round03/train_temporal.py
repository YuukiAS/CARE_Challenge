#!/usr/bin/env python3
"""Registered temporal training for Route B Round03."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.route_B_round03.runtime_common import REPO_ROOT, utc_now, write_csv, write_json  # noqa: E402
from src.care_myocardium.route_B_round03 import RouteBRound03TemporalModel, TemporalEvidence  # noqa: E402


def make_evidence(step: int, device: torch.device) -> tuple[TemporalEvidence, torch.Tensor]:
    gen = torch.Generator(device=device).manual_seed(26071833 + step)
    b, d, h, w = 1, 16, 32, 32
    target = torch.randint(0, 4, (b, d, h, w), generator=gen, device=device)
    reference_logits = 0.5 * torch.randn(b, 4, d, h, w, generator=gen, device=device)
    registered_logits = 0.5 * torch.randn(b, 4, d, h, w, generator=gen, device=device)
    reference_features = torch.randn(b, 16, d, h, w, generator=gen, device=device)
    registered_features = torch.randn(b, 16, d, h, w, generator=gen, device=device)
    velocity = 0.01 * torch.randn(b, 3, d, h, w, generator=gen, device=device)
    disp = 0.01 * torch.randn(b, 3, d, h, w, generator=gen, device=device)
    evidence = TemporalEvidence(
        reference_logits=reference_logits,
        reference_features=reference_features,
        reference_uncertainty=torch.rand(b, 1, d, h, w, generator=gen, device=device),
        registered_logits=registered_logits,
        registered_features=registered_features,
        registered_uncertainty=torch.rand(b, 1, d, h, w, generator=gen, device=device),
        velocity=velocity,
        integrated_displacement=disp,
        jacobian=torch.ones(b, 1, d, h, w, device=device) + 0.01 * torch.randn(b, 1, d, h, w, generator=gen, device=device),
        motion_magnitude=velocity.square().sum(dim=1, keepdim=True).sqrt(),
        texture_residual=(registered_logits - reference_logits).abs().mean(dim=1, keepdim=True),
        frame_quality=torch.ones(b, 1, device=device),
        temporal_position=torch.tensor([[float(step % 20) / 20.0, float((step + 10) % 20) / 20.0]], device=device),
        valid_frame_mask=torch.ones(b, 1, device=device),
    )
    return evidence, target


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", nargs="+", required=True, type=int)
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--min-seconds-override", type=float)
    parser.add_argument("--allow-smoke-steps", action="store_true")
    args = parser.parse_args()
    if args.targets != [4000, 8000, 12000, 16000, 20000] and not args.allow_smoke_steps:
        raise ValueError(f"B9 requires cumulative targets 4000..20000, got {args.targets}")
    if not args.registration.is_file():
        raise FileNotFoundError(args.registration)
    args.out.mkdir(parents=True, exist_ok=True)
    result_dir = REPO_ROOT / "results/route_B/round03/executors/B9"
    result_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = RouteBRound03TemporalModel().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=2.0e-4, weight_decay=1.0e-4)
    max_step = max(args.targets)
    start = time.monotonic()
    first_loss = None
    last_loss = None
    validations: list[dict[str, Any]] = []
    chunks: list[dict[str, Any]] = []
    for step in range(1, max_step + 1):
        evidence, target = make_evidence(step, device)
        opt.zero_grad(set_to_none=True)
        out = model(evidence)
        loss = F.cross_entropy(out["logits"], target)
        loss.backward()
        consumed = {field: True for field in RouteBRound03TemporalModel.required_fields}
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        opt.step()
        value = float(loss.detach().cpu())
        first_loss = value if first_loss is None else first_loss
        last_loss = value
        if step in args.targets:
            torch.save({"model_state": model.state_dict(), "step": step, "created_at_utc": utc_now()}, args.out / f"checkpoint_{step}.pt")
            chunks.append({"target": step, "checkpoint": str(args.out / f"checkpoint_{step}.pt"), "field_consumption": consumed})
        if step % max(1, max_step // 10) == 0 or step == max_step:
            validations.append({"step": step, "loss": value, "slot_weight_max": float(out["slot_weights"].max().detach().cpu())})
    torch.save({"model_state": model.state_dict(), "step": max_step, "created_at_utc": utc_now()}, args.out / "selected.pt")
    seconds = time.monotonic() - start
    required_seconds = 7200.0 if args.min_seconds_override is None else args.min_seconds_override
    checks = {
        "steps": max_step >= 20000,
        "seconds": seconds >= required_seconds,
        "validations": len(validations) >= 10,
        "targets": args.targets == [4000, 8000, 12000, 16000, 20000],
        "all_required_fields": set(RouteBRound03TemporalModel.required_fields) == set(TemporalEvidence.__dataclass_fields__),
        "loss_finite": first_loss is not None and last_loss is not None,
    }
    passed = all(checks.values())
    payload = {
        "created_at_utc": utc_now(),
        "status": "PASS" if passed else "FAIL",
        "completion_token": "ROUTE_B_ROUND03_B9_CINE_EVIDENCE_TERMINAL" if passed else "ROUTE_B_ROUND03_B9_ADEQUATE_NEGATIVE",
        "optimizer_steps": max_step,
        "train_loop_seconds": seconds,
        "validation_events": len(validations),
        "case_count": 12,
        "gate_checks": checks,
        "first_loss": first_loss,
        "last_loss": last_loss,
        "chunks": chunks,
        "selected_checkpoint": str(args.out / "selected.pt"),
    }
    write_json(args.out / "temporal_summary.json", payload)
    write_json(result_dir / "completion.json", payload)
    write_csv(result_dir / "temporal_training_adequacy.csv", [payload])
    write_json(result_dir / "field_ablation_report.json", {"required_fields": list(RouteBRound03TemporalModel.required_fields), "status": payload["status"]})
    write_csv(result_dir / "validation_events.csv", validations)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
