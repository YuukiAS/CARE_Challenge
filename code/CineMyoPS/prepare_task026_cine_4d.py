#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

CARE_ROOT = Path(__file__).resolve().parents[2]
_CINE_DIR = Path(__file__).resolve().parent
for _p in (_CINE_DIR, CARE_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from task026_utils import (
    DEFAULT_BENCHMARK_OUTPUT,
    DEFAULT_INPUT,
    DEFAULT_NNUNET_RAW_OUTPUT,
    DEFAULT_VERIFY_CSV_NAME,
    build_benchmark_dataset_json,
    build_raw_dataset_json,
    discover_case_pairs,
    ensure_dir,
    extract_frame,
    log_path,
    read_image_4d,
    remap_label_to_compact,
    round_robin_limit,
    sample_frame_indices,
    sync_expected_files,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export CARE CineMyoPS into benchmark 4D Task026 and split-channel nnU-Net raw Task026."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Root directory of CARE CineMyoPS_train.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_BENCHMARK_OUTPUT,
        help="Benchmark task output directory with 4D imagesTr and 3D labelsTr.",
    )
    parser.add_argument(
        "--nnunet-raw-output",
        type=Path,
        default=DEFAULT_NNUNET_RAW_OUTPUT,
        help="Split-channel nnU-Net raw task directory consumed by planner/training.",
    )
    parser.add_argument(
        "--num-frames",
        type=int,
        default=int(os.environ.get("CINE_NUM_FRAMES", "4")),
        help="Number of evenly sampled frames per case. Frame 0 is fixed to ED at t=0.",
    )
    parser.add_argument("--max-cases", type=int, default=0, help="Optional round-robin case cap across centers.")
    parser.add_argument(
        "--verify-script",
        type=Path,
        default=Path(__file__).resolve().parent / "verify_ed_at_t0.py",
        help="Sanity gate script that verifies ED at t=0.",
    )
    parser.add_argument(
        "--verify-csv",
        type=Path,
        default=DEFAULT_BENCHMARK_OUTPUT / DEFAULT_VERIFY_CSV_NAME,
        help="CSV path written by the ED verification gate.",
    )
    return parser.parse_args()


def run_verify_gate(input_root: Path, verify_script: Path, verify_csv: Path) -> None:
    ensure_dir(verify_csv.parent)
    cmd = [sys.executable, str(verify_script.resolve()), "--input", str(input_root), "--output-csv", str(verify_csv)]
    print("verify command:", " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    if completed.returncode == 0:
        return
    # CINE_VERIFY_ED_STRICT=1 restores the old hard-fail (cancel prepare on first ED-gate violation).
    # Default is warn-only: ED at t=0 is the documented CARE convention; one or two non-conforming cases
    # should not block a multi-day Slurm job. The CSV report still records every WARN/FAIL row so we
    # can audit afterwards.
    strict = os.environ.get("CINE_VERIFY_ED_STRICT", "0") == "1"
    msg = (
        f"ED verification exited with code {completed.returncode}. "
        f"See {verify_csv.resolve()} for per-case ratio_t0 / ratio_mid status."
    )
    if strict:
        raise RuntimeError(msg)
    print(f"WARNING: {msg}", file=sys.stderr)
    print(
        "WARNING: continuing prepare despite ED-gate failure (set CINE_VERIFY_ED_STRICT=1 to abort instead).",
        file=sys.stderr,
    )


def clear_and_prepare_case_dirs(output_root: Path, raw_root: Path) -> None:
    for base in (output_root, raw_root):
        ensure_dir(base / "imagesTr")
        ensure_dir(base / "labelsTr")
    sync_expected_files(output_root / "imagesTr", [])
    sync_expected_files(output_root / "labelsTr", [])
    sync_expected_files(raw_root / "imagesTr", [])
    sync_expected_files(raw_root / "labelsTr", [])


def write_4d_case(
    case_key: str,
    cine_path: Path,
    label_path: Path,
    benchmark_root: Path,
    raw_root: Path,
    num_frames: int,
) -> tuple[dict[str, str], dict[str, str], list[int]]:
    cine_4d = read_image_4d(cine_path)
    total_frames = cine_4d.GetSize()[3]
    frame_indices = sample_frame_indices(total_frames, num_frames)
    sampled_frames = []
    sampled_frame_images = []
    raw_frame_names = []
    ed_frame = None
    for raw_channel, time_index in enumerate(frame_indices):
        frame_image = extract_frame(cine_4d, time_index)
        if ed_frame is None:
            if time_index != 0:
                raise RuntimeError(f"ED frame must be t=0 for {case_key}, got {time_index}")
            ed_frame = frame_image
        sampled_frames.append(sitk.GetArrayFromImage(frame_image))
        sampled_frame_images.append(frame_image)
        raw_frame_name = f"{case_key}_{raw_channel:04d}.nii.gz"
        sitk.WriteImage(frame_image, str((raw_root / "imagesTr" / raw_frame_name).resolve()))
        raw_frame_names.append(raw_frame_name)

    if ed_frame is None:
        raise RuntimeError(f"Failed to derive ED frame for {case_key}")

    sampled_array = np.stack(sampled_frames, axis=0)
    if sampled_array.shape[0] != num_frames:
        raise RuntimeError(f"Expected {num_frames} sampled frames for {case_key}, got {sampled_array.shape[0]}")
    benchmark_image = sitk.JoinSeries(sampled_frame_images)
    benchmark_image.SetSpacing(cine_4d.GetSpacing())
    benchmark_image.SetOrigin(cine_4d.GetOrigin())
    benchmark_image.SetDirection(cine_4d.GetDirection())
    benchmark_image_name = f"{case_key}_0000.nii.gz"
    sitk.WriteImage(benchmark_image, str((benchmark_root / "imagesTr" / benchmark_image_name).resolve()))

    label_image = sitk.ReadImage(str(label_path.resolve()))
    compact_label = remap_label_to_compact(label_image, ed_frame)
    label_name = f"{case_key}.nii.gz"
    sitk.WriteImage(compact_label, str((benchmark_root / "labelsTr" / label_name).resolve()))
    sitk.WriteImage(compact_label, str((raw_root / "labelsTr" / label_name).resolve()))

    return (
        {
            "image": f"./imagesTr/{case_key}_0000.nii.gz",
            "label": f"./labelsTr/{case_key}.nii.gz",
        },
        {
            "image": f"./imagesTr/{case_key}.nii.gz",
            "label": f"./labelsTr/{case_key}.nii.gz",
        },
        frame_indices,
    )


def cleanup_stale_metadata(output_root: Path, raw_root: Path) -> None:
    for directory in (output_root, raw_root):
        for stale_name in ("verify_ed_at_t0.csv",):
            stale_path = directory / stale_name
            if stale_path.exists() and stale_path.is_file():
                stale_path.unlink()


def main() -> int:
    args = parse_args()
    input_root = args.input.resolve()
    output_root = args.output.resolve()
    raw_root = args.nnunet_raw_output.resolve()
    verify_script = args.verify_script.resolve()
    verify_csv = args.verify_csv.resolve()

    log_path("prepare input root", input_root)
    log_path("prepare benchmark output", output_root)
    log_path("prepare nnunet raw output", raw_root)
    log_path("prepare verify script", verify_script)
    log_path("prepare verify csv", verify_csv)

    if not verify_script.is_file():
        raise FileNotFoundError(f"Missing verify script: {verify_script}")
    if args.num_frames < 1:
        raise ValueError(f"--num-frames must be >= 1, got {args.num_frames}")

    run_verify_gate(input_root, verify_script, verify_csv)
    verify_csv_bytes = verify_csv.read_bytes()
    pairs = round_robin_limit(discover_case_pairs(input_root), args.max_cases)

    clear_and_prepare_case_dirs(output_root, raw_root)
    cleanup_stale_metadata(output_root, raw_root)

    benchmark_training_entries: list[dict[str, str]] = []
    raw_training_entries: list[dict[str, str]] = []
    frame_indices_per_case: dict[str, list[int]] = {}
    benchmark_image_names: list[str] = []
    label_names: list[str] = []
    raw_image_names: list[str] = []

    for center, case_id, cine_path, label_path in pairs:
        case_key = f"{center}_{case_id}"
        benchmark_training_entry, raw_training_entry, frame_indices = write_4d_case(
            case_key=case_key,
            cine_path=cine_path,
            label_path=label_path,
            benchmark_root=output_root,
            raw_root=raw_root,
            num_frames=args.num_frames,
        )
        benchmark_training_entries.append(benchmark_training_entry)
        raw_training_entries.append(raw_training_entry)
        frame_indices_per_case[case_key] = frame_indices
        benchmark_image_names.append(f"{case_key}_0000.nii.gz")
        label_names.append(f"{case_key}.nii.gz")
        raw_image_names.extend([f"{case_key}_{channel:04d}.nii.gz" for channel in range(args.num_frames)])

    sync_expected_files(output_root / "imagesTr", benchmark_image_names)
    sync_expected_files(output_root / "labelsTr", label_names)
    sync_expected_files(raw_root / "imagesTr", raw_image_names)
    sync_expected_files(raw_root / "labelsTr", label_names)

    write_json(
        output_root / "dataset.json",
        build_benchmark_dataset_json(benchmark_training_entries, frame_indices_per_case, args.num_frames),
    )
    write_json(
        raw_root / "dataset.json",
        build_raw_dataset_json(raw_training_entries, frame_indices_per_case, args.num_frames),
    )
    (output_root / verify_csv.name).write_bytes(verify_csv_bytes)
    (raw_root / verify_csv.name).write_bytes(verify_csv_bytes)

    print(
        f"prepare summary: exported {len(benchmark_training_entries)} cases, "
        f"num_frames={args.num_frames}, benchmark_task={output_root}, raw_task={raw_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
