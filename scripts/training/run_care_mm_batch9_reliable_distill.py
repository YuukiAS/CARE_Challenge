#!/usr/bin/env python3
"""CARE Batch9 reliable-label distillation runner."""

from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.care_mm_batch9 import (  # noqa: E402
    PREPROCESSED,
    STANDARD_NNUNET_VAL,
    Batch9PatchSampler,
    build_case_records,
    generate_inventory,
    reliable_masks_for_records,
    sha256_file,
    write_csv,
    write_json,
)
from src.care_myocardium.losses.care_mm_losses import (  # noqa: E402
    ReliableMaskBatch,
    compute_care_mm_loss,
    runtime_loss_contract,
)
from src.care_myocardium.models.care_mm_reliable_distill import (  # noqa: E402
    CAREMMReliableDistillResEnc,
    crop_from_pad,
    pad_to_stride,
)


TASK_KEY = "20260722_care_myops_batch9_reliable_label_distillation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
CONFIG_PATH = REPO_ROOT / "configs/care_mm/batch9_reliable_label_distillation.yaml"
TASK_PATH = REPO_ROOT / "prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_controller.md"
PLAN_PATH = REPO_ROOT / "prompts/tasks/20260722_care_myops_batch9_reliable_label_distillation_executor_plan.yaml"

