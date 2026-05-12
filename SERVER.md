# nnU-Net CARE Myocardium — server runbook

This project converts [data/CARE_Challenge](data/CARE_Challenge) into nnU-Net v2 datasets and trains on a **GPU** node. Local development machines are often CPU-only; use them only for **smoke tests**.

**Data layout:** see [data/README.md](data/README.md). Challenge **source** scans live under `data/CARE_Challenge/MyoPS_train`, `data/CARE_Challenge/CineMyoPS_train`, and the validation counterparts `MyoPS_val` / `CineMyoPS_val`. **nnU-Net** v2 `raw` / `preprocessed` / `results` are **physical directories** under `data/nnUNet/` (see `env_nnunet.sh`). **Paper baselines** (MyoPS-Net, U-MyoPS, CineMyoPS) use additional staging dirs under `data/benchmarks/<name>/`. After conversion, **`nnUNet_raw` holds exactly two** task folders: `Dataset501_CAREMyoPS` (MyoPS / multi-sequence) and `Dataset502_CARECineMyoPS` (Cine / single-frame). Do not keep duplicate exports or extra `Dataset503_*` copies there — they break nnU-Net ID resolution.

**Third-party code** is cloned under `third_party/` (see [third_party/README.md](third_party/README.md)). **Your own models** go under `src/`. Slurm / training entrypoints are grouped under [`jobs/`](jobs/README.md): **`jobs/nnUNet/`** (nnU-Net v2 CARE baselines), **`jobs/MyoPS-Net/`**, **`jobs/U-MyoPS/`**, **`jobs/CineMyoPS/`** (upstream paper repos), and **`jobs/PaperBaselines/run_all.sh`** to orchestrate the three paper methods (`MODEL`, `PREPARE_ONLY`, `STAGE` for U-MyoPS).

## Environment

- **Python env**: install dependencies into `/overflow/htzhu/CARE/env_CARE` (or your own venv):

  ```bash
  /overflow/htzhu/CARE/env_CARE/bin/pip install -r /overflow/htzhu/CARE/requirements-nnunet.txt
  ```

- **GPU PyTorch**: before training, replace CPU torch with a CUDA build, for example:

  ```bash
  pip uninstall -y torch torchvision
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
  ```

  Pick the index URL that matches your driver/CUDA.

- **nnU-Net paths** (required). Either:

  ```bash
  conda activate /overflow/htzhu/CARE/env_CARE
  ```

  This runs `env_CARE/etc/conda/activate.d/care_nnunet_env.sh`, which sets `CARE_ROOT` and sources `env_nnunet.sh` (no echo spam). Or manually:

  ```bash
  source /overflow/htzhu/CARE/env_nnunet.sh
  ```

  Defaults:

  - `nnUNet_raw=/overflow/htzhu/CARE/data/nnUNet/nnUNet_raw`
  - `nnUNet_preprocessed=/overflow/htzhu/CARE/data/nnUNet/nnUNet_preprocessed`
  - `nnUNet_results=/overflow/htzhu/CARE/data/nnUNet/nnUNet_results`
  - `CARE_NNUNET_TRAINER=nnUNetTrainer_500epochs` (500-epoch trainer; override with `nnUNetTrainer` for 1000 epochs)

## Dataset IDs

| ID   | Folder                         | Source data              | Input channels   |
|------|--------------------------------|--------------------------|------------------|
| 501  | `Dataset501_CAREMyoPS`        | `data/CARE_Challenge/MyoPS_train` | LGE, T2, C0      |
| 502  | `Dataset502_CARECineMyoPS`    | `data/CARE_Challenge/CineMyoPS_train` | Cine (one frame) |

**Label classes** (after conversion): `0` background, `1` myocardium, `2` LV blood, `3` RV blood, `4` edema, `5` scar. Original challenge pixel values are remapped in `code/nnUNet/nnunet_label_utils.py`.

**MyoPS**: LGE is the reference grid; missing T2/C0 are **zero-filled**.  
**CineMyoPS**: 4D Cine `(x,y,z,t)` is reduced to 3D using the **middle time frame** by default (`--time-index -1`). For ED-specific evaluation, replace with the correct frame index when metadata is available.

## One-shot commands

### Smoke test (CPU OK, ~3 cases each)

```bash
cd /overflow/htzhu/CARE
bash code/nnUNet/run_smoke.sh
```

Optional: `MAX_CASES=2 NPFP=2 bash code/nnUNet/run_smoke.sh`.

### Full training (GPU)

```bash
cd /overflow/htzhu/CARE
source env_nnunet.sh
bash code/nnUNet/run_full_train.sh
```

Optional:

- `CONFIG=3d_fullres FOLD=0` (defaults)
- `TRAIN_MYOPS=0` to train only Cine (502), or `TRAIN_CINE=0` for MyoPS only
- `SKIP_CONVERT=1` if `nnUNet_raw` was copied from another machine and paths match

### Manual steps (same as scripts)

```bash
# Convert (full data)
python code/nnUNet/convert_myops_to_nnunet.py --output "$nnUNet_raw/Dataset501_CAREMyoPS"
python code/nnUNet/convert_cine_to_nnunet.py --output "$nnUNet_raw/Dataset502_CARECineMyoPS"

nnUNetv2_plan_and_preprocess -d 501 --verify_dataset_integrity
source /overflow/htzhu/CARE/env_nnunet.sh
nnUNetv2_train 501 3d_fullres 0 --npz -tr "${CARE_NNUNET_TRAINER}"

nnUNetv2_plan_and_preprocess -d 502 --verify_dataset_integrity
nnUNetv2_train 502 3d_fullres 0 --npz -tr "${CARE_NNUNET_TRAINER}"
```

## Outputs

- **Preprocessed cache**: `$nnUNet_preprocessed/Dataset501_CAREMyoPS/`, `Dataset502_CARECineMyoPS/` (default under `data/nnUNet/nnUNet_preprocessed/`)
- **Checkpoints / logs**: `$nnUNet_results/` (nnU-Net v2 naming: `Dataset501_CAREMyoPS/...`; default `data/nnUNet/nnUNet_results/`)

## Inference (after training)

After training, use `nnUNetv2_predict` with the dataset id, configuration, fold, and trainer that match the run under `nnUNet_results`. See the [nnU-Net v2 inference documentation](https://github.com/MIC-DKFZ/nnUNet/blob/master/documentation/how_to_use_nnunet.md).

For CARE2026 Myocardium validation submission packaging, use the GPU Slurm wrapper:

```bash
sbatch jobs/submission/prepare_care_myocardium_validation.sh
```

It writes timestamped upload packages under `results/submissions/care_myocardium_validation/<run-name>/packages/`.

## Disk and runtime (rough)

- Full **MyoPS** conversion + preprocessing: moderate disk (NIfTI copies + preprocessed npz); training time depends on GPU and epochs. CARE defaults to **500 epochs** via `env_nnunet.sh` (`CARE_NNUNET_TRAINER=nnUNetTrainer_500epochs`). Use the same `-tr` value for `nnUNetv2_predict` as for training so checkpoint paths match.
- **Cine** subset is smaller (64 cases vs 220).

## Verified locally

Smoke path (`code/nnUNet/run_smoke.sh` with 3 cases per dataset + `plan_and_preprocess` for 501 and 502) completed without dataset integrity errors on the development host (CPU torch).
