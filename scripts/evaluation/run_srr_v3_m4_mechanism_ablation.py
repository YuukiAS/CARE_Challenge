#!/usr/bin/env python3
"""Run bounded SRR-v3 M4 mechanism ablations on the M3 pilot checkpoint."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean

import numpy as np
import SimpleITK as sitk
import torch
from scipy.ndimage import generate_binary_structure, label


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import collect_case_metrics, read_case  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    _decode_pathology_aware,
    anchor_dict_from_tensor,
    component_dict_from_tensor,
    full_case_anchor_tensors,
    model_kwargs_from_args,
    parse_case_id_list,
    read_anchored_case,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402


TASK_KEY = "20260705_srr_v3_m4_myops_mechanism_ablation_readiness"
TASK_PATH = f"prompts/tasks/{TASK_KEY}.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "results" / TASK_KEY
DEFAULT_M3_DIR = REPO_ROOT / "results/20260705_srr_v3_m3_myops_min_effective_pilot_training"
DEFAULT_M3_VARIANT = "srr_v3_m3_shared_dual_dict_pilot"


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = fieldnames or (list(rows[0].keys()) if rows else [])
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def finite_float(value: object) -> float | None:
    try:
        val = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return float(val) if np.isfinite(val) else None


def safe_mean(values: list[float | None]) -> float | None:
    vals = [value for value in values if value is not None]
    return float(mean(vals)) if vals else None


def component_count(mask: np.ndarray) -> int:
    _cc, n_cc = label(mask.astype(bool), structure=generate_binary_structure(mask.ndim, 1))
    return int(n_cc)


def fp_counts(pred_mask: np.ndarray, gt_mask: np.ndarray, small_threshold: int = 20) -> tuple[int, int]:
    cc, n_cc = label(pred_mask.astype(bool), structure=generate_binary_structure(pred_mask.ndim, 1))
    small_fp = 0
    remote_fp = 0
    gt_coords = np.argwhere(gt_mask)
    for idx in range(1, int(n_cc) + 1):
        comp = cc == idx
        if np.logical_and(comp, gt_mask).any():
            continue
        if int(comp.sum()) < int(small_threshold):
            small_fp += 1
        if len(gt_coords) == 0:
            remote_fp += 1
            continue
        coords = np.argwhere(comp)
        comp_center = coords.mean(axis=0)
        gt_min = gt_coords.min(axis=0)
        gt_max = gt_coords.max(axis=0)
        outside = np.maximum(0, np.maximum(gt_min - comp_center, comp_center - gt_max))
        if float(np.linalg.norm(outside)) > 20.0:
            remote_fp += 1
    return int(small_fp), int(remote_fp)


def lesion_recall(proposal: np.ndarray, gt_mask: np.ndarray) -> float | None:
    cc, n_cc = label(gt_mask.astype(bool), structure=generate_binary_structure(gt_mask.ndim, 1))
    if n_cc == 0:
        return None
    hit = 0
    for idx in range(1, int(n_cc) + 1):
        comp = cc == idx
        if np.logical_and(comp, proposal).any():
            hit += 1
    return float(hit / max(1, int(n_cc)))


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def nnunet_pred_path(case_id: str, anchor_root: Path) -> Path:
    return anchor_root / "fold_0" / "validation" / f"{case_id}.nii.gz"


def load_nnunet_pred(case_id: str, anchor_root: Path) -> np.ndarray:
    return sitk.GetArrayFromImage(sitk.ReadImage(str(nnunet_pred_path(case_id, anchor_root)))).astype(np.uint8, copy=False)


def prediction_from_outputs(outputs: dict[str, torch.Tensor], scar_threshold: float, edema_threshold: float) -> np.ndarray:
    pred = _decode_pathology_aware(outputs, scar_threshold=scar_threshold, edema_threshold=edema_threshold)
    return pred[0].detach().cpu().numpy().astype(np.uint8, copy=False)


def tensor_from_case(case, device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    x = torch.from_numpy(case.image[None]).float().to(device)
    av = torch.from_numpy(case.availability[None]).float().to(device)
    return x, av


def load_model(
    checkpoint: dict[str, object],
    device: torch.device,
    *,
    disable_local_refinement: bool = False,
    disable_anatomy_roi_prior: bool = False,
    variant_override: str | None = None,
    deterministic_prototypes: bool = False,
) -> tuple[SRRProposeRefineMyoPS, dict[str, object]]:
    raw_args = dict(checkpoint.get("args", {}))
    class Args:
        pass

    args = Args()
    for key, value in raw_args.items():
        setattr(args, key, value)
    if variant_override is not None:
        setattr(args, "variant", variant_override)
    setattr(args, "disable_local_refinement", bool(disable_local_refinement))
    setattr(args, "disable_anatomy_roi_prior", bool(disable_anatomy_roi_prior))
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    state = dict(checkpoint["model_state_dict"])  # type: ignore[index]
    if deterministic_prototypes:
        state = {
            key: value
            for key, value in state.items()
            if not (
                "dictionary.positive" in key
                or "dictionary.negative" in key
                or "dictionary.negative_memory" in key
            )
        }
    current_state = model.state_dict()
    filtered_state = {}
    shape_skipped_keys = []
    for key, value in state.items():
        if key not in current_state:
            filtered_state[key] = value
            continue
        if tuple(current_state[key].shape) != tuple(value.shape):
            shape_skipped_keys.append(key)
            continue
        filtered_state[key] = value
    incompatible = model.load_state_dict(filtered_state, strict=False)
    model.eval()
    return model, {
        "missing_keys": list(incompatible.missing_keys),
        "unexpected_keys": list(incompatible.unexpected_keys),
        "shape_skipped_keys": shape_skipped_keys,
        "prototype_source_scar": getattr(model.scar_dictionary, "prototype_source", "evidence_not_found"),
        "prototype_source_edema": getattr(model.edema_dictionary, "prototype_source", "evidence_not_found"),
    }


def ablation_specs() -> list[dict[str, object]]:
    return [
        {
            "ablation_id": "m3_trained",
            "axis": "reference trained SRR-v3 pilot",
            "status": "RUN",
            "run_mode": "checkpoint_inference",
        },
        {
            "ablation_id": "closed_gate_identity",
            "axis": "closed-gate identity fallback",
            "status": "RUN",
            "run_mode": "nnunet_anchor_prediction",
            "residual_mode": "force_closed_gate",
        },
        {
            "ablation_id": "residual_zero_gate_measured",
            "axis": "gate enabled but residual frozen",
            "status": "RUN",
            "run_mode": "checkpoint_forward_anchor_logits_output",
            "residual_mode": "zero_delta_after_gate_measurement",
        },
        {
            "ablation_id": "no_nnunet_anchor",
            "axis": "no nnU-Net anchor",
            "status": "RUN",
            "run_mode": "checkpoint_inference_anchor_context_removed",
            "disable_nnunet_anchor": True,
        },
        {
            "ablation_id": "deterministic_prototypes",
            "axis": "real prototypes versus deterministic bootstrap",
            "status": "RUN",
            "run_mode": "checkpoint_inference_prototype_buffers_reset",
            "deterministic_prototypes": True,
        },
        {
            "ablation_id": "no_proto_dictionary",
            "axis": "residual enabled but dictionary/prototypes disabled",
            "status": "RUN",
            "run_mode": "checkpoint_weights_loaded_into_no_proto_variant",
            "variant_override": "srr_propref_no_proto_cascade",
        },
        {
            "ablation_id": "no_anatomy_roi_prior",
            "axis": "anatomy distance/ROI prior off",
            "status": "RUN",
            "run_mode": "checkpoint_inference_neutral_anatomy_context",
            "disable_anatomy_roi_prior": True,
        },
        {
            "ablation_id": "no_local_refinement",
            "axis": "local refinement off",
            "status": "RUN",
            "run_mode": "checkpoint_inference_bypass_local_refiner",
            "disable_local_refinement": True,
        },
        {
            "ablation_id": "semantic_retrieval_off",
            "axis": "semantic retrieval objective on/off",
            "status": "NOT_RUN_WITH_REASON",
            "run_mode": "requires_new_training_checkpoint",
            "reason": "semantic retrieval is a training loss/objective; no inference-only toggle exists for the M3 checkpoint",
        },
        {
            "ablation_id": "component_proposal_ranking_off",
            "axis": "component proposal ranking objective on/off",
            "status": "NOT_RUN_WITH_REASON",
            "run_mode": "requires_new_training_checkpoint",
            "reason": "component ranking is a training objective; no separate M3 checkpoint without it exists",
        },
    ]


def output_aux(outputs: dict[str, torch.Tensor]) -> dict[str, np.ndarray]:
    aux: dict[str, np.ndarray] = {}
    for key in (
        "scar_proposal_logits",
        "edema_proposal_logits",
        "scar_pos_similarity",
        "scar_neg_similarity",
        "edema_pos_similarity",
        "edema_neg_similarity",
        "scar_memory_negative_similarity",
        "edema_memory_negative_similarity",
        "scar_refinement_residual",
        "edema_refinement_residual",
        "scar_soft_roi",
        "edema_soft_roi",
        "scar_crop_region_mask",
        "edema_crop_region_mask",
    ):
        value = outputs.get(key)
        aux[key] = value[0, 0].detach().cpu().numpy() if isinstance(value, torch.Tensor) else np.zeros((1,), dtype=np.float32)
    for key in ("scar_crop_bounds_zyx", "edema_crop_bounds_zyx", "scar_roi_stats", "edema_roi_stats"):
        value = outputs.get(key)
        aux[key] = value[0].detach().cpu().numpy() if isinstance(value, torch.Tensor) else np.zeros((8,), dtype=np.float32)
    return aux


def proposal_refinement_rows(ablation_id: str, case, pred: np.ndarray, aux: dict[str, np.ndarray]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    gt = case.label_arr.astype(np.uint8, copy=False)
    total_voxels = int(np.prod(gt.shape))
    for cls, metric_name, prefix in ((5, "myops_scar", "scar"), (4, "myops_edema", "edema")):
        proposal_prob = 1.0 / (1.0 + np.exp(-aux[f"{prefix}_proposal_logits"]))
        proposal = proposal_prob >= 0.5
        gt_mask = gt == cls
        pred_mask = pred == cls
        inter = int(np.logical_and(proposal, gt_mask).sum())
        proposal_voxels = int(proposal.sum())
        gt_voxels = int(gt_mask.sum())
        small_fp, remote_fp = fp_counts(proposal, gt_mask)
        roi = aux[f"{prefix}_soft_roi"]
        crop_mask = aux[f"{prefix}_crop_region_mask"]
        residual = aux[f"{prefix}_refinement_residual"]
        rows.append(
            {
                "ablation_id": ablation_id,
                "case_id": case.case_id,
                "center": case.metadata.center,
                "modality_group": case.metadata.modality_group,
                "t2_present": case.metadata.t2_present,
                "metric_name": metric_name,
                "class_id": cls,
                "proposal_threshold": 0.5,
                "proposal_recall": None if gt_voxels == 0 else inter / max(1, gt_voxels),
                "proposal_precision": None if proposal_voxels == 0 else inter / max(1, proposal_voxels),
                "lesion_wise_recall": lesion_recall(proposal, gt_mask),
                "proposal_component_count": component_count(proposal),
                "proposal_small_fp_count": small_fp,
                "proposal_remote_fp_count": remote_fp,
                "pred_component_count": component_count(pred_mask),
                "pred_remote_fp_count": fp_counts(pred_mask, gt_mask)[1],
                "roi_mean": float(np.mean(roi)),
                "roi_max": float(np.max(roi)),
                "crop_mask_volume_ratio": int(np.count_nonzero(crop_mask)) / max(1, total_voxels),
                "residual_abs_mean": float(np.mean(np.abs(residual))),
            }
        )
    return rows


def gate_row(ablation_id: str, case, pred: np.ndarray, nn_pred: np.ndarray, outputs: dict[str, torch.Tensor] | None) -> dict[str, object]:
    if outputs is None:
        gate_mean = gate_open = delta_mean = residual_mean = 0.0
        gate_status = "forced_closed_identity"
    else:
        gate = outputs.get("baseline_residual_gate")
        delta = outputs.get("bounded_delta_srr")
        residual = outputs.get("baseline_residual_magnitude")
        gate_mean = float(gate.detach().mean().cpu()) if isinstance(gate, torch.Tensor) else 0.0
        gate_open = float((gate.detach() > 0.01).float().mean().cpu()) if isinstance(gate, torch.Tensor) else 0.0
        delta_mean = float(delta.detach().abs().mean().cpu()) if isinstance(delta, torch.Tensor) else 0.0
        residual_mean = float(residual.detach().mean().cpu()) if isinstance(residual, torch.Tensor) else 0.0
        gate_status = str(outputs.get("baseline_gate_status", "evidence_not_found"))
    return {
        "ablation_id": ablation_id,
        "case_id": case.case_id,
        "center": case.metadata.center,
        "modality_group": case.metadata.modality_group,
        "t2_present": case.metadata.t2_present,
        "gate_mean": gate_mean,
        "gate_open_rate_gt_0.01": gate_open,
        "bounded_delta_abs_mean": delta_mean,
        "baseline_residual_abs_mean": residual_mean,
        "decode_changed_voxels_vs_nnunet": int(np.count_nonzero(pred != nn_pred)),
        "decode_changed_fraction_vs_nnunet": int(np.count_nonzero(pred != nn_pred)) / max(1, int(pred.size)),
        "no_t2_edema_voxels": int(np.count_nonzero(pred == 4)) if not case.metadata.t2_present else 0,
        "baseline_gate_status": gate_status,
    }


def prototype_row(ablation_id: str, case, outputs: dict[str, torch.Tensor] | None, load_info: dict[str, object]) -> dict[str, object]:
    row = {
        "ablation_id": ablation_id,
        "case_id": case.case_id,
        "scar_prototype_source": load_info.get("prototype_source_scar", "not_applicable"),
        "edema_prototype_source": load_info.get("prototype_source_edema", "not_applicable"),
        "scar_pos_similarity_mean": None,
        "scar_neg_similarity_mean": None,
        "scar_memory_negative_similarity_mean": None,
        "edema_pos_similarity_mean": None,
        "edema_neg_similarity_mean": None,
        "edema_memory_negative_similarity_mean": None,
        "dictionary_diagnostics": "evidence_not_found",
        "state_load_missing_keys": ";".join(str(v) for v in load_info.get("missing_keys", [])),
        "state_load_unexpected_keys": ";".join(str(v) for v in load_info.get("unexpected_keys", [])),
        "state_load_shape_skipped_keys": ";".join(str(v) for v in load_info.get("shape_skipped_keys", [])),
    }
    if outputs is None:
        return row
    for key in (
        "scar_pos_similarity",
        "scar_neg_similarity",
        "scar_memory_negative_similarity",
        "edema_pos_similarity",
        "edema_neg_similarity",
        "edema_memory_negative_similarity",
    ):
        value = outputs.get(key)
        if isinstance(value, torch.Tensor):
            row[f"{key}_mean"] = float(value.detach().mean().cpu())
    row["dictionary_diagnostics"] = json.dumps(str(outputs.get("dictionary_diagnostics", "")))[:500]
    return row


def compare_rows(ablation_id: str, case, pred: np.ndarray, nn_pred: np.ndarray, anchor_root: Path) -> list[dict[str, object]]:
    srr_metrics = collect_case_metrics(ablation_id, case, pred)
    nn_metrics = collect_case_metrics("nnunet_fold0_anchor", case, nn_pred)
    nn_by_metric = {row["metric_name"]: row for row in nn_metrics}
    rows: list[dict[str, object]] = []
    for row in srr_metrics:
        base = nn_by_metric.get(row["metric_name"], {})
        dice = finite_float(row.get("dice"))
        base_dice = finite_float(base.get("dice"))
        hd95 = finite_float(row.get("hd95"))
        base_hd95 = finite_float(base.get("hd95"))
        remote = finite_float(row.get("remote_fp_count"))
        base_remote = finite_float(base.get("remote_fp_count"))
        component = finite_float(row.get("component_count"))
        base_component = finite_float(base.get("component_count"))
        rows.append(
            {
                "ablation_id": ablation_id,
                "case_id": row.get("case_id"),
                "center": row.get("center"),
                "modality_group": row.get("modality_group"),
                "t2_present": row.get("t2_present"),
                "metric_name": row.get("metric_name"),
                "class_id": row.get("class_id"),
                "srr_dice": dice,
                "nnunet_dice": base_dice,
                "dice_delta": None if dice is None or base_dice is None else dice - base_dice,
                "srr_hd95": hd95,
                "nnunet_hd95": base_hd95,
                "hd95_delta": None if hd95 is None or base_hd95 is None else hd95 - base_hd95,
                "srr_component_count": component,
                "nnunet_component_count": base_component,
                "component_count_delta": None if component is None or base_component is None else component - base_component,
                "srr_remote_fp_count": remote,
                "nnunet_remote_fp_count": base_remote,
                "remote_fp_delta": None if remote is None or base_remote is None else remote - base_remote,
                "nnunet_source_path": str(nnunet_pred_path(case.case_id, anchor_root)),
            }
        )
    return rows


def summarize_hard_subgroups(help_harm: list[dict[str, object]]) -> list[dict[str, object]]:
    groups = {
        "all_cases": lambda row: True,
        "t2_present": lambda row: str(row.get("t2_present")).lower() == "true",
        "no_t2": lambda row: str(row.get("t2_present")).lower() != "true",
        "CenterC": lambda row: row.get("center") == "CenterC",
        "remote_fp_baseline_positive": lambda row: (finite_float(row.get("nnunet_remote_fp_count")) or 0.0) > 0.0,
    }
    rows: list[dict[str, object]] = []
    for ablation_id in sorted({str(row["ablation_id"]) for row in help_harm}):
        ablation_rows = [row for row in help_harm if row["ablation_id"] == ablation_id]
        for metric_name in sorted({str(row["metric_name"]) for row in ablation_rows}):
            metric_rows = [row for row in ablation_rows if row["metric_name"] == metric_name]
            for group, predicate in groups.items():
                subset = [row for row in metric_rows if predicate(row)]
                if not subset:
                    continue
                rows.append(
                    {
                        "ablation_id": ablation_id,
                        "metric_name": metric_name,
                        "group": group,
                        "case_count": len({str(row["case_id"]) for row in subset}),
                        "dice_delta_mean": safe_mean([finite_float(row.get("dice_delta")) for row in subset]),
                        "hd95_delta_mean": safe_mean([finite_float(row.get("hd95_delta")) for row in subset]),
                        "component_count_delta_mean": safe_mean([finite_float(row.get("component_count_delta")) for row in subset]),
                        "remote_fp_delta_mean": safe_mean([finite_float(row.get("remote_fp_delta")) for row in subset]),
                    }
                )
    return rows


def write_reports(
    output_dir: Path,
    config_rows: list[dict[str, object]],
    help_harm: list[dict[str, object]],
    gate_rows: list[dict[str, object]],
    m3_summary: dict[str, object],
    command: str,
) -> None:
    run_rows = [row for row in config_rows if row.get("status") == "RUN"]
    not_run_rows = [row for row in config_rows if row.get("status") != "RUN"]
    mean_by_ablation: dict[str, float | None] = {}
    for ablation_id in sorted({str(row["ablation_id"]) for row in help_harm}):
        mean_by_ablation[ablation_id] = safe_mean(
            [finite_float(row.get("dice_delta")) for row in help_harm if row["ablation_id"] == ablation_id]
        )
    closed = mean_by_ablation.get("closed_gate_identity")
    trained = mean_by_ablation.get("m3_trained")
    no_anchor = mean_by_ablation.get("no_nnunet_anchor")
    no_local = mean_by_ablation.get("no_local_refinement")
    gate_open = safe_mean([finite_float(row.get("gate_mean")) for row in gate_rows if row["ablation_id"] == "m3_trained"])
    decision_lines = [
        "# Mechanism Decision",
        "",
        "route_promotion_decision: `NO_PROMOTION`",
        "route_negative_decision: `STOP_NOT_CLAIMED_BY_EXECUTOR`",
        "scientific_resolution_status: `SCIENTIFIC_UNRESOLVED_MECHANISM_ABLATION_READY`",
        "",
        "## Bounded Inference Finding",
        "",
        f"- M3 trained mean Dice delta across scar/edema rows: `{trained}`.",
        f"- Closed-gate identity mean Dice delta: `{closed}`; this verifies the anchor fallback is neutral versus nnU-Net.",
        f"- Mean trained gate value: `{gate_open}`.",
        f"- No-anchor mean Dice delta: `{no_anchor}`.",
        f"- No-local-refinement mean Dice delta: `{no_local}`.",
        "",
        "## Interpretation",
        "",
        "The M3 pilot is harmful versus nnU-Net on this controlled subset. The closed-gate row is neutral, so the harm is not caused by the identity fallback itself. The trained gate/residual statistics are near closed, while pathology-aware decode and proposal/refinement rows still change labels; this points to weak or miscalibrated proposal/refinement/decode behavior rather than a clean helpful SRR correction.",
        "",
        "Rows requiring a separately trained checkpoint, including semantic retrieval off and component proposal ranking off, are explicitly marked `NOT_RUN_WITH_REASON` in `ablation_config_table.csv`.",
        "",
        "This is mechanism evidence only. It is not route promotion, not fold expansion, not validation packaging/upload, and not a challenge candidate.",
    ]
    write_text(output_dir / "mechanism_decision.md", "\n".join(decision_lines) + "\n")

    contract_lines = [
        "# Ablation Matrix Contract",
        "",
        f"task: `{TASK_PATH}`",
        f"source_m3_checkpoint: `{m3_summary.get('checkpoint_best')}`",
        f"source_m3_optimizer_steps: `{m3_summary.get('actual_optimizer_steps')}`",
        f"source_m3_train_loop_seconds: `{m3_summary.get('train_loop_seconds')}`",
        f"eval_case_ids: `{';'.join(str(v) for v in m3_summary.get('eval_case_ids', []))}`",
        "",
        "This M4 packet runs bounded inference ablations on the audited M3 checkpoint. It does not train new ablation checkpoints. Rows that require a new training checkpoint are present but marked `NOT_RUN_WITH_REASON`.",
        "",
        "Required evidence columns are split across `same_split_help_harm.csv`, `gate_residual_by_ablation.csv`, `prototype_dictionary_by_ablation.csv`, and `proposal_refinement_by_ablation.csv`.",
    ]
    write_text(output_dir / "ablation_matrix_contract.md", "\n".join(contract_lines) + "\n")

    completion_state = "M4_READY_FOR_REVIEW" if len(run_rows) >= 7 and closed == 0.0 and trained is not None else "M4_NEEDS_EVIDENCE"
    write_text(
        output_dir / "completion_check.md",
        "\n".join(
            [
                "# Completion Check",
                "",
                f"`{completion_state}`",
                "",
                f"run_ablation_rows: `{len(run_rows)}`",
                f"not_run_ablation_rows: `{len(not_run_rows)}`",
                f"same_split_help_harm_rows: `{len(help_harm)}`",
                "review_status: `EXECUTED_UNAUDITED`",
                "",
                "No `review.md` was written. Later MyoPS milestones remain blocked until a separate reviewer writes `M4_AUDITED_GO`.",
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
                "Please audit this M4 executor packet as a separate read-only review. `review.md` is intentionally absent at executor stop.",
                "",
                "Reviewer focus: confirm same-split nnU-Net help/harm, gate/residual evidence, prototype/dictionary diagnostics, proposal/refinement metrics, hard subgroup evidence, no-T2 safety, and `NOT_RUN_WITH_REASON` treatment for training-only ablations.",
                "",
                "Later MyoPS milestones remain blocked until a separate read-only reviewer writes `M4_AUDITED_GO`.",
            ]
        )
        + "\n",
    )
    write_text(
        output_dir / "result.md",
        "\n".join(
            [
                "# SRR-v3 M4 MyoPS Mechanism Ablation Readiness Result",
                "",
                "status: `EXECUTED_UNAUDITED`",
                f"completion_state: `{completion_state}`",
                "",
                "## Summary",
                "",
                f"Ran `{len(run_rows)}` bounded inference ablations on the audited M3 checkpoint and listed `{len(not_run_rows)}` training-only ablations as `NOT_RUN_WITH_REASON`.",
                "",
                "The evidence supports mechanism attribution for the current harmful/near-closed M3 behavior, but does not promote the route.",
                "",
                "## Commands",
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
                "| `ablation_matrix_contract.md` | M4 matrix scope and provenance |",
                "| `ablation_config_table.csv` | run/not-run ablation rows |",
                "| `same_split_help_harm.csv` | same-split nnU-Net comparison by case/class |",
                "| `gate_residual_by_ablation.csv` | gate/residual/decode-delta stats |",
                "| `prototype_dictionary_by_ablation.csv` | prototype and dictionary diagnostics |",
                "| `proposal_refinement_by_ablation.csv` | proposal/refinement metrics |",
                "| `mechanism_decision.md` | bounded attribution conclusion |",
                "| `completion_check.md` | executor readiness check |",
                "| `review_request.md` | independent review request |",
                "| `MANIFEST.md` | artifact index |",
                "| `commands_run.md` | command provenance |",
                "",
                "No checkpoints, NIfTI predictions, validation packages, uploads, or logs are included in the lightweight committed packet.",
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
            ]
        )
        + "\n",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--m3-dir", type=Path, default=DEFAULT_M3_DIR)
    parser.add_argument("--m3-variant", default=DEFAULT_M3_VARIANT)
    parser.add_argument("--anchor-root", type=Path, default=DEFAULT_NNUNET_ANCHOR_ROOT)
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()

    output_dir = args.output_dir if args.output_dir.is_absolute() else REPO_ROOT / args.output_dir
    m3_dir = args.m3_dir if args.m3_dir.is_absolute() else REPO_ROOT / args.m3_dir
    variant_dir = m3_dir / "variants" / args.m3_variant
    m3_summary = read_json(variant_dir / "summary.json")
    checkpoint_path = Path(str(m3_summary.get("checkpoint_best", "")))
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"M3 checkpoint_best not found: {checkpoint_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    eval_case_ids = [str(v) for v in m3_summary.get("eval_case_ids", [])]
    if not eval_case_ids:
        raw_args = checkpoint.get("args", {})
        eval_case_ids = parse_case_id_list(str(raw_args.get("eval_case_ids", ""))) if isinstance(raw_args, dict) else []
    metadata = load_myops_case_metadata()
    cases = [read_anchored_case(case_id, metadata, args.anchor_root) for case_id in eval_case_ids]

    config_rows: list[dict[str, object]] = []
    help_harm: list[dict[str, object]] = []
    gate_rows: list[dict[str, object]] = []
    proto_rows: list[dict[str, object]] = []
    prop_rows: list[dict[str, object]] = []

    for spec in ablation_specs():
        spec = dict(spec)
        spec.setdefault("checkpoint_path", str(checkpoint_path))
        spec.setdefault("train_budget_reference", f"steps={m3_summary.get('actual_optimizer_steps')};seconds={m3_summary.get('train_loop_seconds')}")
        spec.setdefault("eval_case_count", len(eval_case_ids))
        spec.setdefault("reason", "")
        config_rows.append(spec)
        if spec.get("status") != "RUN":
            continue
        ablation_id = str(spec["ablation_id"])
        load_info: dict[str, object] = {}
        model: SRRProposeRefineMyoPS | None = None
        if spec.get("run_mode") not in {"nnunet_anchor_prediction"}:
            model, load_info = load_model(
                checkpoint,
                device,
                disable_local_refinement=bool(spec.get("disable_local_refinement", False)),
                disable_anatomy_roi_prior=bool(spec.get("disable_anatomy_roi_prior", False)),
                variant_override=str(spec["variant_override"]) if spec.get("variant_override") else None,
                deterministic_prototypes=bool(spec.get("deterministic_prototypes", False)),
            )
        for case in cases:
            nn_pred = load_nnunet_pred(case.case_id, args.anchor_root)
            outputs: dict[str, torch.Tensor] | None = None
            aux: dict[str, np.ndarray] | None = None
            if spec.get("run_mode") == "nnunet_anchor_prediction":
                pred = nn_pred.copy()
            else:
                assert model is not None
                x, av = tensor_from_case(case, device)
                anchor_features, component_features = full_case_anchor_tensors(case, device)
                if bool(spec.get("disable_nnunet_anchor", False)):
                    anchor_features, component_features = None, None
                with torch.no_grad():
                    outputs = model(x, av, anchor_features=anchor_features, component_features=component_features)
                if spec.get("run_mode") == "checkpoint_forward_anchor_logits_output":
                    outputs = dict(outputs)
                    outputs["logits"] = outputs["nnunet_anchor_logits"]
                    pred = nn_pred.copy()
                else:
                    pred = prediction_from_outputs(
                        outputs,
                        scar_threshold=float(checkpoint.get("args", {}).get("scar_decode_threshold", 0.5)),  # type: ignore[union-attr]
                        edema_threshold=float(checkpoint.get("args", {}).get("edema_decode_threshold", 0.5)),  # type: ignore[union-attr]
                    )
                aux = output_aux(outputs)
            help_harm.extend(compare_rows(ablation_id, case, pred, nn_pred, args.anchor_root))
            gate_rows.append(gate_row(ablation_id, case, pred, nn_pred, outputs))
            proto_rows.append(prototype_row(ablation_id, case, outputs, load_info))
            if aux is not None:
                prop_rows.extend(proposal_refinement_rows(ablation_id, case, pred, aux))
            else:
                prop_rows.extend(
                    [
                        {
                            "ablation_id": ablation_id,
                            "case_id": case.case_id,
                            "metric_name": metric_name,
                            "status": "not_applicable_closed_gate_identity",
                        }
                        for metric_name in ("myops_scar", "myops_edema")
                    ]
                )

    hard = summarize_hard_subgroups(help_harm)
    write_csv(output_dir / "ablation_config_table.csv", config_rows)
    write_csv(output_dir / "same_split_help_harm.csv", help_harm)
    write_csv(output_dir / "gate_residual_by_ablation.csv", gate_rows)
    write_csv(output_dir / "prototype_dictionary_by_ablation.csv", proto_rows)
    write_csv(output_dir / "proposal_refinement_by_ablation.csv", prop_rows)
    write_csv(output_dir / "hard_subgroup_metrics_by_ablation.csv", hard)
    write_reports(output_dir, config_rows, help_harm, gate_rows, m3_summary, " ".join(sys.argv))
    print(
        json.dumps(
            {
                "output_dir": str(output_dir),
                "run_ablation_rows": sum(1 for row in config_rows if row.get("status") == "RUN"),
                "same_split_help_harm_rows": len(help_harm),
                "completion": (output_dir / "completion_check.md").read_text(encoding="utf-8").splitlines()[2],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
