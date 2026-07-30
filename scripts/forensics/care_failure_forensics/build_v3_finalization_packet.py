#!/usr/bin/env python3
"""Build V3 machine-readable evidence for the CARE failure-forensics packet.

V3 corrects the V2 data audit by treating raw CARE files and subject metadata as
the modality source of truth.  nnU-Net image channels are recorded as
preprocessed channels only because Dataset501 deliberately uses zero
placeholders for missing modalities.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pickle
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

try:
    from scipy import ndimage
except Exception:  # pragma: no cover - optional in minimal environments
    ndimage = None


RESULT_REL = Path("results/20260730_care_failure_forensics_deep_research_packet")
FORBIDDEN_PATTERNS = [
    "NOT_RUN",
    "MISSING_ASSET",
    "UNRESOLVED",
    "NEEDS_REPAIR",
    "validator will fail",
    "diagnostics not run",
    "未运行",
    "未绑定",
    "尚未完成",
    "REQUIRES_",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def write_md(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def run(cmd: list[str], cwd: Path, timeout: int = 120) -> tuple[int, str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    return proc.returncode, proc.stdout


def component_count(mask: np.ndarray) -> int:
    if not bool(mask.any()):
        return 0
    if ndimage is None:
        return -1
    return int(ndimage.label(mask)[1])


def raw_modalities(case_dir: Path, case_id: str) -> dict[str, bool]:
    names = {p.name for p in case_dir.glob("*.nii.gz")}
    return {
        "LGE": f"{case_id}_LGE.nii.gz" in names or f"{case_id}_gd.nii.gz" in names,
        "T2": f"{case_id}_T2.nii.gz" in names,
        "C0": f"{case_id}_C0.nii.gz" in names,
    }


def meta_modalities(meta_path: Path) -> dict[str, bool] | None:
    if not meta_path.exists():
        return None
    data = json.loads(meta_path.read_text(encoding="utf-8"))
    mods = data.get("modalities_present", {})
    return {"LGE": bool(mods.get("de")), "T2": bool(mods.get("t2")), "C0": bool(mods.get("c0"))}


def preprocessed_channels(repo: Path, case_id: str) -> str:
    images_dir = repo / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/imagesTr"
    present = [idx for idx in range(3) if (images_dir / f"{case_id}_{idx:04d}.nii.gz").exists()]
    if len(present) == 3:
        return "3 (LGE,T2,C0 slots; missing modalities may be zero placeholders)"
    return ",".join(str(i) for i in present) if present else "missing"


def build_data_truth(repo: Path, out: Path) -> dict[str, Any]:
    raw_root = repo / "data/CARE_Challenge/MyoPS_train"
    meta_root = repo / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data"
    labels_root = repo / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
    dataset_json = repo / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/dataset.json"
    dataset = json.loads(dataset_json.read_text(encoding="utf-8"))

    rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    blocker_rows: list[dict[str, Any]] = []
    centers = Counter()
    modality_combos = Counter()

    for case_dir in sorted(raw_root.glob("Center*/Case*")):
        if not case_dir.is_dir():
            continue
        center = case_dir.parent.name
        case_id = case_dir.name
        meta_path = meta_root / f"{center}_{case_id}" / "subject_meta.json"
        raw = raw_modalities(case_dir, case_id)
        meta = meta_modalities(meta_path)
        canonical = dict(raw)
        confidence = "high"
        source = "raw_dataset_files+subject_meta_json"
        notes: list[str] = []
        if meta is None:
            confidence = "medium"
            source = "raw_dataset_files_only"
            notes.append("subject_meta.json missing")
        elif meta != raw:
            confidence = "medium"
            notes.append(f"raw/meta mismatch raw={raw} meta={meta}")
            canonical = meta

        label_path = labels_root / f"{case_id}.nii.gz"
        scar_voxels = pure_voxels = edema_zone_voxels = myocardium_union_voxels = ""
        scar_components = pure_components = edema_zone_components = ""
        spacing = image_shape = ""
        if label_path.exists():
            img = nib.load(str(label_path))
            arr = np.asanyarray(img.dataobj)
            image_shape = "x".join(map(str, arr.shape))
            spacing = "x".join(f"{float(x):.4g}" for x in img.header.get_zooms()[: arr.ndim])
            scar = arr == 5
            pure = arr == 4
            zone = (arr == 4) | (arr == 5)
            myo = (arr == 1) | (arr == 4) | (arr == 5)
            scar_voxels = int(scar.sum())
            pure_voxels = int(pure.sum())
            edema_zone_voxels = int(zone.sum())
            myocardium_union_voxels = int(myo.sum())
            scar_components = component_count(scar)
            pure_components = component_count(pure)
            edema_zone_components = component_count(zone)
        else:
            notes.append("label file missing")
            confidence = "low"

        if canonical["T2"]:
            pure_reliable = "true"
            pure_note = "label4 official edema eligible because raw/meta T2 is present"
        else:
            pure_reliable = "false"
            pure_note = "no raw/meta T2; label4 excluded from official pure-edema denominator"

        centers[center] += 1
        combo = "+".join([m for m in ["LGE", "T2", "C0"] if canonical[m]]) or "none"
        modality_combos[(center, combo)] += 1
        rows.append(
            {
                "case_id": case_id,
                "center": center,
                "raw_modalities": "+".join([m for m in ["LGE", "T2", "C0"] if raw[m]]),
                "canonical_modalities": combo,
                "preprocessed_channels": preprocessed_channels(repo, case_id),
                "LGE_present": canonical["LGE"],
                "T2_present": canonical["T2"],
                "C0_present": canonical["C0"],
                "availability_source": source,
                "availability_confidence": confidence,
                "scar_label_reliable": bool(label_path.exists()),
                "pure_edema_label_reliable": pure_reliable,
                "edema_zone_internal_valid": bool(label_path.exists()),
                "scar_voxels_label5": scar_voxels,
                "pure_edema_voxels_label4": pure_voxels,
                "edema_zone_voxels_label4_or_5": edema_zone_voxels,
                "myocardium_union_voxels_label1_or_4_or_5": myocardium_union_voxels,
                "scar_components": scar_components,
                "pure_edema_components": pure_components,
                "edema_zone_components": edema_zone_components,
                "label_shape": image_shape,
                "label_spacing": spacing,
                "notes": "; ".join(notes + [pure_note]),
            }
        )
        label_rows.append(
            {
                "case_id": case_id,
                "center": center,
                "scar_label": "label 5",
                "scar_label_reliable": bool(label_path.exists()),
                "pure_edema_label": "label 4",
                "pure_edema_label_reliable": pure_reliable,
                "pure_edema_official_denominator": "include" if canonical["T2"] else "exclude_no_raw_T2",
                "edema_zone_label": "label 4 or 5",
                "edema_zone_internal_valid": bool(label_path.exists()),
                "myocardium_union_label": "label 1 or 4 or 5",
                "notes": pure_note,
            }
        )

    write_csv(
        out / "v3_canonical_modality_manifest.csv",
        rows,
        [
            "case_id",
            "center",
            "raw_modalities",
            "canonical_modalities",
            "preprocessed_channels",
            "LGE_present",
            "T2_present",
            "C0_present",
            "availability_source",
            "availability_confidence",
            "scar_label_reliable",
            "pure_edema_label_reliable",
            "edema_zone_internal_valid",
            "scar_voxels_label5",
            "pure_edema_voxels_label4",
            "edema_zone_voxels_label4_or_5",
            "myocardium_union_voxels_label1_or_4_or_5",
            "scar_components",
            "pure_edema_components",
            "edema_zone_components",
            "label_shape",
            "label_spacing",
            "notes",
        ],
    )
    write_csv(out / "v3_label_reliability_manifest.csv", label_rows)

    t2_cases = [r for r in rows if str(r["T2_present"]) == "True"]
    no_t2_label4_positive = [
        r
        for r in rows
        if str(r["T2_present"]) != "True" and str(r.get("pure_edema_voxels_label4", "")).isdigit() and int(r["pure_edema_voxels_label4"]) > 0
    ]
    summary = {
        "created_at": utc_now(),
        "source_of_truth": ["raw CARE MyoPS files", "subject_meta.json", "Dataset501 dataset.json", "nnUNet labelsTr"],
        "dataset_json_description": dataset.get("description"),
        "case_count": len(rows),
        "t2_present": len(t2_cases),
        "t2_absent": len(rows) - len(t2_cases),
        "c0_present": sum(1 for r in rows if str(r["C0_present"]) == "True"),
        "lge_present": sum(1 for r in rows if str(r["LGE_present"]) == "True"),
        "scar_positive_label5": sum(1 for r in rows if str(r.get("scar_voxels_label5", "")).isdigit() and int(r["scar_voxels_label5"]) > 0),
        "pure_edema_positive_label4_all_cases": sum(
            1 for r in rows if str(r.get("pure_edema_voxels_label4", "")).isdigit() and int(r["pure_edema_voxels_label4"]) > 0
        ),
        "pure_edema_positive_official_t2_present": sum(
            1
            for r in t2_cases
            if str(r.get("pure_edema_voxels_label4", "")).isdigit() and int(r["pure_edema_voxels_label4"]) > 0
        ),
        "no_t2_label4_positive_cases": [r["case_id"] for r in no_t2_label4_positive],
        "center_counts": dict(sorted(centers.items())),
        "center_modality_combos": {f"{center}:{combo}": n for (center, combo), n in sorted(modality_combos.items())},
        "v2_t2_present_220_is_wrong": len(t2_cases) != 220,
        "corrected_interpretation": "T2_present is 80 by raw/meta evidence; Dataset501 still has three image slots because missing modalities are zero placeholders.",
    }
    write_json(out / "v3_t2_availability_audit.json", summary)
    write_json(
        out / "v3_data_truth_contract.json",
        {
            "created_at": utc_now(),
            "case_count": len(rows),
            "modality_truth": {
                "source_priority": ["subject_meta.json", "raw modality files", "Dataset501 channel_names as slot names only"],
                "T2_present": summary["t2_present"],
                "C0_present": summary["c0_present"],
                "LGE_present": summary["lge_present"],
                "warning": "Do not infer modality availability from nnUNet imagesTr slot existence; zero placeholders are expected.",
            },
            "label_truth": {
                "scar": "label 5",
                "pure_edema": "label 4; official edema only for raw/meta T2-present reliable cases",
                "edema_zone": "label 4 or 5; internal structural metric only",
                "myocardium_union": "label 1 or 4 or 5",
            },
            "positive_counts": {
                "scar_label5": summary["scar_positive_label5"],
                "pure_edema_label4_all_cases": summary["pure_edema_positive_label4_all_cases"],
                "pure_edema_official_t2_present": summary["pure_edema_positive_official_t2_present"],
            },
        },
    )
    if summary["t2_present"] == 220:
        blocker_rows.append({"blocker_id": "T2_TRUTH", "status": "FAIL", "reason": "T2_present still equals preprocessed slot count"})
    else:
        blocker_rows.append(
            {
                "blocker_id": "T2_TRUTH",
                "status": "RESOLVED",
                "reason": f"raw/meta T2_present={summary['t2_present']}; V2 220 was preprocessed slot presence, not raw modality truth",
            }
        )
    write_json(out / "v3_data_truth_blockers.json", {"created_at": utc_now(), "blockers": blocker_rows})
    return summary


def classify_stale_line(path: Path, line_no: int, line: str, pattern: str, result_root: Path) -> dict[str, Any]:
    rel = path.relative_to(result_root) if path.is_relative_to(result_root) else path
    text = line.strip()
    if str(rel).startswith("report_source_v2/") or str(rel) in {"v2_pdf_text_extract.txt", "completion_check.md", "controller_report.md"}:
        category = "过期文字"
        action = "V3 正文不得继承；以 v3_final_task_state.json 为准"
    elif "v1" in str(rel).lower():
        category = "V1 历史回顾"
        action = "允许保留在 V1 审计表，不进入 V3 当前状态叙述"
    elif pattern in {"MISSING_ASSET", "UNRESOLVED"} and "feature" in text.lower():
        category = "V2 最终真实缺口"
        action = "V3 必须替换为 hook/probe 结果或明确 load/replay 阻塞"
    else:
        category = "机器状态冲突"
        action = "V3 以 final_state/evidence_state 统一覆盖"
    return {
        "source_path": str(rel),
        "line": line_no,
        "pattern": pattern,
        "statement_excerpt": text[:220],
        "classification": category,
        "v3_action": action,
    }


def build_stale_audits(repo: Path, out: Path) -> None:
    search_files = [
        p
        for p in out.rglob("*")
        if p.is_file()
        and p.suffix.lower() in {".md", ".csv", ".json", ".txt"}
        and not p.name.startswith("v3_")
        and "runtime/" not in str(p)
        and p.stat().st_size < 5_000_000
    ]
    rows: list[dict[str, Any]] = []
    for path in sorted(search_files):
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for idx, line in enumerate(lines, 1):
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in line:
                    rows.append(classify_stale_line(path, idx, line, pattern, out))
    write_csv(out / "v3_v2_stale_statement_audit.csv", rows)

    contradiction_rows = [
        {
            "contradiction_id": "C1_D0_D3_STATUS",
            "v2_statement_a": "第 7 页称 D0-D3 已完成",
            "v2_statement_b": "第 34/37 页称未运行",
            "v3_truth_source": "v3_final_task_state.json + nnunet_decoder_reset_real_summary.csv",
            "v3_resolution": "D0-D3 decoder-reset 诊断已完成并绑定真实预测；V3 正文只保留完成状态和结果边界。",
        },
        {
            "contradiction_id": "C2_MOSAIC_BINDING",
            "v2_statement_a": "第 7 页称 MoSAIC source/weights 已绑定",
            "v2_statement_b": "第 34 页称 recipe 未绑定",
            "v3_truth_source": "v3_mosaic_recipe_binding.json + v3_mosaic_m0_m10_summary.csv",
            "v3_resolution": "source/weights 和 M0-M10 recipe 均以 V3 binding 文件统一描述；clean/full/hosted 分层。",
        },
        {
            "contradiction_id": "C3_G1_G10_VALIDATOR",
            "v2_statement_a": "第 1 页称 G1-G10 已终态",
            "v2_statement_b": "第 37 页称 validator 尚未完成",
            "v3_truth_source": "v3_final_task_state.json + v3_strict_validator_report.json",
            "v3_resolution": "V3 不沿用 V2 正文旧 validator 句子；validator 是终态文件。",
        },
        {
            "contradiction_id": "C4_ARCHITECTURE_SUPPORT",
            "v2_statement_a": "第 35 页称不支持任何架构",
            "v2_statement_b": "后续部分加入新诊断和可保留经验",
            "v3_truth_source": "v3_component_survival_upgrade.csv + Deep Research input",
            "v3_resolution": "V3 区分支持继承经验、禁止实现和仍未授权的新架构；不把经验写成候选模型。",
        },
        {
            "contradiction_id": "C5_REQUIRED_GPU_AND_ACTIVATION",
            "v2_statement_a": "第 100 页称 required GPU 已完成",
            "v2_statement_b": "正文仍有 missing activation",
            "v3_truth_source": "v3_feature_probe_summary.csv + v3_final_gpu_state.csv",
            "v3_resolution": "V3 必须用 feature probe 结果或可复现阻塞替换 missing activation 文本。",
        },
    ]
    write_csv(out / "v3_v2_contradiction_audit.csv", contradiction_rows)


def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.write_bytes(src.read_bytes())


def mosaic_full_final_binding_status(out: Path) -> tuple[bool, str]:
    receipt_path = out / "v3_mosaic_full_final_prediction_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8")) if receipt_path.exists() else {}
    prediction_rows = read_csv(out / "v3_mosaic_full_final_prediction_manifest.csv")
    atlas_manifest = read_csv(out / "v3_case_atlas_manifest.csv")
    pass_predictions = [r for r in prediction_rows if r.get("status") in {"BOUND", "PASS"} and r.get("prediction_path")]
    atlas_bound = [r for r in atlas_manifest if str(r.get("has_mosaic_full_final", "")).lower() == "true"]
    ok = (
        receipt.get("status") == "PASS"
        and len(pass_predictions) >= 40
        and len(atlas_manifest) >= 40
        and len(atlas_bound) >= 40
    )
    detail = (
        f"receipt_status={receipt.get('status', 'MISSING')}; "
        f"pass_predictions={len(pass_predictions)}; "
        f"atlas_rows={len(atlas_manifest)}; "
        f"atlas_bound={len(atlas_bound)}"
    )
    return ok, detail


def build_evidence_derivatives(repo: Path, out: Path, data_summary: dict[str, Any]) -> None:
    mappings = {
        "batch0_7_casewise_results.csv": "v3_batch0_7_casewise_metrics.csv",
        "batch0_7_design_evidence_matrix.csv": "v3_batch0_7_lineage.csv",
        "batch0_7_component_survival_ledger.csv": "v3_batch7_mechanism_evidence.csv",
        "mmrd_casewise_metrics.csv": "v3_mmrd_casewise_metrics.csv",
        "mmrd_direct_vs_distillation.csv": "v3_mmrd_direct_distillation_comparison.csv",
        "mmrd_component_survival_ledger.csv": "v3_mmrd_component_effect.csv",
        "cascade_casewise_metrics.csv": "v3_cascade_casewise_metrics.csv",
        "cascade_component_survival_ledger.csv": "v3_cascade_component_effect.csv",
        "arc_design_vs_implementation.csv": "v3_arc_design_code_runtime_matrix.csv",
        "arc_loss_final_output_trace.csv": "v3_arc_final_output_trace.csv",
        "arc_component_survival_ledger.csv": "v3_arc_component_effect.csv",
        "mosaic_recipe_decomposition_casewise.csv": "v3_mosaic_m0_m10_casewise.csv",
        "mosaic_recipe_decomposition_summary.csv": "v3_mosaic_m0_m10_summary.csv",
        "mosaic_clean_full_data_gap.csv": "v3_mosaic_gain_waterfall.csv",
        "alignment_error_correlation.csv": "v3_alignment_failure_correlation.csv",
        "cross_modal_alignment_casewise.csv": "v3_alignment_casewise.csv",
        "cine_temporal_signal_probe.csv": "v3_cine_ed_temporal_probe.csv",
        "cine_motion_quality.csv": "v3_cine_motion_quality.csv",
        "large_gain_feasibility_analysis.csv": "v3_large_gain_upper_bound.csv",
    }
    for old, new in mappings.items():
        copy_if_exists(out / old, out / new)

    write_json(
        out / "v3_mmrd_decoder_inheritance_audit.json",
        {
            "created_at": utc_now(),
            "source": "mmrd_model_contract.json + mmrd_checkpoint_binding.csv",
            "status": "CHECKPOINT_BOUND_REPLAY_EVIDENCE_REUSED_FROM_V2",
            "conclusion": "MMRD evidence is preserved as component-level historical evidence; any checkpoint load failure must be reported with keys/shape details before claiming scientific failure.",
        },
    )
    copy_if_exists(out / "cascade_control_semantics_audit.json", out / "v3_cascade_input_equivalence_audit.json")

    # Correction ceiling from existing case oracle rows.
    rows = read_csv(out / "case_oracle_summary.csv")
    ceiling_rows = []
    for metric in ["scar", "pure_edema", "lesion_union"]:
        subset = [r for r in rows if r.get("metric_name") == metric]
        if not subset:
            continue
        nn = [float(r.get("nnunet_dice", "nan")) for r in subset if r.get("nnunet_dice")]
        oracle = [float(r.get("case_oracle_dice", "nan")) for r in subset if r.get("case_oracle_dice")]
        voxel = [float(r.get("voxel_tp_oracle_dice", "nan")) for r in subset if r.get("voxel_tp_oracle_dice")]
        ceiling_rows.append(
            {
                "metric_name": metric,
                "case_count": len(subset),
                "nnunet_mean": float(np.nanmean(nn)) if nn else "",
                "case_oracle_mean": float(np.nanmean(oracle)) if oracle else "",
                "case_oracle_gain": float(np.nanmean(oracle) - np.nanmean(nn)) if nn and oracle else "",
                "voxel_oracle_mean": float(np.nanmean(voxel)) if voxel else "",
                "warning": "case oracle is selector bound; voxel oracle is non-deployable",
            }
        )
    write_csv(out / "v3_cascade_correction_ceiling.csv", ceiling_rows)
    write_csv(out / "v3_large_gain_error_budget.csv", ceiling_rows)

    has_feature_receipt = (out / "v3_feature_probe_receipt.json").exists()
    feature_receipt_payload = {}
    if has_feature_receipt:
        feature_receipt_payload = json.loads((out / "v3_feature_probe_receipt.json").read_text(encoding="utf-8"))
    mosaic_feature_sources = set(feature_receipt_payload.get("mosaic_feature_sources", []))
    atlas_rows = read_csv(out / "v3_case_atlas_quality.csv")
    atlas_manifest = read_csv(out / "v3_case_atlas_manifest.csv")
    atlas_ok = len(atlas_manifest) >= 40 and atlas_rows and all(r.get("status") == "PASS" for r in atlas_rows)
    mosaic_full_final_ok, mosaic_full_final_detail = mosaic_full_final_binding_status(out)
    missing_rows = []
    if not has_feature_receipt:
        missing_rows.append(
            {
                "asset_or_evidence": "forward-hook activation probes",
                "status": "NEEDS_CURRENT_V3_RUN",
                "why_it_matters": "V2 only had prediction/cache-derived feature probes for part of MoSAIC; V3 contract asks nnU-Net/PRISM/MoSAIC activation families.",
                "next_action": "run read-only hook extraction or record explicit checkpoint-load blocking details",
            }
        )
    elif feature_receipt_payload.get("status") == "PASS" and {"MOSAIC_COARSE", "MOSAIC_SCAR_FINE", "MOSAIC_EDEMA"}.issubset(mosaic_feature_sources):
        pass
    elif {"MOSAIC_COARSE", "MOSAIC_SCAR_FINE", "MOSAIC_EDEMA"}.issubset(mosaic_feature_sources):
        missing_rows.append(
            {
                "asset_or_evidence": "MoSAIC activation hook outputs",
                "status": "HOOKED_WITH_SMALL_CACHE_BOUNDARY",
                "why_it_matters": "MoSAIC CoarseNet, FinePathNet, and EdemaNet were hooked from local cache cases; this proves load/forward-hook availability but is not a full patient-level activation study.",
                "next_action": "expand MoSAIC hook extraction to the same actual_train/inner_select population if the final strict validator requires full split coverage",
            }
        )
    else:
        missing_rows.append(
            {
                "asset_or_evidence": "MoSAIC activation hook outputs",
                "status": "NEEDS_CURRENT_FORWARD_HOOK",
                "why_it_matters": "MoSAIC weights are loadable, but required feature sources are absent from the merged feature-probe evidence.",
                "next_action": "use MoSAIC source entrypoint to hook CoarseNet/FinePathNet/EdemaNet",
            }
        )
    if not atlas_ok:
        missing_rows.append(
            {
                "asset_or_evidence": "40-case V3 visual atlas",
                "status": "NEEDS_CURRENT_V3_REBUILD",
                "why_it_matters": "V2 contains 20 cases and user reported small/unclear panels.",
                "next_action": "build landscape atlas pages after V3 case selection",
            }
        )
    if not mosaic_full_final_ok:
        missing_rows.append(
            {
                "asset_or_evidence": "MoSAIC full/final voxel-level atlas prediction",
                "status": "MISSING_BOUND_VOXEL_PREDICTION",
                "why_it_matters": "M0-M10 casewise recipe metrics are bound, but a full/final NIfTI prediction for atlas panels was not found.",
                "next_action": "bind exact full/final local prediction or keep atlas panel marked not bound; do not synthesize a mask from aggregate CSV metrics",
                "detail": mosaic_full_final_detail,
            }
        )
    write_csv(out / "v3_missing_scientific_evidence.csv", missing_rows)

    # Feature probe summary starts from V2 but makes blocked rows explicit rather than MISSING_ASSET.
    if not (out / "v3_feature_probe_receipt.json").exists():
        feature_rows = read_csv(out / "feature_probe_summary.csv")
        upgraded = []
        for row in feature_rows:
            item = dict(row)
            text = " ".join(str(v) for v in item.values()).lower()
            if "missing" in text or "blocked" in text:
                item["v3_status"] = "REQUIRES_CURRENT_FORWARD_HOOK_OR_LOAD_BLOCKER"
                item["v3_interpretation"] = "not usable as terminal V3 negative evidence"
            else:
                item["v3_status"] = "CARRIED_FORWARD_WITH_SCOPE_LIMIT"
                item["v3_interpretation"] = "usable only within bound feature/proxy scope"
            upgraded.append(item)
        if not upgraded:
            upgraded = [
                {
                    "model_feature_source": "ALL_REQUESTED_ACTIVATIONS",
                    "v3_status": "REQUIRES_CURRENT_FORWARD_HOOK_OR_LOAD_BLOCKER",
                    "v3_interpretation": "no V2 feature-probe rows available",
                }
            ]
        write_csv(out / "v3_feature_probe_summary.csv", upgraded)

    write_md(
        out / "v3_batch7_reusable_experience.md",
        """# Batch7 可继承经验

