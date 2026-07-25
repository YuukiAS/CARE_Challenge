#!/usr/bin/env bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=CareSRRAnchor
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=8:00:00
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access

set -euo pipefail

CARE_ROOT="/users/a/e/aereinh/CARE"
cd "${CARE_ROOT}"
source "${CARE_ROOT}/.care-codex-env.sh"
source "${CARE_ROOT}/env_nnunet.sh"

mkdir -p "${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue"
RESULT_ROOT="${CARE_ROOT}/results/20260724_care_myops_srr_cascade_submission_rescue"
ATTEMPT_ID="${ANCHOR_ATTEMPT_ID:-${SLURM_JOB_ID:-local}_${SLURM_JOB_PARTITION:-unknown}}"
RACE_GROUP="${ANCHOR_RACE_GROUP:-care_srr_anchor_direct_all220_20260725_rc2_v1}"
LOCK_DIR="${CARE_ANCHOR_LOCK_DIR:-${RESULT_ROOT}/runtime/anchor_cache_v2.${RACE_GROUP}.winner.lock}"
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/care_myops_srr_cascade_submission_rescue/CareSRRAnchor_${ATTEMPT_ID}_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1

echo "CARE_ROOT=${CARE_ROOT}"
echo "ATTEMPT_ID=${ATTEMPT_ID}"
echo "RACE_GROUP=${RACE_GROUP}"
echo "LOCK_DIR=${LOCK_DIR}"
echo "SLURM_JOB_ID=${SLURM_JOB_ID:-local}"
echo "SLURM_JOB_PARTITION=${SLURM_JOB_PARTITION:-unknown}"
echo "SLURM_JOB_ACCOUNT=${SLURM_JOB_ACCOUNT:-unknown}"
echo "SLURM_JOB_QOS=${SLURM_JOB_QOS:-unknown}"
echo "python=${CARE_ROOT}/envs/env_CARE/bin/python"
nvidia-smi || true

export CARE_ANCHOR_ATTEMPT_ID="${ATTEMPT_ID}"
export CARE_ANCHOR_RACE_GROUP="${RACE_GROUP}"
export CARE_ANCHOR_LOCK_DIR="${LOCK_DIR}"
export CARE_ANCHOR_LOG_FILE="${LOG_FILE}"

"${CARE_ROOT}/envs/env_CARE/bin/python" - <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import socket
from pathlib import Path

import blosc2
import numpy as np
import torch
from scipy.ndimage import distance_transform_edt

from nnunetv2.inference.predict_from_raw_data import nnUNetPredictor

from src.care_myocardium.srr_production.anchor_runtime import (
    anchor_uncertainty,
    canonicalize_probabilities,
    soft_union_probability,
)

ROOT = Path("/users/a/e/aereinh/CARE")
RESULT = ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
MANIFEST = ROOT / "results/srr_production/code_maturity/batch2a_raw_oof_anchor_manifest.json"
PREPROCESSED = ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
FINAL_DIR = RESULT / "runtime/anchor_cache_v2"
ATTEMPT_ID = os.environ.get("CARE_ANCHOR_ATTEMPT_ID", os.environ.get("SLURM_JOB_ID", "local"))
RACE_GROUP = os.environ.get("CARE_ANCHOR_RACE_GROUP", "care_srr_anchor_direct_all220_20260725_rc2_v1")
LOCK_DIR = Path(os.environ["CARE_ANCHOR_LOCK_DIR"])
ATTEMPT_DIR = RESULT / "runtime" / f"anchor_cache_v2_attempt_{ATTEMPT_ID}"
WINNER_RECEIPT = RESULT / f"anchor_cache_v2_race_winner_{ATTEMPT_ID}.json"
LOST_RECEIPT = RESULT / f"anchor_cache_v2_race_lost_{ATTEMPT_ID}.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def claim_winner_lock() -> bool:
    try:
        LOCK_DIR.mkdir(parents=True)
    except FileExistsError:
        write_json(
            LOST_RECEIPT,
            {
                "status": "RACE_LOST",
                "decision": "PASS_EXIT_ZERO_NO_OVERWRITE",
                "attempt_id": ATTEMPT_ID,
                "race_group": RACE_GROUP,
                "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
                "partition": os.environ.get("SLURM_JOB_PARTITION", "unknown"),
                "winner_lock_dir": str(LOCK_DIR.relative_to(ROOT)),
                "log_file": os.environ.get("CARE_ANCHOR_LOG_FILE", ""),
            },
        )
        return False
    write_json(
        LOCK_DIR / "winner.json",
        {
            "status": "WINNER_CLAIMED",
            "attempt_id": ATTEMPT_ID,
            "race_group": RACE_GROUP,
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
            "partition": os.environ.get("SLURM_JOB_PARTITION", "unknown"),
            "hostname": socket.gethostname(),
            "log_file": os.environ.get("CARE_ANCHOR_LOG_FILE", ""),
        },
    )
    return True


