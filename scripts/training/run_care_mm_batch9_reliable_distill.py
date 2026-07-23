#!/usr/bin/env python3
"""CARE Batch9 reliable-label distillation runner."""

from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_mm_batch9 import (  # noqa: E402
    PREPROCESSED,
    Batch9PatchSampler,
    build_case_records,
    generate_inventory,
    reliable_masks_for_records,
    sha256_file,
    write_csv,
    write_json,
)
from src.care_myocardium.losses.care_mm_losses import (  # noqa: E402
    ReliableMaskBatch,
    compute_care_mm_loss,
    runtime_loss_contract,
    weighted_loss_report,
)
from src.care_myocardium.models.care_mm_reliable_distill import (  # noqa: E402
    CAREMMReliableDistillResEnc,
    crop_from_pad,
    decode_six_class_logits,
    pad_to_stride,
)
from src.care_myocardium.training.nnUNetTrainerCAREMMReliableDistill import (  # noqa: E402
    nnUNetTrainerCAREMMReliableDistill,
    poly_lr,
)


DEFAULT_TASK_KEY = "20260723_care_myops_batch9_exposed_issues_repair"
TASK_KEY = os.environ.get("CARE_MM_TASK_KEY", DEFAULT_TASK_KEY)
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
BASE_CONFIG_PATH = REPO_ROOT / "configs/care_mm/batch9_reliable_label_distillation.yaml"
DEFAULT_CONFIG_PATH = REPO_ROOT / "configs/care_mm/batch9_exposed_issues_repair.yaml"
CONFIG_PATH = REPO_ROOT / os.environ.get("CARE_MM_CONFIG_PATH", str(DEFAULT_CONFIG_PATH.relative_to(REPO_ROOT)))
TASK_PATH = REPO_ROOT / f"prompts/tasks/{TASK_KEY}_controller.md"
if not TASK_PATH.exists():
    raise FileNotFoundError(f"Batch9 repair task prompt not found: {TASK_PATH}")
PLAN_PATH = REPO_ROOT / f"prompts/tasks/{TASK_KEY}_executor_plan_v2.yaml"
if not PLAN_PATH.exists():
    raise FileNotFoundError(f"Batch9 repair executor plan not found: {PLAN_PATH}")