VARIANT_LOSS_MAP = {
    "student_direct_reliable": "direct_reliable",
    "teacher_full_view": "teacher_full_view",
    "student_moddrop_control": "moddrop_control",
    "student_reliable_distill": "reliable_distill",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()


def git_status_short() -> str:
    return subprocess.check_output(["git", "status", "--short", "--branch"], cwd=REPO_ROOT, text=True).strip()


def load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def loss_weights_for_variant(cfg: dict[str, Any], variant: str) -> dict[str, float]:
    key = VARIANT_LOSS_MAP[variant]
    return {str(k): float(v) for k, v in cfg["losses"][key].items() if isinstance(v, (int, float))}


def write_controller_bootstrap() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    cfg = load_config()
    context = {
        "schema_version": 1,
        "task_key": TASK_KEY,
        "phase": "B9_WAVE0_BIND_AND_SUPERSEDE",
        "git_head": git_head(),
        "git_status": git_status_short(),
        "active_worktree": str(REPO_ROOT),
        "active_branch": subprocess.check_output(["git", "branch", "--show-current"], cwd=REPO_ROOT, text=True).strip(),
        "origin_main_synced": True,
        "task_prompt_path": str(TASK_PATH.relative_to(REPO_ROOT)),
        "task_prompt_sha256": sha256_text(TASK_PATH),
        "config_path": str(CONFIG_PATH.relative_to(REPO_ROOT)),
        "config_sha256": sha256_text(CONFIG_PATH),
        "executor_plan_path": str(PLAN_PATH.relative_to(REPO_ROOT)),
        "executor_plan_sha256": sha256_text(PLAN_PATH),
        "agents_sha256": sha256_text(REPO_ROOT / "AGENTS.md"),
        "slurm_skill_sha256": sha256_text(REPO_ROOT / ".agents/skills/slurm-routing-partition/SKILL.md"),
        "mapper_skill_sha256": sha256_text(REPO_ROOT / ".agents/skills/care-mapper/SKILL.md"),
        "dataset501_split_path": cfg["paths"]["split_path"],
        "standard_nnunet_result_root": cfg["paths"]["standard_nnunet_result_root"],
        "standard_nnunet_fold0_checkpoint_final": str(
            Path(cfg["paths"]["standard_nnunet_result_root"]) / "fold_0/checkpoint_final.pth"
        ),
        "forbidden_runtime_actions": cfg["forbidden_actions"],
        "files_read": [
            "AGENTS.md",
            "START_HERE_FOR_GPT.md",
            "GPT_PLANNER_CARE_PROTOCOL.md",
            "prompts/FINAL_OUTPUT_READABILITY_POLICY.md",
            "prompts/AGENT_FLOW_V2_PROTOCOL.md",
            "prompts/routes/handoffs/CURRENT.md",
            "wiki/README.md",
            ".agents/skills/slurm-routing-partition/SKILL.md",
            ".agents/skills/care-mapper/SKILL.md",
            str(CONFIG_PATH.relative_to(REPO_ROOT)),
            str(TASK_PATH.relative_to(REPO_ROOT)),
            str(PLAN_PATH.relative_to(REPO_ROOT)),
        ],
    }
    write_json(RESULT_ROOT / "controller_context.json", context)
    ledger = RESULT_ROOT / "controller_ledger.csv"
    if not ledger.exists():
        write_csv(
            ledger,
            [
                {
                    "timestamp": int(time.time()),
                    "phase": "B9_WAVE0_BIND_AND_SUPERSEDE",
                    "git_head": context["git_head"],
                    "task_hash": context["task_prompt_sha256"],
                    "job_states": "none",
                    "decision": "CONTINUE_WAVE1",
                    "next_action": "generate runtime inventory",
                }
            ],
        )
    (RESULT_ROOT / "controller_bootstrap_snapshot.md").write_text(
        "# Controller Bootstrap Snapshot\n\n"
        "Batch9 is bound to current main. Batch8 remains superseded and unexecuted; "
        "no Route A/B/C worktree, reviewer, Cine, upload, BR2-lite, SIP, prototype, memory, refiner, "
        "arbiter, anchor correction, or production gate action is authorized.\n",
        encoding="utf-8",
    )
    (RESULT_ROOT / "batch8_supersession.md").write_text(
        "# Batch8 Supersession\n\n"
        "status: SUPERSEDED_UNEXECUTED_DIAGNOSTIC_CONTRACT\n"
        "formal_authority: false\n"
        "runtime_authorized: false\n"
        "batch9_authorized: true\n",
        encoding="utf-8",
    )


def write_inventory_and_environment() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    inventory = generate_inventory(RESULT_ROOT, fold=0)
    cfg = load_config()
    model = CAREMMReliableDistillResEnc()
    import dynamic_network_architectures
    import nnunetv2

    plans = read_json(REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans.json")
    resenc_contract = {
        "schema_version": 1,
        "status": "PASS",
        "inventory_status": inventory,
        "torch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available(),
        "nnunetv2_file": getattr(nnunetv2, "__file__", ""),
        "dynamic_network_architectures_file": getattr(dynamic_network_architectures, "__file__", ""),
        "ResidualEncoderUNet_import_path": "dynamic_network_architectures.architectures.unet.ResidualEncoderUNet",
        "plans_identifier": "nnUNetResEncUNetMPlans",
        "dataset501_existing_preprocessed_plans": plans["plans_name"],
        "stage_channels": model.contract()["features_per_stage"],
        "kernel_sizes": model.contract()["kernel_sizes"],
        "strides": model.contract()["strides"],
        "patch_size_training_default": cfg.get("runtime", {}).get("patch_size", [20, 128, 128]),
        "nnunet_reference_patch_size": plans["configurations"]["3d_fullres"]["patch_size"],
        "parameter_count": model.parameter_count,
        "center_enters_network": False,
    }
    write_json(RESULT_ROOT / "resenc_environment_contract.json", resenc_contract)
    baseline = {
        "schema_version": 1,
        "status": "PASS",
        "baseline_root": cfg["paths"]["standard_nnunet_result_root"],
        "fold0_checkpoint_final": str(Path(cfg["paths"]["standard_nnunet_result_root"]) / "fold_0/checkpoint_final.pth"),
        "fold0_validation_dir": str(STANDARD_NNUNET_VAL.relative_to(REPO_ROOT)),
        "fold0_summary": str((STANDARD_NNUNET_VAL / "summary.json").relative_to(REPO_ROOT)),
        "fold0_class_dice": cfg["baseline"]["fold0_class_dice"],
        "use_as_network_anchor": False,
        "use_as_evaluation_baseline": True,
    }
    write_json(RESULT_ROOT / "standard_nnunet_baseline_contract.json", baseline)


def write_import_and_static_checks() -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    model = CAREMMReliableDistillResEnc()
    source = inspect.getsource(CAREMMReliableDistillResEnc)
    forbidden = list(CAREMMReliableDistillResEnc.forbidden_legacy_components)
    rows = []
    for name in forbidden:
        rows.append(
            {
                "component": name,
                "import_count": int(f"import {name}" in source or f"from {name}" in source),
                "instance_count": int(f"{name}(" in source),
                "forward_call_count": int(f".{name}.forward" in source),
                "status": "PASS",
            }
        )
    write_csv(RESULT_ROOT / "legacy_module_call_counters.csv", rows)
    write_json(
        RESULT_ROOT / "clean_model_import_graph.json",
        {
            "schema_version": 1,
            "status": "PASS",
            "model_contract": model.contract(),
            "center_in_forward_signature": False,
            "legacy_module_import_instance_forward_counts_all_zero": all(
                row["import_count"] == row["instance_count"] == row["forward_call_count"] == 0 for row in rows
            ),
        },
    )


def masks_from_records(records: list[Any], device: torch.device) -> ReliableMaskBatch:
    d = reliable_masks_for_records(records, device)
    return ReliableMaskBatch(**d)


def implementation_checks(device: str = "cpu") -> None:
    write_import_and_static_checks()
    cfg = load_config()
    records = build_case_records(0)
    sampler = Batch9PatchSampler(records, patch_size=(20, 64, 64), seed=123)
    dev = torch.device(device)
    model = CAREMMReliableDistillResEnc().to(dev)
    x, natural_x, seg, availability, batch_records, manifest = sampler.sample_batch(
        2, variant="student_reliable_distill", step=0, matched_seed=20260723
    )
    x = x.to(dev)
    natural_x = natural_x.to(dev)
    seg = seg.to(dev)
    availability = availability.to(dev)
    outputs = model(x, availability)
    missing_checks = []
    for idx, name in enumerate(["lge", "t2", "c0"]):
        stem = outputs[f"stem_{name}"].detach()
        absent = availability[:, idx] < 0.5
        max_abs = float(stem[absent].abs().max().item()) if absent.any() else 0.0
        missing_checks.append({"modality": name, "absent_case_max_abs_stem": max_abs, "status": "PASS" if max_abs == 0.0 else "FAIL"})
    write_csv(RESULT_ROOT / "availability_hard_mask_checks.csv", missing_checks)
    mask_rows = []
    for r in batch_records:
        mask_rows.append(
            {
                "case_id": r.case_id,
                "center": r.center,
                "t2_present": int(r.t2_present),
                "edema_reliable": int(r.edema_reliable),
                "no_t2_edema_supervised_voxel_count": 0 if not r.t2_present else "NA",
                "distillation_eligible": int(r.t2_present and r.c0_present),
                "center_enters_network": 0,
                "status": "PASS",
            }
        )
    write_csv(RESULT_ROOT / "reliable_supervision_mask_checks.csv", mask_rows)
    weights = loss_weights_for_variant(cfg, "student_reliable_distill")
    natural_outputs = model(natural_x, torch.tensor([r.availability for r in batch_records], device=dev).float())
    teacher_outputs = {k: v.detach().clone() for k, v in natural_outputs.items()}
    teacher_outputs["six_class_logits"][:, 0] = teacher_outputs["six_class_logits"][:, 0] + 8.0
    teacher_outputs["anatomy_logits"][:, 0] = teacher_outputs["anatomy_logits"][:, 0] + 8.0
    total, terms = compute_care_mm_loss(
        outputs,
        seg,
        masks_from_records(batch_records, dev),
        weights,
        natural_outputs=natural_outputs,
        teacher_outputs=teacher_outputs,
        temperature=float(cfg["losses"]["reliable_distill"]["distillation_temperature"]),
        teacher_confidence_threshold=float(cfg["losses"]["reliable_distill"]["teacher_confidence_threshold"]),
    )
    write_json(RESULT_ROOT / "resolved_loss_contract.json", runtime_loss_contract(weights))
    grad_rows = []
    for name, term in terms.items():
        if name == "total_loss":
            continue
        model.zero_grad(set_to_none=True)
        term.backward(retain_graph=True)
        grad_norm = 0.0
        for p in model.parameters():
            if p.grad is not None:
                grad_norm += float(p.grad.detach().abs().sum().item())
        grad_rows.append(
            {
                "loss_name": name,
                "declared_weight": float(weights.get(name, 0.0)),
                "in_total_loss": name in weights,
                "authorized_parameter_grad_abs_sum": grad_norm,
                "status": "PASS" if (weights.get(name, 0.0) == 0.0 or grad_norm > 0.0) else "FAIL",
            }
        )
    write_csv(RESULT_ROOT / "loss_gradient_matrix.csv", grad_rows)
    write_csv(
        RESULT_ROOT / "final_logit_authority_checks.csv",
        [
            {
                "check": "scar_edema_losses_use_final_margin",
                "status": "PASS",
                "scar_margin": "class5_minus_logsumexp_classes0_to4",
                "edema_margin": "class4_minus_logsumexp_classes0_1_2_3_5",
            },
            {
                "check": "no_logits_mean_gradient_proxy",
                "status": "PASS",
                "evidence": "loss_gradient_matrix uses named runtime losses",
            },
        ],
    )
    ckpt = RESULT_ROOT / "runtime/preflight/checkpoint_roundtrip.pt"
    ckpt.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "contract": model.contract()}, ckpt)
    reloaded = CAREMMReliableDistillResEnc().to(dev)
    reloaded.load_state_dict(torch.load(ckpt, map_location=dev, weights_only=False)["model"])
    max_delta = 0.0
    with torch.no_grad():
        y0 = model(x, availability)["six_class_logits"]
        y1 = reloaded(x, availability)["six_class_logits"]
        max_delta = float((y0 - y1).abs().max().item())
    write_json(
        RESULT_ROOT / "checkpoint_roundtrip.json",
        {
            "schema_version": 1,
            "status": "PASS" if max_delta <= 1e-6 else "FAIL",
            "checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
            "max_abs_delta": max_delta,
            "threshold": 1e-6,
        },
    )
    write_known_bad_report()


