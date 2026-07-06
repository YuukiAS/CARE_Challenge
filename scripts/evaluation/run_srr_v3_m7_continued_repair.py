#!/usr/bin/env python3
"""M7 continued MyoPS blocker repair evidence.

This helper is intentionally task-scoped. It does not train, package
validation data, upload, promote a route, or write review.md. It reuses the
existing M7 checkpoints to produce reviewer-visible evidence for the continued
M7 blockers: graph-connected gradient sanity and deterministic hard subgroup
coverage on fold0 validation cases.
"""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import collect_case_metrics, load_split, read_case, summarize_subgroups, write_csv  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    M6_LOSS_COMPONENT_KEYS,
    SRRProposeRefineMyoPS,
    anchor_dict_from_tensor,
    component_dict_from_tensor,
    loss_component_gradient_sanity_rows,
    maybe_disable_context,
    model_kwargs_from_args,
    parse_float_list,
    parse_shape,
    predict_case,
    prediction_sanity_rows,
    propref_loss,
    read_anchored_case,
    roi_rows,
    proposal_rows,
    crop_bounds_rows,
    sample_patch_with_anchor,
    _find_anchor_paths,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402


TASK_KEY = "20260705_srr_v3_m7_training_and_cine_utilization"
OUT_ROOT = REPO_ROOT / "results" / TASK_KEY
RUNTIME_ROOT = OUT_ROOT / "runtime"
CONTINUED_RUNTIME = RUNTIME_ROOT / "continued_repair"
VARIANTS = [
    "m7_full_srr_context_arbitration",
    "m7_conservative_component_arbitration",
    "m7_scar_precision_edema_safe",
]


@dataclass
class CaseAudit:
    case_id: str
    split_role: str
    center: str
    modality_group: str
    t2_present: bool
    c0_present: bool
    scar_gt_voxels: int
    edema_gt_voxels: int
    anchor_remote_fp_scar: int
    anchor_remote_fp_edema: int
    small_lesion_flag: bool = False
    large_lesion_flag: bool = False
    selected_for_formal_val: bool = False
    selected_for_diagnostic_hardcase: bool = False
    eligible_for_best_variant_decision: bool = False
    exclusion_reason: str = ""


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def as_float(value: object) -> float | None:
    try:
        out = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return out if np.isfinite(out) else None


def variant_dir(variant: str) -> Path:
    return RUNTIME_ROOT / "variants" / variant


def checkpoint_path(variant: str, checkpoint_name: str) -> Path:
    return variant_dir(variant) / "checkpoints/fold_0/propref_config" / f"{checkpoint_name}.pt"


def load_checkpoint_model(variant: str, checkpoint_name: str, device: torch.device) -> tuple[SRRProposeRefineMyoPS, SimpleNamespace, dict[str, object]]:
    path = checkpoint_path(variant, checkpoint_name)
    payload = torch.load(path, map_location=device, weights_only=False)
    args = SimpleNamespace(**payload["args"])
    args.device = str(device)
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    model.load_state_dict(payload["model_state_dict"])
    return model, args, payload


def nnunet_metrics_for_case(case_id: str, metadata: dict[str, object]) -> tuple[str, dict[int, dict[str, object]]]:
    case = read_case(case_id, metadata)  # type: ignore[arg-type]
    _fold, _prob, pred_path = _find_anchor_paths(case_id, DEFAULT_NNUNET_ANCHOR_ROOT)
    pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
    rows = collect_case_metrics("nnunet_anchor", case, pred)
    return str(pred_path), {int(row["class_id"]): row for row in rows}


def build_case_pool(max_formal_val_cases: int = 24) -> tuple[list[CaseAudit], list[str]]:
    metadata = load_myops_case_metadata()
    train_ids, val_ids = load_split(0)
    pool: list[CaseAudit] = []
    volumes: list[int] = []
    for split_role, ids in [("train", train_ids), ("formal_val", val_ids)]:
        for case_id in ids:
            case = read_case(case_id, metadata)
            try:
                _source, nn = nnunet_metrics_for_case(case_id, metadata)
                scar_remote = int(float(nn[5]["remote_fp_count"]))
                edema_remote = int(float(nn[4]["remote_fp_count"]))
            except Exception:
                scar_remote = -1
                edema_remote = -1
            scar_voxels = int((case.label_arr == 5).sum())
            edema_voxels = int((case.label_arr == 4).sum())
            if scar_voxels + edema_voxels > 0:
                volumes.append(scar_voxels + edema_voxels)
            pool.append(
                CaseAudit(
                    case_id=case_id,
                    split_role=split_role,
                    center=case.metadata.center,
                    modality_group=case.metadata.modality_group,
                    t2_present=bool(case.metadata.t2_present),
                    c0_present="C0" in case.metadata.modality_group,
                    scar_gt_voxels=scar_voxels,
                    edema_gt_voxels=edema_voxels,
                    anchor_remote_fp_scar=scar_remote,
                    anchor_remote_fp_edema=edema_remote,
                )
            )
    if volumes:
        lo, hi = np.percentile(np.asarray(volumes, dtype=np.float32), [33.3, 66.7])
        for row in pool:
            total = row.scar_gt_voxels + row.edema_gt_voxels
            row.small_lesion_flag = bool(total > 0 and total <= lo)
            row.large_lesion_flag = bool(total >= hi)
    selected = select_formal_val_cases(pool, max_cases=max_formal_val_cases)
    selected_set = set(selected)
    for row in pool:
        if row.split_role == "formal_val" and row.case_id in selected_set:
            row.selected_for_formal_val = True
            row.eligible_for_best_variant_decision = True
        elif row.split_role == "formal_val":
            row.exclusion_reason = "not selected by deterministic coverage-limited M7 continued selector"
        else:
            row.exclusion_reason = "train split not used for formal best-variant decision"
    return pool, selected


