#!/usr/bin/env python3
"""Build Batch7 repair named-category semantic memory from fold0 train cases."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    model_kwargs_from_args,
    read_anchored_case,
    sample_patch_with_anchor,
    vectors_from_mask,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.srr_dictionary_memory import deterministic_memory_shard  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint  # noqa: E402
from src.care_myocardium.srr_production.prototype_memory import hash_tensor  # noqa: E402


SCAR_NEGATIVE_CATEGORIES = (
    "normal_myocardium",
    "blood_pool",
    "outside_myocardium",
    "lge_bright_non_scar",
    "anchor_remote_false_positive",
)
EDEMA_NEGATIVE_CATEGORIES = (
    "normal_myocardium",
    "blood_pool",
    "outside_myocardium",
    "t2_high_non_edema",
    "anchor_remote_false_positive",
)


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


def split_ids(cfg: dict[str, Any]) -> tuple[list[str], list[str]]:
    payload = json.loads(repo_path(cfg["paths"]["split_path"]).read_text(encoding="utf-8"))
    fold = payload["folds"][int(cfg["training_data"]["fold"])]
    return list(fold["train"]), list(fold["val"])


def model_args(cfg: dict[str, Any], result_root: Path) -> argparse.Namespace:
    common = cfg["stagewise_training"]["common"]
    return argparse.Namespace(
        variant=cfg["model"]["variant"],
        encoder_profile=cfg["model"]["encoder_profile"],
        base_channels=int(cfg["model"]["base_channels"]),
        final_output_mode=cfg["model"]["final_output_mode"],
        disable_local_refinement=False,
        disable_anatomy_roi_prior=False,
        disable_nnunet_anchor=False,
        patch_shape=",".join(str(v) for v in common["patch_shape"]),
        out_root=str(result_root / "runtime"),
        run_label="batch7_repair_semantic_memory",
        loss_weight_json="",
        loss_weight=[],
        variant_config_record={"variant_config": {"canonical_loss_weights": {}}},
        canonical_loss_weights={},
    )


def memory_state(model: SRRProposeRefineMyoPS) -> dict[str, torch.Tensor]:
    keep = ("cross_fitted_memory.",)
    return {name: value.detach().cpu() for name, value in model.state_dict().items() if name.startswith(keep)}


def robust_high_mask(channel: np.ndarray, allowed: np.ndarray, z_min: float) -> np.ndarray:
    values = channel[allowed]
    if values.size == 0:
        return np.zeros_like(allowed, dtype=bool)
    median = float(np.median(values))
    mad = float(np.median(np.abs(values - median)))
    scale = max(1e-6, 1.4826 * mad)
    z = (channel - median) / scale
    return allowed & (z >= float(z_min))


def add_update(
    model: SRRProposeRefineMyoPS,
    rows: list[dict[str, Any]],
    tensors: dict[tuple[str, str, str], list[torch.Tensor]],
    *,
    pathology: str,
    polarity: str,
    category: str,
    vectors: torch.Tensor,
    case_id: str,
    t2_present: bool,
) -> None:
    event = model.cross_fitted_memory.update(
        pathology,
        polarity,
        category,
        vectors,
        case_id=case_id,
        t2_present=t2_present,
    )
    accepted = int(event.accepted_count)
    rows.append(
        {
            "pathology": pathology,
            "polarity": polarity,
            "category": category,
            "case_id": case_id,
            "source_shard": deterministic_memory_shard(case_id),
            "t2_present": bool(t2_present),
            "raw_vector_count": int(vectors.shape[0]) if vectors.ndim == 2 else 0,
            "accepted_count": accepted,
            "reason": event.reason,
        }
    )
    if accepted > 0:
        tensors.setdefault((pathology, polarity, category), []).append(vectors.detach().cpu())


def build(config: Path, result_root: Path, device_name: str, max_vectors_per_case_category: int) -> dict[str, Any]:
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    result_root.mkdir(parents=True, exist_ok=True)
    asset_path = repo_path(cfg["paths"]["semantic_memory_asset"])
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    ckpt = repo_path(cfg["source_checkpoints"]["batch7"]["path"])
    actual_sha = sha256_file(ckpt)
    expected_sha = str(cfg["source_checkpoints"]["batch7"]["sha256"])
    if actual_sha != expected_sha:
        raise SystemExit(f"Batch7 checkpoint sha mismatch: {actual_sha} != {expected_sha}")
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
    # Formal repair memory is rebuilt from real category tensors only.
    model.cross_fitted_memory.positive_mu.zero_()
    model.cross_fitted_memory.negative_mu.zero_()
    model.cross_fitted_memory.positive_counts.zero_()
    model.cross_fitted_memory.negative_counts.zero_()
    model.cross_fitted_memory.update_ledger.clear()
    model.cross_fitted_memory.provenance = {pathology: [] for pathology in ("scar", "edema")}
    model.eval()

    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = repo_path(cfg["paths"]["anchor_root"])
    patch_shape = tuple(int(v) for v in cfg["stagewise_training"]["common"]["patch_shape"])
    rng = np.random.default_rng(20260721)
    update_rows: list[dict[str, Any]] = []
    tensor_groups: dict[tuple[str, str, str], list[torch.Tensor]] = {}

    for case_id in train_ids:
        case = read_anchored_case(case_id, metadata, anchor_root)
        focus = (4,) if case.metadata.t2_present and np.any(case.label_arr == 4) else ((5,) if np.any(case.label_arr == 5) else (4, 5))
        x_np, y_np, av_np, anchor_np, _component_np = sample_patch_with_anchor(
            case,
            patch_shape,
            rng,
            oversample_foreground=1.0,
            modality_dropout=False,
            focus_classes=focus,
        )
        x = torch.from_numpy(x_np[None]).float().to(device)
        av = torch.from_numpy(av_np[None]).float().to(device)
        y = torch.from_numpy(y_np[None]).long().to(device)
        with torch.no_grad():
            features, _gates, _metadata, _valid = model._evidence_features(x, av, None)
        lab = F.interpolate(y[:, None].float(), size=features["scar"].shape[-3:], mode="nearest")[:, 0].long()
        y_resized = lab.detach().cpu().numpy()[0]
        anchor_resized = np.asarray(anchor_np).argmax(axis=0)
        if anchor_resized.shape != y_np.shape:
            anchor_t = torch.from_numpy(anchor_resized[None, None]).float().to(device)
            anchor_resized = F.interpolate(anchor_t, size=features["scar"].shape[-3:], mode="nearest")[0, 0].long().cpu().numpy()
        else:
            anchor_t = torch.from_numpy(anchor_resized[None, None]).float().to(device)
            anchor_resized = F.interpolate(anchor_t, size=features["scar"].shape[-3:], mode="nearest")[0, 0].long().cpu().numpy()
        image_resized = []
        for channel in range(x_np.shape[0]):
            chan = torch.from_numpy(x_np[channel][None, None]).float().to(device)
            image_resized.append(F.interpolate(chan, size=features["scar"].shape[-3:], mode="trilinear", align_corners=False)[0, 0].cpu().numpy())
        image_resized_np = np.stack(image_resized, axis=0)
        anatomy = (y_resized >= 1) & (y_resized <= 5)
        normal = y_resized == 1
        blood = (y_resized == 2) | (y_resized == 3)
        outside = ~anatomy
        scar_gt = y_resized == 5
        edema_gt = y_resized == 4
        t2_present = bool(av_np[1] > 0.5)
        lge_bright = robust_high_mask(image_resized_np[0], ((y_resized == 1) | (y_resized == 4)) & ~scar_gt, 2.0)
        t2_high = robust_high_mask(image_resized_np[1], ((y_resized == 1) | (y_resized == 5)) & ~edema_gt, 2.0) if t2_present else np.zeros_like(edema_gt)
        scar_remote_fp = (anchor_resized == 5) & ~scar_gt & outside
        edema_remote_fp = (anchor_resized == 4) & ~edema_gt & outside if t2_present else np.zeros_like(edema_gt)

        scar_masks = {
            "scar_positive": scar_gt,
            "normal_myocardium": normal,
            "blood_pool": blood,
            "outside_myocardium": outside,
            "lge_bright_non_scar": lge_bright,
            "anchor_remote_false_positive": scar_remote_fp,
        }
        edema_masks = {
            "edema_positive": edema_gt & t2_present,
            "normal_myocardium": normal & t2_present,
            "blood_pool": blood & t2_present,
            "outside_myocardium": outside & t2_present,
            "t2_high_non_edema": t2_high & t2_present,
            "anchor_remote_false_positive": edema_remote_fp & t2_present,
        }
        for category, mask_np in scar_masks.items():
            polarity = "positive" if category == "scar_positive" else "negative"
            vectors = vectors_from_mask(
                features["scar"],
                lab,
                torch.from_numpy(mask_np[None]).to(device=device, dtype=torch.bool),
                max_vectors=max_vectors_per_case_category,
            )
            add_update(model, update_rows, tensor_groups, pathology="scar", polarity=polarity, category=category, vectors=vectors, case_id=case_id, t2_present=t2_present)
        for category, mask_np in edema_masks.items():
            polarity = "positive" if category == "edema_positive" else "negative"
            vectors = vectors_from_mask(
                features["edema"],
                lab,
                torch.from_numpy(mask_np[None]).to(device=device, dtype=torch.bool),
                max_vectors=max_vectors_per_case_category,
            )
            add_update(model, update_rows, tensor_groups, pathology="edema", polarity=polarity, category=category, vectors=vectors, case_id=case_id, t2_present=t2_present)

    category_rows: list[dict[str, Any]] = []
    hash_rows: list[dict[str, Any]] = []
    mask_rows: list[dict[str, Any]] = []
    required = [("scar", "negative", category) for category in SCAR_NEGATIVE_CATEGORIES]
    required.extend(("edema", "negative", category) for category in EDEMA_NEGATIVE_CATEGORIES)
    required.extend([("scar", "positive", "scar_positive"), ("edema", "positive", "edema_positive")])
    for pathology, polarity, category in required:
        tensors = tensor_groups.get((pathology, polarity, category), [])
        tensor = torch.cat(tensors, dim=0) if tensors else torch.empty((0, model.feature_channels))
        source_case_ids = sorted({row["case_id"] for row in update_rows if row["pathology"] == pathology and row["polarity"] == polarity and row["category"] == category and int(row["accepted_count"]) > 0})
        valid = bool(tensor.numel() > 0)
        digest = hash_tensor(tensor) if valid else "EMPTY_VALID_MASK_FALSE"
        common = {
            "pathology": pathology,
            "polarity": polarity,
            "category": category,
            "vector_count": int(tensor.shape[0]),
            "source_case_ids": ";".join(source_case_ids),
            "source_case_count": len(source_case_ids),
            "valid_mask": valid,
            "full_tensor_sha256": digest,
        }
        category_rows.append(common)
        hash_rows.append({k: common[k] for k in ("pathology", "polarity", "category", "vector_count", "full_tensor_sha256")})
        mask_rows.append({k: common[k] for k in ("pathology", "polarity", "category", "valid_mask", "vector_count")})

    if not any(row["pathology"] == "scar" and row["polarity"] == "positive" and row["valid_mask"] for row in category_rows):
        raise SystemExit("scar positive memory is empty")
    if not any(row["pathology"] == "edema" and row["polarity"] == "positive" and row["valid_mask"] for row in category_rows):
        raise SystemExit("edema positive memory is empty")
    asset_payload = {
        "schema_version": 1,
        "asset_type": "srr_batch7_repair_named_category_semantic_memory",
        "source_checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
        "source_checkpoint_sha256": actual_sha,
        "source_checkpoint_global_step": payload.get("global_step"),
        "source_train_case_count": len(train_ids),
        "validation_case_count": len(val_ids),
        "validation_intersection": leakage,
        "category_rows": category_rows,
        "model_memory_state": memory_state(model),
        "summary": model.cross_fitted_memory.summary(),
    }
    torch.save(asset_payload, asset_path)
    write_csv(result_root / "semantic_memory_category_counts.csv", category_rows)
    write_csv(result_root / "semantic_memory_tensor_hashes.csv", hash_rows)
    write_csv(result_root / "semantic_memory_valid_masks.csv", mask_rows)
    write_csv(result_root / "runtime/semantic_memory_update_ledger.csv", update_rows)
    manifest = {
        "status": "PASS",
        "schema_version": 1,
        "asset_path": str(asset_path.relative_to(REPO_ROOT)),
        "asset_sha256": sha256_file(asset_path),
        "source_checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
        "source_checkpoint_sha256": actual_sha,
        "source_checkpoint_global_step": payload.get("global_step"),
        "source_case_count": len(train_ids),
        "validation_case_count": len(val_ids),
        "validation_intersection": leakage,
        "shard_count": int(cfg["semantic_memory"]["shard_count"]),
        "training_query_policy": cfg["semantic_memory"]["training_query_policy"],
        "validation_query_policy": cfg["semantic_memory"]["validation_query_policy"],
        "deterministic_axis_random_repeat_formal_contribution": 0,
        "zero_count_category_policy": "valid_mask_false",
        "no_t2_edema_memory_count_zero": all(
            not (row["pathology"] == "edema" and row["t2_present"] is False and int(row["accepted_count"]) > 0)
            for row in update_rows
        ),
        "category_counts_path": str((result_root / "semantic_memory_category_counts.csv").relative_to(REPO_ROOT)),
        "tensor_hashes_path": str((result_root / "semantic_memory_tensor_hashes.csv").relative_to(REPO_ROOT)),
        "valid_masks_path": str((result_root / "semantic_memory_valid_masks.csv").relative_to(REPO_ROOT)),
        "full_tensor_sha256_required": True,
        "formal_named_negative_source": "real_category_banks_with_valid_mask_only",
    }
    (result_root / "semantic_memory_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_repair.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch7_mechanism_closure_repair")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--max-vectors-per-case-category", type=int, default=12)
    args = parser.parse_args()
    manifest = build(repo_path(args.config), repo_path(args.result_root), args.device, args.max_vectors_per_case_category)
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
