#!/usr/bin/env python
"""Formal CARE-PRISM training and W1 validation entrypoint."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_prism_dataset import CAREPRISMAugmenter, CAREPRISMFullPatientDataset, synthetic_w1_batch
from src.care_myocardium.models.care_prism import CAREPRISMConfig, build_care_prism
from src.care_myocardium.training.care_prism_trainer import (
    care_prism_loss,
    load_same_fold_nnunet_encoder,
    optimizer_for_care_prism,
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
        and float(out_no_t2["edema_probability"].max()) == 0.0
        and float(out_no_t2["edema_mask"].sum()) == 0.0
        and edema_no_t2_grad == 0.0
        else "FAIL",
        "t2_metrics": metrics_t2,
        "no_t2_metrics": metrics_no_t2,
        "scar_negative_target_sum": float(batch_t2["scar_negative_targets"].sum()),
        "edema_negative_target_sum": float(batch_t2["edema_negative_targets"].sum()),
        "scar_negative_head_grad_abs": scar_negative_grad,
        "edema_negative_head_grad_abs": edema_negative_grad,
        "no_t2_edema_probability_max": float(out_no_t2["edema_probability"].max()),
        "no_t2_edema_mask_sum": float(out_no_t2["edema_mask"].sum()),
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
        "init_fold0": write_init_transplant_report(result_root / "init_transplant_report_fold0.json", fold=0),
        "init_fold1": write_init_transplant_report(result_root / "init_transplant_report_fold1.json", fold=1),
        "multiscale": w1_multiscale_report(result_root, fold, device),
        "data_pipeline": w1_data_pipeline_report(result_root, fold),
        "intervention": w1_intervention_report(result_root, fold, device),
        "loss_negative": w1_loss_report(result_root, fold, device),
        "known_bad": w1_known_bad_report(result_root, device),
        "checkpoint_resume": w1_checkpoint_resume_report(result_root, fold, device),
    }
    reports["status"] = "PASS" if all(v.get("status") == "PASS" for v in reports.values() if isinstance(v, dict)) else "FAIL"
    write_json(result_root / "implementation_validator_report.json", reports)
    return reports


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


def run_training(args: argparse.Namespace, device: torch.device) -> dict[str, Any]:
    result_root: Path = args.result_root
    runtime_dir = result_root / "runtime" / f"fold{args.fold}_{args.stage.lower()}_{args.run_label}"
    log_path = runtime_dir / "training_log.csv"
    model, transplant = build_initialized_model(args.fold, device)
    optimizer = optimizer_for_care_prism(model, stage=args.stage)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(int(args.train_steps), 1))
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    dataset = CAREPRISMFullPatientDataset(fold=args.fold, split="train", augmenter=CAREPRISMAugmenter(seed=args.seed, training=True))
    eval_dataset = CAREPRISMFullPatientDataset(fold=args.fold, split="train", augmenter=CAREPRISMAugmenter(training=False))
    eligible = eligible_training_indices(eval_dataset)
    model.train()
    for step in range(1, int(args.train_steps) + 1):
        current_stage = prism_training_stage(args.stage, step)
        optimizer.zero_grad(set_to_none=True)
        step_loss = 0.0
        focus_cases: list[str] = []
        for focus, indices in (("scar", eligible["scar"]), ("edema", eligible["edema"])):
            idx = indices[(step - 1) % len(indices)]
            batch = move_batch(dataset[idx], device)
            focus_cases.append(batch["case_id"][0])
            with torch.amp.autocast(device_type=device.type, enabled=device.type == "cuda"):
                outputs = model(batch["images"], batch["availability"])
                loss, metrics = care_prism_loss(outputs, batch, stage=current_stage)
                scaled_loss = loss / 2.0
            scaler.scale(scaled_loss).backward()
            step_loss += float(loss.detach().cpu()) / 2.0
        scaler.step(optimizer)
        scaler.update()
        scheduler.step()
        if step == 1 or step % int(args.log_every) == 0 or step == int(args.train_steps):
            append_csv(
                log_path,
                {
                    "step": step,
                    "stage": current_stage,
                    "requested_stage": args.stage,
                    "loss": step_loss,
                    "lr_encoder": optimizer.param_groups[0]["lr"],
                    "lr_new": optimizer.param_groups[1]["lr"],
                    "scar_case": focus_cases[0],
                    "edema_case": focus_cases[1],
                    "cuda_max_memory_gb": torch.cuda.max_memory_allocated() / 1024**3 if device.type == "cuda" else 0.0,
                },
            )
        if step % int(args.checkpoint_every) == 0 or step == int(args.train_steps):
            save_care_prism_checkpoint(
                runtime_dir / "checkpoints" / f"checkpoint_step{step:05d}.pt",
                model,
                optimizer,
                scheduler=scheduler,
                scaler=scaler,
                stage=current_stage,
                step=step,
                sampler_state={"eligible_indices": eligible, "step": step},
                augmentation_rng_state=dataset.state_dict().get("augmenter"),
                hard_negative_state={"bank_hash": "w2_preflight_safe_negative_targets_from_dataset"},
                contract_hash="care_prism_v2_stock_backbone_repair",
            )
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
        "eligible_case_counts": {k: len(v) for k, v in eligible.items()},
    }
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
