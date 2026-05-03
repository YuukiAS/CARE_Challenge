#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
import SimpleITK as sitk

CARE_ROOT = Path(__file__).resolve().parents[2]
if str(CARE_ROOT) not in sys.path:
    sys.path.insert(0, str(CARE_ROOT))

from scripts.CineMyoPS.task026_utils import (
    DEFAULT_INPUT,
    DEFAULT_VERIFY_CSV_NAME,
    discover_case_pairs,
    ensure_dir,
    log_path,
    read_image_4d,
    remap_label_to_compact,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify that CARE CineMyoPS uses t=0 as ED by foreground intensity ratio."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Root directory of CARE CineMyoPS_train.")
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=DEFAULT_INPUT / DEFAULT_VERIFY_CSV_NAME,
        help="CSV report path.",
    )
    parser.add_argument(
        "--warn-threshold",
        type=float,
        default=0.85,
        help="Per-case warning threshold for ratio_t0.",
    )
    parser.add_argument(
        "--max-warn-ratio",
        type=float,
        default=0.10,
        help="Maximum allowed fraction of WARN cases before returning exit code 1.",
    )
    return parser.parse_args()


def compute_ratio(cine_path: Path, label_path: Path) -> tuple[int, float, float]:
    cine_4d = read_image_4d(cine_path)
    ed_image = sitk.Extract(cine_4d, [*cine_4d.GetSize()[:3], 0], [0, 0, 0, 0])
    label_image = sitk.ReadImage(str(label_path))
    compact_label = remap_label_to_compact(label_image, ed_image)
    label_mask = sitk.GetArrayFromImage(compact_label) > 0
    if not np.any(label_mask):
        raise ValueError(f"Foreground mask is empty for {label_path.resolve()}")

    cine_array = sitk.GetArrayFromImage(cine_4d)
    if cine_array.ndim != 4:
        raise ValueError(f"Expected 4D array for {cine_path.resolve()}, got shape {cine_array.shape}")
    per_frame_means = []
    for frame_index in range(cine_array.shape[0]):
        per_frame_means.append(float(cine_array[frame_index][label_mask].mean()))
    max_mean = max(per_frame_means)
    if max_mean <= 0:
        raise ValueError(f"Maximum foreground intensity is non-positive for {cine_path.resolve()}")
    mid_index = cine_array.shape[0] // 2
    return (
        cine_array.shape[0],
        per_frame_means[0] / max_mean,
        per_frame_means[mid_index] / max_mean,
    )


def main() -> int:
    args = parse_args()
    input_root = args.input.resolve()
    output_csv = args.output_csv.resolve()
    ensure_dir(output_csv.parent)
    log_path("verify input root", input_root)
    log_path("verify output csv", output_csv)

    pairs = discover_case_pairs(input_root)
    rows: list[dict[str, str | int | float]] = []
    warn_count = 0

    for center, case_id, cine_path, label_path in pairs:
        total_frames, ratio_t0, ratio_mid = compute_ratio(cine_path, label_path)
        status = "OK" if ratio_t0 >= args.warn_threshold else "WARN"
        if status == "WARN":
            warn_count += 1
        rows.append(
            {
                "case_id": f"{center}_{case_id}",
                "T": total_frames,
                "ratio_t0": f"{ratio_t0:.6f}",
                "ratio_mid": f"{ratio_mid:.6f}",
                "status": status,
            }
        )

    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["case_id", "T", "ratio_t0", "ratio_mid", "status"])
        writer.writeheader()
        writer.writerows(rows)

    total_cases = len(rows)
    warn_ratio = warn_count / total_cases
    print(f"verify summary: total_cases={total_cases}, warn_count={warn_count}, warn_ratio={warn_ratio:.4f}")
    if warn_ratio > args.max_warn_ratio:
        print("verify result: FAILED", file=sys.stderr)
        return 1
    print("verify result: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
