# U-MyoPS (paper baseline)

Thin wrappers around `third_party/U-MyoPS_myops` and `scripts/U-MyoPS/`.

- **Stage 1** — joint registration + myocardium (`run_stage1.sh`). Upstream Python defaults `--phase` to **`metric`** (no training). CARE sets **`UMYOPS_STAGE1_PHASE=train`** by default in `run_stage1.sh`; only evaluate metrics if you override (e.g. `metric` / `test`).
- **Stage 2** — pathology head, legacy nnU-Net v1 API (`run_stage2.sh` → `pathology_segmentation_train.py`).
- **Python env:** both stages default to `CARE_CineMyoPS_ENV` (same as CineMyoPS v1), usually `env_CARE_nnUNet_v1`. Override with `UMYOPS_PYTHON` / `LEGACY_PYTHON` if needed.
- `run.sh` — local driver: prepare → stage 1; set **`UMYOPS_RUN_STAGE2=1`** to also run stage 2 in the same shell.
- **Slurm:** `sbatch_stage1.sh` (**`U-MyoPS-Stage1-D501`**) — prepare + stage 1; `sbatch_stage2.sh` (**`U-MyoPS-Stage2-D501`**) — pathology nnU-Net only. `sbatch.sh` is a legacy wrapper that runs stage 1 only. Unified benchmarks submit stage 1 always; stage 2 is submitted with **`Slurm afterok`** on stage 1 when **`UMYOPS_RUN_STAGE2=1`** (see `env_nnunet.sh`, default `0`).
- `UMYOPS_STAGE2_TASK` defaults in `env_nnunet.sh` (`Task901_CARE_UmyopsPathology` unless overridden); stage 2 needs the v1 Task + `plan_and_preprocess`. Optional: `UMYOPS_STAGE2_DIM`, `UMYOPS_STAGE2_TRAINER`, `UMYOPS_STAGE2_EPOCHS`.

Upstream code lives under `third_party/U-MyoPS_myops` (not this folder).

### Stage 2 prerequisites (pathology nnU-Net v1)

Stage 2 loads plans from **U-MyoPS’s own nnU-Net v1 tree** (not `data/nnUNet` for v2):

- `${CARE_ROOT}/third_party/U-MyoPS_myops/outputs/nnunet/raw/nnUNet_raw_data/<UMYOPS_STAGE2_TASK>/`
- `${CARE_ROOT}/third_party/U-MyoPS_myops/outputs/nnunet/prepro/<UMYOPS_STAGE2_TASK>/nnUNetPlansv2.1_plans_2D.pkl` (for `UMYOPS_STAGE2_DIM=2d`)

You must create the v1 **Task** folder (imagesTr, labelsTr, dataset.json, …) under `raw/nnUNet_raw_data/`, then run **nnU-Net v1** experiment planning + preprocessing for that task so the `prepro/` folder and `*_plans_2D.pkl` exist. Until that is done, stage 2 will fail with `FileNotFoundError` on the pickle (see logs). `sbatch.sh` now checks for this file before starting stage 2 and prints the expected paths.

`run_stage2.sh` exports absolute `nnUNet_raw_data_base`, `nnUNet_preprocessed`, and `RESULTS_FOLDER` pointing at `third_party/U-MyoPS_myops/outputs/nnunet/...` so paths do not depend on the current working directory.
