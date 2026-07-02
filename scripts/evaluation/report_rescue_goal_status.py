#!/usr/bin/env python3
"""Write current status artifacts for the 20260629 rescue goal."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "results/20260629_rescue_goal"

ROUTES = {
    "repaired_proposal": {
        "task": "prompts/tasks/20260629_repaired_proposal_repeat.md",
        "root": REPO_ROOT / "results/20260629_repaired_proposal_repeat",
        "variants": [
            "repaired_uncertainty_hardneg",
            "repaired_posneg_scar_hardneg",
            "repaired_joint_calibrated_proposal",
        ],
    },
    "srr_v2": {
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core",
        "source_roots": [
            REPO_ROOT / "results/20260629_srr_v2_unet_core",
            REPO_ROOT / "results/20260629_srr_v2_unet_core_htzhulab_fallback",
        ],
        "variants": [
            "srr_v2_multiscale_private_basic",
            "srr_v2_multiscale_private_proposal",
            "srr_v2_proposal_uncertainty_hardneg",
        ],
    },
    "srr_v2_light_refine_extras": {
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core/light_refine_extras",
        "variants": [
            "srr_v2_light_refine_lowmix",
            "srr_v2_light_refine_hardneg",
        ],
    },
    "srr_v2_capacity_extras": {
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core/capacity_extras",
        "variants": [
            "srr_v2_capacity12_proposal",
            "srr_v2_capacity12_hardneg",
        ],
    },
    "srr_v2_targeted_extras": {
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core/targeted_extras",
        "variants": [
            "srr_v2_edema_t2_focus",
            "srr_v2_scar_precision_nointeract",
        ],
    },
    "srr_v2_targeted_extras_a100": {
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core/targeted_extras_a100",
        "variants": [
            "srr_v2_edema_t2_focus",
            "srr_v2_scar_precision_nointeract",
        ],
    },
    "srr_v2_targeted_extras_volta": {
        "task": "prompts/tasks/20260629_srr_v2_unet_core.md",
        "root": REPO_ROOT / "results/20260629_srr_v2_unet_core/targeted_extras_volta",
        "variants": [
            "srr_v2_edema_t2_focus",
            "srr_v2_scar_precision_nointeract",
        ],
    },
    "cascade_teacher": {
        "task": "prompts/tasks/20260629_cascade_teacher_route.md",
        "root": REPO_ROOT / "results/20260629_cascade_teacher_route",
        "variants": [
            "nnunet_anatomy_prior_refiner",
            "nnunet_pathology_teacher_srr_refiner",
            "coarse_to_fine_srr_roi",
        ],
    },
    "cine_motion_alignment": {
        "task": "prompts/tasks/20260629_cine_motion_alignment.md",
        "root": REPO_ROOT / "results/20260629_cine_motion_alignment",
        "variants": [],
    },
    "cine_motion_pathology": {
        "task": "prompts/tasks/20260629_cine_motion_pathology.md",
        "root": REPO_ROOT / "results/20260629_cine_motion_pathology",
        "variants": [],
    },
}


def read_status(path: Path) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "status:" in line or line.startswith("Decision:") or line.startswith("decision:"):
            return line.strip()
    return "present"


def load_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def variant_artifacts(roots: list[Path], variant: str) -> tuple[Path, dict[str, Any], Path, str]:
    searched: list[str] = []
    fallback_vdir = roots[0] / "variants" / variant
    fallback_summary: dict[str, Any] = {}
    fallback_pred = fallback_vdir / "predictions/fold_0/checkpoint_best"
    for root in roots:
        vdir = root / "variants" / variant
        summary = load_summary(vdir / "summary.json")
        pred_dir = Path(summary.get("prediction_dir", vdir / "predictions/fold_0/checkpoint_best")) if summary else vdir / "predictions/fold_0/checkpoint_best"
        ready = bool(summary and pred_dir.is_dir())
        searched.append(f"{root.relative_to(REPO_ROOT)}:{'ready' if ready else 'missing'}")
        if ready:
            return vdir, summary, pred_dir, "; ".join(searched)
        if summary and not fallback_summary:
            fallback_vdir = vdir
            fallback_summary = summary
            fallback_pred = pred_dir
    return fallback_vdir, fallback_summary, fallback_pred, "; ".join(searched)


def route_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route, cfg in ROUTES.items():
        root = Path(cfg["root"])
        selection = root / "selection.md"
        result = root / "result.md"
        metrics = root / "metrics_summary.md"
        variants = list(cfg["variants"])
        if not variants:
            rows.append(
                {
                    "route": route,
                    "variant": "",
                    "task": cfg["task"],
                    "root": str(root),
                    "selection_status": read_status(selection),
                    "result_present": result.is_file(),
                    "metrics_present": metrics.is_file(),
                    "summary_present": "",
                    "prediction_dir_present": "",
                    "stop_reason": "",
                    "budget_status": "",
                    "elapsed_seconds": "",
                    "ready_to_aggregate": bool(selection.is_file() and result.is_file()),
                }
            )
            continue
        for variant in variants:
            source_roots = [Path(p) for p in cfg.get("source_roots", [root])]
            vdir, summary, pred_dir, searched_roots = variant_artifacts(source_roots, variant)
            rows.append(
                {
                    "route": route,
                    "variant": variant,
                    "task": cfg["task"],
                    "root": str(root),
                    "source_variant_dir": str(vdir),
                    "searched_roots": searched_roots,
                    "selection_status": read_status(selection),
                    "result_present": result.is_file(),
                    "metrics_present": metrics.is_file(),
                    "summary_present": bool(summary),
                    "prediction_dir_present": pred_dir.is_dir() if summary else False,
                    "stop_reason": summary.get("stop_reason", ""),
                    "budget_status": summary.get("budget_status", ""),
                    "elapsed_seconds": summary.get("elapsed_seconds", ""),
                    "ready_to_aggregate": bool(summary and pred_dir.is_dir()),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    ready = [r for r in rows if r["ready_to_aggregate"]]
    missing = [r for r in rows if not r["ready_to_aggregate"]]
    repaired = [r for r in rows if r["route"] == "repaired_proposal"]
    srr_v2 = [r for r in rows if r["route"] == "srr_v2"]
    cascade = [r for r in rows if r["route"] == "cascade_teacher"]
    repaired_ready = sum(1 for r in repaired if r["ready_to_aggregate"])
    srr_ready = sum(1 for r in srr_v2 if r["ready_to_aggregate"])
    cascade_ready = sum(1 for r in cascade if r["ready_to_aggregate"])
    lines = [
        "# 20260629 Rescue Goal Pending Status",
        "",
        "This is a status snapshot, not a final route selection.",
        "",
        "## Ready Rows",
        "",
        f"- ready_to_aggregate rows: `{len(ready)}`",
        f"- missing/pending rows: `{len(missing)}`",
        "",
        "## Route Matrix",
        "",
        "| route | variant | selection/status | summary | predictions | ready |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| {route} | {variant} | {selection_status} | {summary_present} | {prediction_dir_present} | {ready_to_aggregate} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            f"- Repaired proposal rows ready: `{repaired_ready}/{len(repaired)}`.",
            f"- Required SRR-v2 rows ready: `{srr_ready}/{len(srr_v2)}`.",
            f"- Cascade teacher formal rows ready: `{cascade_ready}/{len(cascade)}`.",
            "- SRR-v2 light-refine and capacity extras are tracked as separate rows because they are post-required-route improvement probes.",
            "- Targeted extra rows remain pending until full GPU training/export/evaluation writes summaries, predictions, and subgroup metrics under their isolated roots.",
            "- Cine alignment/pathology rows already have selections and are ready as secondary-line evidence.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = route_rows()
    write_csv(args.out_dir / "route_status.csv", rows)
    write_markdown(args.out_dir / "pending_status.md", rows)
    print({"rows": len(rows), "ready": sum(1 for r in rows if r["ready_to_aggregate"])})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
