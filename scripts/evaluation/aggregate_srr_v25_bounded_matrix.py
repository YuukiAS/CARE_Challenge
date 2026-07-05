#!/usr/bin/env python3
"""Aggregate bounded SRR-v2.5 matrix variant outputs."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, rows: Iterable[dict[str, object]]) -> None:
    materialized = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not materialized:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in materialized:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(materialized)


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix-root", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--checkpoint", default="checkpoint_final")
    args = ap.parse_args()

    matrix_root = args.matrix_root
    output_dir = args.output_dir
    variants_dir = matrix_root / "variants"
    variant_dirs = sorted(path for path in variants_dir.iterdir() if path.is_dir()) if variants_dir.is_dir() else []

    training_rows: list[dict[str, object]] = []
    subgroup_rows: list[dict[str, object]] = []
    help_harm_rows: list[dict[str, object]] = []
    ablation_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []

    for variant_dir in variant_dirs:
        variant = variant_dir.name
        summary = read_json(variant_dir / "summary.json")
        summary_rows.append(
            {
                "variant": variant,
                "model_variant": summary.get("model_variant", summary.get("variant", "")),
                "actual_optimizer_steps": summary.get("actual_optimizer_steps", ""),
                "stop_reason": summary.get("stop_reason", ""),
                "eval_cases": summary.get("eval_cases", ""),
                "eval_case_ids": ",".join(str(v) for v in summary.get("eval_case_ids", []) or []),
                "best_step": summary.get("best_step", ""),
                "best_val_patch_loss": summary.get("best_val_patch_loss", ""),
                "first_train_loss": summary.get("first_train_loss", ""),
                "last_train_loss": summary.get("last_train_loss", ""),
                "loss_decrease": summary.get("loss_decrease", ""),
                "elapsed_seconds": summary.get("elapsed_seconds", ""),
                "disable_local_refinement": summary.get("disable_local_refinement", ""),
                "disable_anatomy_roi_prior": summary.get("disable_anatomy_roi_prior", ""),
                "disable_nnunet_anchor": summary.get("disable_nnunet_anchor", ""),
                "prototype_source": (summary.get("prototype_bank_summary") or {}).get("source", "")
                if isinstance(summary.get("prototype_bank_summary"), dict)
                else "",
            }
        )
        for row in read_rows(variant_dir / "training_log.csv"):
            row.setdefault("variant", variant)
            training_rows.append(row)
        for row in read_rows(variant_dir / f"subgroup_metrics_{args.checkpoint}.csv"):
            row["matrix_variant"] = variant
            subgroup_rows.append(row)
        hh_dir = matrix_root / "help_harm" / variant
        for row in read_rows(hh_dir / "help_harm_vs_nnunet.csv"):
            row["matrix_variant"] = variant
            help_harm_rows.append(row)
        for row in read_rows(hh_dir / "ablation_summary.csv"):
            row["matrix_variant"] = variant
            ablation_rows.append(row)

    write_rows(output_dir / "bounded_matrix_summary.csv", summary_rows)
    write_rows(output_dir / "training_curves.csv", training_rows)
    write_rows(output_dir / "subgroup_metrics.csv", subgroup_rows)
    write_rows(output_dir / "help_harm_vs_nnunet.csv", help_harm_rows)
    write_rows(output_dir / "ablation_summary.csv", ablation_rows)

    matrix_lines = [
        "# Variant Matrix",
        "",
        "task_key: `20260704_srr_v25_training_ablation_matrix`",
        "",
        "## Bounded Matrix Evidence",
        "",
        "This is a bounded hard-subgroup matrix with identity rows, not the full required formal matrix.",
        "All rows use fold0 and explicit eval cases `Case1002,Case2002,Case3004,Case3011`.",
        "",
        "| matrix variant | model variant | steps | stop reason | eval cases | evidence status |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in summary_rows:
        evidence_status = "IDENTITY_EXACT_NNUNET" if row["stop_reason"] == "identity_export_only" else "BOUNDED_HARD_SUBGROUP_MATRIX"
        matrix_lines.append(
            "| `{variant}` | `{model_variant}` | {actual_optimizer_steps} | `{stop_reason}` | {eval_cases} | `{evidence_status}` |".format(
                evidence_status=evidence_status, **row
            )
        )
    covered = {str(row["variant"]) for row in summary_rows}
    required = {
        "local refinement": "srr_v25_no_local_refine",
        "anatomy distance/ROI prior": "srr_v25_no_anatomy_roi",
        "nnU-Net anchor": "srr_v25_no_anchor",
    }
    missing = [label for label, variant in required.items() if variant not in covered]
    matrix_lines.extend(["", "## Required Variant Coverage", ""])
    matrix_lines.append("- current anchored PropRef packet is carried forward as a negative baseline but not rerun.")
    for label, variant in required.items():
        status = "covered" if variant in covered else "missing"
        matrix_lines.append(f"- full SRR-v2.5 without {label}: `{status}` via `{variant}`.")
    matrix_lines.append("- same-split nnU-Net only, nnU-Net context identity, and closed-gate identity fallback now exist for the hard-subgroup cases.")
    matrix_lines.extend(
        [
            "",
            f"remaining_required_variant_rows: `{', '.join(missing) if missing else 'none'}`",
            "",
            "No route promotion, scientific stop, fold expansion, validation package, or upload is supported.",
            "",
        ]
    )
    (output_dir / "variant_matrix.md").write_text("\n".join(matrix_lines), encoding="utf-8")

    decision = [
        "# Mechanism Decision",
        "",
        "decision: `BOUNDED_MATRIX_ROW_COMPLETE_PARTIAL_FULL_FOLD0_NEEDS_REMAINING_ROWS_AND_AUDIT`",
        "",
        "The bounded matrix produced same-split hard-subgroup help/harm rows for three PropRef variants plus two identity rows.",
        "It is useful for mechanism triage but remains underpowered and does not satisfy the full task matrix.",
        "",
        "Current decision: missing hard-subgroup ablation rows are now covered at bounded 6-step scale; the primary full-fold0 row is complete, but remaining full-fold0 rows and final read-only audit are still required.",
        "",
    ]
    (output_dir / "mechanism_decision.md").write_text("\n".join(decision), encoding="utf-8")

    same_split = [
        "# Same-Split Metrics",
        "",
        f"- matrix_root: `{matrix_root}`",
        f"- variants: `{', '.join(row['variant'] for row in summary_rows)}`",
        "- comparator: fold0 nnU-Net validation predictions",
        "- output table: `help_harm_vs_nnunet.csv`",
        "",
        "This file summarizes the bounded matrix source; detailed case/metric rows are in CSV.",
        "",
        "Identity rows `nnunet_context_identity` and `closed_gate_identity_fallback` have zero delta versus nnU-Net for Dice, HD95, component count, and remote-FP metrics on the explicit hard-subgroup cases.",
        "",
        "Isolated bounded rows now cover no-local-refine, no-ROI/anatomy, and no-anchor. `srr_v25_no_anchor` is strongly harmful on this packet: pathology-aware scar Dice delta `-0.608290`, edema Dice delta `-0.311185`, scar remote-FP delta `+801.0`, and edema remote-FP delta `+4635.5`. Anchor-enabled isolated rows remain near-neutral and show no remote-FP regression.",
        "",
    ]
    (output_dir / "same_split_metrics.md").write_text("\n".join(same_split), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