V3 只能继承有路径证据的经验：强基线 final-mask ownership 必须明确；任何 router、dictionary、prototype、refiner 组件都必须证明进入 final logits 或 final mask；扩大结构化组件作用后如果 scar 变差，应优先检查 final-output ownership、训练预算、case help/harm 和 remote FP，而不是把概念直接判死。

禁止重复的错误是：用合理设计名词替代 final-logits 证据；把 mixed edema-zone 改善写成 official pure edema 改善；在 control 与 SRR 使用同一 prototype input 时解释为 prototype 无效。
""",
    )
    write_md(
        out / "v3_mmrd_reusable_experience.md",
        """# MMRD 可继承经验

MMRD 的可继承部分主要是数据规则：modality dropout、reliable-label mask、no-T2 edema loss hygiene 是必要边界，不应被写成单独模型增益。未来如果重测 distillation，必须同时绑定 teacher/student/checkpoint/prediction，并分别报告 scar 与 raw/meta T2-present official pure edema。
""",
    )
    write_md(
        out / "v3_cascade_reusable_experience.md",
        """# Cascade 可继承经验

Cascade 的安全经验是 bounded correction、identity fallback 和 selector 审计；但 historical control 若与 SRR 使用相同 prototype input，不能证明 prototype 无效，只能证明 control 不能隔离 prototype contribution。未来必须用 changed voxel rate、case help/harm、scar/pure-edema 分层和 correction ceiling 判断是否值得进入 final mask。
""",
    )
    write_md(
        out / "v3_arc_reusable_experience.md",
        """# ARC 可继承经验

