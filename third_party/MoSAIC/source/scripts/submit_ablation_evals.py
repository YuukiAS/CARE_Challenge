#!/usr/bin/env python3
"""Submit full-pipeline evaluation for every ablation variant whose training is done.

The per-run experiment_result.json written by train_single_experiment.py scores the
Stage-2 model in isolation, which is not comparable to the headline numbers (those
come from the fused cascade). This script re-scores each finished variant through
eval_5fold_full.py so the ablation table and the main table share one scale.

Idempotent: skips variants already evaluated, and variants still training.

    python scripts/submit_ablation_evals.py            # report status, submit ready ones
    python scripts/submit_ablation_evals.py --dry-run  # report only
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDS = [0, 1, 2, 3, 4]

TRACKS = {
    "myops": {"partition": "l40-gpu", "time": "04:00:00"},
    "cine": {"partition": "l40-gpu", "time": "06:00:00"},
}

SBATCH = """#!/bin/bash
#SBATCH --job-name={name}
#SBATCH --partition={partition}
#SBATCH --qos=gpu_access
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=48g
#SBATCH --time={time}
#SBATCH --output={log_dir}/{name}.out
#SBATCH --error={log_dir}/{name}.err

set -eo pipefail
cd {root}
source ~/.bashrc
conda activate stai_tune
python scripts/eval_5fold_full.py --track {track} --fine-root {fine_root} --tag {tag}
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-partial", action="store_true",
                    help="evaluate a variant even if some folds are missing")
    args = ap.parse_args()

    log_dir = ROOT / "ablations" / "eval" / "_logs"
    job_dir = ROOT / "ablations" / "eval" / "_jobs"
    log_dir.mkdir(parents=True, exist_ok=True)
    job_dir.mkdir(parents=True, exist_ok=True)

    queued = subprocess.run(["squeue", "-u", "shucheng", "-h", "-o", "%j"],
                            capture_output=True, text=True).stdout.split()

    ready, waiting, done = [], [], []
    for track, spec in TRACKS.items():
        variant_root = ROOT / "ablations" / track
        if not variant_root.exists():
            continue
        for vdir in sorted(p for p in variant_root.iterdir()
                           if p.is_dir() and not p.name.startswith("_")):
            variant = vdir.name
            finished = [f for f in FOLDS
                        if (vdir / f"fold{f}" / "experiment_result.json").exists()]
            tag = variant
            out_json = ROOT / "paper" / "results" / f"{track}_{tag}.json"
            name = f"mos_eval_{track}_{tag}"

            if out_json.exists():
                done.append(f"{track}/{variant}")
                continue
            if name in queued:
                waiting.append(f"{track}/{variant} (eval queued)")
                continue
            if len(finished) < len(FOLDS) and not args.allow_partial:
                waiting.append(f"{track}/{variant} ({len(finished)}/{len(FOLDS)} folds trained)")
                continue
            if not finished:
                waiting.append(f"{track}/{variant} (0 folds trained)")
                continue

            job = job_dir / f"{name}.sh"
            job.write_text(SBATCH.format(
                name=name, partition=spec["partition"], time=spec["time"],
                log_dir=log_dir, root=ROOT, track=track,
                fine_root=vdir, tag=tag))
            job.chmod(0o755)
            ready.append((f"{track}/{variant}", job))

    print(f"already evaluated : {len(done)}")
    for d in done:
        print(f"    {d}")
    print(f"still waiting     : {len(waiting)}")
    for w in waiting:
        print(f"    {w}")
    print(f"ready to evaluate : {len(ready)}")
    for label, _ in ready:
        print(f"    {label}")

    if args.dry_run or not ready:
        return
    print()
    for label, job in ready:
        r = subprocess.run(["sbatch", str(job)], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  {r.stdout.strip().split()[-1]}  {label}")
        else:
            print(f"  FAILED {label}: {r.stderr.strip()}")


if __name__ == "__main__":
    main()
