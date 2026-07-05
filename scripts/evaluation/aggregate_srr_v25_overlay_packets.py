#!/usr/bin/env python3
"""Aggregate per-variant SRR-v2.5 failure overlay packets."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Iterable


DEFAULT_VARIANTS = (
    "srr_propref_shared_dual_dict",
    "srr_propref_no_proto_cascade",
    "srr_propref_scar_precision",
    "srr_v25_no_local_refine",
    "srr_v25_no_anatomy_roi",
    "srr_v25_no_anchor",
)


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: Iterable[dict[str, object]]) -> int:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not materialized:
        path.write_text("", encoding="utf-8")
        return 0
    fields: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(materialized)
    return len(materialized)


def aggregate_table(root: Path, variants: list[str], source_name: str, output_name: str) -> int:
    rows: list[dict[str, object]] = []
    for variant in variants:
        for row in read_rows(root / variant / source_name):
            rows.append({"matrix_variant": variant, **row})
    return write_rows(root / output_name, rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    args = ap.parse_args()

    root = args.root
    variants = [item.strip() for item in args.variants.replace(";", ",").split(",") if item.strip()]
    table_counts = {
        "bounded_matrix_overlay_taxonomy.csv": aggregate_table(
            root,
            variants,
            "case_error_taxonomy.csv",
            "bounded_matrix_overlay_taxonomy.csv",
        ),
        "bounded_matrix_overlay_proposal_refiner.csv": aggregate_table(
            root,
            variants,
            "proposal_vs_refiner_breakdown.csv",
            "bounded_matrix_overlay_proposal_refiner.csv",
        ),
        "bounded_matrix_overlay_dictionary_trace.csv": aggregate_table(
            root,
            variants,
            "dictionary_gate_trace.csv",
            "bounded_matrix_overlay_dictionary_trace.csv",
        ),
        "bounded_matrix_overlay_residual_gate_trace.csv": aggregate_table(
            root,
            variants,
            "residual_gate_trace.csv",
            "bounded_matrix_overlay_residual_gate_trace.csv",
        ),
    }

    taxonomy_counts: dict[tuple[str, str, str], int] = {}
    for row in read_rows(root / "bounded_matrix_overlay_taxonomy.csv"):
        key = (
            row.get("matrix_variant", ""),
            row.get("metric_name", ""),
            row.get("taxonomy", ""),
        )
        taxonomy_counts[key] = taxonomy_counts.get(key, 0) + 1

    lines = [
        "# Bounded Matrix Overlay Summary",
        "",
        f"source_root: `{root}`",
        "",
        "## Generated Tables",
        "",
    ]
    for name, count in table_counts.items():
        lines.append(f"- `{name}`: {count} rows")
    lines.extend(
        [
            "",
            "## Taxonomy Counts",
            "",
            "| matrix_variant | metric_name | taxonomy | count |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for (variant, metric_name, taxonomy), count in sorted(taxonomy_counts.items()):
        lines.append(f"| `{variant}` | `{metric_name}` | `{taxonomy}` | {count} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Anchor-enabled rows mostly stay in `neutral_or_minor` or boundary/extent categories on this bounded packet.",
            "- `srr_v25_no_anchor` concentrates failures in `remote_island;proposal_flooding_or_decode_export;refiner_overcorrection`, matching the help/harm remote-FP regression.",
            "- This is bounded hard-subgroup evidence only; it does not replace full fold0 subgroup metrics or final read-only audit.",
            "",
        ]
    )
    (root / "bounded_matrix_overlay_summary.md").write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
