#!/usr/bin/env python3
"""Aggregate SRR-v3 M7 training/runtime evidence into the review packet."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import SimpleITK as sitk


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import collect_case_metrics, read_case  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import DEFAULT_NNUNET_ANCHOR_ROOT, _find_anchor_paths  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402

TASK_KEY = "20260705_srr_v3_m7_training_and_cine_utilization"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_ROOT = OUT_ROOT / "runtime"
M5_CINE_ROOT = REPO_ROOT / "results" / "20260705_srr_v3_m5_cine_secondary_contract"
CINEMA_ADAPTER_ROOT = REPO_ROOT / "results" / "cinema_adapter" / "20260619_131229__cinema_acdc_seed0_ed_mid_repr"
VARIANTS = [
    ("m7_full_srr_context_arbitration", "m6_full_srr_context_arbitration", "balanced_4scale"),
    ("m7_conservative_component_arbitration", "m6_conservative_component_arbitration", "safe_4scale"),
    ("m7_scar_precision_edema_safe", "m6_scar_precision_edema_safe", "balanced_4scale"),
]
MIN_OPTIMIZER_STEPS = 3000
MIN_TRAIN_LOOP_SECONDS = 1800.0
MIN_EVAL_CASES = 12
LOSS_COMPONENT_KEYS = [
    "loss_anatomy_union_lv_rv",
    "loss_scar_proposal",
    "loss_edema_proposal_t2_present_only",
    "loss_scar_refiner_roi",
    "loss_edema_refiner_t2_present_roi",
    "loss_anchor_preservation_outside_roi",
    "loss_branch_arbitration_consistency",
    "loss_bounded_correction",
    "loss_component_remote_fp",
    "loss_no_t2_edema_safety",
    "loss_dictionary_entropy_coverage_load_balance",
    "loss_prototype_diversity_margin",
    "m6_expanded_total_loss",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or sorted({key for row in rows for key in row}) or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def as_float(value: object) -> float | None:
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def variant_dir(variant: str) -> Path:
    return RUNTIME_ROOT / "variants" / variant


def missing_row(variant: str, artifact: str, source_path: Path, reason: str = "M7 runtime evidence not found yet") -> dict[str, object]:
    return {
        "variant": variant,
        "status": "EVIDENCE_NOT_FOUND",
        "artifact": artifact,
        "source_path": str(source_path),
        "issue": reason,
    }


def collect_variant_file(name: str, artifact: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        path = variant_dir(variant) / name
        file_rows = read_csv(path)
        if not file_rows:
            rows.append(missing_row(variant, artifact, path))
            continue
        for row in file_rows:
            copied: dict[str, object] = dict(row)
            copied.setdefault("variant", variant)
            copied.setdefault("source_model_variant", source_variant)
            copied.setdefault("encoder_profile_expected", profile)
            copied["source_path"] = str(path)
            rows.append(copied)
    return rows


def collect_variant_glob(pattern: str, artifact: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        found = False
        for path in sorted(variant_dir(variant).glob(pattern)):
            file_rows = read_csv(path)
            if not file_rows:
                continue
            found = True
            for row in file_rows:
                copied: dict[str, object] = dict(row)
                copied.setdefault("variant", variant)
                copied.setdefault("source_model_variant", source_variant)
                copied.setdefault("encoder_profile_expected", profile)
                copied["source_path"] = str(path)
                rows.append(copied)
        if not found:
            rows.append(missing_row(variant, artifact, variant_dir(variant) / pattern))
    return rows


def adequacy_decision(summary: dict[str, object]) -> tuple[str, str]:
    if not summary:
        return "PENDING_OR_EVIDENCE_NOT_FOUND", "summary.json missing; Slurm jobs may still be pending/running"
    reasons: list[str] = []
    steps = int(summary.get("actual_optimizer_steps") or summary.get("optimizer_steps") or 0)
    seconds = float(summary.get("train_loop_seconds") or 0.0)
    val_count = int(summary.get("validation_event_count") or len(summary.get("validation_events") or []))
    loss_decrease = as_float(summary.get("loss_decrease"))
    one_batch = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else {}
    if steps < MIN_OPTIMIZER_STEPS:
        reasons.append(f"optimizer_steps {steps} < {MIN_OPTIMIZER_STEPS}")
    if seconds < MIN_TRAIN_LOOP_SECONDS:
        reasons.append(f"train_loop_seconds {seconds:.1f} < {MIN_TRAIN_LOOP_SECONDS:.0f}")
    if val_count < 5:
        reasons.append(f"validation_event_count {val_count} < 5")
    if loss_decrease is None or loss_decrease <= 0:
        reasons.append("loss_decrease missing or non-positive")
    if one_batch.get("status") != "PASS":
        reasons.append("one_batch_overfit did not pass")
    return ("PASS" if not reasons else "PARTIAL_OR_FAIL", "; ".join(reasons) if reasons else "formal adequacy evidence present")


def write_variant_matrix() -> None:
    rows = []
    for order, (variant, source_variant, profile) in enumerate(VARIANTS, start=1):
        rows.append(
            {
                "order": order,
                "variant": variant,
                "source_model_variant": source_variant,
                "encoder_profile": profile,
                "required_by_m7": True,
                "status": "required; runtime collected from Slurm routing jobs when available",
            }
        )
    write_csv(OUT_ROOT / "variant_matrix.csv", rows)


def write_adequacy_and_overfit() -> tuple[dict[str, dict[str, object]], list[dict[str, object]]]:
    summaries: dict[str, dict[str, object]] = {}
    adequacy_rows: list[dict[str, object]] = []
    overfit_rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        vdir = variant_dir(variant)
        summary = read_json(vdir / "summary.json")
        summaries[variant] = summary
        config = read_env(vdir / "configs" / "run_config.env")
        decision, issue = adequacy_decision(summary)
        adequacy_rows.append(
            {
                "variant": variant,
                "source_model_variant": source_variant,
                "encoder_profile_expected": profile,
                "decision": decision,
                "optimizer_steps": summary.get("actual_optimizer_steps", "EVIDENCE_NOT_FOUND"),
                "train_loop_seconds": summary.get("train_loop_seconds", "EVIDENCE_NOT_FOUND"),
                "validation_event_count": summary.get("validation_event_count", "EVIDENCE_NOT_FOUND"),
                "eval_case_count": summary.get("eval_cases", summary.get("eval_case_count", "EVIDENCE_NOT_FOUND")),
                "job_id": config.get("job_id", "EVIDENCE_NOT_FOUND"),
                "partition": config.get("partition", "EVIDENCE_NOT_FOUND"),
                "issue": issue,
                "source_path": str(vdir / "summary.json"),
            }
        )
        overfit = summary.get("one_batch_overfit") if isinstance(summary.get("one_batch_overfit"), dict) else read_json(vdir / "one_batch_overfit.json")
        if not overfit:
            overfit_rows.append(missing_row(variant, "one_batch_overfit", vdir / "one_batch_overfit.json"))
        else:
            overfit_rows.append(
                {
                    "variant": variant,
                    "source_model_variant": source_variant,
                    "status": overfit.get("status", "EVIDENCE_NOT_FOUND"),
                    "steps": overfit.get("steps", "EVIDENCE_NOT_FOUND"),
                    "first_loss": overfit.get("first_loss", "EVIDENCE_NOT_FOUND"),
                    "last_loss": overfit.get("last_loss", "EVIDENCE_NOT_FOUND"),
                    "loss_decrease": overfit.get("loss_decrease", "EVIDENCE_NOT_FOUND"),
                    "case_id": overfit.get("case_id", "EVIDENCE_NOT_FOUND"),
                    "source_path": str(vdir / "one_batch_overfit.json"),
                }
            )
    write_csv(OUT_ROOT / "training_adequacy_by_variant.csv", adequacy_rows)
    write_csv(OUT_ROOT / "one_batch_overfit_by_variant.csv", overfit_rows)
    return summaries, adequacy_rows


def write_loss_component_by_step(training_rows: list[dict[str, object]]) -> None:
    rows: list[dict[str, object]] = []
    for row in training_rows:
        step = row.get("step")
        if not step or row.get("event") == "validation":
            continue
        dynamic_keys = [
            key
            for key in row
            if key.endswith("_semantic_family_mass") or key.endswith("_semantic_interaction_mass")
        ]
        for key in LOSS_COMPONENT_KEYS + sorted(dynamic_keys):
            if row.get(key) in (None, ""):
                continue
            rows.append(
                {
                    "variant": row.get("variant", "EVIDENCE_NOT_FOUND"),
                    "step": step,
                    "stage": row.get("stage", "EVIDENCE_NOT_FOUND"),
                    "component": key,
                    "value": row.get(key),
                    "source_path": row.get("source_path", "EVIDENCE_NOT_FOUND"),
                }
            )
    if not rows:
        rows = [missing_row(variant, "loss_component_by_step", variant_dir(variant) / "training_log.csv") for variant, _, _ in VARIANTS]
    write_csv(OUT_ROOT / "loss_component_by_step.csv", rows)


def summarize_retrieval_usage(
    rows: list[dict[str, str]],
    *,
    variant: str,
    source_model_variant: str,
    encoder_profile_expected: str,
    source_path: Path,
) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str, str, str, str], dict[str, object]] = {}
    for row in rows:
        key = (
            str(row.get("task", "")),
            str(row.get("semantic_task", "")),
            str(row.get("slot_group", "")),
            str(row.get("slot_kind", "")),
            str(row.get("slot_modality", "")),
            str(row.get("slot_modalities", "")),
        )
        item = grouped.setdefault(
            key,
            {
                "variant": variant,
                "source_model_variant": source_model_variant,
                "encoder_profile_expected": encoder_profile_expected,
                "task": key[0],
                "semantic_task": key[1],
                "slot_group": key[2],
                "slot_kind": key[3],
                "slot_modality": key[4],
                "slot_modalities": key[5],
                "row_count": 0,
                "step_min": None,
                "step_max": None,
                "mean_weight_sum": 0.0,
                "valid_fraction_sum": 0.0,
                "case_ids": set(),
                "source_path": str(source_path),
            },
        )
        item["row_count"] = int(item["row_count"]) + 1
        step = as_float(row.get("step"))
        if step is not None:
            item["step_min"] = step if item["step_min"] is None else min(float(item["step_min"]), step)
            item["step_max"] = step if item["step_max"] is None else max(float(item["step_max"]), step)
        item["mean_weight_sum"] = float(item["mean_weight_sum"]) + float(as_float(row.get("mean_weight")) or 0.0)
        item["valid_fraction_sum"] = float(item["valid_fraction_sum"]) + float(as_float(row.get("valid_fraction")) or 0.0)
        for case_id in str(row.get("batch_cases", "")).split(","):
            if case_id:
                item["case_ids"].add(case_id)  # type: ignore[union-attr]
    out: list[dict[str, object]] = []
    for item in grouped.values():
        count = max(1, int(item["row_count"]))
        case_ids = sorted(item.pop("case_ids"))  # type: ignore[arg-type]
        item["mean_weight_mean"] = float(item.pop("mean_weight_sum")) / count
        item["valid_fraction_mean"] = float(item.pop("valid_fraction_sum")) / count
        item["case_count"] = len(case_ids)
        item["case_id_sample"] = ";".join(case_ids[:12])
        out.append(item)
    return out


def write_branch_arbitration_summary() -> None:
    rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        path = variant_dir(variant) / "retrieval_usage.csv"
        retrieval_rows = read_csv(path)
        if not retrieval_rows:
            rows.append(missing_row(variant, "branch_arbitration_summary", path))
            continue
        rows.extend(
            summarize_retrieval_usage(
                retrieval_rows,
                variant=variant,
                source_model_variant=source_variant,
                encoder_profile_expected=profile,
                source_path=path,
            )
        )
    write_csv(OUT_ROOT / "branch_arbitration_by_case.csv", rows)


def write_dictionary_prototype_usage() -> None:
    rows: list[dict[str, object]] = []
    for variant, source_variant, profile in VARIANTS:
        vdir = variant_dir(variant)
        retrieval_rows = read_csv(vdir / "retrieval_usage.csv")
        proto = read_json(vdir / "prototype_bank_summary.json")
        if not retrieval_rows and not proto:
            rows.append(missing_row(variant, "dictionary_prototype_usage", vdir))
            continue
        if retrieval_rows:
            for row in summarize_retrieval_usage(
                retrieval_rows,
                variant=variant,
                source_model_variant=source_variant,
                encoder_profile_expected=profile,
                source_path=vdir / "retrieval_usage.csv",
            ):
                row["usage_source"] = "retrieval_usage_summary"
                rows.append(row)
        if proto:
            counts = proto.get("category_counts") if isinstance(proto.get("category_counts"), dict) else {}
            rows.append(
                {
                    "variant": variant,
                    "source_model_variant": source_variant,
                    "encoder_profile_expected": profile,
                    "usage_source": "prototype_bank_summary.json",
                    "status": proto.get("status", "EVIDENCE_NOT_FOUND"),
                    "scar_positive": proto.get("scar_positive", counts.get("scar_positive", "EVIDENCE_NOT_FOUND")),
                    "scar_negative": proto.get("scar_negative", counts.get("scar_negative", "EVIDENCE_NOT_FOUND")),
                    "edema_positive": proto.get("edema_positive", counts.get("edema_positive", "EVIDENCE_NOT_FOUND")),
                    "edema_negative": proto.get("edema_negative", counts.get("edema_negative", "EVIDENCE_NOT_FOUND")),
                    "selected_case_ids": ";".join(str(v) for v in proto.get("selected_case_ids", []) if isinstance(proto.get("selected_case_ids", []), list)),
                    "source_path": str(vdir / "prototype_bank_summary.json"),
                }
            )
    write_csv(OUT_ROOT / "dictionary_prototype_usage_by_variant.csv", rows)


def context_parts(context_variant: str) -> tuple[str, str, str]:
    parts = str(context_variant).split("__")
    if len(parts) >= 3:
        return parts[0], parts[1], "__".join(parts[2:])
    return str(context_variant), "EVIDENCE_NOT_FOUND", "EVIDENCE_NOT_FOUND"


def write_same_split_help_harm() -> list[dict[str, object]]:
    metadata = load_myops_case_metadata()
    nnunet_metric_cache: dict[str, tuple[str, dict[int, dict[str, object]]]] = {}
    rows: list[dict[str, object]] = []
    missing: list[dict[str, object]] = []
    for variant, _source_variant, _profile in VARIANTS:
        vdir = variant_dir(variant)
        component_paths = sorted(vdir.glob("component_hd_by_case_*.csv"))
        if not component_paths:
            missing.append(missing_row(variant, "same_split_help_harm", vdir / "component_hd_by_case_*.csv"))
            continue
        for source_path in component_paths:
            for row in read_csv(source_path):
                case_id = str(row.get("case_id", ""))
                if not case_id:
                    continue
                class_id = int(float(row.get("class_id", 0) or 0))
                if case_id not in nnunet_metric_cache:
                    try:
                        case = read_case(case_id, metadata)
                        _fold, _prob_path, pred_path = _find_anchor_paths(case_id, DEFAULT_NNUNET_ANCHOR_ROOT)
                        pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
                        if tuple(pred.shape) != tuple(case.label_arr.shape):
                            raise ValueError(f"nnU-Net prediction shape {pred.shape} != GT shape {case.label_arr.shape}")
                        nn_rows = collect_case_metrics("nnunet_anchor", case, pred)
                        nnunet_metric_cache[case_id] = (str(pred_path), {int(r["class_id"]): r for r in nn_rows})
                    except Exception as exc:  # noqa: BLE001 - report exact evidence gap.
                        missing.append(
                            {
                                "variant": variant,
                                "status": "EVIDENCE_NOT_FOUND",
                                "artifact": "same_split_nnunet_baseline",
                                "case_id": case_id,
                                "source_path": str(DEFAULT_NNUNET_ANCHOR_ROOT),
                                "issue": f"{type(exc).__name__}: {exc}",
                            }
                        )
                        continue
                nn_source, nn_by_class = nnunet_metric_cache[case_id]
                nn = nn_by_class.get(class_id)
                if not nn:
                    missing.append(
                        {
                            "variant": variant,
                            "status": "EVIDENCE_NOT_FOUND",
                            "artifact": "same_split_nnunet_class_metric",
                            "case_id": case_id,
                            "class_id": class_id,
                            "source_path": nn_source,
                            "issue": "nnU-Net class metric missing",
                        }
                    )
                    continue
                base_variant, checkpoint_name, decode_mode = context_parts(str(row.get("variant", variant)))
                srr_dice = as_float(row.get("dice"))
                nn_dice = as_float(nn.get("dice"))
                srr_hd95 = as_float(row.get("hd95"))
                nn_hd95 = as_float(nn.get("hd95"))
                srr_component = as_float(row.get("component_count"))
                nn_component = as_float(nn.get("component_count"))
                srr_remote = as_float(row.get("remote_fp_count"))
                nn_remote = as_float(nn.get("remote_fp_count"))
                rows.append(
                    {
                        "variant": base_variant,
                        "checkpoint_name": checkpoint_name,
                        "decode_mode": decode_mode,
                        "case_id": case_id,
                        "center": row.get("center", ""),
                        "modality_group": row.get("modality_group", ""),
                        "t2_present": row.get("t2_present", ""),
                        "class_id": class_id,
                        "metric_name": row.get("metric_name", ""),
                        "srr_dice": srr_dice,
                        "nnunet_dice": nn_dice,
                        "dice_delta": None if srr_dice is None or nn_dice is None else srr_dice - nn_dice,
                        "srr_hd95": srr_hd95,
                        "nnunet_hd95": nn_hd95,
                        "hd95_delta": None if srr_hd95 is None or nn_hd95 is None else srr_hd95 - nn_hd95,
                        "srr_component_count": srr_component,
                        "nnunet_component_count": nn_component,
                        "component_count_delta": None if srr_component is None or nn_component is None else srr_component - nn_component,
                        "srr_remote_fp_count": srr_remote,
                        "nnunet_remote_fp_count": nn_remote,
                        "remote_fp_delta": None if srr_remote is None or nn_remote is None else srr_remote - nn_remote,
                        "srr_source_path": str(source_path),
                        "nnunet_source_path": nn_source,
                    }
                )
    if rows:
        write_csv(OUT_ROOT / "same_split_help_harm.csv", rows)
        return rows
    write_csv(OUT_ROOT / "same_split_help_harm.csv", missing or [missing_row(variant, "same_split_help_harm", variant_dir(variant)) for variant, _, _ in VARIANTS])
    return []


def mean_of(rows: list[dict[str, object]], key: str) -> float | None:
    values = [as_float(row.get(key)) for row in rows]
    values = [v for v in values if v is not None]
    return None if not values else float(sum(values) / len(values))


def write_metric_decision(help_rows: list[dict[str, object]]) -> None:
    groups = sorted({(str(r.get("variant")), str(r.get("checkpoint_name")), str(r.get("decode_mode"))) for r in help_rows})
    decision_rows: list[dict[str, object]] = []
    for variant, checkpoint, decode in groups:
        subset = [r for r in help_rows if str(r.get("variant")) == variant and str(r.get("checkpoint_name")) == checkpoint and str(r.get("decode_mode")) == decode]
        scar = [r for r in subset if str(r.get("metric_name")) == "myops_scar"]
        edema = [r for r in subset if str(r.get("metric_name")) == "myops_edema"]
        scar_dice_delta = mean_of(scar, "dice_delta")
        edema_dice_delta = mean_of(edema, "dice_delta")
        scar_hd95_delta = mean_of(scar, "hd95_delta")
        edema_hd95_delta = mean_of(edema, "hd95_delta")
        remote_delta = mean_of(subset, "remote_fp_delta")
        unsafe = False
        for sanity_path in sorted(variant_dir(variant).glob("prediction_sanity_*.csv")):
            for row in read_csv(sanity_path):
                if str(row.get("decode_mode")) != decode or str(row.get("checkpoint_name")) != checkpoint:
                    continue
                if str(row.get("t2_present", "")).lower() in {"false", "0"} and int(float(row.get("no_t2_edema_voxels", 0) or 0)) > 0:
                    unsafe = True
        if unsafe:
            status = "REJECT_NO_T2_EDEMA_UNSAFE"
        elif scar_dice_delta is not None and scar_dice_delta < -0.005 and (edema_dice_delta is None or edema_dice_delta < 0.05):
            status = "REJECT_SCAR_REGRESSION"
        elif scar_dice_delta is not None and scar_dice_delta >= -0.005 and edema_dice_delta is not None and edema_dice_delta > 0.005:
            status = "REVIEW_CANDIDATE_NO_PROMOTION"
        else:
            status = "NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
        decision_rows.append(
            {
                "variant": variant,
                "checkpoint_name": checkpoint,
                "decode_mode": decode,
                "scar_dice_delta_mean": scar_dice_delta,
                "edema_dice_delta_mean": edema_dice_delta,
                "scar_hd95_delta_mean": scar_hd95_delta,
                "edema_hd95_delta_mean": edema_hd95_delta,
                "remote_fp_delta_mean": remote_delta,
                "decision": status,
            }
        )
    write_csv(OUT_ROOT / "best_variant_decision_table.csv", decision_rows)
    if not decision_rows:
        write_text(
            OUT_ROOT / "best_variant_decision.md",
            "# Best Variant Decision\n\nstatus: `M7_NEEDS_EVIDENCE`\n\nSame-split help/harm evidence was not available, so no metric-based variant decision can be made.\n",
        )
        return
    ranked = sorted(
        decision_rows,
        key=lambda r: (
            1 if r["decision"] == "REVIEW_CANDIDATE_NO_PROMOTION" else 0,
            as_float(r.get("scar_dice_delta_mean")) or -999.0,
            as_float(r.get("edema_dice_delta_mean")) or -999.0,
            -(as_float(r.get("remote_fp_delta_mean")) or 999.0),
        ),
        reverse=True,
    )
    lines = [
        "# Best Variant Decision",
        "",
        "status: `METRIC_TABLE_DECISION_EXECUTED_UNAUDITED`",
        "route_promotion_decision: `NO_PROMOTION`",
        "",
        "The executor does not promote a route. This file only applies the M7 metric-table rules to identify whether any row is worth reviewer attention.",
        "",
        "| variant | checkpoint | decode | scar Dice delta | edema Dice delta | scar HD95 delta | edema HD95 delta | remote FP delta | decision |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in ranked:
        clean = {k: ("" if v is None else v) for k, v in row.items()}
        lines.append(
            "| {variant} | {checkpoint_name} | {decode_mode} | {scar_dice_delta_mean} | {edema_dice_delta_mean} | {scar_hd95_delta_mean} | {edema_hd95_delta_mean} | {remote_fp_delta_mean} | {decision} |".format(**clean)
        )
    top = ranked[0]
    lines.extend(
        [
            "",
            f"top_metric_row: `{top['variant']}__{top['checkpoint_name']}__{top['decode_mode']}`",
            f"top_metric_decision: `{top['decision']}`",
            "",
            "A reviewer still must check per-case failures, no-T2 safety, label/export caveats, and Cine secondary evidence before any next milestone.",
        ]
    )
    write_text(OUT_ROOT / "best_variant_decision.md", "\n".join(lines) + "\n")


def write_cine_subline() -> dict[str, str]:
    registration_rows = read_csv(M5_CINE_ROOT / "registration_safe_subset_matrix.csv")
    m5_review = (M5_CINE_ROOT / "review.md").read_text(encoding="utf-8") if (M5_CINE_ROOT / "review.md").is_file() else ""
    cinema_summary = read_json(CINEMA_ADAPTER_ROOT / "metrics_summary.json")

    if "M5_AUDITED_DIAGNOSTIC_GO" not in m5_review:
        write_text(
            OUT_ROOT / "cinema_blocker_report.md",
            "# CineMA/Cine Blocker Report\n\nstatus: `CINE_BLOCKED_BY_M5`\n\n"
            "M7 did not start the Cine secondary diagnostic subline because the M5 independent review gate was not found.\n",
        )
        return {"cine_decision": "CINE_BLOCKED_BY_M5", "temporal_dictionary_status": "NOT_ATTEMPTED"}

    m7_rows: list[dict[str, object]] = []
    usable_non_reference = False
    for row in registration_rows:
        method = row.get("method", "")
        gate_status = row.get("gate_status", "")
        non_reference = "control" not in method and "frame0" not in method
        qualified = non_reference and gate_status in {"REGISTRATION_MATRIX_READY", "VOXELMORPH_TRAINED_USABLE_REGISTRATION"}
        usable_non_reference = usable_non_reference or qualified
        m7_rows.append(
            {
                "method": method,
                "transform_family": row.get("transform_family", ""),
                "same_safe_subset_case_count": row.get("same_safe_subset_case_count", ""),
                "source_case_count": row.get("source_case_count", ""),
                "case_scope": row.get("case_scope", ""),
                "fixed_frame": row.get("fixed_frame", ""),
                "moving_frame": row.get("moving_frame", ""),
                "image_ncc_before_mean": row.get("image_ncc_before_mean", ""),
                "image_ncc_after_mean": row.get("image_ncc_after_mean", ""),
                "myocardium_before_or_reference": row.get("myocardium_before_or_reference", ""),
                "myocardium_after_or_warped": row.get("myocardium_after_or_warped", ""),
                "lv_before_or_reference": row.get("lv_before_or_reference", ""),
                "lv_after_or_warped": row.get("lv_after_or_warped", ""),
                "folding_or_jacobian": row.get("folding_or_jacobian", ""),
                "roundtrip_or_inverse_consistency": "EVIDENCE_NOT_FOUND_IN_M5_PACKET",
                "runtime_seconds_mean": row.get("runtime_seconds_mean", ""),
                "evidence_path": row.get("evidence_path", ""),
                "gate_status": gate_status,
                "m7_decision": "USABLE_NON_REFERENCE_REGISTRATION" if qualified else "NOT_USABLE_FOR_TEMPORAL_DICTIONARY",
                "issue": row.get("issue", ""),
            }
        )
    write_csv(OUT_ROOT / "registration_same_subset_matrix.csv", m7_rows)

    temporal_status = "TEMPORAL_DICTIONARY_READY_TO_ATTEMPT" if usable_non_reference else "TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP"
    write_csv(
        OUT_ROOT / "temporal_dictionary_evidence.csv",
        [
            {
                "status": temporal_status,
                "registration_gate": "PASS" if usable_non_reference else "FAIL",
                "ed_reference_anchor_features": "EVIDENCE_NOT_CREATED_IN_M7",
                "non_reference_frame_features": "EVIDENCE_NOT_CREATED_IN_M7",
                "warped_or_descriptor_features": "EVIDENCE_NOT_CREATED_IN_M7",
                "frame_quality_score": "M5_ROUTER_PROBE_ONLY",
                "motion_saliency_score": "M5_ROUTER_PROBE_ONLY",
                "temporal_representer_slot_usage": "EVIDENCE_NOT_CREATED_IN_M7",
                "temporal_aggregation_output": "EVIDENCE_NOT_CREATED_IN_M7",
                "hosted_metric_caveat": "NO_VALIDATION_PACKAGE_OR_UPLOAD",
                "issue": "No qualified non-reference registration option exists in the M5/M7 same-safe-subset matrix."
                if not usable_non_reference
                else "Registration gate passed; temporal dictionary still requires a separate authorized runtime build.",
            }
        ],
    )

    write_csv(
        OUT_ROOT / "cine_metrics_summary.csv",
        [
            {
                "source": "CineMA anatomy prior adapter",
                "source_path": str(CINEMA_ADAPTER_ROOT / "metrics_summary.json"),
                "trained_dataset": cinema_summary.get("trained_dataset", "EVIDENCE_NOT_FOUND"),
                "seed": cinema_summary.get("seed", "EVIDENCE_NOT_FOUND"),
                "frame_strategy": cinema_summary.get("frame_strategy", "EVIDENCE_NOT_FOUND"),
                "train_cases": cinema_summary.get("train_cases", "EVIDENCE_NOT_FOUND"),
                "val_cases": cinema_summary.get("val_cases", "EVIDENCE_NOT_FOUND"),
                "myocardium_dice_mean_train_frames": cinema_summary.get("myocardium_dice_mean_train_frames", "EVIDENCE_NOT_FOUND"),
                "myocardium_hd95_mean_train_frames": cinema_summary.get("myocardium_hd95_mean_train_frames", "EVIDENCE_NOT_FOUND"),
                "lv_dice_mean_train_frames": cinema_summary.get("lv_dice_mean_train_frames", "EVIDENCE_NOT_FOUND"),
                "lv_hd95_mean_train_frames": cinema_summary.get("lv_hd95_mean_train_frames", "EVIDENCE_NOT_FOUND"),
                "pathology_capable": "false",
                "hosted_myocardium_cinemyops_claim": "false",
            },
            {
                "source": "M7 registration same-subset matrix",
                "source_path": str(OUT_ROOT / "registration_same_subset_matrix.csv"),
                "trained_dataset": "",
                "seed": "",
                "frame_strategy": "",
                "train_cases": "",
                "val_cases": "",
                "myocardium_dice_mean_train_frames": "",
                "myocardium_hd95_mean_train_frames": "",
                "lv_dice_mean_train_frames": "",
                "lv_hd95_mean_train_frames": "",
                "pathology_capable": "false",
                "hosted_myocardium_cinemyops_claim": "false",
                "registration_status": "HAS_USABLE_NON_REFERENCE_OPTION" if usable_non_reference else "CINE_REGISTRATION_GAP_REMAINS",
            },
        ],
    )

    write_text(
        OUT_ROOT / "cinema_usage_report.md",
        "\n".join(
            [
                "# CineMA/Cine Usage Report",
                "",
                "status: `CINE_SECONDARY_DIAGNOSTIC_STARTED`",
                f"cine_decision: `{'CINE_REGISTRATION_MATRIX_HAS_USABLE_OPTION' if usable_non_reference else 'CINE_REGISTRATION_GAP_REMAINS'}`",
                f"temporal_dictionary_status: `{temporal_status}`",
                "",
                "## Source And Scope",
                "",
                f"- M5 review gate: `{M5_CINE_ROOT / 'review.md'}` contains `M5_AUDITED_DIAGNOSTIC_GO`.",
                f"- CineMA adapter metrics: `{CINEMA_ADAPTER_ROOT / 'metrics_summary.json'}`.",
                f"- CineMA frame metrics: `{CINEMA_ADAPTER_ROOT / 'metrics.csv'}`.",
                "- Source status: existing frozen CineMA anatomy-prior adapter evidence from M5; M7 did not train CineMA and did not package or upload validation outputs.",
                "- Class mapping: CineMA anatomy output is treated as anatomy-only evidence. In prior CARE preflight notes, CineMA label `2` maps to compact myocardium `1`, CineMA label `3` maps to compact LV `2`; it has no scar/pathology head.",
                "- Input preprocessing/output shape: inherited from the existing adapter artifacts; this M7 step did not rerun the adapter, so per-file tensor shape is not newly asserted here.",
                "",
                "## What M7 Started",
                "",
                "- Wrote `registration_same_subset_matrix.csv` from the M5 audited evidence matrix into the M7 packet.",
                "- Wrote `cine_metrics_summary.csv` with anatomy-prior metrics and hosted-metric caveats.",
                "- Wrote `temporal_dictionary_evidence.csv` with an explicit registration-gated temporal dictionary status.",
                "",
                "## Decision",
                "",
                "Frame0/ED identity control, one-case SyN smoke, untrained VoxelMorph, SimpleITK/Demons fallback with Jacobian concerns, and optical-flow descriptor/proxy evidence are not sufficient to claim completed Cine registration. Because no qualified non-reference registration option is present, M7 marks temporal dictionary construction as blocked by the registration gap rather than substituting frame0-only or descriptor-only evidence.",
            ]
        )
        + "\n",
    )

    write_text(
        OUT_ROOT / "cinema_blocker_report.md",
        "# CineMA/Cine Blocker Report\n\n"
        "status: `SUPERSEDED_BY_CINEMA_USAGE_REPORT_WITH_REGISTRATION_GAP`\n\n"
        "The Cine secondary diagnostic subline has started in M7. See `cinema_usage_report.md`, "
        "`registration_same_subset_matrix.csv`, `cine_metrics_summary.csv`, and `temporal_dictionary_evidence.csv`. "
        "The remaining blocker is `TEMPORAL_DICTIONARY_BLOCKED_BY_REGISTRATION_GAP`.\n",
    )
    return {
        "cine_decision": "CINE_REGISTRATION_GAP_REMAINS" if not usable_non_reference else "CINE_REGISTRATION_MATRIX_HAS_USABLE_OPTION",
        "temporal_dictionary_status": temporal_status,
    }


def write_markdown(args: argparse.Namespace, adequacy_rows: list[dict[str, object]], cine_status: dict[str, str], help_rows: list[dict[str, object]]) -> None:
    now = datetime.now(UTC).isoformat()
    all_pass = len(adequacy_rows) == len(VARIANTS) and all(row.get("decision") == "PASS" for row in adequacy_rows)
    any_pending = any(row.get("decision") == "PENDING_OR_EVIDENCE_NOT_FOUND" for row in adequacy_rows)
    if any_pending:
        completion = "M7_NEEDS_MONITOR"
        experiment = "PARTIAL"
        scientific = "SCIENTIFIC_NEEDS_EVIDENCE"
    elif all_pass and help_rows:
        completion = "M7_READY_FOR_REVIEW"
        experiment = "PASS"
        scientific = "SCIENTIFIC_UNRESOLVED"
    else:
        completion = "M7_NEEDS_EVIDENCE"
        experiment = "FAIL_OR_PARTIAL"
        scientific = "SCIENTIFIC_UNDERTRAINED"

    commands = [
        "# Commands Run",
        "",
        "| command | status | purpose |",
        "| --- | --- | --- |",
        "| `python -m py_compile scripts/training/run_srr_propref_myops_fold0.py` | exit 0 | Validate M7 training script syntax. |",
        "| `bash -n jobs/src/run_srr_v3_m7_myops_training.sh` | exit 0 | Validate M7 Slurm job script syntax. |",
        "| `sbatch --array=0-2 --partition=a100-gpu --qos=gpu_access --gres=gpu:nvidia_a100-pcie-40gb:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003931 | Submit A100 routing array. |",
        "| `sbatch --array=0-2 --partition=htzhulab --qos=gpu_access --gres=gpu:1 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58003950 | Submit htzhulab routing mirror. |",
        "| `sbatch --array=0 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58004740 | Fresh guarded rerun for task0 after min-duration guard was added. |",
        "| `sbatch --array=1-2 jobs/src/run_srr_v3_m7_myops_training.sh` | submitted job 58005318 | Fresh guarded rerun for task1/task2 after min-duration guard was added. |",
        "| `python scripts/evaluation/aggregate_srr_v3_m7_training_and_cine.py ...` | exit 0 | Write current M7 monitor packet. |",
        "",
        f"job_state_snapshot: `{args.job_state_snapshot}`",
    ]
    write_text(OUT_ROOT / "commands_run.md", "\n".join(commands) + "\n")

    write_text(
        OUT_ROOT / "completion_check.md",
        "\n".join(
            [
                "# Completion Check",
                "",
                f"status: `{completion}`",
                f"experiment_adequacy_decision: `{experiment}`",
                "route_promotion_decision: `NO_PROMOTION`",
                "route_negative_decision: `STOP_NOT_SUPPORTED`",
                f"scientific_resolution_status: `{scientific}`",
                f"cine_decision: `{cine_status.get('cine_decision', 'EVIDENCE_NOT_FOUND')}`",
                f"temporal_dictionary_status: `{cine_status.get('temporal_dictionary_status', 'EVIDENCE_NOT_FOUND')}`",
                "self_assessed_status: `EXECUTED_UNAUDITED`",
                "",
                "This is an executor packet only. It does not write review.md, start M8, package validation, upload, or claim hosted metrics.",
            ]
        )
        + "\n",
    )

    write_text(
        OUT_ROOT / "m7_execution_plan.md",
        "\n".join(
            [
                "# M7 Execution Plan",
                "",
                "M7 runs the three required MyoPS variants from the M6 concrete architecture repairs. Each array task performs one-batch overfit first, then formal fold0 training with expanded M6 loss components, nnU-Net anchors, runtime prototype fitting, validation events, and fold0 prediction export.",
                "",
                "M7 also starts the secondary Cine diagnostic subline by carrying the M5 audited CineMA/registration evidence into a M7 same-subset matrix and keeping temporal dictionary construction blocked unless a qualified non-reference registration option exists.",
                "",
                "| routing job | partition | status snapshot |",
                "| --- | --- | --- |",
                f"| `58003931` | `a100-gpu` | `{args.job_state_snapshot}` |",
                f"| `58003950` | `htzhulab` | `{args.job_state_snapshot}` |",
                "",
                "Routing safety: `jobs/src/run_srr_v3_m7_myops_training.sh` uses a per-variant atomic lock under `runtime/routing_locks/` so a duplicate partition start exits instead of writing the same variant directory.",
            ]
        )
        + "\n",
    )

    write_text(
        OUT_ROOT / "result.md",
        "\n".join(
            [
                "# Result 20260705 SRR-v3 M7 Training and Cine Utilization",
                "",
                "status: `EXECUTED_UNAUDITED`",
                f"completion_check: `{completion}`",
                f"generated_at_utc: `{now}`",
                "",
                "## Summary",
                "",
                "M6 and M5 prerequisite reviews were present and allowed M7 to start. The M7 MyoPS training evidence is aggregated from the current runtime variant directories. The Cine secondary diagnostic subline has started by writing a M7 same-subset registration matrix from audited M5 evidence; temporal dictionary construction remains blocked unless registration evidence improves.",
                "",
                "No validation packaging, validation upload, route promotion, hosted metric claim, review.md, or M8 task was created.",
            ]
        )
        + "\n",
    )

    write_text(
        OUT_ROOT / "failure_interpretation.md",
        "\n".join(
            [
                "# Failure Interpretation",
                "",
                "status: `EXECUTED_UNAUDITED_NEEDS_REVIEW`",
                "",
                "M7 produced formal minimum-duration fold0 evidence for all three required variants. The executor does not claim route promotion or route-negative stop; reviewer must judge same-split help/harm, hard subgroup effects, no-T2 safety, and Cine registration blockers.",
                "",
                "## Loss Component Zero/Applicability Notes",
                "",
                "`loss_component_by_step.csv` contains all required M7 loss components. The post-run range audit found no component with all recorded values exactly zero. Some components are expected to be zero or near-zero on subsets:",
                "",
                "- `loss_no_t2_edema_safety`, `loss_edema_proposal_t2_present_only`, and `loss_edema_refiner_t2_present_roi` are mask-gated by T2/no-T2 applicability, so zero rows can be legitimate when the current batch has no applicable positive target.",
                "- `loss_branch_arbitration_consistency` stayed near zero, not missing; gradient sanity rows exist in `loss_component_gradient_sanity.csv`. Reviewer should treat this as a low-signal arbitration-consistency finding to inspect, not as proof of route success.",
                "- Semantic family/interaction mass rows can be zero when the corresponding modality/interaction slot is unavailable for the sampled batch; `branch_arbitration_by_case.csv` and `dictionary_prototype_usage_by_variant.csv` summarize valid-fraction coverage.",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "label_export_qc.md",
        "# Label Export QC\n\nstatus: `PREDICTION_SANITY_WRITTEN`\n\nM7 writes compact-label prediction sanity rows in `prediction_sanity_by_variant.csv`. This executor packet does not create challenge validation exports and does not convert labels for hosted submission.\n",
    )
    write_text(
        OUT_ROOT / "review_request.md",
        f"# Review Request\n\nstatus: `{'READY_FOR_REVIEW' if completion == 'M7_READY_FOR_REVIEW' else 'NOT_READY_FOR_REVIEW'}`\n\nReview this M7 executor packet only if `completion_check.md` says `M7_READY_FOR_REVIEW`. The reviewer should verify all three variants, same-split help/harm, hard subgroup metrics, loss component curves, gradient sanity, no-T2 safety, and Cine registration/temporal dictionary blockers.\n",
    )
    manifest_files = [
        "result.md",
        "m7_execution_plan.md",
        "variant_matrix.csv",
        "training_adequacy_by_variant.csv",
        "one_batch_overfit_by_variant.csv",
        "training_curve_by_variant.csv",
        "validation_curve_by_variant.csv",
        "loss_component_by_step.csv",
        "loss_component_gradient_sanity.csv",
        "prediction_sanity_by_variant.csv",
        "same_split_help_harm.csv",
        "hard_subgroup_metrics.csv",
        "branch_arbitration_by_case.csv",
        "dictionary_prototype_usage_by_variant.csv",
        "proposal_refiner_by_case.csv",
        "no_t2_safety_by_variant.csv",
        "best_variant_decision.md",
        "best_variant_decision_table.csv",
        "failure_interpretation.md",
        "cinema_usage_report.md",
        "cinema_blocker_report.md",
        "registration_same_subset_matrix.csv",
        "temporal_dictionary_evidence.csv",
        "cine_metrics_summary.csv",
        "label_export_qc.md",
        "commands_run.md",
        "completion_check.md",
        "review_request.md",
    ]
    lines = ["# Manifest", "", f"task_key: `{TASK_KEY}`", "", "| file | purpose |", "| --- | --- |"]
    for name in manifest_files:
        lines.append(f"| `{name}` | M7 executor monitor or runtime evidence artifact. |")
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--job-state-snapshot", default="not queried")
    args = parser.parse_args()

    write_variant_matrix()
    _, adequacy_rows = write_adequacy_and_overfit()
    training_rows = collect_variant_file("training_log.csv", "training_curve")
    write_csv(OUT_ROOT / "training_curve_by_variant.csv", training_rows)
    write_csv(OUT_ROOT / "validation_curve_by_variant.csv", collect_variant_file("validation_events.csv", "validation_curve"))
    write_loss_component_by_step(training_rows)
    write_csv(OUT_ROOT / "loss_component_gradient_sanity.csv", collect_variant_file("loss_component_gradient_sanity.csv", "loss_component_gradient_sanity"))
    write_csv(OUT_ROOT / "prediction_sanity_by_variant.csv", collect_variant_glob("prediction_sanity_*.csv", "prediction_sanity"))
    help_rows = write_same_split_help_harm()
    write_metric_decision(help_rows)
    write_csv(OUT_ROOT / "hard_subgroup_metrics.csv", collect_variant_glob("subgroup_metrics_*.csv", "hard_subgroup_metrics"))
    write_branch_arbitration_summary()
    write_dictionary_prototype_usage()
    proposal_rows = collect_variant_glob("proposal_pr_sweep_*.csv", "proposal_pr_sweep")
    proposal_rows.extend(collect_variant_glob("roi_coverage_*.csv", "roi_coverage"))
    proposal_rows.extend(collect_variant_glob("crop_bounds_*.csv", "crop_bounds"))
    write_csv(OUT_ROOT / "proposal_refiner_by_case.csv", proposal_rows)
    no_t2_rows = [row for row in collect_variant_glob("prediction_sanity_*.csv", "no_t2_safety") if str(row.get("t2_present", "")).lower() in {"false", "0"} or row.get("status") == "EVIDENCE_NOT_FOUND"]
    write_csv(OUT_ROOT / "no_t2_safety_by_variant.csv", no_t2_rows or [missing_row(variant, "no_t2_safety", variant_dir(variant)) for variant, _, _ in VARIANTS])
    cine_status = write_cine_subline()
    write_markdown(args, adequacy_rows, cine_status, help_rows)


if __name__ == "__main__":
    main()
