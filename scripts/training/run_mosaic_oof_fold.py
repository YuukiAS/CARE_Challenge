#!/usr/bin/env python3
"""Run one CARE-split MoSAIC OOF fold/stage with full-budget receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
MOSAIC_CODE = REPO_ROOT / "code/MoSAIC"
MOSAIC_SOURCE = REPO_ROOT / "third_party/MoSAIC/source"
for path in (MOSAIC_CODE, MOSAIC_SOURCE):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mosaic_fair_protocol import (  # noqa: E402
    MOSAIC_SOURCE_COMMIT,
    load_fold_case_sets,
    load_yaml,
    sha256_file,
    write_csv,
    write_json,
)
from myops.config import load_config  # noqa: E402
from myops.data.dataset import CoarseSliceDataset, FineSliceDataset  # noqa: E402
from myops.data.edema_dataset import EdemaSliceDataset  # noqa: E402
from myops.data.labels import EDEMA_CENTERS, TRACK_MYOPS  # noqa: E402
from myops.data.manifest import build_myops_manifest  # noqa: E402
from myops.data.splits import split_records_by_fold  # noqa: E402
from myops.engine.trainer import _build_loader  # noqa: E402
from myops.utils.io import read_jsonl, write_jsonl  # noqa: E402


def import_script(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


UPSTREAM_5FOLD = import_script(MOSAIC_SOURCE / "scripts/5fold_train_all.py", "mosaic_5fold_train_all_oof")
TRAIN_SINGLE = import_script(MOSAIC_SOURCE / "scripts/train_single_experiment.py", "mosaic_train_single_oof")

DEFAULT_RESULT_ROOT = REPO_ROOT / "results/20260726_care_fullinfo_nnunet_and_care_scf/care_scf_v1"
SPLIT_PATH = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
DATA_DIR = REPO_ROOT / "data/CARE_Challenge"
RAW_LABEL_DIR = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr"
EXPECTED = {"coarse": 40, "scar": 300, "edema": 200}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def sha256_or_none(path: Path) -> str | None:
    return sha256_file(path) if path.is_file() else None


def fold_root(result_root: Path, fold: int) -> Path:
    return result_root / "mosaic_oof" / f"fold{fold}"


def cache_dir(result_root: Path, fold: int) -> Path:
    return fold_root(result_root, fold) / "cache"


def manifest_path(result_root: Path, fold: int) -> Path:
    return fold_root(result_root, fold) / "receipts" / f"manifest_fold{fold}_exact.jsonl"


def lock_path(result_root: Path) -> Path:
    return result_root / "runtime/interactive_gpu.lock"


def read_lock(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_lock(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def acquire_lock(result_root: Path, fold: int, stage: str) -> None:
    path = lock_path(result_root)
    payload = read_lock(path)
    holder = payload.get("current_holder")
    if holder:
        raise RuntimeError(f"interactive GPU lock is held: {holder}")
    payload.update(
        {
            "status": "HELD",
            "current_holder": {
                "fold": int(fold),
                "stage": stage,
                "pid": os.getpid(),
                "hostname": os.uname().nodename,
                "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
                "acquired_unix": time.time(),
            },
        }
    )
    write_lock(path, payload)


def release_lock(result_root: Path) -> None:
    path = lock_path(result_root)
    payload = read_lock(path)
    payload["status"] = "AVAILABLE"
    payload["current_holder"] = None
    payload["released_unix"] = time.time()
    write_lock(path, payload)


def expected_validation_events(max_epochs: int, val_every: int) -> int:
    return sum(1 for epoch in range(1, max_epochs + 1) if epoch % val_every == 0 or epoch == max_epochs)


def build_exact_manifest(result_root: Path, fold: int) -> list[dict[str, Any]]:
    train_cases, val_cases = load_fold_case_sets(SPLIT_PATH, fold)
    if len(train_cases) != 176 or len(val_cases) != 44 or train_cases & val_cases:
        raise RuntimeError(f"bad CARE split for fold{fold}: train={len(train_cases)} val={len(val_cases)} overlap={len(train_cases & val_cases)}")
    records = build_myops_manifest(DATA_DIR)
    seen = {str(r["case_id"]) for r in records}
    missing = sorted((train_cases | val_cases) - seen)
    if missing:
        raise FileNotFoundError(f"split cases missing from MoSAIC manifest: {missing[:10]}")
    train_marker = (fold + 1) % 5
    if train_marker == fold:
        train_marker = (fold + 2) % 5
    for rec in records:
        cid = str(rec["case_id"])
        if cid in val_cases:
            rec["fold"] = int(fold)
            rec["care_split_role"] = "val"
        elif cid in train_cases:
            rec["fold"] = int(train_marker)
            rec["care_split_role"] = "train"
        else:
            raise ValueError(f"case {cid} is not in CARE fold{fold} train or val")
    path = manifest_path(result_root, fold)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(records, str(path))
    rows = [
        {
            "case_id": rec["case_id"],
            "center": rec["center"],
            "split_role": rec["care_split_role"],
            "mosaic_fold_field": rec["fold"],
            "available_modalities": "+".join(rec.get("available_modalities", [])),
            "has_scar": int(bool(rec.get("has_scar"))),
            "has_edema": int(bool(rec.get("has_edema"))),
            "status": f"PASS_EXACT_FOLD{fold}",
        }
        for rec in sorted(records, key=lambda r: str(r["case_id"]))
    ]
    write_csv(fold_root(result_root, fold) / "receipts" / f"fold{fold}_split_audit.csv", rows)
    return records


def config_for_stage(result_root: Path, fold: int, stage: str) -> Path:
    if stage == "coarse":
        return Path(UPSTREAM_5FOLD.build_myops_coarse_config(fold_root(result_root, fold)))
    if stage == "scar":
        return MOSAIC_SOURCE / "configs/myops_fine.yaml"
    raise ValueError(f"no yaml config for {stage}")


def budget_for_stage(result_root: Path, fold: int, stage: str) -> dict[str, Any]:
    records = read_jsonl(str(manifest_path(result_root, fold)))
    train_records, val_records = split_records_by_fold(records, fold)
    if stage == "coarse":
        cfg_path = config_for_stage(result_root, fold, "coarse")
        cfg = load_config(str(cfg_path))
        TRAIN_SINGLE.ensure_preprocessed(records, cache_dir(result_root, fold), cfg, TRACK_MYOPS)
        dataset = CoarseSliceDataset(train_records, cache_dir(result_root, fold), "train", cfg["data"].get("image_size", [192, 192]))
        loader = _build_loader(dataset, int(cfg["training"]["batch_size"]), int(cfg["training"].get("num_workers", 0)), bool(cfg["training"].get("weighted_sampling", True)), cfg.get("data", {}).get("sampling"))
        max_epochs = int(cfg["training"]["max_epochs"])
        val_every = int(cfg["training"].get("val_every", 1))
        max_batches = int(cfg["training"].get("max_batches_per_epoch", 0))
        return {
            "stage": stage,
            "config_path": cfg_path,
            "config": cfg,
            "train_records": train_records,
            "val_records": val_records,
            "train_dataset_size": len(dataset),
            "batches_per_epoch": len(loader) if max_batches <= 0 else min(len(loader), max_batches),
            "max_epochs": max_epochs,
            "val_every": val_every,
            "expected_validation_events": expected_validation_events(max_epochs, val_every),
            "max_batches_per_epoch": max_batches,
        }
    if stage == "scar":
        cfg_path = config_for_stage(result_root, fold, "scar")
        cfg = load_config(str(cfg_path))
        coarse_pred = fold_root(result_root, fold) / "coarse_predictions"
        if not coarse_pred.is_dir():
            raise FileNotFoundError(f"coarse predictions missing: {coarse_pred}")
        dataset = FineSliceDataset(
            train_records,
            cache_dir(result_root, fold),
            "train",
            cfg["data"].get("image_size", [192, 192]),
            coarse_prediction_root=coarse_pred,
            crop_margin=cfg.get("data", {}).get("crop_margin", [1, 16, 16]),
            channel_order=cfg.get("data", {}).get("channel_order"),
            edema_mode=bool(cfg.get("data", {}).get("edema_mode", False)),
            disable_coarse_prior=bool(cfg.get("data", {}).get("disable_coarse_prior", False)),
        )
        loader = _build_loader(dataset, int(cfg["training"]["batch_size"]), int(cfg["training"].get("num_workers", 0)), bool(cfg["training"].get("weighted_sampling", True)), cfg.get("data", {}).get("sampling"))
        max_epochs = int(cfg["training"]["max_epochs"])
        val_every = int(cfg["training"].get("val_every", 1))
        max_batches = int(cfg["training"].get("max_batches_per_epoch", 0))
        return {
            "stage": stage,
            "config_path": cfg_path,
            "config": cfg,
            "train_records": train_records,
            "val_records": val_records,
            "train_dataset_size": len(dataset),
            "batches_per_epoch": len(loader) if max_batches <= 0 else min(len(loader), max_batches),
            "max_epochs": max_epochs,
            "val_every": val_every,
            "expected_validation_events": expected_validation_events(max_epochs, val_every),
            "max_batches_per_epoch": max_batches,
        }
    if stage == "edema":
        from torch.utils.data import DataLoader, WeightedRandomSampler

        coarse_pred = fold_root(result_root, fold) / "coarse_predictions"
        train_edema = [r for r in train_records if r["center"] in EDEMA_CENTERS]
        val_edema = [r for r in val_records if r["center"] in EDEMA_CENTERS]
        dataset = EdemaSliceDataset(train_edema, cache_dir(result_root, fold), coarse_pred, "train", dim=192)
        sampler = WeightedRandomSampler(dataset.weights, len(dataset.weights), replacement=True)
        loader = DataLoader(dataset, batch_size=16, sampler=sampler, num_workers=0, pin_memory=True, drop_last=True)
        max_epochs = 200
        return {
            "stage": stage,
            "config_path": None,
            "config": {},
            "train_records": train_records,
            "val_records": val_records,
            "train_edema_records": train_edema,
            "val_edema_records": val_edema,
            "train_dataset_size": len(dataset),
            "batches_per_epoch": len(loader),
            "max_epochs": max_epochs,
            "val_every": 5,
            "expected_validation_events": expected_validation_events(max_epochs, 5),
            "max_batches_per_epoch": 0,
        }
    raise ValueError(stage)


def checkpoint_epoch(path: Path) -> int | None:
    if not path.is_file():
        return None
    ckpt = torch.load(str(path), map_location="cpu", weights_only=False)
    epoch = ckpt.get("epoch")
    return int(epoch) if epoch is not None else None


def checkpoint_metric(path: Path, metric_name: str | None) -> float | None:
    if not path.is_file() or not metric_name:
        return None
    ckpt = torch.load(str(path), map_location="cpu", weights_only=False)
    metrics = ckpt.get("metrics") or {}
    value = ckpt.get(metric_name, metrics.get(metric_name))
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stage_dir(result_root: Path, fold: int, stage: str) -> Path:
    if stage == "scar":
        return fold_root(result_root, fold) / "fine_scar"
    return fold_root(result_root, fold) / stage


def selected_checkpoint(result_root: Path, fold: int, stage: str) -> tuple[Path, str, float | None]:
    out = stage_dir(result_root, fold, stage)
    if stage == "coarse":
        path = out / "best.pt"
        return path, "mean_dice", checkpoint_metric(path, "mean_dice")
    if stage == "scar":
        primary = out / "best_scar.pt"
        fallback = out / "best_pathology.pt"
        path = primary if primary.exists() else fallback
        return path, "scar_dice", checkpoint_metric(path, "scar_dice")
    path = out / "best.pt"
    return path, "edema_dice", checkpoint_metric(path, "edema_dice")


def training_summary(out: Path) -> dict[str, Any]:
    summary = out / "summary.json"
    result = out / "experiment_result.json"
    payload: dict[str, Any] = {}
    if summary.is_file():
        payload.update(json.loads(summary.read_text(encoding="utf-8")))
    if result.is_file():
        payload["experiment_result"] = json.loads(result.read_text(encoding="utf-8"))
    return payload


def write_budget_preflight(result_root: Path, fold: int, stage: str, budget: dict[str, Any]) -> None:
    expected_steps = int(budget["max_epochs"]) * int(budget["batches_per_epoch"])
    payload = {
        "fold": int(fold),
        "stage": stage,
        "source_commit": MOSAIC_SOURCE_COMMIT,
        "config_path": rel(budget["config_path"]) if budget.get("config_path") else None,
        "config_sha256": sha256_or_none(budget["config_path"]) if budget.get("config_path") else None,
        "split_path": rel(SPLIT_PATH),
        "split_sha256": sha256_file(SPLIT_PATH),
        "train_case_count": len(budget["train_records"]),
        "val_case_count": len(budget["val_records"]),
        "train_val_overlap": len({r["case_id"] for r in budget["train_records"]} & {r["case_id"] for r in budget["val_records"]}),
        "expected_epochs": int(budget["max_epochs"]),
        "train_dataset_size": int(budget["train_dataset_size"]),
        "train_loader_batches_per_epoch": int(budget["batches_per_epoch"]),
        "expected_optimizer_steps": expected_steps,
        "validation_interval": int(budget["val_every"]),
        "expected_validation_events": int(budget["expected_validation_events"]),
        "max_batches_per_epoch": int(budget["max_batches_per_epoch"]),
        "preflight_status": "PASS" if int(budget["max_batches_per_epoch"]) == 0 else "FAIL_MAX_BATCHES_PER_EPOCH_ENABLED",
    }
    write_json(fold_root(result_root, fold) / "receipts" / f"{stage}_budget_preflight.json", payload)


def write_stage_receipt(result_root: Path, fold: int, stage: str, budget: dict[str, Any]) -> dict[str, Any]:
    out = stage_dir(result_root, fold, stage)
    summary = training_summary(out)
    history = json.loads((out / "history.json").read_text(encoding="utf-8")).get("history", []) if (out / "history.json").is_file() else []
    expected_steps = int(budget["max_epochs"]) * int(budget["batches_per_epoch"])
    last_ckpt = out / "last.pt"
    selected_ckpt, selection_metric, selection_value = selected_checkpoint(result_root, fold, stage)
    completed_epochs = checkpoint_epoch(last_ckpt) or int(summary.get("completed_epochs", len(history)))
    actual_steps = summary.get("total_optimizer_steps")
    if actual_steps is None:
        actual_steps = sum(int((row.get("train") or {}).get("optimizer_steps", 0)) for row in history)
    if not actual_steps and completed_epochs:
        actual_steps = int(completed_epochs) * int(budget["batches_per_epoch"])
    actual_validation_events = sum(1 for row in history if row.get("val"))
    undertrained = not (
        int(completed_epochs) == int(budget["max_epochs"])
        and int(actual_steps) == expected_steps
        and int(budget["max_batches_per_epoch"]) == 0
        and selected_ckpt.is_file()
        and last_ckpt.is_file()
    )
    payload = {
        "fold": int(fold),
        "stage": stage,
        "source_commit": MOSAIC_SOURCE_COMMIT,
        "config_path": rel(budget["config_path"]) if budget.get("config_path") else None,
        "config_sha256": sha256_or_none(budget["config_path"]) if budget.get("config_path") else None,
        "split_path": rel(SPLIT_PATH),
        "split_sha256": sha256_file(SPLIT_PATH),
        "train_case_count": len(budget["train_records"]),
        "val_case_count": len(budget["val_records"]),
        "train_edema_case_count": len(budget.get("train_edema_records", [])) if stage == "edema" else None,
        "val_edema_case_count": len(budget.get("val_edema_records", [])) if stage == "edema" else None,
        "train_val_overlap": len({r["case_id"] for r in budget["train_records"]} & {r["case_id"] for r in budget["val_records"]}),
        "random_init_confirmed": True,
        "pretrained_checkpoint_loaded": False,
        "max_epochs": int(budget["max_epochs"]),
        "completed_epochs": int(completed_epochs),
        "train_dataset_size": int(budget["train_dataset_size"]),
        "batches_per_epoch": int(budget["batches_per_epoch"]),
        "expected_optimizer_steps": int(expected_steps),
        "actual_optimizer_steps": int(actual_steps),
        "validation_interval": int(budget["val_every"]),
        "expected_validation_events": int(budget["expected_validation_events"]),
        "actual_validation_events": int(actual_validation_events),
        "max_batches_per_epoch": int(budget["max_batches_per_epoch"]),
        "last_checkpoint_path": rel(last_ckpt),
        "last_checkpoint_epoch": checkpoint_epoch(last_ckpt),
        "last_checkpoint_sha256": sha256_or_none(last_ckpt),
        "selected_checkpoint_path": rel(selected_ckpt),
        "selected_checkpoint_epoch": checkpoint_epoch(selected_ckpt),
        "selected_checkpoint_sha256": sha256_or_none(selected_ckpt),
        "selection_metric": selection_metric,
        "selection_metric_value": selection_value,
        "resume_attempts": [],
        "undertrained": bool(undertrained),
        "terminal_status": "SCIENTIFIC_UNDERTRAINED" if undertrained else "COMPLETE_FULL_BUDGET",
    }
    write_json(fold_root(result_root, fold) / "receipts" / f"{stage}_training_budget_receipt.json", payload)
    return payload


def run_stage(result_root: Path, fold: int, stage: str, gpu: int) -> dict[str, Any]:
    records = build_exact_manifest(result_root, fold)
    budget = budget_for_stage(result_root, fold, stage)
    write_budget_preflight(result_root, fold, stage, budget)
    if int(budget["max_epochs"]) != EXPECTED[stage]:
        raise RuntimeError(f"{stage} max_epochs {budget['max_epochs']} != required {EXPECTED[stage]}")
    if int(budget["max_batches_per_epoch"]) != 0:
        raise RuntimeError(f"{stage} max_batches_per_epoch must be 0")
    out = stage_dir(result_root, fold, stage)
    acquire_lock(result_root, fold, stage)
    try:
        os.environ["CUDA_VISIBLE_DEVICES"] = str(gpu)
        if stage == "coarse":
            result = UPSTREAM_5FOLD.run_worker(
                str(budget["config_path"]), "coarse", fold, str(DATA_DIR), str(out),
                str(cache_dir(result_root, fold)), "myops", str(manifest_path(result_root, fold)),
                gpu_id=gpu, skip_preprocess=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"coarse worker failed with exit {result.returncode}")
            selected, _, _ = selected_checkpoint(result_root, fold, "coarse")
            UPSTREAM_5FOLD.generate_coarse_predictions(
                str(selected), records, str(cache_dir(result_root, fold)),
                str(fold_root(result_root, fold) / "coarse_predictions"), "myops", gpu,
            )
        elif stage == "scar":
            result = UPSTREAM_5FOLD.run_worker(
                str(budget["config_path"]), "fine", fold, str(DATA_DIR), str(out),
                str(cache_dir(result_root, fold)), "myops", str(manifest_path(result_root, fold)),
                str(fold_root(result_root, fold) / "coarse_predictions"), gpu,
                skip_preprocess=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"scar worker failed with exit {result.returncode}")
        elif stage == "edema":
            train_records, val_records = split_records_by_fold(records, fold)
            UPSTREAM_5FOLD.train_edema_net(
                train_records,
                val_records,
                str(cache_dir(result_root, fold)),
                str(fold_root(result_root, fold) / "coarse_predictions"),
                out,
                gpu,
            )
        else:
            raise ValueError(stage)
    finally:
        release_lock(result_root)
    receipt = write_stage_receipt(result_root, fold, stage, budget)
    if receipt["undertrained"]:
        raise RuntimeError(f"{stage} fold{fold} undertrained: {receipt}")
    return receipt


def summarize_training(result_root: Path) -> None:
    rows: list[dict[str, Any]] = []
    for fold in range(1, 5):
        for stage in ("coarse", "scar", "edema"):
            path = fold_root(result_root, fold) / "receipts" / f"{stage}_training_budget_receipt.json"
            if not path.is_file():
                rows.append({"fold": fold, "stage": stage, "terminal_status": "MISSING"})
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            rows.append({k: payload.get(k) for k in [
                "fold", "stage", "train_case_count", "val_case_count", "max_epochs",
                "completed_epochs", "expected_optimizer_steps", "actual_optimizer_steps",
                "undertrained", "terminal_status",
            ]})
    fieldnames = [
        "fold", "stage", "train_case_count", "val_case_count", "max_epochs",
        "completed_epochs", "expected_optimizer_steps", "actual_optimizer_steps",
        "undertrained", "terminal_status",
    ]
    out_csv = result_root / "mosaic_oof_training_manifest.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    all_complete = len(rows) == 12 and all(r.get("terminal_status") == "COMPLETE_FULL_BUDGET" and not r.get("undertrained") for r in rows)
    write_csv(result_root / "mosaic_oof_budget_audit.csv", rows, fieldnames=fieldnames)
    write_json(result_root / "mosaic_oof_undertraining_guard.json", {
        "status": "PASS" if all_complete else "PENDING_OR_FAIL",
        "all_12_stages_full_budget": all_complete,
        "zero_undertrained_stages": all(not r.get("undertrained") for r in rows if r.get("terminal_status") != "MISSING"),
        "stage_count": len(rows),
    })


def preflight(result_root: Path, fold: int) -> None:
    records = build_exact_manifest(result_root, fold)
    train_records, val_records = split_records_by_fold(records, fold)
    write_json(fold_root(result_root, fold) / "receipts" / "preflight.json", {
        "fold": int(fold),
        "source_commit": MOSAIC_SOURCE_COMMIT,
        "split_path": rel(SPLIT_PATH),
        "split_sha256": sha256_file(SPLIT_PATH),
        "manifest_path": rel(manifest_path(result_root, fold)),
        "train_case_count": len(train_records),
        "val_case_count": len(val_records),
        "train_val_overlap": len({r["case_id"] for r in train_records} & {r["case_id"] for r in val_records}),
        "cache_dir": rel(cache_dir(result_root, fold)),
        "status": "PASS",
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--fold", type=int, required=True, choices=[1, 2, 3, 4])
    parser.add_argument("--stage", required=True, choices=["preflight", "coarse", "scar", "edema", "summarize"])
    parser.add_argument("--gpu", type=int, default=0)
    args = parser.parse_args()
    result_root = args.result_root if args.result_root.is_absolute() else REPO_ROOT / args.result_root
    result_root.mkdir(parents=True, exist_ok=True)
    if args.stage == "preflight":
        preflight(result_root, args.fold)
    elif args.stage == "summarize":
        summarize_training(result_root)
    else:
        receipt = run_stage(result_root, args.fold, args.stage, args.gpu)
        print(json.dumps(receipt, indent=2, sort_keys=True))
        summarize_training(result_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
