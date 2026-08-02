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
    combined_source_hash,
    make_batch,
    parse_patch_size,
    read_b2nd,
)
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.models.care_ase import build_care_ase_for_fold_with_area_references
from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler, compute_actual_train_area_references
from src.care_myocardium.training.care_ase_trainer import (
    CAREASEStageScheduler,
    build_optimizer,
    care_ase_loss,
    checkpoint_receipt,
    load_care_ase_checkpoint,
    save_care_ase_checkpoint,
    set_stage_trainability,
    write_json,
)


RESULT_ROOT = REPO_ROOT / "results/20260803_care_ase_r2_full_fidelity_execution"


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
        desc = probe.descriptor_for_step(step)
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


def one_train_step(model: torch.nn.Module, optimizer: torch.optim.Optimizer, scheduler: CAREASEStageScheduler, batch: dict[str, torch.Tensor], step: int) -> dict[str, Any]:
    model.train()
    stage = set_stage_trainability(model, global_step=step)
    scheduler.step(step)
    optimizer.zero_grad(set_to_none=True)
    outputs = model(batch["image"], batch["availability"], global_step=step)
    loss, metrics = care_ase_loss(outputs, batch)
    loss.backward()
    optimizer.step()
    return {"stage": stage, "loss": float(loss.detach().cpu()), "metrics": metrics}


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
        "lr_B9999_upper": CAREASEStageScheduler.lr_for(group_name="upper_two_encoder_stages", global_step=9999),
        "lr_C10000_lower": CAREASEStageScheduler.lr_for(group_name="lower_encoder_and_bottleneck", global_step=10000),
        "lr_C13999_new_modules": CAREASEStageScheduler.lr_for(group_name="new_modules", global_step=13999),
    }
    checks["status"] = "PASS" if checks["stage_0"] == "A" and checks["stage_2000"] == "B" and checks["stage_10000"] == "C" else "FAIL"
    return checks


