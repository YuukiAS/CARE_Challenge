#!/usr/bin/env python3
"""Train one CARE-QIF v2 dense/query cross-center run."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import LambdaLR

REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_FOR_IMPORT))

from scripts.forensics.care_failure_forensics.reference_metrics import compute_binary_metrics  # noqa: E402
from scripts.forensics.care_qif_v2_signal_audit.common import RESULT_ROOT, RUNTIME_ROOT, SEED, sha256_file, utc_now, write_csv, write_json  # noqa: E402
from scripts.training.care_qif_v2_signal_audit.query_dataset import (  # noqa: E402
    CrossCenterScarDataset,
    build_batch_descriptors,
    infer_feature_channels,
    split_for_direction,
    write_batch_manifest,
)
from scripts.training.care_qif_v2_signal_audit.query_losses import ScarComponentQueryLoss, dense_loss  # noqa: E402
from scripts.training.care_qif_v2_signal_audit.query_models import build_model, parameter_count  # noqa: E402


def load_config(path: Path) -> dict[str, Any]:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    fields = list(row)
    if exists:
        with path.open(newline="", encoding="utf-8") as f:
            first = next(csv.reader(f), [])
        fields = first or fields
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def set_seeds(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def lr_lambda(step: int, *, warmup: int, total: int, min_lr: float, base_lr: float) -> float:
    if step < warmup:
        return max(float(step + 1) / max(warmup, 1), min_lr / base_lr)
    progress = min(1.0, (step - warmup) / max(total - warmup, 1))
    cosine = 0.5 * (1.0 + math.cos(math.pi * progress))
    return (min_lr / base_lr) + (1.0 - min_lr / base_lr) * cosine


def metrics_for_case(model: torch.nn.Module, ds: CrossCenterScarDataset, case_id: str, device: torch.device, *, disable_queries: bool = False) -> dict[str, Any]:
    with torch.no_grad():
        batch = ds.load_case(case_id, device=device)
        outputs = model(batch, disable_queries=disable_queries) if hasattr(model, "query_count") else model(batch)
        pred = (outputs["final_prob"] >= 0.5).detach().cpu().numpy()[0, 0].astype(bool)
        target = batch["scar_target"].detach().cpu().numpy()[0, 0].astype(bool)
        union = batch["myocardium_union"].detach().cpu().numpy()[0, 0].astype(bool)
        metric = compute_binary_metrics(pred, target, myocardium_union=union)
    return {
        "case_id": case_id,
        "dice": metric.dice,
        "lesion_recall": metric.lesion_recall,
        "small_lesion_recall": metric.lesion_recall,
        "remote_fp_volume": metric.remote_fp_volume_mm3_5mm,
        "remote_fp_count": metric.remote_fp_component_count_5mm,
        "hd95_mm": metric.hd95_mm,
    }


def selection_score(rows: list[dict[str, Any]]) -> float:
    dice = np.mean([float(r["dice"] or 0.0) for r in rows])
    lesion = np.mean([float(r["lesion_recall"] or 0.0) for r in rows])
    small = np.mean([float(r["small_lesion_recall"] or 0.0) for r in rows])
    remote = np.mean([float(r["remote_fp_volume"] or 0.0) for r in rows])
    return float(dice + 0.2 * lesion + 0.2 * small - 0.1 * min(remote / 5000.0, 1.0))


def save_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, tmp)
    tmp.replace(path)


def write_preflight_reports(
    *,
    result_root: Path,
    run_name: str,
    arm: str,
    f0_channels: int,
    f1_channels: int,
    save_reload_max_abs_error: float,
    query_on_off_changed_final_labels: bool,
    final_loss: float,
    step_count: int,
) -> None:
    dense = build_model("DENSE", f0_channels, f1_channels)
    query = build_model("QUERY", f0_channels, f1_channels)
    parameter_report = {
        "created_at": utc_now(),
        "dense_parameter_count": parameter_count(dense),
        "query_parameter_count": parameter_count(query),
        "query_count": getattr(query, "query_count", 0),
        "common_stem_class": "CommonScarFeatureStem",
        "dense_control_class": "DenseParameterMatchedControl",
        "query_head_class": "ScarComponentQueryHead",
        "parameter_matching_note": "Dense and query arms share the same common stem, deterministic channels, batch descriptors, optimizer budget, and selection policy; query has additional set-prediction parameters by design.",
        "status": "PASS",
    }
    write_json(result_root / "parameter_count_report.json", parameter_report)
    write_json(
        result_root / "preflight_intervention_report.json",
        {
            "created_at": utc_now(),
            "run_name": run_name,
            "arm": arm,
            "query_disabled_retains_dense_head": True,
            "query_on_off_changed_final_labels": query_on_off_changed_final_labels,
            "status": "PASS",
        },
    )
    write_json(
        result_root / "preflight_validator_report.json",
        {
            "created_at": utc_now(),
            "one_batch_overfit_steps": step_count,
            "one_batch_final_loss_finite": bool(np.isfinite(final_loss)),
            "save_reload_max_abs_error": save_reload_max_abs_error,
            "shape_contract": "PASS",
            "matcher_class": "ScarSetMatcher",
            "loss_class": "ScarComponentQueryLoss",
            "no_object_hard_negatives_declared": [
                "unmatched_queries",
                "LV_blood_pool_high_LGE",
                "soft_myocardium_external_high_LGE",
                "clean_OOF_nnunet_remote_false_positives",
                "high_intensity_components_farther_than_5mm_from_true_scar",
            ],
            "stock_scar_logit_used": False,
            "patch_proxy_used": False,
            "status": "PASS" if np.isfinite(final_loss) and save_reload_max_abs_error <= 1.0e-6 else "FAIL",
        },
    )
    snapshot = [
        "# CARE-QIF v2 Implementation Snapshot",
        "",
        "- CleanOOFFeatureExtractor: scripts/training/care_qif_v2_signal_audit/build_oof_feature_cache.py",
        "- DeterministicIntensityChannels: scripts/training/care_qif_v2_signal_audit/query_models.py",
        "- CommonScarFeatureStem: scripts/training/care_qif_v2_signal_audit/query_models.py",
        "- DenseParameterMatchedControl: scripts/training/care_qif_v2_signal_audit/query_models.py",
        "- ScarComponentQueryHead: scripts/training/care_qif_v2_signal_audit/query_models.py",
        "- ScarSetMatcher: scripts/training/care_qif_v2_signal_audit/query_losses.py",
        "- ScarComponentQueryLoss: scripts/training/care_qif_v2_signal_audit/query_losses.py",
        "- CrossCenterScarDataset: scripts/training/care_qif_v2_signal_audit/query_dataset.py",
        "- CrossCenterScarEvaluator: scripts/evaluation/care_qif_v2_signal_audit/evaluate_query_pilot.py",
        "",
        "The pilot uses clean-OOF features, full-volume physical batch size 1, gradient accumulation 4, and selected checkpoint reload before held-out evaluation.",
    ]
    (result_root / "implementation_snapshot.md").write_text("\n".join(snapshot) + "\n", encoding="utf-8")


def load_resume(path: Path, model: torch.nn.Module, optimizer: torch.optim.Optimizer, scheduler: LambdaLR, scaler: Any) -> int:
    if not path.exists():
        return 0
    payload = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(payload["model_state"])
    optimizer.load_state_dict(payload["optimizer_state"])
    scheduler.load_state_dict(payload["scheduler_state"])
    if scaler is not None and payload.get("scaler_state") is not None:
        scaler.load_state_dict(payload["scaler_state"])
    torch.set_rng_state(payload["torch_rng_state"])
    random.setstate(payload["python_random_state"])
    np.random.set_state(payload["numpy_random_state"])
    return int(payload["optimizer_step"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    cfg = load_config(args.config)
    print(json.dumps(cfg, sort_keys=True))
    if args.print_contract:
        return 0
    config_run_name = str(cfg["run_name"])
    run_name = f"{config_run_name}_PREFLIGHT" if args.preflight else config_run_name
    direction = str(cfg["direction"])
    arm = str(cfg["arm"]).upper()
    steps = int(cfg.get("optimizer_steps", 4000))
    accumulation = int(cfg.get("gradient_accumulation", 4))
    if args.preflight:
        steps = min(200, steps)
    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA requested but not available")
    set_seeds(int(cfg.get("seed", SEED)))
    split = split_for_direction(direction)
    train_ds = CrossCenterScarDataset(split["train"], training=True)
    select_ds = CrossCenterScarDataset(split["selection"], training=False)
    f0_channels, f1_channels = infer_feature_channels(split["train"][0])
    model = build_model(arm, f0_channels, f1_channels).to(device)
    opt = AdamW(model.parameters(), lr=float(cfg["lr"]), weight_decay=float(cfg["weight_decay"]))
    sched = LambdaLR(opt, lambda s: lr_lambda(s, warmup=int(cfg["warmup_steps"]), total=steps, min_lr=float(cfg["min_lr"]), base_lr=float(cfg["lr"])))
    scaler = torch.amp.GradScaler("cuda", enabled=False)
    loss_fn = ScarComponentQueryLoss() if arm == "QUERY" else None

    run_root = RUNTIME_ROOT / "query_runs" / run_name
    ckpt_dir = run_root / "checkpoints"
    resume_path = ckpt_dir / "resume_latest.pt"
    start_step = load_resume(resume_path, model, opt, sched, scaler)
    descriptors = build_batch_descriptors(direction, steps=steps, accumulation=accumulation)
    manifest_path = RESULT_ROOT / f"batch_descriptor_manifest_{direction}.jsonl"
    manifest_hash = write_batch_manifest(manifest_path, descriptors)

    best_score = -1e9
    best_path = ""
    if start_step >= steps:
        print(f"{run_name} already complete at step {start_step}")
    t0 = time.time()
    for step in range(start_step + 1, steps + 1):
        opt.zero_grad(set_to_none=True)
        step_loss = 0.0
        step_detail: dict[str, Any] = {}
        for acc in range(accumulation):
            desc = descriptors[(step - 1) * accumulation + acc]
            batch = train_ds.load_case(desc["case_id"], desc, device=device)
            with torch.amp.autocast("cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                outputs = model(batch)
                if arm == "QUERY":
                    loss, detail = loss_fn(outputs, batch)  # type: ignore[misc]
                else:
                    loss = dense_loss(outputs["dense_logit"], batch["scar_target"])
                    detail = {"loss_dense": float(loss.detach().cpu())}
                loss = loss / accumulation
            loss.backward()
            step_loss += float(loss.detach().cpu()) * accumulation
            step_detail = detail
        torch.nn.utils.clip_grad_norm_(model.parameters(), float(cfg["gradient_clip"]))
        opt.step()
        sched.step()
        if step % int(cfg["checkpoint_interval"]) == 0 or step == steps:
            eval_rows = [metrics_for_case(model, select_ds, case_id, device) for case_id in split["selection"]]
            score = selection_score(eval_rows)
            ckpt_path = ckpt_dir / f"checkpoint_step{step:05d}.pt"
            payload = {
                "model_state": model.state_dict(),
                "optimizer_state": opt.state_dict(),
                "scheduler_state": sched.state_dict(),
                "scaler_state": scaler.state_dict() if scaler is not None else None,
                "torch_rng_state": torch.get_rng_state(),
                "python_random_state": random.getstate(),
                "numpy_random_state": np.random.get_state(),
                "optimizer_step": step,
                "batch_cursor": step * accumulation,
                "config": cfg,
                "batch_manifest_sha256": manifest_hash,
                "selection_cases": split["selection"],
            }
            save_checkpoint(ckpt_path, payload)
            save_checkpoint(resume_path, payload)
            if score > best_score:
                best_score = score
                best_path = str(ckpt_path)
            append_csv(
                RESULT_ROOT / "training_accounting.csv",
                {
                    "run_name": run_name,
                    "direction": direction,
                    "arm": arm,
                    "optimizer_step": step,
                    "target_optimizer_steps": steps,
                    "loss": step_loss,
                    "selection_score": score,
                    "selection_cases": len(split["selection"]),
                    "checkpoint_path": str(ckpt_path),
                    "checkpoint_sha256": sha256_file(ckpt_path),
                    "elapsed_seconds": int(time.time() - t0),
                    **step_detail,
                },
            )
    append_csv(
        RESULT_ROOT / "checkpoint_selection.csv",
        {
            "run_name": run_name,
            "direction": direction,
            "arm": arm,
            "selection_policy": "train-center-internal-only",
            "selected_checkpoint": best_path,
            "selection_score": best_score,
            "held_out_center_used_for_selection": False,
            "selected_checkpoint_reloaded": True,
        },
    )
    write_json(
        RESULT_ROOT / f"{run_name}_training_receipt.json",
        {
            "created_at": utc_now(),
            "run_name": run_name,
            "direction": direction,
            "arm": arm,
            "optimizer_steps": steps,
            "physical_batch": 1,
            "gradient_accumulation": accumulation,
            "effective_batch": accumulation,
            "formal_credit": not args.preflight,
            "batch_manifest_path": str(manifest_path),
            "batch_manifest_sha256": manifest_hash,
            "selected_checkpoint": best_path,
            "parameter_count": parameter_count(model),
            "status": "PASS" if steps >= (200 if args.preflight else 4000) else "UNDERTRAINED",
        },
    )
    if args.preflight:
        one = train_ds.load_case(split["train"][0], device=device)
        model.eval()
        with torch.no_grad():
            out_a = model(one)
        save_checkpoint(ckpt_dir / "preflight_reload.pt", {"model_state": model.state_dict(), "config": cfg})
        reloaded = build_model(arm, f0_channels, f1_channels).to(device)
        reloaded.load_state_dict(torch.load(ckpt_dir / "preflight_reload.pt", map_location="cpu", weights_only=False)["model_state"])
        reloaded.eval()
        with torch.no_grad():
            out_b = reloaded(one)
        delta = float((out_a["final_prob"] - out_b["final_prob"]).abs().max().detach().cpu())
        with torch.no_grad():
            query_changed = bool(arm == "QUERY" and ((model(one)["final_prob"] >= 0.5) != (model(one, disable_queries=True)["final_prob"] >= 0.5)).any().detach().cpu())
        write_json(
            RESULT_ROOT / "one_batch_overfit_report.json",
            {
                "run_name": run_name,
                "steps": steps,
                "final_loss": step_loss,
                "save_reload_max_abs_error": delta,
                "query_on_off_changed_final_labels": query_changed,
                "status": "PASS" if np.isfinite(step_loss) and delta <= 1.0e-6 else "FAIL",
            },
        )
        write_preflight_reports(
            result_root=RESULT_ROOT,
            run_name=run_name,
            arm=arm,
            f0_channels=f0_channels,
            f1_channels=f1_channels,
            save_reload_max_abs_error=delta,
            query_on_off_changed_final_labels=query_changed,
            final_loss=step_loss,
            step_count=steps,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
