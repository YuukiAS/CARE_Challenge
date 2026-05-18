# CARE repository — agent instructions

## Codex rule source

Treat this `AGENTS.md` as the repo-level Codex rules source. Do not rely on `.cursor/rules/`, `.cursor/skills/`, `.cursor/plans/`, or Cursor plugins; migrate future rule changes here.

## Skill Source

- Repo-level skills are installed under `.codex/skills/` from `/overflow/htzhu/mingcheng_new/AI_Skills_Collection/skills`.
- The canonical upstream source remains `/overflow/htzhu/mingcheng_new/AI_Skills_Collection/skills`; when refreshing repo-local skills, replace duplicates with copies from that collection.
- This repository should install the medical imaging skill set from `AI_Skills_Collection/skills/domain/medical-imaging`.
- Do not add `.cursor/skills` or Cursor plugin copies in this repository.

## Reference papers

Third-party papers for consultation live under **`literature/`** (PDFs, etc.). Use them when explaining methods, citations, or baseline details if copies exist there.

## Compute resources

The usual working environment is a compute node. The user also has access to the **`htzhulab`** partition; when CPU-only execution would be slow, use temporary GPU jobs there via `sbatch`, `srun`, or similar Slurm commands instead of letting long CPU runs crawl.

For CARE model work, default to the lab partition first. If queue inspection suggests a materially long wait on `htzhulab`, school GPU partitions may be used as fallbacks. The priority order is:

1. `htzhulab` — preferred/default for CARE jobs.
2. `a100-gpu` — school A100 partition; use only when `htzhulab` is expected to wait too long.
3. `volta-gpu` — school V100 partition; use after `a100-gpu`.

Current Slurm-visible school GPU partitions include:

- `a100-gpu`: `gpu:nvidia_a100-pcie-40gb`
- `volta-gpu`: `gpu:tesla_v100-sxm2-16gb`
- Other visible GPU partitions such as `l40-gpu`, `gpu` (GTX 1080), and `webportal_gpu` are not part of the default CARE fallback order; use them only if the user explicitly asks or the job requirements clearly fit them better.

Before switching away from `htzhulab`, check queue state with commands such as:

```bash
squeue -p htzhulab
sinfo -o '%P|%a|%l|%D|%t|%G'
```

Do **not** switch partitions for short waits or routine pending jobs. Switch only when `htzhulab` is full and the expected wait is long relative to the planned job budget. When switching to school partitions, keep the same logging style, but use the partition-specific Slurm headers below. Do not omit `--qos`: school GPU partitions may reject jobs that inherit an incompatible default QOS. The safe default QOS for CARE fallback jobs is `gpu_access`.

When adding Slurm entrypoints under `jobs/`, mirror the existing header/logging style. Default CARE/lab jobs should use `htzhulab`:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:1
#SBATCH --partition=htzhulab
#SBATCH --qos=gpu_access
```

For the school A100 fallback, use this directly usable header:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:nvidia_a100-pcie-40gb:1
#SBATCH --partition=a100-gpu
#SBATCH --qos=gpu_access
```

Notes for `a100-gpu`: `scontrol show partition a100-gpu` reports `AllowQos=gpu_access,gpu_access_plus`, `MaxTime=6-00:00:00`, nodes `g[141601-141608]`, and `gres/gpu:nvidia_a100-pcie-40gb`. Prefer `gpu_access`; use `gpu_access_plus` only when the user explicitly asks or there is a known reason to request that QOS.

