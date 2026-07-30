#!/usr/bin/env python3
"""Build the MoSAIC paper-results evidence closure packet inside CARE.

The script is aggregative and local-only. It reads CARE-side predictions,
protocol files, leaderboard snapshots, and the read-only MoSAIC source/docs,
then writes traceable evidence artifacts under the requested CARE result root.
It does not train, infer, upload, or modify the MoSAIC repository.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk

try:
    import yaml
except ImportError:  # pragma: no cover - fallback only for stripped envs
    yaml = None

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.evaluation.evaluate_predictions import (
    _hd95_scipy,
    _resample_to_reference,
    dice_per_class,
    hd95_class,
)


REPO_ROOT = REPO_ROOT_FOR_IMPORT
MOSAIC_ROOT = Path("/users/a/e/aereinh/MoSAIC")
DEFAULT_RESULT_ROOT = REPO_ROOT / "results/20260726_mosaic_paper_results_completion"
RESULT_ROOT = DEFAULT_RESULT_ROOT
PAPER_RESULTS = RESULT_ROOT / "paper_results"
SCF_ROOT = REPO_ROOT / "results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1"
FOLD0_REAUDIT_ROOT = REPO_ROOT / "results/20260726_mosaic_fold0_fairness_reaudit"
FOLD0_REPRO_ROOT = REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction"
LEADERBOARD_ALIGNMENT = REPO_ROOT / "results/leaderboard/care2026_validation_submission_alignment_20260726.json"
MYOPS_SPLITS = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
CINE_SPLITS = REPO_ROOT / "data/benchmarks/protocol/splits_CineMyoPS.json"
MYOPS_CASES = REPO_ROOT / "data/benchmarks/protocol/cases_MyoPS.json"
CINE_CASES = REPO_ROOT / "data/benchmarks/protocol/cases_CineMyoPS.json"
MOSAIC_SOURCE = REPO_ROOT / "third_party/MoSAIC/source"
MOSAIC_CONFIG_DIR = MOSAIC_SOURCE / "configs"

LABELS = {
    1: "myocardium",
    2: "lv_blood",
    3: "rv_blood",
    4: "pure_edema",
    5: "scar",
}
UNION_LABEL = "lesion_union_edema_or_scar"


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: str | Path) -> str:
    p = Path(path)
    try:
        return str(p.resolve().relative_to(REPO_ROOT))
    except Exception:
        return str(p)


def resolve_repo_path(path: str | Path) -> Path:
    p = Path(path)
    return p if p.is_absolute() else REPO_ROOT / p


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        keys: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        fieldnames = keys or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def read_json(path: Path) -> Any:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def mean(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return round(float(sum(clean) / len(clean)), 6) if clean else None


def sd(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return round(float(statistics.stdev(clean)), 6) if len(clean) > 1 else None


def round_or_none(value: float | None) -> float | None:
    return None if value is None else round(float(value), 6)


def binary_dice(pred_mask: np.ndarray, gt_mask: np.ndarray, *, skip_if_gt_empty: bool = False) -> float | None:
    p_sum = float(pred_mask.sum())
    g_sum = float(gt_mask.sum())
    inter = float(np.logical_and(pred_mask, gt_mask).sum())
    if skip_if_gt_empty and g_sum < 1e-8:
        return None if p_sum < 1e-8 else 0.0
    denom = p_sum + g_sum
    if denom < 1e-8:
        return 1.0
    return float(2.0 * inter / denom)


def binary_hd95(pred_mask: np.ndarray, gt_mask: np.ndarray, spacing_zyx: tuple[float, ...]) -> float | None:
    if not pred_mask.any() and not gt_mask.any():
        return 0.0
    if not pred_mask.any() or not gt_mask.any():
        return None
    v = _hd95_scipy(pred_mask, gt_mask, spacing_zyx)
    return None if np.isinf(v) else float(v)



def compactize_myops_labels(arr: np.ndarray) -> np.ndarray:
    out = arr.copy()
    mapping = {200: 1, 500: 2, 600: 3, 1220: 4, 2221: 5}
    for src, dst in mapping.items():
        out[arr == src] = dst
    return out

def read_label_arrays(pred_path: Path, gt_path: Path) -> tuple[np.ndarray, np.ndarray, tuple[float, ...]]:
    gt_img = sitk.ReadImage(str(gt_path))
    pred_img = sitk.ReadImage(str(pred_path))
    if (
        pred_img.GetSize() != gt_img.GetSize()
        or pred_img.GetSpacing() != gt_img.GetSpacing()
        or pred_img.GetOrigin() != gt_img.GetOrigin()
        or pred_img.GetDirection() != gt_img.GetDirection()
    ):
        pred_img = _resample_to_reference(pred_img, gt_img, True)
    pred = compactize_myops_labels(sitk.GetArrayFromImage(pred_img).astype(np.int16))
    gt = compactize_myops_labels(sitk.GetArrayFromImage(gt_img).astype(np.int16))
    spacing_zyx = tuple(float(x) for x in reversed(gt_img.GetSpacing()))
    return pred, gt, spacing_zyx


def metric_row(case: dict[str, str], label_name: str, dice: float | None, hd95: float | None, gt_positive: bool, pred_positive: bool) -> dict[str, Any]:
    return {
        "case_id": case.get("case_id"),
        "fold": int(case.get("fold", -1)),
        "center": case.get("center", ""),
        "modality_availability": case.get("modality_availability", ""),
        "t2_present": case.get("t2_present", ""),
        "label": label_name,
        "dice": round_or_none(dice),
        "hd95_mm": round_or_none(hd95),
        "gt_positive": bool(gt_positive),
        "pred_positive": bool(pred_positive),
        "prediction_path": case.get("mosaic_prediction_compact", ""),
        "gt_path": case.get("gt", ""),
        "source_commit": case.get("source_commit", ""),
        "coarse_checkpoint_sha256": case.get("coarse_checkpoint_sha256", ""),
        "scar_checkpoint_sha256": case.get("scar_checkpoint_sha256", ""),
        "trained_on_case": case.get("trained_on_case", ""),
    }


def summarize_casewise(casewise: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fold_values: dict[str, dict[int, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in casewise:
        fold_values[row["label"]][int(row["fold"])].append(row)

    fold_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for label, by_fold in sorted(fold_values.items()):
        fold_dice: list[float | None] = []
        fold_hd95: list[float | None] = []
        for fold in range(5):
            rows = by_fold.get(fold, [])
            dice_mean = mean([r["dice"] for r in rows])
            hd95_mean = mean([r["hd95_mm"] for r in rows])
            fold_dice.append(dice_mean)
            fold_hd95.append(hd95_mean)
            fold_rows.append(
                {
                    "dataset": "MyoPS",
                    "model": "MoSAIC_scar_path_OOF",
                    "label": label,
                    "fold": fold,
                    "case_count": len(rows),
                    "gt_positive_cases": sum(1 for r in rows if r["gt_positive"]),
                    "pred_positive_cases": sum(1 for r in rows if r["pred_positive"]),
                    "dice_mean": dice_mean,
                    "dice_sd_casewise": sd([r["dice"] for r in rows]),
                    "hd95_mm_mean_finite": hd95_mean,
                    "hd95_mm_sd_casewise_finite": sd([r["hd95_mm"] for r in rows]),
                    "undefined_hd95_cases": sum(1 for r in rows if r["hd95_mm"] is None),
                    "status": "computed_from_held_out_oof_predictions",
                }
            )
        summary_rows.append(
            {
                "dataset": "MyoPS",
                "model": "MoSAIC_scar_path_OOF",
                "label": label,
                "fold0_dice": fold_dice[0],
                "fold1_dice": fold_dice[1],
                "fold2_dice": fold_dice[2],
                "fold3_dice": fold_dice[3],
                "fold4_dice": fold_dice[4],
                "mean_dice_across_folds": mean(fold_dice),
                "sd_dice_across_folds": sd(fold_dice),
                "fold0_hd95_mm": fold_hd95[0],
                "fold1_hd95_mm": fold_hd95[1],
                "fold2_hd95_mm": fold_hd95[2],
                "fold3_hd95_mm": fold_hd95[3],
                "fold4_hd95_mm": fold_hd95[4],
                "mean_hd95_mm_across_folds": mean(fold_hd95),
                "sd_hd95_mm_across_folds": sd(fold_hd95),
                "status": "partial_full_mosaic_missing_edema_stage_and_cine",
                "evidence_path": rel(PAPER_RESULTS / "cv/myops_casewise_metrics.csv"),
            }
        )
    return fold_rows, summary_rows


def build_cv_evidence() -> dict[str, Any]:
    out_dir = PAPER_RESULTS / "cv"
    manifest_path = SCF_ROOT / "mosaic_oof_prediction_manifest.csv"
    manifest = [r for r in read_csv(manifest_path) if r.get("pathology_component") == "scar"]
    audit = read_json(SCF_ROOT / "mosaic_oof_no_leakage_audit.json") or {}
    training_manifest = read_csv(SCF_ROOT / "mosaic_oof_training_manifest.csv")
    checkpoint_manifest = read_csv(SCF_ROOT / "mosaic_oof_checkpoint_manifest.csv")

    casewise: list[dict[str, Any]] = []
    missing_inputs: list[dict[str, Any]] = []
    for row in manifest:
        pred_path = resolve_repo_path(row["mosaic_prediction_compact"])
        gt_path = resolve_repo_path(row["gt"])
        if not pred_path.is_file() or not gt_path.is_file():
            missing_inputs.append(
                {
                    "case_id": row.get("case_id"),
                    "prediction_exists": pred_path.is_file(),
                    "gt_exists": gt_path.is_file(),
                    "prediction_path": row.get("mosaic_prediction_compact"),
                    "gt_path": row.get("gt"),
                }
            )
            continue
        pred, gt, spacing = read_label_arrays(pred_path, gt_path)
        for label_id, label_name in LABELS.items():
            gt_positive = bool((gt == label_id).any())
            pred_positive = bool((pred == label_id).any())
            skip_empty = label_id in {4, 5}
            casewise.append(
                metric_row(
                    row,
                    label_name,
                    dice_per_class(pred, gt, label_id, skip_if_gt_empty=skip_empty),
                    hd95_class(pred, gt, label_id, spacing),
                    gt_positive,
                    pred_positive,
                )
            )
        pred_union = np.logical_or(pred == 4, pred == 5)
        gt_union = np.logical_or(gt == 4, gt == 5)
        casewise.append(
            metric_row(
                row,
                UNION_LABEL,
                binary_dice(pred_union, gt_union, skip_if_gt_empty=True),
                binary_hd95(pred_union, gt_union, spacing),
                bool(gt_union.any()),
                bool(pred_union.any()),
            )
        )

    fold_rows, summary_rows = summarize_casewise(casewise)
    write_csv(out_dir / "myops_casewise_metrics.csv", casewise)
    write_csv(out_dir / "myops_fold_metrics.csv", fold_rows)
    write_csv(out_dir / "main_cv_summary.csv", summary_rows)
    write_json(
        out_dir / "myops_fold_metrics.json",
        {
            "status": "PARTIAL_CONFIRMED_MYOPS_5FOLD_SCAR_PATH_OOF",
            "generated_at_utc": now_utc(),
            "metric_semantics": {
                "compact_labels": LABELS,
                "label_standardization": "MyoPS arrays are standardized before metrics: 200->1, 500->2, 600->3, 1220->4, 2221->5; existing compact 1..5 labels are preserved.",
                "lesion_union": "labels 4 or 5",
                "dice_empty_gt_policy": "anatomy labels use empty-empty Dice=1; pathology labels skip empty-GT cases unless false-positive then 0",
                "hd95_policy": "empty-empty is 0; one-sided empty is undefined/null; means use finite values only",
            },
            "manifest": rel(manifest_path),
            "no_leakage_audit": audit,
            "training_manifest": rel(SCF_ROOT / "mosaic_oof_training_manifest.csv"),
            "checkpoint_manifest": rel(SCF_ROOT / "mosaic_oof_checkpoint_manifest.csv"),
            "manifest_row_count": len(manifest),
            "computed_case_metric_rows": len(casewise),
            "missing_input_rows": missing_inputs,
            "fold_metrics_csv": rel(out_dir / "myops_fold_metrics.csv"),
            "summary_csv": rel(out_dir / "main_cv_summary.csv"),
            "casewise_csv": rel(out_dir / "myops_casewise_metrics.csv"),
            "paper_use_boundary": "Use as clean MyoPS OOF evidence for the documented scar-path MoSAIC run; do not describe it as complete final MoSAIC edema/Cine evidence.",
            "training_stage_status": training_manifest,
            "checkpoint_status": checkpoint_manifest,
        },
    )
    write_json(
        out_dir / "cinemyops_fold_metrics.json",
        {
            "status": "MISSING_LOCAL_MOSAIC_CINEMYOPS_5FOLD_OOF",
            "searched_paths": [
                rel(MOSAIC_SOURCE / "scripts"),
                rel(REPO_ROOT / "logs"),
                rel(SCF_ROOT),
                rel(FOLD0_REAUDIT_ROOT),
                rel(REPO_ROOT / "results/care_scf"),
            ],
            "evidence": "No CARE-side MoSAIC CineMyoPS OOF prediction manifest or fold metrics were found during local source/result inspection.",
            "paper_use_boundary": "Do not write CineMyoPS MoSAIC five-fold Dice/HD95 numbers until a CARE-side prediction/GT evaluation artifact exists.",
        },
    )
    return {
        "casewise_count": len(casewise),
        "summary_rows": summary_rows,
        "fold_rows": fold_rows,
        "manifest_count": len(manifest),
        "audit_status": audit.get("status", "missing"),
        "training_manifest": training_manifest,
    }


def build_leaderboard_evidence() -> dict[str, Any]:
    out_dir = PAPER_RESULTS / "leaderboard"
    alignment = read_json(LEADERBOARD_ALIGNMENT) or {}
    payload = {
        "status": "LEADERBOARD_VISIBLE_ATTRIBUTION_UNRESOLVED_FOR_MOSAIC",
        "source": rel(LEADERBOARD_ALIGNMENT),
        "leaderboard_fetch": alignment.get("leaderboard_fetch", {}),
        "organagent_best_by_task": alignment.get("organagent_best_by_task", {}),
        "alignment_notes": alignment.get("alignment_notes", []),
        "interpretation": alignment.get("interpretation", {}),
        "paper_use_boundary": "Visible OrganAgent hosted rows may be cited only as OrganAgent leaderboard rows unless an upload receipt or package manifest binds a row to MoSAIC.",
    }
    write_json(out_dir / "leaderboard_attribution.json", payload)
    lines = [
        "# CARE2026 Leaderboard Attribution",
        "",
        "Status: LEADERBOARD_VISIBLE_ATTRIBUTION_UNRESOLVED_FOR_MOSAIC",
        "",
        f"Source: `{rel(LEADERBOARD_ALIGNMENT)}`",
        "",
        "| task | rank | time | Dice | HD | attribution |",
        "|---|---:|---|---:|---:|---|",
    ]
    for task, row in payload["organagent_best_by_task"].items():
        lines.append(
            f"| {task} | {row.get('rank', '')} | {row.get('time', '')} | {row.get('Dice', row.get('dice', ''))} | {row.get('HD', row.get('hd', ''))} | OrganAgent visible row; not locally bound to MoSAIC |"
        )
    lines += [
        "",
        "The 2026-05-18 row is locally confirmed as nnUNet MyoPS plus CineMyoPS pathology_direct, not MoSAIC. Later OrganAgent rows need hosted upload logs or missing package manifests before MoSAIC attribution.",
    ]
    write_text(out_dir / "leaderboard_attribution.md", "\n".join(lines))
    return payload


def build_ablation_and_robustness() -> tuple[dict[str, Any], dict[str, Any]]:
    ab_dir = PAPER_RESULTS / "ablations"
    rb_dir = PAPER_RESULTS / "robustness"
    full_ablation = read_csv(FOLD0_REAUDIT_ROOT / "full_data_stage_ablation_summary.csv")
    write_csv(ab_dir / "fold0_full_data_stage_ablation_summary_copy.csv", full_ablation)
    ablation = {
        "status": "PARTIAL_CONTAMINATED_FOLD0_DIAGNOSTIC_ONLY",
        "source": rel(FOLD0_REAUDIT_ROOT / "full_data_stage_ablation_summary.csv"),
        "row_count": len(full_ablation),
        "available_evidence": "Fold0 full-data leakage-contaminated stage diagnostics exist for scar/edema postprocessing stages.",
        "missing_evidence": [
            "No clean 5-fold MoSAIC ablation metrics found for coarse prior removal.",
            "No clean 5-fold MoSAIC ablation metrics found for TPS/SPG removal.",
            "No clean 5-fold MoSAIC ablation metrics found for cross-modality consistency removal.",
            "No CineMyoPS MoSAIC ablation metrics found.",
        ],
        "paper_use_boundary": "May be discussed only as diagnostic for recipe forensics; do not enter as manuscript ablation result table.",
    }
    write_json(ab_dir / "ablation_availability_audit.json", ablation)
    write_csv(
        ab_dir / "ablation_status.csv",
        [
            {"ablation": "fold0_full_data_stage_diagnostic", "status": "available_contaminated_diagnostic", "evidence_path": rel(ab_dir / "fold0_full_data_stage_ablation_summary_copy.csv")},
            {"ablation": "coarse_prior_removed_5fold", "status": "missing_clean_5fold", "evidence_path": ""},
            {"ablation": "tps_spg_removed_5fold", "status": "missing_clean_5fold", "evidence_path": ""},
            {"ablation": "modality_consistency_removed_5fold", "status": "missing_clean_5fold", "evidence_path": ""},
            {"ablation": "cinemyops_5fold_ablation", "status": "missing_clean_5fold", "evidence_path": ""},
        ],
    )

    modality_rows = read_csv(PAPER_RESULTS / "cv/myops_casewise_metrics.csv")
    subgroup_rows: list[dict[str, Any]] = []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in modality_rows:
        groups[(row["label"], row.get("modality_availability", ""))].append(row)
    for (label, modality), rows in sorted(groups.items()):
        subgroup_rows.append(
            {
                "dataset": "MyoPS",
                "label": label,
                "modality_availability": modality,
                "case_metric_rows": len(rows),
                "gt_positive_cases": sum(1 for r in rows if r.get("gt_positive") == "True" or r.get("gt_positive") is True),
                "dice_mean": mean([None if r.get("dice") in {"", None} else float(r["dice"]) for r in rows]),
                "hd95_mm_mean_finite": mean([None if r.get("hd95_mm") in {"", None} else float(r["hd95_mm"]) for r in rows]),
                "status": "observational_subgroup_not_controlled_modality_withdrawal",
            }
        )
    write_csv(rb_dir / "myops_modality_subgroup_metrics.csv", subgroup_rows)
    robustness = {
        "status": "PARTIAL_OBSERVATIONAL_SUBGROUP_ONLY",
        "available_evidence": rel(rb_dir / "myops_modality_subgroup_metrics.csv"),
        "missing_evidence": [
            "No controlled LGE-only withdrawal inference from the same trained MoSAIC weights found.",
            "No controlled LGE+C0 withdrawal inference from the same trained MoSAIC weights found.",
            "No full-vs-withdrawal CineMyoPS MoSAIC metrics found.",
        ],
        "paper_use_boundary": "Use only as modality-availability subgroup audit; do not claim modality robustness/withdrawal performance.",
    }
    write_json(rb_dir / "modality_robustness_audit.json", robustness)
    return ablation, robustness


def build_cohort_evidence() -> dict[str, Any]:
    out_dir = PAPER_RESULTS / "cohort"
    myops_cases = (read_json(MYOPS_CASES) or {}).get("cases", [])
    cine_cases = (read_json(CINE_CASES) or {}).get("cases", [])
    myops_splits = read_json(MYOPS_SPLITS) or {}
    cine_splits = read_json(CINE_SPLITS) or {}
    manifest = read_csv(SCF_ROOT / "mosaic_oof_prediction_manifest.csv")

    rows = []
    for dataset, cases, splits_path, splits in [
        ("MyoPS", myops_cases, MYOPS_SPLITS, myops_splits),
        ("CineMyoPS", cine_cases, CINE_SPLITS, cine_splits),
    ]:
        center_counts = Counter(c.get("center", "") for c in cases)
        folds = splits.get("folds", [])
        rows.append(
            {
                "dataset": dataset,
                "case_count": len(cases),
                "center_counts_json": json.dumps(dict(center_counts), sort_keys=True),
                "fold_val_counts_json": json.dumps({str(f.get("fold", i)): len(f.get("val", [])) for i, f in enumerate(folds)}, sort_keys=True),
                "fold_train_counts_json": json.dumps({str(f.get("fold", i)): len(f.get("train", [])) for i, f in enumerate(folds)}, sort_keys=True),
                "source_cases": rel(MYOPS_CASES if dataset == "MyoPS" else CINE_CASES),
                "source_splits": rel(splits_path),
                "status": "confirmed_from_protocol_json",
            }
        )
    myops_manifest_summary = {
        "case_count": len({r.get("case_id") for r in manifest}),
        "center_counts": dict(Counter(r.get("center", "") for r in manifest)),
        "modality_availability_counts": dict(Counter(r.get("modality_availability", "") for r in manifest)),
        "t2_present_counts": dict(Counter(r.get("t2_present", "") for r in manifest)),
        "fold_counts": dict(Counter(r.get("fold", "") for r in manifest)),
        "source": rel(SCF_ROOT / "mosaic_oof_prediction_manifest.csv"),
    }
    write_csv(out_dir / "cohort_summary.csv", rows)
    write_json(out_dir / "myops_oof_manifest_cohort.json", myops_manifest_summary)
    write_json(
        out_dir / "cohort_statistics.json",
        {
            "status": "CONFIRMED_FROM_PROTOCOL_AND_OOF_MANIFEST",
            "datasets": rows,
            "myops_oof_manifest_summary": myops_manifest_summary,
            "paper_use_boundary": "Dataset totals, fold sizes, center counts, and MyoPS OOF modality availability may be cited with these source paths.",
        },
    )
    return {"rows": rows, "myops_manifest_summary": myops_manifest_summary}


def build_config_evidence() -> dict[str, Any]:
    out_dir = PAPER_RESULTS / "config"
    config_rows = []
    config_payload: dict[str, Any] = {}
    for name in [
        "myops_coarse.yaml",
        "myops_fine.yaml",
        "myops_edema.yaml",
        "cine_coarse.yaml",
        "cine_fine.yaml",
        "ablation_no_coarse.yaml",
    ]:
        path = MOSAIC_CONFIG_DIR / name
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        parsed = yaml.safe_load(text) if yaml is not None and text else {"raw_text": text}
        config_payload[name] = {"path": rel(path), "parsed": parsed}
        training = parsed.get("training", {}) if isinstance(parsed, dict) else {}
        model = parsed.get("model", {}) if isinstance(parsed, dict) else {}
        data = parsed.get("data", {}) if isinstance(parsed, dict) else {}
        selection = parsed.get("selection", {}) if isinstance(parsed, dict) else {}
        config_rows.append(
            {
                "config": name,
                "path": rel(path),
                "model_arch": model.get("arch", ""),
                "base_channels": model.get("base_channels", ""),
                "batch_size": training.get("batch_size", ""),
                "learning_rate": training.get("learning_rate", ""),
                "weight_decay": training.get("weight_decay", ""),
                "max_epochs": training.get("max_epochs", ""),
                "use_amp": training.get("use_amp", ""),
                "weighted_sampling": training.get("weighted_sampling", ""),
                "target_spacing": data.get("myops_target_spacing", data.get("cine_target_spacing", "")),
                "selection_metric": selection.get("metric", ""),
                "status": "confirmed_from_care_vendored_mosaic_config" if path.is_file() else "missing",
            }
        )
    training_manifest = read_csv(SCF_ROOT / "mosaic_oof_training_manifest.csv")
    checkpoint_manifest = read_csv(SCF_ROOT / "mosaic_oof_checkpoint_manifest.csv")
    weights_manifest = read_json(REPO_ROOT / "third_party/MoSAIC/weights_manifest.json")
    write_csv(out_dir / "implementation_settings.csv", config_rows)
    write_json(
        out_dir / "implementation_settings.json",
        {
            "status": "CONFIRMED_FROM_CONFIGS_AND_RUNTIME_MANIFESTS",
            "configs": config_payload,
            "training_manifest": {"path": rel(SCF_ROOT / "mosaic_oof_training_manifest.csv"), "rows": training_manifest},
            "checkpoint_manifest": {"path": rel(SCF_ROOT / "mosaic_oof_checkpoint_manifest.csv"), "rows": checkpoint_manifest},
            "weights_manifest": {"path": rel(REPO_ROOT / "third_party/MoSAIC/weights_manifest.json"), "content": weights_manifest},
            "source_commit": (read_json(SCF_ROOT / "mosaic_oof_no_leakage_audit.json") or {}).get("source_commit", ""),
            "paper_use_boundary": "Use configuration values with exact config/runtime source paths; do not infer unrecorded training or hosted inference settings.",
        },
    )
    return {"config_rows": config_rows, "training_manifest": training_manifest}


def build_qualitative_evidence(cv: dict[str, Any]) -> dict[str, Any]:
    out_dir = PAPER_RESULTS / "qualitative"
    rows = read_csv(PAPER_RESULTS / "cv/myops_casewise_metrics.csv")
    scar_rows = [r for r in rows if r.get("label") == "scar" and r.get("gt_positive") == "True" and r.get("dice") not in {"", None}]
    scar_rows.sort(key=lambda r: float(r["dice"]), reverse=True)
    selected = []
    for tag, subset in [("high_scar_dice", scar_rows[:5]), ("low_scar_dice", scar_rows[-5:])]:
        for row in subset:
            selected.append(
                {
                    "selection_group": tag,
                    "case_id": row["case_id"],
                    "fold": row["fold"],
                    "scar_dice": row["dice"],
                    "prediction_path": row["prediction_path"],
                    "gt_path": row["gt_path"],
                    "modality_availability": row["modality_availability"],
                    "status": "traceable_case_candidate_from_computed_oof_metrics",
                }
            )
    write_csv(out_dir / "qualitative_case_provenance.csv", selected)
    payload = {
        "status": "PARTIAL_MYOPS_TRACEABLE_CASE_CANDIDATES",
        "source_casewise_metrics": rel(PAPER_RESULTS / "cv/myops_casewise_metrics.csv"),
        "selected_cases_csv": rel(out_dir / "qualitative_case_provenance.csv"),
        "missing_evidence": [
            "No final manuscript figure source file binding these selected cases was found in CARE results.",
            "No CineMyoPS MoSAIC qualitative provenance was found.",
            "No figure-level crop/window/overlay provenance was generated by this local-only aggregation.",
        ],
        "paper_use_boundary": "Use selected cases only as provenance candidates until figure generation records exact image panel inputs.",
    }
    write_json(out_dir / "qualitative_provenance.json", payload)
    return payload



def build_log_index() -> dict[str, Any]:
    logs = []
    for pattern in ["MosaicOOF_*", "MoSAICF0_*"]:
        for path in sorted((REPO_ROOT / "logs").glob(pattern)):
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
                tail = text.splitlines()[-20:]
            except Exception as exc:
                tail = [f"READ_ERROR: {exc!r}"]
            stage = "unknown"
            name = path.name.lower()
            for candidate in ["coarse", "scar", "edema", "export", "finalizer"]:
                if candidate in name:
                    stage = candidate
                    break
            logs.append(
                {
                    "log_path": rel(path),
                    "name": path.name,
                    "stage": stage,
                    "size_bytes": path.stat().st_size,
                    "mtime_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                    "tail_excerpt": "\\n".join(tail),
                }
            )
    write_csv(PAPER_RESULTS / "log_index.csv", logs)
    payload = {
        "status": "INDEXED_RELEVANT_MOSAIC_LOGS",
        "patterns": ["logs/MosaicOOF_*", "logs/MoSAICF0_*"],
        "log_count": len(logs),
        "logs": logs,
    }
    write_json(PAPER_RESULTS / "log_index.json", payload)
    return payload

def build_existing_results_index() -> None:
    paths = [
        REPO_ROOT / "code/MoSAIC",
        MOSAIC_SOURCE,
        MOSAIC_SOURCE / "scripts",
        MYOPS_SPLITS,
        CINE_SPLITS,
        SCF_ROOT,
        FOLD0_REPRO_ROOT,
        REPO_ROOT / "results/20260725_care_m0_mosaic_fold0_fair_repro",
        FOLD0_REAUDIT_ROOT,
        REPO_ROOT / "results/care_scf",
        REPO_ROOT / "results/leaderboard",
    ]
    rows = []
    for path in paths:
        if path.is_dir():
            files = [p for p in path.rglob("*") if p.is_file()]
            rows.append({"path": rel(path), "exists": True, "type": "dir", "file_count": len(files), "status": "indexed"})
        else:
            rows.append({"path": rel(path), "exists": path.is_file(), "type": "file", "file_count": 1 if path.is_file() else 0, "status": "indexed" if path.exists() else "missing"})
    write_csv(PAPER_RESULTS / "existing_results_index.csv", rows)
    lines = ["# Existing CARE Results Index", "", "| path | exists | type | file_count | status |", "|---|---:|---|---:|---|"]
    cn_lines = ["# CARE 已有结果索引", "", "| 路径 | 是否存在 | 类型 | 文件数 | 状态 |", "|---|---:|---|---:|---|"]
    for r in rows:
        lines.append(f"| `{r['path']}` | {r['exists']} | {r['type']} | {r['file_count']} | {r['status']} |")
        cn_lines.append(f"| `{r['path']}` | {r['exists']} | {r['type']} | {r['file_count']} | {r['status']} |")
    write_text(RESULT_ROOT / "CARE_EXISTING_RESULTS_INDEX.md", "\n".join(lines))
    write_text(RESULT_ROOT / "CARE_EXISTING_RESULTS_INDEX_CN.md", "\n".join(cn_lines))


def table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    lines = ["|" + "|".join(columns) + "|", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        lines.append("|" + "|".join(str(row.get(c, "")) for c in columns) + "|")
    return "\n".join(lines)


def build_final_docs(cv: dict[str, Any], leaderboard: dict[str, Any], ablation: dict[str, Any], robustness: dict[str, Any], cohort: dict[str, Any], config: dict[str, Any], qualitative: dict[str, Any]) -> None:
    categories = [
        {
            "category": "Five-fold CV",
            "status": "PARTIAL_CONFIRMED",
            "evidence": rel(PAPER_RESULTS / "cv/myops_fold_metrics.json"),
            "manuscript_action": "Use MyoPS scar-path OOF numbers with boundary; do not claim complete MoSAIC edema/Cine five-fold.",
        },
        {
            "category": "Leaderboard attribution",
            "status": "VISIBLE_UNRESOLVED_FOR_MOSAIC",
            "evidence": rel(PAPER_RESULTS / "leaderboard/leaderboard_attribution.json"),
            "manuscript_action": "Do not attribute hosted rows to MoSAIC without upload receipt/package lineage.",
        },
        {
            "category": "Ablations",
            "status": ablation["status"],
            "evidence": rel(PAPER_RESULTS / "ablations/ablation_availability_audit.json"),
            "manuscript_action": "Do not use contaminated fold0 diagnostics as clean ablation table.",
        },
        {
            "category": "Modality robustness",
            "status": robustness["status"],
            "evidence": rel(PAPER_RESULTS / "robustness/modality_robustness_audit.json"),
            "manuscript_action": "Use only subgroup audit; no controlled robustness claim.",
        },
        {
            "category": "Cohort statistics",
            "status": "CONFIRMED",
            "evidence": rel(PAPER_RESULTS / "cohort/cohort_statistics.json"),
            "manuscript_action": "Dataset totals, fold sizes, center counts, and MyoPS modality availability can be cited.",
        },
        {
            "category": "Implementation settings",
            "status": "CONFIRMED",
            "evidence": rel(PAPER_RESULTS / "config/implementation_settings.json"),
            "manuscript_action": "Use exact config/runtime values with source paths.",
        },
        {
            "category": "Qualitative provenance",
            "status": qualitative["status"],
            "evidence": rel(PAPER_RESULTS / "qualitative/qualitative_provenance.json"),
            "manuscript_action": "Use cases as candidates only until figure-level provenance is generated.",
        },
    ]
    write_csv(PAPER_RESULTS / "evidence_category_status.csv", categories)
    write_json(
        PAPER_RESULTS / "run_manifest.json",
        {
            "generated_at_utc": now_utc(),
            "result_root": rel(RESULT_ROOT),
            "paper_results_root": rel(PAPER_RESULTS),
            "categories": categories,
            "no_mosaic_repo_execution": True,
            "mosaic_repo_used_read_only": str(MOSAIC_ROOT),
        },
    )
    en = [
        "# MoSAIC Results Evidence Index",
        "",
        "This packet closes the paper-result evidence audit from CARE-side artifacts only. Numeric entries are traceable to local prediction/GT evaluation, protocol JSON, leaderboard snapshots, runtime manifests, or explicit missing-evidence audits.",
        "",
        table(categories, ["category", "status", "evidence", "manuscript_action"]),
        "",
        "Primary boundary: MyoPS clean five-fold OOF evidence is available for the MoSAIC scar path. Complete final MoSAIC edema-stage and CineMyoPS five-fold evidence are not present locally.",
    ]
    cn = [
        "# MoSAIC 结果证据索引",
        "",
        "本包只使用 CARE 侧 artifact 完成结果审计。所有数字必须追到本地预测/GT 评估、protocol JSON、leaderboard 快照、runtime manifest 或明确的缺失证据审计。",
        "",
        table(categories, ["category", "status", "evidence", "manuscript_action"]),
        "",
        "主要边界：MyoPS 的 clean five-fold OOF 证据已覆盖 MoSAIC scar path；完整 final MoSAIC edema stage 和 CineMyoPS five-fold 证据本地仍不存在。",
    ]
    write_text(RESULT_ROOT / "RESULTS_EVIDENCE_INDEX.md", "\n".join(en))
    write_text(RESULT_ROOT / "RESULTS_EVIDENCE_INDEX_CN.md", "\n".join(cn))

    external_en = [
        "# External Requirements",
        "",
        "| requirement | reason | local status |",
        "|---|---|---|",
        "| Hosted upload receipt or official account log for later OrganAgent rows | Needed to attribute CARE2026 leaderboard rows to MoSAIC | Not available in local CARE manifests |",
        "| Official validation GT | Needed for local casewise hosted Dice/HD95 reconstruction | Not available by challenge design |",
    ]
    external_cn = [
        "# 外部要求",
        "",
        "| 要求 | 原因 | 本地状态 |",
        "|---|---|---|",
        "| later OrganAgent rows 的 hosted upload receipt 或官方账号日志 | 只有它能把 CARE2026 leaderboard 行绑定到 MoSAIC | 本地 CARE manifest 未找到 |",
        "| 官方 validation GT | 需要它才能本地重算 hosted casewise Dice/HD95 | 按挑战规则本地不可用 |",
    ]
    write_text(RESULT_ROOT / "RESULTS_EXTERNAL_REQUIREMENTS.md", "\n".join(external_en))
    write_text(RESULT_ROOT / "RESULTS_EXTERNAL_REQUIREMENTS_CN.md", "\n".join(external_cn))

    truth_update = f"""# RESULTS_TRUTH_UPDATE

