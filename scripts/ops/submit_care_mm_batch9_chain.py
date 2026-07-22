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
TASK_KEY = "20260722_care_myops_batch9_reliable_label_distillation"
RESULT_ROOT = REPO_ROOT / "results" / TASK_KEY


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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


def submit_seed(seed: str, script: str, initial_dependency: str = "") -> dict[str, str]:
    root = f"results/{TASK_KEY}/runtime/seed{seed}"
    direct = sbatch(
        script,
        {
            "BATCH9_VARIANT": "student_direct_reliable",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "500",
            "BATCH9_TOTAL_STEPS": "125000",
            "BATCH9_RUNTIME_ROOT": f"{root}/student_direct_reliable",
        },
        dependency=initial_dependency,
    )
    direct_ckpt = f"{root}/student_direct_reliable/checkpoint_epoch500.pt"
    teacher = sbatch(
        script,
        {
            "BATCH9_VARIANT": "teacher_full_view",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/teacher_full_view",
            "BATCH9_WARM_START": direct_ckpt,
        },
        dependency=f"afterok:{direct}",
    )
    teacher_ckpt = f"{root}/teacher_full_view/checkpoint_epoch100.pt"
    moddrop = sbatch(
        script,
        {
            "BATCH9_VARIANT": "student_moddrop_control",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/student_moddrop_control",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_TEACHER_CHECKPOINT": teacher_ckpt,
        },
        dependency=f"afterok:{teacher}",
    )
    distill = sbatch(
        script,
        {
            "BATCH9_VARIANT": "student_reliable_distill",
            "BATCH9_SEED": seed,
            "BATCH9_EPOCHS": "100",
            "BATCH9_TOTAL_STEPS": "25000",
            "BATCH9_RUNTIME_ROOT": f"{root}/student_reliable_distill",
            "BATCH9_WARM_START": direct_ckpt,
            "BATCH9_TEACHER_CHECKPOINT": teacher_ckpt,
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
    args = parser.parse_args()
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

    seed23_script = "jobs/care_mm/run_batch9_stage.sh"
    seed24_script = "jobs/care_mm/run_batch9_stage.sh" if args.temporary_htzhulab_all else "jobs/care_mm/run_batch9_stage_a100.sh"
    seed23 = submit_seed("20260723", seed23_script, initial_dependency)
    seed24 = submit_seed("20260724", seed24_script, initial_dependency)
    all_jobs = [seed23["direct"], seed23["teacher"], seed23["moddrop_control"], seed23["reliable_distill"], seed24["direct"], seed24["teacher"], seed24["moddrop_control"], seed24["reliable_distill"]]
    finalizer = sbatch("jobs/care_mm/run_batch9_finalizer.sh", {}, dependency="afterany:" + ":".join(all_jobs))
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
        "status": "SUBMITTED_FORMAL_CHAIN",
        "seed20260723": seed23,
        "seed20260724": seed24,
        "finalizer_afterany": finalizer,
        "training_dependencies": "afterok within seed",
        "finalizer_dependency": "afterany over all formal jobs",
        "initial_preflight_dependency": initial_dependency,
        "resource_override": resource_override,
    }
    chain_path.write_text(json.dumps(ledger, indent=2, sort_keys=True), encoding="utf-8")
    if args.temporary_htzhulab_all:
        (RESULT_ROOT / "slurm_resource_override.json").write_text(json.dumps({"schema_version": 1, **resource_override}, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(ledger, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
