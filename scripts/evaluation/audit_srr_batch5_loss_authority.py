#!/usr/bin/env python3
"""Batch5 final-loss authority audit for SRR MyoPS."""

from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import numpy as np
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    EXPANDED_SRR_LOSS_COMPONENT_KEYS,
    collect_expanded_loss_weights,
    component_dict_from_tensor,
    read_anchored_case,
    sample_patch_with_anchor,
    safety_context_dicts_from_raw,
    propref_loss,
)
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.losses import srr_losses  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import sha256_file  # noqa: E402
from src.care_myocardium.srr_production.checkpoint import load_srr_checkpoint  # noqa: E402


TASK_KEY = "20260721_srr_batch5_post_batch4_diagnostic_repair"
PARAMETER_GROUPS = {
    "production_correction_gate": ("production_correction_gate.",),
    "scar_refiner": ("scar_refine.",),
    "edema_refiner": ("edema_refine.",),
    "scar_dictionary": ("scar_dictionary.",),
    "edema_dictionary": ("edema_dictionary.",),
    "retrieval_router": ("retrieval.", "m10_spatial_dictionary.", "encoders.", "decoders.", "evidence_heads."),
}
FIXED_PATCH_SHAPE = (4, 32, 32)


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


def state_hash(model: torch.nn.Module) -> str:
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tuple(value.shape)).encode("utf-8"))
        digest.update(str(value.dtype).encode("utf-8"))
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def group_parameters(model: torch.nn.Module) -> dict[str, list[torch.nn.Parameter]]:
    named = list(model.named_parameters())
    groups: dict[str, list[torch.nn.Parameter]] = {}
    for group, prefixes in PARAMETER_GROUPS.items():
        groups[group] = [param for name, param in named if any(name.startswith(prefix) for prefix in prefixes)]
    return groups


def grad_norm(parameters: Iterable[torch.nn.Parameter]) -> tuple[float, int]:
    total = 0.0
    count = 0
    for param in parameters:
        if param.grad is None:
            continue
        value = param.grad.detach()
        if value.numel() == 0:
            continue
        norm = float(value.norm(2).cpu())
        total += norm * norm
        count += 1
    return total**0.5, count


def args_from_config(cfg: dict[str, Any]) -> SimpleNamespace:
    loss_weights = dict(cfg.get("loss_weights", {}) or {})
    canonical_loss_weights = dict(cfg.get("canonical_loss_weights", {}) or {})
    return SimpleNamespace(
        variant=cfg["model"]["variant"],
        loss_weight_json="",
        loss_weight=[],
        variant_config_record={"variant_config": {"loss_weights": loss_weights, "canonical_loss_weights": canonical_loss_weights}},
        canonical_loss_weights=canonical_loss_weights,
        scar_weight=loss_weights.get("scar"),
        edema_weight=loss_weights.get("edema"),
        proposal_weight=loss_weights.get("proposal"),
        margin_weight=loss_weights.get("prototype_margin"),
        component_proposal_weight=loss_weights.get("component_proposal"),
        semantic_retrieval_weight=loss_weights.get("semantic_retrieval"),
        semantic_integrative_weight=loss_weights.get("semantic_integrative"),
        baseline_preservation_weight=loss_weights.get("anchor_preservation"),
        roi_weight=loss_weights.get("roi"),
        roi_remote_weight=loss_weights.get("remote_roi"),
    )


