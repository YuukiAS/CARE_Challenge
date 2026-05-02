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