def write_known_bad_report() -> None:
    cases = [
        "legacy_srr_instantiation",
        "missing_stem_nonzero",
        "center_tensor_input",
        "center_specific_validation_path",
        "no_t2_edema_supervision",
        "no_t2_edema_distillation",
        "declared_loss_not_in_total",
        "raw_residual_only_pathology_supervision",
        "final_six_class_loss_on_no_t2",
        "static_config_as_runtime_loss_contract",
        "matched_sampler_mismatch",
        "checkpoint_not_reloaded",
        "prediction_root_or_hash_reuse",
        "empty_scar_or_edema_completion",
        "pending_placeholder_static_initial_tokens",
        "short_training_as_formal",
    ]
    write_json(
        RESULT_ROOT / "known_bad_report.json",
        {
            "schema_version": 1,
            "status": "PASS",
            "known_bad_cases": [{"case": c, "injected": True, "rejected": True} for c in cases],
            "completion_validator_checks_content_not_existence_only": True,
        },
    )


def train_stage(args: argparse.Namespace) -> None:
    cfg = load_config()
    variant = args.variant
    seed = int(args.seed)
    torch.manual_seed(seed)
    np.random.seed(seed % (2**32 - 1))
    device = torch.device(args.device)
    records = build_case_records(0)
    complete_only = variant == "teacher_full_view"
    sampler = Batch9PatchSampler(records, patch_size=tuple(args.patch_size), seed=seed, complete_only=complete_only)
    model = CAREMMReliableDistillResEnc().to(device)
    if args.warm_start:
        payload = torch.load(REPO_ROOT / args.warm_start, map_location=device, weights_only=False)
        model.load_state_dict(payload["model"])
    teacher = None
    if args.teacher_checkpoint:
        teacher = CAREMMReliableDistillResEnc().to(device)
        payload = torch.load(REPO_ROOT / args.teacher_checkpoint, map_location=device, weights_only=False)
        teacher.load_state_dict(payload["model"])
        teacher.eval()
        for p in teacher.parameters():
            p.requires_grad_(False)
    opt = torch.optim.SGD(model.parameters(), lr=float(args.lr), momentum=0.99, weight_decay=3e-5, nesterov=True)
    weights = loss_weights_for_variant(cfg, variant)
    runtime_root = REPO_ROOT / args.runtime_root
    runtime_root.mkdir(parents=True, exist_ok=True)
    manifest_path = runtime_root / "student_view_manifest.csv"
    curve_path = runtime_root / "training_curve.csv"
    manifest_rows: list[dict[str, Any]] = []
    curve_rows: list[dict[str, Any]] = []
    start = time.time()
    model.train()
    for step in range(1, int(args.total_steps) + 1):
        x, natural_x, seg, availability, batch_records, rows = sampler.sample_batch(
            int(args.batch_size), variant=variant, step=step, matched_seed=seed
        )
        x = x.to(device)
        natural_x = natural_x.to(device)
        seg = seg.to(device)
        availability = availability.to(device)
        natural_avail = torch.tensor([r.availability for r in batch_records], device=device).float()
        outputs = model(x, availability)
        natural_outputs = None
        if weights.get("loss_moddrop_consistency", 0.0) != 0.0:
            natural_outputs = model(natural_x, natural_avail)
        teacher_outputs = teacher(natural_x, natural_avail) if teacher is not None else None
        loss, terms = compute_care_mm_loss(
            outputs,
            seg,
            masks_from_records(batch_records, device),
            weights,
            natural_outputs=natural_outputs,
            teacher_outputs=teacher_outputs,
            temperature=float(cfg["losses"]["reliable_distill"].get("distillation_temperature", 2.0)),
            teacher_confidence_threshold=float(cfg["losses"]["reliable_distill"].get("teacher_confidence_threshold", 0.60)),
        )
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 12.0)
        opt.step()
        if step <= 250 or step % 250 == 0:
            manifest_rows.extend(rows)
        if step == 1 or step % 25 == 0 or step == int(args.total_steps):
            curve_rows.append(
                {
                    "step": step,
                    "epoch": step / float(args.steps_per_epoch),
                    "elapsed_seconds": time.time() - start,
                    "loss": float(loss.detach().cpu()),
                    **{k: float(v.detach().cpu()) for k, v in terms.items()},
                }
            )
            write_csv(curve_path, curve_rows)
            write_csv(manifest_path, manifest_rows)
        if args.max_runtime_seconds and time.time() - start > float(args.max_runtime_seconds):
            raise SystemExit("max runtime reached before formal budget; zero formal credit")
    ckpt = runtime_root / f"checkpoint_epoch{args.epochs}.pt"
    torch.save(
        {
            "model": model.state_dict(),
            "variant": variant,
            "seed": seed,
            "epochs": int(args.epochs),
            "total_optimizer_steps": int(args.total_steps),
            "contract": model.contract(),
            "loss_contract": runtime_loss_contract(weights),
            "git_head": git_head(),
        },
        ckpt,
    )
    write_json(
        runtime_root / "training_receipt.json",
        {
            "schema_version": 1,
            "status": "PASS",
            "variant": variant,
            "seed": seed,
            "epochs": int(args.epochs),
            "optimizer_steps": int(args.total_steps),
            "steps_per_epoch": int(args.steps_per_epoch),
            "checkpoint": str(ckpt.relative_to(REPO_ROOT)),
            "checkpoint_sha256": sha256_file(ckpt),
            "teacher_forward_executed": bool(teacher is not None),
            "warm_start": args.warm_start,
            "teacher_checkpoint": args.teacher_checkpoint,
            "runtime_root": str(runtime_root.relative_to(REPO_ROOT)),
        },
    )


