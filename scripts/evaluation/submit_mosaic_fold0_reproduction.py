#!/usr/bin/env python3
"""Submit the MoSAIC fold0 fair reproduction Slurm dependency chain."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULT_ROOT = REPO_ROOT / "results/20260725_care_myops_mosaic_fold0_reproduction"
STAGE_JOB = REPO_ROOT / "jobs/evaluation/mosaic_fold0_reproduction_stage.sh"
FINALIZER_JOB = REPO_ROOT / "jobs/evaluation/mosaic_fold0_reproduction_finalizer.sh"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    names = ["timestamp", "job_id", "stage", "partition", "dependency", "state", "exit_code", "elapsed", "node_list", "log_path", "submit_stdout", "submit_stderr", "queue_evidence"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=names, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=REPO_ROOT, env=env, text=True, capture_output=True, check=False)


def submit(stage: str, *, dependency: str | None, job_script: Path, partition: str, gres: str, qos: str, job_ids_for_finalizer: str = "") -> tuple[str, subprocess.CompletedProcess[str]]:
    env = os.environ.copy()
    env["RESULT_ROOT"] = str(RESULT_ROOT)
    env["CARE_ROOT"] = str(REPO_ROOT)
    export_parts = [f"RESULT_ROOT={RESULT_ROOT}", f"CARE_ROOT={REPO_ROOT}"]
    if stage not in {"finalizer"}:
        env["MOSAIC_STAGE"] = stage
        export_parts.append(f"MOSAIC_STAGE={stage}")
    if job_ids_for_finalizer:
        env["MOSAIC_JOB_IDS"] = job_ids_for_finalizer
        export_parts.append(f"MOSAIC_JOB_IDS={job_ids_for_finalizer}")
    cmd = ["sbatch", "--parsable", "--export=ALL," + ",".join(export_parts), f"--partition={partition}", f"--qos={qos}", f"--gres={gres}"]
    if dependency:
        cmd.append(f"--dependency={dependency}")
    cmd.append(str(job_script))
    completed = run(cmd, env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"sbatch failed for {stage}: {completed.stderr.strip()}")
    job_id = completed.stdout.strip().split(";")[0]
    if not re.match(r"^[0-9]+", job_id):
        raise RuntimeError(f"cannot parse sbatch job id for {stage}: {completed.stdout!r}")
    return job_id, completed


def queue_snapshot() -> str:
    parts = []
    for cmd in (["squeue", "-p", "htzhulab"], ["squeue", "-p", "a100-gpu"], ["sinfo", "-o", "%P|%a|%l|%D|%t|%G"]):
        completed = run(cmd)
        parts.append("$ " + " ".join(cmd) + "\n" + completed.stdout[:6000] + completed.stderr[:2000])
    return "\n\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--partition", default="htzhulab", choices=["htzhulab", "a100-gpu"])
    args = ap.parse_args()
    if args.partition == "a100-gpu":
        gres = "gpu:nvidia_a100-pcie-40gb:1"
    else:
        gres = "gpu:1"
    qos = "gpu_access"
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    q = queue_snapshot()
    (RESULT_ROOT / "slurm_queue_snapshot_before_submit.txt").write_text(q, encoding="utf-8")
    timestamp = datetime.now(timezone.utc).isoformat()
    rows = []
    coarse, c = submit("coarse", dependency=None, job_script=STAGE_JOB, partition=args.partition, gres=gres, qos=qos)
    rows.append({"timestamp": timestamp, "job_id": coarse, "stage": "coarse", "partition": args.partition, "dependency": "", "state": "SUBMITTED", "submit_stdout": c.stdout.strip(), "submit_stderr": c.stderr.strip(), "queue_evidence": "slurm_queue_snapshot_before_submit.txt"})
    scar, s = submit("scar", dependency=f"afterok:{coarse}", job_script=STAGE_JOB, partition=args.partition, gres=gres, qos=qos)
    rows.append({"timestamp": timestamp, "job_id": scar, "stage": "scar", "partition": args.partition, "dependency": f"afterok:{coarse}", "state": "SUBMITTED", "submit_stdout": s.stdout.strip(), "submit_stderr": s.stderr.strip(), "queue_evidence": "slurm_queue_snapshot_before_submit.txt"})
    edema, e = submit("edema", dependency=f"afterok:{coarse}", job_script=STAGE_JOB, partition=args.partition, gres=gres, qos=qos)
    rows.append({"timestamp": timestamp, "job_id": edema, "stage": "edema", "partition": args.partition, "dependency": f"afterok:{coarse}", "state": "SUBMITTED", "submit_stdout": e.stdout.strip(), "submit_stderr": e.stderr.strip(), "queue_evidence": "slurm_queue_snapshot_before_submit.txt"})
    job_ids = ":".join([coarse, scar, edema])
    finalizer, f = submit("finalizer", dependency=f"afterany:{scar}:{edema}:{coarse}", job_script=FINALIZER_JOB, partition=args.partition, gres=gres, qos=qos, job_ids_for_finalizer=job_ids)
    rows.append({"timestamp": timestamp, "job_id": finalizer, "stage": "finalizer", "partition": args.partition, "dependency": f"afterany:{scar}:{edema}:{coarse}", "state": "SUBMITTED", "submit_stdout": f.stdout.strip(), "submit_stderr": f.stderr.strip(), "queue_evidence": "slurm_queue_snapshot_before_submit.txt"})
    write_csv(RESULT_ROOT / "slurm_attempts.csv", rows)
    write_json = lambda path, payload: path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_json(RESULT_ROOT / "slurm_submission_receipt.json", {"status": "SUBMITTED", "partition": args.partition, "coarse_job_id": coarse, "scar_job_id": scar, "edema_job_id": edema, "finalizer_job_id": finalizer, "dependency_semantics": {"scar": "afterok coarse", "edema": "afterok coarse", "finalizer": "afterany coarse/scar/edema"}, "a100_mirror_submitted": False, "a100_mirror_reason": "a100 queue was not shorter at submission; snapshot recorded"})
    print(json.dumps({"coarse": coarse, "scar": scar, "edema": edema, "finalizer": finalizer}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
