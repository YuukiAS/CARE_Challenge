#!/usr/bin/env python
"""Build CARE-ASE hard-negative manifest from same-fold stock validation outputs."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
STOCK_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def load_stock_prediction(fold: int, case_id: str) -> np.ndarray | None:
    candidates = [
        STOCK_ROOT / f"fold_{fold}" / "validation" / f"{case_id}.npz",
        STOCK_ROOT / f"fold_{fold}" / "validation" / f"{case_id}.npy",
    ]
    for path in candidates:
        if path.suffix == ".npz" and path.exists():
            payload = np.load(path)
            if "probabilities" in payload:
                return np.asarray(payload["probabilities"]).argmax(axis=0).astype(np.int16)
            if "softmax" in payload:
                return np.asarray(payload["softmax"]).argmax(axis=0).astype(np.int16)
        if path.suffix == ".npy" and path.exists():
            arr = np.load(path)
            return arr.argmax(axis=0).astype(np.int16) if arr.ndim == 4 else arr.astype(np.int16)
    return None


def row_for_case(fold: int, case_id: str) -> dict[str, Any]:
    gt = read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int16)
    pred = load_stock_prediction(fold, case_id)
    if pred is None:
        return {"fold": fold, "case_id": case_id, "status": "NO_STOCK_VALIDATION_PREDICTION", "scar_fp_voxels": "", "scar_fn_voxels": "", "edema_fp_voxels": "", "edema_fn_voxels": ""}
    original_pred_shape = tuple(int(v) for v in pred.shape)
    original_gt_shape = tuple(int(v) for v in gt.shape)
    common = tuple(min(int(a), int(b)) for a, b in zip(pred.shape, gt.shape))
    slices = tuple(slice(0, v) for v in common)
    pred = pred[slices]
    gt = gt[slices]
    valid = gt >= 0
    return {
        "fold": fold,
        "case_id": case_id,
        "status": "PASS" if original_pred_shape == original_gt_shape else "PASS_SHAPE_OVERLAP_ONLY",
        "prediction_shape": "x".join(str(v) for v in original_pred_shape),
        "gt_shape": "x".join(str(v) for v in original_gt_shape),
        "overlap_shape": "x".join(str(v) for v in common),
        "scar_fp_voxels": int(((pred == 5) & (gt != 5) & valid).sum()),
        "scar_fn_voxels": int(((pred != 5) & (gt == 5)).sum()),
        "edema_fp_voxels": int(((pred == 4) & (gt != 4) & valid).sum()),
        "edema_fn_voxels": int(((pred != 4) & (gt == 4)).sum()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    val_cases = [str(v) for v in splits[int(args.fold)]["val"]]
    rows = [row_for_case(int(args.fold), case_id) for case_id in val_cases]
    output = (args.output or RESULT_DIR / f"hard_negative_manifest_fold{args.fold}.csv").resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["fold", "case_id"])
        writer.writeheader()
        writer.writerows(rows)
    receipt = {
        "status": "PASS" if any(str(row["status"]).startswith("PASS") for row in rows) else "NEEDS_REPAIR",
        "fold": int(args.fold),
        "output": str(output.relative_to(REPO_ROOT)),
        "row_count": len(rows),
        "stock_prediction_rows": sum(1 for row in rows if str(row["status"]).startswith("PASS")),
        "oof_prediction_source": "same-fold stock validation output; not online/in-sample CARE-ASE refresh",
    }
    receipt_path = output.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
