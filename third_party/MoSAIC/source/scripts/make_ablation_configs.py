#!/usr/bin/env python3
"""Generate ablation configs and SLURM job scripts for the MoSAIC paper.

Every ablation retrains ONLY the Stage-2 model and reuses the frozen Stage-1
coarse predictions already sitting in grid_output*/5fold/fold*/coarse_predictions,
so each variant sees an identical anatomical prior. Stage-1 is never a confound.

Usage:
    python scripts/make_ablation_configs.py --track cine                 # write configs + sbatch
    python scripts/make_ablation_configs.py --track cine --submit        # ... and sbatch them
    python scripts/make_ablation_configs.py --track myops --folds 0 1 2
"""
from __future__ import annotations

import argparse
import copy
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = None  # set via --data-dir argument
CONDA_ENV = "stai_tune"


def deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


# ---------------------------------------------------------------------------
# CineMyoPS. Base = configs/cine_fine.yaml + the CF06 overrides that
# 5fold_train_all.build_cine_fine_config applies to the reported main model.
# ---------------------------------------------------------------------------
CINE_BASE_OVERRIDE = {
    "loss": {"class_weights": [1.0, 1.0, 5.0]},
    "training": {"max_epochs": 150},
}

CINE_VARIANTS = {
    # C1: pathology head reads the raw frame instead of the motion field.
    # This is the central claim of the paper -- motion is better evidence than
    # intensity for cine scar. The motion-dependent aux losses become vacuous,
    # so they are switched off rather than left to contribute zero gradient.
    "no_motion": {
        "model": {"pathology_input": "intensity"},
        "loss": {"cine_aux_weights": {"motion": 0.0, "smooth": 0.0}},
    },
    # C2: keep motion, drop the flow regulariser.
    "no_smooth": {"loss": {"cine_aux_weights": {"smooth": 0.0}}},
    # C3: keep motion, drop warped-anatomy temporal consistency.
    "no_consistency": {"loss": {"cine_aux_weights": {"consistency": 0.0}}},
    # C4: single ED frame -- no temporal context at all.
    "ed_only": {
        "model": {"num_frames": 1},
        "data": {"max_cine_frames": 1},
        "loss": {"cine_aux_weights": {"motion": 0.0, "smooth": 0.0, "consistency": 0.0}},
    },
}

# ---------------------------------------------------------------------------
# MyoPS. Base = configs/myops_fine.yaml (the F01 scar expert, used as-is by
# 5fold_train_all.build_myops_fine_config).
# ---------------------------------------------------------------------------
MYOPS_VARIANTS = {
    "no_tps": {"model": {"use_tps": False}},
    "no_spg": {"model": {"use_spg": False}},
    "no_consistency": {"loss": {"consistency_weight": 0.0}},
    "no_lesion_loss": {
        "loss": {
            "pathology_tversky_weight": 0.0,
            "pathology_focal_weight": 0.0,
            "class_specific_pathology": {
                "edema": {"tversky_weight": 0.0, "focal_weight": 0.0},
                "scar": {"tversky_weight": 0.0, "focal_weight": 0.0},
            },
        }
    },
    "no_cascade": {"data": {"disable_coarse_prior": True}},
    "earlyfusion": {"model": {"arch": "2d_earlyfusion"}},
    "no_supmask": {"loss": {"ignore_supervision_mask": True}},
}

TRACKS = {
    "cine": {
        "base_config": ROOT / "configs" / "cine_fine.yaml",
        "base_override": CINE_BASE_OVERRIDE,
        "variants": CINE_VARIANTS,
        "track_arg": "cinemyops",
        "manifest": ROOT / "cache" / "cine_manifest.jsonl",
        "coarse_root": ROOT / "grid_output_cine" / "5fold",
        "z_spacing_aug": True,          # the reported main model is fine_v2
        "partition": "a100-gpu",
        "time": "36:00:00",             # measured 17 h/fold on the previous GPU
        "mem": "48g",
        "cpus": 4,
    },
    "myops": {
        "base_config": ROOT / "configs" / "myops_fine.yaml",
        "base_override": {},
        "variants": MYOPS_VARIANTS,
        "track_arg": "myops",
        "manifest": ROOT / "cache" / "manifest.jsonl",
        "coarse_root": ROOT / "grid_output" / "5fold",
        "z_spacing_aug": False,
        "partition": "l40-gpu",
        "time": "08:00:00",             # measured 2.2 h/fold
        "mem": "48g",
        "cpus": 4,
    },
}

