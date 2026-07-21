#!/usr/bin/env python3
"""Batch6 fixed Case2002+Case1002 overfit gate for SRR MyoPS."""

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

from scripts.evaluation.audit_srr_batch5_loss_authority import state_hash  # noqa: E402
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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    names: list[str] = []
    for row in rows:
        for key in row:
            if key not in names:
                names.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rel_drop(first: float, last: float) -> float:
    return (first - last) / max(abs(first), 1e-8)


def selected_checkpoint(cfg: dict[str, Any]) -> Path:
    adequacy = json.loads((REPO_ROOT / cfg["source_batch4"]["result_root"] / "training_adequacy.json").read_text(encoding="utf-8"))
    path = REPO_ROOT / str(adequacy["selected_checkpoint_path"])
    expected = str(cfg["source_batch4"]["selected_checkpoint_sha256"])
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"selected checkpoint sha mismatch: {actual} != {expected}")
    return path


def batch6_args(cfg: dict[str, Any], result_root: Path) -> argparse.Namespace:
    formal = cfg["formal_training"]
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
        lr=float(formal["learning_rate"]),
        weight_decay=float(formal["weight_decay"]),
        grad_clip=float(formal["grad_clip"]),
        fold=int(cfg["training_data"]["fold"]),
        out_root=str(result_root / "runtime"),
        run_label="batch6_fixed_overfit",
    )


def set_trainable(model: torch.nn.Module) -> list[str]:
    trainable_prefixes = ("production_correction_gate.", "scar_refine.", "edema_refine.")
    trainable: list[str] = []
    for name, param in model.named_parameters():
        keep = any(name.startswith(prefix) for prefix in trainable_prefixes)
        param.requires_grad_(keep)
        if keep:
            trainable.append(name)
    return trainable


def make_batch(cfg: dict[str, Any], device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, torch.Tensor], dict[str, torch.Tensor], list[str]]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = REPO_ROOT / cfg["paths"]["anchor_root"]
    patch_shape = tuple(int(v) for v in cfg["formal_training"]["patch_shape"])
    rng = np.random.default_rng(20260721)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    avs: list[np.ndarray] = []
    anchors: list[np.ndarray] = []
    components: list[np.ndarray] = []
    case_ids = ["Case2002", "Case1002"]
    for case_id in case_ids:
        case = read_anchored_case(case_id, metadata, anchor_root)
        focus = (4, 5) if case_id == "Case2002" else (5,)
        best: tuple[float, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]] | None = None
        for _idx in range(24):
            candidate = sample_patch_with_anchor(
                case,
                patch_shape,
                rng,
                oversample_foreground=1.0,
                modality_dropout=False,
                focus_classes=focus,
            )
            _x_np, y_np, av_np, anchor_np, _component_np = candidate
            anchor_label = np.asarray(anchor_np).argmax(axis=0)
            scar_gt = y_np == 5
            edema_gt = (y_np == 4) & bool(av_np[1] > 0.5)
            scar_error = np.count_nonzero((anchor_label == 5) != scar_gt)
            edema_error = np.count_nonzero((anchor_label == 4) != edema_gt)
            scar_voxels = np.count_nonzero(scar_gt)
            edema_voxels = np.count_nonzero(edema_gt)
            if case_id == "Case1002":
                score = 10.0 * float(scar_error) + float(scar_voxels)
            else:
                score = 6.0 * float(scar_error + edema_error) + float(scar_voxels + edema_voxels)
            if best is None or score > best[0]:
                best = (score, candidate)
        if best is None:
            raise RuntimeError(f"failed to select fixed overfit patch for {case_id}")
        x_np, y_np, av_np, anchor_np, component_np = best[1]
        xs.append(x_np)
        ys.append(y_np)
        avs.append(av_np)
        anchors.append(anchor_np)
        components.append(component_np)
    x = torch.from_numpy(np.stack(xs, axis=0)).float().to(device)
    y = torch.from_numpy(np.stack(ys, axis=0)).long().to(device)
    av = torch.from_numpy(np.stack(avs, axis=0)).float().to(device)
    anchor_t = torch.from_numpy(np.stack(anchors, axis=0)).float().to(device)
    component_t = torch.from_numpy(np.stack(components, axis=0)).float().to(device)
    return x, y, av, anchor_dict_from_tensor(anchor_t), component_dict_from_tensor(component_t), case_ids