For the school V100 fallback, use this directly usable header:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --job-name=<ShortJobName>
#SBATCH --output=/dev/null
#SBATCH --error=/dev/null
#SBATCH --mem=64G
#SBATCH --time=<limit>
#SBATCH --gres=gpu:tesla_v100-sxm2-16gb:1
#SBATCH --partition=volta-gpu
#SBATCH --qos=gpu_access
```

Notes for `volta-gpu`: `scontrol show partition volta-gpu` reports `AllowQos=gpu_access,hp_volta_gpu,gpu_access_plus`, `MaxTime=11-00:00:00`, nodes `g[0301-0316]`, and `gres/gpu:tesla_v100-sxm2-16gb`. Prefer `gpu_access`; use `gpu_access_plus` or `hp_volta_gpu` only when the user explicitly asks or there is a known reason to request that QOS.

Inside the script, create a timestamped log and tee stdout/stderr there:

```bash
mkdir -p logs
TS="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="${LOG_FILE:-${CARE_ROOT}/logs/<ShortJobName>_${SLURM_JOB_ID:-local}_${TS}.log}"
exec > >(tee -a "${LOG_FILE}") 2>&1
```

Use filenames like `logs/CineMyoPS_44291121_20260418_111101.log`. Avoid Slurm `%x_%j.out` files unless diagnosing scheduler startup failures.

## Model performance questions

When asked about **model performance** (metrics, Dice, fold CV results):

1. Verify whether **all folds** (usually 0–4) completed using logs and/or `validation/summary.json` (or each model’s metric outputs).
2. If incomplete: state missing folds and report partial results with a clear caveat.
3. If complete: report using the **same document structure and Markdown tables** as `results/metrics/nnUNet.md` (Setup table → label semantics → metric paths → per-dataset fold-wise Mean Val Dice → per-class Dice with Fold0–Fold4 + mean column → optional foreground_mean note → optional log references).

Mirror this layout for non–nnU-Net models; answer in **Simplified Chinese** with English for paths/names as needed.

## Iterative model-improvement runs

For CARE model-improvement work, use short, attributable experiment rounds instead of long speculative training runs.

- Default single training/evaluation job walltime is **8 hours or less**. If an existing Slurm script requests more time, create or use a budgeted entrypoint for the current round.
- Do **not** use very long runs such as 1000/2000 epochs to compensate for weak results. Prefer max-runtime guards, max-epoch caps, validation-based early stopping, and explicit best-checkpoint selection.
- Each round should test one main hypothesis: for example modality dropout, label/remap repair, scar-positive sampling, class-weight tuning, Stage1 prior alignment, or export/cache isolation. Avoid bundling several unrelated changes into one run unless a blocker forces it.
- Start with fold 0 or a small protocol validation loop. Expand to folds 1–4 only after predictions are non-empty, label semantics are verified, cache isolation is verified, and the target leaderboard metric improves or the change fixes a proven pipeline bug.
- Record each round in the relevant file under `results/experiments/*_iteration_log.md`: code changes, command/env vars, fold, walltime, actual epochs, checkpoint used/exported, stop reason, and target metrics before/after.
- Do not silently reuse stale prediction caches. Checkpoint-specific or config-specific prediction and metric directories are required when comparing variants.
- For MyoPS models, optimize and report `myops_scar` and `myops_edema`; for U-MyoPS edema analysis, also report all-cases, GT-positive-only, and T2-present subsets when possible. For CineMyoPS, report both the local `class_1` myocardium proxy and `class_3` scar sanity metric until the hosted `myocardium_cinemyops` metric is calibrated by submission.
- Continue small improvement rounds without asking the user after every run unless there is a decision about data compliance, label definitions, official submission strategy, external credentials, or materially longer compute.

## CARE2026 validation leaderboard

When asked for the latest CARE2026 validation/leaderboard/reference scores, first run:

```bash
python scripts/leaderboard/fetch_care2026_scores.py
```

Then answer from the generated latest files under **`results/leaderboard/`**, especially:

- `results/leaderboard/care2026_myocardium_latest.json`
- `results/leaderboard/care2026_myocardium_myops_scar_latest.csv`
- `results/leaderboard/care2026_myocardium_myops_edema_latest.csv`
- `results/leaderboard/care2026_myocardium_myocardium_cinemyops_latest.csv`

If the fetch fails because network access is unavailable or the website/API changed, state that clearly and fall back to the most recent existing `*_latest` files with a timestamp caveat.

For CARE2026 challenge interpretation and optimization, focus only on the three leaderboard tasks/metrics:

- `myops_scar`
- `myops_edema`
- `myocardium_cinemyops`

Do **not** treat myocardium, LV_blood, foreground_mean, or other mean/aggregate values as primary objectives. They may be reported as sanity checks when useful, but the main conclusions and repair plans should target the three leaderboard metrics above.

## CARE2026 validation submission packaging

Validation raw data should live under:

- `data/CARE_Challenge/MyoPS_val`
- `data/CARE_Challenge/CineMyoPS_val`

Use `scripts/submission/prepare_care_myocardium_validation.py` as the single entrypoint for validation submissions. One `CARE-Myocardium-OrganAgent.zip` upload contains both `MyoPS/` and `CineMyoPS/`, consumes one validation submission attempt, and returns the three hosted metrics (`myops_scar`, `myops_edema`, `myocardium_cinemyops`) together. Do not plan separate uploads for those three metrics; use per-metric interpretation after the single package is evaluated.

The script writes intermediate inputs/predictions under:

- `results/submissions/care_myocardium_validation/workspaces/<model_combo>_<timestamp>/`

and writes upload-ready packages under:

- `results/submissions/care_myocardium_validation/upload_ready/<model_combo>_<timestamp>/CARE-Myocardium-OrganAgent.zip`
- `results/submissions/care_myocardium_validation/upload_ready/<model_combo>_<timestamp>/manifest.json`

The upload zip filename intentionally has **no timestamp**, because the official example is `CARE-Myocardium-TeamName.zip`. Keep the timestamp on the parent folder for ordering and auditability.

To prepare the current default nnU-Net 5-fold validation upload zip, use:

```bash
sbatch jobs/submission/prepare_care_myocardium_validation.sh
```

For a local/debug run, use:

```bash
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --team-name OrganAgent \
  --submission-model nnUNet \
  --folds 0 1 2 3 4 \
  --checkpoint checkpoint_best.pth
```

Convenience model selection:

- `--submission-model nnUNet`: use nnU-Net for both MyoPS and CineMyoPS.
- `--submission-model MyoPS-Net` or `--submission-model MyoPS`: use MyoPS-Net for the MyoPS side and nnU-Net for the CineMyoPS side.
- `--submission-model CineMyoPS`: use nnU-Net for the MyoPS side and CineMyoPS for the CineMyoPS side.
- `--submission-model U-MyoPS`: only valid when `--myops-pred-dir` points to compact-label U-MyoPS validation predictions; the current repo has protocol fold export for U-MyoPS but not a full validation Stage1→Stage2 inference pipeline.
- `--myops-model ... --cine-model ...`: explicit hybrid combination, for example `--myops-model MyoPS-Net --cine-model CineMyoPS`.

The script converts compact model labels back to CARE raw labels (`200`, `500`, `600`, `1220`, `2221` as applicable). If a prediction has no pathology label at all, it adds a one-voxel `2221` format fallback and records the case in the manifest, because the official validator rejects predictions missing scar/pathology labels.

The official Myocardium validation zip layout is documented at `https://zmic.org.cn/care_2026/valid_submission/`: top-level `MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz` and `CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz`.

Default inference policy for the current nnU-Net baseline is a 5-fold ensemble (`fold_0`-`fold_4`) using `checkpoint_best.pth`, because all five folds exist for both Dataset501 and Dataset502. Run it on `htzhulab` GPU by default; use a single best fold only for quick experiments or if ensemble inference is too slow.
