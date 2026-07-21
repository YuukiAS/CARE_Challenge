#!/usr/bin/env python3
"""Batch7 fixed Case2002+Case1002 overfit gate."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    anchor_dict_from_tensor,
    component_dict_from_tensor,
    model_kwargs_from_args,
    read_anchored_case,
    sample_patch_with_anchor,
    safety_context_dicts_from_raw,
    save_training_checkpoint,
    propref_loss,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint  # noqa: E402


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


def rel_drop(first: float, last: float) -> float:
    return (first - last) / max(abs(first), 1e-8)


def batch7_args(cfg: dict[str, Any], result_root: Path) -> argparse.Namespace:
    formal = cfg["formal_training"]
    fixed = cfg.get("fixed_batch_overfit", {})
    return argparse.Namespace(
        variant=cfg["model"]["variant"],
        encoder_profile=cfg["model"]["encoder_profile"],
        base_channels=int(cfg["model"]["base_channels"]),
        final_output_mode=cfg["model"]["final_output_mode"],
        disable_local_refinement=False,
        disable_anatomy_roi_prior=False,
        disable_nnunet_anchor=False,
        loss_weight_json="",
        loss_weight=[],
        variant_config_record={"variant_config": {"canonical_loss_weights": cfg["canonical_loss_weights"]}},
        canonical_loss_weights=cfg["canonical_loss_weights"],
        lr=float(fixed.get("learning_rate", formal["learning_rate"])),
        weight_decay=float(formal["weight_decay"]),
        grad_clip=float(formal["grad_clip"]),
        fold=int(cfg["training_data"]["fold"]),
        out_root=str(result_root / "runtime"),
        run_label="batch7_fixed_overfit",
    )


def set_trainable(model: torch.nn.Module) -> list[str]:
    prefixes = (
        "m10_spatial_dictionary.",
        "scar_dictionary.",
        "edema_dictionary.",
        "evidence_heads.scar.",
        "evidence_heads.edema.",
        "scar_refine.",
        "edema_refine.",
        "scar_source_arbiter.",
        "edema_source_arbiter.",
        "production_correction_gate.",
    )
    trainable: list[str] = []
    for name, param in model.named_parameters():
        keep = any(name.startswith(prefix) for prefix in prefixes)
        param.requires_grad_(keep)
        if keep:
            trainable.append(name)
    return trainable


def reset_batch7_production_gate(model: torch.nn.Module) -> dict[str, Any]:
    gate = getattr(model, "production_correction_gate", None)
    if not isinstance(gate, torch.nn.Conv3d):
        return {"applied": False, "reason": "production_correction_gate_missing"}
    with torch.no_grad():
        gate.weight.zero_()
        if gate.bias is not None:
            gate.bias.fill_(2.0)
    return {
        "applied": True,
        "reason": "batch7_source_candidate_input_migrated_from_batch6_gate_weights",
        "weight_init": "zeros",
        "bias_init": 2.0,
        "gate_semantics": "sigmoid_gate_preserved_with_bounded_correction",
    }


def make_batch(cfg: dict[str, Any], device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, torch.Tensor], dict[str, torch.Tensor], list[str]]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = repo_path(cfg["paths"]["anchor_root"])
    patch_shape = tuple(int(v) for v in cfg["formal_training"]["patch_shape"])
    rng = np.random.default_rng(20260721)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    avs: list[np.ndarray] = []
    anchors: list[np.ndarray] = []
    components: list[np.ndarray] = []
    case_ids = list(cfg["fixed_batch_overfit"]["cases"])
    for case_id in case_ids:
        case = read_anchored_case(case_id, metadata, anchor_root)
        focus = (4, 5) if case_id == "Case2002" else (5,)
        best = None
        for _idx in range(128):
            candidate = sample_patch_with_anchor(case, patch_shape, rng, oversample_foreground=1.0, modality_dropout=False, focus_classes=focus)
            _x_np, y_np, av_np, anchor_np, _component_np = candidate
            anchor_label = np.asarray(anchor_np).argmax(axis=0)
            focus_mask = np.isin(y_np, focus)
            anchor_focus = np.isin(anchor_label, focus)
            focus_voxels = int(np.count_nonzero(focus_mask))
            anchor_missed_focus = int(np.count_nonzero(focus_mask & ~anchor_focus))
            anchor_focus_fp = int(np.count_nonzero(anchor_focus & ~focus_mask))
            score = 1000.0 * focus_voxels + 50.0 * anchor_missed_focus - 2.0 * anchor_focus_fp
            if best is None or score > best[0]:
                best = (score, candidate)
        if best is None:
            raise RuntimeError(f"failed to select fixed patch for {case_id}")
        x_np, y_np, av_np, anchor_np, component_np = best[1]
        xs.append(x_np)
        ys.append(y_np)
        avs.append(av_np)
        anchors.append(anchor_np)
        components.append(component_np)
    x = torch.from_numpy(np.stack(xs)).float().to(device)
    y = torch.from_numpy(np.stack(ys)).long().to(device)
    av = torch.from_numpy(np.stack(avs)).float().to(device)
    anchor = torch.from_numpy(np.stack(anchors)).float().to(device)
    component = torch.from_numpy(np.stack(components)).float().to(device)
    return x, y, av, anchor_dict_from_tensor(anchor), component_dict_from_tensor(component), case_ids


def load_model(cfg: dict[str, Any], args: argparse.Namespace, device: torch.device, optimizer: torch.optim.Optimizer | None = None) -> tuple[SRRProposeRefineMyoPS, dict[str, Any]]:
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    dummy_opt = optimizer if optimizer is not None else torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    ckpt = repo_path(cfg["source_batch6"]["checkpoint_path"])
    payload = load_srr_checkpoint(
        path=ckpt,
        model=model,
        optimizer=dummy_opt,
        scheduler=None,
        amp_scaler=None,
        map_location=device,
        restore_rng=False,
        restore_optimizer=False,
        strict_model_state=False,
    )
    gate_migration = reset_batch7_production_gate(model)
    asset = torch.load(repo_path(cfg["paths"]["rebuilt_asset_path"]), map_location=device, weights_only=False)
    model.load_state_dict(asset["model_memory_state"], strict=False)
    payload["production_gate_migration"] = gate_migration
    return model, payload


def run(config: Path, result_root: Path, device_arg: str) -> dict[str, Any]:
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    result_root.mkdir(parents=True, exist_ok=True)
    if sha256_file(repo_path(cfg["source_batch6"]["checkpoint_path"])) != str(cfg["source_batch6"]["selected_checkpoint_sha256"]):
        raise SystemExit("Batch7 fixed overfit blocked: source checkpoint SHA mismatch")
    if not repo_path(cfg["paths"]["rebuilt_asset_path"]).is_file():
        raise SystemExit("Batch7 fixed overfit blocked: rebuilt prototype memory asset missing")
    device = torch.device("cuda" if device_arg == "cuda" and torch.cuda.is_available() else "cpu")
    args = batch7_args(cfg, result_root)
    model, payload = load_model(cfg, args, device)
    trainable = set_trainable(model)
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.lr, weight_decay=args.weight_decay)
    x, y, av, anchor_features, component_features, case_ids = make_batch(cfg, device)
    safety_anchor, safety_component = safety_context_dicts_from_raw(anchor_features, component_features, av)
    rows: list[dict[str, Any]] = []
    first: dict[str, float] = {}
    last: dict[str, float] = {}
    grad_max = {key: 0.0 for key in cfg["fixed_batch_overfit"]["pass_gates"]["nonzero_gradient_groups"]}
    initial_logits: torch.Tensor | None = None
    all_finite = True
    steps = int(cfg["fixed_batch_overfit"]["optimizer_steps"])

    def values(metrics: dict[str, torch.Tensor]) -> dict[str, float]:
        combined = metrics["loss_final_scar_pathology"] + metrics["loss_final_edema_t2_present_pathology"]
        return {
            "combined_final_pathology_loss": float(combined.detach().cpu()),
            "discovery_proposal_loss": float((metrics["loss_scar_discovery_proposal"] + metrics["loss_edema_discovery_proposal_t2_present"]).detach().cpu()),
            "scar_refiner_repair_loss": float(metrics["loss_scar_refiner_roi"].detach().cpu()),
            "source_arbiter_loss": float(metrics["loss_source_arbiter"].detach().cpu()),
            "all_loss": float(metrics["m6_expanded_total_loss"].detach().cpu()),
        }

    for step in range(steps + 1):
        optimizer.zero_grad(set_to_none=True)
        outputs = model(
            x,
            av,
            anchor_features=anchor_features,
            component_features=component_features,
            safety_anchor_features=safety_anchor,
            safety_component_features=safety_component,
            memory_query_policy="validation_inference_all_train_shards",
            case_ids=case_ids,
        )
        loss, metrics = propref_loss(outputs, y, av, "soft_roi_refinement", args, detach_m6_metrics=False)
        final_pathology_loss = metrics["loss_final_scar_pathology"] + metrics["loss_final_edema_t2_present_pathology"]
        final_multiplier = float(cfg["fixed_batch_overfit"].get("final_pathology_loss_multiplier", 1.0))
        if final_multiplier > 1.0:
            loss = loss + (final_multiplier - 1.0) * final_pathology_loss
        if step == 0:
            initial_logits = outputs["logits"].detach().clone()
            first = values(metrics)
        else:
            loss.backward()
            for group in grad_max:
                prefixes = {
                    "m10_spatial_dictionary": ("m10_spatial_dictionary.",),
                    "scar_dictionary": ("scar_dictionary.",),
                    "edema_dictionary": ("edema_dictionary.",),
                    "scar_refine": ("scar_refine.",),
                    "edema_refine": ("edema_refine.",),
                    "scar_source_arbiter": ("scar_source_arbiter.",),
                    "edema_source_arbiter": ("edema_source_arbiter.",),
                    "production_correction_gate": ("production_correction_gate.",),
                }[group]
                total = 0.0
                for name, param in model.named_parameters():
                    if any(name.startswith(prefix) for prefix in prefixes) and param.grad is not None:
                        total += float(param.grad.detach().norm().cpu()) ** 2
                grad_max[group] = max(grad_max[group], math.sqrt(total))
            torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), float(args.grad_clip))
            optimizer.step()
        last = values(metrics)
        all_finite = all_finite and all(math.isfinite(v) for v in last.values())
        if step in {0, 1, 10, 25, 50, 75, 100}:
            rows.append({"step": step, **last})
    final_outputs = model(
        x,
        av,
        anchor_features=anchor_features,
        component_features=component_features,
        safety_anchor_features=safety_anchor,
        safety_component_features=safety_component,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=case_ids,
    )
    _loss, final_metrics = propref_loss(final_outputs, y, av, "soft_roi_refinement", args, detach_m6_metrics=False)
    last = values(final_metrics)
    final_logits_delta = float((final_outputs["logits"].detach() - initial_logits).abs().max().cpu()) if initial_logits is not None else 0.0
    no_t2_exact = bool(
        float(final_outputs["bounded_edema_correction"][1].detach().abs().max().cpu()) == 0.0
        and float(final_outputs["edema_soft_roi"][1].detach().abs().max().cpu()) == 0.0
        and float(final_outputs["edema_refinement_residual"][1].detach().abs().max().cpu()) == 0.0
    )
    ckpt_path = result_root / "runtime/fixed_batch_overfit/checkpoint_step_100.pt"
    save_training_checkpoint(
        path=ckpt_path,
        model=model,
        optimizer=optimizer,
        args=args,
        global_step=steps,
        epoch=0,
        anchor_manifest_hash="batch7_fixed_overfit_reuses_fold0_oof_anchor_manifest",
        prototype_memory_provenance={"asset_path": cfg["paths"]["rebuilt_asset_path"], "asset_sha256": sha256_file(repo_path(cfg["paths"]["rebuilt_asset_path"]))},
        best_metric_state={"checkpoint_role": "batch7_fixed_overfit_step_100"},
    )
    reloaded = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    set_trainable(reloaded)
    reloaded_opt = torch.optim.AdamW((p for p in reloaded.parameters() if p.requires_grad), lr=args.lr, weight_decay=args.weight_decay)
    load_srr_checkpoint(path=ckpt_path, model=reloaded, optimizer=reloaded_opt, scheduler=None, amp_scaler=None, map_location=device, restore_rng=False)
    reload_outputs = reloaded(
        x,
        av,
        anchor_features=anchor_features,
        component_features=component_features,
        safety_anchor_features=safety_anchor,
        safety_component_features=safety_component,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=case_ids,
    )
    reload_delta = float((reload_outputs["logits"].detach() - final_outputs["logits"].detach()).abs().max().cpu())
    gates = cfg["fixed_batch_overfit"]["pass_gates"]
    checks = {
        "combined_final_pathology_loss_relative_decrease": rel_drop(first["combined_final_pathology_loss"], last["combined_final_pathology_loss"]),
        "discovery_proposal_loss_relative_decrease": rel_drop(first["discovery_proposal_loss"], last["discovery_proposal_loss"]),
        "scar_refiner_repair_loss_relative_decrease": rel_drop(first["scar_refiner_repair_loss"], last["scar_refiner_repair_loss"]),
        "source_arbiter_loss_relative_decrease": rel_drop(first["source_arbiter_loss"], last["source_arbiter_loss"]),
        "gradient_l2_max": grad_max,
        "zero_anchor_context_discovery_nonzero": bool(float(final_outputs["scar_discovery_logits"].detach().abs().max().cpu()) > 0.0),
        "no_t2_edema_exact_zero": no_t2_exact,
        "all_losses_finite": all_finite,
        "save_reload_final_logits_max_abs_delta": reload_delta,
        "final_logits_max_abs_change_from_step0": final_logits_delta,
    }
    passed = (
        checks["combined_final_pathology_loss_relative_decrease"] >= float(gates["combined_final_pathology_loss_relative_decrease_minimum"])
        and checks["discovery_proposal_loss_relative_decrease"] >= float(gates["discovery_proposal_loss_relative_decrease_minimum"])
        and checks["scar_refiner_repair_loss_relative_decrease"] >= float(gates["scar_refiner_repair_loss_relative_decrease_minimum"])
        and checks["source_arbiter_loss_relative_decrease"] >= float(gates["source_arbiter_loss_relative_decrease_minimum"])
        and all(float(v) > 0.0 for v in grad_max.values())
        and bool(checks["zero_anchor_context_discovery_nonzero"])
        and no_t2_exact
        and all_finite
        and reload_delta <= float(gates["save_reload_final_logits_max_abs_delta"])
    )
    write_csv(result_root / "fixed_batch_overfit_trace.csv", rows)
    grad_rows = [{"group": group, "grad_l2_max": value, "status": "nonzero" if value > 0 else "zero"} for group, value in grad_max.items()]
    write_csv(result_root / "gradient_authority.csv", grad_rows)
    summary = {
        "status": "PASS" if passed else "FAIL",
        "optimizer_steps": steps,
        "formal_training_credit": 0,
        "case_ids": case_ids,
        "source_checkpoint_path": cfg["source_batch6"]["checkpoint_path"],
        "source_checkpoint_sha256": sha256_file(repo_path(cfg["source_batch6"]["checkpoint_path"])),
        "rebuilt_asset_path": cfg["paths"]["rebuilt_asset_path"],
        "rebuilt_asset_sha256": sha256_file(repo_path(cfg["paths"]["rebuilt_asset_path"])),
        "source_model_load": payload.get("model_state_load", {}),
        "production_gate_migration": payload.get("production_gate_migration", {"applied": False}),
        "fixed_training_loss_overrides": {
            "final_pathology_loss_multiplier": float(cfg["fixed_batch_overfit"].get("final_pathology_loss_multiplier", 1.0)),
            "formal_training_credit": 0,
        },
        "trainable_parameter_names": trainable,
        "initial_losses": first,
        "final_losses": last,
        "checks": checks,
        "checkpoint_path": str(ckpt_path.relative_to(REPO_ROOT)),
    }
    (result_root / "fixed_batch_overfit.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch7_upstream_candidate_quality")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    summary = run(repo_path(args.config), repo_path(args.result_root), args.device)
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
