#!/usr/bin/env python3
"""Batch 3A MyoPS SRR model-in-loop inference/export authority."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import load_split  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    read_anchored_case,
    safety_context_dicts_from_raw,
    full_case_anchor_tensors,
)
from scripts.srr_production.validate_myops_mainline import (  # noqa: E402
    choose_source_cases,
    fit_real_banks,
    select_smoke_cases,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import (  # noqa: E402
    build_anchor_manifest,
    find_anchor_paths,
    rel,
    sha256_file,
    sha256_text,
)
from src.care_myocardium.srr_production.checkpoint import (  # noqa: E402
    checkpoint_receipt,
    load_srr_checkpoint,
    save_srr_checkpoint,
)

SPLIT_NNUNET = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
BATCH5_MODES = (
    "anchor_identity_control",
    "anchor_bounded_full",
    "srr_no_anchor_control",
    "anchor_bounded_proposal_only",
    "anchor_bounded_refiner_only",
    "production_gate_closed",
    "production_gate_open_bounded_control",
)
BATCH6_MODES = (
    "anchor_identity_control",
    "full_learned_gate",
    "full_gate_one",
    "full_gate_zero",
    "proposal_only_gate_one",
    "refiner_only_gate_one",
)
BATCH7_MODES = (
    "anchor_identity",
    "production_gate_closed",
    "full_learned",
    "production_gate_one",
    "proposal_only_gate_one",
    "refiner_only_gate_one",
    "learned_source_gate_one",
    "old_batch4_asset",
    "rebuilt_batch7_asset",
    "prototype_maps_off",
    "semantic_negative_memory_off",
    "zero_anchor_pathology_context",
    "zero_anchor_confirmation_context",
    "discovery_off",
    "proposal_only",
    "refiner_only",
    "learned_source",
    "gt_oracle_source_diagnostic_only",
    "production_gate_closed",
    "production_gate_learned",
    "production_gate_one",
    "no_anchor_diagnostic",
    "anchor_identity_control",
    "srr_no_anchor_control",
)
BATCH5_PRODUCTION_INTERVENTIONS = {
    "anchor_identity_control": "full",
    "anchor_bounded_srr_correction": "full",
    "anchor_bounded_full": "full",
    "full_learned_gate": "full",
    "srr_no_anchor_control": "full",
    "anchor_bounded_proposal_only": "proposal_only",
    "anchor_bounded_refiner_only": "refiner_only",
    "proposal_only_gate_one": "proposal_only_gate_one",
    "refiner_only_gate_one": "refiner_only_gate_one",
    "production_gate_closed": "gate_closed",
    "full_gate_zero": "gate_closed",
    "production_gate_open_bounded_control": "gate_open_bounded_control",
    "full_gate_one": "gate_open_bounded_control",
    "anchor_identity": "full",
    "old_batch4_asset": "learned_source",
    "rebuilt_batch7_asset": "learned_source",
    "prototype_maps_off": "prototype_maps_off",
    "semantic_negative_memory_off": "semantic_negative_memory_off",
    "zero_anchor_pathology_context": "zero_anchor_pathology_context",
    "discovery_off": "discovery_off",
    "proposal_only": "proposal_only",
    "refiner_only": "refiner_only",
    "learned_source": "learned_source",
    "gt_oracle_source_diagnostic_only": "gt_oracle_source_diagnostic_only",
    "production_gate_learned": "learned_source",
    "production_gate_one": "gate_open_bounded_control",
    "full_learned": "learned_source",
    "learned_source_gate_one": "learned_source_gate_one",
    "zero_anchor_confirmation_context": "zero_anchor_confirmation_context",
    "no_anchor_diagnostic": "learned_source",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def fold_cases(split_path: Path, fold: int, max_cases: int = 0) -> list[str]:
    cases = sorted(load_json(split_path)["folds"][fold]["val"])
    return cases[:max_cases] if max_cases > 0 else cases


def image_geometry(path: Path) -> dict[str, Any]:
    img = sitk.ReadImage(str(path))
    return {
        "size_xyz": list(img.GetSize()),
        "spacing_xyz": list(img.GetSpacing()),
        "origin_xyz": list(img.GetOrigin()),
        "direction": list(img.GetDirection()),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def runtime_final_output_mode(mode: str) -> str:
    return "srr_no_anchor_control" if mode in {"srr_no_anchor_control", "no_anchor_diagnostic"} else "anchor_bounded_srr_correction"


def normalized_mode(mode: str) -> str:
    aliases = {
        "anchor_bounded_srr_correction": "anchor_bounded_full",
        "full_learned_gate": "anchor_bounded_full",
        "full_gate_one": "production_gate_open_bounded_control",
        "full_gate_zero": "production_gate_closed",
        "proposal_only_gate_one": "anchor_bounded_proposal_only",
        "refiner_only_gate_one": "anchor_bounded_refiner_only",
        "anchor_identity": "anchor_identity_control",
        "full_learned": "learned_source",
        "rebuilt_batch7_asset": "learned_source",
        "production_gate_one": "production_gate_open_bounded_control",
        "learned_source_gate_one": "learned_source_gate_one",
        "zero_anchor_confirmation_context": "zero_anchor_confirmation_context",
        "production_gate_learned": "learned_source",
        "no_anchor_diagnostic": "srr_no_anchor_control",
    }
    return aliases.get(str(mode), str(mode))


def configured_modes(cfg: dict[str, Any]) -> set[str]:
    modes = cfg.get("modes")
    if isinstance(modes, list):
        return {str(item) for item in modes}
    interventions = cfg.get("intervention_execution", {})
    if isinstance(interventions, dict) and isinstance(interventions.get("modes"), list):
        return {str(item) for item in interventions["modes"]}
    interventions = cfg.get("runtime_interventions", {})
    if isinstance(interventions, dict) and isinstance(interventions.get("modes"), list):
        return {str(item) for item in interventions["modes"]}
    return {"anchor_identity_control", "anchor_bounded_srr_correction", "srr_no_anchor_control"}


def load_memory_asset_fail_closed(model: torch.nn.Module, asset_path: Path, device: torch.device) -> dict[str, Any]:
    asset = torch.load(asset_path, map_location=device, weights_only=False)
    state = dict(asset.get("model_memory_state", asset))
    model_state = model.state_dict()
    required_prefixes = ("cross_fitted_memory.",)
    allowed_prefixes = ("cross_fitted_memory.", "scar_dictionary.", "edema_dictionary.")
    required = sorted(key for key in model_state if key.startswith(required_prefixes))
    missing_required = [key for key in required if key not in state]
    invalid_keys = [
        key
        for key, value in state.items()
        if key not in model_state or not key.startswith(allowed_prefixes) or not isinstance(value, torch.Tensor)
    ]
    shape_mismatch = [
        key
        for key, value in state.items()
        if key in model_state
        and key not in invalid_keys
        and tuple(value.shape) != tuple(model_state[key].shape)
    ]
    if missing_required or invalid_keys or shape_mismatch:
        raise ValueError(
            "invalid semantic memory asset state: "
            f"missing_required={missing_required[:8]} invalid_keys={invalid_keys[:8]} shape_mismatch={shape_mismatch[:8]}"
        )
    load_result = model.load_state_dict(state, strict=False)
    unexpected = list(load_result.unexpected_keys)
    if unexpected:
        raise ValueError(f"unexpected keys while loading semantic memory asset: {unexpected[:8]}")
    return {
        "path": rel(asset_path, REPO_ROOT),
        "sha256": sha256_file(asset_path),
        "required_memory_key_count": len(required),
        "loaded_state_key_count": len(state),
        "missing_required_memory_keys": missing_required,
        "invalid_asset_keys": invalid_keys,
        "shape_mismatch_keys": shape_mismatch,
        "ignored_nonmemory_model_missing_key_count": len(load_result.missing_keys),
    }


def model_from_config(cfg: dict[str, Any], mode: str) -> SRRProposeRefineMyoPS:
    model_cfg = cfg.get("model", {}) or {}
    return SRRProposeRefineMyoPS(
        base_channels=int(model_cfg.get("base_channels", 2)),
        variant=str(model_cfg.get("variant", "srr_propref_shared_dual_dict")),
        encoder_profile=str(model_cfg.get("encoder_profile", "tiny_3scale")),
        disable_local_refinement=bool(model_cfg.get("disable_local_refinement", False)),
        disable_anatomy_roi_prior=bool(model_cfg.get("disable_anatomy_roi_prior", False)),
        final_output_mode=runtime_final_output_mode(mode),
    )


def architecture_config(cfg: dict[str, Any], mode: str) -> dict[str, Any]:
    model_cfg = dict(cfg.get("model", {}) or {})
    return {
        "class_name": "SRRProposeRefineMyoPS",
        "base_channels": int(model_cfg.get("base_channels", 2)),
        "variant": str(model_cfg.get("variant", "srr_propref_shared_dual_dict")),
        "encoder_profile": str(model_cfg.get("encoder_profile", "tiny_3scale")),
        "disable_local_refinement": bool(model_cfg.get("disable_local_refinement", False)),
        "disable_anatomy_roi_prior": bool(model_cfg.get("disable_anatomy_roi_prior", False)),
    }


def manifest_hash(manifest: dict[str, Any]) -> str:
    return sha256_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")))


def tensor_stats(prefix: str, tensor: torch.Tensor) -> dict[str, float]:
    value = tensor.detach().abs().float().flatten().cpu()
    if value.numel() == 0:
        return {
            f"{prefix}_abs_mean": 0.0,
            f"{prefix}_abs_p95": 0.0,
            f"{prefix}_abs_max": 0.0,
        }
    return {
        f"{prefix}_abs_mean": float(value.mean()),
        f"{prefix}_abs_p95": float(torch.quantile(value, 0.95)),
        f"{prefix}_abs_max": float(value.max()),
    }


def gate_stats(prefix: str, tensor: torch.Tensor) -> dict[str, float]:
    value = tensor.detach().float().flatten().cpu()
    if value.numel() == 0:
        return {
            f"{prefix}_mean": 0.0,
            f"{prefix}_p50": 0.0,
            f"{prefix}_p95": 0.0,
            f"{prefix}_max": 0.0,
        }
    return {
        f"{prefix}_mean": float(value.mean()),
        f"{prefix}_p50": float(torch.quantile(value, 0.50)),
        f"{prefix}_p95": float(torch.quantile(value, 0.95)),
        f"{prefix}_max": float(value.max()),
    }


def training_summary_anchor_hash(summary_path: Path | None) -> str:
    if summary_path is None:
        return ""
    if not summary_path.is_file():
        raise FileNotFoundError(f"training summary not found: {summary_path}")
    summary = load_json(summary_path)
    manifest = summary.get("nnunet_anchor_manifest")
    if not isinstance(manifest, dict):
        raise ValueError(f"{summary_path} does not contain nnunet_anchor_manifest")
    return manifest_hash(manifest)


def build_zero_step_checkpoint(
    *,
    cfg: dict[str, Any],
    mode: str,
    manifest: dict[str, Any],
    checkpoint_path: Path,
    anchor_root: Path,
    split_hash: str,
    device: torch.device,
) -> tuple[Path, dict[str, Any]]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    selected = select_smoke_cases(manifest)
    source_ids = choose_source_cases(selected)
    source_cases = [read_anchored_case(cid, metadata, anchor_root) for cid in source_ids]
    model = model_from_config(cfg, mode).to(device)
    prototype_memory_provenance = fit_real_banks(model, source_cases, (4, 32, 32), device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    save_srr_checkpoint(
        path=checkpoint_path,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        global_step=0,
        epoch=0,
        final_output_mode=runtime_final_output_mode(mode),
        architecture_config=architecture_config(cfg, mode),
        oof_anchor_manifest_hash=manifest_hash(manifest),
        prototype_memory_provenance=prototype_memory_provenance,
        split_hash=split_hash,
        source_commit=git_head(),
        best_metric_state={"status": "ZERO_STEP_DIAGNOSTIC_NO_TRAINING", "metric_claim": "NONE"},
    )
    return checkpoint_path, prototype_memory_provenance


def load_checkpoint_into_model(
    *,
    cfg: dict[str, Any],
    mode: str,
    checkpoint_path: Path,
    manifest: dict[str, Any],
    split_hash: str,
    device: torch.device,
    training_anchor_manifest_hash: str = "",
) -> tuple[SRRProposeRefineMyoPS, dict[str, Any], dict[str, Any]]:
    model = model_from_config(cfg, mode).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    payload = load_srr_checkpoint(
        path=checkpoint_path,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        map_location=device,
        restore_rng=False,
        restore_optimizer=False,
    )
    expected_arch = architecture_config(cfg, mode)
    actual_arch = dict(payload.get("architecture_config", {}) or {})
    for key, expected in expected_arch.items():
        if actual_arch.get(key) != expected:
            raise ValueError(f"checkpoint architecture mismatch for {key}: {actual_arch.get(key)!r} != {expected!r}")
    full_manifest_hash = manifest_hash(manifest)
    accepted_hashes = {full_manifest_hash}
    if training_anchor_manifest_hash:
        accepted_hashes.add(training_anchor_manifest_hash)
    if str(payload.get("oof_anchor_manifest_hash")) not in accepted_hashes:
        raise ValueError("checkpoint OOF anchor manifest hash mismatch")
    if str(payload.get("split_hash")) != str(split_hash):
        raise ValueError("checkpoint split hash mismatch")
    return model, payload, checkpoint_receipt(checkpoint_path, payload)


def prediction_image_from_array(arr: np.ndarray, reference: sitk.Image) -> sitk.Image:
    img = sitk.GetImageFromArray(arr.astype(np.uint8, copy=False))
    img.CopyInformation(reference)
    return img


def run(args: argparse.Namespace) -> dict[str, Any]:
    cfg_path = Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path = REPO_ROOT / cfg_path
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    paths = cfg["paths"]
    split_path = REPO_ROOT / paths["split_path"]
    raw_root = REPO_ROOT / paths["raw_root"]
    gt_dir = REPO_ROOT / paths["gt_dir"]
    anchor_root = REPO_ROOT / paths["anchor_root"]
    out_root = Path(args.output_root or paths["inference_root"])
    if not out_root.is_absolute():
        out_root = REPO_ROOT / out_root
    raw_mode = str(args.mode)
    cfg_modes = configured_modes(cfg)
    mode = normalized_mode(raw_mode) if normalized_mode(raw_mode) in cfg_modes else raw_mode
    if mode not in cfg_modes:
        raise ValueError(f"unsupported inference mode {mode!r}")
    if mode != "anchor_identity_control" and not args.checkpoint and not args.allow_untrained_diagnostic:
        raise ValueError(
            f"{mode} requires --checkpoint, or --allow-untrained-diagnostic to write a zero-step diagnostic receipt"
        )

    device = torch.device(args.device)
    case_ids = [item.strip() for item in args.cases.split(",") if item.strip()] if args.cases else fold_cases(split_path, args.fold, args.max_cases)
    manifest = build_anchor_manifest(
        repo_root=REPO_ROOT,
        anchor_root=anchor_root,
        protocol_split=split_path,
        nnunet_split=SPLIT_NNUNET,
        raw_root=raw_root,
        preprocessed_root=PREPROCESSED,
        out_path=out_root / "batch3a_raw_oof_anchor_manifest.json",
    )
    split_hash = sha256_file(split_path)
    summary_path = Path(args.training_summary) if args.training_summary else None
    if summary_path is not None and not summary_path.is_absolute():
        summary_path = REPO_ROOT / summary_path
    compact_anchor_manifest_hash = training_summary_anchor_hash(summary_path)
    checkpoint_path = Path(args.checkpoint) if args.checkpoint else out_root / "runtime_checkpoints" / f"{mode}_zero_step_diagnostic.pth"
    if not checkpoint_path.is_absolute():
        checkpoint_path = REPO_ROOT / checkpoint_path
    prototype_memory_provenance: dict[str, Any] | None = None
    if not checkpoint_path.is_file():
        if not args.allow_untrained_diagnostic:
            raise FileNotFoundError(f"checkpoint not found: {checkpoint_path}")
        checkpoint_path, prototype_memory_provenance = build_zero_step_checkpoint(
            cfg=cfg,
            mode=mode,
            manifest=manifest,
            checkpoint_path=checkpoint_path,
            anchor_root=anchor_root,
            split_hash=split_hash,
            device=device,
        )
    model, payload, ckpt_receipt = load_checkpoint_into_model(
        cfg=cfg,
        mode=mode,
        checkpoint_path=checkpoint_path,
        manifest=manifest,
        split_hash=split_hash,
        device=device,
        training_anchor_manifest_hash=compact_anchor_manifest_hash,
    )
    semantic_asset_raw = str(paths.get("semantic_memory_asset", "") or "").strip()
    if semantic_asset_raw:
        semantic_asset_path = Path(semantic_asset_raw)
        if not semantic_asset_path.is_absolute():
            semantic_asset_path = REPO_ROOT / semantic_asset_path
        if semantic_asset_path.is_file():
            ckpt_receipt["semantic_memory_asset"] = load_memory_asset_fail_closed(model, semantic_asset_path, device)
    model.eval()
    metadata = load_myops_case_metadata(REPO_ROOT)
    pred_dir = out_root / mode / "predictions"
    rows: list[dict[str, Any]] = []
    tensor_rows: list[dict[str, Any]] = []
    for cid in case_ids:
        source_fold, prob_path, pred_path = find_anchor_paths(cid, anchor_root)
        case = read_anchored_case(cid, metadata, anchor_root)
        gt_path = gt_dir / f"{cid}.nii.gz"
        gt_img = sitk.ReadImage(str(gt_path))
        out_path = pred_dir / f"{cid}.nii.gz"
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        raw_anchor, raw_component = full_case_anchor_tensors(case, device)
        safety_anchor, safety_component = safety_context_dicts_from_raw(raw_anchor, raw_component, av)
        with torch.no_grad():
            outputs = model(
                x,
                av,
                anchor_features=raw_anchor,
                component_features=raw_component,
                safety_anchor_features=safety_anchor,
                safety_component_features=safety_component,
                memory_query_policy="validation_inference_all_train_shards",
                case_ids=[cid],
                anchor_identity_control=mode in {"anchor_identity_control", "anchor_identity"},
                production_intervention_mode=BATCH5_PRODUCTION_INTERVENTIONS.get(mode, "full"),
            )
        raw_anchor_labels = raw_anchor["probabilities"].argmax(dim=1)[0].detach().cpu().numpy().astype(np.uint8)
        model_labels = outputs["logits"].argmax(dim=1)[0].detach().cpu().numpy().astype(np.uint8)
        out_arr = model_labels
        out_path.parent.mkdir(parents=True, exist_ok=True)
        sitk.WriteImage(prediction_image_from_array(out_arr, gt_img), str(out_path))
        source_arr = sitk.GetArrayFromImage(sitk.ReadImage(str(pred_path))).astype(np.uint8, copy=False)
        written_arr = sitk.GetArrayFromImage(sitk.ReadImage(str(out_path))).astype(np.uint8, copy=False)
        changed_voxels = int(np.count_nonzero(written_arr != source_arr))
        correction = float(outputs["bounded_scar_correction"].abs().max().detach().cpu())
        correction = max(correction, float(outputs["bounded_edema_correction"].abs().max().detach().cpu()))
        no_t2 = not bool(case.availability[1] > 0)
        no_t2_values = {
            "edema_candidate_probability_abs_max": float(outputs["edema_candidate_probability"].abs().max().detach().cpu()),
            "edema_soft_roi_abs_max": float(outputs["edema_soft_roi"].abs().max().detach().cpu()),
            "edema_refinement_residual_abs_max": float(outputs["edema_refinement_residual"].abs().max().detach().cpu()),
            "bounded_edema_correction_abs_max": float(outputs["bounded_edema_correction"].abs().max().detach().cpu()),
        }
        production_rows = []
        for pathology, channel, gate_channel in (("edema", 4, 1), ("scar", 5, 0)):
            raw_key = f"raw_{pathology}_correction"
            bounded_key = f"bounded_{pathology}_correction"
            proposal_key = f"{pathology}_proposal_logits"
            residual_key = f"{pathology}_refinement_residual"
            production_rows.append(
                {
                    "case_id": cid,
                    "mode": mode,
                    "pathology": pathology,
                    "class_id": channel,
                    "production_intervention_mode": outputs["production_intervention_mode"],
                    **gate_stats("production_gate", outputs["production_correction_gate"][:, gate_channel : gate_channel + 1]),
                    **tensor_stats("raw_correction", outputs[raw_key]),
                    **tensor_stats("bounded_correction", outputs[bounded_key]),
                    "proposal_positive_voxels": int((outputs[proposal_key].detach().sigmoid() >= 0.5).sum().cpu()),
                    "refiner_positive_voxels": int((outputs[f"{pathology}_logits"].detach().sigmoid() >= 0.5).sum().cpu()),
                    "refiner_residual_abs_mean": float(outputs[residual_key].detach().abs().mean().cpu()),
                    "changed_voxels_vs_anchor": int(np.count_nonzero((written_arr == channel) != (source_arr == channel))),
                }
            )
        final_anchor_softmax_delta = float(
            (
                torch.softmax(outputs["logits"], dim=1)
                - torch.softmax(outputs["nnunet_anchor_logits"], dim=1)
            )
            .abs()
            .max()
            .detach()
            .cpu()
        )
        rows.append(
            {
                "case_id": cid,
                "mode": mode,
                "source_fold": source_fold,
                "image_shape_zyx": list(case.image.shape[-3:]),
                "availability_lge_t2_c0": ",".join(str(float(v)) for v in case.availability.tolist()),
                "source_probability_path": rel(prob_path, REPO_ROOT),
                "source_prediction_path": rel(pred_path, REPO_ROOT),
                "output_prediction_path": rel(out_path, REPO_ROOT),
                "gt_path": rel(gt_path, REPO_ROOT),
                "model_forward_count": 1,
                "checkpoint_actual_load_count": 1,
                "prototype_memory_actual_load_count": 1,
                "memory_query_policy": str(outputs["memory_query_policy"]),
                "raw_anchor_used_for_final_baseline": bool(outputs["raw_anchor_used_for_final_baseline"].detach().cpu().item()),
                "safety_context_used_for_srr_evidence": bool(outputs["safety_context_used_for_srr_evidence"].detach().cpu().item()),
                "changed_voxels": changed_voxels,
                "raw_label_mismatch": int(np.count_nonzero(raw_anchor_labels != source_arr)),
                "anchor_identity_softmax_max_abs_delta": final_anchor_softmax_delta if mode in {"anchor_identity_control", "anchor_identity"} else "",
                "nonidentity_downstream_tensor_max_abs_delta": 0.0 if mode in {"anchor_identity_control", "anchor_identity"} else correction,
                "no_t2_case": no_t2,
                "no_t2_full_chain_exact_zero": (not no_t2) or all(value == 0.0 for value in no_t2_values.values()),
                "geometry_matches_gt": image_geometry(out_path) == image_geometry(gt_path),
                "output_sha256": sha256_file(out_path),
            }
        )
        for production_row in production_rows:
            tensor_rows.append({"case_id": cid, **no_t2_values, **production_row})

    geometry_csv = out_root / f"batch3a_{mode}_geometry_roundtrip.csv"
    tensor_csv = out_root / f"batch3a_{mode}_tensor_checks.csv"
    write_csv(geometry_csv, rows)
    write_csv(tensor_csv, tensor_rows)
    changed_total = int(sum(int(row["changed_voxels"]) for row in rows))
    nonidentity_tensor_delta = max(float(row["nonidentity_downstream_tensor_max_abs_delta"]) for row in rows) if rows else 0.0
    identity_softmax_max_abs_delta = (
        max(float(row["anchor_identity_softmax_max_abs_delta"]) for row in rows)
        if mode in {"anchor_identity_control", "anchor_identity"} and rows
        else 0.0
    )
    status = "SRR_MODEL_IN_LOOP_UNTRAINED_DIAGNOSTIC" if int(payload.get("global_step", 0)) == 0 else "SRR_MODEL_IN_LOOP_CHECKPOINT_INFERENCE"
    if mode in {"anchor_identity_control", "anchor_identity"} and changed_total != 0:
        status = "BATCH3A_NEEDS_REPAIR_ANCHOR_IDENTITY_NOT_EXACT"
    if mode in {"anchor_identity_control", "anchor_identity"} and identity_softmax_max_abs_delta > 1e-6:
        status = "BATCH3A_NEEDS_REPAIR_ANCHOR_IDENTITY_SOFTMAX_NOT_EXACT"
    zero_delta_control_modes = {"anchor_identity_control", "anchor_identity", "production_gate_closed", "full_gate_zero"}
    if mode not in zero_delta_control_modes and nonidentity_tensor_delta <= 0.0:
        status = "BATCH3A_NEEDS_REPAIR_NO_NONIDENTITY_TENSOR_EFFECT"
    contract = {
        "schema_version": 5,
        "batch": "7" if mode in BATCH7_MODES else ("6" if mode in BATCH6_MODES else ("5" if mode in BATCH5_MODES else "3A")),
        "status": status,
        "mode": mode,
        "production_intervention_mode": BATCH5_PRODUCTION_INTERVENTIONS.get(mode, "full"),
        "fold": args.fold,
        "case_count": len(rows),
        "model_forward_count": int(sum(int(row["model_forward_count"]) for row in rows)),
        "checkpoint_actual_load_count": 1,
        "prototype_memory_actual_load_count": 1,
        "checkpoint_receipt": ckpt_receipt,
        "checkpoint_global_step": int(payload.get("global_step", 0)),
        "prediction_dir": rel(pred_dir, REPO_ROOT),
        "geometry_roundtrip_csv": rel(geometry_csv, REPO_ROOT),
        "tensor_checks_csv": rel(tensor_csv, REPO_ROOT),
        "raw_oof_anchor_manifest_status": manifest["status"],
        "raw_oof_anchor_manifest_hash": manifest_hash(manifest),
        "training_summary_anchor_manifest_hash": compact_anchor_manifest_hash,
        "checkpoint_oof_anchor_manifest_hash": payload.get("oof_anchor_manifest_hash"),
        "anchor_identity_changed_voxels_total": changed_total,
        "anchor_identity_softmax_max_abs_delta": identity_softmax_max_abs_delta,
        "identity_export_source": "model_logits_argmax",
        "raw_label_mismatch_total": int(sum(int(row["raw_label_mismatch"]) for row in rows)),
        "nonidentity_downstream_tensor_max_abs_delta": nonidentity_tensor_delta,
        "memory_query_policy": "validation_inference_all_train_shards",
        "training_query_policy": "training_crossfit_exclude_query_shard",
        "raw_anchor_and_safety_context_separated": True,
        "prototype_memory_source": (
            ckpt_receipt.get("semantic_memory_asset", {}).get("path")
            if ckpt_receipt.get("semantic_memory_asset")
            else (prototype_memory_provenance["source"] if prototype_memory_provenance else payload["prototype_memory_provenance"].get("source"))
        ),
        "semantic_memory_asset": ckpt_receipt.get("semantic_memory_asset", {}),
        "formal_training_count": 0,
        "slurm_job_count": 0,
        "validation_upload_count": 0,
        "hosted_metric_claim_count": 0,
        "performance_claim": "NONE",
        "notes": "All modes instantiate and call SRRProposeRefineMyoPS. Batch5 intervention modes are inference-only and preserve checkpoint parameters.",
    }
    write_json(out_root / f"batch3a_{mode}_inference_contract.json", contract)
    write_json(out_root / "batch3a_inference_contract.json", contract)
    print(json.dumps(contract, indent=2, sort_keys=True))
    return contract


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch2.yaml")
    parser.add_argument(
        "--mode",
        choices=(
            "anchor_identity_control",
            "srr_no_anchor_control",
            "anchor_bounded_srr_correction",
            "anchor_bounded_full",
            "anchor_bounded_proposal_only",
            "anchor_bounded_refiner_only",
            "production_gate_closed",
            "production_gate_open_bounded_control",
            "full_learned_gate",
            "full_gate_one",
            "full_gate_zero",
            "proposal_only_gate_one",
            "refiner_only_gate_one",
            "learned_source_gate_one",
            "anchor_identity",
            "production_gate_one",
            "full_learned",
            "proposal_only",
            "refiner_only",
            "learned_source",
            "production_gate_learned",
            "prototype_maps_off",
            "semantic_negative_memory_off",
            "zero_anchor_pathology_context",
            "zero_anchor_confirmation_context",
            "no_anchor_diagnostic",
        ),
        default="anchor_identity_control",
    )
    parser.add_argument("--fold", type=int, default=0)
    parser.add_argument("--cases", default="")
    parser.add_argument("--max-cases", type=int, default=0)
    parser.add_argument("--checkpoint", default="")
    parser.add_argument("--training-summary", default="")
    parser.add_argument("--allow-untrained-diagnostic", action="store_true")
    parser.add_argument("--output-root", default="")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    result = run(args)
    return 0 if not str(result["status"]).startswith("BATCH3A_NEEDS_REPAIR") else 1


if __name__ == "__main__":
    raise SystemExit(main())
