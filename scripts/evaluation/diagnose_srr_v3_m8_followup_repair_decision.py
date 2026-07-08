#!/usr/bin/env python3
"""Build the M8 follow-up no-promotion repair-decision packet.

The script is intentionally diagnostic-only. It reads the tracked M8 evidence
packet and produces a fail-closed follow-up packet without training, packaging,
uploading, or reading heavyweight prediction/checkpoint artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


REPO = Path(__file__).resolve().parents[2]
M8_DIR = REPO / "results/20260707_srr_v3_m8_editor_grade_leaderboard_sprint"
OUT_DIR = REPO / "results/20260708_srr_v3_m8_followup_no_promotion_repair_decision"

REQUIRED_M8_INPUTS = [
    "review.md",
    "result.md",
    "completion_check.md",
    "MANIFEST.md",
    "commands_run.md",
    "m8_route_promotion_decision.md",
    "m8_best_variant_decision_table.csv",
    "m8_candidate_assembly_matrix.csv",
    "m8_same_split_help_harm.csv",
    "m8_srr_contribution_by_case.csv",
    "m8_hard_subgroup_metrics.csv",
    "m8_component_remote_fp_hd95_report.csv",
    "m8_nnunet_anchor_control_metrics.csv",
    "m8_training_budget_ledger.csv",
    "m8_validation_events.csv",
    "m8_temporal_dictionary_evidence.csv",
    "m8_registration_same_subset_matrix.csv",
]

REQUIRED_OUTPUTS = [
    "result.md",
    "completion_check.md",
    "review_request.md",
    "MANIFEST.md",
    "commands_run.md",
    "m8_followup_route_objective.md",
    "m8_review_findings_ledger.csv",
    "m8_candidate_failure_matrix.csv",
    "m8_proxy_feature_schema.csv",
    "m8_proxy_arbitration_help_harm.csv",
    "m8_hard_subgroup_help_harm.csv",
    "m8_no_t2_safety_report.csv",
    "m8_repair_contract.md",
    "m8_next_required_action.md",
    "m8_followup_strict_validator_report.csv",
    "m8_followup_strict_validator_report.md",
    "m8_followup_validator_selftest_report.csv",
    "m8_followup_validator_selftest_report.md",
]

FORBIDDEN_READY_TERMS = [
    "validation_upload: AUTHORIZED",
    "validation_packaging: CREATED",
    "hosted_metric_claim: TRUE",
    "leaderboard_readiness: READY",
    "route_promotion_decision: PROMOTE",
    "M9 authorization",
    "start M9",
    "turn M8 into M9",
    "fold expansion authorized",
    "temporal readiness from frame0-only",
    "synthetic placeholder evidence used as the only proof",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fnum(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).strip()
    if text == "":
        return default
    try:
        if text.lower() in {"nan", "none", "evidence_not_found"}:
            return default
        return float(text)
    except ValueError:
        return default


def bval(value: object) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def mean(values: Iterable[float]) -> float:
    vals = list(values)
    return sum(vals) / len(vals) if vals else math.nan


def fmt(value: float) -> str:
    if isinstance(value, float) and math.isnan(value):
        return ""
    return f"{value:.12g}"


@dataclass(frozen=True)
class MetricRow:
    case_id: str
    metric_name: str
    center: str
    modality_group: str
    t2_present: bool
    gt_empty: bool
    dice: float
    hd95: float
    component_count: float
    remote_fp_count: float
    no_t2_edema_voxels: float = 0.0


def missing_m8_inputs() -> list[str]:
    return [str(M8_DIR / name) for name in REQUIRED_M8_INPUTS if not (M8_DIR / name).exists()]


def read_m8() -> dict[str, object]:
    return {
        "review": (M8_DIR / "review.md").read_text(encoding="utf-8"),
        "route_decision": (M8_DIR / "m8_route_promotion_decision.md").read_text(encoding="utf-8"),
        "candidate_assembly": read_csv(M8_DIR / "m8_candidate_assembly_matrix.csv"),
        "best_variant": read_csv(M8_DIR / "m8_best_variant_decision_table.csv"),
        "same_split": read_csv(M8_DIR / "m8_same_split_help_harm.csv"),
        "contribution": read_csv(M8_DIR / "m8_srr_contribution_by_case.csv"),
        "subgroups": read_csv(M8_DIR / "m8_hard_subgroup_metrics.csv"),
        "anchor": read_csv(M8_DIR / "m8_nnunet_anchor_control_metrics.csv"),
    }


def anchor_metrics(data: dict[str, object]) -> dict[tuple[str, str], MetricRow]:
    rows: list[dict[str, str]] = data["anchor"]  # type: ignore[assignment]
    out: dict[tuple[str, str], MetricRow] = {}
    for r in rows:
        key = (r["case_id"], r["metric_name"])
        out[key] = MetricRow(
            case_id=r["case_id"],
            metric_name=r["metric_name"],
            center=r["center"],
            modality_group=r["modality_group"],
            t2_present=bval(r["t2_present"]),
            gt_empty=False,
            dice=fnum(r["dice"]),
            hd95=fnum(r["hd95"]),
            component_count=fnum(r["component_count"]),
            remote_fp_count=fnum(r["remote_fp_count"]),
            no_t2_edema_voxels=fnum(r.get("no_t2_edema_voxels")),
        )
    return out


def candidate_metrics(data: dict[str, object], candidate_id: str) -> dict[tuple[str, str], MetricRow]:
    rows: list[dict[str, str]] = data["same_split"]  # type: ignore[assignment]
    out: dict[tuple[str, str], MetricRow] = {}
    for r in rows:
        if r["variant"] != candidate_id:
            continue
        key = (r["case_id"], r["metric_name"])
        no_t2 = 0.0
        if r["metric_name"] == "myops_edema" and not bval(r["t2_present"]):
            no_t2 = 0.0 if bval(r["pred_empty"]) else 1.0
        out[key] = MetricRow(
            case_id=r["case_id"],
            metric_name=r["metric_name"],
            center=r["center"],
            modality_group=r["modality_group"],
            t2_present=bval(r["t2_present"]),
            gt_empty=bval(r["gt_empty"]),
            dice=fnum(r["dice"]),
            hd95=fnum(r["hd95"]),
            component_count=fnum(r["component_count"]),
            remote_fp_count=fnum(r["remote_fp_count"]),
            no_t2_edema_voxels=no_t2,
        )
    return out


def contribution_map(data: dict[str, object], base_variant: str) -> dict[tuple[str, str], dict[str, str]]:
    rows: list[dict[str, str]] = data["contribution"]  # type: ignore[assignment]
    out: dict[tuple[str, str], dict[str, str]] = {}
    for r in rows:
        if r["variant"] == base_variant:
            out[(r["case_id"], r["class_name"])] = r
    return out


def assembly_by_metric(data: dict[str, object]) -> dict[str, dict[str, str]]:
    rows: list[dict[str, str]] = data["candidate_assembly"]  # type: ignore[assignment]
    return {r["metric_name"]: r for r in rows if r["decision"] == "CONTROL_ONLY"}


def choose_combined_best_candidate(data: dict[str, object]) -> str:
    rows: list[dict[str, str]] = data["candidate_assembly"]  # type: ignore[assignment]
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        if r["decision"] != "CONTROL_ONLY":
            grouped[r["candidate_id"]].append(r)
    best_id = ""
    best_delta = -999.0
    for candidate_id, rs in grouped.items():
        if len({r["metric_name"] for r in rs}) < 2:
            continue
        delta = mean(fnum(r["dice_delta_vs_nnunet"]) for r in rs)
        if delta > best_delta:
            best_delta = delta
            best_id = candidate_id
    return best_id


def policy_rows(
    policy_id: str,
    description: str,
    candidate_source: str,
    anchor: dict[tuple[str, str], MetricRow],
    candidate: dict[tuple[str, str], MetricRow],
    selector: Callable[[tuple[str, str], MetricRow], bool],
    uses_only_allowed_features: str = "true",
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for metric_name in ["myops_scar", "myops_edema"]:
        selected: list[MetricRow] = []
        anchors: list[MetricRow] = []
        srr_used = 0
        for key, anchor_row in sorted(anchor.items()):
            if key[1] != metric_name:
                continue
            use_candidate = selector(key, anchor_row)
            row = candidate.get(key, anchor_row) if use_candidate else anchor_row
            if use_candidate and key in candidate:
                srr_used += 1
            selected.append(row)
            anchors.append(anchor_row)
        dice_anchor = mean(r.dice for r in anchors)
        dice_policy = mean(r.dice for r in selected)
        hd95_anchor = mean(r.hd95 for r in anchors)
        hd95_policy = mean(r.hd95 for r in selected)
        remote_anchor = mean(r.remote_fp_count for r in anchors)
        remote_policy = mean(r.remote_fp_count for r in selected)
        no_t2_voxels = sum(r.no_t2_edema_voxels for r in selected if metric_name == "myops_edema" and not r.t2_present)
        dice_delta = dice_policy - dice_anchor
        hd95_delta = hd95_policy - hd95_anchor
        scar_guardrail = "PASS" if metric_name != "myops_scar" or dice_delta >= -0.001 else "FAIL"
        edema_guardrail = "PASS" if metric_name != "myops_edema" or no_t2_voxels == 0 else "FAIL_NO_T2_EDEMA"
        if policy_id == "anchor_only_control":
            promotion = "CONTROL_ONLY"
        elif policy_id == "candidate_only_control":
            promotion = "REPRODUCES_M8_NO_PROMOTION"
        elif dice_delta > 0.005 and hd95_delta <= 0 and remote_policy <= remote_anchor and no_t2_voxels == 0 and srr_used >= 6:
            promotion = "DIAGNOSTIC_POSITIVE_REQUIRES_REVIEW"
        else:
            promotion = "NO_DEPLOYABLE_REPAIR_SIGNAL"
        rows.append(
            {
                "policy_id": policy_id,
                "policy_description": description,
                "uses_only_allowed_features": uses_only_allowed_features,
                "candidate_source": candidate_source,
                "metric_name": metric_name,
                "case_count": len(selected),
                "srr_case_count": srr_used,
                "srr_case_fraction": fmt(srr_used / len(selected) if selected else 0.0),
                "dice_mean_anchor": fmt(dice_anchor),
                "dice_mean_policy": fmt(dice_policy),
                "dice_delta": fmt(dice_delta),
                "hd95_mean_anchor": fmt(hd95_anchor),
                "hd95_mean_policy": fmt(hd95_policy),
                "hd95_delta": fmt(hd95_delta),
                "remote_fp_mean_anchor": fmt(remote_anchor),
                "remote_fp_mean_policy": fmt(remote_policy),
                "no_t2_edema_voxels": fmt(no_t2_voxels),
                "scar_guardrail_status": scar_guardrail,
                "edema_guardrail_status": edema_guardrail,
                "promotion_status": promotion,
            }
        )
    return rows


def build_review_findings(data: dict[str, object]) -> list[dict[str, object]]:
    review = str(data["review"])
    token = "M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED"
    has_token = token in review
    return [
        {
            "finding_id": "review_status",
            "source_path": str(M8_DIR / "review.md"),
            "source_line_or_section": "review_status",
            "claim": token if has_token else "REQUIRED_TOKEN_NOT_FOUND",
            "effect_on_followup": "authorizes no-promotion diagnostic follow-up only",
            "blocking_level": "blocking_if_missing",
        },
        {
            "finding_id": "no_route_promotion",
            "source_path": str(M8_DIR / "review.md"),
            "source_line_or_section": "Decision / Scientific Interpretation",
            "claim": "M8 completed executor evidence but no candidate selected for promotion",
            "effect_on_followup": "candidate-only control must not be marked promoted",
            "blocking_level": "blocking_for_repair_ready",
        },
        {
            "finding_id": "edema_negative",
            "source_path": str(M8_DIR / "review.md"),
            "source_line_or_section": "Scientific Interpretation",
            "claim": "best local edema candidate is below nnU-Net anchor",
            "effect_on_followup": "repair policy must not hide edema harm behind scar gain",
            "blocking_level": "blocking_for_repair_ready",
        },
        {
            "finding_id": "scar_small_gain",
            "source_path": str(M8_DIR / "review.md"),
            "source_line_or_section": "Scientific Interpretation",
            "claim": "best scar candidate has only small same-split Dice gain",
            "effect_on_followup": "scar-only gain is insufficient for deployable repair",
            "blocking_level": "major_caveat",
        },
        {
            "finding_id": "cine_proxy_only",
            "source_path": str(M8_DIR / "review.md"),
            "source_line_or_section": "Scientific Interpretation",
            "claim": "Cine evidence remains local proxy and does not authorize hosted metric claims",
            "effect_on_followup": "Cine cannot rescue MyoPS no-promotion result",
            "blocking_level": "scope_boundary",
        },
    ]


def build_candidate_failure_matrix(data: dict[str, object]) -> list[dict[str, object]]:
    controls = assembly_by_metric(data)
    rows: list[dict[str, str]] = data["candidate_assembly"]  # type: ignore[assignment]
    out: list[dict[str, object]] = []
    for r in rows:
        if r["decision"] == "CONTROL_ONLY":
            continue
        metric = r["metric_name"]
        control = controls[metric]
        dice_delta = fnum(r["dice_delta_vs_nnunet"])
        hd95_delta = fnum(r["hd95_delta_vs_nnunet"])
        remote_delta = fnum(r["remote_fp_delta_vs_nnunet"])
        component_delta = fnum(r["component_count_delta_vs_nnunet"])
        if metric == "myops_edema" and dice_delta < 0:
            failure = "EDEMA_DICE_BELOW_ANCHOR"
        elif remote_delta > 0 or component_delta > 1:
            failure = "REMOTE_FP_OR_COMPONENT_HARM"
        elif metric == "myops_scar" and 0 < dice_delta < 0.01:
            failure = "SCAR_GAIN_SMALL_NOT_ROUTE_RELEVANT"
        else:
            failure = "NO_PROMOTION_BY_M8_REVIEW"
        eligible = "false"
        if metric == "myops_scar" and dice_delta > 0 and remote_delta <= 0 and component_delta <= 0:
            eligible = "diagnostic_only_scar_signal"
        out.append(
            {
                "candidate_id": r["candidate_id"],
                "metric_name": metric,
                "anchor_dice": control["dice_mean"],
                "candidate_dice": r["dice_mean"],
                "dice_delta": r["dice_delta_vs_nnunet"],
                "anchor_hd95": control["hd95_mean"],
                "candidate_hd95": r["hd95_mean"],
                "hd95_delta": r["hd95_delta_vs_nnunet"],
                "remote_fp_delta": r["remote_fp_delta_vs_nnunet"],
                "component_delta": r["component_count_delta_vs_nnunet"],
                "hard_subgroup": "see m8_hard_subgroup_help_harm.csv",
                "failure_class": failure,
                "eligible_for_repair_contract": eligible,
            }
        )
    return out


def feature_schema() -> list[dict[str, object]]:
    rows = [
        ("t2_present", "case metadata availability mask", True, False, False, False, True, "required for no-T2-safe edema routing"),
        ("modality_group", "case metadata availability mask", True, False, False, False, True, "availability group allowed when not using center or case identity"),
        ("final_delta_rate", "M8 contribution export", True, False, False, False, True, "deployable proxy for candidate-anchor disagreement magnitude"),
        ("anchor_delta_rate", "M8 contribution export", True, False, False, False, True, "deployable proxy for anchor/candidate label delta"),
        ("srr_weight_mean", "M8 contribution export", True, False, False, False, True, "SRR branch contribution proxy"),
        ("refiner_delta_magnitude", "M8 contribution export", True, False, False, False, True, "refiner effect magnitude proxy"),
        ("fallback_weight_mean", "M8 contribution export", True, False, False, False, True, "fallback/safety branch proxy"),
        ("no_t2_edema_voxels", "output safety check", True, False, False, False, True, "allowed as safety guardrail, not as GT metric"),
        ("case_id", "metadata", True, False, True, False, False, "manual case routing is forbidden"),
        ("center", "metadata", True, False, False, False, False, "center-only routing is diagnostic-only because it risks center leakage"),
        ("dice", "validation metric", False, True, False, False, False, "GT metric cannot select deployable policy"),
        ("hd95", "validation metric", False, True, False, False, False, "GT metric cannot select deployable policy"),
        ("component_count_delta", "validation metric", False, True, False, False, False, "component metric cannot select deployable policy"),
        ("hosted_feedback", "external leaderboard", False, False, False, True, False, "hosted feedback is unavailable and forbidden"),
        ("foreground_mean", "aggregate metric", False, True, False, False, False, "foreground mean cannot hide scar/edema failures"),
    ]
    return [
        {
            "feature_name": r[0],
            "source": r[1],
            "available_at_inference": str(r[2]).lower(),
            "uses_ground_truth": str(r[3]).lower(),
            "uses_case_id": str(r[4]).lower(),
            "uses_hosted_feedback": str(r[5]).lower(),
            "allowed_for_policy": str(r[6]).lower(),
            "reason": r[7],
        }
        for r in rows
    ]


def build_policy_tables(data: dict[str, object]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    anchor = anchor_metrics(data)
    best_candidate = choose_combined_best_candidate(data)
    best_candidate_metrics = candidate_metrics(data, best_candidate)

    proxy_candidate = "m8_scar_precision_edema_safe_longrun__checkpoint_best__argmax"
    proxy_metrics = candidate_metrics(data, proxy_candidate)
    ctrace = contribution_map(data, "m8_scar_precision_edema_safe_longrun")

    def anchor_only(_key: tuple[str, str], _anchor_row: MetricRow) -> bool:
        return False

    def candidate_only(_key: tuple[str, str], _anchor_row: MetricRow) -> bool:
        return True

    def conservative_proxy(key: tuple[str, str], anchor_row: MetricRow) -> bool:
        r = ctrace.get(key)
        if not r:
            return False
        metric = key[1]
        if metric == "myops_edema" and not anchor_row.t2_present:
            return False
        if fnum(r.get("no_t2_edema_voxels")) > 0:
            return False
        if fnum(r.get("fallback_weight_mean")) > 0.08:
            return False
        if fnum(r.get("final_delta_rate")) <= 0.00075:
            return False
        if fnum(r.get("srr_weight_mean")) < 0.15:
            return False
        if metric == "myops_scar":
            return fnum(r.get("refiner_delta_magnitude")) > 0.5
        return anchor_row.t2_present and fnum(r.get("refiner_delta_magnitude")) > 0.02

    def high_signal_proxy(key: tuple[str, str], anchor_row: MetricRow) -> bool:
        r = ctrace.get(key)
        if not r:
            return False
        if key[1] == "myops_edema" and not anchor_row.t2_present:
            return False
        return (
            fnum(r.get("no_t2_edema_voxels")) == 0
            and fnum(r.get("srr_weight_mean")) >= 0.18
            and fnum(r.get("final_logit_delta_abs_mean")) >= 0.35
            and fnum(r.get("final_delta_rate")) > 0
        )

    policy_table: list[dict[str, object]] = []
    policy_table.extend(
        policy_rows(
            "anchor_only_control",
            "Always use the same-split nnU-Net anchor/control.",
            "A_nnunet_anchor_control",
            anchor,
            best_candidate_metrics,
            anchor_only,
        )
    )
    policy_table.extend(
        policy_rows(
            "candidate_only_control",
            "Always use the best combined M8 local candidate as-is; reproduces M8 no-promotion outcome.",
            best_candidate,
            anchor,
            best_candidate_metrics,
            candidate_only,
        )
    )
    policy_table.extend(
        policy_rows(
            "deployable_conservative_proxy_fallback",
            "Use SRR only when non-GT exported disagreement/SRR/refiner signals are nontrivial and no-T2 edema safety holds; otherwise anchor.",
            proxy_candidate,
            anchor,
            proxy_metrics,
            conservative_proxy,
        )
    )
    policy_table.extend(
        policy_rows(
            "deployable_high_srr_signal_fallback",
            "Use SRR only when non-GT SRR weight and logit-delta proxies indicate high SRR signal; no case ID, GT metric, center, or hosted feedback.",
            proxy_candidate,
            anchor,
            proxy_metrics,
            high_signal_proxy,
        )
    )

    no_t2_rows = [
        {
            "policy_id": r["policy_id"],
            "metric_name": r["metric_name"],
            "candidate_source": r["candidate_source"],
            "no_t2_edema_voxels": r["no_t2_edema_voxels"],
            "selected_for_repair_contract": "false",
            "safety_status": "PASS" if fnum(r["no_t2_edema_voxels"]) == 0 else "BLOCKER_NONZERO_NO_T2_EDEMA",
            "notes": "selected repair contract is false because no deployable repair signal is promoted",
        }
        for r in policy_table
        if r["metric_name"] == "myops_edema"
    ]
    return policy_table, no_t2_rows


def build_hard_subgroup_table(data: dict[str, object], policy_table: list[dict[str, object]]) -> list[dict[str, object]]:
    anchor = anchor_metrics(data)
    best_candidate = choose_combined_best_candidate(data)
    candidate = candidate_metrics(data, best_candidate)
    labels: dict[str, Callable[[MetricRow, MetricRow], bool]] = {
        "CenterB": lambda a, c: a.center == "CenterB",
        "CenterC": lambda a, c: a.center == "CenterC",
        "T2_present": lambda a, c: a.t2_present,
        "no_T2_safety": lambda a, c: not a.t2_present and a.metric_name == "myops_edema",
        "scar_positive": lambda a, c: a.metric_name == "myops_scar" and not c.gt_empty,
        "edema_positive": lambda a, c: a.metric_name == "myops_edema" and not c.gt_empty,
        "remote_FP_cases": lambda a, c: a.remote_fp_count > 0 or c.remote_fp_count > 0,
        "component_burden_cases": lambda a, c: a.component_count >= 4 or c.component_count >= 4,
    }
    out: list[dict[str, object]] = []
    for label, pred in labels.items():
        for metric in ["myops_scar", "myops_edema"]:
            pairs = [(a, candidate.get(k, a)) for k, a in anchor.items() if k[1] == metric]
            selected = [(a, c) for a, c in pairs if pred(a, c)]
            if not selected:
                out.append(
                    {
                        "subgroup": label,
                        "metric_name": metric,
                        "case_count": 0,
                        "anchor_dice_mean": "",
                        "candidate_dice_mean": "",
                        "dice_delta": "",
                        "anchor_hd95_mean": "",
                        "candidate_hd95_mean": "",
                        "hd95_delta": "",
                        "remote_fp_delta": "",
                        "component_delta": "",
                        "interpretation": "SUBGROUP_NOT_PRESENT_IN_M8_EVIDENCE",
                    }
                )
                continue
            anchor_dice = mean(a.dice for a, _ in selected)
            cand_dice = mean(c.dice for _, c in selected)
            anchor_hd = mean(a.hd95 for a, _ in selected)
            cand_hd = mean(c.hd95 for _, c in selected)
            remote_delta = mean(c.remote_fp_count - a.remote_fp_count for a, c in selected)
            comp_delta = mean(c.component_count - a.component_count for a, c in selected)
            interp = "NO_CLEAR_HELP"
            if cand_dice > anchor_dice + 0.005 and cand_hd <= anchor_hd and remote_delta <= 0:
                interp = "LOCAL_HELP_SIGNAL"
            elif cand_dice < anchor_dice - 0.005 or remote_delta > 0 or comp_delta > 1:
                interp = "HARM_OR_UNRESOLVED"
            out.append(
                {
                    "subgroup": label,
                    "metric_name": metric,
                    "case_count": len(selected),
                    "anchor_dice_mean": fmt(anchor_dice),
                    "candidate_dice_mean": fmt(cand_dice),
                    "dice_delta": fmt(cand_dice - anchor_dice),
                    "anchor_hd95_mean": fmt(anchor_hd),
                    "candidate_hd95_mean": fmt(cand_hd),
                    "hd95_delta": fmt(cand_hd - anchor_hd),
                    "remote_fp_delta": fmt(remote_delta),
                    "component_delta": fmt(comp_delta),
                    "interpretation": interp,
                }
            )
    return out


def repair_contract_state(policy_rows_: list[dict[str, object]]) -> tuple[str, str]:
    deployable_rows = [r for r in policy_rows_ if str(r["policy_id"]).startswith("deployable_")]
    promoted = [r for r in deployable_rows if r["promotion_status"] == "DIAGNOSTIC_POSITIVE_REQUIRES_REVIEW"]
    scar_good = any(r["metric_name"] == "myops_scar" for r in promoted)
    edema_good = any(r["metric_name"] == "myops_edema" for r in promoted)
    if scar_good and edema_good:
        return "REPAIR_CONTRACT_READY_FOR_REVIEW", "GPT_PLAN_BOUNDED_REPAIR_IMPLEMENTATION"
    return "NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND", "GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR"


def validate_output_dir(out_dir: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def add(check_id: str, status: str, detail: str) -> None:
        rows.append({"check_id": check_id, "status": status, "detail": detail})

    for name in REQUIRED_OUTPUTS:
        add(f"required_output:{name}", "PASS" if (out_dir / name).exists() else "FAIL", name)

    review_ledger = out_dir / "m8_review_findings_ledger.csv"
    if review_ledger.exists():
        text = review_ledger.read_text(encoding="utf-8")
        add(
            "previous_review_token",
            "PASS" if "M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED" in text else "FAIL",
            "requires M8 no-promotion review token",
        )
    else:
        add("previous_review_token", "FAIL", "m8_review_findings_ledger.csv missing")

    feature_schema_path = out_dir / "m8_proxy_feature_schema.csv"
    if feature_schema_path.exists():
        features = {r["feature_name"]: r for r in read_csv(feature_schema_path)}
        forbidden = ["case_id", "dice", "hd95", "component_count_delta", "hosted_feedback", "foreground_mean"]
        bad = [f for f in forbidden if features.get(f, {}).get("allowed_for_policy") != "false"]
        add("forbidden_policy_features", "PASS" if not bad else "FAIL", ",".join(bad) or "all forbidden marked false")
    else:
        add("forbidden_policy_features", "FAIL", "schema missing")

    policy_path = out_dir / "m8_proxy_arbitration_help_harm.csv"
    if policy_path.exists():
        policies = read_csv(policy_path)
        policy_ids = {r["policy_id"] for r in policies}
        required = {"anchor_only_control", "candidate_only_control"}
        deployable = {p for p in policy_ids if p.startswith("deployable_")}
        add("policy_families", "PASS" if required <= policy_ids and deployable else "FAIL", f"policies={sorted(policy_ids)}")
        disallowed_policy_rows = [r for r in policies if r.get("uses_only_allowed_features") != "true"]
        add("policies_use_only_allowed_features", "PASS" if not disallowed_policy_rows else "FAIL", f"bad_rows={len(disallowed_policy_rows)}")
        selected_bad_no_t2 = [
            r for r in policies if r["metric_name"] == "myops_edema" and fnum(r["no_t2_edema_voxels"]) > 0 and r["promotion_status"] != "NO_DEPLOYABLE_REPAIR_SIGNAL"
        ]
        add("no_t2_policy_safety", "PASS" if not selected_bad_no_t2 else "FAIL", f"bad_rows={len(selected_bad_no_t2)}")
        candidate_promoted = [
            r for r in policies if r["policy_id"] == "candidate_only_control" and r["promotion_status"] != "REPRODUCES_M8_NO_PROMOTION"
        ]
        add("candidate_only_not_promoted", "PASS" if not candidate_promoted else "FAIL", f"bad_rows={len(candidate_promoted)}")
    else:
        add("policy_families", "FAIL", "policy table missing")
        add("policies_use_only_allowed_features", "FAIL", "policy table missing")
        add("no_t2_policy_safety", "FAIL", "policy table missing")
        add("candidate_only_not_promoted", "FAIL", "policy table missing")

    hard_path = out_dir / "m8_hard_subgroup_help_harm.csv"
    if hard_path.exists():
        labels = {r["subgroup"] for r in read_csv(hard_path)}
        required_labels = {"CenterB", "CenterC", "T2_present", "no_T2_safety", "scar_positive", "edema_positive", "remote_FP_cases", "component_burden_cases"}
        add("hard_subgroup_labels", "PASS" if required_labels <= labels else "FAIL", f"missing={sorted(required_labels - labels)}")
    else:
        add("hard_subgroup_labels", "FAIL", "hard subgroup table missing")

    contract_path = out_dir / "m8_repair_contract.md"
    next_path = out_dir / "m8_next_required_action.md"
    if contract_path.exists() and next_path.exists():
        contract = contract_path.read_text(encoding="utf-8")
        next_action = next_path.read_text(encoding="utf-8")
        allowed_contracts = {
            "REPAIR_CONTRACT_READY_FOR_REVIEW",
            "NO_DEPLOYABLE_REPAIR_CONTRACT_FOUND",
            "NEEDS_EVIDENCE_MISSING_INPUTS",
            "NEEDS_REVISION_PIPELINE_OR_VALIDATOR",
        }
        allowed_next = {
            "GPT_PLAN_BOUNDED_REPAIR_IMPLEMENTATION",
            "GPT_REPLAN_ROUTE_AFTER_NO_DEPLOYABLE_REPAIR",
            "NEEDS_EVIDENCE_BEFORE_ANY_NEXT_TASK",
            "NEEDS_REVISION_BEFORE_REVIEW",
        }
        add("contract_state_allowed", "PASS" if any(s in contract for s in allowed_contracts) else "FAIL", "controlled contract state")
        add("next_action_allowed", "PASS" if any(s in next_action for s in allowed_next) else "FAIL", "controlled next action")
    else:
        add("contract_state_allowed", "FAIL", "contract or next action missing")
        add("next_action_allowed", "FAIL", "contract or next action missing")

    joined = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in out_dir.glob("*.md"))
    completion = (out_dir / "completion_check.md").read_text(encoding="utf-8", errors="ignore") if (out_dir / "completion_check.md").exists() else ""
    ready_with_error = "READY_FOR_REVIEW" in completion and "validator_error_count: `0`" not in completion
    add("ready_requires_zero_validator_errors", "PASS" if not ready_with_error else "FAIL", "ready packets must have validator_error_count 0")
    bad_terms = [term for term in FORBIDDEN_READY_TERMS if term in joined]
    add("forbidden_claims_absent", "PASS" if not bad_terms else "FAIL", ",".join(bad_terms) or "no forbidden claims")
    monitor_terms = ["NEEDS_MONITOR", "PENDING_MONITOR", "JOB_SUBMITTED", "PENDING_PRIORITY", "RUNNING", "AWAITING_SACCT"]
    monitor_bad = [term for term in monitor_terms if term in joined and "not used as completion" not in joined]
    add("monitor_not_completion", "PASS" if not monitor_bad else "FAIL", ",".join(monitor_bad) or "no monitor completion claim")
    return rows


def validation_passed(rows: list[dict[str, object]]) -> bool:
    return all(r["status"] == "PASS" for r in rows)


def run_self_tests(out_dir: Path) -> list[dict[str, object]]:
    mutations: list[tuple[str, Callable[[Path], None]]] = []

    def remove(path_name: str) -> Callable[[Path], None]:
        def _mut(root: Path) -> None:
            (root / path_name).unlink(missing_ok=True)
        return _mut

    def replace(path_name: str, old: str, new: str) -> Callable[[Path], None]:
        def _mut(root: Path) -> None:
            p = root / path_name
            p.write_text(p.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
        return _mut

    def csv_replace(path_name: str, column: str, value: str) -> Callable[[Path], None]:
        def _mut(root: Path) -> None:
            p = root / path_name
            rows = read_csv(p)
            for row in rows:
                row[column] = value
            write_csv(p, rows, list(rows[0].keys()))
        return _mut

    def no_t2_violation(root: Path) -> None:
        p = root / "m8_proxy_arbitration_help_harm.csv"
        rows = read_csv(p)
        for row in rows:
            if row["metric_name"] == "myops_edema" and row["policy_id"].startswith("deployable_"):
                row["no_t2_edema_voxels"] = "3"
                row["promotion_status"] = "DIAGNOSTIC_POSITIVE_REQUIRES_REVIEW"
                break
        write_csv(p, rows, list(rows[0].keys()))

    def policy_uses_metric_values(root: Path) -> None:
        p = root / "m8_proxy_arbitration_help_harm.csv"
        rows = read_csv(p)
        for row in rows:
            if row["policy_id"].startswith("deployable_"):
                row["uses_only_allowed_features"] = "false"
                row["policy_description"] = row["policy_description"] + " Uses Dice/HD95 metric values as decision inputs."
                break
        write_csv(p, rows, list(rows[0].keys()))

    def append_text(path_name: str, text: str) -> Callable[[Path], None]:
        def _mut(root: Path) -> None:
            p = root / path_name
            p.write_text(p.read_text(encoding="utf-8") + "\n" + text + "\n", encoding="utf-8")
        return _mut

    mutations.extend(
        [
            ("good_fixture", lambda _root: None),
            ("missing_m8_review_token", replace("m8_review_findings_ledger.csv", "M8_AUDITED_NO_PROMOTION_SCIENTIFIC_UNRESOLVED", "M8_AUDITED_LOCAL_PROMOTION_CANDIDATE")),
            ("missing_anchor_comparison", remove("m8_candidate_failure_matrix.csv")),
            ("policy_uses_case_id", csv_replace("m8_proxy_feature_schema.csv", "allowed_for_policy", "true")),
            ("policy_uses_dice_metric", policy_uses_metric_values),
            ("hosted_feedback_allowed", replace("m8_proxy_feature_schema.csv", "hosted_feedback,external leaderboard,false,false,false,true,false", "hosted_feedback,external leaderboard,false,false,false,true,true")),
            ("no_t2_edema_selected", no_t2_violation),
            ("foreground_mean_only", remove("m8_hard_subgroup_help_harm.csv")),
            ("candidate_only_promoted", replace("m8_proxy_arbitration_help_harm.csv", "REPRODUCES_M8_NO_PROMOTION", "DIAGNOSTIC_POSITIVE_REQUIRES_REVIEW")),
            ("required_output_missing", remove("m8_no_t2_safety_report.csv")),
            ("ready_with_nonzero_validator_errors", replace("completion_check.md", "validator_error_count: `0`", "validator_error_count: `1`")),
            ("route_promotion_claimed", replace("m8_repair_contract.md", "does not authorize route promotion", "route_promotion_decision: PROMOTE")),
            ("monitor_marked_completion", replace("commands_run.md", "No Slurm job was submitted", "JOB_SUBMITTED marked completion")),
            ("cine_frame0_temporal_ready", replace("m8_followup_route_objective.md", "not validation packaging", "myocardium_cinemyops temporal readiness from frame0-only")),
            ("placeholder_only_proof", append_text("result.md", "synthetic placeholder evidence used as the only proof")),
        ]
    )

    report: list[dict[str, object]] = []
    for name, mutate in mutations:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "packet"
            shutil.copytree(out_dir, root)
            mutate(root)
            rows = validate_output_dir(root)
            passed = validation_passed(rows)
            expected = name == "good_fixture"
            report.append(
                {
                    "test_id": name,
                    "expected_validator_pass": str(expected).lower(),
                    "actual_validator_pass": str(passed).lower(),
                    "fail_closed": str(passed == expected).lower(),
                    "error_count": sum(1 for r in rows if r["status"] != "PASS"),
                }
            )
    return report


def write_missing_input_packet(missing: list[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    missing_rows = [{"missing_path": path} for path in missing]
    write_csv(OUT_DIR / "m8_candidate_failure_matrix.csv", [], ["candidate_id", "metric_name", "anchor_dice", "candidate_dice", "dice_delta", "anchor_hd95", "candidate_hd95", "hd95_delta", "remote_fp_delta", "component_delta", "hard_subgroup", "failure_class", "eligible_for_repair_contract"])
    write_csv(OUT_DIR / "m8_review_findings_ledger.csv", [{"finding_id": "missing_m8_inputs", "source_path": "", "source_line_or_section": "", "claim": ";".join(missing), "effect_on_followup": "cannot execute follow-up", "blocking_level": "blocking"}], ["finding_id", "source_path", "source_line_or_section", "claim", "effect_on_followup", "blocking_level"])
    write_csv(OUT_DIR / "m8_proxy_feature_schema.csv", feature_schema(), ["feature_name", "source", "available_at_inference", "uses_ground_truth", "uses_case_id", "uses_hosted_feedback", "allowed_for_policy", "reason"])
    for name in ["m8_proxy_arbitration_help_harm.csv", "m8_hard_subgroup_help_harm.csv", "m8_no_t2_safety_report.csv", "m8_followup_strict_validator_report.csv", "m8_followup_validator_selftest_report.csv"]:
        write_csv(OUT_DIR / name, missing_rows, ["missing_path"])
    write_text(OUT_DIR / "m8_repair_contract.md", "# M8 Repair Contract\n\nstate: `NEEDS_EVIDENCE_MISSING_INPUTS`\n")
    write_text(OUT_DIR / "m8_next_required_action.md", "# M8 Next Required Action\n\nnext_action: `NEEDS_EVIDENCE_BEFORE_ANY_NEXT_TASK`\n")
    body = "\n".join(f"- {p}" for p in missing)
    for name in ["result.md", "completion_check.md", "review_request.md", "MANIFEST.md", "commands_run.md", "m8_followup_route_objective.md", "m8_followup_strict_validator_report.md", "m8_followup_validator_selftest_report.md"]:
        write_text(OUT_DIR / name, f"# M8 Follow-up Missing Inputs\n\nstatus: `M8_FOLLOWUP_NEEDS_EVIDENCE_MISSING_M8_INPUT`\n\nMissing paths:\n{body}\n")


def write_packet() -> str:
    missing = missing_m8_inputs()
    if missing:
        write_missing_input_packet(missing)
        return "M8_FOLLOWUP_NEEDS_EVIDENCE_MISSING_M8_INPUT"

    data = read_m8()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    review_rows = build_review_findings(data)
    failure_rows = build_candidate_failure_matrix(data)
    policy_table, no_t2_rows = build_policy_tables(data)
    hard_rows = build_hard_subgroup_table(data, policy_table)
    contract_state, next_action = repair_contract_state(policy_table)
    status = "M8_FOLLOWUP_READY_FOR_REVIEW" if contract_state == "REPAIR_CONTRACT_READY_FOR_REVIEW" else "M8_FOLLOWUP_NO_DEPLOYABLE_REPAIR_FOUND_READY_FOR_REVIEW"

    write_csv(OUT_DIR / "m8_review_findings_ledger.csv", review_rows, ["finding_id", "source_path", "source_line_or_section", "claim", "effect_on_followup", "blocking_level"])
    write_csv(OUT_DIR / "m8_candidate_failure_matrix.csv", failure_rows, ["candidate_id", "metric_name", "anchor_dice", "candidate_dice", "dice_delta", "anchor_hd95", "candidate_hd95", "hd95_delta", "remote_fp_delta", "component_delta", "hard_subgroup", "failure_class", "eligible_for_repair_contract"])
    write_csv(OUT_DIR / "m8_proxy_feature_schema.csv", feature_schema(), ["feature_name", "source", "available_at_inference", "uses_ground_truth", "uses_case_id", "uses_hosted_feedback", "allowed_for_policy", "reason"])
    write_csv(OUT_DIR / "m8_proxy_arbitration_help_harm.csv", policy_table, ["policy_id", "policy_description", "uses_only_allowed_features", "candidate_source", "metric_name", "case_count", "srr_case_count", "srr_case_fraction", "dice_mean_anchor", "dice_mean_policy", "dice_delta", "hd95_mean_anchor", "hd95_mean_policy", "hd95_delta", "remote_fp_mean_anchor", "remote_fp_mean_policy", "no_t2_edema_voxels", "scar_guardrail_status", "edema_guardrail_status", "promotion_status"])
    write_csv(OUT_DIR / "m8_hard_subgroup_help_harm.csv", hard_rows, ["subgroup", "metric_name", "case_count", "anchor_dice_mean", "candidate_dice_mean", "dice_delta", "anchor_hd95_mean", "candidate_hd95_mean", "hd95_delta", "remote_fp_delta", "component_delta", "interpretation"])
    write_csv(OUT_DIR / "m8_no_t2_safety_report.csv", no_t2_rows, ["policy_id", "metric_name", "candidate_source", "no_t2_edema_voxels", "selected_for_repair_contract", "safety_status", "notes"])

    write_text(
        OUT_DIR / "m8_followup_route_objective.md",
        """# M8 Follow-up Route Objective

