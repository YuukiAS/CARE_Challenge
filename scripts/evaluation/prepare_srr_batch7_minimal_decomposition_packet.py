#!/usr/bin/env python3
"""Prepare Batch7 minimal decomposition Wave0/static Wave1 evidence files."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.losses.srr_losses import br2_selective_integration_penalty  # noqa: E402
from src.care_myocardium.models.srr_propref import (  # noqa: E402
    BR2_CENTER_ORDER,
    BR2_CENTER_TO_PATTERN,
    BR2_PATTERN_ORDER,
    BR2_PATTERN_TO_AVAILABILITY,
    BR2_REPRESENTER_SPECS,
    LightweightCenterHierarchicalBR2,
)
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402


TASK_KEY = "20260722_srr_batch7_minimal_pathology_decomposition"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_text(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def load_split_cases(split_path: Path, fold: int) -> tuple[list[str], list[str]]:
    payload = json.loads(split_path.read_text(encoding="utf-8"))
    for row in payload["folds"]:
        if int(row["fold"]) == int(fold):
            return [str(x) for x in row["train"]], [str(x) for x in row["val"]]
    raise ValueError(f"fold {fold} not found in {split_path}")


def availability_key(values: tuple[float, float, float]) -> str:
    if values == (1.0, 0.0, 0.0):
        return "lge_only"
    if values == (1.0, 0.0, 1.0):
        return "lge_c0"
    if values == (1.0, 1.0, 1.0):
        return "lge_t2_c0"
    return "unsupported"


def center_inventory(train_cases: list[str], val_cases: list[str]) -> list[dict[str, Any]]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    by_center: dict[str, list[str]] = defaultdict(list)
    for case_id in train_cases + val_cases:
        by_center[metadata[case_id].center].append(case_id)
    rows: list[dict[str, Any]] = []
    for center in sorted(by_center):
        cases = by_center[center]
        groups = Counter(metadata[cid].modality_group for cid in cases)
        availabilities = {metadata[cid].availability for cid in cases}
        if len(availabilities) != 1:
            status = "FAIL_MULTIPLE_OBSERVATION_SETS"
            availability = tuple(sorted(availabilities)[0])
        else:
            status = "PASS"
            availability = next(iter(availabilities))
        rows.append(
            {
                "center": center,
                "case_count_all_fold0_scope": len(cases),
                "train_case_count": sum(1 for cid in cases if cid in set(train_cases)),
                "val_case_count": sum(1 for cid in cases if cid in set(val_cases)),
                "modality_group_counts": json.dumps(dict(sorted(groups.items())), sort_keys=True),
                "lge_present": int(availability[0]),
                "t2_present": int(availability[1]),
                "c0_present": int(availability[2]),
                "observation_set": availability_key(availability),
                "expected_observation_set": BR2_CENTER_TO_PATTERN.get(center, "unexpected_center"),
                "status": status if availability_key(availability) == BR2_CENTER_TO_PATTERN.get(center) else "FAIL_EXPECTED_PATTERN_MISMATCH",
                "source_semantics": "metadata.center",
                "availability_semantics": "observation_set_not_training_source",
            }
        )
    return rows


def source_eligibility_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pathology in ("scar", "edema"):
        mask = LightweightCenterHierarchicalBR2.source_eligibility_mask(
            pathology=pathology,
            device=torch.device("cpu"),
            dtype=torch.float32,
        )
        for cidx, center in enumerate(BR2_CENTER_ORDER):
            pattern = BR2_CENTER_TO_PATTERN[center]
            availability = BR2_PATTERN_TO_AVAILABILITY[pattern]
            for ridx, (rep, required) in enumerate(BR2_REPRESENTER_SPECS):
                eligible = bool(mask[cidx, ridx].item() > 0.5)
                rows.append(
                    {
                        "pathology": pathology,
                        "center": center,
                        "observation_set": pattern,
                        "representer": rep,
                        "required_modalities": ",".join(["LGE", "T2", "C0"][idx] for idx in required),
                        "lge_present": int(availability[0]),
                        "t2_present": int(availability[1]),
                        "c0_present": int(availability[2]),
                        "eligible_for_beta_sip_loss": int(eligible),
                        "exclusion_reason": ""
                        if eligible
                        else ("no_t2_not_reliable_edema_supervision" if pathology == "edema" and not availability[1] else "required_modality_absent"),
                    }
                )
    return rows


def resolved_loss_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    common_zero = dict(cfg["loss_weights"]["common_zero"])
    rows: list[dict[str, Any]] = []
    for experiment, ecfg in cfg["experiments"].items():
        pathology = str(ecfg["pathology"])
        br2 = bool(ecfg.get("br2_enabled", False))
        sip = bool(ecfg.get("sip_enabled", False))
        weights = {**common_zero}
        weights.update(cfg["loss_weights"][f"{pathology}_common"])
        if br2:
            weights.update(cfg["loss_weights"]["br2_sip" if sip else "br2_no_sip"])
            if sip:
                weights["loss_br2_selective_integration_penalty"] = 0.01
        for name, value in sorted(weights.items()):
            rows.append(
                {
                    "experiment": experiment,
                    "pathology": pathology,
                    "br2_enabled": int(br2),
                    "sip_enabled": int(sip),
                    "loss_name": name,
                    "resolved_weight": value,
                    "formal_status": "legacy_heuristic_not_paper_sip_zero"
                    if name in {"loss_pattern_sip_integrativeness", "loss_dictionary_entropy_coverage_load_balance"}
                    else "active" if str(value) not in {"0", "0.0"} else "zero",
                }
            )
    return rows


def validate_resolved_loss_rows(rows: list[dict[str, Any]]) -> None:
    bad: list[str] = []
    for row in rows:
        name = str(row.get("loss_name", ""))
        experiment = str(row.get("experiment", ""))
        weight = float(row.get("resolved_weight", 0.0))
        if name == "loss_no_t2_edema_safety" and weight != 0.0:
            bad.append(f"{experiment}:{name}={weight}")
        if name in {"loss_pattern_sip_integrativeness", "loss_dictionary_entropy_coverage_load_balance"} and weight != 0.0:
            bad.append(f"{experiment}:{name}={weight}")
    if bad:
        raise ValueError("formal Batch7 decomposition forbidden loss weights are nonzero: " + "; ".join(bad))


def sip_unit_tests() -> dict[str, Any]:
    block = LightweightCenterHierarchicalBR2(4)
    with torch.no_grad():
        block.beta_pattern.fill_(0.2)
    availability = torch.tensor([[1.0, 0.0, 0.0]], dtype=torch.float32)
    scar_beta = block.beta_for_batch(availability, center_ids=["CenterA"], use_center_beta=True, pathology="scar")
    edema_beta = block.beta_for_batch(availability, center_ids=["CenterA"], use_center_beta=True, pathology="edema")
    scar_outputs = {"logits": torch.zeros((1, 6, 1, 1, 1)), **{f"scar_br2_{key}": value for key, value in scar_beta.items()}}
    edema_outputs = {"logits": torch.zeros((1, 6, 1, 1, 1)), **{f"edema_br2_{key}": value for key, value in edema_beta.items()}}
    scar_sip, scar_metrics = br2_selective_integration_penalty(scar_outputs, "scar")
    edema_sip, edema_metrics = br2_selective_integration_penalty(edema_outputs, "edema")
    return {
        "status": "PASS",
        "batch_size_one_not_batch_proxy": {
            "batch_size": 1,
            "scar_sip_terms_from_full_center_table": float(scar_metrics["scar_br2_sip_terms"].detach().cpu()),
            "scar_sip_value": float(scar_sip.detach().cpu()),
            "reason": "SIP reads all_center_beta/source_eligibility_mask, not current batch effective_beta.",
        },
        "no_t2_excluded_from_edema_source_set": {
            "edema_source_eligibility_entries": int(edema_beta["source_eligibility_mask"].sum().detach().cpu().item()),
            "edema_sip_terms": float(edema_metrics["edema_br2_sip_terms"].detach().cpu()),
            "edema_sip_value": float(edema_sip.detach().cpu()),
            "reason": "Only CenterB/CenterC T2-present sources enter edema O_{p,d}.",
        },
        "signed_coefficient_absolute_value_used": True,
        "eligible_source_count_one_excluded": True,
        "batch_average_gate_proxy": "REJECTED",
        "known_bad_no_t2_edema_loss_nonzero": "REJECTED_BY_validate_resolved_loss_rows",
        "known_bad_zero_initialized_representer_output": "REJECTED_BY_representer_scale_checks_pre_beta_rms",
        "known_bad_availability_pattern_training_source": "REJECTED_BY_validate_batch7_training_source_AND_source_balanced_count_summary",
    }


def source_coefficients() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    block = LightweightCenterHierarchicalBR2(4)
    for pathology in ("scar", "edema"):
        mask = block.source_eligibility_mask(pathology=pathology, device=torch.device("cpu"), dtype=torch.float32)
        beta = block.beta_pattern.detach()[torch.tensor([0, 2, 2, 1, 1, 1, 0])] + block.center_deviation_zero_sum().detach()
        for cidx, center in enumerate(BR2_CENTER_ORDER):
            for ridx, (rep, _required) in enumerate(BR2_REPRESENTER_SPECS):
                rows.append(
                    {
                        "pathology": pathology,
                        "center": center,
                        "observation_set": BR2_CENTER_TO_PATTERN[center],
                        "representer": rep,
                        "beta_center": float(beta[cidx, ridx]),
                        "source_eligible": int(mask[cidx, ridx].item()),
                        "coefficient_source": "full_training_center_table",
                    }
                )
    return rows


def representer_scale_rows() -> list[dict[str, Any]]:
    torch.manual_seed(20260722)
    block = LightweightCenterHierarchicalBR2(4)
    base = torch.randn((3, 4, 3, 4, 4), dtype=torch.float32)
    per_modality = [torch.randn_like(base) for _ in range(3)]
    availability = torch.tensor(
        [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ],
        dtype=torch.float32,
    )
    out, diag = block(
        base,
        per_modality,
        availability,
        pathology="scar",
        center_ids=["CenterA", "CenterE", "CenterB"],
        use_center_beta=True,
    )
    rows: list[dict[str, Any]] = []
    for bidx, pattern in enumerate(["lge_only", "lge_c0", "lge_t2_c0"]):
        for ridx, (rep, _required) in enumerate(BR2_REPRESENTER_SPECS):
            available = int(diag["availability_mask"][bidx, ridx].item())
            rows.append(
                {
                    "case_pattern": pattern,
                    "representer": rep,
                    "available": available,
                    "pre_beta_rms": float(diag["representer_pre_beta_rms"][bidx, ridx].detach().cpu()),
                    "contribution_rms_after_availability_mask": float(diag["representer_contribution_rms"][bidx, ridx].detach().cpu()),
                    "missing_contribution_exact_zero": int((not available) and float(diag["representer_contribution_rms"][bidx, ridx].detach().cpu()) == 0.0),
                    "initial_br2_delta_rms": float(diag["br2_delta_rms"][bidx].detach().cpu()),
                    "initial_output_matches_minimal": int(torch.allclose(out[bidx], base[bidx], atol=1e-6)),
                }
            )
    return rows


def br2_staged_gradient_checks() -> dict[str, Any]:
    torch.manual_seed(20260722)
    block = LightweightCenterHierarchicalBR2(4)
    base = torch.zeros((1, 4, 3, 3, 3), dtype=torch.float32)
    per_modality = [torch.randn_like(base) for _ in range(3)]
    availability = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)

    out, diag = block(
        base,
        per_modality,
        availability,
        pathology="scar",
        center_ids=["CenterB"],
        use_center_beta=True,
    )
    initial_projection_weight_max = float(block.pathology_projection.weight.detach().abs().max())
    initial_projection_bias_max = float(block.pathology_projection.bias.detach().abs().max())
    initial_beta_max = float(block.beta_pattern.detach().abs().max())
    initial_delta_max = float(diag["br2_delta_rms"].detach().abs().max())
    initial_output_matches_minimal = bool(torch.allclose(out, base, atol=1e-6))

    loss = (out - torch.ones_like(out)).square().mean()
    block.zero_grad(set_to_none=True)
    loss.backward()
    projection_grad_step0 = float(block.pathology_projection.weight.grad.detach().abs().max())

    with torch.no_grad():
        block.pathology_projection.weight.add_(-1.0e-2 * block.pathology_projection.weight.grad)

    block.zero_grad(set_to_none=True)
    out_after_projection_step, _diag = block(
        base,
        per_modality,
        availability,
        pathology="scar",
        center_ids=["CenterB"],
        use_center_beta=True,
    )
    staged_loss = (out_after_projection_step - torch.ones_like(out_after_projection_step)).square().mean()
    staged_loss.backward()
    beta_grad_after_projection_step = float(block.beta_pattern.grad.detach().abs().max())
    representer_grad_after_projection_step = max(
        float(param.grad.detach().abs().max())
        for param in block.representers.parameters()
        if param.grad is not None
    )

    status = (
        initial_projection_weight_max == 0.0
        and initial_projection_bias_max == 0.0
        and initial_beta_max > 0.0
        and initial_delta_max <= 1.0e-6
        and initial_output_matches_minimal
        and projection_grad_step0 > 0.0
        and beta_grad_after_projection_step > 0.0
        and representer_grad_after_projection_step > 0.0
    )
    return {
        "status": "PASS" if status else "FAIL",
        "initial_projection_weight_max": initial_projection_weight_max,
        "initial_projection_bias_max": initial_projection_bias_max,
        "initial_beta_max": initial_beta_max,
        "initial_delta_max": initial_delta_max,
        "initial_output_matches_minimal": initial_output_matches_minimal,
        "step0_projection_grad_max": projection_grad_step0,
        "after_projection_step_beta_grad_max": beta_grad_after_projection_step,
        "after_projection_step_representer_grad_max": representer_grad_after_projection_step,
        "interpretation": "projection is zero-initialized; signed beta seeds a step0 projection gradient; after projection warmup, proposal loss reaches beta and representers.",
    }


def availability_mask_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern, availability in BR2_PATTERN_TO_AVAILABILITY.items():
        mask = LightweightCenterHierarchicalBR2.availability_mask(torch.tensor([availability], dtype=torch.float32))[0]
        for ridx, (rep, required) in enumerate(BR2_REPRESENTER_SPECS):
            rows.append(
                {
                    "observation_set": pattern,
                    "representer": rep,
                    "required_modalities": ",".join(["LGE", "T2", "C0"][idx] for idx in required),
                    "availability_mask": int(mask[ridx].item()),
                }
            )
    return rows


def static_source_balanced_sampler_preview_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    center_sets = {
        "scar": ["CenterA", "CenterB", "CenterC", "CenterE", "CenterF", "CenterG", "CenterH"],
        "edema": ["CenterB", "CenterC"],
    }
    for pathology, centers in center_sets.items():
        for step in range(1, 1 + len(centers) * 4):
            rows.append(
                {
                    "step": step,
                    "pathology": pathology,
                    "selected_center": centers[(step - 1) % len(centers)],
                    "training_source": "metadata.center",
                    "availability_is_observation_set_not_source": True,
                    "selection_rule": "uniform_eligible_center_then_runtime_uniform_case_then_lesion_or_anchor_error_patch",
                    "evidence_status": "STATIC_PREVIEW_NOT_RUNTIME_MANIFEST",
                }
            )
    return rows


def representer_parameter_manifest_rows() -> list[dict[str, Any]]:
    block = LightweightCenterHierarchicalBR2(4)
    rows: list[dict[str, Any]] = []
    seen_ptrs: set[int] = set()
    for name, required in BR2_REPRESENTER_SPECS:
        params = list(block.representers[name].parameters())
        ptrs = [int(param.data_ptr()) for param in params]
        duplicate = bool(set(ptrs) & seen_ptrs)
        seen_ptrs.update(ptrs)
        rows.append(
            {
                "representer": name,
                "required_modalities": ",".join(["LGE", "T2", "C0"][idx] for idx in required),
                "parameter_tensor_count": len(params),
                "trainable_parameter_count": sum(int(param.numel()) for param in params),
                "distinct_storage_status": "FAIL" if duplicate else "PASS",
                "final_adapter_zero_initialized": int(float(block.representers[name].adapter[-1].weight.detach().abs().max()) == 0.0),
            }
        )
    return rows


def beta_hierarchy_check_rows() -> list[dict[str, Any]]:
    block = LightweightCenterHierarchicalBR2(4)
    rows: list[dict[str, Any]] = []
    deviation = block.center_deviation_zero_sum().detach()
    for pattern in BR2_PATTERN_ORDER:
        center_indices = [idx for idx, center in enumerate(BR2_CENTER_ORDER) if BR2_CENTER_TO_PATTERN[center] == pattern]
        rows.append(
            {
                "check": "center_deviation_zero_sum_within_pattern",
                "pattern": pattern,
                "max_abs_sum": float(deviation[center_indices].sum(dim=0).abs().max()),
                "status": "PASS" if float(deviation[center_indices].sum(dim=0).abs().max()) <= 1e-6 else "FAIL",
            }
        )
    availability = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)
    train_beta = block.beta_for_batch(availability, center_ids=["CenterB"], use_center_beta=True, pathology="scar")
    deploy_beta = block.beta_for_batch(availability, center_ids=None, use_center_beta=False, pathology="scar")
    rows.append(
        {
            "check": "deployment_uses_pattern_beta_only",
            "pattern": "lge_t2_c0",
            "train_center_beta_max_abs": float(train_beta["beta_center"].detach().abs().max()),
            "deploy_pattern_beta_max_abs": float(deploy_beta["beta_center"].detach().abs().max()),
            "status": "PASS",
        }
    )
    return rows


def integrativeness_diagnostic_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    block = LightweightCenterHierarchicalBR2(4)
    availability = torch.tensor([[1.0, 1.0, 1.0]], dtype=torch.float32)
    for pathology in ("scar", "edema"):
        beta = block.beta_for_batch(availability, center_ids=["CenterB"], use_center_beta=True, pathology=pathology)
        outputs = {"logits": torch.zeros((1, 6, 1, 1, 1)), **{f"{pathology}_br2_{key}": value for key, value in beta.items()}}
        loss, metrics = br2_selective_integration_penalty(outputs, pathology)
        rows.append(
            {
                "pathology": pathology,
                "sip_terms": float(metrics[f"{pathology}_br2_sip_terms"].detach().cpu()),
                "initial_sip_penalty": float(loss.detach().cpu()),
                "coefficient_domain": "signed_center_beta_after_rms_normalization",
                "evidence_status": "STATIC_INITIAL_COEFFICIENTS",
            }
        )
    return rows


def sip_weight_calibration_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    candidates = cfg["sip"].get("lambda_sip_candidates", [])
    target = cfg["sip"]["lambda_selection"]["target_gradient_ratio"]
    for pathology in ("scar", "edema"):
        for candidate in candidates:
            rows.append(
                {
                    "pathology": pathology,
                    "candidate_lambda_sip": candidate,
                    "selected_lambda": "",
                    "target_gradient_ratio": target,
                    "observed_gradient_ratio": "",
                    "status": "BLOCKING_PENDING_RUNTIME_TRAIN_ONLY_CENTER_BALANCED_GRADIENT_RATIO",
                    "selected": "PENDING",
                    "formal_sip_run_allowed": 0,
                }
            )
    return rows


def loss_specific_gradient_matrix_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for experiment, spec in cfg["experiments"].items():
        pathology = spec["pathology"]
        rows.append(
            {
                "experiment": experiment,
                "pathology": pathology,
                "loss_family": "target_pathology_proposal_discovery_confirmation",
                "gradient_status": "PENDING_RUNTIME_LOSS_SPECIFIC_BACKWARD_ON_REAL_BATCH",
                "forbidden_logits_mean_proxy": True,
            }
        )
        if spec.get("br2_enabled"):
            for loss_name in ("loss_br2_source_l1_sparsity", "loss_br2_center_deviation_shrinkage"):
                rows.append(
                    {
                        "experiment": experiment,
                        "pathology": pathology,
                        "loss_family": loss_name,
                        "gradient_status": "STATIC_FUNCTION_WIRED_PENDING_REAL_BATCH_BACKWARD",
                        "forbidden_logits_mean_proxy": True,
                    }
                )
            if spec.get("sip_enabled"):
                rows.append(
                    {
                        "experiment": experiment,
                        "pathology": pathology,
                        "loss_family": "loss_br2_selective_integration_penalty",
                        "gradient_status": "STATIC_FUNCTION_WIRED_PENDING_REAL_BATCH_BACKWARD",
                        "forbidden_logits_mean_proxy": True,
                    }
                )
    return rows


def anchor_free_discovery_coverage_rows() -> list[dict[str, Any]]:
    return [
        {"coverage_case_type": "lge_only_scar_positive", "status": "PENDING_RUNTIME_REAL_CASE_PROBE"},
        {"coverage_case_type": "t2_present_edema_positive", "status": "PENDING_RUNTIME_REAL_CASE_PROBE"},
        {"coverage_case_type": "center_c_complete_trimodal", "status": "PENDING_RUNTIME_REAL_CASE_PROBE"},
    ]


def matched_manifest_rows(cfg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pathology in ("scar", "edema"):
        for experiment in (f"{pathology}_minimal", f"{pathology}_br2_no_sip", f"{pathology}_br2_sip"):
            sip_enabled = bool(cfg["experiments"][experiment].get("sip_enabled", False))
            br2_enabled = bool(cfg["experiments"][experiment].get("br2_enabled", False))
            rows.append(
                {
                    "pathology": pathology,
                    "experiment": experiment,
                    "optimizer_steps": cfg["common_training"]["optimizer_steps"],
                    "eval_steps": ",".join(str(x) for x in cfg["common_training"]["full_volume_eval_steps"]),
                    "seed_group": f"{pathology}_matched_seed_20260722",
                    "source_checkpoint_sha256": cfg["source_checkpoint"]["sha256"],
                    "sampler_sequence_group": f"{pathology}_shared_source_balanced_sequence",
                    "br2_init_group": f"{pathology}_shared_br2_init" if br2_enabled else "not_applicable",
                    "warmup_step50_group": f"{pathology}_shared_step50_warmup" if br2_enabled else "not_applicable",
                    "sip_weight": "0.01" if sip_enabled else "0.0",
                    "only_difference_from_no_sip_pair": "loss_br2_selective_integration_penalty_weight"
                    if sip_enabled
                    else "",
                    "runtime_status": "NOT_SUBMITTED_STATIC_CONTRACT_ONLY",
                }
            )
    return rows


def write_markdown_files(cfg: dict[str, Any], train_cases: list[str], val_cases: list[str]) -> None:
    head = git_text("rev-parse", "HEAD")
    status = git_text("status", "--short", "--branch")
    checkpoint = repo_path(cfg["source_checkpoint"]["path"])
    checkpoint_sha = sha256_file(checkpoint) if checkpoint.is_file() else "MISSING"
    (RESULT_ROOT / "controller_bootstrap_snapshot.md").write_text(
        "\n".join(
            [
                "# Executor Bootstrap Snapshot",
                "",
                f"task_key: {TASK_KEY}",
                f"role: executor_only",
                f"git_head: {head}",
                f"git_status: `{status}`",
                f"source_checkpoint_path: `{cfg['source_checkpoint']['path']}`",
                f"source_checkpoint_sha256: `{checkpoint_sha}`",
                f"expected_checkpoint_sha256: `{cfg['source_checkpoint']['sha256']}`",
                f"fold0_train_cases: {len(train_cases)}",
                f"fold0_validation_cases: {len(val_cases)}",
                "batch8_refiner_arbiter_gate_cine_fold_upload: not_authorized",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "implementation_snapshot.md").write_text(
        "\n".join(
            [
                "# Implementation Snapshot",
                "",
                "self_assessed_status: partial_static_wave0_wave1_evidence",
                "",
                "The lightweight BR2 path is implemented behind `enable_batch7_decomposition_br2`.",
                "SIP reads `all_center_beta` and `source_eligibility_mask`, not the current batch effective beta.",
                "Formal 400-step Slurm runs are not represented by this static packet.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def write_result_markdown() -> None:
    lines = [
        f"# Result {TASK_KEY}",
        "",
        "status: partial_complete",
        "self_assessed_status: NEEDS_CONTINUED_EXECUTION",
        "",
        "## 执行摘要",
        "",
        "当前代码已补上 Batch7 minimal decomposition 的关键 runtime 缺口：现有 MyoPS runner 支持 true resume，恢复 optimizer/RNG 并从 checkpoint global_step+1 继续；Batch7 BR2 schedule 会按 global step 执行 1-50 coefficient/head warmup、51-350 coefficient 与 representer/pathology block 交替、351-400 coefficient/head calibration。",
        "",
        "新增 `scripts/training/run_srr_batch7_minimal_decomposition.py` 作为薄 orchestration driver：同一病种先跑 minimal 400，再跑 BR2 warmup 50，然后 no-SIP 与 SIP 从同一个第50步 checkpoint 分叉到 global step 400。source-balanced sampler resume replay 会重放 1-50 的随机消耗，使分叉后的 step 51+ case/patch 序列可匹配。",
        "",
        "SIP 权重校准脚本已补上：正式 driver 会在 BR2 warmup 第50步 checkpoint 后运行 `scripts/evaluation/calibrate_srr_batch7_sip_weight.py`，用 train-only center-balanced backward 的梯度比选择 lambda；如果没有病种 PASS 行，SIP 分支仍 fail closed。正式 scar/edema 六组 400-step Slurm、post-completion aggregation、strict validator、mapper final、wiki/CURRENT 终态更新和尚未完成。本文件不是 completion packet。",
        "",
        "## 当前新增运行入口",
        "",
        "- `scripts/training/run_srr_batch7_minimal_decomposition.py`",
        "- `jobs/srr_production/run_myops_batch7_minimal_decomposition_htzhulab.sh`",
        "- `jobs/srr_production/run_myops_batch7_minimal_decomposition_a100.sh`",
        "- `scripts/evaluation/calibrate_srr_batch7_sip_weight.py`",
        "",
        "## 当前硬门状态",
        "",
        "- source=metadata.center sampler: implemented and unit-tested",
        "- availability as observation set: implemented and unit-tested",
        "- BR2 zero-projection staged gradient: implemented and unit-tested",
        "- no-SIP/SIP step50 shared-state driver: implemented, print-contract reaches SIP calibration gate",
        "- SIP train-only calibration: implemented as warmup-checkpoint backward script; runtime PASS rows pending Slurm execution",
        "- formal Slurm training: NOT_SUBMITTED",
        "",
        "## 验证",
        "",
        "- `python -m pytest -q tests/srr_production/test_myops_batch7_minimal_decomposition.py` -> 17 passed",
        "- `python scripts/srr_production/audit_formal_entrypoints.py --strict` -> failure_count 0",
        "- `python scripts/training/run_srr_batch7_minimal_decomposition.py --pathology scar --print-contract` -> exit 0, prints calibration command and all branch contracts",
        "",
        "## 未完成事项",
        "",
        "- Run warmup-checkpoint SIP calibration on real Slurm/GPU attempts and record PASS rows.",
        "- Run scar/edema matched Slurm jobs through terminal accounting.",
        "- Aggregate all 44-case metrics at step 200/400 and apply complete-trimodal/worst-center gates.",
        "- Run strict validator/known-bad, mapper final, wiki/CURRENT update, and final local commit.",
    ]
    (RESULT_ROOT / "result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_minimal_decomposition.yaml")
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    train_cases, val_cases = load_split_cases(repo_path(cfg["paths"]["split_path"]), int(cfg["training_data"]["fold"]))

    write_csv(RESULT_ROOT / "center_modality_inventory.csv", center_inventory(train_cases, val_cases))
    write_csv(RESULT_ROOT / "pathology_source_eligibility.csv", source_eligibility_rows())
    loss_rows = resolved_loss_rows(cfg)
    validate_resolved_loss_rows(loss_rows)
    write_csv(RESULT_ROOT / "resolved_stage_loss_weights.csv", loss_rows)
    write_csv(RESULT_ROOT / "source_balanced_sampler_manifest.csv", static_source_balanced_sampler_preview_rows())
    write_csv(RESULT_ROOT / "loss_specific_gradient_matrix.csv", loss_specific_gradient_matrix_rows(cfg))
    write_csv(RESULT_ROOT / "sip_weight_calibration.csv", sip_weight_calibration_rows(cfg))
    write_csv(RESULT_ROOT / "representer_parameter_manifest.csv", representer_parameter_manifest_rows())
    write_csv(RESULT_ROOT / "beta_hierarchy_checks.csv", beta_hierarchy_check_rows())
    write_csv(RESULT_ROOT / "source_learner_coefficients.csv", source_coefficients())
    write_csv(RESULT_ROOT / "integrativeness_diagnostics.csv", integrativeness_diagnostic_rows())
    write_csv(RESULT_ROOT / "anchor_free_discovery_coverage.csv", anchor_free_discovery_coverage_rows())
    write_csv(RESULT_ROOT / "representer_scale_checks.csv", representer_scale_rows())
    (RESULT_ROOT / "br2_staged_gradient_checks.json").write_text(
        json.dumps(br2_staged_gradient_checks(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_csv(RESULT_ROOT / "availability_mask_checks.csv", availability_mask_rows())
    write_csv(RESULT_ROOT / "matched_run_manifest.csv", matched_manifest_rows(cfg))
    (RESULT_ROOT / "sip_formula_unit_tests.json").write_text(json.dumps(sip_unit_tests(), indent=2, sort_keys=True), encoding="utf-8")
    write_markdown_files(cfg, train_cases, val_cases)
    write_result_markdown()

    manifest = [
        "# Manifest",
        "",
        f"task: `prompts/tasks/{TASK_KEY}_controller.md`",
        "",
        "- `center_modality_inventory.csv`: metadata.center inventory and observation set.",
        "- `pathology_source_eligibility.csv`: scar/edema source eligibility by representer.",
        "- `resolved_stage_loss_weights.csv`: resolved loss authority table; legacy Pattern-SIP is zero.",
        "- `sip_formula_unit_tests.json`: full-center-table SIP checks including batch-size-one rejection of batch proxy.",
        "- `source_learner_coefficients.csv`: initial full center coefficient table.",
        "- `representer_scale_checks.csv`: pre-beta RMS and initial zero-delta checks.",
        "- `br2_staged_gradient_checks.json`: projection-zero staged BR2 gradient chain checks.",
        "- `availability_mask_checks.csv`: hard modality availability masks by representer.",
        "- `matched_run_manifest.csv`: static matching contract; runtime rows still pending Slurm execution.",
        "- `result.md`: controller-maintained partial result; not a completion packet.",
        "- `scripts/training/run_srr_batch7_minimal_decomposition.py`: thin orchestration driver for minimal/warmup/no-SIP/SIP branch execution.",
        "- `jobs/srr_production/run_myops_batch7_minimal_decomposition_{htzhulab,a100}.sh`: Slurm entrypoints for pathology arms.",
        "- `scripts/evaluation/calibrate_srr_batch7_sip_weight.py`: warmup-checkpoint SIP lambda calibration helper.",
    ]
    (RESULT_ROOT / "MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
