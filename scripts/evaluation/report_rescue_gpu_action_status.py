#!/usr/bin/env python3
"""Write GPU queue/action status for the 20260629 rescue goal."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "results/20260629_rescue_goal"

JOB_IDS = {
    "repaired_proposal_formal": "57094448",
    "srr_v2_basic_formal": "57094446",
    "srr_v2_missing_variants_a100": "57095505",
    "srr_v2_missing_variants_htzhulab_fallback": "57272337",
    "cascade_formal_array": "57272502",
    "cascade_component_guard_revision": "57274444",
    "cascade_signal_seek_revision": "57275246",
    "srr_v2_light_refine_extras": "57277361",
    "srr_v2_capacity_extras": "57279322",
}

RECHECK_INTERVAL_HOURS = 2
MAX_RECHECKS = 12

ROUTE_ROOTS = {
    "repaired_proposal": REPO_ROOT / "results/20260629_repaired_proposal_repeat",
    "srr_v2": REPO_ROOT / "results/20260629_srr_v2_unet_core",
    "srr_v2_htzhulab_fallback": REPO_ROOT / "results/20260629_srr_v2_unet_core_htzhulab_fallback",
    "cascade_teacher": REPO_ROOT / "results/20260629_cascade_teacher_route",
    "cascade_teacher_revision_component_guard": REPO_ROOT / "results/20260629_cascade_teacher_route/revision_component_guard",
    "cascade_teacher_revision_signal_seek": REPO_ROOT / "results/20260629_cascade_teacher_route/revision_signal_seek",
    "srr_v2_light_refine_extras": REPO_ROOT / "results/20260629_srr_v2_unet_core/light_refine_extras",
    "srr_v2_capacity_extras": REPO_ROOT / "results/20260629_srr_v2_unet_core/capacity_extras",
}

PARTITION_PRIORITY = [
    ("htzhulab", 1, "preferred"),
    ("a100-gpu", 2, "fallback_after_htzhulab_long_wait"),
    ("volta-gpu", 3, "fallback_after_a100_long_wait"),
]


def run_command(args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(args, cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.strip()


def compact_counts(values: list[str]) -> str:
    counts: dict[str, int] = {}
    for value in values:
        key = value or "UNKNOWN"
        counts[key] = counts.get(key, 0) + 1
    return "; ".join(f"{key}:{counts[key]}" for key in sorted(counts))


def parse_pipe_table(text: str) -> list[dict[str, str]]:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0].split("|")
    rows = []
    for line in lines[1:]:
        values = line.split("|")
        rows.append({key: values[idx] if idx < len(values) else "" for idx, key in enumerate(header)})
    return rows


def squeue_row(job_id: str) -> dict[str, str]:
    code, out = run_command(
        [
            "squeue",
            "-h",
            "-j",
            job_id,
            "-o",
            "%i|%P|%j|%T|%M|%R|%S",
        ]
    )
    if code != 0:
        return {"squeue_error": out}
    lines = [line for line in out.splitlines() if line.strip()]
    if not lines:
        return {}
    # Collapse arrays or multiple rows into one compact detail string.
    parts = []
    first: dict[str, str] = {}
    for line in lines:
        values = line.split("|")
        row = {
            "JOBID": values[0] if len(values) > 0 else "",
            "PARTITION": values[1] if len(values) > 1 else "",
            "NAME": values[2] if len(values) > 2 else "",
            "STATE": values[3] if len(values) > 3 else "",
            "TIME": values[4] if len(values) > 4 else "",
            "REASON": values[5] if len(values) > 5 else "",
            "START_TIME": values[6] if len(values) > 6 else "",
        }
        if not first:
            first = row
        parts.append(
            "{JOBID}:{STATE}:{PARTITION}:{TIME}:{REASON}:{START_TIME}".format(**row)
        )
    first["DETAIL_ROWS"] = "; ".join(parts)
    return first


def sacct_row(job_id: str) -> dict[str, str]:
    code, out = run_command(
        [
            "sacct",
            "-j",
            job_id,
            "--format=JobID,JobName%30,Partition,State,Elapsed,Submit,Start,End,ExitCode",
            "-P",
        ]
    )
    if code != 0:
        return {"sacct_error": out}
    rows = parse_pipe_table(out)
    if not rows:
        return {}
    # Prefer the array parent / batch parent row when present.
    for row in rows:
        if row.get("JobID") == job_id or row.get("JobID", "").startswith(f"{job_id}_"):
            return row
    return rows[0]


def _parse_slurm_time(value: str) -> datetime | None:
    if not value or value in {"Unknown", "N/A", "None"}:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def wait_policy_fields(sacct: dict[str, str], scheduler_state: str) -> dict[str, Any]:
    if scheduler_state != "PENDING":
        return {
            "submit_time": sacct.get("Submit", ""),
            "pending_hours": "",
            "recheck_interval_hours": "",
            "recheck_windows_elapsed": "",
            "next_recheck_after": "",
            "max_recheck_after": "",
            "wait_policy_status": "not_pending",
        }
    submit_time = _parse_slurm_time(sacct.get("Submit", ""))
    if submit_time is None:
        return {
            "submit_time": sacct.get("Submit", ""),
            "pending_hours": "",
            "recheck_interval_hours": RECHECK_INTERVAL_HOURS,
            "recheck_windows_elapsed": "",
            "next_recheck_after": "",
            "max_recheck_after": "",
            "wait_policy_status": "pending_submit_time_unknown",
        }
    now = datetime.now()
    pending_hours = max(0.0, (now - submit_time).total_seconds() / 3600.0)
    windows_elapsed = int(pending_hours // RECHECK_INTERVAL_HOURS)
    next_recheck = submit_time + timedelta(hours=(windows_elapsed + 1) * RECHECK_INTERVAL_HOURS)
    max_recheck = submit_time + timedelta(hours=MAX_RECHECKS * RECHECK_INTERVAL_HOURS)
    if windows_elapsed >= MAX_RECHECKS:
        wait_status = "max_rechecks_elapsed_requires_partition_and_work_audit"
    else:
        wait_status = "continue_monitoring"
    return {
        "submit_time": sacct.get("Submit", ""),
        "pending_hours": f"{pending_hours:.2f}",
        "recheck_interval_hours": RECHECK_INTERVAL_HOURS,
        "recheck_windows_elapsed": min(windows_elapsed, MAX_RECHECKS),
        "next_recheck_after": next_recheck.strftime("%Y-%m-%d %H:%M:%S"),
        "max_recheck_after": max_recheck.strftime("%Y-%m-%d %H:%M:%S"),
        "wait_policy_status": wait_status,
    }


def variants_ready(route: str, variants: str) -> tuple[bool, str]:
    root = ROUTE_ROOTS.get(route)
    if root is None:
        return False, ""
    details = []
    all_ready = True
    for variant in [item for item in variants.split(";") if item]:
        vdir = root / "variants" / variant
        summary = vdir / "summary.json"
        pred_dir = vdir / "predictions/fold_0/checkpoint_best"
        subgroup = vdir / "subgroup_metrics.csv"
        ready = summary.is_file() and pred_dir.is_dir() and subgroup.is_file()
        if not ready and summary.is_file():
            try:
                payload = json.loads(summary.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            cascade_pred = Path(str(payload.get("prediction_dir", ""))) if payload.get("prediction_dir") else None
            pred_count = len(list(cascade_pred.glob("*.nii.gz"))) if cascade_pred and cascade_pred.is_dir() else 0
            comparison = vdir / "baseline_vs_refiner_by_subset.csv"
            metrics = vdir / "round10_fold0_very_short_metrics.csv"
            ready = pred_count >= 44 and comparison.is_file() and metrics.is_file()
        all_ready = all_ready and ready
        details.append(f"{variant}:{'ready' if ready else 'missing'}")
    return all_ready, "; ".join(details)


def job_status_row(name: str, job_id: str, route: str, variants: str, artifact_route: str | None = None) -> dict[str, Any]:
    sq = squeue_row(job_id)
    sa = sacct_row(job_id)
    scheduler_state = sq.get("STATE") or sa.get("State") or "UNKNOWN"
    artifacts_ready, artifact_detail = variants_ready(artifact_route or route, variants)
    if scheduler_state in {"FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"} and artifacts_ready:
        action_status = "DONE_RECOVERED"
    elif scheduler_state in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
        action_status = "DONE" if scheduler_state == "COMPLETED" else "ENDED_WITH_ATTENTION"
    elif scheduler_state in {"PENDING", "RUNNING", "CONFIGURING", "COMPLETING"}:
        action_status = "QUEUED_OR_RUNNING"
    elif sq or sa:
        action_status = "UNKNOWN_RECHECK"
    else:
        action_status = "NO_SCHEDULER_RECORD"
    row = {
        "item": name,
        "category": "slurm_job",
        "route": route,
        "variants": variants,
        "status": action_status,
        "job_id": job_id,
        "partition": sq.get("PARTITION", "") or sa.get("Partition", ""),
        "scheduler_state": scheduler_state,
        "reason": sq.get("REASON", ""),
        "elapsed": sq.get("TIME") or sa.get("Elapsed", ""),
        "start_time": sq.get("START_TIME") or sa.get("Start", ""),
        "exit_code": sa.get("ExitCode", ""),
        "required_action": "monitor" if action_status == "QUEUED_OR_RUNNING" else "inspect_outputs",
        "evidence": sq.get("DETAIL_ROWS") or sa.get("JobID", ""),
        "detail": artifact_detail,
    }
    row.update(wait_policy_fields(sa, scheduler_state))
    return row


def build_rows() -> list[dict[str, Any]]:
    rows = [
        job_status_row(
            "repaired_proposal_formal",
            JOB_IDS["repaired_proposal_formal"],
            "repaired_proposal",
            "repaired_uncertainty_hardneg;repaired_posneg_scar_hardneg;repaired_joint_calibrated_proposal",
        ),
        job_status_row(
            "srr_v2_basic_formal",
            JOB_IDS["srr_v2_basic_formal"],
            "srr_v2",
            "srr_v2_multiscale_private_basic",
        ),
        job_status_row(
            "srr_v2_missing_variants_a100",
            JOB_IDS["srr_v2_missing_variants_a100"],
            "srr_v2",
            "srr_v2_multiscale_private_proposal;srr_v2_proposal_uncertainty_hardneg",
        ),
        job_status_row(
            "srr_v2_missing_variants_htzhulab_fallback",
            JOB_IDS["srr_v2_missing_variants_htzhulab_fallback"],
            "srr_v2",
            "srr_v2_multiscale_private_proposal;srr_v2_proposal_uncertainty_hardneg",
            artifact_route="srr_v2_htzhulab_fallback",
        ),
        job_status_row(
            "cascade_formal_array",
            JOB_IDS["cascade_formal_array"],
            "cascade_teacher",
            "nnunet_anatomy_prior_refiner;nnunet_pathology_teacher_srr_refiner;coarse_to_fine_srr_roi",
        ),
        job_status_row(
            "cascade_component_guard_revision",
            JOB_IDS["cascade_component_guard_revision"],
            "cascade_teacher_revision_component_guard",
            "nnunet_pathology_teacher_srr_refiner_component_guard;coarse_to_fine_srr_roi_component_guard",
        ),
        job_status_row(
            "cascade_signal_seek_revision",
            JOB_IDS["cascade_signal_seek_revision"],
            "cascade_teacher_revision_signal_seek",
            "nnunet_pathology_teacher_srr_refiner_signal_seek;coarse_to_fine_srr_roi_signal_seek",
        ),
        job_status_row(
            "srr_v2_light_refine_extras",
            JOB_IDS["srr_v2_light_refine_extras"],
            "srr_v2_light_refine_extras",
            "srr_v2_light_refine_lowmix;srr_v2_light_refine_hardneg",
        ),
        job_status_row(
            "srr_v2_capacity_extras",
            JOB_IDS["srr_v2_capacity_extras"],
            "srr_v2_capacity_extras",
            "srr_v2_capacity12_proposal;srr_v2_capacity12_hardneg",
        ),
    ]
    return rows


def partition_status_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for partition, rank, role in PARTITION_PRIORITY:
        code, out = run_command(["squeue", "-h", "-p", partition, "-o", "%T|%R"])
        states: list[str] = []
        reasons: list[str] = []
        error = ""
        if code != 0:
            error = out
        else:
            for line in out.splitlines():
                if not line.strip():
                    continue
                parts = line.split("|", 1)
                state = parts[0] if parts else ""
                reason = parts[1] if len(parts) > 1 else ""
                states.append(state)
                if state == "PENDING":
                    reasons.append(reason)
        sinfo_code, sinfo_out = run_command(["sinfo", "-h", "-p", partition, "-o", "%P|%a|%l|%D|%t|%G"])
        rows.append(
            {
                "partition": partition,
                "priority_rank": rank,
                "policy_role": role,
                "total_jobs": len(states),
                "pending_jobs": sum(1 for state in states if state == "PENDING"),
                "running_jobs": sum(1 for state in states if state == "RUNNING"),
                "other_jobs": sum(1 for state in states if state not in {"PENDING", "RUNNING"}),
                "pending_reasons": compact_counts(reasons),
                "state_counts": compact_counts(states),
                "sinfo": sinfo_out if sinfo_code == 0 else "",
                "error": error or (sinfo_out if sinfo_code != 0 else ""),
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "item",
        "category",
        "route",
        "variants",
        "status",
        "job_id",
        "partition",
        "scheduler_state",
        "reason",
        "elapsed",
        "submit_time",
        "pending_hours",
        "recheck_interval_hours",
        "recheck_windows_elapsed",
        "next_recheck_after",
        "max_recheck_after",
        "wait_policy_status",
        "start_time",
        "exit_code",
        "required_action",
        "evidence",
        "detail",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_partition_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "partition",
        "priority_rank",
        "policy_role",
        "total_jobs",
        "pending_jobs",
        "running_jobs",
        "other_jobs",
        "pending_reasons",
        "state_counts",
        "sinfo",
        "error",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    open_rows = [row for row in rows if row["status"] in {"QUEUED_OR_RUNNING", "ACTION_REQUIRED"}]
    lines = [
        "# 20260629 Rescue Goal GPU Action Status",
        "",
        f"- generated_at: `{now}`",
        f"- open_actions: `{len(open_rows)}`",
        f"- recheck_policy: `{RECHECK_INTERVAL_HOURS}h interval, max {MAX_RECHECKS} checks before partition/work audit`",
        "",
        "| item | route | status | job_id | partition | scheduler_state | pending_hours | wait_policy_status | next_recheck_after | required_action |",
        "| --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {item} | {route} | {status} | {job_id} | {partition} | {scheduler_state} | {pending_hours} | {wait_policy_status} | {next_recheck_after} | {required_action} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This file records scheduler/action state only; it is not a route selection.",
            "- `ACTION_REQUIRED` rows are not submitted jobs. They require explicit approval after command-review rejection.",
            "- Existing queued jobs should be monitored before duplicating variants on another partition.",
            "- The two-hour wait policy is advisory state tracking; it does not by itself authorize duplicate GPU submissions or blocked completion.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_partition_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = [
        "# 20260629 Rescue Goal Partition Status",
        "",
        f"- generated_at: `{now}`",
        "- routing_priority: `htzhulab > a100-gpu > volta-gpu`",
        "",
        "| partition | rank | role | pending | running | other | pending reasons |",
        "| --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| {partition} | {priority_rank} | {policy_role} | {pending_jobs} | {running_jobs} | {other_jobs} | {pending_reasons} |".format(
                **row
            )
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This is a read-only queue snapshot for routing decisions; it does not authorize a new GPU submission.",
            "- `sinfo` details and any query errors are preserved in `gpu_partition_status.csv`.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir
    rows = build_rows()
    partition_rows = partition_status_rows()
    write_csv(out_dir / "gpu_action_status.csv", rows)
    write_markdown(out_dir / "gpu_action_status.md", rows)
    write_partition_csv(out_dir / "gpu_partition_status.csv", partition_rows)
    write_partition_markdown(out_dir / "gpu_partition_status.md", partition_rows)
    print({"rows": len(rows), "open_actions": sum(1 for row in rows if row["status"] in {"QUEUED_OR_RUNNING", "ACTION_REQUIRED"})})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