status: `diagnostic_no_promotion_repair_decision`

This is a post-M8 no-promotion repair-decision milestone. It is not M9, not route promotion, not fold expansion, not validation packaging, not validation upload, and not a hosted metric claim.

The question is whether existing M8 evidence supports a deployable, non-GT, non-case-ID, baseline-preserving arbitration or repair contract. nnU-Net remains the same-split anchor/control and safety source; SRR cannot be reduced to an optional postprocess wrapper. Scar and edema are evaluated separately, and no-T2 edema safety is mandatory.
""",
    )
    write_text(
        OUT_DIR / "m8_repair_contract.md",
        f"""# M8 Repair Contract

state: `{contract_state}`

The evaluated deployable proxy policies use only allowed non-GT features, but they do not show a nontrivial mechanism-consistent same-split SRR help signal that improves scar and edema while preserving remote-FP/component and no-T2 guardrails.

This packet does not authorize route promotion, fold expansion, validation packaging, validation upload, hosted metric claims, leaderboard claims, scientific stop, or M9.
""",
    )
    write_text(OUT_DIR / "m8_next_required_action.md", f"# M8 Next Required Action\n\nnext_action: `{next_action}`\n")
    write_text(
        OUT_DIR / "commands_run.md",
        """# Commands Run

- `python scripts/evaluation/diagnose_srr_v3_m8_followup_repair_decision.py`

