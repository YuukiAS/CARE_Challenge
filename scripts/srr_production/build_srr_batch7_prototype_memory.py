#!/usr/bin/env python3
"""Build the Batch7 trained-feature-aligned SRR prototype/memory asset."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    fit_and_load_runtime_prototype_bank,
    model_kwargs_from_args,
    read_anchored_case,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint  # noqa: E402
from src.care_myocardium.srr_production.prototype_memory import hash_tensor  # noqa: E402


def repo_path(raw: str | Path) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def model_args(cfg: dict[str, Any], result_root: Path) -> argparse.Namespace:
    formal = cfg["formal_training"]
    return argparse.Namespace(
        variant=cfg["model"]["variant"],
        encoder_profile=cfg["model"]["encoder_profile"],
        base_channels=int(cfg["model"]["base_channels"]),
        final_output_mode=cfg["model"]["final_output_mode"],
        disable_local_refinement=False,
        disable_anatomy_roi_prior=False,
        disable_nnunet_anchor=False,
        skip_prototype_bank_fit=False,
        prototype_bank_cases=int(cfg["prototype_memory_rebuild"]["source_train_cases"]),
        seed=20260721,
        patch_shape=",".join(str(v) for v in formal["patch_shape"]),
        out_root=str(result_root / "runtime"),
        run_label="batch7_asset_rebuild",
        loss_weight_json="",
        loss_weight=[],
        variant_config_record={"variant_config": {"canonical_loss_weights": cfg["canonical_loss_weights"]}},
        canonical_loss_weights=cfg["canonical_loss_weights"],
    )


def split_ids(cfg: dict[str, Any]) -> tuple[list[str], list[str]]:
    payload = json.loads(repo_path(cfg["paths"]["split_path"]).read_text(encoding="utf-8"))
    fold = payload["folds"][int(cfg["training_data"]["fold"])]
    return list(fold["train"]), list(fold["val"])


def memory_state(model: SRRProposeRefineMyoPS) -> dict[str, torch.Tensor]:
    keep = ("scar_dictionary.", "edema_dictionary.", "cross_fitted_memory.")
    return {name: value.detach().cpu() for name, value in model.state_dict().items() if name.startswith(keep)}


def tensor_hash_rows(model: SRRProposeRefineMyoPS) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, value in memory_state(model).items():
        rows.append(
            {
                "tensor_name": name,
                "shape": "x".join(str(v) for v in value.shape),
                "dtype": str(value.dtype),
                "numel": int(value.numel()),
                "sha256": hash_tensor(value),
            }
        )
    return rows


def semantic_negative_rows(model: SRRProposeRefineMyoPS) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary = model.cross_fitted_memory.summary()
    for pathology, events in summary.get("provenance", {}).items():
        category_counts: dict[str, int] = {}
        if isinstance(events, list):
            for event in events:
                category = str(event.get("category", "unknown"))
                category_counts[category] = category_counts.get(category, 0) + int(event.get("accepted_count", 0) or 0)
        for category, count in sorted(category_counts.items()):
            rows.append({"pathology": pathology, "category": category, "accepted_count": count})
    return rows


def build(config: Path, result_root: Path, device_name: str) -> dict[str, Any]:
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    result_root.mkdir(parents=True, exist_ok=True)
    runtime_asset = repo_path(cfg["paths"]["rebuilt_asset_path"])
    runtime_asset.parent.mkdir(parents=True, exist_ok=True)
    ckpt = repo_path(cfg["source_batch6"]["checkpoint_path"])
    actual_sha = sha256_file(ckpt)
    expected_sha = str(cfg["source_batch6"]["selected_checkpoint_sha256"])
    if actual_sha != expected_sha:
        raise SystemExit(f"source checkpoint sha mismatch: {actual_sha} != {expected_sha}")
    train_ids, val_ids = split_ids(cfg)
    if len(train_ids) != int(cfg["training_data"]["train_case_count"]):
        raise SystemExit(f"train split count mismatch: {len(train_ids)}")
    if len(val_ids) != int(cfg["training_data"]["validation_case_count"]):
        raise SystemExit(f"validation split count mismatch: {len(val_ids)}")
    leakage = sorted(set(train_ids) & set(val_ids))
    if leakage:
        raise SystemExit(f"validation leakage in split: {leakage[:5]}")
    device = torch.device("cuda" if device_name == "cuda" and torch.cuda.is_available() else "cpu")
    args = model_args(cfg, result_root)
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    payload = load_srr_checkpoint(
        path=ckpt,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        map_location=device,
        restore_rng=False,
        restore_optimizer=False,
        strict_model_state=False,
    )
    model.eval()
    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = repo_path(cfg["paths"]["anchor_root"])
    cases = [read_anchored_case(case_id, metadata, anchor_root) for case_id in train_ids]
    patch_shape = tuple(int(v) for v in cfg["formal_training"]["patch_shape"])
    builder_dir = result_root / "runtime/asset_builder"
    builder_dir.mkdir(parents=True, exist_ok=True)
    summary = fit_and_load_runtime_prototype_bank(model, cases, patch_shape, device, args, builder_dir)
    state = memory_state(model)
    asset_payload = {
        "schema_version": 2,
        "asset_type": "srr_batch7_prototype_memory",
        "source_checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
        "source_checkpoint_sha256": actual_sha,
        "source_checkpoint_global_step": payload.get("global_step"),
        "feature_stage": cfg["prototype_memory_rebuild"]["feature_stage"],
        "model_memory_state": state,
        "summary": summary,
    }
    torch.save(asset_payload, runtime_asset)
    tensor_rows = tensor_hash_rows(model)
    write_csv(result_root / "prototype_feature_drift.csv", tensor_rows)
    neg_rows = semantic_negative_rows(model)
    if not neg_rows:
        neg_rows = [{"pathology": "scar", "category": "none", "accepted_count": 0}]
    write_csv(result_root / "semantic_negative_counts.csv", neg_rows)
    manifest = {
        "status": "PASS",
        "schema_version": 2,
        "asset_path": str(runtime_asset.relative_to(REPO_ROOT)),
        "asset_sha256": sha256_file(runtime_asset),
        "source_checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
        "source_checkpoint_sha256": actual_sha,
        "source_checkpoint_global_step": payload.get("global_step"),
        "feature_stage": cfg["prototype_memory_rebuild"]["feature_stage"],
        "model_eval_during_extraction": True,
        "source_case_count": len(train_ids),
        "expected_source_case_count": int(cfg["training_data"]["train_case_count"]),
        "validation_case_count": len(val_ids),
        "validation_intersection": leakage,
        "shard_count": int(cfg["prototype_memory_rebuild"]["shard_count"]),
        "full_tensor_sha256": True,
        "tensor_hash_count": len(tensor_rows),
        "selected_case_ids": train_ids,
        "semantic_negative_counts_path": str((result_root / "semantic_negative_counts.csv").relative_to(REPO_ROOT)),
        "prototype_feature_drift_path": str((result_root / "prototype_feature_drift.csv").relative_to(REPO_ROOT)),
        "formal_named_negative_contribution": "cross_fitted_semantic_memory_only",
        "deterministic_axis_random_repeat_formal_contribution": 0,
        "no_t2_edema_memory_count_zero": all(
            event.get("reason") != "ACCEPTED"
            for event in model.cross_fitted_memory.ledger_rows()
            if event.get("pathology") == "edema" and not bool(event.get("t2_present"))
        ),
        "summary": summary,
    }
    (result_root / "prototype_memory_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch7_upstream_candidate_quality")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    manifest = build(repo_path(args.config), repo_path(args.result_root), args.device)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