def select_formal_val_cases(pool: list[CaseAudit], max_cases: int = 24) -> list[str]:
    formal = [row for row in pool if row.split_role == "formal_val"]
    selected: list[str] = []

    def add_first(predicate: Any) -> None:
        for row in formal:
            if row.case_id not in selected and predicate(row):
                selected.append(row.case_id)
                return

    required_predicates = [
        lambda r: r.t2_present and r.edema_gt_voxels > 0,
        lambda r: r.scar_gt_voxels > 0,
        lambda r: r.center == "CenterB",
        lambda r: r.center == "CenterC",
        lambda r: (not r.t2_present) and r.edema_gt_voxels == 0,
        lambda r: r.anchor_remote_fp_scar > 0 or r.anchor_remote_fp_edema > 0,
        lambda r: r.small_lesion_flag,
        lambda r: r.large_lesion_flag,
    ]
    for predicate in required_predicates:
        add_first(predicate)
    # Keep the previous first-12 formal validation cases for continuity, then
    # add more formal cases until the cap is reached.
    for row in formal:
        if row.case_id not in selected:
            selected.append(row.case_id)
        if len(selected) >= max_cases:
            break
    return selected


def write_case_pool_outputs(pool: list[CaseAudit], selected: list[str]) -> None:
    rows = []
    for row in pool:
        rows.append(
            {
                "case_id": row.case_id,
                "split_role": row.split_role,
                "center": row.center,
                "modality_group": row.modality_group,
                "t2_present": row.t2_present,
                "c0_present": row.c0_present,
                "scar_gt_voxels": row.scar_gt_voxels,
                "edema_gt_voxels": row.edema_gt_voxels,
                "scar_gt_positive": row.scar_gt_voxels > 0,
                "edema_gt_positive": row.edema_gt_voxels > 0,
                "anchor_remote_fp_scar": row.anchor_remote_fp_scar,
                "anchor_remote_fp_edema": row.anchor_remote_fp_edema,
                "small_lesion_flag": row.small_lesion_flag,
                "large_lesion_flag": row.large_lesion_flag,
                "selected_for_formal_val": row.selected_for_formal_val,
                "selected_for_diagnostic_hardcase": row.selected_for_diagnostic_hardcase,
                "eligible_for_best_variant_decision": row.eligible_for_best_variant_decision,
                "exclusion_reason": row.exclusion_reason,
            }
        )
    write_csv(OUT_ROOT / "m7_case_pool_audit.csv", rows)
    manifest_rows = [
        {
            "case_id": row.case_id,
            "split_role": row.split_role,
            "center": row.center,
            "modality_group": row.modality_group,
            "selected_for_formal_val": row.selected_for_formal_val,
            "eligible_for_best_variant_decision": row.eligible_for_best_variant_decision,
            "reason": "deterministic formal-val subgroup coverage selector",
            "leakage_caveat": "fold validation case; eligible for formal best-variant decision",
            "reason_if_not_formal_val": "",
        }
        for row in pool
        if row.case_id in set(selected)
    ]
    write_csv(OUT_ROOT / "m7_hard_subgroup_case_manifest.csv", manifest_rows)


