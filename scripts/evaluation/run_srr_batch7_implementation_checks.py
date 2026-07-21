#!/usr/bin/env python3
"""Run Batch7 real-case implementation interventions and roundtrip checks."""

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

from scripts.training.run_srr_batch7_fixed_overfit import batch7_args, load_model, make_batch, set_trainable  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import model_kwargs_from_args, propref_loss, safety_context_dicts_from_raw, save_training_checkpoint  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
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


def tensor_delta(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a.detach() - b.detach()).abs().mean().cpu())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch7_upstream_candidate_quality")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args_ns = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args_ns.config).read_text(encoding="utf-8"))
    result_root = repo_path(args_ns.result_root)
    result_root.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if args_ns.device == "cuda" and torch.cuda.is_available() else "cpu")
    train_args = batch7_args(cfg, result_root)
    model, _payload = load_model(cfg, train_args, device)
    set_trainable(model)
    model.eval()
    x, y, av, anchor_features, component_features, case_ids = make_batch(cfg, device)
    safety_anchor, safety_component = safety_context_dicts_from_raw(anchor_features, component_features, av)

    modes = [
        "learned_source",
        "prototype_maps_off",
        "semantic_negative_memory_off",
        "zero_anchor_pathology_context",
        "discovery_off",
        "proposal_only",
        "refiner_only",
    ]
    outputs: dict[str, dict[str, torch.Tensor]] = {}
    with torch.no_grad():
        for mode in modes:
            outputs[mode] = model(
                x,
                av,
                anchor_features=anchor_features,
                component_features=component_features,
                safety_anchor_features=safety_anchor,
                safety_component_features=safety_component,
                memory_query_policy="validation_inference_all_train_shards",
                case_ids=case_ids,
                production_intervention_mode=mode,
            )
    base = outputs["learned_source"]
    rows = [
        {
            "intervention": "prototype_maps_on_vs_off",
            "spatial_gate_delta": tensor_delta(base["gates"]["m10_scar_pass1"], outputs["prototype_maps_off"]["gates"]["m10_scar_pass1"]),
            "retrieved_feature_delta": tensor_delta(base["m10_prototype_maps"]["scar_pos"], outputs["prototype_maps_off"].get("m10_prototype_maps", {"scar_pos": torch.zeros_like(base["m10_prototype_maps"]["scar_pos"])})["scar_pos"]),
            "proposal_logit_delta": tensor_delta(base["scar_proposal_logits"], outputs["prototype_maps_off"]["scar_proposal_logits"]),
            "final_logit_delta": tensor_delta(base["logits"], outputs["prototype_maps_off"]["logits"]),
        },
        {
            "intervention": "semantic_negative_memory_on_vs_off",
            "proposal_logit_delta": tensor_delta(base["scar_proposal_logits"], outputs["semantic_negative_memory_off"]["scar_proposal_logits"]),
            "final_logit_delta": tensor_delta(base["logits"], outputs["semantic_negative_memory_off"]["logits"]),
        },
        {
            "intervention": "zero_anchor_pathology_context",
            "discovery_abs_max": float(outputs["zero_anchor_pathology_context"]["scar_discovery_logits"].detach().abs().max().cpu()),
            "proposal_logit_delta": tensor_delta(base["scar_proposal_logits"], outputs["zero_anchor_pathology_context"]["scar_proposal_logits"]),
        },
        {
            "intervention": "source_weight_normalization",
            "scar_sum_max_abs_error": float((base["scar_proposal_source_weight"] + base["scar_refiner_source_weight"] - 1.0).detach().abs().max().cpu()),
            "edema_sum_max_abs_error": float((base["edema_proposal_source_weight"] + base["edema_refiner_source_weight"] - 1.0).detach().abs().max().cpu()),
        },
        {
            "intervention": "no_t2_edema_chain",
            "case_id": case_ids[1],
            "edema_roi_abs_max": float(base["edema_soft_roi"][1].detach().abs().max().cpu()),
            "edema_residual_abs_max": float(base["edema_refinement_residual"][1].detach().abs().max().cpu()),
            "edema_correction_abs_max": float(base["bounded_edema_correction"][1].detach().abs().max().cpu()),
        },
    ]
    write_csv(result_root / "asset_intervention_metrics.csv", rows)

    model.train()
    model.zero_grad(set_to_none=True)
    grad_out = model(
        x,
        av,
        anchor_features=anchor_features,
        component_features=component_features,
        safety_anchor_features=safety_anchor,
        safety_component_features=safety_component,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=case_ids,
        production_intervention_mode="learned_source",
    )
    loss, _metrics = propref_loss(grad_out, y, av, "soft_roi_refinement", train_args, detach_m6_metrics=False)
    loss.backward()
    grad_rows = []
    for group, prefixes in {
        "m10_spatial_dictionary": ("m10_spatial_dictionary.",),
        "proposal": ("scar_dictionary.", "edema_dictionary."),
        "refiner": ("scar_refine.", "edema_refine."),
        "source_arbiter": ("scar_source_arbiter.", "edema_source_arbiter."),
        "production_gate": ("production_correction_gate.",),
    }.items():
        total = 0.0
        for name, param in model.named_parameters():
            if any(name.startswith(prefix) for prefix in prefixes) and param.grad is not None:
                total += float(param.grad.detach().norm().cpu()) ** 2
        grad_rows.append({"group": group, "grad_l2": total ** 0.5, "status": "nonzero" if total > 0 else "zero"})
    write_csv(result_root / "gradient_authority.csv", grad_rows)

    ckpt_path = result_root / "runtime/implementation_roundtrip/checkpoint_roundtrip.pt"
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=train_args.lr, weight_decay=train_args.weight_decay)
    save_training_checkpoint(
        path=ckpt_path,
        model=model,
        optimizer=optimizer,
        args=train_args,
        global_step=0,
        epoch=0,
        anchor_manifest_hash="batch7_implementation_roundtrip",
        prototype_memory_provenance={"asset_path": cfg["paths"]["rebuilt_asset_path"]},
        best_metric_state={"checkpoint_role": "batch7_implementation_roundtrip"},
    )
    reloaded = SRRProposeRefineMyoPS(**model_kwargs_from_args(train_args)).to(device)
    set_trainable(reloaded)
    opt = torch.optim.AdamW((p for p in reloaded.parameters() if p.requires_grad), lr=train_args.lr, weight_decay=train_args.weight_decay)
    load_srr_checkpoint(path=ckpt_path, model=reloaded, optimizer=opt, scheduler=None, amp_scaler=None, map_location=device, restore_rng=False)
    reloaded.eval()
    with torch.no_grad():
        out2 = reloaded(
            x,
            av,
            anchor_features=anchor_features,
            component_features=component_features,
            safety_anchor_features=safety_anchor,
            safety_component_features=safety_component,
            memory_query_policy="validation_inference_all_train_shards",
            case_ids=case_ids,
            production_intervention_mode="learned_source",
        )
    roundtrip = {
        "status": "PASS",
        "checkpoint_path": str(ckpt_path.relative_to(REPO_ROOT)),
        "save_reload_final_logits_max_abs_delta": float((out2["logits"].detach() - base["logits"].detach()).abs().max().cpu()),
        "threshold": 1e-6,
    }
    if roundtrip["save_reload_final_logits_max_abs_delta"] > 1e-6:
        roundtrip["status"] = "FAIL"
    (result_root / "checkpoint_roundtrip.json").write_text(json.dumps(roundtrip, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(roundtrip, indent=2, sort_keys=True))
    return 0 if roundtrip["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
