# Unified Offline Evaluation

Canonical comparison groups in this repository:

- `nnUNet501` vs `MyoPS-Net` vs `U-MyoPS`
  - protocol: `data/benchmarks/protocol/splits_MyoPS.json`
  - GT: `data/nnUNet/nnUNet_raw/Dataset501_CAREMyoPS/labelsTr`
  - default comparison classes: `4,5` (`edema`, `scar`)
- `nnUNet502` vs `CineMyoPS`
  - protocol: `data/benchmarks/protocol/splits_CineMyoPS.json`
  - GT: `data/nnUNet/nnUNet_raw/Dataset502_CARECineMyoPS/labelsTr`
  - default comparison classes: `1,2,3`

Run:

```bash
bash scripts/evaluation/run_unified_eval_model.sh nnUNet501
bash scripts/evaluation/run_unified_eval_model.sh MyoPS-Net
bash scripts/evaluation/run_unified_eval_model.sh nnUNet502
bash scripts/evaluation/run_unified_eval_model.sh CineMyoPS
bash scripts/evaluation/run_unified_eval_all.sh
```

Notes:

- `MyoPS-Net` predictions are auto-exported into `results/predictions/MyoPS-Net/fold_k/` from the best-scoring checkpoint found in `results/checkpoints/MyoPS-Net/fold_k/checkpoints/`.
- `CineMyoPS` uses Task025 nnU-Net v1 case ids such as `center_alpha_Case1005`; unified evaluation strips the center prefix back to CARE protocol ids.
- `U-MyoPS` is not yet training-split aligned with the CARE protocol. For cross-model comparison, evaluate only protocol fold val cases, and use **Stage 2 pathology predictions** as the final comparable output. Stage 1 outputs are not the final pathology segmentation result.

**CARE2026 leaderboard (MyoPS pathology) ↔ unified `evaluate_predictions.py`:** when `--foreground-classes 4,5`, treat **`mean_dice.class_4` as `myops_edema`** and **`mean_dice.class_5` as `myops_scar`**. Stage2 nnU-Net Task901 uses internal labels **1=edema, 2=scar**; `export_stage2_val_predictions.py` remaps **1→4** and **2→5** for Dataset501-compatible NIfTI. Rebuild Stage2 raw labels after changing `compact_pathology_label` in `code/U-MyoPS/build_stage2_task_from_stage1.py` (run `code/U-MyoPS/prepare_stage2_task.sh`).