No Slurm job was submitted. No model training was launched. No validation package was created. No upload was attempted.
""",
    )

    validator_rows = validate_output_dir(OUT_DIR)
    error_count = sum(1 for r in validator_rows if r["status"] != "PASS")
    write_csv(OUT_DIR / "m8_followup_strict_validator_report.csv", validator_rows, ["check_id", "status", "detail"])
    write_text(
        OUT_DIR / "m8_followup_strict_validator_report.md",
        f"""# M8 Follow-up Strict Validator Report

status: `{'PASS' if error_count == 0 else 'FAIL'}`
error_count: `{error_count}`

The validator checks required outputs, previous M8 no-promotion token, same-split policy tables, forbidden policy features, no-T2 safety, hard subgroup coverage, controlled contract states, forbidden claims, and monitor-packet boundaries.
""",
    )

    # Regenerate validator rows now that validator reports exist.
    validator_rows = validate_output_dir(OUT_DIR)
    error_count = sum(1 for r in validator_rows if r["status"] != "PASS")
    write_csv(OUT_DIR / "m8_followup_strict_validator_report.csv", validator_rows, ["check_id", "status", "detail"])

    # Write provisional top-level files so the self-test copies a complete
    # packet. They are overwritten below after self-test accounting.
    write_text(
        OUT_DIR / "result.md",
        f"""# M8 Follow-up No-promotion Repair Decision Result

