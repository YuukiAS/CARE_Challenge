#!/usr/bin/env python
"""CARE-ASE R2 one-time outer evaluator.

This entrypoint is deliberately fail-closed before W4.5. It exists during G1 so
the implementation has a fixed evaluator/decode path, but it refuses to touch
fold1/fold4 outer data unless the pre-outer snapshot push receipt is present.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits, pure_edema_metric_population, scar_metric_population
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint


RESULT_ROOT = REPO_ROOT / "results/20260803_care_ase_r2_full_fidelity_execution"
W45_PUSH_RECEIPT = RESULT_ROOT / "preouter_snapshot_push_receipt.json"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def assert_w45_permit() -> dict[str, Any]:
    if not W45_PUSH_RECEIPT.is_file():
        raise RuntimeError("W5 outer evaluation forbidden before W4.5 snapshot push receipt")
    receipt = json.loads(W45_PUSH_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or not receipt.get("push_verified", False):
        raise RuntimeError("W4.5 snapshot push receipt is not PASS/push_verified")
    return receipt


def parse_patch_size(text: str) -> tuple[int, int, int]:
    parts = tuple(int(v) for v in text.replace("x", ",").split(",") if v)
    if len(parts) != 3:
        raise ValueError(f"patch size must have three dimensions: {text}")
    return parts


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def sliding_window_logits(model: torch.nn.Module, image: torch.Tensor, availability: torch.Tensor, *, patch_size: tuple[int, int, int], overlap: float = 0.5) -> torch.Tensor:
    spatial = tuple(int(v) for v in image.shape[-3:])
    if all(spatial[i] <= patch_size[i] for i in range(3)):
        return model(image, availability, global_step=14000)["final_logits"]
    stride = tuple(max(1, int(size * (1.0 - overlap))) for size in patch_size)
    out = image.new_zeros((1, 6, *spatial))
    count = image.new_zeros((1, 1, *spatial))
    starts = []
    for dim, size, step in zip(spatial, patch_size, stride):
        values = list(range(0, max(dim - size, 0) + 1, step))
        if not values or values[-1] != max(dim - size, 0):
            values.append(max(dim - size, 0))
        starts.append(values)
    for z in starts[0]:
        for y in starts[1]:
            for x in starts[2]:
                patch = image[..., z : z + patch_size[0], y : y + patch_size[1], x : x + patch_size[2]]
                logits = model(patch, availability, global_step=14000)["final_logits"]
                out[..., z : z + patch_size[0], y : y + patch_size[1], x : x + patch_size[2]] += logits
                count[..., z : z + patch_size[0], y : y + patch_size[1], x : x + patch_size[2]] += 1.0
    return out / count.clamp_min(1.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--allow-after-w45", action="store_true")
    args = parser.parse_args()

    if not args.allow_after_w45:
        raise RuntimeError("outer evaluator requires explicit --allow-after-w45")
    permit = assert_w45_permit()
    out = (args.output_dir or RESULT_ROOT / "outer_once" / f"fold_{args.fold}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    patch_size = parse_patch_size(args.patch_size)
    model, payload = load_care_ase_checkpoint(args.checkpoint, map_location="cuda" if torch.cuda.is_available() else "cpu", restore_rng=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device).eval()
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    outer_cases = [str(case_id) for case_id in splits[int(args.fold)]["val"]]
    metadata = load_myops_case_metadata(REPO_ROOT)
    availability_by_case = {case_id: tuple(float(v) for v in metadata[case_id].availability) for case_id in outer_cases}
    case_rows = []
    with torch.no_grad():
        for case_id in outer_cases:
            image_np = read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False)
            image = torch.from_numpy(image_np[None]).to(device=device, dtype=torch.float32)
            availability = torch.tensor([availability_by_case[case_id]], device=device, dtype=torch.float32)
            logits = sliding_window_logits(model, image, availability, patch_size=patch_size)
            decoded = decode_care_ase_r2_logits(logits, availability).cpu().numpy().astype(np.uint8)[0]
            np.savez_compressed(out / f"{case_id}_prediction.npz", prediction=decoded)
            case_rows.append(
                {
                    "case_id": case_id,
                    "t2_present": bool(availability_by_case[case_id][1] > 0.5),
                    "prediction_path": str((out / f"{case_id}_prediction.npz").relative_to(REPO_ROOT)),
                }
            )

    write_json(
        out / "outer_once_evaluator_receipt.json",
        {
            "status": "PASS",
            "fold": int(args.fold),
            "checkpoint": str(args.checkpoint),
            "checkpoint_global_step": int(payload["global_optimizer_step"]),
            "w45_permit": permit,
            "decode": "fixed_argmax_t2_present_0_1_2_3_4_5_no_t2_0_1_2_3_5",
            "scar_population": scar_metric_population(outer_cases),
            "pure_edema_population": pure_edema_metric_population(availability_by_case),
            "case_count": len(case_rows),
            "case_rows": case_rows,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
