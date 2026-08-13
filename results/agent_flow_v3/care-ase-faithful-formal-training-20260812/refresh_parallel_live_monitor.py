#!/usr/bin/env python3
"""Refresh lightweight live-monitor receipts for the CARE-ASE formal run."""

from __future__ import annotations

import csv
import json
import re
import statistics
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path


MAIN_ROOT = Path("/users/a/e/aereinh/CARE")
WORKTREE = MAIN_ROOT / ".worktrees/care-ase-faithful-formal-training-20260812"
RESULT_ROOT = WORKTREE / "results/agent_flow_v3/care-ase-faithful-formal-training-20260812"

TRAINING_JOBS = {"2": "63244446", "3": "63247953"}
BASE_JOB_IDS = [
    "63244446",
    "63247953",
    "63248355",
    "63260064",
    "63297258",
    "63344579",
    "63344580",
    "63344581",
    "63357146",
    "63357148",
    "63357150",
    "63357152",
    "63357154",
]
FOLD_RUNTIME_DIRS = {"2": "fold_2", "3": "fold_3_parallel"}
WATCHER_FILES = {
    "auto_watcher": "core_fair_eval_checkpoint_watcher_status.json",
    "a100_mirror_watcher": "core_fair_eval_a100_mirror_watcher_status.json",
    "auto_watcher_ledger": "core_fair_eval_checkpoint_watcher_ledger.json",
    "a100_mirror_ledger": "core_fair_eval_a100_mirror_ledger.json",
    "duplicate_cleanup_watcher": "core_fair_eval_duplicate_cleanup_status.json",
    "duplicate_cleanup_ledger": "core_fair_eval_duplicate_cleanup_ledger.json",
    "formal_inner_watcher": "formal_inner_eval_watcher_status.json",
    "same_exposure_watcher": "same_exposure_fair_watcher_status.json",
    "same_exposure_ledger": "same_exposure_fair_watcher_ledger.json",
}


