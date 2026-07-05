#!/usr/bin/env python3
"""Eval existing SRR-v2.5 bounded checkpoints on the full fold0 validation split."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    evaluate,
    load_myops_case_metadata,
    load_split,
    parse_float_list,
    read_anchored_case,
)
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402


DEFAULT_MATRIX_ROOT = (
    REPO_ROOT / "results/20260704_srr_v25_training_ablation_matrix/bounded_matrix"
)
DEFAULT_OUTPUT_ROOT = (
    REPO_ROOT / "results/20260704_srr_v25_training_ablation_matrix/full_fold0_eval"
)
DEFAULT_VARIANTS = (
    "srr_propref_shared_dual_dict",
    "srr_propref_no_proto_cascade",
    "srr_propref_scar_precision",
    "srr_v25_no_local_refine",
    "srr_v25_no_anatomy_roi",
    "srr_v25_no_anchor",
)


def resolve_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, manifest: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def checkpoint_args(checkpoint: dict[str, object], summary: dict[str, object]) -> SimpleNamespace:
    raw = checkpoint.get("args", {})
    if not isinstance(raw, dict):
        raw = {}
    merged = dict(raw)
    merged.setdefault("variant", summary.get("model_variant", summary.get("variant", "srr_propref_shared_dual_dict")))
    merged.setdefault("base_channels", summary.get("base_channels", 4))
    merged.setdefault("encoder_profile", summary.get("encoder_profile", "tiny_3scale"))
    merged.setdefault("disable_local_refinement", summary.get("disable_local_refinement", False))
    merged.setdefault("disable_anatomy_roi_prior", summary.get("disable_anatomy_roi_prior", False))
    merged.setdefault("disable_nnunet_anchor", summary.get("disable_nnunet_anchor", False))
    merged.setdefault("scar_decode_threshold", summary.get("scar_decode_threshold", 0.50))
    merged.setdefault("edema_decode_threshold", summary.get("edema_decode_threshold", 0.50))
    merged.setdefault("proposal_thresholds", ",".join(str(v) for v in summary.get("proposal_thresholds", []) or []))
    if not merged.get("proposal_thresholds"):
        merged["proposal_thresholds"] = "0.05,0.10,0.20,0.30,0.40,0.50,0.60,0.70,0.80,0.90"
    return SimpleNamespace(**merged)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--matrix-root", type=Path, default=DEFAULT_MATRIX_ROOT)
    ap.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    ap.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--checkpoint-name", default="checkpoint_final")
    ap.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    ap.add_argument("--nnunet-anchor-root", type=Path, default=DEFAULT_NNUNET_ANCHOR_ROOT)
    ap.add_argument("--limit-cases", type=int, default=0)
    args = ap.parse_args()

    matrix_root = resolve_path(args.matrix_root)
    output_root = resolve_path(args.output_root)
    anchor_root = resolve_path(args.nnunet_anchor_root)
    variants = [item.strip() for item in args.variants.replace(";", ",").split(",") if item.strip()]
    _train_ids, val_ids = load_split(args.fold)
    if args.limit_cases > 0:
        val_ids = val_ids[: int(args.limit_cases)]
    metadata = load_myops_case_metadata()
    val_cases = [read_anchored_case(case_id, metadata, anchor_root) for case_id in val_ids]
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")

    manifest_path = output_root / "manifest.json"
    previous_manifest = read_json(manifest_path)
    previous_is_same_eval = (
        previous_manifest.get("fold") == int(args.fold)
        and previous_manifest.get("eval_case_count") == len(val_cases)
    )
    previous_variants = previous_manifest.get("variants", {}) if previous_is_same_eval else {}
    if not isinstance(previous_variants, dict):
        previous_variants = {}
    previous_completed = previous_manifest.get("completed_variants", []) if previous_is_same_eval else []
    if not isinstance(previous_completed, list):
        previous_completed = []
    completed_variants = [str(item) for item in previous_completed]

    manifest: dict[str, object] = {
        "matrix_root": str(matrix_root),
        "output_root": str(output_root),
        "fold": int(args.fold),
        "checkpoint_name": args.checkpoint_name,
        "device": str(device),
        "eval_case_count": len(val_cases),
        "eval_case_ids": val_ids,
        "variants": previous_variants,
        "completed_variants": completed_variants,
        "previous_status": previous_manifest.get("status", "") if previous_is_same_eval else "",
        "status": "RUNNING_OR_INTERRUPTED",
        "mode": "eval_only_existing_bounded_checkpoints_no_training_no_upload",
    }
    write_manifest(manifest_path, manifest)

    for variant in variants:
        src_dir = matrix_root / "variants" / variant
        src_summary = read_json(src_dir / "summary.json")
        checkpoint_path = src_dir / "checkpoints/fold_0/propref_config" / f"{args.checkpoint_name}.pt"
        if not checkpoint_path.is_file():
            raise FileNotFoundError(checkpoint_path)
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        run_args = checkpoint_args(checkpoint, src_summary)
        model = SRRProposeRefineMyoPS(
            base_channels=int(run_args.base_channels),
            variant=str(run_args.variant),
            encoder_profile=str(run_args.encoder_profile),
            disable_local_refinement=bool(run_args.disable_local_refinement),
            disable_anatomy_roi_prior=bool(run_args.disable_anatomy_roi_prior),
        ).to(device)
        model.load_state_dict(checkpoint["model_state_dict"])
        out_dir = output_root / "variants" / variant
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_dir / "summary.json", out_dir / "bounded_source_summary.json")
        evaluate(
            model,
            val_cases,
            out_dir,
            variant,
            device,
            disable_nnunet_anchor=bool(run_args.disable_nnunet_anchor),
            checkpoint_name=f"{args.checkpoint_name}_full_fold0",
            proposal_thresholds=parse_float_list(str(run_args.proposal_thresholds)),
            scar_decode_threshold=float(run_args.scar_decode_threshold),
            edema_decode_threshold=float(run_args.edema_decode_threshold),
        )
        manifest["variants"][variant] = {
            "source_checkpoint": str(checkpoint_path),
            "source_summary": str(src_dir / "summary.json"),
            "output_dir": str(out_dir),
            "model_variant": str(run_args.variant),
            "disable_local_refinement": bool(run_args.disable_local_refinement),
            "disable_anatomy_roi_prior": bool(run_args.disable_anatomy_roi_prior),
            "disable_nnunet_anchor": bool(run_args.disable_nnunet_anchor),
        }
        if variant not in manifest["completed_variants"]:
            manifest["completed_variants"].append(variant)
        write_manifest(manifest_path, manifest)

    manifest["status"] = "COMPLETE"
    write_manifest(manifest_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