Generated: {now_utc()}

## Confirmed / Partially Confirmed

- MyoPS clean held-out five-fold MoSAIC scar-path OOF metrics are now computed from `paper_results/cv/myops_casewise_metrics.csv`, summarized in `paper_results/cv/main_cv_summary.csv`, and backed by `paper_results/cv/myops_fold_metrics.json`.
- Cohort counts are confirmed from `data/benchmarks/protocol/*` and `paper_results/cohort/cohort_statistics.json`.
- Implementation settings are confirmed from CARE-vendored MoSAIC configs and runtime manifests in `paper_results/config/implementation_settings.json`.

## Not Yet Supported For Manuscript Claims

- Complete final MoSAIC edema-stage five-fold results are not supported; fold1-fold4 edema training rows are `MISSING` in the runtime manifest.
- CineMyoPS MoSAIC five-fold results are not supported by a local prediction/GT evaluation artifact.
- Leaderboard rows are visible for OrganAgent, but MoSAIC attribution remains unresolved without hosted upload receipt/package lineage.
- Ablation and controlled modality robustness claims are not supported by clean five-fold artifacts.
- Qualitative cases are traceable MyoPS OOF candidates only; figure-level provenance is not complete.
"""
    truth_update_cn = f"""# RESULTS_TRUTH_UPDATE_CN

