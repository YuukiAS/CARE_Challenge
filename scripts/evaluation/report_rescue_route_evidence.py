#!/usr/bin/env python3
"""Summarize current route evidence for the 20260629 rescue goal."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "results/20260629_rescue_goal"


def read_status(path: Path) -> str:
    if not path.is_file():
        return "missing"
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip().strip("`")
        if line.startswith("Status:"):
            return line.split(":", 1)[1].strip().strip("`")
    return "present"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def metric_lookup(path: Path) -> dict[tuple[str, str, str], dict[str, str]]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    return {(row["variant"], row["metric_name"], row["group"]): row for row in rows}


def metric(row: dict[str, str] | None, key: str) -> str:
    if not row:
        return ""
    value = row.get(key, "")
    if value in {"", "NA", "None"}:
        return ""
    try:
        return f"{float(value):.4f}"
    except ValueError:
        return value


def myops_rows() -> list[dict[str, str]]:
    repaired_root = REPO_ROOT / "results/20260629_repaired_proposal_repeat"
    srr_root = REPO_ROOT / "results/20260629_srr_v2_unet_core"
    cascade_root = REPO_ROOT / "results/20260629_cascade_teacher_route"
    repaired_metrics = metric_lookup(repaired_root / "subgroup_metrics.csv")
    srr_metrics = metric_lookup(srr_root / "subgroup_metrics.csv")
    nnunet = load_json(REPO_ROOT / "results/metrics/unified/nnUNet501/fold_0/evaluation_summary.json")
    nnunet_dice = nnunet.get("mean_dice", {})

    repaired_scar = repaired_metrics.get(("repaired_posneg_scar_hardneg", "myops_scar", "all_cases"))
    repaired_edema = repaired_metrics.get(("repaired_uncertainty_hardneg", "myops_edema", "gt_positive_only"))
    srr_scar = srr_metrics.get(("srr_v2_multiscale_private_basic", "myops_scar", "all_cases"))
    srr_edema = srr_metrics.get(("srr_v2_multiscale_private_basic", "myops_edema", "gt_positive_only"))

    rows = [
        {
            "route": "repaired_proposal",
            "status": read_status(repaired_root / "selection.md"),
            "formal_ready": "3/3",
            "best_scar_all_dice": metric(repaired_scar, "dice_mean"),
            "best_scar_all_hd95": metric(repaired_scar, "hd95_mean"),
            "best_edema_gtpos_dice": metric(repaired_edema, "dice_mean"),
            "best_edema_gtpos_hd95": metric(repaired_edema, "hd95_mean"),
            "reference_gap": "scar remains near D4 and far below nnU-Net; edema GT+ below previous proposal",
            "current_interpretation": "completed negative evidence for shallow repaired proposal",
            "next_action": "do not expand; use as evidence to continue SRR-v2/cascade",
        },
        {
            "route": "srr_v2",
            "status": read_status(srr_root / "selection.md"),
            "formal_ready": "1/3",
            "best_scar_all_dice": metric(srr_scar, "dice_mean"),
            "best_scar_all_hd95": metric(srr_scar, "hd95_mean"),
            "best_edema_gtpos_dice": metric(srr_edema, "dice_mean"),
            "best_edema_gtpos_hd95": metric(srr_edema, "hd95_mean"),
            "reference_gap": "scar signal improves over repaired proposal but remains far below nnU-Net; 2 variants missing",
            "current_interpretation": "partial positive scar signal, incomplete route",
            "next_action": "monitor 57095505_[1-2] or run approved isolated fallback",
        },
        {
            "route": "cascade_teacher",
            "status": read_status(cascade_root / "metrics_summary.md"),
            "formal_ready": "0/3",
            "best_scar_all_dice": "",
            "best_scar_all_hd95": "",
            "best_edema_gtpos_dice": "",
            "best_edema_gtpos_hd95": "",
            "reference_gap": "formal refiner metrics missing; teacher cache baseline is strong enough to justify route",
            "current_interpretation": "best next MyoPS route to run once GPU approval/capacity exists",
            "next_action": "explicitly approve and submit sbatch --array=0-2 jobs/src/run_cascade_oof_refiner.sh",
        },
        {
            "route": "nnUNet_fold0_reference",
            "status": "reference_only",
            "formal_ready": "44 cases",
            "best_scar_all_dice": f"{float(nnunet_dice.get('class_5', 0.0)):.4f}" if nnunet_dice else "",
            "best_scar_all_hd95": "",
            "best_edema_gtpos_dice": "",
            "best_edema_gtpos_hd95": "",
            "reference_gap": f"edema all-case Dice {float(nnunet_dice.get('class_4', 0.0)):.4f}" if nnunet_dice else "",
            "current_interpretation": "hard reference, not a custom route selection",
            "next_action": "use as benchmark, not validation upload",
        },
    ]
    return rows


def cine_rows() -> list[dict[str, str]]:
    align_root = REPO_ROOT / "results/20260629_cine_motion_alignment"
    pathology_root = REPO_ROOT / "results/20260629_cine_motion_pathology"
    return [
        {
            "route": "cine_motion_alignment",
            "status": read_status(align_root / "selection.md"),
            "formal_ready": "complete",
            "best_scar_all_dice": "",
            "best_scar_all_hd95": "",
            "best_edema_gtpos_dice": "",
            "best_edema_gtpos_hd95": "",
            "reference_gap": "translation delta was approximately zero",
            "current_interpretation": "motion descriptor only, no alignment route selected",
            "next_action": "keep as secondary-line evidence",
        },
        {
            "route": "cine_motion_pathology",
            "status": read_status(pathology_root / "selection.md"),
            "formal_ready": "complete",
            "best_scar_all_dice": "",
            "best_scar_all_hd95": "",
            "best_edema_gtpos_dice": "",
            "best_edema_gtpos_hd95": "",
            "reference_gap": "local proxy only; no hosted metric calibration",
            "current_interpretation": "reference control only",
            "next_action": "do not block MyoPS",
        },
    ]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fields = [
        "route",
        "status",
        "formal_ready",
        "best_scar_all_dice",
        "best_scar_all_hd95",
        "best_edema_gtpos_dice",
        "best_edema_gtpos_hd95",
        "reference_gap",
        "current_interpretation",
        "next_action",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, str]]) -> None:
    lines = [
        "# 20260629 Rescue Goal Route Evidence Matrix",
        "",
        "Status: interim evidence matrix only; this is not `final_status.md`.",
        "",
        "## MyoPS Route Readout",
        "",
        "| route | status | formal ready | scar all Dice | scar all HD95 | edema GT+ Dice | edema GT+ HD95 | interpretation |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        if row["route"].startswith("cine"):
            continue
        lines.append(
            "| {route} | {status} | {formal_ready} | {best_scar_all_dice} | {best_scar_all_hd95} | {best_edema_gtpos_dice} | {best_edema_gtpos_hd95} | {current_interpretation} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Cine Secondary Readout",
            "",
            "| route | status | interpretation | next action |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in rows:
        if not row["route"].startswith("cine"):
            continue
        lines.append("| {route} | {status} | {current_interpretation} | {next_action} |".format(**row))
    lines.extend(
        [
            "",
            "## Current Synthesis",
            "",
            "- Repaired proposal is complete but negative: it did not beat D4/proposal references enough and remains far below nnU-Net.",
            "- SRR-v2 has the best current first-party scar signal (`0.1998` all-case Dice, HD95 `82.7490`) but is incomplete because two formal variants are still pending/missing.",
            "- Cascade teacher is the most justified next MyoPS execution route once approval/capacity is available, because the shallow proposal route failed and SRR-v2 remains far below nnU-Net while incomplete.",
            "- Cine evidence currently supports `CINE_REFERENCE_ONLY`; it should not block MyoPS route completion.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir
    rows = myops_rows() + cine_rows()
    write_csv(out_dir / "route_evidence_matrix.csv", rows)
    write_markdown(out_dir / "route_evidence_matrix.md", rows)
    print({"rows": len(rows), "out": str(out_dir / "route_evidence_matrix.md")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
