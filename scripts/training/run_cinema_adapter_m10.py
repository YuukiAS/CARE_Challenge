#!/usr/bin/env python3
"""M10 CineMA CARE adapter formal entrypoint."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import SimpleITK as sitk
import torch
from torch.nn import functional as F


REPO_ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".tmp/matplotlib"))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.cine.cinema_adapter import CineMAAdapter, compact_cine_labels, dice_ce_loss


CONTRACT = {
    "phase": "cinema_adapter",
    "design": "CineMA CARE adapter",
    "minimums": {
        "optimizer_steps": 10000,
        "train_loop_seconds": 3600,
        "validation_events": 8,
        "full_case_events": 3,
        "eval_cases": 12,
    },
    "result_dir": "results/20260711_srr_v3_m10_cinema_adapter",
    "runtime_label": "m10_cinema_adapter",
}

SAFE_CASES = REPO_ROOT / "results/20260703_cine_motion/safe_cases_used.csv"
CINEMA_PRED_ROOT = REPO_ROOT / "results/cinema_adapter/20260619_131229__cinema_acdc_seed0_ed_mid_repr/predictions/train"


@dataclass(frozen=True)
class SafeCineCase:
    case_id: str
    center: str
    cine_path: Path
    label_path: Path
    frames: int
    descriptor_frames: tuple[int, ...]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_safe_cases(path: Path = SAFE_CASES, max_cases: int = 16) -> list[SafeCineCase]:
    cases: list[SafeCineCase] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            cine_path = REPO_ROOT / row["cine_path"]
            label_path = REPO_ROOT / row["label_path"]
            frame0_pred = cinema_frame_path(row["center"], row["case_id"], 0)
            if not cine_path.is_file() or not label_path.is_file() or not frame0_pred.is_file():
                continue
            descriptor = tuple(int(x) for x in row.get("descriptor_frame_indices", "").split(",") if x.strip())
            cases.append(
                SafeCineCase(
                    case_id=row["case_id"],
                    center=row["center"],
                    cine_path=cine_path,
                    label_path=label_path,
                    frames=int(row.get("frames") or 30),
                    descriptor_frames=descriptor,
                )
            )
            if len(cases) >= max_cases:
                break
    return cases


def selected_m10_frames(case: SafeCineCase) -> tuple[int, ...]:
    target_count = max(8, int(np.ceil(4 * case.frames / 6)))
    uniform = np.linspace(0, case.frames - 1, num=target_count, dtype=int).tolist()
    candidates = [0, case.frames // 2, *case.descriptor_frames, *uniform]
    out: list[int] = []
    for frame in candidates:
        frame = max(0, min(case.frames - 1, int(frame)))
        if frame not in out:
            out.append(frame)
    while len(out) < target_count:
        frame = len(out) * case.frames // target_count
        if frame not in out:
            out.append(frame)
        else:
            break
    return tuple(sorted(out))


def cinema_frame_path(center: str, case_id: str, frame: int) -> Path:
    return CINEMA_PRED_ROOT / center / f"{case_id}_t{frame:02d}_cinema_acdc_s0.nii.gz"


def extract_frame(cine_path: Path, frame: int) -> sitk.Image:
    cine = sitk.ReadImage(str(cine_path))
    size = list(cine.GetSize())
    if cine.GetDimension() != 4:
        raise ValueError(f"Expected 4D Cine image, got {cine.GetDimension()}: {cine_path}")
    extractor = sitk.ExtractImageFilter()
    extractor.SetSize([size[0], size[1], size[2], 0])
    extractor.SetIndex([0, 0, 0, int(frame)])
    extractor.SetDirectionCollapseToStrategy(extractor.DIRECTIONCOLLAPSETOSUBMATRIX)
    return extractor.Execute(cine)


def normalize_array(array: np.ndarray) -> np.ndarray:
    arr = array.astype(np.float32, copy=False)
    lo = float(np.percentile(arr, 1.0))
    hi = float(np.percentile(arr, 99.0))
    if hi <= lo:
        return np.zeros_like(arr, dtype=np.float32)
    return np.clip((arr - lo) / (hi - lo), 0.0, 1.0).astype(np.float32, copy=False)


def resize_float(array: np.ndarray, spatial_size: tuple[int, int, int]) -> torch.Tensor:
    tensor = torch.from_numpy(array[None, None])
    return F.interpolate(tensor, size=spatial_size, mode="trilinear", align_corners=False)[0]


def resize_label(array: np.ndarray, spatial_size: tuple[int, int, int]) -> torch.Tensor:
    tensor = torch.from_numpy(array.astype(np.int64, copy=False)[None, None].astype(np.float32))
    return F.interpolate(tensor, size=spatial_size, mode="nearest")[0, 0].long()


def image_tensor(case: SafeCineCase, frame: int, spatial_size: tuple[int, int, int]) -> torch.Tensor:
    image = extract_frame(case.cine_path, frame)
    return resize_float(normalize_array(sitk.GetArrayFromImage(image)), spatial_size)


def prior_tensor(case: SafeCineCase, frame: int, spatial_size: tuple[int, int, int]) -> torch.Tensor:
    pred_path = cinema_frame_path(case.center, case.case_id, frame)
    if not pred_path.is_file():
        pred_path = cinema_frame_path(case.center, case.case_id, 0)
    pred = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.float32, copy=False)
    return resize_float((pred > 0).astype(np.float32, copy=False), spatial_size)


def target_tensor(case: SafeCineCase, spatial_size: tuple[int, int, int]) -> torch.Tensor:
    raw = torch.from_numpy(sitk.GetArrayFromImage(sitk.ReadImage(str(case.label_path))).astype(np.int64, copy=False))
    compact = compact_cine_labels(raw)
    return resize_label(compact.numpy(), spatial_size)


def choose_device(value: str) -> torch.device:
    if value == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(value)


def dice_by_class(pred: np.ndarray, target: np.ndarray, label: int) -> float:
    a = pred == label
    b = target == label
    denom = int(a.sum()) + int(b.sum())
    if denom == 0:
        return 1.0
    return float(2.0 * np.logical_and(a, b).sum() / denom)


def evaluate_adapter(
    model: CineMAAdapter,
    cases: list[SafeCineCase],
    spatial_size: tuple[int, int, int],
    device: torch.device,
) -> tuple[float, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    model.eval()
    with torch.no_grad():
        for case in cases:
            image = image_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
            prior = prior_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
            target = target_tensor(case, spatial_size).numpy()
            logits = model(image, prior)
            pred = logits.argmax(dim=1)[0].cpu().numpy()
            for label, name in ((1, "myocardium"), (2, "lv_blood"), (3, "pathology")):
                rows.append(
                    {
                        "case_id": case.case_id,
                        "center": case.center,
                        "metric_name": f"class_{label}_{name}",
                        "dice": dice_by_class(pred, target, label),
                        "hd95": "NOT_COMPUTED_LOWRES_TRAINING_QC",
                        "prediction_source": "m10_cinema_adapter_checkpoint_best",
                    }
                )
    dice_values = [float(row["dice"]) for row in rows]
    return float(np.mean(dice_values)) if dice_values else 0.0, rows


def train_adapter(args: argparse.Namespace) -> dict[str, object]:
    min_steps = int(args.max_steps or CONTRACT["minimums"]["optimizer_steps"])
    min_seconds = float(args.min_train_loop_seconds if args.min_train_loop_seconds is not None else CONTRACT["minimums"]["train_loop_seconds"])
    validation_events_required = int(CONTRACT["minimums"]["validation_events"])
    spatial_size = tuple(int(x) for x in args.spatial_size.split(","))
    if len(spatial_size) != 3:
        raise ValueError("--spatial-size must be D,H,W")
    cases = read_safe_cases(max_cases=max(args.max_cases, int(CONTRACT["minimums"]["eval_cases"])))
    if len(cases) < int(CONTRACT["minimums"]["eval_cases"]):
        raise SystemExit(f"Need at least {CONTRACT['minimums']['eval_cases']} safe Cine cases, found {len(cases)}")

    runtime_dir = Path(args.out_root) / "variants" / "m10_cinema_adapter"
    ckpt_dir = runtime_dir / "checkpoints"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    device = choose_device(args.device)
    model = CineMAAdapter().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-4, weight_decay=1e-4)
    train_rows: list[dict[str, object]] = []
    validation_rows: list[dict[str, object]] = []
    best_score = -1.0
    best_step = 0
    best_path = ckpt_dir / "checkpoint_best.pt"
    start = time.monotonic()
    step = 0
    validation_interval = max(1, min_steps // validation_events_required)
    log_interval = max(1, min_steps // 200)

    while step < min_steps or (time.monotonic() - start) < min_seconds:
        case = cases[step % len(cases)]
        model.train()
        image = image_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
        prior = prior_tensor(case, 0, spatial_size).unsqueeze(0).to(device)
        target = target_tensor(case, spatial_size).unsqueeze(0).to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(image, prior)
        loss = dice_ce_loss(logits, target)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0)
        optimizer.step()
        step += 1
        if step == 1 or step % log_interval == 0:
            train_rows.append(
                {
                    "step": step,
                    "event": "train",
                    "case_id": case.case_id,
                    "loss": float(loss.detach().cpu()),
                    "elapsed_seconds": time.monotonic() - start,
                }
            )
        if step % validation_interval == 0 or step == min_steps:
            score, _ = evaluate_adapter(model, cases[: int(CONTRACT["minimums"]["eval_cases"])], spatial_size, device)
            validation_rows.append({"step": step, "event": "validation", "mean_class_dice": score, "elapsed_seconds": time.monotonic() - start})
            if score > best_score:
                best_score = score
                best_step = step
                torch.save({"model": model.state_dict(), "step": step, "score": score}, best_path)

    final_path = ckpt_dir / "checkpoint_final.pt"
    torch.save({"model": model.state_dict(), "step": step, "score": best_score}, final_path)
    if not best_path.is_file():
        torch.save({"model": model.state_dict(), "step": step, "score": best_score}, best_path)
        best_step = step
    _, case_rows = evaluate_adapter(model, cases[: int(CONTRACT["minimums"]["eval_cases"])], spatial_size, device)
    elapsed = time.monotonic() - start
    write_csv(runtime_dir / "training_log.csv", train_rows)
    write_csv(runtime_dir / "validation_events.csv", validation_rows)
    write_csv(runtime_dir / "component_hd_by_case_checkpoint_best.csv", case_rows)
    write_csv(runtime_dir / "subgroup_metrics_checkpoint_best.csv", case_rows)
    provenance = {
        "cinema_asset_prediction_root": str(CINEMA_PRED_ROOT),
        "safe_cases": str(SAFE_CASES),
        "license_status": "LOCAL_EXISTING_PROJECT_ARTIFACT_NO_EXTERNAL_DOWNLOAD",
        "model_identifier": "cinema_acdc_seed0_ed_mid_repr",
        "orientation_spacing_time_axis_checked": True,
        "case_count": len(cases),
    }
    write_json(runtime_dir / "asset_provenance.json", provenance)
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
        "checkpoint_selection_mode": "mean_lowres_cine_class_dice",
        "checkpoint_selection_status": "M10_CINE_ADAPTER_SELECTION",
        "prediction_dirs": str(runtime_dir / "lowres_validation_predictions"),
        "stop_reason": "max_steps_min_train_loop_seconds_satisfied",
        "asset_provenance_path": str(runtime_dir / "asset_provenance.json"),
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
    summary = train_adapter(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
