# CineMyoPS (paper baseline)

Wrappers for `third_party/CineMyoPS` nnU-Net v1 training on Task025 data produced by `code/CineMyoPS/prepare_task025_from_care.py`.

- `run.sh` — prepare + train locally.
- `sbatch.sh` — Slurm **Task025** legacy path (`prepare_task025_from_care.py` + train); set `#SBATCH` for your cluster.
- `sbatch_cinemyops.sh` — Slurm **Task026** paper path (4D cine, `CARECineMyoPSTrainer`).
- `sbatch_smoke.sh` — Slurm **smoke** (tiny Task026 export, few epochs, no val export by default).
- `sbatch_fold0_pipeline.sh` — Slurm **fold-0 train + export + unified eval** (8h wall; appends `results/experiments/CineMyoPS_iteration_log.md`).

Environment knobs: `CINE_NNUNET_DIM`, `CINE_NNUNET_TRAINER`, `CINE_NNUNET_TASK`, `CINE_NNUNET_EPOCHS`, `FOLD`.

## CineMyoPS (paper replication)

`Task025_Cine_Seg` keeps the old single-frame nnU-Net v1 baseline for comparison.
`Task026_Cine_4D` is the CARE paper-replication path: ED is fixed to `t=0`, the exporter keeps sampled cine frames, raw nnU-Net input is split into per-frame channels, and `CARECineMyoPSTrainer` drives `CineSegNet` with scar-only supervision.

Key environment variables:
- `CINE_NNUNET_TASK`: default `Task026_Cine_4D`
- `CINE_NNUNET_TRAINER`: default `CARECineMyoPSTrainer`
- `CINE_NNUNET_DIM`: default `2d`
- `CINE_NUM_FRAMES`: sampled frames per cycle, default `4`
- `CINE_NNUNET_EPOCHS`: trainer epoch cap, default `300` (passed to `run_train.sh` / trainer env)
- `FOLD`: protocol fold index, `0..4`
- `CINE_SKIP_SANITY`: set `1` to skip `sanity_check_task026.py`
- `CINE_SKIP_PREPARE` (sbatch_cinemyops only): `1` skips `prepare_task026_cine_4d.py` + sanity when raw data already exist
- `CINE_FORCE_WRITE_SPLITS`: `1` rebuilds `splits_final.pkl` from protocol JSON with backup of the old file
- `CINE_RUN_EXPORT_EVAL`: when `1`, after training run export + unified eval + aggregate (see `run_task026_paper_steps.sh`; enabled by `sbatch_fold0_pipeline.sh`)

Smoke Slurm (`sbatch_smoke.sh`):

```bash
sbatch jobs/CineMyoPS/sbatch_smoke.sh
# optional: more epochs, still small data
CINE_SMOKE_EPOCHS=8 sbatch jobs/CineMyoPS/sbatch_smoke.sh
```

Logs follow `AGENTS.md`: `logs/<SLURM_JOB_NAME>_<jobid>_<YYYYMMDD_HHMMSS>.log` (Slurm stdout/stderr go to `/dev/null`).

Fold-0 train + export + eval:

```bash
cd /overflow/htzhu/CARE
sbatch jobs/CineMyoPS/sbatch_fold0_pipeline.sh
```

Compare **`mean_dice.class_1`** to nnU-Net Dataset502 myocardium reference **≈ 0.6808** (`results/metrics/nnUNet.md`).

Recommended five-fold launch:

```bash
for f in 0 1 2 3 4; do FOLD=$f sbatch jobs/CineMyoPS/sbatch_cinemyops.sh; done
```

Single-fold launch:

```bash
sbatch jobs/CineMyoPS/sbatch_cinemyops.sh
FOLD=2 sbatch jobs/CineMyoPS/sbatch_cinemyops.sh
```

Validation export still lands in `results/predictions/CineMyoPS/fold_X/<case>.nii.gz`, so the existing evaluator stays unchanged:

```bash
bash scripts/evaluation/run_unified_eval_model.sh CineMyoPS
```

Expected validation behavior:
- `validation_raw/` and protocol exports are written in the compact CARE label space `{0:bg,1:myocardium,2:LV_blood,3:scar}`
- unified evaluation: use **`mean_dice.class_1`** for myocardium vs nnU-Net Dataset502; `class_3` is scar (hosted cinemyops-related)
- smoke-test-scale runs only validate pipeline health, not final Dice quality

## Round4/5 Inference-Semantics Debug

Round4 combine-mode ablations (`current`, `cardiac_only`, `myocardium_gated_scar`, `pathology_direct`) all exported all-background predictions on fold0. The previous debug script selected an invalid 2D slice axis and failed before it could inspect direct branch logits.

Use the fixed short diagnostic before any more training:

```bash
cd /overflow/htzhu/CARE
sbatch jobs/CineMyoPS/sbatch_round5_debug_fixed.sh
```

Output:

- `results/diagnostics/baseline_paper_models/CineMyoPS/round05_fixed_inference/inference_semantics_fixed.json`

Decision rule:

- If direct forward logits are non-empty but sliding-window/export is empty, repair inference/export only.
- If direct forward logits are also all-background, do not run longer training; fix trainer supervision/normalization first.
- Do not expand CineMyoPS to folds 1-4 until fold0 protocol validation has non-empty `class_1` and `class_3` sanity output.
