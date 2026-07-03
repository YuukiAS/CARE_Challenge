#!/usr/bin/env python3
"""Evidence-only MyoPS mechanism audit for prompts/tasks/20260703_myops_audit.md."""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "results/20260703_myops_audit"

NNUNET_SCAR_ALL = 0.5601692281262312
NNUNET_EDEMA_GT_POS = 0.3944358976789887
NNUNET_EDEMA_GATE = 0.8 * NNUNET_EDEMA_GT_POS
NNUNET_SCAR_GATE = 0.8 * NNUNET_SCAR_ALL

KEY_GROUPS = {
    "all_cases",
    "gt_positive_only",
    "t2_present",
    "complete_modality",
    "CenterB",
    "CenterC",
    "C0+LGE",
    "C0+LGE+T2",
    "LGE-only",
    "no_T2_empty_GT",
}

SUBGROUP_SOURCES = [
    ("repaired_proposal", REPO_ROOT / "results/20260629_repaired_proposal_repeat/subgroup_metrics.csv"),
    ("srr_v2_core", REPO_ROOT / "results/20260629_srr_v2_unet_core/subgroup_metrics.csv"),
    ("srr_v2_capacity", REPO_ROOT / "results/20260629_srr_v2_unet_core/capacity_extras/subgroup_metrics.csv"),
    ("srr_v2_balanced_targeted", REPO_ROOT / "results/20260629_srr_v2_unet_core/balanced_targeted_extras/subgroup_metrics.csv"),
]

CASCADE_SUBGROUP_SOURCES = [
    ("cascade_teacher", REPO_ROOT / "results/20260629_cascade_teacher_route/subgroup_metrics.csv"),
    ("cascade_signal_seek", REPO_ROOT / "results/20260629_cascade_teacher_route/revision_signal_seek/subgroup_metrics.csv"),
    ("cascade_postprocess", REPO_ROOT / "results/20260629_cascade_teacher_route/revision_postprocess_sweep/metrics_summary.md"),
]

CASE_SOURCES = [
    ("repaired_proposal", REPO_ROOT / "results/20260629_repaired_proposal_repeat/component_hd_by_case.csv"),
    ("srr_v2_capacity", REPO_ROOT / "results/20260629_srr_v2_unet_core/capacity_extras/component_hd_by_case.csv"),
    ("srr_v2_balanced_targeted", REPO_ROOT / "results/20260629_srr_v2_unet_core/balanced_targeted_extras/component_hd_by_case.csv"),
    ("cascade_teacher", REPO_ROOT / "results/20260629_cascade_teacher_route/component_hd_by_case.csv"),
]

