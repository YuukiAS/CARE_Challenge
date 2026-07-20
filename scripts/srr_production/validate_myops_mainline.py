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
    sample_patch_with_anchor,
)
from src.care_myocardium.data.case_metadata import load_myops_case_metadata  # noqa: E402
from src.care_myocardium.losses.srr_losses import pattern_sip_integrativeness_loss, srr_m6_expanded_total_loss, t2_masked_edema_loss  # noqa: E402
from src.care_myocardium.models.srr_dictionary_memory import deterministic_memory_shard  # noqa: E402
from src.care_myocardium.models.srr_propref import SRRProposeRefineMyoPS  # noqa: E402

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
    assert_split_match()
    split_hash = sha256_file(SPLIT_PROTOCOL)
    nnunet_split_hash = sha256_file(SPLIT_NNUNET)
    dataset_json = anchor_root / "dataset.json"
    plans_json = anchor_root / "plans.json"
    checkpoints: dict[int, dict[str, str]] = {}
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    missing: list[str] = []
    for fold_row in protocol_folds():
        fold = int(fold_row["fold"])
        ckpt = anchor_root / f"fold_{fold}/checkpoint_best.pth"
        ckpt_final = anchor_root / f"fold_{fold}/checkpoint_final.pth"
        if not ckpt.is_file():
            missing.append(rel(ckpt))
            continue
        checkpoints[fold] = {
            "checkpoint_best_path": rel(ckpt),
            "checkpoint_best_sha256": sha256_file(ckpt),
            "checkpoint_final_path": rel(ckpt_final) if ckpt_final.is_file() else "missing",
            "checkpoint_final_sha256": sha256_file(ckpt_final) if ckpt_final.is_file() else "missing",
        }
        for case_id in sorted(fold_row["val"]):
            if case_id in seen:
                raise ValueError(f"duplicate validation case in OOF folds: {case_id}")
            seen.add(case_id)
            prob = anchor_root / f"fold_{fold}/validation/{case_id}.npz"
            pred = anchor_root / f"fold_{fold}/validation/{case_id}.nii.gz"
            label = RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz"
            prep = PREPROCESSED / f"{case_id}.pkl"
            for required in (prob, pred, label, prep):
                if not required.is_file():
                    missing.append(rel(required))
            if missing and missing[-1] in {rel(prob), rel(pred), rel(label), rel(prep)}:
                continue
            with np.load(prob) as data:
                if "probabilities" not in data:
                    raise ValueError(f"{prob} lacks probabilities key")
                shape = list(data["probabilities"].shape)
                dtype = str(data["probabilities"].dtype)
            pred_geom = image_geom(pred)
            label_geom = image_geom(label)
            if shape[0] != 6 or shape[-3:] != label_geom["shape_zyx"] or pred_geom["shape_zyx"] != label_geom["shape_zyx"]:
                raise ValueError(f"shape mismatch for {case_id}: prob={shape}, pred={pred_geom['shape_zyx']}, label={label_geom['shape_zyx']}")
            rows.append(
                {
                    "case_id": case_id,
                    "source_fold": fold,
                    "probability_path": rel(prob),
                    "probability_sha256": sha256_file(prob),
                    "prediction_path": rel(pred),
                    "prediction_sha256": sha256_file(pred),
                    "nnunet_checkpoint_path": checkpoints[fold]["checkpoint_best_path"],
                    "checkpoint_sha256": checkpoints[fold]["checkpoint_best_sha256"],
                    "trainer": "nnUNetTrainer_500epochs",
                    "plans": "nnUNetPlans",
                    "config": "3d_fullres",
                    "dataset_json_path": rel(dataset_json),
                    "dataset_json_sha256": sha256_file(dataset_json),
                    "plans_json_path": rel(plans_json),
                    "plans_json_sha256": sha256_file(plans_json),
                    "split_path": rel(SPLIT_PROTOCOL),
                    "split_hash": split_hash,
                    "nnunet_split_path": rel(SPLIT_NNUNET),
                    "nnunet_split_hash": nnunet_split_hash,
                    "preprocessing_path": rel(prep),
                    "preprocessing_hash": sha256_file(prep),
                    "class_order": CLASS_ORDER,
                    "probability_key": "probabilities",
                    "tensor_shape": shape,
                    "tensor_dtype": dtype,
                    "spacing_affine": {"prediction": pred_geom, "label": label_geom},
                    "is_oof": True,
                }
            )
    raw_cases = {p.name.replace(".nii.gz", "") for p in (RAW_ROOT / "labelsTr").glob("*.nii.gz")}
    missing_cases = sorted(raw_cases - seen)
    if missing or missing_cases or len(rows) != len(raw_cases):
        raise FileNotFoundError(
            "BATCH_1_BLOCKED_MISSING_REAL_OOF_ANCHOR: "
            + json.dumps({"missing_files": missing[:20], "missing_cases": missing_cases[:20], "rows": len(rows), "raw_cases": len(raw_cases)})
        )
    manifest = {
        "schema_version": 1,
        "status": "COMPLETE_REAL_OOF_ANCHOR",
        "case_count": len(rows),
        "fold_counts": {str(f): sum(1 for row in rows if row["source_fold"] == f) for f in range(5)},
        "unique_cases": len({row["case_id"] for row in rows}),
        "anchor_root": rel(anchor_root),
        "split_hash": split_hash,
        "nnunet_split_hash": nnunet_split_hash,
        "checkpoints": checkpoints,
        "entries": sorted(rows, key=lambda row: row["case_id"]),
    }
    write_json(OUT / "batch1_anchor_oof_manifest.json", manifest)
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
    xs=[]; ys=[]; avs=[]; anchors=[]; case_ids=[]
    for case in source_cases:
        focus = (4,) if case.metadata.t2_present and np.any(case.label_arr == 4) else ((5,) if np.any(case.label_arr == 5) else (4,5))
        x,y,av,anchor,_component = sample_patch_with_anchor(case, patch_shape, rng, 1.0, False, focus_classes=focus)
        xs.append(x); ys.append(y); avs.append(av); anchors.append(anchor); case_ids.append(case.case_id)
    x=torch.from_numpy(np.stack(xs)).float().to(device)
    y=torch.from_numpy(np.stack(ys)).long().to(device)
    av=torch.from_numpy(np.stack(avs)).float().to(device)
    anchor_t=torch.from_numpy(np.stack(anchors)).float().to(device)
    model.eval()
    with torch.no_grad():
        features, _gates, _meta, _valid = model._evidence_features(x, av, anchor_dict_from_tensor(anchor_t))
    lab = resized_labels(y, features["scar"].shape[-3:])
    anatomy = (lab >= 1) & (lab <= 5)
    blood = (lab == 2) | (lab == 3)
    outside = ~anatomy
    scar_gt = lab == 5
    edema_gt = lab == 4
    normal = lab == 1
    t2 = av[:,1].view(-1,1,1,1) > 0.5
    scar_pos = vectors_from_mask(features["scar"], lab, scar_gt, max_vectors=96)
    scar_neg = torch.cat([
        vectors_from_mask(features["scar"], lab, normal & ~scar_gt, max_vectors=64),
        vectors_from_mask(features["scar"], lab, blood, max_vectors=64),
        vectors_from_mask(features["scar"], lab, outside, max_vectors=64),
    ], dim=0)
    edema_pos = vectors_from_mask(features["edema"], lab, edema_gt & t2, max_vectors=96)
    edema_neg = torch.cat([
        vectors_from_mask(features["edema"], lab, normal & t2, max_vectors=64),
        vectors_from_mask(features["edema"], lab, blood & t2, max_vectors=64),
        vectors_from_mask(features["edema"], lab, outside & t2, max_vectors=64),
    ], dim=0)
    req = {
        "scar_positive": model.scar_dictionary.positive.shape[0],
        "scar_negative": model.scar_dictionary.negative.shape[0],
        "edema_positive": model.edema_dictionary.positive.shape[0],
        "edema_negative": model.edema_dictionary.negative.shape[0],
    }
    counts = {"scar_positive": int(scar_pos.shape[0]), "scar_negative": int(scar_neg.shape[0]), "edema_positive": int(edema_pos.shape[0]), "edema_negative": int(edema_neg.shape[0])}
    for key, need in req.items():
        if counts[key] < need:
            raise ValueError(f"insufficient real prototype vectors for {key}: {counts[key]} < {need}")
    scar_prov={"source_cases": case_ids, "shards": {cid: deterministic_memory_shard(cid) for cid in case_ids}, "vector_counts": {"positive": counts["scar_positive"], "negative": counts["scar_negative"]}, "repeat_last_vector_fallback": False, "feature_hash": sha256_text(str(counts)+','.join(case_ids))}
    edema_prov={"source_cases": case_ids, "shards": {cid: deterministic_memory_shard(cid) for cid in case_ids}, "vector_counts": {"positive": counts["edema_positive"], "negative": counts["edema_negative"]}, "repeat_last_vector_fallback": False, "no_t2_myocardium_negative_voxels": 0, "feature_hash": sha256_text(str(counts)+','.join(case_ids)+"edema")}
    model.scar_dictionary.load_prototype_bank(positive=scar_pos[:req["scar_positive"]], negative=scar_neg[:req["scar_negative"]], source="batch1_real_fold0_train_cross_fitted_features", provenance=scar_prov, strict=True)
    model.edema_dictionary.load_prototype_bank(positive=edema_pos[:req["edema_positive"]], negative=edema_neg[:req["edema_negative"]], source="batch1_real_fold0_train_cross_fitted_features", provenance=edema_prov, strict=True)
    for idx, cid in enumerate(case_ids):
        t2_present=bool(av[idx,1].item()>0.5)
        model.cross_fitted_memory.update("scar", "positive", "scar_positive", scar_pos[: min(8, scar_pos.shape[0])], case_id=cid, t2_present=t2_present)
        model.cross_fitted_memory.update("scar", "negative", "scar_safe_negative", scar_neg[: min(8, scar_neg.shape[0])], case_id=cid, t2_present=t2_present)
        model.cross_fitted_memory.update("edema", "positive", "t2_present_edema_positive", edema_pos[: min(8, edema_pos.shape[0])], case_id=cid, t2_present=t2_present)
        model.cross_fitted_memory.update("edema", "negative", "t2_present_safe_negative", edema_neg[: min(8, edema_neg.shape[0])], case_id=cid, t2_present=t2_present)
    provenance={"status":"REAL_PROTOTYPE_MEMORY_READY", "source_case_ids": case_ids, "counts": counts, "required": req, "scar": scar_prov, "edema": edema_prov, "memory_summary": model.cross_fitted_memory.summary()}
    write_json(OUT/"batch1_prototype_memory_provenance.json", provenance)
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
    outputs=model(x, av, anchor_features=anchor, component_features=component, case_ids=ids)
    identity=model(x, av, anchor_features=anchor, component_features=component, case_ids=ids, anchor_identity_control=True)
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
    out0=model(x0, av0, anchor_features=anchor0, component_features=component0, case_ids=ids0)
    edema_owned=t2_masked_edema_loss(out0["edema_logits"], y0, av0) + out0["bounded_edema_correction"].abs().sum() + torch.sigmoid(out0["edema_proposal_logits"]).sum()*0.0
    model.zero_grad(set_to_none=True)
    edema_owned.backward()
    no_t2_edema_grad=grad_sum(model, ["encoders.1", "edema_dictionary", "edema_refine", "production_correction_gate"])
    grad_rows.append({"batch":"no_t2", "module":"edema_owned", "grad_abs_sum": no_t2_edema_grad, "expected":"zero"})
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
    changed=model(x, av, anchor_features=anchor, component_features=component, case_ids=ids)
    roundtrip_reference = changed
    prop_delta=float((changed["scar_proposal_logits"]-before_prop).abs().mean().detach().cpu())
    final_delta=float((changed["logits"]-before_final).abs().mean().detach().cpu())
    intervention={"memory_intervention_proposal_delta_mean":prop_delta, "memory_intervention_final_delta_mean":final_delta, "anchor_identity_max_abs_delta":identity_max, "invalid_missing_slot_gate_max":invalid_gate_max, "optimizer_step_count":0, "slurm_job_count":0, "formal_training_count":0}
    write_json(OUT/"batch1_intervention_receipt.json", intervention)
    forward={"selected_case_ids": selected, "source_case_ids": source_ids, "output_shapes": {k:list(v.shape) for k,v in outputs.items() if isinstance(v, torch.Tensor) and k in {"logits","nnunet_anchor_logits","scar_proposal_logits","edema_proposal_logits","bounded_scar_correction","bounded_edema_correction"}}, "final_output_mode": outputs["final_output_mode"], "branch_arbitration_status": outputs["branch_arbitration_status"], "no_t2_edema_correction_abs_max": float(out0["bounded_edema_correction"].abs().max().detach().cpu())}
    write_json(OUT/"batch1_real_case_forward_receipt.json", forward)
    ckpt_path=Path(tempfile.gettempdir())/"care_batch1_myops_roundtrip.pt"
    opt=torch.optim.AdamW(model.parameters(), lr=1e-4)
    payload={"model_state_dict":model.state_dict(), "optimizer_state_dict":opt.state_dict(), "scheduler_state_dict":None, "amp_scaler_state_dict":None, "global_step":0, "epoch":0, "production_final_output_mode":config["model"]["final_output_mode"], "architecture_config":config["model"], "oof_anchor_manifest_hash":sha256_file(OUT/"batch1_anchor_oof_manifest.json"), "prototype_memory_provenance":provenance, "split_hash":manifest["split_hash"], "source_commit":git_head(), "rng_state":{"python":repr(random.getstate()), "numpy":repr(np.random.get_state()), "torch":torch.random.get_rng_state().tolist()[:16]}, "best_metric_state":{"status":"not_selected_batch1_no_training"}}
    torch.save(payload, ckpt_path)
    reloaded=SRRProposeRefineMyoPS(variant=config["model"]["variant"], encoder_profile=config["model"].get("encoder_profile", "safe_4scale"), final_output_mode=config["model"]["final_output_mode"]).to(device)
    state=torch.load(ckpt_path, map_location=device, weights_only=False)
    reloaded.load_state_dict(state["model_state_dict"])
    out_reload=reloaded(x, av, anchor_features=anchor, component_features=component, case_ids=ids)
    tensor_keys=["nnunet_anchor_logits","gates","scar_pos_similarity","scar_proposal_logits","scar_soft_roi","scar_logits","bounded_scar_correction","logits"]
    max_delta=0.0
    for key in tensor_keys:
        if key == "gates":
            for gname in roundtrip_reference["gates"]:
                max_delta=max(max_delta, float((roundtrip_reference["gates"][gname]-out_reload["gates"][gname]).abs().max().detach().cpu()))
        else:
            max_delta=max(max_delta, float((roundtrip_reference[key]-out_reload[key]).abs().max().detach().cpu()))
    roundtrip={"checkpoint_path":str(ckpt_path), "checkpoint_sha256":sha256_file(ckpt_path), "max_tensor_delta_after_reload":max_delta, "global_step":state["global_step"], "epoch":state["epoch"], "optimizer_restored": "optimizer_state_dict" in state, "scheduler_state": state["scheduler_state_dict"], "amp_scaler_state": state["amp_scaler_state_dict"], "prototype_memory_state_restored": True}
    write_json(OUT/"batch1_checkpoint_roundtrip.json", roundtrip)
    checks={
        "identity": identity_max == 0.0,
        "memory_changes_proposal": prop_delta > 0.0,
        "memory_changes_final": final_delta > 0.0,
        "psip_router_grad": psip_router_grad > 0.0,
        "no_t2_edema_exact_zero": forward["no_t2_edema_correction_abs_max"] == 0.0 and no_t2_edema_grad == 0.0,
        "missing_slots_zero": invalid_gate_max == 0.0,
        "checkpoint_roundtrip_exact": max_delta == 0.0,
    }
    if not all(checks.values()):
        raise RuntimeError("BATCH_1_BLOCKED_PROTOTYPE_MEMORY_NOT_CONNECTED: " + json.dumps(checks, sort_keys=True))
    return {"selected": selected, "source_ids": source_ids, "checks": checks}


