#!/usr/bin/env python3
"""Submit the CARE Batch9 formal Slurm dependency chain."""

from __future__ import annotations

import csv
import json
import re
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TASK_KEY = "20260723_care_myops_batch9_exposed_issues_repair"
TASK_KEY = DEFAULT_TASK_KEY
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def set_task(task_key: str) -> None:
    global TASK_KEY, RESULT_ROOT
    TASK_KEY = task_key
    RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def common_env(config_path: str, validation_interval_epochs: str = "25") -> dict[str, str]:
    return {
        "CARE_MM_TASK_KEY": TASK_KEY,
        "CARE_MM_CONFIG_PATH": config_path,
        "BATCH9_VALIDATION_INTERVAL_EPOCHS": validation_interval_epochs,
    }


def require_preflight(allow_pending_preflight_job: str = "", temporary_htzhulab_all: bool = False) -> None:
    rows = read_csv(RESULT_ROOT / "gpu_preflight_attempts.csv")
    passed = {row["partition"] for row in rows if row.get("status") == "PASS"}
    if temporary_htzhulab_all:
        if "htzhulab" not in passed:
            raise SystemExit("Batch9 htzhulab override submission blocked; htzhulab preflight PASS is required")
        return
    missing = {"htzhulab", "a100-gpu"} - passed
    if missing and not allow_pending_preflight_job:
        raise SystemExit(f"Batch9 formal submission blocked; missing preflight PASS for: {sorted(missing)}")
    if allow_pending_preflight_job and "htzhulab" not in passed:
        raise SystemExit("Batch9 dependency submission blocked; htzhulab preflight PASS is required before dependent queueing")


def selected_direct_checkpoint(seed: str) -> str:
    rows = read_csv(RESULT_ROOT / "direct_checkpoint_selection.csv")
    selected = [
        r for r in rows
        if r.get("seed") == seed and r.get("variant") == "student_direct_reliable"
        and (r.get("status") == "SELECTED" or str(r.get("selected", "")).lower() in {"1", "true", "yes"})
    ]
    if not selected:
        raise SystemExit(f"missing selected direct checkpoint for seed {seed}; run direct finalizer first")
    checkpoint = selected[0].get("selected_checkpoint") or selected[0].get("checkpoint")
    if not checkpoint:
        raise SystemExit(f"selected direct checkpoint path empty for seed {seed}")
    return checkpoint


def selected_teacher_checkpoint(seed: str) -> str:
    receipt = RESULT_ROOT / f"runtime/seed{seed}/teacher_full_view/training_receipt.json"
    if not receipt.is_file():
        raise SystemExit(f"missing teacher receipt for seed {seed}; run teacher-only stage first")
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    checkpoint = payload.get("selected_checkpoint") or payload.get("checkpoint")
    if not checkpoint:
        raise SystemExit(f"selected teacher checkpoint path empty for seed {seed}")
    return str(checkpoint)


def require_direct_gate_passed() -> None:
    gate = RESULT_ROOT / "direct_gate.json"
    if not gate.is_file():
        raise SystemExit("direct_gate.json missing; run direct finalizer before teacher")
    payload = json.loads(gate.read_text(encoding="utf-8"))
    if payload.get("continuation_allowed") is not True:
        raise SystemExit("direct gate did not pass; teacher/control/distill submission is forbidden")


def require_coverage_gate_passed() -> None:
    gate = RESULT_ROOT / "distillation_coverage_gate.json"
    if not gate.is_file():
        raise SystemExit("distillation coverage gate missing; run teacher-only coverage first")
    payload = json.loads(gate.read_text(encoding="utf-8"))
    if payload.get("matched_control_distill_authorized") is not True:
        raise SystemExit("distillation coverage gate did not pass; matched control/distill submission is forbidden")


def submit_teacher_seed(seed: str, script: str, *, config_path: str, validation_interval_epochs: str) -> dict[str, str]:
    root = f"results/{TASK_KEY}/runtime/seed{seed}"
    direct_ckpt = selected_direct_checkpoint(seed)
    teacher = sbatch(
        script,
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_VARIANT": "teacher_full_view",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/teacher_full_view",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_LR": "0.001",
        },
    )
    coverage = sbatch(
        "jobs/care_mm/run_batch9_coverage.sh",
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_SEED": seed,
            "BATCH9_TEACHER_CHECKPOINT": "from-receipt",
        },
        dependency=f"afterok:{teacher}",
    )
    return {"seed": seed, "teacher": teacher, "coverage": coverage, "direct_selected_checkpoint": direct_ckpt}


def submit_matched_seed(seed: str, script: str, *, config_path: str, validation_interval_epochs: str) -> dict[str, str]:
    root = f"results/{TASK_KEY}/runtime/seed{seed}"
    direct_ckpt = selected_direct_checkpoint(seed)
    teacher_ckpt = selected_teacher_checkpoint(seed)
    moddrop = sbatch(
        script,
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_VARIANT": "student_moddrop_control",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/student_moddrop_control",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_TEACHER_CHECKPOINT": teacher_ckpt,
            "BATCH9_LR": "0.001",
        },
    )
    distill = sbatch(
        script,
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_VARIANT": "student_reliable_distill",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/student_reliable_distill",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_TEACHER_CHECKPOINT": teacher_ckpt,
            "BATCH9_LR": "0.001",
        },
    )
    return {"seed": seed, "moddrop_control": moddrop, "reliable_distill": distill, "direct_selected_checkpoint": direct_ckpt, "teacher_selected_checkpoint": teacher_ckpt}


