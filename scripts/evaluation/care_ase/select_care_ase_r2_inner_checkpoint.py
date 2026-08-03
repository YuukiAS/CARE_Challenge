#!/usr/bin/env python
"""Deterministic CARE-ASE R2 inner checkpoint selector.

This utility consumes immutable inner monitor packets only. It never reads outer
cases, never searches thresholds, and never combines different pathology
checkpoints.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_STEPS = (4000, 6000, 8000, 10000, 12000, 14000)
REQUIRED_SUMMARY_FIELDS = (
    "scar_dice_mean",
    "scar_hd95_mean",
    "stock_scar_hd95_mean",
    "scar_remote_fp_volume_mm3_mean",
    "scar_harm_fraction_vs_nnunet",
    "pure_edema_dice_mean",
    "pure_edema_sensitivity_mean",
    "pure_edema_volume_ratio_mean",
    "pure_edema_hd95_mean",
    "stock_pure_edema_hd95_mean",
)


def load_packet(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "PASS":
        raise RuntimeError(f"monitor packet is not PASS: {path}")
    step = int(payload.get("checkpoint_step", -1))
    if step not in ALLOWED_STEPS:
        raise RuntimeError(f"checkpoint step {step} is not in fixed candidate set {ALLOWED_STEPS}")
    if payload.get("monitor_type") != "ASYNC_INNER_TREND_ONLY":
        raise RuntimeError(f"unexpected monitor packet type: {payload.get('monitor_type')}")
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError(f"monitor packet missing summary: {path}")
    missing = [field for field in REQUIRED_SUMMARY_FIELDS if field not in summary]
    if missing:
        raise RuntimeError(f"monitor packet missing selector metrics {missing}: {path}")
    if "outer" in json.dumps(payload, sort_keys=True).lower() and payload.get("outer_accessed", False) is True:
        raise RuntimeError(f"monitor packet indicates outer access: {path}")
    return payload


def score_packet(payload: dict[str, Any]) -> dict[str, float]:
    summary = payload["summary"]
    scar = float(summary["scar_dice_mean"])
    scar_hd95 = float(summary["scar_hd95_mean"])
    stock_scar_hd95 = float(summary["stock_scar_hd95_mean"])
    remote_fp = float(summary["scar_remote_fp_volume_mm3_mean"])
    harm_fraction = float(summary["scar_harm_fraction_vs_nnunet"])
    edema = float(summary["pure_edema_dice_mean"])
    edema_sens = float(summary["pure_edema_sensitivity_mean"])
    edema_ratio = float(summary["pure_edema_volume_ratio_mean"])
    edema_hd95 = float(summary["pure_edema_hd95_mean"])
    stock_edema_hd95 = float(summary["stock_pure_edema_hd95_mean"])
    scar_score = (
        scar
        - 0.002 * max(0.0, scar_hd95 - stock_scar_hd95)
        - 0.00002 * remote_fp
        - 0.05 * max(0.0, harm_fraction - 0.35)
    )
    edema_score = (
        edema
        + 0.20 * edema_sens
        - 0.05 * abs(edema_ratio - 1.0)
        - 0.002 * max(0.0, edema_hd95 - stock_edema_hd95)
    )
    return {
        "scar_score": scar_score,
        "edema_score": edema_score,
        "joint_score": 0.5 * (scar_score + edema_score),
    }


def select_checkpoint(packet_paths: list[Path]) -> dict[str, Any]:
    packets = [load_packet(path) for path in packet_paths]
    seen = sorted(int(packet["checkpoint_step"]) for packet in packets)
    if seen != list(ALLOWED_STEPS):
        raise RuntimeError(f"selector requires exactly fixed candidates {ALLOWED_STEPS}, observed {seen}")
    ranked = []
    for packet in packets:
        scores = score_packet(packet)
        ranked.append((scores["joint_score"], int(packet["checkpoint_step"]), packet, scores))
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, best_step, best_packet, scores = ranked[0]
    return {
        "status": "PASS",
        "selector_contract": "CARE_ASE_R2_FIXED_INNER_SELECTOR_V2",
        "allowed_steps": list(ALLOWED_STEPS),
        "selected_checkpoint_step": best_step,
        "joint_score": best_score,
        "scar_score": scores["scar_score"],
        "edema_score": scores["edema_score"],
        "tie_break": "later_step",
        "forbidden_inputs": ["outer", "threshold_search", "pathology_specific_checkpoint_splicing"],
        "selected_packet_checkpoint_sha256": best_packet.get("checkpoint_sha256"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = select_checkpoint(args.packet)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