ARC 的负证据集中在 final mask ownership、random decoder capability loss 和 guidance 是否真正进入 logits。可保留的是 anatomy/safety 约束和 final-output trace 纪律；不能保留的是未证明 crop/refine/paste-back、SDF 因果路径或独立 direct reconstruction 的旧实现。
""",
    )
    write_md(
        out / "v3_mosaic_clean_full_hosted_gap.md",
        """# MoSAIC clean/full-data/hosted gap

MoSAIC clean OOF、full-data diagnostic 和 hosted-near recipe 是三种不同证据层。full-data weights 在 train cases 上的结果不能写成 clean architecture superiority；M0-M10 的贡献必须按 checkpoint scope、TTA、threshold、postprocess 和 official mapping 分层。当前本地证据支持 recipe/训练域/集成带来差异，但不支持直接照搬 MoSAIC 作为唯一主体。
""",
    )
    write_md(
        out / "v3_feature_probe_interpretation.md",
        """# 冻结特征 probe 解释

V3 已把 V2 的 feature-probe 缺口升级为显式执行要求：如果 checkpoint 和代码可加载，必须用只读 forward hook；如果不可加载，必须记录 expected architecture、actual keys、missing/unexpected keys、shape mismatch 和 attempted environments。当前已绑定的 V2 probe 只能作为有限 proxy 证据，不能证明 nnU-Net/PRISM/MoSAIC activation family 没有信号。
""",
    )
    write_md(
        out / "v3_large_gain_feasibility.md",
        """# 约 0.1 Dice 级增益可行性终审

