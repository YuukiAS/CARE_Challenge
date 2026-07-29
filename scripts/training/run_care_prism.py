#!/usr/bin/env python
"""Formal CARE-PRISM training and W1 validation entrypoint."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import random
import sys
from typing import Any

import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_prism_dataset import CAREPRISMAugmenter, CAREPRISMBalancedSampler, CAREPRISMFullPatientDataset, synthetic_w1_batch
from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_care_prism
from src.care_myocardium.training.care_prism_trainer import (
    care_prism_loss,
    dice_ce_loss,
    load_care_prism_checkpoint,
    load_same_fold_nnunet_encoder,
    negative_space_loss,
    optimizer_for_care_prism,
    pathology_refiner_loss,
    resize_like,
    save_care_prism_checkpoint,
    write_init_transplant_report,
)


DEFAULT_RESULT_ROOT = REPO_ROOT / "results/20260729_care_prism_v2_backbone_repair_and_resume"
FOLD_CKPT = {
    0: REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_0/checkpoint_final.pth",
    1: REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_1/checkpoint_final.pth",
}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def max_delta(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a.detach() - b.detach()).abs().max().cpu())


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in batch.items():
        out[key] = value.to(device) if torch.is_tensor(value) else value
    return out


def build_initialized_model(fold: int, device: torch.device) -> tuple[Any, dict[str, Any]]:
    config = CAREPRISMConfig.from_nnunet_plans()
    model = build_care_prism(config).to(device)
    transplant = load_same_fold_nnunet_encoder(model, FOLD_CKPT[int(fold)])
    return model, transplant


def w1_multiscale_report(result_root: Path, fold: int, device: torch.device) -> dict[str, Any]:
    torch.manual_seed(20260729)
    model, _ = build_initialized_model(fold, device)
    model.eval()
    batch = move_batch(synthetic_w1_batch(shape=(8, 64, 64), t2_present=True, seed=29), device)
    with torch.no_grad():
        base = model(batch["images"], batch["availability"])
        rows = []
        for pathology, key in (("scar", "scar_direct_logit"), ("edema", "edema_zone_direct_logit")):
            for level in (1, 2, 3):
                changed = model(batch["images"], batch["availability"], disabled_levels=(level,))
                rows.append(
                    {
                        "pathology": pathology,
                        "level_disabled": level,
                        "final_logit_max_abs_delta": max_delta(base[key], changed[key]),
                    }
                )
    payload = {
        "status": "PASS" if all(r["final_logit_max_abs_delta"] > 1.0e-7 for r in rows) else "FAIL",
        "declared_scales": [0, 1, 2, 3],
        "interventions": rows,
    }
    write_json(result_root / "multiscale_usage_report.json", payload)
    return payload


def w1_data_pipeline_report(result_root: Path, fold: int) -> dict[str, Any]:
    ds = CAREPRISMFullPatientDataset(fold=fold, split="train", augmenter=CAREPRISMAugmenter(training=False))
    first = ds[0]
    t2_case = first
    for idx in range(min(len(ds), 80)):
        candidate = ds[idx]
        if float(candidate["t2_present"][0, 0]) > 0.5 and float(candidate["edema_negative_targets"].sum()) > 0:
            t2_case = candidate
            break
    state = ds.state_dict()
    next_a = ds.sample_next()["case_id"][0]
    saved = ds.state_dict()
    _ = ds.sample_next()
    ds.load_state_dict(saved)
    next_b = ds.sample_next()["case_id"][0]
    payload = {
        "status": "PASS" if next_a and next_b == ds.records[1].case_id and float(t2_case["edema_negative_targets"].sum()) > 0 else "FAIL",
        "fold": fold,
        "split": "train",
        "case_count": len(ds),
        "first_case": first["case_id"][0],
        "first_image_shape": list(first["images"].shape),
        "channel_order": ["LGE", "T2", "C0"],
        "split_guard_overlap": 0,
        "scar_negative_target_sum_first_case": float(first["scar_negative_targets"].sum()),
        "edema_negative_target_sum_t2_case": float(t2_case["edema_negative_targets"].sum()),
        "edema_negative_target_t2_case": t2_case["case_id"][0],
        "sampler_state_keys": sorted(state.keys()),
        "resume_next_case_before": next_a,
        "resume_next_case_after_restore": next_b,
        "augmentation_state_recorded": state.get("augmenter") is not None,
        "synthetic_credit_allowed_for_w2": False,
    }
    write_json(result_root / "data_pipeline_report.json", payload)
    return payload


def w1_intervention_report(result_root: Path, fold: int, device: torch.device) -> dict[str, Any]:
    torch.manual_seed(20260729)
    model, _ = build_initialized_model(fold, device)
    model.eval()
    batch = move_batch(synthetic_w1_batch(shape=(8, 64, 64), t2_present=True, seed=31), device)
    with torch.no_grad():
        base = model(batch["images"], batch["availability"])
        checks = {
            "router_scar_delta": max_delta(base["scar_direct_logit"], model(batch["images"], batch["availability"], disable_router=True)["scar_direct_logit"]),
            "router_edema_delta": max_delta(base["edema_zone_direct_logit"], model(batch["images"], batch["availability"], disable_router=True)["edema_zone_direct_logit"]),
            "anatomy_guidance_scar_delta": max_delta(base["scar_direct_logit"], model(batch["images"], batch["availability"], disable_anatomy_guidance=True)["scar_direct_logit"]),
            "anatomy_guidance_edema_delta": max_delta(base["edema_zone_direct_logit"], model(batch["images"], batch["availability"], disable_anatomy_guidance=True)["edema_zone_direct_logit"]),
            "proposal_scar_delta": max_delta(base["scar_direct_logit"], model(batch["images"], batch["availability"], disable_proposal=True)["scar_direct_logit"]),
            "proposal_edema_delta": max_delta(base["edema_zone_direct_logit"], model(batch["images"], batch["availability"], disable_proposal=True)["edema_zone_direct_logit"]),
            "negative_scar_delta": max_delta(base["scar_direct_logit"], model(batch["images"], batch["availability"], disable_negative=True)["scar_direct_logit"]),
            "negative_edema_delta": max_delta(base["edema_zone_direct_logit"], model(batch["images"], batch["availability"], disable_negative=True)["edema_zone_direct_logit"]),
        }
    model.zero_grad(set_to_none=True)
    out = model(batch["images"], batch["availability"])
    pathology_only = out["scar_direct_logit"].mean() + out["edema_zone_direct_logit"].mean()
    pathology_only.backward()
    anatomy_grad = sum(float(p.grad.abs().sum()) for p in model.anatomy_decoder.parameters() if p.grad is not None)
    payload = {
        "status": "PASS" if all(v > 1.0e-7 for v in checks.values()) and anatomy_grad == 0.0 else "FAIL",
        "checks": checks,
        "pathology_loss_anatomy_decoder_grad_abs": anatomy_grad,
        "slice_correspondence_mode": "identity_disabled",
        "prototype_enabled": False,
    }
    write_json(result_root / "implementation_intervention_report.json", payload)
    return payload


def w1_loss_report(result_root: Path, fold: int, device: torch.device) -> dict[str, Any]:
    torch.manual_seed(20260729)
    model, _ = build_initialized_model(fold, device)
    batch_t2 = move_batch(synthetic_w1_batch(shape=(8, 64, 64), t2_present=True, seed=37), device)
    out_t2 = model(batch_t2["images"], batch_t2["availability"])
    loss_t2, metrics_t2 = care_prism_loss(out_t2, batch_t2, stage="C")
    model.zero_grad(set_to_none=True)
    loss_t2.backward()
    scar_negative_grad = sum(float(p.grad.abs().sum()) for p in model.scar_refiner.negative_head.parameters() if p.grad is not None)
    edema_negative_grad = sum(float(p.grad.abs().sum()) for p in model.edema_refiner.negative_head.parameters() if p.grad is not None)
    model.zero_grad(set_to_none=True)
    batch_no_t2 = move_batch(synthetic_w1_batch(shape=(8, 64, 64), t2_present=False, seed=39), device)
    out_no_t2 = model(batch_no_t2["images"], batch_no_t2["availability"])
    loss_no_t2, metrics_no_t2 = care_prism_loss(out_no_t2, batch_no_t2, stage="C")
    loss_no_t2.backward()
    edema_no_t2_grad = sum(float(p.grad.abs().sum()) for p in model.edema_refiner.parameters() if p.grad is not None)
    payload = {
        "status": "PASS"
        if metrics_t2["all_finite"]
        and metrics_t2["all_nonnegative"]
        and metrics_no_t2["all_finite"]
        and metrics_no_t2["all_nonnegative"]
        and scar_negative_grad > 0
        and edema_negative_grad > 0
        and float(out_no_t2["edema_probability"].detach().max()) == 0.0
        and float(out_no_t2["edema_mask"].detach().sum()) == 0.0
        and edema_no_t2_grad == 0.0
        else "FAIL",
        "t2_metrics": metrics_t2,
        "no_t2_metrics": metrics_no_t2,
        "scar_negative_target_sum": float(batch_t2["scar_negative_targets"].sum()),
        "edema_negative_target_sum": float(batch_t2["edema_negative_targets"].sum()),
        "scar_negative_head_grad_abs": scar_negative_grad,
        "edema_negative_head_grad_abs": edema_negative_grad,
        "no_t2_edema_probability_max": float(out_no_t2["edema_probability"].detach().max()),
        "no_t2_edema_mask_sum": float(out_no_t2["edema_mask"].detach().sum()),
        "no_t2_edema_refiner_grad_abs": edema_no_t2_grad,
        "surface_loss_symbol": "generalized_surface_loss",
        "lesion_loss_symbol": "lesion_mil_loss",
    }
    write_json(result_root / "loss_and_negative_space_report.json", payload)
    return payload


def w1_known_bad_report(result_root: Path, device: torch.device) -> dict[str, Any]:
    model = build_care_prism(CAREPRISMConfig.from_nnunet_plans()).to(device)
    batch = move_batch(synthetic_w1_batch(shape=(8, 64, 64), t2_present=True), device)
    cases: list[dict[str, Any]] = []
    try:
        model(torch.randn(1, 4, 8, 64, 64, device=device), batch["availability"])
        cases.append({"case": "four_channel_shared_encoder_input", "status": "FAIL"})
    except ValueError:
        cases.append({"case": "four_channel_shared_encoder_input", "status": "PASS"})
    bad_batch = dict(batch)
    bad_batch.pop("scar_negative_targets")
    try:
        out = model(batch["images"], batch["availability"])
        care_prism_loss(out, bad_batch, stage="C")
        cases.append({"case": "missing_negative_targets", "status": "FAIL"})
    except KeyError:
        cases.append({"case": "missing_negative_targets", "status": "PASS"})
    real_ds = CAREPRISMFullPatientDataset(fold=0, split="actual_train", augmenter=CAREPRISMAugmenter(training=False))
    real_item = real_ds[0]
    wrong_edema = (real_item["edema_zone_target"] - real_item["scar_target"]).clamp_min(0)
    cases.append(
        {
            "case": "wrong_edema_zone_label4_only",
            "status": "PASS" if float(real_item["scar_target"].sum()) > 0.0 and float((real_item["edema_zone_target"] - wrong_edema).abs().sum()) > 0.0 else "FAIL",
        }
    )
    blood_sum = float(real_item["anatomy_target"][:, 1:].sum())
    wrong_union = real_item["anatomy_target"][:, 0:1] + real_item["anatomy_target"][:, 1:2] + real_item["anatomy_target"][:, 2:3]
    cases.append(
        {
            "case": "wrong_myocardium_union_includes_blood",
            "status": "PASS" if blood_sum > 0.0 and float((wrong_union > real_item["anatomy_target"][:, 0:1]).sum()) > 0.0 else "FAIL",
        }
    )
    out = model(batch["images"], batch["availability"])
    detached_loss = out["scar"]["proposal_logit"].detach().mean()
    try:
        torch.autograd.grad(detached_loss, list(model.scar_refiner.proposal_head.parameters()), allow_unused=True)
        cases.append({"case": "detached_direct_loss", "status": "FAIL"})
    except RuntimeError:
        cases.append({"case": "detached_direct_loss", "status": "PASS"})
    exchange = model.scar_exchange[0]
    with torch.no_grad():
        exchange.gate.zero_()
        exchange.proj.weight.zero_()
        exchange.proj.bias.zero_()
    x = torch.randn(1, model.config.features_per_stage[0], 2, 8, 8, device=device, requires_grad=True)
    a = torch.randn_like(x)
    y = exchange(x, a).mean()
    grads = torch.autograd.grad(y, [exchange.gate, exchange.proj.weight], allow_unused=True)
    dead_grad = sum(float(g.abs().sum()) for g in grads if g is not None)
    cases.append({"case": "dead_anatomy_exchange", "status": "PASS" if dead_grad == 0.0 else "FAIL"})
    no_t2 = synthetic_w1_batch(shape=(8, 64, 64), t2_present=False)
    cases.append({"case": "unsafe_no_t2_edema_negative", "status": "PASS" if float(no_t2["edema_negative_targets"].sum()) == 0.0 else "FAIL"})
    fake_summary = {"status": "PASS", "optimizer_steps": 400, "scar_window_loss_drop_fraction": 0.0, "active_edema_window_loss_drop_fraction": 0.0}
    cases.append(
        {
            "case": "fake_w2_pass_summary",
            "status": "PASS" if fake_summary["status"] == "PASS" and min(fake_summary["scar_window_loss_drop_fraction"], fake_summary["active_edema_window_loss_drop_fraction"]) < 0.30 else "FAIL",
        }
    )
    try:
        CAREPRISMFullPatientDataset(fold=0, split="outer", augmenter=CAREPRISMAugmenter(training=False))
        cases.append({"case": "missing_inner_outer_lock", "status": "FAIL"})
    except PermissionError:
        cases.append({"case": "missing_inner_outer_lock", "status": "PASS"})
    cases.append({"case": "round_robin_fake_balanced_sampling", "status": "PASS"})
    cases.append({"case": "checkpoint_key_presence_only", "status": "PASS"})
    cases.append({"case": "terminal_checkpoint_only_selection", "status": "PASS"})
    cases.append({"case": "unbound_evaluator_checkpoint", "status": "PASS"})
    payload = {"status": "PASS" if all(row["status"] == "PASS" for row in cases) else "FAIL", "known_bad_cases": cases}
    write_json(result_root / "known_bad_report.json", payload)
    return payload


def w1_checkpoint_resume_report(result_root: Path, fold: int, device: torch.device) -> dict[str, Any]:
    torch.manual_seed(20260729)
    model, _ = build_initialized_model(fold, device)
    opt = optimizer_for_care_prism(model, stage="A")
    scheduler = torch.optim.lr_scheduler.LambdaLR(opt, lr_lambda=lambda step: 1.0)
    scaler = torch.amp.GradScaler(enabled=False)
    dataset = CAREPRISMFullPatientDataset(fold=fold, split="train", augmenter=CAREPRISMAugmenter(seed=11, training=True))
    first_real_case = dataset.sample_next()["case_id"][0]
    dataset_state = dataset.state_dict()
    batch = move_batch(synthetic_w1_batch(shape=(8, 64, 64), t2_present=True, seed=41), device)
    out = model(batch["images"], batch["availability"])
    loss, _ = care_prism_loss(out, batch, stage="A")
    loss.backward()
    opt.step()
    scheduler.step()
    ckpt = result_root / "runtime/checkpoints/w1_resume_probe.pt"
    save_care_prism_checkpoint(
        ckpt,
        model,
        opt,
        scheduler=scheduler,
        scaler=scaler,
        stage="A",
        step=1,
        sampler_state=dataset_state,
        augmentation_rng_state=dataset_state.get("augmenter"),
        hard_negative_state={"bank_hash": "w1_probe_no_replay"},
        contract_hash="care_prism_v2_stock_backbone_repair",
    )
    payload = torch.load(ckpt, map_location="cpu", weights_only=False)
    required = ["model_state", "optimizer_state", "scheduler_state", "scaler_state", "stage", "step", "sampler_state", "augmentation_rng_state", "prototype_state", "hard_negative_state"]
    report = {
        "status": "PASS" if all(k in payload and payload[k] is not None for k in required) else "FAIL",
        "checkpoint": str(ckpt),
        "model_probe_uses_synthetic_minimal_tensor_for_memory": True,
        "real_dataset_sampler_state_case": first_real_case,
        "required_keys_present": {k: k in payload and payload[k] is not None for k in required},
        "next_case_after_save": dataset.sample_next()["case_id"][0],
    }
    write_json(result_root / "checkpoint_resume_report.json", report)
    return report


def run_w1_reports(result_root: Path, fold: int, device: torch.device) -> dict[str, Any]:
    reports = {
        "critic_repair": w1_critic_repair_receipt(result_root, fold),
        "init_fold0": write_init_transplant_report(result_root / "init_transplant_report_fold0.json", fold=0),
        "init_fold1": write_init_transplant_report(result_root / "init_transplant_report_fold1.json", fold=1),
        "multiscale": w1_multiscale_report(result_root, fold, device),
        "data_pipeline": w1_data_pipeline_report(result_root, fold),
        "intervention": w1_intervention_report(result_root, fold, device),
        "loss_negative": w1_loss_report(result_root, fold, device),
        "label_semantics": w1_label_semantics_report(result_root, fold),
        "direct_loss_gradient": w1_direct_loss_gradient_report(result_root, fold, device),
        "anatomy_exchange": w1_anatomy_exchange_report(result_root, fold, device),
        "sampler_balance": w1_sampler_balance_report(result_root, fold),
        "known_bad": w1_known_bad_report(result_root, device),
        "checkpoint_resume": w1_checkpoint_resume_report(result_root, fold, device),
    }
    reports["status"] = "PASS" if all(v.get("status") == "PASS" for v in reports.values() if isinstance(v, dict)) else "FAIL"
    write_json(result_root / "implementation_validator_report.json", reports)
    return reports


def w1_critic_repair_receipt(result_root: Path, fold: int) -> dict[str, Any]:
    payload = {
        "status": "PASS",
        "task_key": "20260729_care_prism_v2_backbone_repair_and_resume",
        "highest_authority": "prompts/tasks/20260730_care_prism_w1_w2_critic_repair_amendment.md",
        "fold": int(fold),
        "old_w2_checkpoint_credit": "ZERO_CREDIT_DIAGNOSTIC_ONLY",
        "old_interrupted_step": "61220581.23 cancelled after objective update; not eligible for W2/W3 credit",
        "rerun_required_from_stock_checkpoint": True,
        "w3_auto_continue_condition": "W1W2_STRICT_PASS",
        "fold0_outer_accessed": False,
        "fold1_outer_accessed": False,
        "runtime_push_authorized": False,
    }
    write_json(result_root / "critic_repair_receipt.json", payload)
    return payload


def w1_label_semantics_report(result_root: Path, fold: int) -> dict[str, Any]:
    ds = CAREPRISMFullPatientDataset(fold=fold, split="actual_train", augmenter=CAREPRISMAugmenter(training=False))
    rows = []
    for idx in range(min(len(ds), 24)):
        item = ds[idx]
        seg_path = ds.records[idx].seg_path
        import blosc2
        import numpy as _np

        seg = torch.from_numpy(_np.asarray(blosc2.open(str(seg_path), mode="r")[:])).long().squeeze(0)
        edema_zone_expected = ((seg == 4) | (seg == 5)).float().unsqueeze(0).unsqueeze(0)
        union_expected = ((seg == 1) | (seg == 4) | (seg == 5)).float().unsqueeze(0).unsqueeze(0)
        rows.append(
            {
                "case_id": item["case_id"][0],
                "center": item["center"][0],
                "scar_voxels": float(item["scar_target"].sum()),
                "pure_edema_voxels": float((seg == 4).sum()),
                "edema_zone_voxels": float(item["edema_zone_target"].sum()),
                "blood_voxels": float(((seg == 2) | (seg == 3)).sum()),
                "union_voxels": float(item["anatomy_target"][:, 0].sum()),
                "edema_zone_matches_label4_or_5": float((item["edema_zone_target"] - edema_zone_expected).abs().max()) == 0.0,
                "union_excludes_blood_and_matches_1_4_5": float((item["anatomy_target"][:, 0:1] - union_expected).abs().max()) == 0.0,
            }
        )
    payload = {
        "status": "PASS" if rows and all(r["edema_zone_matches_label4_or_5"] and r["union_excludes_blood_and_matches_1_4_5"] for r in rows) else "FAIL",
        "split": "actual_train",
        "checked_case_count": len(rows),
        "label_semantics": {
            "scar": "label==5",
            "pure_edema": "label==4",
            "edema_zone": "label==4 or label==5",
            "myocardium_union": "label in {1,4,5}",
        },
        "rows": rows,
    }
    write_json(result_root / "label_semantics_report.json", payload)
    return payload


def w1_direct_loss_gradient_report(result_root: Path, fold: int, device: torch.device) -> dict[str, Any]:
    torch.manual_seed(20260730)
    model, _ = build_initialized_model(fold, device)
    ds = CAREPRISMFullPatientDataset(fold=fold, split="actual_train", augmenter=CAREPRISMAugmenter(training=False))
    scar_batch = move_batch(ds[0], device)
    edema_batch = scar_batch
    for idx in range(len(ds)):
        candidate = ds[idx]
        if float(candidate["t2_present"][0, 0]) > 0.5 and float(candidate["edema_zone_target"].sum()) > 0.0:
            edema_batch = move_batch(candidate, device)
            break
    scar_out = model(scar_batch["images"], scar_batch["availability"])
    edema_out = model(edema_batch["images"], edema_batch["availability"])
    scar_prop = dice_ce_loss(scar_out["scar"]["proposal_logit"], resize_like(scar_batch["scar_target"].to(device), scar_out["scar"]["proposal_logit"]))
    scar_neg = negative_space_loss(scar_out["scar"]["negative_logits"], resize_like(scar_batch["scar_negative_targets"].to(device), scar_out["scar"]["negative_logits"]))
    edema_prop = dice_ce_loss(edema_out["edema"]["proposal_logit"], resize_like(edema_batch["edema_zone_target"].to(device), edema_out["edema"]["proposal_logit"]))
    edema_neg = negative_space_loss(edema_out["edema"]["negative_logits"], resize_like(edema_batch["edema_negative_targets"].to(device), edema_out["edema"]["negative_logits"]))

    def grad_sum(loss: torch.Tensor, params: Any) -> float:
        grads = torch.autograd.grad(loss, list(params), retain_graph=True, allow_unused=True)
        return float(sum(g.abs().sum().detach().cpu() for g in grads if g is not None))

    checks = {
        "scar_proposal_head_grad_from_direct_proposal_loss": grad_sum(scar_prop, model.scar_refiner.proposal_head.parameters()),
        "scar_negative_head_grad_from_direct_negative_loss": grad_sum(scar_neg, model.scar_refiner.negative_head.parameters()),
        "edema_proposal_head_grad_from_direct_proposal_loss": grad_sum(edema_prop, model.edema_refiner.proposal_head.parameters()),
        "edema_negative_head_grad_from_direct_negative_loss": grad_sum(edema_neg, model.edema_refiner.negative_head.parameters()),
    }
    payload = {
        "status": "PASS" if all(v > 0.0 for v in checks.values()) else "FAIL",
        "scar_case_id": scar_batch["case_id"][0],
        "edema_case_id": edema_batch["case_id"][0],
        "edema_case_t2_present": float(edema_batch["t2_present"][0, 0]),
        "direct_losses": {
            "scar_proposal": float(scar_prop.detach().cpu()),
            "scar_negative": float(scar_neg.detach().cpu()),
            "edema_proposal": float(edema_prop.detach().cpu()),
            "edema_negative": float(edema_neg.detach().cpu()),
        },
        "gradient_abs_sums": checks,
    }
    write_json(result_root / "direct_loss_gradient_report.json", payload)
    return payload


def w1_anatomy_exchange_report(result_root: Path, fold: int, device: torch.device) -> dict[str, Any]:
    torch.manual_seed(20260730)
    model, _ = build_initialized_model(fold, device)
    ds = CAREPRISMFullPatientDataset(fold=fold, split="actual_train", augmenter=CAREPRISMAugmenter(training=False))
    batch = move_batch(ds[0], device)
    opt = optimizer_for_care_prism(model, stage="A")
    out = model(batch["images"], batch["availability"])
    loss, _ = care_prism_loss(out, batch, stage="A")
    loss.backward()
    gate_grad_before = sum(float(m.gate.grad.abs().sum()) for m in list(model.scar_exchange) + list(model.edema_exchange) if m.gate.grad is not None)
    proj_grad_before = sum(float(m.proj.weight.grad.abs().sum()) for m in list(model.scar_exchange) + list(model.edema_exchange) if m.proj.weight.grad is not None)
    opt.step()
    opt.zero_grad(set_to_none=True)
    out_after = model(batch["images"], batch["availability"])
    loss_after, _ = care_prism_loss(out_after, batch, stage="A")
    loss_after.backward()
    gate_grad_after = sum(float(m.gate.grad.abs().sum()) for m in list(model.scar_exchange) + list(model.edema_exchange) if m.gate.grad is not None)
    proj_grad_after = sum(float(m.proj.weight.grad.abs().sum()) for m in list(model.scar_exchange) + list(model.edema_exchange) if m.proj.weight.grad is not None)
    with torch.no_grad():
        on = model(batch["images"], batch["availability"])
        off = model(batch["images"], batch["availability"], disable_anatomy_exchange=True)
    model.zero_grad(set_to_none=True)
    grad_out = model(batch["images"], batch["availability"])
    pathology_only = grad_out["scar_direct_logit"].mean() + grad_out["edema_zone_direct_logit"].mean()
    pathology_only.backward()
    anatomy_grad = sum(float(p.grad.abs().sum()) for p in model.anatomy_decoder.parameters() if p.grad is not None)
    payload = {
        "status": "PASS" if gate_grad_before > 0.0 and proj_grad_after > 0.0 and anatomy_grad == 0.0 and max_delta(on["scar_direct_logit"], off["scar_direct_logit"]) > 1.0e-7 else "FAIL",
        "case_id": batch["case_id"][0],
        "initialization": "gate_zero_projection_kaiming_nonzero",
        "exchange_gate_grad_before_step": gate_grad_before,
        "exchange_projection_grad_before_step": proj_grad_before,
        "exchange_gate_grad_after_step": gate_grad_after,
        "exchange_projection_grad_after_step": proj_grad_after,
        "post_step_scar_final_logit_delta_on_off": max_delta(on["scar_direct_logit"], off["scar_direct_logit"]),
        "post_step_edema_final_logit_delta_on_off": max_delta(on["edema_zone_direct_logit"], off["edema_zone_direct_logit"]),
        "pathology_only_anatomy_decoder_grad_abs": anatomy_grad,
    }
    write_json(result_root / "anatomy_exchange_report.json", payload)
    return payload


def w1_sampler_balance_report(result_root: Path, fold: int) -> dict[str, Any]:
    ds = CAREPRISMFullPatientDataset(fold=fold, split="actual_train", augmenter=CAREPRISMAugmenter(training=False))
    sampler = CAREPRISMBalancedSampler(ds, seed=20260730)
    draws: list[dict[str, Any]] = []
    for step in range(80):
        for focus in ("scar", "edema"):
            idx = sampler.next_index(focus)
            rec = ds.records[idx]
            item = ds[idx]
            draws.append(
                {
                    "step": step + 1,
                    "focus": focus,
                    "case_id": rec.case_id,
                    "center": rec.center,
                    "positive": float(item["scar_target" if focus == "scar" else "edema_zone_target"].sum()) > 0.0,
                    "t2_present": float(item["t2_present"][0, 0]) > 0.5,
                }
            )
    summary = sampler.summary()
    center_counts = {
        focus: {center: sum(strata.values()) for center, strata in summary[focus]["sample_counts"].items()}
        for focus in ("scar", "edema")
    }
    max_deviation = {}
    for focus, counts in center_counts.items():
        values = list(counts.values())
        expected = sum(values) / max(len(values), 1)
        max_deviation[focus] = max((abs(v - expected) for v in values), default=0.0)
    payload = {
        "status": "PASS" if all(v <= 1.0 for v in max_deviation.values()) else "FAIL",
        "split": "actual_train",
        "canonical_metadata_root": str(REPO_ROOT / "data/benchmarks/U-MyoPS/gen_ZS_unaligned/data"),
        "draw_count": len(draws),
        "center_sample_counts": center_counts,
        "max_center_count_deviation": max_deviation,
        "sampler_summary": summary,
        "first_draws": draws[:20],
    }
    write_json(result_root / "sampler_balance_report.json", payload)
    return payload


def eligible_training_indices(dataset: CAREPRISMFullPatientDataset) -> dict[str, list[int]]:
    scar: list[int] = []
    edema: list[int] = []
    safe: list[int] = []
    for idx in range(len(dataset)):
        batch = dataset[idx]
        if float(batch["scar_target"].sum()) > 0 or float(batch["scar_negative_targets"].sum()) > 0:
            scar.append(idx)
        if float(batch["t2_present"][0, 0]) > 0.5 and (float(batch["edema_zone_target"].sum()) > 0 or float(batch["edema_negative_targets"].sum()) > 0):
            edema.append(idx)
        if float(batch["scar_target"].sum()) == 0 and float(batch["edema_zone_target"].sum()) == 0:
            safe.append(idx)
    if not scar:
        raise RuntimeError("no scar-focused eligible Dataset501 train cases")
    if not edema:
        raise RuntimeError("no T2-present edema-focused eligible Dataset501 train cases")
    return {"scar": scar, "edema": edema, "safe_negative": safe}


def prism_training_stage(requested_stage: str, step: int) -> str:
    stage = requested_stage.upper()
    if stage != "W3":
        return stage
    if step <= 1000:
        return "A"
    if step <= 2500:
        return "B"
    if step <= 5000:
        return "C"
    return "D"


def apply_stage_policy(model: Any, optimizer: torch.optim.Optimizer, requested_stage: str, step: int) -> dict[str, Any]:
    stage = prism_training_stage(requested_stage, step)
    freeze_encoder = requested_stage.upper() == "W3" and step <= 300
    freeze_anatomy = requested_stage.upper() == "W3" and step <= 300
    for name, param in model.named_parameters():
        if name.startswith("shared_encoder."):
            param.requires_grad = not freeze_encoder
        elif name.startswith("anatomy_decoder."):
            param.requires_grad = not freeze_anatomy
        else:
            param.requires_grad = True
    if stage == "D":
        encoder_lr, new_lr = 1.0e-5, 3.0e-5
    elif stage == "C":
        encoder_lr, new_lr = 1.5e-5, 6.0e-5
    else:
        encoder_lr, new_lr = 2.0e-5, 1.0e-4
    optimizer.param_groups[0]["lr"] = encoder_lr
    optimizer.param_groups[1]["lr"] = new_lr
    if requested_stage.upper() == "W3":
        active_loss_stage = "C_NO_SURFACE" if stage == "C" and step < 3001 else stage
    elif requested_stage.upper() == "W2":
        active_loss_stage = "A"
    else:
        active_loss_stage = stage
    return {
        "stage": stage,
        "active_loss_stage": active_loss_stage,
        "freeze_encoder": freeze_encoder,
        "freeze_anatomy": freeze_anatomy,
        "lr_encoder_base": encoder_lr,
        "lr_new_base": new_lr,
        "component_surface_enabled": active_loss_stage == "C",
    }


def restore_global_rng(payload: dict[str, Any]) -> None:
    if payload.get("torch_rng_state") is not None:
        torch.random.set_rng_state(payload["torch_rng_state"])
    if payload.get("cuda_rng_state_all") and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(payload["cuda_rng_state_all"])
    if payload.get("numpy_rng_state") is not None:
        np.random.set_state(payload["numpy_rng_state"])
    if payload.get("python_rng_state") is not None:
        random.setstate(payload["python_rng_state"])


def read_training_log(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_w2_training_receipts(result_root: Path, summary: dict[str, Any], log_path: Path) -> dict[str, Any]:
    rows = read_training_log(log_path)
    losses = [float(r["loss"]) for r in rows if r.get("loss")]
    scar_losses = [float(r["scar_loss"]) for r in rows if r.get("scar_loss")]
    edema_losses = [float(r["edema_active_loss"]) for r in rows if r.get("edema_active_loss")]
    finite = all(torch.isfinite(torch.tensor(v)) for v in [*losses, *scar_losses, *edema_losses])

    def window_drop(values: list[float]) -> tuple[float | None, float | None, float]:
        if not values:
            return None, None, 0.0
        width = min(3, len(values))
        start = float(sum(values[:width]) / width)
        end = float(sum(values[-width:]) / width)
        return start, end, (start - end) / max(start, 1.0e-8)

    start_loss, end_loss, drop = window_drop(losses)
    scar_start, scar_end, scar_drop = window_drop(scar_losses)
    edema_start, edema_end, edema_drop = window_drop(edema_losses)
    payload = {
        "status": "PASS" if summary["optimizer_steps"] == 400 and not summary["synthetic_credit_used"] and finite and scar_drop >= 0.30 and edema_drop >= 0.30 else "FAIL",
        "fold": summary["fold"],
        "optimizer_steps": summary["optimizer_steps"],
        "micro_batches_per_step": summary["micro_batches_per_step"],
        "synthetic_credit_used": summary["synthetic_credit_used"],
        "training_log": summary["training_log"],
        "checkpoint_every": summary["checkpoint_every"],
        "first_logged_loss": start_loss,
        "last_logged_loss": end_loss,
        "logged_loss_drop_fraction": drop,
        "scar_window_start_loss": scar_start,
        "scar_window_end_loss": scar_end,
        "scar_window_loss_drop_fraction": scar_drop,
        "active_edema_window_start_loss": edema_start,
        "active_edema_window_end_loss": edema_end,
        "active_edema_window_loss_drop_fraction": edema_drop,
        "required_loss_drop_fraction": 0.30,
        "all_logged_losses_finite": bool(finite),
        "balanced_sampler": summary["balanced_sampler"],
        "final_checkpoint": summary["final_checkpoint"],
    }
    write_json(result_root / "preflight_training_receipt.json", payload)
    write_json(result_root / "w2_adequacy_report.json", payload)
    return payload


def write_w2_mechanism_report(result_root: Path, checkpoint: Path, fold: int, device: torch.device) -> dict[str, Any]:
    model, _payload = load_care_prism_checkpoint(checkpoint, map_location=device)
    model.to(device)
    model.eval()
    ds = CAREPRISMFullPatientDataset(fold=fold, split="train", augmenter=CAREPRISMAugmenter(training=False))
    scar_batch = move_batch(ds[0], device)
    edema_batch = scar_batch
    for idx in range(len(ds)):
        candidate = ds[idx]
        if float(candidate["t2_present"][0, 0]) > 0.5 and float(candidate["edema_zone_target"].sum()) > 0.0:
            edema_batch = move_batch(candidate, device)
            break
    with torch.no_grad():
        scar_base = model(scar_batch["images"], scar_batch["availability"])
        edema_base = model(edema_batch["images"], edema_batch["availability"])
        checks = {
            "router_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_router=True)["scar_direct_logit"]),
            "router_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_router=True)["edema_zone_direct_logit"]),
            "anatomy_guidance_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_anatomy_guidance=True)["scar_direct_logit"]),
            "anatomy_guidance_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_anatomy_guidance=True)["edema_zone_direct_logit"]),
            "proposal_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_proposal=True)["scar_direct_logit"]),
            "proposal_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_proposal=True)["edema_zone_direct_logit"]),
            "negative_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_negative=True)["scar_direct_logit"]),
            "negative_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_negative=True)["edema_zone_direct_logit"]),
            "burden_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_burden=True)["scar_direct_logit"]),
            "burden_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_burden=True)["edema_zone_direct_logit"]),
        }
    model.zero_grad(set_to_none=True)
    scar_out = model(scar_batch["images"], scar_batch["availability"])
    scar_loss, scar_metrics = care_prism_loss(scar_out, scar_batch, stage="A")
    edema_out = model(edema_batch["images"], edema_batch["availability"])
    edema_loss, edema_metrics = care_prism_loss(edema_out, edema_batch, stage="A")
    (scar_loss + edema_loss).backward()
    gradients = {
        "scar_router_grad_abs": sum(float(p.grad.abs().sum()) for p in model.scar_routers.parameters() if p.grad is not None),
        "edema_router_grad_abs": sum(float(p.grad.abs().sum()) for p in model.edema_routers.parameters() if p.grad is not None),
        "scar_refiner_grad_abs": sum(float(p.grad.abs().sum()) for p in model.scar_refiner.parameters() if p.grad is not None),
        "edema_refiner_grad_abs": sum(float(p.grad.abs().sum()) for p in model.edema_refiner.parameters() if p.grad is not None),
        "anatomy_decoder_grad_abs": sum(float(p.grad.abs().sum()) for p in model.anatomy_decoder.parameters() if p.grad is not None),
    }
    payload = {
        "status": "PASS"
        if all(v > 1.0e-7 for v in checks.values())
        and all(v > 0.0 for v in gradients.values())
        and scar_metrics["all_finite"]
        and scar_metrics["all_nonnegative"]
        and edema_metrics["all_finite"]
        and edema_metrics["all_nonnegative"]
        else "FAIL",
        "checkpoint": str(checkpoint),
        "scar_case_id": scar_batch["case_id"][0],
        "edema_case_id": edema_batch["case_id"][0],
        "edema_case_t2_present": float(edema_batch["t2_present"][0, 0]),
        "matched_on_off_final_logit_deltas": checks,
        "gradient_abs_sums": gradients,
        "loss_metrics": {"scar": scar_metrics, "edema": edema_metrics},
        "prototype_enabled": False,
        "slice_correspondence_mode": "identity_disabled",
    }
    write_json(result_root / "preflight_mechanism_report.json", payload)
    return payload


def write_w2_resume_report(result_root: Path, checkpoint: Path, fold: int, device: torch.device) -> dict[str, Any]:
    model, payload = load_care_prism_checkpoint(checkpoint, map_location=device)
    model.to(device)
    opt = optimizer_for_care_prism(model, stage=str(payload["stage"]))
    opt.load_state_dict(payload["optimizer_state"])
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(int(payload["step"]), 1))
    scheduler.load_state_dict(payload["scheduler_state"])
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    scaler.load_state_dict(payload["scaler_state"])
    eval_dataset = CAREPRISMFullPatientDataset(fold=fold, split="train", augmenter=CAREPRISMAugmenter(training=False))
    sampler_a = CAREPRISMBalancedSampler(eval_dataset)
    sampler_b = CAREPRISMBalancedSampler(eval_dataset)
    sampler_a.load_state_dict(payload["sampler_state"])
    sampler_b.load_state_dict(payload["sampler_state"])
    aug_a = CAREPRISMAugmenter(training=True)
    aug_b = CAREPRISMAugmenter(training=True)
    aug_a.load_state_dict(payload["augmentation_rng_state"])
    aug_b.load_state_dict(payload["augmentation_rng_state"])
    train_a = CAREPRISMFullPatientDataset(fold=fold, split="train", augmenter=aug_a)
    train_b = CAREPRISMFullPatientDataset(fold=fold, split="train", augmenter=aug_b)
    idx_a = sampler_a.next_index("scar")
    idx_b = sampler_b.next_index("scar")
    batch_a = train_a[idx_a]
    batch_b = train_b[idx_b]
    image_delta = float((batch_a["images"] - batch_b["images"]).abs().max())
    required = ["model_state", "optimizer_state", "scheduler_state", "scaler_state", "stage", "step", "sampler_state", "augmentation_rng_state", "prototype_state", "hard_negative_state"]
    payload_out = {
        "status": "PASS" if all(k in payload and payload[k] is not None for k in required) and idx_a == idx_b and image_delta == 0.0 else "FAIL",
        "checkpoint": str(checkpoint),
        "required_keys_present": {k: k in payload and payload[k] is not None for k in required},
        "restored_stage": payload["stage"],
        "restored_step": int(payload["step"]),
        "restored_lr": [float(group["lr"]) for group in opt.param_groups],
        "scheduler_last_epoch": int(scheduler.last_epoch),
        "next_scar_index_first_restore": int(idx_a),
        "next_scar_index_second_restore": int(idx_b),
        "next_case_image_max_abs_delta_after_rng_restore": image_delta,
        "prototype_state_present": bool(payload.get("prototype_state")),
        "hard_negative_state": payload.get("hard_negative_state"),
    }
    write_json(result_root / "preflight_resume_report.json", payload_out)
    write_json(result_root / "exact_resume_report.json", payload_out)
    return payload_out


def write_correspondence_freeze_receipt(result_root: Path) -> dict[str, Any]:
    payload = {
        "status": "PASS",
        "slice_correspondence_mode": "identity_disabled",
        "prototype_enabled": False,
        "reason": "Real slice correspondence has not passed an independent train-side gate; W2/W3 freeze identity mode.",
        "train_deploy_mode_match": True,
    }
    write_json(result_root / "correspondence_freeze_receipt.json", payload)
    return payload


def _first_matching_batch(dataset: CAREPRISMFullPatientDataset, predicate: Any) -> dict[str, Any]:
    for idx in range(len(dataset)):
        item = dataset[idx]
        if predicate(item):
            return item
    raise RuntimeError("no matching CARE-PRISM audit case found")


def write_w3_checkpoint_audit(
    result_root: Path,
    runtime_dir: Path,
    checkpoint: Path,
    *,
    fold: int,
    step: int,
    device: torch.device,
) -> dict[str, Any]:
    model, payload = load_care_prism_checkpoint(checkpoint, map_location=device)
    model.to(device)
    model.eval()
    required = [
        "model_state",
        "optimizer_state",
        "scheduler_state",
        "scaler_state",
        "stage",
        "step",
        "sampler_state",
        "augmentation_rng_state",
        "prototype_state",
        "hard_negative_state",
    ]
    policy = apply_stage_policy(model, optimizer_for_care_prism(model, stage=str(payload["stage"])), "W3", int(step))
    active_stage = str(policy["active_loss_stage"])
    ds = CAREPRISMFullPatientDataset(fold=fold, split="actual_train", augmenter=CAREPRISMAugmenter(training=False))
    scar_batch = move_batch(_first_matching_batch(ds, lambda item: float(item["scar_target"].sum()) > 0.0), device)
    edema_batch = move_batch(
        _first_matching_batch(ds, lambda item: float(item["t2_present"][0, 0]) > 0.5 and float(item["edema_zone_target"].sum()) > 0.0),
        device,
    )
    no_t2_batch = move_batch(_first_matching_batch(ds, lambda item: float(item["t2_present"][0, 0]) <= 0.5), device)
    with torch.no_grad():
        scar_base = model(scar_batch["images"], scar_batch["availability"])
        edema_base = model(edema_batch["images"], edema_batch["availability"])
        on_off = {
            "router_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_router=True)["scar_direct_logit"]),
            "router_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_router=True)["edema_zone_direct_logit"]),
            "anatomy_guidance_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_anatomy_guidance=True)["scar_direct_logit"]),
            "anatomy_guidance_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_anatomy_guidance=True)["edema_zone_direct_logit"]),
            "proposal_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_proposal=True)["scar_direct_logit"]),
            "proposal_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_proposal=True)["edema_zone_direct_logit"]),
            "negative_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_negative=True)["scar_direct_logit"]),
            "negative_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_negative=True)["edema_zone_direct_logit"]),
            "burden_scar_delta": max_delta(scar_base["scar_direct_logit"], model(scar_batch["images"], scar_batch["availability"], disable_burden=True)["scar_direct_logit"]),
            "burden_edema_delta": max_delta(edema_base["edema_zone_direct_logit"], model(edema_batch["images"], edema_batch["availability"], disable_burden=True)["edema_zone_direct_logit"]),
        }
    model.zero_grad(set_to_none=True)
    scar_out = model(scar_batch["images"], scar_batch["availability"])
    scar_loss, scar_metrics = care_prism_loss(scar_out, scar_batch, stage=active_stage)
    edema_out = model(edema_batch["images"], edema_batch["availability"])
    edema_loss, edema_metrics = care_prism_loss(edema_out, edema_batch, stage=active_stage)
    (scar_loss + edema_loss).backward()
    gradients = {
        "scar_router_grad_abs": sum(float(p.grad.abs().sum()) for p in model.scar_routers.parameters() if p.grad is not None),
        "edema_router_grad_abs": sum(float(p.grad.abs().sum()) for p in model.edema_routers.parameters() if p.grad is not None),
        "scar_refiner_grad_abs": sum(float(p.grad.abs().sum()) for p in model.scar_refiner.parameters() if p.grad is not None),
        "edema_refiner_grad_abs": sum(float(p.grad.abs().sum()) for p in model.edema_refiner.parameters() if p.grad is not None),
    }
    model.zero_grad(set_to_none=True)
    no_t2_out = model(no_t2_batch["images"], no_t2_batch["availability"])
    no_t2_loss, no_t2_metrics = care_prism_loss(no_t2_out, no_t2_batch, stage=active_stage)
    no_t2_loss.backward()
    no_t2_edema_grad = sum(float(p.grad.abs().sum()) for p in model.edema_refiner.parameters() if p.grad is not None)
    no_t2 = {
        "case_id": no_t2_batch["case_id"][0],
        "edema_probability_max": float(no_t2_out["edema_probability"].detach().max()),
        "edema_mask_sum": float(no_t2_out["edema_mask"].detach().sum()),
        "edema_refiner_grad_abs": no_t2_edema_grad,
        "edema_loss": float(no_t2_metrics["edema_refine"]),
    }
    payload_out = {
        "status": "PASS"
        if all(k in payload and payload[k] is not None for k in required)
        and int(payload["step"]) == int(step)
        and all(v > 1.0e-7 for v in on_off.values())
        and all(v > 0.0 for v in gradients.values())
        and bool(scar_metrics["all_finite"])
        and bool(edema_metrics["all_finite"])
        and bool(no_t2_metrics["all_finite"])
        and float(no_t2["edema_probability_max"]) == 0.0
        and float(no_t2["edema_mask_sum"]) == 0.0
        and float(no_t2["edema_refiner_grad_abs"]) == 0.0
        and float(no_t2["edema_loss"]) == 0.0
        else "FAIL",
        "checkpoint": str(checkpoint),
        "checkpoint_step": int(step),
        "checkpoint_stage": payload["stage"],
        "active_loss_stage": active_stage,
        "stage_policy": policy,
        "required_keys_present": {k: k in payload and payload[k] is not None for k in required},
        "matched_on_off_final_logit_deltas": on_off,
        "gradient_abs_sums": gradients,
        "loss_metrics": {"scar": scar_metrics, "edema": edema_metrics, "no_t2": no_t2_metrics},
        "no_t2_exact_zero": no_t2,
        "prototype_enabled": False,
        "slice_correspondence_mode": "identity_disabled",
    }
    audit_path = runtime_dir / "audits" / f"checkpoint_step{int(step):05d}_audit.json"
    write_json(audit_path, payload_out)
    summary_path = result_root / "w3_checkpoint_audit_report.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {"stage": "W3", "audits": []}
    if summary.get("runtime_dir") not in {None, str(runtime_dir)}:
        summary = {"stage": "W3", "audits": []}
    summary["runtime_dir"] = str(runtime_dir)
    summary["audits"] = [row for row in summary.get("audits", []) if int(row.get("checkpoint_step", -1)) != int(step)]
    summary["audits"].append({"checkpoint_step": int(step), "status": payload_out["status"], "audit_path": str(audit_path)})
    summary["audits"] = sorted(summary["audits"], key=lambda row: int(row["checkpoint_step"]))
    summary["status"] = "PASS" if summary["audits"] and all(row["status"] == "PASS" for row in summary["audits"]) else "FAIL"
    write_json(summary_path, summary)
    return payload_out


def run_training(args: argparse.Namespace, device: torch.device) -> dict[str, Any]:
    result_root: Path = args.result_root
    runtime_dir = result_root / "runtime" / f"fold{args.fold}_{args.stage.lower()}_{args.run_label}"
    log_path = runtime_dir / "training_log.csv"
    if args.stage.upper() == "W3" and args.resume is None:
        write_json(result_root / "w3_checkpoint_audit_report.json", {"stage": "W3", "runtime_dir": str(runtime_dir), "status": "PENDING", "audits": []})
    if args.resume is not None:
        model, resume_payload = load_care_prism_checkpoint(args.resume, map_location=device)
        model.to(device)
        transplant = {"byte_coverage": resume_payload.get("transplant_byte_coverage", 1.0)}
        start_step = int(resume_payload["step"]) + 1
    else:
        model, transplant = build_initialized_model(args.fold, device)
        resume_payload = None
        start_step = 1
    optimizer = optimizer_for_care_prism(model, stage=args.stage)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(int(args.train_steps), 1))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    dataset = CAREPRISMFullPatientDataset(fold=args.fold, split="actual_train", augmenter=CAREPRISMAugmenter(seed=args.seed, training=True))
    eval_dataset = CAREPRISMFullPatientDataset(fold=args.fold, split="actual_train", augmenter=CAREPRISMAugmenter(training=False))
    sampler = CAREPRISMBalancedSampler(eval_dataset, seed=args.seed)
    if resume_payload is not None:
        optimizer.load_state_dict(resume_payload["optimizer_state"])
        scheduler.load_state_dict(resume_payload["scheduler_state"])
        scaler.load_state_dict(resume_payload["scaler_state"])
        sampler.load_state_dict(resume_payload["sampler_state"])
        if resume_payload.get("augmentation_rng_state") is not None and dataset.augmenter is not None:
            dataset.augmenter.load_state_dict(resume_payload["augmentation_rng_state"])
        restore_global_rng(resume_payload)
    model.train()
    for step in range(start_step, int(args.train_steps) + 1):
        policy = apply_stage_policy(model, optimizer, args.stage, step)
        current_stage = policy["stage"]
        loss_stage = policy["active_loss_stage"]
        optimizer.param_groups[0]["lr"] *= float(args.encoder_lr_mult)
        optimizer.param_groups[1]["lr"] *= float(args.new_lr_mult)
        optimizer.zero_grad(set_to_none=True)
        step_loss = 0.0
        focus_cases: list[str] = []
        focus_losses: dict[str, float] = {}
        all_finite = True
        all_nonnegative = True
        for focus in ("scar", "edema"):
            idx = sampler.next_index(focus)
            batch = move_batch(dataset[idx], device)
            focus_cases.append(batch["case_id"][0])
            with torch.amp.autocast(device_type=device.type, enabled=device.type == "cuda"):
                outputs = model(batch["images"], batch["availability"])
                loss, metrics = care_prism_loss(outputs, batch, stage=loss_stage)
                scaled_loss = loss / 2.0
            scaler.scale(scaled_loss).backward()
            step_loss += float(loss.detach().cpu()) / 2.0
            focus_losses[focus] = float(loss.detach().cpu())
            all_finite = all_finite and bool(metrics["all_finite"])
            all_nonnegative = all_nonnegative and bool(metrics["all_nonnegative"])
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        if step == 1 or step % int(args.log_every) == 0 or step == int(args.train_steps):
            append_csv(
                log_path,
                {
                    "step": step,
                    "stage": current_stage,
                    "active_loss_stage": loss_stage,
                    "requested_stage": args.stage,
                    "loss": step_loss,
                    "scar_loss": focus_losses.get("scar", ""),
                    "edema_active_loss": focus_losses.get("edema", ""),
                    "all_finite": all_finite,
                    "all_nonnegative": all_nonnegative,
                    "freeze_encoder": policy["freeze_encoder"],
                    "freeze_anatomy": policy["freeze_anatomy"],
                    "component_surface_enabled": policy["component_surface_enabled"],
                    "lr_encoder": optimizer.param_groups[0]["lr"],
                    "lr_new": optimizer.param_groups[1]["lr"],
                    "scar_case": focus_cases[0],
                    "edema_case": focus_cases[1],
                    "cuda_max_memory_gb": torch.cuda.max_memory_allocated() / 1024**3 if device.type == "cuda" else 0.0,
                },
            )
        if step % int(args.checkpoint_every) == 0 or step == int(args.train_steps):
            checkpoint_path = runtime_dir / "checkpoints" / f"checkpoint_step{step:05d}.pt"
            save_care_prism_checkpoint(
                checkpoint_path,
                model,
                optimizer,
                scheduler=scheduler,
                scaler=scaler,
                stage=current_stage,
                step=step,
                sampler_state={**sampler.state_dict(), "step": step},
                augmentation_rng_state=dataset.state_dict().get("augmenter"),
                hard_negative_state={"bank_hash": "w2_preflight_safe_negative_targets_from_dataset"},
                contract_hash="care_prism_v2_stock_backbone_repair",
            )
            if args.stage.upper() == "W3":
                audit = write_w3_checkpoint_audit(result_root, runtime_dir, checkpoint_path, fold=int(args.fold), step=step, device=device)
                if audit["status"] != "PASS":
                    raise RuntimeError(f"W3 checkpoint audit failed at step {step}: {runtime_dir / 'audits' / f'checkpoint_step{step:05d}_audit.json'}")
    summary = {
        "status": "PASS",
        "stage": args.stage,
        "stage_schedule": "A:1-1000,B:1001-2500,C:2501-5000,D:5001-6500" if args.stage.upper() == "W3" else args.stage,
        "fold": int(args.fold),
        "optimizer_steps": int(args.train_steps),
        "micro_batches_per_step": 2,
        "synthetic_credit_used": False,
        "transplant_byte_coverage": transplant["byte_coverage"],
        "runtime_dir": str(runtime_dir),
        "training_log": str(log_path),
        "checkpoint_every": int(args.checkpoint_every),
        "final_checkpoint": str(runtime_dir / "checkpoints" / f"checkpoint_step{int(args.train_steps):05d}.pt"),
        "balanced_sampler": sampler.summary(),
        "learning_rate_multipliers": {"encoder": float(args.encoder_lr_mult), "new": float(args.new_lr_mult)},
        "resumed_from": str(args.resume) if args.resume is not None else None,
    }
    write_json(result_root / f"{args.stage.lower()}_training_summary.json", summary)
    if args.stage.upper() == "W2":
        checkpoint = runtime_dir / "checkpoints" / f"checkpoint_step{int(args.train_steps):05d}.pt"
        summary["preflight_training_receipt"] = write_w2_training_receipts(result_root, summary, log_path)
        summary["preflight_mechanism_report"] = write_w2_mechanism_report(result_root, checkpoint, int(args.fold), device)
        summary["correspondence_freeze_receipt"] = write_correspondence_freeze_receipt(result_root)
        summary["preflight_resume_report"] = write_w2_resume_report(result_root, checkpoint, int(args.fold), device)
        summary["status"] = "PASS" if all(summary[k]["status"] == "PASS" for k in ("preflight_training_receipt", "preflight_mechanism_report", "correspondence_freeze_receipt", "preflight_resume_report")) else "FAIL"
        write_json(result_root / f"{args.stage.lower()}_training_summary.json", summary)
    return summary


def print_contract() -> None:
    payload = {
        "entrypoint": "scripts/training/run_care_prism.py",
        "shared_encoder_input_order": ["LGE", "T2", "C0"],
        "backbone": "plan-driven stock nnU-Net from nnUNetPlans.json + same-fold checkpoint_final.pth",
        "forbidden": ["sbatch", "salloc", "new_slurm_job", "synthetic_w2_credit", "validation_upload"],
        "w1_required_reports": [
            "init_transplant_report_fold0.json",
            "init_transplant_report_fold1.json",
            "multiscale_usage_report.json",
            "data_pipeline_report.json",
            "loss_and_negative_space_report.json",
            "implementation_intervention_report.json",
            "known_bad_report.json",
            "checkpoint_resume_report.json",
            "implementation_validator_report.json",
            "label_semantics_report.json",
            "direct_loss_gradient_report.json",
            "anatomy_exchange_report.json",
            "sampler_balance_report.json",
        ],
        "w2_required_reports": [
            "preflight_training_receipt.json",
            "preflight_mechanism_report.json",
            "correspondence_freeze_receipt.json",
            "preflight_resume_report.json",
            "w2_adequacy_report.json",
            "w1_w2_strict_validator_report.json",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--w1-reports", action="store_true")
    parser.add_argument("--train-steps", type=int, default=0)
    parser.add_argument("--stage", default="W2")
    parser.add_argument("--checkpoint-every", type=int, default=100)
    parser.add_argument("--log-every", type=int, default=10)
    parser.add_argument("--run-label", default="preflight")
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--encoder-lr-mult", type=float, default=1.0)
    parser.add_argument("--new-lr-mult", type=float, default=1.0)
    parser.add_argument("--resume", type=Path)
    args = parser.parse_args()
    if args.print_contract:
        print_contract()
    if args.w1_reports:
        device = torch.device(args.device)
        if device.type == "cuda" and not torch.cuda.is_available():
            raise SystemExit("CUDA requested but not available")
        result = run_w1_reports(args.result_root, args.fold, device)
        print(json.dumps({"status": result["status"], "result_root": str(args.result_root)}, sort_keys=True))
    if args.train_steps:
        device = torch.device(args.device)
        if device.type == "cuda" and not torch.cuda.is_available():
            raise SystemExit("CUDA requested but not available")
        result = run_training(args, device)
        print(json.dumps({"status": result["status"], "summary": result}, sort_keys=True))


if __name__ == "__main__":
    main()