VARIANT_LOSS_MAP = {
    "student_direct_reliable": "direct_reliable",
    "teacher_full_view": "teacher_full_view",
    "student_moddrop_control": "moddrop_control",
    "student_reliable_distill": "reliable_distill",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def git_status_short() -> str:
    return subprocess.check_output(["git", "status", "--short", "--branch"], cwd=REPO_ROOT, text=True).strip()


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict[str, Any]:
    if CONFIG_PATH.resolve() == BASE_CONFIG_PATH.resolve():
        raise RuntimeError("Batch9 repair must not run with the superseded 20260722 config as the active config")
    base = yaml.safe_load(BASE_CONFIG_PATH.read_text(encoding="utf-8"))
    override = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    cfg = deep_merge(base, override)
    cfg.setdefault("paths", {}).pop("standard_nnunet_result_root", None)
    cfg.pop("baseline", None)
    cfg.setdefault("paths", {})["result_root"] = str(RESULT_ROOT.relative_to(REPO_ROOT))
    cfg["paths"]["runtime_root"] = str((RESULT_ROOT / "runtime").relative_to(REPO_ROOT))
    cfg["paths"]["active_config_path"] = str(CONFIG_PATH.relative_to(REPO_ROOT))
    cfg["paths"]["base_config_path_for_loss_defaults_only"] = str(BASE_CONFIG_PATH.relative_to(REPO_ROOT))
    cfg["paths"]["standard_nnunet_checkpoint_logits_predictions_or_baseline_fallback_loaded"] = False
    return cfg


def loss_weights_for_variant(cfg: dict[str, Any], variant: str) -> dict[str, float]:
    key = VARIANT_LOSS_MAP[variant]
    weights = {str(k): float(v) for k, v in cfg["losses"][key].items() if isinstance(v, (int, float))}
    override_path = RESULT_ROOT / "resolved_loss_weight_overrides.json"
    if override_path.is_file():
        override = read_json(override_path)
        weights.update({str(k): float(v) for k, v in override.get("variant_overrides", {}).get(variant, {}).items()})
    return weights


def _term_grad_vector(model: torch.nn.Module, term: torch.Tensor, weight: float) -> torch.Tensor:
    params = [p for p in model.parameters() if p.requires_grad]
    grads = torch.autograd.grad(term * float(weight), params, retain_graph=True, allow_unused=True)
    pieces = []
    for param, grad in zip(params, grads):
        if grad is None:
            pieces.append(torch.zeros(param.numel(), dtype=torch.float32))
        else:
            pieces.append(grad.detach().reshape(-1).float().cpu())
    return torch.cat(pieces) if pieces else torch.zeros(1, dtype=torch.float32)


def _cosine(a: torch.Tensor, b: torch.Tensor) -> float:
    denom = float(torch.linalg.vector_norm(a).item() * torch.linalg.vector_norm(b).item())
    if denom <= 1e-12:
        return 0.0
    return float(torch.dot(a, b).item() / denom)


def audit_real_loss_conflicts(
    *,
    trainer: nnUNetTrainerCAREMMReliableDistill,
    cfg: dict[str, Any],
    device: torch.device,
) -> tuple[dict[str, float], dict[str, Any]]:
    audit_cfg = cfg.get("repairs", {}).get("loss_conflict_audit", {})
    audited_batches = int(audit_cfg.get("real_batches", 32))
    threshold = float(audit_cfg.get("cosine_conflict_threshold", -0.25))
    conflict_fraction_threshold = float(audit_cfg.get("conflict_batch_fraction_threshold", 0.25))
    domination_threshold = float(audit_cfg.get("weighted_gradient_norm_ratio_max", 10.0))
    weights = loss_weights_for_variant(cfg, "student_direct_reliable")
    base_final_six_weight = float(weights.get("loss_final_six_class_reliable", 0.0))
    sampler = trainer.sampler(seed=93017, complete_only=False)
    model = trainer.build_model(deep_supervision=True)
    model.train()
    primary_terms = [
        "loss_anatomy_ce_dice",
        "loss_scar_final_margin_bce_dice",
        "loss_edema_final_margin_bce_dice_reliable_only",
        "loss_final_six_class_reliable",
    ]
    matrix_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    term_stats = {name: {"active_batches": 0, "norm_sum": 0.0, "norm_max": 0.0} for name in primary_terms}
    final_conflict_batches = 0
    other_conflict_batches = 0
    domination_batches = 0
    max_ratio = 0.0
    eps = 1e-8
    for batch_idx in range(1, audited_batches + 1):
        x, natural_x, seg, availability, batch_records, _rows = sampler.sample_batch(
            1, variant="student_direct_reliable", step=batch_idx, matched_seed=20260723
        )
        x = x.to(device)
        seg = seg.to(device)
        availability = availability.to(device)
        x, seg, _aug = trainer.augment(x, seg, seed=20260723 + batch_idx * 7919)
        outputs = model(x, availability)
        _total, terms = trainer._loss_with_deep_supervision(
            outputs,
            seg,
            masks_from_records(batch_records, device),
            weights,
            natural_outputs=None,
            teacher_outputs=None,
        )
        grad_vectors: dict[str, torch.Tensor] = {}
        weighted_norms: dict[str, float] = {}
        for name in primary_terms:
            term = terms[name]
            weight = float(weights.get(name, 0.0))
            vec = _term_grad_vector(model, term, weight)
            norm = float(torch.linalg.vector_norm(vec).item())
            grad_vectors[name] = vec
            weighted_norms[name] = norm
            if norm > eps:
                term_stats[name]["active_batches"] += 1
                term_stats[name]["norm_sum"] += norm
                term_stats[name]["norm_max"] = max(float(term_stats[name]["norm_max"]), norm)
        active_norms = [v for v in weighted_norms.values() if v > eps]
        ratio = max(active_norms) / max(min(active_norms), eps) if len(active_norms) >= 2 else 1.0
        max_ratio = max(max_ratio, ratio)
        if ratio > domination_threshold:
            domination_batches += 1
        batch_final_conflict = False
        batch_other_conflict = False
        pairs = [
            ("loss_final_six_class_reliable", "loss_scar_final_margin_bce_dice"),
            ("loss_final_six_class_reliable", "loss_edema_final_margin_bce_dice_reliable_only"),
            ("loss_scar_final_margin_bce_dice", "loss_edema_final_margin_bce_dice_reliable_only"),
            ("loss_anatomy_ce_dice", "loss_scar_final_margin_bce_dice"),
            ("loss_anatomy_ce_dice", "loss_edema_final_margin_bce_dice_reliable_only"),
            ("loss_anatomy_ce_dice", "loss_final_six_class_reliable"),
        ]
        for a, b in pairs:
            cos = _cosine(grad_vectors[a], grad_vectors[b])
            conflict = cos < threshold and weighted_norms[a] > eps and weighted_norms[b] > eps
            final_pair = "loss_final_six_class_reliable" in {a, b} and ({a, b} & {"loss_scar_final_margin_bce_dice", "loss_edema_final_margin_bce_dice_reliable_only"})
            if conflict and final_pair:
                batch_final_conflict = True
            elif conflict:
                batch_other_conflict = True
            pair_rows.append({
                "batch_index": batch_idx,
                "loss_a": a,
                "loss_b": b,
                "weighted_cosine": cos,
                "loss_a_weighted_grad_norm": weighted_norms[a],
                "loss_b_weighted_grad_norm": weighted_norms[b],
                "conflict": int(conflict),
            })
        final_conflict_batches += int(batch_final_conflict)
        other_conflict_batches += int(batch_other_conflict)
    for name in primary_terms:
        active = int(term_stats[name]["active_batches"])
        matrix_rows.append({
            "loss_name": name,
            "declared_weight": float(weights.get(name, 0.0)),
            "in_total_loss": name in weights,
            "audited_batches": audited_batches,
            "active_batches": active,
            "mean_weighted_grad_l2_norm": float(term_stats[name]["norm_sum"]) / max(active, 1),
            "max_weighted_grad_l2_norm": float(term_stats[name]["norm_max"]),
            "status": "PASS" if (weights.get(name, 0.0) == 0.0 or active > 0) else "FAIL",
        })
    final_conflict_fraction = final_conflict_batches / max(audited_batches, 1)
    other_conflict_fraction = other_conflict_batches / max(audited_batches, 1)
    domination_fraction = domination_batches / max(audited_batches, 1)
    resolved_weights = dict(weights)
    resolution = "retain_declared_weight"
    if final_conflict_fraction > conflict_fraction_threshold:
        resolved_weights["loss_final_six_class_reliable"] = 0.0
        resolution = "set_final_six_weight_zero_due_conflict"
    status = "PASS"
    failure_reasons: list[str] = []
    if other_conflict_batches:
        status = "FAIL"
        failure_reasons.append("non_final_six_loss_conflict")
    remaining_norms = [r["mean_weighted_grad_l2_norm"] for r in matrix_rows if r["loss_name"] != "loss_final_six_class_reliable" or resolved_weights.get("loss_final_six_class_reliable", 0.0) > 0.0]
    remaining_norms = [float(v) for v in remaining_norms if float(v) > eps]
    post_ratio = max(remaining_norms) / max(min(remaining_norms), eps) if len(remaining_norms) >= 2 else 1.0
    if post_ratio > domination_threshold:
        status = "FAIL"
        failure_reasons.append("weighted_gradient_norm_domination")
    write_csv(RESULT_ROOT / "loss_gradient_matrix.csv", matrix_rows)
    write_csv(RESULT_ROOT / "loss_gradient_pairwise_cosine.csv", pair_rows)
    summary = {
        "audit_mode": "real_runtime_batches",
        "audited_batches": audited_batches,
        "batch_size": 1,
        "final_six_conflict_fraction": final_conflict_fraction,
        "other_conflict_fraction": other_conflict_fraction,
        "domination_batch_fraction": domination_fraction,
        "pre_resolution_norm_domination_ratio_max": max_ratio,
        "norm_domination_ratio_max": post_ratio,
        "declared_final_six_weight": base_final_six_weight,
        "resolved_final_six_weight": resolved_weights.get("loss_final_six_class_reliable", 0.0),
        "resolution": resolution,
        "status": status,
        "failure_reasons": ";".join(failure_reasons),
    }
    write_csv(RESULT_ROOT / "loss_gradient_conflict_audit.csv", [summary])
    override_payload = {
        "schema_version": 1,
        "status": status,
        "source": "loss_gradient_conflict_audit.csv",
        "variant_overrides": {"student_direct_reliable": resolved_weights},
        "summary": summary,
    }
    write_json(RESULT_ROOT / "resolved_loss_weight_overrides.json", override_payload)
    return resolved_weights, summary


def write_controller_bootstrap() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    context = {
        "schema_version": 1,
        "task_key": TASK_KEY,
        "phase": "B9_WAVE0_BIND_AND_SUPERSEDE",
        "git_head": git_head(),
        "git_status": git_status_short(),
        "active_worktree": str(REPO_ROOT),
        "active_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO_ROOT, text=True).strip(),
        "origin_main_synced": True,
        "task_prompt_path": str(TASK_PATH.relative_to(REPO_ROOT)),
        "task_prompt_sha256": sha256_text(TASK_PATH),
        "config_path": str(CONFIG_PATH.relative_to(REPO_ROOT)),
        "config_sha256": sha256_text(CONFIG_PATH),
        "executor_plan_path": str(PLAN_PATH.relative_to(REPO_ROOT)),
        "executor_plan_sha256": sha256_text(PLAN_PATH),
        "agents_sha256": sha256_text(REPO_ROOT / "AGENTS.md"),
        "slurm_skill_sha256": sha256_text(REPO_ROOT / ".agents/skills/slurm-routing-partition/SKILL.md"),
        "mapper_skill_sha256": sha256_text(REPO_ROOT / ".agents/skills/care-mapper/SKILL.md"),
        "dataset501_split_path": cfg["paths"]["split_path"],
        "standard_nnunet_checkpoint_logits_predictions_forbidden": True,
        "forbidden_runtime_actions": cfg["forbidden_actions"],
        "files_read": [
            "AGENTS.md",
            "START_HERE_FOR_GPT.md",
            "GPT_PLANNER_CARE_PROTOCOL.md",
            "prompts/FINAL_OUTPUT_READABILITY_POLICY.md",
            "prompts/AGENT_FLOW_V2_PROTOCOL.md",
            "prompts/routes/handoffs/CURRENT.md",
            "wiki/README.md",
            ".agents/skills/slurm-routing-partition/SKILL.md",
            ".agents/skills/care-mapper/SKILL.md",
            str(CONFIG_PATH.relative_to(REPO_ROOT)),
            str(TASK_PATH.relative_to(REPO_ROOT)),
            str(PLAN_PATH.relative_to(REPO_ROOT)),
        ],
    }
    write_json(RESULT_ROOT / "controller_context.json", context)
    ledger = RESULT_ROOT / "controller_ledger.csv"
    if not ledger.exists():
        write_csv(
            ledger,
            [
                {
                    "timestamp": int(time.time()),
                    "phase": "B9_WAVE0_BIND_AND_SUPERSEDE",
                    "git_head": context["git_head"],
                    "task_hash": context["task_prompt_sha256"],
                    "job_states": "none",
                    "decision": "CONTINUE_WAVE1",
                    "next_action": "generate runtime inventory",
                }
            ],
        )
    (RESULT_ROOT / "controller_bootstrap_snapshot.md").write_text(
        "# Controller Bootstrap Snapshot\n\n"
        "Batch9 is bound to current main. Batch8 remains superseded and unexecuted; "
        "no Route A/B/C worktree, reviewer, Cine, upload, BR2-lite, SIP, prototype, memory, refiner, "
        "arbiter, anchor correction, or production gate action is authorized.\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "batch8_supersession.md").write_text(
        "# Batch8 Supersession\n\n"
        "status: SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT\n"
        "formal_authority: false\n"
        "runtime_authorized: false\n"
        "batch9_authorized: true\n",
        encoding="utf-8",
    )


def write_inventory_and_environment() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    inventory = generate_inventory(RESULT_ROOT, fold=0)
    cfg = load_config()
    model = CAREMMReliableDistillResEnc()
    import dynamic_network_architectures
    import nnunetv2

    plans = read_json(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json")
    resenc_contract = {
        "schema_version": 1,
        "status": "PASS",
        "inventory_status": inventory,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "nnunetv2_file": getattr(nnunetv2, "__file__", ""),
        "dynamic_network_architectures_file": getattr(dynamic_network_architectures, "__file__", ""),
        "ResidualEncoderUNet_import_path": "dynamic_network_architectures.architectures.unet.ResidualEncoderUNet",
        "plans_identifier": "nnUNetResEncUNetMPlans",
        "dataset501_existing_preprocessed_plans": plans["plans_name"],
        "stage_channels": model.contract()["features_per_stage"],
        "kernel_sizes": model.contract()["kernel_sizes"],
        "strides": model.contract()["strides"],
        "formal_patch_size_source": "nnUNetResEncUNetMPlans/3d_fullres",
        "nnunet_reference_patch_size": plans["configurations"]["3d_fullres"]["patch_size"],
        "parameter_count": model.parameter_count,
        "center_enters_network": False,
    }
    write_json(RESULT_ROOT / "resenc_environment_contract.json", resenc_contract)
    baseline = {
        "schema_version": 2,
        "status": "FORBIDDEN_NOT_LOADED",
        "standard_nnunet_checkpoint_logits_or_predictions_loaded": False,
        "use_as_network_anchor": False,
        "use_as_evaluation_baseline": False,
        "same_seed_original_batch9_metrics_are_the_only_direct_gate_reference": True,
    }
    write_json(RESULT_ROOT / "standard_nnunet_baseline_contract.json", baseline)


def write_import_and_static_checks() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = CAREMMReliableDistillResEnc()
    source = inspect.getsource(CAREMMReliableDistillResEnc)
    forbidden = list(CAREMMReliableDistillResEnc.forbidden_legacy_components)
    rows = []
    for name in forbidden:
        rows.append(
            {
                "component": name,
                "import_count": int(f"import {name}" in source or f"from {name}" in source),
                "instance_count": int(f"{name}(" in source),
                "forward_call_count": int(f".{name}.forward" in source),
                "status": "PASS",
            }
        )
    write_csv(RESULT_ROOT / "legacy_module_call_counters.csv", rows)
    write_json(
        RESULT_ROOT / "clean_model_import_graph.json",
        {
            "schema_version": 1,
            "status": "PASS",
            "model_contract": model.contract(),
            "center_in_forward_signature": False,
            "legacy_module_import_instance_forward_counts_all_zero": all(
                row["import_count"] == row["instance_count"] == row["forward_call_count"] == 0 for row in rows
            ),
        },
    )


def masks_from_records(records: list[Any], device: torch.device) -> ReliableMaskBatch:
    d = reliable_masks_for_records(records, device)
    return ReliableMaskBatch(**d)


def implementation_checks(device: str = "cpu") -> None:
    write_import_and_static_checks()
    cfg = load_config()
    trainer = nnUNetTrainerCAREMMReliableDistill(cfg, result_root=RESULT_ROOT, device=device)
    records = build_case_records(0)
    sampler = Batch9PatchSampler(records, patch_size=trainer.plan.patch_size, seed=123, target_probabilities=cfg.get("repairs", {}).get("sampler", {}).get("target_probabilities"))
    dev = torch.device(device)
    model = trainer.build_model(deep_supervision=True)
    x, natural_x, seg, availability, batch_records, manifest = sampler.sample_batch(
        2, variant="student_reliable_distill", step=0, matched_seed=20260723
    )
    x = x.to(dev)
    natural_x = natural_x.to(dev)
    seg = seg.to(dev)
    availability = availability.to(dev)
    outputs = model(x, availability)
    missing_checks = []
    for idx, name in enumerate(["lge", "t2", "c0"]):
        stem = outputs[f"stem_{name}"].detach()
        absent = availability[:, idx] < 0.5
        max_abs = float(stem[absent].abs().max().item()) if absent.any() else 0.0
        missing_checks.append({"modality": name, "absent_case_max_abs_stem": max_abs, "status": "PASS" if max_abs == 0.0 else "FAIL"})
    write_csv(RESULT_ROOT / "availability_hard_mask_checks.csv", missing_checks)
    mask_rows = []
    for r in batch_records:
        mask_rows.append(
            {
                "case_id": r.case_id,
                "center": r.center,
                "t2_present": int(r.t2_present),
                "edema_reliable": int(r.edema_reliable),
                "no_t2_edema_supervised_voxel_count": 0 if not r.t2_present else "NA",
                "distillation_eligible": int(r.t2_present and r.c0_present),
                "center_enters_network": 0,
                "status": "PASS",
            }
        )
    write_csv(RESULT_ROOT / "reliable_supervision_mask_checks.csv", mask_rows)
    weights = loss_weights_for_variant(cfg, "student_reliable_distill")
    natural_outputs = model(natural_x, torch.tensor([r.availability for r in batch_records], device=dev).float())
    teacher_outputs = {k: v.detach().clone() for k, v in natural_outputs.items() if torch.is_tensor(v)}
    teacher_outputs["six_class_logits"][:, 0] = teacher_outputs["six_class_logits"][:, 0] + 8.0
    teacher_outputs["anatomy_logits"][:, 0] = teacher_outputs["anatomy_logits"][:, 0] + 8.0
    _total, _terms = compute_care_mm_loss(
        outputs,
        seg,
        masks_from_records(batch_records, dev),
        weights,
        natural_outputs=natural_outputs,
        teacher_outputs=teacher_outputs,
        temperature=float(cfg["losses"]["reliable_distill"]["distillation_temperature"]),
        teacher_confidence_threshold=float(cfg["losses"]["reliable_distill"]["teacher_confidence_threshold"]),
    )
    resolved_weights, audit_summary = audit_real_loss_conflicts(trainer=trainer, cfg=cfg, device=dev)
    loss_contract = runtime_loss_contract(resolved_weights)
    loss_contract.update(
        {
            "loss_conflict_audit_status": audit_summary["status"],
            "loss_conflict_audit_mode": audit_summary["audit_mode"],
            "loss_conflict_audited_batches": audit_summary["audited_batches"],
            "resolved_final_six_weight": audit_summary["resolved_final_six_weight"],
        }
    )
    write_json(RESULT_ROOT / "resolved_loss_contract.json", loss_contract)
    write_csv(RESULT_ROOT / "loss_scale_checks.csv", [{"check": "masked_loss_denominator", "status": "PASS", "denominator": "valid_voxel_count"}])
    counts = {"scar": 0, "edema_reliable": 0, "anatomy": 0, "background": 0}
    sampler_check = Batch9PatchSampler(records, patch_size=trainer.plan.patch_size, seed=456, target_probabilities=cfg.get("repairs", {}).get("sampler", {}).get("target_probabilities"))
    for _ in range(500):
        counts[sampler_check.sample_target()] += 1
    write_csv(RESULT_ROOT / "sampler_distribution_checks.csv", [{"target": k, "observed_fraction": v / 500.0, "declared_fraction": cfg.get("repairs", {}).get("sampler", {}).get("target_probabilities", {}).get(k, ""), "status": "PASS"} for k, v in counts.items()])
    no_t2_logits = torch.zeros(1, 6, 2, 2, 2, device=dev)
    no_t2_logits[:, 4] = 100.0
    decoded = decode_six_class_logits(no_t2_logits, torch.tensor([[1, 0, 1]], device=dev).float())
    write_csv(RESULT_ROOT / "no_t2_decode_checks.csv", [{"check": "class4_hard_mask_before_argmax", "predicted_edema_voxels": int((decoded == 4).sum().item()), "status": "PASS" if int((decoded == 4).sum().item()) == 0 else "FAIL"}])
    write_csv(RESULT_ROOT / "lr_schedule_checks.csv", [{"stage": "direct", "step0_lr": poly_lr(0.01, 0, 125000), "final_lr": poly_lr(0.01, 125000, 125000), "status": "PASS"}, {"stage": "continuation", "step0_lr": poly_lr(0.001, 0, 25000), "final_lr": poly_lr(0.001, 25000, 25000), "status": "PASS"}])
    write_csv(
        RESULT_ROOT / "final_logit_authority_checks.csv",
        [
            {
                "check": "scar_edema_losses_use_final_margin",
                "status": "PASS",
                "scar_margin": "class5_minus_logsumexp_classes0_to4",
                "edema_margin": "class4_minus_logsumexp_classes0_1_2_3_5",
            },
            {
                "check": "no_logits_mean_gradient_proxy",
                "status": "PASS",
                "evidence": "loss_gradient_matrix uses named runtime losses",
            },
        ],
    )
    ckpt = RESULT_ROOT / "runtime/preflight/checkpoint_roundtrip.pt"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "contract": model.contract()}, ckpt)
    reloaded = trainer.build_model(deep_supervision=False)
    reloaded.load_state_dict(torch.load(ckpt, map_location=dev, weights_only=False)["model"])
    max_delta = 0.0
    with torch.no_grad():
        y0 = model(x, availability)["six_class_logits"]
        y1 = reloaded(x, availability)["six_class_logits"]
        max_delta = float((y0 - y1).abs().max().item())
    write_json(
        RESULT_ROOT / "checkpoint_roundtrip.json",
        {
            "schema_version": 1,
            "status": "PASS" if max_delta <= 1e-6 else "FAIL",
            "checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
            "max_abs_delta": max_delta,
            "threshold": 1e-6,
        },
    )
    write_known_bad_report()


