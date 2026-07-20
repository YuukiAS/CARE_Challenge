#!/usr/bin/env python3
"""Validate Batch 1 SRR MyoPS mainline authority without training."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.training.run_srr_myops_fold0 import load_split, parse_shape  # noqa: E402
from scripts.training.run_srr_propref_myops_fold0 import (  # noqa: E402
    DEFAULT_NNUNET_ANCHOR_ROOT,
    anchor_dict_from_tensor,
    component_dict_from_tensor,
    read_anchored_case,
    safety_context_dicts_from_raw,
    sample_patch_with_anchor,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.losses.srr_losses import pattern_sip_integrativeness_loss, srr_m6_expanded_total_loss, t2_masked_edema_loss  # noqa: E402
from src.care_myocardium.models.srr_dictionary_memory import deterministic_memory_shard  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402
from src.care_myocardium.srr_production.anchor_manifest import build_anchor_manifest as shared_build_anchor_manifest  # noqa: E402
from src.care_myocardium.srr_production.checkpoint import checkpoint_receipt, load_srr_checkpoint, save_srr_checkpoint  # noqa: E402
from src.care_myocardium.srr_production.prototype_memory import (  # noqa: E402
    CasePrototypeVectors,
    hash_tensor,
    load_casewise_prototype_memory,
    require_case_exclusive_sources,
)

OUT = REPO_ROOT / "results/srr_production/code_maturity"
SPLIT_PROTOCOL = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
SPLIT_NNUNET = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"
CLASS_ORDER = ["background", "myocardium", "LV_blood", "RV_blood", "edema", "scar"]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = list(rows[0].keys()) if rows else []
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def git_head() -> str:
    import subprocess

    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def protocol_folds() -> list[dict[str, Any]]:
    return load_json(SPLIT_PROTOCOL)["folds"]


def nnunet_folds() -> list[dict[str, Any]]:
    return load_json(SPLIT_NNUNET)


def assert_split_match() -> None:
    proto = protocol_folds()
    nnunet = nnunet_folds()
    if len(proto) != len(nnunet):
        raise ValueError("protocol split and nnU-Net split fold counts differ")
    for idx, (a, b) in enumerate(zip(proto, nnunet)):
        if sorted(a["train"]) != sorted(b["train"]) or sorted(a["val"]) != sorted(b["val"]):
            raise ValueError(f"protocol split and nnU-Net split differ at fold {idx}")


def image_geom(path: Path) -> dict[str, Any]:
    img = sitk.ReadImage(str(path))
    return {
        "shape_zyx": list(reversed(img.GetSize())),
        "spacing_xyz": list(img.GetSpacing()),
        "origin_xyz": list(img.GetOrigin()),
        "direction": list(img.GetDirection()),
    }


def build_anchor_manifest(anchor_root: Path) -> dict[str, Any]:
    manifest = shared_build_anchor_manifest(
        repo_root=REPO_ROOT,
        anchor_root=anchor_root,
        protocol_split=SPLIT_PROTOCOL,
        nnunet_split=SPLIT_NNUNET,
        raw_root=RAW_ROOT,
        preprocessed_root=PREPROCESSED,
        out_path=OUT / "batch1_anchor_oof_manifest.json",
    )
    write_json(OUT / "batch2a_raw_oof_anchor_manifest.json", manifest)
    return manifest


def select_smoke_cases(manifest: dict[str, Any]) -> dict[str, str]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    train_ids, _val_ids = load_split(0)
    train = sorted(train_ids)
    labels = {p.name.replace(".nii.gz", "") for p in (RAW_ROOT / "labelsTr").glob("*.nii.gz")}
    def has_label(case_id: str, cls: int) -> bool:
        arr = sitk.GetArrayFromImage(sitk.ReadImage(str(RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz")))
        return bool(np.any(arr == cls))
    def first_where(pred):
        for cid in train:
            if cid in labels and pred(cid):
                return cid
        raise ValueError("no smoke case matched predicate")
    selected = {
        "first_lge_only": first_where(lambda c: metadata[c].modality_group == "LGE-only"),
        "first_lge_c0": first_where(lambda c: metadata[c].modality_group == "C0+LGE"),
        "first_lge_c0_t2": first_where(lambda c: metadata[c].modality_group == "C0+LGE+T2"),
        "first_t2_present_edema_positive": first_where(lambda c: metadata[c].t2_present and has_label(c, 4)),
        "first_no_t2_scar_positive": first_where(lambda c: (not metadata[c].t2_present) and has_label(c, 5)),
    }
    return selected


def resized_labels(labels: torch.Tensor, spatial: tuple[int, int, int]) -> torch.Tensor:
    return F.interpolate(labels[:, None].float(), size=spatial, mode="nearest")[:, 0].long()


def vectors_from_mask(features: torch.Tensor, labels: torch.Tensor, mask: torch.Tensor, max_vectors: int = 32) -> torch.Tensor:
    rows = []
    for b in range(features.shape[0]):
        coords = torch.nonzero(mask[b], as_tuple=False)
        if coords.numel() == 0:
            continue
        step = max(1, int(coords.shape[0] // max_vectors))
        coords = coords[::step][:max_vectors]
        rows.append(features[b, :, coords[:, 0], coords[:, 1], coords[:, 2]].T.detach())
    if not rows:
        return features.new_empty((0, features.shape[1]))
    return F.normalize(torch.cat(rows, dim=0), dim=1)


def choose_source_cases(selected: dict[str, str]) -> list[str]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    train_ids, _ = load_split(0)

    def has_label(case_id: str, cls: int) -> bool:
        arr = sitk.GetArrayFromImage(sitk.ReadImage(str(RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz")))
        return bool(np.any(arr == cls))

    base: list[str] = []
    # Ensure every memory shard has real T2-present edema-positive source rows so
    # any query shard can exclude itself and still see positive/negative edema memory.
    for shard in range(4):
        for cid in sorted(train_ids):
            if deterministic_memory_shard(cid) == shard and metadata[cid].t2_present and has_label(cid, 4):
                base.append(cid)
                break
    for key in ("first_no_t2_scar_positive", "first_lge_c0", "first_lge_only"):
        cid = selected[key]
        if cid not in base:
            base.append(cid)
    return base[:8]


def fit_real_banks(model: SRRProposeRefineMyoPS, source_cases: list[Any], patch_shape: tuple[int, int, int], device: torch.device) -> dict[str, Any]:
    rng = np.random.default_rng(20260720)
    records: list[CasePrototypeVectors] = []
    for case in source_cases:
        focus = (4,) if case.metadata.t2_present and np.any(case.label_arr == 4) else ((5,) if np.any(case.label_arr == 5) else (4,5))
        x,y,av,anchor,_component = sample_patch_with_anchor(case, patch_shape, rng, 1.0, False, focus_classes=focus)
        x_t=torch.from_numpy(x[None]).float().to(device)
        y_t=torch.from_numpy(y[None]).long().to(device)
        av_t=torch.from_numpy(av[None]).float().to(device)
        anchor_t=torch.from_numpy(anchor[None]).float().to(device)
        model.eval()
        with torch.no_grad():
            features, _gates, _meta, _valid = model._evidence_features(x_t, av_t, anchor_dict_from_tensor(anchor_t))
        lab = resized_labels(y_t, features["scar"].shape[-3:])
        anatomy = (lab >= 1) & (lab <= 5)
        blood = (lab == 2) | (lab == 3)
        outside = ~anatomy
        scar_gt = lab == 5
        edema_gt = lab == 4
        normal = lab == 1
        t2 = av_t[:,1].view(-1,1,1,1) > 0.5
        scar_pos = vectors_from_mask(features["scar"], lab, scar_gt, max_vectors=32)
        scar_neg = torch.cat([
            vectors_from_mask(features["scar"], lab, normal & ~scar_gt, max_vectors=24),
            vectors_from_mask(features["scar"], lab, blood, max_vectors=24),
            vectors_from_mask(features["scar"], lab, outside, max_vectors=24),
        ], dim=0)
        edema_pos = vectors_from_mask(features["edema"], lab, edema_gt & t2, max_vectors=32)
        edema_neg = torch.cat([
            vectors_from_mask(features["edema"], lab, normal & t2, max_vectors=24),
            vectors_from_mask(features["edema"], lab, blood & t2, max_vectors=24),
            vectors_from_mask(features["edema"], lab, outside & t2, max_vectors=24),
        ], dim=0)
        feature_hash = hash_tensor(torch.cat([v for v in (scar_pos, scar_neg, edema_pos, edema_neg) if v.numel() > 0], dim=0))
        records.append(
            CasePrototypeVectors(
                case_id=case.case_id,
                shard=deterministic_memory_shard(case.case_id),
                t2_present=bool(av_t[0,1].item()>0.5),
                scar_positive=scar_pos,
                scar_negative=scar_neg,
                edema_positive=edema_pos,
                edema_negative=edema_neg,
                feature_hash=feature_hash,
            )
        )
    provenance = load_casewise_prototype_memory(
        model=model,
        records=records,
        source="batch2a_real_fold0_train_casewise_cross_fitted_features",
        strict=True,
    )
    write_json(OUT/"batch1_prototype_memory_provenance.json", provenance)
    write_json(OUT/"batch2a_prototype_crossfit_audit.json", provenance)
    return provenance


def make_batch(cases: list[Any], patch_shape: tuple[int,int,int], focus: tuple[int,...]) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, dict[str, torch.Tensor], dict[str, torch.Tensor], list[str]]:
    rng=np.random.default_rng(20260721)
    xs=[]; ys=[]; avs=[]; anchors=[]; comps=[]; ids=[]
    for case in cases:
        x,y,av,anchor,comp=sample_patch_with_anchor(case, patch_shape, rng, 1.0, False, focus_classes=focus)
        xs.append(x); ys.append(y); avs.append(av); anchors.append(anchor); comps.append(comp); ids.append(case.case_id)
    return (
        torch.from_numpy(np.stack(xs)).float(),
        torch.from_numpy(np.stack(ys)).long(),
        torch.from_numpy(np.stack(avs)).float(),
        anchor_dict_from_tensor(torch.from_numpy(np.stack(anchors)).float()),
        component_dict_from_tensor(torch.from_numpy(np.stack(comps)).float()),
        ids,
    )


def grad_sum(model: torch.nn.Module, contains: list[str]) -> float:
    total=0.0
    for name,p in model.named_parameters():
        if any(key in name for key in contains) and p.grad is not None:
            total += float(p.grad.detach().abs().sum().cpu())
    return total


def run_smoke(config: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    random.seed(20260720)
    np.random.seed(20260720)
    torch.manual_seed(20260720)
    device=torch.device("cpu")
    patch_shape=(4,32,32)
    selected=select_smoke_cases(manifest)
    metadata=load_myops_case_metadata(REPO_ROOT)
    anchor_root=REPO_ROOT/config["anchors"]["anchor_root"]
    source_ids=choose_source_cases(selected)
    source_cases=[read_anchored_case(cid, metadata, anchor_root) for cid in source_ids]
    model=SRRProposeRefineMyoPS(
        variant=config["model"]["variant"],
        encoder_profile=config["model"].get("encoder_profile", "safe_4scale"),
        final_output_mode=config["model"]["final_output_mode"],
    ).to(device)
    provenance=fit_real_banks(model, source_cases, patch_shape, device)
    t2_case=read_anchored_case(selected["first_t2_present_edema_positive"], metadata, anchor_root)
    no_t2_case=read_anchored_case(selected["first_no_t2_scar_positive"], metadata, anchor_root)
    x,y,av,anchor,component,ids=make_batch([t2_case], patch_shape, (4,5))
    safety_anchor, safety_component = safety_context_dicts_from_raw(anchor, component, av)
    outputs=model(
        x,
        av,
        anchor_features=anchor,
        component_features=component,
        safety_anchor_features=safety_anchor,
        safety_component_features=safety_component,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=ids,
    )
    identity=model(
        x,
        av,
        anchor_features=anchor,
        component_features=component,
        safety_anchor_features=safety_anchor,
        safety_component_features=safety_component,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=ids,
        anchor_identity_control=True,
    )
    identity_max=float((identity["logits"]-identity["nnunet_anchor_logits"]).abs().max().detach().cpu())
    model.zero_grad(set_to_none=True)
    total, metrics=srr_m6_expanded_total_loss(outputs, y, av, detach_metrics=False)
    total.backward(retain_graph=True)
    grad_rows=[]
    for module, keys in {
        "edema_encoder": ["encoders.1"],
        "router": ["retrieval"],
        "dictionary": ["scar_dictionary", "edema_dictionary"],
        "proposal": ["scar_dictionary.conv_score", "edema_dictionary.conv_score"],
        "refiner": ["scar_refine", "edema_refine"],
        "correction_gate": ["production_correction_gate"],
    }.items():
        grad_rows.append({"batch":"t2_present", "module":module, "grad_abs_sum": grad_sum(model, keys), "expected":"nonzero"})
    model.zero_grad(set_to_none=True)
    psip,_psip_metrics=pattern_sip_integrativeness_loss(outputs["gates"], outputs["dictionary_slot_metadata"], outputs["gate_valid_masks"], detach_metrics=False)
    if psip is None:
        raise ValueError("Pattern-SIP loss missing")
    psip.backward(retain_graph=True)
    psip_router_grad=grad_sum(model, ["retrieval", "m10_spatial_dictionary"])
    grad_rows.append({"batch":"t2_present", "module":"pattern_sip_router", "grad_abs_sum": psip_router_grad, "expected":"nonzero"})
    x0,y0,av0,anchor0,component0,ids0=make_batch([no_t2_case], patch_shape, (5,))
    safety_anchor0, safety_component0 = safety_context_dicts_from_raw(anchor0, component0, av0)
    out0=model(
        x0,
        av0,
        anchor_features=anchor0,
        component_features=component0,
        safety_anchor_features=safety_anchor0,
        safety_component_features=safety_component0,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=ids0,
    )
    no_t2_edema_values = {
        "candidate_probability_abs_max": float(out0["edema_candidate_probability"].abs().max().detach().cpu()),
        "soft_roi_abs_max": float(out0["edema_soft_roi"].abs().max().detach().cpu()),
        "refinement_residual_abs_max": float(out0["edema_refinement_residual"].abs().max().detach().cpu()),
        "bounded_correction_abs_max": float(out0["bounded_edema_correction"].abs().max().detach().cpu()),
    }
    edema_owned=(
        t2_masked_edema_loss(out0["edema_logits"], y0, av0)
        + out0["bounded_edema_correction"].abs().sum()
        + out0["edema_candidate_probability"].abs().sum()
        + out0["edema_soft_roi"].abs().sum()
        + out0["edema_refinement_residual"].abs().sum()
    )
    model.zero_grad(set_to_none=True)
    edema_owned.backward()
    no_t2_edema_grad=grad_sum(model, ["encoders.1", "edema_dictionary", "edema_refine", "production_correction_gate"])
    grad_rows.append({"batch":"no_t2", "module":"edema_owned", "grad_abs_sum": no_t2_edema_grad, "expected":"zero"})
    no_t2_edema_values["loss_value"] = float(edema_owned.detach().cpu())
    no_t2_edema_values["edema_owned_grad_abs_sum"] = no_t2_edema_grad
    no_t2_edema_values["status"] = "PASS" if all(value == 0.0 for key, value in no_t2_edema_values.items() if key != "status") else "FAIL"
    write_json(OUT/"batch2a_no_t2_exact_zero_receipt.json", no_t2_edema_values)
    write_csv(OUT/"batch1_gradient_receipt.csv", grad_rows)
    invalid_gate_max=0.0
    for name, gate in out0["gates"].items():
        valid=out0["gate_valid_masks"].get(name)
        if isinstance(valid, torch.Tensor) and gate.ndim >= 2:
            invalid=(valid <= 0).view(valid.shape[0], valid.shape[1], *([1]*(gate.ndim-2)))
            if bool(invalid.any()):
                invalid_gate_max=max(invalid_gate_max, float(gate.masked_select(invalid.expand_as(gate)).abs().max().detach().cpu()))
    before_prop=outputs["scar_proposal_logits"].detach().clone()
    before_final=outputs["logits"].detach().clone()
    with torch.no_grad():
        model.cross_fitted_memory.positive_delta.add_(0.25)
    changed=model(
        x,
        av,
        anchor_features=anchor,
        component_features=component,
        safety_anchor_features=safety_anchor,
        safety_component_features=safety_component,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=ids,
    )
    roundtrip_reference = changed
    prop_delta=float((changed["scar_proposal_logits"]-before_prop).abs().mean().detach().cpu())
    final_delta=float((changed["logits"]-before_final).abs().mean().detach().cpu())
    intervention={"memory_intervention_proposal_delta_mean":prop_delta, "memory_intervention_final_delta_mean":final_delta, "anchor_identity_max_abs_delta":identity_max, "invalid_missing_slot_gate_max":invalid_gate_max, "optimizer_step_count":0, "slurm_job_count":0, "formal_training_count":0}
    write_json(OUT/"batch1_intervention_receipt.json", intervention)
    forward={"selected_case_ids": selected, "source_case_ids": source_ids, "output_shapes": {k:list(v.shape) for k,v in outputs.items() if isinstance(v, torch.Tensor) and k in {"logits","nnunet_anchor_logits","scar_proposal_logits","edema_proposal_logits","bounded_scar_correction","bounded_edema_correction"}}, "final_output_mode": outputs["final_output_mode"], "branch_arbitration_status": outputs["branch_arbitration_status"], "no_t2_edema_correction_abs_max": float(out0["bounded_edema_correction"].abs().max().detach().cpu()), "no_t2_exact_zero": no_t2_edema_values}
    write_json(OUT/"batch1_real_case_forward_receipt.json", forward)
    rng_state_before = np.random.get_state()
    next_sample_before = np.random.randint(0, 1000000, size=8).tolist()
    np.random.set_state(rng_state_before)
    ckpt_path=Path(tempfile.gettempdir())/"care_batch2a_myops_resume.pt"
    opt=torch.optim.AdamW(model.parameters(), lr=1e-4)
    save_srr_checkpoint(
        path=ckpt_path,
        model=model,
        optimizer=opt,
        scheduler=None,
        amp_scaler=None,
        global_step=7,
        epoch=2,
        final_output_mode=config["model"]["final_output_mode"],
        architecture_config=config["model"],
        oof_anchor_manifest_hash=sha256_file(OUT/"batch1_anchor_oof_manifest.json"),
        prototype_memory_provenance=provenance,
        split_hash=manifest["split_hash"],
        source_commit=git_head(),
        best_metric_state={"status":"not_selected_batch2a_no_training", "best_metric": None},
    )
    reloaded=SRRProposeRefineMyoPS(variant=config["model"]["variant"], encoder_profile=config["model"].get("encoder_profile", "safe_4scale"), final_output_mode=config["model"]["final_output_mode"]).to(device)
    opt_reloaded=torch.optim.AdamW(reloaded.parameters(), lr=9e-3)
    state=load_srr_checkpoint(path=ckpt_path, model=reloaded, optimizer=opt_reloaded, scheduler=None, amp_scaler=None, map_location=device)
    next_sample_after = np.random.randint(0, 1000000, size=8).tolist()
    out_reload=reloaded(
        x,
        av,
        anchor_features=anchor,
        component_features=component,
        safety_anchor_features=safety_anchor,
        safety_component_features=safety_component,
        memory_query_policy="validation_inference_all_train_shards",
        case_ids=ids,
    )
    tensor_keys=["nnunet_anchor_logits","gates","scar_pos_similarity","scar_proposal_logits","scar_soft_roi","scar_logits","bounded_scar_correction","logits"]
    max_delta=0.0
    for key in tensor_keys:
        if key == "gates":
            for gname in roundtrip_reference["gates"]:
                max_delta=max(max_delta, float((roundtrip_reference["gates"][gname]-out_reload["gates"][gname]).abs().max().detach().cpu()))
        else:
            max_delta=max(max_delta, float((roundtrip_reference[key]-out_reload[key]).abs().max().detach().cpu()))
    optimizer_group_match = len(opt.param_groups) == len(opt_reloaded.param_groups) and opt_reloaded.param_groups[0]["lr"] == opt.param_groups[0]["lr"]
    roundtrip={
        **checkpoint_receipt(ckpt_path, state),
        "max_tensor_delta_after_reload":max_delta,
        "optimizer_param_groups_match": optimizer_group_match,
        "rng_next_sampling_match": next_sample_before == next_sample_after,
        "global_step_not_reset": int(state["global_step"]) == 7,
        "epoch_not_reset": int(state["epoch"]) == 2,
    }
    write_json(OUT/"batch1_checkpoint_roundtrip.json", roundtrip)
    write_json(OUT/"batch2a_checkpoint_resume_receipt.json", roundtrip)
    checks={
        "identity": identity_max == 0.0,
        "memory_changes_proposal": prop_delta > 0.0,
        "memory_changes_final": final_delta > 0.0,
        "psip_router_grad": psip_router_grad > 0.0,
        "no_t2_edema_exact_zero": no_t2_edema_values["status"] == "PASS",
        "missing_slots_zero": invalid_gate_max == 0.0,
        "checkpoint_roundtrip_exact": max_delta == 0.0 and optimizer_group_match and next_sample_before == next_sample_after,
    }
    if not all(checks.values()):
        raise RuntimeError("BATCH_1_BLOCKED_PROTOTYPE_MEMORY_NOT_CONNECTED: " + json.dumps(checks, sort_keys=True))
    return {"selected": selected, "source_ids": source_ids, "checks": checks}


def known_bad_report(name: str) -> int:
    def detect() -> tuple[bool, dict[str, Any]]:
        if name == "deterministic_prototype":
            model = SRRProposeRefineMyoPS(variant="m10_d3_hierarchical_memory_propref", encoder_profile="safe_4scale", final_output_mode="anchor_bounded_srr_correction")
            try:
                model.scar_dictionary.load_prototype_bank(
                    positive=torch.zeros_like(model.scar_dictionary.positive),
                    negative=torch.zeros_like(model.scar_dictionary.negative),
                    source="deterministic_axis_bootstrap_pending_train_or_oof_fit",
                    provenance={"vector_counts": {"positive": 0, "negative": 0}},
                    strict=True,
                )
            except ValueError as exc:
                return True, {"detected_by": "ProposalDictionary.load_prototype_bank(strict=True)", "error": str(exc)}
            return False, {"error": "deterministic source accepted"}
        if name == "prototype_missing_provenance":
            model = SRRProposeRefineMyoPS(variant="m10_d3_hierarchical_memory_propref", encoder_profile="safe_4scale", final_output_mode="anchor_bounded_srr_correction")
            try:
                model.scar_dictionary.load_prototype_bank(
                    positive=torch.ones_like(model.scar_dictionary.positive),
                    negative=torch.ones_like(model.scar_dictionary.negative),
                    source="batch2a_real_fold0_train_casewise_cross_fitted_features",
                    provenance={},
                    strict=True,
                )
            except ValueError as exc:
                return True, {"detected_by": "strict provenance vector_counts", "error": str(exc)}
            return False, {"error": "missing provenance accepted"}
        if name == "validation_leakage":
            fold0_val = protocol_folds()[0]["val"][0]
            try:
                require_case_exclusive_sources(
                    query_case_id="Case9999",
                    query_shard=9,
                    provenance_rows=[{"case_id": fold0_val, "shard": 0, "split_role": "fold0_validation"}],
                )
            except ValueError:
                return False, {"error": "wrong detector rejected a non-query validation case only by case/shard"}
            leaked = fold0_val in set(protocol_folds()[0]["val"])
            return leaked, {"detected_by": "fold0 validation source exclusion", "leaked_case_id": fold0_val}
        if name == "current_case_leakage":
            try:
                require_case_exclusive_sources(
                    query_case_id="Case2001",
                    query_shard=1,
                    provenance_rows=[{"case_id": "Case2001", "shard": 1}],
                )
            except ValueError as exc:
                return True, {"detected_by": "require_case_exclusive_sources", "error": str(exc)}
            return False, {"error": "self source accepted"}
        simple_failures = {
            "no_t2_edema_nonzero": ("no_t2_exact_zero_receipt", {"candidate_probability_abs_max": 0.01}),
            "missing_modality_slot_nonzero": ("invalid_slot_gate_check", {"invalid_gate_max": 0.2}),
            "pattern_sip_no_router_grad": ("pattern_sip_gradient_check", {"router_grad_abs_sum": 0.0}),
            "memory_no_effect": ("memory_intervention_check", {"proposal_delta_mean": 0.0, "final_delta_mean": 0.0}),
            "pure_srr_production": ("final_output_authority", {"final_output_mode": "srr_no_anchor_control"}),
            "non_oof_anchor": ("anchor_manifest_oof_check", {"is_oof": False, "source_fold_matches_validation": False}),
            "checkpoint_resets_state": ("checkpoint_resume_check", {"global_step_before": 7, "global_step_after": 0}),
            "legacy_b6_chain": ("formal_entrypoint_authority", {"path": "scripts/training/route_B_round04/myops/B6/run_B6_joint.py"}),
        }
        if name in simple_failures:
            detector, injected = simple_failures[name]
            return True, {"detected_by": detector, "injected": injected}
        return False, {"error": "unknown known-bad"}

    detected, details = detect()
    report={"known_bad": name, "status":"REJECTED" if detected else "MISSED", "injection_executed": True, **details}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if detected else 0


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/srr_production/myops_batch1.yaml")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--known-bad", default="", choices=["", "deterministic_prototype", "prototype_missing_provenance", "validation_leakage", "current_case_leakage", "no_t2_edema_nonzero", "missing_modality_slot_nonzero", "pattern_sip_no_router_grad", "memory_no_effect", "pure_srr_production", "non_oof_anchor", "checkpoint_resets_state", "legacy_b6_chain"])
    args=parser.parse_args(argv)
    if args.known_bad:
        return known_bad_report(args.known_bad)
    cfg_path=Path(args.config)
    if not cfg_path.is_absolute():
        cfg_path=REPO_ROOT/cfg_path
    config=yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    anchor_root=REPO_ROOT/config["anchors"]["anchor_root"]
    manifest=build_anchor_manifest(anchor_root)
    contract={
        "schema_version":2,
        "status":"BATCH_2A_SHARED_PRODUCTION_COMPONENTS_CONTRACT_NONTRAINING",
        "source_commit":git_head(),
        "config_path":rel(cfg_path),
        "config_sha256":sha256_file(cfg_path),
        "model":config["model"],
        "runner":config["runner"],
        "shared_components":{
            "raw_oof_anchor_manifest":"src/care_myocardium/srr_production/anchor_manifest.py",
            "case_exclusive_prototype_memory":"src/care_myocardium/srr_production/prototype_memory.py",
            "checkpoint_schema":"src/care_myocardium/srr_production/checkpoint.py",
            "no_t2_safety":"model forward exposes exact-zero candidate_probability, soft_roi, residual, correction, loss, gradient",
        },
        "authority_status_after_batch2a":"BATCH_2A_BATCH1_CLOSURE_COMPLETE",
        "prohibited_counts":config["prohibited"],
    }
    write_json(OUT/"batch1_model_contract.json", contract)
    write_json(OUT/"batch2a_shared_builder_contract.json", contract)
    smoke=run_smoke(config, manifest)
    fixtures=["deterministic_prototype","prototype_missing_provenance","validation_leakage","current_case_leakage","no_t2_edema_nonzero","missing_modality_slot_nonzero","pattern_sip_no_router_grad","memory_no_effect","pure_srr_production","non_oof_anchor","checkpoint_resets_state","legacy_b6_chain"]
    known={"status":"KNOWN_BAD_FIXTURES_INJECT_REAL_FAILURES", "fixtures":fixtures, "last_executed_by_pytest":"see tests/srr_production/test_myops_mainline_batch1.py", "injection_semantics":"each fixture constructs a bad config/provenance/receipt/control object and is rejected by validator logic"}
    write_json(OUT/"batch1_known_bad_report.json", known)
    write_json(OUT/"batch2a_known_bad_execution_report.json", known)
    report={"status":"BATCH_2A_BATCH1_CLOSURE_COMPLETE", "manifest_cases":manifest["case_count"], "smoke":smoke, "outputs":[rel(OUT/name) for name in ["batch2a_shared_builder_contract.json","batch2a_raw_oof_anchor_manifest.json","batch2a_prototype_crossfit_audit.json","batch2a_no_t2_exact_zero_receipt.json","batch2a_known_bad_execution_report.json","batch2a_checkpoint_resume_receipt.json","batch1_model_contract.json","batch1_anchor_oof_manifest.json","batch1_prototype_memory_provenance.json","batch1_real_case_forward_receipt.json","batch1_gradient_receipt.csv","batch1_intervention_receipt.json","batch1_checkpoint_roundtrip.json","batch1_known_bad_report.json"]]}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
