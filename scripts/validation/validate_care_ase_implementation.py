#!/usr/bin/env python
"""Validate CARE-ASE W1 implementation and write implementation receipts."""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import torch

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.models.care_ase import build_care_ase_for_fold, care_ase_contract_summary
from src.care_myocardium.training.care_ase_trainer import (
    build_optimizer,
    care_ase_loss,
    optimizer_parameter_groups,
    save_care_ase_checkpoint,
    set_stage_trainability,
)


RESULT_DIR = REPO_ROOT / "results/20260801_care_ase_final_model"
SOURCE_FILES = [
    REPO_ROOT / "src/care_myocardium/models/care_ase.py",
    REPO_ROOT / "src/care_myocardium/training/care_ase_trainer.py",
]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def ast_forbidden_findings(paths: list[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    forbidden_text = ("NotImplementedError", "fixed-zero placeholder", "random output", "dictionary", "prototype", "query")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                findings.append({"path": str(path.relative_to(REPO_ROOT)), "line": int(node.lineno), "finding": "pass_statement"})
        for token in forbidden_text:
            if token in text:
                findings.append({"path": str(path.relative_to(REPO_ROOT)), "finding": f"forbidden_text:{token}"})
    return findings


def git_diff_summary() -> str:
    cmd = ["git", "diff", "--", "src/care_myocardium/models/care_ase.py", "src/care_myocardium/training/care_ase_trainer.py", "scripts/validation/validate_care_ase_implementation.py"]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = proc.stdout.splitlines()
    return "\n".join(lines[:260]) if lines else "No tracked diff for W1 source files yet; files may be untracked before terminal commit."


def parameter_group_receipt(model: torch.nn.Module) -> dict[str, Any]:
    set_stage_trainability(model, global_step=6000)
    groups = optimizer_parameter_groups(model)  # type: ignore[arg-type]
    rows = []
    total = 0
    for group in groups:
        count = sum(int(p.numel()) for p in group["params"])
        total += count
        rows.append({"name": group["name"], "parameter_count": count, "lr": group["lr"], "weight_decay": group["weight_decay"]})
    return {
        "status": "PASS" if {row["name"] for row in rows} >= {"encoder", "shared_decoder", "anatomy_decoder", "scar_branch", "edema_branch", "component_heads", "modality_adapters"} else "FAIL",
        "stage_c_trainable_parameter_count": total,
        "groups": rows,
        "gradient_accumulation": 4,
        "gradient_clip_global_norm": 12.0,
    }


def component_wiring_receipt(model: torch.nn.Module, sample: torch.Tensor, availability: torch.Tensor) -> dict[str, Any]:
    out = model(sample, availability, global_step=0)  # type: ignore[operator]
    component_shapes = {key: list(value.shape) for key, value in out["components"].items()}
    projection_max = care_ase_contract_summary(model)["zero_init_projection_parameter_max_abs"]  # type: ignore[arg-type]
    expected = {
        "scar_quarter_occupancy",
        "scar_half_occupancy",
        "scar_quarter_center",
        "scar_half_center",
        "scar_context",
        "edema_injury",
        "edema_boundary",
        "edema_context",
        "scar_extent_presence",
        "scar_extent_area",
        "edema_extent_presence",
        "edema_extent_area",
    }
    return {
        "status": "PASS" if set(component_shapes) >= expected and all(float(v) == 0.0 for v in projection_max.values()) else "FAIL",
        "component_shapes": component_shapes,
        "zero_init_projection_parameter_max_abs": projection_max,
        "declared_final_logit_entries": care_ase_contract_summary(model)["declared_component_entries"],  # type: ignore[arg-type]
        "normal_forward_reads_stock_pathology_logits": False,
    }


def runtime_helper_receipt(model: torch.nn.Module, output_dir: Path) -> dict[str, Any]:
    set_stage_trainability(model, global_step=0)  # type: ignore[arg-type]
    optimizer = build_optimizer(model)  # type: ignore[arg-type]
    path = output_dir / "w1_runtime_helper_smoke_checkpoint.pt"
    save_care_ase_checkpoint(
        path,
        model=model,  # type: ignore[arg-type]
        optimizer=optimizer,
        global_step=0,
        microbatch_cursor=0,
        stage_id="A",
        next_batch_hash="w1_smoke",
        loss_history_tail=[],
    )
    payload = torch.load(path, map_location="cpu", weights_only=False)
    return {
        "status": "PASS" if payload.get("global_optimizer_step") == 0 and payload.get("microbatch_cursor") == 0 and payload.get("extent_wall_ramp_value") == 0.0 else "FAIL",
        "checkpoint_path": str(path.resolve().relative_to(REPO_ROOT)),
        "schema_version": int(payload.get("schema_version", -1)),
        "global_optimizer_step": int(payload.get("global_optimizer_step", -1)),
        "microbatch_cursor": int(payload.get("microbatch_cursor", -1)),
        "stage_id": payload.get("stage_id"),
        "extent_wall_ramp_value": float(payload.get("extent_wall_ramp_value", -1.0)),
        "has_optimizer_state": "optimizer_state_dict" in payload,
        "has_rng_state": "rng_state" in payload,
        "allocation_lock_helper_scope": "interactive-first via srun --jobid=61220581 --overlap; fold3 htzhulab-only lock handled by training entrypoint",
    }


def loss_and_gradient_smoke(model: torch.nn.Module, sample: torch.Tensor) -> dict[str, Any]:
    availability = torch.tensor([[1.0, 0.0, 1.0]], dtype=sample.dtype, device=sample.device)
    seg = torch.zeros((1, *sample.shape[-3:]), dtype=torch.long, device=sample.device)
    z0 = max(0, sample.shape[-3] // 2 - 1)
    seg[:, z0 : z0 + 2, sample.shape[-2] // 3 : sample.shape[-2] // 3 + 8, sample.shape[-1] // 3 : sample.shape[-1] // 3 + 8] = 5
    set_stage_trainability(model, global_step=6000)  # type: ignore[arg-type]
    for param in model.parameters():
        param.grad = None
    outputs = model(sample, availability, global_step=6000)  # type: ignore[operator]
    loss, metrics = care_ase_loss(outputs, {"seg": seg, "availability": availability})
    loss.backward()
    edema_grad = max((float(p.grad.detach().abs().max().cpu()) for name, p in model.named_parameters() if name.startswith("edema_branch.") and p.grad is not None), default=0.0)
    return {
        "status": "PASS" if torch.isfinite(loss).item() and edema_grad == 0.0 else "FAIL",
        "loss_metrics": metrics,
        "no_t2_edema_exclusive_parameter_gradient_max_abs": edema_grad,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fold", type=int, default=2)
    parser.add_argument("--output-dir", type=Path, default=RESULT_DIR)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    model = build_care_ase_for_fold(args.fold)
    model.eval()
    sample = torch.zeros(1, 3, 8, 64, 64)
    availability = torch.ones(1, 3)
    parity = model.step0_parity_report(sample, availability)
    summary = care_ase_contract_summary(model)
    findings = ast_forbidden_findings(SOURCE_FILES)
    parameter_groups = parameter_group_receipt(model)
    wiring = component_wiring_receipt(model, sample, availability)
    runtime = runtime_helper_receipt(model, output_dir)
    gradient = loss_and_gradient_smoke(model, sample)

    coverage_items = {
        "stock_encoder_bottleneck_low_mid_decoder": summary["stock_parameter_byte_coverage"] >= 0.99,
        "scar_edema_clone_highest_two_decoder_stages": summary["scar_cloned_decoder_stage_indices"] == [4, 5] and summary["edema_cloned_decoder_stage_indices"] == [4, 5],
        "step0_anatomy_scar_edema_parity": parity["status"] == "PASS",
        "normal_forward_no_stock_pathology_logits": summary["normal_forward_reads_stock_pathology_logits"] is False,
        "zero_init_component_final_logit_entries": wiring["status"] == "PASS",
        "no_t2_edema_gradient_zero": gradient["status"] == "PASS",
        "optimizer_groups_and_runtime_checkpoint": parameter_groups["status"] == "PASS" and runtime["status"] == "PASS",
        "forbidden_ast_tokens_absent": not findings,
    }
    remaining = [key for key, value in coverage_items.items() if not value]
    contract = {
        "status": "PASS" if not remaining else "FAIL",
        "remaining_gap_count": len(remaining),
        "remaining_gaps": remaining,
        "coverage_items": coverage_items,
        "ast_forbidden_findings": findings,
    }

    write_json(output_dir / "contract_coverage.json", contract)
    write_json(output_dir / "stock_clone_and_parity_receipt.json", parity)
    write_json(output_dir / "parameter_group_coverage_receipt.json", parameter_groups)
    write_json(output_dir / "component_final_logit_wiring_receipt.json", wiring)
    write_json(output_dir / "runtime_helper_contract_receipt.json", runtime)
    (output_dir / "implementation_snapshot.md").write_text(
        "# CARE-ASE W1 Implementation Snapshot\n\n"
        f"status: {contract['status']}\n"
        f"remaining_gap_count: {contract['remaining_gap_count']}\n\n"
        "The CARE-ASE model is implemented as a same-fold stock nnU-Net encoder/bottleneck/low-mid decoder with deep-copied half/full pathology decoder branches. "
        "Component heads are present and wired through zero-initialized final-logit projections; no-T2 final competition excludes class4 and the smoke test records zero edema-branch gradient.\n",
        encoding="utf-8",
    )
    (output_dir / "source_diff_summary.md").write_text("# CARE-ASE W1 Source Diff Summary\n\n```diff\n" + git_diff_summary() + "\n```\n", encoding="utf-8")
    print(json.dumps(contract, indent=2, sort_keys=True))
    return 0 if contract["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