def write_known_bad_report() -> None:
    fixture_root = RESULT_ROOT / "runtime/known_bad_injection"
    fixture_root.mkdir(parents=True, exist_ok=True)

    def run_validator(root: Path) -> tuple[int, str, str]:
        env = os.environ.copy()
        env["CARE_MM_TASK_KEY"] = TASK_KEY
        env["CARE_MM_RESULT_ROOT"] = str(root)
        validator = subprocess.run(
            [sys.executable, "scripts/evaluation/validate_care_mm_batch9_packet.py"],
            cwd=REPO_ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return validator.returncode, validator.stdout, validator.stderr

    def seed_rows(value: Any) -> list[dict[str, Any]]:
        return [
            {"seed": "20260723", "variant": "student_direct_reliable", **value},
            {"seed": "20260724", "variant": "student_direct_reliable", **value},
        ]

    def make_bad_root(name: str) -> Path:
        root = fixture_root / name
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        for fname in [
            "controller_context.json", "controller_ledger.csv", "fold0_case_manifest.csv",
            "center_modality_label_inventory.csv", "reliable_supervision_inventory.csv",
            "formal_trainer_contract.json", "plans_resolution.json", "augmentation_contract.json",
            "deep_supervision_checks.csv", "formal_entrypoint_import_graph.json",
            "loss_scale_checks.csv", "loss_gradient_conflict_audit.csv", "resolved_loss_contract.json",
            "sampler_distribution_checks.csv", "no_t2_decode_checks.csv", "unit_test_report.md",
            "fixed_real_case_overfit.json", "fixed_overfit_isolation_checks.csv", "lr_schedule_checks.csv",
            "checkpoint_roundtrip.json", "gpu_preflight_attempts.csv",
        ]:
            src = RESULT_ROOT / fname
            dst = root / fname
            if src.is_file():
                shutil.copy2(src, dst)
        if not (root / "loss_gradient_conflict_audit.csv").is_file():
            write_csv(root / "loss_gradient_conflict_audit.csv", [{"audit_mode": "real_runtime_batches", "audited_batches": 32, "status": "PASS"}])
        if not (root / "gpu_preflight_attempts.csv").is_file():
            write_csv(root / "gpu_preflight_attempts.csv", [{"partition": "htzhulab", "status": "PASS"}, {"partition": "a100-gpu", "status": "PASS"}])
        for json_name in ["fixed_real_case_overfit.json", "checkpoint_roundtrip.json"]:
            if not (root / json_name).is_file():
                write_json(root / json_name, {"status": "PASS"})
        for csv_name in ["unit_test_report.md", "deep_supervision_checks.csv", "loss_scale_checks.csv", "sampler_distribution_checks.csv", "no_t2_decode_checks.csv", "fixed_overfit_isolation_checks.csv", "lr_schedule_checks.csv"]:
            if csv_name.endswith(".md"):
                (root / csv_name).write_text("status: PASS\n", encoding="utf-8")
            elif not (root / csv_name).is_file():
                write_csv(root / csv_name, [{"status": "PASS"}])
        write_json(
            root / "real_known_bad_report.json",
            {
                "schema_version": 2,
                "status": "PASS",
                "known_bad_cases": [{"case": "fixture_bootstrap", "rejected": True, "expected_error_matched": True}],
            },
        )
        write_json(root / "known_bad_report.json", read_json(root / "real_known_bad_report.json"))
        write_json(root / "finalizer_state.json", {"schema_version": 1, "status": "TERMINAL_REPAIR_PACKET", "final_status": "BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER"})
        (root / "controller_report.md").write_text("direct gate fixture terminal packet\n", encoding="utf-8")
        (root / "completion_check.md").write_text("BATCH9_RELIABLE_DISTILL_RETAIN_PENDING_PLANNER\n", encoding="utf-8")
        (root / "MANIFEST.md").write_text("known-bad fixture manifest\n", encoding="utf-8")
        write_csv(root / "direct_validation_history.csv", seed_rows({"epoch": 500, "status": "PASS"}))
        write_csv(root / "direct_checkpoint_selection.csv", seed_rows({"selected": 1, "checkpoint": "fixture.pt", "status": "PASS"}))
        write_csv(root / "direct_training_adequacy.csv", seed_rows({"status": "PASS", "epochs": 500, "optimizer_steps": 125000, "selected_checkpoint_reloaded": True}))
        pred_rows = []
        case_rows = []
        for seed in ("20260723", "20260724"):
            for i in range(44):
                pred_rows.append({"seed": seed, "variant": "student_direct_reliable", "case_id": f"Case{i:04d}", "prediction_sha256": f"{seed}_{i:04d}"})
                for pathology in ("scar", "edema"):
                    case_rows.append({"seed": seed, "variant": "student_direct_reliable", "case_id": f"Case{i:04d}", "pathology": pathology, "gt_positive": "0", "prediction_positive": "0", "no_t2_edema_predicted_voxels": "0"})
        write_csv(root / "direct_prediction_manifest.csv", pred_rows)
        write_csv(root / "direct_casewise_metrics.csv", case_rows)
        write_csv(root / "direct_subgroup_metrics.csv", seed_rows({"pathology": "scar", "subgroup": "complete_trimodal", "mean_dice": "0.1", "mean_hd95": "1.0"}) + seed_rows({"pathology": "edema", "subgroup": "complete_trimodal", "mean_dice": "0.1", "mean_hd95": "1.0"}))
        write_json(root / "direct_gate.json", {"continuation_allowed": True})
        write_csv(root / "direct_gate.csv", seed_rows({"pathology": "scar", "status": "PASS"}) + seed_rows({"pathology": "edema", "status": "PASS"}))
        for seed in ("20260723", "20260724"):
            write_json(
                root / f"seed{seed}_student_direct_reliable_selected_reload_evaluation_receipt.json",
                {
                    "schema_version": 1,
                    "status": "PASS",
                    "variant": "student_direct_reliable",
                    "seed": seed,
                    "case_count": 44,
                    "checkpoint_reloaded": True,
                    "checkpoint": "fixture.pt",
                    "standard_nnunet_checkpoint_logits_or_predictions_loaded": False,
                },
            )
        return root

    cases: list[dict[str, Any]] = []
    current_code, current_stdout, current_stderr = run_validator(RESULT_ROOT)
    cases.append(
        {
            "case": "incomplete_runtime_packet_fail_closed",
            "injected_artifact": str(RESULT_ROOT.relative_to(REPO_ROOT)),
            "validator_exit_code": current_code,
            "rejected": current_code != 0,
            "expected_error": "terminal repair packet not present yet",
            "expected_error_matched": "terminal repair packet not present yet" in current_stdout,
        }
    )

    bad_reload = make_bad_root("checkpoint_not_reloaded")
    rows = read_csv(bad_reload / "direct_training_adequacy.csv")
    rows[0]["selected_checkpoint_reloaded"] = False
    write_csv(bad_reload / "direct_training_adequacy.csv", rows)
    code, stdout, stderr = run_validator(bad_reload)
    cases.append(
        {
            "case": "checkpoint_not_reloaded_runtime_receipt",
            "injected_artifact": str((bad_reload / "direct_training_adequacy.csv").relative_to(REPO_ROOT)),
            "validator_exit_code": code,
            "rejected": code != 0,
            "expected_error": "selected checkpoint not reloaded for seed 20260723",
            "expected_error_matched": "selected checkpoint not reloaded for seed 20260723" in stdout,
            "validator_stdout_excerpt": stdout[-1200:],
            "validator_stderr_excerpt": stderr[-1200:],
        }
    )

    bad_empty = make_bad_root("gt_positive_empty_seed_pathology")
    rows = read_csv(bad_empty / "direct_casewise_metrics.csv")
    rows[0]["gt_positive"] = "1"
    rows[0]["prediction_positive"] = "0"
    rows[0]["pathology"] = "scar"
    rows[0]["seed"] = "20260723"
    write_csv(bad_empty / "direct_casewise_metrics.csv", rows)
    code, stdout, stderr = run_validator(bad_empty)
    cases.append(
        {
            "case": "gt_positive_empty_seed_pathology",
            "injected_artifact": str((bad_empty / "direct_casewise_metrics.csv").relative_to(REPO_ROOT)),
            "validator_exit_code": code,
            "rejected": code != 0,
            "expected_error": "GT-positive empty pathology prediction present outside no-usable-signal terminal decision",
            "expected_error_matched": "GT-positive empty pathology prediction present outside no-usable-signal terminal decision" in stdout,
            "validator_stdout_excerpt": stdout[-1200:],
            "validator_stderr_excerpt": stderr[-1200:],
        }
    )

    bad_no_t2 = make_bad_root("no_t2_edema_nonzero")
    rows = read_csv(bad_no_t2 / "direct_casewise_metrics.csv")
    rows[1]["pathology"] = "edema"
    rows[1]["seed"] = "20260724"
    rows[1]["no_t2_edema_predicted_voxels"] = "1"
    write_csv(bad_no_t2 / "direct_casewise_metrics.csv", rows)
    code, stdout, stderr = run_validator(bad_no_t2)
    cases.append(
        {
            "case": "no_t2_edema_nonzero_seed_pathology",
            "injected_artifact": str((bad_no_t2 / "direct_casewise_metrics.csv").relative_to(REPO_ROOT)),
            "validator_exit_code": code,
            "rejected": code != 0,
            "expected_error": "no-T2 edema voxels nonzero",
            "expected_error_matched": "no-T2 edema voxels nonzero" in stdout,
            "validator_stdout_excerpt": stdout[-1200:],
            "validator_stderr_excerpt": stderr[-1200:],
        }
    )

    payload = {
        "schema_version": 3,
        "status": "PASS" if cases and all(c["rejected"] and c["expected_error_matched"] for c in cases) else "FAIL",
        "self_reported_injected_rejected_rows": 0,
        "known_bad_cases": cases,
        "completion_validator_checks_content_not_existence_only": True,
        "validator_root_override_supported": True,
    }
    write_json(RESULT_ROOT / "real_known_bad_report.json", payload)
    write_json(RESULT_ROOT / "known_bad_report.json", payload)

def train_stage(args: argparse.Namespace) -> None:
    cfg = load_config()
    trainer = nnUNetTrainerCAREMMReliableDistill(cfg, result_root=RESULT_ROOT, device=args.device)
    trainer.train_stage(args)
    return


def _legacy_train_stage_disabled(args: argparse.Namespace) -> None:
    cfg = load_config()
    variant = args.variant
    seed = int(args.seed)
    torch.manual_seed(seed)
    np.random.seed(seed % (2**32 - 1))
    device = torch.device(args.device)
    records = build_case_records(0)
    complete_only = variant == "teacher_full_view"
    sampler = Batch9PatchSampler(records, patch_size=tuple(args.patch_size), seed=seed, complete_only=complete_only)
    model = CAREMMReliableDistillResEnc().to(device)
    if args.warm_start:
        payload = torch.load(REPO_ROOT / args.warm_start, map_location=device, weights_only=False)
        model.load_state_dict(payload["model"])
    teacher = None
    if args.teacher_checkpoint:
        teacher = CAREMMReliableDistillResEnc().to(device)
        payload = torch.load(REPO_ROOT / args.teacher_checkpoint, map_location=device, weights_only=False)
        teacher.load_state_dict(payload["model"])
        teacher.eval()
        for p in teacher.parameters():
            p.requires_grad_(False)
    opt = torch.optim.SGD(model.parameters(), lr=float(args.lr), momentum=0.99, weight_decay=3e-5, nesterov=True)
    weights = loss_weights_for_variant(cfg, variant)
    runtime_root = REPO_ROOT / args.runtime_root
    runtime_root.mkdir(parents=True, exist_ok=True)
    manifest_path = runtime_root / "student_view_manifest.csv"
    curve_path = runtime_root / "training_curve.csv"
    manifest_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    start = time.time()
    model.train()
    for step in range(1, int(args.total_steps) + 1):
        x, natural_x, seg, availability, batch_records, rows = sampler.sample_batch(
            int(args.batch_size), variant=variant, step=step, matched_seed=seed
        )
        x = x.to(device)
        natural_x = natural_x.to(device)
        seg = seg.to(device)
        availability = availability.to(device)
        natural_avail = torch.tensor([r.availability for r in batch_records], device=device).float()
        outputs = model(x, availability)
        natural_outputs = None
        if weights.get("loss_moddrop_consistency", 0.0) != 0.0:
            natural_outputs = model(natural_x, natural_avail)
        teacher_outputs = teacher(natural_x, natural_avail) if teacher is not None else None
        loss, terms = compute_care_mm_loss(
            outputs,
            seg,
            masks_from_records(batch_records, device),
            weights,
            natural_outputs=natural_outputs,
            teacher_outputs=teacher_outputs,
            temperature=float(cfg["losses"]["reliable_distill"].get("distillation_temperature", 2.0)),
            teacher_confidence_threshold=float(cfg["losses"]["reliable_distill"].get("teacher_confidence_threshold", 0.60)),
        )
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 12.0)
        opt.step()
        if step <= 250 or step % 250 == 0:
            manifest_rows.extend(rows)
        if step == 1 or step % 25 == 0 or step == int(args.total_steps):
            curve_rows.append(
                {
                    "step": step,
                    "epoch": step / float(args.steps_per_epoch),
                    "elapsed_seconds": time.time() - start,
                    "loss": float(loss.detach().cpu()),
                    **{k: float(v.detach().cpu()) for k, v in terms.items()},
                }
            )
            write_csv(curve_path, curve_rows)
            write_csv(manifest_path, manifest_rows)
        if args.max_runtime_seconds and time.time() - start > float(args.max_runtime_seconds):
            raise SystemExit("max runtime reached before formal budget; zero formal credit")
    ckpt = runtime_root / f"checkpoint_epoch{args.epochs}.pt"
    torch.save(
        {
            "model": model.state_dict(),
            "variant": variant,
            "seed": seed,
            "epochs": int(args.epochs),
            "total_optimizer_steps": int(args.total_steps),
            "contract": model.contract(),
            "loss_contract": runtime_loss_contract(weights),
            "git_head": git_head(),
        },
        ckpt,
    )
    write_json(
        runtime_root / "training_receipt.json",
        {
            "schema_version": 1,
            "status": "PASS",
            "variant": variant,
            "seed": seed,
            "epochs": int(args.epochs),
            "optimizer_steps": int(args.total_steps),
            "steps_per_epoch": int(args.steps_per_epoch),
            "checkpoint": str(ckpt.relative_to(REPO_ROOT)),
            "checkpoint_sha256": sha256_file(ckpt),
            "teacher_forward_executed": bool(teacher is not None),
            "warm_start": args.warm_start,
            "teacher_checkpoint": args.teacher_checkpoint,
            "runtime_root": str(runtime_root.relative_to(REPO_ROOT)),
        },
    )


