#!/usr/bin/env python
"""CARE-ASE R2 one-time outer evaluator using canonical full-volume inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.inference.care_ase_r2_decode import pure_edema_metric_population, scar_metric_population
from src.care_myocardium.inference.care_ase_r2_full_volume import predict_care_ase_r2_full_volume_labels
from src.care_myocardium.training.care_ase_trainer import load_care_ase_checkpoint_for_inference


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


def parse_patch_size(text: str) -> tuple[int, int, int]:
    parts = tuple(int(v) for v in text.replace("x", ",").split(",") if v)
    if len(parts) != 3:
        raise ValueError(f"patch size must have three dimensions: {text}")
    return parts


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def assert_outer_permit(args: argparse.Namespace, payload: dict[str, Any]) -> dict[str, Any]:
    permit = json.loads(args.outer_permit.read_text(encoding="utf-8"))
    required = {
        "decision",
        "implementation_source_sha",
        "review_packet_commit_sha",
        "effective_contract_sha256",
        "critical_source_manifest_sha256",
        "checkpoint_sha256",
        "outer_access_authorized",
    }
    missing = sorted(required - set(permit))
    if missing:
        raise RuntimeError(f"outer permit missing fields: {missing}")
    checks = {
        "decision_pass": permit.get("decision") == "OUTER_ONCE_AUTHORIZED_AFTER_W4_5",
        "implementation_source_sha": str(args.implementation_source_sha) == str(permit["implementation_source_sha"]),
        "review_packet_sha": str(args.review_packet_sha) == str(permit["review_packet_commit_sha"]),
        "effective_contract_sha256": str(args.effective_contract_sha256) == str(permit["effective_contract_sha256"]),
        "critical_source_manifest_sha256": str(args.critical_source_manifest_sha256) == str(permit["critical_source_manifest_sha256"]),
        "checkpoint_sha256": sha256_file(args.checkpoint) == str(permit["checkpoint_sha256"]),
        "checkpoint_step14000": int(payload.get("global_optimizer_step", -1)) == 14000 and args.checkpoint.name == "checkpoint_step14000.pt",
        "outer_access_authorized": permit.get("outer_access_authorized") is True,
    }
    failed = sorted(key for key, ok in checks.items() if not ok)
    if failed:
        raise RuntimeError(f"CARE-ASE outer permit failed closed: {failed}")
    return {"status": "PASS", "checks": checks, "permit_sha256": sha256_file(args.outer_permit)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--outer-permit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--implementation-source-sha", required=True)
    parser.add_argument("--review-packet-sha", required=True)
    parser.add_argument("--effective-contract-sha256", required=True)
    parser.add_argument("--critical-source-manifest-sha256", required=True)
    parser.add_argument("--patch-size", default="20,256,256")
    args = parser.parse_args()

    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    patch_size = parse_patch_size(args.patch_size)
    model, payload = load_care_ase_checkpoint_for_inference(args.checkpoint, map_location="cuda" if torch.cuda.is_available() else "cpu")
    permit = assert_outer_permit(args, payload)
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
            decoded = predict_care_ase_r2_full_volume_labels(model, image, availability, patch_size=patch_size).cpu().numpy().astype(np.uint8)[0]
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
            "outer_permit": permit,
            "canonical_full_volume_inference": "src.care_myocardium.inference.care_ase_r2_full_volume",
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
