#!/usr/bin/env python
"""Deterministic local CARE-PRISM evaluation helper."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_prism_dataset import CAREPRISMAugmenter, CAREPRISMFullPatientDataset
from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_care_prism


def dice(prob: torch.Tensor, target: torch.Tensor, threshold: float = 0.5) -> float:
    pred = prob >= threshold
    tgt = target > 0.5
    inter = (pred & tgt).sum().float()
    denom = pred.sum().float() + tgt.sum().float()
    if float(denom) == 0.0:
        return 1.0
    return float((2.0 * inter / denom).cpu())


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {key: value.to(device) if torch.is_tensor(value) else value for key, value in batch.items()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--split", default="train")
    parser.add_argument("--max-cases", type=int, default=1)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "results/20260729_care_prism_v2_backbone_repair_and_resume/eval_probe")
    args = parser.parse_args()
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    model = build_care_prism(CAREPRISMConfig.from_nnunet_plans()).to(device)
    if args.checkpoint:
        payload = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
        model.load_state_dict(payload["model_state"])
    model.eval()
    ds = CAREPRISMFullPatientDataset(fold=args.fold, split=args.split, augmenter=CAREPRISMAugmenter(training=False))
    rows: list[dict[str, Any]] = []
    with torch.no_grad():
        for idx in range(min(args.max_cases, len(ds))):
            batch = move_batch(ds[idx], device)
            out = model(batch["images"], batch["availability"])
            rows.append(
                {
                    "case_id": batch["case_id"][0],
                    "scar_dice": dice(out["scar_probability"], batch["scar_target"]),
                    "edema_zone_dice": dice(out["edema_probability"], batch["edema_zone_target"]),
                    "t2_present": float(batch["t2_present"][0, 0]),
                    "no_t2_edema_exact_zero": float(batch["t2_present"][0, 0]) == 0.0 and float(out["edema_probability"].max()) == 0.0,
                }
            )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "case_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["case_id"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (args.output_dir / "summary.json").write_text(json.dumps({"rows": rows, "case_count": len(rows)}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "case_count": len(rows), "output_dir": str(args.output_dir)}, sort_keys=True))


if __name__ == "__main__":
    main()