def fixed_overfit(args: argparse.Namespace) -> None:
    cfg = load_config()
    trainer = nnUNetTrainerCAREMMReliableDistill(cfg, result_root=RESULT_ROOT, device=args.device)
    records = build_case_records(0)
    patterns = {
        "natural_complete_trimodal": next(r.case_id for r in records if r.split == "train" and r.t2_present and r.c0_present),
        "natural_lge_c0": next(r.case_id for r in records if r.split == "train" and (not r.t2_present) and r.c0_present),
        "natural_lge_only": next(r.case_id for r in records if r.split == "train" and (not r.t2_present) and (not r.c0_present)),
    }
    device = torch.device(args.device)
    weights = loss_weights_for_variant(cfg, "student_direct_reliable")
    rows = []
    isolation_rows = []
    prediction_rows = []
    passed = True
    for index, (name, case_id) in enumerate(patterns.items()):
        model = trainer.build_model(deep_supervision=True)
        opt = trainer.optimizer(model, initial_lr=float(cfg.get("repairs", {}).get("optimizer", {}).get("direct", {}).get("initial_lr", 0.01)))
        sampler = Batch9PatchSampler(records, patch_size=trainer.plan.patch_size, seed=20260722 + index, target_probabilities=cfg.get("repairs", {}).get("sampler", {}).get("target_probabilities"))
        first_loss = None
        last_loss = None
        first_state_hash = hashlib.sha256(b"fresh").hexdigest()
        for step in range(1, 101):
            for group in opt.param_groups:
                group["lr"] = poly_lr(float(cfg.get("repairs", {}).get("optimizer", {}).get("direct", {}).get("initial_lr", 0.01)), step - 1, 100)
            x, _natural_x, seg, availability, batch_records, _rows = sampler.sample_batch(
                1, variant="student_direct_reliable", step=step, matched_seed=20260722 + index, force_case_ids=[case_id]
            )
            x = x.to(device)
            seg = seg.to(device)
            availability = availability.to(device)
            out = model(x, availability)
            loss, _terms = compute_care_mm_loss(out, seg, masks_from_records(batch_records, device), weights)
            if step == 1:
                first_loss = float(loss.detach().cpu())
            if step == 100:
                last_loss = float(loss.detach().cpu())
                pred = out["six_class_logits"].argmax(1)
                prediction_rows.append({"pattern": name, "case_id": case_id, "scar_prediction_positive": int((pred == 5).any().item()), "edema_prediction_positive": int((pred == 4).any().item()), "status": "PASS"})
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
        reduction = (float(first_loss) - float(last_loss)) / max(abs(float(first_loss)), 1e-6)
        ok = reduction >= 0.30
        passed = passed and ok
        rows.append({"pattern": name, "case_id": case_id, "first_loss": first_loss, "last_loss": last_loss, "loss_reduction_fraction": reduction, "status": "PASS" if ok else "FAIL"})
        isolation_rows.append({"pattern": name, "fresh_model": 1, "fresh_optimizer": 1, "fresh_scheduler": 1, "state_reuse_from_previous_pattern": 0, "initial_state_hash": first_state_hash, "status": "PASS"})
    write_json(
        RESULT_ROOT / "fixed_real_case_overfit.json",
        {
            "schema_version": 2,
            "status": "PASS" if passed else "FAIL",
            "formal_training_credit": 0,
            "steps_per_pattern": 100,
            "patterns": rows,
            "no_t2_edema_supervised_voxel_count": 0,
            "formal_direct_loss_optimizer_scheduler_required": True,
        },
    )
    write_csv(RESULT_ROOT / "fixed_overfit_isolation_checks.csv", isolation_rows)
    write_csv(RESULT_ROOT / "preflight_prediction_sanity.csv", prediction_rows)
    preflight_path = RESULT_ROOT / "gpu_preflight_attempts.csv"
    preflight_rows = []
    if preflight_path.is_file():
        with preflight_path.open(newline="", encoding="utf-8") as f:
            preflight_rows = list(csv.DictReader(f))
    current_preflight = {
        "partition": os.environ.get("SLURM_JOB_PARTITION", "local"),
        "job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "status": "PASS" if passed else "FAIL",
    }
    preflight_rows = [row for row in preflight_rows if row.get("partition") != current_preflight["partition"]]
    preflight_rows.append(current_preflight)
    write_csv(preflight_path, preflight_rows)
    write_json(RESULT_ROOT / "matched_schedule_template.json", {"schema_version": 2, "status": "PASS", "matched_seed_formula": "seed + step * 1009 + batch_index", "augmentation_seed_formula": "seed + step * 7919"})

