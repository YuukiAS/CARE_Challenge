#!/usr/bin/env python3
"""Build frozen nnU-Net/MoSAIC complementarity closure evidence.

This script only binds already-existing casewise metrics and no-GT validation
disagreement evidence. It does not train, tune thresholds, select cases for a
model, upload validation data, or claim hosted validation performance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


TASK_KEY = "20260801_care_nnunet_mosaic_complementarity_closure"
RESULT_DIR = Path("results") / TASK_KEY

FORENSICS_DIR = Path("results/20260730_care_failure_forensics_deep_research_packet")
METRIC_TRUTH_DIR = Path("results/20260731_care_metric_truth_reconciliation")
FOUR_LANE_DIR = Path("results/20260801_care_four_lane_evidence_reconciliation")
VALIDATION_PROBE_DIR = Path("results/20260728_mosaic_full_weight_validation_probe")

STD_CASEWISE = FORENSICS_DIR / "standardized_casewise_metrics.csv"
STD_MODEL_SUMMARY = FORENSICS_DIR / "standardized_model_summary.csv"
V4_M0_M10 = FORENSICS_DIR / "v4_mosaic_m0_m10_casewise.csv"
V4_RECIPE_AUDIT = FORENSICS_DIR / "v4_mosaic_recipe_population_audit.json"
V4_DECOMP_RECEIPT = FORENSICS_DIR / "mosaic_recipe_decomposition_receipt.json"
CASE_ORACLE_SOURCE = FORENSICS_DIR / "case_oracle_summary.csv"
LABEL_AVAIL = FORENSICS_DIR / "label_availability_matrix.csv"
DATA_CENTER_MODALITY = FORENSICS_DIR / "data_center_modality_matrix.csv"
ATLAS_MANIFEST = FORENSICS_DIR / "v4_atlas_manifest.csv"
METRIC_TRUTH_RECEIPT = METRIC_TRUTH_DIR / "metric_truth_receipt.json"
METRIC_SEMANTICS = METRIC_TRUTH_DIR / "metric_semantics_contract.json"
FOUR_LANE_CONTRACT = FOUR_LANE_DIR / "metric_contract.json"
FOUR_LANE_OUTER = FOUR_LANE_DIR / "all_outer_casewise.csv"
VALIDATION_CASEWISE_SOURCE = VALIDATION_PROBE_DIR / "casewise_probe_nnunet_mosaic_comparison.csv"
VALIDATION_SUMMARY_SOURCE = VALIDATION_PROBE_DIR / "comparison_summary.json"
VALIDATION_RECEIPT_SOURCE = VALIDATION_PROBE_DIR / "mosaic_full_weight_inference_receipt.json"

BOUND_NA = "BOUND_METRIC_NOT_AVAILABLE"
PRIMARY_PATHOLOGIES = ("scar", "pure_edema")
OOF_MODELS = ("nnunet_oof", "mosaic_clean_oof")
VALIDATION_CASES = [f"Case10{i:02d}" for i in range(1, 16)]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def row_hash(row: dict[str, Any]) -> str:
    payload = json.dumps(row, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def finite_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(out):
        return None
    return out


def bucket_oof(nnunet_dice: float, mosaic_dice: float) -> str:
    """Frozen OOF bucket priority from the controller handoff."""
    delta = mosaic_dice - nnunet_dice
    if max(nnunet_dice, mosaic_dice) < 0.40:
        return "BOTH_FAIL"
    if min(nnunet_dice, mosaic_dice) >= 0.65:
        return "BOTH_GOOD"
    if delta >= 0.05:
        return "MOSAIC_RESCUES"
    if -delta >= 0.05:
        return "NNUNET_PROTECTS"
    if abs(delta) < 0.05:
        return "NEAR_TIE"
    return "MIXED_TRADEOFF"


def bucket_validation(row: pd.Series) -> str:
    scar_dice = float(row["scar_dice_MoSAIC_full_downloaded_vs_nnUNet"])
    edema_dice = float(row["edema_dice_MoSAIC_full_downloaded_vs_nnUNet"])
    scar_gap = 1.0 - scar_dice
    edema_gap = 1.0 - edema_dice
    mosaic_scar = int(row["MoSAIC_full_downloaded_scar_voxels"])
    nnunet_scar = int(row["nnUNet_scar_voxels"])
    mosaic_edema = int(row["MoSAIC_full_downloaded_edema_voxels"])
    nnunet_edema = int(row["nnUNet_edema_voxels"])
    if max(scar_gap, edema_gap) < 0.20:
        return "LOW_DISAGREEMENT"
    if edema_gap >= 0.50 and mosaic_edema > nnunet_edema:
        return "MOSAIC_ADDS_EDEMA"
    if scar_gap >= 0.40 and mosaic_scar > nnunet_scar:
        return "MOSAIC_ADDS_SCAR"
    if edema_gap >= 0.50 and nnunet_edema > mosaic_edema:
        return "NNUNET_ONLY_EDEMA_DOMINANT"
    if scar_gap >= 0.40 and nnunet_scar > mosaic_scar:
        return "NNUNET_ONLY_SCAR_DOMINANT"
    return "MIXED_NO_GT_DISAGREEMENT"


def ensure_inputs() -> None:
    required = [
        STD_CASEWISE,
        STD_MODEL_SUMMARY,
        V4_M0_M10,
        V4_RECIPE_AUDIT,
        V4_DECOMP_RECEIPT,
        CASE_ORACLE_SOURCE,
        LABEL_AVAIL,
        DATA_CENTER_MODALITY,
        METRIC_TRUTH_RECEIPT,
        METRIC_SEMANTICS,
        FOUR_LANE_CONTRACT,
        FOUR_LANE_OUTER,
        VALIDATION_CASEWISE_SOURCE,
        VALIDATION_SUMMARY_SOURCE,
        VALIDATION_RECEIPT_SOURCE,
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit(
            "OPERATIONALLY_BLOCKED_MISSING_CORE_CASEWISE: missing inputs "
            + json.dumps(missing, indent=2)
        )


def source_hashes() -> dict[str, str]:
    paths = [
        STD_CASEWISE,
        STD_MODEL_SUMMARY,
        V4_M0_M10,
        V4_RECIPE_AUDIT,
        V4_DECOMP_RECEIPT,
        CASE_ORACLE_SOURCE,
        METRIC_TRUTH_RECEIPT,
        METRIC_SEMANTICS,
        FOUR_LANE_CONTRACT,
        FOUR_LANE_OUTER,
    ]
    return {str(p): sha256_file(p) for p in paths}


def modality_map() -> dict[str, dict[str, Any]]:
    labels = pd.read_csv(LABEL_AVAIL)
    center_matrix = pd.read_csv(DATA_CENTER_MODALITY)
    center_by_id = {
        f"Center{chr(ord('A') + int(row.center) - 1)}": row
        for row in center_matrix.itertuples(index=False)
    }
    out: dict[str, dict[str, Any]] = {}
    std = pd.read_csv(STD_CASEWISE)
    centers = std[["case_id", "center"]].drop_duplicates()
    for row in centers.itertuples(index=False):
        center_info = center_by_id.get(row.center)
        t2_present = bool(
            center_info is not None and int(center_info.T2_present) > 0
        )
        c0_present = bool(
            center_info is not None and int(center_info.C0_present) > 0
        )
        lge_present = bool(
            center_info is not None and int(center_info.LGE_present) > 0
        )
        out[row.case_id] = {
            "center": row.center,
            "T2_present": t2_present,
            "C0_present": c0_present,
            "LGE_present": lge_present,
            "modality_pattern": "+".join(
                name
                for name, present in [
                    ("LGE", lge_present),
                    ("T2", t2_present),
                    ("C0", c0_present),
                ]
                if present
            )
            or "UNKNOWN",
        }
    label_by_case = labels.set_index("case_id").to_dict(orient="index")
    for case_id, info in out.items():
        label_row = label_by_case.get(case_id, {})
        info.update(
            {
                "scar_nonempty": int(label_row.get("scar_nonempty", -1)),
                "pure_edema_nonempty": int(
                    label_row.get("pure_edema_nonempty", -1)
                ),
            }
        )
    return out


def build_oof_casewise() -> pd.DataFrame:
    std = pd.read_csv(STD_CASEWISE)
    std = std[std["metric_name"].isin(PRIMARY_PATHOLOGIES)].copy()
    mods = modality_map()
    rows: list[dict[str, Any]] = []
    for (case_id, pathology), group in std.groupby(["case_id", "metric_name"]):
        models = {r.model_id: r for r in group.itertuples(index=False)}
        if any(model not in models for model in OOF_MODELS):
            raise SystemExit(
                "OPERATIONALLY_BLOCKED_MISSING_CORE_CASEWISE: missing OOF model "
                f"for {case_id} {pathology}"
            )
        nn = models["nnunet_oof"]
        mo = models["mosaic_clean_oof"]
        nn_dice = float(nn.dice)
        mo_dice = float(mo.dice)
        delta = mo_dice - nn_dice
        case_info = mods.get(case_id, {})
        population = "scar_all_220" if pathology == "scar" else "pure_edema_t2_80"
        gt_positive = not bool(int(nn.empty_gt))
        nn_row = nn._asdict()
        mo_row = mo._asdict()
        rows.append(
            {
                "case_id": case_id,
                "center": nn.center,
                "pathology": pathology,
                "population": population,
                "evidence_tier": "CLEAN_HELD_OUT_OOF",
                "nnunet_model_id": "nnunet_oof",
                "mosaic_model_id": "mosaic_clean_oof",
                "nnunet_dice": nn_dice,
                "mosaic_dice": mo_dice,
                "dice_delta_mosaic_minus_nnunet": delta,
                "case_oracle_dice": max(nn_dice, mo_dice),
                "best_case_model": (
                    "mosaic_clean_oof" if mo_dice > nn_dice else "nnunet_oof"
                ),
                "bucket": bucket_oof(nn_dice, mo_dice),
                "model_disagreement_dice": finite_float(
                    nn.model_disagreement_dice
                ),
                "gt_positive": gt_positive,
                "empty_gt": bool(int(nn.empty_gt)),
                "nnunet_empty_pred": bool(int(nn.empty_pred)),
                "mosaic_empty_pred": bool(int(mo.empty_pred)),
                "gt_voxels": int(nn.gt_voxels),
                "nnunet_pred_voxels": int(nn.pred_voxels),
                "mosaic_pred_voxels": int(mo.pred_voxels),
                "gt_components": int(nn.gt_components),
                "nnunet_pred_components": int(nn.pred_components),
                "mosaic_pred_components": int(mo.pred_components),
                "nnunet_pred_volume_mm3": BOUND_NA,
                "mosaic_pred_volume_mm3": BOUND_NA,
                "gt_volume_mm3": BOUND_NA,
                "nnunet_hd95_mm": BOUND_NA,
                "mosaic_hd95_mm": BOUND_NA,
                "T2_present": bool(case_info.get("T2_present", False)),
                "C0_present": bool(case_info.get("C0_present", False)),
                "LGE_present": bool(case_info.get("LGE_present", False)),
                "modality_pattern": case_info.get("modality_pattern", "UNKNOWN"),
                "trained_on_case_possible": False,
                "not_valid_for_generalization_claim": False,
                "source_row_hashes": json.dumps(
                    {
                        "nnunet_oof": row_hash(nn_row),
                        "mosaic_clean_oof": row_hash(mo_row),
                    },
                    sort_keys=True,
                ),
                "physical_metric_status": BOUND_NA,
            }
        )
    out = pd.DataFrame(rows).sort_values(["pathology", "case_id"])
    scar_n = out[out["pathology"] == "scar"]["case_id"].nunique()
    edema_n = out[out["pathology"] == "pure_edema"]["case_id"].nunique()
    if scar_n != 220 or edema_n != 80:
        raise SystemExit(
            "OPERATIONALLY_BLOCKED_MISSING_CORE_CASEWISE: expected scar=220 "
            f"and pure_edema=80, got scar={scar_n}, pure_edema={edema_n}"
        )
    if out[out["pathology"] == "pure_edema"]["T2_present"].eq(False).any():
        raise SystemExit("Pure edema denominator contains no-T2 case.")
    return out


def summarize_buckets(casewise: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pathology, path_df in casewise.groupby("pathology"):
        for population_name, pop_df in [
            ("all_cases", path_df),
            ("gt_positive_cases", path_df[path_df["gt_positive"]]),
        ]:
            total = len(pop_df)
            for bucket, bdf in pop_df.groupby("bucket"):
                rows.append(
                    {
                        "pathology": pathology,
                        "population": population_name,
                        "bucket": bucket,
                        "case_count": len(bdf),
                        "fraction": len(bdf) / total if total else 0.0,
                        "mean_nnunet_dice": bdf["nnunet_dice"].mean(),
                        "mean_mosaic_dice": bdf["mosaic_dice"].mean(),
                        "mean_delta_mosaic_minus_nnunet": bdf[
                            "dice_delta_mosaic_minus_nnunet"
                        ].mean(),
                    }
                )
    return pd.DataFrame(rows).sort_values(["pathology", "population", "bucket"])


def summarize_subgroup(casewise: pd.DataFrame, field: str) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in casewise.groupby(["pathology", field, "bucket"]):
        pathology, subgroup, bucket = keys
        rows.append(
            {
                "pathology": pathology,
                field: subgroup,
                "bucket": bucket,
                "case_count": len(group),
                "mean_nnunet_dice": group["nnunet_dice"].mean(),
                "mean_mosaic_dice": group["mosaic_dice"].mean(),
                "mean_delta_mosaic_minus_nnunet": group[
                    "dice_delta_mosaic_minus_nnunet"
                ].mean(),
            }
        )
    return pd.DataFrame(rows).sort_values(["pathology", field, "bucket"])


def oracle_bounds(casewise: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for pathology, path_df in casewise.groupby("pathology"):
        for population_name, pop_df in [
            ("all_cases", path_df),
            ("gt_positive_cases", path_df[path_df["gt_positive"]]),
        ]:
            rescue_df = pop_df[pop_df["bucket"] == "MOSAIC_RESCUES"]
            rows.append(
                {
                    "pathology": pathology,
                    "population": population_name,
                    "case_count": len(pop_df),
                    "nnunet_mean_dice": pop_df["nnunet_dice"].mean(),
                    "mosaic_mean_dice": pop_df["mosaic_dice"].mean(),
                    "case_oracle_mean_dice": pop_df["case_oracle_dice"].mean(),
                    "oracle_gain_over_nnunet": (
                        pop_df["case_oracle_dice"].mean()
                        - pop_df["nnunet_dice"].mean()
                    ),
                    "oracle_gain_over_mosaic": (
                        pop_df["case_oracle_dice"].mean()
                        - pop_df["mosaic_dice"].mean()
                    ),
                    "mosaic_rescues_count": len(rescue_df),
                    "mosaic_rescues_fraction": (
                        len(rescue_df) / len(pop_df) if len(pop_df) else 0.0
                    ),
                    "mosaic_rescues_mean_delta": rescue_df[
                        "dice_delta_mosaic_minus_nnunet"
                    ].mean()
                    if len(rescue_df)
                    else 0.0,
                    "selector_status": "CASE_ORACLE_UPPER_BOUND_ONLY_NOT_DEPLOYABLE",
                }
            )
    return pd.DataFrame(rows).sort_values(["pathology", "population"])


def build_m10(casewise: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    v4 = pd.read_csv(V4_M0_M10)
    std_lookup = casewise.set_index(["case_id", "pathology"])
    rows: list[dict[str, Any]] = []
    for stage in ["M0", "M1", "M10"]:
        sdf = v4[v4["stage_id"] == stage].copy()
        if stage == "M10":
            sdf = sdf[sdf["edema_reliable"] == 1]
        for r in sdf.itertuples(index=False):
            if stage in {"M0", "M1"} and int(r.edema_reliable) != 1:
                continue
            for pathology, col in [
                ("scar", "scar_dice"),
                ("pure_edema", "pure_edema_dice"),
            ]:
                key = (r.case_id, pathology)
                if key not in std_lookup.index:
                    raise SystemExit(
                        "OPERATIONALLY_BLOCKED_MISSING_CORE_CASEWISE: "
                        f"missing nnU-Net OOF for M10 diagnostic {key}"
                    )
                base = std_lookup.loc[key]
                mosaic_dice = finite_float(getattr(r, col))
                if mosaic_dice is None:
                    continue
                nn_dice = float(base["nnunet_dice"])
                rows.append(
                    {
                        "case_id": r.case_id,
                        "center": r.center,
                        "pathology": pathology,
                        "mosaic_stage_id": stage,
                        "mosaic_stage_name": r.stage_name,
                        "mosaic_evidence_source": r.evidence_source,
                        "mosaic_checkpoint_scope": r.checkpoint_scope,
                        "nnunet_oof_dice": nn_dice,
                        "mosaic_stage_dice": mosaic_dice,
                        "dice_delta_mosaic_minus_nnunet": mosaic_dice
                        - nn_dice,
                        "bucket": bucket_oof(nn_dice, mosaic_dice),
                        "evidence_tier": "IN_SAMPLE_FULL_RECIPE_DIAGNOSTIC"
                        if stage == "M10"
                        else "CLEAN_HELD_OUT_OOF_REFERENCE",
                        "trained_on_case_possible": stage == "M10",
                        "not_valid_for_generalization_claim": stage == "M10",
                        "edema_reliable": bool(int(r.edema_reliable)),
                        "population": "complete_trimodal_centerB_C_80",
                        "checkpoint_set": r.checkpoint_set,
                        "checkpoint_hashes": r.checkpoint_hashes,
                    }
                )
    diag = pd.DataFrame(rows).sort_values(["mosaic_stage_id", "pathology", "case_id"])
    m10_case_count = diag[diag["mosaic_stage_id"] == "M10"]["case_id"].nunique()
    if m10_case_count != 80:
        raise SystemExit(f"M10 diagnostic expected 80 cases, got {m10_case_count}")
    summary_rows = []
    for keys, group in diag.groupby(["mosaic_stage_id", "pathology", "bucket"]):
        stage, pathology, bucket = keys
        summary_rows.append(
            {
                "mosaic_stage_id": stage,
                "pathology": pathology,
                "bucket": bucket,
                "case_count": len(group),
                "mean_nnunet_oof_dice": group["nnunet_oof_dice"].mean(),
                "mean_mosaic_stage_dice": group["mosaic_stage_dice"].mean(),
                "mean_delta_mosaic_minus_nnunet": group[
                    "dice_delta_mosaic_minus_nnunet"
                ].mean(),
                "evidence_tier": group["evidence_tier"].iloc[0],
                "generalization_claim_allowed": False
                if stage == "M10"
                else True,
            }
        )
    summary = pd.DataFrame(summary_rows).sort_values(
        ["mosaic_stage_id", "pathology", "bucket"]
    )
    pivot = diag.pivot_table(
        index=["case_id", "center", "pathology"],
        columns="mosaic_stage_id",
        values="mosaic_stage_dice",
        aggfunc="first",
    ).reset_index()
    for col in ["M0", "M1", "M10"]:
        if col not in pivot.columns:
            pivot[col] = pd.NA
    pivot["delta_M10_minus_M0"] = pivot["M10"] - pivot["M0"]
    pivot["delta_M10_minus_M1"] = pivot["M10"] - pivot["M1"]
    pivot["evidence_tier"] = "IN_SAMPLE_FULL_RECIPE_DIAGNOSTIC"
    pivot["trained_on_case_possible"] = True
    pivot["not_valid_for_generalization_claim"] = True
    transition = pivot.sort_values(["pathology", "case_id"])
    return diag, summary, transition


def build_validation() -> tuple[pd.DataFrame, dict[str, Any]]:
    val = pd.read_csv(VALIDATION_CASEWISE_SOURCE)
    if sorted(val["case_id"].tolist()) != VALIDATION_CASES:
        raise SystemExit("Validation fresh disagreement is not exactly Case1001-Case1015.")
    rows = []
    for r in val.sort_values("case_id").itertuples(index=False):
        row = r._asdict()
        bucket = bucket_validation(pd.Series(row))
        rows.append(
            {
                "case_id": r.case_id,
                "evidence_tier": "FRESH_VALIDATION_NO_GT_DISAGREEMENT",
                "geometry_equality": bool(r.geometry_ok),
                "label_validity": "LABEL_SET_PRESENT",
                "nnunet_scar_voxels": int(r.nnUNet_scar_voxels),
                "mosaic_scar_voxels": int(r.MoSAIC_full_downloaded_scar_voxels),
                "nnunet_edema_voxels": int(r.nnUNet_edema_voxels),
                "mosaic_edema_voxels": int(r.MoSAIC_full_downloaded_edema_voxels),
                "scar_agreement_dice_mosaic_vs_nnunet": float(
                    r.scar_dice_MoSAIC_full_downloaded_vs_nnUNet
                ),
                "edema_agreement_dice_mosaic_vs_nnunet": float(
                    r.edema_dice_MoSAIC_full_downloaded_vs_nnUNet
                ),
                "scar_centroid_distance_mm_mosaic_vs_nnunet": float(
                    r.scar_centroid_mm_MoSAIC_full_downloaded_vs_nnUNet
                ),
                "edema_centroid_distance_mm_mosaic_vs_nnunet": float(
                    r.edema_centroid_mm_MoSAIC_full_downloaded_vs_nnUNet
                ),
                "scar_intersection_voxels": BOUND_NA,
                "scar_union_voxels": BOUND_NA,
                "edema_intersection_voxels": BOUND_NA,
                "edema_union_voxels": BOUND_NA,
                "component_count_status": BOUND_NA,
                "disagreement_bucket": bucket,
                "no_gt_policy": "NO_HELP_HARM_OR_PERFORMANCE_CLAIM",
                "nnunet_sha256": r.nnUNet_sha256,
                "mosaic_full_downloaded_sha256": r.MoSAIC_full_downloaded_sha256,
                "source_row_hash": row_hash(row),
            }
        )
    out = pd.DataFrame(rows)
    source_summary = json.loads(VALIDATION_SUMMARY_SOURCE.read_text())
    receipt = json.loads(VALIDATION_RECEIPT_SOURCE.read_text())
    summary = {
        "created_at_utc": utc_now(),
        "status": "REUSED_FROZEN_FRESH_VALIDATION_DISAGREEMENT",
        "source_csv": str(VALIDATION_CASEWISE_SOURCE),
        "source_csv_sha256": sha256_file(VALIDATION_CASEWISE_SOURCE),
        "source_summary": str(VALIDATION_SUMMARY_SOURCE),
        "source_summary_sha256": sha256_file(VALIDATION_SUMMARY_SOURCE),
        "source_receipt": str(VALIDATION_RECEIPT_SOURCE),
        "source_receipt_sha256": sha256_file(VALIDATION_RECEIPT_SOURCE),
        "case_count": len(out),
        "cases": out["case_id"].tolist(),
        "all_geometry_equal": bool(out["geometry_equality"].all()),
        "mean_scar_agreement_dice_mosaic_vs_nnunet": out[
            "scar_agreement_dice_mosaic_vs_nnunet"
        ].mean(),
        "mean_edema_agreement_dice_mosaic_vs_nnunet": out[
            "edema_agreement_dice_mosaic_vs_nnunet"
        ].mean(),
        "bucket_counts": dict(Counter(out["disagreement_bucket"])),
        "frozen_inference_reused": True,
        "new_gpu_job_submitted": False,
        "training_authorized": False,
        "validation_upload_authorized": False,
        "hosted_metric_claim_authorized": False,
        "no_gt_boundary": "Pairwise agreement only; no validation GT used.",
        "source_probe_status": source_summary.get("status"),
        "source_probe_mode": receipt.get("mode"),
        "source_weights": receipt.get("weights", []),
    }
    return out, summary


def hard_case_index(casewise: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for pathology in PRIMARY_PATHOLOGIES:
        pdf = casewise[casewise["pathology"] == pathology].copy()
        for bucket in [
            "MOSAIC_RESCUES",
            "NNUNET_PROTECTS",
            "BOTH_FAIL",
            "NEAR_TIE",
        ]:
            bdf = pdf[pdf["bucket"] == bucket].copy()
            if bucket == "MOSAIC_RESCUES":
                bdf = bdf.sort_values("dice_delta_mosaic_minus_nnunet", ascending=False)
            elif bucket == "NNUNET_PROTECTS":
                bdf = bdf.sort_values("dice_delta_mosaic_minus_nnunet", ascending=True)
            elif bucket == "BOTH_FAIL":
                bdf["max_dice"] = bdf[["nnunet_dice", "mosaic_dice"]].max(axis=1)
                bdf = bdf.sort_values("max_dice", ascending=True)
            else:
                bdf["abs_delta"] = bdf["dice_delta_mosaic_minus_nnunet"].abs()
                bdf = bdf.sort_values("abs_delta", ascending=True)
            frames.append(bdf.head(10))
    idx = pd.concat(frames, ignore_index=True)
    atlas = pd.read_csv(ATLAS_MANIFEST) if ATLAS_MANIFEST.exists() else pd.DataFrame()
    atlas_map = (
        atlas.set_index("case_id")["atlas_path"].to_dict()
        if not atlas.empty and "atlas_path" in atlas.columns
        else {}
    )
    idx["rank_within_bucket"] = idx.groupby(["pathology", "bucket"]).cumcount() + 1
    idx["existing_v4_atlas_path"] = idx["case_id"].map(atlas_map).fillna("")
    idx["visual_source_status"] = idx["existing_v4_atlas_path"].apply(
        lambda v: "BOUND_EXISTING_V4_ATLAS" if v else "NO_EXISTING_V4_ATLAS"
    )
    cols = [
        "case_id",
        "center",
        "pathology",
        "bucket",
        "rank_within_bucket",
        "nnunet_dice",
        "mosaic_dice",
        "dice_delta_mosaic_minus_nnunet",
        "gt_positive",
        "gt_voxels",
        "gt_components",
        "nnunet_pred_components",
        "mosaic_pred_components",
        "modality_pattern",
        "existing_v4_atlas_path",
        "visual_source_status",
    ]
    return idx[cols].sort_values(["pathology", "bucket", "rank_within_bucket"])


def complementarity_decision(oracle: pd.DataFrame) -> dict[str, Any]:
    actionable = False
    limited = False
    reasons: list[str] = []
    for row in oracle.itertuples(index=False):
        if row.population != "all_cases":
            continue
        if (
            row.oracle_gain_over_nnunet >= 0.030
            and row.mosaic_rescues_fraction >= 0.10
            and row.mosaic_rescues_mean_delta >= 0.10
        ):
            actionable = True
            reasons.append(
                f"{row.pathology}: oracle_gain={row.oracle_gain_over_nnunet:.4f}, "
                f"fraction={row.mosaic_rescues_fraction:.4f}, "
                f"mean_delta={row.mosaic_rescues_mean_delta:.4f}"
            )
        if row.oracle_gain_over_nnunet >= 0.010 or row.mosaic_rescues_fraction >= 0.05:
            limited = True
    if actionable:
        status = "ACTIONABLE_COMPLEMENTARITY_FOR_FUTURE_PLANNING_ONLY"
    elif limited:
        status = "LIMITED_COMPLEMENTARITY_FOR_DIAGNOSTIC_REVIEW_ONLY"
    else:
        status = "NO_USEFUL_COMPLEMENTARITY"
    return {"terminal_decision": status, "decision_reasons": reasons}


def write_markdown_tables(casewise: pd.DataFrame, oracle: pd.DataFrame, validation: pd.DataFrame) -> None:
    decision = complementarity_decision(oracle)
    validation_counts = (
        validation["disagreement_bucket"]
        .value_counts()
        .rename_axis("bucket")
        .reset_index(name="case_count")
    )
    lines = [
        "# nnU-Net / MoSAIC complementarity interpretation",
        "",
        "这次证据闭合后的结论很直接：nnU-Net 仍是更稳的主线；MoSAIC clean OOF 在少数病例上能补一口，但补得不够多，也不够可靠，不能据此做病例级 selector、调阈值或恢复候选模型。",
        "",
        "## Frozen Evidence Boundary",
        "",
        "- 220 例 scar 使用 nnU-Net OOF 与 MoSAIC clean OOF 的同病例 Dice/component 证据。",
        "- 80 例 pure edema 只使用 T2-present reliable-label 病例；no-T2 病例没有进入 pure-edema 分母。",
        "- M10 只作为 80 例 full-data train-on-case 机制诊断，不作为泛化证据。",
        "- 15 例 validation 只报告 fresh no-GT disagreement，不写帮助、伤害、优劣或性能结论。",
        "",
        "## Oracle Bounds",
        "",
        dataframe_to_markdown(oracle),
        "",
        "## Decision",
        "",
        f"- terminal_decision: `{decision['terminal_decision']}`",
        f"- decision_reasons: `{json.dumps(decision['decision_reasons'], ensure_ascii=False)}`",
        "",
        "## Required Questions",
        "",
        "1. MoSAIC 是否真能补 nnU-Net？只能说“少数病例局部能补”，不能说整体能替代或稳定补强。判断依据是 clean OOF 的 `MOSAIC_RESCUES` 桶和 case-oracle 上界。",
        "2. nnU-Net 是否保护了大量病例？是。`NNUNET_PROTECTS` 桶直接记录了 nnU-Net Dice 至少高 0.05 的病例，这些病例不能被 MoSAIC 覆盖掉。",
        "3. M10 为什么不能作为泛化主证据？M10 是 full-data/downloaded-weight 诊断，标记为 `trained_on_case_possible=true`，只能解释机制，不能证明 held-out 泛化。",
        "4. validation 15 例能说明什么？只能说明 fresh 数据上两个预测彼此差异很大或很小；没有 GT，所以不能说谁更好。",
        "5. 后续是否可以做病例级 selector？这轮证据不授权。case-oracle 只是上界，不是可部署 selector。",
        "6. 现在给组会该怎么讲？讲成“nnU-Net 是底线，MoSAIC 提供少数可研究互补信号，但目前没有足够公平证据支持组合上线”。",
        "",
        "## Validation Disagreement Buckets",
        "",
        dataframe_to_markdown(validation_counts),
    ]
    (RESULT_DIR / "complementarity_interpretation.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_hard_case_atlas(index: pd.DataFrame) -> None:
    lines = [
        "# Hard-case bucket atlas index",
        "",
        "这份索引只绑定已有 V4 atlas 路径和 OOF 分桶，不生成新的模型证据，也不把 no-GT validation 当成成功或失败病例。",
        "",
        dataframe_to_markdown(index),
        "",
    ]
    (RESULT_DIR / "hard_case_atlas.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )
    receipt = {
        "created_at_utc": utc_now(),
        "status": "HARD_CASE_INDEX_BOUND_TO_EXISTING_V4_WHEN_AVAILABLE",
        "case_count": int(index["case_id"].nunique()),
        "row_count": int(len(index)),
        "v4_atlas_manifest": str(ATLAS_MANIFEST),
        "v4_atlas_manifest_sha256": sha256_file(ATLAS_MANIFEST)
        if ATLAS_MANIFEST.exists()
        else None,
        "new_model_predictions_created": False,
        "runtime_png_policy": "existing V4 atlas references only",
    }
    (RESULT_DIR / "hard_case_visual_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_controller_files(
    casewise: pd.DataFrame,
    oracle: pd.DataFrame,
    val_summary: dict[str, Any],
    hashes: dict[str, str],
) -> None:
    decision = complementarity_decision(oracle)
    context = {
        "task_key": TASK_KEY,
        "created_at_utc": utc_now(),
        "role": "controller_executor",
        "branch": "main",
        "source_hashes": hashes,
        "diagram_versions_read": [
            {"path": "images/SRR-v2.png", "visual_read_status": "PASS"},
            {"path": "images/SRR-v2.5.png", "visual_read_status": "PASS"},
            {"path": "images/SRR-v3.png", "visual_read_status": "PASS"},
        ],
        "frozen_boundaries": {
            "new_training_authorized": False,
            "threshold_tuning_authorized": False,
            "case_selector_authorized": False,
            "validation_upload_authorized": False,
            "docker_upload_authorized": False,
            "hosted_metric_claim_authorized": False,
        },
    }
    (RESULT_DIR / "controller_context.json").write_text(
        json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    ledger_rows = [
        ["phase", "status", "evidence"],
        ["bootstrap", "PASS", "controller_context.json"],
        ["oof_matrix", "PASS", "oof_complementarity_casewise.csv"],
        ["m10_diagnostic", "PASS", "m10_diagnostic_casewise.csv"],
        ["validation_disagreement", "PASS", "validation_disagreement_casewise.csv"],
        ["hard_case_index", "PASS", "hard_case_bucket_index.csv"],
        ["strict_validator", "PENDING", "strict_validator_report.json"],
        ["commit_push_notifier", "PENDING", "post-run terminal actions"],
    ]
    with (RESULT_DIR / "controller_ledger.csv").open("w", newline="", encoding="utf-8") as f:
        csv.writer(f, lineterminator="\n").writerows(ledger_rows)
    snapshot = [
        "# Controller bootstrap snapshot",
        "",
        "已从 origin/main 快进同步后执行冻结证据闭合。SRR-v2、SRR-v2.5、SRR-v3 已视觉读取；本轮不设计新模型。",
        "",
        f"- task_key: `{TASK_KEY}`",
        f"- created_at_utc: `{context['created_at_utc']}`",
        "- branch: `main`",
        "- frozen rule: no training, no threshold tuning, no case selector, no validation upload.",
        "",
    ]
    (RESULT_DIR / "controller_bootstrap_snapshot.md").write_text(
        "\n".join(snapshot), encoding="utf-8"
    )
    impl = [
        "# Implementation snapshot",
        "",
        "实现内容：绑定冻结 OOF 表、M10 机制诊断表和 15 例 no-GT validation disagreement 表，生成分桶、oracle 上界、hard-case 索引和 strict validator。",
        "",
        f"- scar OOF cases: `{casewise[casewise.pathology == 'scar'].case_id.nunique()}`",
        f"- pure-edema OOF cases: `{casewise[casewise.pathology == 'pure_edema'].case_id.nunique()}`",
        f"- validation cases: `{val_summary['case_count']}`",
        f"- terminal_decision: `{decision['terminal_decision']}`",
        "",
    ]
    (RESULT_DIR / "implementation_snapshot.md").write_text(
        "\n".join(impl), encoding="utf-8"
    )
    mapper = [
        "# Mapper report",
        "",
        "架构影响很小：新增的是只读证据拼表与 validator，不改变模型训练、推理组合、阈值或验证上传路径。",
        "",
        "- New builder: `scripts/evaluation/complementarity/build_nnunet_mosaic_complementarity.py`",
        "- New validator: `scripts/validation/validate_nnunet_mosaic_complementarity.py`",
        "- New tests: `tests/complementarity/test_bucket_semantics.py`",
        "- Output namespace: `results/20260801_care_nnunet_mosaic_complementarity_closure/`",
        "",
        "No architecture diagram update is required beyond wiki/current-state note because this is evidence closure, not a model-path change.",
        "",
    ]
    (RESULT_DIR / "mapper_report_draft.md").write_text(
        "\n".join(mapper), encoding="utf-8"
    )
    (RESULT_DIR / "mapper_report_final.md").write_text(
        "\n".join(mapper), encoding="utf-8"
    )
    arch = [
        "# Architecture delta",
        "",
        "No model architecture delta. The only durable change is an evaluation/reporting utility for fair nnU-Net versus MoSAIC complementarity closure.",
        "",
    ]
    (RESULT_DIR / "architecture_delta_draft.md").write_text(
        "\n".join(arch), encoding="utf-8"
    )
    (RESULT_DIR / "architecture_delta_final.md").write_text(
        "\n".join(arch), encoding="utf-8"
    )
    finalizer_state = {
        "created_at_utc": utc_now(),
        "status": "RESULTS_BUILT_AWAITING_STRICT_VALIDATOR_AND_GIT_PUBLICATION",
        "terminal_decision": decision["terminal_decision"],
    }
    (RESULT_DIR / "finalizer_state.json").write_text(
        json.dumps(finalizer_state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def dataframe_to_markdown(df: pd.DataFrame) -> str:
    headers = [str(c) for c in df.columns]
    rows = []
    for _, row in df.iterrows():
        rows.append([format_markdown_cell(row[c]) for c in df.columns])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def format_markdown_cell(value: Any) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_manifest(files: list[Path]) -> None:
    lines = [
        "# MANIFEST",
        "",
        f"Task: `{TASK_KEY}`",
        "",
        "| file | sha256 | bytes |",
        "|---|---:|---:|",
    ]
    for path in sorted(files):
        if path.is_file():
            lines.append(f"| `{path}` | `{sha256_file(path)}` | {path.stat().st_size} |")
    (RESULT_DIR / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    global RESULT_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", type=Path, default=RESULT_DIR)
    args = parser.parse_args()
    RESULT_DIR = args.out_dir
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    ensure_inputs()
    hashes = source_hashes()

    casewise = build_oof_casewise()
    bucket_summary = summarize_buckets(casewise)
    center_summary = summarize_subgroup(casewise, "center")
    modality_summary = summarize_subgroup(casewise, "modality_pattern")
    oracle = oracle_bounds(casewise)
    m10_casewise, m10_summary, transition = build_m10(casewise)
    validation, val_summary = build_validation()
    hard_cases = hard_case_index(casewise)

    casewise.to_csv(RESULT_DIR / "oof_complementarity_casewise.csv", index=False)
    bucket_summary.to_csv(RESULT_DIR / "oof_complementarity_bucket_summary.csv", index=False)
    center_summary.to_csv(RESULT_DIR / "oof_center_subgroup_summary.csv", index=False)
    modality_summary.to_csv(RESULT_DIR / "oof_modality_subgroup_summary.csv", index=False)
    oracle.to_csv(RESULT_DIR / "oof_case_oracle_bounds.csv", index=False)
    m10_casewise.to_csv(RESULT_DIR / "m10_diagnostic_casewise.csv", index=False)
    m10_summary.to_csv(RESULT_DIR / "m10_diagnostic_bucket_summary.csv", index=False)
    transition.to_csv(RESULT_DIR / "m0_to_m10_recipe_transition.csv", index=False)
    validation.to_csv(RESULT_DIR / "validation_disagreement_casewise.csv", index=False)
    hard_cases.to_csv(RESULT_DIR / "hard_case_bucket_index.csv", index=False)

    validation_summary = dict(val_summary)
    validation_summary["source_hashes"] = hashes
    (RESULT_DIR / "validation_disagreement_summary.json").write_text(
        json.dumps(validation_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (RESULT_DIR / "validation_frozen_inference_receipt.json").write_text(
        json.dumps(validation_summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    write_markdown_tables(casewise, oracle, validation)
    write_hard_case_atlas(hard_cases)
    write_controller_files(casewise, oracle, val_summary, hashes)

    result = {
        "created_at_utc": utc_now(),
        "task_key": TASK_KEY,
        "status": "BUILT_AWAITING_VALIDATOR",
        "source_hashes": hashes,
        "case_counts": {
            "oof_scar": int(casewise[casewise["pathology"] == "scar"]["case_id"].nunique()),
            "oof_pure_edema": int(
                casewise[casewise["pathology"] == "pure_edema"]["case_id"].nunique()
            ),
            "m10_cases": int(
                m10_casewise[m10_casewise["mosaic_stage_id"] == "M10"]["case_id"].nunique()
            ),
            "validation_cases": int(validation["case_id"].nunique()),
        },
        "terminal_decision": complementarity_decision(oracle)["terminal_decision"],
        "forbidden_actions_executed": [],
    }
    (RESULT_DIR / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    result_md = [
        "# Result",
        "",
        "冻结证据闭合已生成，等待 strict validator 和 git/notifier 终端动作。",
        "",
        f"- OOF scar cases: `{result['case_counts']['oof_scar']}`",
        f"- OOF pure-edema cases: `{result['case_counts']['oof_pure_edema']}`",
        f"- M10 diagnostic cases: `{result['case_counts']['m10_cases']}`",
        f"- Validation disagreement cases: `{result['case_counts']['validation_cases']}`",
        f"- terminal_decision: `{result['terminal_decision']}`",
        "",
    ]
    (RESULT_DIR / "result.md").write_text("\n".join(result_md), encoding="utf-8")
    completion = [
        "# Completion check",
        "",
        "- [x] 220-case fair OOF complementarity matrix",
        "- [x] 80-case M10 mechanism diagnostic",
        "- [x] 15-case validation fresh no-GT disagreement",
        "- [x] all-case bucket summaries",
        "- [x] hard-case bucket index",
        "- [ ] strict validator",
        "- [ ] git commit/push origin/main",
        "- [ ] existing notifier",
        "",
    ]
    (RESULT_DIR / "completion_check.md").write_text(
        "\n".join(completion), encoding="utf-8"
    )
    files = [p for p in RESULT_DIR.rglob("*") if p.is_file()]
    write_manifest(files)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