def stage_for_step(step: int) -> str:
    if step < 2000:
        return "A"
    if step < 10000:
        return "B"
    return "C"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run(cmd: list[str]) -> dict[str, object]:
    proc = subprocess.run(cmd, text=True, capture_output=True)
    return {"cmd": cmd, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def read_json(path: Path) -> dict[str, object] | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def current_training_jobs() -> dict[str, str]:
    jobs = dict(TRAINING_JOBS)
    retry = read_json(RESULT_ROOT / "fold2_step06000_same_scope_retry_submission.json") or {}
    retry_job = retry.get("retry_job") if isinstance(retry.get("retry_job"), dict) else {}
    retry_job_id = retry_job.get("job_id") if isinstance(retry_job, dict) else None
    if retry_job_id:
        jobs["2"] = str(retry_job_id)
    return jobs


def fair_submission_receipts() -> list[dict[str, object]]:
    receipts: list[dict[str, object]] = []
    pattern = re.compile(r"core_fair_panel_fold(?P<fold>\d+)_step(?P<step>\d+)_submission\.json$")
    for path in sorted(RESULT_ROOT.glob("core_fair_panel_fold*_step*_submission.json")):
        match = pattern.match(path.name)
        if not match:
            continue
        payload = read_json(path) or {}
        job = payload.get("fair_eval_job") if isinstance(payload.get("fair_eval_job"), dict) else {}
        job_id = job.get("job_id") if isinstance(job, dict) else None
        if not job_id:
            continue
        monitor = payload.get("monitor_outputs") or payload.get("monitor_outputs_expected") or {}
        output_dir = None
        if isinstance(monitor, dict):
            packet = monitor.get("monitor_packet")
            if packet:
                output_dir = str(Path(str(packet)).parent)
        receipts.append(
            {
                "created_utc": payload.get("created_utc"),
                "fold": int(match.group("fold")),
                "step": int(match.group("step")),
                "job_id": str(job_id),
                "slurm_job_id": str(job_id),
                "job_name": job.get("job_name"),
                "partition": job.get("partition"),
                "qos": job.get("qos"),
                "checkpoint": payload.get("read_only_checkpoint_input"),
                "output_dir": output_dir,
                "script": job.get("script"),
                "status": payload.get("status"),
                "outer_accessed": payload.get("outer_accessed", False),
            }
        )
    return receipts


def parse_squeue(stdout: str) -> dict[str, dict[str, str]]:
    states: dict[str, dict[str, str]] = {}
    for line in stdout.splitlines()[1:]:
        parts = line.split("|")
        if len(parts) >= 9:
            states[parts[0]] = {
                "job_id": parts[0],
                "job_name": parts[1],
                "partition": parts[2],
                "state": parts[3],
                "elapsed": parts[4],
                "time_left": parts[5],
                "node_or_reason": parts[6],
                "tres_per_node": parts[7],
                "nodes": parts[8],
            }
    return states


def parse_sacct(stdout: str) -> dict[str, dict[str, str]]:
    states: dict[str, dict[str, str]] = {}
    for line in stdout.splitlines()[1:]:
        parts = line.split("|")
        if len(parts) < 8:
            continue
        job_id = parts[0].split(".")[0]
        if job_id in states and parts[0] != job_id:
            continue
        states[job_id] = {
            "job_id": job_id,
            "job_name": parts[1],
            "partition": parts[2],
            "state": parts[3],
            "exit_code": parts[4],
            "elapsed": parts[5],
            "time_limit": parts[6],
            "node_or_reason": parts[7],
        }
    return states


def collect_job_ids() -> list[str]:
    ids = set(BASE_JOB_IDS)
    ids.update(current_training_jobs().values())
    for submission in fair_submission_receipts():
        if submission.get("job_id"):
            ids.add(str(submission["job_id"]))
    for filename in [
        "core_fair_eval_job_manifest.json",
        "formal_inner_eval_job_manifest.json",
        "checkpoint_manifest.json",
        "core_fair_eval_checkpoint_watcher_ledger.json",
        "core_fair_eval_a100_mirror_ledger.json",
    ]:
        data = read_json(RESULT_ROOT / filename) or {}
        for job in data.get("jobs", []):
            if job.get("job_id"):
                ids.add(str(job["job_id"]))
            if job.get("slurm_job_id"):
                ids.add(str(job["slurm_job_id"]))
        for checkpoint in data.get("checkpoints", []):
            for job_id in checkpoint.get("core_fair_eval_job_ids", []):
                ids.add(str(job_id))
        for submission in data.get("submissions", []):
            if submission.get("job_id"):
                ids.add(str(submission["job_id"]))
            if submission.get("slurm_job_id"):
                ids.add(str(submission["slurm_job_id"]))
    return sorted(ids, key=int)


def refresh_fair_eval_job_manifest(
    squeue_states: dict[str, dict[str, str]],
    sacct_states: dict[str, dict[str, str]],
    updated: str,
) -> None:
    manifest_path = RESULT_ROOT / "core_fair_eval_job_manifest.json"
    manifest = read_json(manifest_path)
    if not manifest:
        manifest = {
            "schema": "CARE_ASE_CORE_FAIR_EVAL_JOB_MANIFEST_V1",
            "task_key": "care-ase-faithful-formal-training-20260812",
            "jobs": [],
            "outer_accessed": False,
            "routing_review_summary": "initialized from fair-eval submission receipts",
        }
    known_job_ids = {str(job.get("job_id")) for job in manifest.get("jobs", []) if job.get("job_id")}
    for submission in fair_submission_receipts():
        job_id = submission.get("job_id") or submission.get("slurm_job_id")
        if not job_id or str(job_id) in known_job_ids:
            continue
        manifest.setdefault("jobs", []).append(dict(submission))
        known_job_ids.add(str(job_id))
    for ledger_name in ["core_fair_eval_checkpoint_watcher_ledger.json", "core_fair_eval_a100_mirror_ledger.json"]:
        ledger = read_json(RESULT_ROOT / ledger_name) or {}
        for submission in ledger.get("submissions", []):
            job_id = submission.get("job_id") or submission.get("slurm_job_id")
            if not job_id or str(job_id) in known_job_ids:
                continue
            manifest.setdefault("jobs", []).append(
                {
                    "created_utc": submission.get("created_utc"),
                    "fold": submission.get("fold"),
                    "step": submission.get("step"),
                    "job_id": str(job_id),
                    "slurm_job_id": str(job_id),
                    "job_name": submission.get("job_name"),
                    "partition": submission.get("partition"),
                    "qos": submission.get("qos"),
                    "checkpoint": submission.get("checkpoint"),
                    "output_dir": submission.get("output_dir"),
                    "lock_dir": submission.get("lock_dir"),
                    "script": submission.get("script"),
                    "status": submission.get("status"),
                    "outer_accessed": submission.get("outer_accessed", False),
                }
            )
            known_job_ids.add(str(job_id))
    cleanup = read_json(RESULT_ROOT / "core_fair_eval_duplicate_cleanup_ledger.json") or {}
    cancelled = {str(event.get("job_id")) for event in cleanup.get("events", []) if event.get("job_id")}
    for job in manifest.get("jobs", []):
        job_id = str(job.get("job_id", ""))
        state = squeue_states.get(job_id) or sacct_states.get(job_id)
        output_dir = Path(str(job.get("output_dir", "")))
        output_present = (output_dir / "monitor_packet.json").exists() and (output_dir / "casewise_metrics.csv").exists()
        job["output_present"] = output_present
        if state:
            job["state"] = state.get("state")
            job["state_source"] = "squeue" if job_id in squeue_states else "sacct"
            job["slurm_state"] = state
        elif job_id in cancelled:
            job["state"] = "CANCELLED_OR_SCANCEL_SUBMITTED"
            job["state_source"] = "duplicate_cleanup_ledger"
        elif output_present:
            job["state"] = "OUTPUT_PRESENT"
            job["state_source"] = "output_files"
        else:
            job["state_source"] = "manifest_unverified"
        if output_present:
            job["aggregation_status"] = "OUTPUT_PRESENT"
        elif job.get("state") in {"COMPLETED", "COMPLETED+"}:
            job["aggregation_status"] = "NEEDS_OUTPUT_CHECK"
        else:
            job["aggregation_status"] = "PENDING_OR_NONTERMINAL"
    manifest["updated_utc"] = updated
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def refresh_formal_inner_eval_job_manifest(
    squeue_states: dict[str, dict[str, str]],
    sacct_states: dict[str, dict[str, str]],
    updated: str,
) -> None:
    manifest_path = RESULT_ROOT / "formal_inner_eval_job_manifest.json"
    manifest = read_json(manifest_path)
    if not manifest:
        return
    for job in manifest.get("jobs", []):
        job_id = str(job.get("job_id", ""))
        state = squeue_states.get(job_id) or sacct_states.get(job_id)
        output_dir = Path(str(job.get("output_dir", "")))
        output_present = (output_dir / "monitor_packet.json").exists() and (output_dir / "casewise_metrics.csv").exists()
        job["output_present"] = output_present
        if state:
            job["state"] = state.get("state")
            job["state_source"] = "squeue" if job_id in squeue_states else "sacct"
            job["slurm_state"] = state
        elif output_present:
            job["state"] = "OUTPUT_PRESENT"
            job["state_source"] = "output_files"
        else:
            job["state_source"] = "manifest_unverified"
        if output_present:
            job["aggregation_status"] = "OUTPUT_PRESENT"
        elif job.get("state") in {"COMPLETED", "COMPLETED+"}:
            job["aggregation_status"] = "NEEDS_OUTPUT_CHECK"
        else:
            job["aggregation_status"] = "PENDING_OR_NONTERMINAL"
    manifest["updated_utc"] = updated
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def fold_log_summary(fold: str, subdir: str) -> dict[str, object]:
    runtime_dir = RESULT_ROOT / "runtime" / subdir
    rows: list[tuple[int, str | None, float, float]] = []
    bad: list[tuple[str, int, str, str]] = []
    for path in sorted(runtime_dir.glob("training_log_*.csv")):
        try:
            with path.open(newline="") as f:
                for row in csv.DictReader(f):
                    try:
                        step = int(row["optimizer_step"])
                        stage = row.get("stage")
                        wall = float(row.get("step_wall_seconds") or 0)
                        for key, value in row.items():
                            if str(value).lower() in {"nan", "inf", "-inf"}:
                                bad.append((path.name, step, key, str(value)))
                        rows.append((step, stage, wall, path.stat().st_mtime))
                    except Exception:
                        continue
        except FileNotFoundError:
            continue

    dedup = {step: (stage, wall, mtime) for step, stage, wall, mtime in rows}
    last = max(dedup) if dedup else 0
    recent = [value[1] for _, value in sorted(dedup.items())[-20:]] if dedup else []
    checkpoints: list[int] = []
    for path in runtime_dir.glob("checkpoint_step*.pt"):
        try:
            checkpoints.append(int(path.stem.replace("checkpoint_step", "")))
        except ValueError:
            continue
    latest_checkpoint = max(checkpoints) if checkpoints else None
    next_checkpoint = next((step for step in range(1000, 14001, 1000) if step > (latest_checkpoint or 0)), None)
    median_step_seconds = statistics.median(recent) if recent else None
    remaining_steps = max(0, 14000 - last)
    projected_finish = (
        (datetime.now(timezone.utc) + timedelta(seconds=remaining_steps * median_step_seconds))
        .isoformat()
        .replace("+00:00", "Z")
        if median_step_seconds
        else None
    )
    return {
        "fold": int(fold),
        "subdir": subdir,
        "last_completed_optimizer_step": last,
        "stage": dedup[last][0] if last else None,
        "recent20_median_sec_per_optimizer_step": median_step_seconds,
        "remaining_steps": remaining_steps,
        "projected_finish_utc": projected_finish,
        "latest_log_mtime": time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(dedup[last][2])) if last else None,
        "latest_checkpoint_step": latest_checkpoint,
        "next_checkpoint_step": next_checkpoint,
        "nan_or_inf_count": len(bad),
        "nan_or_inf_examples": bad[:5],
    }


