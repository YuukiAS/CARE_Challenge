#!/usr/bin/env python3
"""Calibrate Batch7 SIP lambda from train-only center-balanced gradients."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    SRRProposeRefineMyoPS,
    _repo_path,
    apply_batch6_trainable_groups,
    apply_batch7_decomposition_schedule,
    batch_from_source_balanced_case,
    build_source_balanced_center_sequence,
    component_dict_from_tensor,
    load_split,
    model_kwargs_from_args,
    parse_shape,
    propref_loss,
    read_anchored_case,
    safety_context_dicts_from_raw,
    source_balanced_case_pools,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.losses.srr_losses import br2_selective_integration_penalty  # noqa: E402
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
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def target_loss_weights(cfg: dict[str, Any], pathology: str) -> dict[str, float]:
    weights: dict[str, float] = {}
    for section in ("common_zero", f"{pathology}_common"):
        for key, value in cfg["loss_weights"].get(section, {}).items():
            try:
                weights[str(key)] = float(value)
            except (TypeError, ValueError):
                continue
    return weights


def coefficient_parameters(model: torch.nn.Module, pathology: str) -> list[torch.nn.Parameter]:
    prefix = "scar_lightweight_br2." if pathology == "scar" else "edema_lightweight_br2."
    names = (f"{prefix}beta_pattern", f"{prefix}center_deviation_raw")
    return [param for name, param in model.named_parameters() if any(name.startswith(item) for item in names)]


def grad_norm(params: list[torch.nn.Parameter]) -> float:
    total = 0.0
    for param in params:
        if param.grad is None:
            continue
        norm = float(param.grad.detach().norm(2).cpu())
        total += norm * norm
    return total ** 0.5


def make_args(cfg: dict[str, Any], pathology: str, loss_json: dict[str, float], device: str) -> SimpleNamespace:
    common = cfg["common_training"]
    model = cfg["model"]
    return SimpleNamespace(
        variant=model["source_variant"],
        base_channels=int(model["base_channels"]),
        encoder_profile=str(model["encoder_profile"]),
        disable_local_refinement=True,
        disable_anatomy_roi_prior=False,
        final_output_mode=str(model["final_output_mode"]),
        enable_batch7_decomposition_br2=True,
        batch7_decomposition_use_sip=False,
        batch7_minimal_decomposition_mode=True,
        variant_config_record={},
        canonical_loss_weights={},
        loss_weight_json=json.dumps(loss_json, sort_keys=True, separators=(",", ":")),
        loss_weight=[],
        scar_weight=None,
        edema_weight=None,
        proposal_weight=None,
        margin_weight=0.0,
        component_proposal_weight=0.0,
        semantic_retrieval_weight=0.0,
        semantic_integrative_weight=0.0,
        baseline_preservation_weight=0.0,
        roi_weight=0.0,
        roi_remote_weight=0.0,
        batch6_trainable_groups=(
            "scar_evidence_head,scar_proposal_dictionary,scar_lightweight_br2,scar_br2_coefficients"
            if pathology == "scar"
            else "edema_evidence_head,edema_proposal_dictionary,edema_lightweight_br2,edema_br2_coefficients"
        ),
        patch_shape=",".join(str(x) for x in common["patch_shape"]),
        device=device,
    )


def calibrate(args: argparse.Namespace) -> list[dict[str, Any]]:
    cfg = yaml.safe_load(repo_path(args.config).read_text(encoding="utf-8"))
    result_root = repo_path(cfg["paths"]["result_root"])
    checkpoint = repo_path(args.checkpoint)
    expected_sha = str(args.checkpoint_sha256 or "").strip()
    actual_sha = sha256_file(checkpoint)
    if expected_sha and actual_sha != expected_sha:
        raise SystemExit(f"checkpoint sha mismatch: {actual_sha} != {expected_sha}")
    device = torch.device("cuda" if args.device == "cuda" and torch.cuda.is_available() else "cpu")
    train_ids, _val_ids = load_split(int(cfg["training_data"]["fold"]))
    metadata = load_myops_case_metadata(REPO_ROOT)
    anchor_root = repo_path(cfg["paths"].get("anchor_root", DEFAULT_NNUNET_ANCHOR_ROOT))
    train_cases = [read_anchored_case(case_id, metadata, anchor_root) for case_id in train_ids]
    pools = source_balanced_case_pools(train_cases, args.pathology)
    centers = sorted(pools)
    if not centers:
        raise SystemExit(f"no eligible centers for {args.pathology} calibration")
    patch_shape = parse_shape(",".join(str(x) for x in cfg["common_training"]["patch_shape"]))
    center_sequence = build_source_balanced_center_sequence(centers, steps=len(centers), rng=np.random.default_rng(20260722))
    rng = np.random.default_rng(20260722 + (11 if args.pathology == "scar" else 23))
    train_args = make_args(cfg, args.pathology, target_loss_weights(cfg, args.pathology), str(device))
    model = SRRProposeRefineMyoPS(**model_kwargs_from_args(train_args)).to(device)
    apply_batch6_trainable_groups(model, train_args.batch6_trainable_groups)
    optimizer = torch.optim.AdamW([param for param in model.parameters() if param.requires_grad], lr=1e-4)
    payload = load_srr_checkpoint(
        path=checkpoint,
        model=model,
        optimizer=optimizer,
        scheduler=None,
        amp_scaler=None,
        map_location=device,
        restore_rng=False,
        restore_optimizer=False,
        strict_model_state=True,
    )
    apply_batch7_decomposition_schedule(model, pathology=args.pathology, step=51, br2_enabled=True)
    params = coefficient_parameters(model, args.pathology)
    if not params:
        raise SystemExit("no BR2 coefficient parameters found for calibration")
    batch_records: list[dict[str, Any]] = []

    def iterate_losses(kind: str) -> float:
        model.zero_grad(set_to_none=True)
        for step in range(1, len(centers) + 1):
            x_cpu, y_cpu, av_cpu, anchor_cpu, component_cpu, keys, manifest = batch_from_source_balanced_case(
                pools=pools,
                step=step,
                patch_shape=patch_shape,
                rng=rng if kind == "target" else np.random.default_rng(20260722 + (11 if args.pathology == "scar" else 23) + step - step),
                pathology=args.pathology,
                oversample_foreground=1.0,
                center_sequence=center_sequence,
            )
            if kind == "sip":
                # Recreate the same center-balanced sequence for the SIP pass.
                local_rng = np.random.default_rng(20260722 + (11 if args.pathology == "scar" else 23))
                for replay_step in range(1, step + 1):
                    x_cpu, y_cpu, av_cpu, anchor_cpu, component_cpu, keys, manifest = batch_from_source_balanced_case(
                        pools=pools,
                        step=replay_step,
                        patch_shape=patch_shape,
                        rng=local_rng,
                        pathology=args.pathology,
                        oversample_foreground=1.0,
                        center_sequence=center_sequence,
                    )
            x = x_cpu.to(device)
            y = y_cpu.to(device)
            av = av_cpu.to(device)
            anchor_features = {key: value.to(device) for key, value in anchor_cpu.items()}
            component_features = {key: value.to(device) for key, value in component_cpu.items()}
            safety_anchor, safety_component = safety_context_dicts_from_raw(anchor_features, component_features, av)
            case_lookup = {case.case_id: case for rows in pools.values() for case in rows}
            outputs = model(
                x,
                av,
                anchor_features=anchor_features,
                component_features=component_features,
                safety_anchor_features=safety_anchor,
                safety_component_features=safety_component,
                case_ids=keys,
                production_intervention_mode="full",
                center_ids=[str(case_lookup[key].metadata.center) for key in keys],
                use_center_beta=True,
            )
            if kind == "target":
                loss, _metrics = propref_loss(outputs, y, av, "proposal_dictionary", train_args, detach_m6_metrics=False)
                batch_records.append({"step": step, "case_id": keys[0], **manifest})
            else:
                loss, _metrics = br2_selective_integration_penalty(outputs, args.pathology, tau=float(cfg["sip"]["tau"]))
            (loss / float(len(centers))).backward()
        return grad_norm(params)

    target_norm = iterate_losses("target")
    sip_norm = iterate_losses("sip")
    target = float(cfg["sip"]["lambda_selection"]["target_gradient_ratio"])
    preferred_lo, preferred_hi = [float(x) for x in cfg["sip"]["lambda_selection"]["preferred_ratio_range"]]
    abs_lo, abs_hi = [float(x) for x in cfg["sip"]["lambda_selection"]["absolute_allowed_ratio_range"]]
    candidates = [float(x) for x in cfg["sip"].get("lambda_sip_candidates", [])]
    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        ratio = float("inf") if target_norm <= 0.0 else candidate * sip_norm / max(target_norm, 1e-12)
        scored.append(
            {
                "pathology": args.pathology,
                "candidate_lambda_sip": candidate,
                "selected_lambda": "",
                "target_gradient_ratio": target,
                "observed_gradient_ratio": ratio,
                "target_loss_coefficient_grad_norm": target_norm,
                "sip_unit_lambda_coefficient_grad_norm": sip_norm,
                "calibration_case_count": len(batch_records),
                "calibration_centers": ";".join(centers),
                "checkpoint_path": str(checkpoint),
                "checkpoint_sha256": actual_sha,
                "checkpoint_global_step": int(payload.get("global_step", -1)),
                "status": "CANDIDATE_EVALUATED",
                "selected": 0,
                "formal_sip_run_allowed": 0,
            }
        )
    preferred = [row for row in scored if preferred_lo <= float(row["observed_gradient_ratio"]) <= preferred_hi]
    absolute = [row for row in scored if abs_lo <= float(row["observed_gradient_ratio"]) <= abs_hi]
    pool = preferred or absolute
    if not pool:
        for row in scored:
            row["status"] = "FAIL_NO_CANDIDATE_IN_ALLOWED_GRADIENT_RATIO_RANGE"
        selected = None
    else:
        selected = min(pool, key=lambda row: abs(float(row["observed_gradient_ratio"]) - target))
        selected["selected"] = 1
        selected["selected_lambda"] = selected["candidate_lambda_sip"]
        selected["status"] = "PASS"
        selected["formal_sip_run_allowed"] = 1
    existing = []
    out_csv = result_root / "sip_weight_calibration.csv"
    if out_csv.is_file():
        with out_csv.open(newline="", encoding="utf-8") as handle:
            existing = [row for row in csv.DictReader(handle) if row.get("pathology") != args.pathology]
    rows = existing + scored
    write_csv(out_csv, rows)
    write_csv(result_root / f"{args.pathology}_sip_calibration_batches.csv", batch_records)
    if selected is None:
        raise SystemExit(f"no allowed SIP lambda candidate for {args.pathology}; wrote {out_csv}")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch7_minimal_decomposition.yaml")
    parser.add_argument("--pathology", choices=("scar", "edema"), required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--checkpoint-sha256", default="")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    args = parser.parse_args()
    rows = calibrate(args)
    selected = [row for row in rows if row.get("pathology") == args.pathology and row.get("status") == "PASS"]
    print(json.dumps({"pathology": args.pathology, "selected": selected}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