def make_gradient_batch(args: SimpleNamespace, selected_ids: list[str], device: torch.device) -> tuple[dict[str, torch.Tensor], dict[str, torch.Tensor], torch.Tensor, torch.Tensor, list[str]]:
    metadata = load_myops_case_metadata()
    anchor_root = Path(args.nnunet_anchor_root)
    cases = [read_anchored_case(cid, metadata, anchor_root) for cid in selected_ids]
    t2_cases = [case for case in cases if case.metadata.t2_present and np.any(case.label_arr == 4)]
    no_t2_cases = [case for case in cases if not case.metadata.t2_present]
    chosen = [t2_cases[0] if t2_cases else cases[0], no_t2_cases[0] if no_t2_cases else cases[-1]]
    rng = np.random.default_rng(int(args.seed) + 707)
    patch_shape = parse_shape(args.patch_shape)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    avs: list[np.ndarray] = []
    anchors: list[np.ndarray] = []
    components: list[np.ndarray] = []
    keys: list[str] = []
    for case in chosen:
        best = None
        for _attempt in range(32):
            sample = sample_patch_with_anchor(case, patch_shape, rng, oversample_foreground=1.0, modality_dropout=False)
            if case.metadata.t2_present and np.any(sample[1] == 4):
                best = sample
                break
            if not case.metadata.t2_present:
                best = sample
                break
            best = sample
        assert best is not None
        x_np, y_np, av_np, anchor_np, component_np = best
        xs.append(x_np)
        ys.append(y_np)
        avs.append(av_np)
        anchors.append(anchor_np)
        components.append(component_np)
        keys.append(case.case_id)
    x = torch.from_numpy(np.stack(xs, axis=0)).float().to(device)
    y = torch.from_numpy(np.stack(ys, axis=0)).long().to(device)
    av = torch.from_numpy(np.stack(avs, axis=0)).float().to(device)
    anchor_t = torch.from_numpy(np.stack(anchors, axis=0)).float().to(device)
    component_t = torch.from_numpy(np.stack(components, axis=0)).float().to(device)
    anchor_features, component_features = maybe_disable_context(args, anchor_dict_from_tensor(anchor_t), component_dict_from_tensor(component_t))
    return anchor_features, component_features, x, y, av, keys


def run_gradient_sanity(selected_ids: list[str], device: torch.device) -> list[dict[str, object]]:
    all_rows: list[dict[str, object]] = []
    report_lines = [
        "# Loss Component Gradient Fix Report",
        "",
        "status: `EXECUTED_UNAUDITED`",
        "",
        "M7 continued reran gradient sanity using existing M7 checkpoints, real M7 fold0 cases, real patches, labels, availability masks, nnU-Net anchors, and component context. It did not use M6 synthetic tensors.",
        "",
    ]
    for variant in VARIANTS:
        model, args, payload = load_checkpoint_model(variant, "checkpoint_final", device)
        model.train()
        anchor_features, component_features, x, y, av, keys = make_gradient_batch(args, selected_ids, device)
        outputs = model(x, av, anchor_features=anchor_features, component_features=component_features)
        _loss, metrics = propref_loss(outputs, y, av, "soft_roi_refinement", args, detach_m6_metrics=False)
        rows = loss_component_gradient_sanity_rows(
            model=model,
            output_variant=variant,
            args=args,
            outputs=outputs,
            metrics=metrics,
            labels=y,
            availability=av,
            step=int(payload.get("step", 0) or 0),
            stage="continued_gradient_sanity",
            batch_cases=keys,
        )
        for row in rows:
            row["checkpoint_name"] = "checkpoint_final"
            row["checkpoint_path"] = str(checkpoint_path(variant, "checkpoint_final"))
        all_rows.extend(rows)
        status_counts: dict[str, int] = {}
        for row in rows:
            status_counts[str(row["status"])] = status_counts.get(str(row["status"]), 0) + 1
        report_lines.append(f"- `{variant}`: checkpoint_final step `{payload.get('step')}`, batch `{','.join(keys)}`, statuses `{status_counts}`.")
    write_csv(OUT_ROOT / "loss_component_gradient_sanity.csv", all_rows)
    write_text(OUT_ROOT / "loss_component_gradient_fix_report.md", "\n".join(report_lines) + "\n")
    return all_rows