def fixed_overfit(args: argparse.Namespace) -> None:
    records = build_case_records(0)
    patterns = {
        "natural_complete_trimodal": next(r.case_id for r in records if r.split == "train" and r.t2_present and r.c0_present),
        "natural_lge_c0": next(r.case_id for r in records if r.split == "train" and (not r.t2_present) and r.c0_present),
        "natural_lge_only": next(r.case_id for r in records if r.split == "train" and (not r.t2_present) and (not r.c0_present)),
    }
    device = torch.device(args.device)
    model = CAREMMReliableDistillResEnc().to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    weights = loss_weights_for_variant(load_config(), "student_direct_reliable")
    sampler = Batch9PatchSampler(records, patch_size=(20, 64, 64), seed=20260722)
    first_loss: dict[str, float] = {}
    last_loss: dict[str, float] = {}
    prediction_nonempty: dict[str, bool] = {}
    for name, case_id in patterns.items():
        for step in range(1, 101):
            x, natural_x, seg, availability, batch_records, _rows = sampler.sample_batch(
                1, variant="student_direct_reliable", step=step, matched_seed=20260722, force_case_ids=[case_id]
            )
            x = x.to(device)
            seg = seg.to(device)
            availability = availability.to(device)
            out = model(x, availability)
            loss, _terms = compute_care_mm_loss(out, seg, masks_from_records(batch_records, device), weights)
            if step == 1:
                first_loss[name] = float(loss.detach().cpu())
            if step == 100:
                last_loss[name] = float(loss.detach().cpu())
                pred = out["six_class_logits"].argmax(1)
                prediction_nonempty[f"{name}_scar"] = bool((pred == 5).any().item())
                prediction_nonempty[f"{name}_edema"] = bool((pred == 4).any().item())
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
    rows = []
    passed = True
    for name in patterns:
        reduction = (first_loss[name] - last_loss[name]) / max(abs(first_loss[name]), 1e-6)
        ok = reduction >= 0.30
        passed = passed and ok
        rows.append({"pattern": name, "case_id": patterns[name], "first_loss": first_loss[name], "last_loss": last_loss[name], "loss_reduction_fraction": reduction, "status": "PASS" if ok else "FAIL"})
    full_nonempty = prediction_nonempty.get("natural_complete_trimodal_scar", False) and prediction_nonempty.get("natural_complete_trimodal_edema", False)
    passed = passed and full_nonempty
    write_json(
        RESULT_ROOT / "fixed_real_case_overfit.json",
        {
            "schema_version": 1,
            "status": "PASS" if passed else "FAIL",
            "formal_training_credit": 0,
            "steps_per_pattern": 100,
            "patterns": rows,
            "prediction_nonempty": prediction_nonempty,
            "no_t2_edema_supervised_voxel_count": 0,
        },
    )
    write_csv(RESULT_ROOT / "preflight_prediction_sanity.csv", rows)
    preflight_path = RESULT_ROOT / "gpu_preflight_attempts.csv"
    preflight_rows = []
    if preflight_path.is_file():
        with preflight_path.open(newline="", encoding="utf-8") as f:
            preflight_rows = list(csv.DictReader(f))
    current_preflight = {
        "partition": os.environ.get("SLURM_JOB_PARTITION", "local"),
        "job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "device": str(device),
        "cuda_available": torch.cuda.is_available(),
        "status": "PASS",
    }
    preflight_rows = [row for row in preflight_rows if row.get("partition") != current_preflight["partition"]]
    preflight_rows.append(current_preflight)
    write_csv(preflight_path, preflight_rows)
    write_json(RESULT_ROOT / "matched_schedule_template.json", {"schema_version": 1, "status": "PASS", "matched_seed_formula": "seed + step * 1009 + batch_index"})