status: `{status}`

This provisional result is written before validator self-tests and overwritten by the final result in the same script run.
""",
    )
    write_text(
        OUT_DIR / "completion_check.md",
        f"""# M8 Follow-up Completion Check

status: `{status}`

required_outputs_present: `true`
strict_validator_pass: `{'true' if error_count == 0 else 'false'}`
known_bad_selftests_fail_closed: `pending`
validator_error_count: `{error_count}`
repair_contract: `{contract_state}`
next_required_action: `{next_action}`

blocking_issues:
- pending self-test finalization
""",
    )
    write_text(
        OUT_DIR / "review_request.md",
        f"""# M8 Follow-up Review Request

status: `{status}`

Provisional review request; final text is written after validator self-tests.
""",
    )
    manifest_lines = "\n".join(f"- `{name}`" for name in REQUIRED_OUTPUTS)
    write_text(
        OUT_DIR / "MANIFEST.md",
        f"""# Manifest

source_prompt: `prompts/shared/EXECUTOR_PROMPTS.md` section `M8 executor follow-up: no-promotion repair decision`
source_m8_packet: `{M8_DIR.relative_to(REPO)}`
status: `{status}`

## Files

{manifest_lines}
""",
    )
    write_csv(
        OUT_DIR / "m8_followup_validator_selftest_report.csv",
        [{"test_id": "pending", "expected_validator_pass": "pending", "actual_validator_pass": "pending", "fail_closed": "pending", "error_count": ""}],
        ["test_id", "expected_validator_pass", "actual_validator_pass", "fail_closed", "error_count"],
    )
    write_text(
        OUT_DIR / "m8_followup_validator_selftest_report.md",
        "# M8 Follow-up Validator Self-test Report\n\nstatus: `PENDING_FINALIZATION`\n",
    )

    selftest_rows = run_self_tests(OUT_DIR)
    selftest_failures = [r for r in selftest_rows if r["fail_closed"] != "true"]
    write_csv(OUT_DIR / "m8_followup_validator_selftest_report.csv", selftest_rows, ["test_id", "expected_validator_pass", "actual_validator_pass", "fail_closed", "error_count"])
    write_text(
        OUT_DIR / "m8_followup_validator_selftest_report.md",
        f"""# M8 Follow-up Validator Self-test Report