def refresh_checkpoint_manifest(job_state: dict[str, dict[str, str]], updated: str) -> list[dict[str, object]]:
    manifest_path = RESULT_ROOT / "checkpoint_manifest.json"
    manifest = read_json(manifest_path) or {}
    manifest["updated_utc"] = updated
    fair_manifest = read_json(RESULT_ROOT / "core_fair_eval_job_manifest.json") or {}
    formal_manifest = read_json(RESULT_ROOT / "formal_inner_eval_job_manifest.json") or {}
    fair_jobs_by_key: dict[tuple[int, int], list[dict[str, object]]] = {}
    for job in fair_manifest.get("jobs", []):
        try:
            key = (int(job["fold"]), int(job["step"]))
        except Exception:
            continue
        fair_jobs_by_key.setdefault(key, []).append(job)
    formal_jobs_by_key: dict[tuple[int, int], list[dict[str, object]]] = {}
    for job in formal_manifest.get("jobs", []):
        try:
            key = (int(job["fold"]), int(job["step"]))
        except Exception:
            continue
        formal_jobs_by_key.setdefault(key, []).append(job)

    checkpoints = manifest.setdefault("checkpoints", [])
    by_key: dict[tuple[int, int], dict[str, object]] = {}
    for checkpoint in checkpoints:
        try:
            by_key[(int(checkpoint["fold"]), int(checkpoint["step"]))] = checkpoint
        except Exception:
            continue

    for fold_text, subdir in FOLD_RUNTIME_DIRS.items():
        fold = int(fold_text)
        runtime_dir = RESULT_ROOT / "runtime" / subdir
        for checkpoint_path in sorted(runtime_dir.glob("checkpoint_step*.pt")):
            try:
                step = int(checkpoint_path.stem.replace("checkpoint_step", ""))
            except ValueError:
                continue
            key = (fold, step)
            checkpoint = by_key.get(key)
            if checkpoint is None:
                checkpoint = {"fold": fold, "step": step}
                checkpoints.append(checkpoint)
                by_key[key] = checkpoint
            sha_path = Path(str(checkpoint_path) + ".sha256")
            verified = read_json(Path(str(checkpoint_path) + ".verified.json")) or {}
            receipt = read_json(runtime_dir / f"checkpoint_step{step:05d}_receipt.json") or {}
            full_reload = read_json(runtime_dir / f"checkpoint_step{step:05d}_full_reload_receipt.json") or {}
            fair_jobs = fair_jobs_by_key.get(key, [])
            fair_job_ids = [str(job.get("job_id")) for job in fair_jobs if job.get("job_id")]
            fair_partitions = sorted({str(job.get("partition")) for job in fair_jobs if job.get("partition")})
            formal_output_dir = RESULT_ROOT / "inner_checkpoint_monitor" / f"fold_{fold}" / f"step{step:05d}"
            formal_present = (formal_output_dir / "monitor_packet.json").exists() and (formal_output_dir / "casewise_metrics.csv").exists()
            checkpoint.update(
                {
                    "checkpoint_path": str(checkpoint_path),
                    "checkpoint_sha256": sha_path.read_text().split()[0] if sha_path.exists() else checkpoint.get("checkpoint_sha256"),
                    "schema_version": receipt.get("schema_version", checkpoint.get("schema_version")),
                    "stage": receipt.get("stage") or checkpoint.get("stage") or stage_for_step(step),
                    "verified_status": verified.get("status", checkpoint.get("verified_status")),
                    "full_reload_status": full_reload.get("status") or checkpoint.get("full_reload_status") or verified.get("full_reload_status"),
                    "full_reload_logit_parity": full_reload.get("logits_max_abs_error", checkpoint.get("full_reload_logit_parity")),
                    "required_fields_present": checkpoint.get("required_fields_present", True),
                    "core_fair_eval_dir": str(RESULT_ROOT / "core_fair_panel_monitor" / f"fold_{fold}" / f"step{step:05d}"),
                    "core_fair_eval_job_ids": fair_job_ids,
                    "core_fair_eval_bound_partitions": fair_partitions,
                    "core_fair_eval_job_id": next((str(job.get("job_id")) for job in fair_jobs if job.get("partition") == "htzhulab" and job.get("job_id")), None),
                    "core_fair_eval_mirror_job_ids": [str(job.get("job_id")) for job in fair_jobs if job.get("partition") == "a100-gpu" and job.get("job_id")],
                    "formal_inner_eval_dir": str(formal_output_dir),
                    "formal_inner_eval_status": (
                        "NOT_FORMAL_BOUNDARY"
                        if step % 2000
                        else ("PRESENT" if formal_present else ("JOB_RECORDED" if formal_jobs_by_key.get(key) else "MISSING_JOB_AND_OUTPUT"))
                    ),
                }
            )
    checkpoints.sort(key=lambda item: (int(item.get("fold", 0)), int(item.get("step", 0))))
    manifest["checkpoint_count"] = len(checkpoints)
    missing: list[dict[str, object]] = []
    for checkpoint in manifest.get("checkpoints", []):
        states = []
        for job_id in checkpoint.get("core_fair_eval_job_ids", []):
            if job_id in job_state:
                states.append(job_state[job_id])
        checkpoint["core_fair_eval_job_states"] = states
        output_dir = Path(checkpoint.get("core_fair_eval_dir", ""))
        output_present = (output_dir / "monitor_packet.json").exists() and (output_dir / "casewise_metrics.csv").exists()
        checkpoint["core_fair_eval_output_present"] = output_present
        if not checkpoint.get("core_fair_eval_job_ids") and not output_present:
            missing.append({"fold": checkpoint.get("fold"), "step": checkpoint.get("step")})
        elif output_present:
            checkpoint["core_fair_eval_status"] = "PRESENT"
        elif checkpoint.get("core_fair_eval_job_ids"):
            checkpoint["core_fair_eval_status"] = "PENDING_SUBMITTED_EXTRA_JOBS"
    manifest["new_checkpoint_without_fair_eval_job"] = missing
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return missing


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def formal_inner_eval_progress(summaries: list[dict[str, object]]) -> dict[str, object]:
    manifest = read_json(RESULT_ROOT / "formal_inner_eval_job_manifest.json") or {}
    jobs_by_fold_step: dict[tuple[int, int], list[dict[str, object]]] = {}
    for job in manifest.get("jobs", []):
        try:
            key = (int(job["fold"]), int(job["step"]))
        except Exception:
            continue
        jobs_by_fold_step.setdefault(key, []).append(job)

    rows: list[dict[str, object]] = []
    missing: list[dict[str, int]] = []
    for summary in summaries:
        fold = int(summary["fold"])
        latest = int(summary["latest_checkpoint_step"] or 0)
        for step in range(2000, min(latest, 14000) + 1, 2000):
            output_dir = RESULT_ROOT / "inner_checkpoint_monitor" / f"fold_{fold}" / f"step{step:05d}"
            output_present = (output_dir / "monitor_packet.json").exists() and (output_dir / "casewise_metrics.csv").exists()
            jobs = jobs_by_fold_step.get((fold, step), [])
            status = "OUTPUT_PRESENT" if output_present else ("JOB_RECORDED" if jobs else "MISSING_JOB_AND_OUTPUT")
            row = {
                "fold": fold,
                "step": step,
                "status": status,
                "output_present": output_present,
                "output_dir": str(output_dir),
                "job_ids": [job.get("job_id") for job in jobs],
                "job_states": [job.get("state") for job in jobs],
            }
            rows.append(row)
            if status == "MISSING_JOB_AND_OUTPUT":
                missing.append({"fold": fold, "step": step})
    return {"rows": rows, "missing": missing}


