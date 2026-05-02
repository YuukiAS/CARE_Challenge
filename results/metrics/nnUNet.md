# nnU-Net v2 baseline (CARE)

Aggregated validation metrics for reproducibility and multi-model comparison. Raw nnU-Net outputs: `data/nnUNet/nnUNet_results/`.

## Setup


| Item          | Value                                                           |
| ------------- | --------------------------------------------------------------- |
| Trainer       | `nnUNetTrainer_500epochs`                                       |
| Configuration | `3d_fullres`                                                    |
| Plans         | `nnUNetPlans`                                                   |
| Dataset 501   | `Dataset501_CAREMyoPS` (MyoPS_train, multi-sequence)            |
| Dataset 502   | `Dataset502_CARECineMyoPS` (CineMyoPS_train, single Cine frame) |


Label semantics (from `data/nnUNet/nnUNet_raw/*/dataset.json`):

- **501:** 1=myocardium, 2=LV_blood, 3=RV_blood, 4=edema, 5=scar  
- **502:** 1=myocardium, 2=LV_blood, 3=scar

Per-fold summaries are read from:

`data/nnUNet/nnUNet_results/<Dataset>/nnUNetTrainer_500epochs__nnUNetPlans__3d_fullres/fold_{0..4}/validation/summary.json`

---

## Dataset 501 — fold-wise Mean Validation Dice (foreground aggregate)

These match the `Mean Validation Dice` line in training logs (`foreground_mean` in `summary.json`).


| Fold | Mean Val Dice |
| ---- | ------------- |
| 0    | 0.6940        |
| 1    | 0.7139        |
| 2    | 0.7326        |
| 3    | 0.7084        |
| 4    | 0.6991        |


---

## Dataset 502 — fold-wise Mean Validation Dice


| Fold | Mean Val Dice |
| ---- | ------------- |
| 0    | 0.6115        |
| 1    | 0.5899        |
| 2    | 0.6133        |
| 3    | 0.6451        |
| 4    | 0.5849        |


---

## Dataset 501 — per-class Dice (validation `mean` in summary.json)


| Class | Name       | Fold0  | Fold1  | Fold2  | Fold3  | Fold4  | Mean (5 folds) |
| ----- | ---------- | ------ | ------ | ------ | ------ | ------ | -------------- |
| 1     | myocardium | 0.7197 | 0.7536 | 0.7622 | 0.7640 | 0.7739 | **0.7547**     |
| 2     | LV_blood   | 0.9211 | 0.9262 | 0.9322 | 0.9301 | 0.9266 | **0.9272**     |
| 3     | RV_blood   | 0.8745 | 0.9063 | 0.9077 | 0.8837 | 0.8640 | **0.8872**     |
| 4     | edema      | 0.3944 | 0.4158 | 0.4761 | 0.4435 | 0.3686 | **0.4197**     |
| 5     | scar       | 0.5602 | 0.5679 | 0.5846 | 0.5206 | 0.5625 | **0.5592**     |


Note: `foreground_mean.Dice` is not necessarily the unweighted arithmetic mean of class Dice; nnU-Net aggregates foreground metrics separately.

---

## Dataset 502 — per-class Dice


| Class | Name       | Fold0  | Fold1  | Fold2  | Fold3  | Fold4  | Mean (5 folds) |
| ----- | ---------- | ------ | ------ | ------ | ------ | ------ | -------------- |
| 1     | myocardium | 0.6864 | 0.6494 | 0.6962 | 0.6909 | 0.6812 | **0.6808**     |
| 2     | LV_blood   | 0.9036 | 0.8538 | 0.8778 | 0.9123 | 0.8895 | **0.8874**     |
| 3     | scar       | 0.2446 | 0.2665 | 0.2660 | 0.3321 | 0.1839 | **0.2586**     |


---

## Log references (Slurm)

Representative completed runs under `logs/`:

- 501: `nnUNet_D501_44293090`_* (fold 0), `nnUNet_D501_44347321_`* (fold 1), `nnUNet_D501_44347322_*` (fold 2), `nnUNet_D501_44347323_*` (fold 3), `nnUNet_D501_44347324_*` (fold 4)
- 502: `nnUNet_D502_44293096_*` (fold 0), `nnUNet_D502_44347325_*` (fold 1), `nnUNet_D502_44347326_*` (fold 2), `nnUNet_D502_44347327_*` (fold 3), `nnUNet_D502_44347328_*` (fold 4)