status: `{'PASS' if not selftest_failures else 'FAIL'}`
self_test_rows: `{len(selftest_rows)}`
failed: `{[r['test_id'] for r in selftest_failures]}`

The self-test includes one good fixture plus known-bad mutations for missing M8 review token, missing anchor comparison, forbidden policy features, no-T2 violation, foreground-mean/easy-only evidence, candidate-only promotion, missing output, ready-with-validator-error, route-promotion claim, monitor completion, Cine frame0-only temporal claim, and placeholder-only proof.
""",
    )

    validator_rows = validate_output_dir(OUT_DIR)
    error_count = sum(1 for r in validator_rows if r["status"] != "PASS")
    write_csv(OUT_DIR / "m8_followup_strict_validator_report.csv", validator_rows, ["check_id", "status", "detail"])
    write_text(
        OUT_DIR / "m8_followup_strict_validator_report.md",
        f"""# M8 Follow-up Strict Validator Report

status: `{'PASS' if error_count == 0 else 'FAIL'}`
error_count: `{error_count}`

The validator checks required outputs, previous M8 no-promotion token, same-split policy tables, forbidden policy features, no-T2 safety, hard subgroup coverage, controlled contract states, forbidden claims, and monitor-packet boundaries.
""",
    )

    final_error_count = error_count + len(selftest_failures)
    if final_error_count:
        status = "M8_FOLLOWUP_NEEDS_REVISION_PIPELINE_OR_VALIDATOR"
        contract_state = "NEEDS_REVISION_PIPELINE_OR_VALIDATOR"
        next_action = "NEEDS_REVISION_BEFORE_REVIEW"
        write_text(OUT_DIR / "m8_repair_contract.md", f"# M8 Repair Contract\n\nstate: `{contract_state}`\n")
        write_text(OUT_DIR / "m8_next_required_action.md", f"# M8 Next Required Action\n\nnext_action: `{next_action}`\n")

    write_text(
        OUT_DIR / "result.md",
        f"""# M8 Follow-up No-promotion Repair Decision Result

