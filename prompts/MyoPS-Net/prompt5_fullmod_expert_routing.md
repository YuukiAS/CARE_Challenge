# MyoPS-Net round5 prompt: full-modality expert and modality-routed export

你是 CARE-Myocardium 项目的代码实现与实验 agent。请在 `/overflow/htzhu/CARE` 中继续改进 MyoPS-Net。本轮目标是争取让 MyoPS-Net 在 MyoPS 任务上超过 nnU-Net reference，但必须保持单个训练/评估 job 不超过 8 小时，不要跑长 epoch。

本轮只验证一个主要假设：

> CARE 官方 validation 的 MyoPS cases 全部是 C0+LGE+T2 完整三模态；round4 已证明缺 T2 病例的 edema false positive 是 local overall edema 的主要问题。下一步不应继续让一个混合缺模态模型平均适配所有 source groups，而应训练/校准一个完整三模态专家用于 official-style cases，并用 modality-aware routing 保留缺模态病例的 scar 结果。

## 必须先读

- `docs/notes/MyoPS-Net_improvement_round4.md`
- `results/experiments/MyoPS-Net_iteration_log.md`
- `results/metrics/unified/MyoPS-Net_maskgated_round3/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round4_combined_safe/fold_0/evaluation_summary.json`
- `results/metrics/unified/MyoPS-Net_round4_combined_safe/fold_0/modality_group_metrics.md`
- `logs/MyoPS-Net_51264396_20260517_060037.log`
- `results/metrics/nnUNet.md`
- `AGENTS.md`

## 当前事实

nnU-Net 5-fold reference:

| metric | nnU-Net |
| --- | ---: |
| `myops_scar` / class_5 | 0.5592 |
| `myops_edema` / class_4 | 0.4197 |

MyoPS-Net fold0 trajectory:

| variant | `myops_edema` class_4 | `myops_scar` class_5 | foreground_mean |
| --- | ---: | ---: | ---: |
| original fold0 | 0.2794 | 0.4637 | 0.4039 |
| round3 mask-gated | 0.1293 | 0.4965 | 0.3129 |
| round4 `t2_missing_suppress_edema` | 0.3555 | 0.4965 | 0.4490 |
| round4 `combined_safe` | **0.3733** | **0.5048** | **0.4589** |

Round4 best T2-present subgroup:

| variant | T2-present edema | T2-present scar |
| --- | ---: | ---: |
| round3 mask-gated | 0.3555 | 0.6171 |
| round4 `combined_safe` | **0.3733** | **0.6258** |

Interpretation:

- `combined_safe` is the best current local fold0 MyoPS-Net result, but still below nnU-Net overall.
- T2-present scar already exceeds the nnU-Net 5-fold scar reference, but T2-present edema is still below 0.4197.
- Since official validation is T2-present, the most plausible path is to improve full-modality edema while preserving the current scar advantage.

## Round5 required work

### 1. Add full-modality staging/filtering

Extend `code/MyoPS-Net/prepare_myops_net_layout.py` with explicit filters, for example:

- `--train-require-all-modalities`
- `--val-require-all-modalities`

Use these to create a full-modality training/validation staging root:

- data: `data/benchmarks/MyoPS-Net/fold_0_fullmod_round5`

Expected fold0 composition should be approximately:

- train: complete C0+LGE+T2 cases only from fold0 train split
- validation: complete C0+LGE+T2 cases only from fold0 validation split

Do not delete or overwrite earlier round data roots.

### 2. Add short fine-tuning support

Add optional checkpoint initialization to MyoPS-Net training:

- env/arg: `MYOPS_NET_INIT_CHECKPOINT`
- load `results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth`
- log missing/unexpected keys
- keep `challenge3`, do not restore T1m/T2* mapping branches

Add configurable best-checkpoint selection so this round can favor edema without ignoring scar:

- env/arg: `MYOPS_NET_BEST_METRIC`
- minimally support the current avg pathology metric and a weighted metric like `weighted_pathology`
- env weights such as `MYOPS_NET_BEST_WEIGHT_EDEMA=2.0`, `MYOPS_NET_BEST_WEIGHT_SCAR=1.0`
- record the selected metric, epoch, edema Dice, scar Dice, and stop reason in `train_stop_summary.json`

Keep `MYOPS_NET_MASK_GATED_LOSS=1`; no modality dropout in this round.

### 3. Run one full-modality fold0 expert job

Use an isolated <=8h Slurm run. Check `squeue -p htzhulab`; if htzhulab wait is materially long, use the AGENTS fallback priority `htzhulab > a100-gpu > volta-gpu`.

Suggested command:

```bash
sbatch --export=ALL,FOLD=0,PREPARE=1,MYOPS_NET_DATA=/overflow/htzhu/CARE/data/benchmarks/MyoPS-Net/fold_0_fullmod_round5,MYOPS_NET_WORKDIR=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_fullmod_round5,MYOPS_NET_VARIANT=challenge3,MYOPS_NET_INIT_CHECKPOINT=/overflow/htzhu/CARE/results/checkpoints/MyoPS-Net/fold_0_maskgated_round3/checkpoints/best.pth,MYOPS_NET_END_EPOCH=80,MYOPS_NET_MAX_RUNTIME_HOURS=7.75,MYOPS_NET_EARLY_STOP_PATIENCE=15,MYOPS_NET_LR=5e-5,MYOPS_NET_MASK_GATED_LOSS=1,MYOPS_NET_MODALITY_DROPOUT=0,MYOPS_NET_PATHOLOGY_SAMPLER=1,MYOPS_NET_SAMPLE_WEIGHT_SCAR=2.0,MYOPS_NET_SAMPLE_WEIGHT_EDEMA=12.0,MYOPS_NET_SAMPLE_WEIGHT_BOTH=4.0,MYOPS_NET_BEST_METRIC=weighted_pathology,MYOPS_NET_BEST_WEIGHT_EDEMA=2.0,MYOPS_NET_BEST_WEIGHT_SCAR=1.0,MYOPS_NET_PREP_TRAIN_REQUIRE_ALL_MODALITIES=1,MYOPS_NET_PREP_VAL_REQUIRE_ALL_MODALITIES=1,MYOPS_NET_EXPORT_EVAL=1,MYOPS_NET_PRED_DIR=/overflow/htzhu/CARE/results/predictions/MyoPS-Net_fullmod_round5/fold_0,MYOPS_NET_EVAL_OUTPUT_DIR=/overflow/htzhu/CARE/results/metrics/unified/MyoPS-Net_fullmod_round5/fold_0 jobs/MyoPS-Net/sbatch.sh
```

If `jobs/MyoPS-Net/sbatch.sh` does not yet pass the new prepare flags, update it.

### 4. Export and evaluate official-style and local-hybrid variants

After training, evaluate all outputs under isolated directories:

1. `MyoPS-Net_fullmod_round5`
   - export the full-modality expert on its full-modality validation staging root.
   - report T2-present/full-modality metrics.

2. `MyoPS-Net_round5_fullmod_on_allval`
   - export the same round5 checkpoint on the all-case fold0 validation root, e.g. `data/benchmarks/MyoPS-Net/fold_0_maskgated_round3`.
   - this shows how badly the full expert behaves on missing modalities.

3. `MyoPS-Net_round5_hybrid_fullmod_plus_round4`
   - for C0+LGE+T2 cases, use round5 fullmod expert predictions.
   - for T2-missing cases, use the best round4 safe predictions:
     - prefer `MyoPS-Net_round4_combined_safe` if it improves scar without unacceptable side effects;
     - otherwise use `MyoPS-Net_round4_t2_missing_suppress_edema`.
   - evaluate all fold0 cases for direct comparison to nnU-Net.

4. Apply `t2_missing_suppress_edema` and `combined_safe` style postprocess to round5 predictions if useful, but do not use GT-derived masks.

### 5. Optional calibration if training alone is close

If fullmod round5 edema is between 0.38 and 0.42, add a lightweight export-only calibration before launching any second training job:

- save or recompute T2 edema and LGE scar softmax/probability maps;
- sweep non-GT thresholds for class_4 and class_5 on the full-modality validation cases;
- keep the chosen threshold only if it improves edema without dropping scar below 0.61 on T2-present cases;
- write threshold-specific predictions/metrics under `results/predictions/MyoPS-Net_round5_threshold_<name>/fold_0` and `results/metrics/unified/MyoPS-Net_round5_threshold_<name>/fold_0`.

Do not start folds 1-4 unless fold0 clearly beats or matches nnU-Net on the target metrics.

## Required reporting

Create `docs/notes/MyoPS-Net_improvement_round5.md` and append `results/experiments/MyoPS-Net_iteration_log.md`.

Report at minimum:

- train/val case counts and modality composition for `fold_0_fullmod_round5`;
- checkpoint initialization status;
- actual Slurm job id, partition, elapsed time, stop reason, best epoch, selected checkpoint metric;
- full-modality subgroup Dice: `myops_edema`, `myops_scar`;
- all-case fold0 Dice for raw round5 and hybrid round5;
- source-group metrics for C0+LGE+T2, C0+LGE, LGE-only;
- changed voxel counts if postprocess/routing changes predictions;
- whether the result exceeds:
  - nnU-Net edema 0.4197;
  - nnU-Net scar 0.5592;
  - previous best MyoPS-Net round4 combined_safe edema 0.3733 and scar 0.5048.

## Success criteria

- Official-style success: C0+LGE+T2/full-modality validation reaches `myops_edema >= 0.4197` and preserves `myops_scar >= 0.61`.
- Local hybrid success: all-case hybrid reaches `myops_edema >= 0.4197` and improves scar over round4; if all-case scar still cannot reach 0.5592, explain whether that is due to missing-modality LGE-only scar and whether it matters for official validation.
- Expansion criterion: only prepare folds 1-4 if full-modality fold0 beats nnU-Net edema and maintains the scar advantage, or if the official-validation-specific rationale is strong enough to justify a submission ablation.

## Hard constraints

- No 1000/2000 epoch runs.
- Single train/eval job walltime <=8h.
- Do not overwrite previous round predictions or metrics.
- Do not use GT masks or labels in postprocess/export rules.
- Do not change edema semantics to scar union; strict CARE class_4 edema and class_5 scar only.
- Do not treat myocardium/LV/RV/foreground mean as primary objectives.