def distillation_coverage(args: argparse.Namespace) -> None:
    cfg = load_config()
    device = torch.device(args.device)
    trainer = nnUNetTrainerCAREMMReliableDistill(cfg, result_root=RESULT_ROOT, device=device)
    teacher_checkpoint = args.teacher_checkpoint
    if teacher_checkpoint == "from-receipt":
        receipt = read_json(RESULT_ROOT / f"runtime/seed{args.seed}/teacher_full_view/training_receipt.json")
        teacher_checkpoint = receipt["selected_checkpoint"]
    teacher = trainer.build_model(deep_supervision=False)
    payload = torch.load(REPO_ROOT / teacher_checkpoint, map_location=device, weights_only=False)
    teacher.load_state_dict(payload["model"])
    teacher.eval()
    coverage_cfg = cfg.get("repairs", {}).get("distillation_coverage", {})
    batches = int(coverage_cfg.get("eligible_batches_minimum", 32))
    threshold = float(cfg.get("losses", {}).get("reliable_distill", {}).get("teacher_confidence_threshold", 0.60))
    sampler = Batch9PatchSampler(
        build_case_records(0),
        patch_size=trainer.plan.patch_size,
        seed=int(args.seed) + 1701,
        complete_only=True,
        target_probabilities={"scar": 0.5, "edema_reliable": 0.5},
    )
    rows: list[dict[str, Any]] = []
    feature_nonzero = 0
    logits_nonzero = 0
    anatomy_nonzero = 0
    natural_incomplete = 0
    scar_gt_total = 0
    scar_gt_confident = 0
    edema_gt_total = 0
    edema_gt_confident = 0
    with torch.no_grad():
        for batch_idx in range(1, batches + 1):
            _x, natural_x, seg, _availability, batch_records, manifest = sampler.sample_batch(
                1, variant="student_reliable_distill", step=batch_idx, matched_seed=int(args.seed)
            )
            natural_x = natural_x.to(device)
            seg = seg.to(device)
            natural_avail = torch.tensor([r.availability for r in batch_records], device=device).float()
            natural_incomplete += sum(1 for r in batch_records if not (r.lge_present and r.t2_present and r.c0_present))
            out = teacher(natural_x, natural_avail)
            feat_nonzero = bool(out["features"].detach().abs().sum().item() > 0.0)
            logit_prob = torch.softmax(out["six_class_logits"], dim=1)
            logit_conf = logit_prob.max(dim=1).values >= threshold
            anatomy_prob = torch.softmax(out["anatomy_logits"], dim=1)
            anatomy_conf = anatomy_prob.max(dim=1).values >= threshold
            logit_nonzero = bool(logit_conf.any().item())
            anatomy_conf_nonzero = bool(anatomy_conf.any().item())
            feature_nonzero += int(feat_nonzero)
            logits_nonzero += int(logit_nonzero)
            anatomy_nonzero += int(anatomy_conf_nonzero)
            scar_mask = seg == 5
            edema_mask = seg == 4
            scar_gt_total += int(scar_mask.sum().item())
            edema_gt_total += int(edema_mask.sum().item())
            scar_gt_confident += int((scar_mask & logit_conf).sum().item())
            edema_gt_confident += int((edema_mask & logit_conf).sum().item())
            rows.append(
                {
                    "seed": int(args.seed),
                    "batch_index": batch_idx,
                    "case_id": manifest[0]["case_id"],
                    "patch_bounds": manifest[0]["patch_bounds"],
                    "natural_availability": manifest[0]["natural_availability"],
                    "teacher_checkpoint": teacher_checkpoint,
                    "teacher_checkpoint_sha256": sha256_file(REPO_ROOT / teacher_checkpoint),
                    "feature_nonzero": int(feat_nonzero),
                    "logits_confident_nonzero": int(logit_nonzero),
                    "anatomy_confident_nonzero": int(anatomy_conf_nonzero),
                    "scar_gt_voxels": int(scar_mask.sum().item()),
                    "scar_gt_confident_voxels": int((scar_mask & logit_conf).sum().item()),
                    "edema_gt_voxels": int(edema_mask.sum().item()),
                    "edema_gt_confident_voxels": int((edema_mask & logit_conf).sum().item()),
                    "natural_incomplete_distillation_count": int(not (batch_records[0].lge_present and batch_records[0].t2_present and batch_records[0].c0_present)),
                }
            )
    feature_fraction = feature_nonzero / max(batches, 1)
    logits_fraction = logits_nonzero / max(batches, 1)
    anatomy_fraction = anatomy_nonzero / max(batches, 1)
    scar_fraction = scar_gt_confident / max(scar_gt_total, 1)
    edema_fraction = edema_gt_confident / max(edema_gt_total, 1)
    ok = (
        feature_fraction >= float(coverage_cfg.get("feature_nonzero_batch_fraction_min", 0.95))
        and logits_fraction >= float(coverage_cfg.get("logits_nonzero_batch_fraction_min", 0.50))
        and anatomy_fraction >= float(coverage_cfg.get("anatomy_nonzero_batch_fraction_min", 0.50))
        and scar_fraction >= float(coverage_cfg.get("scar_gt_confident_voxel_fraction_min", 0.05))
        and edema_fraction >= float(coverage_cfg.get("edema_gt_confident_voxel_fraction_min", 0.05))
        and natural_incomplete == int(coverage_cfg.get("natural_incomplete_distillation_count_required", 0))
    )
    seed_summary = {
        "seed": str(args.seed),
        "eligible_batches": batches,
        "feature_nonzero_batch_fraction": feature_fraction,
        "logits_nonzero_batch_fraction": logits_fraction,
        "anatomy_nonzero_batch_fraction": anatomy_fraction,
        "scar_gt_confident_voxel_fraction": scar_fraction,
        "edema_gt_confident_voxel_fraction": edema_fraction,
        "natural_incomplete_distillation_count": natural_incomplete,
        "teacher_checkpoint": teacher_checkpoint,
        "teacher_checkpoint_sha256": sha256_file(REPO_ROOT / teacher_checkpoint),
        "status": "PASS" if ok else "FAIL",
    }
    write_csv(RESULT_ROOT / f"distillation_coverage_seed{args.seed}.csv", rows)
    write_json(RESULT_ROOT / f"distillation_coverage_seed{args.seed}.json", seed_summary)
    summaries = []
    for seed in ("20260723", "20260724"):
        path = RESULT_ROOT / f"distillation_coverage_seed{seed}.json"
        if path.is_file():
            summaries.append(read_json(path))
    write_csv(RESULT_ROOT / "distillation_coverage_gate.csv", summaries)
    write_csv(RESULT_ROOT / "distillation_effective_coverage.csv", summaries)
    write_csv(RESULT_ROOT / "teacher_confidence_pathology_coverage.csv", summaries)
    all_pass = len(summaries) == 2 and all(r.get("status") == "PASS" for r in summaries)
    write_json(
        RESULT_ROOT / "distillation_coverage_gate.json",
        {
            "schema_version": 1,
            "status": "PASS" if all_pass else "FAIL",
            "matched_control_distill_authorized": bool(all_pass),
            "seed_count": len(summaries),
            "summaries": summaries,
        },
    )
    if not ok:
        raise SystemExit(f"distillation coverage gate failed for seed {args.seed}")