生成时间：{now_utc()}

## 已确认 / 部分确认

- MyoPS clean held-out five-fold MoSAIC scar-path OOF 指标已从 `paper_results/cv/myops_casewise_metrics.csv` 重算，并汇总到 `paper_results/cv/main_cv_summary.csv`，主审计文件为 `paper_results/cv/myops_fold_metrics.json`。
- cohort 数量可由 `data/benchmarks/protocol/*` 和 `paper_results/cohort/cohort_statistics.json` 支撑。
- 实现参数可由 CARE vendored MoSAIC configs 和 runtime manifests 支撑，见 `paper_results/config/implementation_settings.json`。

## 仍不能写成正文结果

- 完整 final MoSAIC edema-stage five-fold 结果仍不成立；runtime manifest 中 fold1-fold4 edema 行为 `MISSING`。
- CineMyoPS MoSAIC five-fold 没有本地 prediction/GT evaluation artifact 支撑。
- leaderboard 上能看到 OrganAgent 行，但没有 hosted upload receipt/package lineage 前，不能归属为 MoSAIC。
- ablation 和 controlled modality robustness 没有 clean five-fold artifact 支撑。
- qualitative 目前只有 MyoPS OOF 候选病例 provenance，还没有 figure-level crop/window/overlay provenance。
"""
    ledger_update = """# CLAIM_LEDGER_UPDATE

