#!/usr/bin/env python
"""Freeze and reload checks for CARE-ASE fixed step14000 checkpoints."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_ase_splits import actual_train_cases, sha256_file
from src.care_myocardium.training.care_ase_trainer import build_optimizer, load_care_ase_checkpoint, write_json


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def crop_or_pad(array: np.ndarray, patch_size: tuple[int, int, int]) -> np.ndarray:
    spatial = array.shape[-3:]
    out_shape = array.shape[:-3] + patch_size
    out = np.zeros(out_shape, dtype=array.dtype)
    src = []
    dst = []
    for dim, size in zip(spatial, patch_size):
        src_start = max(0, (dim - size) // 2)
        src_stop = min(dim, src_start + size)
        dst_start = max(0, (size - dim) // 2)
        dst_stop = dst_start + (src_stop - src_start)
        src.append(slice(src_start, src_stop))
        dst.append(slice(dst_start, dst_stop))
    out[(..., *dst)] = array[(..., *src)]
    return out


def load_actual_train_sample(fold: int, patch_size: tuple[int, int, int], device: torch.device) -> tuple[str, torch.Tensor, torch.Tensor]:
    case_id, availability = actual_train_cases(REPO_ROOT, fold, complete_only=True)[0]
    image = crop_or_pad(read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False), patch_size)
    return case_id, torch.from_numpy(image[None]).to(device=device, dtype=torch.float32), torch.tensor([availability], device=device, dtype=torch.float32)


def max_state_delta(a: dict[str, torch.Tensor], b: dict[str, torch.Tensor]) -> float:
    return max(float((a[key].detach().cpu() - b[key].detach().cpu()).abs().max()) for key in a)


def check_fold(fold: int, patch_size: tuple[int, int, int], device: torch.device) -> dict[str, Any]:
    runtime = RESULT_DIR / "runtime" / f"fold_{fold}"
    checkpoint = runtime / "checkpoint_step14000.pt"
    terminal = runtime / "training_terminal_receipt.json"
    start = runtime / "training_start_receipt.json"
    if not checkpoint.exists() or not terminal.exists() or not start.exists():
        return {"fold": int(fold), "status": "FAIL", "reason": "missing terminal checkpoint/start/terminal receipt"}
    terminal_payload = json.loads(terminal.read_text(encoding="utf-8"))
    start_payload = json.loads(start.read_text(encoding="utf-8"))
    model_a, payload_a = load_care_ase_checkpoint(checkpoint, map_location="cpu", restore_rng=True)
    model_b, payload_b = load_care_ase_checkpoint(checkpoint, map_location="cpu", restore_rng=False)
    optimizer = build_optimizer(model_a)
    optimizer.load_state_dict(payload_a["optimizer_state_dict"])
    state_delta = max_state_delta(model_a.state_dict(), payload_a["model_state_dict"])
    case_id, image, availability = load_actual_train_sample(fold, patch_size, device)
    model_a.to(device).eval()
    model_b.to(device).eval()
    with torch.no_grad():
        logits_a = model_a(image, availability, global_step=14000)["final_logits"].detach().cpu()
        logits_b = model_b(image, availability, global_step=14000)["final_logits"].detach().cpu()
    reload_delta = float((logits_a - logits_b).abs().max())
    ok = (
        int(payload_a["global_optimizer_step"]) == 14000
        and int(payload_a["microbatch_cursor"]) == 0
        and bool(payload_a.get("optimizer_state_dict"))
        and bool(payload_a.get("rng_state"))
        and math.isclose(float(payload_a["extent_wall_ramp_value"]), 1.0)
        and terminal_payload.get("status") == "PASS"
        and start_payload.get("inner_excluded") is True
        and state_delta == 0.0
        and reload_delta == 0.0
    )
    return {
        "fold": int(fold),
        "status": "PASS" if ok else "FAIL",
        "checkpoint_path": str(checkpoint.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint),
        "checkpoint_size_bytes": checkpoint.stat().st_size,
        "global_optimizer_step": int(payload_a["global_optimizer_step"]),
        "microbatch_cursor": int(payload_a["microbatch_cursor"]),
        "stage_id": payload_a.get("stage_id"),
        "extent_wall_ramp_value": float(payload_a["extent_wall_ramp_value"]),
        "has_optimizer_state": "optimizer_state_dict" in payload_a,
        "optimizer_state_loaded": True,
        "scheduler_state": "none_static_lr_contract",
        "has_rng_state": "rng_state" in payload_a,
        "batch_cursor_state": int(payload_a["microbatch_cursor"]),
        "next_batch_hash": payload_a.get("next_batch_hash"),
        "inner_excluded": start_payload.get("inner_excluded") is True,
        "model_state_reload_max_abs_error": state_delta,
        "full_reload_parity_case_id": case_id,
        "full_reload_final_logits_max_abs_error": reload_delta,
        "payloads_identical_step": payload_a["global_optimizer_step"] == payload_b["global_optimizer_step"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--patch-size", default="20,256,256")
    args = parser.parse_args()
    patch_size = tuple(int(v) for v in args.patch_size.replace("x", ",").split(",") if v)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    outer_receipts = sorted((RESULT_DIR / "outer_eval").glob("fold_*/evaluation_receipt.json")) if (RESULT_DIR / "outer_eval").exists() else []
    fold_rows = [check_fold(fold, patch_size, device) for fold in (2, 3)]
    freeze = {
        "status": "PASS" if all(row["status"] == "PASS" for row in fold_rows) else "FAIL",
        "folds": fold_rows,
        "fixed_checkpoint_name": "checkpoint_step14000.pt",
        "no_checkpoint_selection": True,
        "outer_access_count_before_freeze": len(outer_receipts),
        "outer_access_receipts_before_freeze": [str(path.relative_to(REPO_ROOT)) for path in outer_receipts],
    }
    reload_receipt = {
        "status": freeze["status"],
        "folds": [
            {
                "fold": row["fold"],
                "full_reload_parity_case_id": row.get("full_reload_parity_case_id"),
                "full_reload_final_logits_max_abs_error": row.get("full_reload_final_logits_max_abs_error"),
                "model_state_reload_max_abs_error": row.get("model_state_reload_max_abs_error"),
            }
            for row in fold_rows
        ],
    }
    outer_audit = {
        "status": "PASS" if len(outer_receipts) == 0 else "FAIL",
        "outer_access_count_before_freeze": len(outer_receipts),
        "evidence": [str(path.relative_to(REPO_ROOT)) for path in outer_receipts],
    }
    write_json(RESULT_DIR / "checkpoint_freeze_receipt.json", freeze)
    write_json(RESULT_DIR / "full_reload_parity_receipt.json", reload_receipt)
    write_json(RESULT_DIR / "outer_access_audit_receipt.json", outer_audit)
    print(json.dumps({"checkpoint_freeze_receipt": freeze, "full_reload_parity_receipt": reload_receipt, "outer_access_audit_receipt": outer_audit}, indent=2, sort_keys=True, default=str))
    return 0 if freeze["status"] == "PASS" and outer_audit["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