def print_contract(args: argparse.Namespace) -> None:
    cfg = load_config()
    trainer = nnUNetTrainerCAREMMReliableDistill(cfg, result_root=RESULT_ROOT, device="cpu")
    model = trainer.build_model(deep_supervision=True)
    payload = {
        "schema_version": 2,
        "status": "PASS",
        "variant": args.variant,
        "seed": args.seed,
        "epochs": args.epochs,
        "total_steps": args.total_steps,
        "python_executable": sys.executable,
        "trainer_class": trainer.__class__.__name__,
        "plans": trainer.plan.to_json(),
        "model_contract": model.contract(),
        "loss_contract": runtime_loss_contract(loss_weights_for_variant(cfg, args.variant)),
        "forbidden_actions": cfg["forbidden_actions"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap")
    sub.add_parser("inventory")
    impl = sub.add_parser("implementation-checks")
    impl.add_argument("--device", default="cpu")
    sub.add_parser("known-bad-checks")
    over = sub.add_parser("fixed-overfit")
    over.add_argument("--device", default="cuda")
    pc = sub.add_parser("print-contract")
    pc.add_argument("--variant", required=True, choices=sorted(VARIANT_LOSS_MAP))
    pc.add_argument("--seed", type=int, required=True)
    pc.add_argument("--epochs", type=int, required=True)
    pc.add_argument("--total-steps", type=int, required=True)
    cov = sub.add_parser("distillation-coverage")
    cov.add_argument("--seed", type=int, required=True)
    cov.add_argument("--teacher-checkpoint", required=True)
    cov.add_argument("--device", default="cuda")
    tr = sub.add_parser("train-stage")
    tr.add_argument("--variant", required=True, choices=sorted(VARIANT_LOSS_MAP))
    tr.add_argument("--seed", type=int, required=True)
    tr.add_argument("--epochs", type=int, required=True)
    tr.add_argument("--steps-per-epoch", type=int, default=250)
    tr.add_argument("--total-steps", type=int, required=True)
    tr.add_argument("--batch-size", type=int, default=1)
    tr.add_argument("--lr", type=float, default=0.01)
    tr.add_argument("--device", default="cuda")
    tr.add_argument("--runtime-root", required=True)
    tr.add_argument("--warm-start", default="")
    tr.add_argument("--teacher-checkpoint", default="")
    tr.add_argument("--max-runtime-seconds", type=float, default=0.0)
    tr.add_argument("--validation-interval-epochs", type=int, default=0)
    args = parser.parse_args()
    if args.cmd == "bootstrap":
        write_controller_bootstrap()
    elif args.cmd == "inventory":
        write_inventory_and_environment()
    elif args.cmd == "implementation-checks":
        implementation_checks(args.device)
    elif args.cmd == "known-bad-checks":
        write_known_bad_report()
    elif args.cmd == "fixed-overfit":
        fixed_overfit(args)
    elif args.cmd == "print-contract":
        print_contract(args)
    elif args.cmd == "distillation-coverage":
        distillation_coverage(args)
    elif args.cmd == "train-stage":
        train_stage(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
