#!/usr/bin/env python
"""CARE-ASE R2 G2 real-GPU implementation fidelity gate."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import random
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluation.care_ase.evaluate_care_ase_r2_outer import sliding_window_logits
from scripts.training.care_ase.run_care_ase_r2_chunk import (
    PREPROCESSED,
    SPLITS,
    _sampler_state_from_checkpoint_payload,
    combined_source_hash,
    make_batch,
    parse_patch_size,
    read_b2nd,
)
from src.care_myocardium.training.care_ase_augmentation import build_stock_augmentation_contract, build_stock_training_transform_preserve_ignore
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.models.care_ase import build_care_ase_for_fold_with_area_references
from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler, compute_actual_train_area_references
from src.care_myocardium.training.care_ase_trainer import (
    CAREASEStageScheduler,
    build_optimizer,
    care_ase_loss,
    checkpoint_receipt,
    load_care_ase_checkpoint,
    run_formal_optimizer_step,
    save_care_ase_checkpoint,
    write_json,
)


RESULT_ROOT = REPO_ROOT / "results/20260803_care_ase_r2_pretraining_fidelity_repair_v6"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def require_gpu() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError("G2 requires a real CUDA GPU")
    return torch.device("cuda")


def find_descriptor(sampler: CAREASEDeterministicSampler, predicate: Any, *, max_steps: int = 12000) -> Any:
    probe = CAREASEDeterministicSampler(sampler.repo_root, sampler.fold, seed=sampler.seed)
    for step in range(max_steps):
        bundle = probe.descriptor_bundle_for_step(step)
        for desc in bundle.micro_descriptors:
            if predicate(desc):
                return desc
    raise RuntimeError("required descriptor not found")


def grad_max(model: torch.nn.Module, prefix: str) -> float:
    values = [
        float(param.grad.detach().abs().max().cpu())
        for name, param in model.named_parameters()
        if name.startswith(prefix) and param.grad is not None
    ]
    return max(values, default=0.0)


def grad_max_exact_prefixes(model: torch.nn.Module, prefixes: list[str]) -> dict[str, float]:
    return {prefix: grad_max(model, prefix) for prefix in prefixes}


def named_projection_prefixes(model: torch.nn.Module) -> dict[str, str]:
    registry = model.named_evidence_projection_registry()
    group_to_prefix = {
        "scar_half": "scar_branch.half_projections.projections",
        "scar_full": "scar_branch.full_projections.projections",
        "edema_half": "edema_branch.half_projections.projections",
        "edema_full": "edema_branch.full_projections.projections",
    }
    out: dict[str, str] = {}
    for group, payload in registry["groups"].items():
        for name in payload["sources"]:
            out[name] = f"{group_to_prefix[group]}.{name}."
    return out


def named_producer_prefixes() -> dict[str, list[str]]:
    mapping = {
        "scar_quarter_occupancy": ["component_heads.scar_quarter_occupancy."],
        "scar_quarter_center": ["component_heads.scar_quarter_center."],
        "scar_half_occupancy": ["component_heads.scar_half_occupancy."],
        "scar_half_center": ["component_heads.scar_half_center."],
        "scar_context": ["component_heads.scar_context."],
        "scar_lge": ["scar_lge_half_adapter.", "scar_lge_full_adapter."],
        "scar_c0": ["scar_c0_gate.", "scar_c0_half_adapter.", "scar_c0_full_adapter."],
        "edema_context": ["component_heads.edema_context."],
        "edema_injury": ["component_heads.edema_injury."],
        "edema_boundary": ["component_heads.edema_boundary."],
        "edema_dilation1": ["edema_dilation_context.dilated.1."],
        "edema_dilation2": ["edema_dilation_context.dilated.2."],
        "edema_dilation4": ["edema_dilation_context.dilated.4."],
        "edema_t2": ["edema_t2_half_adapter.", "edema_t2_full_adapter."],
        "edema_c0": ["edema_c0_gate.", "edema_c0_half_adapter.", "edema_c0_full_adapter."],
        "edema_lge": ["edema_lge_gate.", "edema_lge_half_adapter.", "edema_lge_full_adapter."],
        "anatomy_context_detached": ["anatomy_geometry_heads.", "anatomy_top_stages.", "anatomy_top_seg_layers."],
    }
    return mapping


def _producer_key_for_projection(name: str) -> str:
    for key in (
        "scar_quarter_occupancy",
        "scar_quarter_center",
        "scar_half_occupancy",
        "scar_half_center",
        "scar_context",
        "scar_lge",
        "scar_c0",
        "edema_context",
        "edema_injury",
        "edema_boundary",
        "edema_dilation1",
        "edema_dilation2",
        "edema_dilation4",
        "edema_t2",
        "edema_c0",
        "edema_lge",
    ):
        if name.startswith(key):
            return key
    return "anatomy_context_detached"


def named_projection_gradient_audit(model: torch.nn.Module, batch: dict[str, torch.Tensor]) -> dict[str, Any]:
    projection_prefixes = named_projection_prefixes(model)
    producer_prefixes = named_producer_prefixes()
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)

    optimizer.zero_grad(set_to_none=True)
    outputs = model(batch["image"], batch["availability"], global_step=2000)
    loss, metrics = care_ase_loss(outputs, batch)
    loss.backward()
    projection_first = {name: grad_max(model, prefix) for name, prefix in projection_prefixes.items()}
    producer_first = {name: max(grad_max(model, prefix) for prefix in prefixes) for name, prefixes in producer_prefixes.items()}
    optimizer.step()

    scheduler.step(2001)
    optimizer.zero_grad(set_to_none=True)
    outputs2 = model(batch["image"], batch["availability"], global_step=2001)
    loss2, metrics2 = care_ase_loss(outputs2, batch)
    loss2.backward()
    projection_second = {name: grad_max(model, prefix) for name, prefix in projection_prefixes.items()}
    producer_second = {name: max(grad_max(model, prefix) for prefix in prefixes) for name, prefixes in producer_prefixes.items()}
    gate_second = grad_max_exact_prefixes(model, ["scar_c0_gate.", "edema_c0_gate.", "edema_lge_gate."])

    rows = {}
    for name in projection_prefixes:
        producer_key = _producer_key_for_projection(name)
        rows[name] = {
            "projection_prefix": projection_prefixes[name],
            "producer_key": producer_key,
            "projection_grad_first_backward": projection_first[name],
            "projection_grad_second_backward": projection_second[name],
            "producer_grad_first_backward": producer_first.get(producer_key, 0.0),
            "producer_grad_second_backward": producer_second.get(producer_key, 0.0),
            "projection_gradient_positive": projection_first[name] > 0.0 or projection_second[name] > 0.0,
        }
    gate_status = {
        "scar_c0_gate_second_backward_positive": gate_second["scar_c0_gate."] > 0.0,
        "edema_c0_gate_second_backward_positive": gate_second["edema_c0_gate."] > 0.0,
        "edema_lge_gate_second_backward_positive": gate_second["edema_lge_gate."] > 0.0,
    }
    return {
        "status": "PASS" if all(row["projection_gradient_positive"] for row in rows.values()) and all(gate_status.values()) else "FAIL",
        "loss_first": float(loss.detach().cpu()),
        "loss_second": float(loss2.detach().cpu()),
        "metrics_first": metrics,
        "metrics_second": metrics2,
        "named_projection_count": len(rows),
        "projection_rows": rows,
        "producer_grad_first_backward": producer_first,
        "producer_grad_second_backward": producer_second,
        "gate_grad_second_backward": gate_second,
        "gate_status": gate_status,
    }


def named_projection_intervention_audit(model: torch.nn.Module, batch: dict[str, torch.Tensor], *, global_step: int) -> dict[str, Any]:
    model.eval()
    projection_names = sorted(named_projection_prefixes(model))
    with torch.no_grad():
        base = model(batch["image"], batch["availability"], global_step=global_step)
        base_logits = base["final_logits"]
        rows = {}
        for name in projection_names:
            off = model(batch["image"], batch["availability"], global_step=global_step, disabled_named_evidence_sources={name})
            diff = (base_logits - off["final_logits"]).abs()
            rows[name] = {
                "final_logit_max_abs_delta": float(diff.max().detach().cpu()),
                "scar_logit_max_abs_delta": float(diff[:, 5:6].max().detach().cpu()),
                "edema_logit_max_abs_delta": float(diff[:, 4:5].max().detach().cpu()),
                "passes_logit_effect": float(diff.max().detach().cpu()) > 1.0e-8,
            }
    return {
        "status": "PASS" if all(row["passes_logit_effect"] for row in rows.values()) else "FAIL",
        "global_step": int(global_step),
        "named_projection_count": len(rows),
        "intervention_rows": rows,
    }


def one_train_step(model: torch.nn.Module, optimizer: torch.optim.Optimizer, scheduler: CAREASEStageScheduler, batch: dict[str, torch.Tensor], step: int) -> dict[str, Any]:
    model.train()
    result = run_formal_optimizer_step(
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        microbatches=[batch],
        global_step=step,
        gradient_accumulation=1,
        autocast_device_type="cuda",
        autocast_enabled=False,
    )
    return {"stage": result["stage"], "loss": float(result["loss_mean"]), "metrics": result["metrics"], "formal_step_api": result["formal_step_api"]}


def scheduler_checks() -> dict[str, Any]:
    checks = {
        "stage_0": CAREASEStageScheduler.stage_for_step(0),
        "stage_1999": CAREASEStageScheduler.stage_for_step(1999),
        "stage_2000": CAREASEStageScheduler.stage_for_step(2000),
        "stage_9999": CAREASEStageScheduler.stage_for_step(9999),
        "stage_10000": CAREASEStageScheduler.stage_for_step(10000),
        "stage_13999": CAREASEStageScheduler.stage_for_step(13999),
        "lr_A0_new_modules": CAREASEStageScheduler.lr_for(group_name="new_modules", global_step=0),
        "lr_A199_new_modules": CAREASEStageScheduler.lr_for(group_name="new_modules", global_step=199),
        "lr_B2000_new_modules": CAREASEStageScheduler.lr_for(group_name="new_modules", global_step=2000),
        "lr_B9999_upper": CAREASEStageScheduler.lr_for(group_name="upper_two_encoder", global_step=9999),
        "lr_C10000_lower": CAREASEStageScheduler.lr_for(group_name="lower_encoder_bottleneck", global_step=10000),
        "lr_C13999_new_modules": CAREASEStageScheduler.lr_for(group_name="new_modules", global_step=13999),
    }
    checks["status"] = "PASS" if checks["stage_0"] == "A" and checks["stage_2000"] == "B" and checks["stage_10000"] == "C" else "FAIL"
    return checks


def sampler_400_checks(repo_root: Path, fold: int) -> dict[str, Any]:
    sampler = CAREASEDeterministicSampler(repo_root, fold)
    receipt = sampler.composition_receipt(400, start_step=0)
    manifest = sampler.hard_negative_manifest
    status = receipt["status"] == "PASS" and manifest.get("manifest_sha256") not in {"MISSING", None} and int(manifest.get("case_count", 0) or len(manifest.get("cases", {}))) > 0
    return {
        "status": "PASS" if status else "FAIL",
        **receipt,
        "manifest_path": manifest.get("manifest_path"),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "manifest_case_count": int(manifest.get("case_count", 0) or len(manifest.get("cases", {}))),
    }


def _state_dict_max_abs_diff(left: dict[str, torch.Tensor], right: dict[str, torch.Tensor]) -> float:
    diffs = []
    for key, value in left.items():
        other = right[key]
        if torch.is_tensor(value) and torch.is_tensor(other) and value.is_floating_point() and value.numel() > 0:
            diffs.append(float((value.detach().cpu() - other.detach().cpu()).abs().max()))
    return max(diffs, default=0.0)


def _optimizer_state_max_abs_diff(left: torch.optim.Optimizer, right: torch.optim.Optimizer) -> float:
    left_state = left.state_dict()["state"]
    right_state = right.state_dict()["state"]
    diffs = []
    if set(left_state) != set(right_state):
        return float("inf")
    for key in left_state:
        for field, value in left_state[key].items():
            other = right_state[key].get(field)
            if torch.is_tensor(value) and torch.is_tensor(other) and value.is_floating_point() and value.numel() > 0:
                diffs.append(float((value.detach().cpu() - other.detach().cpu()).abs().max()))
            elif not torch.is_tensor(value) and value != other:
                return float("inf")
    return max(diffs, default=0.0)


def exact_resume_behavioral_equivalence(
    model: torch.nn.Module,
    batch: dict[str, torch.Tensor],
    *,
    fold: int,
    device: torch.device,
    ckpt_path: Path,
) -> dict[str, Any]:
    torch.manual_seed(31081986)
    torch.cuda.manual_seed_all(31081986)
    model_a = copy.deepcopy(model).to(device)
    model_b = copy.deepcopy(model).to(device)
    opt_a = build_optimizer(model_a)
    opt_b = build_optimizer(model_b)
    sched_a = CAREASEStageScheduler(opt_a)
    sched_b = CAREASEStageScheduler(opt_b)
    sampler_a = CAREASEDeterministicSampler(REPO_ROOT, fold)
    sampler_b = CAREASEDeterministicSampler(REPO_ROOT, fold)

    history_a = []
    history_b = []
    for step in (0, 1):
        sampler_a.descriptor_bundle_for_step(step)
        sampler_b.descriptor_bundle_for_step(step)
        history_a.append(one_train_step(model_a, opt_a, sched_a, batch, step))
        history_b.append(one_train_step(model_b, opt_b, sched_b, batch, step))

    next_bundle_b = sampler_b.peek_descriptor_bundle_for_step(2)
    sampler_state_b = sampler_b.state_dict(next_descriptor=next_bundle_b)
    save_care_ase_checkpoint(
        ckpt_path,
        model=model_b,
        optimizer=opt_b,
        scheduler=sched_b,
        global_step=2,
        stage_id="A",
        next_batch_hash=next_bundle_b.sha256(),
        loss_history_tail=history_b,
        sampler_state=sampler_state_b,
        code_hash=combined_source_hash(),
        split_hash=sha256_file(SPLITS),
    )
    reloaded_model, payload = load_care_ase_checkpoint(ckpt_path, map_location=device, restore_rng=True)
    reloaded_model.to(device)
    reloaded_opt = build_optimizer(reloaded_model)
    reloaded_opt.load_state_dict(payload["optimizer"])
    reloaded_sched = CAREASEStageScheduler(reloaded_opt)
    reloaded_sched.load_state_dict(payload["scheduler"])
    reloaded_sampler = CAREASEDeterministicSampler(REPO_ROOT, fold)
    reloaded_sampler.load_state_dict(_sampler_state_from_checkpoint_payload(payload))
    pre_step2_next_hash = reloaded_sampler.peek_descriptor_bundle_for_step(2).sha256()

    sampler_a.descriptor_bundle_for_step(2)
    reloaded_sampler.descriptor_bundle_for_step(2)
    history_a.append(one_train_step(model_a, opt_a, sched_a, batch, 2))
    history_b.append(one_train_step(reloaded_model, reloaded_opt, reloaded_sched, batch, 2))

    model_a.eval()
    reloaded_model.eval()
    with torch.no_grad():
        logits_a = model_a(batch["image"], batch["availability"], global_step=3)["final_logits"]
        logits_b = reloaded_model(batch["image"], batch["availability"], global_step=3)["final_logits"]
    next_a = sampler_a.peek_descriptor_bundle_for_step(3).sha256()
    next_b = reloaded_sampler.peek_descriptor_bundle_for_step(3).sha256()
    tolerances = {
        "loss_step2_abs_diff": 5.0e-6,
        "logits_max_abs_diff": 5.0e-2,
        "model_parameter_max_abs_diff": 5.0e-5,
        "optimizer_moment_max_abs_diff": 1.0e-5,
    }
    checks = {
        "loss_step2_abs_diff": abs(history_a[-1]["loss"] - history_b[-1]["loss"]),
        "logits_max_abs_diff": float((logits_a - logits_b).abs().max().detach().cpu()),
        "model_parameter_max_abs_diff": _state_dict_max_abs_diff(model_a.state_dict(), reloaded_model.state_dict()),
        "optimizer_moment_max_abs_diff": _optimizer_state_max_abs_diff(opt_a, reloaded_opt),
        "scheduler_equal": sched_a.state_dict() == reloaded_sched.state_dict(),
        "sampler_pre_step2_next_hash_equal": pre_step2_next_hash == payload["next_optimizer_step_micro_descriptor_sha256"],
        "sampler_post_step2_next_hash_equal": next_a == next_b,
        "payload_micro_case_rng_state_present": bool(payload.get("micro_case_rng_state_by_group")),
        "payload_micro_patch_rng_state_present": bool(payload.get("micro_patch_rng_state")) and payload.get("micro_patch_rng_state") != "UNSET",
    }
    pass_checks = [
        checks["loss_step2_abs_diff"] <= tolerances["loss_step2_abs_diff"],
        checks["logits_max_abs_diff"] <= tolerances["logits_max_abs_diff"],
        checks["model_parameter_max_abs_diff"] <= tolerances["model_parameter_max_abs_diff"],
        checks["optimizer_moment_max_abs_diff"] <= tolerances["optimizer_moment_max_abs_diff"],
        checks["scheduler_equal"],
        checks["sampler_pre_step2_next_hash_equal"],
        checks["sampler_post_step2_next_hash_equal"],
        checks["payload_micro_case_rng_state_present"],
        checks["payload_micro_patch_rng_state_present"],
    ]
    return {
        "status": "PASS" if all(pass_checks) else "FAIL",
        "path_a": "init->step0->step1->step2",
        "path_b": "init->step0->step1->save->new_model_optimizer_scheduler_sampler->load->step2",
        "checks": checks,
        "tolerance_basis": "predeclared_real_h100_step0_1_reload_step2_behavioral_equivalence_tolerance_with_raw_errors_retained",
        "tolerances": tolerances,
    }


def outer_access_audit(out: Path) -> dict[str, Any]:
    audited_patterns = [
        "outer_eval/fold_*/evaluation_receipt.json",
        "outer_eval/fold_*/consumed_permit_token*.json",
        "outer_eval/fold_*/*outer*receipt*.json",
    ]
    evidence: list[str] = []
    for pattern in audited_patterns:
        evidence.extend(str(path.relative_to(REPO_ROOT)) for path in sorted(out.glob(pattern)) if path.is_file())
    return {
        "status": "PASS" if not evidence else "FAIL",
        "audited_result_root": str(out.relative_to(REPO_ROOT)),
        "audited_patterns": audited_patterns,
        "outer_access_count_before_freeze": len(evidence),
        "outer_access_evidence_before_freeze": evidence,
    }


def module_off_checks(model: torch.nn.Module, batch: dict[str, torch.Tensor], *, global_step: int) -> dict[str, Any]:
    model.eval()
    toggles: dict[str, dict[str, bool]] = {
        "disable_scar_proposal": {"disable_scar_proposal": True},
        "disable_scar_center": {"disable_scar_center": True},
        "disable_scar_context": {"disable_scar_context": True},
        "disable_edema_injury": {"disable_edema_injury": True},
        "disable_edema_boundary": {"disable_edema_boundary": True},
        "disable_edema_context": {"disable_edema_context": True},
        "disable_extent_wall": {"disable_extent_wall": True},
        "disable_all_evidence": {"disable_all_evidence": True},
    }
    with torch.no_grad():
        base = model(batch["image"], batch["availability"], global_step=global_step)
        base_logits = base["final_logits"]
        base_labels = decode_care_ase_r2_logits(base_logits, batch["availability"])
        rows = {}
        for name, kwargs in toggles.items():
            off = model(batch["image"], batch["availability"], global_step=global_step, **kwargs)
            off_logits = off["final_logits"]
            off_labels = decode_care_ase_r2_logits(off_logits, batch["availability"])
            diff = (base_logits - off_logits).abs()
            rows[name] = {
                "final_logit_max_abs_delta": float(diff.max().detach().cpu()),
                "scar_logit_max_abs_delta": float(diff[:, 5:6].max().detach().cpu()),
                "edema_logit_max_abs_delta": float(diff[:, 4:5].max().detach().cpu()),
                "final_label_changed_voxels": int((base_labels != off_labels).sum().detach().cpu()),
                "passes_logit_or_label_effect": float(diff.max().detach().cpu()) > 1.0e-8 or int((base_labels != off_labels).sum().detach().cpu()) > 0,
            }
    return {
        "status": "PASS" if all(row["passes_logit_or_label_effect"] for row in rows.values()) else "FAIL",
        "global_step": int(global_step),
        "probe_case_shape": list(batch["image"].shape),
        "toggles": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=1, choices=(1, 4))
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--sliding-window-patch-size", default="20,256,256")
    parser.add_argument("--output-dir", type=Path, default=RESULT_ROOT)
    parser.add_argument("--seed", type=int, default=20260803)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True, warn_only=True)
    device = require_gpu()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    patch_size = parse_patch_size(args.patch_size)
    sw_patch = parse_patch_size(args.sliding_window_patch_size)
    fold = int(args.fold)
    fold_out = out / f"g2_fold{fold}"
    fold_out.mkdir(parents=True, exist_ok=True)
    plans_path = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"
    augmentation_contract = build_stock_augmentation_contract(plans_path)
    stock_transform = build_stock_training_transform_preserve_ignore(plans_path)
    initial_patch_size = tuple(int(v) for v in augmentation_contract.initial_patch_size)

    area = compute_actual_train_area_references(REPO_ROOT, fold)
    sampler = CAREASEDeterministicSampler(REPO_ROOT, fold)
    descriptors = {
        "complete_centerB": find_descriptor(sampler, lambda d: d.case_group == "complete" and d.center == "CenterB"),
        "complete_centerC": find_descriptor(sampler, lambda d: d.case_group == "complete" and d.center == "CenterC"),
        "lge_only": find_descriptor(sampler, lambda d: d.case_group == "lge_only"),
        "lge_c0": find_descriptor(sampler, lambda d: d.case_group == "lge_c0"),
        "small_scar": find_descriptor(sampler, lambda d: d.pathology_focus == "scar" and d.within_focus == "small_component"),
        "edema_focus_complete": find_descriptor(sampler, lambda d: d.case_group == "complete" and d.pathology_focus == "edema"),
    }

    model = build_care_ase_for_fold_with_area_references(
        fold,
        scar_area_reference=area["scar_reference"],
        edema_area_reference=area["edema_reference"],
        map_location="cpu",
    ).to(device)
    model.train()
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)

    batches = {
        name: make_batch(
            desc,
            descriptor_sha=desc.sha256(),
            micro=0,
            initial_patch_size=initial_patch_size,
            final_patch_size=patch_size,
            stock_transform=stock_transform,
            device=device,
        )
        for name, desc in descriptors.items()
    }
    complete_batch = batches["complete_centerB"]
    no_t2_batch = batches["lge_only"]

    step0 = model.step0_parity_report(complete_batch["image"], complete_batch["availability"])
    optimizer.zero_grad(set_to_none=True)
    outputs_complete = model(complete_batch["image"], complete_batch["availability"], global_step=2000)
    complete_loss, complete_metrics = care_ase_loss(outputs_complete, complete_batch)
    complete_loss.backward()
    complete_grad = {
        "scar_branch": grad_max(model, "scar_branch."),
        "edema_branch": grad_max(model, "edema_branch."),
        "component_heads": grad_max(model, "component_heads."),
    }
    named_gradient = named_projection_gradient_audit(copy.deepcopy(model).to(device), complete_batch)

    optimizer.zero_grad(set_to_none=True)
    outputs_no_t2 = model(no_t2_batch["image"], no_t2_batch["availability"], global_step=2000)
    no_t2_loss, no_t2_metrics = care_ase_loss(outputs_no_t2, no_t2_batch)
    no_t2_loss.backward()
    edema_exclusive_prefixes = (
        "edema_branch.",
        "edema_t2_half_adapter.",
        "edema_t2_full_adapter.",
        "edema_c0_half_adapter.",
        "edema_c0_full_adapter.",
        "edema_lge_half_adapter.",
        "edema_lge_full_adapter.",
        "edema_c0_gate.",
        "edema_lge_gate.",
        "edema_dilation_context.",
    )
    no_t2_edema_grad_by_prefix = {prefix: grad_max(model, prefix) for prefix in edema_exclusive_prefixes}
    no_t2_edema_grad = max(no_t2_edema_grad_by_prefix.values(), default=0.0)

    overfit_model = copy.deepcopy(model).to(device)
    overfit_optimizer = build_optimizer(overfit_model)
    overfit_scheduler = CAREASEStageScheduler(overfit_optimizer)
    overfit_history = [one_train_step(overfit_model, overfit_optimizer, overfit_scheduler, complete_batch, 2000 + idx) for idx in range(4)]
    module_off = module_off_checks(overfit_model, complete_batch, global_step=2004)
    named_intervention = named_projection_intervention_audit(overfit_model, complete_batch, global_step=2004)

    decode_input = torch.zeros(2, 6, 2, 4, 4, device=device)
    decode_input[0, 4] = 10.0
    decode_input[1, 4] = 10.0
    decoded = decode_care_ase_r2_logits(decode_input, torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]], device=device))

    ckpt = fold_out / "g2_atomic_checkpoint_probe.pt"
    next_desc = sampler.peek_descriptor_bundle_for_step(1)
    sampler_state = sampler.state_dict(next_descriptor=next_desc)
    save_care_ase_checkpoint(
        ckpt,
        model=model,
        optimizer=optimizer,
        scheduler=scheduler,
        global_step=1,
        stage_id="A",
        next_batch_hash=sampler_state["next_batch_descriptor_sha256"],
        loss_history_tail=[{"optimizer_step": 1, "loss": float(complete_loss.detach().cpu())}],
        sampler_state=sampler_state,
        code_hash=combined_source_hash(),
        split_hash=sha256_file(SPLITS),
    )
    reloaded, payload = load_care_ase_checkpoint(ckpt, map_location=device, restore_rng=False)
    reloaded.to(device).eval()
    model.eval()
    with torch.no_grad():
        before = model(complete_batch["image"], complete_batch["availability"], global_step=1)["final_logits"]
        after = reloaded(complete_batch["image"], complete_batch["availability"], global_step=1)["final_logits"]
        reload_max_abs = float((before - after).abs().max().detach().cpu())
    exact_resume = exact_resume_behavioral_equivalence(copy.deepcopy(model).to(device), complete_batch, fold=fold, device=device, ckpt_path=fold_out / "g2_exact_resume_probe.pt")

    image_np = read_b2nd(PREPROCESSED / f"{descriptors['complete_centerB'].case_id}.b2nd").astype(np.float32, copy=False)
    image = torch.from_numpy(image_np[None]).to(device=device, dtype=torch.float32)
    availability = torch.tensor([descriptors["complete_centerB"].availability], device=device, dtype=torch.float32)
    with torch.no_grad():
        sw_logits = sliding_window_logits(model, image, availability, patch_size=sw_patch)
        sw_decoded = decode_care_ase_r2_logits(sw_logits, availability)

    outer_audit = outer_access_audit(out)
    checks = {
        "cuda_device": torch.cuda.get_device_name(0),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "fold": fold,
        "source_hash": combined_source_hash(),
        "area_reference": area,
        "augmentation_contract": {**augmentation_contract.__dict__, "sha256": augmentation_contract.sha256()},
        "required_case_descriptors": {
            key: {
                "case_id": value.case_id,
                "global_step": value.global_step,
                "case_group": value.case_group,
                "center": value.center,
                "pathology_focus": value.pathology_focus,
                "within_focus": value.within_focus,
                "availability": value.availability,
                "hard_negative_category": value.hard_negative_category,
                "resolved_target_coordinate_count": len(value.resolved_target_coordinates),
            }
            for key, value in descriptors.items()
        },
        "step0_parity": step0,
        "gradient": {
            "complete_loss_finite": bool(torch.isfinite(complete_loss).item()),
            "complete_metrics": complete_metrics,
            "complete_grad_max": complete_grad,
            "named_projection_gradient": named_gradient,
            "no_t2_loss_finite": bool(torch.isfinite(no_t2_loss).item()),
            "no_t2_metrics": no_t2_metrics,
            "no_t2_edema_exclusive_grad_by_prefix": no_t2_edema_grad_by_prefix,
            "no_t2_edema_exclusive_grad_max": no_t2_edema_grad,
            "no_t2_edema_exclusive_gradient_zero": no_t2_edema_grad == 0.0,
        },
        "overfit_direction": {
            "steps": overfit_history,
            "initial_loss": overfit_history[0]["loss"],
            "final_loss": overfit_history[-1]["loss"],
            "loss_decreased": overfit_history[-1]["loss"] < overfit_history[0]["loss"],
        },
        "module_off_final_logit_final_label_evidence": module_off,
        "named_projection_intervention": named_intervention,
        "sampler_400": sampler_400_checks(REPO_ROOT, fold),
        "scheduler": scheduler_checks(),
        "checkpoint": {
            **checkpoint_receipt(ckpt, payload),
            "reload_logits_max_abs_error": reload_max_abs,
            "sidecar_exists": ckpt.with_suffix(ckpt.suffix + ".sha256").is_file(),
        },
        "resume_equivalence": {
            **exact_resume,
            "scheduler_last_global_step": int(payload["scheduler"]["last_global_step"]),
            "next_batch_descriptor_sha256": payload["next_batch_descriptor_sha256"],
            "case_group_cursor": int(payload["case_group_cursor"]),
            "batch_descriptor_cursor": int(payload["batch_descriptor_cursor"]),
        },
        "decode": {
            "t2_present_argmax_class": int(decoded[0, 0, 0, 0].detach().cpu()),
            "no_t2_class4_excluded_argmax_class": int(decoded[1, 0, 0, 0].detach().cpu()),
            "no_t2_excludes_class4": int(decoded[1, 0, 0, 0].detach().cpu()) != 4,
        },
        "sliding_window": {
            "case_id": descriptors["complete_centerB"].case_id,
            "input_shape": list(image.shape),
            "patch_size": list(sw_patch),
            "logits_shape": list(sw_logits.shape),
            "decoded_shape": list(sw_decoded.shape),
            "finite_logits": bool(torch.isfinite(sw_logits).all().item()),
        },
        "outer_access_audit": outer_audit,
        "outer_access_count_before_freeze": int(outer_audit["outer_access_count_before_freeze"]),
    }
    write_json(out / f"named_evidence_projection_gradient_fold{fold}.json", named_gradient)
    write_json(out / f"named_evidence_projection_intervention_fold{fold}.json", named_intervention)
    write_json(out / f"sampler_400_step_full_composition_receipt_fold{fold}.json", checks["sampler_400"])
    write_json(out / f"exact_resume_behavioral_equivalence_fold{fold}.json", exact_resume)
    write_json(out / f"outer_access_audit_receipt_fold{fold}.json", outer_audit)
    pass_conditions = [
        step0["status"] == "PASS",
        checks["gradient"]["complete_loss_finite"],
        checks["gradient"]["no_t2_loss_finite"],
        complete_grad["scar_branch"] > 0.0,
        complete_grad["edema_branch"] > 0.0,
        complete_grad["component_heads"] > 0.0,
        named_gradient["status"] == "PASS",
        checks["gradient"]["no_t2_edema_exclusive_gradient_zero"],
        checks["overfit_direction"]["loss_decreased"],
        checks["module_off_final_logit_final_label_evidence"]["status"] == "PASS",
        checks["named_projection_intervention"]["status"] == "PASS",
        checks["sampler_400"]["status"] == "PASS",
        checks["scheduler"]["status"] == "PASS",
        checks["checkpoint"]["required_fields_present"],
        checks["checkpoint"]["sidecar_exists"],
        reload_max_abs <= 1.0e-6,
        exact_resume["status"] == "PASS",
        checks["decode"]["no_t2_excludes_class4"],
        checks["sliding_window"]["finite_logits"],
        checks["outer_access_audit"]["status"] == "PASS",
    ]
    checks["decision"] = "PASS" if all(pass_conditions) else "NEEDS_REPAIR_CONTINUE_CURRENT_GOAL"
    checks["pass_condition_count"] = sum(bool(item) for item in pass_conditions)
    checks["required_pass_condition_count"] = len(pass_conditions)
    write_json(out / f"g2_real_gpu_fidelity_receipt_fold{fold}.json", checks)
    aggregate = {"folds": {}, "decision": checks["decision"], "required_folds": [1, 4]}
    for candidate_fold in (1, 4):
        candidate = out / f"g2_real_gpu_fidelity_receipt_fold{candidate_fold}.json"
        if candidate.is_file():
            aggregate["folds"][str(candidate_fold)] = json.loads(candidate.read_text(encoding="utf-8"))
    aggregate["completed_folds"] = sorted(int(k) for k in aggregate["folds"])
    aggregate["decision"] = "PASS" if aggregate["completed_folds"] == [1, 4] and all(row.get("decision") == "PASS" for row in aggregate["folds"].values()) else "NEEDS_REPAIR_CONTINUE_CURRENT_GOAL"
    write_json(out / "g2_real_gpu_fidelity_receipt.json", aggregate)
    print(json.dumps({"decision": checks["decision"], "pass_condition_count": checks["pass_condition_count"], "required": checks["required_pass_condition_count"]}, indent=2))
    return 0 if checks["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