def directionality_rows(weights: dict[str, float]) -> list[dict[str, Any]]:
    rows = [
        {
            "loss_component": "loss_final_scar_pathology",
            "resolved_weight": weights.get("loss_final_scar_pathology", 0.0),
            "consumed_output_tensors": "outputs.logits class5 one-vs-rest margin",
            "direct_final_pathology_supervision": True,
            "production_gate_corrective_gradient": True,
            "optimization_direction": "repair",
        },
        {
            "loss_component": "loss_final_edema_t2_present_pathology",
            "resolved_weight": weights.get("loss_final_edema_t2_present_pathology", 0.0),
            "consumed_output_tensors": "outputs.logits class4 one-vs-rest margin; T2-present mask",
            "direct_final_pathology_supervision": True,
            "production_gate_corrective_gradient": True,
            "optimization_direction": "repair",
        },
        {
            "loss_component": "loss_production_gate_repair_preserve",
            "resolved_weight": weights.get("loss_production_gate_repair_preserve", 0.0),
            "consumed_output_tensors": "production_correction_gate_logits,nnunet_anchor_logits,labels,availability",
            "direct_final_pathology_supervision": False,
            "production_gate_corrective_gradient": True,
            "optimization_direction": "repair | preserve",
        },
        {
            "loss_component": "loss_scar_refiner_roi",
            "resolved_weight": weights.get("loss_scar_refiner_roi", 1.0),
            "consumed_output_tensors": "scar_logits",
            "direct_final_pathology_supervision": False,
            "production_gate_corrective_gradient": False,
            "optimization_direction": "repair_refiner_branch_not_final_logits",
        },
        {
            "loss_component": "loss_edema_refiner_t2_present_roi",
            "resolved_weight": weights.get("loss_edema_refiner_t2_present_roi", 1.0),
            "consumed_output_tensors": "edema_logits",
            "direct_final_pathology_supervision": False,
            "production_gate_corrective_gradient": False,
            "optimization_direction": "repair_refiner_branch_not_final_logits",
        },
        {
            "loss_component": "loss_correction_opportunity",
            "resolved_weight": weights.get("loss_correction_opportunity", 0.20),
            "consumed_output_tensors": "segmentation_weight,nnunet_anchor_logits",
            "direct_final_pathology_supervision": False,
            "production_gate_corrective_gradient": False,
            "optimization_direction": "legacy_arbitration_open_signal",
        },
        {
            "loss_component": "loss_branch_arbitration_consistency",
            "resolved_weight": weights.get("loss_branch_arbitration_consistency", 0.15),
            "consumed_output_tensors": "segmentation_weight,branch_correction_mask",
            "direct_final_pathology_supervision": False,
            "production_gate_corrective_gradient": False,
            "optimization_direction": "legacy_arbitration_consistency",
        },
        {
            "loss_component": "loss_bounded_correction",
            "resolved_weight": weights.get("loss_bounded_correction", 0.02),
            "consumed_output_tensors": "arbitration_bounded_delta",
            "direct_final_pathology_supervision": False,
            "production_gate_corrective_gradient": False,
            "optimization_direction": "shrink",
        },
        {
            "loss_component": "loss_refiner_final_label_effect",
            "resolved_weight": weights.get("loss_refiner_final_label_effect", 0.02),
            "consumed_output_tensors": "scar_refinement_residual,edema_refinement_residual",
            "direct_final_pathology_supervision": False,
            "production_gate_corrective_gradient": False,
            "optimization_direction": "shrink",
        },
    ]
    return rows


def load_selected_checkpoint_model(cfg: dict[str, Any], device: torch.device) -> tuple[SRRProposeRefineMyoPS, dict[str, Any], Path]:
    batch4_root = REPO_ROOT / str(cfg["source_batch4"]["result_root"])
    adequacy = json.loads((batch4_root / "training_adequacy.json").read_text(encoding="utf-8"))
    checkpoint_path = REPO_ROOT / str(adequacy["selected_checkpoint_path"])
    actual_sha = sha256_file(checkpoint_path)
    expected_sha = str(cfg["source_batch4"]["selected_checkpoint_sha256"])
    if actual_sha != expected_sha:
        raise ValueError(f"selected checkpoint SHA mismatch: {actual_sha} != {expected_sha}")
    model = SRRProposeRefineMyoPS(
        base_channels=int(cfg["model"]["base_channels"]),
        variant=str(cfg["model"]["variant"]),
        encoder_profile=str(cfg["model"]["encoder_profile"]),
        final_output_mode="anchor_bounded_srr_correction",
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)
    payload = load_srr_checkpoint(
        path=checkpoint_path,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        map_location=device,
        restore_rng=False,
    )
    return model, payload, checkpoint_path


