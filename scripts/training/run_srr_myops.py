#!/usr/bin/env python3
"""SRR-MyoPS bounded smoke/training entrypoint.

The spec task uses only ``--smoke``. Fold0 training is intentionally left for
``prompts/tasks/20260621_srr_fold0.md`` after the GO_FOLD0 gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.losses.srr_losses import srr_total_loss
from src.care_myocardium.models.srr_myops import SRRMyoPSLite


def run_smoke(output_json: Path) -> None:
    torch.manual_seed(20260621)
    model = SRRMyoPSLite(base_channels=8)
    x = torch.randn(3, 3, 8, 12, 10)
    availability = torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0], [1.0, 0.0, 0.0]])
    labels = torch.zeros(3, 8, 12, 10, dtype=torch.long)
    labels[0, 2:4, 4:7, 4:7] = 4
    labels[:, 3:5, 5:8, 5:8] = 5
    outputs = model(x, availability)
    loss, metrics = srr_total_loss(outputs, labels, availability)
    loss.backward()
    result = {
        "status": "pass",
        "loss": float(loss.detach()),
        "logits_shape": list(outputs["logits"].shape),
        "gate_sums": {name: [float(v.detach()) for v in gate.sum(dim=1)] for name, gate in outputs["gates"].items()},
        "metrics": {name: float(value.detach()) for name, value in metrics.items()},
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="Run synthetic one-batch forward/backward only.")
    parser.add_argument(
        "--output-json",
        type=Path,
        default=REPO_ROOT / "results/20260621_srr_spec/one_batch_smoke.json",
    )
    args = parser.parse_args()
    if not args.smoke:
        raise SystemExit("Only --smoke is enabled in the spec task. Use the fold0 task for training.")
    run_smoke(args.output_json)


if __name__ == "__main__":
    main()