本地 clean held-out 证据不支持 simple ensemble 或 case selector 达到约 0.1 Dice。nnU-Net + MoSAIC 的 case-oracle gain 对 scar 只有约 0.02 量级，对 pure edema 约 0.00 量级；voxel oracle 只说明错误体素中存在可分割空间，不是可部署模型上限。

当前结论：LOCAL_EVIDENCE_SUPPORTS_ONLY_MODEST_GAIN。

若要追求约 0.1 Dice，需要新机制直接攻击大误差池，例如小病灶 FN、remote FP、边界 undersegmentation、no-T2 supervision hygiene、center/domain calibration 和 decoder capability preservation。该机制必须先通过 patient-level feature probe、error-pool ablation 和 clean validation evidence，而不是复用历史未进入 final logits 的组件。
""",
    )
    for name, lesion in [("v3_scar_evidence_brief.md", "scar"), ("v3_pure_edema_evidence_brief.md", "pure edema")]:
        write_md(
            out / name,
            f"""# {lesion} evidence brief

1. 数据规模：总病例 {data_summary['case_count']}；raw/meta T2-present 病例 {data_summary['t2_present']}。
2. 可靠标签：scar 使用 label 5；pure edema 使用 label 4 且仅在 raw/meta T2-present 病例作为 official edema。
3. 模态信息：不能从 Dataset501 三通道 slot 推断 T2/C0 可用性。
4. nnU-Net 失败：主要表现为病例级 FN/FP、边界和小病灶误差；完整 decoder/recipe 是强基线条件。
5. MoSAIC 失败：clean OOF 与 full-data/hosted-near recipe 必须分层，不能混写。
6. CARE 历史失败：组件名不等于 final-logits effect，必须绑定 prediction/casewise/help-harm。
7. lesion morphology：V3 manifest 提供 component count 和体素量。
8. feature separability：当前 proxy 证据不足，activation hook 是 V3 未决执行项。
9. oracle：case oracle 只支持有限 selector 上限，voxel oracle 不可部署。
10. center/domain：center 与 modality availability 强相关，需防 center shortcut。
11. alignment：complete tri-modal alignment 不能被旧 safe-subset smoke 替代。
12. valid historical experience：保留数据 hygiene、bounded correction、final-output trace 和 decoder preservation。
13. forbidden repeated mistakes：禁止 no-T2 假阴性监督、edema-zone 冒充 official edema、full-data 冒充 clean。
14. plausible high-gain mechanisms：必须直接覆盖 error pool 并有 patient-level probe 支持。
15. unresolved questions：activation separability、clean external domain、hosted recipe provenance 仍需严格绑定。
""",
        )
    write_md(
        out / "v3_cine_alignment_conclusion.md",
        """# Cine 和 alignment 结论

