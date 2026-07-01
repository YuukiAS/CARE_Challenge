#!/usr/bin/env python3
"""Aggregate cascade teacher route outputs for the rescue goal."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO_ROOT / "results/20260629_cascade_teacher_route"
VARIANTS = [
    "nnunet_anatomy_prior_refiner",
    "nnunet_pathology_teacher_srr_refiner",
    "coarse_to_fine_srr_roi",
]


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def read_comparison(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8") as f:
        return {str(r["subset"]): r for r in csv.DictReader(f)}


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fmt(value: object) -> str:
    if value in ("", None):
        return ""
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def variant_dir(root: Path, variants_root: Path | None, variant: str) -> Path:
    return (variants_root / variant) if variants_root is not None else (root / "variants" / variant)


def variant_rows(root: Path, variants_root: Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in VARIANTS:
        vdir = variant_dir(root, variants_root, variant)
        summary = load_json(vdir / "summary.json")
        pred_dir = Path(summary.get("prediction_dir", vdir / "predictions" / f"{variant}_oof_edema_residual" / "validation"))
        comparison = read_comparison(vdir / "baseline_vs_refiner_by_subset.csv")
        all_case = comparison.get("all_case", {})
        t2_pos = comparison.get("t2_present_gt_positive", {})
        center_c = comparison.get("CenterC", {})
        rows.append(
            {
                "variant": variant,
                "summary_present": bool(summary),
                "prediction_dir_present": pred_dir.is_dir(),
                "evaluation_ran": bool(summary.get("evaluation_ran")),
                "eval_decision": summary.get("eval_decision", ""),
                "elapsed_seconds": summary.get("elapsed_seconds", ""),
                "stop_reason": summary.get("stop_reason", ""),
                "delta_all_edema_dice": all_case.get("delta_edema_dice", ""),
                "delta_all_edema_hd95_improvement": all_case.get("delta_edema_hd95_improvement", ""),
                "delta_t2pos_edema_dice": t2_pos.get("delta_edema_dice", ""),
                "delta_t2pos_edema_hd95_improvement": t2_pos.get("delta_edema_hd95_improvement", ""),
                "delta_centerC_edema_dice": center_c.get("delta_edema_dice", ""),
                "delta_centerC_edema_hd95_improvement": center_c.get("delta_edema_hd95_improvement", ""),
                "delta_all_scar_dice": all_case.get("delta_scar_dice", ""),
                "delta_all_scar_hd95_improvement": all_case.get("delta_scar_hd95_improvement", ""),
                "ready": bool(summary and pred_dir.is_dir() and summary.get("evaluation_ran")),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_csv_with_fields(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_standard_artifacts(root: Path, rows: list[dict[str, Any]], variants_root: Path | None = None) -> None:
    subgroup_rows: list[dict[str, Any]] = []
    teacher_delta_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    for row in rows:
        variant = str(row["variant"])
        vdir = variant_dir(root, variants_root, variant)
        summary = load_json(vdir / "summary.json")
        comparison_rows = read_csv_rows(vdir / "baseline_vs_refiner_by_subset.csv")
        metrics_rows = read_csv_rows(Path(str(summary.get("metrics_path", vdir / "round10_fold0_very_short_metrics.csv"))))
        for comp in comparison_rows:
            enriched = {"variant": variant, **comp}
            subgroup_rows.append(enriched)
            teacher_delta_rows.append(enriched)
        for metric in metrics_rows:
            if metric.get("model") != "candidate_laneA_round10_edema_refiner":
                continue
            component_rows.append(
                {
                    "variant": variant,
                    "case_id": metric.get("case_id", ""),
                    "center": metric.get("center", ""),
                    "modality_group": metric.get("modality_group", ""),
                    "t2_present": metric.get("t2_present", ""),
                    "edema_gt_positive": metric.get("edema_gt_positive", ""),
                    "scar_gt_positive": metric.get("scar_gt_positive", ""),
                    "myops_edema_dice": metric.get("myops_edema_dice", ""),
                    "myops_edema_hd": metric.get("myops_edema_hd", ""),
                    "myops_edema_hd95": metric.get("myops_edema_hd95", ""),
                    "myops_edema_component_count": metric.get("myops_edema_component_count", ""),
                    "myops_edema_remote_fp": metric.get("myops_edema_remote_fp", ""),
                    "myops_scar_dice": metric.get("myops_scar_dice", ""),
                    "myops_scar_hd": metric.get("myops_scar_hd", ""),
                    "myops_scar_hd95": metric.get("myops_scar_hd95", ""),
                    "myops_scar_component_count": metric.get("myops_scar_component_count", ""),
                    "myops_scar_remote_fp": metric.get("myops_scar_remote_fp", ""),
                }
            )
    subgroup_fields = [
        "variant",
        "subset",
        "n",
        "baseline_edema_dice",
        "candidate_edema_dice",
        "delta_edema_dice",
        "baseline_edema_hd95",
        "candidate_edema_hd95",
        "delta_edema_hd95_improvement",
        "baseline_scar_dice",
        "candidate_scar_dice",
        "delta_scar_dice",
        "baseline_scar_hd95",
        "candidate_scar_hd95",
        "delta_scar_hd95_improvement",
    ]
    component_fields = [
        "variant",
        "case_id",
        "center",
        "modality_group",
        "t2_present",
        "edema_gt_positive",
        "scar_gt_positive",
        "myops_edema_dice",
        "myops_edema_hd",
        "myops_edema_hd95",
        "myops_edema_component_count",
        "myops_edema_remote_fp",
        "myops_scar_dice",
        "myops_scar_hd",
        "myops_scar_hd95",
        "myops_scar_component_count",
        "myops_scar_remote_fp",
    ]
    write_csv_with_fields(root / "subgroup_metrics.csv", subgroup_rows, subgroup_fields)
    write_csv_with_fields(root / "teacher_student_delta.csv", teacher_delta_rows, subgroup_fields)
    write_csv_with_fields(root / "component_hd_by_case.csv", component_rows, component_fields)

    roi_source = root / "teacher_cache" / "roi_coverage.csv"
    roi_rows = read_csv_rows(roi_source)
    if roi_rows:
        roi_fields = ["variant", *list(roi_rows[0].keys())]
        expanded = [{"variant": variant, **roi} for variant in VARIANTS for roi in roi_rows]
    else:
        roi_fields = ["variant", "case_id", "split", "class_id", "roi_coverage"]
        expanded = []
    write_csv_with_fields(root / "roi_coverage.csv", expanded, roi_fields)


def choose_status(rows: list[dict[str, Any]]) -> tuple[str, str, list[str]]:
    ready = [r for r in rows if r["ready"]]
    if len(ready) < len(VARIANTS):
        return "PENDING_FORMAL_CASCADE", "", [f"ready variants {len(ready)}/{len(VARIANTS)}"]
    failed_decisions = [r for r in ready if str(r.get("eval_decision", "")).startswith("fail_stop")]
    if len(failed_decisions) == len(ready):
        return (
            "STOP_NO_CASCADE_SIGNAL",
            "",
            [
                "all formal variants reported fail_stop_refiner_candidate",
                "tiny positive deltas are not treated as route selection evidence",
            ],
        )
    positives: list[tuple[float, dict[str, Any], str]] = []
    for row in ready:
        if str(row.get("eval_decision", "")).startswith("fail_stop"):
            continue
        for key in (
            "delta_t2pos_edema_dice",
            "delta_t2pos_edema_hd95_improvement",
            "delta_centerC_edema_dice",
            "delta_centerC_edema_hd95_improvement",
            "delta_all_scar_dice",
            "delta_all_scar_hd95_improvement",
        ):
            value = row.get(key)
            try:
                number = float(value)
            except (TypeError, ValueError):
                continue
            if number > 0:
                positives.append((number, row, key))
    if positives:
        number, row, key = max(positives, key=lambda x: x[0])
        return "SELECT_CASCADE_TEACHER_ROUTE", str(row["variant"]), [f"best_positive={row['variant']}.{key}:{number:.4f}"]
    return "STOP_NO_CASCADE_SIGNAL", "", ["no positive teacher-student delta across edema/scar decision metrics"]


def write_markdown(root: Path, rows: list[dict[str, Any]], status: str, selected: str, reasons: list[str]) -> None:
    ready = sum(1 for r in rows if r["ready"])
    lines = [
        "# Cascade Teacher Metrics Summary",
        "",
        f"Status: `{status}`",
        f"Selected variant: `{selected or 'none'}`",
        f"Ready variants: `{ready}/{len(VARIANTS)}`",
        "",
        "| variant | ready | eval decision | delta T2+ edema Dice | delta T2+ edema HD95 | delta all scar Dice | delta all scar HD95 |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {variant} | {ready} | {eval_decision} | {dt2d} | {dt2h} | {dsd} | {dsh} |".format(
                variant=row["variant"],
                ready=row["ready"],
                eval_decision=row["eval_decision"],
                dt2d=fmt(row["delta_t2pos_edema_dice"]),
                dt2h=fmt(row["delta_t2pos_edema_hd95_improvement"]),
                dsd=fmt(row["delta_all_scar_dice"]),
                dsh=fmt(row["delta_all_scar_hd95_improvement"]),
            )
        )
    lines.extend(["", "## Reasons", "", *[f"- {r}" for r in reasons]])
    (root / "metrics_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "aggregation_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if status == "PENDING_FORMAL_CASCADE":
        return
    (root / "selection.md").write_text(
        "\n".join(
            [
                "# Cascade Teacher Selection",
                "",
                f"status: `{status}`",
                f"selected_variant: `{selected or 'none'}`",
                "",
                "## Reasons",
                "",
                *[f"- {r}" for r in reasons],
                "",
                "No validation upload or fold expansion was performed.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--variants-root", type=Path, default=None, help="Override variant output base, useful for preflight contract dry-runs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = variant_rows(args.root, args.variants_root)
    write_csv(args.root / "aggregation_status.csv", rows)
    write_standard_artifacts(args.root, rows, args.variants_root)
    status, selected, reasons = choose_status(rows)
    write_markdown(args.root, rows, status, selected, reasons)
    print({"status": status, "selected": selected, "ready": sum(1 for r in rows if r["ready"])})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