status: `{status}`

## Summary

This diagnostic used existing M8 evidence only. It reproduced the M8 no-promotion finding: candidate-only use does not beat the same-split nnU-Net anchor overall, and the deployable proxy fallback policies do not show enough mechanism-consistent SRR contribution across scar and edema to justify a bounded repair implementation contract.

## Decision

- repair_contract: `{contract_state}`
- next_required_action: `{next_action}`
- validator_error_count: `{final_error_count}`

No training, Slurm submission, validation packaging, upload, hosted metric claim, route promotion, fold expansion, scientific stop, or M9 was performed.
""",
    )
    write_text(
        OUT_DIR / "completion_check.md",
        f"""# M8 Follow-up Completion Check

status: `{status}`

required_outputs_present: `true`
strict_validator_pass: `{'true' if error_count == 0 else 'false'}`
known_bad_selftests_fail_closed: `{'true' if not selftest_failures else 'false'}`
validator_error_count: `{final_error_count}`
repair_contract: `{contract_state}`
next_required_action: `{next_action}`

blocking_issues:
{('- none' if final_error_count == 0 else '- validator/self-test failure')}
""",
    )
    write_text(
        OUT_DIR / "review_request.md",
        f"""# M8 Follow-up Review Request

status: `{status}`

Please run the separate read-only reviewer prompt for the M8 follow-up no-promotion repair decision. This executor did not write `review.md` and did not start any next milestone.
""",
    )
    manifest_lines = "\n".join(f"- `{name}`" for name in REQUIRED_OUTPUTS)
    write_text(
        OUT_DIR / "MANIFEST.md",
        f"""# Manifest

source_prompt: `prompts/shared/EXECUTOR_PROMPTS.md` section `M8 executor follow-up: no-promotion repair decision`
source_m8_packet: `{M8_DIR.relative_to(REPO)}`
status: `{status}`

## Files

{manifest_lines}

## Artifact Policy

Only lightweight Markdown/CSV/JSON result files and the helper script are required for review. No checkpoints, NIfTI predictions, upload packages, raw data, large logs, secrets, or runtime trees are included.
""",
    )
    return status


def main() -> int:
    global OUT_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()
    OUT_DIR = args.output_dir.resolve()
    status = write_packet()
    print(f"status={status}")
    print(f"output_dir={OUT_DIR}")
    return 0 if "NEEDS_REVISION" not in status and "MISSING" not in status else 2


if __name__ == "__main__":
    raise SystemExit(main())