def sbatch(script: str, env: dict[str, str], dependency: str = "") -> str:
    cmd = ["sbatch"]
    if dependency:
        cmd.extend(["--dependency", dependency])
    export = ",".join([f"{k}={v}" for k, v in env.items()])
    cmd.extend(["--export", f"ALL,{export}" if export else "ALL", script])
    out = subprocess.check_output(cmd, cwd=REPO_ROOT, text=True).strip()
    match = re.search(r"Submitted batch job (\d+)", out)
    if not match:
        raise RuntimeError(f"cannot parse sbatch output: {out}")
    return match.group(1)


def direct_runtime_name(attempt_label: str) -> str:
    label = attempt_label.strip()
    if not label:
        return "student_direct_reliable"
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", label):
        raise SystemExit("--attempt-label may contain only letters, digits, underscore, dash, and dot")
    return f"student_direct_reliable__{label}"


def submit_seed(
    seed: str,
    script: str,
    initial_dependency: str = "",
    *,
    config_path: str,
    direct_only: bool,
    validation_interval_epochs: str,
    attempt_label: str,
) -> dict[str, str]:
    root = f"results/{TASK_KEY}/runtime/seed{seed}"
    runtime_name = direct_runtime_name(attempt_label)
    direct = sbatch(
        script,
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_VARIANT": "student_direct_reliable",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "500",
            "BATCH9_TOTAL_STEPS": "125000",
            "BATCH9_RUNTIME_ROOT": f"{root}/{runtime_name}",
            "BATCH9_LR": "0.01",
        },
        dependency=initial_dependency,
    )
    direct_ckpt = f"{root}/{runtime_name}/checkpoint_epoch500.pt"
    if direct_only:
        return {"seed": seed, "direct": direct, "runtime_variant": runtime_name}
    teacher = sbatch(
        script,
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_VARIANT": "teacher_full_view",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/teacher_full_view",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_LR": "0.001",
        },
        dependency=f"afterok:{direct}",
    )
    teacher_ckpt = f"{root}/teacher_full_view/checkpoint_epoch100.pt"
    moddrop = sbatch(
        script,
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_VARIANT": "student_moddrop_control",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/student_moddrop_control",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_TEACHER_CHECKPOINT": teacher_ckpt,
            "BATCH9_LR": "0.001",
        },
        dependency=f"afterok:{teacher}",
    )
    distill = sbatch(
        script,
        {
            **common_env(config_path, validation_interval_epochs),
            "BATCH9_VARIANT": "student_reliable_distill",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/student_reliable_distill",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_TEACHER_CHECKPOINT": teacher_ckpt,
            "BATCH9_LR": "0.001",
        },
        dependency=f"afterok:{teacher}",
    )
    return {
        "seed": seed,
        "direct": direct,
        "teacher": teacher,
        "moddrop_control": moddrop,
        "reliable_distill": distill,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pending-preflight-job", default="", help="Queue formal jobs behind afterok:<jobid> while a required preflight is pending.")
    parser.add_argument("--temporary-htzhulab-all", action="store_true", help="User-authorized temporary resource override: run both Batch9 seeds on htzhulab after a100 pending became too long.")
    parser.add_argument("--resource-override-reason", default="", help="Short reason recorded in the resource override receipt when --temporary-htzhulab-all is used.")
    parser.add_argument("--task-key", default=DEFAULT_TASK_KEY)
    parser.add_argument("--config-path", default="configs/care_mm/batch9_exposed_issues_repair.yaml")
    parser.add_argument("--direct-only", action="store_true")
    parser.add_argument("--teacher-only", action="store_true")
    parser.add_argument("--matched-only", action="store_true")
    parser.add_argument("--validation-interval-epochs", default="25")
    parser.add_argument("--attempt-label", default="", help="Optional isolated runtime suffix for direct-only restarts.")
    args = parser.parse_args()
    set_task(args.task_key)
    require_preflight(args.pending_preflight_job, temporary_htzhulab_all=args.temporary_htzhulab_all)
    initial_dependency = f"afterok:{args.pending_preflight_job}" if args.pending_preflight_job else ""
    if args.temporary_htzhulab_all and initial_dependency:
        raise SystemExit("--temporary-htzhulab-all cannot be combined with --pending-preflight-job")

    chain_path = RESULT_ROOT / "slurm_formal_chain.json"
    if chain_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prior = json.loads(chain_path.read_text(encoding="utf-8"))
        prior["superseded_at"] = stamp
        prior["superseded_reason"] = args.resource_override_reason or "superseded_by_resource_override"
        (RESULT_ROOT / f"slurm_formal_chain_superseded_{stamp}.json").write_text(json.dumps(prior, indent=2, sort_keys=True), encoding="utf-8")

    modes = [args.direct_only, args.teacher_only, args.matched_only]
    if sum(bool(v) for v in modes) > 1:
        raise SystemExit("choose only one of --direct-only, --teacher-only, or --matched-only")
    seed23_script = "jobs/care_mm/run_batch9_stage.sh"
    seed24_script = "jobs/care_mm/run_batch9_stage.sh" if args.temporary_htzhulab_all else "jobs/care_mm/run_batch9_stage_a100.sh"
    finalizer_env = common_env(args.config_path, args.validation_interval_epochs)
    if args.teacher_only:
        require_direct_gate_passed()
        seed23 = submit_teacher_seed("20260723", seed23_script, config_path=args.config_path, validation_interval_epochs=args.validation_interval_epochs)
        seed24 = submit_teacher_seed("20260724", seed24_script, config_path=args.config_path, validation_interval_epochs=args.validation_interval_epochs)
        all_jobs = [seed23["teacher"], seed23["coverage"], seed24["teacher"], seed24["coverage"]]
        finalizer_env |= {"BATCH9_FINALIZER_TEACHER_ONLY": "1"}
    elif args.matched_only:
        require_direct_gate_passed()
        require_coverage_gate_passed()
        seed23 = submit_matched_seed("20260723", seed23_script, config_path=args.config_path, validation_interval_epochs=args.validation_interval_epochs)
        seed24 = submit_matched_seed("20260724", seed24_script, config_path=args.config_path, validation_interval_epochs=args.validation_interval_epochs)
        all_jobs = [seed23["moddrop_control"], seed23["reliable_distill"], seed24["moddrop_control"], seed24["reliable_distill"]]
    else:
        seed23 = submit_seed("20260723", seed23_script, initial_dependency, config_path=args.config_path, direct_only=args.direct_only, validation_interval_epochs=args.validation_interval_epochs, attempt_label=args.attempt_label)
        seed24 = submit_seed("20260724", seed24_script, initial_dependency, config_path=args.config_path, direct_only=args.direct_only, validation_interval_epochs=args.validation_interval_epochs, attempt_label=args.attempt_label)
        if args.direct_only:
            all_jobs = [seed23["direct"], seed24["direct"]]
            finalizer_env |= {"BATCH9_FINALIZER_DIRECT_ONLY": "1"}
        else:
            raise SystemExit("full direct+teacher+matched chain is disabled; use direct-only, teacher-only after gate, then matched-only after coverage")
    finalizer = sbatch("jobs/care_mm/run_batch9_finalizer.sh", finalizer_env, dependency="afterany:" + ":".join(all_jobs))
    resource_override = {
        "enabled": bool(args.temporary_htzhulab_all),
        "authorized_by_user_in_controller_thread": bool(args.temporary_htzhulab_all),
        "reason": args.resource_override_reason if args.temporary_htzhulab_all else "",
        "forbidden_changes_still_forbidden": ["model", "loss", "seed", "epoch_budget", "step_budget", "data_scope", "validation_upload", "hosted_claim"],
        "seed20260723_partition": "htzhulab",
        "seed20260724_partition": "htzhulab" if args.temporary_htzhulab_all else "a100-gpu",
    }
    ledger = {
        "schema_version": 1,
        "status": "SUBMITTED_DIRECT_ONLY_CHAIN" if args.direct_only else ("SUBMITTED_TEACHER_ONLY_CHAIN" if args.teacher_only else "SUBMITTED_MATCHED_ONLY_CHAIN"),
        "seed20260723": seed23,
        "seed20260724": seed24,
        "finalizer_afterany": finalizer,
        "training_dependencies": "afterok within seed",
        "finalizer_dependency": "afterany over all formal jobs",
        "initial_preflight_dependency": initial_dependency,
        "resource_override": resource_override,
    }
    chain_path.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")
    allowlist_path = RESULT_ROOT / "formal_runtime_allowlist.json"
    existing_allowlist = json.loads(allowlist_path.read_text(encoding="utf-8")) if allowlist_path.is_file() else {}
    if args.direct_only:
        allowlist = {
            "schema_version": 1,
            "status": "PASS",
            "direct_runtime_variants": {
                "20260723": [seed23.get("runtime_variant", "student_direct_reliable")],
                "20260724": [seed24.get("runtime_variant", "student_direct_reliable")],
            },
            "reason": "formal direct evidence namespace for current submitted chain",
        }
    else:
        allowlist = existing_allowlist or {
            "schema_version": 1,
            "status": "FAIL",
            "direct_runtime_variants": {},
            "reason": "missing direct allowlist; teacher/matched submission should be blocked by prior gates",
        }
    ledger["formal_runtime_allowlist"] = allowlist
    (RESULT_ROOT / "formal_runtime_allowlist.json").write_text(json.dumps(allowlist, indent=2, sort_keys=True), encoding="utf-8")
    chain_path.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")
    if args.temporary_htzhulab_all:
        (RESULT_ROOT / "slurm_resource_override.json").write_text(json.dumps({"schema_version": 1, **resource_override}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(ledger, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