def run(config: Path, result_root: Path, device_arg: str) -> dict[str, Any]:
    cfg = yaml.safe_load(config.read_text(encoding="utf-8"))
    result_root.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if device_arg == "cuda" and torch.cuda.is_available() else "cpu")
    args = batch6_args(cfg, result_root)
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    trainable_names = set_trainable(model)
    overfit_lr = float(cfg["fixed_batch_overfit"].get("learning_rate", args.lr))
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=overfit_lr, weight_decay=args.weight_decay)
    source_ckpt = selected_checkpoint(cfg)
    payload = load_srr_checkpoint(
        path=source_ckpt,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        map_location=device,
        restore_rng=False,
    )
    x, y, av, anchor_features, component_features, case_ids = make_batch(cfg, device)
    safety_anchor, safety_component = safety_context_dicts_from_raw(anchor_features, component_features, av)
    rows: list[dict[str, Any]] = []
    first: dict[str, float] = {}
    last: dict[str, float] = {}
    initial_logits: torch.Tensor | None = None
    gate_grad_l2 = 0.0
    all_finite = True
    for step in range(0, int(cfg["fixed_batch_overfit"]["optimizer_steps"]) + 1):
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
        _loss, metrics = propref_loss(outputs, y, av, "soft_roi_refinement", args, detach_m6_metrics=False)
        combined_final = metrics["loss_final_scar_pathology"] + metrics["loss_final_edema_t2_present_pathology"]
        train_loss = (
            combined_final
            + float(cfg["canonical_loss_weights"]["loss_production_gate_repair_preserve"]) * metrics["loss_production_gate_repair_preserve"]
        )
        if step == 0:
            initial_logits = outputs["logits"].detach().clone()
            first = {
                "combined_final_pathology_loss": float(combined_final.detach().cpu()),
                "scar_final_pathology_loss": float(metrics["loss_final_scar_pathology"].detach().cpu()),
                "edema_final_pathology_loss": float(metrics["loss_final_edema_t2_present_pathology"].detach().cpu()),
                "gate_repair_preserve_loss": float(metrics["loss_production_gate_repair_preserve"].detach().cpu()),
            }
        else:
            train_loss.backward()
            gate_norm = 0.0
            for name, param in model.named_parameters():
                if name.startswith("production_correction_gate.") and param.grad is not None:
                    gate_norm += float(param.grad.detach().norm().cpu()) ** 2
            gate_grad_l2 = max(gate_grad_l2, math.sqrt(gate_norm))
            torch.nn.utils.clip_grad_norm_((p for p in model.parameters() if p.requires_grad), float(args.grad_clip))
            optimizer.step()
        values = {
            "combined_final_pathology_loss": float(combined_final.detach().cpu()),
            "scar_final_pathology_loss": float(metrics["loss_final_scar_pathology"].detach().cpu()),
            "edema_final_pathology_loss": float(metrics["loss_final_edema_t2_present_pathology"].detach().cpu()),
            "gate_repair_preserve_loss": float(metrics["loss_production_gate_repair_preserve"].detach().cpu()),
            "repair_mask_voxels": float(metrics["repair_mask_voxels"].detach().cpu()),
            "preserve_mask_voxels": float(metrics["preserve_mask_voxels"].detach().cpu()),
        }
        all_finite = all_finite and all(math.isfinite(v) for v in values.values())
        if step in {0, 1, 10, 20, 40, 60}:
            rows.append({"step": step, **values})
        last = values
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
    final_logits_delta = float((final_outputs["logits"].detach() - initial_logits).abs().max().cpu()) if initial_logits is not None else 0.0
    no_t2_edema_exact_zero = bool(float(final_outputs["bounded_edema_correction"][1].detach().abs().max().cpu()) == 0.0)
    ckpt_path = result_root / "runtime/fixed_batch_overfit/checkpoint_step_60.pt"
    save_training_checkpoint(
        path=ckpt_path,
        model=model,
        optimizer=optimizer,
        args=args,
        global_step=60,
        epoch=0,
        anchor_manifest_hash="batch6_fixed_overfit_reuses_batch4_anchor_manifest",
        prototype_memory_provenance=payload.get("prototype_memory_provenance", {}),
        best_metric_state={"checkpoint_role": "batch6_fixed_overfit_step_60"},
    )
    reloaded = SRRProposeRefineMyoPS(**model_kwargs_from_args(args)).to(device)
    set_trainable(reloaded)
    reloaded_opt = torch.optim.AdamW((p for p in reloaded.parameters() if p.requires_grad), lr=overfit_lr, weight_decay=args.weight_decay)
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
        "scar_final_pathology_loss_relative_decrease": rel_drop(first["scar_final_pathology_loss"], last["scar_final_pathology_loss"]),
        "edema_final_pathology_loss_relative_decrease": rel_drop(first["edema_final_pathology_loss"], last["edema_final_pathology_loss"]),
        "gate_loss_relative_decrease": rel_drop(first["gate_repair_preserve_loss"], last["gate_repair_preserve_loss"]),
        "production_gate_repair_gradient_l2_max": gate_grad_l2,
        "final_logits_max_abs_change_from_step0": final_logits_delta,
        "no_t2_edema_exact_zero": no_t2_edema_exact_zero,
        "all_losses_finite": all_finite,
        "save_reload_final_logits_max_abs_delta": reload_delta,
    }
    passed = (
        checks["combined_final_pathology_loss_relative_decrease"] >= float(gates["combined_final_pathology_loss_relative_decrease_minimum"])
        and checks["scar_final_pathology_loss_relative_decrease"] >= float(gates["scar_final_pathology_loss_relative_decrease_minimum"])
        and checks["edema_final_pathology_loss_relative_decrease"] >= float(gates["edema_final_pathology_loss_relative_decrease_minimum"])
        and checks["gate_loss_relative_decrease"] >= float(gates["gate_loss_relative_decrease_minimum"])
        and checks["production_gate_repair_gradient_l2_max"] > 0.0
        and checks["final_logits_max_abs_change_from_step0"] > 0.0
        and checks["no_t2_edema_exact_zero"]
        and checks["all_losses_finite"]
        and checks["save_reload_final_logits_max_abs_delta"] <= float(gates["save_reload_final_logits_max_abs_delta"])
    )
    write_csv(result_root / "fixed_batch_overfit_trace.csv", rows)
    summary = {
        "status": "PASS" if passed else "FAIL",
        "optimizer_steps": 60,
        "learning_rate": overfit_lr,
        "formal_training_credit": 0,
        "case_ids": case_ids,
        "source_checkpoint_path": str(source_ckpt.relative_to(REPO_ROOT)),
        "source_checkpoint_sha256": sha256_file(source_ckpt),
        "production_gate_migration": payload.get("production_gate_migration", {}),
        "trainable_parameter_names": sorted(trainable_names),
        "frozen_scope": cfg["fixed_batch_overfit"]["frozen_groups"],
        "initial_losses": first,
        "final_losses": {key: last[key] for key in first},
        "checks": checks,
        "checkpoint_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "parameter_hash_after": state_hash(model),
    }
    (result_root / "fixed_batch_overfit.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch6.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch6_final_objective_alignment")
    parser.add_argument("--device", choices=["cuda", "cpu"], default="cuda")
    args = parser.parse_args()
    summary = run(REPO_ROOT / args.config, REPO_ROOT / args.result_root, args.device)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
