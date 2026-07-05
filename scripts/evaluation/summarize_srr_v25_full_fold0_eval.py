#!/usr/bin/env python3
"""Summarize SRR-v2.5 full fold0 eval-only help/harm rows."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_OUTPUT_ROOT = Path("results/20260704_srr_v25_training_ablation_matrix/full_fold0_eval")
DEFAULT_VARIANTS = (
    "srr_propref_shared_dual_dict",
    "srr_propref_no_proto_cascade",
    "srr_propref_scar_precision",
    "srr_v25_no_local_refine",
    "srr_v25_no_anatomy_roi",
    "srr_v25_no_anchor",
)
KEY_ROWS = (
    ("myops_edema", "dice"),
    ("myops_edema", "hd95"),
    ("myops_edema", "remote_fp_count"),
    ("myops_scar", "dice"),
    ("myops_scar", "hd95"),
    ("myops_scar", "remote_fp_count"),
)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value: str) -> str:
    try:
        return f"{float(value):.9g}"
    except (TypeError, ValueError):
        return value


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    ap.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    ap.add_argument("--output-md", type=Path, default=None)
    args = ap.parse_args()

    output_root = args.output_root
    variants = [item.strip() for item in args.variants.replace(";", ",").split(",") if item.strip()]
    manifest = read_json(output_root / "manifest.json")
    completed: list[str] = []
    incomplete: list[str] = []
    variant_rows: dict[str, dict[tuple[str, str], dict[str, str]]] = {}
    prediction_counts: dict[str, int] = {}
    case_metric_rows: dict[str, int] = {}
    subgroup_rows: dict[str, int] = {}

    for variant in variants:
        metrics = output_root / "variants" / variant / "component_hd_by_case_checkpoint_final_full_fold0.csv"
        subgroups = output_root / "variants" / variant / "subgroup_metrics_checkpoint_final_full_fold0.csv"
        ablation = output_root / "help_harm" / variant / "ablation_summary.csv"
        rows = read_csv(ablation)
        selected: dict[tuple[str, str], dict[str, str]] = {}
        for row in rows:
            srr_variant = row.get("srr_variant", "")
            if not srr_variant.endswith("__pathology_aware"):
                continue
            key = (row.get("metric_name", ""), row.get("metric", ""))
            if key in KEY_ROWS:
                selected[key] = row
        variant_rows[variant] = selected
        prediction_counts[variant] = len(list((output_root / "variants" / variant).rglob("*.nii.gz")))
        case_metric_rows[variant] = max(0, len(read_csv(metrics)))
        subgroup_rows[variant] = max(0, len(read_csv(subgroups)))
        if metrics.is_file() and subgroups.is_file() and ablation.is_file() and all(key in selected for key in KEY_ROWS):
            completed.append(variant)
        else:
            incomplete.append(variant)

    status = "FULL_FOLD0_EVAL_COMPLETE" if not incomplete else "PARTIAL_FULL_FOLD0_EVAL"
    lines: list[str] = [
        "# Full Fold0 Eval Summary",
        "",
        f"status: `{status}`",
        "",
        "This packet evaluates existing bounded checkpoints only. It does not train,",
        "rerun the current anchored packet, validation-package, or upload.",
        "",
        "## Completion",
        "",
        f"- expected variants: `{len(variants)}`",
        f"- completed variants: `{len(completed)}`",
        f"- manifest status: `{manifest.get('status', '')}`",
        f"- eval cases: `{manifest.get('eval_case_count', '')}`",
        f"- fold: `{manifest.get('fold', '')}`",
    ]
    if incomplete:
        lines.append(f"- incomplete variants: `{', '.join(incomplete)}`")
    lines.extend(["", "## Artifact Counts", "", "| variant | predictions | case metric rows | subgroup rows |", "| --- | ---: | ---: | ---: |"])
    for variant in variants:
        lines.append(
            f"| `{variant}` | {prediction_counts[variant]} | {case_metric_rows[variant]} | {subgroup_rows[variant]} |"
        )

    lines.extend(
        [
            "",
            "## Pathology-Aware Help/Harm Vs Same-Split nnU-Net",
            "",
            "| variant | metric_name | metric | n | delta_mean | help | harm | neutral |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for variant in variants:
        for key in KEY_ROWS:
            row = variant_rows.get(variant, {}).get(key)
            if row is None:
                lines.append(f"| `{variant}` | `{key[0]}` | `{key[1]}` |  |  |  |  |  |")
                continue
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{variant}`",
                        f"`{row['metric_name']}`",
                        f"`{row['metric']}`",
                        row["n"],
                        fmt(row["delta_mean"]),
                        row["help_count"],
                        row["harm_count"],
                        row["neutral_count"],
                    ]
                )
                + " |"
            )

    lines.extend(["", "## Decision", ""])
    if incomplete:
        lines.append(
            "The full-fold0 eval remains incomplete. Do not use partial rows for final audit, route promotion, or scientific stop."
        )
    else:
        lines.append(
            "All expected full-fold0 rows are present. This enables a read-only audit, but does not itself authorize route promotion, validation packaging, upload, or scientific stop."
        )

    output_md = args.output_md or (output_root / "full_fold0_eval_summary.md")
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
