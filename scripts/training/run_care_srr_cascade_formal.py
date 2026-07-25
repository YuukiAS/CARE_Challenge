#!/usr/bin/env python
"""Formal CARE-SRR-Cascade training entrypoint."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch
from scipy.ndimage import distance_transform_edt

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from nnunetv2.utilities.plans_handling.plans_handler import PlansManager

from src.care_myocardium.data.care_srr_cascade_runtime import ScheduleRow, schedule_sha256
from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.models.care_srr_cascade_rescue import CARESRRCascadeRescue
from src.care_myocardium.srr_production.case_prototypes import cosine_similarity_maps, select_crossfit_prototype_bank
from src.care_myocardium.training.care_srr_cascade_trainer import (
    CARESRRCascadeFormalTrainer,
    FormalRuntimeConfig,
    checkpoint_schema_contract,
)


RESULT_ROOT = REPO_ROOT / "results/20260724_care_myops_srr_cascade_submission_rescue"
REPAIR_ROOT = RESULT_ROOT / "runtime_closure_repair_rc1"
FORMAL_ROOT = RESULT_ROOT / "runtime/formal_v2"
CONFIG_PATH = REPO_ROOT / "configs/care_mm/srr_cascade_runtime_closure_repair.yaml"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
PLANS = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetResEncUNetMPlans.json"
ANCHOR_DIR = RESULT_ROOT / "runtime/anchor_cache_v2"
SOURCE_DIR = RESULT_ROOT / "runtime/source_cache_v2"
PROTOTYPE_DIR = RESULT_ROOT / "runtime/prototype_cache_v2"
SCHEDULE_DIR = RESULT_ROOT / "runtime/matched_schedules_v2"
LOCK_DIR = FORMAL_ROOT / "locks"


LOGICAL_JOBS = {
    "scar_seed20260724": ("scar", 20260724, ("scar_cascade_control", "scar_srr_cascade")),
    "edema_seed20260724": ("edema", 20260724, ("edema_zone_control", "edema_srr_zone_cascade")),
    "scar_seed20260725": ("scar", 20260725, ("scar_cascade_control", "scar_srr_cascade")),
    "edema_seed20260725": ("edema", 20260725, ("edema_zone_control", "edema_srr_zone_cascade")),
}


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def acquire_logical_run_lock(logical_run_id: str) -> bool:
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    lock = LOCK_DIR / f"{logical_run_id}.lock"
    job_id = os.environ.get("SLURM_JOB_ID", "local")
    owner = {
        "decision": "LOCK_HELD",
        "logical_run_id": logical_run_id,
        "slurm_job_id": job_id,
        "formal_training_credit": "PENDING_REAL_RUN",
    }
    try:
        lock.mkdir()
    except FileExistsError:
        owner_path = lock / "owner.json"
        existing = json.loads(owner_path.read_text()) if owner_path.exists() else {"decision": "LOCK_OWNER_UNKNOWN"}
        loser = {
            "decision": "RACE_LOCK_LOST",
            "logical_run_id": logical_run_id,
            "slurm_job_id": job_id,
            "lock_path": str(lock.relative_to(REPO_ROOT)),
            "owner": existing,
            "formal_training_credit": 0,
        }
        write_json(FORMAL_ROOT / logical_run_id / f"race_lock_lost_{job_id}.json", loser)
        print(json.dumps(loser, indent=2, sort_keys=True))
        return False
    write_json(lock / "owner.json", owner)
    return True


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def parse_variants(text: str) -> tuple[str, ...]:
    return tuple(v for v in str(text).split("|") if v)


def validate_formal_args(args: argparse.Namespace) -> tuple[str, int, tuple[str, ...]]:
    if args.logical_run_id not in LOGICAL_JOBS:
        raise ValueError(f"unknown logical_run_id: {args.logical_run_id}")
    pathology, seed, variants = LOGICAL_JOBS[args.logical_run_id]
    if args.pathology != pathology:
        raise ValueError(f"pathology mismatch for {args.logical_run_id}: {args.pathology} != {pathology}")
    if int(args.seed) != int(seed):
        raise ValueError(f"seed mismatch for {args.logical_run_id}: {args.seed} != {seed}")
    requested = parse_variants(args.variants)
    if requested != variants:
        raise ValueError(f"variant order mismatch: {requested} != {variants}")
    if int(args.optimizer_steps_each) != 6250:
        raise ValueError("optimizer_steps_each must be exactly 6250")
    validation_steps = tuple(int(v) for v in str(args.validation_steps).split("|") if v)
    if validation_steps != (1250, 2500, 3750, 5000, 6250):
        raise ValueError("validation_steps must be 1250|2500|3750|5000|6250")
    return pathology, seed, variants


def required_assets() -> dict[str, Path]:
    return {
        "formal_authorization_gate": REPAIR_ROOT / "formal_authorization_gate.json",
        "source_cache_hashes": RESULT_ROOT / "source_cache_hashes_v2.json",
        "anchor_cache_manifest": RESULT_ROOT / "anchor_cache_manifest_v2.csv",
        "source_cache_manifest": RESULT_ROOT / "source_cache_manifest_v2.csv",
        "prototype_cache_manifest": RESULT_ROOT / "prototype_cache_manifest_v2.csv",
        "matched_schedule_hashes": RESULT_ROOT / "matched_schedule_hashes_v2.json",
    }


def check_preformal_assets() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for name, path in required_assets().items():
        rows[name] = {"path": str(path.relative_to(REPO_ROOT)), "exists": path.exists()}
    gate = required_assets()["formal_authorization_gate"]
    if gate.exists():
        payload = json.loads(gate.read_text())
        rows["formal_authorization_gate"]["decision"] = payload.get("decision")
    decision = "PASS" if all(item.get("exists") for item in rows.values()) and rows["formal_authorization_gate"].get("decision") == "PASS" else "NEEDS_REPAIR_PREFORMAL_ASSETS"
    return {"decision": decision, "assets": rows}


def load_plans_spacing() -> tuple[float, float, float]:
    plans = json.loads(PLANS.read_text())
    return tuple(float(v) for v in PlansManager(plans).get_configuration("3d_fullres").spacing)


def parse_schedule_row(row: dict[str, str]) -> ScheduleRow:
    return ScheduleRow(
        row_index=int(row["row_index"]),
        optimizer_step=int(row["optimizer_step"]),
        microbatch_index=int(row["microbatch_index"]),
        variant=row["variant"],
        pathology=row["pathology"],
        target=row["target"],
        case_id=row["case_id"],
        center_zyx=tuple(int(v) for v in row["center_zyx"].split("x")),  # type: ignore[arg-type]
        rotate_hw_k=int(row["rotate_hw_k"]),
        flip_d=str(row["flip_d"]) == "True",
        flip_h=str(row["flip_h"]) == "True",
        flip_w=str(row["flip_w"]) == "True",
        intensity_seed=int(row["intensity_seed"]),
    )


def schedule_path(logical_run_id: str, variant: str) -> Path:
    return SCHEDULE_DIR / f"{logical_run_id}__{variant}.csv"


def crop_slices(center: tuple[int, int, int], shape: tuple[int, int, int], size: tuple[int, int, int] = (3, 32, 32)) -> tuple[slice, slice, slice]:
    slices = []
    for c, dim, span in zip(center, shape, size):
        start = max(0, min(int(c) - span // 2, dim - span))
        stop = min(dim, start + span)
        slices.append(slice(start, stop))
    return tuple(slices)  # type: ignore[return-value]


def deterministic_coord(mask: np.ndarray, row: ScheduleRow) -> tuple[int, int, int] | None:
    coords = np.argwhere(mask)
    if coords.size == 0:
        return None
    key = f"{row.seed if hasattr(row, 'seed') else ''}|{row.variant}|{row.pathology}|{row.target}|{row.case_id}|{row.row_index}|{row.center_zyx}"
    idx = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16) % len(coords)
    return tuple(int(v) for v in coords[idx])


def target_center(row: ScheduleRow, labels_np: np.ndarray, anchor_pred: np.ndarray, t2_present: bool) -> tuple[int, int, int]:
    if row.target == "scar_positive":
        selected = deterministic_coord(labels_np == 5, row)
    elif row.target == "edema_zone_positive":
        selected = deterministic_coord(((labels_np == 4) | (labels_np == 5)) if t2_present else np.zeros_like(labels_np, dtype=bool), row)
    elif row.target == "anatomy_union":
        selected = deterministic_coord((labels_np == 1) | (labels_np == 4) | (labels_np == 5), row)
    elif row.target == "background":
        selected = deterministic_coord(labels_np == 0, row)
    elif row.target == "anchor_error_hard_negative":
        selected = deterministic_coord((anchor_pred == 5) & (labels_np != 5), row)
    elif row.target == "anchor_error":
        selected = deterministic_coord(((anchor_pred == 4) != (labels_np == 4)) & ((labels_np == 4) | (anchor_pred == 4)), row)
    else:
        selected = None
    return selected if selected is not None else row.center_zyx


def canonical_distance(mask: np.ndarray, spacing: tuple[float, float, float]) -> np.ndarray:
    if mask.any():
        return distance_transform_edt(~mask.astype(bool), sampling=spacing).astype(np.float32)
    return np.full(mask.shape, 999.0, dtype=np.float32)


def transform_tensor(tensor: torch.Tensor, row: ScheduleRow) -> torch.Tensor:
    out = torch.rot90(tensor, k=int(row.rotate_hw_k) % 4, dims=(-2, -1))
    if row.flip_d:
        out = torch.flip(out, dims=(-3,))
    if row.flip_h:
        out = torch.flip(out, dims=(-2,))
    if row.flip_w:
        out = torch.flip(out, dims=(-1,))
    return out.contiguous()


def transform_batch(batch: dict[str, Any], row: ScheduleRow) -> dict[str, Any]:
    transformed: dict[str, Any] = {}
    for key, value in batch.items():
        if torch.is_tensor(value) and value.ndim >= 4 and key != "t2_present":
            transformed[key] = transform_tensor(value, row)
        else:
            transformed[key] = value
    return transformed


class AssetBackedBatchFactory:
    def __init__(self, *, max_cached_cases: int = 8) -> None:
        self.metadata = load_myops_case_metadata(REPO_ROOT)
        self.spacing = load_plans_spacing()
        self.source_paths = {
            (row["case_id"], row["checkpoint_role"], row["field"]): REPO_ROOT / row["cache_path"]
            for row in read_csv_rows(RESULT_ROOT / "source_cache_manifest_v2.csv")
        }
        self.records = [torch.load(path, map_location="cpu", weights_only=False) for path in sorted(PROTOTYPE_DIR.glob("*__prototypes.pt"))]
        self.record_by_case = {record.case_id: record for record in self.records}
        self.max_cached_cases = int(max_cached_cases)
        self.case_cache: dict[str, dict[str, Any]] = {}
        self.case_order: list[str] = []

    def _source_tensor(self, case_id: str, role: str, field: str) -> torch.Tensor:
        payload = torch.load(self.source_paths[(case_id, role, field)], map_location="cpu", weights_only=True)
        tensor = payload["tensor"]
        return tensor[0] if tensor.ndim == 5 and tensor.shape[0] == 1 else tensor

    def _case_payload(self, case_id: str) -> dict[str, Any]:
        if case_id in self.case_cache:
            self.case_order.remove(case_id)
            self.case_order.append(case_id)
            return self.case_cache[case_id]
        anchor = torch.load(ANCHOR_DIR / f"{case_id}__anchor.pt", map_location="cpu", weights_only=True)
        payload = {
            "anchor": anchor,
            "anchor_pred": anchor["canonical_anchor_logits"].argmax(dim=0).cpu().numpy().astype(np.int16),
            "source_features": self._source_tensor(case_id, "teacher_full_view", "full_resolution_feature"),
            "anatomy_logits": self._source_tensor(case_id, "teacher_full_view", "anatomy_logits"),
            "edema_logit": self._source_tensor(case_id, "teacher_full_view", "edema_logit"),
            "scar_margin": self._source_tensor(case_id, "student_reliable_distill", "scar_final_margin"),
            "raw": torch.from_numpy(blosc2.open(str(PREPROCESSED / f"{case_id}.b2nd"), mode="r")[...]).float(),
            "labels_np": blosc2.open(str(PREPROCESSED / f"{case_id}_seg.b2nd"), mode="r")[...][0].astype(np.int16),
            "t2_present": bool(self.metadata[case_id].t2_present),
            "record": self.record_by_case[case_id],
        }
        self.case_cache[case_id] = payload
        self.case_order.append(case_id)
        while len(self.case_order) > self.max_cached_cases:
            old = self.case_order.pop(0)
            self.case_cache.pop(old, None)
        return payload

    def batch_for_row(self, row: ScheduleRow) -> dict[str, Any]:
        payload = self._case_payload(row.case_id)
        labels_np = payload["labels_np"]
        center = target_center(row, labels_np, payload["anchor_pred"], bool(payload["t2_present"]))
        slc = crop_slices(center, labels_np.shape)
        labels = torch.from_numpy(labels_np[slc]).long().unsqueeze(0)
        anchor = payload["anchor"]
        anchor_logits = anchor["canonical_anchor_logits"][(slice(None), *slc)].unsqueeze(0).float()
        anchor_probs = anchor["canonical_anchor_probabilities"][(slice(None), *slc)].unsqueeze(0).float()
        source_features = payload["source_features"][(slice(None), *slc)].unsqueeze(0).float()
        anatomy_logits = payload["anatomy_logits"][(slice(None), *slc)].unsqueeze(0).float()
        edema_logit = payload["edema_logit"][(slice(None), *slc)].unsqueeze(0).float()
        scar_margin = payload["scar_margin"][(slice(None), *slc)].unsqueeze(0).float()
        raw = payload["raw"][(slice(None), *slc)].unsqueeze(0).float()
        bank, _ = select_crossfit_prototype_bank(
            self.records,
            query_case_id=row.case_id,
            query_shard=payload["record"].shard,
            pathology=row.pathology,
        )
        sims = cosine_similarity_maps(source_features[0], bank)
        channel = 5 if row.pathology == "scar" else 4
        union_mask = ((labels_np == 1) | (labels_np == 4) | (labels_np == 5))[slc]
        path_mask = (labels_np == channel)[slc]
        zeros = torch.zeros(1, 1, *labels.shape[1:])
        batch = {
            "case_id": row.case_id,
            "effective_center_zyx": torch.tensor(center, dtype=torch.int16),
            "anchor_logits": anchor_logits,
            "source_features": source_features,
            "distance_to_union_mm": anchor["distance_to_union_mm"][(slice(None), *slc)].unsqueeze(0).float(),
            "t2_present": torch.tensor([float(payload["t2_present"])]),
            "normalized_lge": raw[:, 0:1],
            "normalized_t2": raw[:, 1:2] if raw.shape[1] > 1 else zeros.clone(),
            "teacher_anatomy_probabilities": torch.softmax(anatomy_logits, dim=1),
            "teacher_edema_probability": torch.sigmoid(edema_logit),
            "scar_source_margin": scar_margin,
            "explicit_anchor_probabilities": anchor_probs,
            "explicit_anchor_uncertainty": anchor["anchor_uncertainty"][(slice(None), *slc)].unsqueeze(0).float(),
            "explicit_soft_union_probability": anchor["soft_union_probability"][(slice(None), *slc)].unsqueeze(0).float(),
            "normalized_distance_to_union": (anchor["distance_to_union_mm"][(slice(None), *slc)].unsqueeze(0).float() / 15.0).clamp(0.0, 1.0),
            "prototype_scar_positive_similarity": sims["positive"].unsqueeze(0) if row.pathology == "scar" else zeros.clone(),
            "prototype_scar_negative_similarity": sims["negative"].unsqueeze(0) if row.pathology == "scar" else zeros.clone(),
            "prototype_edema_positive_similarity": sims["positive"].unsqueeze(0) if row.pathology == "edema" else zeros.clone(),
            "prototype_edema_negative_similarity": sims["negative"].unsqueeze(0) if row.pathology == "edema" else zeros.clone(),
            "labels": labels,
            "distance_to_gt_union_mm": torch.from_numpy(canonical_distance(union_mask, self.spacing)).unsqueeze(0).unsqueeze(0),
            "distance_to_gt_pathology_surface_mm": torch.from_numpy(canonical_distance(path_mask, self.spacing)).unsqueeze(0).unsqueeze(0),
        }
        return transform_batch(batch, row)


def iter_schedule_batches(logical_run_id: str, variant: str, factory: AssetBackedBatchFactory):
    rows = read_csv_rows(schedule_path(logical_run_id, variant))
    for raw in rows:
        yield factory.batch_for_row(parse_schedule_row(raw))


def contract_payload() -> dict[str, Any]:
    return {
        "entrypoint": "scripts/training/run_care_srr_cascade_formal.py",
        "logical_jobs": {key: {"pathology": v[0], "seed": v[1], "variants": v[2]} for key, v in LOGICAL_JOBS.items()},
        "control_then_srr": True,
        "optimizer_steps_each": 6250,
        "validation_steps": [1250, 2500, 3750, 5000, 6250],
        "checkpoint_schema": checkpoint_schema_contract(),
        "formal_authorization_gate_required": True,
        "dry_run_has_formal_training_credit": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--logical-run-id", required=False, default="scar_seed20260724")
    parser.add_argument("--pathology", choices=["scar", "edema"], default="scar")
    parser.add_argument("--seed", type=int, default=20260724)
    parser.add_argument("--variants", default="scar_cascade_control|scar_srr_cascade")
    parser.add_argument("--optimizer-steps-each", type=int, default=6250)
    parser.add_argument("--validation-steps", default="1250|2500|3750|5000|6250")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-contract", action="store_true")
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = parser.parse_args()

    if args.print_contract:
        print(json.dumps(contract_payload(), indent=2, sort_keys=True))
        return 0

    pathology, seed, variants = validate_formal_args(args)
    asset_status = check_preformal_assets()
    schedule_rows_by_variant = {variant: [parse_schedule_row(row) for row in read_csv_rows(schedule_path(args.logical_run_id, variant))] for variant in variants}
    schedule_sha_by_variant = {variant: schedule_sha256(rows) for variant, rows in schedule_rows_by_variant.items()}
    first_batch_status: dict[str, Any] = {}
    if asset_status["decision"] == "PASS":
        try:
            factory = AssetBackedBatchFactory(max_cached_cases=2)
            for variant in variants:
                batch = factory.batch_for_row(schedule_rows_by_variant[variant][0])
                first_batch_status[variant] = {
                    "decision": "PASS",
                    "case_id": batch["case_id"],
                    "anchor_shape": list(batch["anchor_logits"].shape),
                    "source_shape": list(batch["source_features"].shape),
                    "label_shape": list(batch["labels"].shape),
                    "label_values": sorted(int(v) for v in torch.unique(batch["labels"]).tolist()),
                }
        except Exception as exc:
            first_batch_status = {"decision": "NEEDS_REPAIR_ASSET_BACKED_STREAM", "error": repr(exc)}
            asset_status = {**asset_status, "decision": "NEEDS_REPAIR_ASSET_BACKED_STREAM"}
    receipt = {
        "logical_run_id": args.logical_run_id,
        "pathology": pathology,
        "seed": seed,
        "variants": list(variants),
        "control_then_srr": True,
        "optimizer_steps_each": int(args.optimizer_steps_each),
        "validation_steps": [int(v) for v in str(args.validation_steps).split("|") if v],
        "schedule_rows_per_variant": {variant: len(rows) for variant, rows in schedule_rows_by_variant.items()},
        "schedule_sha256_by_variant": schedule_sha_by_variant,
        "asset_backed_stream_first_batch": first_batch_status,
        "asset_status": asset_status,
        "formal_training_credit": 0 if args.dry_run else "PENDING_REAL_RUN",
        "decision": "PASS_DRY_RUN" if args.dry_run and asset_status["decision"] == "PASS" else asset_status["decision"],
    }
    out = FORMAL_ROOT / args.logical_run_id / "formal_entrypoint_receipt.json"
    write_json(out, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if args.dry_run:
        return 0 if asset_status["decision"] == "PASS" else 2
    if asset_status["decision"] != "PASS":
        return 2
    if not acquire_logical_run_lock(args.logical_run_id):
        return 0

    base_model = CARESRRCascadeRescue(source_feature_channels=32)
    initial_state_bytes = json.dumps({k: list(v.shape) for k, v in base_model.state_dict().items()}, sort_keys=True).encode("utf-8")
    initial_state_sha = sha256_file(CONFIG_PATH) + "." + str(len(initial_state_bytes))
    for variant in variants:
        model = CARESRRCascadeRescue(source_feature_channels=32)
        model.load_state_dict(base_model.state_dict())
        runtime = FormalRuntimeConfig(
            logical_run_id=args.logical_run_id,
            pathology=pathology,
            variant=variant,
            seed=seed,
            optimizer_steps=int(args.optimizer_steps_each),
        )
        trainer = CARESRRCascadeFormalTrainer(model=model, config=runtime, device=args.device, use_amp=torch.cuda.is_available())
        run_dir = FORMAL_ROOT / args.logical_run_id / variant
        try:
            factory = AssetBackedBatchFactory(max_cached_cases=8)
            stats = trainer.train_microbatches(iter_schedule_batches(args.logical_run_id, variant, factory))
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            failure = {
                "decision": "NEEDS_REPAIR_ASSET_BACKED_STREAM_FAILED",
                "variant": variant,
                "error": str(exc),
                "formal_training_credit": 0,
            }
            write_json(run_dir / "runtime_failure.json", failure)
            print(json.dumps(failure, indent=2, sort_keys=True))
            return 2
        checkpoint = trainer.save_checkpoint(
            run_dir / "checkpoints" / "checkpoint_final.pt",
            schedule_sha256=schedule_sha_by_variant[variant],
            initial_state_sha256=initial_state_sha,
            code_sha256=sha256_file(Path(__file__)),
            config_sha256=sha256_file(CONFIG_PATH),
            source_cache_sha256=sha256_file(required_assets()["source_cache_hashes"]),
            anchor_cache_sha256=sha256_file(required_assets()["anchor_cache_manifest"]),
            prototype_cache_sha256=sha256_file(required_assets()["prototype_cache_manifest"]),
        )
        write_json(
            run_dir / "training_summary.json",
            {
                "decision": "PASS" if stats["optimizer_step"] == int(args.optimizer_steps_each) else "NEEDS_REPAIR",
                "variant": variant,
                "stats": stats,
                "checkpoint": checkpoint,
            },
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