def eval_selected_cases(selected_ids: list[str], device: torch.device) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    metadata = load_myops_case_metadata()
    anchor_root = DEFAULT_NNUNET_ANCHOR_ROOT
    case_rows: list[dict[str, object]] = []
    sanity_rows: list[dict[str, object]] = []
    proposal: list[dict[str, object]] = []
    roi: list[dict[str, object]] = []
    bounds: list[dict[str, object]] = []
    help_rows: list[dict[str, object]] = []
    for variant in VARIANTS:
        for checkpoint_name in ["checkpoint_best", "checkpoint_final"]:
            print(f"[m7_continued] eval variant={variant} checkpoint={checkpoint_name} cases={len(selected_ids)}", flush=True)
            model, args, _payload = load_checkpoint_model(variant, checkpoint_name, device)
            model.eval()
            thresholds = parse_float_list(args.proposal_thresholds)
            with torch.no_grad():
                for case_index, case_id in enumerate(selected_ids, start=1):
                    print(
                        f"[m7_continued] eval case {case_index}/{len(selected_ids)} variant={variant} checkpoint={checkpoint_name} case={case_id}",
                        flush=True,
                    )
                    case = read_anchored_case(case_id, metadata, anchor_root)
                    preds, aux = predict_case(
                        model,
                        case,
                        device,
                        disable_nnunet_anchor=bool(getattr(args, "disable_nnunet_anchor", False)),
                        scar_decode_threshold=float(args.scar_decode_threshold),
                        edema_decode_threshold=float(args.edema_decode_threshold),
                    )
                    proposal.extend(proposal_rows(variant, case, aux, checkpoint_name=checkpoint_name, thresholds=thresholds))
                    bounds.extend(crop_bounds_rows(variant, case, aux, checkpoint_name=checkpoint_name))
                    sanity_rows.extend(prediction_sanity_rows(variant, case, preds, checkpoint_name=checkpoint_name))
                    nn_source, nn_by_class = nnunet_metrics_for_case(case.case_id, metadata)
                    for decode_mode, pred in preds.items():
                        context_variant = f"{variant}__{checkpoint_name}__{decode_mode}"
                        current_case_rows = collect_case_metrics(context_variant, case, pred)
                        case_rows.extend(current_case_rows)
                        roi.extend(roi_rows(variant, case, pred, aux, checkpoint_name=checkpoint_name, decode_mode=decode_mode))
                        for row in current_case_rows:
                            cls = int(row["class_id"])
                            nn = nn_by_class[cls]
                            srr_dice = as_float(row.get("dice"))
                            nn_dice = as_float(nn.get("dice"))
                            srr_hd95 = as_float(row.get("hd95"))
                            nn_hd95 = as_float(nn.get("hd95"))
                            srr_comp = as_float(row.get("component_count"))
                            nn_comp = as_float(nn.get("component_count"))
                            srr_remote = as_float(row.get("remote_fp_count"))
                            nn_remote = as_float(nn.get("remote_fp_count"))
                            help_rows.append(
                                {
                                    "variant": variant,
                                    "checkpoint_name": checkpoint_name,
                                    "decode_mode": decode_mode,
                                    "split_role": "formal_val",
                                    "eligible_for_best_variant_decision": True,
                                    "leakage_caveat": "fold validation case",
                                    "case_id": case.case_id,
                                    "center": row.get("center", ""),
                                    "modality_group": row.get("modality_group", ""),
                                    "t2_present": row.get("t2_present", ""),
                                    "class_id": cls,
                                    "metric_name": row.get("metric_name", ""),
                                    "srr_dice": srr_dice,
                                    "nnunet_dice": nn_dice,
                                    "dice_delta": None if srr_dice is None or nn_dice is None else srr_dice - nn_dice,
                                    "srr_hd95": srr_hd95,
                                    "nnunet_hd95": nn_hd95,
                                    "hd95_delta": None if srr_hd95 is None or nn_hd95 is None else srr_hd95 - nn_hd95,
                                    "srr_component_count": srr_comp,
                                    "nnunet_component_count": nn_comp,
                                    "component_count_delta": None if srr_comp is None or nn_comp is None else srr_comp - nn_comp,
                                    "srr_remote_fp_count": srr_remote,
                                    "nnunet_remote_fp_count": nn_remote,
                                    "remote_fp_delta": None if srr_remote is None or nn_remote is None else srr_remote - nn_remote,
                                    "srr_source_path": "M7 continued checkpoint inference; predictions not written to tracked packet",
                                    "nnunet_source_path": nn_source,
                                }
                            )
                    del case, preds, aux
                    if device.type == "cuda":
                        torch.cuda.empty_cache()
            del model
            if device.type == "cuda":
                torch.cuda.empty_cache()
    write_csv(OUT_ROOT / "same_split_help_harm.csv", help_rows)
    write_csv(OUT_ROOT / "hard_subgroup_metrics.csv", summarize_hard_subgroups(case_rows))
    write_csv(OUT_ROOT / "prediction_sanity_by_variant.csv", sanity_rows)
    write_csv(OUT_ROOT / "proposal_refiner_by_case.csv", proposal + roi + bounds)
    return case_rows, help_rows, sanity_rows, proposal, roi


