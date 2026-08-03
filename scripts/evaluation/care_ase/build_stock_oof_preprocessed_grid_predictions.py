#!/usr/bin/env python
"""Generate canonical stock nnU-Net OOF predictions on the preprocessed grid.

This producer never reads original-space NIfTI predictions. It loads each
actual-train case's preprocessed `.b2nd` CZYX tensor, selects the patient-held-out
stock fold from `splits_final.json`, runs the stock nnU-Net predictor directly on
that tensor, and writes only lightweight receipts plus optional temporary arrays.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_ase_splits import PREPROCESSED_REL, SPLITS_REL, build_care_ase_case_roles


RESULT_TASK = "20260803_care_ase_r2_final_pretraining_closure_v8"
STOCK_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_array(array: np.ndarray) -> str:
    arr = np.ascontiguousarray(array)
    h = hashlib.sha256()
    h.update(str(arr.dtype).encode("utf-8"))
    h.update(json.dumps(list(arr.shape)).encode("utf-8"))
    h.update(arr.tobytes())
    return h.hexdigest()


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_json(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_preprocessed_geometry(preprocessed: Path, case_id: str, shape: tuple[int, int, int]) -> dict[str, Any]:
    props_path = preprocessed / f"{case_id}.pkl"
    props: dict[str, Any] = {}
    if props_path.is_file():
        import pickle

        with props_path.open("rb") as f:
            props = pickle.load(f)
    plans_path = preprocessed.parent / "nnUNetPlans.json"
    if plans_path.is_file():
        plans = json.loads(plans_path.read_text(encoding="utf-8"))
        spacing = tuple(float(v) for v in plans["configurations"]["3d_fullres"]["spacing"])
        return {
            "shape_zyx": list(shape),
            "spacing_zyx": list(spacing),
            "spacing_source": str(plans_path.relative_to(REPO_ROOT)),
            "source_spacing_zyx": list(tuple(float(v) for v in props.get("spacing", spacing))),
            "bbox_used_for_cropping": props.get("bbox_used_for_cropping"),
            "shape_before_cropping": props.get("shape_before_cropping"),
            "shape_after_cropping_and_before_resampling": props.get("shape_after_cropping_and_before_resampling"),
        }
    spacing = (1.0, 1.0, 1.0)
    if props:
        spacing = tuple(float(v) for v in props.get("spacing", spacing))
    return {"shape_zyx": list(shape), "spacing_zyx": list(spacing)}


def held_out_source_fold(case_id: str, splits: list[dict[str, Any]]) -> int:
    matches = [idx for idx, split in enumerate(splits) if case_id in {str(v) for v in split.get("val", [])}]
    if len(matches) != 1:
        raise RuntimeError(f"case {case_id} must appear in exactly one stock validation fold, observed={matches}")
    return int(matches[0])


def write_npz_atomic(path: Path, **arrays: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    np.savez_compressed(tmp, **arrays)
    os.replace(tmp.with_suffix(tmp.suffix + ".npz"), path)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_predictor(source_fold: int, *, device: torch.device) -> nnUNetPredictor:
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=True,
        perform_everything_on_device=device.type == "cuda",
        device=device,
        verbose=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(
        str(STOCK_ROOT),
        use_folds=(int(source_fold),),
        checkpoint_name="checkpoint_final.pth",
    )
    return predictor


def predict_case(
    case_id: str,
    source_fold: int,
    *,
    out_array_dir: Path,
    device: torch.device,
    predictor: nnUNetPredictor | None = None,
) -> dict[str, Any]:
    preprocessed = REPO_ROOT / PREPROCESSED_REL
    image_path = preprocessed / f"{case_id}.b2nd"
    seg_path = preprocessed / f"{case_id}_seg.b2nd"
    plans_path = preprocessed.parent / "nnUNetPlans.json"
    checkpoint_path = STOCK_ROOT / f"fold_{source_fold}" / "checkpoint_final.pth"
    if not image_path.is_file() or not seg_path.is_file():
        raise FileNotFoundError(f"missing preprocessed image/seg for {case_id}")
    if not checkpoint_path.is_file():
        raise FileNotFoundError(f"missing source stock checkpoint: {checkpoint_path}")
    image = np.asarray(blosc2.open(str(image_path), mode="r")[:]).astype(np.float32, copy=False)
    seg = np.asarray(blosc2.open(str(seg_path), mode="r")[:])[0]
    if image.ndim != 4:
        raise RuntimeError(f"preprocessed image must be CZYX, got {image.shape} for {case_id}")
    predictor = predictor or build_predictor(source_fold, device=device)
    with torch.inference_mode():
        logits = predictor.predict_logits_from_preprocessed_data(torch.from_numpy(image).to(device=device, dtype=torch.float32))
        probs = torch.softmax(logits.float(), dim=0).cpu().numpy().astype(np.float32, copy=False)
    argmax = np.asarray(np.argmax(probs, axis=0), dtype=np.uint8)
    if tuple(argmax.shape) != tuple(seg.shape):
        raise RuntimeError(f"direct stock OOF argmax shape mismatch for {case_id}: {argmax.shape} != {seg.shape}")
    prob_path = out_array_dir / f"{case_id}.npz"
    argmax_path = out_array_dir / f"{case_id}_argmax.npy"
    write_npz_atomic(prob_path, probabilities=probs)
    argmax_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(argmax_path, argmax)
    probability_sha = sha256_file(prob_path)
    argmax_sha = sha256_file(argmax_path)
    preprocessed_geometry = load_preprocessed_geometry(preprocessed, case_id, tuple(int(v) for v in argmax.shape))
    preprocessed_geometry_sha = sha256_json(preprocessed_geometry)
    return {
        "case_id": case_id,
        "prediction_exists": True,
        "prediction_path": display_path(argmax_path),
        "prediction_sha256": argmax_sha,
        "probability_exists": True,
        "probability_path": display_path(prob_path),
        "probability_sha256": probability_sha,
        "probability_shape_CZYX": list(probs.shape),
        "argmax_shape_ZYX": list(argmax.shape),
        "argmax_sha256": argmax_sha,
        "source_fold": int(source_fold),
        "source_stock_fold": int(source_fold),
        "source_checkpoint_path": str(checkpoint_path.relative_to(REPO_ROOT)),
        "source_checkpoint_sha256": sha256_file(checkpoint_path),
        "source_preprocessed_image_path": str(image_path.relative_to(REPO_ROOT)),
        "source_preprocessed_image_sha256": sha256_file(image_path),
        "plans_path": str(plans_path.relative_to(REPO_ROOT)),
        "plans_sha256": sha256_file(plans_path),
        "producer_source_commit_sha": git_sha(),
        "producer_command": "scripts/evaluation/care_ase/build_stock_oof_preprocessed_grid_predictions.py",
        "producer_stage": "direct_preprocessed_grid_inference",
        "producer_binding_method": "direct_stock_inference_on_preprocessed_grid",
        "preprocessed_grid_binding": True,
        "preprocessed_shape": list(argmax.shape),
        "preprocessed_geometry": preprocessed_geometry,
        "preprocessed_geometry_sha256": preprocessed_geometry_sha,
        "transform_or_exact_array_binding": {
            "binding": "direct_stock_inference_on_preprocessed_grid",
            "preprocessed_grid_binding": True,
            "preprocessed_shape": list(argmax.shape),
            "preprocessed_geometry": preprocessed_geometry,
            "preprocessed_geometry_sha256": preprocessed_geometry_sha,
        },
        "proof_case_not_in_source_fold_train": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--array-dir", type=Path, default=None)
    parser.add_argument("--case-limit", type=int, default=None)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("direct preprocessed-grid stock OOF producer requires CUDA when --device cuda")
    device = torch.device(args.device)
    output = args.output or REPO_ROOT / "results" / RESULT_TASK / f"direct_stock_oof_preprocessed_grid_fold{args.fold}.json"
    array_dir = args.array_dir or Path("/users/a/e/aereinh/.tmp/codex-CARE") / RESULT_TASK / "stock_oof_preprocessed_grid" / f"fold_{args.fold}"
    splits = load_json(REPO_ROOT / SPLITS_REL)
    rows = [row for row in build_care_ase_case_roles(REPO_ROOT, int(args.fold)) if row.role == "actual-train"]
    if args.case_limit is not None:
        rows = rows[: int(args.case_limit)]
    entries = []
    checkpoints: dict[str, dict[str, Any]] = {}
    predictors: dict[int, nnUNetPredictor] = {}
    for row in rows:
        source_fold = held_out_source_fold(row.case_id, splits)
        if source_fold not in predictors:
            predictors[source_fold] = build_predictor(source_fold, device=device)
        entry = predict_case(row.case_id, source_fold, out_array_dir=array_dir, device=device, predictor=predictors[source_fold])
        entries.append(entry)
        checkpoints[str(source_fold)] = {
            "checkpoint_final_path": entry["source_checkpoint_path"],
            "checkpoint_final_sha256": entry["source_checkpoint_sha256"],
        }
    payload = {
        "status": "PASS",
        "task_key": RESULT_TASK,
        "schema_version": 1,
        "producer_stage": "direct_preprocessed_grid_inference",
        "binding_method": "direct_stock_inference_on_preprocessed_grid",
        "fold": int(args.fold),
        "case_count": len(entries),
        "entries": entries,
        "checkpoints": checkpoints,
        "arrays_runtime_dir": str(array_dir),
    }
    payload["payload_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "output": str(output), "case_count": len(entries)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