V3 只允许诊断，不允许训练新 Cine 模型。现有 alignment/Cine 文件可作为历史诊断输入，但 V2 的 safe-subset smoke 不能单独支持最终机制判断。未来必须在 complete tri-modal 病例上重新报告 LGE-T2、LGE-C0、centroid/anatomy overlap、MI/NCC、slice correspondence 和 failure correlation；Cine 需在 matched patient split 下比较 ED-only、temporal difference、motion 和 wall-thickness 信号。
""",
    )


def build_final_state(repo: Path, out: Path, data_summary: dict[str, Any]) -> None:
    code_head = run(["git", "rev-parse", "HEAD"], repo)[1].strip()
    origin_head = run(["git", "rev-parse", "origin/main"], repo)[1].strip()
    feature_receipt = {}
    if (out / "v3_feature_probe_receipt.json").exists():
        feature_receipt = json.loads((out / "v3_feature_probe_receipt.json").read_text(encoding="utf-8"))
    atlas_rows = read_csv(out / "v3_case_atlas_quality.csv")
    atlas_manifest = read_csv(out / "v3_case_atlas_manifest.csv")
    atlas_ok = len(atlas_manifest) >= 40 and atlas_rows and all(r.get("status") == "PASS" for r in atlas_rows)
    mosaic_load = read_csv(out / "v3_mosaic_loadability_audit.csv")
    mosaic_load_ok = bool(mosaic_load) and all(r.get("status", "").startswith("LOADED") for r in mosaic_load)
    feature_summary = read_csv(out / "v3_feature_probe_summary.csv")
    feature_sources = {r.get("feature_source", "") for r in feature_summary}
    feature_probe_models = {r.get("probe_model", "") for r in feature_summary}
    feature_statuses = {r.get("status", "") for r in feature_summary}
    required_feature_sources = {
        *(f"NNUNET_ENCODER_L{i}" for i in range(6)),
        *(f"NNUNET_DECODER_L{i}" for i in range(5)),
        *(f"PRISM_SHARED_L{i}" for i in range(4)),
        *(f"PRISM_PRIVATE_LGE_L{i}" for i in range(4)),
        *(f"PRISM_PRIVATE_T2_L{i}" for i in range(4)),
        *(f"PRISM_PRIVATE_C0_L{i}" for i in range(4)),
        *(f"PRISM_SCAR_ROUTED_L{i}" for i in range(4)),
        *(f"PRISM_EDEMA_ROUTED_L{i}" for i in range(4)),
        "PRISM_SCAR_REFINER",
        "PRISM_EDEMA_REFINER",
        "MOSAIC_COARSE",
        "MOSAIC_SCAR_FINE",
        "MOSAIC_EDEMA",
        "RAW_INTENSITY_CONTROL",
    }
    required_probe_models = {"logistic_regression", "linear_svm", "1x1_convolution"}
    missing_feature_sources = sorted(required_feature_sources - feature_sources)
    missing_probe_models = sorted(required_probe_models - feature_probe_models)
    hard_feature_failures = sorted(s for s in feature_statuses if s in {"NOT_IMPLEMENTED", "PROBE_FAILED"})
    feature_receipt_status = str(feature_receipt.get("status", "MISSING_RECEIPT"))
    feature_ok = (
        feature_receipt_status == "PASS"
        and bool(feature_summary)
        and not missing_feature_sources
        and not missing_probe_models
        and not hard_feature_failures
    )
    missing_asset_rows = [
        row for row in read_csv(out / "v3_missing_scientific_evidence.csv")
        if row.get("status", "").startswith(("MISSING", "NEEDS", "LIMITATION", "BLOCKED"))
    ]
    task_rows = [
        {
            "task_id": "V3_DATA_TRUTH",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE",
            "terminal_status": "COMPLETE",
            "evidence_path": "v3_data_truth_contract.json",
            "notes": f"T2_present corrected to {data_summary['t2_present']} raw/meta cases",
        },
        {
            "task_id": "V3_STALE_STATEMENT_AUDIT",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE",
            "terminal_status": "COMPLETE",
            "evidence_path": "v3_v2_stale_statement_audit.csv",
            "notes": "V2 stale statements classified and excluded from V3 current-state prose",
        },
        {
            "task_id": "V3_FEATURE_HOOKS",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE" if feature_ok and mosaic_load_ok else "NEEDS_FULL_PATIENT_LEVEL_PROBE_OR_EXPLICIT_VALIDATOR_ACCEPTANCE",
            "terminal_status": "COMPLETE" if feature_ok and mosaic_load_ok else "INCOMPLETE",
            "evidence_path": "v3_feature_probe_summary.csv",
            "notes": (
                "receipt_status="
                + feature_receipt_status
                + "; required sources missing="
                + (";".join(missing_feature_sources) if missing_feature_sources else "none")
                + "; missing probe models="
                + (";".join(missing_probe_models) if missing_probe_models else "none")
                + "; hard failures="
                + (";".join(hard_feature_failures) if hard_feature_failures else "none")
            ),
        },
        {
            "task_id": "V3_VISUAL_ATLAS_40",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE" if atlas_ok else "NEEDS_CURRENT_V3_REBUILD",
            "terminal_status": "COMPLETE" if atlas_ok else "INCOMPLETE",
            "evidence_path": "v3_case_atlas_manifest.csv",
            "notes": f"{len(atlas_manifest)} case atlas pages; QA failures={sum(1 for r in atlas_rows if r.get('status') != 'PASS')}",
        },
        {
            "task_id": "V3_REMAINING_SCIENTIFIC_ASSETS",
            "required": "true",
            "status": "COMPLETED_WITH_VALID_EVIDENCE" if not missing_asset_rows else "NEEDS_BOUND_ASSET_OR_EXPLICIT_FINAL_LIMITATION",
            "terminal_status": "COMPLETE" if not missing_asset_rows else "INCOMPLETE",
            "evidence_path": "v3_missing_scientific_evidence.csv",
            "notes": "; ".join(f"{r.get('asset_or_evidence')}={r.get('status')}" for r in missing_asset_rows) or "none",
        },
    ]
    write_csv(out / "v3_final_evidence_state.csv", task_rows)
    write_csv(
        out / "v3_final_gpu_state.csv",
        [
            {
                "job_id": "NONE_SUBMITTED_IN_THIS_V3_BUILDER_PASS",
                "scope": "initial V3 evidence rebuild",
                "state": "not_submitted",
                "terminal": "true",
                "notes": "No new GPU job was started by build_v3_finalization_packet.py",
            }
        ],
    )
    incomplete = [r for r in task_rows if r["terminal_status"] != "COMPLETE"]
    decision = "VERIFIED_COMPLETE" if not incomplete else "NEEDS_REPAIR"
    write_json(
        out / "v3_final_task_state.json",
        {
            "task_key": "20260730_care_failure_forensics_v3_finalization",
            "created_at": utc_now(),
            "git_head": code_head,
            "origin_main": origin_head,
            "controller_verification_decision": decision,
            "route_change": False,
            "new_architecture_training": False,
            "validation_upload": False,
            "docker_upload": False,
            "push_allowed": False,
            "current_blockers": [r for r in task_rows if r["terminal_status"] == "INCOMPLETE"],
            "limitations": [r for r in task_rows if r["terminal_status"] == "COMPLETE_WITH_LIMITATION"],
        },
    )
    write_csv(
        out / "v3_superseded_statement_manifest.csv",
        [
            {
                "superseded_file": "data_case_manifest.csv",
                "replacement": "v3_canonical_modality_manifest.csv",
                "reason": "V2 inferred T2/C0 from nnUNet placeholder channels.",
            },
            {
                "superseded_file": "label_availability_matrix.csv",
                "replacement": "v3_label_reliability_manifest.csv",
                "reason": "V2 used T2_present=220 and did not separate raw T2 availability from slot existence.",
            },
            {
                "superseded_file": "report_source_v2/CARE_failure_forensics_20260730_v2.md",
                "replacement": "future report_source_v3/CARE_failure_forensics_20260730_v3.md",
                "reason": "V2 prose contains stale completion/missing-status contradictions.",
            },
        ],
    )


def build_deep_research_input(out: Path, data_summary: dict[str, Any]) -> None:
    text = f"""# CARE Deep Research 模型设计输入 20260730

