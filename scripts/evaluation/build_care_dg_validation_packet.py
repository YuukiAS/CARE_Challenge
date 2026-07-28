#!/usr/bin/env python3
"""Build and validate the CARE-DG dual-pathology validation packet.

This entrypoint is controller-owned. It records source-of-truth hashes,
allocation state, input assets, and fail-closed wave status. It must not submit
Slurm jobs, upload validation packages, build/upload Docker images, or push git.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.care_myocardium.data.case_metadata import load_myops_case_metadata

TASK_KEY = "20260727_care_dg_dual_pathology_validation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY
BLUEPRINT = REPO_ROOT / "prompts/blueprints/CARE_DG_dual_pathology_blueprint_20260727.md"
CONTROLLER = REPO_ROOT / "prompts/tasks/20260727_care_dg_dual_pathology_validation_controller.md"
EXECUTOR_PLAN = REPO_ROOT / "prompts/tasks/20260727_care_dg_dual_pathology_validation_executor_plan.yaml"
AGENTS = REPO_ROOT / "AGENTS.md"
SLURM_SKILL = REPO_ROOT / ".agents/skills/slurm-routing-partition/SKILL.md"
MAPPER_SKILL = REPO_ROOT / ".agents/skills/care-mapper/SKILL.md"
CURRENT = REPO_ROOT / "prompts/routes/handoffs/CURRENT.md"
WIKI_README = REPO_ROOT / "wiki/README.md"
WIKI_STATE = REPO_ROOT / "wiki/current_state.yaml"

ANCHOR_ROOT = (
    REPO_ROOT
    / "data/nnUNet/nnUNet_results/Dataset501_CAREMyoPS/"
    "nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres"
)
RAW_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS"
PREPROCESSED_ROOT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/nnUNetPlans_3d_fullres"
PROTOCOL_SPLIT = REPO_ROOT / "data/benchmarks/protocol/splits_MyoPS.json"
NNUNET_SPLIT = REPO_ROOT / "data/nnUNet/nnUNet_preprocessed/Dataset501_CAREMyoPS/splits_final.json"
MYOPS_VAL_ROOT = REPO_ROOT / "data/CARE_Challenge/MyoPS_val"
CINE_VAL_ROOT = REPO_ROOT / "data/CARE_Challenge/CineMyoPS_val"

FORBIDDEN_RUNTIME_TOKENS = (
    "IndeedLiu/MoSAIC",
    "/MoSAIC/code/weights",
    "prototype",
    "dictionary",
    "SIP",
    "CAREMMRD",
    "CARESRRCascadeRescue(",
)

REQUIRED_W0 = (
    "controller_context.json",
    "controller_ledger.csv",
    "controller_bootstrap_snapshot.md",
    "existing_allocation_receipt.json",
    "existing_allocation_gpu_lock.json",
    "input_asset_manifest.json",
    "evaluator_parity_report.json",
    "repair_ledger.csv",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run_capture(cmd: list[str], timeout: int = 60) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "elapsed_seconds": round(time.time() - started, 3),
        }
    except Exception as exc:  # pragma: no cover - defensive runtime receipt
        return {
            "cmd": cmd,
            "returncode": None,
            "error": repr(exc),
            "elapsed_seconds": round(time.time() - started, 3),
        }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        seen = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        fieldnames = fieldnames or ["status"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def case_count_under(root: Path) -> int:
    if not root.exists():
        return 0
    case_dirs = [p for p in root.rglob("Case*") if p.is_dir()]
    return len({p.name for p in case_dirs})




def npz_array_header(path: Path, key: str = "probabilities") -> dict[str, Any]:
    """Read an npz member header without materializing the full array."""

    import numpy as np

    member = f"{key}.npy"
    with zipfile.ZipFile(path) as zf:
        with zf.open(member) as f:
            version = np.lib.format.read_magic(f)
            shape, fortran_order, dtype = np.lib.format._read_array_header(f, version)  # type: ignore[attr-defined]
    return {"shape": list(shape), "dtype": str(dtype), "fortran_order": bool(fortran_order)}


def build_lightweight_anchor_manifest(*, repair_rows: list[dict[str, Any]]) -> dict[str, Any]:
    split_data = load_json(PROTOCOL_SPLIT)["folds"]
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    checkpoint_rows: dict[str, dict[str, Any]] = {}
    for fold_row in split_data:
        fold = int(fold_row["fold"])
        ckpt = ANCHOR_ROOT / f"fold_{fold}/checkpoint_best.pth"
        ckpt_final = ANCHOR_ROOT / f"fold_{fold}/checkpoint_final.pth"
        checkpoint_rows[str(fold)] = {
            "checkpoint_best_path": rel(ckpt),
            "checkpoint_best_exists": ckpt.is_file(),
            "checkpoint_best_size_bytes": ckpt.stat().st_size if ckpt.is_file() else None,
            "checkpoint_best_sha256": "DEFERRED_FULL_HASH_BLOCKING_REPAIR",
            "checkpoint_final_path": rel(ckpt_final),
            "checkpoint_final_exists": ckpt_final.is_file(),
            "checkpoint_final_size_bytes": ckpt_final.stat().st_size if ckpt_final.is_file() else None,
            "checkpoint_final_sha256": "DEFERRED_FULL_HASH_BLOCKING_REPAIR",
        }
        for case_id in sorted(fold_row["val"]):
            prob = ANCHOR_ROOT / f"fold_{fold}/validation/{case_id}.npz"
            pred = ANCHOR_ROOT / f"fold_{fold}/validation/{case_id}.nii.gz"
            label_path = RAW_ROOT / "labelsTr" / f"{case_id}.nii.gz"
            for required in (prob, pred, label_path):
                if not required.is_file():
                    missing.append(rel(required))
            header: dict[str, Any] = {}
            if prob.is_file():
                try:
                    header = npz_array_header(prob)
                except Exception as exc:
                    header = {"error": repr(exc)}
                    missing.append(f"{rel(prob)}:probability_header_unreadable")
            rows.append(
                {
                    "case_id": case_id,
                    "source_fold": fold,
                    "probability_path": rel(prob),
                    "probability_exists": prob.is_file(),
                    "probability_size_bytes": prob.stat().st_size if prob.is_file() else None,
                    "probability_header": header,
                    "probability_sha256": "DEFERRED_FULL_HASH_BLOCKING_REPAIR",
                    "prediction_path": rel(pred),
                    "prediction_exists": pred.is_file(),
                    "prediction_size_bytes": pred.stat().st_size if pred.is_file() else None,
                    "prediction_sha256": "DEFERRED_FULL_HASH_BLOCKING_REPAIR",
                    "label_path": rel(label_path),
                    "label_exists": label_path.is_file(),
                }
            )
    status = "COMPLETE_LIGHTWEIGHT_NEEDS_FULL_HASH_REPAIR" if not missing and len(rows) == 220 else "NEEDS_REPAIR"
    repair_rows.append(
        {
            "timestamp_utc": now_utc(),
            "wave": "W0",
            "issue": "full_oof_anchor_sha256_deferred_after_npz_full_read_timeout",
            "severity": "formal_training_blocking_repairable",
            "action": "replace lightweight manifest with full SHA256 manifest before formal training credit",
            "old_hash": "",
            "new_hash": "",
            "status": "OPEN",
        }
    )
    manifest = {
        "schema_version": 1,
        "status": status,
        "case_count": len(rows),
        "unique_cases": len({row["case_id"] for row in rows}),
        "fold_counts": {str(f): sum(1 for row in rows if int(row["source_fold"]) == f) for f in range(5)},
        "anchor_root": rel(ANCHOR_ROOT),
        "split_hash": sha256_file(PROTOCOL_SPLIT),
        "nnunet_split_hash": sha256_file(NNUNET_SPLIT) if NNUNET_SPLIT.exists() else "missing",
        "hash_completeness": "DEFERRED_FULL_HASH_BLOCKING_REPAIR",
        "missing": missing[:50],
        "checkpoints": checkpoint_rows,
        "entries": rows,
    }
    out_path = RESULT_ROOT / "nnunet_oof_anchor_manifest.json"
    write_json(out_path, manifest)
    return manifest


def build_context() -> dict[str, Any]:
    prompt_hashes = {
        rel(path): sha256_file(path)
        for path in (BLUEPRINT, CONTROLLER, EXECUTOR_PLAN, AGENTS, SLURM_SKILL, MAPPER_SKILL, CURRENT, WIKI_README, WIKI_STATE)
        if path.exists()
    }
    return {
        "task_key": TASK_KEY,
        "phase": "W0_BOOTSTRAP_AND_PARITY",
        "created_at_utc": now_utc(),
        "git_head": run_capture(["git", "rev-parse", "HEAD"]),
        "git_status": run_capture(["git", "status", "--short", "--branch"]),
        "origin_main": run_capture(["git", "rev-parse", "origin/main"]),
        "prompt_hashes": prompt_hashes,
        "controller_role": "Controller/Coordinator acceptance owner",
        "executor_count": 1,
        "parallel_execution_allowed": False,
        "allowed_allocation": {
            "job_id": "60657290",
            "partition": "htzhulab",
            "node": "g1807htzh01",
            "job_name": "CAREInteractive3d",
        },
        "forbidden_actions": {
            "sbatch": True,
            "salloc": True,
            "new_slurm_job": True,
            "validation_upload": True,
            "docker_upload": True,
            "runtime_git_push": True,
            "write_overflow_htzhu_CARE": True,
        },
        "current_and_wiki_staleness": {
            "CURRENT.md": "STALE_BASELINE_ONLY_TRUTH_OVERRIDDEN_BY_20260727_CARE_DG_TASK_UNTIL_TERMINAL_PACKET",
            "wiki": "STALE_BASELINE_ONLY_TRUTH_OVERRIDDEN_BY_20260727_CARE_DG_TASK_UNTIL_TERMINAL_PACKET",
        },
    }


def build_allocation_receipts() -> tuple[dict[str, Any], dict[str, Any]]:
    squeue = run_capture(["squeue", "-j", "60657290", "-o", "%i|%t|%M|%l|%D|%R|%j|%P"])
    scontrol = run_capture(["scontrol", "show", "job", "60657290"], timeout=60)
    gpu_probe = run_capture(
        [
            "srun",
            "--jobid=60657290",
            "--overlap",
            "--ntasks=1",
            "bash",
            "-lc",
            "hostname; date -Is; nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader",
        ],
        timeout=120,
    )
    running = "|R|" in squeue.get("stdout", "")
    allocation = {
        "checked_at_utc": now_utc(),
        "job_id": "60657290",
        "expected_partition": "htzhulab",
        "expected_node": "g1807htzh01",
        "expected_job_name": "CAREInteractive3d",
        "squeue": squeue,
        "scontrol": scontrol,
        "status": "RUNNING" if running else "NOT_RUNNING_OR_NOT_VISIBLE",
    }
    lock = {
        "checked_at_utc": now_utc(),
        "lock_scope": "CARE_DG_GPU_SERIAL_ONLY",
        "job_id": "60657290",
        "parallel_gpu_processes_allowed": 0,
        "gpu_probe": gpu_probe,
        "gpu_available_for_next_serial_command": gpu_probe.get("returncode") == 0 and "0 %" in gpu_probe.get("stdout", ""),
    }
    return allocation, lock


def build_asset_manifest(repair_rows: list[dict[str, Any]]) -> dict[str, Any]:
    metadata = load_myops_case_metadata(REPO_ROOT)
    complete_cases = sorted([case_id for case_id, meta in metadata.items() if meta.modality_group == "C0+LGE+T2"])
    split_data = load_json(PROTOCOL_SPLIT)["folds"]
    fold_counts = {str(fold["fold"]): {"train": len(fold["train"]), "val": len(fold["val"])} for fold in split_data}
    anchor_manifest_path = RESULT_ROOT / "nnunet_oof_anchor_manifest.json"
    anchor_status: dict[str, Any]
    anchor_status = build_lightweight_anchor_manifest(repair_rows=repair_rows)
    return {
        "created_at_utc": now_utc(),
        "task_key": TASK_KEY,
        "case_lists": {
            "myops_train_cases": len(metadata),
            "complete_trimodal_cases": len(complete_cases),
            "complete_trimodal_case_ids_sha256": hashlib.sha256("\n".join(complete_cases).encode()).hexdigest(),
            "myops_validation_cases": case_count_under(MYOPS_VAL_ROOT),
            "cine_validation_cases": case_count_under(CINE_VAL_ROOT),
        },
        "splits": {
            "protocol_split_path": rel(PROTOCOL_SPLIT),
            "protocol_split_sha256": sha256_file(PROTOCOL_SPLIT),
            "nnunet_split_path": rel(NNUNET_SPLIT),
            "nnunet_split_sha256": sha256_file(NNUNET_SPLIT) if NNUNET_SPLIT.exists() else "missing",
            "fold_counts": fold_counts,
        },
        "anchor": {
            "anchor_root": rel(ANCHOR_ROOT),
            "oof_anchor_manifest_path": rel(anchor_manifest_path),
            "oof_anchor_manifest_status": anchor_status.get("status"),
            "hash_completeness": anchor_status.get("hash_completeness"),
            "oof_case_count": anchor_status.get("case_count"),
            "fold_counts": anchor_status.get("fold_counts"),
        },
        "labels": {
            "compact_labels": {"0": "background", "1": "myocardium", "2": "LV_blood", "3": "RV_blood", "4": "edema", "5": "scar"},
            "official_myops_labels": {"0": 0, "1": 200, "2": 500, "3": 600, "4": 1220, "5": 2221},
        },
        "metric_contract": {
            "required": ["Dice", "leaderboard_HD", "HD95", "exact_HD", "precision", "recall", "remote_FP", "component_count", "volume_ratio", "help_harm"],
            "parity_tolerance": {"dice_precision_recall": 1e-6, "distance_mm": 1e-4},
        },
    }


def build_parity_report(repair_rows: list[dict[str, Any]]) -> dict[str, Any]:
    sources = {
        "mosaic_gap_oof_casewise": RESULT_ROOT.parent / "20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/oof_casewise_metrics.csv",
        "mosaic_gap_oof_summary": RESULT_ROOT.parent / "20260726_care_mosaic_validation_gap_forensics_and_final_blueprint/oof_model_summary.csv",
        "srr_anchor_audit": RESULT_ROOT.parent / "20260724_care_myops_srr_cascade_submission_rescue/anchor_oof_audit.json",
        "mosaic_fold0_canonical": RESULT_ROOT.parent / "20260725_care_myops_mosaic_fold0_reproduction/canonical_casewise_metrics.csv",
    }
    present = {name: path.exists() for name, path in sources.items()}
    parity = {
        "created_at_utc": now_utc(),
        "status": "NEEDS_REPAIR",
        "reason": "W0 evaluator parity entrypoint not yet rerun against fold0 nnU-Net, Batch7, MMRD, SCR canonical metrics.",
        "required_tolerance": {"dice_precision_recall": 1e-6, "distance_mm": 1e-4},
        "source_tables_present": {name: {"path": rel(path), "exists": exists} for name, (path, exists) in zip(sources, [(p, present[n]) for n, p in sources.items()])},
        "formal_training_allowed": False,
    }
    repair_rows.append(
        {
            "timestamp_utc": now_utc(),
            "wave": "W0",
            "issue": "evaluator_parity_not_yet_recomputed",
            "severity": "formal_training_blocking_repairable",
            "action": "implement and run canonical evaluator parity for fold0 nnU-Net, Batch7, MMRD, and SCR metrics before W1/W2 formal training",
            "old_hash": "",
            "new_hash": "",
            "status": "OPEN",
        }
    )
    return parity


def write_bootstrap_snapshot(context: dict[str, Any], allocation: dict[str, Any], asset_manifest: dict[str, Any], parity: dict[str, Any]) -> None:
    text = f"""# CARE-DG W0 bootstrap snapshot

