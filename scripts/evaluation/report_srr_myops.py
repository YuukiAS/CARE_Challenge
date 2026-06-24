#!/usr/bin/env python3
"""Report SRR-MyoPS task-scoped artifacts without validation upload."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-json", type=Path, default=Path("results/20260621_srr_spec/one_batch_smoke.json"))
    parser.add_argument("--output-md", type=Path, default=Path("results/20260621_srr_spec/smoke_report.md"))
    args = parser.parse_args()
    data = json.loads(args.smoke_json.read_text(encoding="utf-8"))
    lines = [
        "# SRR-MyoPS Smoke Report",
        "",
        f"- status: `{data['status']}`",
        f"- loss: `{data['loss']:.6f}`",
        f"- logits shape: `{data['logits_shape']}`",
        "- validation upload: not run",
    ]
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