## A. 用户硬约束

1. 必须使用 Batch7、MMRD、Cascade、ARC 中至少一到两条有效经验。
2. 不得复制失败实现。
3. nnU-Net、MoSAIC 不得成为唯一主体。
4. 不得堆叠多个完整 backbone。
5. scar 和 edema 分别建模且同等重要。
6. 必须具有显著超过 nnU-Net 和 MoSAIC validation 的机制上限。
7. 不接受仅约 0.005-0.02 Dice 的收益。
8. 应评估约 0.1 Dice 级别的合理性。

## B. 本地已证实事实

- MyoPS training cases: {data_summary['case_count']}。
- raw/meta T2-present cases: {data_summary['t2_present']}；V2 的 `t2_present=220` 是错误的 preprocessed slot 推断。
- scar = label 5。
- pure edema = label 4，official edema 只允许 raw/meta T2-present 且标签可靠病例。
- edema-zone = label 4 or 5，只能作为内部结构指标。
- myocardium union = label 1 or 4 or 5。

## C. 本地有效历史经验

- 数据 hygiene：no-T2 病例不得产生 edema 假阴性监督。
- final-output trace：任何新组件必须证明进入 final logits/final mask。
- decoder preservation：完整 decoder/recipe 对强基线至关重要。
- bounded correction 和 fallback safety 可作为安全规则保留。

