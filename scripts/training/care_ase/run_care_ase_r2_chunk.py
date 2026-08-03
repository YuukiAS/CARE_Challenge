#!/usr/bin/env python
"""Formal CARE-ASE R2 exact-resume chunk training entrypoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import pickle
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
from scipy.ndimage import label as ndimage_label
from scipy import ndimage
import torch

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.care_ase import build_care_ase_for_fold_with_area_references
from src.care_myocardium.inference.care_ase_r2_decode import decode_care_ase_r2_logits
from src.care_myocardium.training.care_ase_sampler import CAREASEDeterministicSampler, compute_actual_train_area_references
from src.care_myocardium.training.care_ase_trainer import (
    CAREASEStageScheduler,
    build_optimizer,
    care_ase_loss,
    checkpoint_receipt,
    load_care_ase_checkpoint,
    parameter_group_coverage,
    save_care_ase_checkpoint,
    set_stage_trainability,
    write_json,
)


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
SPLITS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
RESULT_DIR = REPO_ROOT / "results/20260803_care_ase_r2_full_fidelity_execution"
CRITICAL_SOURCE_PATHS = (
    "src/care_myocardium/models/care_ase.py",
    "src/care_myocardium/training/care_ase_trainer.py",
    "src/care_myocardium/training/care_ase_sampler.py",
    "src/care_myocardium/inference/care_ase_r2_decode.py",
    "scripts/training/care_ase/run_care_ase_r2_chunk.py",
    "scripts/evaluation/care_ase/build_care_ase_r2_hard_negative_manifest.py",
    "scripts/evaluation/care_ase/evaluate_care_ase_r2_outer.py",
    "jobs/care_ase_r2/run_fold_chunk_htzhulab.sh",
)
INVALIDATED_TRAINING_SOURCE_SHAS = {
    "207f360f22dd4e28fcecd4a22b67ed1af074ab42",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def combined_source_hash() -> str:
    payload = {path: sha256_file(REPO_ROOT / path) for path in CRITICAL_SOURCE_PATHS if (REPO_ROOT / path).is_file()}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def git_sha(ref: str) -> str:
    return subprocess.check_output(["git", "rev-parse", ref], cwd=REPO_ROOT, text=True).strip()


def verify_external_review_permit(path: Path) -> dict[str, Any]:
    permit = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "decision",
        "reviewed_candidate_commit_sha",
        "origin_main_sha",
        "implementation_source_sha",
        "semantic_reviewer_sha",
        "effective_contract_sha256",
        "created_utc",
    }
    missing = sorted(required - set(permit))
    if missing:
        raise RuntimeError(f"external review permit missing fields: {missing}")
    if permit["decision"] != "PRETRAINING_EXTERNAL_REVIEW_PASS":
        raise RuntimeError(f"external review permit decision is not PASS: {permit['decision']}")
    head = git_sha("HEAD")
    origin = git_sha("origin/main")
    compared = {
        str(permit["reviewed_candidate_commit_sha"]),
        str(permit["origin_main_sha"]),
        str(permit["implementation_source_sha"]),
        str(permit["semantic_reviewer_sha"]),
        head,
        origin,
    }
    if len(compared) != 1:
        raise RuntimeError(f"external review permit SHA mismatch: {sorted(compared)}")
    if head in INVALIDATED_TRAINING_SOURCE_SHAS:
        raise RuntimeError(f"invalidated training source is permanently refused: {head}")
    permit["current_head_sha"] = head
    permit["current_origin_main_sha"] = origin
    permit["permit_verified_for_formal_training"] = True
    return permit


def _slurm_job_is_live(job_id: str) -> bool:
    if not job_id or job_id == "local":
        return False
    try:
        state = subprocess.check_output(
            ["squeue", "-h", "-j", str(job_id), "-o", "%T"],
            cwd=REPO_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        ).strip()
    except Exception:
        return False
    return bool(state) and state.splitlines()[0].strip() in {"PENDING", "CONFIGURING", "RUNNING", "COMPLETING"}


def _local_pid_is_live(pid: Any) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def acquire_chunk_lock(lock_dir: Path, out_dir: Path, *, fold: int, start_step: int, end_step: int) -> dict[str, Any]:
    owner_payload = {
        "pid": os.getpid(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "fold": int(fold),
        "start_step": int(start_step),
        "end_step": int(end_step),
        "created_unix": int(time.time()),
    }
    try:
        lock_dir.mkdir()
        write_json(lock_dir / "owner.json", owner_payload)
        return {"status": "ACQUIRED", "recovered_stale_lock": False, "owner": owner_payload}
    except FileExistsError:
        owner_path = lock_dir / "owner.json"
        owner = json.loads(owner_path.read_text(encoding="utf-8")) if owner_path.is_file() else {}
        terminal = out_dir / f"chunk_terminal_{start_step:05d}_{end_step:05d}.json"
        terminal_status = json.loads(terminal.read_text(encoding="utf-8")).get("status") if terminal.is_file() else None
        live_owner = _slurm_job_is_live(str(owner.get("slurm_job_id", ""))) or (
            str(owner.get("slurm_job_id", "local")) == "local" and _local_pid_is_live(owner.get("pid"))
        )
        if live_owner and terminal_status != "PASS":
            write_json(
                out_dir / f"lock_lost_{os.getpid()}_{start_step:05d}_{end_step:05d}.json",
                {"status": "LOCK_HELD", "owner": owner, "terminal_status": terminal_status, "live_owner": True},
            )
            raise RuntimeError(f"active chunk lock is held by live owner: {owner}")
        archive_root = out_dir / "stale_locks"
        archive_root.mkdir(parents=True, exist_ok=True)
        archive = archive_root / f"{lock_dir.name}_{int(time.time())}_{os.getpid()}"
        shutil.move(str(lock_dir), str(archive))
        write_json(
            out_dir / f"stale_lock_recovered_{start_step:05d}_{end_step:05d}.json",
            {"status": "PASS", "archived_lock": str(archive), "owner": owner, "terminal_status": terminal_status, "live_owner": live_owner},
        )
        lock_dir.mkdir()
        write_json(lock_dir / "owner.json", owner_payload)
        return {"status": "ACQUIRED", "recovered_stale_lock": True, "archived_lock": str(archive), "previous_owner": owner, "owner": owner_payload}


def parse_patch_size(text: str) -> tuple[int, int, int]:
    parts = tuple(int(v) for v in text.replace("x", ",").split(",") if v)
    if len(parts) != 3:
        raise ValueError(f"patch size must have 3 dimensions, got {text}")
    return parts


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def crop_or_pad(array: np.ndarray, center: tuple[int, int, int], patch_size: tuple[int, int, int]) -> np.ndarray:
    spatial = array.shape[-3:]
    src_slices: list[slice] = []
    dst_slices: list[slice] = []
    for c, dim, size in zip(center, spatial, patch_size):
        start = int(c) - size // 2
        stop = start + size
        src_start = max(0, start)
        src_stop = min(dim, stop)
        dst_start = src_start - start
        dst_stop = dst_start + (src_stop - src_start)
        src_slices.append(slice(src_start, src_stop))
        dst_slices.append(slice(dst_start, dst_stop))
    out = np.zeros(array.shape[:-3] + patch_size, dtype=array.dtype)
    out[(..., *dst_slices)] = array[(..., *src_slices)]
    return out


def deterministic_center(
    seg: np.ndarray,
    *,
    descriptor_sha: str,
    pathology_focus: str,
    within_focus: str,
    hard_negative_category: str,
    resolved_target_coordinates: tuple[tuple[int, int, int], ...],
    fallback_sequence: tuple[str, ...],
    micro: int,
    patch_size: tuple[int, int, int],
    spacing: tuple[float, float, float],
) -> tuple[int, int, int]:
    if resolved_target_coordinates:
        idx = int(hashlib.sha256(f"{descriptor_sha}|coords|micro={micro}".encode("utf-8")).hexdigest()[:16], 16) % len(resolved_target_coordinates)
        return tuple(int(v) for v in resolved_target_coordinates[idx])
    wall = (seg == 1) | (seg == 4) | (seg == 5)
    blood = (seg == 2) | (seg == 3)
    pathology = (seg == 4) | (seg == 5)
    background = seg == 0
    scar = seg == 5
    edema = seg == 4
    lesion = scar if pathology_focus == "scar" else edema
    labels, count = ndimage_label(lesion)
    small_component = np.zeros_like(lesion, dtype=bool)
    if count > 0:
        component_ids = list(range(1, count + 1))
        physical_volumes = {idx: float((labels == idx).sum() * np.prod(spacing)) for idx in component_ids}
        small_ids = [idx for idx in component_ids if physical_volumes[idx] < 1000.0]
        if small_ids:
            chosen = small_ids[int(hashlib.sha256(f"{descriptor_sha}|small_component|micro={micro}".encode("utf-8")).hexdigest()[:16], 16) % len(small_ids)]
            small_component = labels == chosen
    gt_component = lesion
    if count > 0:
        component_ids = list(range(1, count + 1))
        chosen = component_ids[int(hashlib.sha256(f"{descriptor_sha}|gt_component|micro={micro}".encode("utf-8")).hexdigest()[:16], 16) % len(component_ids)]
        gt_component = labels == chosen
    dist_wall = ndimage.distance_transform_edt(~wall, sampling=spacing)
    dist_blood = ndimage.distance_transform_edt(~blood, sampling=spacing)
    remote_background = background & (dist_wall >= 10.0)
    blood_pool_adjacent = (~pathology) & (dist_blood <= 3.0)
    if edema.any() and not edema.all():
        raw_edema_boundary_mm = ndimage.distance_transform_edt(edema, sampling=spacing) - ndimage.distance_transform_edt(~edema, sampling=spacing)
        edema_boundary_band = (np.abs(raw_edema_boundary_mm) <= 10.0) | edema
    else:
        edema_boundary_band = np.zeros_like(edema, dtype=bool)
    masks = {
        "gt_component": gt_component,
        "small_component": small_component,
        "oof_fn": gt_component,
        "scar_oof_fn": gt_component,
        "scar_oof_fp": remote_background,
        "oof_fp": remote_background,
        "edema_oof_fn_or_low_volume": gt_component,
        "oof_fn_or_low_volume": gt_component,
        "edema_safe_fp": remote_background,
        "safe_fp": remote_background,
        "positive": lesion,
        "boundary": edema_boundary_band if pathology_focus == "edema" else wall,
        "remote_background": remote_background,
        "blood_pool_adjacent": blood_pool_adjacent,
        "random_wall": wall,
        "random_background": background,
        "background": background,
        "random": wall | background,
    }
    mask = np.zeros_like(lesion, dtype=bool)
    for item in (hard_negative_category, within_focus, *fallback_sequence, "random"):
        candidate = masks.get(str(item), mask)
        if bool(candidate.any()):
            mask = candidate
            break
    coords = np.argwhere(mask)
    if coords.size == 0:
        return tuple(int(v // 2) for v in seg.shape)
    idx = int(hashlib.sha256(f"{descriptor_sha}|micro={micro}|{patch_size}".encode("utf-8")).hexdigest()[:16], 16) % len(coords)
    return tuple(int(v) for v in coords[idx])


def make_batch(descriptor: Any, *, descriptor_sha: str, micro: int, patch_size: tuple[int, int, int], device: torch.device) -> dict[str, torch.Tensor]:
    image = read_b2nd(PREPROCESSED / f"{descriptor.case_id}.b2nd").astype(np.float32, copy=False)
    seg = read_b2nd(PREPROCESSED / f"{descriptor.case_id}_seg.b2nd")[0].astype(np.int64, copy=False)
    spacing = (1.0, 1.0, 1.0)
    properties_path = PREPROCESSED / f"{descriptor.case_id}.pkl"
    if properties_path.is_file():
        with properties_path.open("rb") as f:
            spacing = tuple(float(v) for v in pickle.load(f).get("spacing", spacing))
    center = deterministic_center(
        seg,
        descriptor_sha=descriptor_sha,
        pathology_focus=descriptor.pathology_focus,
        within_focus=descriptor.within_focus,
        hard_negative_category=descriptor.hard_negative_category,
        resolved_target_coordinates=descriptor.resolved_target_coordinates,
        fallback_sequence=descriptor.fallback_sequence,
        micro=micro,
        patch_size=patch_size,
        spacing=spacing,
    )
    return {
        "image": torch.from_numpy(crop_or_pad(image, center, patch_size)[None]).to(device=device, dtype=torch.float32),
        "seg": torch.from_numpy(crop_or_pad(seg[None], center, patch_size)[0][None]).to(device=device, dtype=torch.long),
        "availability": torch.tensor([descriptor.availability], device=device, dtype=torch.float32),
        "spacing": torch.tensor([spacing], device=device, dtype=torch.float32),
    }


def append_csv(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _load_previous(path: Path, device: torch.device) -> tuple[torch.nn.Module, dict[str, Any]]:
    model, payload = load_care_ase_checkpoint(path, map_location=device, restore_rng=True)
    source_sha = str(payload.get("training_source_commit_sha", payload.get("config", {}).get("training_source_commit_sha", "")))
    if source_sha in INVALIDATED_TRAINING_SOURCE_SHAS:
        raise RuntimeError(f"refusing resume from invalidated source checkpoint: {source_sha}")
    return model.to(device), payload


def _sampler_state_from_checkpoint_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_group_cursor": payload["case_group_cursor"],
        "complete_center_selector_cursor": payload.get("complete_center_selector_cursor", payload.get("complete_center_cursor", payload.get("center_cursor", 0))),
        "complete_centerB_case_cursor": payload.get("complete_centerB_case_cursor", 0),
        "complete_centerC_case_cursor": payload.get("complete_centerC_case_cursor", 0),
        "complete_center_cursor": payload.get("complete_center_cursor", payload.get("center_cursor", 0)),
        "complete_pathology_cursor": payload.get("complete_pathology_cursor", payload.get("pathology_focus_cursor", 0)),
        "partial_case_cursors": payload.get("partial_case_cursors", {"lge_only": 0, "lge_c0": 0}),
        "micro_case_cursors_by_group": payload.get("micro_case_cursors_by_group", {}),
        "micro_patch_cursor": payload.get("micro_patch_cursor", 0),
        "center_cursor": payload.get("center_cursor", payload.get("complete_center_cursor", 0)),
        "pathology_focus_cursor": payload.get("pathology_focus_cursor", payload.get("complete_pathology_cursor", 0)),
        "scar_focus_cursor": payload["scar_focus_cursor"],
        "edema_focus_cursor": payload["edema_focus_cursor"],
        "sampler_rng_state": payload["sampler_rng_state"],
        "batch_descriptor_cursor": payload["batch_descriptor_cursor"],
    }


def _write_full_reload_receipt(
    ckpt: Path,
    *,
    live_model: torch.nn.Module,
    live_optimizer: torch.optim.Optimizer,
    live_scheduler: CAREASEStageScheduler,
    fixed_batch: dict[str, torch.Tensor],
    global_step: int,
    fold: int,
    seed: int,
    out_dir: Path,
) -> dict[str, Any]:
    was_training = live_model.training
    live_model.eval()
    with torch.no_grad():
        live_logits = live_model(fixed_batch["image"], fixed_batch["availability"], global_step=global_step)["final_logits"].detach().float().cpu()
    if was_training:
        live_model.train()
    reloaded_model, payload = load_care_ase_checkpoint(ckpt, map_location=fixed_batch["image"].device, restore_rng=False)
    reloaded_model = reloaded_model.to(fixed_batch["image"].device)
    reloaded_optimizer = build_optimizer(reloaded_model)
    reloaded_optimizer.load_state_dict(payload["optimizer"])
    reloaded_scheduler = CAREASEStageScheduler(reloaded_optimizer)
    reloaded_scheduler.load_state_dict(payload["scheduler"])
    reloaded_sampler = CAREASEDeterministicSampler(REPO_ROOT, fold, seed=seed)
    reloaded_sampler.load_state_dict(_sampler_state_from_checkpoint_payload(payload))
    reloaded_model.eval()
    with torch.no_grad():
        reloaded_logits = reloaded_model(fixed_batch["image"], fixed_batch["availability"], global_step=global_step)["final_logits"].detach().float().cpu()
    max_abs = float((live_logits - reloaded_logits).abs().max().item())
    next_hash = "TRAINING_COMPLETE"
    if int(global_step) < 14000:
        next_hash = reloaded_sampler.peek_descriptor_bundle_for_step(global_step).sha256()
    receipt = {
        "status": "PASS" if max_abs <= 1.0e-5 else "FAIL",
        "fold": int(fold),
        "checkpoint_path": str(ckpt),
        "checkpoint_sha256": sha256_file(ckpt),
        "global_optimizer_step": int(global_step),
        "fresh_model_instance_loaded": True,
        "optimizer_state_loaded": bool(reloaded_optimizer.state_dict()["state"] or live_optimizer.state_dict()["state"]),
        "scheduler_state_loaded": reloaded_scheduler.state_dict(),
        "sampler_rng_state_loaded": bool(payload.get("sampler_rng_state")) and payload.get("sampler_rng_state") != "UNSET",
        "dataloader_worker_seed_state_nonempty": bool(payload.get("dataloader_worker_seed_state")),
        "fixed_batch_case_id": fixed_batch.get("case_id", "UNSET"),
        "fixed_batch_descriptor_sha256": fixed_batch.get("descriptor_sha256", "UNSET"),
        "logits_max_abs_error": max_abs,
        "logits_tolerance": 1.0e-5,
        "next_batch_hash_payload": payload.get("next_batch_descriptor_sha256"),
        "next_optimizer_step_micro_descriptor_hash_payload": payload.get("next_optimizer_step_micro_descriptor_sha256"),
        "next_batch_hash_recomputed": next_hash,
        "next_batch_hash_match": payload.get("next_batch_descriptor_sha256") in {next_hash, "TRAINING_COMPLETE"},
        "next_optimizer_step_micro_descriptor_hash_match": payload.get("next_optimizer_step_micro_descriptor_sha256") in {next_hash, "TRAINING_COMPLETE"},
        "live_scheduler_last_global_step": live_scheduler.last_global_step,
    }
    receipt["payload_sha256"] = hashlib.sha256(json.dumps(receipt, sort_keys=True, default=str).encode("utf-8")).hexdigest()
    fold_receipt = out_dir / f"{ckpt.stem}_full_reload_receipt.json"
    write_json(fold_receipt, receipt)
    write_json(RESULT_DIR / f"full_checkpoint_reload_receipt_fold{fold}.json", {**receipt, "fold_receipt": str(fold_receipt)})
    if receipt["status"] != "PASS" or not receipt["next_batch_hash_match"] or not receipt["next_optimizer_step_micro_descriptor_hash_match"]:
        raise RuntimeError(f"full checkpoint reload failed for {ckpt}: {receipt}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, required=True, choices=(1, 4))
    parser.add_argument("--start-step", type=int, required=True)
    parser.add_argument("--end-step", type=int, required=True)
    parser.add_argument("--patch-size", default="20,256,256")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--seed", type=int, default=20260803)
    parser.add_argument("--resume-checkpoint", type=Path, default=None)
    parser.add_argument("--allow-short-smoke", action="store_true")
    parser.add_argument("--external-review-permit", type=Path, default=None)
    args = parser.parse_args()

    if args.start_step < 0 or args.end_step > 14000 or args.start_step >= args.end_step:
        raise ValueError("CARE-ASE R2 chunk must satisfy 0 <= start < end <= 14000")
    if not args.allow_short_smoke and (args.end_step - args.start_step) != 2000:
        raise ValueError("formal CARE-ASE R2 chunks must be exactly 2000 optimizer steps")
    if not args.allow_short_smoke and args.start_step % 2000 != 0:
        raise ValueError("formal CARE-ASE R2 chunk start must align to 2000 optimizer steps")
    permit = None
    if not args.allow_short_smoke:
        if args.external_review_permit is None:
            raise RuntimeError("formal CARE-ASE R2 W3 chunk requires --external-review-permit")
        permit = verify_external_review_permit(args.external_review_permit)

    patch_size = parse_patch_size(args.patch_size)
    fold = int(args.fold)
    random.seed(args.seed + fold)
    np.random.seed(args.seed + fold)
    torch.manual_seed(args.seed + fold)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = (args.output_dir or RESULT_DIR / "runtime" / f"fold_{fold}").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    lock_dir = out_dir / f"lock_{args.start_step:05d}_{args.end_step:05d}"
    lock_receipt = acquire_chunk_lock(lock_dir, out_dir, fold=fold, start_step=args.start_step, end_step=args.end_step)

    area = compute_actual_train_area_references(REPO_ROOT, fold)
    if args.resume_checkpoint is not None:
        model, prior = _load_previous(args.resume_checkpoint, device)
        if int(prior["global_optimizer_step"]) != int(args.start_step):
            raise RuntimeError(f"resume checkpoint step {prior['global_optimizer_step']} != requested start {args.start_step}")
    elif args.start_step == 0:
        model = build_care_ase_for_fold_with_area_references(
            fold,
            scar_area_reference=area["scar_reference"],
            edema_area_reference=area["edema_reference"],
            map_location="cpu",
        ).to(device)
        prior = None
    else:
        raise RuntimeError("nonzero start-step requires --resume-checkpoint")

    sampler = CAREASEDeterministicSampler(REPO_ROOT, fold, seed=args.seed)
    for step in range(args.start_step):
        sampler.descriptor_for_step(step)
    optimizer = build_optimizer(model)
    scheduler = CAREASEStageScheduler(optimizer)
    if prior is not None:
        optimizer.load_state_dict(prior["optimizer"])
        scheduler.load_state_dict(prior["scheduler"])
        sampler.load_state_dict(_sampler_state_from_checkpoint_payload(prior))

    write_json(RESULT_DIR / "parameter_group_coverage.json", parameter_group_coverage(model))
    write_json(RESULT_DIR / f"sampler_400_step_full_composition_receipt_fold{fold}.json", sampler.composition_receipt(400, start_step=args.start_step))

    write_json(
        out_dir / f"chunk_start_{args.start_step:05d}_{args.end_step:05d}.json",
        {
            "status": "STARTED",
            "formal_training_entrypoint": "scripts/training/care_ase/run_care_ase_r2_chunk.py",
            "fold": fold,
            "start_step": int(args.start_step),
            "end_step": int(args.end_step),
            "device": str(device),
            "patch_size": list(patch_size),
            "gradient_accumulation": 4,
            "area_reference": area,
            "source_hash": combined_source_hash(),
            "split_hash": sha256_file(SPLITS),
            "plans_hash": sha256_file(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json"),
            "outer_access_before_freeze": 0,
            "fixed_decode_function": decode_care_ase_r2_logits.__name__,
            "formal_training_credit_current_external_review_revise_runtime": "zero_until_new_external_review_pass",
            "external_review_permit": permit or {"not_required_for_allow_short_smoke": bool(args.allow_short_smoke)},
            "chunk_lock": lock_receipt,
        },
    )

    log_path = out_dir / f"training_log_{args.start_step:05d}_{args.end_step:05d}.csv"
    history: list[dict[str, Any]] = []
    for step in range(int(args.start_step), int(args.end_step)):
        stage = set_stage_trainability(model, global_step=step)
        scheduler.step(step)
        optimizer.zero_grad(set_to_none=True)
        bundle = sampler.descriptor_bundle_for_step(step, microbatch_count=4)
        descriptor = bundle.micro_descriptors[0]
        desc_sha = bundle.sha256()
        loss_total = 0.0
        metrics: dict[str, float] = {}
        for micro, micro_descriptor in enumerate(bundle.micro_descriptors):
            micro_sha = micro_descriptor.sha256()
            batch = make_batch(micro_descriptor, descriptor_sha=micro_sha, micro=micro, patch_size=patch_size, device=device)
            batch["case_id"] = micro_descriptor.case_id
            batch["descriptor_sha256"] = micro_sha
            batch["optimizer_step_bundle_sha256"] = desc_sha
            with torch.autocast(device_type="cuda", dtype=torch.bfloat16, enabled=(device.type == "cuda")):
                outputs = model(batch["image"], batch["availability"], global_step=step)
                loss, metrics = care_ase_loss(outputs, batch)
            (loss / 4.0).backward()
            loss_total += float(loss.detach().cpu())
        grad_norm = torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=12.0)
        optimizer.step()
        row = {
            "optimizer_step": step + 1,
            "stage": stage,
            "case_id": descriptor.case_id,
            "micro_case_ids": json.dumps([item.case_id for item in bundle.micro_descriptors]),
            "case_group": descriptor.case_group,
            "center": descriptor.center,
            "pathology_focus": descriptor.pathology_focus,
            "within_focus": descriptor.within_focus,
            "hard_negative_category": descriptor.hard_negative_category,
            "hard_negative_counts": json.dumps(descriptor.hard_negative_counts, sort_keys=True),
            "resolved_target_coordinate_count": len(descriptor.resolved_target_coordinates),
            "fallback_sequence": "|".join(descriptor.fallback_sequence),
            "descriptor_sha256": desc_sha,
            "loss": loss_total / 4.0,
            "grad_norm": float(grad_norm.detach().cpu() if torch.is_tensor(grad_norm) else grad_norm),
            "lr_new_modules": CAREASEStageScheduler.lr_for(group_name="new_modules", global_step=step),
            "extent_wall_ramp_value": model.extent_wall_ramp(step + 1),
            "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        }
        append_csv(log_path, row)
        history.append(row)

        if (step + 1) % 1000 == 0 or (step + 1) == int(args.end_step):
            next_descriptor = sampler.peek_descriptor_bundle_for_step(step + 1) if (step + 1) < 14000 else None
            sampler_state = sampler.state_dict(next_descriptor=next_descriptor)
            ckpt_name = "checkpoint_step14000.pt" if (step + 1) == 14000 else f"checkpoint_step{step + 1:05d}.pt"
            ckpt = out_dir / ckpt_name
            save_care_ase_checkpoint(
                ckpt,
                model=model,
                optimizer=optimizer,
                scheduler=scheduler,
                global_step=step + 1,
                microbatch_cursor=0,
                stage_id=CAREASEStageScheduler.stage_for_step(step + 1 if step + 1 < 14000 else 13999),
                next_batch_hash=sampler_state.get("next_batch_descriptor_sha256", "TRAINING_COMPLETE"),
                loss_history_tail=history,
                sampler_state=sampler_state,
                code_hash=combined_source_hash(),
                split_hash=sha256_file(SPLITS),
            )
            payload = torch.load(ckpt, map_location="cpu", weights_only=False)
            write_json(out_dir / f"{ckpt.stem}_receipt.json", checkpoint_receipt(ckpt, payload))
            reload_descriptor = bundle.micro_descriptors[0]
            reload_batch = make_batch(reload_descriptor, descriptor_sha=reload_descriptor.sha256(), micro=0, patch_size=patch_size, device=device)
            reload_batch["case_id"] = descriptor.case_id
            reload_batch["descriptor_sha256"] = desc_sha
            _write_full_reload_receipt(
                ckpt,
                live_model=model,
                live_optimizer=optimizer,
                live_scheduler=scheduler,
                fixed_batch=reload_batch,
                global_step=step + 1,
                fold=fold,
                seed=args.seed,
                out_dir=out_dir,
            )

    terminal = out_dir / f"checkpoint_step{args.end_step:05d}.pt" if args.end_step < 14000 else out_dir / "checkpoint_step14000.pt"
    payload = torch.load(terminal, map_location="cpu", weights_only=False)
    write_json(
        out_dir / f"chunk_terminal_{args.start_step:05d}_{args.end_step:05d}.json",
        {"status": "PASS", "log_path": str(log_path), **checkpoint_receipt(terminal, payload)},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
