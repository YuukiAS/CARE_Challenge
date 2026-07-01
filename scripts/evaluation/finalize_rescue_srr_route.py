#!/usr/bin/env python3
"""Finalize or report pending status for rescue SRR-style routes."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

ROUTE_CONFIG = {
    "repaired": {
        "root": REPO_ROOT / "results/20260629_repaired_proposal_repeat",
        "variants": [
            "repaired_uncertainty_hardneg",
            "repaired_posneg_scar_hardneg",
            "repaired_joint_calibrated_proposal",
        ],
        "task": "prompts/tasks/20260629_repaired_proposal_repeat.md",
    },
    "srr_v2": {
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core",
        "variants": [
            "srr_v2_multiscale_private_basic",
            "srr_v2_multiscale_private_proposal",
            "srr_v2_proposal_uncertainty_hardneg",
        ],
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
    },
    "srr_v2_light_refine_extras": {
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core/light_refine_extras",
        "variants": [
            "srr_v2_light_refine_lowmix",
            "srr_v2_light_refine_hardneg",
        ],
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
    },
}

NNUNET_REFERENCE = {
    "scar_all_cases_dice": 0.5601692281262312,
    "edema_gt_positive_dice": 0.3944,
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def ready_in_root(root: Path, variant: str) -> tuple[bool, Path, str]:
    vdir = root / "variants" / variant
    summary = vdir / "summary.json"
    pred_dir = vdir / "predictions/fold_0/checkpoint_best"
    subgroup = vdir / "subgroup_metrics.csv"
    if summary.is_file() and pred_dir.is_dir() and subgroup.is_file():
        return True, vdir, "ready"
    missing = []
    if not summary.is_file():
        missing.append("summary")
    if not pred_dir.is_dir():
        missing.append("predictions")
    if not subgroup.is_file():
        missing.append("subgroup_metrics")
    return False, vdir, "missing " + ",".join(missing)


def variant_status(roots: list[Path], variants: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in variants:
        chosen_ready = False
        chosen_vdir: Path | None = None
        searched = []
        for root in roots:
            ready, vdir, detail = ready_in_root(root, variant)
            searched.append(f"{rel(root)}:{detail}")
            if ready and chosen_vdir is None:
                chosen_ready = True
                chosen_vdir = vdir
        vdir = chosen_vdir or roots[0] / "variants" / variant
        rows.append(
            {
                "variant": variant,
                "source_variant_dir": rel(vdir),
                "summary_present": (vdir / "summary.json").is_file(),
                "predictions_present": (vdir / "predictions/fold_0/checkpoint_best").is_dir(),
                "subgroup_metrics_present": (vdir / "subgroup_metrics.csv").is_file(),
                "component_metrics_present": (vdir / "component_hd_by_case.csv").is_file(),
                "ready": chosen_ready,
                "searched_roots": "; ".join(searched),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = list(rows[0].keys()) if rows else []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_status(root: Path, route: str, rows: list[dict[str, Any]], *, finalized: bool) -> None:
    ready = sum(1 for row in rows if row["ready"])
    lines = [
        f"# {route} Aggregation Status",
        "",
        f"- root: `{root}`",
        f"- finalized: `{finalized}`",
        f"- ready variants: `{ready}/{len(rows)}`",
        "",
        "| variant | source | summary | predictions | subgroup metrics | ready |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {variant} | `{source_variant_dir}` | {summary_present} | {predictions_present} | {subgroup_metrics_present} | {ready} |".format(**row)
        )
    if not finalized:
        lines.extend(["", "Aggregation is pending; no task-level `selection.md` was written by this helper."])
    root.joinpath("aggregation_status.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--route", choices=sorted(ROUTE_CONFIG), required=True)
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Override the route result root, useful for isolated fallback/retry outputs.",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        action="append",
        default=[],
        help="Additional roots to search for ready variants before aggregating into --root.",
    )
    parser.add_argument("--force-partial", action="store_true", help="Aggregate ready variants even if some expected variants are missing.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def as_float(value: str | None) -> float | None:
    if value in {None, "", "NA", "nan", "None"}:
        return None
    try:
        val = float(value)
    except (TypeError, ValueError):
        return None
    if val != val or val in {float("inf"), float("-inf")}:
        return None
    return val


def best_metric(subgroups: list[dict[str, str]], *, class_id: int, group: str) -> tuple[str, float] | None:
    best: tuple[str, float] | None = None
    for row in subgroups:
        if int(row.get("class_id", -1)) != class_id or row.get("group") != group:
            continue
        val = as_float(row.get("dice_mean"))
        if val is None:
            continue
        variant = row.get("variant", "")
        if best is None or val > best[1]:
            best = (variant, val)
    return best


def build_combined_view(root: Path, rows: list[dict[str, Any]]) -> Path:
    view = root / "combined_sources"
    variants_dir = view / "variants"
    if variants_dir.exists():
        shutil.rmtree(variants_dir)
    variants_dir.mkdir(parents=True, exist_ok=True)
    for row in rows:
        if not row["ready"]:
            continue
        src = REPO_ROOT / row["source_variant_dir"]
        dst = variants_dir / row["variant"]
        dst.symlink_to(src, target_is_directory=True)
    return view


def copy_aggregate_outputs(view: Path, root: Path) -> None:
    for name in [
        "metrics_summary.md",
        "decision.md",
        "subgroup_metrics.csv",
        "component_hd_by_case.csv",
        "retrieval_usage.csv",
        "proposal_metrics.csv",
        "prototype_usage.csv",
    ]:
        src = view / name
        if src.is_file():
            shutil.copyfile(src, root / name)


def write_selection(root: Path, route: str, variants: list[str], rows: list[dict[str, Any]]) -> None:
    subgroups = read_csv(root / "subgroup_metrics.csv")
    best_edema = best_metric(subgroups, class_id=4, group="gt_positive_only")
    best_scar = best_metric(subgroups, class_id=5, group="all_cases")
    edema_floor = 0.80 * NNUNET_REFERENCE["edema_gt_positive_dice"]
    scar_floor = 0.80 * NNUNET_REFERENCE["scar_all_cases_dice"]
    selected_variant = "none"
    status = "STOP_NO_SRR_V2_SIGNAL"
    reasons = []
    if best_edema is not None:
        reasons.append(
            f"best_edema_gt_positive={best_edema[0]}:{best_edema[1]:.4f}; selection_floor_80pct_nnunet={edema_floor:.4f}"
        )
    if best_scar is not None:
        reasons.append(
            f"best_scar_all_cases={best_scar[0]}:{best_scar[1]:.4f}; selection_floor_80pct_nnunet={scar_floor:.4f}"
        )
    if best_scar is None and best_edema is None:
        reasons.append("missing SRR-v2 subgroup Dice rows")
        status = "STOP_PIPELINE_BUG"
    elif best_scar is not None and best_scar[1] >= scar_floor:
        status = "SELECT_SRR_V2_PROPOSAL" if "proposal" in best_scar[0] else "SELECT_SRR_V2_CORE"
        selected_variant = best_scar[0]
        reasons.append("scar all-case Dice reached the conservative 80pct nnU-Net reference floor")
    elif best_edema is not None and best_edema[1] >= edema_floor:
        status = "SELECT_SRR_V2_PROPOSAL" if "proposal" in best_edema[0] else "SELECT_SRR_V2_CORE"
        selected_variant = best_edema[0]
        reasons.append("edema GT-positive Dice reached the conservative 80pct nnU-Net reference floor")
    else:
        reasons.append("no SRR-v2 variant approached nnU-Net enough for selection")
    lines = [
        f"# {route} Selection",
        "",
        f"status: `{status}`",
        f"selected_variant: `{selected_variant}`",
        "",
        "## Evidence Roots",
        "",
    ]
    for row in rows:
        lines.append(f"- `{row['variant']}`: `{row['source_variant_dir']}`")
    lines.extend(
        [
            "",
            "## Decision Basis",
            "",
            f"- nnU-Net scar all-case reference: `{NNUNET_REFERENCE['scar_all_cases_dice']:.4f}`",
            f"- nnU-Net edema GT-positive reference used for this gate: `{NNUNET_REFERENCE['edema_gt_positive_dice']:.4f}`",
            "- Conservative selection rule: select only if a target metric reaches at least 80% of the corresponding nnU-Net reference.",
            "",
            "## Reasons",
            "",
            *[f"- {reason}" for reason in reasons],
            "",
            "No validation upload, fold expansion, split change, label mapping change, or evaluator change was performed.",
        ]
    )
    (root / "selection.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    result_lines = [
        f"# Result 20260629 {route}",
        "",
        f"Status: `{status}`",
        f"Selected variant: `{selected_variant}`",
        "",
        "## What Was Aggregated",
        "",
        "This route aggregates canonical and isolated fallback outputs without moving or overwriting variant artifacts.",
        "",
        *[f"- `{row['variant']}` from `{row['source_variant_dir']}`" for row in rows],
        "",
        "## Interpretation",
        "",
        "SRR-v2 is judged against the nnU-Net reference, not merely against the previous shallow SRR floor.",
        "See `metrics_summary.md`, `subgroup_metrics.csv`, and `selection.md` for the complete evidence.",
        "",
        "No validation upload, fold expansion, split change, label mapping change, or evaluator change was performed.",
    ]
    (root / "result.md").write_text("\n".join(result_lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    cfg = ROUTE_CONFIG[args.route]
    root = args.root if args.root is not None else Path(cfg["root"])
    if not root.is_absolute():
        root = REPO_ROOT / root
    source_roots = [root]
    for source_root in args.source_root:
        source_root = source_root if source_root.is_absolute() else REPO_ROOT / source_root
        source_roots.append(source_root)
    variants = list(cfg["variants"])
    rows = variant_status(source_roots, variants)
    write_csv(root / "aggregation_status.csv", rows)
    ready_variants = [row["variant"] for row in rows if row["ready"]]
    if len(ready_variants) != len(variants) and not args.force_partial:
        write_status(root, args.route, rows, finalized=False)
        print({"route": args.route, "ready": len(ready_variants), "expected": len(variants), "finalized": False})
        return 0
    if not ready_variants:
        write_status(root, args.route, rows, finalized=False)
        print({"route": args.route, "ready": 0, "expected": len(variants), "finalized": False})
        return 0
    aggregate_root = root
    if len(source_roots) > 1:
        aggregate_root = build_combined_view(root, rows)
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/evaluation/report_srr_fold0.py"),
            "--root",
            str(aggregate_root),
            "--decision-mode",
            "recovery",
            "--variants",
            *ready_variants,
        ],
        cwd=str(REPO_ROOT),
        check=True,
    )
    if aggregate_root != root:
        copy_aggregate_outputs(aggregate_root, root)
    write_selection(root, args.route, ready_variants, rows)
    write_status(root, args.route, rows, finalized=True)
    print({"route": args.route, "ready": len(ready_variants), "expected": len(variants), "finalized": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