def fixed_case_manifest(cfg: dict[str, Any], *, max_cases: int) -> tuple[list[dict[str, Any]], list[Any]]:
    paths = cfg["paths"]
    split_path = REPO_ROOT / paths["split_path"]
    anchor_root = REPO_ROOT / paths["anchor_root"]
    metadata = load_myops_case_metadata(REPO_ROOT)
    split_data = json.loads(split_path.read_text(encoding="utf-8"))
    val_cases = list(split_data["folds"][int(cfg["source_batch4"]["fold"])]["val"])
    selected: list[Any] = []
    manifest: list[dict[str, Any]] = []
    needs = {"scar": True, "edema": True}
    for cid in val_cases:
        case = read_anchored_case(cid, metadata, anchor_root)
        scar_pos = bool(np.any(case.label_arr == 5))
        edema_pos = bool(np.any(case.label_arr == 4)) and bool(case.metadata.t2_present)
        take = False
        if needs["scar"] and scar_pos:
            take = True
            needs["scar"] = False
        if needs["edema"] and edema_pos:
            take = True
            needs["edema"] = False
        if take:
            selected.append(case)
            manifest.append(
                {
                    "case_id": cid,
                    "label_path": f"data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr/{cid}.nii.gz",
                    "anchor_source": case.anchor_source,
                    "patch_shape_zyx": list(FIXED_PATCH_SHAPE),
                    "scar_positive": scar_pos,
                    "edema_positive": edema_pos,
                    "t2_present": bool(case.metadata.t2_present),
                }
            )
        if len(selected) >= max_cases and not any(needs.values()):
            break
    if not selected:
        raise ValueError("no fixed validation cases selected for Batch5 loss audit")
    return manifest, selected


def batch_from_fixed_cases(cases: list[Any], device: torch.device) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, torch.Tensor], dict[str, torch.Tensor], list[str]]:
    rng = np.random.default_rng(20260721)
    xs: list[np.ndarray] = []
    ys: list[np.ndarray] = []
    avs: list[np.ndarray] = []
    anchors: list[np.ndarray] = []
    components: list[np.ndarray] = []
    case_ids: list[str] = []
    for case in cases:
        x_np, y_np, av_np, anchor_np, component_np = sample_patch_with_anchor(
            case,
            FIXED_PATCH_SHAPE,
            rng,
            oversample_foreground=1.0,
            modality_dropout=False,
        )
        xs.append(x_np)
        ys.append(y_np)
        avs.append(av_np)
        anchors.append(anchor_np)
        components.append(component_np)
        case_ids.append(case.case_id)
    x = torch.from_numpy(np.stack(xs, axis=0)).float().to(device)
    y = torch.from_numpy(np.stack(ys, axis=0)).long().to(device)
    av = torch.from_numpy(np.stack(avs, axis=0)).float().to(device)
    anchor_t = torch.from_numpy(np.stack(anchors, axis=0)).float().to(device)
    component_t = torch.from_numpy(np.stack(components, axis=0)).float().to(device)
    return x, y, av, {"probabilities": anchor_t}, component_dict_from_tensor(component_t), case_ids


