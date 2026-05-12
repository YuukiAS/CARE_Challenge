# CARE repository — agent instructions

## Reference papers

Third-party papers for consultation live under **`literature/`** (PDFs, etc.). Use them when explaining methods, citations, or baseline details if copies exist there.

## Compute resources

The usual working environment is a compute node. The user also has access to the **`htzhulab`** partition; when CPU-only execution would be slow, use temporary GPU jobs there via `sbatch`, `srun`, or similar Slurm commands instead of letting long CPU runs crawl.

When adding Slurm entrypoints under `jobs/`, mirror the existing header/logging style:

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

To prepare a CARE-Myocardium validation upload zip from the nnU-Net baselines, use:

```bash
sbatch jobs/submission/prepare_care_myocardium_validation.sh
```

For a local/debug run, use:

```bash
./env_CARE/bin/python scripts/submission/prepare_care_myocardium_validation.py \
  --team-name OrganAgent \
  --run-name nnunet_5fold_best \
  --folds 0 1 2 3 4 \
  --checkpoint checkpoint_best.pth
```

The script converts validation inputs to nnU-Net channel files under the fixed `<run-name>` workspace, runs `Dataset501_CAREMyoPS` and `Dataset502_CARECineMyoPS`, remaps compact nnU-Net labels back to CARE raw labels (`200`, `500`, `600`, `1220`, `2221` as applicable), appends a timestamp to the submission package by default, and writes:

- `results/submissions/care_myocardium_validation/<run-name>/packages/CARE-Myocardium-OrganAgent_<YYYYMMDD_HHMMSS>.zip`
- `results/submissions/care_myocardium_validation/<run-name>/packages/CARE-Myocardium-OrganAgent_<YYYYMMDD_HHMMSS>_manifest.json`

The official Myocardium validation zip layout is documented at `https://zmic.org.cn/care_2026/valid_submission/`: top-level `MyoPS/Anonymous Center/Case****/Case****_pred.nii.gz` and `CineMyoPS/Anonymous Center/Case****/Case****_pred.nii.gz`.

Default inference policy for the current nnU-Net baseline is a 5-fold ensemble (`fold_0`-`fold_4`) using `checkpoint_best.pth`, because all five folds exist for both Dataset501 and Dataset502. Run it on `htzhulab` GPU by default; use a single best fold only for quick experiments or if ensemble inference is too slow.
