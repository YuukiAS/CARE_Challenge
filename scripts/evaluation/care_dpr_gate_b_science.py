"""Shared CARE-DPR Gate B scientific-gate recomputation helpers."""

from __future__ import annotations

import math
from typing import Any

from scripts.evaluation.evaluate_care_dg import PATHOLOGIES, finite_mean

ANCHOR_NAME = "A0_nnunet_anchor"
DICE_DELTA_TOLERANCE = 0.005
HD95_RATIO_LIMIT = 1.05
REMOTE_FP_RATIO_LIMIT = 1.10
COMPONENT_COUNT_RATIO_LIMIT = 10.0


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def recompute_help_harm_from_casewise(
    casewise_rows: list[dict[str, Any]],
    *,
    population: str,
    model_name: str,
    anchor_name: str = ANCHOR_NAME,
    dice_delta_tolerance: float = DICE_DELTA_TOLERANCE,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    by = {
        (r.get("population"), r.get("model"), r.get("pathology"), r.get("case_id")): r
        for r in casewise_rows
    }
    rows: list[dict[str, Any]] = []
    summary: dict[str, dict[str, Any]] = {}
    for pathology in PATHOLOGIES:
        deltas: list[float] = []
        hd_ratios: list[float] = []
        remote_ratios: list[float] = []
        component_ratios: list[float] = []
        new_infinite = False
        for key, pred in by.items():
            pop, model, path, case_id = key
            if pop != population or model != model_name or path != pathology:
                continue
            anchor = by.get((population, anchor_name, pathology, case_id))
            if not anchor:
                continue
            dice_delta = _as_float(pred.get("dice")) - _as_float(anchor.get("dice"))
            hd_anchor = _as_float(anchor.get("hd95_mm"))
            hd_pred = _as_float(pred.get("hd95_mm"))
            exact_anchor_inf = _as_bool(anchor.get("exact_hd_is_infinite"))
            exact_pred_inf = _as_bool(pred.get("exact_hd_is_infinite"))
            remote_anchor = _as_float(anchor.get("remote_fp_volume_mm3"))
            remote_pred = _as_float(pred.get("remote_fp_volume_mm3"))
            comp_anchor = _as_float(anchor.get("component_count"))
            comp_pred = _as_float(pred.get("component_count"))
            help_harm = (
                "help"
                if dice_delta >= dice_delta_tolerance
                else "harm"
                if dice_delta <= -dice_delta_tolerance
                else "neutral"
            )
            rows.append(
                {
                    "population": population,
                    "case_id": case_id,
                    "pathology": pathology,
                    "anchor_dice": _as_float(anchor.get("dice")),
                    "dpr_dice": _as_float(pred.get("dice")),
                    "dice_delta": dice_delta,
                    "help_harm": help_harm,
                    "help_harm_dice_delta_threshold": dice_delta_tolerance,
                }
            )
            deltas.append(dice_delta)
            hd_ratios.append(hd_pred / max(hd_anchor, 1e-6) if math.isfinite(hd_pred) and math.isfinite(hd_anchor) else math.inf)
            remote_ratios.append(remote_pred / max(remote_anchor, 1e-6))
            component_ratios.append(comp_pred / max(comp_anchor, 1.0))
            if exact_pred_inf and not exact_anchor_inf:
                new_infinite = True
        help_count = sum(1 for row in rows if row["pathology"] == pathology and row["help_harm"] == "help")
        harm_count = sum(1 for row in rows if row["pathology"] == pathology and row["help_harm"] == "harm")
        summary[pathology] = {
            "dice_delta_mean": finite_mean(deltas),
            "hd95_ratio_mean": finite_mean(hd_ratios),
            "remote_fp_ratio_mean": finite_mean(remote_ratios),
            "component_count_ratio_mean": finite_mean(component_ratios),
            "help": help_count,
            "harm": harm_count,
            "help_ge_harm_minus_1": help_count >= harm_count - 1,
            "improves_by_ge_0.005": finite_mean(deltas) >= dice_delta_tolerance,
            "not_below_anchor_by_more_than_0.005": finite_mean(deltas) >= -dice_delta_tolerance,
            "hd95_le_1.05x_anchor": finite_mean(hd_ratios) <= HD95_RATIO_LIMIT,
            "no_new_infinite_exact_hd": not new_infinite,
            "remote_fp_le_1.10x_anchor": finite_mean(remote_ratios) <= REMOTE_FP_RATIO_LIMIT,
            "no_component_count_explosion": finite_mean(component_ratios) <= COMPONENT_COUNT_RATIO_LIMIT,
        }
    return rows, summary


def scientific_gate_from_casewise(
    casewise_rows: list[dict[str, Any]],
    no_t2_rows: list[dict[str, Any]],
    *,
    population: str,
    model_name: str,
    anchor_name: str = ANCHOR_NAME,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    help_harm_rows, delta_summary = recompute_help_harm_from_casewise(
        casewise_rows,
        population=population,
        model_name=model_name,
        anchor_name=anchor_name,
    )
    failures: list[str] = []
    for pathology in PATHOLOGIES:
        item = delta_summary[pathology]
        if not item["not_below_anchor_by_more_than_0.005"]:
            failures.append(f"{pathology}_dice_delta_lt_-0.005")
        if not item["help_ge_harm_minus_1"]:
            failures.append(f"{pathology}_help_lt_harm_minus_1")
        if not item["hd95_le_1.05x_anchor"]:
            failures.append(f"{pathology}_hd95_gt_1.05x_anchor")
        if not item["no_new_infinite_exact_hd"]:
            failures.append(f"{pathology}_new_infinite_exact_hd")
        if not item["remote_fp_le_1.10x_anchor"]:
            failures.append(f"{pathology}_remote_fp_gt_1.10x_anchor")
        if not item["no_component_count_explosion"]:
            failures.append(f"{pathology}_component_count_explosion")
    if not any(delta_summary[p]["improves_by_ge_0.005"] for p in PATHOLOGIES):
        failures.append("no_pathology_improves_by_at_least_0.005")
    if not all(row.get("status") == "PASS" for row in no_t2_rows):
        failures.append("no_t2_exact_zero_fail")
    gate = {
        "status": "PASS" if not failures else "FAIL",
        "failures": failures,
        "scientific_final_output_credit": 0 if failures else 1,
        "fold_expansion_authorized": False,
        "complete16_delta_summary": delta_summary,
        "help_harm_by_pathology": {
            pathology: {
                "help": delta_summary[pathology]["help"],
                "harm": delta_summary[pathology]["harm"],
                "help_ge_harm_minus_1": delta_summary[pathology]["help_ge_harm_minus_1"],
                "help_harm_dice_delta_threshold": DICE_DELTA_TOLERANCE,
            }
            for pathology in PATHOLOGIES
        },
        "contract_checks": {
            "per_pathology_dice_delta_ge_minus_0.005": all(delta_summary[p]["not_below_anchor_by_more_than_0.005"] for p in PATHOLOGIES),
            "at_least_one_pathology_dice_delta_ge_plus_0.005": any(delta_summary[p]["improves_by_ge_0.005"] for p in PATHOLOGIES),
            "per_pathology_help_ge_harm_minus_1": all(delta_summary[p]["help_ge_harm_minus_1"] for p in PATHOLOGIES),
            "per_pathology_hd95_le_1.05x_anchor": all(delta_summary[p]["hd95_le_1.05x_anchor"] for p in PATHOLOGIES),
            "no_new_infinite_exact_hd": all(delta_summary[p]["no_new_infinite_exact_hd"] for p in PATHOLOGIES),
            "remote_fp_le_1.10x_anchor": all(delta_summary[p]["remote_fp_le_1.10x_anchor"] for p in PATHOLOGIES),
            "component_count_no_order_explosion": all(delta_summary[p]["no_component_count_explosion"] for p in PATHOLOGIES),
            "no_t2_exact_zero": all(row.get("status") == "PASS" for row in no_t2_rows),
        },
    }
    return gate, help_harm_rows