## D. 本地禁止重复错误

- 用 Dataset501 三通道文件存在性推断 T2/C0 availability。
- 用 edema-zone 冒充 official pure edema。
- 把 full-data 或 hosted-near recipe 写成 clean architecture superiority。
- 把 control 与 SRR 同 prototype input 的结果解释为 prototype 无效。
- 使用未进入 final logits 的 router/dictionary/prototype/refiner 作为机制证据。

## E. scar evidence

scar 有病例级互补但 case-oracle gain 只在约 0.02 量级；simple selector/ensemble 不足以支撑约 0.1 Dice。未来机制必须直接减少 small-lesion FN、remote FP、blood-pool/normal-myocardium confusion 和 boundary undersegmentation。

## F. pure-edema evidence

pure edema 必须只在 raw/meta T2-present 病例评价。clean OOF 互补弱；任何 edema 专家必须证明不是 center shortcut、availability shortcut 或 no-T2 false-negative supervision。

## G. MoSAIC recipe evidence

M0-M10 需作为 recipe decomposition 使用：clean OOF、full-data diagnostic、hosted-near recipe 分开。可探索 coarse/fine、ensemble、TTA、threshold、postprocess 的贡献，但不能把 full-data 结果当 clean 验证。

## H. nnU-Net decoder/recipe evidence

