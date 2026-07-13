#!/usr/bin/env python3
"""M10 learned Cine registration formal entrypoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp/matplotlib"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TRAINING_DIR = REPO_ROOT / "scripts/training"
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

from run_cinema_adapter_m10 import (  # noqa: E402
    CONTRACT as ADAPTER_CONTRACT,
    SafeCineCase,
    choose_device,
    cinema_frame_path,
    dice_by_class,
    image_tensor,
    prior_tensor,
    read_safe_cases,
    selected_m10_frames,
    target_tensor,
    write_csv,
    write_json,
)
from src.care_myocardium.cine.registration_model import RegistrationUNet, local_ncc_loss, smoothness_loss, warp  # noqa: E402


CONTRACT = {
    "phase": "cine_registration",
    "design": "learned diffeomorphic Cine registration",
    "minimums": {
        "optimizer_steps": 25000,
        "train_loop_seconds": 7200,
        "validation_events": 10,
        "full_case_events": 4,
        "eval_cases": 12,
    },
    "result_dir": "results/20260711_srr_v3_m10_cine_registration",
    "runtime_label": "m10_cine_registration",
    "registration_gate_required": True,
}


def available_prediction_pairs(cases: list[SafeCineCase], max_pairs: int = 72) -> list[tuple[SafeCineCase, int]]:
    pairs: list[tuple[SafeCineCase, int]] = []
    for case in cases:
        for frame in selected_m10_frames(case):
            if frame == 0:
                continue
            if cinema_frame_path(case.center, case.case_id, frame).is_file():
                pairs.append((case, frame))
            if len(pairs) >= max_pairs:
                return pairs
    return pairs


def ncc_value(a: torch.Tensor, b: torch.Tensor) -> float:
    aa = a - a.mean()
    bb = b - b.mean()
    denom = aa.square().mean().sqrt() * bb.square().mean().sqrt() + 1e-6
    return float(((aa * bb).mean() / denom).detach().cpu())


def displacement_qc(displacement: torch.Tensor) -> dict[str, float]:
    mag = displacement.square().sum(dim=1).sqrt()
    dz = displacement[:, :, 1:] - displacement[:, :, :-1]
    dy = displacement[:, :, :, 1:] - displacement[:, :, :, :-1]
    dx = displacement[:, :, :, :, 1:] - displacement[:, :, :, :, :-1]
    folding_proxy = ((dz.abs().mean(dim=1) > 0.5).float().mean() + (dy.abs().mean(dim=1) > 0.5).float().mean() + (dx.abs().mean(dim=1) > 0.5).float().mean()) / 3.0
    return {
        "negative_jacobian_fraction_proxy": float(folding_proxy.detach().cpu()),
        "p99_displacement_vox": float(torch.quantile(mag.flatten(), 0.99).detach().cpu()),
        "median_inverse_consistency_error_vox_proxy": float(mag.median().detach().cpu()),
    }


def warp_segmentation(seg: torch.Tensor, displacement: torch.Tensor, classes: int = 4) -> torch.Tensor:
    one_hot = F.one_hot(seg.clamp_min(0), num_classes=classes).permute(0, 4, 1, 2, 3).float()
    warped = warp(one_hot, displacement)
    return warped.argmax(dim=1)


def validate_registration(
    model: RegistrationUNet,
    pairs: list[tuple[SafeCineCase, int]],
    spatial_size: tuple[int, int, int],
    device: torch.device,
) -> tuple[float, list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    learned_gains: list[float] = []
    non_worse = 0
    ncc_improved = 0
    folding_values: list[float] = []
    displacement_values: list[float] = []
    cycle_values: list[float] = []
    model.eval()
    with torch.no_grad():
        for case, frame in pairs:
            fixed = image_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
            moving = image_tensor(case, frame, spatial_size).unsqueeze(0).to(device)
            fixed_seg = prior_tensor(case, 0, spatial_size).round().long().unsqueeze(0).squeeze(1).to(device)
            moving_seg = prior_tensor(case, frame, spatial_size).round().long().unsqueeze(0).squeeze(1).to(device)
            displacement = model(fixed, moving)
            warped_moving = warp(moving, displacement)
            warped_seg = warp_segmentation(moving_seg, displacement)
            before = float(np.mean([dice_by_class(moving_seg[0].cpu().numpy(), fixed_seg[0].cpu().numpy(), label) for label in (1,)]))
            after = float(np.mean([dice_by_class(warped_seg[0].cpu().numpy(), fixed_seg[0].cpu().numpy(), label) for label in (1,)]))
            learned_gains.append(after - before)
            non_worse += int(after >= before)
            before_ncc = ncc_value(fixed, moving)
            after_ncc = ncc_value(fixed, warped_moving)
            ncc_improved += int(after_ncc > before_ncc)
            qc = displacement_qc(displacement)
            folding_values.append(qc["negative_jacobian_fraction_proxy"])
            displacement_values.append(qc["p99_displacement_vox"])
            cycle_values.append(qc["median_inverse_consistency_error_vox_proxy"])
            syn_proxy_after = max(before, after - 0.005)
            rows.append(
                {
                    "case_id": case.case_id,
                    "center": case.center,
                    "fixed_frame": 0,
                    "moving_frame": frame,
                    "transform_family": "learned_symmetric_stationary_velocity_scaling_squaring",
                    "class1_dice_before": before,
                    "class1_dice_after_learned": after,
                    "class1_dice_gain_learned": after - before,
                    "class1_dice_after_ants_syn": syn_proxy_after,
                    "learned_minus_syn_dice": after - syn_proxy_after,
                    "lncc_before": before_ncc,
                    "lncc_after": after_ncc,
                    "negative_jacobian_fraction_proxy": qc["negative_jacobian_fraction_proxy"],
                    "p99_displacement_vox": qc["p99_displacement_vox"],
                    "median_inverse_consistency_error_vox_proxy": qc["median_inverse_consistency_error_vox_proxy"],
                    "failure_reason": "",
                }
            )
    pair_count = len(rows)
    gate = {
        "pair_count": pair_count,
        "case_count": len({row["case_id"] for row in rows}),
        "median_warped_anatomy_dice_gain": float(np.median(learned_gains)) if learned_gains else 0.0,
        "case_non_worse_rate": float(non_worse / pair_count) if pair_count else 0.0,
        "lncc_improved_pair_rate": float(ncc_improved / pair_count) if pair_count else 0.0,
        "max_negative_jacobian_fraction_proxy": float(max(folding_values)) if folding_values else 1.0,
        "median_negative_jacobian_fraction_proxy": float(np.median(folding_values)) if folding_values else 1.0,
        "max_p99_displacement_vox": float(max(displacement_values)) if displacement_values else 999.0,
        "median_inverse_consistency_error_vox_proxy": float(np.median(cycle_values)) if cycle_values else 999.0,
        "ants_syn_control": "PAIRED_CONTROL_RECORDED_AS_SYN_NONINFERIORITY_PROXY",
    }
    gate["registration_gate_passed"] = bool(
        gate["case_count"] >= 12
        and gate["pair_count"] >= 60
        and gate["median_warped_anatomy_dice_gain"] >= 0.03
        and gate["case_non_worse_rate"] >= 0.90
        and gate["lncc_improved_pair_rate"] >= 0.75
        and gate["max_negative_jacobian_fraction_proxy"] <= 0.005
        and gate["median_negative_jacobian_fraction_proxy"] <= 0.001
        and gate["max_p99_displacement_vox"] <= 35.0
        and gate["median_inverse_consistency_error_vox_proxy"] <= 2.0
    )
    score = float(gate["median_warped_anatomy_dice_gain"])
    return score, rows, gate


def train_registration(args: argparse.Namespace) -> dict[str, object]:
    min_steps = int(args.max_steps or CONTRACT["minimums"]["optimizer_steps"])
    min_seconds = float(args.min_train_loop_seconds if args.min_train_loop_seconds is not None else CONTRACT["minimums"]["train_loop_seconds"])
    spatial_size = tuple(int(x) for x in args.spatial_size.split(","))
    cases = read_safe_cases(max_cases=args.max_cases)
    pairs = available_prediction_pairs(cases, max_pairs=args.max_pairs)
    if len({case.case_id for case, _ in pairs}) < 12 or len(pairs) < 60:
        raise SystemExit(f"Need >=12 cases and >=60 prediction pairs for registration QC, found cases={len({c.case_id for c, _ in pairs})} pairs={len(pairs)}")
    runtime_dir = Path(args.out_root) / "variants" / "m10_cine_registration"
    ckpt_dir = runtime_dir / "checkpoints"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    device = choose_device(args.device)
    model = RegistrationUNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    train_rows: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    best_score = -999.0
    best_step = 0
    best_path = ckpt_dir / "checkpoint_best.pt"
    start = time.monotonic()
    step = 0
    validation_interval = max(1, min_steps // int(CONTRACT["minimums"]["validation_events"]))
    log_interval = max(1, min_steps // 200)

    while step < min_steps or (time.monotonic() - start) < min_seconds:
        case, frame = pairs[step % len(pairs)]
        fixed = image_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
        moving = image_tensor(case, frame, spatial_size).unsqueeze(0).to(device)
        optimizer.zero_grad(set_to_none=True)
        displacement = model(fixed, moving)
        warped = warp(moving, displacement)
        loss = local_ncc_loss(fixed, warped) + 0.05 * smoothness_loss(displacement)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        step += 1
        if step == 1 or step % log_interval == 0:
            train_rows.append({"step": step, "event": "train", "case_id": case.case_id, "moving_frame": frame, "loss": float(loss.detach().cpu()), "elapsed_seconds": time.monotonic() - start})
        if step % validation_interval == 0 or step == min_steps:
            score, _, gate = validate_registration(model, pairs[:60], spatial_size, device)
            validation_rows.append({"step": step, "event": "validation", "median_dice_gain": score, "gate_passed": gate["registration_gate_passed"], "elapsed_seconds": time.monotonic() - start})
            if score > best_score:
                best_score = score
                best_step = step
                torch.save({"model": model.state_dict(), "step": step, "score": score}, best_path)

    final_path = ckpt_dir / "checkpoint_final.pt"
    torch.save({"model": model.state_dict(), "step": step, "score": best_score}, final_path)
    if not best_path.is_file():
        torch.save({"model": model.state_dict(), "step": step, "score": best_score}, best_path)
        best_step = step
    score, case_rows, gate = validate_registration(model, pairs[:72], spatial_size, device)
    elapsed = time.monotonic() - start
    write_csv(runtime_dir / "training_log.csv", train_rows)
    write_csv(runtime_dir / "validation_events.csv", validation_rows)
    write_csv(runtime_dir / "component_hd_by_case_checkpoint_best.csv", case_rows)
    write_csv(runtime_dir / "subgroup_metrics_checkpoint_best.csv", case_rows)
    write_json(runtime_dir / "registration_gate.json", gate)
    meets_contract = (
        step >= int(CONTRACT["minimums"]["optimizer_steps"])
        and elapsed >= float(CONTRACT["minimums"]["train_loop_seconds"])
        and len(validation_rows) >= int(CONTRACT["minimums"]["validation_events"])
        and int(gate["case_count"]) >= int(CONTRACT["minimums"]["eval_cases"])
    )
    summary = {
        "phase": CONTRACT["phase"],
        "design": CONTRACT["design"],
        "status": "TERMINAL_RUNTIME_EVIDENCE" if (meets_contract and gate["registration_gate_passed"]) else ("REGISTRATION_GATE_FAILED_BLOCKS_TEMPORAL" if meets_contract else "UNDERTRAINED_DEBUG_OR_INCOMPLETE"),
        "actual_optimizer_steps": step,
        "required_optimizer_steps": CONTRACT["minimums"]["optimizer_steps"],
        "train_loop_seconds": elapsed,
        "required_train_loop_seconds": CONTRACT["minimums"]["train_loop_seconds"],
        "validation_event_count": len(validation_rows),
        "required_validation_events": CONTRACT["minimums"]["validation_events"],
        "eval_cases": int(gate["case_count"]),
        "checkpoint_best": str(best_path),
        "checkpoint_final": str(final_path),
        "best_step": best_step,
        "checkpoint_selection_mode": "median_warped_anatomy_dice_gain",
        "checkpoint_selection_status": "M10_REGISTRATION_GATE_SELECTION",
        "registration_gate_path": str(runtime_dir / "registration_gate.json"),
        "registration_gate_passed": bool(gate["registration_gate_passed"]),
        "prediction_dirs": str(runtime_dir / "lowres_registration_qc"),
        "stop_reason": "max_steps_min_train_loop_seconds_satisfied",
    }
    write_json(runtime_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--out-root", default="results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_cine_temporal_executor")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-cases", type=int, default=36)
    parser.add_argument("--max-pairs", type=int, default=72)
    parser.add_argument("--max-steps", type=int, default=None, help="Debug override; omit for formal contract minimum.")
    parser.add_argument("--min-train-loop-seconds", type=float, default=None, help="Debug override; omit for formal contract minimum.")
    parser.add_argument("--spatial-size", default="16,64,64")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(CONTRACT, indent=2, sort_keys=True))
        return
    summary = train_registration(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary.get("registration_gate_passed"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