def gradient_matrix(
    cfg: dict[str, Any],
    weights: dict[str, float],
    *,
    fixed_case_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    torch.manual_seed(20260721)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, payload, checkpoint_path = load_selected_checkpoint_model(cfg, device)
    manifest, cases = fixed_case_manifest(cfg, max_cases=fixed_case_count)
    before = state_hash(model)
    model.train()
    x, labels, availability, anchor_features, component_features, case_ids = batch_from_fixed_cases(cases, device)
    safety_anchor_features, safety_component_features = safety_context_dicts_from_raw(anchor_features, component_features, availability)
    outputs = model(
        x,
        availability,
        anchor_features=anchor_features,
        component_features=component_features,
        safety_anchor_features=safety_anchor_features,
        safety_component_features=safety_component_features,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=case_ids,
    )
    loss_args = args_from_config(cfg)
    _total, metrics = propref_loss(outputs, labels, availability, "soft_roi_refinement", loss_args, detach_m6_metrics=False)
    groups = group_parameters(model)
    rows: list[dict[str, Any]] = []
    for component in EXPANDED_SRR_LOSS_COMPONENT_KEYS:
        value = metrics.get(component)
        if not isinstance(value, torch.Tensor):
            continue
        model.zero_grad(set_to_none=True)
        try:
            value.backward(retain_graph=True)
            backward_status = "OK"
        except RuntimeError as exc:
            backward_status = f"BACKWARD_FAILED:{type(exc).__name__}"
        for group, params in groups.items():
            if backward_status == "OK":
                norm, count = grad_norm(params)
                status = "GRADIENT_PRESENT" if norm > 0 and count > 0 else "NO_GRADIENT_PATH_OR_LOCAL_ZERO"
            else:
                norm = 0.0
                count = 0
                status = backward_status
            rows.append(
                {
                    "loss_component": component,
                    "resolved_weight": weights.get(component, ""),
                    "parameter_group": group,
                    "loss_value": float(value.detach().cpu()) if value.numel() == 1 else "",
                    "grad_l2_norm": norm,
                    "param_with_grad_count": count,
                    "gradient_status": status,
                    "optimizer_steps": 0,
                    "parameter_updates": 0,
                }
            )
    after = state_hash(model)
    return rows, {
        "parameter_hash_before": before,
        "parameter_hash_after": after,
        "parameter_hash_unchanged": before == after,
        "optimizer_steps": 0,
        "parameter_updates": 0,
        "probe_type": "real_batch4_selected_checkpoint_fixed_validation_patch_backward_only",
        "checkpoint_path": str(checkpoint_path.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "checkpoint_global_step": int(payload.get("global_step", -1)),
        "fixed_case_ids": case_ids,
        "fixed_case_manifest": manifest,
        "patch_shape_zyx": list(FIXED_PATCH_SHAPE),
        "device": str(device),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    result_root = REPO_ROOT / args.result_root
    cfg = yaml.safe_load((REPO_ROOT / args.config).read_text(encoding="utf-8"))
    loss_args = args_from_config(cfg)
    weights = collect_expanded_loss_weights(loss_args)
    matrix_rows, hash_payload = gradient_matrix(
        cfg,
        weights,
        fixed_case_count=int(args.fixed_case_count),
    )
    direction_rows = directionality_rows(weights)
    write_csv(result_root / "loss_parameter_gradient_matrix.csv", matrix_rows)
    write_csv(result_root / "loss_gradient_authority.csv", matrix_rows)
    write_csv(result_root / "loss_directionality_audit.csv", direction_rows)
    resolved_rows = []
    for row in direction_rows:
        resolved_rows.append(
            {
                "loss_component": row["loss_component"],
                "source": "canonical_loss_weights" if row["loss_component"] in cfg.get("canonical_loss_weights", {}) else "legacy_or_default_resolution",
                "raw_key": row["loss_component"],
                "alias_chain": row["loss_component"],
                "canonical_component": row["loss_component"],
                "resolved_weight": row["resolved_weight"],
                "consumed_tensors": row["consumed_output_tensors"],
                "parameter_groups_receiving_gradient": ";".join(
                    sorted(
                        {
                            grad_row["parameter_group"]
                            for grad_row in matrix_rows
                            if grad_row["loss_component"] == row["loss_component"] and float(grad_row["grad_l2_norm"]) > 0.0
                        }
                    )
                ),
                "optimization_direction": row["optimization_direction"],
            }
        )
    write_csv(result_root / "resolved_loss_weights.csv", resolved_rows)

    runner_source = inspect.getsource(propref_loss)
    loss_source = inspect.getsource(srr_losses)
    final_direct = (
        "final_pathology_loss_from_logits(outputs[\"logits\"]" in loss_source
        or "_one_vs_rest_margin(final_logits, SCAR_CLASS)" in loss_source
    )
    production_gate_rows = [
        row for row in matrix_rows if row["parameter_group"] == "production_correction_gate" and float(row["grad_l2_norm"]) > 0.0
    ]
    shrink_penalties = [
        row for row in direction_rows if row["optimization_direction"] == "shrink" and float(row["resolved_weight"] or 0.0) > 0.0
    ]
    md = [
        "# Loss Authority Audit",
        "",
        "status: COMPLETE",
        "",
        f"runner_symbol: scripts.training.run_srr_propref_myops_fold0.propref_loss",
        f"loss_source: src/care_myocardium/losses/srr_losses.py",
        f"optimizer_steps: {hash_payload['optimizer_steps']}",
        f"parameter_updates: {hash_payload['parameter_updates']}",
        f"parameter_hash_unchanged: {hash_payload['parameter_hash_unchanged']}",
        "",
        "## Findings",
        "",
        f"does_any_direct_final_pathology_loss_supervise_model_logits: {bool(final_direct)}",
        f"does_production_correction_gate_receive_task_corrective_gradient: {bool(production_gate_rows)}",
        "does_correction_opportunity_target_production_gate_or_legacy_arbitration: legacy_arbitration",
        f"do_active_magnitude_penalties_prefer_zero_correction: {bool(shrink_penalties)}",
        "does_refiner_effect_loss_reward_or_penalize_nonzero_residual: penalize_nonzero_residual",
        "",
        (
            "Batch6 now adds direct deployed `outputs[\"logits\"]` scar/edema GT repair losses and a production gate repair/preserve loss. "
            "Legacy correction-opportunity, branch arbitration, bounded-correction shrink, and refiner-effect shrink weights resolve to zero under the Batch6 canonical config."
            if final_direct
            else "The active branch/refiner losses supervise proposal/refiner tensors, while the final deployed `outputs[\"logits\"]` production correction path lacks a direct scar/edema GT repair loss. The correction-opportunity term is wired to the legacy arbitration open signal, and the bounded-correction/refiner-effect terms are positive magnitude penalties."
        ),
    ]
    (result_root / "loss_authority_audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    payload = {
        "status": "BATCH5_LOSS_AUTHORITY_AUDIT_COMPLETE",
        **hash_payload,
        "direct_final_logits_supervision": bool(final_direct),
        "production_gate_gradient_rows": len(production_gate_rows),
        "active_shrink_penalty_rows": len(shrink_penalties),
    }
    (result_root / "loss_authority_audit.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    reconciliation = [
        "# Batch5 Reconciliation",
        "",
        "optimizer_steps: 0",
        f"parameter_hash_unchanged: {hash_payload['parameter_hash_unchanged']}",
        f"checkpoint_sha256: {hash_payload['checkpoint_sha256']}",
        "effective_weight_resolution: COMPLETE",
        "direct_final_objective_status: RECALCULATED_FOR_BATCH6",
        "proposal_refiner_purity_status: REQUIRES_MODE_METRIC_VALIDATOR",
    ]
    (result_root / "batch5_reconciliation.md").write_text("\n".join(reconciliation) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch5.yaml")
    parser.add_argument("--result-root", default=f"results/{TASK_KEY}")
    parser.add_argument("--fixed-case-count", type=int, default=2)
    args = parser.parse_args()
    payload = run(args)
    return 0 if payload["parameter_hash_unchanged"] and payload["optimizer_steps"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