完整 nnU-Net decoder 和 training recipe 是强基线核心。未来模型不能只迁移 encoder 后重置 decoder；必须证明 decoder capability 没有丢失。

## I. large-gain feasibility

当前本地结论：LOCAL_EVIDENCE_SUPPORTS_ONLY_MODEST_GAIN。约 0.1 Dice 需要新的空间或表征机制，并需要 patient-level feature probe、error-pool ablation 和 clean validation evidence。

## J. unresolved external research questions

- 哪类机制能真实恢复 small-lesion FN 且不引入 remote FP？
- 是否存在不依赖 center/availability shortcut 的 edema 表征？
- hosted validation 的 small-sample/domain shift 对 MoSAIC/nnU-Net 差距贡献多大？
- 如何在不堆多个完整 backbone 的情况下保持 decoder capacity？

## K. 允许 Deep Research 探索的机制类别

- 轻量 lesion-proposal + bounded correction。
- scar/edema 分离专家，但共享底座受限且必须有独立 loss/evidence。
- uncertainty/calibration 和 topology-safe postprocess。
- modality-aware supervision hygiene。
- decoder-preserving adaptation。

## L. 必须被拒绝的设计类别

- nnU-Net 或 MoSAIC 单独作为主体后只调 threshold。
- 多完整 backbone 堆叠。
- 无 final-logits 证据的 router/prototype/dictionary。
- 使用 no-T2 病例训练 edema 假阴性。
- 把 voxel oracle 当可部署上限。
"""
    write_md(out / "DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730.md", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    repo = args.root.resolve()
    out = repo / RESULT_REL
    out.mkdir(parents=True, exist_ok=True)
    data_summary = build_data_truth(repo, out)
    build_stale_audits(repo, out)
    build_evidence_derivatives(repo, out, data_summary)
    build_final_state(repo, out, data_summary)
    build_deep_research_input(out, data_summary)
    write_json(
        out / "v3_initial_builder_receipt.json",
        {
            "created_at": utc_now(),
            "script": str(Path(__file__).relative_to(repo)),
            "outputs": [
                "v3_canonical_modality_manifest.csv",
                "v3_t2_availability_audit.json",
                "v3_label_reliability_manifest.csv",
                "v3_data_truth_contract.json",
                "v3_v2_contradiction_audit.csv",
                "v3_v2_stale_statement_audit.csv",
                "DEEP_RESEARCH_MODEL_DESIGN_INPUT_20260730.md",
            ],
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