def sampler_400_checks(repo_root: Path, fold: int) -> dict[str, Any]:
    sampler = CAREASEDeterministicSampler(repo_root, fold)
    rows = [sampler.descriptor_for_step(step) for step in range(400)]
    counts = Counter(desc.case_group for desc in rows)
    within = Counter((desc.pathology_focus, desc.within_focus) for desc in rows)
    manifest = sampler.hard_negative_manifest
    status = (
        counts.get("complete", 0) == 200
        and counts.get("lge_only", 0) == 100
        and counts.get("lge_c0", 0) == 100
        and manifest.get("manifest_sha256") not in {"MISSING", None}
        and int(manifest.get("case_count", 0) or len(manifest.get("cases", {}))) > 0
    )
    return {
        "status": "PASS" if status else "FAIL",
        "counts": dict(counts),
        "within_focus_counts": {f"{k[0]}:{k[1]}": v for k, v in within.items()},
        "manifest_path": manifest.get("manifest_path"),
        "manifest_sha256": manifest.get("manifest_sha256"),
        "manifest_case_count": int(manifest.get("case_count", 0) or len(manifest.get("cases", {}))),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=1, choices=(1, 4))
    parser.add_argument("--patch-size", default="8,64,64")
    parser.add_argument("--sliding-window-patch-size", default="8,128,128")
    parser.add_argument("--output-dir", type=Path, default=RESULT_ROOT)
    parser.add_argument("--seed", type=int, default=20260803)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = require_gpu()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    patch_size = parse_patch_size(args.patch_size)
    sw_patch = parse_patch_size(args.sliding_window_patch_size)
    fold = int(args.fold)

    area = compute_actual_train_area_references(REPO_ROOT, fold)
    sampler = CAREASEDeterministicSampler(REPO_ROOT, fold)
    descriptors = {
        "complete_centerB": find_descriptor(sampler, lambda d: d.case_group == "complete" and d.center == "CenterB"),
        "complete_centerC": find_descriptor(sampler, lambda d: d.case_group == "complete" and d.center == "CenterC"),
        "lge_only": find_descriptor(sampler, lambda d: d.case_group == "lge_only"),
        "lge_c0": find_descriptor(sampler, lambda d: d.case_group == "lge_c0"),
        "small_scar": find_descriptor(sampler, lambda d: d.pathology_focus == "scar" and d.within_focus == "small_component"),
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
        name: make_batch(desc, descriptor_sha=desc.sha256(), micro=0, patch_size=patch_size, device=device)
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

    optimizer.zero_grad(set_to_none=True)
    outputs_no_t2 = model(no_t2_batch["image"], no_t2_batch["availability"], global_step=2000)
    no_t2_loss, no_t2_metrics = care_ase_loss(outputs_no_t2, no_t2_batch)
    no_t2_loss.backward()
    no_t2_edema_grad = grad_max(model, "edema_branch.")

    overfit_model = copy.deepcopy(model).to(device)
    overfit_optimizer = build_optimizer(overfit_model)
    overfit_scheduler = CAREASEStageScheduler(overfit_optimizer)
    overfit_history = [one_train_step(overfit_model, overfit_optimizer, overfit_scheduler, complete_batch, 2000 + idx) for idx in range(4)]

    decode_input = torch.zeros(2, 6, 2, 4, 4, device=device)
    decode_input[0, 4] = 10.0
    decode_input[1, 4] = 10.0
    decoded = decode_care_ase_r2_logits(decode_input, torch.tensor([[1.0, 1.0, 1.0], [1.0, 0.0, 1.0]], device=device))

    ckpt = out / "g2_atomic_checkpoint_probe.pt"
    next_desc = sampler.peek_descriptor_for_step(1)
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

    image_np = read_b2nd(PREPROCESSED / f"{descriptors['complete_centerB'].case_id}.b2nd").astype(np.float32, copy=False)
    image = torch.from_numpy(image_np[None]).to(device=device, dtype=torch.float32)
    availability = torch.tensor([descriptors["complete_centerB"].availability], device=device, dtype=torch.float32)
    with torch.no_grad():
        sw_logits = sliding_window_logits(model, image, availability, patch_size=sw_patch)
        sw_decoded = decode_care_ase_r2_logits(sw_logits, availability)

    checks = {
        "cuda_device": torch.cuda.get_device_name(0),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "fold": fold,
        "source_hash": combined_source_hash(),
        "area_reference": area,
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
            "no_t2_loss_finite": bool(torch.isfinite(no_t2_loss).item()),
            "no_t2_metrics": no_t2_metrics,
            "no_t2_edema_branch_grad_max": no_t2_edema_grad,
            "no_t2_edema_exclusive_gradient_zero": no_t2_edema_grad == 0.0,
        },
        "overfit_direction": {
            "steps": overfit_history,
            "initial_loss": overfit_history[0]["loss"],
            "final_loss": overfit_history[-1]["loss"],
            "loss_decreased": overfit_history[-1]["loss"] < overfit_history[0]["loss"],
        },
        "sampler_400": sampler_400_checks(REPO_ROOT, fold),
        "scheduler": scheduler_checks(),
        "checkpoint": {
            **checkpoint_receipt(ckpt, payload),
            "reload_logits_max_abs_error": reload_max_abs,
            "sidecar_exists": ckpt.with_suffix(ckpt.suffix + ".sha256").is_file(),
        },
        "resume_equivalence": {
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
        "outer_access_count_before_freeze": 0,
    }
    pass_conditions = [
        step0["status"] == "PASS",
        checks["gradient"]["complete_loss_finite"],
        checks["gradient"]["no_t2_loss_finite"],
        complete_grad["scar_branch"] > 0.0,
        complete_grad["edema_branch"] > 0.0,
        complete_grad["component_heads"] > 0.0,
        checks["gradient"]["no_t2_edema_exclusive_gradient_zero"],
        checks["overfit_direction"]["loss_decreased"],
        checks["sampler_400"]["status"] == "PASS",
        checks["scheduler"]["status"] == "PASS",
        checks["checkpoint"]["required_fields_present"],
        checks["checkpoint"]["sidecar_exists"],
        reload_max_abs <= 1.0e-6,
        checks["decode"]["no_t2_excludes_class4"],
        checks["sliding_window"]["finite_logits"],
    ]
    checks["decision"] = "PASS" if all(pass_conditions) else "NEEDS_REPAIR_CONTINUE_CURRENT_GOAL"
    checks["pass_condition_count"] = sum(bool(item) for item in pass_conditions)
    checks["required_pass_condition_count"] = len(pass_conditions)
    write_json(out / "g2_real_gpu_fidelity_receipt.json", checks)
    print(json.dumps({"decision": checks["decision"], "pass_condition_count": checks["pass_condition_count"], "required": checks["required_pass_condition_count"]}, indent=2))
    return 0 if checks["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
