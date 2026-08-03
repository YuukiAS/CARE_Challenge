#!/usr/bin/env python
"""CARE-ASE R2 one-time outer evaluator.

This entrypoint is deliberately fail-closed before W4.5. It exists during G1 so
the implementation has a fixed evaluator/decode path, but it refuses to touch
fold1/fold4 outer data unless the pre-outer snapshot push receipt is present.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
import torch.nn.functional as F

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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _fsync_file(path: Path) -> None:
    with path.open("rb") as f:
        os.fsync(f.fileno())


def _fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    _fsync_file(tmp)
    os.replace(tmp, path)
    _fsync_dir(path.parent)


def _fold_checkpoint_entry(receipt: dict[str, Any], fold: int) -> dict[str, Any]:
    fold_key = str(int(fold))
    for key in ("fold_checkpoints", "folds", "checkpoints"):
        table = receipt.get(key)
        if isinstance(table, dict):
            entry = table.get(fold_key) or table.get(f"fold{fold_key}") or table.get(f"fold_{fold_key}")
            if isinstance(entry, dict):
                return entry
    rows = receipt.get("fold_checkpoint_rows", receipt.get("checkpoint_rows", []))
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and int(row.get("fold", -1)) == int(fold):
                return row
    raise RuntimeError(f"W4.5 permit does not bind fold {fold} checkpoint")


def assert_w45_permit(*, fold: int, checkpoint: Path, payload: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    if not W45_PUSH_RECEIPT.is_file():
        raise RuntimeError("W5 outer evaluation forbidden before W4.5 snapshot push receipt")
    receipt = json.loads(W45_PUSH_RECEIPT.read_text(encoding="utf-8"))
    if receipt.get("status") != "PASS" or not receipt.get("push_verified", False):
        raise RuntimeError("W4.5 snapshot push receipt is not PASS/push_verified")
    if int(payload.get("global_optimizer_step", -1)) != 14000:
        raise RuntimeError(f"outer evaluation requires checkpoint global_optimizer_step == 14000, got {payload.get('global_optimizer_step')}")
    if checkpoint.name != "checkpoint_step14000.pt":
        raise RuntimeError("outer evaluation requires fixed checkpoint_step14000.pt")
    entry = _fold_checkpoint_entry(receipt, fold)
    checkpoint_sha = sha256_file(checkpoint)
    expected_sha = str(entry.get("checkpoint_sha256", entry.get("sha256", "")))
    expected_step = int(entry.get("global_optimizer_step", entry.get("checkpoint_step", -1)))
    expected_path = str(entry.get("checkpoint_path", entry.get("path", "")))
    if expected_step != 14000:
        raise RuntimeError(f"W4.5 permit fold {fold} checkpoint step is not 14000: {expected_step}")
    if expected_sha != checkpoint_sha:
        raise RuntimeError(f"W4.5 permit fold {fold} checkpoint SHA mismatch")
    if expected_path and Path(expected_path).name != "checkpoint_step14000.pt":
        raise RuntimeError(f"W4.5 permit fold {fold} checkpoint path is not checkpoint_step14000.pt: {expected_path}")
    token_root = RESULT_ROOT / "outer_once" / "consumed_permits"
    token_root.mkdir(parents=True, exist_ok=True)
    token = token_root / f"fold{int(fold)}_{checkpoint_sha}.json"
    try:
        fd = os.open(token, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise RuntimeError(f"outer permit already consumed for fold {fold} checkpoint {checkpoint_sha}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(
            {
                "status": "CONSUMED",
                "fold": int(fold),
                "checkpoint_sha256": checkpoint_sha,
                "checkpoint_path": str(checkpoint),
                "output_dir": str(output_dir),
                "created_unix": int(time.time()),
            },
            f,
            indent=2,
            sort_keys=True,
        )
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    _fsync_dir(token_root)
    return {**receipt, "fold_checkpoint_entry": entry, "consumed_permit_token": str(token), "checkpoint_sha256_verified": checkpoint_sha}


def parse_patch_size(text: str) -> tuple[int, int, int]:
    parts = tuple(int(v) for v in text.replace("x", ",").split(",") if v)
    if len(parts) != 3:
        raise ValueError(f"patch size must have three dimensions: {text}")
    return parts


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def _pad_patch_to_size(patch: torch.Tensor, patch_size: tuple[int, int, int]) -> tuple[torch.Tensor, tuple[int, int, int]]:
    actual = tuple(int(v) for v in patch.shape[-3:])
    pads = []
    for have, want in reversed(list(zip(actual, patch_size))):
        pads.extend([0, max(int(want) - int(have), 0)])
    if any(pads):
        patch = F.pad(patch, pads)
    return patch, actual


def sliding_window_logits(model: torch.nn.Module, image: torch.Tensor, availability: torch.Tensor, *, patch_size: tuple[int, int, int], overlap: float = 0.5) -> torch.Tensor:
    spatial = tuple(int(v) for v in image.shape[-3:])
    if all(spatial[i] <= patch_size[i] for i in range(3)):
        patch, actual = _pad_patch_to_size(image, patch_size)
        logits = model(patch, availability, global_step=14000)["final_logits"]
        return logits[..., : actual[0], : actual[1], : actual[2]]
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
                patch_padded, actual = _pad_patch_to_size(patch, patch_size)
                logits = model(patch_padded, availability, global_step=14000)["final_logits"]
                logits = logits[..., : actual[0], : actual[1], : actual[2]]
                out[..., z : z + actual[0], y : y + actual[1], x : x + actual[2]] += logits
                count[..., z : z + actual[0], y : y + actual[1], x : x + actual[2]] += 1.0
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
    out = (args.output_dir or RESULT_ROOT / "outer_once" / f"fold_{args.fold}").resolve()
    out.mkdir(parents=True, exist_ok=True)
    patch_size = parse_patch_size(args.patch_size)
    model, payload = load_care_ase_checkpoint(args.checkpoint, map_location="cuda" if torch.cuda.is_available() else "cpu", restore_rng=False)
    permit = assert_w45_permit(fold=args.fold, checkpoint=args.checkpoint, payload=payload, output_dir=out)
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