task_key: `{TASK_KEY}`
created_at_utc: `{context['created_at_utc']}`
git_head: `{context['git_head'].get('stdout', '')}`
origin_main: `{context['origin_main'].get('stdout', '')}`
allocation_60657290: `{allocation['status']}`
myops_train_cases: `{asset_manifest['case_lists']['myops_train_cases']}`
complete_trimodal_cases: `{asset_manifest['case_lists']['complete_trimodal_cases']}`
myops_validation_cases: `{asset_manifest['case_lists']['myops_validation_cases']}`
cine_validation_cases: `{asset_manifest['case_lists']['cine_validation_cases']}`
oof_anchor_manifest_status: `{asset_manifest['anchor']['oof_anchor_manifest_status']}`
evaluator_parity_status: `{parity['status']}`

CURRENT/wiki are stale baseline-only truth from the previous MoSAIC packet and
are intentionally not rewritten as CARE-DG verified until W6 terminal evidence.
"""
    write_text(RESULT_ROOT / "controller_bootstrap_snapshot.md", text)




def validate_gate_a_r3(failures: list[str]) -> None:
    contract_path = RESULT_ROOT / "implementation_contract.json"
    scar_priority_root = RESULT_ROOT / "runtime/gate_b_scar_priority_preflight/fold0"
    preflight_root = scar_priority_root if scar_priority_root.exists() else RESULT_ROOT / "runtime/gate_a_r3_preflight/fold0"
    receipt_path = preflight_root / "fold_training_receipt.json"
    split_path = preflight_root / "inner_split_manifest.json"
    plan_path = preflight_root / "inner_evaluation_plan.json"
    sampler_stage_a_path = preflight_root / "sampler_quota_audit_stage_a.json"
    sampler_stage_b_path = preflight_root / "sampler_quota_audit_stage_b.json"
    resolved_contract_path = preflight_root / "resolved_training_contract.json"
    repeat_path = preflight_root / "inner_evaluation_repeat_receipt.json"
    preflight_validator_path = preflight_root / "preflight_validator_report.json"
    checkpoint_manifest_path = preflight_root / "checkpoint_manifest.csv"
    random_negative_stage_a_path = preflight_root / "random_negative_semantics_audit_stage_a.json"
    random_negative_stage_b_path = preflight_root / "random_negative_semantics_audit_stage_b.json"
    if not contract_path.exists():
        failures.append("gate_a_r3_missing_implementation_contract")
        return
    contract = load_json(contract_path)
    if contract.get("status") != "GATE_A_REPAIRED_IMPLEMENTATION_PASS":
        failures.append("gate_a_r3_contract_status_not_allowed")
    if contract.get("gate_revision") != "A-R3":
        failures.append("gate_a_r3_contract_revision_missing")
    if contract.get("approval_token_required") != "APPROVE_GATE_A_R3":
        failures.append("gate_a_r3_approval_token_wrong")
    implemented = contract.get("implemented_contract", {})
    for key in [
        "validate_w0_accepts_preregistered_status_only",
        "inner_select_excluded_from_stage_a_and_stage_b",
        "checkpoint_selection_fixed_complete_inner_objective",
        "fixed_inner_evaluation_plan_generated_before_training",
        "fixed_inner_evaluation_covers_complete_inner_select",
        "evaluate_inner_independent_of_training_rng",
        "stage_A_and_stage_B_use_same_fixed_inner_objective",
        "effective_sampler_eligible_pools_precomputed",
        "effective_sampler_target_hit_verified_after_jitter",
        "sampler_audit_reports_effective_not_nominal_quota",
        "checkpoint_saves_python_numpy_torch_cuda_scaler_and_local_rng",
        "checkpoint_resume_validates_hash_contract_before_restore",
        "gate_a_r3_preflight_runs_stage_A_and_stage_B",
        "stage_A_optimizer_two_groups_3e_minus_4",
        "stage_B_optimizer_representation_2e_minus_5_pathology_1e_minus_4",
        "every_trainable_parameter_exactly_one_optimizer_group",
        "checkpoint_reload_preserves_optimizer_groups_and_lrs",
        "resolved_training_contract_sha256_written_to_checkpoint_receipt_manifest",
        "checkpoint_resume_rejects_resolved_contract_mismatch",
        "stage_A_and_stage_B_effective_sampler_audits_written",
        "consistency_validator_rejects_fail_deferred_mismatch",
        "margin_caps_fit_actual_train_only",
        "soft_support_union_labels_1_4_5_excludes_lv_rv",
        "repaired_runtime_label_isolated",
        "scar_priority_composition_anchor_edema_scar_argmax",
        "scar_priority_outputs_after_edema_and_final_after_scar",
        "post_scar_decision_not_overwritten_by_later_edema",
        "negative_scar_correction_can_release_false_scar",
        "random_negative_semantics_audit_stage_A_and_B_written_without_sampler_change",
        "support_distance_clips_empty_anchor_simpleitk_max_float",
        "support_actionable_sampler_excludes_empty_anchor_error_pathology_pools",
    ]:
        if implemented.get(key) is not True:
            failures.append(f"gate_a_r3_contract_missing:{key}")
    for path, name in [
        (receipt_path, "preflight_receipt"),
        (split_path, "inner_split_manifest"),
        (plan_path, "inner_evaluation_plan"),
        (sampler_stage_a_path, "sampler_quota_audit_stage_a"),
        (sampler_stage_b_path, "sampler_quota_audit_stage_b"),
        (resolved_contract_path, "resolved_training_contract"),
        (repeat_path, "inner_evaluation_repeat"),
        (preflight_validator_path, "preflight_validator"),
        (checkpoint_manifest_path, "checkpoint_manifest"),
        (random_negative_stage_a_path, "random_negative_semantics_audit_stage_a"),
        (random_negative_stage_b_path, "random_negative_semantics_audit_stage_b"),
    ]:
        if not path.exists():
            failures.append(f"gate_a_r3_{name}_missing")
    if not receipt_path.exists():
        return
    receipt = load_json(receipt_path)
    if receipt.get("status") != "PASS":
        failures.append("gate_a_r3_preflight_receipt_not_PASS")
    if receipt.get("preflight_only") is not True:
        failures.append("gate_a_r3_preflight_not_marked_preflight_only")
    if int(receipt.get("expected_stage_a_steps", -1)) != 1:
        failures.append("gate_a_r3_stage_A_not_one_step")
    if int(receipt.get("expected_stage_b_steps", -1)) != 1:
        failures.append("gate_a_r3_stage_B_not_one_step")
    if int(receipt.get("actual_optimizer_steps", -1)) != 2:
        failures.append("gate_a_r3_preflight_step_count_not_2")
    if int(receipt.get("formal_training_credit", -1)) != 0:
        failures.append("gate_a_r3_preflight_has_formal_training_credit")
    if receipt.get("validate_w0_status") != "PASS":
        failures.append("gate_a_r3_validate_w0_not_PASS")
    if receipt.get("runtime_kind") not in {"gate_a_r3_preflight", "gate_b_scar_priority_preflight"}:
        failures.append("gate_a_r3_runtime_label_not_isolated")
    if receipt.get("fixed_inner_objective") != "fixed_complete_inner_select_no_aug_patch_loss":
        failures.append("gate_a_r3_inner_objective_not_fixed")
    if receipt.get("outer_val_used_for_checkpoint_selection") is not False:
        failures.append("gate_a_r3_outer_val_used_for_checkpoint_selection")
    if receipt.get("margin_cap_audit", {}).get("fit_population") != "actual_train_cases_only":
        failures.append("gate_a_r3_margin_cap_not_train_only")
    if receipt.get("checkpoint_write_reload", {}).get("status") != "PASS":
        failures.append("gate_a_r3_checkpoint_reload_not_PASS")
    if receipt.get("checkpoint_write_reload", {}).get("inner_evaluation_repeat_exact") is not True:
        failures.append("gate_a_r3_inner_evaluation_repeat_not_exact")
    for sampler_path, stage_name in [(sampler_stage_a_path, "stage_a"), (sampler_stage_b_path, "stage_b")]:
        sampler = load_json(sampler_path) if sampler_path.exists() else {}
        if sampler.get("status") != "PASS":
            failures.append(f"gate_a_r3_effective_sampler_audit_not_PASS:{stage_name}")
        if int(sampler.get("silent_fallback_count", -1)) != 0:
            failures.append(f"gate_a_r3_sampler_silent_fallback_nonzero:{stage_name}")
        hit_rates = sampler.get("target_hit_rates", {})
        for key in ("error_fn", "error_fp", "pathology"):
            if float(hit_rates.get(key, -1.0)) != 1.0:
                failures.append(f"gate_a_r3_sampler_hit_rate_not_100:{stage_name}:{key}")
        fractions = sampler.get("effective_fractions", {})
        if abs(float(fractions.get("error_fn", 0.0)) + float(fractions.get("error_fp", 0.0)) - 0.5) > 0.02:
            failures.append(f"gate_a_r3_sampler_fn_fp_fraction_bad:{stage_name}")
        if abs(float(fractions.get("pathology", 0.0)) - 0.25) > 0.02:
            failures.append(f"gate_a_r3_sampler_pathology_fraction_bad:{stage_name}")
        if abs(float(fractions.get("random", 0.0)) - 0.25) > 0.02:
            failures.append(f"gate_a_r3_sampler_random_fraction_bad:{stage_name}")
    if plan_path.exists():
        plan = load_json(plan_path)
        if plan.get("plan_sha256") != receipt.get("fixed_inner_evaluation_plan_sha256"):
            failures.append("gate_a_r3_inner_plan_hash_mismatch")
        if int(plan.get("case_count", -1)) != int(receipt.get("complete_inner_selection_cases", -2)):
            failures.append("gate_a_r3_inner_plan_case_count_not_complete_inner_select")
        if int(plan.get("patch_count", 0)) < int(plan.get("case_count", 0)):
            failures.append("gate_a_r3_inner_plan_does_not_cover_all_cases")
        if plan.get("training_rng_dependency") is not False:
            failures.append("gate_a_r3_inner_plan_training_rng_dependency")
        if plan.get("stage_a_and_stage_b_share_objective") is not True:
            failures.append("gate_a_r3_inner_plan_not_shared_by_stage_A_B")
    if repeat_path.exists():
        repeat = load_json(repeat_path)
        if repeat.get("status") != "PASS":
            failures.append("gate_a_r3_inner_evaluation_repeat_receipt_not_PASS")
    if split_path.exists():
        split = load_json(split_path)
        actual = set(split.get("actual_train_cases") or [])
        inner = set(split.get("inner_select_cases") or [])
        complete_actual = set(split.get("complete_actual_train_cases") or [])
        complete_inner = set(split.get("complete_inner_select_cases") or [])
        if actual & inner:
            failures.append("gate_a_r3_inner_select_in_stage_a_cases")
        if complete_actual & inner:
            failures.append("gate_a_r3_inner_select_in_stage_b_cases")
        if not complete_inner:
            failures.append("gate_a_r3_complete_inner_select_empty")
        if complete_inner != inner:
            failures.append("gate_a_r3_inner_select_not_complete_trimodal")
        if split.get("outer_val_used") is not False:
            failures.append("gate_a_r3_split_outer_val_used")
        if receipt.get("stage_a_case_ids_sha256") != split.get("sha256", {}).get("actual_train"):
            failures.append("gate_a_r3_stage_a_hash_mismatch")
        if receipt.get("stage_b_case_ids_sha256") != split.get("sha256", {}).get("complete_actual_train"):
            failures.append("gate_a_r3_stage_b_hash_mismatch")
        if receipt.get("inner_select_case_ids_sha256") != split.get("sha256", {}).get("inner_select"):
            failures.append("gate_a_r3_inner_select_hash_mismatch")
        if receipt.get("margin_cap_audit", {}).get("case_ids_sha256") != split.get("sha256", {}).get("actual_train"):
            failures.append("gate_a_r3_margin_cap_case_hash_mismatch")
    if resolved_contract_path.exists():
        resolved = load_json(resolved_contract_path)
        if resolved.get("resolved_training_contract_sha256") != receipt.get("resolved_training_contract_sha256"):
            failures.append("gate_a_r3_resolved_contract_hash_mismatch")
        lr = resolved.get("learning_rates", {})
        if float(lr.get("stage_a", {}).get("representation_group", -1.0)) != 3e-4:
            failures.append("gate_a_r3_stage_a_representation_lr_bad")
        if float(lr.get("stage_a", {}).get("pathology_group", -1.0)) != 3e-4:
            failures.append("gate_a_r3_stage_a_pathology_lr_bad")
        if float(lr.get("stage_b", {}).get("representation_group", -1.0)) != 2e-5:
            failures.append("gate_a_r3_stage_b_representation_lr_bad")
        if float(lr.get("stage_b", {}).get("pathology_group", -1.0)) != 1e-4:
            failures.append("gate_a_r3_stage_b_pathology_lr_bad")
        if float(resolved.get("weight_decay", -1.0)) != 1e-4:
            failures.append("gate_a_r3_weight_decay_bad")
        if float(resolved.get("grad_clip_norm", -1.0)) != 1.0:
            failures.append("gate_a_r3_grad_clip_norm_bad")
        if resolved.get("amp", {}).get("dtype") != "bfloat16":
            failures.append("gate_a_r3_amp_dtype_not_bfloat16")
        gradient_clipping = resolved.get("gradient_clipping", {})
        if gradient_clipping.get("enabled") is not True or float(gradient_clipping.get("max_norm", -1.0)) != 1.0:
            failures.append("gate_a_r3_gradient_clipping_contract_bad")
        support = resolved.get("support_semantics", {})
        if support.get("support_labels") != [1, 4, 5] or support.get("excluded_labels") != [2, 3]:
            failures.append("gate_a_r3_support_semantics_bad")
        if support.get("distance_to_myocardium_clip_mm") != [-64.0, 128.0]:
            failures.append("gate_b_support_distance_clip_contract_bad")
        if resolved.get("sampler_hashes", {}).get("stage_a_sampler_index_sha256") != (load_json(sampler_stage_a_path).get("sampler_index_sha256") if sampler_stage_a_path.exists() else None):
            failures.append("gate_a_r3_stage_a_sampler_hash_missing_from_resolved_contract")
        if resolved.get("sampler_hashes", {}).get("stage_b_sampler_index_sha256") != (load_json(sampler_stage_b_path).get("sampler_index_sha256") if sampler_stage_b_path.exists() else None):
            failures.append("gate_a_r3_stage_b_sampler_hash_missing_from_resolved_contract")
        comp = resolved.get("composition_semantics", {})
        if comp.get("order") != ["anchor_logits", "bounded_edema_zone_correction", "bounded_scar_correction", "final_six_class_argmax"] or comp.get("post_scar_overwrite_allowed") is not False:
            failures.append("gate_b_scar_priority_composition_contract_bad")
        if "after_edema_logits" not in comp.get("required_outputs", []) or "final_logits_after_scar_priority" not in comp.get("required_outputs", []):
            failures.append("gate_b_scar_priority_required_outputs_missing")
        random_hashes = resolved.get("random_negative_semantics_audit_hashes", {})
        if random_hashes.get("stage_a_sha256") != (load_json(random_negative_stage_a_path).get("audit_sha256") if random_negative_stage_a_path.exists() else None):
            failures.append("gate_b_random_negative_stage_a_hash_mismatch")
        if random_hashes.get("stage_b_sha256") != (load_json(random_negative_stage_b_path).get("audit_sha256") if random_negative_stage_b_path.exists() else None):
            failures.append("gate_b_random_negative_stage_b_hash_mismatch")
        for sampler_path, stage_name in [(sampler_stage_a_path, "stage_a"), (sampler_stage_b_path, "stage_b")]:
            sampler = load_json(sampler_path) if sampler_path.exists() else {}
            actionability = sampler.get("sampler_index", {}).get("support_actionability", {})
            if actionability.get("distance_clip_mm") != [-64.0, 128.0]:
                failures.append(f"gate_b_sampler_actionability_distance_clip_missing:{stage_name}")
            if "empty_anchor_tissue_cases" not in actionability or "excluded_unactionable_cases" not in actionability:
                failures.append(f"gate_b_sampler_actionability_summary_missing:{stage_name}")
    for audit_path, stage_name in [(random_negative_stage_a_path, "stage_a"), (random_negative_stage_b_path, "stage_b")]:
        audit = load_json(audit_path) if audit_path.exists() else {}
        if audit.get("status") != "PASS":
            failures.append(f"gate_b_random_negative_audit_not_PASS:{stage_name}")
        if int(audit.get("samples", -1)) != 1000:
            failures.append(f"gate_b_random_negative_audit_sample_count_bad:{stage_name}")
        records = audit.get("records") or []
        if len(records) != 1000:
            failures.append(f"gate_b_random_negative_audit_records_missing:{stage_name}")
        if any(str(row.get("patch_hash", "")) == "" for row in records[:20]):
            failures.append(f"gate_b_random_negative_audit_patch_hash_missing:{stage_name}")
    if receipt.get("stage_a_representation_lr") != 3e-4 or receipt.get("stage_a_pathology_lr") != 3e-4:
        failures.append("gate_a_r3_receipt_stage_a_lrs_bad")
    if receipt.get("stage_b_representation_lr") != 2e-5 or receipt.get("stage_b_pathology_lr") != 1e-4:
        failures.append("gate_a_r3_receipt_stage_b_lrs_bad")
    if receipt.get("hash_contract", {}).get("resolved_training_contract_sha256") != receipt.get("resolved_training_contract_sha256"):
        failures.append("gate_a_r3_checkpoint_hash_contract_missing_resolved_sha")
    if checkpoint_manifest_path.exists():
        with checkpoint_manifest_path.open(newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        stages = {str(row.get("stage")) for row in rows}
        if "A" not in stages or "B" not in stages:
            failures.append("gate_a_r3_preflight_checkpoint_manifest_missing_stage_A_or_B")
        for row in rows:
            if row.get("outer_val_used") not in {False, "False", "false", "0", 0}:
                failures.append("gate_a_r3_checkpoint_manifest_outer_val_used")
            if row.get("inner_plan_sha256") and row.get("inner_plan_sha256") != receipt.get("fixed_inner_evaluation_plan_sha256"):
                failures.append("gate_a_r3_checkpoint_inner_plan_hash_mismatch")
            if row.get("resolved_training_contract_sha256") and row.get("resolved_training_contract_sha256") != receipt.get("resolved_training_contract_sha256"):
                failures.append("gate_a_r3_checkpoint_resolved_contract_hash_mismatch")
            if str(row.get("stage")) == "A" and (float(row.get("representation_lr", -1.0)) != 3e-4 or float(row.get("pathology_lr", -1.0)) != 3e-4):
                failures.append("gate_a_r3_checkpoint_manifest_stage_a_lrs_bad")
            if str(row.get("stage")) == "B" and (float(row.get("representation_lr", -1.0)) != 2e-5 or float(row.get("pathology_lr", -1.0)) != 1e-4):
                failures.append("gate_a_r3_checkpoint_manifest_stage_b_lrs_bad")
    if preflight_validator_path.exists():
        preflight_validator = load_json(preflight_validator_path)
        if preflight_validator.get("status") != "PASS":
            failures.append("gate_a_r3_preflight_validator_not_PASS")
        if int(preflight_validator.get("formal_training_credit", -1)) != 0:
            failures.append("gate_a_r3_preflight_validator_has_training_credit")


def read_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def validate_gate_b_fold0(failures: list[str]) -> None:
    runtime_root = RESULT_ROOT / "runtime/repaired_formal_scar_priority/fold0"
    eval_root = runtime_root / "gate_b_evaluation"
    receipt_path = runtime_root / "fold_training_receipt.json"
    summary_path = eval_root / "gate_b_summary.json"
    validator_path = eval_root / "gate_b_validator_report.json"
    overwrite_path = eval_root / "gate_b_post_scar_overwrite_audit.json"
    required_csvs = {
        "casewise": eval_root / "gate_b_fold0_casewise_metrics.csv",
        "summary": eval_root / "gate_b_fold0_model_summary.csv",
        "complete16": eval_root / "gate_b_complete16_summary.csv",
        "help_harm": eval_root / "gate_b_help_harm.csv",
        "exact_hd_tail": eval_root / "gate_b_exact_hd_tail_audit.csv",
        "remote_fp": eval_root / "gate_b_remote_fp_audit.csv",
        "conflict_transition": eval_root / "gate_b_scar_edema_conflict_transition_matrix.csv",
        "component": eval_root / "gate_b_component_audit.csv",
        "mechanism": eval_root / "gate_b_mechanism_activation_audit.csv",
        "no_t2": eval_root / "gate_b_no_t2_safety_audit.csv",
        "prediction_hashes": eval_root / "gate_b_prediction_hashes.csv",
    }
    for name, csv_path in required_csvs.items():
        if not csv_path.exists():
            failures.append(f"gate_b_missing_output:{name}")
        elif not read_csv_rows(csv_path):
            failures.append(f"gate_b_empty_output:{name}")
    for json_path, name in [
        (receipt_path, "fold_training_receipt"),
        (summary_path, "summary"),
        (validator_path, "validator"),
        (overwrite_path, "post_scar_overwrite"),
    ]:
        if not json_path.exists():
            failures.append(f"gate_b_missing_output:{name}")
    if not receipt_path.exists() or not summary_path.exists() or not validator_path.exists() or not overwrite_path.exists():
        return

    receipt = load_json(receipt_path)
    summary = load_json(summary_path)
    validator = load_json(validator_path)
    overwrite = load_json(overwrite_path)
    if receipt.get("status") != "PASS":
        failures.append("gate_b_fold0_training_receipt_not_PASS")
    if int(receipt.get("actual_optimizer_steps", -1)) != 8000:
        failures.append("gate_b_fold0_training_not_8000_steps")
    if int(receipt.get("formal_training_credit", -1)) != 8000:
        failures.append("gate_b_fold0_formal_training_credit_not_8000")
    if receipt.get("runtime_label") != "repaired_formal_scar_priority":
        failures.append("gate_b_runtime_label_not_repaired_formal_scar_priority")
    if receipt.get("stage_a_representation_lr") != 3e-4 or receipt.get("stage_b_representation_lr") != 2e-5:
        failures.append("gate_b_fold0_representation_lr_bad")
    if receipt.get("stage_a_pathology_lr") != 3e-4 or receipt.get("stage_b_pathology_lr") != 1e-4:
        failures.append("gate_b_fold0_pathology_lr_bad")
    allowed_gate_b_statuses = {"PASS", "GATE_B_OVERACTIVE_FRAGMENTED_CORRECTION_DIAGNOSTIC"}
    if summary.get("status") not in allowed_gate_b_statuses or summary.get("receipt_status") != "PASS":
        failures.append("gate_b_summary_status_inconsistent")
    if summary.get("status") == "GATE_B_OVERACTIVE_FRAGMENTED_CORRECTION_DIAGNOSTIC" and summary.get("scientific_expansion_authorized") is not False:
        failures.append("gate_b_diagnostic_scientific_expansion_not_false")
    if validator.get("status") != "PASS" or validator.get("failures") not in ([], None):
        failures.append("gate_b_evaluator_validator_not_PASS")
    if int(summary.get("outer_heldout_cases", -1)) != 44 or int(summary.get("prediction_count", -1)) != 44:
        failures.append("gate_b_outer44_count_bad")
    if int(summary.get("complete_trimodal_heldout_cases", -1)) != 16:
        failures.append("gate_b_complete16_count_bad")
    if summary.get("runtime_label") != "repaired_formal_scar_priority":
        failures.append("gate_b_summary_runtime_label_bad")
    selected_ckpt = runtime_root / "checkpoints/checkpoint_best.pt"
    if not selected_ckpt.exists() or summary.get("checkpoint_sha256") != sha256_file(selected_ckpt):
        failures.append("gate_b_selected_checkpoint_hash_mismatch")
    if int(summary.get("post_scar_decision_overwritten_voxels", -1)) != 0:
        failures.append("gate_b_post_scar_overwrite_nonzero")
    if int(overwrite.get("post_scar_decision_overwritten_voxels", -1)) != 0:
        failures.append("gate_b_post_scar_overwrite_audit_nonzero")
    if summary.get("no_t2_edema_delta_exact_zero") is not True:
        failures.append("gate_b_no_t2_edema_not_exact_zero")
    if int(summary.get("scar_activated_cases", 0)) <= 0:
        failures.append("gate_b_scar_activation_missing")
    if int(summary.get("edema_activated_t2_cases", 0)) <= 0:
        failures.append("gate_b_edema_activation_missing")
    if float(summary.get("changed_case_fraction_complete16", 0.0)) <= 0.0:
        failures.append("gate_b_complete16_identity_collapse")

    expected_models = {"A0_nnunet_anchor", "A2_care_dg"}
    expected_pathologies = {"scar", "edema_zone", "pure_edema"}
    for population, csv_path, expected_n in [
        ("fold0_outer44", required_csvs["summary"], 44),
        ("fold0_complete_trimodal16", required_csvs["complete16"], 16),
    ]:
        rows = read_csv_rows(csv_path) if csv_path.exists() else []
        seen = {(row.get("model"), row.get("pathology")) for row in rows if row.get("population") == population}
        for model in expected_models:
            for pathology in expected_pathologies:
                if (model, pathology) not in seen:
                    failures.append(f"gate_b_missing_summary_row:{population}:{model}:{pathology}")
        for row in rows:
            if row.get("population") == population and int(float(row.get("n_cases", -1))) != expected_n:
                failures.append(f"gate_b_summary_n_cases_bad:{population}")

    no_t2_rows = read_csv_rows(required_csvs["no_t2"]) if required_csvs["no_t2"].exists() else []
    if any(row.get("status") != "PASS" or float(row.get("edema_delta_abs_max", -1.0)) != 0.0 for row in no_t2_rows):
        failures.append("gate_b_no_t2_safety_audit_not_exact_PASS")



def validate_gate_b_r1(failures: list[str]) -> None:
    runtime_root = RESULT_ROOT / "runtime/repaired_formal_scar_priority/fold0"
    eval_root = runtime_root / "gate_b_r1_evaluation"
    summary_path = eval_root / "gate_b_r1_summary.json"
    validator_path = eval_root / "gate_b_r1_validator_report.json"
    required = {
        "inner_selection": eval_root / "gate_b_r1_inner_checkpoint_selection.csv",
        "inner_selection_json": eval_root / "gate_b_r1_inner_checkpoint_selection.json",
        "casewise": eval_root / "gate_b_r1_casewise_metrics.csv",
        "summary": eval_root / "gate_b_r1_model_summary.csv",
        "complete16": eval_root / "gate_b_r1_complete16_summary.csv",
        "help_harm": eval_root / "gate_b_r1_help_harm.csv",
        "exact_hd_tail": eval_root / "gate_b_r1_exact_hd_tail_audit.csv",
        "remote_fp": eval_root / "gate_b_r1_remote_fp_audit.csv",
        "component": eval_root / "gate_b_r1_component_audit.csv",
        "transition": eval_root / "gate_b_r1_scar_edema_conflict_transition_matrix.csv",
        "mechanism": eval_root / "gate_b_r1_mechanism_activation_audit.csv",
        "seam": eval_root / "gate_b_r1_seam_audit.csv",
        "no_t2": eval_root / "gate_b_r1_no_t2_safety_audit.csv",
        "post_scar_overwrite": eval_root / "gate_b_r1_post_scar_overwrite_audit.json",
        "summary_json": summary_path,
        "validator": validator_path,
    }
    if not eval_root.exists():
        return
    for name, path in required.items():
        if not path.exists():
            failures.append(f"gate_b_r1_missing_output:{name}")
        elif path.suffix == ".csv" and not read_csv_rows(path):
            failures.append(f"gate_b_r1_empty_output:{name}")
    if not summary_path.exists() or not validator_path.exists():
        return
    summary = load_json(summary_path)
    validator = load_json(validator_path)
    if validator.get("status") != "PASS" or validator.get("failures") not in ([], None):
        failures.append("gate_b_r1_validator_not_PASS")
    if summary.get("outer_val_used_for_selection") is not False:
        failures.append("gate_b_r1_outer_val_used_for_selection")
    if summary.get("post_scar_decision_overwritten_voxels") != 0:
        failures.append("gate_b_r1_post_scar_overwrite_nonzero")
    if summary.get("no_t2_edema_delta_exact_zero") is not True:
        failures.append("gate_b_r1_no_t2_not_exact_zero")
    contract = summary.get("r1_inference_contract", {})
    if contract.get("sliding_window_overlap") != 0.5 or contract.get("gaussian_blending") is not True:
        failures.append("gate_b_r1_inference_contract_not_overlap_gaussian")
    if contract.get("forbidden") != "patch_final_logits_averaging":
        failures.append("gate_b_r1_forbidden_patch_final_average_not_recorded")
    selection_rows = read_csv_rows(required["inner_selection"]) if required["inner_selection"].exists() else []
    if len(selection_rows) != 8:
        failures.append("gate_b_r1_inner_checkpoint_sweep_not_8")
    if any(row.get("outer_val_used") != "False" for row in selection_rows):
        failures.append("gate_b_r1_inner_selection_used_outer_val")
    summary_rows = read_csv_rows(required["summary"]) if required["summary"].exists() else []
    models = {row.get("model") for row in summary_rows}
    for model in ["A0_nnunet_anchor", "A1_direct_residual_control", "A2_care_dg_r1_selected", "A3_no_stage_b_matched_control"]:
        if model not in models:
            failures.append(f"gate_b_r1_missing_ablation_model:{model}")
    sci = summary.get("scientific_gate", {})
    if sci.get("status") not in {"PASS", "FAIL"}:
        failures.append("gate_b_r1_scientific_gate_status_bad")
    if bool(sci.get("scientific_expansion_authorized", False)) != bool(validator.get("scientific_expansion_authorized", False)):
        failures.append("gate_b_r1_scientific_authorization_mismatch")


def validate_gate_b_r2(failures: list[str]) -> None:
    runtime_root = RESULT_ROOT / "runtime/repaired_formal_scar_priority/fold0"
    eval_root = runtime_root / "gate_b_r2_scale_diagnostic"
    csv_path = eval_root / "gate_b_r2_scale_grid_selection.csv"
    runtime_summary_path = eval_root / "gate_b_r2_scale_grid_selection.json"
    runtime_validator_path = eval_root / "gate_b_r2_validator_report.json"
    root_summary_path = RESULT_ROOT / "gate_b_r2_scale_grid_selection.json"
    root_gate_summary_path = RESULT_ROOT / "gate_b_r2_summary.json"
    root_validator_path = RESULT_ROOT / "gate_b_r2_validator_report.json"
    diagnostic_report_path = RESULT_ROOT / "gate_b_r2_diagnostic_report.md"
    required = {
        "scale_grid_csv": csv_path,
        "runtime_scale_grid_json": runtime_summary_path,
        "runtime_validator": runtime_validator_path,
        "root_scale_grid_json": root_summary_path,
        "root_gate_summary": root_gate_summary_path,
        "root_validator": root_validator_path,
        "diagnostic_report": diagnostic_report_path,
    }
    if not eval_root.exists() and not root_gate_summary_path.exists():
        return
    for name, path in required.items():
        if not path.exists():
            failures.append(f"gate_b_r2_missing_output:{name}")
    if not csv_path.exists() or not root_summary_path.exists() or not root_validator_path.exists() or not root_gate_summary_path.exists():
        return
    rows = read_csv_rows(csv_path)
    summary = load_json(root_summary_path)
    gate_summary = load_json(root_gate_summary_path)
    validator = load_json(root_validator_path)
    if len(rows) != 512:
        failures.append(f"gate_b_r2_scale_grid_row_count_not_512:{len(rows)}")
    if any(row.get("outer_val_used") != "False" for row in rows):
        failures.append("gate_b_r2_scale_grid_used_outer_val")
    if any(row.get("status") == "PASS" for row in rows):
        failures.append("gate_b_r2_scale_grid_contains_PASS_candidate")
    if summary.get("status") != "NO_INNER_ELIGIBLE_CANDIDATE" or gate_summary.get("status") != "GATE_B_R2_SCALE_GRID_NO_INNER_ELIGIBLE_CANDIDATE":
        failures.append("gate_b_r2_status_bad")
    if int(summary.get("eligible_count", -1)) != 0 or int(validator.get("eligible_count", -1)) != 0:
        failures.append("gate_b_r2_eligible_count_not_zero")
    if summary.get("outer_val_used") is not False or validator.get("outer_val_used") is not False:
        failures.append("gate_b_r2_outer_val_used")
    if gate_summary.get("outer_fold0_re_evaluated") is not False or validator.get("outer_fold0_re_evaluated") is not False:
        failures.append("gate_b_r2_outer_fold0_re_evaluated")
    if gate_summary.get("scientific_expansion_authorized") is not False:
        failures.append("gate_b_r2_scientific_expansion_not_false")
    if int(summary.get("checkpoint_count", -1)) != 8 or int(summary.get("inner_case_count", -1)) != 12:
        failures.append("gate_b_r2_checkpoint_or_inner_case_count_bad")
    if validator.get("status") != "PASS" or validator.get("failures") not in ([], None):
        failures.append("gate_b_r2_validator_not_PASS")
    selected = summary.get("selected", {})
    if selected.get("status") != "FAIL":
        failures.append("gate_b_r2_selected_not_FAIL")
    if "no_pathology_improves_by_more_than_0.005" not in str(selected.get("failures", "")):
        failures.append("gate_b_r2_selected_missing_scientific_failure")
    if float(selected.get("scar_dice_delta", 0.0)) >= 0.005:
        failures.append("gate_b_r2_selected_scar_delta_unexpectedly_passes_gate")
    if float(selected.get("edema_zone_dice_delta", 0.0)) >= 0.005:
        failures.append("gate_b_r2_selected_edema_zone_delta_unexpectedly_passes_gate")
    if float(selected.get("pure_edema_dice_delta", 0.0)) >= 0.005:
        failures.append("gate_b_r2_selected_pure_edema_delta_unexpectedly_passes_gate")


def validate_packet() -> dict[str, Any]:
    failures: list[str] = []
    missing = [name for name in REQUIRED_W0 if not (RESULT_ROOT / name).exists()]
    failures.extend([f"missing_w0_output:{name}" for name in missing])
    if not missing:
        allocation = load_json(RESULT_ROOT / "existing_allocation_receipt.json")
        assets = load_json(RESULT_ROOT / "input_asset_manifest.json")
        parity = load_json(RESULT_ROOT / "evaluator_parity_report.json")
        if allocation.get("status") != "RUNNING":
            failures.append("allocation_60657290_not_running")
        if assets.get("case_lists", {}).get("myops_train_cases") != 220:
            failures.append("myops_train_case_count_not_220")
        if assets.get("case_lists", {}).get("complete_trimodal_cases") != 80:
            failures.append("complete_trimodal_case_count_not_80")
        if assets.get("case_lists", {}).get("myops_validation_cases") != 15:
            failures.append("myops_validation_case_count_not_15")
        if assets.get("anchor", {}).get("oof_case_count") != 220:
            failures.append("oof_anchor_case_count_not_220")
        if assets.get("anchor", {}).get("hash_completeness") != "COMPLETE_FULL_SHA256":
            failures.append("oof_anchor_full_sha256_not_frozen")
        if parity.get("status") != "PASS":
            failures.append("evaluator_parity_not_PASS")
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in [
            REPO_ROOT / "src/care_myocardium/models/care_dg.py",
            REPO_ROOT / "src/care_myocardium/data/care_dg_dataset.py",
            REPO_ROOT / "src/care_myocardium/training/care_dg_trainer.py",
            REPO_ROOT / "src/care_myocardium/inference/care_dg_predictor.py",
        ]
        if path.exists()
    )
    for token in FORBIDDEN_RUNTIME_TOKENS:
        if token in source_text:
            failures.append(f"forbidden_runtime_token:{token}")
    validate_gate_a_r3(failures)
    validate_gate_b_fold0(failures)
    validate_gate_b_r1(failures)
    validate_gate_b_r2(failures)
    status = "PASS" if not failures else "NEEDS_REPAIR"
    report = {
        "checked_at_utc": now_utc(),
        "task_key": TASK_KEY,
        "status": status,
        "failures": failures,
        "known_bad_failures": [f for f in failures if f.startswith("forbidden_runtime_token")],
    }
    write_json(RESULT_ROOT / "strict_validator_report.json", report)
    return report


def bootstrap() -> dict[str, Any]:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    repair_rows: list[dict[str, Any]] = []
    context = build_context()
    allocation, gpu_lock = build_allocation_receipts()
    assets = build_asset_manifest(repair_rows)
    parity = build_parity_report(repair_rows)
    write_json(RESULT_ROOT / "controller_context.json", context)
    write_csv(
        RESULT_ROOT / "controller_ledger.csv",
        [
            {
                "timestamp_utc": now_utc(),
                "phase": "W0_BOOTSTRAP_AND_PARITY",
                "git_head": context["git_head"].get("stdout", ""),
                "task_hash": context["prompt_hashes"].get(rel(CONTROLLER), ""),
                "job_states": allocation["status"],
                "decision": "NEEDS_REPAIR" if parity["status"] != "PASS" else "W0_READY",
                "next_action": "run evaluator parity before formal training",
            }
        ],
    )
    write_json(RESULT_ROOT / "existing_allocation_receipt.json", allocation)
    write_json(RESULT_ROOT / "existing_allocation_gpu_lock.json", gpu_lock)
    write_json(RESULT_ROOT / "input_asset_manifest.json", assets)
    write_json(RESULT_ROOT / "evaluator_parity_report.json", parity)
    write_csv(RESULT_ROOT / "repair_ledger.csv", repair_rows)
    write_bootstrap_snapshot(context, allocation, assets, parity)
    return validate_packet()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.bootstrap:
        report = bootstrap()
    elif args.validate_only:
        report = validate_packet()
    else:
        parser.error("expected --bootstrap or --validate-only")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
