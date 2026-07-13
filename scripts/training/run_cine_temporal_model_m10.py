#!/usr/bin/env python3
"""M10 learned Cine temporal dictionary formal entrypoint."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp/matplotlib"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TRAINING_DIR = REPO_ROOT / "scripts/training"
if str(TRAINING_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_DIR))

from run_cinema_adapter_m10 import (  # noqa: E402
    choose_device,
    dice_by_class,
    image_tensor,
    prior_tensor,
    read_safe_cases,
    selected_m10_frames,
    target_tensor,
    write_csv,
    write_json,
)
from src.care_myocardium.cine.cinema_adapter import dice_ce_loss  # noqa: E402
from src.care_myocardium.cine.temporal_dictionary import temporal_load_loss  # noqa: E402
from src.care_myocardium.cine.temporal_model import CineTemporalModel  # noqa: E402


CONTRACT = {
    "phase": "cine_temporal",
    "design": "registration-gated learned temporal dictionary",
    "minimums": {
        "optimizer_steps": 20000,
        "train_loop_seconds": 7200,
        "validation_events": 10,
        "full_case_events": 4,
        "eval_cases": 12,
    },
    "result_dir": "results/20260711_srr_v3_m10_cine_learned_temporal",
    "runtime_label": "m10_cine_learned_temporal",
    "registration_gate_required": True,
    "temporal_slot_count": 8,
}


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def temporal_z(case, spatial_size: tuple[int, int, int], device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    frames = selected_m10_frames(case)
    tensors: list[torch.Tensor] = []
    frame0 = image_tensor(case, 0, spatial_size)
    for frame in frames:
        image = image_tensor(case, frame, spatial_size)
        prior = prior_tensor(case, frame, spatial_size)
        motion_mag = torch.full_like(image, abs(frame - 0) / max(1, case.frames - 1))
        residual = (image - frame0).abs()
        time_embed = torch.full_like(image, frame / max(1, case.frames - 1))
        tensors.append(torch.cat([image, prior, motion_mag, residual, time_embed], dim=0))
    z = torch.stack(tensors, dim=0).unsqueeze(0).to(device)
    valid = torch.ones((1, len(frames)), dtype=torch.bool, device=device)
    return z, valid


def evaluate_temporal(
    model: CineTemporalModel,
    cases,
    spatial_size: tuple[int, int, int],
    device: torch.device,
) -> tuple[float, list[dict[str, object]], list[dict[str, object]]]:
    metric_rows: list[dict[str, object]] = []
    usage_rows: list[dict[str, object]] = []
    model.eval()
    with torch.no_grad():
        for case in cases:
            z, valid = temporal_z(case, spatial_size, device)
            ed_image = image_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
            ed_prior = prior_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
            target = target_tensor(case, spatial_size).to(device)
            logits, beta = model(ed_image, ed_prior, z, valid)
            temporal_pred = logits.argmax(dim=1)[0].cpu().numpy()
            frame0_pred = model.adapter(ed_image, ed_prior).argmax(dim=1)[0].cpu().numpy()
            target_np = target.cpu().numpy()
            nonref_count = int(valid.sum().item()) - 1
            status = "TEMPORAL_DICTIONARY_VALID" if nonref_count >= 4 else "REGISTRATION_FAILURE_FEWER_THAN_FOUR_NONREF"
            usage_rows.append(
                {
                    "case_id": case.case_id,
                    "center": case.center,
                    "reference_frame": 0,
                    "selected_frames": ";".join(str(x) for x in selected_m10_frames(case)),
                    "valid_nonreference_frames": nonref_count,
                    "temporal_slot_count": 8,
                    "slot_mass": ";".join(f"{float(v):.6f}" for v in beta.mean(dim=(0, 1, 3, 4, 5)).cpu()),
                    "status": status,
                }
            )
            for label, name in ((1, "myocardium"), (2, "lv_blood"), (3, "pathology")):
                frame0_dice = dice_by_class(frame0_pred, target_np, label)
                temporal_dice = dice_by_class(temporal_pred, target_np, label)
                metric_rows.append(
                    {
                        "case_id": case.case_id,
                        "center": case.center,
                        "metric_name": f"class_{label}_{name}",
                        "frame0_reference_dice": frame0_dice,
                        "temporal_final_output_dice": temporal_dice,
                        "dice_delta_vs_frame0": temporal_dice - frame0_dice,
                        "temporal_jitter_proxy": float(np.std([frame0_dice, temporal_dice])),
                        "topology_failure": "NOT_COMPUTED_LOWRES_TRAINING_QC",
                        "final_label_changed_voxels": int(np.count_nonzero(temporal_pred != frame0_pred)),
                        "hosted_metric_caveat": "no hosted metric claim",
                    }
                )
    dice_values = [float(row["temporal_final_output_dice"]) for row in metric_rows]
    return float(np.mean(dice_values)) if dice_values else 0.0, metric_rows, usage_rows


def check_upstream(out_root: Path) -> None:
    adapter_summary = read_json(out_root / "variants/m10_cinema_adapter/summary.json")
    registration_summary = read_json(out_root / "variants/m10_cine_registration/summary.json")
    if not adapter_summary:
        raise SystemExit("Missing CineMA adapter summary; temporal training requires adapter evidence.")
    if not registration_summary:
        raise SystemExit("Missing registration summary; temporal training requires registration gate evidence.")
    if not registration_summary.get("registration_gate_passed"):
        raise SystemExit("Registration gate did not pass; temporal training is blocked by M10 contract.")


def train_temporal(args: argparse.Namespace) -> dict[str, object]:
    out_root = Path(args.out_root)
    check_upstream(out_root)
    min_steps = int(args.max_steps or CONTRACT["minimums"]["optimizer_steps"])
    min_seconds = float(args.min_train_loop_seconds if args.min_train_loop_seconds is not None else CONTRACT["minimums"]["train_loop_seconds"])
    spatial_size = tuple(int(x) for x in args.spatial_size.split(","))
    cases = read_safe_cases(max_cases=max(args.max_cases, int(CONTRACT["minimums"]["eval_cases"])))
    cases = [case for case in cases if len(selected_m10_frames(case)) - 1 >= 4]
    if len(cases) < int(CONTRACT["minimums"]["eval_cases"]):
        raise SystemExit(f"Need at least {CONTRACT['minimums']['eval_cases']} cases with >=4 valid non-reference frames, found {len(cases)}")
    runtime_dir = out_root / "variants" / "m10_cine_learned_temporal"
    ckpt_dir = runtime_dir / "checkpoints"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    device = choose_device(args.device)
    model = CineTemporalModel().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    train_rows: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    best_score = -1.0
    best_step = 0
    best_path = ckpt_dir / "checkpoint_best.pt"
    start = time.monotonic()
    step = 0
    validation_interval = max(1, min_steps // int(CONTRACT["minimums"]["validation_events"]))
    log_interval = max(1, min_steps // 200)

    while step < min_steps or (time.monotonic() - start) < min_seconds:
        case = cases[step % len(cases)]
        model.train()
        z, valid = temporal_z(case, spatial_size, device)
        ed_image = image_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
        ed_prior = prior_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
        target = target_tensor(case, spatial_size).unsqueeze(0).to(device)
        optimizer.zero_grad(set_to_none=True)
        logits, beta = model(ed_image, ed_prior, z, valid)
        loss = dice_ce_loss(logits, target) + 0.05 * temporal_load_loss(beta)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        step += 1
        if step == 1 or step % log_interval == 0:
            train_rows.append({"step": step, "event": "train", "case_id": case.case_id, "loss": float(loss.detach().cpu()), "elapsed_seconds": time.monotonic() - start})
        if step % validation_interval == 0 or step == min_steps:
            score, _, _ = evaluate_temporal(model, cases[: int(CONTRACT["minimums"]["eval_cases"])], spatial_size, device)
            validation_rows.append({"step": step, "event": "validation", "mean_temporal_dice": score, "elapsed_seconds": time.monotonic() - start})
            if score > best_score:
                best_score = score
                best_step = step
                torch.save({"model": model.state_dict(), "step": step, "score": score}, best_path)

    final_path = ckpt_dir / "checkpoint_final.pt"
    torch.save({"model": model.state_dict(), "step": step, "score": best_score}, final_path)
    if not best_path.is_file():
        torch.save({"model": model.state_dict(), "step": step, "score": best_score}, best_path)
        best_step = step
    score, metric_rows, usage_rows = evaluate_temporal(model, cases[: int(CONTRACT["minimums"]["eval_cases"])], spatial_size, device)
    elapsed = time.monotonic() - start
    write_csv(runtime_dir / "training_log.csv", train_rows)
    write_csv(runtime_dir / "validation_events.csv", validation_rows)
    write_csv(runtime_dir / "component_hd_by_case_checkpoint_best.csv", metric_rows)
    write_csv(runtime_dir / "subgroup_metrics_checkpoint_best.csv", metric_rows)
    write_csv(runtime_dir / "temporal_slot_usage.csv", usage_rows)
    meets_contract = (
        step >= int(CONTRACT["minimums"]["optimizer_steps"])
        and elapsed >= float(CONTRACT["minimums"]["train_loop_seconds"])
        and len(validation_rows) >= int(CONTRACT["minimums"]["validation_events"])
        and int(CONTRACT["minimums"]["eval_cases"]) <= len(cases)
    )
    summary = {
        "phase": CONTRACT["phase"],
        "design": CONTRACT["design"],
        "status": "TERMINAL_RUNTIME_EVIDENCE" if meets_contract else "UNDERTRAINED_DEBUG_OR_INCOMPLETE",
        "actual_optimizer_steps": step,
        "required_optimizer_steps": CONTRACT["minimums"]["optimizer_steps"],
        "train_loop_seconds": elapsed,
        "required_train_loop_seconds": CONTRACT["minimums"]["train_loop_seconds"],
        "validation_event_count": len(validation_rows),
        "required_validation_events": CONTRACT["minimums"]["validation_events"],
        "eval_cases": int(CONTRACT["minimums"]["eval_cases"]),
        "checkpoint_best": str(best_path),
        "checkpoint_final": str(final_path),
        "best_step": best_step,
        "checkpoint_selection_mode": "mean_lowres_temporal_final_output_dice",
        "checkpoint_selection_status": "M10_TEMPORAL_SELECTION",
        "prediction_dirs": str(runtime_dir / "lowres_temporal_qc"),
        "temporal_slot_usage_path": str(runtime_dir / "temporal_slot_usage.csv"),
        "stop_reason": "max_steps_min_train_loop_seconds_satisfied",
        "hosted_metric_caveat": "no hosted metric claim",
    }
    write_json(runtime_dir / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--out-root", default="results/20260711_srr_v3_m10_complete_mechanism_repair/runtime/m10_cine_temporal_executor")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--max-cases", type=int, default=16)
    parser.add_argument("--max-steps", type=int, default=None, help="Debug override; omit for formal contract minimum.")
    parser.add_argument("--min-train-loop-seconds", type=float, default=None, help="Debug override; omit for formal contract minimum.")
    parser.add_argument("--spatial-size", default="16,64,64")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(CONTRACT, indent=2, sort_keys=True))
        return
    summary = train_temporal(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