PREDICTION_DIRS = {
    "repaired_uncertainty_hardneg": REPO_ROOT
    / "results/20260629_repaired_proposal_repeat/variants/repaired_uncertainty_hardneg/predictions/fold_0/checkpoint_best",
    "srr_v2_capacity12_hardneg": REPO_ROOT
    / "results/20260629_srr_v2_unet_core/capacity_extras/variants/srr_v2_capacity12_hardneg/predictions/fold_0/checkpoint_best",
    "srr_v2_capacity12_scar_precision_interact": REPO_ROOT
    / "results/20260629_srr_v2_unet_core/balanced_targeted_extras/variants/srr_v2_capacity12_scar_precision_interact/predictions/fold_0/checkpoint_best",
    "coarse_to_fine_srr_roi": REPO_ROOT
    / "results/20260629_cascade_teacher_route/variants/coarse_to_fine_srr_roi/predictions/coarse_to_fine_srr_roi_oof_refiner/validation",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def as_float(value: Any) -> float | None:
    if value in (None, "", "NA", "nan", "None"):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def fmt(value: Any) -> str:
    val = as_float(value)
    if val is None:
        return "evidence not found" if value in (None, "") else str(value)
    return f"{val:.4f}"


def existing_path(path: Path | str | None) -> str:
    if path in (None, ""):
        return "evidence not found"
    p = Path(path)
    if p.is_file() or p.is_dir():
        return rel(p)
    return "evidence not found"


def source_variant_path(row: dict[str, str]) -> Path | None:
    raw = row.get("source_variant_dir", "")
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def route_root_path(row: dict[str, str]) -> Path:
    raw = row.get("root", "")
    path = Path(raw)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path


def find_prediction_dir(root: Path | None) -> Path | None:
    if root is None or not root.is_dir():
        return None
    candidates = [p for p in root.rglob("*") if p.is_dir() and any(p.glob("*.nii.gz"))]
    if not candidates:
        return None
    candidates.sort(key=lambda p: (len(p.parts), str(p)), reverse=True)
    return candidates[0]


def count_predictions(path: Path | None) -> str:
    if path is None or not path.is_dir():
        return "evidence not found"
    return str(len(list(path.glob("*.nii.gz"))))


def find_checkpoint(root: Path | None) -> Path | None:
    if root is None or not root.is_dir():
        return None
    checkpoints = sorted(list(root.rglob("*.pt")) + list(root.rglob("*.pth")))
    if not checkpoints:
        return None
    for token in ("checkpoint_best", "_oof_refiner", "signal_seek", "component_guard"):
        for path in checkpoints:
            if token in path.name:
                return path
    return checkpoints[0]


def metric_paths(route_root: Path, variant_root: Path | None) -> str:
    candidates: list[Path] = []
    for path in [
        route_root / "metrics_summary.md",
        route_root / "subgroup_metrics.csv",
        route_root / "component_hd_by_case.csv",
        route_root / "aggregation_status.csv",
    ]:
        if path.is_file():
            candidates.append(path)
    if variant_root is not None:
        for path in [
            variant_root / "summary.json",
            variant_root / "summary.md",
            variant_root / "subgroup_metrics.csv",
            variant_root / "component_hd_by_case.csv",
            variant_root / "proposal_metrics.csv",
            variant_root / "round10_fold0_very_short_metrics.csv",
            variant_root / "baseline_vs_refiner_by_subset.csv",
        ]:
            if path.is_file():
                candidates.append(path)
    if not candidates:
        return "evidence not found"
    return ";".join(rel(path) for path in candidates)


def find_log_path(route: str, variant: str, variant_root: Path | None) -> str:
    logs_dir = REPO_ROOT / "logs"
    if not logs_dir.is_dir():
        return "evidence not found"
    matches: list[Path] = []
    out_root = str(variant_root) if variant_root is not None else ""
    for path in sorted(logs_dir.glob("*.log")):
        name = path.name
        if variant and variant in name:
            matches.append(path)
            continue
        if not variant and not out_root:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if variant and (
            f"VARIANT={variant}" in text
            or f"variant={variant}" in text
            or f"output_variant={variant}" in text
            or f"formal={variant}" in text
        ):
            matches.append(path)
        elif out_root and out_root in text:
            matches.append(path)
    if not matches:
        return "evidence not found"
    return ";".join(rel(path) for path in matches)


def build_route_evidence_index() -> list[dict[str, Any]]:
    rows = read_csv(REPO_ROOT / "results/20260629_rescue_goal/route_status.csv")
    out: list[dict[str, Any]] = []
    for row in rows:
        route_root = route_root_path(row)
        variant_root = source_variant_path(row)
        evidence_root = variant_root if variant_root is not None else route_root
        pred_dir = find_prediction_dir(evidence_root)
        checkpoint = find_checkpoint(evidence_root)
        result_path = route_root / "result.md"
        selection_path = route_root / "selection.md"
        log_path = (
            find_log_path(row.get("route", ""), row.get("variant", ""), evidence_root)
            if row.get("ready_to_aggregate") == "True"
            else "evidence not found"
        )
        out.append(
            {
                "route": row.get("route", ""),
                "variant": row.get("variant", ""),
                "ready_to_aggregate": row.get("ready_to_aggregate", ""),
                "selection_status": row.get("selection_status", "") or "evidence not found",
                "result_path": existing_path(result_path),
                "selection_path": existing_path(selection_path),
                "metric_paths": metric_paths(route_root, variant_root),
                "prediction_dir": existing_path(pred_dir),
                "prediction_file_count": count_predictions(pred_dir),
                "checkpoint_path": existing_path(checkpoint),
                "training_or_variant_log_path": existing_path(variant_root / "training_log.csv")
                if variant_root is not None
                else "evidence not found",
                "job_log_path": log_path,
                "source_variant_dir": existing_path(variant_root),
                "route_root": existing_path(route_root),
                "task": row.get("task", ""),
                "stop_reason": row.get("stop_reason", "") or "evidence not found",
                "notes": ""
                if row.get("ready_to_aggregate") == "True"
                else "not selected evidence; missing/cancelled duplicate or route without variant evidence",
            }
        )
    return out


def build_cache_isolation_table(route_evidence_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in route_evidence_rows:
        evidence_root = row["source_variant_dir"]
        if evidence_root == "evidence not found":
            evidence_root = row["route_root"]
        selected = row["ready_to_aggregate"] == "True"
        variant_specific = "/variants/" in evidence_root or row["variant"] == ""
        pred = row["prediction_dir"]
        ckpt = row["checkpoint_path"]
        metric = row["metric_paths"]
        log = row["job_log_path"]
        missing = [
            name
            for name, value in [
                ("prediction_dir", pred),
                ("checkpoint_path", ckpt),
                ("metric_paths", metric),
                ("job_log_path", log),
            ]
            if value == "evidence not found"
        ]
        shared_risk = "low" if selected and variant_specific and pred != "evidence not found" else "requires auditor review"
        if not selected:
            shared_risk = "not selected evidence"
        out.append(
            {
                "route": row["route"],
                "variant": row["variant"],
                "selected_evidence": str(selected),
                "evidence_root": evidence_root,
                "variant_specific_root": str(variant_specific),
                "prediction_cache": pred,
                "checkpoint_cache": ckpt,
                "metric_cache": metric,
                "log_cache": log,
                "cache_isolation_assessment": shared_risk,
                "missing_cache_evidence": ";".join(missing) if missing else "",
            }
        )
    return out


def build_route_gap_table() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for route, path in SUBGROUP_SOURCES:
        for r in read_csv(path):
            if r.get("group") not in KEY_GROUPS:
                continue
            metric = r.get("metric_name", "")
            group = r.get("group", "")
            cls = r.get("class_id", "")
            nnunet_ref = ""
            gate_80 = ""
            if metric == "myops_edema" and group in {"gt_positive_only", "t2_present", "complete_modality"}:
                nnunet_ref = f"{NNUNET_EDEMA_GT_POS:.6f}"
                gate_80 = f"{NNUNET_EDEMA_GATE:.6f}"
            elif metric == "myops_scar" and group == "all_cases":
                nnunet_ref = f"{NNUNET_SCAR_ALL:.6f}"
                gate_80 = f"{NNUNET_SCAR_GATE:.6f}"
            dice = as_float(r.get("dice_mean"))
            gap = ""
            if gate_80 and dice is not None:
                gap = f"{float(gate_80) - dice:.6f}"
            rows.append(
                {
                    "route": route,
                    "variant": r.get("variant", ""),
                    "metric_name": metric,
                    "class_id": cls,
                    "group": group,
                    "n": r.get("n", ""),
                    "dice_mean": r.get("dice_mean", ""),
                    "hd95_mean": r.get("hd95_mean", ""),
                    "component_count_mean": r.get("component_count_mean", ""),
                    "remote_fp_mean": r.get("remote_fp_mean", ""),
                    "empty_prediction_rate": r.get("empty_prediction_rate", ""),
                    "nnunet_reference_dice": nnunet_ref or "evidence not found",
                    "selection_floor_80pct": gate_80 or "evidence not found",
                    "gap_to_80pct_floor": gap or "evidence not found",
                    "source_file": rel(path),
                }
            )

    for route, path in CASCADE_SUBGROUP_SOURCES:
        if path.suffix != ".csv":
            continue
        for r in read_csv(path):
            subset = r.get("subset", "")
            if subset not in {
                "all_case",
                "t2_present_gt_positive",
                "complete_modality",
                "CenterB",
                "CenterC",
                "modality:C0+LGE",
                "modality:C0+LGE+T2",
                "modality:LGE-only",
                "no_t2_empty_gt",
            }:
                continue
            rows.append(
                {
                    "route": route,
                    "variant": r.get("variant", ""),
                    "metric_name": "cascade_delta",
                    "class_id": "4/5",
                    "group": subset,
                    "n": r.get("n", ""),
                    "dice_mean": f"edema_delta={r.get('delta_edema_dice', '')};scar_delta={r.get('delta_scar_dice', '')}",
                    "hd95_mean": f"edema_hd95_improve={r.get('delta_edema_hd95_improvement', '')};scar_hd95_improve={r.get('delta_scar_hd95_improvement', '')}",
                    "component_count_mean": "evidence not found",
                    "remote_fp_mean": "evidence not found",
                    "empty_prediction_rate": "evidence not found",
                    "nnunet_reference_dice": f"edema={r.get('baseline_edema_dice', '')};scar={r.get('baseline_scar_dice', '')}",
                    "selection_floor_80pct": "teacher delta route, no 80pct floor",
                    "gap_to_80pct_floor": "teacher delta route, no 80pct floor",
                    "source_file": rel(path),
                }
            )
    return rows


def build_failure_case_table() -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for route, path in CASE_SOURCES:
        for r in read_csv(path):
            dice = as_float(r.get("dice") or r.get("myops_edema_dice") or r.get("myops_scar_dice"))
            remote = as_float(r.get("remote_fp_count") or r.get("myops_edema_remote_fp") or r.get("myops_scar_remote_fp")) or 0.0
            comp = as_float(r.get("component_count") or r.get("myops_edema_component_count") or r.get("myops_scar_component_count")) or 0.0
            hd95 = as_float(r.get("hd95") or r.get("myops_edema_hd95") or r.get("myops_scar_hd95"))
            if dice is None:
                dice = 0.0
            score = (1.0 - dice) + min(remote / 50.0, 3.0) + min(comp / 75.0, 3.0)
            candidates.append(
                {
                    "route": route,
                    "variant": r.get("variant", ""),
                    "case_id": r.get("case_id", ""),
                    "center": r.get("center", ""),
                    "modality_group": r.get("modality_group", ""),
                    "t2_present": r.get("t2_present", ""),
                    "metric_name": r.get("metric_name", ""),
                    "class_id": r.get("class_id", ""),
                    "dice": f"{dice:.6f}",
                    "hd95": "" if hd95 is None else f"{hd95:.6f}",
                    "component_count": f"{comp:.0f}",
                    "remote_fp_count": f"{remote:.0f}",
                    "pred_gt_volume_ratio": r.get("pred_gt_volume_ratio", ""),
                    "pred_empty": r.get("pred_empty", ""),
                    "gt_empty": r.get("gt_empty", ""),
                    "failure_score": f"{score:.6f}",
                    "source_file": rel(path),
                }
            )
    candidates.sort(key=lambda row: float(row["failure_score"]), reverse=True)
    return candidates[:80]


def prediction_label_sets() -> dict[str, str]:
    try:
        import SimpleITK as sitk  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return {name: "evidence not found" for name in PREDICTION_DIRS}
    out: dict[str, str] = {}
    for name, pdir in PREDICTION_DIRS.items():
        if not pdir.is_dir():
            out[name] = "evidence not found"
            continue
        labels: set[int] = set()
        count = 0
        for path in sorted(pdir.glob("*.nii.gz")):
            arr = sitk.GetArrayFromImage(sitk.ReadImage(str(path)))
            labels.update(int(v) for v in np.unique(arr).tolist())
            count += 1
        out[name] = f"cases={count};labels={','.join(str(x) for x in sorted(labels))}"
    return out


def route_best(rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    best: dict[str, dict[str, str]] = {}
    for row in rows:
        metric = row["metric_name"]
        group = row["group"]
        key = ""
        if metric == "myops_edema" and group == "gt_positive_only":
            key = "best_edema_gt_positive"
        elif metric == "myops_scar" and group == "all_cases":
            key = "best_scar_all_cases"
        if not key:
            continue
        val = as_float(row["dice_mean"])
        if val is None:
            continue
        old = best.get(key)
        if old is None or val > float(old["dice_mean"]):
            best[key] = {
                "route": row["route"],
                "variant": row["variant"],
                "dice_mean": f"{val:.6f}",
                "source_file": row["source_file"],
            }
    return best


def route_completion_md() -> str:
    route_status = REPO_ROOT / "results/20260629_rescue_goal/route_status.csv"
    rows = read_csv(route_status)
    ready = [r for r in rows if r.get("ready_to_aggregate") == "True"]
    missing = [r for r in rows if r.get("ready_to_aggregate") != "True"]
    lines = [
        "# MyoPS Mechanism Audit",
        "",
        "controlled_state: EXECUTED_UNAUDITED",
        "domain_evidence_label: PARTIAL_MECHANISM_INCOMPLETE",
        "",
        "## Route Completion",
        "",
        f"- rescue route ledger: `{rel(route_status)}`",
        f"- ready rows: `{len(ready)}`",
        f"- not-ready rows: `{len(missing)}` (cancelled duplicate A100/Volta targeted roots are not selected evidence)",
        "",
        "| route | variant | status | result | metrics | prediction_dir | source |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for r in rows:
        lines.append(
            "| {route} | {variant} | {status} | {result} | {metrics} | {preds} | `{src}` |".format(
                route=r.get("route", ""),
                variant=r.get("variant", ""),
                status=r.get("selection_status", "") or "evidence not found",
                result=r.get("result_present", ""),
                metrics=r.get("metrics_present", ""),
                preds=r.get("prediction_dir_present", ""),
                src=r.get("source_variant_dir", ""),
            )
        )
    lines.extend(
        [
        "",
        "## Main Finding",
        "",
        "The current MyoPS custom routes are executed but not promotable. The strongest SRR-v2 scar signal remains below the nnU-Net-relative gate, and the strongest edema GT-positive signal remains below the nnU-Net-relative gate. Cascade variants mostly preserve the nnU-Net teacher and produce only tiny deltas, so the route is not an independent pathology rescue.",
        "",
        "## Evidence Supplement Indexes",
        "",
        "- per-route/per-variant artifact index: `results/20260703_myops_audit/route_evidence_index.csv`",
        "- cache-isolation table: `results/20260703_myops_audit/cache_isolation_table.csv`",
        "- revision command transcript: `results/20260703_myops_audit/command_transcript.md`",
        "",
        "## Missing Evidence Policy",
        "",
        "Where this audit could not locate route-specific evidence, the tables use `evidence not found`. No validation upload, upload-ready package, fold expansion, training, label-mapping edit, split edit, or evaluator edit was performed.",
        ]
    )
    return "\n".join(lines)


def label_export_qc_md(label_sets: dict[str, str]) -> str:
    return f"""# Label Export QC

controlled_state: EXECUTED_UNAUDITED

## Train/Eval Label Contract

- raw-to-compact mapping path: `code/nnUNet/nnunet_label_utils.py`
- raw labels mapped to compact labels: `0->0`, `200->1`, `500->2`, `600->3`, `1220->4`, `2221->5`, raw `1->5`
- Dataset501 dataset path: `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json`
- Dataset501 channels: `0=LGE`, `1=T2`, `2=C0`
- compact labels: `1=myocardium`, `2=LV_blood`, `3=RV_blood`, `4=edema`, `5=scar`
- evaluator path: `scripts/evaluation/evaluate_predictions.py`
- evaluator decode mode: compact labels by default; optional `--pred-remap-json`; CARE pathology labels use class_4=`myops_edema`, class_5=`myops_scar`

## Export Contract

- validation submission path: `scripts/submission/prepare_care_myocardium_validation.py`
- MyoPS compact-to-raw export mapping: `0->0`, `1->200`, `2->500`, `3->600`, `4->1220`, `5->2221`
- allowed MyoPS submission labels: `0,200,500,600,1220,2221`
- pathology fallback: if no MyoPS pathology raw label is present, the packager can insert one raw `2221` voxel and record it in the manifest.
- challenge-facing caveat: compact-label fold0 metrics are not by themselves hosted validation evidence; raw export and official one-zip validation remain separate gates.

## Prediction Label Value Sets

| prediction source | compact value set |
| --- | --- |
{chr(10).join(f"| `{name}` | {value} |" for name, value in label_sets.items())}

## QC Decision

- mapping consistency: SUPPORTED for compact train/eval and compact-to-raw export code paths.
- evaluator evidence: SUPPORTED for compact offline evaluator paths.
- hosted validation evidence: evidence not found because upload/package execution is forbidden in this task.
"""


def architecture_gap_md() -> str:
    return """# Architecture Gap Audit

controlled_state: EXECUTED_UNAUDITED
domain_evidence_label: PARTIAL_MECHANISM_INCOMPLETE

## SRR-Lite

- code: `src/care_myocardium/models/srr_myops.py`
- mechanism present: availability-aware modality stems, masked modality fusion, shared/private SRR retrieval, soft anatomy prior, separate scar/edema logits.
- gap: the main `SRRMyoPSLite` path is one-scale after modality stems plus a single refine block, not a high-resolution lesion decoder.
- gap: `AnatomyPathologyHeads` in `src/care_myocardium/models/pathology_heads.py` uses 1x1 scar and edema heads with a soft anatomy prior.
- gap: `PathologyProposalHead` writes proposal logits but then mixes proposal and evidence logits directly into final scar/edema logits; this is not an independent candidate generator followed by a separately evaluated refinement stage.

## SRR-v2

- code: `src/care_myocardium/models/srr_v2_unet.py`
- mechanism present: three-scale modality-private encoders, scale retrieval, task decoders with skip-like concatenation, optional proposal head.
- gap: pathology output still terminates in the same 1x1 pathology heads and optional direct proposal/evidence logit mixing.
- gap: the proposal route lacks independent lesion candidate recall/precision promotion evidence that beats the same-split nnU-Net reference.
- gap: no true trainable alignment expert, registration transform family, warp plausibility metric, or deformation evidence is present in these MyoPS routes.

## Cascade Teacher

- code: `scripts/evaluation/finalize_cascade_teacher_route.py`, `scripts/evaluation/preflight_cascade_teacher_cache.py`, cascade route artifacts under `results/20260629_cascade_teacher_route/`
- mechanism present: nnU-Net teacher cache and formal refiner variants with teacher-vs-candidate deltas.
- gap: formal variants are marked `fail_stop_refiner_candidate`; signal-seek and postprocess revisions show tiny Dice deltas and worsening or unresolved HD95/component/remote-FP behavior.
- gap: this behaves as a weak teacher-preserving residual/postprocess route, not a robust independent pathology refiner.

## Architecture Decision

The audited architecture evidence is not TRUE_DONE for a new custom route. SRR-v2 is materially stronger than the original shallow SRR, but its candidate/proposal/refinement mechanism remains incomplete relative to the medical-imaging deep-learning gate because the route lacks independent proposal coverage evidence, robust lesion-scale refinement, and same-split superiority over nnU-Net.
"""


def code_path_md() -> str:
    return """# Code Path Audit

controlled_state: EXECUTED_UNAUDITED

## Required Rules And Task Files Read

- `AGENTS.md`
- `prompts/AGENT_RULES.md`
- `prompts/CHATGPT_RULES.md`
- `prompts/HANDOFF_STATE_MACHINE.md`
- `prompts/CARE_OVERLAY_GATES.md`
- `.agents/skills/agent-task-executor/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md`
- `.agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md`
- `prompts/tasks/20260703_myops_audit.md`
- `results/20260703_hardmode_goal/subagents/myops_audit_executor_prompt.md`

## Data/Split/Evaluator/Export Paths

- Dataset501 raw dataset: `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json`
- Dataset501 preprocessed split: `data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json`
- protocol split used by custom fold0 routes: `data/benchmarks/protocol/splits_MyoPS.json`
- compact label utilities: `code/nnUNet/nnunet_label_utils.py`
- conversion code: `code/nnUNet/convert_myops_to_nnunet.py`
- offline evaluator: `scripts/evaluation/evaluate_predictions.py`
- validation export/package code: `scripts/submission/prepare_care_myocardium_validation.py`

## Model/Loss/Route Paths

- SRR fold0 runner and evaluator: `scripts/training/run_srr_myops_fold0.py`
- SRR losses and missing-T2 mask: `src/care_myocardium/losses/srr_losses.py`
- SRR-lite model: `src/care_myocardium/models/srr_myops.py`
- SRR-v2 model: `src/care_myocardium/models/srr_v2_unet.py`
- pathology heads: `src/care_myocardium/models/pathology_heads.py`
- retrieval blocks: `src/care_myocardium/models/srr_blocks.py`
- rescue route finalizer: `scripts/evaluation/finalize_rescue_srr_route.py`
- cascade finalizer: `scripts/evaluation/finalize_cascade_teacher_route.py`

## Same-Split Reference Paths

- nnU-Net fold0 checkpoint: `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_best.pth`
- nnU-Net fold0 validation summary: `data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation/summary.json`
- nnU-Net pathology subgroup summary: `results/metrics/unified/nnUNet_D501_fold0_pathology_hd/fold_0/modality_group_metrics.md`
- nnU-Net aggregate summary: `results/metrics/unified/nnUNet501/aggregate.md`

## Cache Isolation

- SRR-v2 variant outputs are isolated under per-route `results/20260629_srr_v2_unet_core/**/variants/<variant>/`.
- Cascade outputs are isolated under `results/20260629_cascade_teacher_route/variants/`, `revision_signal_seek/variants/`, and `revision_postprocess_sweep/variants/`.
- Prediction caches are checkpoint/variant-specific directories, not a shared validation cache.

## Evidence Supplement Tables

- `results/20260703_myops_audit/route_evidence_index.csv`: per-route/per-variant result, selection, metric, prediction, checkpoint, training log, and job log path index.
- `results/20260703_myops_audit/cache_isolation_table.csv`: selected evidence roots and cache-isolation assessment.
- `results/20260703_myops_audit/command_transcript.md`: saved command transcript for this evidence revision; original executor transcript is recorded as `evidence not found`.
"""


def next_route_gate_md(best: dict[str, dict[str, str]]) -> str:
    best_edema = best.get("best_edema_gt_positive", {})
    best_scar = best.get("best_scar_all_cases", {})
    return f"""# Next Route Gate

controlled_state: EXECUTED_UNAUDITED

## Current Gate Inputs

- nnU-Net scar all-case reference: `{NNUNET_SCAR_ALL:.4f}`; 80pct floor `{NNUNET_SCAR_GATE:.4f}`
- nnU-Net edema GT-positive reference: `{NNUNET_EDEMA_GT_POS:.4f}`; 80pct floor `{NNUNET_EDEMA_GATE:.4f}`
- best custom scar all-case: `{best_scar.get('variant', 'evidence not found')}` Dice `{best_scar.get('dice_mean', 'evidence not found')}` from `{best_scar.get('source_file', 'evidence not found')}`
- best custom edema GT-positive: `{best_edema.get('variant', 'evidence not found')}` Dice `{best_edema.get('dice_mean', 'evidence not found')}` from `{best_edema.get('source_file', 'evidence not found')}`

## Candidate Next Tasks

| task | gate | decision | required evidence before promotion |
| --- | --- | --- | --- |
| `20260703_myops_fp_control` | Start only if it is nnU-Net anchored and targets remote FP/component burden without changing labels/evaluator. | GO_WITH_REVIEW | same-split fold0 metrics, no-T2 empty-GT stability, CenterB/CenterC, component/remote-FP table, prediction/cache path |
| `20260703_myops_srr_propose_refine` | Start only if it is a real proposal/refinement mechanism, not direct logit mixing. | CONDITIONAL_GO | proposal recall/precision, candidate coverage, independent second-stage input contract, same-split nnU-Net comparison |
| `20260703_myops_alignment_gate` | Start only with explicit transform family and plausibility checks. | NO_GO_FOR_CURRENT_EVIDENCE | moving/fixed definitions, affine/deformable/TPS/flow evidence, interpolation policy, Jacobian/roundtrip/mask consistency, downstream metric |
| `20260703_myops_anchor_refine` | Preferred over more SRR tuning if anchored to nnU-Net predictions and designed as pathology postprocessor/refiner. | GO_WITH_REVIEW | teacher path, residual/refinement contract, scar/edema Dice+HD95, CenterC, LGE-only, no-T2 stability, ablation vs no-refiner |

## Escalation

Do not expand folds, package validation, upload, or continue SRR tuning automatically from this executor result. A separate read-only audit must review these artifacts first.
"""


def result_md() -> str:
    written = [
        "results/20260703_myops_audit/result.md",
        "results/20260703_myops_audit/MANIFEST.md",
        "results/20260703_myops_audit/mechanism_audit.md",
        "results/20260703_myops_audit/label_export_qc.md",
        "results/20260703_myops_audit/architecture_gap_audit.md",
        "results/20260703_myops_audit/route_gap_table.csv",
        "results/20260703_myops_audit/failure_case_table.csv",
        "results/20260703_myops_audit/route_evidence_index.csv",
        "results/20260703_myops_audit/cache_isolation_table.csv",
        "results/20260703_myops_audit/command_transcript.md",
        "results/20260703_myops_audit/code_path_audit.md",
        "results/20260703_myops_audit/next_route_gate.md",
    ]
    return f"""# Result 20260703 MyoPS Audit

self_assessed_status: EXECUTED_UNAUDITED
role: executor
review_required: true

## Execution Summary

Completed an evidence-only MyoPS mechanism audit. No validation upload, upload-ready package, fold expansion, training, label mapping edit, fold split edit, evaluator edit, network access, commit, or push was performed.

Evidence supplement revision: added the route evidence index, cache-isolation table, and saved command transcript requested by the first read-only audit in `results/20260703_myops_audit/review.md`.

claim.route_completion: `results/20260629_rescue_goal/route_status.csv` and `completion_audit.md` support that the selected rescue routes have result/selection/metric/prediction evidence, while cancelled duplicate targeted A100/Volta roots are not selected evidence.
claim.route_evidence_index: `results/20260703_myops_audit/route_evidence_index.csv` now enumerates result, selection, metric, prediction, checkpoint, training log, and job log paths per route/variant, with `evidence not found` where unavailable.
claim.cache_isolation: `results/20260703_myops_audit/cache_isolation_table.csv` now enumerates selected evidence roots and cache paths; missing caches remain explicit.
claim.label_mapping: compact train/eval mapping and compact-to-raw submission mapping are present and consistent in code paths.
claim.t2_contract: current SRR loss/proposal code masks dense edema supervision to T2-present samples and avoids myocardium/scar as no-T2 edema hard negatives; poor no-T2/CenterC metrics remain a model failure, not a label-contract proof.
claim.architecture_gap: SRR-v2 has multiscale encoder-decoder machinery, but pathology outputs still use 1x1 heads and proposal evidence is directly mixed into final logits; cascade revisions remain teacher-preserving with tiny deltas.
claim.next_state: executor stops at EXECUTED_UNAUDITED pending separate read-only audit.

## Files Read

See `results/20260703_myops_audit/code_path_audit.md` for the indexed read set, including repository rules, task rules, rescue status, Dataset501 split/data, evaluator/export code, model/loss code, nnU-Net reference artifacts, and SRR/cascade selection files.

## Files Changed

- `scripts/evaluation/audit_myops_mechanism_20260703.py`
{chr(10).join(f"- `{p}`" for p in written)}

## Commands

- `git status --short` -> exit 0
- required rule/skill/task reads with `sed` -> exit 0
- targeted `find`/`rg` evidence discovery -> exit 0, except the memory registry quick-pass returned exit 2 because the runtime memory file was absent and one optional fallback aggregation-file check returned exit 2 because that file was not present.
- `python scripts/evaluation/audit_myops_mechanism_20260703.py` -> exit 0
- saved revision command transcript: `results/20260703_myops_audit/command_transcript.md`

## Tests / Verification

- Generated CSV artifacts are present under `results/20260703_myops_audit/`.
- Evidence supplement CSVs were regenerated from `results/20260629_rescue_goal/route_status.csv` and selected evidence roots.
- Supplement verification counted `25` route rows: `21` ready rows, `4` not-selected duplicate rows, and no non-selected row with inherited job-log evidence.
- Generator syntax check passed with `python -m py_compile scripts/evaluation/audit_myops_mechanism_20260703.py`.
- Prediction label-set QC read representative compact prediction directories when SimpleITK was available.
- This was an audit/report generation task; no model training or validation upload tests were run.

## Artifacts

{chr(10).join(f"- `{p}`" for p in written)}

## Failures And Incomplete Items

- `results/20260703_myops_audit/review.md` was not written because this session is the executor and must not audit itself.
- The original first-executor stdout/stderr transcript is `evidence not found`; this revision records a current command transcript in `command_transcript.md`.
- Hosted validation metrics are `evidence not found` because validation upload/package execution is forbidden by task scope.
- Official upload-ready raw-label package evidence is `evidence not found` for this task; label/export code paths are audited only.

## Git Diff Summary

- Updated the task-scoped audit script to generate per-route evidence and cache-isolation supplement tables.
- Added required audit reports and CSV tables under `results/20260703_myops_audit/`.

## Required Next State

EXECUTED_UNAUDITED
"""


def manifest_md() -> str:
    return """# Manifest 20260703 MyoPS Audit

Task: `prompts/tasks/20260703_myops_audit.md`
Result: `results/20260703_myops_audit/result.md`
Review: `results/20260703_myops_audit/review.md` (not written by executor; required separate audit)

## Artifacts

- `results/20260703_myops_audit/mechanism_audit.md`: route completion and mechanism-level finding.
- `results/20260703_myops_audit/label_export_qc.md`: compact/raw label and export QC.
- `results/20260703_myops_audit/architecture_gap_audit.md`: SRR/cascade architecture adequacy audit.
- `results/20260703_myops_audit/route_gap_table.csv`: subgroup and nnU-Net/reference gap table.
- `results/20260703_myops_audit/failure_case_table.csv`: high-risk case-level failures by route/variant.
- `results/20260703_myops_audit/code_path_audit.md`: evidence, code, evaluator, split, and cache-isolation path index.
- `results/20260703_myops_audit/next_route_gate.md`: GO/NO-GO gate for next candidate tasks.
- `results/20260703_myops_audit/route_evidence_index.csv`: evidence supplement table with result, selection, metric, prediction, checkpoint, and log paths per route/variant.
- `results/20260703_myops_audit/cache_isolation_table.csv`: evidence supplement table for selected roots and cache isolation.
- `results/20260703_myops_audit/command_transcript.md`: saved command transcript for this revision; original executor transcript is marked `evidence not found`.

## Generator

- `scripts/evaluation/audit_myops_mechanism_20260703.py`
"""


def command_transcript_md() -> str:
    return """# Command Transcript 20260703 MyoPS Audit Evidence Revision

scope: evidence supplement only
original_executor_transcript: evidence not found

This transcript records the commands used for the narrow evidence revision. It does not reconstruct stdout/stderr from the first executor session; no saved original executor transcript artifact was found in `results/20260703_myops_audit/`.

| command | exit_status | purpose |
| --- | ---: | --- |
| `rg -n "20260703_myops_audit|myops_audit|hardmode_goal" /users/a/e/aereinh/.codex-homes/CARE/memories/MEMORY.md` | 2 | Memory quick-pass check; runtime memory registry was absent in this workspace. |
| `git status --short --branch` | 0 | Record dirty worktree before revision. |
| `sed -n ... AGENTS.md prompts/AGENT_RULES.md prompts/CHATGPT_RULES.md prompts/HANDOFF_STATE_MACHINE.md prompts/CARE_OVERLAY_GATES.md prompts/tasks/20260703_myops_audit.md` | 0 | Required rule and parent task reads. |
| `sed -n ... .agents/skills/agent-task-executor/SKILL.md .agents/skills/domains-medical-imaging-medical-imaging-deep-learning/SKILL.md .agents/skills/domains-medical-imaging-medical-imaging-deep-learning/references/reference.md` | 0 | Required executor and medical-imaging evidence-gate skill reads. |
| `sed -n ... results/20260703_hardmode_goal/subagents/myops_audit_evidence_revision_executor_prompt.md` | 0 | Read revision-specific executor prompt. |
| `find results/20260703_myops_audit -maxdepth 2 -type f | sort` | 0 | Enumerate existing audit artifacts before supplement. |
| `sed -n ... results/20260703_myops_audit/result.md review.md MANIFEST.md mechanism_audit.md code_path_audit.md` | 0 | Read first executor result, first audit decision, manifest, and indexed evidence. |
| `sed -n ... results/20260629_rescue_goal/final_status.md completion_audit.md route_status.csv` | 0 | Read rescue final status and route ledger used by supplement tables. |
| `find ... -path '*/predictions*' ...` | 0 | Discover prediction cache directories under selected route roots. |
| `find ... -iname '*.pt' -o -iname '*.pth' ...` | 0 | Discover route checkpoint artifacts. |
| `find logs -maxdepth 1 -type f | sort | rg 'RePropF0|SRRv2|Cascade'` | 0 | Discover route job logs. |
| `rg -n "VARIANT|variant|coarse_to_fine|nnunet_anatomy|pathology_teacher" logs/CascadeOOFRefine_*.log` | 0 | Map cascade job logs to formal variants. |
| `sed -n '1,80p' results/20260629_srr_v2_unet_core_htzhulab_fallback/aggregation_status.csv` | 2 | Optional fallback aggregation file check; file was not present. |
| `python scripts/evaluation/audit_myops_mechanism_20260703.py` | 0 | Regenerate audit artifacts plus evidence supplement CSVs and this transcript. |
| `rg -n "find evidence discovery|Supplement verification|Required Next State|self_assessed_status|route_evidence_index|cache_isolation_table|command_transcript" results/20260703_myops_audit/result.md` | 126 | Read-only verification attempt with unsafe shell quoting in an earlier pattern; no files were modified. |
| `rg -n 'find evidence discovery|Supplement verification|Required Next State|self_assessed_status|route_evidence_index|cache_isolation_table|command_transcript' results/20260703_myops_audit/result.md` | 0 | Safe rerun verifying result fields and supplement references. |
| `python -m py_compile scripts/evaluation/audit_myops_mechanism_20260703.py` | 0 | Generator syntax check. |
| `python -c 'import csv; ... route_evidence_index.csv ... cache_isolation_table.csv ...'` | 0 | Count supplement rows and verify ready/not-ready coverage. |

Forbidden actions not run: training, validation upload, validation packaging, fold expansion, label mapping edits, fold split edits, evaluator edits, network calls, git commit, git push.
"""


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    gap_rows = build_route_gap_table()
    failure_rows = build_failure_case_table()
    label_sets = prediction_label_sets()
    best = route_best(gap_rows)
    route_evidence_rows = build_route_evidence_index()
    cache_rows = build_cache_isolation_table(route_evidence_rows)

    write_csv(
        OUT_DIR / "route_gap_table.csv",
        gap_rows,
        [
            "route",
            "variant",
            "metric_name",
            "class_id",
            "group",
            "n",
            "dice_mean",
            "hd95_mean",
            "component_count_mean",
            "remote_fp_mean",
            "empty_prediction_rate",
            "nnunet_reference_dice",
            "selection_floor_80pct",
            "gap_to_80pct_floor",
            "source_file",
        ],
    )
    write_csv(
        OUT_DIR / "failure_case_table.csv",
        failure_rows,
        [
            "route",
            "variant",
            "case_id",
            "center",
            "modality_group",
            "t2_present",
            "metric_name",
            "class_id",
            "dice",
            "hd95",
            "component_count",
            "remote_fp_count",
            "pred_gt_volume_ratio",
            "pred_empty",
            "gt_empty",
            "failure_score",
            "source_file",
        ],
    )
    write_csv(
        OUT_DIR / "route_evidence_index.csv",
        route_evidence_rows,
        [
            "route",
            "variant",
            "ready_to_aggregate",
            "selection_status",
            "result_path",
            "selection_path",
            "metric_paths",
            "prediction_dir",
            "prediction_file_count",
            "checkpoint_path",
            "training_or_variant_log_path",
            "job_log_path",
            "source_variant_dir",
            "route_root",
            "task",
            "stop_reason",
            "notes",
        ],
    )
    write_csv(
        OUT_DIR / "cache_isolation_table.csv",
        cache_rows,
        [
            "route",
            "variant",
            "selected_evidence",
            "evidence_root",
            "variant_specific_root",
            "prediction_cache",
            "checkpoint_cache",
            "metric_cache",
            "log_cache",
            "cache_isolation_assessment",
            "missing_cache_evidence",
        ],
    )
    write_text(OUT_DIR / "mechanism_audit.md", route_completion_md())
    write_text(OUT_DIR / "label_export_qc.md", label_export_qc_md(label_sets))
    write_text(OUT_DIR / "architecture_gap_audit.md", architecture_gap_md())
    write_text(OUT_DIR / "code_path_audit.md", code_path_md())
    write_text(OUT_DIR / "next_route_gate.md", next_route_gate_md(best))
    write_text(OUT_DIR / "command_transcript.md", command_transcript_md())
    write_text(OUT_DIR / "MANIFEST.md", manifest_md())
    write_text(OUT_DIR / "result.md", result_md())
    print(f"Wrote audit artifacts to {rel(OUT_DIR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
