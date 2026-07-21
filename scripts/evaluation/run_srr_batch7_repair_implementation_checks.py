#!/usr/bin/env python3
"""Run Batch7 repair semantic-memory and anchor-free discovery checks."""

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

from scripts.srr_production.infer_myops import load_memory_asset_fail_closed  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    full_case_anchor_tensors,
    model_kwargs_from_args,
    read_anchored_case,
    safety_context_dicts_from_raw,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint, save_srr_checkpoint  # noqa: E402


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


def model_args(cfg: dict[str, Any]) -> argparse.Namespace:
    return argparse.Namespace(
        variant=cfg["model"]["variant"],
        encoder_profile=cfg["model"]["encoder_profile"],
        base_channels=int(cfg["model"]["base_channels"]),
        final_output_mode=cfg["model"]["final_output_mode"],
        disable_local_refinement=False,
        disable_anatomy_roi_prior=False,
    )


def load_model(cfg: dict[str, Any], device: torch.device) -> SRRProposeRefineMyoPS:
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(model_args(cfg))).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4, weight_decay=1e-4)
    ckpt = repo_path(cfg["source_checkpoints"]["batch7"]["path"])
    if sha256_file(ckpt) != str(cfg["source_checkpoints"]["batch7"]["sha256"]):
        raise SystemExit("Batch7 checkpoint SHA mismatch")
    load_srr_checkpoint(
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
    asset = repo_path(cfg["paths"]["semantic_memory_asset"])
    if asset.is_file():
        load_memory_asset_fail_closed(model, asset, device)
    model.eval()
    return model


def tensor_delta(a: torch.Tensor, b: torch.Tensor) -> float:
    return float((a.detach() - b.detach()).abs().max().cpu())


def parameter_group(name: str) -> str:
    if name.startswith("scar_dictionary."):
        return "scar_dictionary"
    if name.startswith("edema_dictionary."):
        return "edema_dictionary"
    if name.startswith("evidence_heads.scar."):
        return "scar_evidence_head"
    if name.startswith("evidence_heads.edema."):
        return "edema_evidence_head"
    if name.startswith("m10_spatial_dictionary."):
        return "spatial_dictionary"
    return "other"


def select_gradient_case_ids(cfg: dict[str, Any], case_ids: list[str]) -> dict[str, str]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = repo_path(cfg["paths"]["anchor_root"])
    selected: dict[str, str] = {}
    for case_id in case_ids:
        case = read_anchored_case(case_id, metadata, anchor_root)
        target = torch.from_numpy(case.label_arr)
        if "scar" not in selected and bool((target == 5).any()):
            selected["scar"] = case_id
        if "edema" not in selected and bool(case.availability[1] > 0) and bool((target == 4).any()):
            selected["edema"] = case_id
        if {"scar", "edema"} <= set(selected):
            break
    missing = sorted({"scar", "edema"} - set(selected))
    if missing:
        raise ValueError(f"could not find required pathology-positive validation cases for gradient authority: {missing}")
    return selected


def gradient_authority_rows(
    model: SRRProposeRefineMyoPS,
    cfg: dict[str, Any],
    case_ids: list[str],
    device: torch.device,
) -> list[dict[str, Any]]:
    from scripts.training.run_srr_propref_myops_fold0 import apply_batch6_trainable_groups

    proposal_groups = ",".join(str(item) for item in cfg["stagewise_training"]["proposal_stage"]["trainable_groups"])
    contract = apply_batch6_trainable_groups(model, proposal_groups)
    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = repo_path(cfg["paths"]["anchor_root"])
    selected = select_gradient_case_ids(cfg, case_ids)
    rows: list[dict[str, Any]] = []
    for pathology, case_id in selected.items():
        case = read_anchored_case(case_id, metadata, anchor_root)
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        anchor_features, component_features = full_case_anchor_tensors(case, device)
        safety_anchor, safety_component = safety_context_dicts_from_raw(anchor_features, component_features, av)
        model.zero_grad(set_to_none=True)
        out = model(
            x,
            av,
            anchor_features=anchor_features,
            component_features=component_features,
            safety_anchor_features=safety_anchor,
            safety_component_features=safety_component,
            memory_query_policy="validation_inference_all_train_shards",
            case_ids=[case_id],
            production_intervention_mode="proposal_only_gate_one",
        )
        loss_key = "scar_proposal_logits" if pathology == "scar" else "edema_proposal_logits"
        out[loss_key].float().mean().backward()
        for name, param in model.named_parameters():
            if not param.requires_grad:
                continue
            grad_abs_sum = 0.0 if param.grad is None else float(param.grad.detach().abs().sum().cpu())
            group = parameter_group(name)
            rows.append(
                {
                    "pathology": pathology,
                    "case_id": case_id,
                    "case_t2_present": bool(case.availability[1] > 0),
                    "case_has_scar_label": bool((torch.from_numpy(case.label_arr) == 5).any()),
                    "case_has_edema_label": bool((torch.from_numpy(case.label_arr) == 4).any()),
                    "trainable_groups": ",".join(contract["trainable_groups"]),
                    "required_group": group
                    in {
                        f"{pathology}_dictionary",
                        f"{pathology}_evidence_head",
                        "spatial_dictionary",
                    },
                    "parameter_group": group,
                    "parameter_name": name,
                    "requires_grad": bool(param.requires_grad),
                    "grad_abs_sum": grad_abs_sum,
                    "nonzero_gradient": grad_abs_sum > 0.0,
                }
            )
    return rows


def gradient_authority_pass(rows: list[dict[str, Any]]) -> bool:
    required = {
        ("scar", "scar_dictionary"),
        ("scar", "scar_evidence_head"),
        ("scar", "spatial_dictionary"),
        ("edema", "edema_dictionary"),
        ("edema", "edema_evidence_head"),
        ("edema", "spatial_dictionary"),
    }
    totals = {key: 0.0 for key in required}
    for row in rows:
        key = (str(row["pathology"]), str(row["parameter_group"]))
        if key in totals:
            totals[key] += float(row["grad_abs_sum"])
    return all(value > 0.0 for value in totals.values())


def checkpoint_roundtrip_receipt(model: SRRProposeRefineMyoPS, cfg: dict[str, Any], device: torch.device) -> dict[str, Any]:
    result_root = repo_path(cfg["paths"]["result_root"])
    path = result_root / "runtime/checkpoint_roundtrip/batch7_repair_roundtrip.pt"
    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4, weight_decay=1e-4)
    before = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    save_srr_checkpoint(
        path=path,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        global_step=0,
        epoch=0,
        final_output_mode=str(cfg["model"]["final_output_mode"]),
        architecture_config=dict(cfg["model"]),
        oof_anchor_manifest_hash="batch7_repair_wave2_semantic_memory_checks",
        prototype_memory_provenance={"semantic_memory_asset": cfg["paths"]["semantic_memory_asset"]},
        split_hash=sha256_file(repo_path(cfg["paths"]["split_path"])),
        source_commit=str(cfg.get("source_main_commit", "")),
        best_metric_state={"status": "wave2_roundtrip_check"},
        loss_weight_contract={},
    )
    reloaded = SRRProposeRefineMyoPS(**model_kwargs_from_args(model_args(cfg))).to(device)
    reloaded_optimizer = torch.optim.AdamW(reloaded.parameters(), lr=1e-4, weight_decay=1e-4)
    load_srr_checkpoint(
        path=path,
        model=reloaded,
        optimizer=reloaded_optimizer,
        scheduler=None,
        amp_scaler=None,
        map_location=device,
        restore_rng=False,
        restore_optimizer=False,
        strict_model_state=True,
    )
    after = {key: value.detach().cpu() for key, value in reloaded.state_dict().items()}
    max_abs_delta = max(float((before[key] - after[key]).abs().max()) for key in before)
    return {
        "status": "PASS" if max_abs_delta <= 1e-6 else "FAIL",
        "checkpoint_path": str(path.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(path),
        "max_abs_delta": max_abs_delta,
        "threshold": 1e-6,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_repair.yaml")
    parser.add_argument("--result-root", default="results/20260721_srr_batch7_mechanism_closure_repair")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--max-cases", type=int, default=2)
    args = parser.parse_args()
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(args.result_root)
    result_root.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    model = load_model(cfg, device)
    split = json.loads(repo_path(cfg["paths"]["split_path"]).read_text(encoding="utf-8"))["folds"][int(cfg["training_data"]["fold"])]["val"]
    case_ids = list(split)[: max(1, int(args.max_cases))]
    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = repo_path(cfg["paths"]["anchor_root"])
    discovery_rows: list[dict[str, Any]] = []
    prototype_rows: list[dict[str, Any]] = []
    semantic_rows: list[dict[str, Any]] = []
    for case_id in case_ids:
        case = read_anchored_case(case_id, metadata, anchor_root)
        x = torch.from_numpy(case.image[None]).float().to(device)
        av = torch.from_numpy(case.availability[None]).float().to(device)
        anchor_features, component_features = full_case_anchor_tensors(case, device)
        safety_anchor, safety_component = safety_context_dicts_from_raw(anchor_features, component_features, av)
        with torch.no_grad():
            base = model(
                x,
                av,
                anchor_features=anchor_features,
                component_features=component_features,
                safety_anchor_features=safety_anchor,
                safety_component_features=safety_component,
                memory_query_policy="validation_inference_all_train_shards",
                case_ids=[case_id],
                production_intervention_mode="learned_source",
            )
            zero = model(
                x,
                av,
                anchor_features=anchor_features,
                component_features=component_features,
                safety_anchor_features=safety_anchor,
                safety_component_features=safety_component,
                memory_query_policy="validation_inference_all_train_shards",
                case_ids=[case_id],
                production_intervention_mode="zero_anchor_confirmation_context",
            )
            proto_off = model(
                x,
                av,
                anchor_features=anchor_features,
                component_features=component_features,
                safety_anchor_features=safety_anchor,
                safety_component_features=safety_component,
                memory_query_policy="validation_inference_all_train_shards",
                case_ids=[case_id],
                production_intervention_mode="prototype_maps_off",
            )
            sem_off = model(
                x,
                av,
                anchor_features=anchor_features,
                component_features=component_features,
                safety_anchor_features=safety_anchor,
                safety_component_features=safety_component,
                memory_query_policy="validation_inference_all_train_shards",
                case_ids=[case_id],
                production_intervention_mode="semantic_negative_memory_off",
            )
        discovery_rows.append(
            {
                "case_id": case_id,
                "scar_discovery_logits_max_abs_delta": tensor_delta(base["scar_discovery_logits"], zero["scar_discovery_logits"]),
                "edema_discovery_logits_max_abs_delta": tensor_delta(base["edema_discovery_logits"], zero["edema_discovery_logits"]),
                "discovery_logits_max_abs_delta": max(
                    tensor_delta(base["scar_discovery_logits"], zero["scar_discovery_logits"]),
                    tensor_delta(base["edema_discovery_logits"], zero["edema_discovery_logits"]),
                ),
                "scar_confirmation_logits_max_abs_delta": tensor_delta(base["scar_confirmation_logits"], zero["scar_confirmation_logits"]),
                "edema_confirmation_logits_max_abs_delta": tensor_delta(base["edema_confirmation_logits"], zero["edema_confirmation_logits"]),
                "confirmation_logits_max_abs_delta": max(
                    tensor_delta(base["scar_confirmation_logits"], zero["scar_confirmation_logits"]),
                    tensor_delta(base["edema_confirmation_logits"], zero["edema_confirmation_logits"]),
                ),
                "discovery_logits_abs_max": max(
                    float(base["scar_discovery_logits"].detach().abs().max().cpu()),
                    float(base["edema_discovery_logits"].detach().abs().max().cpu()),
                ),
            }
        )
        prototype_rows.append(
            {
                "case_id": case_id,
                "proposal_logit_delta": max(
                    tensor_delta(base["scar_proposal_logits"], proto_off["scar_proposal_logits"]),
                    tensor_delta(base["edema_proposal_logits"], proto_off["edema_proposal_logits"]),
                ),
                "final_logit_delta": tensor_delta(base["logits"], proto_off["logits"]),
                "spatial_gate_delta": tensor_delta(base["gates"]["m10_scar_pass1"], proto_off["gates"]["m10_scar_pass1"]),
            }
        )
        semantic_rows.append(
            {
                "case_id": case_id,
                "proposal_logit_delta": max(
                    tensor_delta(base["scar_proposal_logits"], sem_off["scar_proposal_logits"]),
                    tensor_delta(base["edema_proposal_logits"], sem_off["edema_proposal_logits"]),
                ),
                "final_logit_delta": tensor_delta(base["logits"], sem_off["logits"]),
            }
        )
    write_csv(result_root / "discovery_independence.csv", discovery_rows)
    write_csv(result_root / "prototype_map_intervention.csv", prototype_rows)
    write_csv(result_root / "semantic_memory_intervention.csv", semantic_rows)
    gradient_rows = gradient_authority_rows(model, cfg, list(split), device)
    write_csv(result_root / "gradient_authority.csv", gradient_rows)
    roundtrip = checkpoint_roundtrip_receipt(model, cfg, device)
    (result_root / "checkpoint_roundtrip.json").write_text(json.dumps(roundtrip, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    status = (
        all(float(row["discovery_logits_max_abs_delta"]) <= 1e-6 and float(row["confirmation_logits_max_abs_delta"]) > 1e-5 for row in discovery_rows)
        and gradient_authority_pass(gradient_rows)
        and roundtrip["status"] == "PASS"
    )
    return 0 if status else 1


if __name__ == "__main__":
    raise SystemExit(main())
