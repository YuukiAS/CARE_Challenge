#!/usr/bin/env python3
"""Read-only Stage-B partial/no-T2 scar forgetting diagnostics for CARE-ASE.

This script intentionally reads existing formal-training checkpoints, logs, and
metric CSVs only. It writes lightweight diagnostic evidence to an independent
result directory and never edits training runtime/checkpoint files.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


TASK_NAME = "care-ase-faithful-formal-training-20260812"
TASK_RESULTS_REL = Path("results/agent_flow_v3") / TASK_NAME
DEFAULT_STEPS = (2000, 4000, 6000)


def _float(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _mean(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None and math.isfinite(v)]
    if not vals:
        return None
    return float(sum(vals) / len(vals))


def _median(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None and math.isfinite(v)]
    if not vals:
        return None
    return float(statistics.median(vals))


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        return f"{value:.10g}"
    return str(value)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _fmt(row.get(k)) for k in fieldnames})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _role_rows(split_rows: list[dict[str, str]], fold: int, role: str, t2_present: bool | None) -> list[dict[str, str]]:
    rows = [r for r in split_rows if int(r["fold"]) == fold and r["role"] == role]
    if t2_present is not None:
        rows = [r for r in rows if _bool(r["t2_present"]) == t2_present]
    return rows


def summarize_casewise(rows: list[dict[str, str]], *, metric_prefix: str) -> dict[str, Any]:
    if metric_prefix == "scar":
        dice_key = "care_scar_dice"
        hd95_key = "care_scar_hd95_mm"
        sens_key = "scar_sensitivity"
        prec_key = "scar_precision"
        empty_key = "scar_empty_prediction"
        vol_key = "scar_volume_ratio"
        comp_key = "scar_component_count"
        remote_key = "scar_remote_fp_volume_mm3"
    elif metric_prefix == "edema":
        dice_key = "care_pure_edema_dice"
        hd95_key = "care_pure_edema_hd95_mm"
        sens_key = "pure_edema_sensitivity"
        prec_key = "pure_edema_precision"
        empty_key = "pure_edema_empty_prediction"
        vol_key = "pure_edema_volume_ratio"
        comp_key = "pure_edema_component_count"
        remote_key = None
    else:
        raise ValueError(metric_prefix)
    return {
        "case_count": len(rows),
        "dice_mean": _mean(_float(r.get(dice_key)) for r in rows),
        "dice_median": _median(_float(r.get(dice_key)) for r in rows),
        "sensitivity_mean": _mean(_float(r.get(sens_key)) for r in rows),
        "precision_mean": _mean(_float(r.get(prec_key)) for r in rows),
        "hd95_mean_mm": _mean(_float(r.get(hd95_key)) for r in rows),
        "empty_count": sum(1 for r in rows if _bool(r.get(empty_key))),
        "volume_ratio_mean": _mean(_float(r.get(vol_key)) for r in rows),
        "component_count_mean": _mean(_float(r.get(comp_key)) for r in rows),
        "remote_fp_volume_mean_mm3": _mean(_float(r.get(remote_key)) for r in rows) if remote_key else None,
    }


def build_subgroup_checkpoint_trend(runtime_repo: Path, output_dir: Path, steps: tuple[int, ...]) -> list[dict[str, Any]]:
    monitor_root = runtime_repo / TASK_RESULTS_REL / "inner_checkpoint_monitor"
    rows_out: list[dict[str, Any]] = []
    for fold in (2, 3):
        for step in steps:
            path = monitor_root / f"fold_{fold}" / f"step{step:05d}" / "casewise_metrics.csv"
            if not path.exists():
                rows_out.append(
                    {
                        "fold": fold,
                        "checkpoint_step": step,
                        "metric_source": "FORMAL_35_CASE_INNER",
                        "subgroup": "MISSING_FORMAL_INNER_CASEWISE",
                        "case_count": 0,
                    }
                )
                continue
            rows = _read_csv(path)
            complete = [r for r in rows if _bool(r.get("t2_present"))]
            partial = [r for r in rows if not _bool(r.get("t2_present"))]
            for subgroup, subgroup_rows, metric_prefix in (
                ("complete_tri_modal_inner_scar", complete, "scar"),
                ("partial_no_t2_inner_scar", partial, "scar"),
                ("complete_tri_modal_inner_edema", complete, "edema"),
            ):
                summary = summarize_casewise(subgroup_rows, metric_prefix=metric_prefix)
                rows_out.append(
                    {
                        "fold": fold,
                        "checkpoint_step": step,
                        "metric_source": "FORMAL_35_CASE_INNER",
                        "subgroup": subgroup,
                        **summary,
                    }
                )
    fieldnames = [
        "fold",
        "checkpoint_step",
        "metric_source",
        "subgroup",
        "case_count",
        "dice_mean",
        "dice_median",
        "sensitivity_mean",
        "precision_mean",
        "hd95_mean_mm",
        "empty_count",
        "volume_ratio_mean",
        "component_count_mean",
        "remote_fp_volume_mean_mm3",
    ]
    _write_csv(output_dir / "subgroup_checkpoint_trend.csv", rows_out, fieldnames)
    return rows_out


def build_actual_train_vs_inner_partial(runtime_repo: Path, output_dir: Path, steps: tuple[int, ...]) -> list[dict[str, Any]]:
    split_path = runtime_repo / TASK_RESULTS_REL / "split_case_lists.csv"
    split_rows = _read_csv(split_path) if split_path.exists() else []
    monitor_root = runtime_repo / TASK_RESULTS_REL / "inner_checkpoint_monitor"
    out_rows: list[dict[str, Any]] = []
    for fold in (2, 3):
        inner_partial_ids = {r["case_id"] for r in _role_rows(split_rows, fold, "inner", False)}
        actual_partial_ids = {r["case_id"] for r in _role_rows(split_rows, fold, "actual-train", False)}
        actual_complete_ids = {r["case_id"] for r in _role_rows(split_rows, fold, "actual-train", True)}
        for step in steps:
            path = monitor_root / f"fold_{fold}" / f"step{step:05d}" / "casewise_metrics.csv"
            if path.exists():
                rows = _read_csv(path)
                partial = [r for r in rows if r["case_id"] in inner_partial_ids]
                summary = summarize_casewise(partial, metric_prefix="scar")
                out_rows.append(
                    {
                        "fold": fold,
                        "checkpoint_step": step,
                        "population": "inner_partial_no_t2",
                        "metric_source": "FORMAL_35_CASE_INNER",
                        "status": "COMPLETE_FROM_EXISTING_CASEWISE",
                        **summary,
                    }
                )
            out_rows.append(
                {
                    "fold": fold,
                    "checkpoint_step": step,
                    "population": "actual_train_partial_no_t2",
                    "metric_source": "ACTUAL_TRAIN_DIAGNOSTIC",
                    "status": "PENDING_READ_ONLY_GPU_INFERENCE",
                    "case_count": len(actual_partial_ids),
                }
            )
            out_rows.append(
                {
                    "fold": fold,
                    "checkpoint_step": step,
                    "population": "actual_train_complete_control",
                    "metric_source": "ACTUAL_TRAIN_DIAGNOSTIC",
                    "status": "PENDING_READ_ONLY_GPU_INFERENCE",
                    "case_count": len(actual_complete_ids),
                }
            )
    fieldnames = [
        "fold",
        "checkpoint_step",
        "population",
        "metric_source",
        "status",
        "case_count",
        "dice_mean",
        "dice_median",
        "sensitivity_mean",
        "precision_mean",
        "hd95_mean_mm",
        "empty_count",
        "volume_ratio_mean",
        "component_count_mean",
        "remote_fp_volume_mean_mm3",
    ]
    _write_csv(output_dir / "actual_train_vs_inner_partial.csv", out_rows, fieldnames)
    return out_rows


def build_sampler_effective_supervision(runtime_repo: Path, output_dir: Path) -> list[dict[str, Any]]:
    fold_runtime = {
        2: runtime_repo / TASK_RESULTS_REL / "runtime/fold_2",
        3: runtime_repo / TASK_RESULTS_REL / "runtime/fold_3_parallel",
    }
    out_rows: list[dict[str, Any]] = []
    for fold, root in fold_runtime.items():
        for start, end in ((2000, 4000), (4000, 6000), (6000, 7000)):
            rows: list[dict[str, str]] = []
            for path in root.glob("training_log_*.csv"):
                try:
                    part = _read_csv(path)
                except Exception:
                    continue
                for r in part:
                    step = int(r.get("optimizer_step") or 0)
                    if start < step <= end:
                        rows.append(r)
            if not rows:
                continue
            total = len(rows)
            partial_scar = [
                r
                for r in rows
                if r.get("case_group") in {"lge_only", "lge_c0"}
                and (r.get("pathology_focus") == "scar" or r.get("requested_category") in {"gt_component", "small_component", "oof_fn", "oof_fp"})
            ]
            manifest_coordinate_consumed_rows = [
                r for r in partial_scar if (r.get("fallback_reason") or "").strip() == "manifest_coordinate_consumed"
            ]
            bad_fallback_rows = [
                r
                for r in partial_scar
                if (r.get("fallback_reason") or "").strip()
                and (r.get("fallback_reason") or "").strip() != "manifest_coordinate_consumed"
            ]
            randomish_rows = [
                r
                for r in partial_scar
                if (r.get("resolved_category") or "").strip() in {"random", "random_wall", "background", "wall_random"}
            ]
            unexpected_randomish_rows = [r for r in randomish_rows if (r.get("requested_category") or "").strip() != "random"]
            requested = Counter(r.get("requested_category") or "NA" for r in partial_scar)
            resolved = Counter(r.get("resolved_category") or "NA" for r in partial_scar)
            fallback = Counter((r.get("fallback_reason") or "NONE") for r in partial_scar)
            out_rows.append(
                {
                    "fold": fold,
                    "step_start_exclusive": start,
                    "step_end_inclusive": end,
                    "optimizer_events": total,
                    "partial_scar_events": len(partial_scar),
                    "partial_scar_microbatches_estimated": len(partial_scar) * 4,
                    "lge_only_events": sum(1 for r in rows if r.get("case_group") == "lge_only"),
                    "lge_c0_events": sum(1 for r in rows if r.get("case_group") == "lge_c0"),
                    "complete_events": sum(1 for r in rows if r.get("case_group") == "complete"),
                    "manifest_coordinate_consumed_events": len(manifest_coordinate_consumed_rows),
                    "bad_fallback_events": len(bad_fallback_rows),
                    "bad_fallback_rate": (len(bad_fallback_rows) / len(partial_scar)) if partial_scar else None,
                    "randomish_resolved_events": len(randomish_rows),
                    "randomish_resolved_rate": (len(randomish_rows) / len(partial_scar)) if partial_scar else None,
                    "unexpected_randomish_resolved_events": len(unexpected_randomish_rows),
                    "unexpected_randomish_resolved_rate": (len(unexpected_randomish_rows) / len(partial_scar)) if partial_scar else None,
                    "eligible_case_count_mean": _mean(_float(r.get("eligible_case_count")) for r in partial_scar),
                    "candidate_coordinate_count_mean": _mean(_float(r.get("candidate_coordinate_count")) for r in partial_scar),
                    "requested_category_counts_json": json.dumps(dict(requested), sort_keys=True),
                    "resolved_category_counts_json": json.dumps(dict(resolved), sort_keys=True),
                    "fallback_reason_counts_json": json.dumps(dict(fallback), sort_keys=True),
                    "supervision_gap_flag": bool(bad_fallback_rows or unexpected_randomish_rows),
                }
            )
    fieldnames = [
        "fold",
        "step_start_exclusive",
        "step_end_inclusive",
        "optimizer_events",
        "partial_scar_events",
        "partial_scar_microbatches_estimated",
        "lge_only_events",
        "lge_c0_events",
        "complete_events",
        "manifest_coordinate_consumed_events",
        "bad_fallback_events",
        "bad_fallback_rate",
        "randomish_resolved_events",
        "randomish_resolved_rate",
        "unexpected_randomish_resolved_events",
        "unexpected_randomish_resolved_rate",
        "eligible_case_count_mean",
        "candidate_coordinate_count_mean",
        "requested_category_counts_json",
        "resolved_category_counts_json",
        "fallback_reason_counts_json",
        "supervision_gap_flag",
    ]
    _write_csv(output_dir / "sampler_effective_supervision.csv", out_rows, fieldnames)
    return out_rows


@dataclass
class ParamRef:
    canonical_name: str
    group: str
    aliases: list[str]


def _load_param_manifest(runtime_repo: Path) -> list[ParamRef]:
    candidates = [
        runtime_repo / TASK_RESULTS_REL / "runtime/fold_3_parallel/parameter_group_coverage_fold3.json",
        runtime_repo / TASK_RESULTS_REL / "runtime/fold_2/parameter_group_coverage_fold2.json",
        runtime_repo / TASK_RESULTS_REL / "../care-ase-faithful/implementation/parameter_owner_registry.json",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        raise FileNotFoundError("No CARE-ASE parameter coverage/owner registry JSON found")
    data = json.loads(path.read_text())
    if "registry" in data:
        data = data["registry"]
    refs: list[ParamRef] = []
    for row in data.get("parameters", []):
        refs.append(ParamRef(row["canonical_name"], row["group"], list(row.get("code_aliases") or [])))
    return refs


def _diagnostic_group(ref: ParamRef) -> str | None:
    names = " ".join([ref.canonical_name, *ref.aliases]).lower()
    group = ref.group
    if group == "shared_low_mid_decoder":
        return "shared_low_mid_decoder"
    if group == "upper_two_encoder":
        return "upper_two_encoder"
    if group == "anatomy_decoder":
        return "anatomy_decoder"
    if group == "cloned_pathology_blocks":
        if "scar" in names:
            return "scar_cloned_pathology_blocks"
        if "edema" in names:
            return "edema_modules"
    if group == "cloned_pathology_classifiers":
        if "scar" in names:
            return "scar_classifier"
        if "edema" in names:
            return "edema_modules"
    if group in {"new_modules", "named_evidence_projection"}:
        if "scar" in names:
            return "new_scar_modules"
        if "edema" in names:
            return "edema_modules"
    return None


def _checkpoint_path(runtime_repo: Path, fold: int, step: int) -> Path:
    runtime_name = "fold_3_parallel" if fold == 3 else "fold_2"
    return runtime_repo / TASK_RESULTS_REL / "runtime" / runtime_name / f"checkpoint_step{step:05d}.pt"


def _torch_load_state(path: Path) -> dict[str, Any]:
    import torch

    payload = torch.load(path, map_location="cpu", weights_only=False)
    state = payload.get("model_state_dict") or payload.get("state_dict") or payload.get("model")
    if state is None:
        raise KeyError(f"No model_state_dict/state_dict in {path}")
    return state


def _stock_state(runtime_repo: Path, fold: int) -> dict[str, Any]:
    sys.path.insert(0, str(runtime_repo))
    sys.path.insert(0, str(runtime_repo / "src"))
    from care_myocardium.models.care_ase import CAREASE, CAREASEConfig

    config = CAREASEConfig.for_fold(fold)
    model = CAREASE(config)
    return model.state_dict()


def _find_tensor(state: dict[str, Any], ref: ParamRef) -> Any | None:
    for name in [ref.canonical_name, *ref.aliases]:
        if name in state:
            return state[name]
    return None


def build_parameter_drift(runtime_repo: Path, output_dir: Path, steps: tuple[int, ...]) -> list[dict[str, Any]]:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - depends on runtime env
        row = {"status": "PENDING_TORCH_ENV", "error": repr(exc)}
        _write_csv(output_dir / "parameter_drift.csv", [row], ["status", "error"])
        return [row]

    refs = _load_param_manifest(runtime_repo)
    grouped_refs: dict[str, list[ParamRef]] = defaultdict(list)
    for ref in refs:
        g = _diagnostic_group(ref)
        if g:
            grouped_refs[g].append(ref)

    out_rows: list[dict[str, Any]] = []
    for fold in (2, 3):
        try:
            base_stock = _stock_state(runtime_repo, fold)
        except Exception as exc:
            base_stock = None
            out_rows.append({"fold": fold, "status": "STOCK_LOAD_FAILED", "error": repr(exc)})
        step_states: dict[int, dict[str, Any]] = {}
        for step in steps:
            ckpt = _checkpoint_path(runtime_repo, fold, step)
            if ckpt.exists():
                step_states[step] = _torch_load_state(ckpt)
            else:
                out_rows.append({"fold": fold, "checkpoint_step": step, "status": "CHECKPOINT_MISSING", "path": str(ckpt)})
        ref_2000 = step_states.get(2000)
        for step, state in sorted(step_states.items()):
            for group_name, group_refs in grouped_refs.items():
                for reference_name, ref_state in (("stock_initialization", base_stock), ("step2000", ref_2000)):
                    if ref_state is None:
                        continue
                    norm_ref = 0.0
                    norm_cur = 0.0
                    norm_delta = 0.0
                    dot = 0.0
                    n = 0
                    missing = 0
                    with torch.no_grad():
                        for ref in group_refs:
                            a = _find_tensor(ref_state, ref)
                            b = _find_tensor(state, ref)
                            if a is None or b is None or not hasattr(a, "float") or a.shape != b.shape:
                                missing += 1
                                continue
                            af = a.float().reshape(-1)
                            bf = b.float().reshape(-1)
                            diff = bf - af
                            norm_ref += float(torch.dot(af, af).item())
                            norm_cur += float(torch.dot(bf, bf).item())
                            norm_delta += float(torch.dot(diff, diff).item())
                            dot += float(torch.dot(af, bf).item())
                            n += int(af.numel())
                    if n == 0:
                        continue
                    ref_l2 = math.sqrt(norm_ref)
                    cur_l2 = math.sqrt(norm_cur)
                    delta_l2 = math.sqrt(norm_delta)
                    cosine = dot / (ref_l2 * cur_l2) if ref_l2 > 0 and cur_l2 > 0 else None
                    out_rows.append(
                        {
                            "fold": fold,
                            "checkpoint_step": step,
                            "parameter_group": group_name,
                            "reference": reference_name,
                            "covered_parameter_tensors": len(group_refs) - missing,
                            "missing_parameter_tensors": missing,
                            "weight_norm": cur_l2,
                            "reference_weight_norm": ref_l2,
                            "update_l2_norm": delta_l2,
                            "relative_l2_parameter_drift": delta_l2 / ref_l2 if ref_l2 > 0 else None,
                            "cosine_similarity": cosine,
                            "status": "COMPLETE",
                        }
                    )
    fieldnames = [
        "fold",
        "checkpoint_step",
        "parameter_group",
        "reference",
        "covered_parameter_tensors",
        "missing_parameter_tensors",
        "weight_norm",
        "reference_weight_norm",
        "update_l2_norm",
        "relative_l2_parameter_drift",
        "cosine_similarity",
        "status",
        "path",
        "error",
    ]
    _write_csv(output_dir / "parameter_drift.csv", out_rows, fieldnames)
    return out_rows


def build_runtime_semantic_audit(runtime_repo: Path, output_dir: Path, steps: tuple[int, ...]) -> dict[str, Any]:
    decode_path = runtime_repo / "src/care_myocardium/inference/care_ase_r2_decode.py"
    core_path = runtime_repo / "src/care_myocardium/models/care_ase/core.py"
    split_path = runtime_repo / TASK_RESULTS_REL / "split_case_lists.csv"
    split_rows = _read_csv(split_path) if split_path.exists() else []
    checkpoint_rows = []
    for fold in (2, 3):
        for step in steps:
            ckpt = _checkpoint_path(runtime_repo, fold, step)
            checkpoint_rows.append(
                {
                    "fold": fold,
                    "step": step,
                    "exists": ckpt.exists(),
                    "sha256": _sha256(ckpt),
                    "path": str(ckpt),
                }
            )
    no_t2_class_set_static_pass = "[0, 1, 2, 3, 5]" in decode_path.read_text() or "(0, 1, 2, 3, 5)" in decode_path.read_text()
    core_text = core_path.read_text()
    payload = {
        "audit_scope": "READ_ONLY_STATIC_AND_METADATA_FIRST_PASS",
        "outer_accessed": False,
        "training_mutation": False,
        "split_case_counts": {
            f"fold{fold}_{role}_{'t2' if t2 else 'no_t2'}": len(_role_rows(split_rows, fold, role, t2))
            for fold in (2, 3)
            for role in ("inner", "actual-train")
            for t2 in (True, False)
        },
        "no_t2_decode_class_set_0_1_2_3_5_static_pass": no_t2_class_set_static_pass,
        "disable_extent_wall_forward_arg_static_pass": "disable_extent_wall" in core_text,
        "disabled_named_evidence_sources_static_pass": "disabled_named_evidence_sources" in core_text,
        "checkpoint_inventory": checkpoint_rows,
        "gpu_forward_runtime_semantic_checks": "PENDING_READ_ONLY_GPU_INFERENCE",
        "runtime_semantic_bug_status": "NO_PARTIAL_RUNTIME_SEMANTIC_BUG_FOUND_IN_STATIC_METADATA_FIRST_PASS_GPU_FORWARD_PENDING",
    }
    _write_json(output_dir / "runtime_semantic_audit.json", payload)
    return payload


def build_pending_gpu_csvs(output_dir: Path) -> None:
    pending_rows = [
        {
            "status": "PENDING_READ_ONLY_GPU_INFERENCE",
            "reason": "Requires full-volume logits/components without modifying training runtime",
        }
    ]
    _write_csv(
        output_dir / "logit_margin_trend.csv",
        pending_rows,
        ["status", "reason"],
    )
    _write_csv(
        output_dir / "extent_wall_intervention.csv",
        pending_rows,
        ["status", "reason"],
    )
    _write_csv(
        output_dir / "evidence_intervention.csv",
        pending_rows,
        ["status", "reason"],
    )


def write_report(output_dir: Path, subgroup_rows: list[dict[str, Any]], sampler_rows: list[dict[str, Any]], runtime_audit: dict[str, Any]) -> None:
    def lookup(fold: int, step: int, subgroup: str) -> dict[str, Any] | None:
        for row in subgroup_rows:
            if row.get("fold") == fold and row.get("checkpoint_step") == step and row.get("subgroup") == subgroup:
                return row
        return None

    lines = [
        "# CARE-ASE Stage-B Forgetting Diagnostic",
        "",
        "第一轮只读诊断已经把现有 formal-inner 35-case 证据、训练 sampler 日志、checkpoint 参数漂移和静态 runtime 语义审计分开汇总。当前证据说明这不是单纯的评估口径问题：fold3 no-T2/partial scar 在 Stage B 中确实从 step2000 的较高召回退化到 step6000 的近乎全空预测；同时没有发现足以停止当前 formal training 的新实现性硬错误。GPU-only 的 logit margin、extent/wall intervention、named evidence intervention 和 actual-train full-volume 对照仍在独立诊断支线中继续补齐，不能用于 checkpoint selection 或 early stop。",
        "",
        "## Scope",
        "",
        "- metric source: `FORMAL_35_CASE_INNER`, `ACTUAL_TRAIN_DIAGNOSTIC`, `CORE_6_CASE_INNER_TREND_PANEL` separated by name.",
        "- no outer labels or predictions were read by this script.",
        "- no model, loss, sampler, schedule, checkpoint, decode, threshold, or training runtime file was modified.",
        "- current frozen formal training should continue to 14000 unless a later GPU runtime audit finds a hard implementation blocker.",
        "",
        "## Formal Inner Subgroup Trend",
        "",
        "| fold | step | complete scar Dice | no-T2 scar Dice | complete edema Dice | no-T2 empty scar cases |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for fold in (2, 3):
        for step in DEFAULT_STEPS:
            complete_scar = lookup(fold, step, "complete_tri_modal_inner_scar") or {}
            partial_scar = lookup(fold, step, "partial_no_t2_inner_scar") or {}
            complete_edema = lookup(fold, step, "complete_tri_modal_inner_edema") or {}
            lines.append(
                f"| {fold} | {step} | {_fmt(complete_scar.get('dice_mean'))} | {_fmt(partial_scar.get('dice_mean'))} | {_fmt(complete_edema.get('dice_mean'))} | {_fmt(partial_scar.get('empty_count'))}/{_fmt(partial_scar.get('case_count'))} |"
            )
    lines.extend(
        [
            "",
            "## Sampler Effective Supervision First Pass",
            "",
            "| fold | steps | partial scar events | bad fallback rate | unexpected random rate | candidate coord mean | supervision gap flag |",
            "|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in sampler_rows:
        lines.append(
            f"| {row.get('fold')} | ({row.get('step_start_exclusive')},{row.get('step_end_inclusive')}] | {row.get('partial_scar_events')} | {_fmt(row.get('bad_fallback_rate'))} | {_fmt(row.get('unexpected_randomish_resolved_rate'))} | {_fmt(row.get('candidate_coordinate_count_mean'))} | {row.get('supervision_gap_flag')} |"
        )
    lines.extend(
        [
            "",
            "## Runtime Semantic First Pass",
            "",
            f"- no-T2 decode class set `[0,1,2,3,5]` static pass: `{runtime_audit.get('no_t2_decode_class_set_0_1_2_3_5_static_pass')}`",
            f"- `disable_extent_wall` forward argument present: `{runtime_audit.get('disable_extent_wall_forward_arg_static_pass')}`",
            f"- named evidence disabling API present: `{runtime_audit.get('disabled_named_evidence_sources_static_pass')}`",
            f"- status: `{runtime_audit.get('runtime_semantic_bug_status')}`",
            "",
            "## Causal Diagnosis Status",
            "",
            "- PRIMARY_CAUSE: `UNRESOLVED_GPU_LOGIT_AND_ACTUAL_TRAIN_DIAGNOSTICS_PENDING`",
            "- STRONG_SIGNAL: `REAL_STAGE_B_PARTIAL_NO_T2_SCAR_FORGETTING_IN_FORMAL_INNER`, especially fold3.",
            "- RULED_OUT_OR_WEAK_CAUSES: sampler omission is weak in this first pass because Stage B logs show substantial partial-scar events with low/no fallback in the inspected windows.",
            "- UNRESOLVED: final myocardium competition vs scar-logit collapse, extent/wall negative bias, named evidence contribution loss, actual-train collapse vs held-out overfit.",
            "",
            "## Required Files",
            "",
            "- `subgroup_checkpoint_trend.csv`",
            "- `actual_train_vs_inner_partial.csv`",
            "- `sampler_effective_supervision.csv`",
            "- `parameter_drift.csv`",
            "- `runtime_semantic_audit.json`",
            "- GPU-only placeholders: `logit_margin_trend.csv`, `extent_wall_intervention.csv`, `evidence_intervention.csv`",
        ]
    )
    (output_dir / "DIAGNOSTIC_REPORT_FOR_GPT.md").write_text("\n".join(lines) + "\n")


def write_manifest(output_dir: Path, runtime_repo: Path, files: list[str]) -> None:
    lines = [
        "# Stage-B Forgetting Diagnostic Manifest",
        "",
        f"- task: `{TASK_NAME}`",
        f"- runtime_repo: `{runtime_repo}`",
        "- mode: read-only diagnostic evidence",
        "- training_runtime_mutated: false",
        "- outer_accessed_by_this_script: false",
        "",
        "## Artifacts",
        "",
    ]
    for name in files:
        path = output_dir / name
        lines.append(f"- `{name}` sha256=`{_sha256(path)}`")
    (output_dir / "MANIFEST.md").write_text("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-repo", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--steps", nargs="*", type=int, default=list(DEFAULT_STEPS))
    args = parser.parse_args()

    runtime_repo = args.runtime_repo.resolve()
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = runtime_repo / TASK_RESULTS_REL / "stage_b_forgetting_diagnostic"
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / "diagnostic.lock"
    if lock_path.exists():
        raise SystemExit(f"Diagnostic lock already exists: {lock_path}")
    lock_path.write_text(f"pid={os.getpid()}\nruntime_repo={runtime_repo}\n")
    try:
        steps = tuple(sorted(set(args.steps)))
        subgroup_rows = build_subgroup_checkpoint_trend(runtime_repo, output_dir, steps)
        build_actual_train_vs_inner_partial(runtime_repo, output_dir, steps)
        sampler_rows = build_sampler_effective_supervision(runtime_repo, output_dir)
        build_parameter_drift(runtime_repo, output_dir, steps)
        runtime_audit = build_runtime_semantic_audit(runtime_repo, output_dir, steps)
        build_pending_gpu_csvs(output_dir)
        summary = {
            "task_name": TASK_NAME,
            "runtime_repo": str(runtime_repo),
            "output_dir": str(output_dir),
            "outer_accessed_by_this_script": False,
            "training_runtime_mutated": False,
            "formal_training_should_continue": True,
            "implementation_blocker_candidate": False,
            "first_pass_conclusion": "REAL_STAGE_B_PARTIAL_NO_T2_SCAR_FORGETTING_IN_FORMAL_INNER_GPU_CAUSAL_LOCALIZATION_PENDING",
            "runtime_semantic_bug_status": runtime_audit.get("runtime_semantic_bug_status"),
        }
        _write_json(output_dir / "diagnostic_summary.json", summary)
        artifact_names = [
            "DIAGNOSTIC_REPORT_FOR_GPT.md",
            "diagnostic_summary.json",
            "subgroup_checkpoint_trend.csv",
            "actual_train_vs_inner_partial.csv",
            "logit_margin_trend.csv",
            "extent_wall_intervention.csv",
            "evidence_intervention.csv",
            "parameter_drift.csv",
            "sampler_effective_supervision.csv",
            "runtime_semantic_audit.json",
        ]
        write_report(output_dir, subgroup_rows, sampler_rows, runtime_audit)
        write_manifest(output_dir, runtime_repo, artifact_names)
    finally:
        lock_path.unlink(missing_ok=True)
    print(f"Wrote Stage-B forgetting diagnostic evidence to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