def main() -> None:
    updated = utc_now()
    all_job_ids = collect_job_ids()
    squeue = run(["squeue", "-j", ",".join(all_job_ids), "-o", "%i|%j|%P|%T|%M|%L|%R|%b|%D"])
    sacct = run(
        [
            "sacct",
            "-j",
            ",".join(all_job_ids),
            "--format=JobID,JobName,Partition,State,ExitCode,Elapsed,Timelimit,NodeList",
            "-P",
        ]
    )
    job_state = parse_squeue(str(squeue["stdout"])) if squeue["returncode"] == 0 else {}
    sacct_state = parse_sacct(str(sacct["stdout"])) if sacct["returncode"] == 0 else {}
    refresh_fair_eval_job_manifest(job_state, sacct_state, updated)
    refresh_formal_inner_eval_job_manifest(job_state, sacct_state, updated)
    summaries = [fold_log_summary(fold, subdir) for fold, subdir in FOLD_RUNTIME_DIRS.items()]
    formal_inner = formal_inner_eval_progress(summaries)

    progress = []
    throughput = []
    training_jobs = current_training_jobs()
    for summary in summaries:
        fold = str(summary["fold"])
        job_id = training_jobs[fold]
        slurm = job_state.get(job_id, {})
        progress.append(
            {
                "updated_utc": updated,
                "fold": fold,
                "job_id": job_id,
                "slurm_state": slurm.get("state", "UNKNOWN"),
                "node_or_reason": slurm.get("node_or_reason", "UNKNOWN"),
                "elapsed": slurm.get("elapsed", "UNKNOWN"),
                "time_left": slurm.get("time_left", "UNKNOWN"),
                "last_completed_optimizer_step": str(summary["last_completed_optimizer_step"]),
                "stage": summary["stage"],
                "latest_checkpoint_step": str(summary["latest_checkpoint_step"] or ""),
                "next_checkpoint_step": str(summary["next_checkpoint_step"] or ""),
                "target_step": "14000",
                "nan_or_inf_count": str(summary["nan_or_inf_count"]),
                "outer_accessed": "False",
            }
        )
        throughput.append(
            {
                "updated_utc": updated,
                "fold": fold,
                "recent20_median_sec_per_optimizer_step": str(summary["recent20_median_sec_per_optimizer_step"]),
                "remaining_steps": str(summary["remaining_steps"]),
                "projected_finish_utc": summary["projected_finish_utc"],
                "basis": "training_log_recent20_excludes_fair_eval",
            }
        )

    write_csv(RESULT_ROOT / "training_progress.csv", progress)
    write_csv(RESULT_ROOT / "throughput.csv", throughput)
    missing = refresh_checkpoint_manifest(job_state, updated)

    watchers = {}
    for key, filename in WATCHER_FILES.items():
        path = RESULT_ROOT / filename
        watchers[key] = read_json(path)

    live = {
        "schema": "CARE_ASE_PARALLEL_LIVE_MONITOR_V1",
        "updated_utc": updated,
        "task_key": "care-ase-faithful-formal-training-20260812",
        "goal_status": "RUNNING_NOT_COMPLETE",
        "outer_accessed": False,
        "fair_comparison_execution_policy": (
            "authorized eval-only sbatch to htzhulab/a100-gpu when needed; "
            "htzhulab primary watcher, a100 mirror watcher, and duplicate cleanup "
            "watcher are active; jobs are read-only and use isolated outputs/locks"
        ),
        "training_progress": [
            {
                **row,
                "fold": int(row["fold"]),
                "last_completed_optimizer_step": int(row["last_completed_optimizer_step"]),
                "latest_checkpoint_step": int(row["latest_checkpoint_step"] or 0),
                "next_checkpoint_step": int(row["next_checkpoint_step"] or 0),
                "target_step": 14000,
                "nan_or_inf_count": int(row["nan_or_inf_count"]),
                "outer_accessed": False,
            }
            for row in progress
        ],
        "throughput": [
            {
                **row,
                "fold": int(row["fold"]),
                "recent20_median_sec_per_optimizer_step": float(row["recent20_median_sec_per_optimizer_step"]),
                "remaining_steps": int(row["remaining_steps"]),
            }
            for row in throughput
        ],
        "new_checkpoint_without_fair_eval_job": missing,
        "formal_inner_eval_progress": formal_inner["rows"],
        "new_formal_inner_eval_without_job": formal_inner["missing"],
        "checkpoint_manifest_path": str(RESULT_ROOT / "checkpoint_manifest.json"),
        "core_fair_eval_job_manifest_path": str(RESULT_ROOT / "core_fair_eval_job_manifest.json"),
        "formal_inner_eval_job_manifest_path": str(RESULT_ROOT / "formal_inner_eval_job_manifest.json"),
        "a100_mirror_watcher_status_path": str(RESULT_ROOT / "core_fair_eval_a100_mirror_watcher_status.json"),
        "duplicate_cleanup_watcher_status_path": str(RESULT_ROOT / "core_fair_eval_duplicate_cleanup_status.json"),
        "watchers": watchers,
        "slurm": {"squeue": squeue, "sacct": sacct},
    }
    (RESULT_ROOT / "CURRENT_LIVE_MONITOR.json").write_text(json.dumps(live, indent=2, sort_keys=True) + "\n")
    snapshot = RESULT_ROOT / f"parallel_live_monitor_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    snapshot.write_text(json.dumps(live, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "updated_utc": updated,
                "snapshot": str(snapshot),
                "training_progress": progress,
                "throughput": throughput,
                "new_checkpoint_without_fair_eval_job": missing,
                "new_formal_inner_eval_without_job": formal_inner["missing"],
                "cleanup_events": len((watchers.get("duplicate_cleanup_ledger") or {}).get("events", [])),
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