| claim | proposed status | evidence | action |
|---|---|---|---|
| MoSAIC method architecture and configs | confirmed_code_and_config | `paper_results/config/implementation_settings.json` | Keep with exact implementation wording. |
| MyoPS five-fold MoSAIC result | partial_confirmed_result | `paper_results/cv/myops_fold_metrics.json` | State as scar-path OOF only. |
| Complete MoSAIC edema five-fold result | unsupported_currently | `paper_results/cv/myops_fold_metrics.json` | Do not claim. |
| CineMyoPS MoSAIC five-fold result | unsupported_currently | `paper_results/cv/cinemyops_fold_metrics.json` | Do not claim. |
| CARE2026 leaderboard MoSAIC attribution | leaderboard_seen_attribution_unresolved | `paper_results/leaderboard/leaderboard_attribution.json` | Require external upload receipt. |
| Ablation gains | unsupported_currently | `paper_results/ablations/ablation_availability_audit.json` | Remove or mark future work. |
| Modality robustness | unsupported_currently | `paper_results/robustness/modality_robustness_audit.json` | Do not claim controlled robustness. |
| Cohort statistics | confirmed_result | `paper_results/cohort/cohort_statistics.json` | Use exact counts with source paths. |
| Qualitative provenance | partial_provenance | `paper_results/qualitative/qualitative_provenance.json` | Use only after final figure provenance is generated. |
"""
    ledger_update_cn = """# CLAIM_LEDGER_UPDATE_CN

