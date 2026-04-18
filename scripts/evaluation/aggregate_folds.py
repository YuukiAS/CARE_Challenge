#!/usr/bin/env python3
"""Aggregate per-fold evaluation_summary.json files into mean ± std (Markdown + JSON)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser(description="Aggregate fold metrics from evaluate_predictions.py outputs")
    ap.add_argument(
        "--inputs",
        nargs="+",
        type=Path,
        required=True,
        help="Paths to evaluation_summary.json (one per fold)",
    )
    ap.add_argument("--output-json", type=Path, default=None)
    ap.add_argument("--output-md", type=Path, default=None)
    args = ap.parse_args()

    keys: set[str] = set()
    fold_means: list[dict[str, float]] = []

    for p in args.inputs:
        if not p.is_file():
            print(f"Missing {p}", file=sys.stderr)
            sys.exit(1)
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        md = data.get("mean_dice", {})
        fold_means.append({k: float(v) for k, v in md.items()})
        keys.update(md.keys())

    agg: dict[str, dict[str, float]] = {}
    for k in sorted(keys):
        vals = [fm[k] for fm in fold_means if k in fm]
        if not vals:
            continue
        arr = np.array(vals, dtype=np.float64)
        agg[k] = {"mean": float(arr.mean()), "std": float(arr.std(ddof=1) if len(arr) > 1 else 0.0), "n": len(vals)}

    out = {"folds": len(fold_means), "metrics": agg}

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {args.output_json}")

    if args.output_md:
        lines = ["| Metric | mean ± std |", "| --- | --- |"]
        for k in sorted(agg.keys()):
            m = agg[k]
            lines.append(f"| {k} | {m['mean']:.4f} ± {m['std']:.4f} |")
        args.output_md.parent.mkdir(parents=True, exist_ok=True)
        args.output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Wrote {args.output_md}")

    if not args.output_json and not args.output_md:
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
