#!/usr/bin/env python3
"""Aggregate lightweight M9 SRR dictionary fidelity evidence."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


REQUIRED_OUTPUT_DIR = Path("results/20260708_srr_v3_m9_dictionary_fidelity_repair_training")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_summary(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runtime-root",
        action="append",
        default=[],
        help="Runtime root to scan; may be repeated. Defaults to runtime and runtime_* under the output directory.",
    )
    parser.add_argument("--out-dir", default=str(REQUIRED_OUTPUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime_roots = [Path(item) for item in args.runtime_root]
    if not runtime_roots:
        candidates = [out_dir / "runtime"]
        candidates.extend(sorted(out_dir.glob("runtime_*")))
        runtime_roots = []
        seen: set[Path] = set()
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in seen:
                runtime_roots.append(candidate)
                seen.add(resolved)

    rows: list[dict[str, object]] = []
    for runtime_root in runtime_roots:
        for summary_path in sorted(runtime_root.glob("variants/*/summary.json")):
            summary = load_summary(summary_path)
            variant = str(summary.get("variant", summary_path.parent.name))
            rows.append(
                {
                    "candidate_id": variant,
                    "runtime_root": str(runtime_root),
                    "summary_path": str(summary_path),
                    "actual_optimizer_steps": summary.get("actual_optimizer_steps", "EVIDENCE_NOT_FOUND"),
                    "train_loop_seconds": summary.get("train_loop_seconds", summary.get("elapsed_seconds", "EVIDENCE_NOT_FOUND")),
                    "checkpoint_selection_mode": summary.get("checkpoint_selection_mode", "EVIDENCE_NOT_FOUND"),
                    "checkpoint_selection_status": summary.get("checkpoint_selection_status", "EVIDENCE_NOT_FOUND"),
                    "checkpoint_best": summary.get("checkpoint_best", "EVIDENCE_NOT_FOUND"),
                }
            )

    if not rows:
        rows.append(
            {
                "candidate_id": "EVIDENCE_NOT_FOUND",
                "runtime_root": ";".join(str(path) for path in runtime_roots),
                "summary_path": "EVIDENCE_NOT_FOUND",
                "actual_optimizer_steps": "EVIDENCE_NOT_FOUND",
                "train_loop_seconds": "EVIDENCE_NOT_FOUND",
                "checkpoint_selection_mode": "EVIDENCE_NOT_FOUND",
                "checkpoint_selection_status": "EVIDENCE_NOT_FOUND",
                "checkpoint_best": "EVIDENCE_NOT_FOUND",
            }
        )
    write_csv(
        out_dir / "m9_training_budget_ledger.csv",
        rows,
        [
            "candidate_id",
            "runtime_root",
            "summary_path",
            "actual_optimizer_steps",
            "train_loop_seconds",
            "checkpoint_selection_mode",
            "checkpoint_selection_status",
            "checkpoint_best",
        ],
    )
    write_csv(
        out_dir / "m9_metric_aligned_checkpoint_selection.csv",
        [
            {
                "candidate_id": row["candidate_id"],
                "selection_metric": row["checkpoint_selection_mode"],
                "selected_checkpoint": row["checkpoint_best"],
                "status": row["checkpoint_selection_status"],
            }
            for row in rows
        ],
        ["candidate_id", "selection_metric", "selected_checkpoint", "status"],
    )
    print(f"wrote {out_dir / 'm9_training_budget_ledger.csv'}")


if __name__ == "__main__":
    main()