| claim | 建议状态 | 证据 | 动作 |
|---|---|---|---|
| MoSAIC 方法结构和 config | confirmed_code_and_config | `paper_results/config/implementation_settings.json` | 可保留，但必须按实现精确表述。 |
| MyoPS five-fold MoSAIC result | partial_confirmed_result | `paper_results/cv/myops_fold_metrics.json` | 只能写成 scar-path OOF。 |
| 完整 MoSAIC edema five-fold result | unsupported_currently | `paper_results/cv/myops_fold_metrics.json` | 不要声明。 |
| CineMyoPS MoSAIC five-fold result | unsupported_currently | `paper_results/cv/cinemyops_fold_metrics.json` | 不要声明。 |
| CARE2026 leaderboard MoSAIC 归属 | leaderboard_seen_attribution_unresolved | `paper_results/leaderboard/leaderboard_attribution.json` | 需要外部 upload receipt。 |
| 消融收益 | unsupported_currently | `paper_results/ablations/ablation_availability_audit.json` | 删除或写成 future work。 |
| 模态鲁棒性 | unsupported_currently | `paper_results/robustness/modality_robustness_audit.json` | 不能声明 controlled robustness。 |
| cohort 统计 | confirmed_result | `paper_results/cohort/cohort_statistics.json` | 可按证据路径使用精确计数。 |
| qualitative provenance | partial_provenance | `paper_results/qualitative/qualitative_provenance.json` | 生成最终图的 figure-level provenance 后再使用。 |
"""
    write_text(RESULT_ROOT / "RESULTS_TRUTH_UPDATE.md", truth_update)
    write_text(RESULT_ROOT / "RESULTS_TRUTH_UPDATE_CN.md", truth_update_cn)
    write_text(RESULT_ROOT / "CLAIM_LEDGER_UPDATE.md", ledger_update)
    write_text(RESULT_ROOT / "CLAIM_LEDGER_UPDATE_CN.md", ledger_update_cn)


def main() -> None:
    global RESULT_ROOT, PAPER_RESULTS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    args = parser.parse_args()
    RESULT_ROOT = args.result_root
    PAPER_RESULTS = RESULT_ROOT / "paper_results"
    for sub in ["cv", "leaderboard", "ablations", "robustness", "cohort", "config", "qualitative"]:
        (PAPER_RESULTS / sub).mkdir(parents=True, exist_ok=True)

    build_existing_results_index()
    build_log_index()
    cv = build_cv_evidence()
    leaderboard = build_leaderboard_evidence()
    ablation, robustness = build_ablation_and_robustness()
    cohort = build_cohort_evidence()
    config = build_config_evidence()
    qualitative = build_qualitative_evidence(cv)
    build_final_docs(cv, leaderboard, ablation, robustness, cohort, config, qualitative)


if __name__ == "__main__":
    main()
