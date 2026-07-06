#!/usr/bin/env python3
"""Generate the SRR-v3 M5 Cine secondary diagnostic contract packet.

This is an evidence aggregation task only. It reads prior Cine diagnostic
Markdown/CSV/JSON artifacts and writes a compact review packet for M5.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean


REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_KEY = "20260705_srr_v3_m5_cine_secondary_contract"
TASK_PATH = f"prompts/tasks/{TASK_KEY}.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / TASK_KEY


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def f(value: object) -> float | None:
    try:
        val = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return val


def fmt(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def mean_float(rows: list[dict[str, str]], key: str) -> float | None:
    vals = [f(row.get(key)) for row in rows]
    vals = [v for v in vals if v is not None]
    return mean(vals) if vals else None


def first(rows: list[dict[str, str]], key: str) -> str:
    for row in rows:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def build_registration_matrix() -> list[dict[str, object]]:
    syn_summary = read_json(REPO_ROOT / "results/20260704_cine_full_cinema_registration/syn_probe_summary.json")
    syn_rows = read_csv(REPO_ROOT / "results/20260704_cine_full_cinema_registration/syn_voxelmorph_probe.csv")
    vxm_summary = read_json(REPO_ROOT / "results/20260704_cine_full_cinema_registration/voxelmorph_adapter_probe_summary.json")
    vxm_rows = read_csv(REPO_ROOT / "results/20260704_cine_full_cinema_registration/voxelmorph_adapter_probe.csv")
    demons_summary = read_csv(REPO_ROOT / "results/20260704_cine_temporal_motion_resume/simpleitk_demons_summary.csv")
    flow_summary = read_csv(REPO_ROOT / "results/20260703_cine_motion/motion_or_warp_summary.csv")
    safe_cases = read_csv(REPO_ROOT / "results/20260703_cine_motion/safe_cases_used.csv")
    cinema_summary = read_json(
        REPO_ROOT / "results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics_summary.json"
    )
    cinema_metrics = read_csv(REPO_ROOT / "results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv")
    frame0_train = [
        row
        for row in cinema_metrics
        if row.get("split") == "train" and str(row.get("frame_index", "")) in {"0", "0.0"}
    ]
    frame0_myo_mean = mean_float(frame0_train, "myocardium_dice")
    frame0_lv_mean = mean_float(frame0_train, "lv_dice")

    safe_case_count = len({row.get("case_id", "") for row in safe_cases if row.get("case_id")})
    strict_safe_count = sum(str(row.get("strict_frame0_label_metadata_match", "")).lower() == "true" for row in safe_cases)

    return [
        {
            "method": "frame0_control_cinema_anatomy_prior",
            "transform_family": "none",
            "same_safe_subset_case_count": safe_case_count,
            "source_case_count": int(cinema_summary.get("train_cases", 0) or 0),
            "case_scope": "CineMA frame0 anatomy metrics over train set; safe subset available from prior motion run",
            "fixed_frame": 0,
            "moving_frame": "",
            "image_ncc_before_mean": "",
            "image_ncc_after_mean": "",
            "myocardium_before_or_reference": fmt(frame0_myo_mean),
            "myocardium_after_or_warped": fmt(frame0_myo_mean),
            "lv_before_or_reference": fmt(frame0_lv_mean),
            "lv_after_or_warped": fmt(frame0_lv_mean),
            "folding_or_jacobian": "not_applicable_control",
            "runtime_seconds_mean": fmt(cinema_summary.get("elapsed_sec")),
            "evidence_path": "results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv",
            "gate_status": "CONTROL_ONLY_NOT_REGISTRATION",
            "issue": "frame0 control is required but cannot satisfy temporal registration",
        },
        {
            "method": "antspy_synonly_downsampled_smoke",
            "transform_family": "ANTsPy SyNOnly deformable",
            "same_safe_subset_case_count": 1,
            "source_case_count": 1,
            "case_scope": "Case1001 only, frame 9 to frame 0, downsampled x/y by 2",
            "fixed_frame": syn_summary.get("fixed_frame_index", ""),
            "moving_frame": syn_summary.get("moving_frame_index", ""),
            "image_ncc_before_mean": fmt(syn_summary.get("image_ncc_before")),
            "image_ncc_after_mean": fmt(syn_summary.get("image_ncc_after")),
            "myocardium_before_or_reference": fmt(first([r for r in syn_rows if r.get("class_id") == "1"], "moving_consistency_to_reference")),
            "myocardium_after_or_warped": fmt(first([r for r in syn_rows if r.get("class_id") == "1"], "warped_consistency_to_reference")),
            "lv_before_or_reference": fmt(first([r for r in syn_rows if r.get("class_id") == "2"], "moving_consistency_to_reference")),
            "lv_after_or_warped": fmt(first([r for r in syn_rows if r.get("class_id") == "2"], "warped_consistency_to_reference")),
            "folding_or_jacobian": "EVIDENCE_NOT_FOUND for SyN field; transform files exist but no Jacobian audit",
            "runtime_seconds_mean": fmt(syn_summary.get("runtime_seconds")),
            "evidence_path": "results/20260704_cine_full_cinema_registration/syn_probe_summary.json",
            "gate_status": "SMOKE_SUPPORTED_NEEDS_SAFE_SUBSET_MATRIX",
            "issue": "one-case SyN smoke cannot pass full registration",
        },
        {
            "method": "voxelmorph_pytorch_untrained_adapter_probe",
            "transform_family": "learned_deformable_untrained",
            "same_safe_subset_case_count": 1,
            "source_case_count": 1,
            "case_scope": "Case1001 only, frame 9 to frame 0, untrained local API",
            "fixed_frame": vxm_summary.get("fixed_frame", ""),
            "moving_frame": vxm_summary.get("moving_frame", ""),
            "image_ncc_before_mean": fmt(vxm_summary.get("image_ncc_before")),
            "image_ncc_after_mean": fmt(vxm_summary.get("image_ncc_after")),
            "myocardium_before_or_reference": fmt(first([r for r in vxm_rows if r.get("class_id") == "1"], "dice_before")),
            "myocardium_after_or_warped": fmt(first([r for r in vxm_rows if r.get("class_id") == "1"], "dice_after")),
            "lv_before_or_reference": fmt(first([r for r in vxm_rows if r.get("class_id") == "2"], "dice_before")),
            "lv_after_or_warped": fmt(first([r for r in vxm_rows if r.get("class_id") == "2"], "dice_after")),
            "folding_or_jacobian": f"jacobian proxy ok on untrained near-identity probe; folding_proxy_voxels={vxm_summary.get('folding_proxy_voxels', '')}",
            "runtime_seconds_mean": fmt(vxm_summary.get("runtime_seconds")),
            "evidence_path": "results/20260704_cine_full_cinema_registration/voxelmorph_adapter_probe_summary.json",
            "gate_status": "ADAPTER_RUNS_NOT_TRAINED_NOT_USABLE_REGISTRATION",
            "issue": "untrained near-identity adapter is not learned registration evidence",
        },
        {
            "method": "simpleitk_demons_displacement_fallback",
            "transform_family": "deformable_displacement_fallback",
            "same_safe_subset_case_count": 8,
            "source_case_count": 8,
            "case_scope": "8 safe cases from prior temporal motion resume",
            "fixed_frame": 0,
            "moving_frame": "selected_non_reference",
            "image_ncc_before_mean": fmt(mean_float(demons_summary, "image_ncc_before_mean")),
            "image_ncc_after_mean": fmt(mean_float(demons_summary, "image_ncc_after_mean")),
            "myocardium_before_or_reference": fmt(first([r for r in demons_summary if r.get("class_id") == "1"], "moving_dice_to_gt_mean")),
            "myocardium_after_or_warped": fmt(first([r for r in demons_summary if r.get("class_id") == "1"], "warped_dice_to_gt_mean")),
            "lv_before_or_reference": fmt(first([r for r in demons_summary if r.get("class_id") == "2"], "moving_dice_to_gt_mean")),
            "lv_after_or_warped": fmt(first([r for r in demons_summary if r.get("class_id") == "2"], "warped_dice_to_gt_mean")),
            "folding_or_jacobian": f"folding_voxels_mean={mean_float(demons_summary, 'folding_voxels_mean')}; jacobian_min_min={mean_float(demons_summary, 'jacobian_min_min')}",
            "runtime_seconds_mean": fmt(mean_float(demons_summary, "runtime_seconds_mean")),
            "evidence_path": "results/20260704_cine_temporal_motion_resume/simpleitk_demons_summary.csv",
            "gate_status": "FALLBACK_ONLY_JACOBIAN_CONCERN",
            "issue": "improves moving frame but below frame0 control and has negative Jacobian evidence",
        },
        {
            "method": "slice2d_dense_optical_flow_proxy",
            "transform_family": "dense optical-flow feature-warp proxy",
            "same_safe_subset_case_count": safe_case_count,
            "source_case_count": safe_case_count,
            "case_scope": f"{safe_case_count} strict-safe frame0-label cases; strict matches recorded {strict_safe_count}",
            "fixed_frame": 0,
            "moving_frame": "selected_flow_frame",
            "image_ncc_before_mean": fmt(first([r for r in flow_summary if r.get("variant") == "cine_deformable_or_feature_warp"], "image_ncc_before_mean")),
            "image_ncc_after_mean": fmt(first([r for r in flow_summary if r.get("variant") == "cine_deformable_or_feature_warp"], "image_ncc_after_mean")),
            "myocardium_before_or_reference": "",
            "myocardium_after_or_warped": fmt(first([r for r in flow_summary if r.get("metric_name") == "class_1_myocardium" and r.get("variant") == "cine_deformable_or_feature_warp"], "anatomy_consistency_mean")),
            "lv_before_or_reference": "",
            "lv_after_or_warped": fmt(first([r for r in flow_summary if r.get("metric_name") == "class_2_lv" and r.get("variant") == "cine_deformable_or_feature_warp"], "anatomy_consistency_mean")),
            "folding_or_jacobian": f"folding_voxels_mean={first([r for r in flow_summary if r.get('variant') == 'cine_deformable_or_feature_warp'], 'folding_voxels_mean')}; jacobian_min_proxy_min={first([r for r in flow_summary if r.get('variant') == 'cine_deformable_or_feature_warp'], 'jacobian_min_proxy_min')}",
            "runtime_seconds_mean": fmt(first([r for r in flow_summary if r.get("variant") == "cine_deformable_or_feature_warp"], "runtime_seconds_mean")),
            "evidence_path": "results/20260703_cine_motion/motion_or_warp_summary.csv",
            "gate_status": "PROXY_ONLY_NOT_VALIDATED_REGISTRATION",
            "issue": "proxy has temporal signal but folding proxy is poor and transform is not SyN/VoxelMorph",
        },
    ]


def build_router_probe() -> list[dict[str, object]]:
    warp_rows = read_csv(REPO_ROOT / "results/20260703_cine_motion/warp_sanity.csv")
    demons_case = read_csv(REPO_ROOT / "results/20260704_cine_temporal_motion_resume/simpleitk_demons_case_metrics.csv")
    syn_summary = read_json(REPO_ROOT / "results/20260704_cine_full_cinema_registration/syn_probe_summary.json")
    vxm_summary = read_json(REPO_ROOT / "results/20260704_cine_full_cinema_registration/voxelmorph_adapter_probe_summary.json")

    flow_rows = [r for r in warp_rows if r.get("variant") == "cine_deformable_or_feature_warp"]
    desc_rows = [r for r in warp_rows if r.get("variant") == "cine_motion_descriptor_temporal_refiner"]
    demons_cases = {}
    for row in demons_case:
        demons_cases.setdefault(row.get("case_id", ""), row)

    rows: list[dict[str, object]] = []
    for row in flow_rows[:12]:
        rows.append(
            {
                "router_source": "optical_flow_proxy",
                "case_id": row.get("case_id", ""),
                "frame_index": row.get("frame_index", ""),
                "image_ncc_before": row.get("image_ncc_before", ""),
                "image_ncc_after": row.get("image_ncc_after", ""),
                "image_ncc_delta": row.get("image_ncc_delta", ""),
                "motion_saliency": row.get("flow_magnitude_mean_px", ""),
                "smoothness_or_quality": row.get("flow_smoothness_mean", ""),
                "folding_or_jacobian_risk": row.get("folding_voxels", ""),
                "temporal_entropy": "",
                "reference_weight": "",
                "route_decision": "candidate_signal_but_registration_proxy_only",
                "evidence_path": "results/20260703_cine_motion/warp_sanity.csv",
            }
        )
    for row in desc_rows[:12]:
        rows.append(
            {
                "router_source": "descriptor_temporal_refiner",
                "case_id": row.get("case_id", ""),
                "frame_index": row.get("frame_indices", ""),
                "image_ncc_before": "",
                "image_ncc_after": "",
                "image_ncc_delta": "",
                "motion_saliency": row.get("center_shift_mm", ""),
                "smoothness_or_quality": row.get("reference_dominance", ""),
                "folding_or_jacobian_risk": "",
                "temporal_entropy": row.get("temporal_entropy", ""),
                "reference_weight": row.get("reference_weight", ""),
                "route_decision": "router_inputs_available_no_runtime_dictionary",
                "evidence_path": "results/20260703_cine_motion/warp_sanity.csv",
            }
        )
    for case_id, row in sorted(demons_cases.items())[:8]:
        rows.append(
            {
                "router_source": "simpleitk_demons_fallback",
                "case_id": case_id,
                "frame_index": row.get("moving_frame_index", ""),
                "image_ncc_before": row.get("image_ncc_before", ""),
                "image_ncc_after": row.get("image_ncc_after", ""),
                "image_ncc_delta": "",
                "motion_saliency": row.get("displacement_mean", ""),
                "smoothness_or_quality": row.get("displacement_max", ""),
                "folding_or_jacobian_risk": row.get("folding_voxels", ""),
                "temporal_entropy": "",
                "reference_weight": "",
                "route_decision": "fallback_quality_signal_jacobian_concern",
                "evidence_path": "results/20260704_cine_temporal_motion_resume/simpleitk_demons_case_metrics.csv",
            }
        )
    rows.extend(
        [
            {
                "router_source": "antspy_syn_smoke",
                "case_id": syn_summary.get("case_id", ""),
                "frame_index": syn_summary.get("moving_frame_index", ""),
                "image_ncc_before": fmt(syn_summary.get("image_ncc_before")),
                "image_ncc_after": fmt(syn_summary.get("image_ncc_after")),
                "image_ncc_delta": fmt((f(syn_summary.get("image_ncc_after")) or 0) - (f(syn_summary.get("image_ncc_before")) or 0)),
                "motion_saliency": "",
                "smoothness_or_quality": "SyN smoke improved NCC/label consistency",
                "folding_or_jacobian_risk": "EVIDENCE_NOT_FOUND",
                "temporal_entropy": "",
                "reference_weight": "",
                "route_decision": "strong_registration_candidate_needs_matrix",
                "evidence_path": "results/20260704_cine_full_cinema_registration/syn_probe_summary.json",
            },
            {
                "router_source": "voxelmorph_untrained_probe",
                "case_id": vxm_summary.get("case_id", ""),
                "frame_index": vxm_summary.get("moving_frame", ""),
                "image_ncc_before": fmt(vxm_summary.get("image_ncc_before")),
                "image_ncc_after": fmt(vxm_summary.get("image_ncc_after")),
                "image_ncc_delta": fmt((f(vxm_summary.get("image_ncc_after")) or 0) - (f(vxm_summary.get("image_ncc_before")) or 0)),
                "motion_saliency": fmt(vxm_summary.get("mean_abs_displacement")),
                "smoothness_or_quality": "near_identity_untrained",
                "folding_or_jacobian_risk": fmt(vxm_summary.get("folding_proxy_voxels")),
                "temporal_entropy": "",
                "reference_weight": "",
                "route_decision": "not_usable_as_trained_registration",
                "evidence_path": "results/20260704_cine_full_cinema_registration/voxelmorph_adapter_probe_summary.json",
            },
        ]
    )
    return rows


def write_reports(output_dir: Path, registration_rows: list[dict[str, object]], router_rows: list[dict[str, object]], command: str) -> None:
    same_safe_full = all(int(row.get("same_safe_subset_case_count", 0) or 0) >= 8 for row in registration_rows if "control" not in str(row.get("method", "")))
    has_syn_matrix = any(row["method"] == "antspy_synonly_downsampled_smoke" and int(row.get("source_case_count", 0) or 0) > 1 for row in registration_rows)
    has_trained_vxm = any("VOXELMORPH_TRAINED" in str(row.get("gate_status", "")) for row in registration_rows)
    registration_gap = not (same_safe_full and has_syn_matrix and has_trained_vxm)

    temporal_runtime_ready = False
    completion_state = "M5_DIAGNOSTIC_READY_FOR_REVIEW"

    write_text(
        output_dir / "cine_scope_contract.md",
        "\n".join(
            [
                "# Cine Scope Contract",
                "",
                "task: `prompts/tasks/20260705_srr_v3_m5_cine_secondary_contract.md`",
                "status: `EXECUTED_UNAUDITED`",
                "route_promotion_decision: `NO_PROMOTION`",
                "hosted_metric_claim: `NOT_CLAIMED`",
                "validation_packaging_upload: `NOT_RUN_FORBIDDEN_BY_TASK`",
                "",
                "## Scope",
                "",
                "M5 keeps Cine as a secondary diagnostic line. It aggregates existing CineMA anatomy-prior, registration, VoxelMorph, frame0/ED, temporal descriptor, and router evidence into a reviewer-visible packet.",
                "",
                "This packet does not train Cine models, does not run validation packaging/upload, does not claim hosted `myocardium_cinemyops`, and does not block MyoPS milestones.",
                "",
                "## Controlled Status",
                "",
                f"- registration_status: `{'CINE_REGISTRATION_GAP_REMAINS' if registration_gap else 'CINE_REGISTRATION_MATRIX_READY'}`",
                "- temporal_dictionary_status: `TEMPORAL_DICTIONARY_NOT_READY`",
                "- CineMA/anatomy_prior_status: `PARTIAL_SUPPORTED_ANATOMY_ONLY`",
                "- VoxelMorph_status: `ADAPTER_RUNS_NOT_TRAINED_NOT_USABLE_REGISTRATION`",
            ]
        )
        + "\n",
    )

    write_text(
        output_dir / "temporal_dictionary_readiness.md",
        "\n".join(
            [
                "# Temporal Dictionary Readiness",
                "",
                "temporal_dictionary_status: `TEMPORAL_DICTIONARY_NOT_READY`",
                "registration_status: `CINE_REGISTRATION_GAP_REMAINS`",
                "",
                "## Evidence Present",
                "",
                "- Frame0/ED anatomy prior exists from the CineMA adapter pilot.",
                "- Non-reference optical-flow proxy rows and descriptor-router rows exist for a strict-safe subset.",
                "- SimpleITK/Demons fallback rows exist for 8 safe cases.",
                "- One ANTsPy SyN smoke row exists for `Case1001` frame 9 to frame 0.",
                "- One untrained VoxelMorph adapter probe exists for the same pair.",
                "",
                "## Missing Runtime Contract",
                "",
                "- No runtime temporal dictionary artifact stores reference anatomy plus validated non-reference warped features.",
                "- No same-safe-subset SyN/VoxelMorph/Demons/control matrix exists across the same cases.",
                "- No trained or public-weight VoxelMorph row exists.",
                "- No temporal aggregation metrics against a frame0/ED control exist for a validated registration path.",
                "- No hosted `myocardium_cinemyops` metric is claimed.",
                "",
                "Conclusion: router inputs are partially available, but temporal dictionary integration must not start as a full method until the registration matrix and runtime dictionary are produced.",
            ]
        )
        + "\n",
    )

    write_text(
        output_dir / "cine_missing_evidence.md",
        "\n".join(
            [
                "# Cine Missing Evidence",
                "",
                "primary_missing_tokens:",
                "",
                "- `CINE_REGISTRATION_GAP_REMAINS`",
                "- `TEMPORAL_DICTIONARY_NOT_READY`",
                "",
                "## Missing Or Insufficient Evidence",
                "",
                "| requirement | current evidence | decision |",
                "| --- | --- | --- |",
                "| CineMA/anatomy prior | ACDC SAX seed0 adapter ran on 64 train + 15 validation cases; anatomy only | `PARTIAL_SUPPORTED_ANATOMY_ONLY` |",
                "| ANTsPy SyN same-safe-subset matrix | one downsampled `Case1001` smoke | `SMOKE_ONLY_NEEDS_MATRIX` |",
                "| VoxelMorph trained/usable status | local PyTorch API runs, but untrained near-identity | `NOT_TRAINED_NOT_USABLE` |",
                "| SimpleITK/Demons fallback | 8-case fallback improves moving frame but has negative Jacobian/folding evidence | `FALLBACK_ONLY` |",
                "| optical flow | 59-case proxy has temporal signal but poor folding proxy | `PROXY_ONLY` |",
                "| frame0/ED controls | present and necessary | `CONTROL_SUPPORTED` |",
                "| temporal dictionary runtime | contract exists; no runtime dictionary artifact | `TEMPORAL_DICTIONARY_NOT_READY` |",
                "| frame-quality router | input signals exist in prior proxy/fallback rows; no production router integrated | `PROBE_ONLY` |",
                "| hosted metric | not run by task constraint | `NOT_CLAIMED` |",
            ]
        )
        + "\n",
    )

    write_text(
        output_dir / "completion_check.md",
        "\n".join(
            [
                "# Completion Check",
                "",
                f"`{completion_state}`",
                "",
                "executor_status: `EXECUTED_UNAUDITED`",
                "registration_status: `CINE_REGISTRATION_GAP_REMAINS`",
                "temporal_dictionary_status: `TEMPORAL_DICTIONARY_NOT_READY`",
                f"registration_rows: `{len(registration_rows)}`",
                f"router_probe_rows: `{len(router_rows)}`",
                "",
                "No `review.md` was written. Later Cine work remains blocked until a separate reviewer writes `M5_AUDITED_DIAGNOSTIC_GO`.",
            ]
        )
        + "\n",
    )

    write_text(
        output_dir / "review_request.md",
        "\n".join(
            [
                "# Review Request",
                "",
                "Please audit this M5 executor packet as a separate read-only review. `review.md` is intentionally absent at executor stop.",
                "",
                "Reviewer focus: confirm the packet does not overclaim Cine registration, VoxelMorph, temporal dictionary readiness, hosted metrics, validation packaging/upload, or MyoPS blocking authority.",
                "",
                "Later Cine work remains blocked until a separate read-only reviewer writes `M5_AUDITED_DIAGNOSTIC_GO`.",
            ]
        )
        + "\n",
    )

    write_text(
        output_dir / "result.md",
        "\n".join(
            [
                "# SRR-v3 M5 Cine Secondary Contract Result",
                "",
                "status: `EXECUTED_UNAUDITED`",
                f"completion_state: `{completion_state}`",
                "domain_evidence_label: `PARTIAL_MECHANISM_INCOMPLETE`",
                "",
                "## Summary",
                "",
                "Generated a diagnostic-only Cine secondary contract packet from existing Cine evidence. The packet supports planning/review of the Cine side line, not route promotion.",
                "",
                "Key conclusion: `CINE_REGISTRATION_GAP_REMAINS` and `TEMPORAL_DICTIONARY_NOT_READY`. CineMA anatomy prior evidence is useful but anatomy-only; ANTsPy SyN is one-case smoke; VoxelMorph is untrained near-identity; SimpleITK/Demons and optical flow are fallback/proxy rows.",
                "",
                "## Command",
                "",
                f"- `{command}`",
            ]
        )
        + "\n",
    )

    write_text(
        output_dir / "MANIFEST.md",
        "\n".join(
            [
                "# MANIFEST",
                "",
                f"task: `{TASK_PATH}`",
                f"result_dir: `{output_dir}`",
                "",
                "| artifact | purpose |",
                "| --- | --- |",
                "| `result.md` | executor summary |",
                "| `cine_scope_contract.md` | diagnostic boundary and controlled statuses |",
                "| `registration_safe_subset_matrix.csv` | existing registration/control evidence matrix and gaps |",
                "| `temporal_dictionary_readiness.md` | runtime dictionary readiness assessment |",
                "| `frame_quality_router_probe.csv` | current router input signals and quality gates |",
                "| `cine_missing_evidence.md` | explicit blockers before temporal integration |",
                "| `completion_check.md` | executor readiness check |",
                "| `review_request.md` | independent review request |",
                "| `MANIFEST.md` | artifact index |",
                "| `commands_run.md` | command provenance |",
                "| `source_evidence_index.csv` | source artifacts used by the aggregation script |",
                "",
                "No checkpoints, NIfTI predictions, validation packages, uploads, heavy logs, or external credentials are included.",
            ]
        )
        + "\n",
    )

    write_text(
        output_dir / "commands_run.md",
        "\n".join(
            [
                "# Commands Run",
                "",
                f"- command: `{command}`",
                f"- aggregate_time_utc: `{datetime.now(UTC).isoformat()}`",
                "- network_used: `false`",
                "- training_run: `false`",
                "- validation_packaging_upload: `false`",
            ]
        )
        + "\n",
    )


def build_source_index() -> list[dict[str, object]]:
    sources = [
        "results/20260620_cinema_adapter_pilot/result.md",
        "results/20260620_cinema_adapter_pilot/review.md",
        "results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics_summary.json",
        "results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/metrics.csv",
        "results/20260703_cine_motion/temporal_metrics_summary.md",
        "results/20260703_cine_motion/motion_or_warp_summary.csv",
        "results/20260703_cine_motion/warp_sanity.csv",
        "results/20260703_cine_motion/safe_cases_used.csv",
        "results/20260704_cine_temporal_motion_resume/result.md",
        "results/20260704_cine_temporal_motion_resume/review.md",
        "results/20260704_cine_temporal_motion_resume/simpleitk_demons_summary.csv",
        "results/20260704_cine_temporal_motion_resume/simpleitk_demons_case_metrics.csv",
        "results/20260704_cine_full_cinema_registration/result.md",
        "results/20260704_cine_full_cinema_registration/syn_probe_summary.json",
        "results/20260704_cine_full_cinema_registration/syn_voxelmorph_probe.csv",
        "results/20260704_cine_full_cinema_registration/voxelmorph_adapter_probe_summary.json",
        "results/20260704_cine_full_cinema_registration/voxelmorph_adapter_probe.csv",
        "results/20260704_external_assets_cinema_registration/usable_asset_matrix.md",
        "results/20260704_external_assets_cinema_registration/environment_probe.md",
    ]
    rows = []
    for source in sources:
        path = REPO_ROOT / source
        rows.append(
            {
                "source_path": source,
                "exists": path.is_file(),
                "size_bytes": path.stat().st_size if path.is_file() else "",
                "role": "M5 evidence source",
            }
        )
    return rows


def validate_packet(output_dir: Path) -> None:
    required = [
        "result.md",
        "cine_scope_contract.md",
        "registration_safe_subset_matrix.csv",
        "temporal_dictionary_readiness.md",
        "frame_quality_router_probe.csv",
        "cine_missing_evidence.md",
        "completion_check.md",
        "review_request.md",
        "MANIFEST.md",
        "commands_run.md",
        "source_evidence_index.csv",
    ]
    missing = [name for name in required if not (output_dir / name).is_file()]
    if missing:
        raise RuntimeError(f"missing required M5 packet files: {missing}")
    if (output_dir / "review.md").exists():
        raise RuntimeError("executor packet must not contain review.md")
    completion = read_text(output_dir / "completion_check.md")
    if "M5_DIAGNOSTIC_READY_FOR_REVIEW" not in completion:
        raise RuntimeError("completion_check.md does not contain M5_DIAGNOSTIC_READY_FOR_REVIEW")
    if "CINE_REGISTRATION_GAP_REMAINS" not in completion:
        raise RuntimeError("completion_check.md must preserve CINE_REGISTRATION_GAP_REMAINS")
    if "TEMPORAL_DICTIONARY_NOT_READY" not in completion:
        raise RuntimeError("completion_check.md must preserve TEMPORAL_DICTIONARY_NOT_READY")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else REPO_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    registration_rows = build_registration_matrix()
    router_rows = build_router_probe()
    source_rows = build_source_index()

    write_csv(output_dir / "registration_safe_subset_matrix.csv", registration_rows)
    write_csv(output_dir / "frame_quality_router_probe.csv", router_rows)
    write_csv(output_dir / "source_evidence_index.csv", source_rows)
    write_reports(output_dir, registration_rows, router_rows, " ".join(sys.argv))
    validate_packet(output_dir)
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "registration_rows": len(registration_rows),
                "router_rows": len(router_rows),
                "completion": "M5_DIAGNOSTIC_READY_FOR_REVIEW",
                "registration_status": "CINE_REGISTRATION_GAP_REMAINS",
                "temporal_dictionary_status": "TEMPORAL_DICTIONARY_NOT_READY",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