SBATCH_TEMPLATE = """#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --qos=gpu_access
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem}
#SBATCH --time={time}
#SBATCH --output={log_dir}/{job_name}.out
#SBATCH --error={log_dir}/{job_name}.err

# NB: no `set -u` -- the system /etc/bashrc references an unbound BASHRCSOURCED.
set -eo pipefail
cd {root}
source ~/.bashrc
conda activate {env}

echo "=== [$(date)] {job_name} ==="
python scripts/train_single_experiment.py \\
    --config {config} \\
    --stage fine \\
    --fold {fold} \\
    --data-dir {data_dir} \\
    --output-dir {output_dir} \\
    --cache-dir {cache_dir} \\
    --track {track_arg} \\
    --manifest {manifest} \\
    --coarse-pred-dir {coarse_pred_dir} \\
    --skip-preprocess{z_flag}
echo "=== [$(date)] {job_name} DONE ==="
"""


def validate(track: str, variant: str, cfg: dict) -> None:
    """Fail loudly on the config traps that would silently waste GPU-days."""
    if track == "cine":
        model_frames = int(cfg["model"]["num_frames"])
        data_frames = int(cfg["data"]["max_cine_frames"])
        if model_frames != data_frames:
            raise ValueError(
                f"[{track}/{variant}] model.num_frames={model_frames} != "
                f"data.max_cine_frames={data_frames}; the dataset would feed a "
                f"different T than the network was built with."
            )
        pi = cfg["model"].get("pathology_input", "flow")
        if pi not in ("flow", "intensity", "none"):
            raise ValueError(f"[{track}/{variant}] bad pathology_input={pi!r}")
    else:
        arch = cfg["model"].get("arch", "2d_multi")
        if arch not in ("2d_multi", "2d_earlyfusion"):
            raise ValueError(f"[{track}/{variant}] bad arch={arch!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--track", required=True, choices=sorted(TRACKS))
    parser.add_argument("--folds", type=int, nargs="+", default=[0, 1, 2, 3, 4])
    parser.add_argument("--variants", type=str, nargs="+", default=None)
    parser.add_argument("--data-dir", type=str, required=True, help="Path to Myo_train data directory")
    parser.add_argument("--submit", action="store_true", help="sbatch the generated jobs")
    parser.add_argument("--partition", type=str, default=None, help="override partition")
    args = parser.parse_args()

    global DATA_DIR
    DATA_DIR = args.data_dir

    spec = TRACKS[args.track]
    base_cfg = yaml.safe_load(spec["base_config"].read_text())
    base_cfg = deep_merge(base_cfg, spec["base_override"])

    variants = args.variants or sorted(spec["variants"])
    unknown = set(variants) - set(spec["variants"])
    if unknown:
        raise SystemExit(f"Unknown variants for {args.track}: {sorted(unknown)}")

    abl_root = ROOT / "ablations" / args.track
    cfg_dir = abl_root / "_configs"
    job_dir = abl_root / "_jobs"
    log_dir = abl_root / "_logs"
    for d in (cfg_dir, job_dir, log_dir):
        d.mkdir(parents=True, exist_ok=True)

    job_files: list[Path] = []
    for variant in variants:
        cfg = deep_merge(base_cfg, spec["variants"][variant])
        cfg.pop("config_path", None)
        validate(args.track, variant, cfg)

        config_path = cfg_dir / f"{variant}.yaml"
        config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))

        for fold in args.folds:
            coarse_pred_dir = spec["coarse_root"] / f"fold{fold}" / "coarse_predictions"
            if not coarse_pred_dir.exists():
                raise SystemExit(f"Missing frozen coarse predictions: {coarse_pred_dir}")

            output_dir = abl_root / variant / f"fold{fold}"
            if (output_dir / "experiment_result.json").exists():
                print(f"  skip (done): {args.track}/{variant}/fold{fold}")
                continue

            job_name = f"mos_{args.track}_{variant}_f{fold}"
            job_path = job_dir / f"{job_name}.sh"
            job_path.write_text(SBATCH_TEMPLATE.format(
                job_name=job_name,
                partition=args.partition or spec["partition"],
                cpus=spec["cpus"], mem=spec["mem"], time=spec["time"],
                log_dir=log_dir, root=ROOT, env=CONDA_ENV,
                config=config_path, fold=fold, data_dir=DATA_DIR,
                output_dir=output_dir, cache_dir=ROOT / "cache",
                track_arg=spec["track_arg"], manifest=spec["manifest"],
                coarse_pred_dir=coarse_pred_dir,
                z_flag=" \\\n    --z-spacing-aug" if spec["z_spacing_aug"] else "",
            ))
            job_path.chmod(0o755)
            job_files.append(job_path)

    print(f"\nGenerated {len(job_files)} job scripts under {job_dir}")
    if not args.submit:
        print("Re-run with --submit to queue them.")
        return

    submitted = []
    for job_path in job_files:
        result = subprocess.run(["sbatch", str(job_path)], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  FAILED {job_path.name}: {result.stderr.strip()}", file=sys.stderr)
            continue
        job_id = result.stdout.strip().split()[-1]
        submitted.append(job_id)
        print(f"  {job_id}  {job_path.name}")
    print(f"\nSubmitted {len(submitted)}/{len(job_files)} jobs.")


if __name__ == "__main__":
    main()
