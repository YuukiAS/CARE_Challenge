#!/usr/bin/env python3
"""Batch10 Wave2 fair 44-case re-evaluation orchestration and aggregation."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.evaluate_predictions import dice_per_class, hd95_class  # noqa: E402
from scripts.inference.run_care_mm_batch10_fair_inference import (  # noqa: E402
    LABELS,
    RAW_LABEL_DIR,
    component_stats,
    precision_recall,
    read_label,
)
from src.care_myocardium.data.care_mm_batch9 import build_case_records, load_fold_cases, sha256_file  # noqa: E402

TASK_KEY = "20260724_care_myops_batch10_deadline_rescue"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
BASELINE_PRED_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/validation"
INFERENCE_ENTRYPOINT = REPO_ROOT / "scripts/inference/run_care_mm_batch10_fair_inference.py"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def val_cases() -> list[str]:
    return sorted(load_fold_cases(0)[1])


def records_by_case() -> dict[str, Any]:
    return {r.case_id: r for r in build_case_records(0)}


def rescue_split_by_case() -> dict[str, str]:
    path = RESULT_ROOT / "rescue_split_manifest.csv"
    return {row["case_id"]: row["rescue_split"] for row in read_csv(path)} if path.is_file() else {}


def rescue_cases(split_name: str) -> list[str]:
    return sorted(case_id for case_id, split in rescue_split_by_case().items() if split == split_name)


def candidate_prefix(row: dict[str, str], *, tta: bool = False) -> str:
    sha = str(row.get("checkpoint_sha256", ""))[:8]
    epoch = str(row.get("epoch") or row.get("checkpoint_epoch") or "")
    epoch_part = f"_epoch{int(epoch):03d}" if str(epoch).isdigit() else ""
    phase = "tta" if tta else "phase1"
    return f"{phase}_{row['variant']}_seed{row['seed']}{epoch_part}_{sha}"


def evaluation_inventory() -> list[dict[str, str]]:
    screening = RESULT_ROOT / "checkpoint_screening_manifest.csv"
    promoted = []
    if screening.is_file():
        for row in read_csv(screening):
            if row.get("selection_status") == "PROMOTED_TOP2_CALIBRATION_ONLY":
                promoted.append({
                    "seed": row["seed"],
                    "variant": row["screen_variant"],
                    "checkpoint_path": row["checkpoint_path"],
                    "checkpoint_sha256": row["checkpoint_sha256"],
                    "epoch": row.get("epoch", ""),
                    "candidate_source": "checkpoint_screening_calibration_top2",
                })
    fixed = []
    for row in read_csv(RESULT_ROOT / "existing_checkpoint_inventory.csv"):
        if row.get("variant") in {"student_moddrop_control", "student_reliable_distill"}:
            fixed.append({**row, "candidate_source": "fixed_epoch25_from_batch9_freeze", "epoch": "25"})
    return sorted(promoted + fixed, key=lambda r: (r.get("variant", ""), r.get("seed", ""), int(r.get("epoch") or 0), r.get("checkpoint_sha256", "")))


def ensure_rescue_split() -> list[dict[str, Any]]:
    records = records_by_case()
    val = [records[c] for c in val_cases()]
    grouped: dict[tuple[str, int, int], list[Any]] = defaultdict(list)
    for rec in val:
        grouped[(rec.center, int(rec.scar_positive), int(rec.edema_positive))].append(rec)
    rows: list[dict[str, Any]] = []
    counts = {"calibration": 0, "audit": 0}
    for key in sorted(grouped):
        members = sorted(grouped[key], key=lambda r: hashlib.sha256(r.case_id.encode("utf-8")).hexdigest())
        start_calibration = counts["calibration"] <= counts["audit"]
        for idx, rec in enumerate(members):
            even_slot = idx % 2 == 0
            assignment = "calibration" if even_slot == start_calibration else "audit"
            counts[assignment] += 1
            rows.append({
                "case_id": rec.case_id,
                "split": rec.split,
                "rescue_split": assignment,
                "center": rec.center,
                "modality_group": rec.modality_group,
                "scar_positive": int(rec.scar_positive),
                "edema_positive": int(rec.edema_positive),
                "t2_present": int(rec.t2_present),
                "complete_trimodal": int(rec.t2_present and rec.c0_present),
                "stratum": f"{rec.center}|scar{int(rec.scar_positive)}|edema{int(rec.edema_positive)}",
                "within_stratum_key": hashlib.sha256(rec.case_id.encode("utf-8")).hexdigest(),
            })
    rows = sorted(rows, key=lambda r: r["case_id"])
    write_csv(RESULT_ROOT / "rescue_split_manifest.csv", rows)
    write_json(RESULT_ROOT / "rescue_split_receipt.json", {
        "schema_version": 1,
        "status": "PASS" if len(rows) == 44 and abs(counts["calibration"] - counts["audit"]) <= 1 else "FAIL",
        "case_count": len(rows),
        "counts": counts,
        "source_cases": "fold0_validation_44",
        "strata": ["center", "scar_positive", "edema_positive"],
        "within_stratum_order": "sha256_case_id",
        "assignment": "alternating_calibration_audit",
        "parameter_selection_uses_audit": False,
    })
    return rows


def baseline_casewise() -> list[dict[str, Any]]:
    records = records_by_case()
    splits = rescue_split_by_case()
    rows: list[dict[str, Any]] = []
    for case_id in val_cases():
        rec = records[case_id]
        pred_path = BASELINE_PRED_ROOT / f"{case_id}.nii.gz"
        if not pred_path.is_file():
            raise FileNotFoundError(f"missing baseline prediction: {pred_path}")
        gt_img, gt = read_label(RAW_LABEL_DIR / f"{case_id}.nii.gz")
        _pred_img, pred = read_label(pred_path, reference=gt_img)
        spacing = tuple(float(x) for x in gt_img.GetSpacing()[::-1])
        myocardium = (gt >= 1) & (gt <= 5)
        for pathology, class_id in LABELS.items():
            prec, rec_val = precision_recall(pred, gt, class_id)
            row = {
                "variant": "nnunet_fold0_baseline",
                "seed": "fold0",
                "case_id": case_id,
                "pathology": pathology,
                "class_id": class_id,
                "dice": dice_per_class(pred, gt, class_id, skip_if_gt_empty=True),
                "hd95": hd95_class(pred, gt, class_id, spacing),
                "precision": prec,
                "recall": rec_val,
                "gt_positive": int(bool(np.any(gt == class_id))),
                "prediction_positive": int(bool(np.any(pred == class_id))),
                "center": rec.center,
                "modality_group": rec.modality_group,
                "complete_trimodal": int(rec.t2_present and rec.c0_present),
                "rescue_split": splits.get(case_id, ""),
                "no_t2_edema_predicted_voxels": int(np.count_nonzero(pred == 4)) if not rec.t2_present else 0,
                "source_prefix": "baseline_nnunet_fold0_existing_prediction",
                "checkpoint_path": "NA_baseline_evaluation_only",
                "checkpoint_sha256": "NA_baseline_evaluation_only",
            }
            row.update(component_stats(pred, gt, myocardium, class_id, spacing))
            rows.append(row)
    write_csv(RESULT_ROOT / "baseline_recomputed_casewise.csv", rows)
    return rows


def to_float(value: Any) -> float | None:
    if value in (None, "", "nan", "None"):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if np.isnan(v) or np.isinf(v):
        return None
    return v


def mean(values: list[Any]) -> float | None:
    vals = [v for v in (to_float(x) for x in values) if v is not None]
    return float(np.mean(vals)) if vals else None


def population_filter(rows: list[dict[str, Any]], population: str) -> list[dict[str, Any]]:
    if population == "full44":
        return rows
    if population == "positive_gt":
        return [r for r in rows if str(r.get("gt_positive")) in {"1", "True", "true"}]
    if population == "complete_trimodal":
        return [r for r in rows if str(r.get("complete_trimodal")) in {"1", "True", "true"}]
    if population == "calibration":
        return [r for r in rows if r.get("rescue_split") == "calibration"]
    if population == "audit":
        return [r for r in rows if r.get("rescue_split") == "audit"]
    if population == "CenterB":
        return [r for r in rows if r.get("center") == "CenterB"]
    if population == "CenterC":
        return [r for r in rows if r.get("center") == "CenterC"]
    if population == "lge_only":
        return [r for r in rows if r.get("modality_group") == "LGE-only"]
    if population == "lge_c0":
        return [r for r in rows if r.get("modality_group") == "C0+LGE"]
    if population == "small_scar":
        return [r for r in rows if r.get("pathology") == "scar" and str(r.get("gt_positive")) in {"1", "True", "true"} and (to_float(r.get("gt_volume_mm3")) or 0.0) < 500.0]
    if population == "large_scar":
        return [r for r in rows if r.get("pathology") == "scar" and str(r.get("gt_positive")) in {"1", "True", "true"} and (to_float(r.get("gt_volume_mm3")) or 0.0) >= 500.0]
    if population == "all_cases_empty_safe":
        return rows
    raise ValueError(f"unknown population {population}")


def summarize(rows: list[dict[str, Any]], output: Path, *, source: str) -> list[dict[str, Any]]:
    populations = ["full44", "positive_gt", "all_cases_empty_safe", "complete_trimodal", "calibration", "audit", "CenterB", "CenterC", "lge_only", "lge_c0", "small_scar", "large_scar"]
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row.get("variant")), str(row.get("seed")), str(row.get("source_prefix")), str(row.get("pathology")))].append(row)
    summary: list[dict[str, Any]] = []
    for (variant, seed, prefix, pathology), group in sorted(grouped.items()):
        for pop in populations:
            subset = population_filter(group, pop)
            if not subset:
                continue
            summary.append({
                "source": source,
                "variant": variant,
                "seed": seed,
                "source_prefix": prefix,
                "pathology": pathology,
                "population": pop,
                "case_count": len(subset),
                "gt_positive_cases": sum(int(str(r.get("gt_positive")) in {"1", "True", "true"}) for r in subset),
                "mean_dice": mean([r.get("dice") for r in subset]),
                "mean_hd95": mean([r.get("hd95") for r in subset]),
                "mean_precision": mean([r.get("precision") for r in subset]),
                "mean_recall": mean([r.get("recall") for r in subset]),
                "mean_remote_fp_volume_mm3": mean([r.get("remote_fp_volume_mm3") for r in subset]),
                "mean_component_count": mean([r.get("component_count") for r in subset]),
                "mean_volume_ratio": mean([r.get("volume_ratio") for r in subset]),
                "empty_prediction_count": sum(int(float(r.get("empty_prediction") or 0)) for r in subset),
                "empty_prediction_rate": sum(int(float(r.get("empty_prediction") or 0)) for r in subset) / max(1, len(subset)),
                "no_t2_edema_predicted_voxels_sum": sum(int(float(r.get("no_t2_edema_predicted_voxels") or 0)) for r in subset),
                "help_count_vs_nnunet": sum(int((to_float(r.get("delta_dice_vs_nnunet")) or 0.0) > 1e-8) for r in subset),
                "harm_count_vs_nnunet": sum(int((to_float(r.get("delta_dice_vs_nnunet")) or 0.0) < -1e-8) for r in subset),
            })
    write_csv(output, summary)
    return summary


def add_help_harm(candidate_rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline = {(r["case_id"], r["pathology"]): r for r in baseline_rows}
    splits = rescue_split_by_case()
    out: list[dict[str, Any]] = []
    for row in candidate_rows:
        b = baseline.get((str(row["case_id"]), str(row["pathology"])))
        new = dict(row)
        new["rescue_split"] = splits.get(str(row.get("case_id")), new.get("rescue_split", ""))
        if b is not None:
            d = to_float(row.get("dice"))
            bd = to_float(b.get("dice"))
            h = to_float(row.get("hd95"))
            bh = to_float(b.get("hd95"))
            new["baseline_dice"] = bd
            new["baseline_hd95"] = bh
            new["delta_dice_vs_nnunet"] = None if d is None or bd is None else d - bd
            new["delta_hd95_vs_nnunet"] = None if h is None or bh is None else h - bh
            delta = to_float(new["delta_dice_vs_nnunet"])
            new["casewise_help_harm_vs_nnunet"] = "tie_or_empty" if delta is None or abs(delta) <= 1e-8 else ("help" if delta > 0 else "harm")
        out.append(new)
    return out


def completed_casewise(path: Path) -> bool:
    rows = read_csv(path)
    return len(rows) == 88 and len({r.get("case_id") for r in rows}) == 44


def run_candidate(row: dict[str, str], *, device: str, tta: bool, force: bool) -> None:
    prefix = candidate_prefix(row, tta=tta)
    out_casewise = RESULT_ROOT / f"{prefix}_casewise_metrics.csv"
    if completed_casewise(out_casewise) and not force:
        print(f"SKIP completed {prefix}")
        return
    pred_dir = RESULT_ROOT / "runtime" / ("phase2_tta" if tta else "phase1") / prefix
    cmd = [
        sys.executable,
        str(INFERENCE_ENTRYPOINT),
        "--variant", row["variant"],
        "--seed", row["seed"],
        "--checkpoint", row["checkpoint_path"],
        "--prediction-dir", str(pred_dir.relative_to(REPO_ROOT)),
        "--output-dir", str(RESULT_ROOT.relative_to(REPO_ROOT)),
        "--prefix", prefix,
        "--cases", ",".join(val_cases()),
        "--device", device,
        "--save-probabilities",
        "--save-preprocessed-logits",
    ]
    if tta:
        cmd.extend(["--mirror-axes", "0,1,2"])
    started = int(time.time())
    proc = subprocess.run(cmd, cwd=REPO_ROOT, text=True)
    attempt = {
        "timestamp_unix": started,
        "finished_unix": int(time.time()),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "phase": "phase2_tta" if tta else "phase1_no_tta",
        "variant": row["variant"],
        "seed": row["seed"],
        "prefix": prefix,
        "checkpoint_path": row["checkpoint_path"],
        "checkpoint_sha256": row.get("checkpoint_sha256"),
        "device": device,
        "mirror_tta": int(tta),
        "returncode": proc.returncode,
        "command": " ".join(cmd),
    }
    attempts = read_csv(RESULT_ROOT / "inference_slurm_attempts.csv")
    attempts.append(attempt)
    write_csv(RESULT_ROOT / "inference_slurm_attempts.csv", attempts)
    if proc.returncode != 0:
        raise RuntimeError(f"inference failed for {prefix} rc={proc.returncode}")


def aggregate_single_models(baseline_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inventory = evaluation_inventory()
    all_rows: list[dict[str, Any]] = []
    all_manifest: list[dict[str, Any]] = []
    missing: list[str] = []
    for row in inventory:
        prefix = candidate_prefix(row, tta=False)
        case_path = RESULT_ROOT / f"{prefix}_casewise_metrics.csv"
        manifest_path = RESULT_ROOT / f"{prefix}_prediction_manifest.csv"
        if not completed_casewise(case_path):
            missing.append(prefix)
            continue
        all_rows.extend(read_csv(case_path))
        all_manifest.extend(read_csv(manifest_path))
    if missing:
        raise RuntimeError(f"missing or incomplete phase1 candidate outputs: {missing}")
    all_rows = add_help_harm(all_rows, baseline_rows)
    write_csv(RESULT_ROOT / "single_model_casewise_metrics.csv", all_rows)
    write_csv(RESULT_ROOT / "single_model_candidate_manifest.csv", all_manifest)
    summary = summarize(all_rows, RESULT_ROOT / "single_model_summary.csv", source="phase1_no_tta")
    teacher_summary = [r for r in summary if r.get("variant") == "teacher_full_view"]
    write_csv(RESULT_ROOT / "teacher_candidate_summary.csv", teacher_summary)
    return all_rows, summary


def select_tta_candidates(summary: list[dict[str, Any]]) -> list[dict[str, str]]:
    del summary
    inventory = evaluation_inventory()
    by_key = {(r["variant"], r["seed"], str(r.get("epoch", "")), r["checkpoint_sha256"]): r for r in inventory}
    rows = read_csv(RESULT_ROOT / "single_model_casewise_metrics.csv")
    selected: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    for pathology in LABELS:
        scored = []
        for key, row in by_key.items():
            subset = [r for r in rows if r.get("variant") == row["variant"] and r.get("seed") == row["seed"] and r.get("source_prefix") == candidate_prefix(row, tta=False) and r.get("pathology") == pathology and r.get("rescue_split") == "calibration" and r.get("gt_positive") == "1"]
            dice = mean([r.get("dice") for r in subset]) if subset else None
            hd95 = mean([r.get("hd95") for r in subset]) if subset else None
            scored.append((row, dice, hd95, len(subset)))
        scored.sort(key=lambda x: (x[1] if x[1] is not None else -1.0, -(x[2] if x[2] is not None else 1e9), x[3]), reverse=True)
        for row, _dice, _hd95, _n in scored[:2]:
            selected[(row["variant"], row["seed"], str(row.get("epoch", "")), row["checkpoint_sha256"])].add(pathology)
    out = []
    for key, reasons in sorted(selected.items()):
        row = dict(by_key[key])
        row["tta_selected_for_pathologies"] = ";".join(sorted(reasons))
        row["selection_source"] = "calibration_only_positive_gt"
        out.append(row)
    write_csv(RESULT_ROOT / "tta_candidate_selection.csv", out)
    return out


def record_tta_selection_provenance(selected: list[dict[str, str]]) -> None:
    path = RESULT_ROOT / "selection_provenance.json"
    data = json.loads(path.read_text()) if path.is_file() else {"schema_version": 1, "selection_events": []}
    data.setdefault("selection_events", []).append({
        "event": "wave2_calibration_only_tta_candidate_selection",
        "timestamp_unix": int(time.time()),
        "selection_rule": "calibration_positive_gt_top2_per_pathology_by_dice_then_hd95_no_audit_case_ids",
        "selection_read_case_ids": rescue_cases("calibration"),
        "audit_case_ids": rescue_cases("audit"),
        "audit_case_ids_used_for_selection": [],
        "selected_tta_candidates": [
            {
                "variant": r.get("variant"),
                "seed": r.get("seed"),
                "epoch": r.get("epoch"),
                "checkpoint_path": r.get("checkpoint_path"),
                "checkpoint_sha256": r.get("checkpoint_sha256"),
                "tta_selected_for_pathologies": r.get("tta_selected_for_pathologies", ""),
                "candidate_source": r.get("candidate_source", ""),
            }
            for r in selected
        ],
    })
    data["status"] = "WAVE2_TTA_SELECTION_RECORDED"
    write_json(path, data)

def aggregate_tta(baseline_rows: list[dict[str, Any]], selected: list[dict[str, str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in selected:
        prefix = candidate_prefix(row, tta=True)
        path = RESULT_ROOT / f"{prefix}_casewise_metrics.csv"
        if not completed_casewise(path):
            raise RuntimeError(f"missing or incomplete TTA output: {prefix}")
        for case_row in read_csv(path):
            case_row["tta_selected_for_pathologies"] = row.get("tta_selected_for_pathologies", "")
            rows.append(case_row)
    rows = add_help_harm(rows, baseline_rows)
    write_csv(RESULT_ROOT / "tta_candidate_casewise_metrics.csv", rows)
    return summarize(rows, RESULT_ROOT / "tta_candidate_summary.csv", source="phase2_mirror_tta")


def write_wave2_receipt(status: str, detail: dict[str, Any]) -> None:
    inventory = evaluation_inventory()
    payload = {
        "schema_version": 1,
        "status": status,
        "validation_case_count": len(val_cases()),
        "baseline_prediction_root": str(BASELINE_PRED_ROOT.relative_to(REPO_ROOT)),
        "baseline_evaluation_only": True,
        "single_model_candidates_required": len(inventory),
        "screening_promoted_candidates": sum(1 for r in inventory if r.get("candidate_source") == "checkpoint_screening_calibration_top2"),
        "fixed_control_candidates": sum(1 for r in inventory if r.get("candidate_source") == "fixed_epoch25_from_batch9_freeze"),
        "same_metric_implementation": True,
        "standard_nnunet_checkpoint_logits_or_probabilities_loaded": False,
        "detail": detail,
    }
    write_json(RESULT_ROOT / "wave2_fair_reevaluation_receipt.json", payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["prep", "phase1", "phase2", "aggregate", "all"], default="aggregate")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    ensure_rescue_split()
    baseline_rows = baseline_casewise()
    baseline_summary = summarize(baseline_rows, RESULT_ROOT / "baseline_recomputed_summary.csv", source="baseline_nnunet_evaluation_only")
    if args.phase in {"prep"}:
        write_wave2_receipt("PREP_ONLY", {"baseline_rows": len(baseline_rows), "baseline_summary_rows": len(baseline_summary)})
        return 0
    inventory = evaluation_inventory()
    if not inventory:
        raise RuntimeError("no evaluation candidates available; checkpoint screening/fixed inventory missing")
    if args.phase in {"phase1", "all"}:
        for row in inventory:
            run_candidate(row, device=args.device, tta=False, force=args.force)
    if args.phase in {"aggregate", "phase2", "all"}:
        single_rows, summary = aggregate_single_models(baseline_rows)
        selected = select_tta_candidates(summary)
        record_tta_selection_provenance(selected)
    else:
        single_rows, summary, selected = [], [], []
    if args.phase in {"phase2", "all"}:
        for row in selected:
            run_candidate(row, device=args.device, tta=True, force=args.force)
        tta_summary = aggregate_tta(baseline_rows, selected)
    elif args.phase == "aggregate":
        selected = select_tta_candidates(summary)
        completed = [row for row in selected if completed_casewise(RESULT_ROOT / f"{candidate_prefix(row, tta=True)}_casewise_metrics.csv")]
        tta_summary = aggregate_tta(baseline_rows, completed) if completed else []
        if not tta_summary:
            write_csv(RESULT_ROOT / "tta_candidate_summary.csv", [])
    else:
        tta_summary = []
    detail = {
        "baseline_rows": len(baseline_rows),
        "single_model_casewise_rows": len(single_rows),
        "single_model_summary_rows": len(summary),
        "tta_selected_candidates": len(selected),
        "tta_summary_rows": len(tta_summary),
    }
    expected_single_rows = len(evaluation_inventory()) * 44 * 2
    status = "PASS" if len(single_rows) == expected_single_rows and (args.phase not in {"phase2", "all"} or tta_summary) else "PARTIAL"
    write_wave2_receipt(status, detail)
    print(json.dumps({"status": status, **detail}, indent=2, sort_keys=True))
    return 0 if status in {"PASS", "PARTIAL"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
