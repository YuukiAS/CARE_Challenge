#!/usr/bin/env python3
"""Combine SRR fold0 variant outputs and write task-level reports."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from collections import defaultdict
from statistics import mean


DEFAULT_VARIANTS = ("conditional_dualhead_control", "srr_minimal")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def as_float(value: str | None) -> float | None:
    if value in (None, "", "None", "NA", "nan"):
        return None
    try:
        v = float(value)
    except ValueError:
        return None
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def find_row(rows: list[dict[str, str]], variant: str, class_id: int, group: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("variant") == variant and int(row.get("class_id", -1)) == class_id and row.get("group") == group:
            return row
    return None


def mean_weight(rows: list[dict[str, str]], variant: str, task: str) -> float | None:
    vals = [as_float(r.get("mean_weight")) for r in rows if r.get("variant") == variant and r.get("task") == task]
    vals = [v for v in vals if v is not None]
    return float(mean(vals)) if vals else None


def expert_weight_summary(rows: list[dict[str, str]], variant: str, task: str) -> tuple[dict[int, float], float | None]:
    by_expert: dict[int, list[float]] = defaultdict(list)
    max_row: float | None = None
    for row in rows:
        if row.get("variant") != variant or row.get("task") != task:
            continue
        value = as_float(row.get("mean_weight"))
        if value is None:
            continue
        if max_row is None or value > max_row:
            max_row = value
        try:
            expert_index = int(row.get("expert_index", ""))
        except ValueError:
            continue
        by_expert[expert_index].append(value)
    return {idx: float(mean(vals)) for idx, vals in sorted(by_expert.items())}, max_row


def decide(subgroups: list[dict[str, str]], usage: list[dict[str, str]], variants: list[str], mode: str) -> tuple[str, list[str]]:
    if mode == "recovery":
        return decide_recovery(subgroups, usage, variants)
    reasons: list[str] = []
    a_ede = find_row(subgroups, "conditional_dualhead_control", 4, "gt_positive_only")
    b_ede = find_row(subgroups, "srr_minimal", 4, "gt_positive_only")
    a_scar = find_row(subgroups, "conditional_dualhead_control", 5, "all_cases")
    b_scar = find_row(subgroups, "srr_minimal", 5, "all_cases")
    if a_ede is None or b_ede is None or a_scar is None or b_scar is None:
        return "STOP_PIPELINE_BUG", ["missing required subgroup rows"]
    a_ede_dice = as_float(a_ede.get("dice_mean"))
    b_ede_dice = as_float(b_ede.get("dice_mean"))
    a_ede_hd95 = as_float(a_ede.get("hd95_mean"))
    b_ede_hd95 = as_float(b_ede.get("hd95_mean"))
    a_scar_dice = as_float(a_scar.get("dice_mean"))
    b_scar_dice = as_float(b_scar.get("dice_mean"))
    if None in (a_ede_dice, b_ede_dice, a_scar_dice, b_scar_dice):
        return "STOP_PIPELINE_BUG", ["required Dice values are missing"]
    edema_dice_gain = float(b_ede_dice) - float(a_ede_dice)
    scar_delta = float(b_scar_dice) - float(a_scar_dice)
    reasons.append(f"edema_gt_positive_dice_delta_B_minus_A={edema_dice_gain:.4f}")
    reasons.append(f"scar_all_cases_dice_delta_B_minus_A={scar_delta:.4f}")
    if a_ede_hd95 is not None and b_ede_hd95 is not None:
        reasons.append(f"edema_gt_positive_hd95_delta_B_minus_A={float(b_ede_hd95) - float(a_ede_hd95):.4f}")
    sr_usage = [as_float(r.get("mean_weight")) for r in usage if r.get("variant") == "srr_minimal" and r.get("task") in {"anatomy", "scar", "edema"}]
    sr_usage = [v for v in sr_usage if v is not None]
    if not sr_usage:
        return "REVISE_ROUTING", [*reasons, "missing SRR gate usage"]
    if max(sr_usage) > 0.98:
        return "REVISE_ROUTING", [*reasons, "gate collapse: logged row-level expert weight > 0.98"]
    if edema_dice_gain > 0.005 and scar_delta > -0.02:
        return "GO_ABLATION", reasons
    if scar_delta > -0.02:
        return "KEEP_CONDITIONAL_ONLY", [*reasons, "SRR did not beat conditional edema signal"]
    return "STOP_SRR", [*reasons, "SRR scar degradation"]


def decide_recovery(subgroups: list[dict[str, str]], usage: list[dict[str, str]], variants: list[str]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    revised = [v for v in variants if v.startswith("srr_") or v.endswith("_dictionary")]
    if not revised:
        return "STOP_PIPELINE_BUG", ["no revised SRR variants found"]

    best_edema = None
    best_scar = None
    for variant in revised:
        edema = find_row(subgroups, variant, 4, "gt_positive_only")
        scar = find_row(subgroups, variant, 5, "all_cases")
        if edema is not None:
            dice = as_float(edema.get("dice_mean"))
            if dice is not None and (best_edema is None or dice > best_edema[1]):
                best_edema = (variant, dice)
        if scar is not None:
            dice = as_float(scar.get("dice_mean"))
            if dice is not None and (best_scar is None or dice > best_scar[1]):
                best_scar = (variant, dice)
    if best_edema is None and best_scar is None:
        return "STOP_PIPELINE_BUG", ["missing revised SRR subgroup Dice rows"]

    for label, best in [("best_edema_gt_positive", best_edema), ("best_scar_all_cases", best_scar)]:
        if best is not None:
            reasons.append(f"{label}={best[0]}:{best[1]:.4f}")

    max_weights = []
    entropies = []
    for row in usage:
        if row.get("variant") not in revised or row.get("task") not in {"anatomy", "scar", "edema"}:
            continue
        val = as_float(row.get("mean_weight"))
        if val is not None:
            max_weights.append(val)
    for task in ("anatomy", "scar", "edema"):
        for variant in revised:
            per_expert, max_row = expert_weight_summary(usage, variant, task)
            if per_expert:
                entropy_proxy = 1.0 - max(per_expert.values())
                entropies.append(entropy_proxy)
                reasons.append(f"{variant}.{task}.max_mean_weight={max(per_expert.values()):.4f}")
                if max_row is not None:
                    reasons.append(f"{variant}.{task}.max_logged_weight={max_row:.4f}")

    best_edema_ok = best_edema is not None and best_edema[1] >= 0.10
    best_scar_ok = best_scar is not None and best_scar[1] >= 0.05
    any_usage_improved = bool(entropies and max(entropies) > 0.05)
    if (best_edema_ok or best_scar_ok) and any_usage_improved:
        return "GO_RESCUE_ABLATION", reasons
    if best_edema_ok or best_scar_ok:
        return "GO_CONDITIONAL_ABLATION", [*reasons, "metric signal present but routing remains weak"]
    return "STOP_SRR_NO_SIGNAL", [*reasons, "no revised SRR metric signal reached the recovery floor"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("results/20260621_srr_fold0"))
    parser.add_argument("--variants", nargs="*")
    parser.add_argument("--decision-mode", choices=["fold0", "recovery"], default="fold0")
    args = parser.parse_args()
    root = args.root
    if args.variants:
        variants = list(args.variants)
    else:
        variant_dirs = sorted(p.name for p in (root / "variants").glob("*") if (p / "summary.json").is_file())
        variants = variant_dirs or list(DEFAULT_VARIANTS)
    subgroup_rows: list[dict[str, str]] = []
    component_rows: list[dict[str, str]] = []
    usage_rows: list[dict[str, str]] = []
    summaries = {}
    for variant in variants:
        vdir = root / "variants" / variant
        subgroup_rows.extend(read_csv(vdir / "subgroup_metrics.csv"))
        component_rows.extend(read_csv(vdir / "component_hd_by_case.csv"))
        usage_rows.extend(read_csv(vdir / "retrieval_usage.csv"))
        summaries[variant] = json.loads((vdir / "summary.json").read_text(encoding="utf-8"))
    write_csv(root / "subgroup_metrics.csv", subgroup_rows)
    write_csv(root / "component_hd_by_case.csv", component_rows)
    write_csv(root / "retrieval_usage.csv", usage_rows)
    decision, reasons = decide(subgroup_rows, usage_rows, variants, args.decision_mode)
    write = root.joinpath
    lines = [
        "# SRR Fold0 Metrics Summary",
        "",
        "## Variant Summaries",
        "",
    ]
    for variant in variants:
        summary = summaries[variant]
        lines.extend(
            [
                f"### {variant}",
                "",
                f"- stop_reason: `{summary.get('stop_reason')}`",
                f"- elapsed_seconds: `{summary.get('elapsed_seconds')}`",
                f"- best_step: `{summary.get('best_step')}`",
                f"- checkpoint_best: `{summary.get('checkpoint_best')}`",
                f"- predictions: `{summary.get('prediction_dir')}`",
                "",
            ]
        )
    lines.extend(["## Key Subgroups", "", "| variant | class | group | n | Dice | HD | HD95 |", "| --- | --- | --- | ---: | ---: | ---: | ---: |"])
    for row in subgroup_rows:
        if row["group"] in {"all_cases", "gt_positive_only", "complete_modality", "LGE-only"}:
            lines.append(
                f"| {row['variant']} | {row['metric_name']} | {row['group']} | {row['n']} | {row['dice_mean']} | {row['hd_mean']} | {row['hd95_mean']} |"
            )
    lines.extend(["", f"Decision: `{decision}`", "", "Reasons:"])
    lines.extend([f"- {reason}" for reason in reasons])
    write("metrics_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write("decision.md").write_text("\n".join([f"decision: `{decision}`", "", *[f"- {r}" for r in reasons]]) + "\n", encoding="utf-8")
    usage_lines = ["# Retrieval Usage", ""]
    for variant in variants:
        usage_lines.append(f"## {variant}")
        tasks = sorted({row.get("task", "") for row in usage_rows if row.get("variant") == variant})
        for task in [t for t in tasks if t]:
            per_expert, max_row = expert_weight_summary(usage_rows, variant, task)
            if per_expert:
                parts = ", ".join(f"expert{idx}={value:.4f}" for idx, value in per_expert.items())
                usage_lines.append(f"- {task}: per-expert mean weights `{parts}`; max logged row weight `{max_row:.4f}`")
                continue
            val = mean_weight(usage_rows, variant, task)
            if val is not None:
                usage_lines.append(f"- {task}: mean expert weight across logged rows `{val:.4f}`")
        usage_lines.append("")
    write("retrieval_usage.md").write_text("\n".join(usage_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