def canonical_distance(mask: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray:
    if mask.any():
        return distance_transform_edt(~mask.astype(bool), sampling=spacing).astype(np.float32)
    return np.full(mask.shape, 999.0, dtype=np.float32)


def load_predictor(model_dir: Path, fold: int, device: torch.device) -> nnUNetPredictor:
    predictor = nnUNetPredictor(
        tile_step_size=0.5,
        use_gaussian=True,
        use_mirroring=False,
        perform_everything_on_device=True,
        device=device,
        verbose=False,
        verbose_preprocessing=False,
        allow_tqdm=False,
    )
    predictor.initialize_from_trained_model_folder(str(model_dir), use_folds=(int(fold),), checkpoint_name="checkpoint_best.pth")
    predictor.allowed_mirroring_axes = []
    return predictor


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
if device.type != "cuda":
    raise RuntimeError("direct_oof_checkpoint_fallback requires a Slurm GPU allocation")

if not claim_winner_lock():
    print(json.dumps({"decision": "RACE_LOST_EXIT_ZERO", "attempt_id": ATTEMPT_ID}, indent=2), flush=True)
    raise SystemExit(0)

manifest = json.loads(MANIFEST.read_text())
entries = sorted(manifest.get("entries", []), key=lambda item: item["case_id"])
case_ids = sorted({str(entry["case_id"]) for entry in entries})
if len(case_ids) != 220 or len(entries) != 220:
    raise RuntimeError(f"expected 220 OOF entries, got cases={len(case_ids)} entries={len(entries)}")

if ATTEMPT_DIR.exists():
    shutil.rmtree(ATTEMPT_DIR)
ATTEMPT_DIR.mkdir(parents=True)

predictors: dict[int, nnUNetPredictor] = {}
rows: list[dict[str, object]] = []
roundtrip: list[dict[str, object]] = []
for index, entry in enumerate(entries, start=1):
    case_id = str(entry["case_id"])
    fold = int(entry["source_fold"])
    if entry.get("is_oof") is not True:
        raise RuntimeError(f"non-OOF anchor entry: {case_id}")
    ckpt = ROOT / entry["nnunet_checkpoint_path"]
    if sha256_file(ckpt) != entry["checkpoint_sha256"]:
        raise RuntimeError(f"OOF checkpoint sha mismatch: {case_id}")
    if fold not in predictors:
        predictors[fold] = load_predictor(ckpt.parents[1], fold, device)
    image = blosc2.open(str(PREPROCESSED / f"{case_id}.b2nd"), mode="r")[...].astype(np.float32)
    logits = predictors[fold].predict_sliding_window_return_logits(torch.from_numpy(image)).float().cpu().unsqueeze(0)
    probs = torch.softmax(logits, dim=1)
    canonical_logits, canonical_probs = canonicalize_probabilities(probs)
    union = soft_union_probability(canonical_probs)
    spacing = tuple(float(v) for v in predictors[fold].configuration_manager.spacing)
    union_mask = (canonical_probs[:, 1:2] + canonical_probs[:, 4:5] + canonical_probs[:, 5:6])[0, 0].numpy() > 0.5
    distance = canonical_distance(union_mask, spacing)
    payload = {
        "schema_version": 2,
        "case_id": case_id,
        "source_semantics": "five_fold_OOF_only",
        "builder": "direct_oof_checkpoint_fallback",
        "source_fold": fold,
        "is_oof": True,
        "nnunet_checkpoint_path": entry["nnunet_checkpoint_path"],
        "checkpoint_sha256": entry["checkpoint_sha256"],
        "canonical_anchor_logits": canonical_logits.squeeze(0).contiguous(),
        "canonical_anchor_probabilities": canonical_probs.squeeze(0).contiguous(),
        "anchor_uncertainty": anchor_uncertainty(canonical_probs).squeeze(0).contiguous(),
        "soft_union_probability": union.squeeze(0).contiguous(),
        "distance_to_union_mm": torch.from_numpy(distance).unsqueeze(0).contiguous(),
        "plans_configuration": "nnUNetPlans:3d_fullres direct checkpoint predictor",
        "tile_step_size": 0.5,
        "gaussian": True,
        "mirror_axes": [],
    }
    cache_path = ATTEMPT_DIR / f"{case_id}__anchor.pt"
    torch.save(payload, cache_path)
    loaded = torch.load(cache_path, map_location="cpu", weights_only=True)
    changed = int(
        (
            loaded["canonical_anchor_probabilities"].argmax(0).numpy().astype(np.int16)
            != canonical_probs.squeeze(0).argmax(0).numpy().astype(np.int16)
        ).sum()
    )
    sum_error = float((canonical_probs.sum(dim=1) - 1.0).abs().max().item())
    decision = "PASS" if changed == 0 and sum_error <= 1e-5 else "NEEDS_REPAIR"
    rel_cache = (FINAL_DIR / cache_path.name).relative_to(ROOT)
    rows.append(
        {
            "case_id": case_id,
            "source_fold": fold,
            "is_oof": True,
            "builder": "direct_oof_checkpoint_fallback",
            "nnunet_checkpoint_path": entry["nnunet_checkpoint_path"],
            "checkpoint_sha256": entry["checkpoint_sha256"],
            "cache_path": str(rel_cache),
            "cache_sha256": sha256_file(cache_path),
            "preprocessed_shape": "x".join(map(str, image.shape[1:])),
            "probability_sum_max_abs_error": f"{sum_error:.8g}",
            "decision": decision,
        }
    )
    roundtrip.append(
        {
            "case_id": case_id,
            "source_fold": fold,
            "builder": "direct_oof_checkpoint_fallback",
            "preprocessed_shape": "x".join(map(str, image.shape[1:])),
            "roundtrip_scope": "preprocessed_grid_direct_inference_cache_write_load",
            "changed_voxels": changed,
            "decision": decision,
        }
    )
    if index % 10 == 0 or index == len(entries):
        print(f"anchor direct fallback {index}/220", flush=True)

if any(row["decision"] != "PASS" for row in rows):
    write_csv(RESULT / "anchor_cache_manifest_v2.failed.csv", rows)
    write_csv(RESULT / "anchor_cache_roundtrip_v2.failed.csv", roundtrip)
    raise RuntimeError("direct anchor fallback failed roundtrip")

backup = None
if FINAL_DIR.exists():
    backup = RESULT / "runtime" / f"anchor_cache_v2_superseded_by_{ATTEMPT_ID}"
    if backup.exists():
        shutil.rmtree(backup)
    FINAL_DIR.rename(backup)
ATTEMPT_DIR.rename(FINAL_DIR)
write_csv(RESULT / "anchor_cache_manifest_v2.csv", rows)
write_csv(RESULT / "anchor_cache_roundtrip_v2.csv", roundtrip)
receipt = {
    "decision": "PASS",
    "builder": "direct_oof_checkpoint_fallback",
    "case_count": len(rows),
    "cache_file_count": len(list(FINAL_DIR.glob("*__anchor.pt"))),
    "manifest_rows": len(rows),
    "roundtrip_rows": len(roundtrip),
    "roundtrip_changed_voxels_max": max(int(row["changed_voxels"]) for row in roundtrip),
    "manifest_sha256": sha256_file(RESULT / "anchor_cache_manifest_v2.csv"),
    "roundtrip_sha256": sha256_file(RESULT / "anchor_cache_roundtrip_v2.csv"),
    "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
    "partition": os.environ.get("SLURM_JOB_PARTITION", "unknown"),
    "attempt_id": ATTEMPT_ID,
    "race_group": RACE_GROUP,
    "winner_lock_dir": str(LOCK_DIR.relative_to(ROOT)),
    "log_file": os.environ.get("CARE_ANCHOR_LOG_FILE", ""),
    "superseded_previous_final_cache_dir": str(backup.relative_to(ROOT)) if backup is not None else "",
}
(RESULT / "anchor_cache_hashes_v2.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
write_json(WINNER_RECEIPT, receipt)
print(json.dumps(receipt, indent=2, sort_keys=True))
PY