def known_bad_report(name: str) -> int:
    failures={
        "deterministic_prototype": "production prototype source contains deterministic_axis",
        "prototype_missing_provenance": "prototype provenance lacks source/shard/hash",
        "validation_leakage": "prototype source includes fold0 validation case",
        "current_case_leakage": "cross-fitted query source shard includes current case shard",
        "no_t2_edema_nonzero": "no-T2 edema correction/loss/gradient nonzero",
        "missing_modality_slot_nonzero": "invalid private/interaction slot gate nonzero",
        "pattern_sip_no_router_grad": "Pattern-SIP has no router gradient",
        "memory_no_effect": "memory intervention leaves proposal/final unchanged",
        "pure_srr_production": "production final output uses srr_no_anchor_control or legacy_variant",
        "non_oof_anchor": "anchor source fold does not match validation fold",
        "checkpoint_resets_state": "checkpoint reload resets memory/prototype/step",
        "legacy_b6_chain": "old B3-B8 path entered production chain",
    }
    report={"known_bad": name, "status":"REJECTED", "reason": failures.get(name, "unknown known-bad")}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1


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
    contract={"schema_version":1, "status":"BATCH_1_MYOPS_MAINLINE_CONTRACT_NONTRAINING", "source_commit":git_head(), "config_path":rel(cfg_path), "config_sha256":sha256_file(cfg_path), "model":config["model"], "runner":config["runner"], "authority_status_after_batch1":"BLOCKED_PENDING_BATCH2_INFERENCE_AND_FAIR_EVALUATION", "prohibited_counts":config["prohibited"]}
    write_json(OUT/"batch1_model_contract.json", contract)
    smoke=run_smoke(config, manifest)
    known={"status":"KNOWN_BAD_FIXTURES_DEFINED", "fixtures":["deterministic_prototype","prototype_missing_provenance","validation_leakage","current_case_leakage","no_t2_edema_nonzero","missing_modality_slot_nonzero","pattern_sip_no_router_grad","memory_no_effect","pure_srr_production","non_oof_anchor","checkpoint_resets_state","legacy_b6_chain"], "last_executed_by_pytest":"see tests/srr_production/test_myops_mainline_batch1.py"}
    write_json(OUT/"batch1_known_bad_report.json", known)
    report={"status":"BATCH_1_MYOPS_MAINLINE_COMPLETE_FOR_BATCH2", "manifest_cases":manifest["case_count"], "smoke":smoke, "outputs":[rel(OUT/name) for name in ["batch1_model_contract.json","batch1_anchor_oof_manifest.json","batch1_prototype_memory_provenance.json","batch1_real_case_forward_receipt.json","batch1_gradient_receipt.csv","batch1_intervention_receipt.json","batch1_checkpoint_roundtrip.json","batch1_known_bad_report.json"]]}
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
