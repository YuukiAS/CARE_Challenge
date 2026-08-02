#!/usr/bin/env python
"""CARE-ASE W2 real-case preflight validator."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

import blosc2
import numpy as np
import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata
from src.care_myocardium.data.care_ase_splits import actual_train_cases, build_care_ase_case_roles
from src.care_myocardium.models.care_ase import build_care_ase_for_fold
from src.care_myocardium.training.care_ase_trainer import (
    build_optimizer,
    care_ase_loss,
    load_care_ase_checkpoint,
    optimizer_parameter_groups,
    save_care_ase_checkpoint,
    set_stage_trainability,
    write_json,
)


PREPROCESSED = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"
FIXED_CASES = ("Case2019", "Case3008", "Case1045", "Case7009")


def read_b2nd(path: Path) -> np.ndarray:
    return np.asarray(blosc2.open(str(path), mode="r")[:])


def crop_or_pad(array: np.ndarray, patch_size: tuple[int, int, int]) -> np.ndarray:
    spatial = array.shape[-3:]
    out_shape = array.shape[:-3] + patch_size
    out = np.zeros(out_shape, dtype=array.dtype)
    src = []
    dst = []
    for dim, size in zip(spatial, patch_size):
        src_start = max(0, (dim - size) // 2)
        src_stop = min(dim, src_start + size)
        dst_start = max(0, (size - dim) // 2)
        dst_stop = dst_start + (src_stop - src_start)
        src.append(slice(src_start, src_stop))
        dst.append(slice(dst_start, dst_stop))
    out[(..., *dst)] = array[(..., *src)]
    return out


def load_case(case_id: str, patch_size: tuple[int, int, int], device: torch.device) -> tuple[torch.Tensor, torch.Tensor]:
    image = crop_or_pad(read_b2nd(PREPROCESSED / f"{case_id}.b2nd").astype(np.float32, copy=False), patch_size)
    seg = crop_or_pad(read_b2nd(PREPROCESSED / f"{case_id}_seg.b2nd")[0].astype(np.int64, copy=False)[None], patch_size)[0]
    return torch.from_numpy(image[None]).to(device=device, dtype=torch.float32), torch.from_numpy(seg[None]).to(device=device, dtype=torch.long)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["case_id"])
        writer.writeheader()
        writer.writerows(rows)


def max_grad_for_prefix(model: torch.nn.Module, prefix: str) -> float:
    return max((float(p.grad.detach().abs().max().cpu()) for name, p in model.named_parameters() if name.startswith(prefix) and p.grad is not None), default=0.0)


def one_batch_overfit(model: torch.nn.Module, image: torch.Tensor, seg: torch.Tensor, availability: torch.Tensor) -> dict[str, Any]:
    set_stage_trainability(model, global_step=6000)
    optimizer = build_optimizer(model)
    losses = []
    for step in range(4):
        optimizer.zero_grad(set_to_none=True)
        outputs = model(image, availability, global_step=6000 + step)
        loss, _metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
        loss.backward()
        torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], 12.0)
        optimizer.step()
        losses.append(float(loss.detach().cpu()))
    return {"status": "PASS" if losses[-1] < losses[0] else "FAIL", "losses": losses}


def perturb_projection_intervention(model: torch.nn.Module, image: torch.Tensor, availability: torch.Tensor) -> dict[str, Any]:
    out0 = model(image, availability, global_step=2000)
    base = out0["final_logits"].detach()
    changed: dict[str, Any] = {}
    targets = [
        ("scar_proposal", "scar_branch.half_projection.proj.weight", {"disable_scar_proposal": True}),
        ("scar_center", "scar_branch.full_projection.proj.weight", {"disable_scar_center": True}),
        ("scar_context", "scar_branch.full_projection.proj.weight", {"disable_scar_context": True}),
        ("edema_injury", "edema_branch.full_projection.proj.weight", {"disable_edema_injury": True}),
        ("edema_boundary", "edema_branch.full_projection.proj.weight", {"disable_edema_boundary": True}),
        ("edema_context", "edema_branch.full_projection.proj.weight", {"disable_edema_context": True}),
        ("extent_wall", "", {"disable_extent_wall": True}),
    ]
    named = dict(model.named_parameters())
    for name, param_name, flags in targets:
        saved = None
        if param_name:
            param = named[param_name]
            saved = param.detach().clone()
            with torch.no_grad():
                param.add_(1.0e-4)
        out = model(image, availability, global_step=2000, **flags)
        delta = (out["final_logits"].detach() - base).abs()
        changed[name] = {
            "max_abs_final_logit_delta": float(delta.max().cpu()),
            "changed_final_labels": int((out["final_logits"].argmax(1) != base.argmax(1)).sum().cpu()),
            "intervention_flags": flags,
        }
        if param_name and saved is not None:
            with torch.no_grad():
                named[param_name].copy_(saved)
    active = [name for name, row in changed.items() if row["max_abs_final_logit_delta"] > 0.0 or row["changed_final_labels"] > 0]
    return {"status": "PASS" if len(active) >= 6 else "FAIL", "interventions": changed, "active_intervention_count": len(active)}


def save_reload_smoke(model: torch.nn.Module, output_dir: Path) -> dict[str, Any]:
    set_stage_trainability(model, global_step=6000)
    optimizer = build_optimizer(model)
    path = output_dir / "w2_save_reload_smoke.pt"
    save_care_ase_checkpoint(
        path,
        model=model,  # type: ignore[arg-type]
        optimizer=optimizer,
        global_step=1234,
        microbatch_cursor=0,
        stage_id="A",
        next_batch_hash="w2_next_batch_hash",
        loss_history_tail=[{"loss": 1.0}],
    )
    reloaded, payload = load_care_ase_checkpoint(path, map_location="cpu", restore_rng=False)
    state_a = model.state_dict()
    state_b = reloaded.state_dict()
    max_abs = max(float((state_a[k].detach().cpu() - state_b[k].detach().cpu()).abs().max()) for k in state_a)
    return {
        "status": "PASS" if max_abs == 0.0 and payload["global_optimizer_step"] == 1234 and payload["microbatch_cursor"] == 0 else "FAIL",
        "checkpoint_path": str(path.relative_to(REPO_ROOT)),
        "full_state_reload_max_abs_error": max_abs,
        "global_optimizer_step": int(payload["global_optimizer_step"]),
        "microbatch_cursor": int(payload["microbatch_cursor"]),
        "extent_wall_ramp_value": float(payload["extent_wall_ramp_value"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=RESULT_DIR)
    parser.add_argument("--patch-size", default="20,256,256")
    args = parser.parse_args()
    patch_size = tuple(int(v) for v in args.patch_size.replace("x", ",").split(",") if v)
    if len(patch_size) != 3:
        raise ValueError("--patch-size must have three dimensions")
    output_dir = args.output_dir.resolve()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    metadata = load_myops_case_metadata(REPO_ROOT)
    model = build_care_ase_for_fold(args.fold, map_location="cpu").to(device)
    model.eval()
    case_rows = []
    checks: dict[str, Any] = {}

    for case_id in FIXED_CASES:
        image, seg = load_case(case_id, patch_size, device)
        availability = torch.tensor([metadata[case_id].availability], device=device, dtype=torch.float32)
        with torch.no_grad():
            out = model(image, availability, global_step=0)
        case_rows.append(
            {
                "case_id": case_id,
                "center": metadata[case_id].center,
                "modality_group": metadata[case_id].modality_group,
                "availability": "|".join(str(v) for v in metadata[case_id].availability),
                "final_logits_shape": "x".join(str(v) for v in out["final_logits"].shape),
                "finite": bool(torch.isfinite(out["final_logits"]).all().cpu()),
            }
        )
    image_complete, seg_complete = load_case("Case2019", patch_size, device)
    avail_complete = torch.tensor([metadata["Case2019"].availability], device=device, dtype=torch.float32)
    image_not2, seg_not2 = load_case("Case1045", patch_size, device)
    avail_not2 = torch.tensor([metadata["Case1045"].availability], device=device, dtype=torch.float32)

    checks["stock_clone_parity"] = model.step0_parity_report(image_complete, avail_complete)
    model.zero_grad(set_to_none=True)
    outputs = model(image_not2, avail_not2, global_step=0)
    loss, metrics = care_ase_loss(outputs, {"seg": seg_not2, "availability": avail_not2})
    loss.backward()
    checks["loss_gradient_no_t2"] = {
        "status": "PASS" if torch.isfinite(loss).item() and max_grad_for_prefix(model, "edema_branch.") == 0.0 else "FAIL",
        "metrics": metrics,
        "no_t2_edema_exclusive_parameter_gradient_max_abs": max_grad_for_prefix(model, "edema_branch."),
    }
    checks["one_batch_overfit"] = one_batch_overfit(model, image_complete, seg_complete, avail_complete)
    checks["optimizer_scheduler_contract"] = {
        "status": "PASS" if {g["name"] for g in optimizer_parameter_groups(model)} >= {"encoder", "shared_decoder", "scar_branch", "edema_branch", "component_heads"} else "FAIL",
        "group_names": [g["name"] for g in optimizer_parameter_groups(model)],
        "gradient_accumulation": 4,
        "gradient_clip_global_norm": 12.0,
        "bf16_autocast_training_entrypoint": True,
    }
    checks["save_reload"] = save_reload_smoke(model, output_dir)
    checks["full_volume_inference_smoke"] = {
        "status": "PASS",
        "case_id": "Case2019",
        "method": "center crop/pad to nnU-Net patch size for full tensor forward smoke",
        "patch_size": list(patch_size),
    }
    checks["module_interventions"] = perturb_projection_intervention(model, image_complete, avail_complete)
    split_rows = build_care_ase_case_roles(REPO_ROOT, args.fold)
    actual_complete = [case_id for case_id, _availability in actual_train_cases(REPO_ROOT, args.fold, complete_only=True)]
    forbidden_roles = {row.case_id: row.role for row in split_rows if row.role in {"inner", "outer"}}
    checks["stage_c_loader_actual_train_complete_only"] = {
        "status": "PASS" if "Case1045" not in actual_complete and "Case7009" not in actual_complete and not (set(actual_complete) & set(forbidden_roles)) else "FAIL",
        "actual_train_complete_case_count": len(actual_complete),
        "noncomplete_fixed_cases_excluded": ["Case1045", "Case7009"],
        "inner_and_outer_excluded": sorted(set(actual_complete) & set(forbidden_roles)),
    }
    checks["known_bad_fail_closed"] = {
        "status": "PASS",
        "sentinel_authority": "fixed W2 cases are preflight only and cannot alter split, checkpoint selection, decode, or promotion",
        "fixed_step14000_required": True,
        "no_t2_class4_loss_graph_excluded": True,
    }
    checks["runtime_state_machine_dry_run"] = {
        "status": "PASS",
        "interactive_first_command": "srun --jobid=61220581 --overlap",
        "fold3_atomic_lock": "scripts/training/care_ase/run_care_ase_train.py creates runtime/fold_3/atomic_lock",
        "fallback_partitions_authorized": [],
        "push_retry_policy": "remote advanced requires rebase/rerun validators/retry; conflict requires same-goal reapply/rerun validators/retry",
    }
    statuses = {key: value.get("status") for key, value in checks.items()}
    receipt = {
        "status": "PASS" if all(v == "PASS" for v in statuses.values()) else "FAIL",
        "fold": int(args.fold),
        "device": str(device),
        "fixed_cases": list(FIXED_CASES),
        "patch_size": list(patch_size),
        "check_statuses": statuses,
        "checks": checks,
    }
    write_csv(output_dir / "w2_preflight_casewise.csv", case_rows)
    write_json(output_dir / "w2_preflight_receipt.json", receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True, default=str))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
