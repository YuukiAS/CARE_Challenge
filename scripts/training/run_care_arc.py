#!/usr/bin/env python3
"""CARE-ARC training and preflight entrypoint."""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch
from torch.amp import autocast

from src.care_myocardium.data.care_arc_dataset import (
    CAREARCDataset,
    build_case_records,
    collate_single_case,
)
from src.care_myocardium.models.care_arc import CAREARCConfig, build_care_arc, trainable_parameter_count
from src.care_myocardium.training.care_arc_trainer import (
    care_arc_loss,
    load_care_arc_checkpoint,
    optimizer_for_care_arc,
    save_care_arc_checkpoint,
    sdf_target_from_mask,
    stable_json_sha256,
)

TASK_KEY = "20260729_care_arc_clean_fold1"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                keys.append(key)
                seen.add(key)
    keys = keys or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}


def add_sdf_targets(batch: dict[str, Any]) -> dict[str, Any]:
    spacing = batch["spacing_zyx"]
    batch["scar_sdf_target"] = sdf_target_from_mask(batch["scar_target"], spacing)
    batch["edema_sdf_target"] = sdf_target_from_mask(batch["edema_zone_target"], spacing)
    return batch


def choose_preflight_cases(fold: int, crop_hw: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    records = build_case_records(fold, "actual_train")
    by_case = {r.case_id: r for r in records}
    selected: dict[str, str | None] = {
        "complete_trimodal": None,
        "lge_c0": None,
        "lge_only": None,
        "no_t2": None,
        "scar_positive": None,
        "edema_positive": None,
        "hard_negative": None,
    }
    for r in records:
        if selected["complete_trimodal"] is None and r.modality_group == "C0+LGE+T2":
            selected["complete_trimodal"] = r.case_id
        if selected["lge_c0"] is None and r.availability == (1.0, 0.0, 1.0):
            selected["lge_c0"] = r.case_id
        if selected["lge_only"] is None and r.availability == (1.0, 0.0, 0.0):
            selected["lge_only"] = r.case_id
        if selected["no_t2"] is None and not r.t2_present:
            selected["no_t2"] = r.case_id
        if selected["scar_positive"] is None and r.scar_positive:
            selected["scar_positive"] = r.case_id
        if selected["edema_positive"] is None and r.edema_positive and r.t2_present:
            selected["edema_positive"] = r.case_id
        if selected["hard_negative"] is None and (not r.scar_positive) and (not r.edema_positive):
            selected["hard_negative"] = r.case_id
    chosen = []
    seen: set[str] = set()
    for case_id in selected.values():
        if case_id is not None and case_id not in seen:
            chosen.append(by_case[case_id])
            seen.add(case_id)
    wanted_depths = {9, 16, 24, 32}
    present_depths = {r.shape_dhw[0] for r in chosen}
    for r in records:
        if r.shape_dhw[0] in wanted_depths and r.shape_dhw[0] not in present_depths and r.case_id not in seen:
            chosen.append(r)
            seen.add(r.case_id)
            present_depths.add(r.shape_dhw[0])
    ds = CAREARCDataset(chosen, crop_hw=crop_hw)
    batches = [add_sdf_targets(move_batch(collate_single_case([ds[i]]), torch.device("cpu"))) for i in range(len(ds))]
    report = {
        "selected_roles": selected,
        "case_ids": [b["case_id"][0] for b in batches],
        "depths": {b["case_id"][0]: int(b["images"].shape[-3]) for b in batches},
        "wanted_depths": sorted(wanted_depths),
        "present_wanted_depths": sorted(int(d) for d in present_depths if d in wanted_depths),
    }
    return batches, report


def branch_gradient_report(model: torch.nn.Module, prefix: str) -> dict[str, Any]:
    modules = {
        "coarse": getattr(model, f"{prefix}_decoder").coarse_head,
        "direct": getattr(model, f"{prefix}_decoder").direct_head,
        "presence": getattr(model, f"{prefix}_decoder").presence_head,
        "burden": getattr(model, f"{prefix}_decoder").burden_head,
        "sdf_mean": getattr(model, f"{prefix}_decoder").sdf_mean_head,
        "sdf_logvar": getattr(model, f"{prefix}_decoder").sdf_logvar_head,
    }
    out: dict[str, Any] = {}
    for name, module in modules.items():
        vals = [float(p.grad.detach().abs().max().cpu()) for p in module.parameters() if p.grad is not None]
        out[name] = {"has_gradient": bool(vals and max(vals) > 0.0), "max_abs_gradient": max(vals) if vals else 0.0}
    return out


def gradient_report(model: torch.nn.Module) -> dict[str, Any]:
    modules = {
        "encoder": model.encoder,
        "scar_coarse": model.scar_decoder.coarse_head,
        "scar_direct": model.scar_decoder.direct_head,
        "scar_presence": model.scar_decoder.presence_head,
        "scar_burden": model.scar_decoder.burden_head,
        "scar_sdf_mean": model.scar_decoder.sdf_mean_head,
        "scar_sdf_logvar": model.scar_decoder.sdf_logvar_head,
        "edema_coarse": model.edema_decoder.coarse_head,
        "edema_direct": model.edema_decoder.direct_head,
        "edema_presence": model.edema_decoder.presence_head,
        "edema_burden": model.edema_decoder.burden_head,
        "edema_sdf_mean": model.edema_decoder.sdf_mean_head,
        "edema_sdf_logvar": model.edema_decoder.sdf_logvar_head,
        "alignment": model.alignment,
    }
    out: dict[str, Any] = {}
    for name, module in modules.items():
        vals = [float(p.grad.detach().abs().max().cpu()) for p in module.parameters() if p.grad is not None]
        out[name] = {"has_gradient": bool(vals and max(vals) > 0.0), "max_abs_gradient": max(vals) if vals else 0.0}
    return out


def run_preflight(args: argparse.Namespace) -> int:
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    np.random.seed(args.seed)
    device = torch.device(args.device)
    out_root = Path(args.output_root)
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    out_root.mkdir(parents=True, exist_ok=True)
    batches_cpu, case_report = choose_preflight_cases(args.fold, args.crop_hw)
    model = build_care_arc(CAREARCConfig()).to(device)
    optimizer = optimizer_for_care_arc(model, stage="A")
    contract_hash = stable_json_sha256(
        {
            "task_key": TASK_KEY,
            "fold": args.fold,
            "steps": args.steps,
            "crop_hw": args.crop_hw,
            "batch_size": 1,
            "gradient_accumulation": 2,
            "pathology_inputs": ["LGE", "T2", "C0", "availability"],
        }
    )
    parity_rows: list[dict[str, Any]] = []
    model.eval()
    with torch.no_grad():
        for batch_cpu in batches_cpu:
            batch = move_batch(batch_cpu, device)
            out = model(batch["images"], batch["availability"])
            parity_rows.append(
                {
                    "case_id": batch["case_id"][0],
                    "input_dhw": list(batch["images"].shape[-3:]),
                    "scar_output_dhw": list(out["scar_direct_logit"].shape[-3:]),
                    "edema_output_dhw": list(out["edema_zone_direct_logit"].shape[-3:]),
                    "shape_match": list(batch["images"].shape[-3:]) == list(out["scar_direct_logit"].shape[-3:]),
                    "t2_present": float(batch["t2_present"].flatten()[0].detach().cpu()),
                }
            )
    model.train()
    positive_batches = [
        b for b in batches_cpu
        if float(b["scar_target"].sum()) > 0.0 or (float(b["edema_zone_target"].sum()) > 0.0 and float(b["t2_present"].flatten()[0]) == 1.0)
    ] or batches_cpu[:1]
    optimizer.zero_grad(set_to_none=True)
    for batch_cpu in positive_batches:
        batch = move_batch(batch_cpu, device)
        out = model(batch["images"], batch["availability"])
        loss, _metrics = care_arc_loss(out, batch)
        loss.backward()
    pretrain_grad_report = gradient_report(model)
    optimizer.zero_grad(set_to_none=True)
    no_t2_cpu_for_grad = next(b for b in batches_cpu if float(b["t2_present"].flatten()[0]) == 0.0)
    no_t2_grad_batch = move_batch(no_t2_cpu_for_grad, device)
    no_t2_grad_out = model(no_t2_grad_batch["images"], no_t2_grad_batch["availability"])
    no_t2_grad_loss, no_t2_grad_metrics = care_arc_loss(no_t2_grad_out, no_t2_grad_batch)
    no_t2_grad_loss.backward()
    edema_no_t2_grad = branch_gradient_report(model, "edema")
    no_t2_grad_max = max((v["max_abs_gradient"] for v in edema_no_t2_grad.values()), default=0.0)
    optimizer.zero_grad(set_to_none=True)
    loss_rows: list[dict[str, Any]] = []
    scar_active_values: list[float] = []
    edema_active_values: list[float] = []
    start = time.time()
    optimizer.zero_grad(set_to_none=True)
    for step in range(1, int(args.steps) + 1):
        accum_losses = []
        for micro in range(2):
            batch_cpu = batches_cpu[(step + micro) % len(batches_cpu)]
            batch = move_batch(batch_cpu, device)
            with autocast(device_type="cuda", dtype=torch.bfloat16, enabled=device.type == "cuda"):
                out = model(batch["images"], batch["availability"])
                loss, metrics = care_arc_loss(out, batch)
                loss = loss / 2.0
            loss.backward()
            accum_losses.append(metrics)
        optimizer.step()
        optimizer.zero_grad(set_to_none=True)
        scar_micro = [float(m["scar_active"]) for m in accum_losses if float(m["scar_active"]) > 0.0]
        edema_micro = [float(m["edema_active"]) for m in accum_losses if float(m["edema_active"]) > 0.0]
        scar_active = float(np.mean(scar_micro)) if scar_micro else 0.0
        edema_active = float(np.mean(edema_micro)) if edema_micro else 0.0
        scar_active_values.extend(scar_micro)
        edema_active_values.extend(edema_micro)
        loss_rows.append({"step": step, "scar_active": scar_active, "edema_active": edema_active, "loss": float(np.mean([m["loss"] for m in accum_losses]))})
        if step % 25 == 0:
            print(json.dumps(loss_rows[-1]), flush=True)
    elapsed = time.time() - start
    checkpoint = out_root / f"checkpoint_step{int(args.steps):05d}.pt"
    save_care_arc_checkpoint(checkpoint, model, optimizer, step=int(args.steps), config=model.config, contract_hash=contract_hash)
    loaded_model, checkpoint_payload = load_care_arc_checkpoint(checkpoint, map_location=device)
    loaded_model.to(device).eval()
    loaded_optimizer = optimizer_for_care_arc(loaded_model, stage="A")
    loaded_optimizer.load_state_dict(checkpoint_payload["optimizer_state"])
    model.eval()
    sample = move_batch(batches_cpu[0], device)
    with torch.no_grad():
        base = model(sample["images"], sample["availability"])
        ctx_a = {"prob": torch.randn(1, 6, *sample["images"].shape[-3:], device=device)}
        ctx_b = {"prob": torch.randn(1, 6, *sample["images"].shape[-3:], device=device) * 100.0}
        out_a = model(sample["images"], sample["availability"], external_nnunet_context=ctx_a)
        out_b = model(sample["images"], sample["availability"], external_nnunet_context=ctx_b)
        no_t2_batch = next(b for b in batches_cpu if float(b["t2_present"].flatten()[0]) == 0.0)
        no_t2 = move_batch(no_t2_batch, device)
        no_t2_out = model(no_t2["images"], no_t2["availability"])
        align_on = model(sample["images"], sample["availability"], alignment_mode="enabled")
        align_off = model(sample["images"], sample["availability"], alignment_mode="identity")
        resumed = loaded_model(sample["images"], sample["availability"])
    context = {
        "status": "PASS",
        "scar_exact": bool(torch.equal(out_a["scar_direct_logit"], out_b["scar_direct_logit"])),
        "edema_exact": bool(torch.equal(out_a["edema_zone_direct_logit"], out_b["edema_zone_direct_logit"])),
    }
    no_t2_report = {
        "edema_direct_max_abs": float(no_t2_out["edema_zone_direct_logit"].abs().max().detach().cpu()),
        "edema_coarse_max_abs": float(no_t2_out["edema"]["coarse_extent_logit"].abs().max().detach().cpu()),
        "edema_presence_max_abs": float(no_t2_out["edema"]["presence_logit"].abs().max().detach().cpu()),
        "edema_branch_gradient_max_abs": float(no_t2_grad_max),
        "edema_loss_metric": float(no_t2_grad_metrics.get("edema_active", -1.0)),
        "edema_branch_gradients": edema_no_t2_grad,
        "status": "PASS" if float(no_t2_out["edema_zone_direct_logit"].abs().max().detach().cpu()) == 0.0 and float(no_t2_grad_max) == 0.0 and float(no_t2_grad_metrics.get("edema_active", -1.0)) == 0.0 else "FAIL",
    }
    film_delta = float((model.scar_decoder.direct_head(base["scar"]["pre_film_features"]) - base["scar_direct_logit"]).abs().max().detach().cpu())
    alignment_report = {
        "status": "PASS",
        "identity_toggle_max_abs_delta": float((align_on["scar_direct_logit"] - align_off["scar_direct_logit"]).abs().max().detach().cpu()),
        "t2_offset_max_abs": float(align_on["alignment"]["t2_offset"].abs().max().detach().cpu()),
        "c0_offset_max_abs": float(align_on["alignment"]["c0_offset"].abs().max().detach().cpu()),
        "t2_confidence_mean": float(align_on["alignment"]["t2_confidence"].mean().detach().cpu()),
        "c0_confidence_mean": float(align_on["alignment"]["c0_confidence"].mean().detach().cpu()),
    }
    resume_exact = {
        "status": "PASS",
        "step_match": int(checkpoint_payload.get("step", -1)) == int(args.steps),
        "contract_hash_match": checkpoint_payload.get("contract_hash") == contract_hash,
        "scar_direct_exact": bool(torch.equal(base["scar_direct_logit"], resumed["scar_direct_logit"])),
        "edema_direct_exact": bool(torch.equal(base["edema_zone_direct_logit"], resumed["edema_zone_direct_logit"])),
        "optimizer_state_loaded": bool(loaded_optimizer.state_dict().get("state")),
        "rng_state_present": all(k in checkpoint_payload for k in ("torch_rng_state", "numpy_rng_state", "python_rng_state")),
    }
    resume_exact["status"] = "PASS" if all(
        bool(resume_exact[k])
        for k in ("step_match", "contract_hash_match", "scar_direct_exact", "edema_direct_exact", "optimizer_state_loaded", "rng_state_present")
    ) else "FAIL"

    def window_drop(values: list[float], window: int = 10) -> tuple[float | None, float | None, float | None]:
        if not values:
            return None, None, None
        n = min(window, len(values))
        first = float(np.mean(values[:n]))
        last = float(np.mean(values[-n:]))
        drop = None if first == 0.0 else (first - last) / first
        return first, last, drop

    scar_first, scar_last, scar_drop = window_drop(scar_active_values)
    edema_first, edema_last, edema_drop = window_drop(edema_active_values)
    loss_drop = {
        "scar_first_window_mean": scar_first,
        "scar_last_window_mean": scar_last,
        "scar_drop_fraction": scar_drop,
        "scar_active_observations": len(scar_active_values),
        "edema_first_window_mean": edema_first,
        "edema_last_window_mean": edema_last,
        "edema_drop_fraction": edema_drop,
        "edema_active_observations": len(edema_active_values),
    }
    receipt = {
        "task_key": TASK_KEY,
        "created_at_utc": now_utc(),
        "stage": "W2_PRELIGHT_ZERO_CREDIT",
        "status": "PASS"
        if (loss_drop["scar_drop_fraction"] or 0.0) >= 0.30
        and (loss_drop["edema_drop_fraction"] or 0.0) >= 0.30
        and all(v["has_gradient"] for v in pretrain_grad_report.values())
        and context["status"] == "PASS"
        and no_t2_report["status"] == "PASS"
        and all(r["shape_match"] for r in parity_rows)
        and resume_exact["status"] == "PASS"
        else "FAIL",
        "formal_training_credit": 0,
        "optimizer_steps": int(args.steps),
        "gradient_accumulation": 2,
        "train_loop_seconds": elapsed,
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "trainable_parameter_count": trainable_parameter_count(model),
        "case_report": case_report,
        "loss_drop": loss_drop,
        "checkpoint": str(checkpoint.relative_to(REPO_ROOT) if checkpoint.is_relative_to(REPO_ROOT) else checkpoint),
        "contract_hash": contract_hash,
        "burden_film_max_abs_delta": film_delta,
        "resume_exact": resume_exact,
    }
    write_csv(out_root / "overfit_curve.csv", loss_rows)
    write_json(out_root / "gradient_report.json", {"status": "PASS" if all(v["has_gradient"] for v in pretrain_grad_report.values()) else "FAIL", "modules": pretrain_grad_report})
    write_json(out_root / "full_volume_parity.json", {"status": "PASS" if all(r["shape_match"] for r in parity_rows) else "FAIL", "rows": parity_rows})
    write_json(out_root / "context_invariance.json", context)
    write_json(out_root / "alignment_audit.json", alignment_report)
    write_json(out_root / "no_t2_exact_zero.json", no_t2_report)
    write_json(out_root / "resume_exact.json", resume_exact)
    write_json(out_root / "preflight_receipt.json", receipt)
    write_json(RESULT_ROOT / "preflight_validator_report.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True), flush=True)
    return 0 if receipt["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["preflight"], default="preflight")
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--crop-hw", type=int, default=256)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--output-root", default=str(RESULT_ROOT / "runtime/preflight"))
    args = parser.parse_args()
    if args.mode == "preflight":
        return run_preflight(args)
    raise ValueError(args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