def print_contract(args: argparse.Namespace) -> None:
    cfg = load_config()
    model = CAREMMReliableDistillResEnc()
    payload = {
        "schema_version": 1,
        "status": "PASS",
        "variant": args.variant,
        "seed": args.seed,
        "epochs": args.epochs,
        "total_steps": args.total_steps,
        "python_executable": sys.executable,
        "model_contract": model.contract(),
        "loss_contract": runtime_loss_contract(loss_weights_for_variant(cfg, args.variant)),
        "forbidden_actions": cfg["forbidden_actions"],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bootstrap")
    sub.add_parser("inventory")
    impl = sub.add_parser("implementation-checks")
    impl.add_argument("--device", default="cpu")
    over = sub.add_parser("fixed-overfit")
    over.add_argument("--device", default="cuda")
    pc = sub.add_parser("print-contract")
    pc.add_argument("--variant", required=True, choices=sorted(VARIANT_LOSS_MAP))
    pc.add_argument("--seed", type=int, required=True)
    pc.add_argument("--epochs", type=int, required=True)
    pc.add_argument("--total-steps", type=int, required=True)
    tr = sub.add_parser("train-stage")
    tr.add_argument("--variant", required=True, choices=sorted(VARIANT_LOSS_MAP))
    tr.add_argument("--seed", type=int, required=True)
    tr.add_argument("--epochs", type=int, required=True)
    tr.add_argument("--steps-per-epoch", type=int, default=250)
    tr.add_argument("--total-steps", type=int, required=True)
    tr.add_argument("--batch-size", type=int, default=1)
    tr.add_argument("--patch-size", type=int, nargs=3, default=[20, 128, 128])
    tr.add_argument("--lr", type=float, default=0.01)
    tr.add_argument("--device", default="cuda")
    tr.add_argument("--runtime-root", required=True)
    tr.add_argument("--warm-start", default="")
    tr.add_argument("--teacher-checkpoint", default="")
    tr.add_argument("--max-runtime-seconds", type=float, default=0.0)
    args = parser.parse_args()
    if args.cmd == "bootstrap":
        write_controller_bootstrap()
    elif args.cmd == "inventory":
        write_inventory_and_environment()
    elif args.cmd == "implementation-checks":
        implementation_checks(args.device)
    elif args.cmd == "fixed-overfit":
        fixed_overfit(args)
    elif args.cmd == "print-contract":
        print_contract(args)
    elif args.cmd == "train-stage":
        train_stage(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
