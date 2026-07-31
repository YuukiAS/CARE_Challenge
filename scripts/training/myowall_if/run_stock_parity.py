#!/usr/bin/env python3
"""Run fold1 full stock nnU-Net parity and F0 hook checks for MyoWall-IF."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
import torch.nn.functional as F

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.myowall_if.stock_adapter import StockNNUNetFeatureAdapter  # noqa: E402

TASK_KEY = "20260731_care_myowall_if_mechanism_pilot"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def read_first_case(result_root: Path) -> str:
    path = result_root / "pilot_train_cases.txt"
    return path.read_text(encoding="utf-8").splitlines()[0].strip()


def load_patch(case_id: str, patch_size: list[int]) -> torch.Tensor:
    import blosc2
    import numpy as np

    arr = np.asarray(blosc2.open(str(REPO_ROOT / f"data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres/{case_id}.b2nd"), mode="r")[:])
    x = torch.from_numpy(arr).float().unsqueeze(0)
    z, y, w = x.shape[-3:]
    target_z, target_y, target_x = patch_size
    crop = x[..., : min(z, target_z), : min(y, target_y), : min(w, target_x)]
    pad = (0, max(0, target_x - crop.shape[-1]), 0, max(0, target_y - crop.shape[-2]), 0, max(0, target_z - crop.shape[-3]))
    return F.pad(crop, pad)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", default="")
    parser.add_argument("--output", type=Path, default=RESULT_ROOT / "stock_parity_report.json")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    torch.set_num_threads(4)
    adapter = StockNNUNetFeatureAdapter(fold=1, map_location=args.device)
    adapter.to(args.device)
    case_id = args.case_id or read_first_case(RESULT_ROOT)
    sample = load_patch(case_id, adapter.patch_size).to(args.device)
    report = adapter.parity_report(sample)
    report["case_id"] = case_id
    report["sample_shape"] = list(sample.shape)
    report["decoder_feature_layer"] = "network.decoder.stages[-1]"
    report["decoder_feature_channels_required"] = 32
    report["decoder_feature_channels_status"] = "PASS" if report.get("f0_shape") and int(report["f0_shape"][1]) == 32 else "FAIL"
    if report["decoder_feature_channels_status"] != "PASS":
        report["status"] = "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