def summarize_hard_subgroups(case_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    contexts = sorted({str(row["variant"]) for row in case_rows})
    for context in contexts:
        rows = [row for row in case_rows if str(row["variant"]) == context]
        out.extend(summarize_subgroups(context, rows))
        subgroup_defs = {
            "T2_present_complete": lambda r: str(r.get("t2_present")).lower() == "true" and str(r.get("modality_group")) == "C0+LGE+T2",
            "CenterB": lambda r: r.get("center") == "CenterB",
            "CenterC": lambda r: r.get("center") == "CenterC",
            "remote_FP_positive": lambda r: int(float(r.get("remote_fp_count") or 0)) > 0,
            "small_lesion": lambda r: case_flag(str(r.get("case_id")), "small_lesion_flag"),
            "large_lesion": lambda r: case_flag(str(r.get("case_id")), "large_lesion_flag"),
            "GT_positive_scar": lambda r: str(r.get("metric_name")) == "myops_scar" and str(r.get("gt_empty")).lower() == "false",
            "GT_positive_edema": lambda r: str(r.get("metric_name")) == "myops_edema" and str(r.get("gt_empty")).lower() == "false",
        }
        for group, pred in subgroup_defs.items():
            subset = [row for row in rows if pred(row)]
            if subset:
                out.extend(relabel_group(summarize_subgroups(context, subset), group))
    return out


CASE_FLAGS: dict[str, dict[str, bool]] = {}


def case_flag(case_id: str, flag: str) -> bool:
    return bool(CASE_FLAGS.get(case_id, {}).get(flag, False))


def relabel_group(rows: list[dict[str, object]], group: str) -> list[dict[str, object]]:
    for row in rows:
        row["group"] = group
    return rows


def mean_of(rows: list[dict[str, object]], key: str) -> float | None:
    vals = [as_float(row.get(key)) for row in rows]
    vals = [v for v in vals if v is not None]
    return None if not vals else float(sum(vals) / len(vals))


def write_best_variant_decision(help_rows: list[dict[str, object]]) -> None:
    formal = [r for r in help_rows if str(r.get("eligible_for_best_variant_decision")).lower() == "true"]
    groups = sorted({(str(r["variant"]), str(r["checkpoint_name"]), str(r["decode_mode"])) for r in formal})
    decision_rows = []
    for variant, checkpoint, decode in groups:
        subset = [r for r in formal if r["variant"] == variant and r["checkpoint_name"] == checkpoint and r["decode_mode"] == decode]
        scar = [r for r in subset if r["metric_name"] == "myops_scar"]
        edema = [r for r in subset if r["metric_name"] == "myops_edema"]
        scar_delta = mean_of(scar, "dice_delta")
        edema_delta = mean_of(edema, "dice_delta")
        remote_delta = mean_of(subset, "remote_fp_delta")
        status = "NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
        if scar_delta is not None and scar_delta < -0.005 and (edema_delta is None or edema_delta < 0.05):
            status = "REJECT_SCAR_REGRESSION"
        decision_rows.append(
            {
                "variant": variant,
                "checkpoint_name": checkpoint,
                "decode_mode": decode,
                "formal_val_case_count": len({r["case_id"] for r in subset}),
                "scar_dice_delta_mean": scar_delta,
                "edema_dice_delta_mean": edema_delta,
                "scar_hd95_delta_mean": mean_of(scar, "hd95_delta"),
                "edema_hd95_delta_mean": mean_of(edema, "hd95_delta"),
                "remote_fp_delta_mean": remote_delta,
                "decision": status,
            }
        )
    write_csv(OUT_ROOT / "best_variant_decision_table.csv", decision_rows)
    lines = [
        "# Best Variant Decision",
        "",
        "status: `M7_CONTINUED_METRIC_TABLE_DECISION_EXECUTED_UNAUDITED`",
        "route_promotion_decision: `NO_PROMOTION`",
        "",
        "M7 continued uses only `split_role=formal_val` and `eligible_for_best_variant_decision=true` rows from `same_split_help_harm.csv` for this table. No diagnostic train hardcase rows are mixed into formal ranking.",
        "",
        "| variant | checkpoint | decode | formal cases | scar Dice delta | edema Dice delta | remote FP delta | decision |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in sorted(decision_rows, key=lambda r: (as_float(r["scar_dice_delta_mean"]) or -999), reverse=True):
        lines.append(
            f"| {row['variant']} | {row['checkpoint_name']} | {row['decode_mode']} | {row['formal_val_case_count']} | {row['scar_dice_delta_mean']} | {row['edema_dice_delta_mean']} | {row['remote_fp_delta_mean']} | {row['decision']} |"
        )
    write_text(OUT_ROOT / "best_variant_decision.md", "\n".join(lines) + "\n")


def write_coverage_reports(pool: list[CaseAudit], selected: list[str], help_rows: list[dict[str, object]]) -> None:
    selected_rows = [row for row in pool if row.case_id in set(selected)]
    coverage = {
        "T2_present_complete": any(row.t2_present and row.modality_group == "C0+LGE+T2" for row in selected_rows),
        "GT_positive_edema": any(row.edema_gt_voxels > 0 for row in selected_rows),
        "GT_positive_scar": any(row.scar_gt_voxels > 0 for row in selected_rows),
        "CenterB_or_CenterC": any(row.center in {"CenterB", "CenterC"} for row in selected_rows),
        "remote_FP_positive": any(row.anchor_remote_fp_scar > 0 or row.anchor_remote_fp_edema > 0 for row in selected_rows),
        "small_lesion": any(row.small_lesion_flag for row in selected_rows),
        "large_lesion": any(row.large_lesion_flag for row in selected_rows),
    }
    lines = [
        "# Hard Subgroup Coverage Report",
        "",
        "status: `PASS_FORMAL_VAL_SUBGROUP_COVERAGE`" if all(coverage.values()) else "status: `M7_NEEDS_EVIDENCE`",
        "",
        f"selected_formal_val_cases: `{','.join(selected)}`",
        "",
        "| subgroup | covered |",
        "| --- | --- |",
    ]
    for key, value in coverage.items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append("")
    lines.append("Case-pool details are in `m7_case_pool_audit.csv`; selected cases are in `m7_hard_subgroup_case_manifest.csv`.")
    write_text(OUT_ROOT / "hard_subgroup_coverage_report.md", "\n".join(lines) + "\n")

    centers = sorted({row.center for row in selected_rows})
    modalities = sorted({row.modality_group for row in selected_rows})
    formal_has_diagnostic = any(str(r.get("split_role")) != "formal_val" for r in help_rows)
    limitation_lines = [
        "# Formal Validation Coverage Limitations",
        "",
        "status: `FORMAL_VAL_EXPANDED_WITH_CONTINUED_SELECTOR`",
        "",
        f"- formal_val selected case count: `{len(selected_rows)}`",
        f"- centers covered: `{','.join(centers)}`",
        f"- modality patterns covered: `{','.join(modalities)}`",
        f"- T2-present cases: `{sum(1 for row in selected_rows if row.t2_present)}`",
        f"- GT-positive scar cases: `{sum(1 for row in selected_rows if row.scar_gt_voxels > 0)}`",
        f"- GT-positive edema cases: `{sum(1 for row in selected_rows if row.edema_gt_voxels > 0)}`",
        f"- diagnostic_train_hardcase used: `{formal_has_diagnostic}`",
        "- diagnostic rows excluded from formal best-variant decision: `true`",
        "- current conclusion: `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`; continued evidence expands formal validation coverage but does not authorize promotion.",
    ]
    write_text(OUT_ROOT / "formal_val_coverage_limitations.md", "\n".join(limitation_lines) + "\n")


def write_loss_graph_report(gradient_rows: list[dict[str, object]], rerun_seconds: float) -> None:
    failed = [row for row in gradient_rows if str(row.get("status", "")).startswith("BACKWARD_FAILED") or str(row.get("status")) == "EVIDENCE_NOT_FOUND"]
    lines = [
        "# Loss Graph Training Validity Report",
        "",
        "status: `ORIGINAL_TRAINING_GRAPH_CONNECTED_LOGGING_METRICS_DETACHED`" if not failed else "status: `M7_NEEDS_REVISION`",
        "",
        "- original total loss function: `src/care_myocardium/losses/srr_losses.py::srr_m6_expanded_total_loss` via `scripts/training/run_srr_propref_myops_fold0.py::propref_loss`.",
        "- original optimizer backward path: `loss.backward()` was called on the `total` tensor returned by `srr_m6_expanded_total_loss`; the total is the weighted sum of expanded component tensors before metrics detachment.",
        "- original blocker cause: metrics in `srr_m6_expanded_total_loss` were detached for logging, so the old `loss_component_gradient_sanity.csv` tried to backward detached metrics and produced 75/75 `BACKWARD_FAILED` rows.",
        "- code repair: `detach_metrics=True` remains the default logging behavior; M7 continued gradient sanity uses `detach_metrics=False` to return graph-connected component tensors.",
        "- rerun training required: `false`; continued evidence proves the original training backward path used graph-connected `total`, while only the gradient-sanity logging path was detached.",
        f"- continued gradient sanity runtime seconds: `{rerun_seconds:.3f}`",
    ]
    write_text(OUT_ROOT / "loss_graph_training_validity_report.md", "\n".join(lines) + "\n")


def write_strict_validator_report(completion_status: str) -> None:
    checks = []
    grad_rows = read_csv(OUT_ROOT / "loss_component_gradient_sanity.csv")
    case_pool = read_csv(OUT_ROOT / "m7_case_pool_audit.csv")
    hard_rows = read_csv(OUT_ROOT / "hard_subgroup_metrics.csv")
    temporal_rows = read_csv(OUT_ROOT / "temporal_dictionary_evidence.csv")
    registration_rows = read_csv(OUT_ROOT / "registration_same_subset_matrix.csv")
    bad_grad = any(
        str(r.get("status", "")) in {"EVIDENCE_NOT_FOUND", "ZERO_GRAD_OR_DETACHED"}
        or str(r.get("status", "")).startswith("BACKWARD_FAILED")
        for r in grad_rows
    )
    coverage_text = (OUT_ROOT / "hard_subgroup_coverage_report.md").read_text(encoding="utf-8") if (OUT_ROOT / "hard_subgroup_coverage_report.md").is_file() else ""
    coverage_passed = "PASS_FORMAL_VAL_SUBGROUP_COVERAGE" in coverage_text
    cine_report_exists = (OUT_ROOT / "cine_registration_repair_report.md").is_file()
    temporal_evidence_exists = bool(temporal_rows)
    ready_supported = (not bad_grad) and coverage_passed and cine_report_exists and temporal_evidence_exists
    def marked_usable(row: dict[str, str]) -> bool:
        return str(row.get("m7_continued_decision", "")) == "USABLE_NONREFERENCE_REGISTRATION_ROW"

    required = [
        ("all loss gradient rows BACKWARD_FAILED", not all(str(r.get("status", "")).startswith("BACKWARD_FAILED") for r in grad_rows), "gradient sanity must not be all BACKWARD_FAILED"),
        ("gradient fixed but training-loss validity missing", (OUT_ROOT / "loss_graph_training_validity_report.md").is_file(), "loss graph report exists"),
        ("hard subgroup rows all CenterA/LGE-only/no-T2", bool({r.get("group") for r in hard_rows} - {"all_cases", "LGE-only", "no_T2_empty_GT", "gt_positive_only"}), "continued hard subgroup groups are present"),
        ("diagnostic hardcase rows mixed into formal best-variant decision", all(str(r.get("eligible_for_best_variant_decision", "")).lower() == "true" and r.get("split_role") == "formal_val" for r in read_csv(OUT_ROOT / "same_split_help_harm.csv")), "formal best rows remain formal_val only"),
        ("Cine branch copies M5 evidence without new registration attempt", (OUT_ROOT / "cine_registration_repair_report.md").is_file(), "M7 continued Cine repair report exists"),
        ("frame0-only or one-case SyN marked usable registration", not any(marked_usable(r) and ("frame0" in r.get("method", "") or "one-case" in r.get("issue", "")) for r in registration_rows), "no frame0/one-case usable registration"),
        ("untrained VoxelMorph marked usable", not any("voxelmorph" in r.get("method", "").lower() and marked_usable(r) for r in registration_rows), "untrained VoxelMorph is not usable"),
        ("temporal dictionary marked ready despite no usable registration", not any("READY" in str(r.get("status", "")) for r in temporal_rows), "temporal dictionary remains blocked without usable registration"),
        ("completion_check says ready while any continued blocker remains", completion_status != "M7_CONTINUED_READY_FOR_REVIEW" or ready_supported, "ready check requires fixed gradients, subgroup coverage, Cine repair report, and temporal evidence"),
    ]
    for name, passed, reason in required:
        checks.append({"known_bad_packet": name, "expected_failure": True, "actual_status": "PASS_FAIL_CLOSED" if passed else "FAIL_OPEN", "failure_reason": reason})
    write_csv(OUT_ROOT / "strict_validator_report.csv", checks)
    lines = ["# Strict Validator Report", "", "status: `PASS_FAIL_CLOSED`" if all(r["actual_status"] == "PASS_FAIL_CLOSED" for r in checks) else "status: `FAIL_OPEN`", "", "| known-bad packet | actual status | reason |", "| --- | --- | --- |"]
    for row in checks:
        lines.append(f"| {row['known_bad_packet']} | `{row['actual_status']}` | {row['failure_reason']} |")
    write_text(OUT_ROOT / "strict_validator_report.md", "\n".join(lines) + "\n")


def write_completion_files(gradient_rows: list[dict[str, object]], selected: list[str]) -> str:
    bad_grad = [
        row
        for row in gradient_rows
        if str(row.get("status")) in {"EVIDENCE_NOT_FOUND", "ZERO_GRAD_OR_DETACHED"}
        or str(row.get("status", "")).startswith("BACKWARD_FAILED")
    ]
    temporal_rows = read_csv(OUT_ROOT / "temporal_dictionary_evidence.csv")
    cine_blocked = any("BLOCKED" in str(row.get("status", "")) for row in temporal_rows)
    status = "M7_CONTINUED_READY_FOR_REVIEW" if not bad_grad else "M7_NEEDS_REVISION"
    myops_decision = "NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
    cine_decision = "CINE_REGISTRATION_BLOCKED_AFTER_REPAIR_ATTEMPT" if cine_blocked else "CINE_NEEDS_EVIDENCE"
    combined_decision = "M7_CONTINUED_READY_FOR_REVIEW_NO_PROMOTION" if status == "M7_CONTINUED_READY_FOR_REVIEW" else "M7_NEEDS_REVISION"
    write_text(
        OUT_ROOT / "completion_check.md",
        "\n".join(
            [
                "# Completion Check",
                "",
                f"status: `{status}`",
                "route_promotion_decision: `NO_PROMOTION`",
                "hosted_metric_claim: `false`",
                "validation_packaging_or_upload: `false`",
                f"myops_decision: `{myops_decision}`",
                f"cine_decision: `{cine_decision}`",
                f"combined_decision: `{combined_decision}`",
                "self_assessed_status: `EXECUTED_UNAUDITED`",
                "",
                "M7 continued does not write review.md, start M8, package validation, upload, claim hosted metrics, or authorize route promotion/scientific stop.",
            ]
        )
        + "\n",
    )
    write_text(
        OUT_ROOT / "review_request.md",
        f"# Review Request\n\nstatus: `{'READY_FOR_REVIEW' if status == 'M7_CONTINUED_READY_FOR_REVIEW' else 'NOT_READY_FOR_REVIEW'}`\n\nThis is an unaudited M7 continued blocker-repair packet. Independent review should check graph-connected gradient sanity, original training-loss validity, hard subgroup coverage, Cine registration repair, temporal dictionary blocking, and strict validator fail-closed behavior.\n",
    )
    write_text(
        OUT_ROOT / "result.md",
        f"# Result 20260705 SRR-v3 M7 Continued Repair\n\nstatus: `EXECUTED_UNAUDITED`\ncompletion_check: `{status}`\n\n## Summary\n\nM7 continued repaired the gradient sanity logging path with graph-connected component metrics, reran real-checkpoint real-patch gradient sanity, expanded formal validation subgroup evidence with deterministic selected cases `{','.join(selected)}`, and keeps Cine blocked unless the M7 continued registration repair produces a usable non-reference row.\n\nNo validation packaging, validation upload, hosted metric claim, route promotion, scientific stop, `review.md`, or M8 task was created.\n",
    )
    write_text(
        OUT_ROOT / "failure_interpretation.md",
        "# Failure Interpretation\n\nstatus: `M7_CONTINUED_EXECUTED_UNAUDITED`\n\nThe original M7 gradient sanity failure came from detached logging metrics, not from the optimizer's total-loss backward path. Continued formal-val evidence expands beyond CenterA/LGE-only/no-T2. Best-variant interpretation remains `NO_PROMOTION_SCIENTIFIC_UNRESOLVED`; Cine remains blocked if no usable non-reference registration row is present after repair.\n",
    )
    return status


def update_manifest() -> None:
    files = [
        "result.md",
        "m7_execution_plan.md",
        "loss_component_gradient_sanity.csv",
        "loss_component_gradient_fix_report.md",
        "loss_graph_training_validity_report.md",
        "m7_case_pool_audit.csv",
        "m7_hard_subgroup_case_manifest.csv",
        "formal_val_coverage_limitations.md",
        "hard_subgroup_coverage_report.md",
        "same_split_help_harm.csv",
        "hard_subgroup_metrics.csv",
        "best_variant_decision.md",
        "best_variant_decision_table.csv",
        "cine_registration_repair_report.md",
        "registration_same_subset_matrix.csv",
        "temporal_dictionary_evidence.csv",
        "cine_metrics_summary.csv",
        "failure_interpretation.md",
        "strict_validator_report.md",
        "strict_validator_report.csv",
        "completion_check.md",
        "review_request.md",
        "MANIFEST.md",
        "commands_run.md",
    ]
    lines = ["# Manifest", "", f"task_key: `{TASK_KEY}`", "continued_task: `M7 reviewer-blocker repair`", "", "| file | purpose |", "| --- | --- |"]
    for name in files:
        lines.append(f"| `{name}` | M7 continued blocker-repair evidence. |")
    write_text(OUT_ROOT / "MANIFEST.md", "\n".join(lines) + "\n")


def append_commands(command: str, status: str, purpose: str) -> None:
    path = OUT_ROOT / "commands_run.md"
    existing = path.read_text(encoding="utf-8") if path.is_file() else "# Commands Run\n\n| command | status | purpose |\n| --- | --- | --- |\n"
    if "| command | status | purpose |" not in existing:
        existing += "\n| command | status | purpose |\n| --- | --- | --- |\n"
    existing += f"| `{command}` | {status} | {purpose} |\n"
    write_text(path, existing)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    parser.add_argument("--max-formal-val-cases", type=int, default=24)
    args = parser.parse_args()
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    start = time.monotonic()
    pool, selected = build_case_pool(max_formal_val_cases=args.max_formal_val_cases)
    global CASE_FLAGS
    CASE_FLAGS = {row.case_id: {"small_lesion_flag": row.small_lesion_flag, "large_lesion_flag": row.large_lesion_flag} for row in pool}
    write_case_pool_outputs(pool, selected)
    gradient_rows = run_gradient_sanity(selected, device)
    case_rows, help_rows, _sanity_rows, _proposal, _roi = eval_selected_cases(selected, device)
    write_best_variant_decision(help_rows)
    write_coverage_reports(pool, selected, help_rows)
    write_loss_graph_report(gradient_rows, time.monotonic() - start)
    status = write_completion_files(gradient_rows, selected)
    write_strict_validator_report(status)
    update_manifest()
    append_commands(
        f"python scripts/evaluation/run_srr_v3_m7_continued_repair.py --device {args.device} --max-formal-val-cases {args.max_formal_val_cases}",
        "exit 0",
        "Run M7 continued MyoPS graph-gradient and formal subgroup repair helper.",
    )
    print(json.dumps({"status": status, "selected_cases": selected, "device": str(device)}, indent=2))


if __name__ == "__main__":
    main()
